# Draft release notes: v1.0.0

> Maintainer review draft. No Git tag or GitHub Release has been created.

`v1.0.0` is proposed as the first formal release of Dell iDRAC Fan Controller with GPU Support. It establishes a documented, tested baseline for operators who need CPU and accelerator temperatures to drive Dell PowerEdge fan curves in Proxmox VE, homelab, AI server, and other GPU workload environments.

## Highlights

- Collect CPU temperatures plus NVIDIA and AMD GPU temperatures from hosts and SSH-accessible VMs.
- Manage multiple hosts with independent fan curves, credentials, modes, and VM temperature sources.
- Choose maximum or average control policy, with the exact aggregation semantics documented in `ARCHITECTURE.md`.
- Enter a conservative configured fan-curve state when required CPU or configured GPU sensor data is unavailable.
- Send structured local or SSH-executed `ipmitool` commands to Dell iDRAC.
- Deploy as a hardened systemd service or a remote-oriented Docker Compose service.
- Monitor runtime state through a loopback-by-default, read-only dashboard and JSON API.
- Reload fully validated configuration and Web settings without restarting the process.
- Attempt Dell automatic fan-mode recovery on graceful shutdown, `SIGTERM`, and configuration replacement.

## Safety and compatibility

This release does not guarantee hardware safety or broad Dell compatibility. Raw command support and firmware behavior vary. The recorded R730 evidence includes a partial maintainer Docker test with local IPMI, non-debug control, and graceful automatic-mode restoration, but it omits other required environment and fail-safe details. No Dell/iDRAC combination is therefore marked Verified for this release candidate.

Fail-safe selects the highest **configured** curve speed; it is not an unconditional 100% command. Automatic-mode recovery is best-effort and can fail or be bypassed by abrupt termination, power loss, bad credentials, network failure, or an unavailable iDRAC. Read `SECURITY.md` and `COMPATIBILITY.md`, test on the exact deployment, and keep independent monitoring and out-of-band access.

## Deployment notes

- Python 3.11 and 3.13 are exercised by CI.
- The Docker image is designed for remote management and does not bundle host GPU tooling.
- Runtime configuration reload requires mounting the configuration directory, not a single file, in Docker.
- The monitoring service has no authentication or TLS and should remain loopback-only or behind a suitable proxy.
- Do not run more than one controller against the same server.

## Upgrade notes

This is the first formal release, so there is no versioned upgrade path. Existing untagged deployments should back up `fan_control_config.yaml`, compare it with the current example, run the documented tests, and validate graceful automatic-mode recovery before replacing a running installation.

## Known limitations

- No complete physical hardware combination currently meets the project's Verified evidence level.
- Hysteresis is implemented as a threshold-centered tolerance band, not a stateful delayed-downshift controller.
- Runtime state records the last successful command and sensor observations; it does not independently query physical fan RPM or confirm iDRAC mode.
- Docker local CPU/GPU sensing is not packaged by the included image.
