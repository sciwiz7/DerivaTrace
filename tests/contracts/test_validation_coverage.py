from __future__ import annotations

from datetime import UTC, datetime

import pytest

from derivatrace.contracts import (
    Add,
    AllOf,
    AnyOf,
    BooleanConstant,
    Both,
    Comparison,
    ComparisonOperator,
    ConditionalContract,
    ConditionalValue,
    ContractError,
    ContractValidationError,
    Currency,
    Divide,
    ExactNumber,
    Maximum,
    Minimum,
    Multiply,
    Negate,
    Not,
    Number,
    Observable,
    ObservableId,
    ObservationTime,
    Payment,
    Scale,
    SettlementTime,
    Subtract,
    Unit,
    Zero,
    validate_contract,
)
from derivatrace.contracts._validation import (
    _iter_children,
    _multiply_unit,
    _validate_node_invariants,
)


def _usd() -> Currency:
    return Currency.from_code("USD")


def _eur() -> Currency:
    return Currency.from_code("EUR")


def _settlement() -> SettlementTime:
    return SettlementTime(datetime(2030, 6, 1, tzinfo=UTC))


def _scalar(value: str = "3") -> Number:
    return Number(ExactNumber.from_string(value), Unit.scalar())


def _money(value: str = "10", currency: Currency | None = None) -> Number:
    cur = currency or _usd()
    return Number(ExactNumber.from_string(value), Unit.money(cur))


def _obs() -> Observable:
    return Observable(
        ObservableId.from_parts("equity", "ACME", "spot"),
        ObservationTime(datetime(2030, 1, 1, tzinfo=UTC)),
        Unit.scalar(),
    )


def _bool(value: bool = True) -> BooleanConstant:
    return BooleanConstant(value)


def _payment(value: str = "10", currency: Currency | None = None) -> Payment:
    cur = currency or _usd()
    return Payment(_money(value, cur), cur, _settlement())


def _forge(node: object, field: str, value: object) -> object:
    object.__setattr__(node, field, value)
    return node


# ---------------------------------------------------------------------------
# A contract that contains at least one instance of every node type, all valid.
# Running validate_contract over it exercises every success branch of the
# internal validators and every branch of _iter_children.
# ---------------------------------------------------------------------------
def test_validate_every_node_type_via_big_contract() -> None:
    usd = _usd()
    st = _settlement()
    obs = _obs()
    s = _scalar()
    m = _money()
    add = Add((s, s))
    sub = Subtract(s, s)
    mul_ss = Multiply(s, s)
    mul_ms = Multiply(m, s)
    mul_sm = Multiply(s, m)
    div = Divide(m, s)
    neg = Negate(s)
    mx = Maximum((s, s))
    mn = Minimum((m, m))
    cv = ConditionalValue(_bool(True), m, m)
    cmp = Comparison(s, s, ComparisonOperator.GREATER_THAN)
    allof = AllOf((_bool(True), _bool(False)))
    anyof = AnyOf((_bool(True), _bool(False)))
    notb = Not(_bool(False))
    p = Payment(m, usd, st)

    contract = Both(
        (
            p,
            Payment(mul_ms, usd, st),
            Payment(mul_sm, usd, st),
            Payment(div, usd, st),
            Payment(mn, usd, st),
            Payment(cv, usd, st),
            ConditionalContract(cmp, Zero(), Zero()),
            ConditionalContract(allof, Zero(), Zero()),
            ConditionalContract(anyof, Zero(), Zero()),
            ConditionalContract(notb, Zero(), Zero()),
            Scale(obs, p),
            Scale(s, p),
            Scale(add, p),
            Scale(sub, p),
            Scale(mul_ss, p),
            Scale(neg, p),
            Scale(mx, p),
            Zero(),
        )
    )
    metrics = validate_contract(contract)
    assert metrics.node_count > 0
    assert metrics.max_depth >= 4


# ---------------------------------------------------------------------------
# Every node type's _iter_children branch, called directly.
# ---------------------------------------------------------------------------
def test_iter_children_branches() -> None:
    usd = _usd()
    s = _scalar()
    m = _money()
    p = Payment(m, usd, _settlement())
    for node in (
        Add((s, s)),
        Maximum((s, s)),
        Minimum((s, s)),
        Subtract(s, s),
        Multiply(s, s),
        Divide(m, s),
        Negate(s),
        ConditionalValue(_bool(True), m, m),
        Comparison(s, s, ComparisonOperator.LESS_THAN),
        AllOf((_bool(True), _bool(False))),
        AnyOf((_bool(True), _bool(False))),
        Not(_bool(False)),
        p,
        Both((p, p)),
        Scale(s, p),
        ConditionalContract(_bool(True), Zero(), Zero()),
        # Leaves return no children.
        Number(ExactNumber.from_int(1), Unit.scalar()),
        _obs(),
        _bool(False),
        Zero(),
    ):
        assert isinstance(_iter_children(node), list)


# ---------------------------------------------------------------------------
# _multiply_unit directly: all four combinations.
# ---------------------------------------------------------------------------
def test_multiply_unit_combinations() -> None:
    scalar = Unit.scalar()
    money = Unit.money(_usd())
    assert _multiply_unit(scalar, scalar) == scalar
    assert _multiply_unit(money, scalar) == money
    assert _multiply_unit(scalar, money) == money
    with pytest.raises(ContractValidationError):
        _multiply_unit(money, money)


# ---------------------------------------------------------------------------
# Every remaining failure branch of the internal validators, exercised by
# forging a field after construction and calling _validate_node_invariants
# directly.
# ---------------------------------------------------------------------------
_FORGERIES: list[tuple[str, object, str, object]] = []


def _scalar_forge() -> list[tuple[str, object, str, object]]:
    s = _scalar()
    m = _money()
    cases: list[tuple[str, object, str, object]] = [
        ("Number.value not ExactNumber", _scalar(), "value", 123),
        ("Number.unit not Unit", _scalar(), "unit", "x"),
        ("Observable.observable_id bad", _obs(), "observable_id", "x"),
        ("Observable.observation_time bad", _obs(), "observation_time", "x"),
        ("Observable.unit bad", _obs(), "unit", "x"),
        ("Add.operands not tuple", Add((s, s)), "operands", [s, s]),
        ("Add.operands <2", Add((s, s)), "operands", (s,)),
        ("Add.operands non-scalar", Add((s, s)), "operands", (s, _bool())),
        ("Add.operands mismatch", Add((s, s)), "operands", (s, m)),
        ("Add.unit mismatch", Add((s, s)), "unit", Unit.money(_usd())),
        ("Subtract.minuend not scalar", Subtract(s, s), "minuend", _bool()),
        ("Subtract.subtrahend not scalar", Subtract(s, s), "subtrahend", _bool()),
        ("Subtract node.unit mismatch", Subtract(s, s), "unit", Unit.money(_usd())),
        ("Subtract unit mismatch", Subtract(s, s), "minuend", m),
        ("Multiply.left not scalar", Multiply(s, s), "left", _bool()),
        ("Multiply.right not scalar", Multiply(s, s), "right", _bool()),
        ("Multiply unit mismatch", Multiply(m, s), "unit", Unit.scalar()),
        ("Divide.numerator not scalar", Divide(m, s), "numerator", _bool()),
        ("Divide.denominator not scalar", Divide(m, s), "denominator", _bool()),
        ("Divide numerator unit mismatch", Divide(m, s), "numerator", s),
        ("Negate.operand not scalar", Negate(s), "operand", _bool()),
        ("Negate unit mismatch", Negate(s), "unit", Unit.money(_usd())),
        ("Maximum.operands not tuple", Maximum((s, s)), "operands", [s, s]),
        ("Maximum.operands <2", Maximum((s, s)), "operands", (s,)),
        ("Maximum.operands non-scalar", Maximum((s, s)), "operands", (s, _bool())),
        ("Maximum.operands mismatch", Maximum((s, s)), "operands", (s, m)),
        ("Maximum.unit mismatch", Maximum((s, s)), "unit", Unit.money(_usd())),
        ("Minimum.operands mismatch", Minimum((m, m)), "operands", (m, s)),
        (
            "ConditionalValue.condition not boolean",
            ConditionalValue(_bool(), m, m),
            "condition",
            s,
        ),
        (
            "ConditionalValue.true not scalar",
            ConditionalValue(_bool(), m, m),
            "true_value",
            _bool(),
        ),
        (
            "ConditionalValue.false not scalar",
            ConditionalValue(_bool(), m, m),
            "false_value",
            _bool(),
        ),
        (
            "ConditionalValue branch mismatch",
            ConditionalValue(_bool(), m, m),
            "false_value",
            s,
        ),
        (
            "ConditionalValue unit mismatch",
            ConditionalValue(_bool(), m, m),
            "unit",
            Unit.scalar(),
        ),
        ("BooleanConstant.value not bool", _bool(), "value", 1),
        (
            "Comparison.left not scalar",
            Comparison(s, s, ComparisonOperator.LESS_THAN),
            "left",
            _bool(),
        ),
        (
            "Comparison.right not scalar",
            Comparison(s, s, ComparisonOperator.LESS_THAN),
            "right",
            _bool(),
        ),
        (
            "Comparison.operator not enum",
            Comparison(s, s, ComparisonOperator.LESS_THAN),
            "operator",
            "x",
        ),
        (
            "Comparison unit mismatch",
            Comparison(s, s, ComparisonOperator.LESS_THAN),
            "right",
            m,
        ),
        ("AllOf.operands not tuple", AllOf((_bool(), _bool())), "operands", [_bool()]),
        ("AllOf.operands <2", AllOf((_bool(), _bool())), "operands", (_bool(),)),
        (
            "AllOf.operands non-boolean",
            AllOf((_bool(), _bool())),
            "operands",
            (_bool(), s),
        ),
        ("AnyOf.operands <2", AnyOf((_bool(), _bool())), "operands", (_bool(),)),
        ("Not.operand not boolean", Not(_bool()), "operand", s),
        ("Payment.amount not scalar", _payment(), "amount", _bool()),
        ("Payment.amount not money", _payment(), "amount", s),
        ("Payment.currency not Currency", _payment(), "currency", "x"),
        ("Payment.settlement not SettlementTime", _payment(), "settlement_time", "x"),
        (
            "Both.operands not tuple",
            Both((_payment(), _payment())),
            "operands",
            [_payment()],
        ),
        ("Both.operands <2", Both((_payment(), _payment())), "operands", (_payment(),)),
        (
            "Both.operands non-contract",
            Both((_payment(), _payment())),
            "operands",
            (_payment(), s),
        ),
        ("Scale.factor not scalar", Scale(s, _payment()), "factor", _bool()),
        ("Scale.contract not contract", Scale(s, _payment()), "contract", s),
        (
            "ConditionalContract.condition not boolean",
            ConditionalContract(_bool(), Zero(), Zero()),
            "condition",
            s,
        ),
        (
            "ConditionalContract.true not contract",
            ConditionalContract(_bool(), Zero(), Zero()),
            "true_contract",
            s,
        ),
        (
            "ConditionalContract.false not contract",
            ConditionalContract(_bool(), Zero(), Zero()),
            "false_contract",
            s,
        ),
    ]
    return cases


@pytest.mark.parametrize(
    "description,node,field,value",
    _scalar_forge(),
    ids=[c[0] for c in _scalar_forge()],
)
def test_validate_node_invariants_rejects_forgeries(
    description: str, node: object, field: str, value: object
) -> None:
    _forge(node, field, value)
    with pytest.raises(ContractError):
        _validate_node_invariants(node, ())


def test_validate_node_invariants_rejects_unsupported_object() -> None:
    with pytest.raises(ContractValidationError):
        _validate_node_invariants("not a node", ())
    with pytest.raises(ContractValidationError):
        _validate_node_invariants(12345, ())
    with pytest.raises(ContractValidationError):
        _validate_node_invariants([_scalar()], ())


def test_validate_node_invariants_accepts_every_valid_node() -> None:
    usd = _usd()
    s = _scalar()
    m = _money()
    p = Payment(m, usd, _settlement())
    valid_nodes = [
        s,
        _obs(),
        Add((s, s)),
        Subtract(s, s),
        Multiply(s, s),
        Multiply(m, s),
        Multiply(s, m),
        Divide(m, s),
        Negate(s),
        Maximum((s, s)),
        Minimum((m, m)),
        ConditionalValue(_bool(True), m, m),
        _bool(True),
        Comparison(s, s, ComparisonOperator.LESS_THAN),
        AllOf((_bool(True), _bool(False))),
        AnyOf((_bool(True), _bool(False))),
        Not(_bool(False)),
        Zero(),
        p,
        Both((p, p)),
        Scale(s, p),
        ConditionalContract(_bool(True), Zero(), Zero()),
    ]
    for node in valid_nodes:
        _validate_node_invariants(node, ())


def test_error_str_without_path() -> None:
    err = ContractValidationError("boom")
    text = str(err)
    assert "contract.validation" in text
    assert "boom" in text
    assert "path" not in text


def test_add_construction_rejects_non_tuple_operands() -> None:
    with pytest.raises(ContractError):
        Add(_scalar("1"))  # type: ignore[arg-type]
