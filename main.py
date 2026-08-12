#!/usr/bin/env python3

import os
import signal
import sys
import time
import datetime

from config_loader import Config, ConfigError, ConfigWatcher
from state import state, init_state_from_config
from fan_controller import FanController
from temp_monitor import TempMonitor
from utils import log, redact_mapping
from control_policy import SensorSnapshot, determine_control_temperature
from lifecycle import restore_automatic_control
from monitoring_web import MonitoringServer, WebSettings

def web_settings(config):
    if not config.general.get('web_enabled', True):
        return None
    return WebSettings(
        host=config.general.get('web_host', '127.0.0.1'),
        port=config.general.get('web_port', 8080),
        stale_after_seconds=max(180, config.general.get('interval', 60) * 3),
    )


def start_web_server(settings):
    if settings is None:
        return None
    server = MonitoringServer(state, settings)
    server.start()
    web_host, web_port = server.address
    log("INFO", "web", f"Read-only monitoring available at http://{web_host}:{web_port}")
    return server


def configure_hosts(config, controller):
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


def apply_config_reload(config, candidate, controller, monitor, on_reload=None):
    old_hosts = config.hosts
    failures = restore_automatic_control(controller, old_hosts, logger=log)
    if failures:
        log(
            "ERROR",
            "CONFIG",
            "Configuration reload rejected; failed to restore automatic fan control for: "
            + ", ".join(failures),
            file=sys.stderr,
        )
        configure_hosts(config, controller)
        return False

    try:
        if on_reload:
            on_reload(candidate)
    except Exception as exc:
        log("ERROR", "CONFIG", f"Configuration reload rejected: {exc}", file=sys.stderr)
        configure_hosts(config, controller)
        return False

    config.general = candidate.general
    config.hosts = candidate.hosts
    controller.config = config
    monitor.config = config
    init_state_from_config(config.hosts)
    configure_hosts(config, controller)
    log("INFO", "CONFIG", "Configuration reloaded successfully.")
    return True


def main(config_path="fan_control_config.yaml"):
    config = Config(config_path)
    config_watcher = ConfigWatcher(config_path)
    init_state_from_config(config.hosts)
    controller = FanController(config)
    monitor = TempMonitor(config)
    current_web_settings = web_settings(config)
    web_server = start_web_server(current_web_settings)

    def reconfigure_web(candidate):
        nonlocal web_server, current_web_settings
        next_settings = web_settings(candidate)
        if next_settings == current_web_settings:
            return

        previous_settings = current_web_settings
        if web_server:
            web_server.stop()
            web_server = None
        try:
            web_server = start_web_server(next_settings)
        except Exception:
            web_server = start_web_server(previous_settings)
            raise
        current_web_settings = next_settings

    try:
        run_controller(
            config,
            controller,
            monitor,
            config_watcher=config_watcher,
            on_reload=reconfigure_web,
        )
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


def run_controller(config, controller, monitor, config_watcher=None, on_reload=None):
    configure_hosts(config, controller)
    log("INFO", "main", "=" * 50)
    log("INFO", "main", "Initialization complete. Start main loop.")
    log("INFO", "main", "=" * 50)
    
    while True:
        if config_watcher:
            try:
                candidate = config_watcher.load_if_changed()
                if candidate:
                    apply_config_reload(
                        config, candidate, controller, monitor, on_reload=on_reload
                    )
            except (ConfigError, OSError, RuntimeError) as exc:
                log(
                    "ERROR",
                    "CONFIG",
                    f"Configuration reload rejected; keeping previous settings: {exc}",
                    file=sys.stderr,
                )

        debug = config.general.get('debug', False)
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
                gpu_temps, host_gpu_error = monitor.get_gpu_temps(host)
                if debug:
                    log("DEBUG", host['name'], f"Host CPU temperature: {cpu_temps}")
                    log("DEBUG", host['name'], f"Host GPU temperature: {gpu_temps}")

                vm_gpu_temps = []
                gpu_source_errors = []
                if host.get('gpu_type') and not gpu_temps:
                    gpu_source_errors.append(host_gpu_error or 'Host GPU temperature unavailable')
                if 'vms' in host and isinstance(host['vms'], list):
                    for vm in host['vms']:
                        temps, vm_error = monitor.get_gpu_temps(host, vm['name'])
                        if debug:
                            log("DEBUG", host['name'], f"VM {vm['name']} GPU temps: {temps}")
                        if temps:
                            vm_gpu_temps.extend(temps)
                        else:
                            gpu_source_errors.append(
                                vm_error or f"VM {vm['name']} GPU temperature unavailable"
                            )
                        vm_state = state[host['name']]['vms'][vm['name']]
                        vm_state['gpu_temps'] = list(temps or [])
                        vm_state['sensor_status'] = 'ok' if temps else 'error'
                        vm_state['last_error'] = None if temps else (vm_error or 'GPU temperature unavailable')
                        vm_state['last_updated'] = datetime.datetime.now().astimezone().isoformat()

                all_gpu_temps = list(gpu_temps) if gpu_temps else []
                all_gpu_temps.extend(vm_gpu_temps)

                decision = determine_control_temperature(
                    SensorSnapshot(
                        cpu_temps=cpu_temps,
                        gpu_temps=all_gpu_temps,
                        gpu_sources_healthy=not gpu_source_errors,
                    ),
                    mode=config.general.get('temperature_control_mode', 'max'),
                )

                if decision.fail_safe:
                    log("ERROR", host['name'], "Required temperature data unavailable, fans running at full speed", file=sys.stderr)
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
                if not cpu_temps:
                    host_state['last_error'] = 'CPU temperature unavailable'
                elif gpu_source_errors:
                    host_state['last_error'] = '; '.join(gpu_source_errors)
                else:
                    host_state['last_error'] = None

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
        main(os.environ.get("FAN_CONTROL_CONFIG", "fan_control_config.yaml"))
    except ConfigError as e:
        log("ERROR", "MAIN", "Configuration error: {}".format(e), file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        log("ERROR", "MAIN", "An unexpected error occurred: {}".format(e), file=sys.stderr)
        sys.exit(1)
