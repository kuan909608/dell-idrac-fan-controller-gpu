# Changelog

All notable user-facing changes to this project are documented here. The project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and will use [Semantic Versioning](https://semver.org/spec/v2.0.0.html) beginning with its first formal release.

## [Unreleased]

### Added

- Draft release notes and a maintainer release checklist for the proposed `v1.0.0` release.
- Evidence-based compatibility matrix with Verified, Community Reported, Expected, and Unknown levels.
- Architecture documentation derived from the current sensor, policy, fan-curve, IPMI, reload, monitoring, and recovery code paths.
- Feature Request issue form and expanded hardware compatibility reporting fields.
- CI-discovered documentation integrity tests for local links, bilingual capability coverage, architecture labels, and Issue Form structure.
- Clean-install startup import coverage plus rendered systemd unit verification in CI.
- Ruff static analysis with a pinned development dependency.

### Changed

- Made the example configuration default to IPMI dry-run mode for safer first-run validation; existing installed configurations remain unchanged.
- Repositioned the project around Dell PowerEdge, Proxmox VE, GPU workloads, homelabs, and local AI servers without claiming unverified hardware support.
- Documented the fork's relationship to `nmaggioni/r710-fan-controller` and retained upstream credits and MIT attribution.
- Aligned English and Traditional Chinese documentation with actual `max`/`avg`, hysteresis, Docker, fail-safe, Web monitoring, and automatic-mode recovery behavior.
- Expanded contribution and security guidance for physical cooling, credentials, root privileges, and release evidence.
- Made the systemd installer independent of the caller's working directory and installed the actual runtime `lm-sensors` package.
- Recorded a successful clean Rocky Linux 9.6 systemd install/startup test performed with dry-run configuration and an IPMI-blocking safety shim.

## Historical development before formal versioning

The Git history begins in 2019 and has no tags. Important capabilities accumulated before the first formal release include:

- CPU-core-based Dell IPMI fan control, threshold curves, and per-host hysteresis;
- remote and multi-host operation, systemd installation, shutdown recovery, and Docker support;
- host and VM NVIDIA/AMD GPU monitoring with configurable maximum or average policy;
- two-point fan-curve expansion;
- missing-sensor fail-safe policy and best-effort Dell automatic-mode recovery;
- read-only Web dashboard and JSON status endpoint;
- secure command construction, SSH host-key verification, credential redaction, and systemd hardening;
- validated runtime configuration reload and live Web-setting reload;
- Docker Compose deployment, CI, dependency review, and unit/security/packaging tests.

Because those changes were never published as versioned releases, they are summarized rather than assigned invented version numbers or dates.
