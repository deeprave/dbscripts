# Agent Notes

Read `project.md` first for project context, Python compatibility, and CI expectations.

## Tooling

Use `uv` for dependency management: `uv sync`.

Use `pre-commit` for the full local quality gate. The configured hooks include
Ruff lint/fix, Ruff format, OSV vulnerability checks, metadata checks, and
pytest.

## Checks

| Purpose | Command | Notes |
| --- | --- | --- |
| Full local gate | `pre-commit run --all-files` | Includes Ruff, Ruff format, OSV check, file hygiene, and pytest. |
| Lint | `uv run ruff check dbscripts tests` | Use `--fix` when making lint-only repairs. |
| Format | `uv run ruff format dbscripts tests` | Mirrors the `ruff-format` pre-commit hook. |
| Tests | `uv run pytest` | Requires Docker because tests use `testcontainers`. |
| Dependencies | `uv sync` | Refresh after dependency or lockfile changes. |

## Style

Ruff configuration lives in `ruff.toml` and `pyproject.toml`.

Line length is 120, quote style is double quotes, and indentation is 4 spaces.

`ruff.toml` currently sets `target-version = "py310"` while
`pyproject.toml` sets `requires-python = ">= 3.11"`. Treat Python 3.11 as the
actual compatibility target unless that mismatch is intentionally changed.
