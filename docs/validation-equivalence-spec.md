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

When either operand fails Stage 1A validation, all comparison statuses **at or
deeper than the requested level** are `not_comparable` (reason
`upstream_stage_failure`); comparison statuses **shallower than the requested
level** remain `not_evaluated` (reason `shallower_level_requested`):

- Requested `structural`, either operand invalid: `canonical` =
  `not_evaluated` (shallower_level_requested); `payoff` = `not_evaluated`
  (shallower_level_requested).
- Requested `canonical`, either operand invalid: `canonical` =
  `not_comparable` (upstream_stage_failure); `payoff` = `not_evaluated`
  (shallower_level_requested).
- Requested `payoff`, either operand invalid: `canonical` =
  `not_comparable` (upstream_stage_failure); `payoff` = `not_comparable`
  (upstream_stage_failure).

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

#### 3.1.1 Per-call schema selection (never per-side)

`canonical_schema` and `payoff_schema` are **per-call** selections. There is
**exactly one** canonical schema selection and **exactly one** payoff schema
selection for the whole call; neither operand may carry an independent schema
version. Both operands are processed under the same selected canonical schema
version and under the same selected payoff schema version.

Consequences, binding for Stage 1C v1:

- Ordinary `compare_contracts` **cannot** construct a left/right schema-version
  mismatch, because there is no per-side schema input.
- An unsupported `canonical_schema` selection, an unsupported `payoff_schema`
  selection, and a contradictory schema configuration are **caller-owned raised
  Stage 1C errors** (§3.13.1, §8), never captured comparison outcomes.
- No Stage 1C v1 report claims `not_comparable` merely because two sides used
  different schema versions, because the public API cannot construct that state.
- Cross-version comparison of previously generated representations is **outside**
  the Stage 1C v1 public API (§5.2). A future explicitly versioned
  migration/comparison adapter may add that capability through a separate
  architecture decision.

### 3.2 Accepted trusted inputs

- Two `derivatrace.contracts.Contract` instances (validated Stage 1A graphs).
- The function internally validates, canonicalizes, and compiles payoff graphs
  via the Stage 1B runtimes. It does **not** accept pre-canonicalized bytes,
  pre-computed identities, or arbitrary JSON.
- Both operands are processed under the single per-call `canonical_schema` and
  `payoff_schema` selections (§3.1.1).

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
  "report_id": "validation-equivalence:sha256:<hex>",
  "requested_level": "structural | canonical | payoff",
  "canonical_schema_version": "1.0.0",
  "payoff_schema_version": "1.0.0",
  "left_validation_outcome": "valid | invalid",
  "right_validation_outcome": "valid | invalid",
  "canonical_comparison_status": "equivalent | different | not_comparable | not_evaluated",
  "canonical_comparison_reason": "<stable-code> | null",
  "payoff_comparison_status": "equivalent | different | not_comparable | not_evaluated",
  "payoff_comparison_reason": "<stable-code> | null",
  "left": {
    "contract_identity": "canonical:sha256:<hex> | null",
    "payoff_graph_identity": "payoffgraph:sha256:<hex> | null",
    "failures": [
      {
        "stage": "structural | canonical | payoff",
        "code": "<existing upstream namespaced code>",
        "classification": "<closed stable classification>"
      }
    ]
  },
  "right": { "... same shape as left ..." },
  "diff_representation": "canonical | payoff | none",
  "diff_summary": {
    "entries": [
      {
        "path": "/nodes/<left-node-id>",
        "op": "remove",
        "left_value": "<json-value>",
        "right_value": null
      },
      {
        "path": "/nodes/<right-node-id>",
        "op": "add",
        "left_value": null,
        "right_value": "<json-value>"
      },
      {
        "path": "/root",
        "op": "change",
        "left_value": "<left-root-id>",
        "right_value": "<right-root-id>"
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
    "diff": {
      "max_compared_bytes": "...",
      "max_compared_nodes": "...",
      "max_entries": "...",
      "max_report_bytes": "...",
      "max_path_length": "..."
    }
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

- `report_id` — **mandatory and non-null** on every successfully returned
  report. SHA-256 over the **structural projection** of the report (all fields
  except `provenance` and `report_id` itself), framed as
  `validation-equivalence:sha256:<hex>` with domain tag
  `derivatrace.validation-equivalence.report`, schema version `1.0.0`
  participating in the preimage (§7). Report construction includes encoding and
  identity generation; if the report cannot be encoded or its identity cannot be
  produced, **no report is returned** and a Stage 1C error is raised (§3.13.1,
  §8). The serialized and in-memory forms carry the same exact non-null
  `report_id`; there is no nullable in-memory identity (§7).
- `requested_level` — the enum value the caller requested (`structural`,
  `canonical`, or `payoff`).
- `canonical_schema_version` / `payoff_schema_version` — the exact schema
  versions used for canonicalization and payoff compilation (echoed from the
  runtime or the caller's override).
- `left_validation_outcome` / `right_validation_outcome` — per-side Stage 1A
  validation outcome using the closed taxonomy `valid | invalid`. Every valid
  Stage 1C call evaluates Stage 1A for both operands; caller-owned or internal
  failures that prevent validation are raised and return no report. These
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
  - `failures` — the **single** structured captured-failure representation for
    this side. It is **always an array** (an **empty array** on success, never
    `null`), so there is no null-versus-empty ambiguity. Each record is
    `{stage, code, classification}` (§3.13.2). There is no `side` key inside a
    record because the array is already nested under `left` or `right`. The
    deprecated fields `structural_errors`, `canonicalization_errors`, and
    `payoff_compilation_errors` do **not** exist; the same failure is never
    encoded twice.
- `diff_representation` — the selected representation (`canonical | payoff |
  none`). One report contains at most one structural diff section.
- `diff_summary` — deterministic structural diff (see §4). When unavailable,
  `entries` is empty and `unavailable_reason` carries a stable code; no partial
  content diff is emitted.
- `limits_used` — echoed limit objects (exact types) so the report is
  self-describing.
- `schema_metadata` — deterministic schema metadata (e.g., node classifications,
  hash domain tags) recorded for reproducibility. May be included even when a
  comparison is `not_comparable`.
- `provenance` — compiler tag, exclusion policy, and source canonical identities.
  Excluded from `report_id` preimage (like payoff-graph provenance). The exact
  provenance identity rule is: `source_left_identity` / `source_right_identity`
  is the canonical identity when canonicalization was evaluated and succeeded; it
  is `null` when canonicalization was not requested or failed. This is one exact
  rule covering structural-level and failed reports. Provenance remains excluded
  from report identity.

### 3.5 Comparison status taxonomy (closed enum)

For each representation-level comparison the report uses a **closed** status
taxonomy. The four states are distinct and must not be collapsed into a boolean.

| Status | Meaning |
|--------|---------|
| `equivalent` | Both trusted representations were produced (under the single per-call schema selection); their relevant identities are equal. |
| `different` | Both trusted representations were produced (under the single per-call schema selection); their relevant identities differ. |
| `not_comparable` | The requested comparison could not be validly established for a **constructible operand-owned** reason: one or both sides failed a required upstream stage; a required representation is unavailable; or another explicitly defined runtime comparison precondition failed after a valid call began. |
| `not_evaluated` | The caller requested a shallower validation level, so the comparison was not attempted. |

Because `canonical_schema` and `payoff_schema` are per-call selections (§3.1.1),
`not_comparable` is **never** produced because left and right used different
schema versions: ordinary `compare_contracts` cannot construct that state.
Unsupported or contradictory schema selections are raised, not reported (§8).

Exact meaning:

- `equivalent` — both sides succeeded through the required upstream stages under
  the single per-call schema selection and the relevant identities are
  byte-equal.
- `different` — both sides succeeded through the required upstream stages under
  the single per-call schema selection and the relevant identities differ.
- `not_comparable` — the comparison could not be validly established for a
  constructible operand-owned reason: an upstream stage failure, an unavailable
  required representation, or a failed runtime comparison precondition after a
  valid call began. It does **not** mean `different` or `false`, and it is
  **never** caused by a left/right schema-version mismatch.
- `not_evaluated` — the caller requested a shallower validation level, so this
  comparison was not attempted.

`not_comparable` and `not_evaluated` are distinct: `not_comparable` means a
comparison was attempted but could not be validly established; `not_evaluated`
means no comparison was attempted because the requested level was shallower.

Neither `not_comparable` nor `not_evaluated` may be collapsed into `different`,
`false`, or any boolean-like `not_equivalent`.

Required reason codes (closed; all constructible after a valid call began):

- `upstream_stage_failure` — one or both sides failed a required upstream stage
  (structural, canonical, or payoff compilation).
- `representation_unavailable` — the required representation does not exist for
  one or both sides.
- `runtime_precondition_failed` — another explicitly defined runtime comparison
  precondition failed after a valid call began.
- `shallower_level_requested` — the caller requested a shallower validation
  level, so this comparison was not attempted (`not_evaluated`).

There is **no** `incompatible_schema_versions` reason code and **no**
`unsupported_migration_boundary` reason code in Stage 1C v1: the public API
processes both operands under one per-call schema selection (§3.1.1), so a
left/right schema-version mismatch is not constructible, and unsupported or
contradictory schema selections are **raised** (§8), not reported.

### 3.6 Validation outcome taxonomy (closed enum)

Per-side validation outcomes use a closed taxonomy:

| Status | Meaning |
|--------|---------|
| `valid` | The operand passed Stage 1A validation. |
| `invalid` | The operand failed Stage 1A validation (records captured in the per-side `failures` array). |

Every valid Stage 1C call evaluates Stage 1A for both operands. Caller-owned
or internal failures that prevent validation are raised and return no report.
`null` is never used to mean multiple different states; the two values are
closed and exhaustive.

### 3.7 Left and right identities

Identities are the Stage 1B-R1 `canonical:sha256:<hex>` and Stage 1B-R2
`payoffgraph:sha256:<hex>` strings. They are **not** recomputed by Stage 1C;
they are taken from the Stage 1B runtimes.

### 3.8 Canonical and payoff schema versions used

The report **must** record the single per-call `CanonicalSchemaVersion` and
`PayoffGraphSchemaVersion` used (§3.1.1). If the caller passes `None`, the
runtime defaults are used and recorded. Both operands are processed under the
same recorded selections, so both sides always share one canonical schema
version and one payoff schema version.

An unsupported `canonical_schema` selection, an unsupported `payoff_schema`
selection, or a contradictory schema configuration is a **caller-owned raised**
Stage 1C error (§8); it is never reported as a comparison outcome. Cross-version
comparison of previously generated representations is outside the Stage 1C v1
public API and is deferred to a future adapter (§5.2).

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

Two `ValidationEquivalenceReport` instances are equal iff their **mandatory,
non-null** `report_id` values are equal. The in-memory type implements `__eq__`
and `__hash__` on the mandatory `report_id`, backed by the collision defence
(§7, §8). There is no nullable-identity fallback, because `report_id` is never
`null` on a returned report.

### 3.13 Hybrid report-versus-exception policy

Stage 1C separates **caller-owned failures** from **operand-owned evaluation
outcomes**.

#### 3.13.1 Caller-owned failures are RAISED (Stage 1C-owned typed errors)

Stage 1C raises a typed error in its own `validation_equivalence` namespace for:

- wrong exact input types at the Stage 1C API boundary;
- unsupported validation level;
- malformed Stage 1C limits;
- unsupported Stage 1C report schema version;
- invalid diff representation selection (including `"both"`, which is not in
  the v1 `DiffSelection` taxonomy);
- impossible or contradictory caller configuration;
- report encoding failure;
- report identity collision;
- malformed Stage 1C internal state or invariant failure.

If the report itself cannot be encoded or its identity cannot be produced, **no
report is returned**; the Stage 1C error is raised.

#### 3.13.2 Operand-owned outcomes are CAPTURED inside the report

For either left or right operand, the report captures (rather than raises)
operand-owned failures into the **single** per-side `failures` array (§3.4):

- Stage 1A contract validation failure;
- Stage 1B-R1 canonicalization failure;
- Stage 1B-R2 payoff compilation failure;
- upstream complexity failure;
- upstream encoding or collision error when it belongs to processing one operand
  and a deterministic report can still be formed.

**Exact captured-failure record.** Each element of `failures` is one versioned
record with exactly these three fields and no others:

```json
{
  "stage": "structural | canonical | payoff",
  "code": "<existing upstream namespaced code>",
  "classification": "<closed stable classification>"
}
```

Required rules for the captured-failure record:

- `failures` is **always an array**, including an **empty array** on success;
  there is no null-versus-empty ambiguity.
- `stage` — the failing stage, one of `structural`, `canonical`, `payoff`.
- `code` — the existing upstream error code **in its original namespace**
  (`validation.*`, `canonicalization.*`, `payoff_graph.*`); never relabelled.
- `classification` — a value drawn from a **closed documented taxonomy** (§3.13.3).
- No `side` field appears **inside** a record: the array is already nested under
  `left` or `right`, so the side is unambiguous and is never repeated.
- Order is **deterministic** by stage order (`structural`, then `canonical`,
  then `payoff`), then by `code` (ASCII byte order), then by `classification`
  (ASCII byte order).
- The same failure is **never encoded twice**; the deprecated fields
  `structural_errors`, `canonicalization_errors`, and
  `payoff_compilation_errors` do not exist.

Captured-failure records contain **no**:

- raw traceback;
- exception message;
- `repr` of the malformed object;
- unstable exception text;
- malformed object content;
- secret or full-content leakage.

Upstream error codes retain their original namespace. Stage 1C must **not**
relabel a canonicalization or payoff-graph failure as a Stage 1C error merely
because it appears inside a Stage 1C report.

#### 3.13.3 Closed captured-failure classification taxonomy

`classification` is drawn from a closed, documented taxonomy:

| Classification | Meaning |
|----------------|---------|
| `validation_failure` | The operand failed Stage 1A structural validation. |
| `canonicalization_failure` | The operand failed Stage 1B-R1 canonicalization. |
| `payoff_compilation_failure` | The operand failed Stage 1B-R2 payoff compilation. |
| `complexity_failure` | An upstream complexity/limit bound was exceeded. |
| `collision_failure` | An upstream identity collision was detected while processing this operand. |
| `encoding_failure` | An upstream encoding failure occurred while processing this operand. |

The taxonomy is closed and additive-only (new classifications are a MINOR report
schema change; renames/removals are MAJOR, §5.7).

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
| Requested `structural`, either operand invalid | `left_validation_outcome`/`right_validation_outcome` = `invalid` for the failing side; that side's `failures` populated (`stage: structural`); `canonical_comparison_status` = `not_evaluated` (reason `shallower_level_requested`); `payoff_comparison_status` = `not_evaluated` (reason `shallower_level_requested`). |
| Requested `canonical`, either operand invalid | `left_validation_outcome`/`right_validation_outcome` = `invalid` for the failing side; that side's `failures` populated (`stage: structural`); `canonical_comparison_status` = `not_comparable` (reason `upstream_stage_failure`); `payoff_comparison_status` = `not_evaluated` (reason `shallower_level_requested`). |
| Requested `payoff`, either operand invalid | `left_validation_outcome`/`right_validation_outcome` = `invalid` for the failing side; that side's `failures` populated (`stage: structural`); `canonical_comparison_status` = `not_comparable` (reason `upstream_stage_failure`); `payoff_comparison_status` = `not_comparable` (reason `upstream_stage_failure`). |
| R1 canonicalization fails | `contract_identity: null`; that side's `failures` populated (`stage: canonical`); `canonical_comparison_status` = `not_comparable` (reason `upstream_stage_failure`) when requested; `payoff_comparison_status` = `not_comparable` (reason `upstream_stage_failure`) when requested. |
| R2 payoff-graph compilation fails | `payoff_graph_identity: null`; that side's `failures` populated (`stage: payoff`); `payoff_comparison_status` = `not_comparable` (reason `upstream_stage_failure`) when requested; `canonical_comparison_status` retains its actual result when both R1 representations exist. |
| Unsupported canonical schema selection | `ValidationEquivalenceInputError` is **raised** (not placed in report); no report is returned. |
| Unsupported payoff schema selection | `ValidationEquivalenceInputError` is **raised** (not placed in report); no report is returned. |
| Contradictory schema configuration | `ValidationEquivalenceIncompatibleSchemasError` is **raised** (not placed in report); no report is returned. |
| Repeated comparison under the same explicit schema version | Deterministic: repeated calls with the same inputs and the same per-call schema selections produce byte-identical reports with identical `report_id`. |
| Limits differ between sides | Limits are per-call, not per-side; the single `limits_used` applies to both. |
| Identities collide at an internal seam (R1 or R2 collision) | The originating runtime raises its collision error (`canonicalization.collision` or `payoff_graph.collision`); Stage 1C captures it in that side's `failures` (`code` retains its original namespace, `classification: collision_failure`) and marks the relevant comparison as `not_comparable` (reason `upstream_stage_failure`). |
| Only one requested validation level succeeds | Results for deeper levels are `not_evaluated`; the report is still returned. |
| Caller requests unsupported level | `ValidationEquivalenceUnsupportedLevelError` is **raised** (not placed in report), because the request itself is malformed. |
| Caller passes malformed limits | `ValidationEquivalenceInputError` is **raised** (not placed in report). |
| Report encoding fails | `ValidationEquivalenceEncodingError` is **raised**; no partial report is returned. |
| Report identity cannot be produced | `ValidationEquivalenceReportCollisionError` is **raised**; no report is returned. |

## 4. Structural diffing

### 4.1 Representation diffed

Stage 1C-R2 v1 is a **content-addressed document diff**, not a semantic graph
matcher. The caller selects the representation via `DiffSelection`:

- `"canonical"` — diff the Stage 1B-R1 canonical contract structural documents
  (the `structural_bytes` of each `CanonicalContract`, i.e. the reachable-only
  node table and root).
- `"payoff"` — diff the Stage 1B-R2 payoff-graph structural documents (the
  `structural_bytes` of each `PayoffGraph`).
- `"none"` — no diff; `diff_summary.entries` empty, `truncated: false`.

The default is `"canonical"`. A v1 report contains **at most one** structural
diff section; `diff_representation` names that one selected representation or
`none`. The value `"both"` is **not** in the v1 `DiffSelection` taxonomy:
callers needing both canonical and payoff diffs perform two separate comparisons.
Simultaneous independently keyed diff sections are deferred to a future
report-schema version and separate architecture review. Unsupported `"both"`
raises the existing Stage 1C invalid-diff-selection input error.

Each selected structural document is compared **exactly as a versioned JSON
object** of the shape `{schema_name, schema_version, nodes, root}`. The `nodes`
field is a **map keyed by content-derived node ids**. Comparison is over these
exact documents; no author object graph, no tree expansion, and no semantic
alignment is performed.

### 4.2 Content-addressed node identity (trusted assumptions)

Node ids are derived from node content by the trusted Stage 1B runtimes. Under
the trusted collision-resistance assumptions (§6.2):

- **Matching node ids imply byte-identical node records.** If a key exists in
  both node tables, its record is identical on both sides and produces **no
  diff**.
- **A payload change necessarily produces a different node id.** There is no
  such thing as "the same node id with a changed payload".

Therefore a changed node **normally** appears as a node-table key removal on the
left, a node-table key addition on the right, and — when the root id changes — a
`change` at `/root`. The diff never promises leaf-level payload `change` entries
inside a node whose content-addressed id changed, and it never attempts
heuristic or semantic alignment of two different node ids.

### 4.3 Stable path syntax

Paths use a **JSON-Pointer-inspired** syntax with the following rules:

- Root document paths: `/schema_name`, `/schema_version`, `/root`.
- Node-table entry: `/nodes/<node-id>` (bare 64-hex node id, no prefix).
- The path always starts from the document root (`{schema_name, schema_version,
  nodes, root}`).
- No URI-encoding; node ids and field names are ASCII-safe by construction.

Examples:

```
/schema_version
/root
/nodes/ff90f90d58c9197c0f65f11af7938c0571e03d9716bbbd7f623483b7f2e4c6f1
/nodes/245f56804c0f4df293c96845228b11540e7f06a606c73188115c754b13e0aa5a
```

### 4.4 Operation taxonomy (exact-document model, non-overlapping)

Each diff entry carries an `op`. The four operations for this exact-document
model are:

| Op | Meaning |
|----|---------|
| `add` | Path **absent left, present right** (e.g. a node-table key that exists only on the right). |
| `remove` | Path **present left, absent right** (e.g. a node-table key that exists only on the left). |
| `change` | The **same** scalar/document field path exists on both sides and the values differ, such as `/root` or a supported schema-metadata field. |
| `replace` | The **same** path exists on both sides but the JSON structural **kind** differs (scalar/object/array). Expected only at malformed private seams or future explicitly versioned formats. |

Non-overlap guarantee: `change` applies only when both sides carry the same JSON
structural kind at that path and the values differ; `replace` applies only when
the JSON structural kind differs. They are disjoint by construction, so no path
can satisfy both.

### 4.5 Node-table and root handling

The node table is compared as a **map keyed by content-derived node id**:

- key present only in left → `remove` at `/nodes/<left-id>`;
- key present only in right → `add` at `/nodes/<right-id>`;
- key present in both → byte-identical record (§4.2) → **no entry**.

The `root` field is a content-derived node id string; when the root id differs a
single `change` at `/root` is emitted. Because a payload change changes the node
id, an altered node appears as `remove /nodes/<left-id>` + `add /nodes/<right-id>`
(+ `change /root` when the root changed), **never** as a same-id leaf change.

### 4.6 No-diff cases (canonical equivalence)

The following produce **no diff** because they canonicalize to identical
structural bytes:

- **Identical structural bytes** — same document on both sides.
- **Independently allocated but structurally identical inputs** — content
  addressing ignores Python object identity.
- **Commutative author reorderings that canonicalize identically** — e.g.
  `Add(A, B)` vs `Add(B, A)`, or nested-versus-flattened `Add`. These are
  normalised by Stage 1B canonicalization, so the structural documents are
  byte-identical and there is **no diff**. (Prior drafts that described a
  commutative reorder as index-level `change` entries are withdrawn.)
- **Copied versus shared author objects that canonicalize identically** — a
  content-addressed DAG shares equal subgraphs by node-table key, so a "copied"
  and a "shared" author object with the same content yield the same node table
  and **no diff**.

### 4.7 Author-order-sensitive changes

For author-order-sensitive constructs (Subtract, Divide, Comparison, Both,
ConditionalValue, Scale, ConditionalContract, and their payoff counterparts) a
meaningful reordering changes the canonical content and therefore the node ids.
Such a change appears as content-addressed node **removals** and **additions**
and a `/root` `change` as applicable — never as an in-place index `change`.

### 4.8 Duplicate references

Duplicate operand references change node content and therefore node ids. A
difference in duplicate structure appears as content-addressed node
removals/additions (and `/root` change when applicable), reported once per
node-table key.

### 4.9 Shared DAG nodes reported once

Because the structural documents are content-addressed DAGs, a shared node
appears exactly once in the node table. The diff operates on the node-table map,
reports each affected node once by its key, and performs **no recursive tree
expansion**. A node shared by many parents is never multiplied in the diff.

### 4.10 Provenance excluded from structural diff

Provenance is **not** part of the structural bytes and is **excluded** from the
structural diff. It does not participate in identity or in any diff entry.

### 4.11 Schema metadata and schema-version comparison

`schema_name` and `schema_version` are ordinary document fields. Within the
single per-call schema selection (§3.1.1), both sides always carry the same
schema metadata, so no schema-metadata diff arises from a v1
`compare_contracts` call. **Schema-version comparison across different versions
is not performed through this v1 API** (§5.2); a `change` at `/schema_version`
or `/schema_name` is reserved for future explicitly versioned formats.

### 4.12 Semantic alignment is out of scope

Semantic node alignment and human-friendly minimal edit explanations (matching a
removed node to a "corresponding" added node, or explaining *which leaf* changed
inside a re-hashed node) are **explicitly deferred** to a future, separately
specified layer. Stage 1C-R2 v1 reports only exact content-addressed
document differences.

### 4.13 Limits

`DiffLimits` (exact positive `int` fields, never `bool`) are divided into
**admission limits** and **output limits**:

**Admission limits** (input validation, evaluated before diffing begins):

| Limit | Default | Purpose |
|-------|---------|---------|
| `max_compared_bytes` | `2_097_152` (2 MiB) | Maximum combined structural bytes of left + right considered for diffing. |
| `max_compared_nodes` | `4096` | Maximum combined reachable nodes considered. |

**Output limits** (entry emission, evaluated after successful admission):

| Limit | Default | Purpose |
|-------|---------|---------|
| `max_entries` | `1024` | Maximum diff entries in the report. |
| `max_report_bytes` | `8_388_608` (8 MiB) | Maximum serialized report size. |
| `max_path_length` | `256` | Maximum path string length. |

Admission policy:

- Validate limit objects exactly at the API boundary; malformed limits raise
  `validation_equivalence.input`.
- Compute deterministic input sizes before emitting diff entries.
- When an admission limit is exceeded: return the equivalence report; emit
  **zero** diff entries; `truncated` is `false`; `unavailable_reason` is set
  to `comparison_limit_exceeded`; equivalence statuses and identities remain
  available.

Output policy:

- After successful admission, emit entries in the specified deterministic order
  (§4.14).
- Stop before the entry that would exceed an output bound; retain the
  deterministic accepted prefix.
- Set `truncated: true`; set the precise truncation reason.
- Never partially serialize an entry.

### 4.14 Deterministic ordering

Diff entries are emitted in this exact deterministic order:

1. **schema-metadata paths** (`/schema_name`, then `/schema_version`), when
   present (reserved for future explicitly versioned formats, §4.11);
2. **root path** (`/root`);
3. **node removals**, sorted by node id (bare 64-hex, ASCII byte order);
4. **node additions**, sorted by node id (bare 64-hex, ASCII byte order);
5. **any other exact-document paths**, in lexical path order.

The resulting entry list is already in deterministic order; no post-sort is
needed. Identical structural bytes produce no entries.

### 4.15 Truncation behaviour

Truncation is **deterministic**: entries are produced in the order of §4.14, and
when a limit is reached iteration stops immediately with `truncated: true` and
`truncation_reason` set to the limiting factor. Entries already collected are
retained. Truncation must respect **exact entry and byte boundaries** — the
entry that would cross `max_entries` or `max_compared_bytes` is not partially
emitted.

### 4.16 Bounded entry values

Each entry carries only the affected node record or scalar value (or `null` for
the absent side of an `add`/`remove`). For a node removal `left_value` is the
node record and `right_value` is `null`; for a node addition `left_value` is
`null` and `right_value` is the node record; for a `/root` `change` both values
are the respective root id strings. The total report size is bounded by
`DiffLimits`.

### 4.17 Node-table map diff algorithm

The diff is computed over the two structural documents as maps; no recursion and
no tree expansion are used:

1. If `/schema_name` or `/schema_version` differ (future versioned formats
   only), emit those entries first (§4.14).
2. If `root` ids differ, emit a `change` at `/root`.
3. Compute the set difference of node-table keys:
   a. keys only in left → `remove /nodes/<id>` (sorted by id);
   b. keys only in right → `add /nodes/<id>` (sorted by id);
   c. keys in both → identical records (§4.2) → no entry.
4. Stop when the stream is exhausted or a `DiffLimits` boundary is reached
   (§4.15).

Each affected node-table key is visited at most once; a shared DAG node is
reported once by its key (§4.9).

### 4.18 Diff availability rules

A structural diff is generated **only when**:

- the selected representation exists for both sides;
- the selected diff mode is supported;
- limits permit the comparison.

When unavailable, the report records a stable `unavailable_reason` in
`diff_summary` and emits **no** entries. No misleading partial content diff is
emitted when the diff is unavailable. Schema-version comparison across different
versions is not performed through this v1 API (§4.11, §5.2), so it is never a
source of diff content.

## 5. Versioning and compatibility

### 5.1 Schema version compatibility rules

- **Canonical schema** (`derivatrace.contract.canonical`): Any change to
  canonicalization laws, encoding, node classification, or hash domain tags
  requires a version bump. Because both operands are processed under one per-call
  `canonical_schema` selection (§3.1.1), a v1 `compare_contracts` call cannot
  construct a left/right canonical-version mismatch. An **unsupported**
  `canonical_schema` selection is a caller-owned raised error (§8).
- **Payoff schema** (`derivatrace.payoffgraph`): Same rule under one per-call
  `payoff_schema` selection. An **unsupported** `payoff_schema` selection is a
  caller-owned raised error (§8).
- **Report schema** (`derivatrace.validation-equivalence.report`): Version
  `1.0.0`. Additive changes (new optional fields) are MINOR; any change to
  existing field meaning, removal, or type change is MAJOR. Consumers must reject
  unknown major versions.

### 5.2 Cross-version comparison policy (deferred to a future adapter)

**Cross-version comparison of previously generated representations is outside the
Stage 1C v1 public API.** `compare_contracts` processes both operands under one
per-call `canonical_schema` selection and one per-call `payoff_schema` selection
(§3.1.1), so it cannot construct a left/right schema-version mismatch and never
reports `not_comparable` for such a reason. There is no
`incompatible_schema_versions` or `unsupported_migration_boundary` comparison
outcome in v1.

A future capability to compare representations produced under **different**
schema versions may be added **only** through an explicitly versioned
migration/comparison adapter, introduced by a **separate architecture decision**
(ADR 0008, Decision 7). Such an adapter would be a distinct API surface with its
own error codes and report fields; it is **not** part of `compare_contracts` v1.

### 5.3 Migration boundaries

- Schema versions are explicit and monotonic.
- Old identities remain verifiable by recomputing under the recorded version.
- No silent downgrade; a canonical/payoff form claiming an unsupported version
  is rejected at the Stage 1B boundary with `canonicalization.input` or
  `payoff_graph.input`.
- An unsupported Stage 1C schema selection, or a contradictory schema
  configuration, is **raised** by the Stage 1C boundary (§8); it is never a
  reported comparison outcome.

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
increments. Stage 1C comparisons under the new version (selected per-call for
both operands) will see the new node type in the node table and diff it normally.
Comparing representations produced under different versions remains outside the
v1 public API and is deferred to a future adapter (§5.2). The node-table map diff
is generic over node ids and requires no update for new node types.

### 5.7 Additive vs breaking report-schema changes

- **Additive (MINOR):** New optional field in `diff_summary`, `limits_used`, or
  `provenance`; new classification code in `canonical_comparison_reason` /
  `payoff_comparison_reason`; new captured-failure `classification` value.
- **Breaking (MAJOR):** Renaming/removing an existing field (including the
  `failures` array or its record fields), changing the type of
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
- `DiffLimits` (Stage 1C): admission limits `max_compared_bytes=2_097_152`,
  `max_compared_nodes=4096`; output limits `max_entries=1024`,
  `max_report_bytes=8_388_608`, `max_path_length=256`.

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
- **Bounded structural-content disclosure in diff** — node add/remove entries
  contain bounded complete canonical or payoff node records; `/root` and
  metadata changes contain scalar values. The report never embeds the complete
  canonical/payoff document as one field, but a sufficiently large non-truncated
  diff may reveal substantial bounded structural contract content.
  `diff="none"` is the privacy-preserving option when structural content should
  not be disclosed. Report consumers must treat diff entries as potentially
  sensitive contract structure. Captured failures still contain no object repr,
  traceback, exception text, or malformed object content.
- **Misleading "equivalent" terminology** — the report uses precise enum values
  (`equivalent`, `different`, `not_comparable`, `not_evaluated`) and never the
  word "equivalent" unqualified. The display names are distinct from economic
  claims.
- **Denial of service through oversized diffs** — bounded by admission limits
  (`max_compared_bytes`, `max_compared_nodes`) evaluated before diffing, and
  output limits (`max_entries`, `max_report_bytes`, `max_path_length`)
  evaluated after successful admission.
- **Non-deterministic dictionary/set iteration** — all iterations use sorted
  keys (canonical JSON order for objects, node-id order for node table, numeric
  order for arrays).

### 6.3 Processing guarantees

- Iterative (explicit stack), never recursive.
- Bounded by `DiffLimits` and inherited limits.
- Deterministic ordering (sorted keys, node-id order, index order).
- No unbounded allocation.

## 7. Report identity

Every successfully returned report has a **mandatory, validated, non-null**
`report_id`, derived from its structural projection:

- **Domain tag:** `derivatrace.validation-equivalence.report`
- **Schema version:** `1.0.0` (participates in preimage)
- **Preimage:** `DOMAIN + 0x00 + "1.0.0" + 0x00 + structural_bytes`
- **Output:** `validation-equivalence:sha256:<lowercase-hex>`

Report construction includes encoding **and** identity generation. If the report
cannot be encoded, or its identity cannot be produced (or a collision is
detected), **no report is returned** and the corresponding Stage 1C error is
raised (§8). There is **no** nullable in-memory identity: the serialized and
in-memory forms carry the same exact non-null `report_id`.

The structural projection excludes `provenance` and `report_id` itself. Two
reports with identical structural content have the same identity.

**Equality and hashing.** Two `ValidationEquivalenceReport` instances are equal
iff their mandatory `report_id` values are equal; `__hash__` is defined on the
mandatory `report_id`, backed by the collision defence
(`validation_equivalence.report_collision`, §8). A structural-only or failed
report is still fully representable and still carries a mandatory, non-null
`report_id` (its provenance may carry `null` source identities per §3.4).

## 8. Error taxonomy

Stage 1C owns the `validation_equivalence` error namespace. All derive from
`ValidationEquivalenceError` (base, derives from `DerivaTraceError`).

| Exception | Stable `.code` | When raised (caller-owned) |
|-----------|----------------|----------------------------|
| `ValidationEquivalenceError` | `validation_equivalence.error` | Unexpected internal failure / malformed internal state or invariant failure. |
| `ValidationEquivalenceInputError` | `validation_equivalence.input` | Wrong exact input type at the API boundary; malformed limits; **unsupported canonical schema selection**; **unsupported payoff schema selection**; unsupported report schema version; invalid enum value; invalid diff representation selection (including `"both"`). |
| `ValidationEquivalenceUnsupportedLevelError` | `validation_equivalence.unsupported_level` | Caller passes a `level` not in the closed enum. |
| `ValidationEquivalenceIncompatibleSchemasError` | `validation_equivalence.incompatible_schemas` | **Contradictory schema configuration** at the call boundary (a raised caller-owned error). Cross-version comparison of previously generated representations is out of scope for v1 (§5.2) and is not a comparison outcome. |
| `ValidationEquivalenceComparisonError` | `validation_equivalence.comparison_failed` | Internal comparison logic failure (should not occur). |
| `ValidationEquivalenceEncodingError` | `validation_equivalence.encoding` | Report serialization failed; **raised**, no partial report returned. |
| `ValidationEquivalenceReportCollisionError` | `validation_equivalence.report_collision` | Two distinct structural projections hash to the same `report_id`; **raised**, no report returned. |
| `ValidationEquivalenceMalformedRepresentationError` | `validation_equivalence.malformed_representation` | A trusted Stage 1B output fails internal consistency checks (e.g., node id not in table, reference to missing node). |

**Caller-owned vs operand-owned policy.** The errors above are **raised** for
caller-owned failures (§3.13.1), including unsupported canonical/payoff schema
selection and contradictory schema configuration. Upstream errors (Stage 1A
`validation.*`, Stage 1B-R1 `canonicalization.*`, Stage 1B-R2 `payoff_graph.*`)
are **captured inside the report** in the single per-side `failures` array
(§3.4, §3.13.2) and **do not raise** from `compare_contracts`, provided a
deterministic report can still be formed. Only the Stage 1C-owned errors above
may raise.

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
| `expect_diff_class` | `empty` (no diff) / `remove_add_root` (content-addressed node removals/additions and `/root` change, §4.5) / `truncated` / `none` (diff not requested/unavailable). |
| `raises` | `""` (no raise) or a Stage 1C error code (caller-owned raised case). |
| `economic_equivalence_claim` | `"never"` (normative: no vector may be described as economically equivalent). |

`remove_add_root` is the content-addressed result: a changed node is reported as
a node-table `remove` of the left id and an `add` of the right id, plus a
`change` at `/root` when the root id changed (§4.5). No vector produces
same-node-id leaf `change` entries.

### 9.2 Vector inventory

| Key | Left | Right | Level | Structural (L/R) | Canonical | Payoff | Diff | Raises | Economic eq. |
|-----|------|-------|-------|------------------|-----------|--------|------|--------|--------------|
| `ve_001_self_equivalence` | `Payment(Add(obs_A, obs_B), USD, T0)` | *same object* | `payoff` | valid / valid | equivalent | equivalent | empty |  | never |
| `ve_002_independent_identical` | `Payment(Add(obs_A, obs_B), USD, T0)` (new allocation) | `Payment(Add(obs_A, obs_B), USD, T0)` (new allocation) | `payoff` | valid / valid | equivalent | equivalent | empty |  | never |
| `ve_003_pgadd_commutation` | `Payment(Add(obs_A, obs_B), USD, T0)` | `Payment(Add(obs_B, obs_A), USD, T0)` | `payoff` | valid / valid | equivalent | equivalent | empty |  | never |
| `ve_004_nested_vs_flat_add` | `Payment(Add(obs_A, Add(obs_B, obs_X)), USD, T0)` | `Payment(Add(obs_A, obs_B, obs_X), USD, T0)` | `payoff` | valid / valid | equivalent | equivalent | empty |  | never |
| `ve_005_pgmultiply_commutation` | `Payment(Multiply(obs_A, Num("2", scalar)), USD, T0)` | `Payment(Multiply(Num("2",s), obs_A), USD, T0)` | `payoff` | valid / valid | equivalent | equivalent | empty |  | never |
| `ve_006_pgmultiply_grouping` | `Payment(Multiply(obs_A, Multiply(Num("2",s), Num("3",s))), USD, T0)` | `Payment(Multiply(Multiply(obs_A, Num("2",s)), Num("3",s)), USD, T0)` | `payoff` | valid / valid | different | different | remove_add_root |  | never |
| `ve_007_subtract_order` | `Payment(Subtract(obs_A, obs_B), USD, T0)` | `Payment(Subtract(obs_B, obs_A), USD, T0)` | `payoff` | valid / valid | different | different | remove_add_root |  | never |
| `ve_008_divide_order` | `Scale(Divide(scalar_A, scalar_B), Payment(obs_A, USD, T0))` | `Scale(Divide(scalar_B, scalar_A), Payment(obs_A, USD, T0))` | `payoff` | valid / valid | different | different | remove_add_root |  | never |
| `ve_009_both_order` | `Both(Payment(obs_A, USD, T0), Payment(obs_B, USD, T0))` | `Both(Payment(obs_B, USD, T0), Payment(obs_A, USD, T0))` | `payoff` | valid / valid | different | different | remove_add_root |  | never |
| `ve_010_duplicate_add` | `Payment(Add(obs_A, obs_A), USD, T0)` | `Payment(obs_A, USD, T0)` | `payoff` | valid / valid | different | different | remove_add_root |  | never |
| `ve_011_duplicate_multiply_ref` | `Scale(Multiply(shared, shared), Payment(obs_A, USD, T0))` where `shared = Observable(scalar_A)` | (no direct counterpart; compare against `ve_005`) | `payoff` | valid / valid | different | different | remove_add_root |  | never |
| `ve_012_duplicate_both` | `Both((shared, shared))` | `Both((shared,))` | `payoff` | valid / valid | different | different | remove_add_root |  | never |
| `ve_013_shared_vs_copied_subgraph` | `Both((shared, Scale(Num("2",s), shared)))` | `Both((pay1, Scale(Num("2",s), pay2)))` where `shared` = structurally identical | `payoff` | valid / valid | equivalent | equivalent | empty |  | never |
| `ve_014_provenance_only_diff` | Canonical contract A | Canonical contract A (same structure, different provenance only) | `canonical` | valid / valid | equivalent | not_evaluated | empty |  | never |
| `ve_015_settlement_timestamp_diff` | `Payment(Num("1", USD), USD, T0)` | `Payment(Num("1", USD), USD, T0_500ms)` | `payoff` | valid / valid | different | different | remove_add_root |  | never |
| `ve_016_observation_timestamp_diff` | `Payment(Add(obs_A@T0, obs_B@T0), USD, T0)` | `Payment(Add(obs_A@T0_500ms, obs_B@T0), USD, T0)` | `payoff` | valid / valid | different | different | remove_add_root |  | never |
| `ve_017_currency_diff` | `Payment(Num("1", USD), USD, T0)` | `Payment(Num("1", EUR), EUR, T0)` | `payoff` | valid / valid | different | different | remove_add_root |  | never |
| `ve_018_scalar_vs_money_unit` | `Scale(Num("2", scalar), Payment(obs_A, USD, T0))` | `Scale(Num("2", money(USD)), Payment(obs_A, USD, T0))` — invalid right (Stage 1A rejects) | `payoff` | valid / invalid | not_comparable | not_comparable | none |  | never |
| `ve_019_comparison_operator_diff` | `Payment(ConditionalValue(Comparison(obs_A, obs_B, GT), obs_A, obs_B), USD, T0)` | `Payment(ConditionalValue(Comparison(obs_A, obs_B, LT), obs_A, obs_B), USD, T0)` | `payoff` | valid / valid | different | different | remove_add_root |  | never |
| `ve_020_conditional_branch_order` | `Payment(ConditionalValue(cond, obs_A, obs_B), USD, T0)` | `Payment(ConditionalValue(cond, obs_B, obs_A), USD, T0)` | `payoff` | valid / valid | different | different | remove_add_root |  | never |
| `ve_021_zero_vs_nonzero` | `Zero()` | `Payment(Num("1", USD), USD, T0)` | `payoff` | valid / valid | different | different | remove_add_root |  | never |
| `ve_022_invalid_left` | `Add(obs_A)` (single operand — invalid) | `Payment(obs_A, USD, T0)` | `structural` | invalid / valid | not_evaluated | not_evaluated | empty |  | never |
| `ve_023_invalid_right` | `Payment(obs_A, USD, T0)` | `Add(obs_A)` | `structural` | valid / invalid | not_evaluated | not_evaluated | empty |  | never |
| `ve_024_invalid_left_at_payoff_level` | `Add(obs_A)` (single operand — invalid) | `Payment(obs_A, USD, T0)` | `payoff` | invalid / valid | not_comparable | not_comparable | none |  | never |
| `ve_025_admission_byte_boundary_exact` | Large contract (exactly `max_compared_bytes` total structural bytes) | Same contract | `payoff` | valid / valid | equivalent | equivalent | none (admission limit reached, zero entries) |  | never |
| `ve_026_admission_byte_boundary_exceeded` | Large contract (exactly `max_compared_bytes + 1` total structural bytes) | Same contract | `payoff` | valid / valid | equivalent | equivalent | none (admission limit reached, zero entries) |  | never |
| `ve_027_admission_node_boundary_exact` | Large contract (exactly `max_compared_nodes` combined nodes) | Same contract | `payoff` | valid / valid | equivalent | equivalent | none (admission limit reached, zero entries) |  | never |
| `ve_028_admission_node_boundary_exceeded` | Large contract (exactly `max_compared_nodes + 1` combined nodes) | Same contract | `payoff` | valid / valid | equivalent | equivalent | none (admission limit reached, zero entries) |  | never |
| `ve_029_output_entry_boundary_exact` | Large contract producing exactly `max_entries` diff entries | Different contract | `payoff` | valid / valid | different | different | truncated (exact entry boundary) |  | never |
| `ve_030_output_entry_boundary_exceeded` | Large contract producing `max_entries + 1` diff entries | Different contract | `payoff` | valid / valid | different | different | truncated (one beyond entry boundary) |  | never |
| `ve_031_output_report_byte_truncation` | Large contract exceeding `max_report_bytes` | Different contract | `payoff` | valid / valid | different | different | truncated (report byte limit) |  | never |
| `ve_032_admission_failure_preserves_identities` | Large contract exceeding `max_compared_bytes` | Same contract | `payoff` | valid / valid | equivalent | equivalent | none (admission limit preserves identities and statuses) |  | never |
| `ve_033_deterministic_repeated_reporting` | Contract A | Contract A | `payoff` | valid / valid | equivalent | equivalent | empty |  | never |
| `ve_034_invalid_both_diff_selection` | Contract A | Contract A | `canonical` (diff=`both`) | valid / valid | — | — | — | `validation_equivalence.input` | never |
| `ve_035_unsupported_level_raises` | Contract A | Contract A | `bogus` | valid / valid | — | — | — | `validation_equivalence.unsupported_level` | never |
| `ve_036_malformed_limits_raise` | Contract A | Contract A | `canonical` | valid / valid | — | — | — | `validation_equivalence.input` | never |
| `ve_037_report_encoding_failure_raises` | Contract A | Contract A | `canonical` | valid / valid | — | — | — | `validation_equivalence.encoding` | never |
| `ve_038_deterministic_repeated_captured_failure` | `Add(obs_A)` (single operand — invalid) | `Payment(obs_A, USD, T0)` | `canonical` | invalid / valid | not_comparable | not_evaluated | none |  | never |
| `ve_039_upstream_r1_failure_captured` | Contract whose R1 canonicalization fails (e.g. internal complexity bound) | `Payment(obs_A, USD, T0)` | `canonical` | valid / valid | not_comparable | not_evaluated | none |  | never |
| `ve_040_upstream_r2_failure_captured` | Contract whose R2 payoff compilation fails (e.g. payoff complexity bound) | `Payment(obs_A, USD, T0)` | `payoff` | valid / valid | equivalent | not_comparable | none |  | never |
| `ve_041_contradictory_schema_config_raises` | Contract A | Contract A | `canonical` (contradictory schema configuration) | — | — | — | — | `validation_equivalence.incompatible_schemas` | never |
| `ve_042_report_identity_mandatory` | Contract A | Contract B (different structure) | `payoff` | valid / valid | different | different | remove_add_root |  | never |
| `ve_043_unsupported_canonical_schema_raises` | Contract A | Contract A | `canonical` (unsupported `canonical_schema` selection) | — | — | — | — | `validation_equivalence.input` | never |
| `ve_044_unsupported_payoff_schema_raises` | Contract A | Contract A | `payoff` (unsupported `payoff_schema` selection) | — | — | — | — | `validation_equivalence.input` | never |

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
- **No-diff cases (§4.6):** `ve_001`, `ve_002` (independently allocated identical),
  `ve_003` (Add commutation), `ve_004` (nested vs flattened Add), `ve_005`
  (commutative Multiply), and `ve_013` (shared vs copied canonical-equivalent
  subgraphs) all canonicalize identically and produce **no diff**.
- **Content-addressed `remove_add_root` cases (§4.5, §4.7, §4.8):** `ve_006`–`ve_012`,
  `ve_015`–`ve_017`, `ve_019`–`ve_021`, and `ve_042` (author-order-sensitive
  swaps, timestamp/currency/operator changes, and duplicate-reference changes)
  produce content-addressed node removals/additions plus a `/root` change. None
  produces a same-node-id leaf `change`.
- `ve_022` and `ve_023` demonstrate **invalid Stage 1A operand at requested
  `structural` level**: `left_validation_outcome`/`right_validation_outcome` =
  `invalid`, the corresponding side's `failures` array is populated
  (`stage: structural`), `canonical_comparison_status` = `not_evaluated`
  (shallower_level_requested), `payoff_comparison_status` = `not_evaluated`
  (shallower_level_requested); no Stage 1C error is raised.
- `ve_038` demonstrates **invalid Stage 1A operand at requested `canonical`
  level**: `left_validation_outcome` = `invalid`, `failures` populated
  (`stage: structural`), `canonical_comparison_status` = `not_comparable`
  (upstream_stage_failure), `payoff_comparison_status` = `not_evaluated`
  (shallower_level_requested).
- `ve_024` demonstrates **invalid Stage 1A operand at requested `payoff`
  level**: `left_validation_outcome` = `invalid`, `failures` populated
  (`stage: structural`), `canonical_comparison_status` = `not_comparable`
  (upstream_stage_failure), `payoff_comparison_status` = `not_comparable`
  (upstream_stage_failure). `not_evaluated` is never used for a comparison at
  or deeper than the requested level.
- `ve_043` and `ve_044` demonstrate that an **unsupported** canonical or payoff
  schema selection is a caller-owned **raised** error
  (`validation_equivalence.input`); no report is returned. Because
  `canonical_schema` and `payoff_schema` are per-call (§3.1.1), a left/right
  schema-version mismatch cannot be constructed.
- `ve_034` demonstrates that `"both"` is **not** in the v1 `DiffSelection`
  taxonomy; selecting it raises `validation_equivalence.input`.
- `ve_035`, `ve_036`, `ve_037`, and `ve_041` are **caller-owned raised-error**
  cases: no report is returned; the listed Stage 1C error code is raised.
  `ve_041` is a contradictory schema configuration
  (`validation_equivalence.incompatible_schemas`).
- `ve_038` demonstrates a **deterministic repeated failed-operand report** at
  requested `canonical` level: an upstream Stage 1A failure is captured
  (`canonical_comparison_status` = `not_comparable`,
  `payoff_comparison_status` = `not_evaluated`) and repeated comparisons of the
  same inputs produce byte-identical reports with identical `report_id`.
- `ve_039` and `ve_040` demonstrate **upstream R1 / R2 failures captured** in
  the failing side's `failures` array with the **original** upstream code
  (`canonicalization.*` / `payoff_graph.*`); no Stage 1C error is raised.
- `ve_033` and `ve_042` demonstrate that `report_id` is **mandatory,
  non-null, and deterministic** on every successfully returned report.
- `ve_014` demonstrates that provenance-only variation does **not** affect
  `report_id` (provenance is excluded from the structural projection, §7).
- `ve_025`–`ve_028` demonstrate **admission limits** (`max_compared_bytes`,
  `max_compared_nodes`): when exceeded, the report is returned with zero diff
  entries, `truncated: false`, and `unavailable_reason: comparison_limit_exceeded`;
  equivalence statuses and identities remain available.
- `ve_029`–`ve_031` demonstrate **output limits** (`max_entries`,
  `max_report_bytes`): when exceeded, the report retains the deterministic
  accepted prefix and sets `truncated: true` with the precise reason.
- `ve_032` demonstrates that an admission-limit failure preserves comparison
  identities and statuses.
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
- The validation-outcome taxonomy is closed (`valid`, `invalid`); `null` is
  never used to mean multiple states.
- `not_evaluated` in validation outcomes is removed; only `valid`/`invalid`
  remain.
- `"both"` is absent from the v1 `DiffSelection` taxonomy.
- One report has one diff summary (at most one structural diff section).
- Report schema (`derivatrace.validation-equivalence.report` v1.0.0) is fully
  specified with all fields; `report_id` is mandatory, non-null on every
  successfully returned report.
- Structural-diff schema (path syntax, op taxonomy — `add`/`remove`/`change`
  where `change` = identical node kind with differing value; `replace` = differing
  JSON kind — limits, truncation, availability rules, deterministic ordering) is
  fully specified; content-addressed node ids are used and a changed node is
  reported as a node-table `remove` plus node-table `add` plus a `/root` change
  (no same-node-id leaf `change`); semantic alignment is **out of scope** for
  Stage 1C.
- Admission limits (`max_compared_bytes`, `max_compared_nodes`) are separated
  from output limits (`max_entries`, `max_report_bytes`, `max_path_length`);
  admission failure emits zero entries and does not truncate.
- Output-limit failure emits a deterministic truncated prefix.
- Schema selection is **per-call** (one `canonical_schema`, one `payoff_schema`
  per comparison, §3.1.1): a left/right schema-version mismatch is not
  constructible. An **unsupported** canonical/payoff schema selection raises
  `validation_equivalence.input`; a **contradictory** schema configuration raises
  `validation_equivalence.incompatible_schemas`. Neither maps to a
  `not_comparable` report outcome.
- A single captured-failure representation exists: each operand's `failures`
  array holds records `{stage, code, classification}` with the **original**
  upstream (Stage 1A/1B) codes preserved. The deprecated field names
  `structural_errors`, `canonicalization_errors`, and
  `payoff_compilation_errors` do **not** appear anywhere outside this
  deprecation note.
- `failures` is always present (non-null) and is an array (empty on success);
  records carry no `side` field and are ordered deterministically
  (stage → code → classification); `classification` uses the closed taxonomy
  (`validation_failure`, `canonicalization_failure`,
  `payoff_compilation_failure`, `complexity_failure`, `collision_failure`,
  `encoding_failure`).
- `report_id` is mandatory, non-null, and deterministic on every successfully
  returned report; report equality and hashing are defined on `report_id`;
  provenance is excluded from the structural projection that determines identity
  (§7).
- Node add/remove entries may contain complete bounded node records; the threat
  model does not claim leaf-only diffs; `diff="none"` is documented as
  privacy-preserving.
- `ValidationEquivalenceComplexityError` is absent from the v1 error taxonomy.
- Provenance identities are `null` when canonicalization was not requested or
  failed; this is one exact rule covering structural-level and failed reports.
- Stage 1C runtime: **Unimplemented** (no public API, no runtime module exists).
- No economic-equivalence claim exists.
- Vector keys remain unique.
- When either operand fails Stage 1A validation: requested `structural` →
  `canonical` = `not_evaluated`, `payoff` = `not_evaluated`; requested
  `canonical` → `canonical` = `not_comparable` (upstream_stage_failure),
  `payoff` = `not_evaluated` (shallower_level_requested); requested `payoff`
  → `canonical` = `not_comparable` (upstream_stage_failure), `payoff` =
  `not_comparable` (upstream_stage_failure). `not_evaluated` is used only for
  comparisons shallower than the requested level.
- Cross-version representation comparison is **deferred** to a future
  separately-specified adapter described in a separate ADR; no Stage 1C
  cross-version report or adapter exists.
- Commutative constructs (Add, Multiply, and payoff counterparts) and
  nested-vs-flattened Add and shared-vs-copied canonical-equivalent subgraphs
  produce `equivalent`/no-diff; author-order-sensitive constructs (Subtract,
  Divide, Comparison, Both, ConditionalValue, Scale, ConditionalContract, plus
  payoff counterparts) produce content-addressed `remove`/`add`/`/root` diffs.
- Every vector key in §9.2 is unique (44 vectors).
- All internal markdown links resolve.
- Status language is consistent across README, ROADMAP, docs/index.md,
  architecture.md, threat-model.md.
- The wording "payoff equivalence subsumes canonical equivalence", "payoff
  equivalence proves canonical equivalence", and "the R1-to-R2 mapping is
  permanently injective" does not appear.
