# Changelog

All notable user-facing changes to this project are documented here. The project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and will use [Semantic Versioning](https://semver.org/spec/v2.0.0.html) beginning with its first formal release.

## [Unreleased]

## [1.1.0-rc.3] - 2026-08-13

### Added

- Version-pinned one-command systemd uninstallation that stops the controller for automatic-mode recovery before removing its service unit and installation directory.

### Changed

- Mark systemd-owned installation directories so the uninstaller refuses to remove unrelated directories under `/opt`.
- Update the prerelease install bootstrap and documentation to `v1.1.0-rc.3` for paired installation and uninstallation staging.

## [1.1.0-rc.2] - 2026-08-12

### Changed

- Clean up the online installer's temporary source archive after installation completes.

## [1.1.0-rc.1] - 2026-08-12

### Added

- One-command host installation through a small HTTPS bootstrap that downloads a selected repository ref and delegates to the existing systemd installer.

## [1.0.0] - 2026-08-12

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
- Restricted custom root-owned installation targets to dedicated directories directly under `/opt`.
- Added Docker image build and startup-import smoke testing to CI.

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
