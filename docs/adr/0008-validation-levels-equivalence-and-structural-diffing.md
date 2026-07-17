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
| `not_comparable` | The requested comparison could not be validly established, including: incompatible schema versions; one or both sides failed an upstream stage; required representation unavailable; explicitly unsupported migration boundary. |
| `not_evaluated` | The caller requested a shallower validation level, so the comparison was not attempted. |

**Required meaning:**

- `equivalent` — both sides succeeded through the required upstream stages under
  compatible schema versions and the relevant identities are byte-equal.
- `different` — both sides succeeded through the required upstream stages under
  compatible schema versions and the relevant identities differ.
- `not_comparable` — the comparison could not be validly established. This
  includes incompatible schema versions, upstream stage failures, unavailable
  representations, and explicitly unsupported migration boundaries. It does **not**
  mean "different" or "false".
- `not_evaluated` — the caller requested a shallower validation level, so this
  comparison was not attempted.

Do not collapse `not_comparable` or `not_evaluated` into `false` or
`not_equivalent`. The four states are distinct and closed.

### 5. Validation outcome taxonomy (closed enum)

Per-side validation outcomes use a closed taxonomy:

| Status | Meaning |
|--------|---------|
| `valid` | The operand passed the stage successfully. |
| `invalid` | The operand failed the stage (errors captured in the corresponding error array). |
| `not_evaluated` | The stage was not reached because the caller requested a shallower level or a prior stage failed. |

Do not use `null` to mean multiple different states.

### 6. Report-internal error policy (caller-owned vs. operand-owned)

**RAISE** Stage 1C-owned typed errors for caller-owned failures:

- Wrong exact input types at the Stage 1C API boundary.
- Unsupported validation level.
- Malformed Stage 1C limits.
- Unsupported Stage 1C report schema version.
- Invalid diff representation selection.
- Impossible or contradictory caller configuration.
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
- Existing upstream error code.
- Side: `left` or `right`.
- Deterministic classification.
- No raw traceback.
- No `repr` of the malformed object.
- No unstable exception text.
- No secret or full-content leakage.

Upstream error codes retain their original namespace. Stage 1C must not relabel
a canonicalization or payoff-graph failure as a Stage 1C error merely because it
appears inside a Stage 1C report.

If the report itself cannot be encoded or its identity cannot be produced, no
report is returned; the Stage 1C error is raised.

### 7. Cross-version comparison semantics

**Remove every rule that maps incompatible schema versions directly to**
`not_equivalent`, `different`, or `false`.

The normative result for incompatible schema versions must be:

- Comparison status: `not_comparable`.
- Stable reason code: `incompatible_schema_versions` (or an equally precise
  fixed code).
- No canonical or payoff equivalence claim.
- No content structural diff across the incompatible representations.
- Deterministic schema metadata may still be included in the report.

Cross-version comparison may become possible only through an explicitly
versioned migration or compatibility adapter approved in a later architecture
change.

The incompatible-schema conformance vector is updated accordingly.

Documentation guards prove:

- The specification never says cross-version means `not_equivalent`.
- Incompatible versions produce `not_comparable`.
- No cross-version structural diff is promised.

### 8. Structural diff availability

A structural diff is generated **only when**:

- The selected representation exists for both sides.
- Both representations use compatible schema versions.
- The selected diff mode is supported.
- Limits permit the comparison.

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

Use another exact distinction only if it is demonstrably non-overlapping.

### 10. Updated conformance vectors

Retain the existing 26 vector keys unless a split requires additional vectors.
At minimum update or add cases for:

- `structural` level produces canonical/payoff status `not_evaluated`.
- `canonical` level produces payoff status `not_evaluated`.
- Incompatible canonical schema versions produce `not_comparable`.
- Incompatible payoff schema versions produce `not_comparable`.
- Invalid left operand is captured in the report.
- Invalid right operand is captured in the report.
- Unsupported level raises Stage 1C input/unsupported-level error.
- Malformed limits raise Stage 1C input error.
- Report encoding failure raises rather than returning a partial report.
- No diff when schema versions are incompatible.
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
- Report identity (if retained)
- Deterministic provenance policy

Validation outcomes use the closed taxonomy (`valid`, `invalid`, `not_evaluated`).
Comparison statuses use the closed taxonomy (`equivalent`, `different`,
`not_comparable`, `not_evaluated`). Do not use `null` to mean multiple
different states.

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
   carry only leaf values; `DiffLimits` bounds entries, bytes, nodes, path
   length. Truncation is deterministic.

6. **Ignoring schema-version differences** — Rejected. Schema version
   participates in identity (ADR 0007). Cross-version comparison must yield
   `not_comparable` with a stable reason code.

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
- Stage 1C-R1 implements `compare_contracts`, `ValidationLevel` enum,
  `ValidationEquivalenceReport`, `DiffLimits`, and the error taxonomy.
- Stage 1C-R2 implements the iterative diff algorithm with the specified path
  syntax and operation taxonomy.
- Documentation guards in `tests/test_documentation.py` enforce: no
  economic-equivalence language, taxonomy completeness, report/diff schema
  presence, vector key uniqueness, link resolution, consistent status language,
  independent comparison conclusions, closed comparison status taxonomy.

## Future migration implications

- Adding a fourth validation level (e.g., `certificate` for Stage 4) extends
  the enum and the `results` object additively (MINOR report schema bump).
- Adding `reasons` array with classification codes is additive (MINOR).
- Changing path syntax or `op` taxonomy is breaking (MAJOR).
- Cross-version mediation (if ever added) would introduce a new report field
  and a new error code; current policy rejects it.

---

**Decision recorded:** 2026-07-17. This ADR establishes the Stage 1C
architecture baseline. Implementation proceeds in two runtime increments
(1C-R1, 1C-R2) after baseline review.