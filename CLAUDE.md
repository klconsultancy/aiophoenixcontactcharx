## Agent skills

### Issue tracker

Issues live in GitHub Issues for klconsultancy/aiophoenixcontactcharx. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the default five-role label vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo — one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Pull requests and releases

PRs are squash-merged and the PR title becomes the commit on `main`, so the title must be a Conventional Commit (`fix:`, `feat:`, `feat!:` for a breaking API change, `docs:`, `ci:`, `build:`, `chore:`). release-please builds the next version and `CHANGELOG.md` from those titles and keeps a release PR open; merging that PR tags the release and publishes to PyPI. Don't bump `version` in `pyproject.toml` or `__version__` by hand. Renovate handles dependency updates; there is no Dependabot.

## Tooling

uv manages the environment (`uv sync`, `uv run pytest`); `uv.lock` is committed. The package is in `src/aiophoenixcontactcharx/`. ruff runs with `select = ["ALL"]` and mypy in strict mode. Coverage must stay at 100 % (`fail_under`).

## Design

[`docs/design.md`](docs/design.md) describes the 2.0 register map, encoding, reads and public API; keep it current when a choice changes. [`docs/errata.md`](docs/errata.md) records where the manual (transcribed in `docs/protocol/B3-modbus.md`) is wrong or unclear, and how the map reads it. `tests/test_register_map.py` checks the map against that transcription in both directions.
