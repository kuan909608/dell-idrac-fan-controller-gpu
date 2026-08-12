from typing import Callable, Iterable, List, Optional


def restore_automatic_control(
    controller,
    hosts: Iterable[dict],
    logger: Optional[Callable] = None,
) -> List[str]:
    """Best-effort restoration for every host configured for manual control."""
    failures = []
    for host in hosts:
        if host.get("fan_control_mode") != "manual":
            continue
        host_name = host.get("name", "unknown")
        try:
            restored = controller.set_fan_control("automatic", host)
            if restored is False:
                failures.append(host_name)
        except Exception as exc:
            failures.append(host_name)
            if logger:
                logger("ERROR", host_name, f"Failed to restore automatic fan control: {exc}")
    return failures
