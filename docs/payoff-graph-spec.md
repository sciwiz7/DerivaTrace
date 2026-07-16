# Payoff-graph specification (Stage 1B-R2)

- **Status:** Specification only. **Not implemented.** This document is the
  **Stage 1B-R2 specification-closure** pass: it closes every contradiction found
  in the earlier Stage 1B baseline payoff-graph draft before runtime
  implementation begins.
- **Stage:** 1B-R2 (specification closure; **runtime Planned**).
- **Depends on:** `canonicalization-spec.md`, the Stage 1B-R1 canonical runtime
  (`derivatrace.canonical`), and ADR 0001–0007.
- **Schema name:** `derivatrace.payoffgraph`.
- **Schema version:** `1.0.0` (semantic version; participates in identity, §9).

This document specifies the **canonical payoff graph**: the model-independent,
compiled representation of a validated and canonicalized DerivaTrace contract.
It is the design specification for Stage 1B-R2. **No compilation logic, node
classes, or serialization code described here exists in the package yet.** The
payoff-graph runtime remains Planned; only this specification is closed here.

> **Conservative principle (binding).** The payoff graph is a *structural*
> compilation of the contract under the approved canonicalization laws. It
> performs no valuation and asserts no economic equivalence. It is not a price.
> Canonical equivalence is equivalence only under the enumerated laws; it is not
> complete mathematical, economic, pricing, or legal equivalence
> (`canonicalization-spec.md` §12).

## 1. Purpose and boundaries

The payoff graph is the artifact a future model/engine values. It is:

- **Model-independent** — contains no stochastic assumptions or numerical method.
- **Deterministic** — the same canonical contract always compiles to the same
  payoff graph.
- **Structural** — a normalized DAG of payoff terms with explicit currency,
  unit, and settlement attributes.

Explicitly **out of scope**: pricing, Greeks, market-data resolution, model or
engine selection, calibration, hedging, certificates.

## 2. Schema and domain constants

These are fixed, versioned schema constants. Changing any of them requires a
schema-version bump.

| Constant | Value |
|----------|-------|
| Schema name | `derivatrace.payoffgraph` |
| Schema version | `1.0.0` |
| Payoff-node domain | `derivatrace.payoffgraph.node` |
| Payoff-graph domain | `derivatrace.payoffgraph.graph` |
| Compiler provenance tag | `derivatrace.payoffgraph.compiler/1.0.0` |

The identity preimage framing (§9) is:

```text
<DOMAIN> + 0x00 + <SCHEMA_VERSION> + 0x00 + <PAYLOAD_BYTES>
```

where `<DOMAIN>` is one of the two payoff domains above, `<SCHEMA_VERSION>` is the
literal ASCII string `"1.0.0"`, and `<PAYLOAD_BYTES>` is the canonical JSON bytes
of the hashed structure (§3 of `canonicalization-spec.md`). All output hashes are
lowercase SHA-256 hex. Schema and limit objects must later use exact-type,
use-time validation equivalent to the hardened R1 boundary
(`derivatrace.canonical._schema`).

## 3. Payoff-graph node taxonomy

The graph is a DAG. Nodes fall into four categories: **leaves**, **operations**,
**boolean**, and **combinations**. Each node carries an explicit `Unit` (and,
where relevant, a `Currency`), but **only the nodes that own a time carry it**:

- **Observation time** is owned exclusively by `PGObservable`.
- **Settlement time** is owned exclusively by `PGPayment`.

No other node carries `settlement_time` or `observation_time`. The explicit
ownership rule replaces the older, contradictory statement that "leaves are the
only nodes carrying settlement time."

### 3.1 Payoff leaves

| Node | Fields | Source contract node |
|------|--------|----------------------|
| `PGConstant` | `amount` (exact `Decimal` tuple + `unit`) | `Number` inside a `Payment` amount; or folded literal |
| `PGObservable` | `observable_id`, `observation_time` (`<rfc3339z>`), `unit` | `Observable` referenced by a `Payment` amount |

- `PGConstant` contains **exact value** (`amount`) and **unit** only. It does
  **not** contain `settlement_time`. A `PGConstant` represents a structural
  scalar or money amount; settlement is owned by the `PGPayment` that references
  it.
- `PGObservable` contains `observable_id`, `observation_time`, and `unit` only.
  It does **not** contain `settlement_time`. Compilation does not evaluate the
  observable; it preserves the identity and time.

### 3.2 Payoff operations (scalar on payoffs)

| Node | Fields | Source | Commutativity / shape in graph |
|------|--------|--------|-------------------------------|
| `PGAdd` | `operands` (≥2) | `Add` | Associative + commutative multiset (same rule as `Add`) |
| `PGSubtract` | `minuend`, `subtrahend` | `Subtract` | **Author-order-preserving**; binary; **not** lowered to `PGAdd`+`PGNegate` |
| `PGMultiply` | `left`, `right` | `Multiply` | Commutative; **binary** (same rule as `Multiply`) |
| `PGNegate` | `operand` | `Negate` | n/a (unary) |
| `PGMaximum` | `operands` (≥2) | `Maximum` | Associative + commutative (same rule as `Maximum`) |
| `PGMinimum` | `operands` (≥2) | `Minimum` | Associative + commutative (same rule as `Minimum`) |
| `PGDivide` | `numerator`, `denominator` | `Divide` | **Author-order-preserving**; **no reciprocal rewrite** (see §5) |

Operation nodes inherit the exact commutativity / flattening / duplicate /
literal-folding rules defined in `canonicalization-spec.md` §5 — with the
**explicit exception** that `Subtract` compiles to a dedicated `PGSubtract` node
and is never lowered into `PGAdd` of (`minuend`, `PGNegate(subtrahend)`). No new
rewrite law is introduced here. `PGDivide` is author-order-preserving (like
`Divide`); it is never rewritten into `PGMultiply` by a reciprocal.

### 3.3 Payoff boolean nodes (conditions)

Boolean expressions used as `condition` operands compile to mirroring nodes. The
Boolean policy is **node-specific**, not a blanket "all Boolean nodes preserve
author order":

| Node | Fields | Source | Policy |
|------|--------|--------|--------|
| `PGComparison` | `left`, `right`, `operator` | `Comparison` | **Binary, operator-sensitive, author-order preserved, not commutative** |
| `PGAllOf` | `operands` (≥2) | `AllOf` | **Commutative, associative, flattened, sorted canonically, duplicates retained** |
| `PGAnyOf` | `operands` (≥2) | `AnyOf` | **Commutative, associative, flattened, sorted canonically, duplicates retained** |
| `PGNot` | `operand` | `Not` | **Unary, positional** |
| `PGBooleanConstant` | `value` (`true`/`false`) | `BooleanConstant` | Leaf; constant condition made explicit (never left implicit) |

`PGAllOf` / `PGAnyOf` are flattened and sorted by canonical node id
(tie-broken by canonical payload bytes), matching `AllOf`/`AnyOf`. `PGComparison`
preserves author order and is operator-sensitive: `a < b` is not `b < a`.
`PGNot` is unary and positional. `PGBooleanConstant` is introduced so that a
constant Boolean condition is represented explicitly in the graph rather than
left implicit.

### 3.4 Payoff combinations (contracts)

| Node | Fields | Source | Commutativity / shape in graph |
|------|--------|--------|-------------------------------|
| `PGCombine` | `operands` (≥2; **empty** for `Zero`) | `Both` / `Zero` | **Author-order-preserving** (same rule as `Both` — NOT commutative, NOT flattened) |
| `PGPayment` | `amount`, `currency`, `settlement_time` | `Payment` | Positional |
| `PGScale` | `factor`, `payoff` | `Scale` | Author-order-preserving (`factor` then `payoff`) |
| `PGConditionalValue` | `condition`, `true_payoff`, `false_payoff` | `ConditionalValue` | Author-order-preserving |
| `PGConditionalContract` | `condition`, `true_payoff`, `false_payoff` | `ConditionalContract` | Author-order-preserving |

`PGCombine` deliberately preserves author order, matching the `Both` policy in
`canonicalization-spec.md` §5.1. `PGPayment`'s `amount` is a **reference id** to
any valid compiled value expression (a `PGConstant`, `PGObservable`, `PGAdd`,
`PGSubtract`, `PGMultiply`, `PGDivide`, `PGNegate`, `PGMaximum`, `PGMinimum`, or
`PGConditionalValue`); the field is named **`amount`**, never `payoff_leaf`.
Settlement time is owned by `PGPayment`.

## 4. Complete node mapping (normative matrix)

Every canonical R1 node maps to exactly one payoff node. There is no unmapped
canonical node. The matrix records, per source node: the output node, its output
fields, its reference fields (used for reachability, §12), ordering, flattening,
duplicate policy, permitted folding, and time/unit ownership.

| Canonical node | Output node | Output fields | Reference fields | Ordering | Flatten | Dup | PG folding | Time / unit ownership |
|----------------|-------------|--------------|-----------------|----------|---------|-----|-----------|----------------------|
| `Number` | `PGConstant` | `amount`, `unit` | — | n/a (leaf) | n/a | n/a | none | no time; carries `unit` |
| `Observable` | `PGObservable` | `observable_id`, `observation_time`, `unit` | — | n/a (leaf) | n/a | n/a | none | **observation_time** owned here; carries `unit` |
| `Add` | `PGAdd` | `operands` | `operands` | sorted by id (tie payload) | yes | retained | none (reuse R1 result) | carries operand units |
| `Subtract` | `PGSubtract` | `minuend`, `subtrahend` | `minuend`, `subtrahend` | **author order** | none | n/a | none | carries operand units |
| `Multiply` | `PGMultiply` | `left`, `right` | `left`, `right` | sorted by id (binary) | none | retained | none | carries operand units |
| `Divide` | `PGDivide` | `numerator`, `denominator` | `numerator`, `denominator` | **author order** | none | n/a | none (no reciprocal) | carries operand units |
| `Negate` | `PGNegate` | `operand` | `operand` | unary positional | none | n/a | none | carries operand unit |
| `Maximum` | `PGMaximum` | `operands` | `operands` | sorted by id (tie payload) | yes | retained | none | carries operand units |
| `Minimum` | `PGMinimum` | `operands` | `operands` | sorted by id (tie payload) | yes | retained | none | carries operand units |
| `ConditionalValue` | `PGConditionalValue` | `condition`, `true_payoff`, `false_payoff` | all three | **author order** | none | n/a | none | unit of selected branch |
| `BooleanConstant` | `PGBooleanConstant` | `value` | — | leaf | n/a | n/a | none | none |
| `Comparison` | `PGComparison` | `left`, `right`, `operator` | `left`, `right` | **author order**, operator-sensitive | none | n/a | none | none |
| `AllOf` | `PGAllOf` | `operands` | `operands` | sorted by id (tie payload) | yes | retained | none | none |
| `AnyOf` | `PGAnyOf` | `operands` | `operands` | sorted by id (tie payload) | yes | retained | none | none |
| `Not` | `PGNot` | `operand` | `operand` | unary positional | none | n/a | none | none |
| `Zero` | `PGCombine` | `operands` (empty array) | — | n/a | n/a | n/a | none | distinguished zero |
| `Payment` | `PGPayment` | `amount`, `currency`, `settlement_time` | `amount` | positional | none | n/a | none | **settlement_time** owned here; `currency` carried here |
| `Both` | `PGCombine` | `operands` | `operands` | **author order** | none | retained | none | carries contract operands |
| `Scale` | `PGScale` | `factor`, `payoff` | `factor`, `payoff` | **author order** | none | n/a | none | unit of `payoff` |
| `ConditionalContract` | `PGConditionalContract` | `condition`, `true_payoff`, `false_payoff` | all three | **author order** | none | n/a | none | unit of selected branch |

The `amount` reference of `PGPayment` and the `factor`/`payoff` references of
`PGScale` may point to any value-expression node above; the graph remains a DAG
because references only point to already-compiled upstream nodes.

## 5. Compilation mapping (specification)

The compiler walks the canonical contract DAG (produced by the authoritative R1
runtime) and emits a payoff-graph DAG. Compilation is deterministic and reuses the
§4 commutativity / flattening / duplicate / literal-folding rules of the source
nodes **as already applied by R1** — it does not re-evaluate or re-fold.

1. `Zero` → `PGCombine` with an **empty** `operands` array. (A distinguished
   zero; its identity is the canonical `PGCombine` payload with an empty array.)
2. `Number` (standing alone, e.g. inside a `Scale` factor) → `PGConstant` with
   its `amount` (`unit`) and **no** `settlement_time`.
3. `Observable` → `PGObservable` carrying `observable_id`, `observation_time`, and
   `unit`; **no** `settlement_time`.
4. `Add`/`Maximum`/`Minimum` → `PGAdd`/`PGMaximum`/`PGMinimum` with the same
   commutative + associative + duplicate + literal-folding rules (already applied
   by R1).
5. `Subtract` → `PGSubtract` with `minuend` and `subtrahend` references preserved
   **exactly** as compiled from the canonical `Subtract` node. **It is NOT lowered
   to `PGAdd` of (`minuend`, `PGNegate(subtrahend)`).** Stage 1B-R2 introduces no
   new equivalence law collapsing `Subtract(a,b)` with `Add(a,Negate(b))`.
6. `Multiply` → `PGMultiply` (commutative, binary, no flattening).
7. `Divide` → `PGDivide` with `numerator` and `denominator` references preserved
   **exactly**. **No reciprocal rewrite**, no float, no literal folding in schema
   1.0.0.
8. `Negate` → `PGNegate`.
9. `ConditionalValue` → `PGConditionalValue`.
10. `BooleanConstant` → `PGBooleanConstant` (explicit `value`).
11. `Comparison` → `PGComparison` (author order, operator-sensitive).
12. `AllOf`/`AnyOf` → `PGAllOf`/`PGAnyOf` (flattened, sorted, commutative).
13. `Not` → `PGNot`.
14. `Scale` → `PGScale(factor, payoff)`.
15. `Payment(amount, currency, settlement_time)` → `PGPayment` whose `amount` is
    the compiled `amount` reference, annotated with `currency` and
    `settlement_time`. The `amount` field (never `payoff_leaf`) may reference any
    compiled value expression.
16. `Both` → `PGCombine` (author order preserved).
17. `ConditionalContract` → `PGConditionalContract`.

The compiled graph is itself canonicalized using the same byte-encoding (§3 of
`canonicalization-spec.md`) and hashing rules (§9 of this document), yielding a
`payoffgraph:sha256:<hex>` identity under `derivatrace.payoffgraph.graph`.

## 6. Compiler input and public boundary

The public Stage 1B-R2 entry point accepts a **validated Stage 1A `Contract`**,
not arbitrary JSON or arbitrary canonical bytes:

```python
def compile_payoff_graph(
    contract: Contract,
    *,
    canonical_schema: CanonicalSchemaVersion | None = None,
    payoff_schema: PayoffGraphSchemaVersion | None = None,
    canonicalization_limits: CanonicalizationLimits | None = None,
    payoff_limits: PayoffGraphLimits | None = None,
    validation_limits: ValidationLimits | None = None,
) -> PayoffGraph: ...
```

Required flow:

1. **Validate and canonicalize** the `Contract` through the authoritative R1
   runtime (`derivatrace.canonical`). Canonicalization failures from R1 propagate
   without being silently reclassified unless the specification explicitly
   requires wrapping with the original cause preserved (§11).
2. **Compile from the resulting canonical contract document**, not
   independently from the author AST.
3. **Reuse canonical payload encodings** without evaluating expressions.
4. Produce a **deterministic reachable-only payoff DAG** (§12).
5. Attach the **source canonical identity** as provenance (§8).

The initial API does **not** accept arbitrary JSON or arbitrary canonical bytes.
A user-forged `CanonicalContract` instance is **not** trusted as input unless a
future, separately reviewed parser/validator is introduced.

## 7. Deterministic result type and bytes

The compiler returns an **immutable** `PayoffGraph` result carrying at least:

| Field | Type | Meaning |
|-------|------|---------|
| `schema_version` | string | `"1.0.0"` |
| `document_bytes` | bytes | full canonical JSON **including** provenance |
| `structural_bytes` | bytes | canonical JSON of exactly `{nodes, root, schema_name, schema_version}` |
| `identity` | string | `payoffgraph:sha256:<hex>` over `structural_bytes` only |
| `root_node_id` | string | bare 64-hex id of the final payoff root node |
| `node_count` | int | number of payoff nodes reachable from the final payoff root |
| `source_contract_identity` | string | `canonical:sha256:<hex>` of the source canonical contract |

Definitions:

- **`document_bytes`** — the full canonical JSON of the payoff-graph document,
  including `provenance` (§8).
- **`structural_bytes`** — the canonical JSON of exactly
  `{"nodes": ..., "root": ..., "schema_name": ..., "schema_version": ...}`,
  **excluding** `provenance`. This is the preimage for `identity`.
- **`identity`** — domain-separated SHA-256 over `structural_bytes` only.
- **`node_count`** — the number of payoff nodes reachable from the final payoff
  root.

Equality and hashing of `PayoffGraph` are based on **payoff-graph identity**
(`identity`), not on `document_bytes` (which includes provenance).

## 8. Provenance

Deterministic provenance is attached to every compiled graph:

```json
{
  "source_contract_identity": "canonical:sha256:<hex>",
  "compiler": "derivatrace.payoffgraph.compiler/1.0.0"
}
```

`source_contract_identity` is the canonical contract identity of the R1 document
the graph was compiled from. `compiler` is the fixed compiler tag from §2.

Provenance is included in **`document_bytes`** but **excluded** from
**`structural_bytes`** and from **`identity`**. Therefore:

- changing provenance alone changes `document_bytes`;
- changing provenance alone does **not** change payoff-graph identity;
- the runtime-generated provenance remains deterministic.

## 9. Identity preimages and node identities

Identities use the §8 framing of `canonicalization-spec.md` with the payoff
domains from §2:

```text
<DOMAIN> + 0x00 + "1.0.0" + 0x00 + <CANONICAL_PAYLOAD_BYTES>
```

- **Payoff-node id** — domain `derivatrace.payoffgraph.node`, hashed over the
  canonical JSON bytes of the **payoff node payload**. Stored/referenced as the
  bare 64-hex string.
- **Payoff-graph id** — domain `derivatrace.payoffgraph.graph`, hashed over the
  canonical JSON bytes of the **structural projection** of the payoff-graph
  document (§7, excluding `provenance`). Presented as
  `payoffgraph:sha256:<hex>`.

Both participate in identity via the schema version in the preimage framing. SHA-256
output is lowercase 64-hex. Domain tags are fixed schema constants; changing one
requires a version bump.

## 10. Output limits (PayoffGraphLimits)

`PayoffGraphLimits` carries conservative initial defaults and applies to the
**final reachable graph**, not to discarded compilation intermediates. Each limit
is an **exact positive `int`** (never a `bool`):

| Limit | Default | Justification |
|-------|---------|---------------|
| `max_payoff_nodes` | `4096` | Bounds reachable-node count; reuses the R1 `max_unique_nodes` order of magnitude while leaving room for expression expansion. |
| `max_document_bytes` | `4_194_304` (4 MiB) | Bounds the full `document_bytes`; comfortably exceeds the largest realistic single-contract graph under the node cap. |
| `max_structural_bytes` | `2_097_152` (2 MiB) | Bounds `structural_bytes` (the identity preimage); strictly smaller than `max_document_bytes` since it excludes provenance. |

Exceeding any limit raises `payoff_graph.complexity`. The compiler must remain
**iterative and recursion-free** (explicit stack), reusing the R1 cycle detection
and `ValidationLimits`.

## 11. Error taxonomy

A dedicated payoff-graph error taxonomy is defined, deriving from
`DerivaTraceError`. It must **not** reuse `canonicalization.collision` for a
payoff-node collision.

| Exception | Stable `.code` |
|-----------|----------------|
| `PayoffGraphError` | `payoff_graph.error` |
| `PayoffGraphInputError` | `payoff_graph.input` |
| `PayoffGraphCompilationError` | `payoff_graph.compilation` |
| `PayoffGraphComplexityError` | `payoff_graph.complexity` |
| `PayoffGraphEncodingError` | `payoff_graph.encoding` |
| `PayoffGraphCollisionError` | `payoff_graph.collision` |

- `payoff_graph.collision` is raised when the same payoff-node id maps to
  different payload bytes (the payoff-graph analogue of the R1 collision rule).
- Canonicalization failures from R1 (e.g. `canonicalization.complexity`,
  `canonicalization.collision`) **propagate** to the caller without being
  silently reclassified. Only when the specification explicitly requires wrapping
  (preserving the original cause) may a `PayoffGraph*` error carry the R1 error
  as `__cause__`.

## 12. Reachable-only graph

The final payoff document contains **only nodes reachable from the final payoff
root**. Discarded lowering intermediates (for example, any transient `PGNegate`
that would have been produced if `Subtract` had been lowered — it is not) must
never participate in:

- `document_bytes`
- `structural_bytes`
- `identity`
- `node_count`

Reference traversal uses an **explicit per-node-type reference-field map** (the
"Reference fields" column of §4). It never infers references by treating
arbitrary strings or 64-character values as ids. Currency codes, observable
identifiers, and arbitrary string literals are never confused with node ids.

## 13. Determinism, sharing, and complexity

- The payoff graph is a **DAG**; shared canonical subexpressions are represented
  once and referenced by content-derived id (same policy as
  `canonicalization-spec.md` §7).
- Compilation reuses the Stage 1A cycle detection and `ValidationLimits`.
- Traversal is iterative (stack-based), never recursive.
- Cycles are rejected before any canonical output is produced (inherited from R1).
- The compiler is recursion-free and bounded by `PayoffGraphLimits` (§10).

## 14. Relationship to other documents

- Consumes the canonical contract from `canonicalization-spec.md` (R1 runtime).
- Aligned with `certificate-spec.md` so a future certificate can embed the
  payoff-graph identity.
- Constitutional decision in
  [ADR 0007](./adr/0007-canonical-contract-identity-and-payoff-graph.md).
- Normative and planned vectors in `canonical-test-vectors.md`.

> **Reminder:** This file is a specification. No payoff-graph compilation or
> node code exists in Stage 1B-R2 yet; the runtime remains Planned.
