# Glossary

This glossary defines key terms used across DerivaTrace documentation. Terms are
defined in the context of this project and are not legal or regulatory
definitions.

- **Arbitrage check** — a validation that a price does not permit a risk-free
  profit under stated assumptions.
- **Canonicalization** — the process of converting equivalent inputs into a
  single stable representation.
- **Certificate** — a versioned evidence envelope describing what was calculated
  and how.
- **Contract semantics** — the definition of what a financial instrument pays,
  independent of valuation.
- **Determinism** — the property that identical inputs produce identical,
  reproducible outputs within a declared policy.
- **Evidence** — recorded facts about a calculation and its context.
- **Exact term** — a contract quantity represented exactly (e.g., via
  `Decimal` or structured types), not as a floating-point approximation.
- **Hashing** — computing a deterministic digest (SHA-256) over canonical bytes
  for integrity.
- **Integrity hash** — a SHA-256 digest used to detect modification. Not a
  digital signature.
- **Market snapshot** — a captured set of observable market inputs with a
  deterministic identity.
- **Model** — a set of assumptions governing stochastic behaviour.
- **Numerical engine** — a method that computes results from a model and inputs.
- **Observation time** — when a market value is read.
- **Payoff graph** — a canonical, model-independent representation of a
  contract's payoffs.
- **Reproducibility policy** — the declared conditions under which a result can
  be reproduced.
- **Risk** — sensitivities (Greeks) and uncertainty associated with a valuation.
- **Settlement time** — when cash is exchanged.
- **Signature (future)** — an optional external cryptographic attestation of
  provenance; distinct from an integrity hash.
- **Validation outcome** — the result (`pass`, `warn`, `fail`) of a check.
- **Warning** — a non-fatal caution recorded in a certificate.
