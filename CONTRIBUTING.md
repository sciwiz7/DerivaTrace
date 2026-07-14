# Contributing to DerivaTrace

Thank you for your interest in DerivaTrace. This document describes how to
contribute to the project during its early, pre-alpha stage.

## Code of conduct

All contributors are expected to follow the
[Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold
its standards.

## Project stage

DerivaTrace is at **Stage 0** and is **pre-alpha**. The current focus is the
foundation and specification. Contributions that introduce pricing, Greeks,
Monte Carlo, PDEs, calibration, or hedging functionality are **out of scope**
for Stage 0 and should be discussed in an issue first.

## Development setup

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Workflow

1. Open or claim an issue describing the change.
2. Discuss architectural changes in an Architectural Decision Record (ADR)
   under `docs/adr/` when appropriate.
3. Create a branch from `main` and make focused changes.
4. Ensure the following pass locally:
   - `ruff format --check .`
   - `ruff check .`
   - `mypy`
   - `pytest --cov=derivatrace --cov-branch --cov-fail-under=100`
   - `python -m build`
5. Open a pull request describing the intent, scope, and acceptance criteria.

## Design principles

- **Separation of concerns:** contract semantics, market data, model,
  numerical engine, risk, validation, and evidence certificate are distinct.
- **Determinism:** identical inputs must produce identical, reproducible
  outputs within the declared policy.
- **Immutability and typing:** prefer frozen, typed, explicit structures.
- **No hidden intelligence:** the deterministic core is authoritative; assistive
  tooling must not silently alter contracts, models, inputs, engines, or
  validation outcomes.
- **Evidence by default:** a result without evidence is incomplete.
- **Security by default:** treat external inputs as untrusted.

## Documentation

Keep documentation links valid. Every Markdown link to a local file must
resolve. Avoid absolute local filesystem paths. Do not claim capabilities that
do not yet exist, and do not claim formal verification or "first ever" status.

## Security

If you discover a security issue, please follow the
[Security policy](SECURITY.md). Do not open public issues for vulnerabilities.

## Licence

By contributing, you agree that your contributions will be licensed under the
[MIT licence](LICENSE).
