# ADR 0006 — Stage 1A contract algebra and runtime type system

- **Status:** Accepted
- **Stage:** 1A (implemented)
- **Date:** 2026-07-15
- **Supersedes:** — (builds on ADR 0001–0005)
- **Superseded by:** —

## Context

DerivaTrace separates *contract semantics* (what a contract pays) from models,
numerical engines, market data, and evidence certificates (ADR 0001). Stage 0
established the project constitution, package skeleton, and full specification.
Stage 1 introduces the immutable contract algebra. The work is delivered in
three parts:

- **Stage 1A** — contract algebra and runtime type system (this ADR).
- **Stage 1B** — canonical payoff graph and structural canonicalization.
- **Stage 1C** — validation levels and equivalence reporting.

This ADR records the design decisions for Stage 1A only. It deliberately
excludes pricing, evaluation, canonicalization, serialization, hashing,
payoff-graph compilation, and certificates.

## Decision

Stage 1A provides a strongly typed, immutable contract AST plus a deterministic,
iterative structural validator. The validator re-checks every node's invariants
so that objects forged or mutated after construction cannot bypass validation.
No node is ever executed, evaluated, priced, or compiled.

## Exact numeric boundary

`ExactNumber` wraps `decimal.Decimal`. Construction is restricted to
`from_int` and `from_string`; `float` and `bool` are rejected so binary
floating point cannot enter the algebra.

Input-safety limits (conservative, not a security perimeter on their own):

- Maximum significant digits: `MAX_SIGNIFICANT_DIGITS = 50`.
- Maximum absolute exponent: `MAX_ABS_EXPONENT = 100`.
- Non-finite values (`NaN`, `Infinity`) are rejected.
- Negative zero is normalized to `0`.

The valid zero forms `"0"`, `"-0"`, `"0.0"`, and integer `0` are all accepted
and normalised to canonical `0`. Rejection is **never** performed via
`Decimal.is_normal()`: `is_normal()` returns `False` for zero (and for
subnormals), so a zero-based check would wrongly reject legitimate zeros.
Zero acceptance is decided by an explicit, positive construction path, not by
the absence of normality.

These bounds keep `Decimal` arithmetic bounded and reproducible while leaving
genuine numerical valuation to later stages that do not exist in Stage 1A.

## Input safety limits and rationale

The limits prevent pathological `Decimal` values (extreme exponent or digit
count) from consuming unbounded memory or producing misleading output. They are
defensive only; Stage 1A performs no arithmetic beyond unit bookkeeping. The
numbers are stored exactly and never approximated.

## Strict currency syntax

`Currency` accepts exactly three uppercase ASCII letters (`^[A-Z]{3}$`). This
rejects lowercase, mixed case, wrong length, and Unicode look-alikes. Accepted
syntax does **not** confirm official ISO 4217 registration; the two concerns
are distinct.

## Minimal unit system

`UnitKind` is `SCALAR` or `MONEY`.

- A scalar unit carries no currency.
- A money unit must carry exactly one `Currency`.
- Contradictory states (scalar with a currency, money without a currency) are
  rejected.
- `Unit.kind` must be **exactly** an approved `UnitKind`. Because `UnitKind` is
  a `StrEnum`, a plain string such as `"scalar"` would otherwise compare equal
  to `UnitKind.SCALAR`; such strings are explicitly rejected, so only genuine
  `UnitKind` members are accepted.

`Multiply` allows `scalar × scalar`, `scalar × money`, and `money × scalar`,
but rejects `money × money`. `Divide` requires a dimensionless denominator and
rejects a literal zero denominator.

## Structured observable identity

`ObservableId` is composed of `namespace`, `identifier`, and `field`, each
non-empty, length-bounded, and restricted to a conservative ASCII grammar
(slugs for `namespace`/`field`, a broader identifier grammar for `identifier`).
No market data is fetched or resolved.

## Separate observation and settlement runtime types

`ObservationTime` and `SettlementTime` are distinct types wrapping
timezone-aware `datetime` values normalized to UTC. Naive timestamps (no
`tzinfo`) are rejected, and a `datetime` whose `tzinfo` reports a `None`
`utcoffset()` is also rejected — such a value is not a concrete, comparable
instant. Any genuinely timezone-aware `datetime` is accepted and converted to
UTC with `astimezone(UTC)`; this preserves microsecond precision and means two
timestamps that represent the same instant in different offsets compare equal
(after normalization). The separation prevents silent substitution of an
observation timestamp for a settlement timestamp.

## Three AST categories

The AST has three abstract categories:

- `ScalarExpression` — numeric expressions with an explicit `Unit`.
- `BooleanExpression` — conditions.
- `Contract` — obligations.

Concrete nodes are listed explicitly below.

## Supported concrete-node policy

The set of supported concrete nodes is fixed and explicit. Validation enforces
it through `isinstance` checks for each supported type within the three category
validators; any node that is an instance of a category base but not one of the
supported concrete types is rejected with `ContractValidationError`.

Supported scalar nodes: `Number`, `Observable`, `Add`, `Subtract`, `Multiply`,
`Divide`, `Negate`, `Maximum`, `Minimum`, `ConditionalValue`.

Supported boolean nodes: `BooleanConstant`, `Comparison`, `AllOf`, `AnyOf`,
`Not`.

Supported contract nodes: `Zero`, `Payment`, `Both`, `Scale`,
`ConditionalContract`.

Third-party subclasses of the abstract bases are **not** part of the supported
policy and are rejected. The policy is **closed and exact**: only the exact
concrete types listed above are admitted. A subclass of an approved concrete
node is **not** automatically approved — its exact type must be one of the
reviewed classes, because a subclass could override field access or other
behaviour. The exact-type check runs at the very start of every traversal frame,
before any attribute access, unit derivation, or child iteration, so a
non-approved subclass cannot execute overridden behaviour before being
rejected. The supported set must be extended deliberately through review, never
by implicit subclassing.

## Comparison design

Comparisons use a single `Comparison` node carrying a `ComparisonOperator`
enumeration. All six operators are supported:

- `ComparisonOperator.LESS_THAN` (`<`)
- `ComparisonOperator.LESS_THAN_OR_EQUAL` (`<=`)
- `ComparisonOperator.EQUAL` (`==`)
- `ComparisonOperator.NOT_EQUAL` (`!=`)
- `ComparisonOperator.GREATER_THAN_OR_EQUAL` (`>=`)
- `ComparisonOperator.GREATER_THAN` (`>`)

Both operands must share a unit. The enumerated form keeps the boolean grammar
closed and avoids six near-identical concrete node types.

## Boolean composition design

Boolean combination uses the declarative n-ary nodes `AllOf` (conjunction) and
`AnyOf` (disjunction), plus the unary `Not`. These are plain AST combinators;
constructing them performs no evaluation and they have **no short-circuit
semantics** — there is no control flow or evaluation order to short-circuit.
The older names `And`/`Or` are intentionally absent to avoid implying Python
short-circuit execution.

## Frozen/slotted dataclass policy

All concrete nodes are `frozen=True, slots=True` dataclasses. Value objects use
`__slots__` and raise `AttributeError` on assignment. This makes graphs
structural and shareable by reference, and prevents accidental mutation after
construction. Forged or mutated objects are caught by graph validation.

## Constructor validation

Every constructor validates its own inputs immediately: field types, unit
consistency, currency consistency, arity, and supported-node membership. This
gives fast, local failure at build time.

## Whole-graph structural validation

`validate_contract` validates the entire graph, not just the root. It
re-derives unit fields and re-checks child types, arity, unit, and currency
invariants on every node, so forged objects cannot bypass construction-time
checks.

## Value-object internal revalidation and exact-type policy

Construction validates a value object's inputs immediately. Graph validation
goes further and **re-checks the stored internal state** of every value object
it relies on (`ExactNumber`, `Currency`, `Unit`, `ObservableId`,
`ObservationTime`, `SettlementTime`, and `ValidationLimits`). The revalidation
reads the private stored fields directly and re-derives the original
construction invariants; it does **not** re-run the public constructors, which
would silently normalize forged-but-valid state. Objects mutated after
construction via `object.__setattr__` (for example a `Currency._code` changed to
lowercase, a `Unit.kind` changed to a plain string, a `money` unit stripped of
its currency, an `ExactNumber._value` changed to `NaN`/`Infinity`/non-`Decimal`,
or an `ObservationTime._value` changed to a naive `datetime`) are therefore
detected and rejected during validation.

Deterministic value objects additionally require the **exact** approved type.
A subclass of `Currency`, `Unit`, `ExactNumber`, `ObservableId`,
`ObservationTime`, `SettlementTime`, or `ValidationLimits` could override
`__eq__`, property access, or other behaviour, so `isinstance` is not
sufficient; the revalidation requires `type(x) is T`. This exact-type policy is
consistent with the closed, exact supported-node policy applied to AST nodes.

## Iterative traversal

Traversal is an explicit stack, not recursion, so it cannot be exhausted by deep
structures. Depth and unique-node limits are enforced during traversal.

## Concrete-node allow-list policy

See *Supported concrete-node policy* above. The allow-list is the exact-type
registry (`_SUPPORTED_NODE_TYPES`) consulted by `_ensure_supported_node_type`
at the start of every traversal frame; there is no implicit acceptance of
arbitrary subclasses. Constructors enforce category and local-field correctness,
but the authoritative graph validator rejects any node whose exact type is not
in the approved registry.

## Cycle detection

A node encountered on the current traversal path (in the ancestor set) raises
`ContractCycleError`. Safe DAG sharing is permitted.

## DAG sharing

Shared subexpressions are accepted. An explored set plus a best-depth map
ensures a shared node is validated once and never re-expanded at an
equal-or-greater depth. Shared nodes are counted once by object identity.

## Depth semantics

Depth is measured from the root contract at depth 1. A node's depth is one
greater than its parent's depth. `max_depth` is the maximum depth reached.

## Unique-node semantics

`node_count` counts unique object nodes by identity, excluding value objects
(`Currency`, `SettlementTime`, `ObservableId`, `ExactNumber`), which are leaves.
A subexpression shared by reference is counted once.

## Complexity limits

`ValidationLimits` defaults to `max_depth=64` and `max_unique_nodes=4096`.
Both fields must be genuine integers strictly greater than zero; `bool` is
rejected (it is a subclass of `int` and must not be accepted as `1`/`0`). A
forged `ValidationLimits` (for example one whose `max_depth` was mutated to a
`bool` or zero) is revalidated at `validate_contract` entry, so it cannot bypass
these invariants. Exceeding either limit raises `ContractComplexityError`
before traversal becomes expensive.

## Stable error codes and structural paths

Errors derive from `DerivaTraceError` and carry a stable `.code` and an optional
structural `.path` (a tuple of field names and integer indices). Paths locate
failures without leaking node `repr` values. Codes: `derivatrace.error`,
`contract.error`, `contract.input`, `contract.input.type_mismatch`,
`contract.validation`, `contract.validation.cycle`,
`contract.validation.complexity`.

## Rejected alternatives

- **Dynamic type acceptance:** admitting arbitrary `ScalarExpression` subclasses
  would let untrusted graphs inject unknown node behaviour. Rejected; the
  supported set is explicit.
- **Recursive validation:** simpler to write but exhaustible by deep graphs.
  Rejected in favour of iterative traversal.
- **`float` for numbers:** introduces approximation and hidden rounding.
  Rejected; `ExactNumber` is exact.
- **Single combined unit/money type without `UnitKind`:** loses compile-time
  unit safety. Rejected.
- **Evaluating observables during validation:** out of scope for Stage 1A and a
  confidentiality/complexity risk. Rejected.
- **Canonicalization or hashing in Stage 1A:** deferred to Stage 1B/1C where the
  payoff graph exists.
- **Contractual choice / exercise / optionality (`Either`-style nodes):** a node
  that selects one of several contracts (or models an option's exercise) encodes
  a model or economic decision that Stage 1A explicitly excludes. `Either` is
  therefore not part of the Stage 1A node set and is deferred to a later stage
  that introduces choice, exercise rights, and barriers.
- **`And`/`Or` boolean combinators:** replaced by `AllOf`/`AnyOf` so the names
  cannot imply Python short-circuit execution.
- **`Cond`/`Max`/`Min` short names:** replaced by `ConditionalContract`/
  `ConditionalValue` and `Maximum`/`Minimum` to keep the public surface explicit
  and unambiguous.

## Consequences

- Contract graphs are exact, immutable, and shareable.
- Structural validation is deterministic and bounded.
- Forged or mutated objects are rejected.
- No pricing, model, engine, market data, canonicalization, serialization,
  hashing, payoff graph, or certificate exists yet.

## Security considerations

Stage 1A validation is a defensive boundary against malformed or hostile graphs.
It protects against forged frozen objects, unsupported subclasses, malicious
graph depth, excessive node count, cycles, shared-node DAGs, extreme `Decimal`
values, Unicode identifier confusion, naive timestamps, and currency/unit
mismatch. It is **not** a proof of economic correctness, and it must not be
described as pricing, valuation, economic approval, or formal verification.

## Stage 1B and Stage 1C follow-up work

- **Stage 1B:** canonical payoff graph, structural canonicalization, canonical
  contract identity, equivalence checks.
- **Stage 1C:** graded validation levels, equivalence reporting, structural
  diffing.
