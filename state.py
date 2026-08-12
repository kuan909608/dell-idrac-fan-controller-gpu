state = {}

def init_state_from_config(hosts):
    global state
    state.clear()
    for host in hosts:
        host_name = host['name']
        state[host_name] = {
            'dry_run': False,
            'fan_control_mode': 'automatic',
            'fan_speed': 0,
            'temp_avg': None,
            'temp_max': None,
            'cpu_temps': [],
            'gpu_temps': [],
            'control_temperature': None,
            'sensor_status': 'initializing',
            'last_error': None,
            'last_updated': None,
            'temps': [],
            'vms': {}
        }
        if 'vms' in host and isinstance(host['vms'], list):
            for vm in host['vms']:
                vm_name = vm['name']
                state[host_name]['vms'][vm_name] = {
                    'temp_avg': None,
                    'temp_max': None,
                    'gpu_temps': [],
                    'sensor_status': 'initializing',
                    'last_error': None,
                    'last_updated': None,
                    'temps': []
                }
