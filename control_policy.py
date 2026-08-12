from dataclasses import dataclass
from typing import Optional, Sequence


FAIL_SAFE_TEMPERATURE = 999.0


@dataclass(frozen=True)
class SensorSnapshot:
    cpu_temps: Optional[Sequence[float]]
    gpu_temps: Optional[Sequence[float]]


@dataclass(frozen=True)
class ControlDecision:
    control_temperature: float
    fail_safe: bool
    cpu_avg: Optional[float]
    cpu_max: Optional[float]
    gpu_avg: Optional[float]
    gpu_max: Optional[float]
    combined_avg: Optional[float]
    combined_max: Optional[float]


def _average(values: Sequence[float]) -> float:
    return round(sum(values) / len(values), 2)


def determine_control_temperature(snapshot: SensorSnapshot, mode: str) -> ControlDecision:
    """Return the temperature used by fan control without performing any I/O.

    CPU sensor loss is treated as unsafe because every configured host is
    expected to provide CPU temperature data. GPU data remains optional.
    """
    if not snapshot.cpu_temps:
        return ControlDecision(
            control_temperature=FAIL_SAFE_TEMPERATURE,
            fail_safe=True,
            cpu_avg=None,
            cpu_max=None,
            gpu_avg=None,
            gpu_max=None,
            combined_avg=None,
            combined_max=None,
        )

    cpu_temps = [float(value) for value in snapshot.cpu_temps]
    gpu_temps = [float(value) for value in (snapshot.gpu_temps or [])]
    cpu_avg = _average(cpu_temps)
    cpu_max = round(max(cpu_temps), 2)
    gpu_avg = _average(gpu_temps) if gpu_temps else None
    gpu_max = round(max(gpu_temps), 2) if gpu_temps else None

    # Preserve the existing policy: represent the host CPUs by their hottest
    # core, then combine that value with each GPU temperature.
    combined_temps = [cpu_max, *gpu_temps]
    combined_avg = _average(combined_temps)
    combined_max = round(max(combined_temps), 2)
    control_temperature = combined_avg if mode == "avg" else combined_max

    return ControlDecision(
        control_temperature=control_temperature,
        fail_safe=False,
        cpu_avg=cpu_avg,
        cpu_max=cpu_max,
        gpu_avg=gpu_avg,
        gpu_max=gpu_max,
        combined_avg=combined_avg,
        combined_max=combined_max,
    )
