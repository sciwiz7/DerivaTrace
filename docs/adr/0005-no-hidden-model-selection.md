# ADR 0005: No hidden model selection

- **Status:** Accepted (Stage 0)
- **Date:** 2026-01-01
- **Deciders:** Founding principal architect

## Context

If a system silently chooses a model or numerical engine, the user cannot know
which assumptions produced a price. Silent selection also prevents fair model
comparison and undermines auditability and reproducibility.

## Decision

DerivaTrace never silently selects a financial model or numerical engine. Models
and engines are chosen explicitly by the caller and recorded in the evidence
certificate. The deterministic core remains authoritative for contract
semantics, canonicalization, calculations, tolerances, validation, and
certificates.

Future assistive (including AI) features may explain or summarize results, but
they must not silently change contracts, models, market inputs, engine
settings, or validation outcomes. Model or engine substitution is treated as a
security and integrity threat (see threat-model.md).

## Consequences

- **Positive:** Every result names the exact model and engine used.
- **Positive:** Model disagreement becomes visible information, not a hidden
  choice.
- **Negative:** Callers must make explicit choices; there is no "magic default"
  that hides assumptions.
- **Constraint:** Assistive tooling is bounded and cannot mutate authoritative
  inputs or outputs.

## Alternatives considered

- A smart default that picks the "best" model — rejected as hidden intelligence.
- AI auto-selection of engines — rejected as incompatible with auditability.
