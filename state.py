state = {}

def init_state_from_config(hosts):
    global state
    state.clear()
    for host in hosts:
        host_name = host['name']
        state[host_name] = {
            'fan_control_mode': 'automatic',
            'fan_speed': 0,
            'temp_avg': None,
            'temp_max': None,
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
                    'last_updated': None,
                    'temps': []
                }
