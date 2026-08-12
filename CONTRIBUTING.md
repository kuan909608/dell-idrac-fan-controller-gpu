# Contributing

Contributions are welcome for documentation, tests, deployment support, hardware reports, and focused controller improvements. Because this project controls physical cooling, changes must be reviewable, evidence-based, and scoped narrowly.

## Before opening a change

- Search existing issues and open the appropriate Bug Report, Feature Request, or Hardware Compatibility Report.
- For behavior changes, describe the current behavior, proposed behavior, failure mode, and recovery behavior.
- Remove credentials, public addresses, hostnames, service tags, serial numbers, private key paths, and other identifying data.
- Do not generalize compatibility beyond the exact model, iDRAC firmware, OS, GPU, and deployment tested.

Small documentation corrections may be submitted directly. Security vulnerabilities must follow [SECURITY.md](SECURITY.md), not a public issue.

## Development setup and checks

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q .
.venv/bin/python -m ruff check .
bash -n install.sh
```

CI runs the same Python checks on 3.11 and 3.13. If deployment files change, also validate the relevant environment where available:

```bash
docker compose config
systemd-analyze verify fan-control.service
```

The systemd template contains `{TARGETDIR}` until installed, so `systemd-analyze` may report that placeholder; the installer replaces it with the selected path.

## Pull requests

- Keep each PR focused and link the originating issue where one exists.
- Update both `README.md` and `README.zh-TW.md` when their shared user-facing behavior changes.
- Update `CHANGELOG.md` under **Unreleased** for user-visible changes.
- Add regression tests for changes to aggregation, fan curves, sensor failures, shutdown recovery, configuration/reload, command handling, packaging, or the monitoring API.
- Complete the physical-safety section in the pull request template and report only hardware actually tested.
- Do not combine a documentation or feature change with unrelated core refactoring.

## Safety and security requirements

- Never place passwords or private keys in fixtures, logs, screenshots, process arguments, issue reports, or commits.
- Treat shell, SSH, IPMI, root installation, dependencies, Web exposure, and fan-control changes as security-sensitive.
- Keep the built-in Web API read-only. A remote mutation API requires a separate threat model and explicit design review.
- Preserve best-effort automatic-mode recovery and fail-safe coverage unless the PR explicitly proposes, documents, and tests a replacement.
- State whether tests used debug/dry-run mode, mocks, or physical hardware. Software-only tests are not hardware verification.

## Versioning and releases

The project uses [Semantic Versioning](https://semver.org/). Maintainers prepare releases using [RELEASING.md](RELEASING.md); contributors must not create repository tags as part of a PR.

By contributing, you agree that your contribution is licensed under the repository's [MIT License](LICENSE).
