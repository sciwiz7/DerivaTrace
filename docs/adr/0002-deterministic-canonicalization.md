# ADR 0002: Deterministic canonicalization

- **Status:** Accepted (Stage 0)
- **Date:** 2026-01-01
- **Deciders:** Founding principal architect

## Context

To compare, reproduce, and certify valuations, equivalent serialized inputs must
map to a single stable representation. Non-deterministic serialization,
ambiguous numbers, missing time zones, or locale-dependent formatting would
break identity, hashing, and reproducibility.

## Decision

DerivaTrace canonicalizes with the following rules:

- Explicit schema versions for all serializable objects.
- Deterministic key ordering (e.g., lexicographic).
- Deterministic number representation (no locale, no trailing-precision noise).
- Explicit time zones (UTC for timestamps).
- Explicit currencies and units.
- Rejection of `NaN` and `Infinity` in certificates.
- Rejection of ambiguous or unsupported input.
- Deterministic UTF-8 serialization.
- SHA-256 integrity hashing over canonical bytes.
- Clear separation between integrity hashes and cryptographic signatures.

## Consequences

- **Positive:** Stable identity, tamper-evident certificates, reproducible
  builds and runs.
- **Positive:** Hashes detect modification; they are explicitly *not*
  signatures.
- **Negative:** Inputs must be well-formed; ambiguous data is rejected rather
  than guessed.
- **Constraint:** Any change to canonicalization must bump the schema version
  and preserve old-certificate verifiability.

## Alternatives considered

- Accepting loosely typed input and normalizing lazily — rejected as
  non-reproducible.
- Using hashes as authentication — rejected; hashing is integrity only (see
  certificate-spec.md).
