#!/usr/bin/env python3

import signal
import sys
import time
import datetime

from config_loader import Config, ConfigError
from state import state, init_state_from_config
from fan_controller import FanController
from temp_monitor import TempMonitor
from utils import log

config = Config("fan_control_config.yaml")
init_state_from_config(config.hosts)

def main():
    controller = FanController(config)
    monitor = TempMonitor(config)
    debug = config.general.get('debug', False)
    for host in config.hosts:
        thresholds_str = "，".join(
            f"{t:.2f}°C ({s}%)" for t, s in zip(host['temperatures'], host['speeds'])
        )
        log("INFO", host['name'], f"Host temperature thresholds: {thresholds_str}")
        log("INFO", host['name'], f"Host temperature hysteresis: {host['hysteresis']:.2f}°C")
        controller.set_fan_control(host.get('fan_control_mode', 'manual'), host)
        if debug:
            log("DEBUG", host['name'], f"Host config: {host}")

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

                all_gpu_temps = list(gpu_temps) if gpu_temps else []
                all_gpu_temps.extend(vm_gpu_temps)

                if cpu_temps is None:
                    log("ERROR", host['name'], "Host CPU temperature data error, fans running at full speed", file=sys.stderr)
                    temp_avg = 999
                    temp_max = 999
                    control_temperature = 999
                else:
                    cpu_avg = round(sum(cpu_temps) / len(cpu_temps), 2)
                    cpu_max = round(max(cpu_temps), 2)
                    log("INFO", host['name'], f"Host CPU avg temperature: {cpu_avg:.2f}°C")
                    log("INFO", host['name'], f"Host CPU max temperature: {cpu_max:.2f}°C")

                    if all_gpu_temps:
                        gpu_avg = round(sum(all_gpu_temps) / len(all_gpu_temps), 2)
                        gpu_max = round(max(all_gpu_temps), 2)
                        log("INFO", host['name'], f"Host GPU avg temperature: {gpu_avg:.2f}°C")
                        log("INFO", host['name'], f"Host GPU max temperature: {gpu_max:.2f}°C")
                    else:
                        gpu_avg = None
                        gpu_max = None
                        log("INFO", host['name'], "No GPU temperature data for host, using CPU only.")

                    all_temps = []
                    if cpu_max is not None:
                        all_temps.append(cpu_max)
                    if all_gpu_temps:
                        all_temps.extend(all_gpu_temps)
                    if all_temps:
                        temp_avg = round(sum(all_temps) / len(all_temps), 2)
                        temp_max = round(max(all_temps), 2)
                    else:
                        temp_avg = None
                        temp_max = None
                    log("INFO", host['name'], f"Host all avg temperature: {temp_avg:.2f}°C")
                    log("INFO", host['name'], f"Host all max temperature: {temp_max:.2f}°C")

                    mode = config.general.get('temperature_control_mode', 'max')
                    if mode == 'avg':
                        if all_temps:
                            control_temperature = temp_avg
                        else:
                            control_temperature = 999
                        log("INFO", host['name'], f"Host control temperature (avg): {control_temperature:.2f}°C")
                    else:
                        if gpu_max is not None:
                            control_temperature = temp_max
                        else:
                            control_temperature = 999
                        log("INFO", host['name'], f"Host control temperature (max): {control_temperature:.2f}°C")

                state[host['name']]['temps'].append({
                    'temp_avg': temp_avg,
                    'temp_max': temp_max,
                    'last_updated': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                state[host['name']]['last_updated'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                controller.apply_fan_speed(control_temperature, host)
            except Exception as e:
                log("ERROR", host['name'], f"Unexpected error: {e}", file=sys.stderr)
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
