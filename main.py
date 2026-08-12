#!/usr/bin/env python3

import signal
import sys
import time
import datetime

from config_loader import Config, ConfigError
from state import state, init_state_from_config
from fan_controller import FanController
from temp_monitor import TempMonitor
from utils import log, redact_mapping
from control_policy import SensorSnapshot, determine_control_temperature
from lifecycle import restore_automatic_control
from monitoring_web import MonitoringServer, WebSettings

def main(config_path="fan_control_config.yaml"):
    config = Config(config_path)
    init_state_from_config(config.hosts)
    controller = FanController(config)
    monitor = TempMonitor(config)
    web_server = None
    if config.general.get('web_enabled', True):
        web_server = MonitoringServer(
            state,
            WebSettings(
                host=config.general.get('web_host', '127.0.0.1'),
                port=config.general.get('web_port', 8080),
            ),
        )
        web_server.start()
        web_host, web_port = web_server.address
        log("INFO", "web", f"Read-only monitoring available at http://{web_host}:{web_port}")
    try:
        run_controller(config, controller, monitor)
    finally:
        if web_server:
            web_server.stop()
        failures = restore_automatic_control(controller, config.hosts, logger=log)
        if failures:
            log(
                "ERROR",
                "main",
                "Failed to restore automatic fan control for: " + ", ".join(failures),
                file=sys.stderr,
            )


def run_controller(config, controller, monitor):
    debug = config.general.get('debug', False)
    for host in config.hosts:
        thresholds_str = ", ".join(
            f"{t:.2f}°C ({s}%)" for t, s in zip(host['temperatures'], host['speeds'])
        )
        log("INFO", host['name'], f"Host temperature thresholds: {thresholds_str}")
        log("INFO", host['name'], f"Host temperature hysteresis: {host['hysteresis']:.2f}°C")
        controller.set_fan_control(host.get('fan_control_mode', 'manual'), host)
        if debug:
            log("DEBUG", host['name'], f"Host config: {redact_mapping(host)}")

    log("INFO", "main", "=" * 50)
    log("INFO", "main", "Initialization complete. Start main loop.")
    log("INFO", "main", "=" * 50)
    
    while True:
        for host in config.hosts:
            log("INFO", host['name'], "-" * 50)
            ip = (
                host.get('ipmi_credentials', {}).get('host')
                or host.get('ssh_credentials', {}).get('host')
                or 'localhost'
            )
            log("INFO", host['name'], f"Host: {host['name']}, IP: {ip}")
            log("INFO", host['name'], "-" * 50)

            try:
                cpu_temps = monitor.get_cpu_temps(host)
                gpu_temps = monitor.get_gpu_temps(host)
                if debug:
                    log("DEBUG", host['name'], f"Host CPU temperature: {cpu_temps}")
                    log("DEBUG", host['name'], f"Host GPU temperature: {gpu_temps}")

                vm_gpu_temps = []
                if 'vms' in host and isinstance(host['vms'], list):
                    for vm in host['vms']:
                        temps = monitor.get_gpu_temps(host, vm['name'])
                        if debug:
                            log("DEBUG", host['name'], f"VM {vm['name']} GPU temps: {temps}")
                        if temps:
                            vm_gpu_temps.extend(temps)
                        vm_state = state[host['name']]['vms'][vm['name']]
                        vm_state['gpu_temps'] = list(temps or [])
                        vm_state['sensor_status'] = 'ok' if temps else 'error'
                        vm_state['last_error'] = None if temps else 'GPU temperature unavailable'
                        vm_state['last_updated'] = datetime.datetime.now().astimezone().isoformat()

                all_gpu_temps = list(gpu_temps) if gpu_temps else []
                all_gpu_temps.extend(vm_gpu_temps)

                decision = determine_control_temperature(
                    SensorSnapshot(cpu_temps=cpu_temps, gpu_temps=all_gpu_temps),
                    mode=config.general.get('temperature_control_mode', 'max'),
                )

                if decision.fail_safe:
                    log("ERROR", host['name'], "Host CPU temperature data error, fans running at full speed", file=sys.stderr)
                else:
                    log("INFO", host['name'], f"Host CPU avg temperature: {decision.cpu_avg:.2f}°C")
                    log("INFO", host['name'], f"Host CPU max temperature: {decision.cpu_max:.2f}°C")

                    if all_gpu_temps:
                        log("INFO", host['name'], f"Host GPU avg temperature: {decision.gpu_avg:.2f}°C")
                        log("INFO", host['name'], f"Host GPU max temperature: {decision.gpu_max:.2f}°C")
                    else:
                        log("INFO", host['name'], "No GPU temperature data for host, using CPU only.")

                    log("INFO", host['name'], f"Host all avg temperature: {decision.combined_avg:.2f}°C")
                    log("INFO", host['name'], f"Host all max temperature: {decision.combined_max:.2f}°C")
                    mode = config.general.get('temperature_control_mode', 'max')
                    log("INFO", host['name'], f"Host control temperature ({mode}): {decision.control_temperature:.2f}°C")

                temp_avg = decision.combined_avg
                temp_max = decision.combined_max
                control_temperature = decision.control_temperature
                host_state = state[host['name']]
                host_state['cpu_temps'] = list(cpu_temps or [])
                host_state['gpu_temps'] = list(all_gpu_temps or [])
                host_state['control_temperature'] = control_temperature
                host_state['sensor_status'] = 'error' if decision.fail_safe else 'ok'
                host_state['last_error'] = 'CPU temperature unavailable' if decision.fail_safe else None

                host_state['temps'].append({
                    'temp_avg': temp_avg,
                    'temp_max': temp_max,
                    'last_updated': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                host_state['temps'] = host_state['temps'][-120:]
                host_state['last_updated'] = datetime.datetime.now().astimezone().isoformat()
                controller.apply_fan_speed(control_temperature, host)
            except Exception as e:
                log("ERROR", host['name'], f"Unexpected error: {e}", file=sys.stderr)
                state[host['name']]['sensor_status'] = 'error'
                state[host['name']]['last_error'] = str(e)
                state[host['name']]['control_temperature'] = 999.0
                state[host['name']]['last_updated'] = datetime.datetime.now().astimezone().isoformat()
                controller.apply_fan_speed(999, host)

        time.sleep(config.general['interval'])

        log("INFO", "main", "=" * 50)
        log("INFO", "main", f"Loop triggered by interval ({config.general['interval']} seconds)")
        log("INFO", "main", "=" * 50)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))

    try:
        main()
    except ConfigError as e:
        log("ERROR", "MAIN", "Configuration error: {}".format(e), file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        log("ERROR", "MAIN", "An unexpected error occurred: {}".format(e), file=sys.stderr)
        sys.exit(1)
