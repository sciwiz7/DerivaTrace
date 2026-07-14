# Certificate specification

This document specifies the planned **evidence certificate** for DerivaTrace
valuations. It is a specification for Stage 4 and later; no certificate is
produced in Stage 0. A certificate is evidence and a record of validation
outcomes — it is **not** a mathematical proof.

## Certificate goals

- Attach self-contained evidence to every valuation result.
- Make a result reproducible from its certificate under the same software and
  configuration.
- Surface model disagreement, uncertainty, warnings, and limitations.
- Enable tamper detection through deterministic integrity hashes.

## Certificate non-goals

- A certificate does **not** constitute a proof of correctness or fairness.
- A certificate does **not** replace human or institutional model-risk review.
- A certificate hash is **not** a digital signature.
- External signing, if added later, is an explicit optional capability.

## Terminology

- **Evidence** — recorded facts about what was calculated and how.
- **Assertion** — a stated claim made by the producing system (e.g., "engine
  converged").
- **Validation outcome** — the result of a check (pass, warn, fail).
- **Warning** — a non-fatal limitation or caution.
- **Unsupported claim** — a statement the system is not entitled to make.
- **Integrity hash** — a deterministic SHA-256 digest over canonical bytes.
- **Signature (future)** — an external cryptographic attestation, optional.

## Versioned envelope

The certificate is a versioned JSON envelope. The schema version is explicit so
that consumers can migrate safely.

```json
{
  "certificate_schema_version": "1.0.0",
  "certificate_id": "cert:sha256:<hex>",
  "created_at": "2026-01-01T00:00:00Z",
  "contract": {
    "canonical": "<canonical-contract-representation>",
    "contract_hash": "sha256:<hex>"
  },
  "market_snapshot": {
    "snapshot_hash": "sha256:<hex>"
  },
  "model": {
    "model_id": "black_scholes",
    "parameters": {}
  },
  "engine": {
    "engine_id": "closed_form",
    "configuration": {}
  },
  "result": {
    "value": 0.0,
    "currency": "USD",
    "units": "present_value"
  },
  "uncertainty": {
    "method": "analytic",
    "tolerance": 0.0
  },
  "greeks": {},
  "validation": [
    {"check": "non_negative_price", "outcome": "pass"}
  ],
  "warnings": [],
  "limitations": [],
  "software": {
    "package_version": "0.1.0.dev0",
    "source_commit": "<git-commit-sha>"
  },
  "environment": {
    "python_version": "3.14"
  },
  "reproducibility": {
    "seed": null,
    "path_count": null,
    "time_steps": null,
    "sampling_method": null
  },
  "reproducibility_hash": "sha256:<hex>",
  "certificate_hash": "sha256:<hex>"
}
```

## Field-by-field semantics

- `certificate_schema_version` — semantic version of this envelope.
- `certificate_id` — a deterministic identifier derived from the certificate
  hash (planned).
- `created_at` — RFC 3339 timestamp with explicit UTC offset.
- `contract.canonical` — the canonical contract representation or reference.
- `contract.contract_hash` — SHA-256 of the canonical contract bytes.
- `market_snapshot.snapshot_hash` — SHA-256 of the market snapshot.
- `model.model_id` / `parameters` — model identity and explicit parameters.
- `engine.engine_id` / `configuration` — engine identity and configuration.
- `result.value` / `currency` / `units` — the primary result with units.
- `uncertainty` — method and tolerance/error estimate.
- `greeks` — sensitivities keyed by name (Stage 5+).
- `validation` — list of named checks with outcomes.
- `warnings` / `limitations` — non-fatal cautions and scope limits.
- `software` / `environment` — versions enabling reproduction.
- `reproducibility` — seed, path counts, time steps, sampling method.
- `reproducibility_hash` — SHA-256 over the canonicalized bytes of the
  deterministic, computation-defining fields only (see "Hashing procedure").
  Two valuations produced from identical inputs and configuration share a
  `reproducibility_hash` regardless of when they were created.
- `certificate_hash` — SHA-256 over the canonicalized certificate bytes
  (excluding itself). This fingerprint includes `created_at`, so it captures the
  moment of creation and is the basis of `certificate_id`.

## Canonicalization requirements

The certificate bytes used for hashing must be canonical:

- Explicit schema version.
- Deterministic key ordering (e.g., lexicographic).
- Deterministic number representation (no locale, no trailing precision noise).
- Explicit time zones (UTC for timestamps).
- Explicit currencies and units.
- **No `NaN` or `Infinity`** anywhere in the certificate.
- Rejection of ambiguous or unsupported input.
- Deterministic UTF-8 serialization.

## Hashing procedure

All hashing uses canonical UTF-8 JSON serialization with the following fixed
rules:

- Object keys are serialized in lexicographic (sorted) order.
- Every field declared by the schema is serialized, including `null` values;
  fields are never silently dropped or reordered.
- Numbers use a deterministic, locale-independent representation with no
  trailing-precision noise (see "Decimal and numeric canonicalization").
- Timestamps are UTC and use the RFC 3339 profile (`YYYY-MM-DDThh:mm:ssZ`).
- Currencies and units are explicit strings, never implied.

Two distinct hashes are computed:

### `certificate_hash` (integrity + identity fingerprint)

1. Start from the full certificate object.
2. Serialize to canonical UTF-8 JSON with sorted keys.
3. Omit **only** the `certificate_hash` field from the serialized payload.
4. Compute `SHA-256` over the resulting UTF-8 bytes.
5. Store the hex digest in `certificate_hash`.

Because this payload includes `created_at` (and `reproducibility_hash`), the
`certificate_hash` changes if the certificate is re-created at a different time
even when the underlying computation is identical. `certificate_id` is derived
from `certificate_hash`, so certificate identity is creation-time-dependent by
design. The `certificate_hash` is an **integrity** mechanism: it detects
accidental or malicious modification. It is **not** an authentication mechanism.

### `reproducibility_hash` (deterministic computation identity)

1. Build a reduced certificate object containing only the fields that fully
   determine the computation: `certificate_schema_version`, `contract`,
   `market_snapshot`, `model`, `engine`, `result` (value, currency, units),
   `uncertainty`, `greeks`, `validation`, `warnings`, `limitations`,
   `software`, `environment`, and `reproducibility`.
2. Serialize to canonical UTF-8 JSON with sorted keys.
3. Omit `certificate_hash` **and** `reproducibility_hash` from the payload.
4. Compute `SHA-256` over the resulting UTF-8 bytes.
5. Store the hex digest in `reproducibility_hash`.

Two certificates that describe the same valuation under the same software and
configuration produce an identical `reproducibility_hash` regardless of
`created_at`. This is the field that enables "reproduce the same result" checks
and model/engine comparison, and it must **not** be confused with either
integrity or identity.

## Decimal and numeric canonicalization

Neither the `certificate_hash` nor the `reproducibility_hash` may be computed
over ambiguous numeric text. Exact contract terms represented as `Decimal` must
be serialized in a single, pinned canonical form (for example, a fixed
scientific-notation normalization with a declared significant-digit and exponent
rule) so that two numerically equal values always produce identical bytes. The
precise serialization rule is finalized in Stage 4 together with the canonical
contract representation; it must be deterministic, locale-independent, and
independent of Python's default `float`/`Decimal` `repr`.

## Certificate identity

`certificate_id` is planned to be derived from `certificate_hash` so that two
byte-identical certificates share an identity and any change is detectable.
Because `certificate_hash` includes `created_at`, certificate identity is
creation-time-dependent: it identifies a specific issuance, not the underlying
computation. To compare two valuations that should be equivalent regardless of
when they were produced, use `reproducibility_hash` instead.

## Result evidence

The `result` block records the value, its currency, and its units. It is
evidence of *what* was computed, not a claim that the computation is correct.

## Validation evidence

The `validation` block records each check by name and outcome. Outcomes are
`pass`, `warn`, or `fail`. A `fail` must prevent the certificate from claiming a
successful valuation.

## Numerical uncertainty

The `uncertainty` block records the method (analytic, Monte Carlo error
estimate, etc.) and a tolerance or error estimate. Stochastic engines must
expose seeds, path counts, time steps, sampling methods, error estimates, and
convergence diagnostics (planned Stage 3+).

## Reproducibility information

The `reproducibility` block records everything needed to replay the calculation:
software version, source commit, engine configuration, and stochastic controls.
Given identical inputs and controls, the system is designed to reproduce the same
result within its declared numerical reproducibility policy.

## Warning taxonomy

Warnings are categorized, for example:

- **Numerical** — near-boundary inputs, low path counts.
- **Model** — assumptions that may not hold.
- **Data** — stale or interpolated market data.
- **Scope** — functionality outside the validated stage.

## Tamper detection

Because `certificate_hash` covers the canonical payload, any modification of a
field changes the hash. Verification recomputes the hash and compares. A
mismatch indicates tampering or corruption.

## Optional future signing

An external digital signature may later be attached as an optional field. Signing
is distinct from hashing: a hash proves integrity; a signature proves
provenance. The two must not be confused in code or documentation.

## Schema migration policy

- Schema versions are explicit and monotonic.
- Consumers must reject certificates with unknown or unsupported schema
  versions.
- Migrations must preserve the ability to verify integrity of older
  certificates.

## Example (non-production, illustrative)

The JSON above is illustrative only. It is **not** produced by current code and
must not be treated as a real valuation. DerivaTrace at Stage 0 performs no
pricing.

See also [architecture.md](./architecture.md),
[contract-semantics.md](./contract-semantics.md), and
[ADR 0003](./adr/0003-evidence-carrying-results.md).
