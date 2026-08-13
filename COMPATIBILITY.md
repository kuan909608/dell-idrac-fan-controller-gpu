# Compatibility matrix

Compatibility is tracked by evidence, not by similarity between Dell models. A passing unit test, successful container build, or matching iDRAC generation does not prove that raw fan commands are safe or supported on physical hardware.

## Evidence levels

| Status | Meaning |
| --- | --- |
| **Verified** | Maintainers have complete, release-specific physical-hardware evidence covering fan commands, sensors, sustained load, fail-safe, and automatic-mode recovery. |
| **Community Reported** | A user reported a physical deployment, but maintainers have not reproduced it or some required details are missing. |
| **Expected** | The software path is implemented and is reasonably expected to work, but the complete physical combination has not been verified. |
| **Unknown** | There is insufficient evidence to make a compatibility statement. |

## Dell PowerEdge and iDRAC

| Dell model | iDRAC generation / firmware | Status | Evidence and limits |
| --- | --- | --- | --- |
| PowerEdge R730 | Not recorded | **Community Reported** | A maintainer reported a 2026-08-12 Docker test with local IPMI, non-debug control, and graceful automatic-mode restoration. Exact firmware, OS, GPU, sustained-load observations, and missing-sensor fail-safe evidence were not recorded, so this is not Verified. |
| Other PowerEdge models | Any | **Unknown** | No evidence is recorded in this repository. Similar raw IPMI behavior must not be assumed. |

There are currently **no Verified Dell/iDRAC combinations** for a formal release.

## Operating system and deployment paths

These statuses describe software support only; they do not upgrade any hardware combination to Verified.

| Component | Status | Evidence and limits |
| --- | --- | --- |
| Linux, Python 3.11 | **Expected** | Unit, compile, packaging, and security tests run in CI; no release-specific physical-hardware record. |
| Linux, Python 3.13 | **Expected** | Unit, compile, packaging, and security tests run in CI; no release-specific physical-hardware record. |
| systemd installation | **Expected** | A clean install and service startup were verified on Rocky Linux 9.6 on 2026-08-12 using the exact PR commit, an isolated target directory, dry-run configuration, and an `ipmitool` blocking shim. A community reporter confirmed on 2026-08-13 that `v1.1.0-rc.2` installs past the obsolete `libsensors4-dev` failure on Debian 13 with Proxmox VE 9; no hardware, runtime-control, recovery, or sustained-load evidence was supplied. Live IPMI control was intentionally not exercised by the maintainer systemd test. |
| Docker Compose, remote management | **Expected** | Compose mounts and lifecycle are covered by repository tests. The image is designed for remote sensors/IPMI and is not a local GPU runtime image. |
| Proxmox VE host or VM monitoring over SSH | **Expected** | Generic SSH sensor execution and VM GPU aggregation are implemented; no complete Proxmox/hardware report is recorded. |
| Other operating systems or orchestrators | **Unknown** | No supported deployment instructions or evidence are recorded. |

## Sensors and GPUs

| Source | Status | Evidence and limits |
| --- | --- | --- |
| CPU via administrator-configured `sensors` command | **Expected** | Parsing and fail-safe behavior are tested with mocked output; actual sensor labels vary by platform. |
| NVIDIA GPU via `nvidia-smi` | **Expected** | Host and VM command paths are implemented; no specific GPU/driver combination is release-verified. |
| AMD GPU via `rocm-smi` | **Expected** | Host and VM command paths are implemented; no specific GPU/driver combination is release-verified. |
| Mixed NVIDIA and AMD sources | **Expected** | Aggregation is implemented; complete physical evidence is not recorded. |
| Other accelerators or sensor tools | **Unknown** | They may be usable with custom commands, but are not explicitly supported or evidenced. |

## Submit a compatibility report

Open a [Hardware Compatibility Report](https://github.com/kuan909608/dell-idrac-fan-controller-gpu/issues/new?template=hardware_compatibility.yml) and remove service tags, serial numbers, public addresses, credentials, hostnames, and other identifying data.

To qualify for Verified review, include:

- exact Dell model;
- iDRAC generation and firmware version;
- operating system and version, plus Python version;
- GPU vendor/model and driver/tool version, or state that no GPU is installed;
- systemd, Docker, or other deployment method;
- local/remote sensor and IPMI execution topology;
- manual fan command and curve observations;
- missing-CPU and configured-GPU sensor fail-safe results;
- normal shutdown and controller-host restart recovery results;
- sustained-load temperature and fan observations.

A maintainer may classify a complete report as Community Reported first. Verified remains a release decision and may require independent reproduction.
