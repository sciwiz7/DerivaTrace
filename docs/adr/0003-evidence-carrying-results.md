# ADR 0003: Evidence-carrying results

- **Status:** Accepted (Stage 0)
- **Date:** 2026-01-01
- **Deciders:** Founding principal architect

## Context

A derivative price delivered without context cannot be independently
reproduced, compared, or audited. Stakeholders need to know the contract,
market data, model, engine, parameters, uncertainty, and checks behind a number.

## Decision

Every future valuation is designed to produce a versioned **evidence
certificate** containing: certificate schema version and identity, creation
timestamp, contract canonical representation and hash, market snapshot hash,
model identifier and parameters, engine identifier and configuration, result
values with units and currency, uncertainty and tolerances, Greeks, validation
checks, warnings and limitations, software package version, source commit,
environment information, reproducibility configuration, and a certificate hash.

The certificate clearly distinguishes evidence, assertions, validation outcomes,
warnings, and unsupported claims. Passing checks does **not** constitute a
mathematical proof, and the system will not claim that it does.

## Consequences

- **Positive:** Results are auditable and reproducible from their certificate.
- **Positive:** Model disagreement and limitations are explicit.
- **Negative:** More metadata must be captured and maintained.
- **Constraint:** Certificates record evidence; they are not proofs and not
  signatures.

## Alternatives considered

- Bare numeric output — rejected as incomplete under the project principle.
- Claiming proof on check success — rejected as misleading.
