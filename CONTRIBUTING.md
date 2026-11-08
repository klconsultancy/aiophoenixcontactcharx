# Contributing

Thanks for your interest. The library is the Modbus/TCP client for Phoenix Contact CHARX SEC controllers and stays free of Home Assistant: the integration lives in [haphoenixcontactcharx](https://github.com/klconsultancy/haphoenixcontactcharx).

## Before you write code

Open an issue first for anything beyond a small fix, so we can agree on the approach before you spend time on it. Read [CONTEXT.md](CONTEXT.md) for the domain terms and [docs/adr/](docs/adr/) for the decisions already made. Report security issues privately as described in [SECURITY.md](SECURITY.md).

## Development

You need [uv](https://docs.astral.sh/uv/); it installs Python 3.12 or later and the locked dev tools.

```sh
uv sync
uv run prek install   # ruff, ruff format and mypy before every commit
uv run pytest
```

CI also runs `uv run ruff format --check`, `uv run ruff check` and `uv run mypy` (strict).

## Pull requests

- Keep a pull request to one change, with tests.
- CI (lint, type check, tests on every supported Python version, a build of the distribution, dependency review and CodeQL) must pass before merging.
- Pull requests are squash-merged, so the pull request title becomes the commit message on `main`. Write it as a [Conventional Commit](https://www.conventionalcommits.org/) with a short imperative description, such as `fix: retry a read after the controller drops the connection`: release-please derives the next version and the changelog from these titles. Use `feat!:` or a `BREAKING CHANGE:` footer for a change that breaks the public API.

By contributing you agree that your contribution is licensed under the [MIT license](LICENSE), and you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
