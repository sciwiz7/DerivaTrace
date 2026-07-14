# ADR 0004: Exact contract terms and numerical boundaries

- **Status:** Accepted (Stage 0)
- **Date:** 2026-01-01
- **Deciders:** Founding principal architect

## Context

Mixing exact contractual quantities (notionals, strikes, dates, currencies) with
approximate numerical-engine representations invites silent precision loss and
subtle valuation errors. A system that cannot show where exact terms became
approximate cannot be audited.

## Decision

DerivaTrace distinguishes two numeric domains:

- Contractual terms and exact identifiers may use `Decimal` or exact structured
  representations.
- Numerical pricing engines may later use floating-point arrays.

Conversion between exact contract terms and numerical-engine inputs must be
explicit, validated, and recorded. No silent precision conversion is permitted.
The foundational Stage 0 package adds no numerical dependencies (no NumPy,
SciPy, pandas, JAX, PyTorch, QuantLib, or Streamlit).

## Consequences

- **Positive:** Exact terms remain exact until an explicit, recorded conversion.
- **Positive:** Numerical choices are visible and reproducible.
- **Negative:** Additional plumbing is required at the contract/engine boundary.
- **Constraint:** Any numerical dependency added later must be reviewed and
  recorded as part of the evidence.

## Alternatives considered

- Using floats everywhere — rejected due to silent precision loss.
- Hiding conversion inside the engine — rejected as a hidden-intelligence and
  auditability risk.
