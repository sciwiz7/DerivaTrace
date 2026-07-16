# Glossary

This glossary defines key terms used across DerivaTrace documentation. Terms are
defined in the context of this project and are not legal or regulatory
definitions.

- **Arbitrage check** — a validation that a price does not permit a risk-free
  profit under stated assumptions.
- **Canonicalization** — the process of converting equivalent inputs into a
  single stable representation.
- **Certificate** — a versioned evidence envelope describing what was calculated
  and how.
- **Contract semantics** — the definition of what a financial instrument pays,
  independent of valuation.
- **Determinism** — the property that identical inputs produce identical,
  reproducible outputs within a declared policy.
- **Evidence** — recorded facts about a calculation and its context.
- **Exact term** — a contract quantity represented exactly (e.g., via
  `Decimal` or structured types), not as a floating-point approximation.
- **Hashing** — computing a deterministic digest (SHA-256) over canonical bytes
  for integrity.
- **Integrity hash** — a SHA-256 digest used to detect modification. Not a
  digital signature.
- **Market snapshot** — a captured set of observable market inputs with a
  deterministic identity.
- **Model** — a set of assumptions governing stochastic behaviour.
- **Numerical engine** — a method that computes results from a model and inputs.
- **Observation time** — when a market value is read.
- **Payoff graph** — a canonical, model-independent representation of a
  contract's payoffs. Its Stage 1B-R2 taxonomy and compilation mapping are
  specified in `payoff-graph-spec.md` (Stage 1B-R2 runtime planned). The graph
  is reachable-only (discarded compilation intermediates never participate in the
  identity), and its identity (`payoffgraph:sha256:<hex>`) is computed over the
  structural projection that excludes deterministic provenance.
- **Canonical contract identity** — a deterministic `SHA-256` fingerprint
  (`canonical:sha256:<hex>`) over the canonical bytes of a validated contract,
  under a fixed, versioned domain-separation tag. A structural identity under
  the approved canonicalization laws, not a proof of economic equivalence.
- **Canonical schema** — the named, versioned specification of the canonical
  contract representation (`derivatrace.contract.canonical`, `1.0.0`). Its
  version participates in the canonical identity.
- **Commutative associative collection node** — a Stage 1A node whose
  operand order is not load-bearing and which is n-ary and associative
  (`Add`, `Maximum`, `Minimum`, `AllOf`, `AnyOf`); normalized by associative
  flattening and sorting operands by canonical id (tie-broken by canonical
  payload bytes) while preserving multiplicity.
- **Commutative binary node** — a Stage 1A node with exactly two operands
  whose order is not load-bearing but which is **not** flattened in schema 1.0.0
  (`Multiply` only); the two operands are reordered deterministically by canonical
  id (tie-broken by canonical payload bytes).
- **Author-order-preserving node** — a Stage 1A node whose operand order is
  preserved exactly by canonicalization (`Subtract`, `Divide`, `Comparison`,
  `ConditionalValue`, `Scale`, `Payment`, `ConditionalContract`, `Both`, `Negate`,
  `Not`, and all leaves).
- **Literal-only simplification** — an approved exact rewrite that applies only
  when every operand is a literal (`Number` / `BooleanConstant`); for example,
  constant folding using integer-coefficient tuple arithmetic (never `Decimal`
  under ambient context, never `float`, never rounding). `Divide` folding is
  excluded from schema 1.0.0. No market data, model, or engine is involved.
- **Canonical collision** — the event (assumed negligible) that two distinct
  canonical payloads hash to the same id; canonicalization raises
  `canonicalization.collision` rather than silently merging them.
- **Payoff-graph collision** — the Stage 1B-R2 analogue for the payoff graph:
  two distinct payoff payloads hash to the same payoff-node id; the compiler
  raises `payoff_graph.collision` (a dedicated code, **not**
  `canonicalization.collision`) rather than silently merging them. Canonical
  collisions from the Stage 1B-R1 runtime propagate to the payoff compiler
  without silent reclassification.
- **Payoff-graph node (PG node)** — a node in the canonical payoff graph
  (`PGConstant`, `PGObservable`, `PGAdd`, `PGSubtract`, `PGMultiply`, `PGNegate`,
  `PGMaximum`, `PGMinimum`, `PGDivide`, `PGScale`, `PGConditionalValue`,
  `PGBooleanConstant`, `PGComparison`, `PGAllOf`, `PGAnyOf`, `PGNot`,
  `PGCombine`, `PGPayment`, `PGConditionalContract`); a model-independent
  compiled representation of a contract node. `Divide` compiles directly to
  `PGDivide`, never to a reciprocal. `Subtract` compiles directly to `PGSubtract`
  (`minuend`/`subtrahend`), never to `PGAdd` + `PGNegate`. `Payment` owns the
  settlement time and references its amount via an `amount` field (never
  `payoff_leaf`); `PGObservable` owns the observation time; `PGConstant` carries
  neither time. `BooleanConstant` compiles to an explicit `PGBooleanConstant`.
- **Reachability pruning (semantic closure)** — after canonicalization applies
  all approved structural laws (flattening, literal folding, conditional branch
  selection), a deterministic traversal from the final canonical root collects
  only the nodes actually referenced by canonical payload fields. Nodes that
  existed transiently during processing (flattened inner collections, folded-away
  literals, discarded conditional branches) are excluded from the final canonical
  node table, canonical bytes, and contract identity. The public
  `CanonicalContract.node_count` equals the number of reachable nodes. Internal
  processing history is never part of canonical identity.
- **Canonicalization (Stage 1B)** — the process of converting a validated
  Stage 1A contract graph into a single, stable, deterministically serialized
  form under explicitly approved structural laws. Specified in
  `canonicalization-spec.md` and implemented in the Stage 1B-R1 canonical
  runtime (`derivatrace.canonical`); the payoff-graph compilation remains a
  Stage 1B-R2 deliverable.
- **Reproducibility policy** — the declared conditions under which a result can
  be reproduced.
- **Risk** — sensitivities (Greeks) and uncertainty associated with a valuation.
- **Settlement time** — when cash is exchanged.
- **Signature (future)** — an optional external cryptographic attestation of
  provenance; distinct from an integrity hash.
- **Validation outcome** — the result (`pass`, `warn`, `fail`) of a check.
- **Warning** — a non-fatal caution recorded in a certificate.
- **ExactNumber** — a `Decimal`-backed exact numeric value with bounded
  precision and exponent; it rejects `float`, `bool`, `NaN`, `Infinity`, and
  non-normalized forms. Stage 1A's exact numeric contract term.
- **Unit** — the explicit dimension of a numeric value: dimensionless, count,
  or money (with a required currency). Units are re-derived by validation rather
  than trusted from input.
- **UnitKind** — an enumeration of unit kinds: `DIMENSIONLESS`, `COUNT`, and
  `MONEY`.
- **Currency** — an explicit currency identity (ISO-4217 code) carried by money
  amounts; not an implicit assumption.
- **ObservableId** — a validated, normalized identifier of a market observable
  (a structured string), distinct from its observed value.
- **ObservationTime** — when a market value is read; a timezone-aware UTC
  `datetime` (naive timestamps are rejected).
- **SettlementTime** — when cash is exchanged; a timezone-aware UTC `datetime`,
  distinct from observation time.
- **ScalarExpression** — an abstract node category for numeric contract
  expressions (constants, observables, arithmetic, comparisons, `Maximum`/
  `Minimum`, `ConditionalValue`).
- **BooleanExpression** — an abstract node category for boolean contract
  expressions (`Comparison` over a `ComparisonOperator`, `AllOf`, `AnyOf`,
  `Not`). There is no `And`/`Or`; `AllOf`/`AnyOf` are declarative n-ary
  combinators with no short-circuit semantics.
- **Contract (AST node)** — an abstract node category for contract combinators
  (`Zero`, `Payment`, `Both`, `Scale`, `ConditionalContract`). `Either`
  (contractual choice/exercise/optionality) is deliberately not part of Stage 1A.
- **validate_contract** — the Stage 1A whole-graph validator that checks
  structural and semantic invariants (well-formed tree, supported node types,
  acyclicity, depth and node-count limits, currency/unit consistency, exact
  numbers) and returns `ContractMetrics`.
- **ContractMetrics** — the metrics returned by `validate_contract`: unique node
  count, maximum depth, and flags for cycles and DAG sharing.
- **Supported-node policy** — the rule that only the exact set of implemented
  concrete node types is accepted; arbitrary subclasses of the abstract bases
  are rejected.
- **Frozen object** — a value or node whose fields cannot be mutated after
  construction; immutability is enforced by `__slots__` and a guarded
  `__setattr__`.
