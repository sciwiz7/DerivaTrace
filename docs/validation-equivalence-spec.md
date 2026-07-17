# Validation-equivalence specification (Stage 1C baseline)

- **Status:** Architecture baseline established. Runtime implementation planned for
  Stage 1C-R1 (validation levels and equivalence reports) and Stage 1C-R2
  (deterministic structural diffing).
- **Stage:** 1C (architecture baseline **established**; runtimes planned).
- **Depends on:** Stage 1A (`derivatrace.contracts`), Stage 1B-R1 canonical runtime
  (`derivatrace.canonical`), Stage 1B-R2 payoff-graph runtime
  (`derivatrace.payoffgraph`), ADR 0001–0007, ADR 0008.
- **Schema name (report):** `derivatrace.validation-equivalence.report`.
- **Schema version:** `1.0.0` (semantic version; participates in report identity,
  §7).

This document defines the **validation-equivalence layer** for DerivaTrace:
graded validation levels, a deterministic equivalence report, and deterministic
structural diffing over trusted Stage 1B representations. It implements no
pricing, valuation, model, engine, market data, or economic-equivalence claim.

> **Conservative principle (binding).** Stage 1C distinguishes and reports
> structural validation outcomes. It **must not** claim, imply, or enable any
> assertion of general economic equivalence, equal value, equal cash flows under
> every market path, legal equivalence, accounting equivalence, tax equivalence,
> model equivalence, or suitability/recommendation equivalence. Every result is
> a structural comparison under explicitly enumerated laws.

## 1. Scope and hard boundaries

Validation-equivalence operates **only** on:

- Validated Stage 1A contract graphs (or their Stage 1B canonical/payoff
  projections).
- Trusted, versioned canonical-contract and payoff-graph identities and
  structures produced by the Stage 1B runtimes.

Explicitly **out of scope** for this specification and for Stage 1C
implementation:

- Pricing, valuation, Greeks, any financial calculation.
- Model or numerical-engine selection or execution.
- Market-data retrieval or observable evaluation.
- Evidence-certificate generation (Stage 4).
- Arbitrary executable user code.
- Any claim of economic, legal, accounting, tax, model, or suitability
  equivalence.
- AI-derived semantic decisions inside the deterministic core.
- New runtime dependencies without separate review.

## 2. Validation-level taxonomy

Stage 1C defines a **closed, ordered enum** of validation levels. The enum
values are stable strings; they are not free-form.

| Level key (enum) | Display name | Evaluation depth |
|------------------|--------------|------------------|
| `structural` | Structural validity | Stage 1A whole-graph validation: type invariants, unit/currency consistency, cycle detection, depth/node-count limits. No canonicalization, no identity. |
| `canonical` | Canonical-contract equivalence | Stage 1A validation **and** Stage 1B-R1 canonicalization. |
| `payoff` | Payoff-graph structural equivalence | Stage 1A validation **and** Stage 1B-R1 canonicalization **and** Stage 1B-R2 payoff-graph compilation. |

### 2.1 Progressive processing depth (not a logical implication hierarchy)

The levels describe **progressive evaluation depth**, **not** a logical
implication hierarchy between equivalence results:

- `structural` performs Stage 1A validation only.
- `canonical` performs Stage 1A validation **and** Stage 1B-R1 canonicalization.
- `payoff` performs Stage 1A validation, Stage 1B-R1 canonicalization, **and**
  Stage 1B-R2 payoff-graph compilation.

Normative rules:

- Canonical evaluation requires successful structural validation.
- Payoff evaluation requires successful structural validation and R1
  canonicalization.
- Requesting a deeper level causes prior stages to be evaluated.
- Canonical-equivalence and payoff-equivalence remain separately reported.
- Stage 1C does **not** guarantee that payoff-graph equivalence implies
  canonical contract equivalence.
- Stage 1C does **not** guarantee the converse beyond the deterministic
  behaviour explicitly provided by the selected schema versions.
- No permanent injectivity guarantee is made for the R1-to-R2 compiler.

A level never returns a comparison result for a deeper level than requested:
requesting `structural` leaves `canonical`/`payoff` statuses `not_evaluated`;
requesting `canonical` leaves the `payoff` status `not_evaluated`.

The enum is closed; `unsupported_level` is raised for any other string.

### 2.2 Documentation guard on level wording

The following wording is **rejected** and must not appear in documentation or
specifications:

- "payoff equivalence subsumes canonical equivalence"
- "payoff equivalence proves canonical equivalence"
- "the R1-to-R2 mapping is permanently injective"
- any phrasing that implies a logical implication hierarchy between equivalence
  results across levels.

The validation levels describe **progressive processing depth**; the equivalence
results at each level are **independent comparison conclusions**.

## 3. Equivalence reporting

### 3.1 Proposed public entry point (unimplemented)

```python
def compare_contracts(
    left: Contract,
    right: Contract,
    *,
    level: ValidationLevel = "canonical",
    canonical_schema: CanonicalSchemaVersion | None = None,
    payoff_schema: PayoffGraphSchemaVersion | None = None,
    canonicalization_limits: CanonicalizationLimits | None = None,
    payoff_limits: PayoffGraphLimits | None = None,
    validation_limits: ValidationLimits | None = None,
    diff: DiffSelection = "canonical",
    diff_limits: DiffLimits | None = None,
) -> ValidationEquivalenceReport: ...
```

The function is **not yet implemented**; this specification defines its contract.
No Stage 1C runtime module exists.

### 3.2 Accepted trusted inputs

- Two `derivatrace.contracts.Contract` instances (validated Stage 1A graphs).
- The function internally validates, canonicalizes, and compiles payoff graphs
  via the Stage 1B runtimes. It does **not** accept pre-canonicalized bytes,
  pre-computed identities, or arbitrary JSON.

### 3.3 Report schema and versioning

- **Schema name:** `derivatrace.validation-equivalence.report`
- **Schema version:** `1.0.0` (carried in the report; participates in report
  identity if reports are hashed, §7).
- **Serialization:** Canonical JSON per `canonicalization-spec.md` §3
  (`json.dumps(..., ensure_ascii=True, sort_keys=True, separators=(",", ":"))`,
  UTF-8, no BOM, no trailing newline). A report is **immutable** once produced.

### 3.4 Exact report fields

```json
{
  "schema_name": "derivatrace.validation-equivalence.report",
  "schema_version": "1.0.0",
  "report_id": "validation-equivalence:sha256:<hex> | null",
  "requested_level": "structural | canonical | payoff",
  "canonical_schema_version": "1.0.0",
  "payoff_schema_version": "1.0.0",
  "left_validation_outcome": "valid | invalid | not_evaluated",
  "right_validation_outcome": "valid | invalid | not_evaluated",
  "canonical_comparison_status": "equivalent | different | not_comparable | not_evaluated",
  "canonical_comparison_reason": "<stable-code> | null",
  "payoff_comparison_status": "equivalent | different | not_comparable | not_evaluated",
  "payoff_comparison_reason": "<stable-code> | null",
  "left": {
    "contract_identity": "canonical:sha256:<hex> | null",
    "payoff_graph_identity": "payoffgraph:sha256:<hex> | null",
    "structural_errors": ["validation.error.code", ...] | null,
    "canonicalization_errors": ["canonicalization.error.code", ...] | null,
    "payoff_compilation_errors": ["payoff_graph.error.code", ...] | null
  },
  "right": { "... same shape as left ..." },
  "diff_representation": "canonical | payoff | both | none",
  "diff_summary": {
    "entries": [
      {
        "path": "/nodes/<node-id>/payload/operands/0",
        "op": "add | remove | change | replace",
        "left_value": "<json-value> | null",
        "right_value": "<json-value> | null"
      }
    ],
    "truncated": false,
    "truncation_reason": "entry_limit | byte_limit | node_limit | path_limit | null",
    "unavailable_reason": "<stable-code> | null"
  },
  "limits_used": {
    "canonicalization": { "... exact limit object ..." },
    "payoff": { "... exact limit object ..." },
    "validation": { "... exact limit object ..." },
    "diff": { "... exact limit object ..." }
  },
  "schema_metadata": {
    "canonical": { "... deterministic schema metadata ..." },
    "payoff": { "... deterministic schema metadata ..." }
  },
  "provenance": {
    "compiler": "derivatrace.validation-equivalence/1.0.0",
    "policy": "excluded_from_identity",
    "source_left_identity": "canonical:sha256:<hex>",
    "source_right_identity": "canonical:sha256:<hex>"
  }
}
```

Field-by-field rules:

- `report_id` — SHA-256 over the **structural projection** of the report
  (all fields except `provenance` and `report_id` itself), framed as
  `validation-equivalence:sha256:<hex>` with domain tag
  `derivatrace.validation-equivalence.report`, schema version `1.0.0`
  participating in the preimage (§7). If the report is never hashed by the
  caller, the field may be `null` in the in-memory object but must be present
  and correct in any serialized form.
- `requested_level` — the enum value the caller requested (`structural`,
  `canonical`, or `payoff`).
- `canonical_schema_version` / `payoff_schema_version` — the exact schema
  versions used for canonicalization and payoff compilation (echoed from the
  runtime or the caller's override).
- `left_validation_outcome` / `right_validation_outcome` — per-side Stage 1A
  validation outcome using the closed taxonomy `valid | invalid | not_evaluated`.
  `not_evaluated` means the structural stage was not reached (e.g., an internal
  error before validation, or a caller configuration that prevented it). These
  fields are never `null`.
- `canonical_comparison_status` — closed comparison status for the canonical
  representation (see §3.5). One of `equivalent | different | not_comparable |
  not_evaluated`.
- `canonical_comparison_reason` — stable classification code when the status is
  `not_comparable` or `not_evaluated`; `null` for `equivalent`/`different`.
- `payoff_comparison_status` / `payoff_comparison_reason` — same as above for the
  payoff representation.
- `left` / `right` — per-side structured capture (see §3.13):
  - `contract_identity` — present if structural validation passed and
    canonicalization succeeded; otherwise `null`.
  - `payoff_graph_identity` — present if canonicalization and payoff compilation
    both succeeded; otherwise `null`.
  - `structural_errors` — array of Stage 1A `validation.*` error codes if
    invalid; otherwise `null`.
  - `canonicalization_errors` — array of Stage 1B-R1 `canonicalization.*` error
    codes if canonicalization failed; otherwise `null`.
  - `payoff_compilation_errors` — array of Stage 1B-R2 `payoff_graph.*` error
    codes if payoff compilation failed; otherwise `null`.
- `diff_representation` — the selected representation (`canonical | payoff |
  both | none`).
- `diff_summary` — deterministic structural diff (see §4). When unavailable,
  `entries` is empty and `unavailable_reason` carries a stable code; no partial
  content diff is emitted.
- `limits_used` — echoed limit objects (exact types) so the report is
  self-describing.
- `schema_metadata` — deterministic schema metadata (e.g., node classifications,
  hash domain tags) recorded for reproducibility. May be included even when a
  comparison is `not_comparable`.
- `provenance` — compiler tag, exclusion policy, and source canonical identities.
  Excluded from `report_id` preimage (like payoff-graph provenance).

### 3.5 Comparison status taxonomy (closed enum)

For each representation-level comparison the report uses a **closed** status
taxonomy. The four states are distinct and must not be collapsed into a boolean.

| Status | Meaning |
|--------|---------|
| `equivalent` | Both trusted representations were produced under compatible schema rules; their relevant identities are equal. |
| `different` | Both trusted representations were produced under compatible schema rules; their relevant identities differ. |
| `not_comparable` | The requested comparison could not be validly established, including: incompatible schema versions; one or both sides failed an upstream stage; required representation unavailable; explicitly unsupported migration boundary. |
| `not_evaluated` | The caller requested a shallower validation level, so the comparison was not attempted. |

Exact meaning:

- `equivalent` — both sides succeeded through the required upstream stages under
  compatible schema versions and the relevant identities are byte-equal.
- `different` — both sides succeeded through the required upstream stages under
  compatible schema versions and the relevant identities differ.
- `not_comparable` — the comparison could not be validly established. This
  includes incompatible schema versions, upstream stage failures, unavailable
  representations, and explicitly unsupported migration boundaries. It does
  **not** mean `different` or `false`.
- `not_evaluated` — the caller requested a shallower validation level, so this
  comparison was not attempted.

`not_comparable` and `not_evaluated` are distinct: `not_comparable` means a
comparison was attempted but could not be validly established; `not_evaluated`
means no comparison was attempted because the requested level was shallower.

Neither `not_comparable` nor `not_evaluated` may be collapsed into `different`,
`false`, or any boolean-like `not_equivalent`.

Required reason codes:

- `incompatible_schema_versions` — the two sides used incompatible schema
  versions for the compared representation.
- `upstream_stage_failure` — one or both sides failed a required upstream stage
  (structural, canonical, or payoff compilation).
- `representation_unavailable` — the required representation does not exist for
  one or both sides.
- `unsupported_migration_boundary` — the requested comparison crosses an
  explicitly unsupported migration boundary.
- `shallower_level_requested` — the caller requested a shallower validation
  level, so this comparison was not attempted.

### 3.6 Validation outcome taxonomy (closed enum)

Per-side validation outcomes use a closed taxonomy:

| Status | Meaning |
|--------|---------|
| `valid` | The operand passed Stage 1A validation. |
| `invalid` | The operand failed Stage 1A validation (codes captured in `structural_errors`). |
| `not_evaluated` | The structural stage was not reached. |

`null` is never used to mean multiple different states; the three values are
closed and exhaustive.

### 3.7 Left and right identities

Identities are the Stage 1B-R1 `canonical:sha256:<hex>` and Stage 1B-R2
`payoffgraph:sha256:<hex>` strings. They are **not** recomputed by Stage 1C;
they are taken from the Stage 1B runtimes.

### 3.8 Canonical and payoff schema versions used

The report **must** record the exact `CanonicalSchemaVersion` and
`PayoffGraphSchemaVersion` used. If the caller passes `None`, the runtime
defaults are used and recorded. Comparisons across different schema versions
yield `not_comparable` at the corresponding level with reason code
`incompatible_schema_versions` (§3.5, §5). No `equivalent`/`different` claim is
made, and no content structural diff is emitted across the incompatible
representations.

### 3.9 Optional bounded structural-diff summary

See §4. The diff is bounded by `DiffLimits` and may be truncated. When the diff
is unavailable, `diff_summary.entries` is empty and `unavailable_reason` carries
a stable code (§4.17).

### 3.10 Limits used

The report echoes the exact limit objects (or their defaults) so that a
consumer can verify the bounds under which the comparison ran.

### 3.11 Stable serialization and identity policy

Reports are serialized with the canonical JSON rules (§3.3). The `report_id`
hashes the structural projection (excludes `provenance` and `report_id` itself),
so changing provenance alone does not change the report identity. Two reports
with identical structural content have identical `report_id`.

### 3.12 Equality semantics

Two `ValidationEquivalenceReport` instances are equal iff their `report_id`
values are equal (when present and non-null) **or** their structural projections
are byte-equal. The in-memory type implements `__eq__` and `__hash__` on
`report_id` (falling back to structural bytes if `report_id` is `null`).

### 3.13 Hybrid report-versus-exception policy

Stage 1C separates **caller-owned failures** from **operand-owned evaluation
outcomes**.

#### 3.13.1 Caller-owned failures are RAISED (Stage 1C-owned typed errors)

Stage 1C raises a typed error in its own `validation_equivalence` namespace for:

- wrong exact input types at the Stage 1C API boundary;
- unsupported validation level;
- malformed Stage 1C limits;
- unsupported Stage 1C report schema version;
- invalid diff representation selection;
- impossible or contradictory caller configuration;
- report encoding failure;
- report identity collision;
- malformed Stage 1C internal state or invariant failure.

If the report itself cannot be encoded or its identity cannot be produced, **no
report is returned**; the Stage 1C error is raised.

#### 3.13.2 Operand-owned outcomes are CAPTURED inside the report

For either left or right operand, the report captures (rather than raises):

- Stage 1A contract validation failure;
- Stage 1B-R1 canonicalization failure;
- Stage 1B-R2 payoff compilation failure;
- upstream complexity failure;
- upstream encoding or collision error when it belongs to processing one operand
  and a deterministic report can still be formed.

Captured failures contain **stable structured data only**:

- `stage` — the failing stage (`structural`, `canonical`, or `payoff`);
- `code` — the existing upstream error code, in its original namespace
  (`validation.*`, `canonicalization.*`, `payoff_graph.*`);
- `side` — `left` or `right`;
- `classification` — a deterministic classification string.

Captured failures contain **no**:

- raw traceback;
- `repr` of the malformed object;
- unstable exception text;
- secret or full-content leakage.

Upstream error codes retain their original namespace. Stage 1C must **not**
relabel a canonicalization or payoff-graph failure as a Stage 1C error merely
because it appears inside a Stage 1C report.

### 3.14 Use-time exact-type validation

All limit objects, schema-version enums, the `ValidationLevel` enum, and the
`DiffSelection` enum are validated at call time using the same hardened boundary
pattern as `derivatrace.canonical._schema` and `derivatrace.payoffgraph._schema`.
Unknown schema versions are rejected with `validation_equivalence.input`.
Unsupported report schema versions are rejected with
`validation_equivalence.input`.

### 3.15 Provenance policy

Provenance is recorded in the report (compiler tag, exclusion policy, source
canonical identities) but **excluded** from the report identity preimage.
Changing provenance alone does not change `report_id`.

### 3.16 Deterministic provenance policy field

The report carries an explicit `provenance.policy` value
(`excluded_from_identity`) so consumers can verify that provenance does not
participate in identity.

### 3.17 Behaviour when preconditions fail

| Situation | Report outcome |
|-----------|----------------|
| Either Stage 1A contract invalid | `left_validation_outcome`/`right_validation_outcome` = `invalid`; `structural_errors` populated; `canonical_comparison_status`/`payoff_comparison_status` = `not_comparable` (reason `upstream_stage_failure`) when that level was requested, else `not_evaluated`. |
| R1 canonicalization fails | `contract_identity: null`; `canonicalization_errors` populated; `canonical_comparison_status` = `not_comparable` (reason `upstream_stage_failure`) when requested, else `not_evaluated`; `payoff_comparison_status` = `not_evaluated`. |
| R2 payoff-graph compilation fails | `payoff_graph_identity: null`; `payoff_compilation_errors` populated; `payoff_comparison_status` = `not_comparable` (reason `upstream_stage_failure`) when requested, else `not_evaluated`. |
| Canonical schema versions differ | `canonical_comparison_status` = `not_comparable` (reason `incompatible_schema_versions`); `payoff_comparison_status` proceeds only if payoff schemas match; `diff_summary.unavailable_reason` = `incompatible_schema_versions` for the canonical diff; no content structural diff across the incompatible representations. |
| Payoff schema versions differ | `payoff_comparison_status` = `not_comparable` (reason `incompatible_schema_versions`); `diff_summary.unavailable_reason` = `incompatible_schema_versions` for the payoff diff; no content structural diff across the incompatible representations. |
| Limits differ between sides | Limits are per-call, not per-side; the single `limits_used` applies to both. |
| Identities collide at an internal seam (R1 or R2 collision) | The originating runtime raises its collision error (`canonicalization.collision` or `payoff_graph.collision`); Stage 1C captures it in the corresponding error array (`code` retains its original namespace) and marks the relevant comparison as `not_comparable` (reason `upstream_stage_failure`). |
| Only one requested validation level succeeds | Results for deeper levels are `not_evaluated`; the report is still returned. |
| Caller requests unsupported level | `ValidationEquivalenceUnsupportedLevelError` is **raised** (not placed in report), because the request itself is malformed. |
| Caller passes malformed limits | `ValidationEquivalenceInputError` is **raised** (not placed in report). |
| Report encoding fails | `ValidationEquivalenceEncodingError` is **raised**; no partial report is returned. |
| Report identity cannot be produced | `ValidationEquivalenceReportCollisionError` is **raised**; no report is returned. |

## 4. Structural diffing

### 4.1 Representation diffed

The caller selects the representation via `DiffSelection`:

- `"canonical"` — diff the Stage 1B-R1 canonical contract documents (the
  `structural_bytes` of each `CanonicalContract`, i.e. the reachable-only node
  table and root).
- `"payoff"` — diff the Stage 1B-R2 payoff-graph structural documents (the
  `structural_bytes` of each `PayoffGraph`).
- `"both"` — produce two independent diff sections (canonical and payoff).
- `"none"` — no diff; `diff_summary.entries` empty, `truncated: false`.

The default is `"canonical"`.

### 4.2 Stable path syntax

Paths use a **JSON-Pointer-inspired** syntax with the following rules:

- Root is `/`.
- Object member: `/nodes/<node-id>/payload/<field>`.
- Array element: `/nodes/<node-id>/payload/operands/0`.
- Node ids are bare 64-hex strings (no prefix).
- The path always starts from the document root (`{nodes, root, schema_name,
  schema_version}`).
- No URI-encoding; node ids and field names are ASCII-safe by construction.

Examples:

```
/nodes/ff90f90d58c9197c0f65f11af7938c0571e03d9716bbbd7f623483b7f2e4c6f1/payload/operands/0
/nodes/245f56804c0f4df293c96845228b11540e7f06a606c73188115c754b13e0aa5a/payload/amount
/root
/schema_version
```

### 4.3 Operation taxonomy (non-overlapping)

Each diff entry carries an `op`. The four operations are defined so that `change`
and `replace` cannot overlap:

| Op | Meaning |
|----|---------|
| `add` | Path absent on left and present on right. |
| `remove` | Path present on left and absent on right. |
| `change` | Path present on both sides; the **structural role is identical** (same node/payload kind) and only the leaf/scalar value differs. |
| `replace` | Path present on both sides, but the **structural role changed**: the node/payload kind differs, or a leaf became a container, or a container became a leaf. |

Non-overlap guarantee: `change` applies **only** when the structural role is
preserved; `replace` applies **only** when the structural role changed. Because
the two are distinguished by the structural role, they are disjoint by
construction — no path can simultaneously satisfy both.

For arrays, `change` at index `i` means the element at `i` differs while keeping
the same structural role; `add`/`remove` mean length change. **Commutative sorted
operands** (Add, Maximum, Minimum, AllOf, AnyOf, PGAdd, PGMaximum, PGMinimum,
PGAllOf, PGAnyOf) are compared by index in their **canonical sorted order** (by
node id, tie-broken by payload bytes). A reordering that preserves the multiset
appears as a series of `change` entries at each index. **Author-order-preserving
operands** (Subtract, Divide, Comparison, Both, PGSubtract, PGDivide,
PGComparison, PGCombine, etc.) are compared by position; a swap appears as two
`change` entries.

### 4.4 Node-table and root handling

The node table is an object keyed by node id. Diffing treats it as an unordered
map: keys present only in left → `remove` at `/nodes/<id>`; keys only in right →
`add`; keys in both → `change` on the payload (recursively). The `root` field is
a string; a different root id is a `change` at `/root`. A change from a node id
to a non-node-id value (or vice versa) is a `replace` because the structural
role changed.

### 4.5 Commutative sorted operands

For commutative associative nodes (Add, Maximum, Minimum, AllOf, AnyOf and their
payoff counterparts), operands are **already sorted canonically** in the trusted
representation. Diffing compares them positionally in that canonical order. A
difference in multiplicity (duplicate count) appears as `change` at the indices
where the extra duplicate appears in one but not the other.

### 4.6 Author-order-sensitive operands

For author-order nodes (Subtract, Divide, Comparison, Both, ConditionalValue,
Scale, ConditionalContract, and payoff counterparts), operands are compared by
their **author-order position** as preserved in the canonical/payoff
representation. A swap is two `change` entries.

### 4.7 Duplicate references

Duplicate operand references (same node id appearing multiple times) are
**preserved** in the canonical/payoff representation. Diffing sees them as
separate array elements at distinct indices; a difference in duplicate count
appears as `change`/`add`/`remove` at the relevant indices.

### 4.8 Shared versus copied subgraphs

Because canonical and payoff representations are **content-addressed DAGs**,
shared subgraphs appear as **one node** referenced from multiple parents. The
diff operates on the **node table**, not on a tree expansion. A structural change
in a shared node appears once in the node-table diff and is visible at all
referencing paths. The diff does **not** duplicate shared subgraphs.

### 4.9 Provenance fields

Provenance (`provenance` top-level field) is **excluded** from diffing. It is
not part of the structural bytes and does not participate in identity.

### 4.10 Schema metadata

`schema_name` and `schema_version` are diffed like any other field. A version
mismatch appears as a `change` at `/schema_version` **only when both sides use
compatible schema versions** (see §4.17). When schema versions are incompatible,
no content diff is emitted.

### 4.11 Value/unit/currency/timestamp changes

These are leaf values in payloads. A change in `amount.digits`, `currency`,
`settlement_time`, `unit.kind`, `observable_id`, etc. appears as a `change` at
the corresponding leaf path. A change from (e.g.) a `currency` leaf to an object
would be a `replace` because the structural role changed.

### 4.12 Limits

`DiffLimits` (exact positive `int` fields, never `bool`):

| Limit | Default | Purpose |
|-------|---------|---------|
| `max_entries` | `1024` | Maximum diff entries in the report. |
| `max_compared_bytes` | `2_097_152` (2 MiB) | Maximum combined structural bytes of left + right considered for diffing. |
| `max_compared_nodes` | `4096` | Maximum combined reachable nodes considered. |
| `max_path_length` | `256` | Maximum path string length. |

Exceeding any limit causes the diff to **truncate**: `truncated: true`,
`truncation_reason` set to the limiting factor, and no further entries added.
Entries already collected are retained.

### 4.13 Truncation behaviour

Truncation is **deterministic**: the diff algorithm processes paths in
**lexicographic order** (ASCII byte order of the path string). When the limit is
reached, iteration stops immediately. The `truncation_reason` indicates which
limit fired first.

### 4.14 Deterministic ordering

- Node-table keys are iterated in **ascending node-id order** (bare 64-hex,
  ASCII byte order).
- Within a node payload, object keys are iterated in **sorted key order**
  (matching canonical JSON).
- Array indices are iterated in **ascending numeric order**.
- The resulting entry list is already in deterministic order; no post-sort is
  needed.

### 4.15 Complete bytes vs bounded summaries

The diff entries **carry only the differing leaf values** (or `null` for
add/remove). Full subtrees are never embedded. The `left_value` and
`right_value` are JSON values (string, number, boolean, null, object, array) as
they appear in the canonical JSON. The total report size is bounded by
`max_entries` and the size of leaf values.

### 4.16 Iterative algorithm

The diff is implemented iteratively with an explicit stack of `(left_node,
right_node, path)` tuples. No recursion is used. The algorithm:

1. Push `(left_doc, right_doc, "/")` onto stack.
2. While stack not empty and `entries < max_entries`:
   a. Pop.
   b. If both are objects: iterate union of keys in sorted order; for each key,
      push child pair with extended path.
   c. If both are arrays: iterate indices up to `max(len(left), len(right))`;
      push child pair with path `/<index>`.
   d. If both are scalars with the same structural role: if not equal, emit
      `change` entry.
   e. If one is `null` (absent) and other present: emit `add` or `remove`.
   f. If the structural role differs (e.g., scalar vs object, or different
      node/payload kind): emit `replace`.
3. If stack exhausted before limit: `truncated: false`. Else: `truncated: true`
   with reason.

The algorithm visits each comparable pair at most once. Shared subgraphs
(reachable via multiple paths) are compared once per path in this simple
algorithm; a future optimization may memoize visited `(left_id, right_id,
path_prefix)` triples, but the bounded limits make the simple approach
acceptable for v1.0.0.

### 4.17 Diff availability rules

A structural diff is generated **only when**:

- the selected representation exists for both sides;
- both representations use compatible schema versions;
- the selected diff mode is supported;
- limits permit the comparison.

When unavailable, the report records a stable `unavailable_reason` in
`diff_summary` and emits **no** entries. No misleading partial content diff is
emitted when the diff is unavailable. Specifically, when canonical or payoff
schema versions are incompatible, no content structural diff is emitted across
the incompatible representations; the report may still carry deterministic schema
metadata.

## 5. Versioning and compatibility

### 5.1 Schema version compatibility rules

- **Canonical schema** (`derivatrace.contract.canonical`): Any change to
  canonicalization laws, encoding, node classification, or hash domain tags
  requires a version bump. Comparisons across different canonical schema
  versions yield `canonical_comparison_status: not_comparable` with reason code
  `incompatible_schema_versions`. No `equivalent`/`different` claim is made, and
  no content structural diff is emitted across the incompatible representations.
- **Payoff schema** (`derivatrace.payoffgraph`): Same rule. Cross-version payoff
  comparison yields `payoff_comparison_status: not_comparable` with reason code
  `incompatible_schema_versions`.
- **Report schema** (`derivatrace.validation-equivalence.report`): Version
  `1.0.0`. Additive changes (new optional fields) are MINOR; any change to
  existing field meaning, removal, or type change is MAJOR. Consumers must reject
  unknown major versions.

### 5.2 Cross-version comparison policy

**Rejected as a comparison outcome.** Stage 1C does not mediate or translate
across schema versions. If the caller overrides the default schema version on
one side only (or the two sides were produced under different schema versions),
the comparison status at that level is `not_comparable` with reason code
`incompatible_schema_versions`. The report records both versions used and may
include deterministic schema metadata, but makes **no** canonical or payoff
equivalence claim and emits **no** content structural diff across the
incompatible representations.

Cross-version comparison may become possible only through an explicitly
versioned migration or compatibility adapter approved in a later architecture
change.

### 5.3 Migration boundaries

- Schema versions are explicit and monotonic.
- Old identities remain verifiable by recomputing under the recorded version.
- No silent downgrade; a canonical/payoff form claiming an unsupported version
  is rejected at the Stage 1B boundary with `canonicalization.input` or
  `payoff_graph.input`.
- Explicitly unsupported migration boundaries yield `not_comparable` with reason
  `unsupported_migration_boundary`.

### 5.4 Report identity stability across implementation versions

The `report_id` depends only on the **report schema version** and the
**structural content** of the report. A bug-fix release of the Stage 1C runtime
that produces byte-identical reports yields the same `report_id`. A change to the
report schema (field added/removed/renamed) bumps the report schema version and
changes the `report_id` preimage framing.

### 5.5 Compiler/runtime provenance treatment

Provenance is recorded in the report but **excluded** from `report_id`, mirroring
the payoff-graph provenance policy.

### 5.6 Behaviour when a future canonical or payoff schema adds node types

If a future canonical schema adds a node type, the canonical schema version
increments. Stage 1C comparisons under the new version will see the new node type
in the node table and diff it normally. Cross-version comparisons are rejected
(yield `not_comparable`). The diff algorithm is generic over the node table and
requires no update for new node types.

### 5.7 Additive vs breaking report-schema changes

- **Additive (MINOR):** New optional field in `diff_summary`, `limits_used`, or
  `provenance`; new classification code in `canonical_comparison_reason` /
  `payoff_comparison_reason`.
- **Breaking (MAJOR):** Renaming/removing an existing field, changing the type of
  `canonical_comparison_status` / `payoff_comparison_status` / validation
  outcomes, changing the `op` taxonomy, changing the path syntax.

## 6. Limits and security

### 6.1 Deterministic limits

All limits are exact positive integers. The limit objects are:

- `ValidationLimits` (Stage 1A): `max_depth=64`, `max_unique_nodes=4096`.
- `CanonicalizationLimits` (Stage 1B-R1): reuses `ValidationLimits`; adds
  `max_canonical_bytes=4_194_304` (4 MiB).
- `PayoffGraphLimits` (Stage 1B-R2): `max_payoff_nodes=4096`,
  `max_document_bytes=4_194_304`, `max_structural_bytes=2_097_152`.
- `DiffLimits` (Stage 1C): `max_entries=1024`, `max_compared_bytes=2_097_152`,
  `max_compared_nodes=4096`, `max_path_length=256`.

### 6.2 Threat model

Stage 1C inherits the Stage 1A and 1B threat models (`threat-model.md`) and
adds:

- **Adversarially deep graphs** — mitigated by iterative traversal and depth
  limits inherited from Stage 1A.
- **Very wide collections** — mitigated by `max_unique_nodes` / `max_payoff_nodes`
  and `max_entries` in diff.
- **Duplicate-reference amplification** — a DAG with many references to one
  large subgraph does not multiply the diff work because the node table has one
  entry per node id; diff operates on the table.
- **Malformed internal documents** — Stage 1C only consumes trusted
  Stage 1B outputs; malformed documents are rejected at the Stage 1B boundary.
- **Cycles at private seams** — rejected by Stage 1A validation before
  canonicalization.
- **Hash collisions** — SHA-256 collision resistance assumed; collision
  detection in Stage 1B (raise on same id, different payload) carries forward.
- **Confusing Unicode in paths or display labels** — paths use only ASCII node
  ids and field names; no user-supplied strings appear in paths.
- **Accidental leakage of full contract content** — diff entries carry only
  leaf values; the report never embeds full canonical bytes; captured failures
  contain no full-content leakage.
- **Misleading "equivalent" terminology** — the report uses precise enum values
  (`equivalent`, `different`, `not_comparable`, `not_evaluated`) and never the
  word "equivalent" unqualified. The display names are distinct from economic
  claims.
- **Denial of service through oversized diffs** — bounded by `DiffLimits`.
- **Non-deterministic dictionary/set iteration** — all iterations use sorted
  keys (canonical JSON order for objects, node-id order for node table, numeric
  order for arrays).

### 6.3 Processing guarantees

- Iterative (explicit stack), never recursive.
- Bounded by `DiffLimits` and inherited limits.
- Deterministic ordering (sorted keys, node-id order, index order).
- No unbounded allocation.

## 7. Report identity

The report has its own identity, derived from its structural projection:

- **Domain tag:** `derivatrace.validation-equivalence.report`
- **Schema version:** `1.0.0` (participates in preimage)
- **Preimage:** `DOMAIN + 0x00 + "1.0.0" + 0x00 + structural_bytes`
- **Output:** `validation-equivalence:sha256:<lowercase-hex>`

The structural projection excludes `provenance` and `report_id` itself. Two
reports with identical structural content have the same identity.

## 8. Error taxonomy

Stage 1C owns the `validation_equivalence` error namespace. All derive from
`ValidationEquivalenceError` (base, derives from `DerivaTraceError`).

| Exception | Stable `.code` | When raised (caller-owned) |
|-----------|----------------|----------------------------|
| `ValidationEquivalenceError` | `validation_equivalence.error` | Unexpected internal failure / malformed internal state or invariant failure. |
| `ValidationEquivalenceInputError` | `validation_equivalence.input` | Wrong exact input type at the API boundary; malformed limits; unknown/unsupported schema version; invalid enum value; invalid diff representation selection; impossible or contradictory caller configuration. |
| `ValidationEquivalenceUnsupportedLevelError` | `validation_equivalence.unsupported_level` | Caller passes a `level` not in the closed enum. |
| `ValidationEquivalenceIncompatibleSchemasError` | `validation_equivalence.incompatible_schemas` | Reserved for future cross-version mediation; not raised in v1.0.0 (cross-version yields `not_comparable` in report). |
| `ValidationEquivalenceComparisonError` | `validation_equivalence.comparison_failed` | Internal comparison logic failure (should not occur). |
| `ValidationEquivalenceComplexityError` | `validation_equivalence.complexity` | Diff limits exceeded at setup before diffing starts. |
| `ValidationEquivalenceEncodingError` | `validation_equivalence.encoding` | Report serialization failed; **raised**, no partial report returned. |
| `ValidationEquivalenceReportCollisionError` | `validation_equivalence.report_collision` | Two distinct structural projections hash to the same `report_id`; **raised**, no report returned. |
| `ValidationEquivalenceMalformedRepresentationError` | `validation_equivalence.malformed_representation` | A trusted Stage 1B output fails internal consistency checks (e.g., node id not in table, reference to missing node). |

**Caller-owned vs operand-owned policy.** The errors above are **raised** for
caller-owned failures (§3.13.1). Upstream errors (Stage 1A `validation.*`,
Stage 1B-R1 `canonicalization.*`, Stage 1B-R2 `payoff_graph.*`) are
**captured inside the report** (fields `structural_errors`,
`canonicalization_errors`, `payoff_compilation_errors`) and **do not raise**
from `compare_contracts`, provided a deterministic report can still be formed
(§3.13.2). Only the Stage 1C-owned errors above may raise.

Upstream error codes retain their original namespace. Stage 1C must not relabel
a canonicalization or payoff-graph failure as a Stage 1C error merely because it
appears inside a Stage 1C report.

If the report itself cannot be encoded or its identity cannot be produced, no
report is returned; the Stage 1C error is raised.

Rationale: a comparison is a query that normally returns a complete report,
including "left invalid" or "canonicalization failed". Raising would fragment
error handling and lose the per-side granularity. Caller-owned mistakes (wrong
types, unsupported level, malformed limits, unsupported report schema version,
encoding/collision failure) are distinct and are raised because no valid report
can be formed.

## 9. Normative conformance vectors

The following vectors are **planned** for Stage 1C-R1/R2 runtime implementation.
Each vector specifies a stable key, left/right source constructions (using the
public Stage 1A API), requested validation level, and expected outcomes. No
runtime identities are invented here; they will be populated by the future
runtime.

### 9.1 Vector schema

| Field | Meaning |
|-------|---------|
| `key` | Stable vector identifier (e.g., `ve_001_self_equivalence`). |
| `left` | Source contract expression (constructible via public Stage 1A API). |
| `right` | Source contract expression. |
| `level` | Requested `ValidationLevel`. |
| `expect_structural` | `valid` / `invalid` for each side. |
| `expect_canonical` | `equivalent` / `different` / `not_comparable` / `not_evaluated`. |
| `expect_payoff` | `equivalent` / `different` / `not_comparable` / `not_evaluated`. |
| `expect_diff_class` | `empty` / `canonical_diff` / `payoff_diff` / `both_diff` / `truncated` / `none`. |
| `raises` | `""` (no raise) or a Stage 1C error code (caller-owned raised case). |
| `economic_equivalence_claim` | `"never"` (normative: no vector may be described as economically equivalent). |

### 9.2 Vector inventory

| Key | Left | Right | Level | Structural (L/R) | Canonical | Payoff | Diff | Raises | Economic eq. |
|-----|------|-------|-------|------------------|-----------|--------|------|--------|--------------|
| `ve_001_self_equivalence` | `Payment(Add(obs_A, obs_B), USD, T0)` | *same object* | `payoff` | valid / valid | equivalent | equivalent | empty |  | never |
| `ve_002_independent_identical` | `Payment(Add(obs_A, obs_B), USD, T0)` (new allocation) | `Payment(Add(obs_A, obs_B), USD, T0)` (new allocation) | `payoff` | valid / valid | equivalent | equivalent | empty |  | never |
| `ve_003_pgadd_commutation` | `Payment(Add(obs_A, obs_B), USD, T0)` | `Payment(Add(obs_B, obs_A), USD, T0)` | `payoff` | valid / valid | equivalent | equivalent | empty |  | never |
| `ve_004_nested_vs_flat_add` | `Payment(Add(obs_A, Add(obs_B, obs_X)), USD, T0)` | `Payment(Add(obs_A, obs_B, obs_X), USD, T0)` | `payoff` | valid / valid | equivalent | equivalent | empty |  | never |
| `ve_005_pgmultiply_commutation` | `Payment(Multiply(obs_A, Num("2", scalar)), USD, T0)` | `Payment(Multiply(Num("2",s), obs_A), USD, T0)` | `payoff` | valid / valid | equivalent | equivalent | empty |  | never |
| `ve_006_pgmultiply_grouping` | `Payment(Multiply(obs_A, Multiply(Num("2",s), Num("3",s))), USD, T0)` | `Payment(Multiply(Multiply(obs_A, Num("2",s)), Num("3",s)), USD, T0)` | `payoff` | valid / valid | different | different | canonical_diff + payoff_diff |  | never |
| `ve_007_subtract_order` | `Payment(Subtract(obs_A, obs_B), USD, T0)` | `Payment(Subtract(obs_B, obs_A), USD, T0)` | `payoff` | valid / valid | different | different | canonical_diff + payoff_diff |  | never |
| `ve_008_divide_order` | `Scale(Divide(scalar_A, scalar_B), Payment(obs_A, USD, T0))` | `Scale(Divide(scalar_B, scalar_A), Payment(obs_A, USD, T0))` | `payoff` | valid / valid | different | different | canonical_diff + payoff_diff |  | never |
| `ve_009_both_order` | `Both(Payment(obs_A, USD, T0), Payment(obs_B, USD, T0))` | `Both(Payment(obs_B, USD, T0), Payment(obs_A, USD, T0))` | `payoff` | valid / valid | different | different | canonical_diff + payoff_diff |  | never |
| `ve_010_duplicate_add` | `Payment(Add(obs_A, obs_A), USD, T0)` | `Payment(obs_A, USD, T0)` | `payoff` | valid / valid | different | different | canonical_diff + payoff_diff |  | never |
| `ve_011_duplicate_multiply_ref` | `Scale(Multiply(shared, shared), Payment(obs_A, USD, T0))` where `shared = Observable(scalar_A)` | (no direct counterpart; compare against `ve_005`) | `payoff` | valid / valid | different | different | canonical_diff + payoff_diff |  | never |
| `ve_012_duplicate_both` | `Both((shared, shared))` | `Both((shared,))` | `payoff` | valid / valid | different | different | canonical_diff + payoff_diff |  | never |
| `ve_013_shared_vs_copied_subgraph` | `Both((shared, Scale(Num("2",s), shared)))` | `Both((pay1, Scale(Num("2",s), pay2)))` where `shared` = structurally identical | `payoff` | valid / valid | equivalent | equivalent | empty |  | never |
| `ve_014_provenance_only_diff` | Canonical contract A | Canonical contract A (same structure) | `canonical` | valid / valid | equivalent | not_evaluated | empty |  | never |
| `ve_015_settlement_timestamp_diff` | `Payment(Num("1", USD), USD, T0)` | `Payment(Num("1", USD), USD, T0_500ms)` | `payoff` | valid / valid | different | different | canonical_diff + payoff_diff |  | never |
| `ve_016_observation_timestamp_diff` | `Payment(Add(obs_A@T0, obs_B@T0), USD, T0)` | `Payment(Add(obs_A@T0_500ms, obs_B@T0), USD, T0)` | `payoff` | valid / valid | different | different | canonical_diff + payoff_diff |  | never |
| `ve_017_currency_diff` | `Payment(Num("1", USD), USD, T0)` | `Payment(Num("1", EUR), EUR, T0)` | `payoff` | valid / valid | different | different | canonical_diff + payoff_diff |  | never |
| `ve_018_scalar_vs_money_unit` | `Scale(Num("2", scalar), Payment(obs_A, USD, T0))` | `Scale(Num("2", money(USD)), Payment(obs_A, USD, T0))` — invalid right (Stage 1A rejects) | `payoff` | valid / invalid | not_comparable | not_evaluated | empty |  | never |
| `ve_019_comparison_operator_diff` | `Payment(ConditionalValue(Comparison(obs_A, obs_B, GT), obs_A, obs_B), USD, T0)` | `Payment(ConditionalValue(Comparison(obs_A, obs_B, LT), obs_A, obs_B), USD, T0)` | `payoff` | valid / valid | different | different | canonical_diff + payoff_diff |  | never |
| `ve_020_conditional_branch_order` | `Payment(ConditionalValue(cond, obs_A, obs_B), USD, T0)` | `Payment(ConditionalValue(cond, obs_B, obs_A), USD, T0)` | `payoff` | valid / valid | different | different | canonical_diff + payoff_diff |  | never |
| `ve_021_zero_vs_nonzero` | `Zero()` | `Payment(Num("1", USD), USD, T0)` | `payoff` | valid / valid | different | different | canonical_diff + payoff_diff |  | never |
| `ve_022_invalid_left` | `Add(obs_A)` (single operand — invalid) | `Payment(obs_A, USD, T0)` | `structural` | invalid / valid | not_evaluated | not_evaluated | empty |  | never |
| `ve_023_invalid_right` | `Payment(obs_A, USD, T0)` | `Add(obs_A)` | `structural` | valid / invalid | not_evaluated | not_evaluated | empty |  | never |
| `ve_024_incompatible_canonical_schema` | Contract A | Contract A (override canonical schema to 2.0.0 on right) | `canonical` | valid / valid | not_comparable | not_evaluated | none |  | never |
| `ve_025_diff_truncation_at_boundary` | Large contract (4096 nodes) | Same contract + one extra leaf | `payoff` | valid / valid | different | different | truncated (entry_limit) |  | never |
| `ve_026_deterministic_repeated_reporting` | Contract A | Contract A | `payoff` | valid / valid | equivalent | equivalent | empty |  | never |
| `ve_027_incompatible_payoff_schema` | Contract A | Contract A (override payoff schema to 2.0.0 on right) | `payoff` | valid / valid | equivalent | not_comparable | none |  | never |
| `ve_028_unsupported_level_raises` | Contract A | Contract A | `bogus` | valid / valid | — | — | — | `validation_equivalence.unsupported_level` | never |
| `ve_029_malformed_limits_raise` | Contract A | Contract A | `canonical` | valid / valid | — | — | — | `validation_equivalence.input` | never |
| `ve_030_report_encoding_failure_raises` | Contract A | Contract A | `canonical` | valid / valid | — | — | — | `validation_equivalence.encoding` | never |
| `ve_031_deterministic_repeated_captured_failure` | `Add(obs_A)` (single operand — invalid) | `Payment(obs_A, USD, T0)` | `canonical` | invalid / valid | not_comparable | not_evaluated | none |  | never |

**Notes:**

- `obs_A`, `obs_B`, `obs_X` are `Observable(ObservableId("equity", "AAA|BBB|XXX", "close"), T0, Unit.money(USD))`.
- `scalar_A`, `scalar_B` are `Observable(ObservableId("macro", "SCALARA|SCALARB", "level"), T0, Unit.scalar())`.
- `Num("2", scalar)` is `Number(ExactNumber("2"), Unit.scalar())`.
- `T0` = `2030-01-01T00:00:00.000000Z`; `T0_500ms` = `2030-01-01T00:00:00.500000Z`.
- All vectors use the public Stage 1A API; `validate_contract` succeeds on every
  valid source.
- The `expect_canonical` and `expect_payoff` values are **predictions** based on
  the Stage 1B specifications; the future runtime will compute and confirm the
  exact identities.
- `ve_022` and `ve_023` demonstrate that an invalid operand is **captured** in
  the report (`left_validation_outcome`/`right_validation_outcome` = `invalid`;
  `structural_errors` populated); no Stage 1C error is raised.
- `ve_024` demonstrates that incompatible canonical schema versions yield
  `not_comparable` with reason `incompatible_schema_versions` and **no** content
  structural diff.
- `ve_027` demonstrates that incompatible payoff schema versions yield
  `not_comparable` with reason `incompatible_schema_versions` and **no** content
  structural diff; the canonical comparison remains `equivalent`.
- `ve_028`, `ve_029`, and `ve_030` are **caller-owned raised-error** cases: no
  report is returned; the listed Stage 1C error code is raised.
- `ve_031` demonstrates a **deterministic repeated report** that includes a
  captured upstream (Stage 1A) failure: repeated comparisons of the same inputs
  produce byte-identical reports.
- Every vector explicitly states `economic_equivalence_claim: "never"`.
- No vector establishes economic equivalence.

## 10. Documentation guards (normative)

The following properties **must** hold in the repository after this baseline is
merged. They are enforced by `tests/test_documentation.py`:

- Stage 1B is no longer marked "In progress" (Stage 1B-R1: Implemented;
  Stage 1B-R2: Implemented).
- Stage 1C architecture baseline: "Established".
- Stage 1C runtime: "Unimplemented" (no public API, no runtime module).
- No economic-equivalence claim exists in any documentation.
- All three validation-level terms (`structural`, `canonical`, `payoff`) and the
  progressive-processing-depth rule appear in `validation-equivalence-spec.md`.
- The validation-level taxonomy is complete (closed enum, three values).
- The comparison-status taxonomy is closed (`equivalent`, `different`,
  `not_comparable`, `not_evaluated`) and distinct; `not_comparable` and
  `not_evaluated` are never collapsed into `different`/`false`/`not_equivalent`.
- The validation-outcome taxonomy is closed (`valid`, `invalid`,
  `not_evaluated`); `null` is never used to mean multiple states.
- Report schema (`derivatrace.validation-equivalence.report` v1.0.0) is fully
  specified with all fields.
- Structural-diff schema (path syntax, op taxonomy, limits, truncation,
  availability rules) is fully specified.
- Incompatible schema versions never map to `different`/`not_equivalent`/`false`;
  they map to `not_comparable` with reason `incompatible_schema_versions`.
- Every vector key in §9.2 is unique.
- All internal markdown links resolve.
- Status language is consistent across README, ROADMAP, docs/index.md,
  architecture.md.
- The wording "payoff equivalence subsumes canonical equivalence", "payoff
  equivalence proves canonical equivalence", and "the R1-to-R2 mapping is
  permanently injective" does not appear.
