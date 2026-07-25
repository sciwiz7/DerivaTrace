# Contributing to DerivaTrace

Thank you for your interest in DerivaTrace. The project is pre-alpha and not yet
published, but contributions are welcome through focused issues and pull requests.

## Code of conduct

All contributors must follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Current project stage

Implemented today:

- Stage 1A immutable contract algebra and whole-graph validation;
- Stage 1B-R1 byte-exact canonicalization and deterministic contract identity;
- Stage 1B-R2 deterministic payoff-graph compilation, identity and provenance;
- Stage 1C-R1A private report foundation;
- Stage 1C-R1B private validation-equivalence orchestration.

Stage 1C-R1 is complete privately. Stage 1C-R2 deterministic structural diffing
is planned, and no public Stage 1C comparison API is exported.

Pricing, valuation, Greeks, market data, numerical engines, calibration, hedging
and model selection remain outside the implemented scope.

## Development setup

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Contribution workflow

1. Open or claim an issue describing the intended change.
2. Discuss changes to public semantics, deterministic identity, security
   boundaries, dependencies or architecture before implementation.
3. Add or update an ADR under [`docs/adr/`](docs/adr/) for constitutional changes.
4. Create a focused branch from `main`.
5. Add tests for every changed behaviour, including hostile and forged inputs when
   boundary hardening is affected.
6. Run the complete quality gate.
7. Open a pull request explaining intent, scope, evidence and exclusions.

## Required checks

```bash
ruff format .
ruff format --check .
ruff check .
mypy
pytest --cov=derivatrace --cov-branch --cov-report=term-missing --cov-fail-under=100
DG_TEST_PACKAGING=1 pytest tests/test_packaging.py -v
```

Pull requests must preserve Python 3.11–3.14 compatibility, 100% statement and
branch coverage, strict typing, deterministic behaviour and packaging integrity.

## Design principles

- **Separation of concerns:** contract semantics, market data, models, numerical
  engines, risk, validation and evidence certificates remain distinct.
- **Determinism:** identical supported inputs produce identical canonical outputs
  and identities under the declared schema and policy.
- **Immutability and typing:** implemented domain values and graph nodes are frozen,
  slotted and explicitly typed.
- **Use-time validation:** caller-owned or forged state is re-checked at trusted
  boundaries.
- **Exact numbers:** ambiguous floating-point contract terms are rejected.
- **Supported-node policy:** only explicitly implemented concrete node types are
  accepted.
- **No hidden intelligence:** assistive tooling must not silently alter contracts,
  schemas, models, inputs, engines or validation outcomes.
- **Security by default:** external inputs are untrusted and processing is bounded.
- **Evidence by design:** future results should carry enough information to be
  audited and reproduced.

## Scope discipline

Do not introduce any of the following without a separately reviewed roadmap and
architecture decision:

- runtime dependencies;
- pricing or valuation functionality;
- market-data access;
- numerical engines;
- automatic model selection;
- arbitrary executable user code;
- changes to existing canonical identities or schemas;
- a public Stage 1C API before the R2 export gate.

## Documentation

Keep documentation links valid and status claims consistent across the README,
roadmap, specifications, ADRs and changelog. Do not claim formal verification,
production readiness, ecosystem adoption or capabilities that do not exist.

## Security

Follow the [Security policy](SECURITY.md) for vulnerabilities. Never disclose a
security-sensitive issue in a public ticket before coordinated review.

## Licence

Contributions are accepted under the [MIT License](LICENSE).