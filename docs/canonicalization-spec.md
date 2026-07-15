# Canonicalization specification (Stage 1B baseline)

- **Status:** Specification only. **Not implemented.**
- **Stage:** 1B (architecture baseline; implementation follows separate review).
- **Schema name:** `derivatrace.contract.canonical`.
- **Schema version:** `1.0.0` (semantic version; participates in identity, §9).
- **Depends on:** Stage 1A (`derivatrace.contracts`) and ADR 0001–0006.

This document defines the **canonical contract representation** for DerivaTrace:
how a validated Stage 1A contract graph is normalized into a single stable
structure, how that structure is serialized to deterministic bytes, and how a
deterministic **canonical contract identity** is derived. It is the design
baseline for Stage 1B. No code, module, function, or class described here
exists in the package yet.

> **Conservative principle (binding).** Canonicalization may apply **only**
> explicitly approved structural laws documented in this file. It must **not**
> claim complete mathematical or economic equivalence between contracts. The
> canonical identity is a *structural* identity under the approved laws, not a
> proof of economic parity. See §12 (Claim boundaries).

## 1. Scope and hard boundaries

Canonicalization operates **only** on an already-validated Stage 1A contract
graph. It performs no financial calculation and resolves no market data.

Explicitly **out of scope** for this specification (and for Stage 1B
implementation):

- Pricing, valuation, Greeks, any financial calculation.
- Model or numerical-engine selection or execution.
- Market-data retrieval or evaluation of observables.
- Monte Carlo, trees, PDEs, calibration, hedging.
- Evidence-certificate generation.
- Arbitrary executable user code.
- Float-based contractual representation (exact `Decimal` only).
- Any undocumented semantic rewrite.
- Runtime dependencies beyond those already approved (none).

## 2. Canonicalization pipeline

1. **Require validation.** The input graph must pass `validate_contract`
   (Stage 1A) first. A graph that is not validated, or that fails validation,
   is rejected with `canonicalization.input.not_validated`.
2. **Reject cycles / bound complexity.** Reuse the Stage 1A cycle detection and
   `ValidationLimits` (`max_depth=64`, `max_unique_nodes=4096`). Exceeded limits
   raise `canonicalization.complexity`; a residual cycle raises
   `canonicalization.cycle`. Cycles are rejected **before** any canonical output
   is produced (§7).
3. **Iterative traversal.** Walk the graph with an explicit stack (never
   recursion) so deep structures cannot exhaust the call stack.
4. **Per-node normalization.** Apply the node-specific laws in §5. Children are
   canonicalized **before** their parent; literal folding (§4, §5.3) is applied
   **after** child canonicalization.
5. **DAG shaping.** Share identical canonical subgraphs by content-derived id
   (§7).
6. **Serialize.** Emit deterministic UTF-8 bytes per §3.
7. **Hash.** Derive the canonical identity with SHA-256 and explicit,
   versioned domain framing (§8).

## 3. Canonical byte encoding (byte-exact)

Every canonical artifact (node payload, contract document, payoff-graph node,
payoff graph) is serialized to a single, unambiguous UTF-8 byte sequence. There
is **exactly one** canonical byte string for a given structure; any other
serialization is a *display* form and must never be hashed or used for identity.

The canonical bytes are produced by:

```python
json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
```

encoded to UTF-8 with **no BOM** and **no trailing newline**. The exact policy:

- **UTF-8, no BOM, no trailing newline.** The serializer emits bytes
  `0x7B ... 0x7D` with nothing before or after.
- **No insignificant whitespace.** Separators are the exact two-character tokens
  `("," , ":")` — a comma between array elements / object members and a colon
  between an object key and its value, with **no spaces** around them. No
  indentation, no newlines, no pretty printing.
- **Sorted object keys.** Object keys are ordered lexicographically by their
  **ASCII byte sequence** (ascending). Because the input is ASCII by
  construction (§3.1), this equals ordering by Unicode code point. The
  key set and values determine the bytes; key *ordering* is therefore fixed and
  not a freedom.
- **Arrays preserve order.** Array *elements* are **not** reordered by
  canonicalization; only object *keys* are sorted. Operand arrays already carry
  their canonical (sorted or author-order) element sequence from §5/§7.
- **Lowercase JSON literals only.** `true`, `false`, `null`. Never `True`,
  `False`, `None`, `NaN`, `Infinity`, or `Infinity`.
- **No JSON floating-point values.** A canonical artifact contains **no** JSON
  number token with a decimal point, exponent, or negative sign
  (`-?\d+(\.\d+)?([eE][+-]?\d+)?`). The only JSON integers that may appear are
  `Decimal.exponent` fields (which are exact integers) and integer literals in
  payloads. All user quantities are encoded as strings or structured objects
  (§4), never as a raw JSON number.
- **No locale-sensitive or platform-dependent formatting.** `str()`,
  `locale`, thousands separators, and platform `Decimal` context never affect
  output.
- **Exact escaping rules.**
  - `"` → `\"`, `\` → `\\`.
  - Control characters U+0000–U+001F are escaped as `\u00XX` (except that
    `\n`, `\t`, `\r` may use the short forms; all are fixed).
  - **Solidus `/` is NOT escaped.** It is emitted literally. (This is a fixed
    rule so the byte sequence is reproducible; `json.dumps` with default settings
    does not escape `/`.)
  - **Non-ASCII is not permitted in raw form.** `ensure_ascii=True` encodes any
    non-ASCII character as `\uXXXX`. All accepted Stage 1A identifiers,
    currencies, observable ids, units, and timestamps are ASCII by construction;
    the schema nonetheless **requires** that any non-ASCII character be escaped
    as `\uXXXX` and **forbids** raw UTF-8 multibyte sequences in canonical
    bytes. A canonical artifact is therefore pure ASCII (bytes 0x09, 0x0A,
    0x0D, 0x20–0x7E plus the fixed ASCII escape sequences).

### 3.1 Canonical document shapes

The top-level canonical **contract document** is a single JSON object with
exactly these four fields (field names fixed):

| Field | Type | Meaning |
|-------|------|---------|
| `schema_name` | string | `"derivatrace.contract.canonical"` |
| `schema_version` | string | `"1.0.0"` (semver) |
| `root` | string | canonical node id (bare 64-hex) of the root node |
| `nodes` | object | node table: map `node id` → node record |

A **node record** is a JSON object with exactly these fields:

| Field | Type | Meaning |
|-------|------|---------|
| `id` | string | the node's canonical node id (bare 64-hex) |
| `payload` | object | the node's canonical payload (§5.4) |

The **root reference** is the `root` field: the canonical node id of the
root node. The **schema name** and **schema version** are the `schema_name`
and `schema_version` fields; both participate in the contract identity (§8, §9).

> **Identity is not stored inside the document.** The contract identity is
> derived from the document bytes (§8); it is never embedded in the document, so
> there is no circularity. A `canonical:sha256:<hex>` value may be conveyed
> *alongside* the document as external metadata, but it is not part of the
> hashed bytes.

## 4. Value encoding rules

### 4.1 Exact `Decimal` encoding (tuple semantics)

`ExactNumber` wraps `decimal.Decimal`. The canonical encoding is a
**value-normalized tuple form**, chosen so that two numerically equal `Decimal`
values always produce identical bytes:

```json
{ "sign": 0, "digits": "314", "exponent": -2 }
```

This encoding is defined by a **context-independent algorithm using the
`Decimal` tuple**, explicitly **not** `Decimal.normalize()` and explicitly
**not** the ambient `decimal` context. The algorithm (§4.4) operates on the
tuple `(sign, digits, exponent)` only.

### 4.2 Canonical zero handling

Zero is the canonical `Decimal("0")` with `as_tuple() == (0, (0,), 0)`. The
Stage 1A canonical-zero invariant already enforces this in stored state, and
canonicalization re-asserts it. Forged forms (`Decimal("-0")`,
`Decimal("0.0")`, `Decimal("0E+1")`) are rejected before encoding (they are
non-canonical stored state). Negative zero is normalized to zero (non-negative
sign).

### 4.3 UTC timestamp encoding and precision

`ObservationTime` and `SettlementTime` are stored in canonical UTC by Stage 1A.
Encode as **RFC 3339** with **full microsecond precision** and a `Z` suffix:

```text
2030-01-01T00:00:00.000000Z
```

- The complete stored precision is preserved (no truncation to seconds).
- Two timestamps representing the same instant in different offsets are already
  normalized to identical UTC by Stage 1A, so they encode identically.
- Nanosecond-or-finer precision and leap-second handling are out of scope;
  microsecond precision matches the Stage 1A storage guarantee.
- The timestamp is encoded as a JSON **string**; it is never a JSON number.

### 4.4 Decimal-normalization algorithm (normative)

Input: a finite `Decimal` `d` that has already passed Stage 1A validation
(zero, if present, is stored as canonical `Decimal("0")`; no `NaN`/`Infinity`
can appear).

1. `t = d.as_tuple()` → `(sign, digits, exponent)` where `sign ∈ {0, 1}`,
   `digits` is a tuple of integers `0..9`, `exponent` is an `int`.
2. **Strip trailing coefficient zeros.** While `len(digits) > 1` and
   `digits[-1] == 0`: drop the final digit and increment `exponent` by 1.
   (This removes insignificant trailing zeros without changing value.)
3. **Remove leading coefficient zeros.** While `len(digits) > 1` and
   `digits[0] == 0`: drop the leading digit (do **not** change `exponent`).
   (Defensive; Stage 1A already rejects leading-zero coefficients.)
4. **Canonical zero.** If the value is zero — i.e. after step 2 `digits == (0,)`
   (the exponent is then irrelevant) — force `sign = 0`, `digits = (0,)`,
   `exponent = 0`.
5. **Preserve negative sign for non-zero values.** For a non-zero value, `sign`
   is taken from `t.sign` unchanged (so `-3` keeps `sign = 1`).
6. Encode:
   - `sign` → JSON integer `0` (non-negative) or `1` (negative).
   - `digits` → the concatenated ASCII digit string `"".join(str(d) for d in digits)`.
   - `exponent` → the JSON integer `exponent`.

**Bounds and failure behaviour.** Let `MAX_COEFF_DIGITS = 50` and
`EXP_MIN = -(2**31)`, `EXP_MAX = 2**31 - 1`. If `len(digits) > MAX_COEFF_DIGITS`
or `exponent` lies outside `[EXP_MIN, EXP_MAX]` at any point, canonicalization
raises `canonicalization.encoding` (a non-canonical or out-of-range value). No
rounding is ever performed; results that would require rounding are rejected
rather than approximated.

**Worked examples.**

| Input `Decimal` | Tuple after step 2 | Encoded |
|-----------------|--------------------|----------|
| `Decimal("2")` | `(0, (2,), 0)` | `{"sign":0,"digits":"2","exponent":0}` |
| `Decimal("2.0")` | `(0, (2,), 0)` | `{"sign":0,"digits":"2","exponent":0}` |
| `Decimal("2.00")` | `(0, (2,), 0)` | `{"sign":0,"digits":"2","exponent":0}` |
| `Decimal("10e-1")` | `(0, (1,), 0)` | `{"sign":0,"digits":"1","exponent":0}` |
| `Decimal("1")` | `(0, (1,), 0)` | `{"sign":0,"digits":"1","exponent":0}` |
| `Decimal("1.0")` | `(0, (1,), 0)` | `{"sign":0,"digits":"1","exponent":0}` |
| `Decimal("1.00")` | `(0, (1,), 0)` | `{"sign":0,"digits":"1","exponent":0}` |
| `Decimal("0")` | `(0, (0,), 0)` → zero rule | `{"sign":0,"digits":"0","exponent":0}` |
| `Decimal("-0")` | value zero → zero rule | `{"sign":0,"digits":"0","exponent":0}` |
| `Decimal("0.0")` | `(0,(0,),0)` → zero rule | `{"sign":0,"digits":"0","exponent":0}` |
| `Decimal("100")` | `(0, (1,), 2)` | `{"sign":0,"digits":"1","exponent":2}` |
| `Decimal("1E+2")` | `(0, (1,), 2)` | `{"sign":0,"digits":"1","exponent":2}` |
| `Decimal("-3")` | `(1, (3,), 0)` | `{"sign":1,"digits":"3","exponent":0}` |
| `Decimal("0.0314")` | `(0, (3,1,4), -4)` | `{"sign":0,"digits":"314","exponent":-4}` |

`Decimal("1")`, `Decimal("1.0")`, `Decimal("1.00")`, and `Decimal("10e-1")`
all encode identically — correct, because they are the same contractual amount.

### 4.5 Currency, Unit, ObservableId, and enum encoding

- **Currency** — the three-letter code string, e.g. `"USD"`. Syntax only;
  ISO 4217 registration is not implied.
- **Unit** — object: `{"kind":"scalar"}` or
  `{"kind":"money","currency":"USD"}`.
- **UnitKind** — its stable string value (`"scalar"` / `"money"`), never the
  Python member name or `repr`.
- **ObservableId** — `{"field":..., "identifier":..., "namespace":...}`
  (sorted keys). The three parts are the validated ASCII grammar from Stage 1A.
- **ComparisonOperator** — its stable **symbol** string
  (`"<"`, `"<="`, `"=="`, `"!="`, `">="`, `">"`), chosen for compactness and
  fixed meaning. The mapping symbol↔member is part of the schema and must not
  change without a version bump.
- **BooleanConstant** — JSON `true` / `false`.
- All enums are encoded by their **stable string value**, never by Python
  member name, ordinal, or `repr`.

## 5. Node-by-node normalization laws

Every Stage 1A node belongs to exactly one of three classes. The classification
is the central design decision of Stage 1B and is derived from the *documented
DerivaTrace semantics*, not from mathematical convenience. **No node is ever
treated as more than one class, and no "flattening" language is applied to any
non-collection node.**

### 5.1 The three node classes

**(A) Commutative associative collection nodes.** These are n-ary and their
documented Stage 1A semantics assign no meaning to operand position (homogeneous
units, no evaluation, no short-circuit, no side effects). They are normalized as
**commutative, associative multisets**:

- `Add`, `Maximum`, `Minimum` (scalar collections)
- `AllOf`, `AnyOf` (boolean collections)

Normalization:
1. **Associative flattening:** a nested same-type collection node is merged into
   the parent. `Add(Add(a, b), c)` → `Add(a, b, c)`. Applies **only** to the
   five nodes listed above.
2. **Commutative ordering:** after flattening, operands are sorted by their
   deterministic canonical node id (§7/§8), with canonical payload bytes as a
   tie-breaker (§6). This yields a single canonical order regardless of author
   order.
3. **Duplicate-operand policy:** operand **multiplicity is preserved** (§7).

**(B) Commutative binary nodes.** Exactly two operands; operand position is not
load-bearing, but the node is **not** associative/flattened in schema 1.0.0.

- `Multiply`

`Multiply` is **binary** (it always has exactly two operands). Its two operands
are **reordered deterministically** — ordered by canonical node id, tie-broken
by canonical payload bytes (§6) — because the valid Stage 1A semantics permit
`scalar×scalar`, `scalar×money`, and `money×scalar`, and the unit product is
symmetric. **Nested `Multiply` nodes are NOT associatively flattened** in schema
1.0.0. A valid graph can never contain `money×money`. The result unit remains
determined by the Stage 1A unit rules.

**(C) Author-order-preserving nodes.** For these nodes, operand position is
treated as load-bearing (or its reordering would contradict documented Stage 1A
behaviour or assert an equivalence the project has chosen not to make).
Canonicalization **preserves author order exactly and performs no flattening and
no reordering**:

- `Subtract` (`minuend`, `subtrahend` — ordered difference; `a - b != b - a`)
- `Divide` (`numerator`, `denominator` — ordered quotient; denominator must be
  dimensionless per Stage 1A; see §5.3 for the v1 non-folding decision)
- `Comparison` (`left`, `right`, `operator` — ordered; operator is directional)
- `ConditionalValue` (`condition`, `true_value`, `false_value` — branches
  distinct; selection is positional)
- `Scale` (`factor`, `contract` — factor applies to contract; positional)
- `Payment` (`amount`, `currency`, `settlement_time` — dated cash flow; all
  fields positional and distinct)
- `ConditionalContract` (`condition`, `true_contract`, `false_contract` —
  branches distinct; positional)
- `Both` (`operands` tuple — Stage 1A explicitly **preserves author order** and
  performs **no flattening**; contract-combination ordering is not asserted
  insignificant. Reordering would collapse author-distinct contracts and is
  **forbidden**.)
- `Negate` (`operand` — single operand)
- `Not` (`operand` — single operand)
- `Number`, `BooleanConstant`, `Observable`, `Zero` — leaves; nothing to reorder
  or flatten.

### 5.2 Why `Both` is excluded while `AllOf`/`AnyOf` are included

`Both` combines *contracts* (obligations) and Stage 1A explicitly preserves
author order and performs no normalization; `AllOf`/`AnyOf` combine *boolean
expressions* whose documented semantics explicitly deny evaluation and
short-circuit, removing any positional meaning. The distinction is grounded in
the documented node semantics, not in mathematical taste.

### 5.3 Safe literal-only simplifications (approved, exact, no market/model)

These are the **only** approved simplifications beyond structural reordering and
flattening. Each requires that **every** operand involved be a literal
(`Number` / `BooleanConstant`); no `Observable`, market data, model, or engine
may be involved. Folding is applied **after** child canonicalization (§2 step 4),
so all operands are already in canonical form.

Simplification occurs **after** child canonicalization and **before** the parent
node's own identity is computed.

**Exact arithmetic policy (integer-coefficient semantics).** For the numeric
operations below, folding computes the exact result using integer coefficient and
exponent arithmetic on the canonical `Decimal` tuple form (§4.4) — never
`Decimal` addition/multiplication under the ambient context, never `float`, never
rounding. The result is re-normalized by §4.4. If the exact result would exceed
the §4.4 bounds (`MAX_COEFF_DIGITS` / exponent range), the fold is **not**
applied and the node is retained unchanged (raising `canonicalization.encoding`
only if the *inputs* themselves were already out of range).

- **`Add`** — sum of literal `Number` operands → single `Number`. Align
  exponents, add coefficients exactly, re-normalize.
- **`Subtract`** — `a - b` of literal `Number` operands → single `Number`.
- **`Multiply`** — `a * b` of literal `Number` operands → single `Number`
  (multiply coefficients, add exponents, XOR signs, re-normalize).
- **`Negate`** — `Negate(Number)` → `Number` with flipped sign.
- **`Maximum` / `Minimum`** — pick the extremal literal `Number` by exact
  integer-coefficient comparison (sign first, then magnitude).
- **`Comparison`** — compare two literal `Number` operands exactly →
  `BooleanConstant` of the comparison result.
- **`ConditionalValue`** — if `condition` is a literal `BooleanConstant`,
  reduce to the selected branch (`true_value` or `false_value`) and continue
  canonicalizing that branch.
- **`AllOf` / `AnyOf` / `Not`** — boolean constant folding over literal
  `BooleanConstant` operands: `AllOf` of all-true → `BooleanConstant(true)`;
  `AnyOf` of all-false → `BooleanConstant(false)`; `Not(const)` → `const`.

**Divide-folding policy (schema 1.0.0): removed.** `Divide` folding is
**excluded** from schema 1.0.0. `Divide` is an author-order-preserving node
and is only structurally normalized (canonicalize `numerator` and
`denominator`, preserve order). Rationale: an exact reduced rational has a
terminating base-10 representation only when its denominator (in lowest terms)
has no prime factors other than 2 or 5; folding otherwise requires either
rounding or a non-terminating decimal, neither of which is acceptable under the
conservative, fully-normative v1 policy. Because this rule could not be made
completely normative and simple for all inputs, **Divide folding is deferred**;
`Divide` is carried through unchanged. (The Stage 1A literal-zero-denominator
and dimensionless-denominator rules still apply at validation, so the
denominator is a non-zero dimensionless literal when literals are present.) This
also fixes the payoff-graph mapping (§8 of `payoff-graph-spec.md`): `Divide`
compiles directly to `PGDivide` with numerator/denominator references, never to
a reciprocal.

All folding uses exact `Decimal` / boolean logic; no approximation, no float.
These rules are explicitly approved; everything else is forbidden (§6).

### 5.4 Canonical payload schema (every Stage 1A public node)

Every node's **canonical payload** is a JSON object. The fixed field `type`
carries the node name; remaining fields are listed below with their exact names
and types. Operand references are **canonical node ids** (bare 64-hex strings)
produced by §8. The payload is serialized with the §3 rules (sorted keys,
compact). Arrays already carry their canonical element order.

**Scalar nodes**

| Node | Canonical payload object |
|------|--------------------------|
| `Number` | `{"type":"Number","value":<dec>, "unit":<unit>}` |
| `Observable` | `{"type":"Observable","observable_id":<oid>,"observation_time":"<rfc3339z>","unit":<unit>}` |
| `Add` | `{"type":"Add","operands":[<id>, ...]}` (≥2, flattened, sorted) |
| `Subtract` | `{"type":"Subtract","minuend":<id>,"subtrahend":<id>}` |
| `Multiply` | `{"type":"Multiply","left":<id>,"right":<id>}` (binary, sorted) |
| `Divide` | `{"type":"Divide","numerator":<id>,"denominator":<id>}` |
| `Negate` | `{"type":"Negate","operand":<id>}` |
| `Maximum` | `{"type":"Maximum","operands":[<id>, ...]}` (≥2, flattened, sorted) |
| `Minimum` | `{"type":"Minimum","operands":[<id>, ...]}` (≥2, flattened, sorted) |
| `ConditionalValue` | `{"type":"ConditionalValue","condition":<id>,"true_value":<id>,"false_value":<id>}` |

**Boolean nodes**

| Node | Canonical payload object |
|------|--------------------------|
| `BooleanConstant` | `{"type":"BooleanConstant","value":true|false}` |
| `Comparison` | `{"type":"Comparison","left":<id>,"right":<id>,"operator":"<"|"<="|"=="|"!="|">="|">"}` |
| `AllOf` | `{"type":"AllOf","operands":[<id>, ...]}` (≥2, flattened, sorted) |
| `AnyOf` | `{"type":"AnyOf","operands":[<id>, ...]}` (≥2, flattened, sorted) |
| `Not` | `{"type":"Not","operand":<id>}` |

**Contract nodes**

| Node | Canonical payload object |
|------|--------------------------|
| `Zero` | `{"type":"Zero"}` |
| `Payment` | `{"type":"Payment","amount":<id>,"currency":"USD","settlement_time":"<rfc3339z>"}` |
| `Both` | `{"type":"Both","operands":[<id>, ...]}` (author order preserved) |
| `Scale` | `{"type":"Scale","factor":<id>,"contract":<id>}` |
| `ConditionalContract` | `{"type":"ConditionalContract","condition":<id>,"true_contract":<id>,"false_contract":<id>}` |

Where `<dec>` = `{"sign":0|1,"digits":"...","exponent":int}`, `<unit>` =
`{"kind":"scalar"}` or `{"kind":"money","currency":"USD"}`, `<oid>` =
`{"field":...,"identifier":...,"namespace":...}`, and `<id>` is a canonical
node id (bare 64-hex). No field name or representation is left to implementation
choice.

## 6. Transformations explicitly forbidden

- Reordering operands of any **author-order-preserving** node (§5.1 class C).
- Flattening `Both`, `Subtract`, `Divide`, `Comparison`, `Scale`, `Payment`,
  `ConditionalContract`, `ConditionalValue`, `Negate`, `Not`, or any leaf.
- Associative flattening of `Multiply` (always binary).
- Removing duplicate operands (dedup) from any node.
- Reordering the two operands of `Multiply` arbitrarily — they are reordered
  **only** by the deterministic canonical-id / payload-bytes rule (§6, §7).
- Distribution (`a * (b + c)` → `a*b + a*c`), factorization, or cancellation.
- Any rewriting that depends on market data, a model, a numerical engine, or
  observable evaluation.
- Comparing or resolving `ObservableId` against market values.
- **Divide folding** (explicitly removed for schema 1.0.0, §5.3).
- Asserting or implying **economic equivalence**: canonical identity is
  structural only (§12).
- Implicitly changing units or currencies.
- Schema-version downgrade or silent migration.
- Any semantic rewrite not listed in §5.

## 7. DAG sharing and node-identity policy

Normatively:

- **Python object identity is never part of canonical identity.** Identity
  depends only on canonical structural content. Two graphs that share a
  subexpression, or one graph that inlines a copy of a subexpression, yield the
  **same** canonical node and the same overall identity.
- A shared subtree and two independently allocated but structurally identical
  subtrees produce the **same** canonical contract identity.
- Canonical node records are **content-addressed**: identical structural nodes
  appear **once** in the node table.
- Operand arrays **retain duplicate references**, so deduplication of node
  records does **not** deduplicate contract operands (multiplicity is
  preserved, §5.1).
- Node-table ordering is **deterministic and independent of traversal order**:
  records are ordered by ascending canonical node id, with canonical payload
  bytes as the collision tie-breaker (§8).
- **Cycles are rejected before canonical output is produced** (§2 step 2).

## 8. Deterministic graph-node identifiers and hashing

Identities are SHA-256 digests over an **explicit byte-exact preimage** with
domain separation. The preimage is:

```text
<DOMAIN> + 0x00 + <SCHEMA_VERSION> + 0x00 + <CANONICAL_PAYLOAD_BYTES>
```

where:

- `<DOMAIN>` is a fixed ASCII domain tag (no NUL inside it),
- `0x00` is a single NUL byte separating the fixed parts,
- `<SCHEMA_VERSION>` is the literal ASCII string `"1.0.0"` (so the schema
  version participates **directly** in every identity, not only via the embedded
  document field),
- `<CANONICAL_PAYLOAD_BYTES>` is the §3 canonical JSON bytes of the hashed
  structure.

**Domain tags and what each hashes over**

| Identity | Domain tag (ASCII) | Hashed over |
|----------|--------------------|-------------|
| Canonical node id | `derivatrace.canonical.node` | canonical JSON bytes of the **node payload** (§5.4) |
| Canonical contract id | `derivatrace.canonical.contract` | canonical JSON bytes of the **complete contract document** (§3.1) |
| Payoff-graph node id | `derivatrace.payoffgraph.node` | canonical JSON bytes of the **payoff node payload** |
| Payoff-graph id | `derivatrace.payoffgraph.graph` | canonical JSON bytes of the **payoff-graph document** (structural projection; §9 of `payoff-graph-spec.md`) |

**Output format.** SHA-256 produces 32 bytes, rendered as a **lowercase
64-character hexadecimal string**.

- **Node ids** (canonical and payoff) are stored and referenced as the bare
  64-hex string (e.g. inside `operands` arrays and as document `root`).
- The **canonical contract identity** is presented with the prefix
  `canonical:sha256:<hex>`.
- The **payoff-graph identity** is presented with the prefix
  `payoffgraph:sha256:<hex>`.

**Root and whole-graph derivation.**

- The **root node identity** is the canonical node id of the document's `root`
  node.
- The **canonical contract identity** is the contract-document preimage hash
  (over the complete document, which embeds the `root` reference and node
  table). It is **not** merely the root node's id.
- The **payoff-graph identity** is the payoff-graph-document preimage hash
  (§9 of `payoff-graph-spec.md`).

Domain tags are fixed constants belonging to the schema; changing any tag (or the
schema version) requires a schema-version bump. The single NUL separators prevent
prefix confusion between the domain, the version, and the payload.

## 9. Schema version and participation in identity

- **Schema name:** `derivatrace.contract.canonical`.
- **Version format:** semantic version string, `"1.0.0"` (MAJOR.MINOR.PATCH),
  carried in the document field `schema_version`.
- **Participation in identity:** the schema version is part of the preimage
  framing (`<SCHEMA_VERSION>` in §8) **and** appears in the document; two
  structurally identical contracts under different schema versions produce
  **different** identities.
- **Migration and compatibility policy:**
  - Schema versions are explicit and monotonic.
  - Any change to a canonicalization rule (operand ordering, flattening,
    decimal form, timestamp precision, enum encoding, hash domain tags, node
    classification) requires a version bump.
  - Consumers **must reject** canonical input or identity claims with unknown or
    unsupported schema versions.
  - Old identities remain verifiable: recompute under the recorded version.
  - No silent downgrade; a canonical form claiming an unsupported version is
    rejected.

## 10. Canonicalization error taxonomy

Mirrors the Stage 1A error taxonomy. All derive from a `CanonicalizationError`
base (to be defined at implementation time). Stable `.code` values:

- `canonicalization.error` — unexpected internal failure.
- `canonicalization.input` — input is not a supported, validated contract graph.
- `canonicalization.input.not_validated` — `validate_contract` did not pass.
- `canonicalization.cycle` — residual cycle detected.
- `canonicalization.complexity` — depth or unique-node limit exceeded.
- `canonicalization.encoding` — a value object could not be encoded canonically
  (e.g., non-canonical stored state, or a value exceeding §4.4 bounds).
- `canonicalization.collision` — two distinct canonical payloads hashed to the
  same node id (§11).

Errors carry a structural `.path` (tuple of field names / integer indices),
consistent with Stage 1A.

## 11. Hash collisions and deterministic sort order

SHA-256 collision resistance is **assumed, not proven** (§12). Canonicalization
must not *rely* on collisions being impossible; it must behave deterministically
even in the (vanishingly unlikely) event of one.

- **Commutative ordering.** Operands of commutative nodes (class A and class B)
  are ordered by their canonical node id. As a deterministic tie-breaker for the
  rare case where two distinct payloads share an id, operands are ordered by
  `(canonical node id, canonical payload bytes)`.
- **Collision detection.** If the same canonical node id maps to **different**
  canonical payload bytes, canonicalization raises `canonicalization.collision`.
  This is a hard error; differing nodes are never silently merged.
- **Sharing.** Identical payloads with identical identities may be shared (one
  record in the node table, §7).
- **Duplicate operands.** Remain represented as duplicate references in operand
  arrays; collision handling never silently merges different nodes.
- This collision rule is recorded in the threat model (§13 of
  `threat-model.md`) and in ADR 0007.

## 12. Claim boundaries (normative)

Canonical equivalence and identity are deliberately narrow:

- Canonical equivalence is equivalence **only** under the enumerated schema laws
  in §5.
- It is **not** complete mathematical equivalence.
- It is **not** economic equivalence.
- It is **not** pricing equivalence.
- It is **not** legal equivalence.
- Hash equality is meaningful **only** under the same schema name **and**
  version. Two artifacts under different schema versions are different even if
  structurally similar.
- SHA-256 collision resistance is **assumed, not proven**.
- **No formal verification claim exists.** Nothing here constitutes a proof of
  correctness, completeness, or soundness.

## 13. Security and collision considerations

- **Injective by construction:** distinct canonical structures must map to
  distinct canonical bytes, so distinct contracts get distinct identities. This
  is enforced by tests (distinct inputs → distinct identities) at
  implementation time.
- **Hash collision:** SHA-256 collision resistance is assumed; the §11
  collision rule makes behaviour deterministic even if a collision occurs.
- **Domain separation:** fixed, versioned domain tags (§8) prevent
  cross-context hash confusion (a node id cannot be mistaken for a contract
  identity, etc.).
- **Forged / non-canonical input:** any decoded canonical form that is not
  itself canonical is rejected; canonicalization does not trust a claimed
  identity.
- **Identity ≠ authentication:** the canonical identity is an integrity/
  structural fingerprint, **not** a digital signature (ADR 0002/0003).
- **Cycle / DoS protections** from Stage 1A carry over (§2).
- **Canonicalization-collision threat** (see `threat-model.md`) is mitigated by
  injectivity, domain separation, the §11 collision rule, and rejection of
  non-canonical input.

## 14. Relationship to other documents

- Builds on ADR 0002 (deterministic canonicalization) and ADR 0006 (Stage 1A
  algebra).
- The canonical byte rules are intentionally aligned with
  `certificate-spec.md` (sorted keys, UTC, explicit units, no `NaN`/`Infinity`,
  SHA-256) so a future certificate can embed the canonical contract cleanly.
- The payoff-graph compilation is specified separately in
  `payoff-graph-spec.md`.
- Test vectors are specified in `canonical-test-vectors.md`.
- The constitutional decision is recorded in
  [ADR 0007](./adr/0007-canonical-contract-identity-and-payoff-graph.md).

> **Reminder:** This file is a specification. No canonicalization, hashing,
> serialization, or payoff-graph code exists in Stage 1B's baseline.
