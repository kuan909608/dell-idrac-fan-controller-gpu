# Contributing

Contributions should begin with a GitHub issue describing the hardware, iDRAC generation and firmware, operating system, GPU type, deployment mode, observed behavior, and expected fail-safe behavior. Remove all credentials and identifying data.

## Development checks

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q .
bash -n install.sh
```

## Safety requirements

- Do not place passwords or private keys in fixtures, logs, process arguments, screenshots, or issue reports.
- Treat shell, SSH, IPMI, install scripts, dependencies, and fan-control changes as security-sensitive.
- Add a regression test for changes to temperature aggregation, fan curves, sensor failures, shutdown behavior, configuration, or the monitoring API.
- Keep the Web API read-only. Proposals for remote fan control require a separate threat model and will not be accepted as incidental dashboard changes.
- State exactly which hardware was tested. Do not generalize compatibility from one Dell model or firmware revision.
