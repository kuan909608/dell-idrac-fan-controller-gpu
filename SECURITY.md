# Security policy

## Supported versions

Security fixes are applied to the latest published release and the default branch. Until the first release is published, only the default branch is supported.

## Reporting a vulnerability

Do not open a public issue for a vulnerability. Use GitHub's private vulnerability reporting for this repository. Include the affected revision, deployment topology, threat scenario, reproduction steps, and whether credentials or physical cooling may be affected.

Remove real IP addresses, passwords, private keys, host keys, hardware serial numbers, service tags, and other identifying data from reports and logs. If private reporting is unavailable, contact the maintainer through the address shown on their GitHub profile without including exploit details in the first message.

## Privilege and credential boundaries

The controller can run as root, execute administrator-configured sensor commands through a local shell, connect over SSH, handle IPMI and SSH credentials, and issue raw IPMI commands that change physical fan behavior.

- Treat the YAML configuration and installation directory as privileged. Use restrictive ownership and mode `0600` for the active configuration.
- Prefer a dedicated, least-privileged iDRAC account if the required raw fan commands can be granted safely in your environment.
- Prefer restricted SSH keys over passwords. The client loads system `known_hosts` and rejects unknown host keys; provision and verify those keys out of band.
- IPMI passwords are passed to `ipmitool` through standard input rather than command arguments. They still exist in process memory and the configuration file.
- Sensor command strings intentionally use a shell so pipelines work. They are trusted code: anyone who can alter them can execute commands with the service's privileges.
- The systemd hardening settings reduce exposure but do not turn root-controlled IPMI and shell execution into an unprivileged operation.

## Web monitoring boundary

The monitoring service is read-only and binds to `127.0.0.1` by default. It has no authentication or TLS and is not an authorization boundary. Keep it on loopback, use an SSH tunnel, or place it behind an authenticated TLS reverse proxy. Do not expose it directly to an untrusted network.

## Thermal fail-safe and recovery limits

Missing CPU data or any failed configured GPU source causes the control policy to select a sentinel above every valid threshold. The fan curve then uses its last configured speed. This is only as conservative as the operator's final speed value and cannot guarantee safe cooling.

On normal shutdown, `SIGTERM`, and accepted configuration reload, the process makes a best-effort attempt to return each configured manual host to Dell automatic fan mode. It attempts every host even if one fails. Recovery is not guaranteed:

- `SIGKILL`, power loss, interpreter/runtime failure, or host crash may bypass cleanup;
- network, SSH, credential, `ipmitool`, or iDRAC failures may prevent the recovery command;
- iDRAC firmware behavior and raw command support differ across hardware;
- the dashboard reports process state and the last successful command, not an independent physical verification of fan RPM or iDRAC mode.

Before unattended use, test missing sensors, sustained peak load, graceful stop, controller reboot, network loss, and iDRAC recovery on the exact hardware. Keep iDRAC access and independent thermal alerting available. Never rely on this software as the only hardware-protection mechanism.
