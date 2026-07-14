# DerivaTrace documentation

This is the documentation index for **DerivaTrace**, an open-source
evidence-carrying derivatives compiler and model-risk laboratory. DerivaTrace is at
**Stage 0** (pre-alpha, not published).

## Project status

- Stage 0 establishes the foundation and the architectural constitution.
- No pricing, valuation, Greeks, Monte Carlo, PDE, calibration, or hedging
  functionality exists yet.
- The deterministic core and evidence-certificate design are specified here,
  not implemented.

## Core principle

> **A valuation without evidence is an incomplete output.**

## Document map

- [Vision](./vision.md) — why a price alone is insufficient and the long-term
  ambition.
- [Product specification](./product-spec.md) — users, requirements, scope, and
  success criteria.
- [Architecture](./architecture.md) — bounded contexts, dependency direction,
  diagrams, and forbidden dependencies.
- [Contract semantics](./contract-semantics.md) — future contract AST,
  primitives, and validation levels.
- [Certificate specification](./certificate-spec.md) — versioned evidence
  envelope and hashing procedure.
- [Threat model](./threat-model.md) — assets, actors, attack surfaces, and
  mitigations.
- [Glossary](./glossary.md) — definitions of key terms.
- [Architectural decision records](./adr/) — the constitutional decisions:
  - [ADR 0001: Separation of contract, model, and engine](./adr/0001-separation-of-contract-model-engine.md)
  - [ADR 0002: Deterministic canonicalization](./adr/0002-deterministic-canonicalization.md)
  - [ADR 0003: Evidence-carrying results](./adr/0003-evidence-carrying-results.md)
  - [ADR 0004: Exact contract terms and numerical boundaries](./adr/0004-exact-contract-terms-and-numerical-boundaries.md)
  - [ADR 0005: No hidden model selection](./adr/0005-no-hidden-model-selection.md)

## Related root documents

- [README](../README.md)
- [Roadmap](../ROADMAP.md)
- [Contributing](../CONTRIBUTING.md)
- [Code of conduct](../CODE_OF_CONDUCT.md)
- [Security policy](../SECURITY.md)
- [Governance](../GOVERNANCE.md)
- [Changelog](../CHANGELOG.md)
- [Licence](../LICENSE)

## Separation of concerns

DerivaTrace separates:

1. **Contract semantics** — what the instrument pays.
2. **Market data** — observable inputs and snapshots.
3. **Model** — assumptions governing stochastic behaviour.
4. **Numerical engine** — the method used to calculate results.
5. **Risk** — sensitivities and uncertainty.
6. **Validation** — invariants and arbitrage checks.
7. **Evidence certificate** — what was calculated and how.

No layer may silently absorb another layer's responsibility.
