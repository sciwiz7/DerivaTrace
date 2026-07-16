# Threat model

This document analyzes the security threats relevant to DerivaTrace. All
external inputs are treated as untrusted. Stage 1A introduces a concrete
contract algebra (see [contract-api.md](./contract-api.md) and
[ADR 0006](./adr/0006-stage-1-contract-algebra-and-runtime-type-system.md));
the additional threats and mitigations for that runtime type system are
documented below.

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

## Contract-algebra (Stage 1A) runtime type-system threats

Stage 1A ships a concrete contract algebra (`derivatrace.contracts`) with
frozen, slotted value and node objects and a whole-graph `validate_contract`
validator. The following threats are specific to that runtime type system.

- **Forged immutable object** — an attacker subclasses a value or node type and
  bypasses its frozen `__setattr__` (for example, using `object.__setattr__`)
  to set an inconsistent field, such as a `Payment.amount` whose stored `unit`
  disagrees with the amount's currency, or a `Currency._code` lowered to
  `"usd"`, a `money` unit stripped of its currency, an `ExactNumber._value`
  changed to `NaN`/`Infinity`/non-`Decimal`, or an `ObservationTime._value`
  changed to a naive `datetime`. Validation must re-derive dependent fields
  (e.g. `Unit`) itself rather than trust the stored attribute, and must
  re-validate the *stored internal state* of every value object it relies on,
  reading the raw private fields and re-deriving the construction invariants
  rather than re-running the constructors (which would silently normalize
  forged-but-valid state). Deterministic value objects additionally require the
  exact approved type, so a subclass of `Currency`, `Unit`, `ExactNumber`,
  `ObservableId`, `ObservationTime`, `SettlementTime`, or `ValidationLimits` is
  rejected by validation. The re-validation is applied **recursively to nested
  value objects**, so a forged inner value cannot be masked by an otherwise-valid
  outer container: a `money` unit's `Currency` is re-checked from its stored
  `_code` even when nested inside a `Number` inside a `Comparison` or `Payment`,
  and unrelated genuinely-valid currencies elsewhere in the graph do not suppress
  it. Two stored-state invariants are enforced explicitly:
  - **Stored UTC invariant** — `ObservationTime`/`SettlementTime` must be stored
    in canonical UTC (`tzinfo is UTC`), so a stored value shifted to a non-UTC
    offset (e.g. `+02:00`) is rejected even though it remains timezone-aware.
  - **Canonical zero invariant** — an `ExactNumber` must store the canonical
    zero `Decimal("0")`; forged `Decimal("-0")` or `Decimal("0.0")` forms are
    rejected because the stored representation must itself be canonical, not
    merely numerically zero.
- **Unsupported subclass injection** — a crafted contract uses a third-party
  subclass of the abstract `ScalarExpression`, `BooleanExpression`, or
  `Contract` bases that is not one of the supported concrete node types, hoping
  to bypass per-type validation. Validation runs an exact-type check at the
  start of every traversal frame and traverses in **post-order**, so an
  unsupported child subclass is rejected (and cannot execute overridden field
  access) before any parent reads its fields. Validation must reject any node
  that is not an exact supported type.
- **Deep recursion / resource exhaustion** — an attacker submits a contract
  whose AST depth or unique-node count exceeds configured limits, exhausting
  stack or memory. Validation must bound depth and total node count and fail
  fast.
- **Cyclic graph** — a self-referential or circular contract graph (a node
  referencing an ancestor) causes unbounded traversal. Validation must detect
  cycles during the iterative walk and reject them before any unbounded
  expansion.
- **Shared-node DAG confusion** — a contract that shares a sub-expression across
  branches must be traversed once per shared node without double-counting or
  re-expansion. Validation must track explored nodes and best-known depth.
- **Currency or unit mismatch** — an amount carries a currency that conflicts
  with its declared `Unit`, or operands of arithmetic combine incompatible
  units. Validation must enforce currency/unit consistency.
- **Extreme or non-exact numeric value** — a `Decimal` amount exceeds the
  allowed precision/exponent, or is constructed from a `float`/`bool`/`NaN`/
  `Infinity`. `ExactNumber` and validation must reject all such inputs.
- **Unicode identifier confusion** — an `ObservableId` uses look-alike
  characters to impersonate a different observable. Identifiers must be
  validated against an explicit allowed pattern and normalized form.
- **Naive or offset-less timestamp** — an observation or settlement time is
  supplied as a naive `datetime` (no `tzinfo`) or as a `datetime` whose
  `tzinfo` reports a `None` `utcoffset()`, which is not a concrete, comparable
  instant. Validation must reject both.
- **Misleading structural-validation claim** — a contract is presented as
  "fully validated" when only structural checks ran, or as canonical when it has
  not been canonicalized (canonicalization is not part of Stage 1A). Such claims
  must be avoided in API, docs, and tests.

Mitigations for the above are enforced by the validator and by the frozen,
slotted, `object.__setattr__`-guarded object design documented in
[ADR 0006](./adr/0006-stage-1-contract-algebra-and-runtime-type-system.md) and
exercised by `tests/contracts/test_supported_node_policy.py`,
`tests/contracts/test_validation.py`, and
`tests/contracts/test_value_object_invariants.py`.

## Canonicalization and payoff-graph (Stage 1B baseline) threats

Stage 1B introduces a canonical contract representation, a canonical identity,
and a canonical payoff graph. The canonical contract representation and identity
are implemented in the Stage 1B-R1 canonical runtime (`derivatrace.canonical`);
the payoff-graph compilation remains specified, not yet implemented (Stage 1B-R2;
see [canonicalization-spec.md](./canonicalization-spec.md),
[payoff-graph-spec.md](./payoff-graph-spec.md), and
[ADR 0007](./adr/0007-canonical-contract-identity-and-payoff-graph.md)). The
following threats are specific to that design and are mitigated by the
specification's rules and the canonical runtime's tests.

- **Canonicalization collision** — two distinct, non-equivalent contracts
  serialize to identical canonical bytes, yielding the same identity and
  defeating equality and integrity checks. The specification requires
  canonicalization to be injective by construction, exercised by tests that
  prove distinct inputs map to distinct identities.
- **Hash confusion / domain confusion** — a node id, payoff-graph id, or
  unrelated hash is mistaken for the contract identity, or a weak/preimage
  collision is exploited. Mitigated by fixed, versioned SHA-256 domain-
  separation tags whose preimage is
  `DOMAIN + 0x00 + "1.0.0" + 0x00 + payload_bytes`
  (`derivatrace.canonical.node`, `derivatrace.canonical.contract`,
  `derivatrace.payoffgraph.node`, `derivatrace.payoffgraph.graph`). The schema
  version participates directly in every identity, so a different version is a
  different identity.
- **Canonicalization collision** — two distinct canonical payloads hash to the
  same id. SHA-256 collision resistance is *assumed, not proven*; the
  specification does not rely on collisions being impossible. Canonicalization
  orders commutative operands by canonical id (tie-broken by payload bytes) and
  raises `canonicalization.collision` if the same id maps to different payload
  bytes, so differing nodes are never silently merged. Identical payloads may be
  shared; duplicate operands remain duplicate references.
- **Forged / non-canonical input** — a decoded canonical form is not itself
  canonical but is presented as an identity. Mitigated by rejecting any
  canonical form that is not self-canonical, and by never trusting a claimed
  identity.
- **Over-claiming equivalence** — canonical identity is presented as proof of
  economic equivalence. Mitigated explicitly: identity is structural under the
  approved laws only; the conservative principle forbids claiming complete
  mathematical or economic equivalence.
- **Schema downgrade / confusion** — a canonical form claims an unknown or
  older schema version. Mitigated by monotonic, explicit schema versions;
  consumers must reject unknown versions; the schema version participates in
  the identity.
- **Cycle / resource exhaustion during canonicalization** — a malformed or
  oversized graph exhausts resources. Mitigated by requiring `validate_contract`
  to pass first (cycle detection, depth/node limits) and by reusing the same
  `ValidationLimits` during canonicalization with iterative traversal.

These mitigations are recorded in the Stage 1B specification and enforced by the
Stage 1B-R1 canonical runtime and its tests; the payoff-graph runtime mitigations
land with Stage 1B-R2.

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
