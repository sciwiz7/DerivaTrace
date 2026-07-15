# Payoff-graph specification (Stage 1B baseline)

- **Status:** Specification only. **Not implemented.**
- **Stage:** 1B (architecture baseline; compilation follows separate review).
- **Schema name:** `derivatrace.payoffgraph`.
- **Schema version:** `1.0.0` (semantic version; participates in identity, §5).
- **Depends on:** `canonicalization-spec.md` and ADR 0001–0006.

This document specifies the **canonical payoff graph**: the model-independent,
compiled representation of a validated and canonicalized DerivaTrace contract.
It is the design baseline for Stage 1B. No compilation logic, node classes, or
serialization code described here exists in the package yet.

> **Conservative principle (binding).** The payoff graph is a *structural*
> compilation of the contract under the approved canonicalization laws. It
> performs no valuation and asserts no economic equivalence. It is not a price.
> Canonical equivalence is equivalence only under the enumerated laws; it is not
> complete mathematical, economic, pricing, or legal equivalence
> (`canonicalization-spec.md` §12).

## 1. Purpose and boundaries

The payoff graph is the artifact a future model/engine values. It is:

- **Model-independent** — contains no stochastic assumptions or numerical
  method.
- **Deterministic** — the same canonical contract always compiles to the same
  payoff graph.
- **Structural** — a normalized DAG of payoff terms with explicit currency,
  unit, and settlement attributes.

Explicitly **out of scope**: pricing, Greeks, market-data resolution, model or
engine selection, calibration, hedging, certificates.

## 2. Payoff-graph node taxonomy

The graph is a DAG. Nodes fall into three categories: **leaves**, **operations**,
and **combinations**. Each node carries an explicit `Unit` (and, where
relevant, a `Currency` and `SettlementTime`).

### 2.1 Payoff leaves

| Node | Fields | Source contract node |
|------|--------|----------------------|
| `PGConstant` | `amount` (exact `Decimal` tuple + `Unit`), `settlement_time` (`<rfc3339z>` or `null`) | `Number` inside a `Payment` amount; or folded literal |
| `PGObservable` | `observable_id`, `observation_time` (`<rfc3339z>`), `unit`, `settlement_time` (`null`) | `Observable` referenced by a `Payment` amount |

Leaves are the only nodes that carry `settlement_time` / `observation_time`.
Compilation does **not** evaluate the observable; it preserves the identity and
time. A `PGConstant` whose `settlement_time` is `null` represents a scalar
constant used structurally (e.g., a `Scale` factor) rather than a dated cash
flow.

### 2.2 Payoff operations (scalar on payoffs)

| Node | Fields | Source | Commutativity in graph |
|------|--------|--------|------------------------|
| `PGAdd` | `operands` (≥2) | `Add` | Associative + commutative multiset (same rule as `Add`) |
| `PGMultiply` | `left`, `right` | `Multiply` | Commutative; **binary** (same rule as `Multiply`) |
| `PGNegate` | `operand` | `Negate` | n/a (unary) |
| `PGMaximum` | `operands` (≥2) | `Maximum` | Associative + commutative (same rule as `Maximum`) |
| `PGMinimum` | `operands` (≥2) | `Minimum` | Associative + commutative (same rule as `Minimum`) |
| `PGScale` | `factor`, `payoff` | `Scale` | Author-order-preserving (`factor` then `payoff`) |
| `PGConditionalValue` | `condition`, `true_payoff`, `false_payoff` | `ConditionalValue` | Author-order-preserving |
| `PGDivide` | `numerator`, `denominator` | `Divide` | Author-order-preserving; **no reciprocal rewrite** (see §3) |

Operation nodes inherit the exact commutativity / flattening / duplicate /
literal-folding rules defined in `canonicalization-spec.md` §5. No new rewrite
law is introduced here. `PGDivide` is **author-order-preserving** (like
`Divide`); it is **never** rewritten into `PGMultiply` by a reciprocal.

### 2.4 Payoff boolean nodes (conditions)

Boolean expressions used as `condition` operands compile to mirroring
author-order-preserving nodes:

| Node | Fields | Source |
|------|--------|--------|
| `PGComparison` | `left`, `right`, `operator` | `Comparison` |
| `PGAllOf` | `operands` (≥2) | `AllOf` |
| `PGAnyOf` | `operands` (≥2) | `AnyOf` |
| `PGNot` | `operand` | `Not` |

These carry the same fields and ordering rules as their contract-source nodes
(§5.1 class C). They appear as the `condition` reference of
`PGConditionalValue` / `PGConditionalContract`.

### 2.3 Payoff combinations (contracts)

| Node | Fields | Source | Commutativity in graph |
|------|--------|--------|------------------------|
| `PGCombine` | `operands` (≥2; may be empty for `Zero`) | `Both` / `Zero` | **Author-order-preserving** (same rule as `Both` — NOT commutative, NOT flattened) |
| `PGPayment` | `payoff_leaf`, `currency`, `settlement_time` | `Payment` | Positional |
| `PGConditionalContract` | `condition`, `true_payoff`, `false_payoff` | `ConditionalContract` | Author-order-preserving |

`PGCombine` deliberately preserves author order, matching the `Both` policy in
`canonicalization-spec.md` §5.1. A future stage that introduces optionality or
exercise rights may revisit this; such a change requires a schema-version bump
and a new ADR.

## 3. Compilation mapping (specification)

The compiler walks the canonical contract DAG and emits a payoff-graph DAG.
Compilation is deterministic and reuses the §5 commutativity / flattening /
duplicate / literal-folding rules of the source nodes.

1. `Zero` → `PGCombine` with an **empty** `operands` array. (A distinguished
   zero; its identity is the canonical `PGCombine` payload.)
2. `Number` (standing alone, e.g. inside a `Scale` factor) → `PGConstant`
   with its `Unit` and `settlement_time = null`.
3. `Observable` → `PGObservable` carrying `observable_id`, `observation_time`,
   and `unit`; `settlement_time = null`.
4. `Add`/`Maximum`/`Minimum` → `PGAdd`/`PGMaximum`/`PGMinimum` with the same
   commutative + associative + duplicate + literal-folding rules.
5. `Multiply` → `PGMultiply` (commutative, binary, no flattening).
6. `Subtract` → `PGAdd` of (`minuend`, `PGNegate(subtrahend)`); positional.
7. `Divide` → **`PGDivide`** with `numerator` and `denominator` references
   preserved **exactly** as compiled from the canonical `Divide` node. The
   compiler does **NOT** rewrite division into multiplication by a reciprocal,
   does **NOT** compute a reciprocal, does **NOT** introduce floating point, and
   preserves the Stage 1A literal-zero-denominator and dimensionless-denominator
   rules. `PGDivide` folding is **excluded** in schema 1.0.0 (consistent with
   the removed `Divide` folding in `canonicalization-spec.md` §5.3).
8. `Negate` → `PGNegate`.
9. `ConditionalValue` → `PGConditionalValue`.
10. `Scale` → `PGScale(factor, payoff)`.
11. `Payment(amount, currency, settlement_time)` → `PGPayment` whose
    `payoff_leaf` is the compiled `amount` (a `PGConstant` or `PGObservable`)
    annotated with `currency` and `settlement_time`.
12. `Both` → `PGCombine` (author order preserved).
13. `ConditionalContract` → `PGConditionalContract`.

The compiled graph is itself canonicalized using the same byte-encoding (§3 of
`canonicalization-spec.md`) and hashing rules (§8 of
`canonicalization-spec.md`), yielding a `payoffgraph:sha256:<hex>` identity
under `derivatrace.payoffgraph.graph`.

## 4. Payoff-graph canonical document and identity

### 4.1 Document shape

The canonical **payoff-graph document** is a single JSON object with exactly
these fields (field names fixed):

| Field | Type | Meaning |
|-------|------|---------|
| `schema_name` | string | `"derivatrace.payoffgraph"` |
| `schema_version` | string | `"1.0.0"` |
| `root` | string | canonical payoff-node id (bare 64-hex) of the root node |
| `nodes` | object | node table: map `node id` → node record |
| `provenance` | object | identity-exempt linkage metadata (see §4.2) |

A **payoff node record** mirrors the contract node record:

| Field | Type | Meaning |
|-------|------|---------|
| `id` | string | the node's canonical payoff-node id (bare 64-hex) |
| `payload` | object | the node's canonical payoff payload (§2 / §4.3) |

### 4.2 Source-contract linkage and identity exemption

`provenance` is an object:

```json
{
  "source_contract_identity": "canonical:sha256:<hex>",
  "compiler": "derivatrace.stage1b.baseline"
}
```

It records the source canonical contract identity for traceability. **It is
identity-exempt:** the payoff-graph identity (§4.4) is computed over the
**structural projection** of the document — `{schema_name, schema_version, root,
nodes}` — and explicitly **excludes** `provenance`. Recompiling the same
contract therefore always yields the same payoff-graph identity regardless of how
it is referenced. `provenance` is **not** part of the hashed preimage.

### 4.3 Payoff node payload schema

Canonical payloads use the same §3 byte rules and the same operand-reference
convention (bare 64-hex payoff-node ids). The fixed `type` field carries the
payoff node name.

| Node | Canonical payload object |
|------|--------------------------|
| `PGConstant` | `{"type":"PGConstant","amount":<dec>,"unit":<unit>,"settlement_time":"<rfc3339z>"|null}` |
| `PGObservable` | `{"type":"PGObservable","observable_id":<oid>,"observation_time":"<rfc3339z>","unit":<unit>,"settlement_time":null}` |
| `PGAdd` | `{"type":"PGAdd","operands":[<id>, ...]}` (≥2, flattened, sorted) |
| `PGMultiply` | `{"type":"PGMultiply","left":<id>,"right":<id>}` (binary, sorted) |
| `PGNegate` | `{"type":"PGNegate","operand":<id>}` |
| `PGMaximum` | `{"type":"PGMaximum","operands":[<id>, ...]}` (≥2, flattened, sorted) |
| `PGMinimum` | `{"type":"PGMinimum","operands":[<id>, ...]}` (≥2, flattened, sorted) |
| `PGScale` | `{"type":"PGScale","factor":<id>,"payoff":<id>}` |
| `PGConditionalValue` | `{"type":"PGConditionalValue","condition":<id>,"true_payoff":<id>,"false_payoff":<id>}` |
| `PGDivide` | `{"type":"PGDivide","numerator":<id>,"denominator":<id>}` |
| `PGCombine` | `{"type":"PGCombine","operands":[<id>, ...]}` (author order; may be empty) |
| `PGPayment` | `{"type":"PGPayment","payoff_leaf":<id>,"currency":"USD","settlement_time":"<rfc3339z>"}` |
| `PGConditionalContract` | `{"type":"PGConditionalContract","condition":<id>,"true_payoff":<id>,"false_payoff":<id>}` |
| `PGComparison` | `{"type":"PGComparison","left":<id>,"right":<id>,"operator":"<"|"<="|"=="|"!="|">="|">"}` |
| `PGAllOf` | `{"type":"PGAllOf","operands":[<id>, ...]}` (≥2, flattened, sorted) |
| `PGAnyOf` | `{"type":"PGAnyOf","operands":[<id>, ...]}` (≥2, flattened, sorted) |
| `PGNot` | `{"type":"PGNot","operand":<id>}` |

Where `<dec>`, `<unit>`, `<oid>`, and `<id>` follow the same definitions as in
`canonicalization-spec.md` §5.4 (the `<id>` here is a payoff-node id).

### 4.4 Identity preimages

Identities use the §8 framing of `canonicalization-spec.md`:

```text
<DOMAIN> + 0x00 + "1.0.0" + 0x00 + <CANONICAL_PAYLOAD_BYTES>
```

- **Payoff-node id** — domain `derivatrace.payoffgraph.node`, hashed over the
  canonical JSON bytes of the **payoff node payload**. Stored/referenced as the
  bare 64-hex string.
- **Payoff-graph id** — domain `derivatrace.payoffgraph.graph`, hashed over
  the canonical JSON bytes of the **structural projection** of the payoff-graph
  document (§4.2, excluding `provenance`). Presented as
  `payoffgraph:sha256:<hex>`.

Both participate in identity via the schema version in the preimage framing. SHA-256
output is lowercase 64-hex. Domain tags are fixed schema constants; changing one
requires a version bump.

### 4.5 Ordering, sharing, duplicates, collisions

- **Records ordered** by ascending payoff-node id, tie-broken by canonical
  payload bytes (mirrors `canonicalization-spec.md` §7/§11).
- **Sharing** — identical subgraphs share one content-addressed record; Python
  object identity is never part of identity.
- **Duplicate operands** remain duplicate references in operand arrays.
- **Collisions** — if the same payoff-node id maps to different payload bytes,
  raise `canonicalization.collision` (same rule as
  `canonicalization-spec.md` §11).

## 5. Determinism, sharing, and complexity

- The payoff graph is a **DAG**; shared canonical subexpressions are
  represented once and referenced by content-derived id (same policy as
  `canonicalization-spec.md` §7).
- Compilation reuses the Stage 1A cycle detection and `ValidationLimits`.
- Traversal is iterative (stack-based), never recursive.
- Cycles are rejected before any canonical output is produced.

## 6. Validation levels and equivalence (deferred to Stage 1C)

Graded validation levels, equivalence *reporting*, and structural diffing are
**Stage 1C**, not Stage 1B. This document defines only the graph shape and its
identity. The canonical identity supports future equivalence checks but does not
itself constitute an economic-equivalence proof.

## 7. Relationship to other documents

- Consumes the canonical contract from `canonicalization-spec.md`.
- Aligned with `certificate-spec.md` so a future certificate can embed the
  payoff-graph identity.
- Constitutional decision in
  [ADR 0007](./adr/0007-canonical-contract-identity-and-payoff-graph.md).
- Test vectors in `canonical-test-vectors.md`.

> **Reminder:** This file is a specification. No payoff-graph compilation or
> node code exists in Stage 1B's baseline.
