# Contributing to Overseer

Thanks for wanting to help! A few ground rules keep the project easy to
maintain.

## Branch model

- **`main` is the protected release branch.** Every merge into it rebuilds
  the release zip and ships it to users — pull requests never target `main`.
- **Target `dev` with your PR**, from a `feature/<topic>` branch in your
  fork. The maintainer merges `dev` into `main` when a release is cut.

## Before you open a PR

All CI gates must be green locally:

```bash
python -m pytest                 # unit tests (run without Cinema 4D)
python -m ruff check src tests   # lint
cd frontend && pnpm test         # frontend unit tests
cd frontend && pnpm run build    # typecheck + build
```

## Code rules (the short version)

- **English everywhere** — code, comments, commit messages, UI copy.
- Pure logic lives in `src/overseer/` and must **not import `c4d`**; only
  `src/overseer/cinema/` and `src/overseer/bridge/` may. New pure logic
  needs a test in `tests/`.
- Source files carry no docstrings or explanatory comments — prose lives in
  `docs/`, one file per module.
- Commit messages are clean and imperative, without attribution trailers.

The full, binding conventions live in [.claude/rules.md](.claude/rules.md);
architecture and package guides in [CLAUDE.md](CLAUDE.md) and
[docs/claude/](docs/claude/).

## Bugs & ideas

Open a [GitHub issue](https://github.com/lukasguziel/overseer/issues) —
please include your Cinema 4D version and, for bugs, the steps to reproduce.
