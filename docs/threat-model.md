# Threat model

This document analyzes the security threats relevant to DerivaTrace. It is part
of the Stage 0 specification. All external inputs are treated as untrusted.

## Assets

- Contract definitions (user-authored or imported).
- Market-data snapshots.
- Serialized evidence certificates.
- Plugin metadata and future contribution inputs.
- The deterministic core and its canonicalization/hashing logic.
- Source code, build, and release workflows.
- Validation and certificate outputs relied upon by reviewers.

## Actors

- **Legitimate users** — authors, quants, model-risk reviewers, contributors.
- **Malicious external input** — crafted contracts, snapshots, certificates,
  or plugin metadata.
- **Compromised dependency or release pipeline** — supply-chain adversary.
- **Insider with excessive privilege** — inappropriate access to release or
  signing.

## Trust boundaries

- Deterministic core (trusted) vs. all external inputs (untrusted).
- Local process vs. network/serialized artifacts.
- Build environment vs. published artifacts.
- Assistive/AI features (untrusted to change results) vs. authoritative core.

## Attack surfaces

- Contract/market/certificate parsers and deserializers.
- Canonicalization and hashing routines.
- Future plugin loading and registration.
- Build, CI, and release pipelines.
- Serialization formats (JSON, archive, future interchange formats).

## Misuse cases

- **Arbitrary-code execution** — a malicious contract or plugin attempts to run
  code (e.g., via `eval`/`exec` or unsafe dynamic imports). DerivaTrace must
  never execute contract or plugin code; contract logic is data, not code.
- **Malicious serialization** — crafted JSON/archive triggers resource
  exhaustion or unexpected object construction.
- **Schema confusion** — a certificate is presented as a contract, or a newer
  schema is downgraded silently.
- **Dependency substitution** — a compromised or typosquatted dependency is
  installed.
- **Certificate tampering** — a value is altered after signing/hashing.
- **Hash confusion** — an integrity hash is mistaken for a signature, or a weak
  hash is accepted.
- **Path traversal** — file references escape intended directories.
- **Archive extraction** — a zip/tar bomb or symlink attack during extraction.
- **Denial of service** — extreme numeric values, huge inputs, or deep
  recursion exhaust resources.
- **Extreme numeric values** — `NaN`, `Infinity`, or overflow corrupt results
  or comparisons.
- **Secret leakage** — credentials embedded in configs, logs, or certificates.
- **Compromised release workflows** — an attacker publishes a malicious build.
- **Model or engine substitution** — a different model/engine is used than the
  one recorded, without detection.
- **Misleading validation claims** — a certificate implies proof or hides a
  failed check.
- **Canonicalization collision** — two distinct, non-equivalent contracts or
  snapshots serialize to identical canonical bytes, yielding the same hash and
  identity and defeating equality and integrity checks.
- **Cyclic graph** — a self-referential or circular contract graph (for example,
  a payoff referencing itself, or circular exercise/observation dependencies)
  causes unbounded recursion during canonicalization or valuation.
- **Dependency confusion** — an internal or expected package name is resolved
  from a public index that hosts a attacker-controlled same-named package,
  substituting a malicious dependency.

## Supply-chain threats

- Compromised or typosquatted dependencies.
- Tampered build environment or CI runner.
- Malicious pre-commit hook or Action.
- Substituted package index or proxy.

## Serialization threats

- Untrusted deserialization (pickle, `eval`, unsafe YAML/JSON object hooks).
- Schema version downgrade or confusion.
- Non-canonical or locale-dependent number/date formatting.

## Certificate-integrity threats

- Tampering with values after hashing.
- Confusing integrity hash with authentication.
- Accepting certificates with unknown schema versions.
- Forged or omitted validation outcomes.

## Numerical abuse and denial of service

- Non-finite or extreme values passed as inputs.
- Excessively large path counts, time steps, or recursion depth.
- Resource exhaustion through huge or deeply nested contracts.

## Plugin threats

- A plugin that silently overrides the deterministic core.
- A plugin that alters validation outcomes or contract semantics.
- Unsigned or unverified plugin metadata executed as trusted.

## Contribution threats

- Malicious code or documentation submitted via pull request.
- Secrets accidentally committed.
- Misleading claims about capabilities or validation.

## Mitigations

- Treat all external inputs as untrusted; validate and reject ambiguous input.
- Never use `eval`, `exec`, arbitrary dynamic imports, or executable user code.
- Canonicalize deterministically; reject `NaN`/`Infinity` in certificates.
- Use SHA-256 integrity hashes and clearly separate them from signatures.
- Enforce schema-version checks; reject unknown versions.
- Bound recursion, input size, numeric ranges, and engine resource usage.
- Detect cycles in contract graphs during construction and validation; reject
  cyclic definitions before canonicalization or valuation.
- Ensure canonicalization is injective by construction and covered by tests that
  prove distinct inputs map to distinct canonical forms and hashes.
- Keep runtime dependencies empty at the foundation; review any addition.
- Pin package indexes and lock constraints; restrict index URLs so an expected
  package name cannot be silently resolved from an untrusted public index
  (dependency confusion).
- Least-privilege CI (read-only contents, no OIDC publish, no secrets).
- Pin trusted actions to major versions; review pre-commit hooks.
- No hidden model or engine selection; record exactly what was used.
- Separation of concerns prevents silent responsibility absorption.
- Security policy and coordinated disclosure (see
  [SECURITY.md](../SECURITY.md)).

## Residual risks

- Zero-day vulnerabilities in the Python runtime or tooling.
- Compromise of trusted maintainer credentials.
- Errors in canonicalization or hashing logic not yet caught by tests.
- Social-engineering of reviewers or maintainers.

## Security assumptions

- Contract and market inputs are untrusted data, never code.
- The deterministic core is the authoritative, trusted component.
- Integrity hashes detect modification but do not authenticate provenance.
- Users operate within their own institutional controls and compliance.

## Incident response

Suspected vulnerabilities are reported privately per
[SECURITY.md](../SECURITY.md). Confirmed issues are fixed on a private track,
disclosed on a coordinated timeline, and recorded in the
[Changelog](../CHANGELOG.md).

See also [architecture.md](./architecture.md) and
[threat-model.md](./threat-model.md) cross-references in
[certificate-spec.md](./certificate-spec.md).
