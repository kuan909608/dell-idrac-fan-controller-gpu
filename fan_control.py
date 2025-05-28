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
            f"{t}°C ({s}%)" for t, s in zip(host['temperatures'], host['speeds'])
        )
        log("INFO", host['name'], f"Host thresholds (temperature thresholds): {thresholds_str}")
        controller.set_fan_control(host.get('fan_control_mode', 'manual'), host)
        if debug:
            log("DEBUG", host['name'], f"Host config: {host}")

    while True:
        for host in config.hosts:
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
                    log("INFO", host['name'], f"Host CPU avg temperature: {cpu_avg:.2f}")
                    log("INFO", host['name'], f"Host CPU max temperature: {cpu_max:.2f}")

                    if all_gpu_temps:
                        gpu_avg = round(sum(all_gpu_temps) / len(all_gpu_temps), 2)
                        gpu_max = round(max(all_gpu_temps), 2)
                        log("INFO", host['name'], f"Host GPU avg temperature: {gpu_avg:.2f}")
                        log("INFO", host['name'], f"Host GPU max temperature: {gpu_max:.2f}")
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
                    log("INFO", host['name'], f"Host temp_avg (all): {temp_avg}")
                    log("INFO", host['name'], f"Host temp_max (all): {temp_max}")

                    mode = config.general.get('temperature_control_mode', 'max')
                    if mode == 'avg':
                        if all_temps:
                            control_temperature = temp_avg
                        else:
                            control_temperature = 999
                        log("INFO", host['name'], f"Host control temperature (avg): {control_temperature:.2f}")
                    else:
                        if gpu_max is not None:
                            control_temperature = temp_max
                        else:
                            control_temperature = 999
                        log("INFO", host['name'], f"Host control temperature (max): {control_temperature:.2f}")

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
