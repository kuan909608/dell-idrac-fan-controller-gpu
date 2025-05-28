import os
from typing import List, Optional
from state import state
from utils import log, run_command

class TempMonitor:
    def __init__(self, config):
        self.config = config

    def get_cpu_temps(self, host: dict) -> Optional[List[float]]:
        if 'name' not in host:
            log("WARN", "TEMP", f"Invalid host configuration: {host}")
            return None
        if host['name'] not in state:
            log("WARN", host.get('name', 'TEMP'), f"Host {host['name']} not found in state.")
            return None

        debug = self.config.general.get('debug', False)
        ssh_creds = host.get('ssh_credentials')
        ssh_command = self.config.general['cpu_temperature_command']

        temps = []
        try:
            if debug:
                log("DEBUG", host['name'], f"Command for {host['name']}: {ssh_command}")
            output, error = run_command(host, ssh_command, logger=log, log_tag=host['name'])
            if error or not output or not output.strip():
                log("ERROR", host['name'], f"Error getting CPU temps from host {host['name']}: {error if error else 'No output'}")
                return None
            temps = [float(n) for n in output.strip().split(';') if n]
        except Exception as e:
            log("ERROR", host['name'], f"Error getting CPU temps from host {host['name']}: {e}")
            return None
        return temps if temps else None

    def get_cpu_temp_overall(self, host: dict) -> Optional[float]:
        temps = self.get_cpu_temps(host)
        if temps:
            return max(temps)
        return None

    def get_gpu_temps(self, host: dict, vm_name: Optional[str] = None) -> Optional[List[float]]:
        if vm_name is not None:
            device = next((v for v in host.get('vms', []) if v['name'] == vm_name), None)
            if not device:
                log("WARN", host['name'], f"VM ({vm_name}) not found in host {host['name']}.")
                return None
        else:
            device = host

        name = device.get('name', '')
        ssh_creds = device['ssh_credentials']
        gpu_type = device.get('gpu_type')
        if not gpu_type or (isinstance(gpu_type, list) and len(gpu_type) == 0):
            return None
        if isinstance(gpu_type, list):
            gpu_types = [str(gt).lower() for gt in gpu_type]
        elif isinstance(gpu_type, str):
            gpu_types = [gpu_type.lower()]
        else:
            gpu_types = []

        cmds = []
        if any('nvidia' in gt for gt in gpu_types):
            cmds.append(self.config.general['gpu_temperature_command_nvidia'])
        if any('amd' in gt for gt in gpu_types):
            cmds.append(self.config.general['gpu_temperature_command_amd'])

        if not cmds:
            log("WARN", name, f"Device {name} has invalid GPU type: {gpu_type}")
            return None

        temps = []
        for ssh_command in cmds:
            output, error = run_command(device, ssh_command, logger=log, log_tag=name)
            if error or not output or not isinstance(output, str) or not output.strip():
                log("ERROR", name, f"Error getting GPU temps from Device {name}: {error if error else 'No output'}")
                continue
            for n in output.strip().split(';'):
                try:
                    temps.append(float(n))
                except ValueError:
                    log("WARN", name, f"Warning: The GPU temperature response is not a numeric value: {n}")
                    continue
        return temps if temps else None
