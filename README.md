# DerivaTrace

> An open-source evidence-carrying derivatives compiler and model-risk laboratory.

[![CI](https://github.com/sciwiz7/DerivaTrace/actions/workflows/ci.yml/badge.svg)](https://github.com/sciwiz7/DerivaTrace/actions/workflows/ci.yml)
![Python 3.11–3.14](https://img.shields.io/badge/python-3.11%E2%80%933.14-blue)
![Coverage](https://img.shields.io/badge/statement%20%26%20branch%20coverage-100%25-brightgreen)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## Current status

DerivaTrace is **pre-alpha**, **not published**, and not available on PyPI.

- **Stage 0:** foundation, governance, security policy, CI, packaging and architecture — complete.
- **Stage 1A:** immutable typed contract algebra and whole-graph validation — complete.
- **Stage 1B-R1:** byte-exact canonical contract representation and deterministic identity — implemented.
- **Stage 1B-R2:** deterministic payoff-graph compilation, identity and provenance — implemented.
- **Stage 1C architecture baseline:** established.
- **Stage 1C-R1A:** private validation-equivalence report foundation — implemented.
- **Stage 1C-R1B:** private orchestration runtime — implemented.
- **Stage 1C-R1 overall:** complete privately.
- **Stage 1C-R2:** deterministic structural diffing — planned.
- **Public Stage 1C API:** unimplemented; no public `compare_contracts` export exists.

The repository currently has **1,451 passing tests**, 5 intentionally skipped tests,
100% statement and branch coverage, strict mypy, Ruff, packaging validation and CI
across Python 3.11–3.14.

## Why DerivaTrace exists

Derivatives analytics often delivers a number without a self-contained record of
how it was produced. Reproducing, comparing or challenging that result can require
scattered notebooks, undocumented engine settings and institutional knowledge.

DerivaTrace is designed around a stricter principle:

> **A valuation without evidence is an incomplete output.**

The long-term system separates contract semantics, market data, models, numerical
engines, risk, validation and evidence certificates so that one layer cannot
silently absorb another layer's responsibility.

## What exists today

### Stage 1A — Contract algebra and validation

The public `derivatrace.contracts` package provides:

- exact domain values including `ExactNumber`, `Currency`, `Unit`, identifiers and timestamps;
- immutable scalar and Boolean expression nodes;
- immutable contract nodes including `Zero`, `Payment`, `Both`, `Scale` and `ConditionalContract`;
- iterative whole-graph validation with deterministic metrics;
- rejection of forged objects, unsupported subclasses, cycles and excessive complexity.

### Stage 1B-R1 — Canonical contract identity

The public `derivatrace.canonical` package:

- validates and canonicalizes supported contracts;
- emits compact, byte-exact canonical JSON;
- content-addresses canonical nodes;
- detects collisions;
- derives deterministic `canonical:sha256:` identities.

### Stage 1B-R2 — Payoff-graph runtime

The public `derivatrace.payoffgraph` package compiles supported contracts into a
deterministic, reachable-only payoff DAG.

- `structural_bytes` contains the canonical structural projection used for identity.
- `document_bytes` contains the same structural fields plus deterministic provenance.
- Neither representation is pretty-printed.
- Provenance includes the compiler tag and source contract identity but is excluded
  from the payoff-graph identity.
- The resulting identity uses the `payoffgraph:sha256:` domain.

### Stage 1C-R1 — Private validation-equivalence runtime

The architecture baseline established graded evaluation levels (`structural`,
`canonical`, `payoff`) and deterministic equivalence reports.

The private R1 runtime now:

- validates caller-owned schemas and limits before operand processing;
- processes each operand independently through the requested evaluation depth;
- preserves upstream error namespaces and classifications;
- checks explicit and internal canonicalization consistency;
- constructs deterministic, self-validating reports;
- supports `diff_representation="none"` only.

Stage 1C-R2 structural diffing remains planned. The public Stage 1C API remains
unimplemented until the R2 and export gates are completed.

## Security and maintenance model

DerivaTrace treats caller-owned objects and serialized representations as untrusted.
The project uses exact-type boundaries, use-time invariant validation, iterative
bounded traversal, collision checks, deterministic encoding, exception containment
and a dedicated security-reporting process.

Maintenance work is organised through issues, ADRs, focused pull requests and a CI
gate requiring:

- Ruff formatting and linting;
- strict mypy;
- 100% statement and branch coverage;
- Python 3.11–3.14 compatibility;
- wheel and sdist inventory validation.

See [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md) and
[GOVERNANCE.md](GOVERNANCE.md).

## What does not exist today

DerivaTrace does **not** currently provide:

- pricing, valuation or Greeks calculations;
- Monte Carlo, PDE, tree or closed-form numerical engines;
- market-data retrieval or market snapshots;
- calibration, hedging or model selection;
- evidence-carrying valuation certificates;
- a public validation-equivalence comparison API;
- a published package or stable release.

Nothing in this repository constitutes financial advice or a production-ready
pricing or risk system.

## Installation for contributors

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Development commands

```bash
ruff format .
ruff format --check .
ruff check .
mypy
pytest --cov=derivatrace --cov-branch --cov-report=term-missing --cov-fail-under=100
DG_TEST_PACKAGING=1 pytest tests/test_packaging.py -v
```

## Repository map

```text
DerivaTrace/
├── .github/workflows/ci.yml
├── docs/
│   ├── architecture.md
│   ├── canonicalization-spec.md
│   ├── payoff-graph-spec.md
│   ├── validation-equivalence-spec.md
│   ├── threat-model.md
│   └── adr/
├── src/derivatrace/
├── tests/
├── README.md
├── ROADMAP.md
├── CONTRIBUTING.md
├── SECURITY.md
├── GOVERNANCE.md
├── CHANGELOG.md
└── LICENSE
```

## Documentation

- [Documentation index](docs/index.md)
- [Vision](docs/vision.md)
- [Product specification](docs/product-spec.md)
- [Architecture](docs/architecture.md)
- [Contract API](docs/contract-api.md)
- [Canonicalization specification](docs/canonicalization-spec.md)
- [Payoff-graph specification](docs/payoff-graph-spec.md)
- [Canonical test vectors](docs/canonical-test-vectors.md)
- [Validation-equivalence specification](docs/validation-equivalence-spec.md)
- [Threat model](docs/threat-model.md)
- [Architectural decision records](docs/adr/)
- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)

## Licence

DerivaTrace is released under the [MIT License](LICENSE).

## Disclaimer

DerivaTrace is a research and educational project. It is pre-alpha, not validated
for production use, and must not be used to make investment, trading, valuation or
risk decisions. Future capabilities described in the documentation are aspirational
and subject to architectural review.