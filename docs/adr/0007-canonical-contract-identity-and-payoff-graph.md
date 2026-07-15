# ADR 0007 — Canonical contract identity and payoff graph

- **Status:** Accepted (Stage 1B baseline)
- **Stage:** 1B (specification-only baseline; **not implemented** — implementation
  follows separate review)
- **Date:** 2026-07-15
- **Supersedes:** — (builds on ADR 0001–0006)
- **Superseded by:** —
- **Related issue:** Stage 1B: Canonical payoff graph and structural
  canonicalization (#3)

## Context

Stage 1A delivered an immutable, typed contract algebra and a structural
validator (ADR 0006). Its acceptance criteria require equivalent contracts to
produce identical canonical forms and identities, stable contract identity, and
a model-independent payoff graph. Stage 1B must therefore define *how* a
validated contract is normalized, serialized, and hashed into a deterministic
identity, and *how* it compiles into a canonical payoff graph.

The work is a **design baseline**: specification, test vectors, and this ADR.
No canonicalization, serialization, hashing, or payoff-graph code is introduced
in this stage's baseline. Stage 1C (validation levels, equivalence reporting)
remains outstanding and does not close issue #1.

## Decision

DerivaTrace canonicalizes a **validated** Stage 1A contract graph under a
**closed, explicitly enumerated set of structural laws**, serializes it to
**deterministic ASCII UTF-8 JSON** with sorted keys, and derives a
**SHA-256 canonical identity** with fixed domain separation. It compiles the
result into a **model-independent canonical payoff graph** (separate spec).

The governing principle is conservative: canonicalization applies **only**
approved structural laws and **must not** claim complete mathematical or
economic equivalence. Identity is *structural* under the approved laws.

### Canonical schema

- Name `derivatrace.contract.canonical`, version `1.0.0` (semver), carried as
  `canonical_schema_version`. The version **participates in the identity**.

### Canonical byte encoding

- Byte-exact: UTF-8, **no BOM**, **no trailing newline**, compact
  (`separators=(",", ":")`, no spaces), sorted keys by ASCII byte sequence
  (`sort_keys=True`), `ensure_ascii=True` (non-ASCII escaped as `\uXXXX`;
  solidus `/` not escaped). **No JSON floating-point values** (all user
  quantities are strings/structured objects). No locale- or platform-dependent
  formatting. Full rules in `canonicalization-spec.md` §3. Aligned with ADR 0002
  and `certificate-spec.md`.

### Value encoding (key rulings)

- **Exact `Decimal`:** value-normalized tuple form
  `{sign, digits, exponent}` with trailing zeros stripped; zero forced to
  `{0,"0",0}`. Two numerically equal `Decimal`s encode identically
  (`"2"` == `"2.0"`).
- **Canonical zero:** `Decimal("0")`; forged `-0`/`0.0`/`0E1` rejected.
- **Timestamps:** RFC 3339 UTC with full microsecond precision and `Z` suffix;
  stored UTC from Stage 1A preserved exactly.
- **Currency:** three-letter code string. **Unit:** `{kind}` or
  `{kind, currency}`. **ObservableId:** `{field, identifier, namespace}`.
  **Enums** (UnitKind, ComparisonOperator): stable string value, never Python
  member name/`repr`.

### Node commutativity (decided per documented semantics)

Three mutually exclusive classes — no node is treated as more than one, and no
"flattening" language is applied to a non-collection node.

- **Commutative associative collection (reorder + flatten; duplicates
  preserved):** `Add`, `Maximum`, `Minimum`, `AllOf`, `AnyOf`.
- **Commutative binary (reorder the two operands by canonical id; NOT
  flattened):** `Multiply` only. It is binary; operands are ordered by canonical
  node id (tie-broken by payload bytes), never associated into an n-ary node.
- **Author-order-preserving (NO reorder, NO flatten):** `Subtract`, `Divide`,
  `Comparison`, `ConditionalValue`, `Scale`, `Payment`, `ConditionalContract`,
  **`Both`**, `Negate`, `Not`, and all leaves (`Number`, `BooleanConstant`,
  `Observable`, `Zero`).

`Both` is deliberately **excluded** from the commutative set even though
`AllOf`/`AnyOf` are included: `Both` combines *contracts* and Stage 1A
explicitly preserves author order and performs no normalization, whereas
`AllOf`/`AnyOf` combine *boolean expressions* whose documented semantics deny
evaluation and short-circuit, removing positional meaning. The distinction is
grounded in documented node semantics, not mathematical convenience.

### Associative flattening

- Flatten nested same-type `Add`/`Maximum`/`Minimum`/`AllOf`/`AnyOf` into one
  n-ary node. `Multiply` is binary (no flattening). `Both` and all
  author-order-preserving nodes are **not** flattened.

### Duplicate-operand policy

- Operand **multiplicity preserved**; dedup is forbidden (it would change
  observable count and value).

### Safe literal-only simplifications (approved)

- Exact constant folding of pure-`Number` arithmetic (`Add`, `Subtract`,
  `Multiply`, `Negate`, `Maximum`, `Minimum`) using integer-coefficient tuple
  arithmetic — never `Decimal` under ambient context, never `float`, never
  rounding; retained only when the exact result stays within the §4.4 bounds.
  Pure-`BooleanConstant` boolean folding (`AllOf`/`AnyOf`/`Not`); literal
  `Comparison` → `BooleanConstant`; literal-condition selection in
  `ConditionalValue`/`ConditionalContract`. **`Divide` folding is removed from
  schema 1.0.0** (it cannot be made fully normative and simple for all
  inputs); `Divide` is carried through unchanged and compiles to `PGDivide`
  with preserved numerator/denominator references. All exact, no market data, no
  model.

### Forbidden transformations

- Reordering author-order-preserving nodes; flattening `Both`/others listed;
  dedup; distribution/factorization/cancellation; any market/model/engine-
  dependent rewrite; observable evaluation; asserting economic equivalence;
  implicit unit/currency change; schema downgrade.

### DAG sharing and node identity

- Canonicalization yields a **DAG**; identical subgraphs share one
  content-derived node id. Identity is **content-derived, not object-identity
  derived**, so shared and inlined copies coincide.

### Deterministic identifiers and hashing

Byte-exact preimage framing (full rules in `canonicalization-spec.md` §8 and
`payoff-graph-spec.md` §4.4):

```text
<DOMAIN> + 0x00 + "1.0.0" + 0x00 + <CANONICAL_PAYLOAD_BYTES>
```

- Node id: `SHA-256( b"derivatrace.canonical.node" + b"\x00" + b"1.0.0" +
  b"\x00" + payload_bytes )` → bare 64-hex, referenced inside documents.
- Contract identity: `SHA-256( b"derivatrace.canonical.contract" + b"\x00" +
  b"1.0.0" + b"\x00" + canonical_contract_document_bytes )` →
  `canonical:sha256:<hex>`.
- Payoff-graph node id: `SHA-256( b"derivatrace.payoffgraph.node" + ... )` →
  bare 64-hex.
- Payoff-graph identity: `SHA-256( b"derivatrace.payoffgraph.graph" + ... )`
  over the structural document projection → `payoffgraph:sha256:<hex>`.

The schema version is in the preimage framing, so it participates **directly**
in every identity. Node/PG-node ids hash over their **payload**; contract/PG
identities hash over the **complete (or structural-projection) document**. Output
is lowercase 64-hex. Domain tags are fixed schema constants; changing one (or the
version) requires a version bump.

### Hash collisions and sort order

- Commutative operands ordered by canonical id, tie-broken by canonical payload
  bytes.
- If the same id maps to **different** payload bytes, canonicalization raises
  `canonicalization.collision` (never silently merges).
- Identical payloads/identities may be shared; duplicate operands remain
  duplicate references; collision handling never merges different nodes.

### Payoff graph

- A separate, model-independent compiled DAG (see `payoff-graph-spec.md`) whose
  combination node `PGCombine` preserves author order, inheriting the `Both`
  policy. `Divide` compiles **directly** to `PGDivide` (numerator/denominator
  references preserved; no reciprocal rewrite, no float). Compilation is
  specification-only in this baseline.

### Error taxonomy

- `CanonicalizationError` base with codes `canonicalization.error`,
  `.input`, `.input.not_validated`, `.cycle`, `.complexity`, `.encoding`,
  mirroring the Stage 1A taxonomy and carrying a structural `.path`.

### Migration and compatibility

- Explicit, monotonic schema versions; any canonicalization-rule change bumps
  the version; consumers reject unknown versions; old identities remain
  verifiable under their recorded version; no silent downgrade.

## Consequences

- Equivalent contracts under the approved laws get identical, stable identities;
  non-equivalent contracts do not collapse through undocumented transformations.
- The conservative, enumerated-law approach limits the surface area of
  canonicalization and makes every rewrite auditable.
- `Both` order is preserved, so author-distinct contract combinations keep
  distinct identities (a deliberate, documented trade-off against maximal
  collapsing).
- Decimal spelling (`"2"` vs `"2.0"`) does not affect identity, by explicit
  value-normalization.
- Canonical identity is an integrity/structural fingerprint, **not** a proof of
  economic equivalence and **not** a digital signature.

## Alternatives considered

- **Reorder everything (treat `Both` as commutative):** rejected — contradicts
  documented Stage 1A author-order preservation and would assert an
  equivalence the project declines to make.
- **Preserve all author order, no commutative reordering at all:** rejected —
  it would make clearly equivalent scalar sums (`Add(a,b)` vs `Add(b,a)`) get
  different identities, violating the Stage 1B acceptance criterion, and
  contradicts the documented normalization precedent.
- **Float-based or locale-dependent number formatting:** rejected (ADR 0002,
  ADR 0004).
- **Dedup duplicate operands:** rejected — changes observable semantics/value.
- **Hash without domain separation:** rejected — risks cross-context confusion.
- **Schema version not in identity:** rejected — breaks verifiability across
  canonicalization-rule changes.
- **Claiming economic equivalence from canonical identity:** rejected as
  misleading under the project's evidence principle.

## Security considerations

- Canonicalization is injective by construction; distinct structures get
  distinct identities (mitigates the canonicalization-collision threat in
  `threat-model.md`).
- Domain separation prevents node-id / contract-id / payoff-id confusion.
- Forged or non-canonical input is rejected; identity is not trusted from a
  claimant.
- Cycle/DoS protections and the untrusted-input trust boundary from Stage 1A
  carry over.
- Canonicalization performs no evaluation and never executes contract content.

## Follow-up work

- Stage 1B implementation (canonicalization, serialization, hashing, payoff-
  graph compilation) under this baseline.
- Stage 1C: graded validation levels, equivalence reporting, structural
  diffing.
