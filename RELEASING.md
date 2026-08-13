# Release process

Releases follow Semantic Versioning and are created only by a maintainer after review. A release must not claim hardware compatibility beyond the evidence in `COMPATIBILITY.md`.

## Version selection

- **MAJOR**: incompatible configuration, deployment, monitoring schema, or control-policy change.
- **MINOR**: backward-compatible capability or meaningful new sensor/deployment support.
- **PATCH**: backward-compatible bug, security, packaging, or documentation correction.

The project has a stable 1.x baseline. Future incompatible changes require a major version.

## Maintainer checklist

1. Choose the target commit and version; ensure the working tree is clean.
2. Review every `Unreleased` changelog entry and move it under `## [X.Y.Z] - YYYY-MM-DD`.
3. Copy and update `RELEASE_NOTES.md` for the target version. Remove the draft notice and all unsupported claims.
4. Confirm `README.md` and `README.zh-TW.md` describe the same user-visible behavior.
5. Review `COMPATIBILITY.md`; require physical evidence before using Verified.
6. Run:

   ```bash
   python3 -m unittest discover -s tests -v
   python3 -m compileall -q .
   python3 -m ruff check .
   bash -n install.sh install-online.sh uninstall.sh uninstall-online.sh
   docker compose config
   ```

7. Confirm CI and dependency review pass on the release commit.
8. Exercise a staging deployment: configuration reload, missing CPU sensor, missing configured GPU sensor, graceful stop, and automatic-mode recovery.
9. If claiming Verified compatibility, repeat the required sustained-load checks on each exact hardware combination and record sanitized evidence.
10. Review dependencies, private vulnerability reports, credentials in Git history/diff, Markdown links, and Mermaid rendering.
11. Obtain maintainer approval of the final changelog and release notes.
12. Only then create a signed or annotated `vX.Y.Z` tag, push it, and create the GitHub Release from the reviewed notes.

Tagging and publishing are intentionally outside documentation-preparation pull requests. If any check fails, fix it on the branch and repeat the checklist rather than moving the tag.

## Dependency updates

Dependabot checks runtime Python packages, GitHub Actions, and the Docker base image weekly. Runtime packages stay exactly pinned in `requirements.txt`; development-only checks stay exactly pinned in `requirements-dev.txt`. Review one update at a time, run the complete checklist above, and record user-visible runtime changes in `CHANGELOG.md`. Never merge a dependency update solely because its version is newer.

## Post-release

- Verify the release page, source archives, badges, and changelog links.
- Open a fresh `Unreleased` section if it was removed during preparation.
- Monitor security and hardware reports without promoting Community Reported results automatically.
