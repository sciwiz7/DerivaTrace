# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to semantic versioning once a stable release is published.

## [Unreleased]

### Added (Stage 1C-R1B — Private orchestration runtime, implemented)

- `derivatrace.validation_equivalence._orchestration`: private `_compare_contracts`
  orchestrating independent Stage 1A validation, canonicalization, and payoff
  compilation with deterministic equivalence-report construction through the
  existing R1A report builder.
- Caller-owned configuration validation with exact-type checks for all
  arguments; unsupported diff selections and non-`ValidationLevel` values
  rejected before any operand processing.
- Per-side structural/canonical/payoff progression with upstream error capture
  using original namespaced codes and documented classifications.
- Second-pass consistency: internal canonicalization mismatch raises
  `ValidationEquivalenceComparisonError`; source-identity mismatch raises
  `ValidationEquivalenceMalformedRepresentationError`.
- Deterministic comparison-status calculation: equivalent, different,
  not_comparable, not_evaluated with correct `ComparisonReason` values.
- `ValidationEquivalenceUnsupportedLevelError`
  (`validation_equivalence.unsupported_level`) and
  `ValidationEquivalenceComparisonError` (`validation_equivalence.comparison_failed`)
  added to the seven-class Stage 1C error taxonomy.
- `diff_representation="none"` only (R1 constraint); exact R1 empty diff
  state enforced.
- 49 focused orchestration tests covering caller boundary, structural,
  canonical, payoff, internal consistency, and report integration.
- Full coverage, Ruff, and mypy clean.

### Added (Stage 1A — Immutable contract algebra and runtime type system)

- `derivatrace.contracts`: an immutable, strongly typed contract AST and a
  deterministic structural validator, with no pricing, models, or engines.
- Exact-domain value objects: `ExactNumber`, `Currency`, `Unit`/`UnitKind`,
  `ObservableId`, `ObservationTime`, `SettlementTime`.
- Scalar expression nodes (`Number`, `Observable`, `Add`, `Subtract`,
  `Multiply`, `Divide`, `Negate`, `Maximum`, `Minimum`, `ConditionalValue`).
- Boolean expression nodes (`BooleanConstant`, `Comparison`, `AllOf`, `AnyOf`,
  `Not`).
- Contract nodes (`Zero`, `Payment`, `Both`, `Scale`, `ConditionalContract`).
- `validate_contract`, returning deterministic `ContractMetrics` (unique node
  count and maximum depth), with iterative traversal, cycle detection, DAG
  sharing, and complexity limits.
- A stable error taxonomy (`DerivaTraceError`, `ContractError`,
  `ContractInputError`, `ContractTypeMismatchError`, `ContractValidationError`,
  `ContractCycleError`, `ContractComplexityError`) carrying structural paths.
- 100% statement and branch coverage; strict mypy; Ruff clean.

### Not implemented

- Canonicalization, canonical contract identity, serialization, hashing, the
  payoff graph, models, numerical engines, market data, and evidence
  certificates remain outside Stage 1A.

### Added (Stage 1B — Canonical architecture baseline, Complete)

- A rigorous Stage 1B design baseline specifying the canonical contract
  representation and canonical payoff graph (specification; no runtime code
  belongs to the baseline spec itself).
- `docs/canonicalization-spec.md` — canonical schema (`derivatrace.contract
  .canonical` `1.0.0`), canonical byte encoding (ASCII UTF-8 JSON, sorted keys),
  exact `Decimal` / UTC / currency / unit / enum encoding, per-node commutativity
  and associative-flattening decisions, duplicate-operand policy, safe
  literal-only simplifications, forbidden transformations, DAG-sharing and
  node-identity policy, cycle and complexity protections, deterministic
  graph-node identifiers, SHA-256 domain separation, canonicalization error
  taxonomy, and version-migration policy.
- `docs/payoff-graph-spec.md` — model-independent payoff-graph node taxonomy and
  compilation mapping (specification-only).
- `docs/canonical-test-vectors.md` — test-vector format and illustrative vectors
  pinning the Stage 1B decisions.
- `docs/adr/0007-canonical-contract-identity-and-payoff-graph.md` — the
  constitutional decision recording the conservative, enumerated-law approach.

### Added (Stage 1B-R1 — Canonical runtime, Implemented)

- `derivatrace.canonical`: a canonical runtime that canonicalizes a validated
  Stage 1A contract graph into byte-exact canonical JSON, content-addresses
  nodes with deterministic ids, detects canonical collisions, and derives a
  deterministic canonical contract identity (`canonical:sha256:<hex>`) with
  SHA-256 domain separation and schema-version participation.
- Normative test vectors in `docs/canonical-test-vectors.md` (CV-001–CV-011)
  produced and verified by the canonical runtime.
- 100% statement and branch coverage across `derivatrace.canonical`; strict mypy;
  Ruff clean.

### Not implemented

- Stage 1B-R2 payoff-graph compilation remains unimplemented; its specification
  is now closed (`docs/payoff-graph-spec.md`, `docs/canonical-test-vectors.md`,
  `docs/adr/0007-canonical-contract-identity-and-payoff-graph.md`) and deferred to
  Stage 1B-R2. No `derivatrace.payoffgraph` runtime, modules, or `compile_payoff_graph`
  entry point exist yet.
- Pricing, valuation, Greeks, models, numerical engines, market data, and
  evidence certificates remain outside Stage 1B.

### Changed (Stage 1B-R2 payoff-graph specification closure)

- Closed the contradiction between the earlier Stage 1B baseline payoff-graph
  draft and the binding architectural decisions: `PGPayment` now uses an
  `amount` field (never `payoff_leaf`); `settlement_time` is owned only by
  `PGPayment` and `observation_time` only by `PGObservable` (a `PGConstant`
  carries neither), superseding the obsolete "leaves carry settlement time"
  wording.
- Added a dedicated binary `PGSubtract` node; `Subtract` compiles directly to
  `PGSubtract` and is no longer lowered to `PGAdd` + `PGNegate`.
- Documented the Boolean policy precisely: `PGComparison` preserves author order
  and is operator-sensitive; `PGAllOf`/`PGAnyOf` are commutative, associative,
  flattened, sorted, and retain duplicates; `PGNot` is unary and positional.
- Added `PGBooleanConstant` so constant Boolean conditions are represented
  explicitly.
- Specified the public `compile_payoff_graph(contract, ...)` boundary, the
  immutable `PayoffGraph` result (`schema_version`, `document_bytes`,
  `structural_bytes`, `identity`, `root_node_id`, `node_count`,
  `source_contract_identity`), deterministic provenance (excluded from identity),
  schema/domain constants, `PayoffGraphLimits`, the `payoff_graph.*` error
  taxonomy (with `payoff_graph.collision`, never reusing
  `canonicalization.collision`), and the reachable-only graph policy.
- Provided a complete 20-node mapping matrix covering every Stage 1A/R1 node.
- Regenerated CV-011 under the corrected schema with exact, pre-computed
  canonical payload bytes, node ids, structural bytes, document bytes, and graph
  identity (computed by an isolated standard-library verification script, not
  shipped), and added planned R2 normative vectors.

### Changed (Stage 1C-R1B — Architecture reconciliation, documentation only)

- Revised the Stage 1C error taxonomy to exactly 7 classes:
  `ValidationEquivalenceError`, `ValidationEquivalenceInputError`,
  `ValidationEquivalenceUnsupportedLevelError`,
  `ValidationEquivalenceComparisonError`, `ValidationEquivalenceEncodingError`,
  `ValidationEquivalenceReportCollisionError`,
  `ValidationEquivalenceMalformedRepresentationError`. Removed
  `ValidationEquivalenceIncompatibleSchemasError` and its
  `validation_equivalence.incompatible_schemas` code from all documentation.
- Replaced vector `ve_041_contradictory_schema_config_raises` (error code
  `incompatible_schemas`) with `ve_041_wrong_schema_type_raises` (error code
  `input`): passing a `PayoffGraphSchemaVersion` instance as `canonical_schema`.
- Corrected the `ve_018_scalar_vs_money_unit` vector: `ve_018` now uses a
  documented caller-forged money-denominated `Scale.factor` (via
  `object.__setattr__`) that passes root construction but fails Stage 1A
  use-time validation; the right operand outcome is `invalid`.
- Replaced the `Add(obs_A)` single-operand construction in `ve_022`,
  `ve_023`, `ve_024` and `ve_038` with a constructible unsupported
  `Contract` subclass (`UnsupportedContract`).
- Clarified `public_api` vs `private_seam` vector-kind definitions in
  `validation-equivalence-spec.md` §3.1.2: `public_api` vectors now
  explicitly permit caller-owned hostile or forged objects when testing
  use-time boundary hardening, provided no Stage 1C internal function is
  monkeypatched, no seam is replaced, and no orchestration dependency is
  injected.
- Added the R1 nine-step orchestration sequence (`validation-equivalence-spec.md`
  §9.5), documenting that Stage 1A validation occurs through
  `validate_contract`, not only through the Stage 1B-R1 path.
- Added the double-canonicalization exception policy
  (`validation-equivalence-spec.md` §8.1).
- Added structural-level identity rules (`validation-equivalence-spec.md` §10):
  all identity fields `null`, all deeper-level statuses `not_evaluated`
  with reason `shallower_level_requested`.
- Corrected failure-code examples to use `canonicalization.input.not_validated`
  (not `canonicalization.not_validated`) in canonicalization-spec.md.
- Updated ADR 0008 and ADR 0009 to reflect the revised taxonomy and vector
  names.
- Updated `tests/test_documentation.py` to enforce all revised guards.

## [0.1.0.dev0] — Stage 0 (Unreleased)

Stage 0 is the project foundation and system specification. It contains no
pricing functionality.

### Added

- Minimal, importable, dependency-free Python package `derivatrace`.
- `derivatrace.__version__` pinned to `0.1.0.dev0`.
- `derivatrace.ProjectMetadata`, an immutable, frozen value object holding safe
  static project facts.
- `derivatrace.project_metadata()`, a deterministic metadata accessor.
- `py.typed` marker for downstream type checking.
- Repository constitution: README, vision, product specification, architecture,
  contract semantics, certificate specification, threat model, glossary.
- Five architectural decision records (ADRs).
- Staged roadmap (Stages 0–12).
- Contributor, code-of-conduct, security, and governance documents.
- Continuous integration for Python 3.11, 3.12, 3.13, and 3.14.

### Not implemented

- All pricing, valuation, Greeks, Monte Carlo, PDE, tree, and calibration
  functionality. See the roadmap and the "what does not exist today" section of
  the README.

[0.1.0.dev0]: https://github.com/sciwiz7/DerivaTrace/releases/tag/0.1.0.dev0
