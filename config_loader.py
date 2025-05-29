import os
import sys
import yaml
from utils import log, auto_split_thresholds

class ConfigError(Exception):
    pass

class Config:
    def __init__(self, config_path="fan_control_config.yaml"):
        self.general = {
            'debug': False,
            'interval': 60,
            'temperature_control_mode': 'max',
            'cpu_temperature_command': 'sensors | grep -E "Core [0-9]+:" | awk \'{print $3}\' | sed \'s/+//;s/°C//\' | paste -sd \';\' -',
            'gpu_temperature_command_nvidia': 'nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | paste -sd \';\' -',
            'gpu_temperature_command_amd': 'rocm-smi --showtemp | grep -E "Temp" | awk \'{print $2}\' | sed \'s/[^0-9.]//g\' | paste -sd \';\' -'
        }
        self.hosts = []
        self.config_paths = ['fan_control.yaml', '/opt/fan_control/fan_control.yaml']

        self.load_config_from_file(config_path)

    def load_config_from_file(self, config_path):
        _debug = self.general['debug']
        _interval = self.general['interval']
        _temperature_control_mode = self.general['temperature_control_mode']
        _cpu_temperature_command = self.general['cpu_temperature_command']
        _gpu_temperature_command_nvidia = self.general['gpu_temperature_command_nvidia']
        _gpu_temperature_command_amd = self.general['gpu_temperature_command_amd']

        if config_path and os.path.isfile(config_path):
            use_path = config_path
        else:
            use_path = None
            for path in self.config_paths:
                if os.path.isfile(path):
                    use_path = path
                    break
        if not use_path:
            raise RuntimeError("Missing or unspecified configuration file.")
        else:
            log("INFO", "CONFIG", f"Loading configuration file from {use_path}.")
            _config = None
            try:
                with open(use_path, 'r', encoding='utf-8') as yaml_conf:
                    _config = yaml.safe_load(yaml_conf)
            except yaml.YAMLError as err:
                log("ERROR", "CONFIG", f"YAML configuration error in {use_path}: {err}", file=sys.stderr)
                raise ConfigError("Failed to load YAML configuration.")

            config_section = _config.get("general", {})
            _config["general"] = {
                'debug': config_section.get('debug', _debug),
                'interval': config_section.get('interval', _interval),
                'temperature_control_mode': config_section.get('temperature_control_mode', _temperature_control_mode),
                'cpu_temperature_command': config_section.get('cpu_temperature_command', _cpu_temperature_command),
                'gpu_temperature_command_nvidia': config_section.get('gpu_temperature_command_nvidia', _gpu_temperature_command_nvidia),
                'gpu_temperature_command_amd': config_section.get('gpu_temperature_command_amd', _gpu_temperature_command_amd),
            }

        self.load_config_sections(_config)

    def load_config_sections(self, _config):
        if not isinstance(_config, dict):
            raise ConfigError("Config file must be a dictionary.")

        self.load_general_config(_config)
        self.load_hosts_config(_config)

    def load_general_config(self, _config):
        general_config = _config.get('general', {})
        self.general['debug'] = general_config.get('debug', False)
        self.general['interval'] = general_config.get('interval', 60)
        self.general['temperature_control_mode'] = general_config.get('temperature_control_mode', 'max')
        self.general['cpu_temperature_command'] = general_config.get('cpu_temperature_command', 'sensors | grep -E "Core [0-9]+:" | awk \'{print $3}\' | sed \'s/+//;s/°C//\' | paste -sd \';\' -')
        self.general['gpu_temperature_command_nvidia'] = general_config.get('gpu_temperature_command_nvidia', 'nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | paste -sd \';\' -')
        self.general['gpu_temperature_command_amd'] = general_config.get('gpu_temperature_command_amd', 'rocm-smi --showtemp | grep -E "Temp" | awk \'{print $2}\' | sed \'s/[^0-9.]//g\' | paste -sd \';\' -')

    def load_hosts_config(self, _config):
        if 'hosts' not in _config:
            raise ConfigError('Missing "hosts" section in configuration file.')

        self.hosts = _config['hosts']

        for host in self.hosts:
            if 'name' not in host or not isinstance(host['name'], str):
                raise ConfigError("Each host must have a non-empty 'name' field.")

            if 'fan_control_mode' not in host or host['fan_control_mode'] not in ['manual', 'automatic']:
                raise ConfigError(f'Host "{host["name"]}" must have "fan_control_mode" set to "manual" or "automatic".')

            if 'ipmi_credentials' in host and host['ipmi_credentials']:
                ipmi_creds = host['ipmi_credentials']
                for key in ['host', 'username', 'password']:
                    if key not in ipmi_creds or not ipmi_creds[key]:
                        raise ConfigError(f'Host "{host["name"]}" missing "{key}" in ipmi_credentials.')

            host['hysteresis'] = host.get('hysteresis', 0)

            if (
                isinstance(host['temperatures'], list) and
                isinstance(host['speeds'], list) and
                len(host['temperatures']) == 2 and
                len(host['speeds']) == 2 and
                host['hysteresis'] > 0
            ):
                t_min, t_max = host['temperatures']
                s_min, s_max = host['speeds']
                thresholds, speeds = auto_split_thresholds(t_min, t_max, s_min, s_max, host['hysteresis'])
                host['temperatures'] = thresholds
                host['speeds'] = speeds
            else:
                if len(host['temperatures']) != len(host['speeds']):
                    raise ConfigError(f'Host "{host["name"]}" temperatures and speeds count must be equal.')
                if not isinstance(host['temperatures'], list) or not all(isinstance(x, (int, float)) for x in host['temperatures']):
                    raise ConfigError(f'Host "{host["name"]}" temperatures must be a list of numbers.')
                if not isinstance(host['speeds'], list) or not all(isinstance(x, (int, float)) for x in host['speeds']):
                    raise ConfigError(f'Host "{host["name"]}" speeds must be a list of numbers.')
                if len(host['temperatures']) < 2:
                    raise ConfigError(f'Host "{host["name"]}" must have at least 2 temperature thresholds and fan speeds.')
                if any(host['temperatures'][i] > host['temperatures'][i+1] for i in range(len(host['temperatures']) - 1)):
                    raise ConfigError(f'Host "{host["name"]}" temperatures must be in ascending order or equal.')
                if any(host['speeds'][i] > host['speeds'][i+1] for i in range(len(host['speeds']) - 1)):
                    raise ConfigError(f'Host "{host["name"]}" speeds must be in ascending order or equal.')

            if 'ssh_credentials' in host and host['ssh_credentials']:
                creds = host['ssh_credentials']
                for key in ['host', 'username', 'password']:
                    if key not in creds or not creds[key]:
                        raise ConfigError(f'Host "{host.get("name", "unknown")}" missing "{key}" in ssh_credentials.')
                if 'key_path' in creds and creds['key_path'] and not isinstance(creds['key_path'], str):
                    raise ConfigError(f'Host "{host.get("name", "unknown")}" key_path in ssh_credentials must be a string if provided.')

            if 'gpu_type' in host:
                if isinstance(host['gpu_type'], str):
                    host['gpu_type'] = [host['gpu_type']]
                if not isinstance(host['gpu_type'], list) or not all(x in ['nvidia', 'amd'] for x in host['gpu_type']):
                    raise ConfigError(f'Host "{host["name"]}" gpu_type must be an array containing only "nvidia" or "amd", e.g. ["nvidia", "amd"]')
                if 'nvidia' in host['gpu_type'] and 'gpu_temperature_command_nvidia' in self.general:
                    if not self.general['gpu_temperature_command_nvidia']:
                        raise ConfigError(f'Host "{host["name"]}" general config is missing gpu_temperature_command_nvidia command')
                if 'amd' in host['gpu_type'] and 'gpu_temperature_command_amd' in self.general:
                    if not self.general['gpu_temperature_command_amd']:
                        raise ConfigError(f'Host "{host["name"]}" general config is missing gpu_temperature_command_amd command')

            if 'vms' in host:
                self.load_vms_config(host)

    def load_vms_config(self, host):
        for vm in host['vms']:
            if 'name' not in vm or not isinstance(vm['name'], str) or not vm['name']:
                raise ConfigError(f'VM in host "{host.get("name", "unknown")}" must have a non-empty "name" field.')
            if 'ssh_credentials' not in vm:
                raise ConfigError(f'VM "{vm.get("name", "unknown")}" must include "ssh_credentials".')
            creds = vm['ssh_credentials']
            for key in ['host', 'username', 'password']:
                if key not in creds or not creds[key]:
                    raise ConfigError(f'VM "{vm.get("name", "unknown")}" missing "{key}" in ssh_credentials.')
            if 'key_path' in creds and creds['key_path'] and not isinstance(creds['key_path'], str):
                raise ConfigError(f'VM "{vm.get("name", "unknown")}" key_path in ssh_credentials must be a string if provided.')
            if 'gpu_type' not in vm:
                raise ConfigError(f'VM "{vm.get("name", "unknown")}" must specify gpu_type')
            if isinstance(vm['gpu_type'], str):
                vm['gpu_type'] = [vm['gpu_type']]
            if not isinstance(vm['gpu_type'], list) or not all(x in ['nvidia', 'amd'] for x in vm['gpu_type']):
                raise ConfigError(f'VM "{vm.get("name", "unknown")}" gpu_type must be an array containing only "nvidia" or "amd", e.g. ["nvidia", "amd"]')
