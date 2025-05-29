import os
from state import state
from utils import log, run_command

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
        ipmi = host.get('ipmi_credentials')

        ipmi_host = ipmi.get('host') if ipmi else None
        ipmi_user = ipmi.get('username') if ipmi else None
        ipmi_pass = ipmi.get('password') if ipmi else None
        host_opt = f" -H {str(ipmi_host).strip()}" if ipmi_host and str(ipmi_host).strip() else ""
        user_opt = f" -U {ipmi_user}" if ipmi_user else ""
        pass_opt = f" -P {ipmi_pass}" if ipmi_pass else ""
        lanplus_opt = " -I lanplus" if ipmi else ""
        raw_cmd = f" raw 0x30 0x30 0x02 0xff 0x{int(level):02x}"
        cmd = f"ipmitool{lanplus_opt}{host_opt}{user_opt}{pass_opt}{raw_cmd}".strip()

        if debug:
            log("DEBUG", host_name, f"Planned set fan speed via ipmitool command: {cmd}")
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
        ipmi = host.get('ipmi_credentials')
        ipmi_host = ipmi.get('host') if ipmi else None
        ipmi_user = ipmi.get('username') if ipmi else None
        ipmi_pass = ipmi.get('password') if ipmi else None
        host_opt = f" -H {str(ipmi_host).strip()}" if ipmi_host and str(ipmi_host).strip() else ""
        user_opt = f" -U {ipmi_user}" if ipmi_user else ""
        pass_opt = f" -P {ipmi_pass}" if ipmi_pass else ""
        lanplus_opt = " -I lanplus" if ipmi else ""

        if mode == "manual":
            cmd = f"ipmitool{lanplus_opt}{host_opt}{user_opt}{pass_opt} raw 0x30 0x30 0x01 0x00".strip()
        elif mode == "automatic":
            cmd = f"ipmitool{lanplus_opt}{host_opt}{user_opt}{pass_opt} raw 0x30 0x30 0x01 0x01".strip()
        else:
            log("WARN", host_name, f"Unknown fan control mode: {mode}")
            state[host_name]['fan_control_mode'] = mode
            return
        
        if mode == "automatic":
            state[host_name]['fan_speed'] = 0

        if debug:
            log("DEBUG", host_name, f"Planned Set fan control command: {cmd}")
            state[host_name]['fan_control_mode'] = mode
            return

        try:
            output, error = run_command(host, cmd, logger=log, log_tag=host_name, debug=debug)
            if output:
                log("DEBUG", host_name, f"Command output: {output}")
            if error:
                log("ERROR", host_name, f"Command error: {error}")
            else:
                state[host_name]['fan_control_mode'] = mode
        except Exception as e:
            log("ERROR", host_name, f"Error setting fan control: {e}")

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
