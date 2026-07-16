# Contributing to Overseer

Thanks for wanting to help! A few ground rules keep the project easy to
maintain.

## Branch model

- **`main` is the protected release branch** — every merge into it rebuilds
  the release zip and ships it to users, so PRs are merged only when they
  are release-ready.
- **Open your PR against `main`**, from a `feature/<topic>` branch in your
  fork. There is no permanent dev branch.

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

The full, binding conventions live in [docs/ai/rules.md](docs/ai/rules.md);
architecture and package guides in [AGENTS.md](AGENTS.md) and
[docs/ai/](docs/ai/).

## Bugs & ideas

Open a [GitHub issue](https://github.com/lukasguziel/overseer/issues) —
please include your Cinema 4D version and, for bugs, the steps to reproduce.
