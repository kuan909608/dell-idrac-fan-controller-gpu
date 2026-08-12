# v1.1.0-rc.2

`v1.1.0-rc.2` is the second prerelease of the version-pinned one-command installer for Dell iDRAC Fan Controller with GPU Support. It supersedes `v1.1.0-rc.1` by ensuring that downloaded source archives are removed after installation.

## Highlights

- Install directly on a Proxmox VE or Debian host with one HTTPS bootstrap command.
- Pin both the bootstrap and downloaded source archive to the same prerelease tag.
- Delegate package, Python environment, configuration, and systemd setup to the existing repository installer.
- Preserve an existing `/opt/fan_control/fan_control_config.yaml` during reinstalls.
- Remove the temporary source archive when installation finishes or fails.

## Safety and compatibility

The online installer runs the existing systemd installer as root. It installs operating-system and pinned Python dependencies, deploys a systemd unit, preserves an existing configuration, and restarts the service. Review the bootstrap and source tag before running the command.

This prerelease does not establish hardware compatibility. The published installer was exercised end to end in a disposable Debian 13 container with systemd operations replaced by a no-op. It has not yet been installed on a physical PVE host as part of this release process.

## Installation

```bash
bash -c "$(curl --proto '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/kuan909608/dell-idrac-fan-controller-gpu/v1.1.0-rc.2/install-online.sh)"
```

The example configuration defaults to IPMI dry-run mode. Inspect and validate the installed configuration before enabling manual fan control.

## Known limitations

- The bootstrap requires `curl`, `tar`, and outbound HTTPS access before it can invoke the repository installer.
- GitHub release tags are treated as immutable by project policy, but the installer does not independently verify an archive checksum.
- The monitoring service has no authentication or TLS and remains loopback-only by default.
- No complete physical hardware combination currently meets the project's Verified evidence level.
