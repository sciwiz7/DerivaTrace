# DerivaTrace Contract API (Stage 1A)

Stage 1A delivers an immutable, strongly typed contract algebra and a
deterministic structural validator. It contains **no pricing, valuation,
models, numerical engines, market data, canonicalization, hashing, payoff
graphs, or certificates**.

Every example below is executable and is exercised by the test suite.

## 1. Status and scope

- **Stage:** 1A implemented. Stage 0 foundation complete.
- **Package state:** Pre-Alpha. **Not published.** Not available on PyPI.
- **Runtime dependencies:** none (`dependencies = []`).
- **Python:** 3.11, 3.12, 3.13, 3.14.
- **What this API does:** represents *what a contract pays*, validates the
  graph structurally, and reports deterministic metrics. It does **not**
  evaluate, price, or approve anything economically.

## 2. Installation for contributors

DerivaTrace is not published and must not be installed from PyPI. For local
development only:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 3. Import surface

The entire public surface lives under `derivatrace.contracts`.

```python
from derivatrace.contracts import (
    ExactNumber,
    Currency,
    Unit,
    UnitKind,
    ObservableId,
    ObservationTime,
    SettlementTime,
    Number,
    Observable,
    Add,
    Subtract,
    Multiply,
    Divide,
    Negate,
    Maximum,
    Minimum,
    ConditionalValue,
    BooleanConstant,
    Comparison,
    ComparisonOperator,
    AllOf,
    AnyOf,
    Not,
    Zero,
    Payment,
    Both,
    Scale,
    ConditionalContract,
    ValidationLimits,
    ContractMetrics,
    validate_contract,
    DerivaTraceError,
    ContractError,
    ContractInputError,
    ContractTypeMismatchError,
    ContractValidationError,
    ContractCycleError,
    ContractComplexityError,
)
```

```python
import derivatrace.contracts as contracts

assert "validate_contract" in dir(contracts)
```

`BooleanExpression` and `ScalarExpression` are also exported as abstract base
types for typing user code; concrete nodes are the listed classes above.

## 4. Error taxonomy

All errors derive from `DerivaTraceError` and carry a stable `.code` and an
optional structural `.path`.

```python
from derivatrace.contracts import (
    DerivaTraceError,
    ContractError,
    ContractInputError,
    ContractTypeMismatchError,
    ContractValidationError,
    ContractCycleError,
    ContractComplexityError,
)

assert issubclass(ContractValidationError, ContractError)
assert issubclass(ContractCycleError, ContractValidationError)
assert issubclass(ContractComplexityError, ContractValidationError)
assert issubclass(ContractTypeMismatchError, ContractInputError)
assert issubclass(ContractInputError, ContractError)

err = ContractValidationError("boom", path=("operands", 0))
assert err.code == "contract.validation"
assert err.path == ("operands", 0)
```

## 5. ExactNumber

`ExactNumber` wraps `decimal.Decimal`. Construction is restricted to
`from_int` and `from_string` so that binary floating point can never enter the
algebra. `float` and `bool` are rejected.

```python
from derivatrace.contracts import ExactNumber, ContractTypeMismatchError
import pytest

n = ExactNumber.from_string("3.14159265358979")
assert n.value == ExactNumber.from_string("3.14159265358979").value

m = ExactNumber.from_int(7)
assert m.value == ExactNumber.from_int(7).value

with pytest.raises(ContractTypeMismatchError):
    ExactNumber.from_int(True)  # bool is rejected, not treated as an int
```

Negative zero is normalized to zero. Non-finite values and extreme magnitudes
are rejected by conservative input-safety limits.

## 6. Currency

`Currency` validates a strict syntax: exactly three uppercase ASCII letters.
Accepted codes are **not** verified against the official ISO 4217 registry;
syntax validity and official registration are different concerns.

```python
from derivatrace.contracts import Currency, ContractInputError
import pytest

usd = Currency.from_code("USD")
assert usd.code == "USD"

with pytest.raises(ContractInputError):
    Currency.from_code("usd")  # lowercase rejected

with pytest.raises(ContractInputError):
    Currency.from_code("US")  # wrong length rejected
```

## 7. Unit and UnitKind

`UnitKind` is `SCALAR` or `MONEY`. A scalar unit carries no currency; a money
unit must carry exactly one currency. Contradictory states are rejected.
`Unit.kind` must be exactly an approved `UnitKind`: a plain string such as
`"scalar"` is rejected (even though `UnitKind` is a `StrEnum` and would otherwise
compare equal to `UnitKind.SCALAR`).

```python
from derivatrace.contracts import Unit, UnitKind, Currency, ContractInputError
import pytest

scalar = Unit.scalar()
money = Unit.money(Currency.from_code("EUR"))

assert scalar.kind == UnitKind.SCALAR
assert scalar.currency is None
assert money.kind == UnitKind.MONEY
assert money.currency.code == "EUR"

with pytest.raises(ContractInputError):
    Unit(kind=UnitKind.MONEY, currency=None)  # money requires a currency

with pytest.raises(ContractInputError):
    Unit(kind="scalar", currency=None)  # plain strings rejected
```

## 8. ObservableId

`ObservableId` is a structured, unambiguous market-observable identity composed
of a `namespace`, an `identifier`, and a `field`. All parts are non-empty,
length-bounded, and restricted to a conservative ASCII grammar. No market data
is fetched.

```python
from derivatrace.contracts import ObservableId

oid = ObservableId.from_parts("equity", "ACME", "spot")
assert oid.namespace == "equity"
assert oid.identifier == "ACME"
assert oid.field == "spot"
```

## 9. ObservationTime and SettlementTime

`ObservationTime` and `SettlementTime` are distinct runtime types so they
cannot be substituted silently. Both wrap timezone-aware `datetime` values,
normalized to UTC. Naive timestamps (no `tzinfo`) are rejected, and a
`datetime` whose `tzinfo` reports a `None` `utcoffset()` is also rejected, since
it is not a concrete, comparable instant.

```python
from datetime import datetime, timezone
from derivatrace.contracts import ObservationTime, SettlementTime, ContractInputError
import pytest

ot = ObservationTime.from_datetime(datetime(2030, 1, 1, tzinfo=timezone.utc))
st = SettlementTime.from_datetime(datetime(2030, 6, 1, tzinfo=timezone.utc))

assert ot.value.tzinfo is not None
assert st.value.utcoffset() == timezone.utc.utcoffset(None)

with pytest.raises(ContractInputError):
    ObservationTime.from_datetime(datetime(2030, 1, 1))  # naive rejected
```

## 10. ScalarExpression nodes

Scalar nodes carry an explicit `Unit`. Arithmetic enforces unit consistency and
rejects `money × money`.

```python
from derivatrace.contracts import (
    Number,
    Observable,
    Add,
    Subtract,
    Multiply,
    Divide,
    Negate,
    Maximum,
    Minimum,
    ConditionalValue,
    ExactNumber,
    Currency,
    Unit,
    ObservableId,
    ObservationTime,
    BooleanConstant,
    ComparisonOperator,
)

usd = Currency.from_code("USD")
principal = Number(ExactNumber.from_string("100"), Unit.money(usd))
rate = Number(ExactNumber.from_string("0.05"), Unit.scalar())

interest = Multiply(rate, principal)          # scalar * money -> money
total = Add((principal, interest))            # money + money -> money
half = Divide(principal, Number(ExactNumber.from_string("2"), Unit.scalar()))
negated = Negate(rate)

assert interest.unit.kind == Unit.money(usd).kind
assert total.unit.currency.code == "USD"
```

`Observable` references a market observation by identity and is never evaluated
here:

```python
obs = Observable(
    ObservableId.from_parts("equity", "ACME", "spot"),
    ObservationTime.from_datetime(datetime(2030, 1, 1, tzinfo=timezone.utc)),
    Unit.scalar(),
)
```

## 11. BooleanExpression nodes

Boolean nodes express conditions. `Comparison` requires identical operand units
and carries one of the six `ComparisonOperator` members: `LESS_THAN`,
`LESS_THAN_OR_EQUAL`, `EQUAL`, `NOT_EQUAL`, `GREATER_THAN_OR_EQUAL`,
`GREATER_THAN`.

```python
cond = Comparison(
    principal,
    Number(ExactNumber.from_string("0"), Unit.money(usd)),
    ComparisonOperator.GREATER_THAN,
)
all_of = AllOf((cond, BooleanConstant(False)))
any_of = AnyOf((cond, BooleanConstant(True)))
not_cond = Not(cond)
```

`AllOf` and `AnyOf` are declarative, n-ary boolean combinators. They describe a
conjunction/disjunction of sub-conditions; they perform **no evaluation** and
have **no short-circuit semantics** (there is no control flow to short-circuit).
The older names `And`/`Or` are intentionally not provided.

## 12. Contract nodes

Contracts declare what is paid. `Payment` requires a money amount in the same
currency as the payment. `Scale` multiplies by a dimensionless factor.
`ConditionalContract` selects a branch by a boolean condition.

```python
from derivatrace.contracts import (
    Zero,
    Payment,
    Both,
    Scale,
    ConditionalContract,
    SettlementTime,
)

st = SettlementTime.from_datetime(datetime(2030, 6, 1, tzinfo=timezone.utc))
pay = Payment(principal, usd, st)
scaled = Scale(rate, pay)
both = Both((pay, scaled))
chosen = ConditionalContract(cond, pay, Zero())
```

## 13. ValidationLimits

`ValidationLimits` bounds traversal. Defaults are `max_depth=64` and
`max_unique_nodes=4096`. Both fields must be genuine integers strictly greater
than zero; `bool` is rejected (it is a subclass of `int`).

```python
from derivatrace.contracts import ValidationLimits, ContractInputError
import pytest

limits = ValidationLimits(max_depth=32, max_unique_nodes=512)
assert limits.max_depth == 32

with pytest.raises(ContractInputError):
    ValidationLimits(max_depth=True, max_unique_nodes=10)  # bool rejected
```

## 14. ContractMetrics

`ContractMetrics` reports deterministic counts: `node_count` (unique object
nodes) and `max_depth` (root is depth 1).

```python
from derivatrace.contracts import ContractMetrics

metrics = ContractMetrics(node_count=5, max_depth=3)
assert metrics.node_count == 5
assert metrics.max_depth == 3
```

## 15. validate_contract

`validate_contract` performs iterative, whole-graph structural validation and
returns `ContractMetrics`.

Validation is **post-order**: each node's own invariants are checked only after
every descendant has been validated. This means an unsupported child subclass is
rejected by the exact-type policy before any parent reads its fields, so a
parent can never observe or execute forged/hostile child behaviour.

The validator also re-checks the **stored internal state** of every value object
recursively, including nested ones:

- a `money` unit's `Currency` is revalidated from its stored `_code` even when
  nested inside a `Number` inside a `Comparison` or `Payment`;
- `ObservationTime`/`SettlementTime` must be stored in canonical UTC
  (`tzinfo is UTC`), not merely timezone-aware;
- an `ExactNumber` must store the canonical zero `Decimal("0")` — forged
  `Decimal("-0")` or `Decimal("0.0")` forms are rejected.

These stored-state invariants are enforced independently of the constructor, so
objects mutated after construction (via `object.__setattr__`) are detected.

```python
from derivatrace.contracts import validate_contract

metrics = validate_contract(both)
assert metrics.node_count > 0
assert metrics.max_depth >= 2
```

## 16. Structural path semantics

Every node carries a structural path from the root, expressed as a tuple of
field names and integer indices (for example `("operands", 0, "amount")`).
Error objects expose this path so failures can be located without leaking
node `repr` values.

```python
err = ContractValidationError("bad", path=("operands", 1, "amount"))
assert "operands.1.amount" in str(err)
```

## 17. Depth and unique-node definitions

- **Depth:** the root contract is depth 1. A node's depth is one greater than
  its parent's depth.
- **Unique nodes:** counted by object identity; a subexpression shared by
  reference is counted once even when reached through several parents.

```python
shared = Payment(principal, usd, st)
dag = Both((shared, Scale(rate, shared)))
m = validate_contract(dag)
assert m.max_depth == 4
```

## 18. DAG-sharing behaviour

Shared subexpressions are accepted. They are validated once and counted once.
The validator uses an explicit ancestor set and an explored set so it never
loops and never re-expands a shared node at an equal-or-greater depth.

```python
shared = Payment(principal, usd, st)
dag = Both((shared, Scale(rate, shared)))
m = validate_contract(dag)
assert m.node_count == 5
```

## 19. Cycle detection

Reference cycles are rejected. A node encountered on the current traversal path
raises `ContractCycleError`.

```python
from derivatrace.contracts import Both, ContractCycleError

base = Both((pay, pay))
object.__setattr__(base, "operands", (base, pay))  # forge a self-cycle
with pytest.raises(ContractCycleError):
    validate_contract(base)
```

## 20. Complexity protection

Depth and unique-node limits raise `ContractComplexityError` before traversal
becomes expensive.

```python
from derivatrace.contracts import ContractComplexityError

deep = Scale(rate, pay)
for _ in range(20):
    deep = Scale(rate, deep)

with pytest.raises(ContractComplexityError):
    validate_contract(deep, limits=ValidationLimits(max_depth=8, max_unique_nodes=4096))
```

## 21. Executable examples

A complete, self-contained example:

```python
from datetime import datetime, timezone
from derivatrace.contracts import (
    ExactNumber,
    Currency,
    Unit,
    Number,
    Multiply,
    Add,
    Payment,
    Scale,
    Both,
    ConditionalContract,
    Zero,
    Comparison,
    ComparisonOperator,
    SettlementTime,
    validate_contract,
)

usd = Currency.from_code("USD")
principal = Number(ExactNumber.from_string("100"), Unit.money(usd))
rate = Number(ExactNumber.from_string("0.05"), Unit.scalar())
interest = Multiply(rate, principal)
total = Add((principal, interest))
st = SettlementTime.from_datetime(datetime(2030, 6, 1, tzinfo=timezone.utc))
pay = Payment(total, usd, st)
contract = Both((pay, Scale(rate, pay)))

metrics = validate_contract(contract)
assert metrics.node_count > 0
assert metrics.max_depth >= 2
```

## 22. Constructor failures versus graph-validation failures

Construction validates inputs immediately. Graph validation re-checks the same
invariants on every node so that objects forged or mutated after construction
(for example through `object.__setattr__`) cannot bypass validation.

```python
from derivatrace.contracts import ContractValidationError

forged = Number(ExactNumber.from_string("100"), Unit.money(usd))
object.__setattr__(forged, "value", 12345)  # forge the inner Decimal
with pytest.raises(ContractValidationError):
    validate_contract(Payment(forged, usd, st))
```

Unknown subclasses of the abstract expression bases are rejected by the
supported-node policy:

```python
from derivatrace.contracts import ScalarExpression

class Rogue(ScalarExpression):
    __slots__ = ("unit",)
    def __init__(self) -> None:
        self.unit = Unit.scalar()

with pytest.raises(ContractValidationError):
    validate_contract(Scale(Rogue(), pay))
```

Graph validation also re-checks the **stored internal state** of every value
object it relies on (`ExactNumber`, `Currency`, `Unit`, `ObservableId`,
`ObservationTime`, `SettlementTime`, `ValidationLimits`). A value object mutated
after construction via `object.__setattr__` — for example a `Currency._code`
lowercased to `"usd"`, a `money` unit stripped of its currency, or an
`ObservationTime._value` replaced by a naive `datetime` — is detected and
rejected, because the revalidation reads the raw stored fields and re-derives
the construction invariants rather than trusting the attributes or re-running
the constructors (which would silently normalize forged-but-valid state).
Deterministic value objects additionally require the exact approved type, so a
subclass of `Currency` or `Unit`, for instance, is rejected by validation.

## 23. Immutability boundaries

Nodes are frozen, slotted dataclasses. Their fields cannot be reassigned.
Reuse instances by reference; do not mutate them.

```python
with pytest.raises(AttributeError):
    principal.value = ExactNumber.from_string("200")
```

## 24. Security limitations

`validate_contract` is pure structural checking. It never executes node
content, never calls user callbacks, never evaluates observables, never uses
`eval`/`exec`, and never imports code dynamically. It is a defensive boundary
against malformed or hostile graphs, not a proof of economic correctness.

## 25. Stage 1A exclusions

The following are **explicitly outside** Stage 1A and do not exist in this API:

- Pricing, valuation, Greeks, and any financial calculation.
- Models, numerical engines, Monte Carlo, trees, and closed-form pricing.
- Market data, snapshots, and evaluation of observables.
- Canonicalization, canonical contract identity, and equivalence checks.
- Serialization and hashing of any kind (there is no serialize or deserialize API).
- A canonical payoff graph.
- Evidence certificates and reproducibility hashes.
- AI rewriting of contracts or results.

## 26. Planned Stage 1B and Stage 1C work

- **Stage 1B:** compile the validated graph into a canonical payoff graph and
  produce a structural canonical form with a deterministic canonical identity.
- **Stage 1C:** define graded validation levels and equivalence reporting on
  top of the canonical form.

Neither stage introduces pricing or engines; those remain later (Stage 2+).
