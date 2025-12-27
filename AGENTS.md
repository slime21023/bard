# Repository Guidelines

## Project Structure & Module Organization
- `README.md` contains the quick start and public examples.
- `pyproject.toml` defines build metadata and dependencies; `uv.lock` pins them.
- `_design.md` captures architecture notes for the ASGI prototype.
- No `src/` or `tests/` directories are committed yet. When adding code, place
  the package under `bard/` (or `src/bard/`) and tests under `tests/`.

## Build, Test, and Development Commands
- Use `uv` to manage the Python environment and lockfile.
- `uv sync` creates/updates the virtual environment from `uv.lock`.
- `uv run python -m pytest` runs tests inside the managed environment.
- `pip install -e .` installs the package in editable mode.
- `pip install -e .[dev]` adds development dependencies (currently `pytest`).
- `python -m pytest` runs the test suite once tests are added.
- The README references `python main.py` for a demo app; keep that entrypoint
  aligned with `README.md` if you add it.

## Coding Style & Naming Conventions
- Use 4-space indentation, `snake_case` for functions/variables, and
  `PascalCase` for classes, with type hints throughout.
- Prefer `typing.Annotated` for request extractors (see `README.md` examples).
- No formatter or linter is configured; document any new tool in
  `pyproject.toml` and update this guide.

## Testing Guidelines
- Use `pytest` and keep tests small and behavior-focused.
- Suggested naming: `tests/test_*.py` and `test_*` functions.
- Exercise the ASGI lifecycle with `TestClient` when possible.

## Commit & Pull Request Guidelines
- No commit history exists yet, so no convention is established.
- Recommended: short, imperative commit subjects (for example, "Add router
  extractor"); use Conventional Commits only if the team agrees.
- PRs should explain intent, list notable API changes, and include runnable
  snippets or tests when behavior changes.

## Architecture & References
- This is an early ASGI framework prototype; use `_design.md` for design
  context and `README.md` for public-facing examples.
