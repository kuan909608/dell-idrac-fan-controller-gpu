# v1.1.0

`v1.1.0` adds version-pinned one-command installation and safe uninstallation for direct systemd deployments.

## Highlights

- Install directly on a Proxmox VE or Debian host with one HTTPS bootstrap command.
- Pin each bootstrap and its downloaded source archive to the same formal release tag.
- Delegate package, Python environment, configuration, and systemd setup to the existing repository installer.
- Preserve an existing `/opt/fan_control/fan_control_config.yaml` during reinstalls.
- Remove the temporary source archive when installation finishes or fails.
- Stop the controller before uninstallation so its normal automatic-mode recovery path can run.
- Refuse to delete an installation directory unless it contains the marker created by the installer.
- Remove the systemd unit and installation directory while leaving shared operating-system packages installed.

## Safety and compatibility

The online installer runs the existing systemd installer as root. It installs operating-system and pinned Python dependencies, deploys a systemd unit, preserves an existing configuration, and restarts the service. Review the bootstrap and source tag before running the command.

This release does not establish hardware compatibility. A community reporter confirmed that `v1.1.0-rc.2` resolves the obsolete `libsensors4-dev` installation failure on Debian 13 with Proxmox VE 9.

Maintainer staging on 2026-08-13 exercised the RC3 candidate on Proxmox VE 9.2.5 with kernel 7.0.14-6-pve. The version-pinned online install, service startup, validated configuration reload, missing-CPU and configured-GPU fail-safe selection, graceful dry-run recovery, stop-failure removal guard, and online uninstall cleanup all succeeded. The final release changes only release-version metadata from that candidate. All IPMI changes remained in debug dry-run mode; no real fan command or sustained-load hardware validation was performed.

## Installation

```bash
bash -c "$(curl --proto '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/kuan909608/dell-idrac-fan-controller-gpu/v1.1.0/install-online.sh)"
```

The example configuration defaults to IPMI dry-run mode. Inspect and validate the installed configuration before enabling manual fan control.

## Uninstallation

```bash
bash -c "$(curl --proto '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/kuan909608/dell-idrac-fan-controller-gpu/v1.1.0/uninstall-online.sh)"
```

The uninstaller is intentionally limited to systemd deployments carrying the installer's ownership marker. It does not remove shared operating-system packages.

## Known limitations

- The bootstrap requires `curl`, `tar`, and outbound HTTPS access before it can invoke the repository installer.
- GitHub release tags are treated as immutable by project policy, but the installer does not independently verify an archive checksum.
- The monitoring service has no authentication or TLS and remains loopback-only by default.
- No complete physical hardware combination currently meets the project's Verified evidence level.
