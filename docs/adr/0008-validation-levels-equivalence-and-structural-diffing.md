# ADR 0008 — Validation levels, equivalence reporting, and structural diffing

- **Status:** Accepted (Stage 1C architecture baseline)
- **Stage:** 1C (architecture baseline **Established**; runtimes planned:
  Stage 1C-R1 validation levels and equivalence reports, Stage 1C-R2
  deterministic structural diffing).
- **Date:** 2026-07-17
- **Supersedes:** —
- **Superseded by:** —
- **Related issues:** Stage 1C: Validation levels, equivalence reporting, and
  structural diffing (#8); part of Stage 1 (#1).
- **Related specs:** `validation-equivalence-spec.md`,
  `canonicalization-spec.md`, `payoff-graph-spec.md`,
  `canonical-test-vectors.md`, ADR 0001–0007.

## Context

Stage 1A delivered an immutable, typed contract algebra with whole-graph
structural validation (`validate_contract`). Stage 1B-R1 delivered a canonical
contract representation with byte-exact identity (`canonical:sha256:`). Stage
1B-R2 delivered a canonical payoff-graph compilation with byte-exact identity
(`payoffgraph:sha256:`). Both runtimes are deterministic, bounded, and
implemented.

**Frozen upstream runtime defaults (Stage 1C inherits and records these exact
values):**

- `ValidationLimits` (Stage 1A): `max_depth=64`, `max_unique_nodes=4096`.
- `CanonicalizationLimits` (Stage 1B-R1): reuses `ValidationLimits`; adds
  `max_canonical_nodes=16384`, `max_canonical_bytes=8_000_000`.
- `PayoffGraphLimits` (Stage 1B-R2): `max_payoff_nodes=4096`,
  `max_document_bytes=4_194_304`, `max_structural_bytes=2_097_152`.
- `DiffLimits` (Stage 1C): admission limits `max_compared_bytes=2_097_152`,
  `max_compared_nodes=4096`; output limits `max_entries=1024`,
  `max_report_bytes=8_388_608`, `max_path_length=256`.

Stage 1C uses and records the actual selected upstream runtime limit objects.
A caller-supplied `None` resolves to the corresponding frozen runtime default.
Stage 1C does not silently replace Stage 1B defaults. The incorrect
`4_194_304` canonicalization-byte default is removed.

Stage 1C must now define **graded validation levels** and **equivalence
reporting** on top of these foundations, plus **deterministic structural
diffing** over the trusted Stage 1B representations. The goal is to give
callers a precise, reproducible answer to "how do these two contracts relate?"
without ever claiming economic equivalence.

## Problem

Callers need to compare contracts at different semantic depths:

1. **Structural validity only** — does each contract pass Stage 1A validation?
2. **Canonical-contract equivalence** — do they have the same canonical
   identity under the same canonical schema version?
3. **Payoff-graph structural equivalence** — do they compile to the same
   payoff-graph identity under the same payoff schema version?

Callers also need a **deterministic report** recording the outcome at each
level, the schema versions used, the limits applied, and — when identities
differ — a **bounded structural diff** explaining *where* the trusted
representations diverge.

The design must:

- Never imply economic/legal/accounting/tax/model equivalence.
- Use a closed, stable validation-level taxonomy (not free-form strings).
- Define a versioned, immutable report schema with deterministic identity.
- Choose a coherent policy for failures (report-internal vs. raised).
- Specify structural diffing over DAGs (not tree expansion) with stable paths,
  bounded output, and deterministic ordering.
- Define version-compatibility rules for canonical, payoff, and report schemas.
- Set deterministic complexity/security limits.
- Own a Stage 1C error namespace (not reusing Stage 1A/1B codes).

## Decision

### 1. Validation-level taxonomy (closed enum)

Three levels, strict progression by **evaluation depth**:

| Enum key | Display name | Evaluation depth |
|----------|--------------|------------------|
| `structural` | Structural validity | Stage 1A validation only |
| `canonical` | Canonical-contract equivalence | Stage 1A validation + Stage 1B-R1 canonicalization |
| `payoff` | Payoff-graph structural equivalence | Stage 1A validation + Stage 1B-R1 canonicalization + Stage 1B-R2 payoff-graph compilation |

The levels form a **progressive evaluation depth** hierarchy, not a logical
implication hierarchy between equivalence results:

- `structural` performs Stage 1A validation only.
- `canonical` performs Stage 1A validation **and** Stage 1B-R1 canonicalization.
- `payoff` performs Stage 1A validation, Stage 1B-R1 canonicalization, **and**
  Stage 1B-R2 payoff-graph compilation.

Requesting a deeper level causes prior stages to be evaluated. The enum is
closed; unknown values raise `ValidationEquivalenceUnsupportedLevelError`.

### 2. Independent comparison conclusions

Canonical-equivalence and payoff-equivalence are **independently reported
conclusions**. Stage 1C normatively states:

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

### 3. Documentation guards

The following wording is **rejected** and must not appear in documentation or
specifications:

- "payoff equivalence subsumes canonical equivalence"
- "payoff equivalence proves canonical equivalence"
- "the R1-to-R2 mapping is permanently injective"
- Any phrasing that implies a logical implication hierarchy between equivalence
  results across levels.

The validation levels describe **progressive processing depth**; the equivalence
results at each level are **independent comparison conclusions**.

### 4. Comparison status taxonomy (closed enum)

For each representation-level comparison, the report uses a closed status
taxonomy:

| Status | Meaning |
|--------|---------|
| `equivalent` | Both trusted representations were produced under compatible schema rules; their relevant identities are equal. |
| `different` | Both trusted representations were produced under compatible schema rules; their relevant identities differ. |
| `not_comparable` | The requested comparison could not be validly established, including: one or both sides failed an upstream stage; required representation unavailable; failed runtime precondition. |
| `not_evaluated` | The caller requested a shallower validation level, so the comparison was not attempted. |

**Required meaning:**

- `equivalent` — both sides succeeded through the required upstream stages under
  the selected compatible schema versions and the relevant identities are byte-equal.
- `different` — both sides succeeded through the required upstream stages under
  the selected compatible schema versions and the relevant identities differ.
- `not_comparable` — the comparison could not be validly established. This
  includes upstream stage failures, unavailable representations, and failed
  runtime preconditions. It does **not** mean "different" or "false".

  Left/right **schema-version incompatibility is not a report outcome**: because
  schema selection is per-call (one `canonical_schema` and one `payoff_schema`
  for both operands, §1C architecture), a left/right schema mismatch is not
  constructible. An unsupported selection is a raised caller-owned input error;
  a wrong schema type in `canonical_schema` or `payoff_schema` raises
  `validation_equivalence.input`. Cross-version
  comparison is deferred (§7).
- `not_evaluated` — the caller requested a shallower validation level, so this
  comparison was not attempted.

Do not collapse `not_comparable` or `not_evaluated` into `false` or
`not_equivalent`. The four states are distinct and closed.

### 5. Validation outcome taxonomy (closed enum)

Per-side validation outcomes use a closed taxonomy:

| Status | Meaning |
|--------|---------|
| `valid` | The operand passed the stage successfully. |
| `invalid` | The operand failed the stage (failures captured in the corresponding side's `failures` array). |

Every valid Stage 1C call evaluates Stage 1A for both operands. Caller-owned
or internal failures that prevent validation are raised and return no report.
Do not use `null` to mean multiple different states.

### 6. Report-internal error policy (caller-owned vs. operand-owned)

**RAISE** Stage 1C-owned typed errors for caller-owned failures:

- Wrong exact input types at the Stage 1C API boundary.
- Unsupported validation level.
- Unsupported or wrong-schema-type `canonical_schema` / `payoff_schema` selection.
- Malformed Stage 1C limits.
- Unsupported Stage 1C report schema version.
- Invalid diff representation selection.
- Wrong schema type in `canonical_schema` or `payoff_schema` parameter.
- Report encoding failure.
- Report identity collision.
- Malformed Stage 1C internal state or invariant failure.

**CAPTURE INSIDE THE REPORT** for operand-owned evaluation outcomes (per side,
left or right):

- Stage 1A contract validation failure.
- Stage 1B-R1 canonicalization failure.
- Stage 1B-R2 payoff compilation failure.
- Upstream complexity failure.
- Upstream encoding or collision error when it belongs to processing one operand
  and a deterministic report can still be formed.

Captured failures must contain stable structured data only:

- Stage identifier.
- Existing upstream error code (original namespace retained).
- Deterministic classification from the closed taxonomy
  (`validation_failure`, `canonicalization_failure`,
  `payoff_compilation_failure`, `complexity_failure`, `collision_failure`,
  `encoding_failure`).
- No raw traceback.
- No `repr` of the malformed object.
- No unstable exception text.
- No secret or full-content leakage.

The side (`left` or `right`) is **implicit in which `failures` array holds the
record** (the `left`/`right` operand block), not stored as a per-record field.
Records carry only `{stage, code, classification}` and are ordered
deterministically (stage → code → classification). The `failures` array is
always present and is an array (empty on success). The deprecated field names
`structural_errors`, `canonicalization_errors`, and
`payoff_compilation_errors` are not used.

Unsupported or wrong-schema-type caller schema configuration is **not** captured as
a failure; it is a raised caller-owned error (§6 first list, using
`validation_equivalence.input`).

Upstream error codes retain their original namespace. Stage 1C must not relabel
a canonicalization or payoff-graph failure as a Stage 1C error merely because it
appears inside a Stage 1C report.

If the report itself cannot be encoded or its identity cannot be produced, no
report is returned; the Stage 1C error is raised.

### 7. Cross-version comparison semantics

**Remove every rule that maps incompatible schema versions directly to**
`not_equivalent`, `different`, or `false`, and remove the `incompatible_schema_versions`
reason code from the report taxonomy.

Schema selection is **per-call**: a single `canonical_schema` and a single
`payoff_schema` apply to both operands (Stage 1C v1 public API). Because the
schema is selected once for the comparison, a left/right schema-version
mismatch is **not constructible** — there is no per-side schema input. The
normative consequences are:

- An **unsupported** `canonical_schema` / `payoff_schema` selection is a raised
  caller-owned `validation_equivalence.input` error; no report is returned.
- A **wrong schema type** in the `canonical_schema` or `payoff_schema`
  parameter is a raised caller-owned
  `validation_equivalence.input` error; no report is returned.
- Neither an unsupported nor a wrong-schema-type selection produces a
  `not_comparable` report outcome.
- No left/right cross-version report or content structural diff exists.

Cross-version **representation** comparison (comparing two canonical/payoff
identities produced under different schema versions) is **deferred** to a
future separately-specified adapter, described in a separate ADR approved in a
later architecture change. The Stage 1C v1 baseline includes no cross-version
report, no cross-version adapter, and no `incompatible_schema_versions` reason
code.

Documentation guards prove:

- The specification never says cross-version means `not_equivalent`/`different`.
- No per-side schema input exists; left/right schema incompatibility is not a
  report outcome.
- No cross-version structural diff is promised by the Stage 1C v1 baseline.

### 8. Structural diff availability

A structural diff is generated **only when**:

- The selected representation exists for both sides.
- Both representations use compatible schema versions.
- The selected diff mode is supported.
- Limits permit the comparison.

A v1 report contains **at most one** structural diff section;
`diff_representation` names that one selected representation or `none`. The
value `"both"` is **not** in the v1 `DiffSelection` taxonomy: callers needing
both canonical and payoff diffs perform two separate comparisons. Simultaneous
independently keyed diff sections are deferred to a future report-schema
version and separate architecture review. Unsupported `"both"` raises the
existing Stage 1C invalid-diff-selection input error.

When unavailable, report a stable reason rather than emitting a misleading
partial content diff.

### 9. Exact change-versus-replace distinction

The four diff operations are defined so that `change` and `replace` cannot
overlap:

- `add`: path absent on left and present on right.
- `remove`: path present on left and absent on right.
- `change`: scalar or leaf value changed while the structural role remains the
  same.
- `replace`: node/payload kind or structural role changed.

When diffing the node table, node identities are **content-addressed**: a node
whose content changed receives a new id, so the change is reported as a node
`remove` (old id) plus a node `add` (new id), not as a same-id leaf `change`.
The `change` op is reserved for genuinely same-role path changes (notably
`/root`) and for scalar/leaf values at paths that are not node-table entries.
Use another exact distinction only if it is demonstrably non-overlapping.

### 10. Updated conformance vectors

Retain the existing 44 vector keys (§9.2 of the spec) unless a split requires
additional vectors. At minimum update or add cases for:

- `structural` level produces canonical/payoff status `not_evaluated`.
- `canonical` level produces payoff status `not_evaluated`.
- Unsupported canonical schema selection raises `validation_equivalence.input`.
- Unsupported payoff schema selection raises `validation_equivalence.input`.
- Wrong schema type in `canonical_schema` or `payoff_schema` parameter raises
  `validation_equivalence.input`.
- Invalid left operand is captured in the report (`failures`, `stage: structural`).
- Invalid right operand is captured in the report (`failures`, `stage: structural`).
- Unsupported level raises Stage 1C input/unsupported-level error.
- Malformed limits raise Stage 1C input error.
- Report encoding failure raises rather than returning a partial report.
- Upstream R1 canonicalization failure is captured in `failures` with the
  original `canonicalization.*` code.
- Upstream R2 payoff compilation failure is captured in `failures` with the
  original `payoff_graph.*` code.
- Commutative constructs and shared-vs-copied canonical-equivalent subgraphs
  produce equivalent / no-diff.
- Author-order-sensitive constructs produce content-addressed
  `remove`/`add`/`/root` diffs.
- `report_id` is mandatory, non-null, and deterministic on every successful
  report.
- Deterministic repeated report including captured upstream failure.

For every vector preserve the explicit rule that no result establishes economic
equivalence.

### 11. Report schema alignment

The report schema includes unambiguous fields equivalent to:

- `requested_level`
- `left_validation_outcome`
- `right_validation_outcome`
- `canonical_comparison_status`
- `canonical_comparison_reason`
- `payoff_comparison_status`
- `payoff_comparison_reason`
- `diff_representation`
- `diff_summary`
- `truncated`
- `limits`
- Schema metadata
- Report identity (`report_id`, mandatory, non-null, deterministic)
- Deterministic provenance policy

Validation outcomes use the closed taxonomy (`valid`, `invalid`). Comparison
statuses use the closed taxonomy (`equivalent`, `different`,
`not_comparable`, `not_evaluated`). Captured failures use the closed record
shape `{stage, code, classification}` with the classification taxonomy
(`validation_failure`, `canonicalization_failure`, `payoff_compilation_failure`,
`complexity_failure`, `collision_failure`, `encoding_failure`). Do not use
`null` to mean multiple different states.

### 12. Admission-versus-output limit distinction

`DiffLimits` is divided into admission limits (`max_compared_bytes`,
`max_compared_nodes`) and output limits (`max_entries`, `max_report_bytes`,
`max_path_length`). Admission limits are validated at the API boundary and
evaluated before diffing begins; when exceeded, the report is returned with
zero diff entries, `truncated: false`, and `unavailable_reason:
comparison_limit_exceeded`. Output limits are evaluated after successful
admission; when exceeded, the report retains the deterministic accepted prefix
and sets `truncated: true` with the precise reason.

### 13. Bounded structural-content disclosure

Node add/remove entries contain bounded complete canonical or payoff node
records; `/root` and metadata changes contain scalar values. The report never
embeds the complete canonical/payoff document as one field, but a sufficiently
large non-truncated diff may reveal substantial bounded structural contract
content. `diff="none"` is the privacy-preserving option when structural content
should not be disclosed. Report consumers must treat diff entries as
potentially sensitive contract structure. Captured failures still contain no
object repr, traceback, exception text, or malformed object content.

### 14. Exact requested-level status propagation

- requested structural: canonical = `not_evaluated` /
  `shallower_level_requested`, payoff = `not_evaluated` /
  `shallower_level_requested`
- requested canonical, either operand invalid: canonical = `not_comparable` /
  `upstream_stage_failure`, payoff = `not_evaluated` /
  `shallower_level_requested`
- requested payoff, either operand invalid: canonical = `not_comparable` /
  `upstream_stage_failure`, payoff = `not_comparable` /
  `upstream_stage_failure`
- requested canonical, R1 fails: canonical = `not_comparable` /
  `upstream_stage_failure`, payoff = `not_evaluated` /
  `shallower_level_requested`
- requested payoff, R1 fails: canonical = `not_comparable` /
  `upstream_stage_failure`, payoff = `not_comparable` /
  `upstream_stage_failure`
- requested payoff, R2 fails: canonical retains its actual equivalent/different
  result when both R1 representations exist; payoff = `not_comparable` /
  `upstream_stage_failure`

`not_evaluated` is used only when the comparison is strictly deeper than the
requested evaluation level. A requested comparison blocked by an upstream
failure is `not_comparable`, never `not_evaluated`.

### 15. Private-R1 / Public-R2 delivery seam

Stage 1C is delivered in two private increments (R1, R2) before the public API
is exported. The seam between them is specified exactly:

**R1 (private implementation increment):**

- Internal module/package implementation is permitted.
- **No public `compare_contracts` export.**
- **No public Stage 1C API claim** in documentation or packaging.
- Final report schema may be exercised internally.
- Private report construction uses **only** `diff_representation="none"`.
- Exact empty diff summary state:
  ```json
  {
    "entries": [],
    "truncated": false,
    "truncation_reason": null,
    "unavailable_reason": null
  }
  ```
- **No temporary unavailable reason** and **no temporary enum value** (such as
  `diff_not_implemented_r1`) is invented.
- Public vectors are **not** claimed satisfied.
- `ve_014_provenance_only_diff` and `ve_037_report_encoding_failure_raises`
  remain the **exact private-seam vectors**.

**R2 (public implementation increment):**

- Implements **one generic content-addressed document-diff engine**.
- Applies it to **both** canonical structural documents and payoff structural
  documents.
- Implements **both** `diff="canonical"` and `diff="payoff"`.
- Implements admission limits, output limits, ordering, paths, and truncation.
- **Only then** exports `compare_contracts` with its exact permanent signature
  and canonical default `diff: DiffSelection = "canonical"`.

### 16. Frozen limits_used shape

The report echoes the exact limit objects in this exact frozen shape. These
exact field names and integer values participate in report identity:

```json
"limits_used": {
  "validation": {
    "max_depth": "<exact int>",
    "max_unique_nodes": "<exact int>"
  },
  "canonicalization": {
    "max_canonical_nodes": "<exact int>",
    "max_canonical_bytes": "<exact int>"
  },
  "payoff": {
    "max_payoff_nodes": "<exact int>",
    "max_document_bytes": "<exact int>",
    "max_structural_bytes": "<exact int>"
  },
  "diff": {
    "max_compared_bytes": "<exact int>",
    "max_compared_nodes": "<exact int>",
    "max_entries": "<exact int>",
    "max_report_bytes": "<exact int>",
    "max_path_length": "<exact int>"
  }
}
```

### 17. Frozen schema_metadata shape

The report records the exact frozen shape of `schema_metadata`. These exact
field names and values participate in report identity:

```json
"schema_metadata": {
  "canonical": {
    "schema_name": "derivatrace.contract.canonical",
    "schema_version": "1.0.0",
    "node_identity_domain": "derivatrace.canonical.node",
    "representation_identity_domain": "derivatrace.canonical.contract"
  },
  "payoff": {
    "schema_name": "derivatrace.payoffgraph",
    "schema_version": "1.0.0",
    "node_identity_domain": "derivatrace.payoffgraph.node",
    "representation_identity_domain": "derivatrace.payoffgraph.graph"
  }
}
```

Compiler/runtime tags remain in provenance, not in `schema_metadata`.

### 18. Report collision defence without global state

Report construction computes `structural_bytes` from the complete structural
projection and computes `report_id` from those bytes. The immutable report
retains the exact structural bytes privately for integrity and collision checks.

Constructor/factory validation recomputes the identity from structural bytes.
**No process-global registry, persistent cache, or unbounded mutable state
exists.**

Collision behaviour:

- If two report objects carry the same `report_id` but different structural
  bytes, the collision-check seam raises
  `ValidationEquivalenceReportCollisionError`.
- Equality returns `False` for different `report_id` values.
- Equality returns `True` for the same `report_id` and same structural bytes.
- Equality **raises** `ValidationEquivalenceReportCollisionError` for the same
  `report_id` with different structural bytes (the forced collision case).
- `__hash__` remains based on `report_id`.
- The private digest seam may be monkeypatched in tests to force a collision.

### 19. Double-canonicalization consistency rule

`compile_payoff_graph` accepts a Stage 1A `Contract` and internally canonicalizes
it. Stage 1C payoff-level processing therefore:

1. First canonicalizes the operand for the canonical comparison.
2. Then calls `compile_payoff_graph` on the **original** `Contract` using
   **exactly the same** canonical schema, canonicalization limits, and validation
   limits.
3. Verifies `PayoffGraph.source_contract_identity` equals the already-produced
   `CanonicalContract.identity`.
4. Treats mismatch or contradictory second-pass canonicalization behaviour as a
   **Stage 1C internal consistency failure**, not as a fabricated upstream
   failure.
5. Captures genuine `payoff_graph.*` operand-owned failures at `stage=payoff`.
6. **Never** creates a synthetic `payoff_graph.upstream_failure` code.
7. When canonicalization failed, payoff compilation is **not attempted** and the
   original canonical failure is recorded once.

### 20. Preserved failure capture rule

Captured failures use the **original upstream error code in its original
namespace** (`canonicalization.*` or `payoff_graph.*`). Stage 1C must not
relabel an upstream failure as a Stage 1C error merely because it appears inside
a Stage 1C report. No synthetic `payoff_graph.upstream_failure` code exists.

### 21. Implementation-phase classification buckets

The following implementation-phase classification distinguishes vector buckets
without changing any normative `Kind` value:

| Bucket | Description | Count |
|--------|-------------|-------|
| `complete_public` | Complete public vector satisfied (public API) | 0 |
| `supporting_r1_private` | Supporting R1 facts testable privately, but complete public vector unsatisfied | 34 |
| `private_r1_seam` | Private R1 seam (`ve_014`, `ve_037`) | 2 |
| `fully_r2_dependent` | Fully R2-dependent (diff engine) | 8 |

The exact private R1 seams are:

- `ve_014_provenance_only_diff`
- `ve_037_report_encoding_failure_raises`

The exact fully R2-dependent vectors (defining normative behaviour requires the
R2 diff engine) are:

- `ve_025_admission_byte_boundary_exact`
- `ve_026_admission_byte_boundary_exceeded`
- `ve_027_admission_node_boundary_exact`
- `ve_028_admission_node_boundary_exceeded`
- `ve_029_output_entry_boundary_exact`
- `ve_030_output_entry_boundary_exceeded`
- `ve_031_output_report_byte_truncation`
- `ve_032_admission_failure_preserves_identities`

No `public_api` vector may be relabelled `private_seam`. The normative `Kind`
values remain exactly 42 `public_api` and 2 `private_seam`. Bucket counts sum
to 44.

---

## Rejected alternatives

1. **Single Boolean `equivalent` field** — Rejected. Conflates distinct
   semantic levels and invites economic-equivalence misreading. The three-level
   taxonomy with explicit `not_evaluated` and `not_comparable` is necessary.

2. **Claiming economic equivalence from structural identity** — Rejected.
   Violates the conservative principle (ADR 0002, ADR 0007, canonicalization
   spec §12). Report uses precise enum values and never the unqualified word
   "equivalent" in a way that could be misread.

3. **Diffing the mutable author object graph directly** — Rejected. Author
   graphs are not canonicalized (operand order, spelling, duplicates, sharing
   vary). Diff must operate on the **trusted, canonicalized, reachable-only**
   Stage 1B representations.

4. **Recursive traversal for diffing** — Rejected. Deep graphs exhaust the
   call stack. Iterative with explicit stack is required.

5. **Unbounded full-content reports** — Rejected. DoS vector. Diff entries
   carry bounded complete node records for node add/remove entries, and scalar
   values for root and metadata changes; the full structural document is not
   embedded as one field; `diff="none"` is the privacy-preserving option.
   `DiffLimits` bounds entries, bytes, nodes, path length. Truncation is
   deterministic.

6. **Ignoring schema-version differences** — Rejected. Schema version
   participates in identity (ADR 0007). Cross-version comparison is deferred to
   a future adapter (separate ADR); a left/right schema-version mismatch is not
   constructible because schema selection is per-call, and an unsupported or
   contradictory selection is a raised caller-owned error.

7. **AI-generated equivalence explanations inside the deterministic core** —
   Rejected. The deterministic core produces only structural facts. Any
   natural-language summary is an assistive layer outside the core.

8. **Raising upstream errors instead of capturing in report** — Rejected.
   Would force callers to catch multiple exception types to get a complete
   picture. The report is the single answer object.

9. **Tree expansion for shared-subgraph diffing** — Rejected. Would duplicate
   shared DAG nodes unboundedly. Node-table diff (one entry per node id) is
   correct and bounded.

10. **Free-form string validation levels** — Rejected. Closed enum ensures
    static analysis, exhaustive handling, and stable serialization.

11. **Logical implication hierarchy between equivalence levels** — Rejected.
    The levels describe evaluation depth; the equivalence conclusions are
    independent. Payoff equivalence does not imply canonical equivalence.

---

## Consequences

- Callers get a precise, reproducible, versioned report with explicit
  per-level outcomes and a bounded structural diff.
- No economic-equivalence claim is possible from the report schema or
  vocabulary.
- Stage 1C-R1 implements `ValidationLevel` enum, `ValidationEquivalenceReport`,
  `DiffLimits`, and the error taxonomy. **R1 does not export `compare_contracts`.**
- Stage 1C-R2 implements the generic content-addressed document-diff engine for
  both canonical and payoff representations, implements both `diff="canonical"`
  and `diff="payoff"`, implements admission limits, output limits, ordering,
  paths, and truncation. **Only then** is `compare_contracts` exported with its
  exact permanent signature and canonical default.
- Documentation guards in `tests/test_documentation.py` enforce: no
  economic-equivalence language, taxonomy completeness, report/diff schema
  presence, vector key uniqueness, link resolution, consistent status language,
  independent comparison conclusions, closed comparison status taxonomy, single
  captured-failure representation, mandatory `report_id`, content-addressed
  diff model, per-call schema selection (no left/right incompatibility outcome),
  cross-version comparison deferral, exact frozen upstream defaults, absent
  incorrect canonicalization default, R1 private seam (no public export, exact
  no-diff state, no temporary unavailable reason), R2 requires both canonical
  and payoff diff, frozen `limits_used` shape, frozen `schema_metadata` shape,
  identity participation of `schema_metadata` and `limits_used`, no global
  collision registry, explicit collision behaviour, double-canonicalization
  consistency rule, no synthetic `payoff_graph.upstream_failure` code, 42
  `public_api` and 2 `private_seam` vectors with exact keys `ve_014` and
  `ve_037`, all runtime-status guards accurate.

## Future migration implications

- Adding a fourth validation level (e.g., `certificate` for Stage 4) extends
  the enum and the `results` object additively (MINOR report schema bump).
- Adding `reasons` array with classification codes is additive (MINOR).
- Changing path syntax or `op` taxonomy is breaking (MAJOR).
- Cross-version mediation (if ever added) would introduce a new report field
  and a new error code; current policy defers it to a separately-specified
  adapter via a separate ADR.

---

**Decision recorded:** 2026-07-17. This ADR establishes the Stage 1C
architecture baseline. Implementation proceeds in two runtime increments
(1C-R1, 1C-R2) after baseline review.
