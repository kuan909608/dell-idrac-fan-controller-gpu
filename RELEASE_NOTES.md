# v1.1.0-rc.3

`v1.1.0-rc.3` adds a version-pinned one-command uninstaller for staging the complete systemd deployment lifecycle before `v1.1.0`.

## Highlights

- Install directly on a Proxmox VE or Debian host with one HTTPS bootstrap command.
- Pin both the bootstrap and downloaded source archive to the same prerelease tag.
- Delegate package, Python environment, configuration, and systemd setup to the existing repository installer.
- Preserve an existing `/opt/fan_control/fan_control_config.yaml` during reinstalls.
- Remove the temporary source archive when installation finishes or fails.
- Stop the controller before uninstallation so its normal automatic-mode recovery path can run.
- Refuse to delete an installation directory unless it contains the marker created by the RC3 installer.
- Remove the systemd unit and installation directory while leaving shared operating-system packages installed.

## Safety and compatibility

The online installer runs the existing systemd installer as root. It installs operating-system and pinned Python dependencies, deploys a systemd unit, preserves an existing configuration, and restarts the service. Review the bootstrap and source tag before running the command.

This prerelease does not establish hardware compatibility. A community reporter confirmed that `v1.1.0-rc.2` resolves the obsolete `libsensors4-dev` installation failure on Debian 13 with Proxmox VE 9. RC3 still requires a maintainer staging test of installation, dry-run operation, graceful stop, and uninstallation before the final release.

## Installation

```bash
bash -c "$(curl --proto '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/kuan909608/dell-idrac-fan-controller-gpu/v1.1.0-rc.3/install-online.sh)"
```

The example configuration defaults to IPMI dry-run mode. Inspect and validate the installed configuration before enabling manual fan control.

## Uninstallation

```bash
bash -c "$(curl --proto '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/kuan909608/dell-idrac-fan-controller-gpu/v1.1.0-rc.3/uninstall-online.sh)"
```

The uninstaller is intentionally limited to systemd deployments created by RC3 or later. It does not remove shared operating-system packages.

## Known limitations

- The bootstrap requires `curl`, `tar`, and outbound HTTPS access before it can invoke the repository installer.
- GitHub release tags are treated as immutable by project policy, but the installer does not independently verify an archive checksum.
- The monitoring service has no authentication or TLS and remains loopback-only by default.
- No complete physical hardware combination currently meets the project's Verified evidence level.
