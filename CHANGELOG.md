# Changelog

All notable changes to DerivaTrace are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Semantic versioning will
apply once stable releases begin.

## [Unreleased]

### Documentation and application readiness

- Reconciled the README, roadmap, documentation index, contribution guide,
  security policy and governance document with the merged implementation state.
- Clarified that Stage 1C-R1 is complete privately, Stage 1C-R2 remains planned,
  and no public Stage 1C comparison API exists.
- Added a concise maintenance, security and CI summary for external reviewers.
- Removed stale statements that described implemented canonical, payoff-graph and
  validation-equivalence runtimes as nonexistent or merely planned.

### Stage 1C-R1B — Private orchestration runtime

- Added private `_compare_contracts` orchestration over Stage 1A validation,
  Stage 1B-R1 canonicalization and Stage 1B-R2 payoff compilation.
- Added authoritative use-time validation for caller-owned schemas and limits.
- Preserved upstream namespaced failures and documented failure classifications.
- Added double-canonicalization consistency and source-identity checks.
- Added non-leaking containment for unexpected internal exceptions.
- Preserved caller-supplied `DiffLimits` in `limits_used`.
- Constructed deterministic reports exclusively through the R1A report builder.
- Kept `diff_representation="none"` as the only private R1 diff mode.
- Added `ValidationEquivalenceUnsupportedLevelError` and
  `ValidationEquivalenceComparisonError`, preserving the seven-class Stage 1C
  error taxonomy.
- Completed 1,451 passing tests with 100% statement and branch coverage, strict
  mypy, Ruff, packaging validation and green Python 3.11–3.14 CI.

### Stage 1C-R1A — Private report foundation

- Added closed validation, comparison, failure, schema and diff taxonomies.
- Added immutable report-side, failure, limits, schema metadata and diff records.
- Added deterministic report encoding, identity and collision defence.
- Added the exact R1 empty diff state and private report builder.
- Kept the package unexported from the public Stage 1C boundary.

### Stage 1C architecture baseline

- Established graded `structural`, `canonical` and `payoff` evaluation levels.
- Defined independently reported canonical and payoff conclusions.
- Defined deterministic report and structural-diff schemas, limits, error
  taxonomy, security rules and 44 normative vectors.
- Recorded the delivery and public-export gates in ADRs 0008 and 0009.
- Explicitly prohibited claims of economic, pricing, legal, accounting, tax,
  model or suitability equivalence.

### Stage 1B-R2 — Payoff-graph runtime

- Added `derivatrace.payoffgraph` and public `compile_payoff_graph`.
- Implemented all supported canonical-to-payoff node mappings.
- Added deterministic reachable-only structural and provenance-bearing document
  representations.
- Added domain-separated `payoffgraph:sha256:` identity and dedicated limits,
  collision and error handling.
- Preserved source canonical identity as deterministic provenance excluded from
  payoff-graph identity.

### Stage 1B-R1 — Canonical runtime

- Added `derivatrace.canonical` and public `canonicalize_contract`.
- Added byte-exact compact canonical JSON, exact-value encoding,
  content-addressed node identifiers, collision detection and deterministic
  `canonical:sha256:` contract identity.
- Added and verified normative canonical vectors.

### Stage 1A — Immutable contract algebra and validation

- Added exact domain values, immutable expression and contract nodes, and the
  public `validate_contract` boundary.
- Added iterative whole-graph validation, deterministic metrics, cycle detection,
  complexity limits, supported-node enforcement and forgery rejection.
- Added a stable namespaced error taxonomy.

## [0.1.0.dev0] — Stage 0 foundation (unreleased)

- Added the dependency-free package skeleton and typed package metadata.
- Added the project constitution, architecture, product and security documents.
- Added ADR, governance, contribution and code-of-conduct processes.
- Added CI for Python 3.11–3.14, strict typing, linting, coverage and packaging.
- Added the MIT License.

No version has been published to PyPI and no stable release exists.

[0.1.0.dev0]: https://github.com/sciwiz7/DerivaTrace/releases/tag/0.1.0.dev0