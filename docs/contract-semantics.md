# Contract semantics

This document specifies the contract representation for DerivaTrace. The minimal
Stage 1A algebra — constants, observables, arithmetic, comparisons, `max`/`min`,
payment obligations, currencies, dates, observation/settlement times, conditions,
and contract composition — is now **implemented** as the typed, immutable
`derivatrace.contracts` module. Canonicalization and compilation to a canonical
payoff graph are specified for Stage 1B as a **design baseline**
(specification-only; no implementation). The approved normalization laws, value
encoding, and canonical identity are defined in
[canonicalization-spec.md](./canonicalization-spec.md) and
[payoff-graph-spec.md](./payoff-graph-spec.md). No pricing, valuation, or engine
functionality is implemented in Stage 1A.

## Financial contract versus pricing model

A financial contract is a declaration of *what is paid* under what conditions.
A pricing model is a set of assumptions about stochastic behaviour. A numerical
engine is a method for computing results. Confusing these leads to opaque,
non-reproducible valuations. DerivaTrace keeps them separate: the contract is
model-independent and is compiled into a canonical payoff representation that
later models and engines value.

## Future AST responsibilities

The contract representation will be an **immutable, typed abstract syntax tree
(AST)**. Its responsibilities:

- Encode the contractual obligations and cash flows exactly and unambiguously.
- Be canonical: equivalent serialized contracts map to identical trees.
- Be compositional: complex contracts are built from primitives.
- Support validation at multiple levels (structural, semantic, economic).
- Carry currency, unit, observation, and settlement information explicitly.
- Remain independent of any model or numerical engine.

## Semantic node categories

The AST is expected to distinguish the following node categories. This is a
specification, not an implementation.

- **Constants** — exact numeric or boolean literals.
- **Market observables** — references to market data by identity.
- **Arithmetic expressions** — addition, subtraction, multiplication,
  division, negation, scaling.
- **Comparisons and conditions** — equal, less-than, greater-than, and
  boolean combinations.
- **Maximum and minimum** — `max`/`min` over expressions.
- **Payment obligations** — a dated cash flow of a specified amount and
  currency.
- **Currencies** — explicit currency identity and unit.
- **Observation times** — when a value is observed.
- **Settlement times** — when a cash flow is exchanged.
- **Conditional cash flows** — pay if a condition holds.
- **Path observations** — values observed along a trajectory (for path-
  dependent contracts).
- **Exercise rights** — call/put/bermuda exercise with payoff and constraints.
- **Barriers** — trigger/knock conditions based on observed paths.
- **Schedules** — sequences of dates and associated actions.
- **Contract composition** — combination, scaling, and choice of sub-contracts.

## Typing concepts

- Nodes are immutable and carry explicit types (e.g., `Money`, `Observable`,
  `Boolean`, `Date`, `Currency`).
- Exact terms (e.g., notionals, strikes, dates) use exact structured
  representations or `Decimal`; they are not silently converted to floating
  point.
- The tree is constructed through typed constructors, not by handwritten pricing
  functions for each instrument.

## Contract lifecycle

1. **Authoring** — a contract is expressed from primitives.
2. **Canonicalization** — equivalent inputs normalize to a stable tree.
3. **Validation** — structural, semantic, and economic checks run.
4. **Compilation** — the tree is compiled to a canonical payoff graph.
5. **Valuation** — a model and engine value the compiled form.
6. **Certification** — an evidence certificate records the result.

## Observation versus settlement

Observation times (when a value is read from the market) are distinct from
settlement times (when cash is exchanged). The AST must encode both explicitly;
confusing them is a common source of valuation error and must be prevented by
typing and validation. This reinforces the project's separation of concerns
between contract semantics, market data, model, numerical engine, risk,
validation, and the evidence certificate.

## Currency and unit handling

Currency is an explicit identity, not an implicit assumption. Amounts carry
their currency and unit. Conversions between currencies or between exact
contract terms and numerical-engine inputs must be explicit, recorded, and
validated. No silent precision or unit conversion is permitted.

## Schedules and calendars

Schedules describe date sequences (coupons, exercises, observations). Calendars
and day-count conventions, when introduced, must be explicit and part of the
canonical identity so that two schedules that differ only by convention are not
mistaken for equivalent.

## Normalization

Normalization rewrites a contract into a canonical form using deterministic
rules (for example, sorting commutative terms, folding constants, resolving
trivial conditions). Normalization must preserve semantics exactly.

> **Conservative scope (Stage 1B).** Per
> [canonicalization-spec.md](./canonicalization-spec.md), normalization applies
> **only** explicitly approved structural laws and does **not** claim complete
> mathematical or economic equivalence. Which nodes are commutative, which are
> flattened, how duplicates and literals are handled, and which transformations
> are forbidden are enumerated there; the canonical identity is *structural*
> under those laws, not a proof of economic parity.

## Canonical equivalence

Two contracts are canonically equivalent if their normalized ASTs are
identical. Canonical equivalence is the basis for stable contract identity and
for detecting redundant or divergent definitions.

## Validation levels

- **Structural** — the tree is well-formed and well-typed.
- **Semantic** — references resolve, currencies are consistent, dates are
  ordered.
- **Economic** — sanity checks such as non-negative notionals where required,
  and later arbitrage checks.

## Unsupported or ambiguous inputs

Inputs that are ambiguous, contradictory, or outside the supported schema must
be rejected with an explicit error. Examples include missing currencies,
unresolved observables, contradictory exercise constraints, and non-finite or
extreme values that cannot be represented exactly.

## Conceptual examples (not executable public API)

The following illustrate the *intent* of the contract algebra. They are
conceptual and must **not** be treated as implemented or importable behaviour.

```text
# Conceptual: a European call payoff
Pay(
    currency="USD",
    amount=Max(0, Obs(observable="EQUITY:ACME:spot", at=maturity) - strike),
    at=settlement,
)

# Conceptual: a conditional coupon
If(
    condition=Obs(observable="RATE:USD:libor3m", at=fixing) > barrier,
    then=Pay(currency="USD", amount=coupon, at=coupon_date),
    else=Pay(currency="USD", amount=0, at=coupon_date),
)
```

These are illustrations only; the actual Stage 1 API will be defined by its own
specification and ADR.

## Implemented Stage 1A contract algebra

The minimal algebra described above is implemented as `derivatrace.contracts`.
It includes: exact numeric and boolean constants; market observables identified
by `ObservableId`; arithmetic (`Add`, `Subtract`, `Multiply`, `Divide`,
`Negate`); comparisons and boolean logic (`Equal`, `LessThan`, `GreaterThan`,
`And`, `Or`, `Not`); `Max`/`Min`; `Payment`, `Both`, `Either`, `Cond`, and
`Scale`; currencies/units via `Currency` and `Unit`; and observation/settlement
times via `ObservationTime` and `SettlementTime`. Path observations, exercise
rights, barriers, and schedules are planned for later stages.

The concrete API, construction rules, and validation semantics are documented in
[contract-api.md](./contract-api.md) and
[ADR 0006](./adr/0006-stage-1-contract-algebra-and-runtime-type-system.md).

See also [architecture.md](./architecture.md),
[certificate-spec.md](./certificate-spec.md), and
[ADR 0001](./adr/0001-separation-of-contract-model-engine.md).
