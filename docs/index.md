# DerivaTrace documentation

This is the documentation index for **DerivaTrace**, an open-source
evidence-carrying derivatives compiler and model-risk laboratory. DerivaTrace is at
**Stage 1A** (pre-alpha, not published).

## Project status

- Stage 0 established the foundation and the architectural constitution.
- Stage 1A implements the **contract semantics** and **validation** bounded
  contexts as a concrete, typed, immutable contract algebra
  (`derivatrace.contracts`) with whole-graph validation.
- **Stage 1B architecture baseline is Complete.** The canonical contract
  representation, canonical payoff graph, and canonical identity are specified in
  `canonicalization-spec.md`, `payoff-graph-spec.md`, `canonical-test-vectors.md`,
  and [ADR 0007](./adr/0007-canonical-contract-identity-and-payoff-graph.md).
- **Stage 1B-R1 canonical runtime is Implemented:** `derivatrace.canonical`
  canonicalizes a validated contract graph into byte-exact canonical JSON with a
  deterministic canonical contract identity. The Stage 1B-R2 payoff-graph runtime
  remains Planned (specified, not implemented).
- Stage 1C (validation levels and equivalence reporting) is planned.
- No pricing, valuation, Greeks, Monte Carlo, PDE, calibration, or hedging
  functionality exists yet.
- The deterministic core and evidence-certificate design are specified here,
  not fully implemented.

## Core principle

> **A valuation without evidence is an incomplete output.**

## Document map

- [Vision](./vision.md) — why a price alone is insufficient and the long-term
  ambition.
- [Product specification](./product-spec.md) — users, requirements, scope, and
  success criteria.
- [Architecture](./architecture.md) — bounded contexts, dependency direction,
  diagrams, and forbidden dependencies.
- [Contract semantics](./contract-semantics.md) — contract AST, primitives, and
  validation levels.
- [Contract API (Stage 1A)](./contract-api.md) — the implemented public API,
  construction rules, and validation semantics with runnable examples.
- [Canonicalization specification (Stage 1B)](./canonicalization-spec.md) —
  canonical schema, byte encoding, value encoding, per-node laws, DAG policy,
  hashing, and error taxonomy (Stage 1B architecture baseline, now implemented as
  the Stage 1B-R1 canonical runtime).
- [Payoff-graph specification (Stage 1B)](./payoff-graph-spec.md) — model-
  independent payoff-graph node taxonomy and compilation mapping (specified;
  Stage 1B-R2 runtime planned).
- [Canonical test vectors (Stage 1B)](./canonical-test-vectors.md) — test-vector
  format and normative vectors produced and verified by the canonical runtime.
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
  - [ADR 0006: Stage 1 contract algebra and runtime type system](./adr/0006-stage-1-contract-algebra-and-runtime-type-system.md)
  - [ADR 0007: Canonical contract identity and payoff graph](./adr/0007-canonical-contract-identity-and-payoff-graph.md)

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
