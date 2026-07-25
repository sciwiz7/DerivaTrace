# DerivaTrace documentation

DerivaTrace is an open-source evidence-carrying derivatives compiler and model-risk
laboratory. It is **pre-alpha**, **not published**, and has no pricing or valuation
functionality.

## Project status

- Stage 0 foundation, governance, security and CI: complete.
- Stage 1A contract algebra and validation: complete.
- Stage 1B-R1 canonical runtime: implemented.
- Stage 1B-R2 payoff-graph runtime: implemented.
- Stage 1C architecture baseline: established.
- Stage 1C-R1A private report foundation: implemented.
- Stage 1C-R1B private orchestration: implemented.
- Stage 1C-R1 overall: complete privately.
- Stage 1C-R2 structural diffing: planned.
- Public Stage 1C API: unimplemented.

The implemented code is exercised by 1,451 passing tests with 100% statement and
branch coverage, strict mypy, Ruff, packaging validation and CI on Python
3.11–3.14.

## Core principle

> **A valuation without evidence is an incomplete output.**

The project maintains a strict separation of concerns between:

1. contract semantics;
2. market data;
3. models;
4. numerical engines;
5. risk;
6. validation;
7. evidence certificates.

No layer may silently absorb another layer's responsibility.

## Implemented documentation

- [Contract API](./contract-api.md) — the public Stage 1A immutable contract and
  validation API.
- [Canonicalization specification](./canonicalization-spec.md) — byte-exact
  canonical representation, identity, limits and error taxonomy implemented by
  Stage 1B-R1.
- [Payoff-graph specification](./payoff-graph-spec.md) — deterministic payoff DAG,
  identity and provenance implemented by Stage 1B-R2.
- [Canonical test vectors](./canonical-test-vectors.md) — normative canonical and
  payoff-graph vectors exercised by the runtimes.
- [Validation-equivalence specification](./validation-equivalence-spec.md) — the
  established Stage 1C architecture, implemented private R1 report and
  orchestration foundation, and planned R2 diff engine.

## Architecture and product documents

- [Vision](./vision.md)
- [Product specification](./product-spec.md)
- [Architecture](./architecture.md)
- [Contract semantics](./contract-semantics.md)
- [Certificate specification](./certificate-spec.md)
- [Threat model](./threat-model.md)
- [Glossary](./glossary.md)

## Architectural decision records

- [ADR 0001: Separation of contract, model and engine](./adr/0001-separation-of-contract-model-engine.md)
- [ADR 0002: Deterministic canonicalization](./adr/0002-deterministic-canonicalization.md)
- [ADR 0003: Evidence-carrying results](./adr/0003-evidence-carrying-results.md)
- [ADR 0004: Exact contract terms and numerical boundaries](./adr/0004-exact-contract-terms-and-numerical-boundaries.md)
- [ADR 0005: No hidden model selection](./adr/0005-no-hidden-model-selection.md)
- [ADR 0006: Stage 1 contract algebra and runtime type system](./adr/0006-stage-1-contract-algebra-and-runtime-type-system.md)
- [ADR 0007: Canonical contract identity and payoff graph](./adr/0007-canonical-contract-identity-and-payoff-graph.md)
- [ADR 0008: Validation levels, equivalence and structural diffing](./adr/0008-validation-levels-equivalence-and-structural-diffing.md)
- [ADR 0009: Stage 1C runtime delivery seam](./adr/0009-stage-1c-runtime-delivery-seam.md)

## Repository governance

- [README](../README.md)
- [Roadmap](../ROADMAP.md)
- [Contributing](../CONTRIBUTING.md)
- [Code of conduct](../CODE_OF_CONDUCT.md)
- [Security policy](../SECURITY.md)
- [Governance](../GOVERNANCE.md)
- [Changelog](../CHANGELOG.md)
- [MIT License](../LICENSE)

## Scope boundary

The repository does not currently calculate prices, values, Greeks or market-risk
measures. It does not contain numerical engines, market data, calibration or
hedging functionality, and it is not suitable for production or investment use.