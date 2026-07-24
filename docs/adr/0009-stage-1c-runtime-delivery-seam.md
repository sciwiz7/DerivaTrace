# ADR 0009 — Stage 1C runtime delivery seam (R1 private, R2 private, public after R2)

- **Status:** Accepted (Stage 1C architecture baseline)
- **Stage:** 1C (architecture baseline **Established**; private runtimes planned:
  Stage 1C-R1 validation levels and equivalence reports, Stage 1C-R2
  deterministic structural diffing; public API only after R2).
- **Date:** 2026-07-20
- **Supersedes:** —
- **Superseded by:** —
- **Related issues:** Stage 1C: Validation levels, equivalence reporting, and
  structural diffing (#8); part of Stage 1 (#1).
- **Related specs:** `validation-equivalence-spec.md` (§3.18, §3.19, §3.20, §3.21,
  §9.3), ADR 0008 (§15–§21).

## Context

ADR 0008 establishes the Stage 1C architecture baseline: graded validation
levels, deterministic equivalence reporting, and structural diffing over trusted
Stage 1B representations. The specification defines the exact public API
signature, report schema, diff model, error taxonomy, and 44 normative
conformance vectors.

Implementation must proceed in two private increments (R1, R2) before any
public Stage 1C API is exported. This ADR defines the exact seam between those
increments and the public export gate.

## Decision

### R1 — Private implementation increment (validation levels and equivalence reports)

**Permitted:**

- Internal module/package implementation under `derivatrace._validationequivalence`
  or similar private namespace.
- Exercise of the final report schema (construction, serialization, identity).
- Construction of equivalence reports with `diff_representation="none"` only.
- Empty diff summary state:
  ```json
  {
    "entries": [],
    "truncated": false,
    "truncation_reason": null,
    "unavailable_reason": null
  }
  ```
- Capture of upstream failures (Stage 1A, Stage 1B-R1, Stage 1B-R2) into the
  single per-side `failures` array with original upstream codes.
- Verification of the double-canonicalization consistency rule (§3.20 of spec,
  §19 of ADR 0008): `compile_payoff_graph` uses the same canonical schema,
  canonicalization limits, and validation limits as the first canonicalization
  pass; `PayoffGraph.source_contract_identity` must equal the already-produced
  `CanonicalContract.identity`.

**Forbidden:**

- **No public `compare_contracts` export.**
- **No public Stage 1C API claim** in documentation, packaging, or `__all__`.
- No temporary unavailable reason (e.g., `diff_not_implemented_r1`) invented.
- No temporary enum value added to `DiffSelection`.
- Public conformance vectors (`ve_001`–`ve_013`, `ve_015`–`ve_036`, `ve_038`–`ve_044`)
  are **not** claimed satisfied.
- Only the two exact private-seam vectors are testable in R1:
  - `ve_014_provenance_only_diff` (report-construction / identity-projection seam).
  - `ve_037_report_encoding_failure_raises` (injected deterministic report-encoder failure seam).

### R2 — Private implementation increment (deterministic structural diffing)

**Permitted:**

- Implementation of **one generic content-addressed document-diff engine**.
- Application of that engine to **both** canonical structural documents and payoff
  structural documents.
- Implementation of **both** `diff="canonical"` and `diff="payoff"`.
- Implementation of admission limits (`max_compared_bytes`, `max_compared_nodes`),
  output limits (`max_entries`, `max_report_bytes`, `max_path_length`), deterministic
  ordering (§4.14 of spec), stable path syntax (§4.3), operation taxonomy (§4.4),
  and truncation behaviour (§4.15).
- Exercise of all 44 conformance vectors, including boundary vectors
  `ve_025`–`ve_031`.

**Forbidden:**

- No public `compare_contracts` export until R2 is complete and all vectors pass.

### Public export gate (after R2)

**Only after R2 is complete and all 44 vectors pass:**

- Export `compare_contracts` with its exact permanent signature:
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
- Canonical default `diff: DiffSelection = "canonical"` retained.
- Documentation updated: Stage 1C runtime status becomes "Implemented" (public).
- All 44 vectors claimed satisfied.

### Vector implementation-phase classification

The 44 normative vectors are classified by implementation-phase bucket without
changing their normative `Kind` (`public_api` / `private_seam`):

| Bucket | Description | Vectors | Count |
|--------|-------------|---------|-------|
| `complete_public` | Complete public vector satisfied (public API) | — | 0 |
| `supporting_r1_private` | Supporting R1 facts testable privately, but complete public vector unsatisfied | `ve_001_self_equivalence`, `ve_002_independent_identical`, `ve_003_pgadd_commutation`, `ve_004_nested_vs_flat_add`, `ve_005_pgmultiply_commutation`, `ve_006_pgmultiply_grouping`, `ve_007_subtract_order`, `ve_008_divide_order`, `ve_009_both_order`, `ve_010_duplicate_add`, `ve_011_duplicate_multiply_ref`, `ve_012_duplicate_both`, `ve_013_shared_vs_copied_subgraph`, `ve_015_settlement_timestamp_diff`, `ve_016_observation_timestamp_diff`, `ve_017_currency_diff`, `ve_018_scalar_vs_money_unit`, `ve_019_comparison_operator_diff`, `ve_020_conditional_branch_order`, `ve_021_zero_vs_nonzero`, `ve_022_invalid_left`, `ve_023_invalid_right`, `ve_024_invalid_left_at_payoff_level`, `ve_033_deterministic_repeated_reporting`, `ve_034_invalid_both_diff_selection`, `ve_035_unsupported_level_raises`, `ve_036_malformed_limits_raise`, `ve_038_deterministic_repeated_captured_failure`, `ve_039_upstream_r1_failure_captured`, `ve_040_upstream_r2_failure_captured`, `ve_041_wrong_schema_type_raises`, `ve_042_report_identity_mandatory`, `ve_043_unsupported_canonical_schema_raises`, `ve_044_unsupported_payoff_schema_raises` | 34 |
| `private_r1_seam` | Private R1 seam | `ve_014_provenance_only_diff`, `ve_037_report_encoding_failure_raises` | 2 |
| `fully_r2_dependent` | Fully R2-dependent (diff engine) | `ve_025_admission_byte_boundary_exact`, `ve_026_admission_byte_boundary_exceeded`, `ve_027_admission_node_boundary_exact`, `ve_028_admission_node_boundary_exceeded`, `ve_029_output_entry_boundary_exact`, `ve_030_output_entry_boundary_exceeded`, `ve_031_output_report_byte_truncation`, `ve_032_admission_failure_preserves_identities` | 8 |

The two exact `private_seam` vectors remain:

- `ve_014_provenance_only_diff` (report-construction / identity-projection seam).
- `ve_037_report_encoding_failure_raises` (injected deterministic report-encoder failure seam).

No `public_api` vector may be relabelled `private_seam`. Normative `Kind`
values remain exactly 42 `public_api` and 2 `private_seam`.

## Consequences

- Stage 1C public runtime remains **Unimplemented** after R1 and after R2
  (until the public export gate).
- Documentation guards in `tests/test_documentation.py` enforce:
  - R1 has no public `compare_contracts` export.
  - R1 uses only `diff="none"` with exact empty diff state.
  - No temporary unavailable reason or enum value exists.
  - Public vectors not claimed satisfied in R1.
  - Only `ve_014` and `ve_037` are private seams.
  - Public export occurs only after R2 with both canonical and payoff diff.
- The exact frozen `limits_used` shape (§3.10 of spec, §16 of ADR 0008) and
  `schema_metadata` shape (§3.11 of spec, §17 of ADR 0008) participate in
  report identity from R1 onward.
- Report collision defence without global state (§3.19 of spec, §18 of ADR 0008)
  is implemented in R1.
- Double-canonicalization consistency rule (§3.20 of spec, §19 of ADR 0008) is
  implemented in R1.
- No synthetic `payoff_graph.upstream_failure` code is ever created (§3.21 of
  spec, §20 of ADR 0008).

## Rejected alternatives

1. **Export `compare_contracts` in R1 with `diff="none"` only** — Rejected.
   Creates a temporary public API surface with a temporary diff restriction;
   callers would observe a partial implementation and the default
   `diff="canonical"` would silently change behaviour in R2.

2. **Invent a temporary `diff_not_implemented_r1` unavailable reason** —
   Rejected. Introduces a non-final enum value and reason code that must be
   removed, creating migration burden and confusion.

3. **Implement canonical diff in R1, payoff diff in R2** — Rejected. The diff
   engine is generic over content-addressed structural documents; splitting it
   duplicates logic and defers the payoff diff arbitrarily. Both representations
   must be exercised together.

4. **Claim public vectors satisfied in R1** — Rejected. Public vectors require
   the complete public API including diff; R1 does not provide diff.

---

**Decision recorded:** 2026-07-20. This ADR defines the Stage 1C runtime delivery
seam. Implementation proceeds: R1 (private) → R2 (private) → public export gate.