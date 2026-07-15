# Contributing to DerivaTrace

Thank you for your interest in DerivaTrace. This document describes how to
contribute to the project during its early, pre-alpha stage.

## Code of conduct

All contributors are expected to follow the
[Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold
its standards.

## Project stage

DerivaTrace is at **Stage 1A** and is **pre-alpha** (not yet published). Stage 1A
implements the contract semantics and validation bounded contexts as the typed,
immutable `derivatrace.contracts` module. Contributions that introduce pricing,
Greeks, Monte Carlo, PDEs, calibration, hedging, canonicalization, hashing, or
engine functionality are **out of scope** for Stage 1A and should be discussed
in an issue first (they belong to later stages).

## Development setup

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Workflow

1. Open or claim an issue describing the change.
2. Discuss architectural changes in an Architectural Decision Record (ADR)
   under `docs/adr/` when appropriate. Changes to the contract algebra or its
   runtime type system must respect [ADR 0006](docs/adr/0006-stage-1-contract-algebra-and-runtime-type-system.md)
   and the public API documented in [contract-api.md](docs/contract-api.md).
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
- **Immutability and typing:** contract values and nodes are frozen, slotted,
  explicitly typed structures; mutation after construction (including via
  `object.__setattr__` forgery) is rejected or re-checked by validation.
- **Exact numbers:** contract quantities use `Decimal`-backed `ExactNumber`;
  `float`, `bool`, `NaN`, and `Infinity` are never accepted.
- **Supported-node policy:** only the exact set of implemented concrete node
  types is accepted; third-party subclasses of the abstract bases are rejected.
- **No hidden intelligence:** the deterministic core is authoritative; assistive
  tooling must not silently alter contracts, models, inputs, engines, or
  validation outcomes.
- **Evidence by default:** a result without evidence is incomplete. Stage 1A
  provides structural and semantic validation, not an evidence certificate.
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
