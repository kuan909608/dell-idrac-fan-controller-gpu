[English](README.md) | [繁體中文](README.zh-TW.md)

# Dell iDRAC Fan Controller with GPU Support

> A temperature-based fan speed controller for Dell PowerEdge servers. The project was historically reported on an R730, but every model, iDRAC firmware, GPU, and deployment combination requires independent verification; see [COMPATIBILITY.md](COMPATIBILITY.md).

This fork is designed for homelab and Proxmox users running local AI or other GPU workloads on Dell PowerEdge hardware. It combines CPU, NVIDIA/AMD GPU, and VM temperature signals so operators can observe thermal health and apply predictable fan curves when vendor defaults are unsuitable for nonstandard accelerators.

> [!CAUTION]
> This software changes physical cooling through raw IPMI commands and may run as root. It cannot guarantee hardware safety. Validate thresholds on your exact server, iDRAC firmware, GPU, and workload; retain out-of-band monitoring; and verify automatic fan restoration during shutdown and failure tests.

- [Requisites](#requisites)
- [Installation / Upgrade](#installation--upgrade)
  - [Docker](#docker)
- [Configuration](#configuration)
- [How it works](#how-it-works)
- [Read-only Web monitoring](#read-only-web-monitoring)
- [Security](#security)
- [Notes on remote hosts](#notes-on-remote-hosts)
- [Credits](#credits)

---

## Requisites

1. Python 3 is installed.
2. **IPMI Over LAN** is enabled in all used iDRACs (_Login > Network/Security > IPMI Settings_).
   - May not be needed if you're only managing the local machine.
3. All hosts to be monitored must have the appropriate sensor tools installed as needed:

   - For monitoring local CPU: install and configure `lm-sensors`
   - For monitoring NVIDIA GPU: install `nvidia-smi`
   - For monitoring AMD GPU: install `rocm-smi`

   - Example output of `sensors` for a dual CPU system:

     ```text
     coretemp-isa-0000
     Adapter: ISA adapter
     Core 0:       +38.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 1:       +46.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 2:       +40.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 8:       +43.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 9:       +39.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 10:      +39.0°C  (high = +69.0°C, crit = +79.0°C)

     coretemp-isa-0001
     Adapter: ISA adapter
     Core 0:       +29.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 1:       +35.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 2:       +29.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 8:       +34.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 9:       +33.0°C  (high = +69.0°C, crit = +79.0°C)
     Core 10:      +31.0°C  (high = +69.0°C, crit = +79.0°C)
     ```

## Installation / Upgrade

Clone the repo and run the installation script as root to configure the system or upgrade the already installed controller:

```text
git clone https://github.com/kuan909608/dell-idrac-fan-controller-gpu.git
cd dell-idrac-fan-controller-gpu
sudo ./install.sh [<installation path>]
```

The default installation path is `/opt/fan_control` and the service will be installed as `fan-control.service`. An existing `fan_control_config.yaml` is preserved unchanged; back it up before editing or upgrading.

### Docker

To deploy remote fan management with Docker (`fan_control` running on a separate host and only interacting with remote ones, see [Notes on remote hosts](#notes-on-remote-hosts)), build the image in the repo and bind mount your own YAML config and SSH keys folder:

```bash
git clone https://github.com/kuan909608/dell-idrac-fan-controller-gpu.git
cd dell-idrac-fan-controller-gpu
mkdir -p config
cp fan_control_config.yaml.example config/fan_control_config.yaml
chmod 600 config/fan_control_config.yaml
docker build -t fan_control .
docker run -d --restart=always --name fan_control \
  -p 127.0.0.1:8080:8080 \
  -v "./config:/config:ro" \
  -v "./keys:/app/keys:ro" \
  -v "$HOME/.ssh/known_hosts:/root/.ssh/known_hosts:ro" \
  fan_control
```

For Docker Web monitoring, set `general.web_host: 0.0.0.0` inside the container. The `-p 127.0.0.1:8080:8080` mapping above still restricts access to the Docker host; use the documented SSH tunnel for remote viewing.

The controller detects changes to `fan_control_config.yaml` before the next control cycle. A changed file is fully validated before use; invalid updates are rejected while the last valid configuration remains active. Reloading a manual-control configuration first restores Dell automatic mode, then applies the validated replacement. Docker deployments must mount the configuration directory as shown above so editors that atomically replace the YAML file remain visible inside the container.

#### Docker Compose

The included `docker-compose.yml` uses the same loopback-only dashboard, reloadable configuration directory, SSH keys, and verified `known_hosts` mounts:

```bash
mkdir -p config keys
cp fan_control_config.yaml.example config/fan_control_config.yaml
chmod 600 config/fan_control_config.yaml
test -f "$HOME/.ssh/known_hosts"
docker compose up -d --build
docker compose logs -f
```

Use `docker compose down` for a graceful stop. Compose allows 30 seconds for the controller to restore Dell automatic fan mode. Do not run this service at the same time as a systemd or standalone Docker deployment controlling the same server.

Running this tool under a proper orchestrator is advised.

---

### Deployment Method Selection Guide

**You can deploy this tool in two ways: systemd (bare-metal) or Docker. Please choose only one method for each host.**

#### When to use systemd (bare-metal)

- Recommended if you need direct access to hardware sensors (e.g., lm-sensors) on the host.
- Suitable for environments where you want the service to start automatically with the OS and be managed by systemd.
- The `install.sh` script automates dependency installation, venv setup, file copying, and systemd service configuration.

#### When to use Docker

- Recommended for remote-only management, or if you want to isolate the environment and simplify migration.
- If you need to access hardware sensors inside Docker, you must mount additional system directories (e.g., `/dev`, `/sys`). Example:
  ```bash
  docker run ... -v /dev:/dev -v /sys:/sys ...
  ```
- Make sure to mount your configuration file and SSH keys as shown above.
- For production, use an orchestrator for better reliability.

#### Important Notes

- **Do not enable both systemd service and Docker container on the same host at the same time.** Running both may cause conflicts or resource contention.
- The `install.sh` script will overwrite existing files and systemd service. Backup your configuration before running it.
- When using SSH keys in Docker, ensure proper permissions and security practices.

## Configuration

You can tune the controller's settings via the `fan_control_config.yaml` file in the installation directory.

Saved changes are loaded automatically before the next control cycle; restarting the process or container is not required. Invalid files are rejected and the last valid settings remain active.

### Configuration File Structure

The configuration file contains two main sections: `general` and `hosts`.

#### `general` section

| Key                              | Description                                                                                       |
| -------------------------------- | ------------------------------------------------------------------------------------------------- |
| `debug`                          | Toggle debug mode (print ipmitool commands instead of executing them, enable additional logging). |
| `interval`                       | How often (in seconds) to read the CPUs' and GPUs' temperatures and adjust the fans' speeds.      |
| `temperature_control_mode`       | Use `max` or `avg` to decide if fan control is based on the maximum or average temperature.       |
| `web_enabled`                    | Enable the read-only monitoring dashboard.                                                        |
| `web_host`                       | Monitoring bind address; defaults to `127.0.0.1`.                                                 |
| `web_port`                       | Monitoring TCP port; defaults to `8080`.                                                          |
| `cpu_temperature_command`        | Shell command to get CPU temperatures (semicolon separated).                                      |
| `gpu_temperature_command_nvidia` | Shell command to get NVIDIA GPU temperatures (semicolon separated).                               |
| `gpu_temperature_command_amd`    | Shell command to get AMD GPU temperatures (semicolon separated).                                  |

#### `hosts` section

Each host object supports the following keys:

| Key                | Description                                                                                                                           |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| `name`             | Host name identifier.                                                                                                                 |
| `fan_control_mode` | Fan control mode, `manual` or `automatic`.                                                                                            |
| `temperatures`     | List of temperature thresholds (in °C). **Must have at least 2 values.**                                                              |
| `speeds`           | List of fan speeds (in %) for each threshold. **Must have at least 2 values.**                                                        |
| `hysteresis`       | Hysteresis value in °C to prevent rapid fan speed changes.                                                                            |
| `ipmi_credentials` | (Optional) IPMI login info for this host.                                                                                             |
| `ssh_credentials`  | (Optional) SSH login info. Requires `host`, `username`, and either `password` or `key_path`. Unknown host keys are rejected. |
| `gpu_type`         | (Optional) Supported GPU types, can be a string (e.g., `nvidia`) or an array (e.g., `[nvidia, amd]`).                                 |
| `vms`              | (Optional) List of VM objects. See below for VM object structure.                                                                     |

##### `vms` objects

Each VM object supports the following keys:

| Key               | Description                                                                                                             |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `name`            | VM name identifier.                                                                                                     |
| `ssh_credentials` | SSH login info for the VM. Requires `host`, `username`, and either `password` or `key_path`. |
| `gpu_type`        | Supported GPU types for the VM, can be a string (e.g., `nvidia`) or an array (e.g., `[nvidia, amd]`).                   |

### Auto-splitting thresholds and speeds

If you only specify 2 pairs of `temperatures` and `speeds` (e.g., `[40, 80]` and `[20, 80]`), the system will automatically split them into multiple steps based on the `hysteresis` value.

The splitting logic:

- The range between `temp_min` and `temp_max` will be divided into intervals of `hysteresis * 2`.
- For each interval, a new threshold and corresponding speed will be generated, resulting in smoother fan speed transitions.

**Example:**

```yaml
temperatures: [40, 80]
speeds: [20, 80]
hysteresis: 5
```

This will be automatically expanded to:

```
thresholds: [40.00, 50.00, 60.00, 70.00, 80.00]
speeds: [20, 35, 50, 65, 80]
```

#### Example

```yaml
general:
  debug: False
  interval: 60
  cpu_temperature_command: "sensors | grep -E 'Core [0-9]+:' | awk '{print $3}' | sed 's/+//;s/°C//' | paste -sd ';' -"
  gpu_temperature_command_nvidia: "nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | paste -sd ';' -"
  gpu_temperature_command_amd: "rocm-smi --showtemp | grep -E 'Temp' | awk '{print \$2}' | sed 's/[^0-9.]//g' | paste -sd ';' -"

hosts:
  - name: host1
    temperatures: [40, 60, 80]
    speeds: [20, 50, 80]
    hysteresis: 5
    ipmi_credentials:
      host: 10.0.0.1
      username: admin
      password: password
    ssh_credentials:
      host: 10.0.0.2
      username: admin
      password: password
    gpu_type: nvidia
    vms:
      - name: vm1
        ssh_credentials:
          host: 10.0.0.3
          username: user
          password: password
        gpu_type: [nvidia]
  - name: host2
    temperatures: [35, 55, 75]
    speeds: [30, 60, 90]
    hysteresis: 5
    gpu_type: nvidia
```

### Auto-splitting thresholds and speeds

If you only specify 2 pairs of `temperatures` and `speeds` (e.g., `[40, 80]` and `[20, 80]`), the system will automatically split them into multiple steps based on the `hysteresis` value.

The splitting logic:

- The range between `temp_min` and `temp_max` will be divided into intervals of `hysteresis * 2`.
- For each interval, a new threshold and corresponding speed will be generated, resulting in smoother fan speed transitions.

**Example:**

```yaml
temperatures: [40, 80]
speeds: [20, 80]
hysteresis: 5
```

This will be automatically expanded to:

```
thresholds: [40.00, 50.00, 60.00, 70.00, 80.00]
speeds: [20, 35, 50, 65, 80]
```

#### Additional Notes

- `temperature_control_mode` (in `general`): Set to `max` to use the highest temperature for fan control, or `avg` to use the average.
- `fan_control_mode` (in each host): Set to `manual` for script-controlled fan speed, or `automatic` to let hardware manage it.
- `gpu_type`: Can be a string or an array, e.g., `nvidia` or `[nvidia, amd]`.
- `ssh_credentials.key_path`: (Optional) Path to SSH private key for authentication.
- VM objects under `vms` also support `gpu_type` as an array.

### Multi-host and VM Support

- Each host can define its own temperature thresholds, fan speeds, and credentials.
- Hosts can include a `vms` list，each VM supports its own SSH credentials and GPU type。
- The script will collect GPU temperatures from both the host and all defined VMs, and use the highest temperature for fan control.

### Temperature Collection & Fan Control Logic

- The script collects CPU and GPU temperatures for each host and its VMs.
- If temperature data is missing or abnormal, the fan will run at the highest configured speed (the last value in `speeds`) for safety.
- The maximum value among all CPU/GPU temperatures (including VMs) is used as the control temperature.
- Fan speed is set according to the configured thresholds and speeds.
- All temperature readings and control actions are recorded in the internal state for monitoring and debugging.

## How it works

Every `interval` seconds, the controller will collect CPU and GPU temperatures from all hosts and their VMs.  
The highest temperature among all CPUs/GPUs (including VMs) is used as the control temperature to determine the fan speed.

- If temperature data is missing or abnormal, the fan will run at the highest configured speed (the last value in `speeds`) for safety.
- Fan speed is set according to the configured thresholds and speeds.
- All temperature readings and control actions are recorded in the internal state for monitoring and debugging.

Fan speed is determined by each temperature threshold and its corresponding speed. The number of thresholds/speeds can be any matching pair count.

| Condition                        | Fan speed                                         |
| -------------------------------- | ------------------------------------------------- |
| _Tmax_ ≤ Threshold1              | Speed1                                            |
| Threshold1 < _Tmax_ ≤ Threshold2 | Speed2                                            |
| ...                              | ...                                               |
| _Tmax_ > ThresholdN              | Highest configured speed (last value in `speeds`) |

If `hysteresis` is set for a given host, the controller will wait for the temperature to go below _ThresholdN - hysteresis_ before lowering the fan speed.  
For example: with a Threshold2 of 37°C and a hysteresis of 3°C, the fans won't slow down from Threshold3 to Threshold2 speed until the temperature reaches 34°C.

## Read-only Web monitoring

The controller includes a small TUI-style dashboard and JSON status endpoint. It shows CPU/GPU temperatures, VM GPU sources, control temperature, fan mode/speed, sensor status, errors, and the last update time.

```yaml
general:
  web_enabled: true
  web_host: 127.0.0.1
  web_port: 8080
```

Open `http://127.0.0.1:8080/` on the controller host. `GET /api/status` returns the same read-only status as JSON. All mutation methods are rejected, and credentials are excluded from the schema.

For remote viewing, keep the loopback binding and use an SSH tunnel:

```bash
ssh -L 8080:127.0.0.1:8080 operator@controller-host
```

Do not expose the built-in server directly to an untrusted network. Put it behind an authenticated TLS reverse proxy if shared access is required.

## Security

This project crosses privileged shell, SSH, IPMI, credential, dependency, and physical-cooling boundaries. Unknown SSH host keys are rejected, IPMI passwords are passed through standard input rather than process arguments, and debug configuration output is redacted. Administrator-configured sensor commands remain trusted shell input and must not be copied from untrusted sources.

Report vulnerabilities through GitHub private vulnerability reporting as described in [SECURITY.md](SECURITY.md). Never include real credentials, private keys, public IP addresses, or identifying hardware data in issues or logs.

Verified and pending hardware reports are tracked in [COMPATIBILITY.md](COMPATIBILITY.md).

## Notes on remote hosts

This controller can monitor the temperature and change the fan speed of remote hosts too: the only caveat is that you'll need to extract the temperatures via an external command. This could be via SSH, for example. The controller expects such a command to return **a semicolon-delimited list of numbers parseable as floats**.

**The included example is a good fit for a remote Proxmox VE host**: it will connect to it via SSH and extract the temperature of all CPU cores, one per line. This way you'll be able to manage that machine just as well as the local one without applying any hardly trackable modification to the base OS.

## Credits

Major thanks go to [NoLooseEnds's directions](https://github.com/NoLooseEnds/Scripts/tree/master/R710-IPMI-TEMP) for the core commands, [sulaweyo's ruby script](https://github.com/sulaweyo/r710-fan-control) for the idea of automating them, and [nmaggioni's r710-fan-controller](https://github.com/nmaggioni/r710-fan-controller) as the main forked project.

**Note:** The key difference of this script, other than handling remote hosts, is that it's based on the temperature of the CPUs' cores and not on the ambient temperature sensor on the server's motherboard.
