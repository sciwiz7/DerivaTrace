# ADR 0001: Separation of contract, model, and engine

- **Status:** Accepted (Stage 0)
- **Date:** 2026-01-01
- **Deciders:** Founding principal architect

## Context

Derivatives tooling frequently entangles *what is paid* (the contract), *how
the world behaves* (the model), and *how the math is done* (the numerical
engine). This entanglement makes results hard to reproduce, compare, and audit,
and hides assumption changes behind implementation details.

## Decision

DerivaTrace separates seven concerns: contract semantics, market data, model,
numerical engine, risk, validation, and evidence certificate. Each has a single
responsibility and must not silently absorb another's duty. A contract is
defined once in a model-independent, canonical form and is valued by explicitly
selected models and engines.

## Consequences

- **Positive:** Reproducibility, comparability across models, and auditable
  assumptions become first-class.
- **Positive:** Validation and certificates can reference each layer explicitly.
- **Negative:** More structure upfront; contracts require an explicit algebra
  rather than ad-hoc pricing functions.
- **Constraint:** Forbidden cross-layer dependencies are enforced by design
  review and tests (see architecture.md).

## Alternatives considered

- Monolithic pricing functions per instrument — rejected as non-compositional
  and opaque.
- Implicit model selection inside engines — rejected as a hidden-intelligence
  risk (see ADR 0005).
