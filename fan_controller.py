import os
from state import state
from utils import CommandSpec, format_command, log, run_command


def _build_ipmi_command(host: dict, raw_args) -> CommandSpec:
    ipmi = host.get('ipmi_credentials')
    argv = ['ipmitool']
    stdin_data = None
    if ipmi:
        argv.extend([
            '-I', 'lanplus',
            '-H', str(ipmi['host']).strip(),
            '-U', str(ipmi['username']),
            '-f', '/dev/stdin',
        ])
        stdin_data = f"{ipmi['password']}\n"
    argv.extend(raw_args)
    return CommandSpec(argv=argv, stdin_data=stdin_data)


def build_ipmi_control_command(host: dict, mode: str) -> CommandSpec:
    mode_value = {'manual': '0x00', 'automatic': '0x01'}.get(mode)
    if mode_value is None:
        raise ValueError(f"Unknown fan control mode: {mode}")
    return _build_ipmi_command(host, ['raw', '0x30', '0x30', '0x01', mode_value])


def build_ipmi_speed_command(host: dict, level: float) -> CommandSpec:
    return _build_ipmi_command(
        host,
        ['raw', '0x30', '0x30', '0x02', '0xff', f'0x{int(level):02x}'],
    )

class FanController:
    def __init__(self, config):
        self.config = config

    def check_hysteresis(self, temp: float, threshold_temp: float, hysteresis: float) -> bool:
        return threshold_temp - hysteresis <= temp <= threshold_temp + hysteresis

    def compute_fan_speed_level(self, temp: float, host: dict) -> float:
        debug = self.config.general.get('debug', False)
        temperatures = host['temperatures']
        hysteresis = host['hysteresis']
        speeds = host['speeds']
        for i in range(len(temperatures)):
            if self.check_hysteresis(temp, temperatures[i], hysteresis):
                if debug:
                    log(
                        "DEBUG", host.get('name', 'FAN'), f"Temp={temp:.2f}°C, threshold={temperatures[i]:.2f}°C (hysteresis={hysteresis:.2f}°C), use speed={speeds[i]}% [IN HYSTERESIS]")
                return speeds[i]
            if temp <= temperatures[i]:
                if debug:
                    log("DEBUG", host.get('name', 'FAN'), f"Temp={temp:.2f}°C, threshold={temperatures[i]:.2f}°C (hysteresis={hysteresis:.2f}°C), use speed={speeds[i-1] if i > 0 else speeds[0]}% [NO HYSTERESIS]")
                return speeds[i - 1] if i > 0 else speeds[0]

        if debug:
            log("DEBUG", host.get('name', 'FAN'), f"temp={temp:.2f}°C did not match any threshold, fallback speeds[-1]={speeds[0]}%")
        return speeds[-1]

    def set_fan_speed(self, level: float, host: dict):
        debug = self.config.general.get('debug', False)
        host_name = host.get('name', 'host')
        cmd = build_ipmi_speed_command(host, level)

        if debug:
            log("DEBUG", host_name, f"Planned set fan speed via ipmitool command: {format_command(cmd)}")
            if host_name in state:
                state[host_name]['fan_speed'] = int(level)
            return

        try:
            output, error = run_command(host, cmd, logger=log, log_tag=host_name, debug=debug)
            if debug:
                log("DEBUG", host_name, f"Command output: {output}")
            if error:
                log("ERROR", host_name, f"Command error: {error}")
            else:
                if host_name in state:
                    state[host_name]['fan_speed'] = int(level)
        except Exception as e:
            log("ERROR", host_name, f"Error setting fan speed: {e}")

    def set_fan_control(self, mode: str, host: dict):
        host_name = host.get('name')
        debug = self.config.general.get('debug', False)
        try:
            cmd = build_ipmi_control_command(host, mode)
        except ValueError:
            log("WARN", host_name, f"Unknown fan control mode: {mode}")
            state[host_name]['fan_control_mode'] = mode
            return False
        
        if mode == "automatic":
            state[host_name]['fan_speed'] = 0

        if debug:
            log("DEBUG", host_name, f"Planned Set fan control command: {format_command(cmd)}")
            state[host_name]['fan_control_mode'] = mode
            return True

        try:
            output, error = run_command(host, cmd, logger=log, log_tag=host_name, debug=debug)
            if output:
                log("DEBUG", host_name, f"Command output: {output}")
            if error:
                log("ERROR", host_name, f"Command error: {error}")
                return False
            else:
                state[host_name]['fan_control_mode'] = mode
                return True
        except Exception as e:
            log("ERROR", host_name, f"Error setting fan control: {e}")
            return False

    def apply_fan_speed(self, temp: float, host: dict):
        if 'name' not in host:
            log("WARN", "FAN", "Invalid host config, missing name.")
            return

        level = self.compute_fan_speed_level(temp, host)
        self.set_fan_speed(level, host)

        log("INFO", host['name'], "Temp: {:.2f}°C, Mode: {}, Speed: {}%".format(
            temp,
            state[host['name']]['fan_control_mode'],
            state[host['name']]['fan_speed']
        ))
