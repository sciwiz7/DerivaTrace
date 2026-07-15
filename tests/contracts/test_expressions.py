from __future__ import annotations

from datetime import UTC, datetime

import pytest

from derivatrace.contracts import (
    Add,
    AllOf,
    AnyOf,
    BooleanConstant,
    BooleanExpression,
    Comparison,
    ComparisonOperator,
    ConditionalValue,
    ContractInputError,
    ContractTypeMismatchError,
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
    ScalarExpression,
    Subtract,
    Unit,
    UnitKind,
)


def _usd() -> Currency:
    return Currency.from_code("USD")


def _eur() -> Currency:
    return Currency.from_code("EUR")


def _money(value: str) -> Number:
    return Number(ExactNumber.from_string(value), Unit.money(_usd()))


def _scalar(value: str) -> Number:
    return Number(ExactNumber.from_string(value), Unit.scalar())


def _obs() -> Observable:
    return Observable(
        ObservableId.from_parts("equity", "ACME", "spot"),
        ObservationTime(datetime(2030, 1, 1, tzinfo=UTC)),
        Unit.scalar(),
    )


# ---------------------------------------------------------------------------
# Number / Observable
# ---------------------------------------------------------------------------


def test_number_requires_exact_number() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Number("100", Unit.scalar())  # type: ignore[arg-type]


def test_number_requires_unit() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Number(ExactNumber.from_int(1), "scalar")  # type: ignore[arg-type]


def test_number_valid() -> None:
    n = _money("10")
    assert n.value == ExactNumber.from_string("10")
    assert n.unit.kind == UnitKind.MONEY


def test_observable_requires_valid_parts() -> None:
    t = ObservationTime(datetime(2030, 1, 1, tzinfo=UTC))
    with pytest.raises(ContractTypeMismatchError):
        Observable("bad", t, Unit.scalar())  # type: ignore[arg-type]
    with pytest.raises(ContractTypeMismatchError):
        Observable(ObservableId.from_parts("e", "A", "f"), "t", Unit.scalar())  # type: ignore[arg-type]
    with pytest.raises(ContractTypeMismatchError):
        Observable(ObservableId.from_parts("e", "A", "f"), t, "u")  # type: ignore[arg-type]


def test_observable_valid() -> None:
    o = _obs()
    assert isinstance(o, ScalarExpression)
    assert o.unit == Unit.scalar()


# ---------------------------------------------------------------------------
# Add
# ---------------------------------------------------------------------------


def test_add_requires_tuple() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Add(("x", _scalar("1")))  # type: ignore[arg-type]


def test_add_requires_at_least_two() -> None:
    with pytest.raises(ContractInputError):
        Add((_scalar("1"),))


def test_add_requires_scalar_elements() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Add((_scalar("1"), BooleanConstant(True)))  # type: ignore[arg-type]


def test_add_requires_same_unit() -> None:
    with pytest.raises(ContractInputError):
        Add((_scalar("1"), _money("2")))


def test_add_valid() -> None:
    a = Add((_scalar("1"), _scalar("2"), _scalar("3")))
    assert isinstance(a, ScalarExpression)
    assert a.unit == Unit.scalar()


# ---------------------------------------------------------------------------
# Subtract
# ---------------------------------------------------------------------------


def test_subtract_requires_scalars() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Subtract(_scalar("1"), BooleanConstant(True))  # type: ignore[arg-type]


def test_subtract_requires_same_unit() -> None:
    with pytest.raises(ContractInputError):
        Subtract(_scalar("1"), _money("2"))


def test_subtract_valid() -> None:
    s = Subtract(_scalar("5"), _scalar("3"))
    assert s.unit == Unit.scalar()


# ---------------------------------------------------------------------------
# Multiply
# ---------------------------------------------------------------------------


def test_multiply_requires_scalars() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Multiply(_scalar("1"), BooleanConstant(True))  # type: ignore[arg-type]


def test_multiply_rejects_money_x_money() -> None:
    with pytest.raises(ContractInputError):
        Multiply(_money("1"), _money("2"))


def test_multiply_scalar_x_scalar() -> None:
    m = Multiply(_scalar("2"), _scalar("3"))
    assert m.unit == Unit.scalar()


def test_multiply_scalar_x_money() -> None:
    m = Multiply(_scalar("2"), _money("3"))
    assert m.unit.kind == UnitKind.MONEY
    assert m.unit.currency == _usd()


def test_multiply_money_x_scalar() -> None:
    m = Multiply(_money("3"), _scalar("2"))
    assert m.unit.kind == UnitKind.MONEY
    assert m.unit.currency == _usd()


# ---------------------------------------------------------------------------
# Divide
# ---------------------------------------------------------------------------


def test_divide_requires_scalars() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Divide(_scalar("1"), BooleanConstant(True))  # type: ignore[arg-type]


def test_divide_rejects_non_scalar_denominator() -> None:
    with pytest.raises(ContractInputError):
        Divide(_scalar("1"), _money("2"))


def test_divide_rejects_literal_zero_denominator() -> None:
    with pytest.raises(ContractInputError):
        Divide(_scalar("1"), _scalar("0"))


def test_divide_allows_symbolic_nonzero_denominator() -> None:
    d = Divide(_scalar("1"), _obs())
    assert d.unit == Unit.scalar()


def test_divide_valid() -> None:
    d = Divide(_money("6"), _scalar("2"))
    assert d.unit.kind == UnitKind.MONEY


# ---------------------------------------------------------------------------
# Negate
# ---------------------------------------------------------------------------


def test_negate_requires_scalar() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Negate(BooleanConstant(True))  # type: ignore[arg-type]


def test_negate_preserves_unit() -> None:
    n = Negate(_money("5"))
    assert n.unit.kind == UnitKind.MONEY


# ---------------------------------------------------------------------------
# Maximum / Minimum
# ---------------------------------------------------------------------------


def test_maximum_requires_at_least_two() -> None:
    with pytest.raises(ContractInputError):
        Maximum((_scalar("1"),))


def test_maximum_requires_same_unit() -> None:
    with pytest.raises(ContractInputError):
        Maximum((_scalar("1"), _money("2")))


def test_maximum_valid() -> None:
    m = Maximum((_scalar("1"), _scalar("2")))
    assert m.unit == Unit.scalar()


def test_minimum_requires_at_least_two() -> None:
    with pytest.raises(ContractInputError):
        Minimum((_money("1"),))


def test_minimum_valid() -> None:
    m = Minimum((_money("1"), _money("2")))
    assert m.unit.kind == UnitKind.MONEY


# ---------------------------------------------------------------------------
# ConditionalValue
# ---------------------------------------------------------------------------


def test_conditional_value_requires_boolean_condition() -> None:
    with pytest.raises(ContractTypeMismatchError):
        ConditionalValue(_scalar("1"), _scalar("1"), _scalar("2"))  # type: ignore[arg-type]


def test_conditional_value_requires_scalar_branches() -> None:
    with pytest.raises(ContractTypeMismatchError):
        ConditionalValue(BooleanConstant(True), BooleanConstant(True), _scalar("2"))  # type: ignore[arg-type]


def test_conditional_value_requires_same_unit() -> None:
    with pytest.raises(ContractInputError):
        ConditionalValue(BooleanConstant(True), _scalar("1"), _money("2"))


def test_conditional_value_valid() -> None:
    c = ConditionalValue(BooleanConstant(True), _money("1"), _money("2"))
    assert c.unit.kind == UnitKind.MONEY


# ---------------------------------------------------------------------------
# Boolean nodes
# ---------------------------------------------------------------------------


def test_boolean_constant_requires_bool() -> None:
    with pytest.raises(ContractTypeMismatchError):
        BooleanConstant(1)  # type: ignore[arg-type]


def test_boolean_constant_valid() -> None:
    b = BooleanConstant(False)
    assert isinstance(b, BooleanExpression)
    assert b.value is False


def test_comparison_requires_scalars() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Comparison(_scalar("1"), BooleanConstant(True), ComparisonOperator.LESS_THAN)  # type: ignore[arg-type]


def test_comparison_requires_operator() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Comparison(_scalar("1"), _scalar("2"), "<")  # type: ignore[arg-type]


def test_comparison_requires_same_unit() -> None:
    with pytest.raises(ContractInputError):
        Comparison(_scalar("1"), _money("2"), ComparisonOperator.LESS_THAN)


def test_comparison_valid() -> None:
    c = Comparison(_scalar("1"), _scalar("2"), ComparisonOperator.LESS_THAN)
    assert c.operator == ComparisonOperator.LESS_THAN


def test_comparison_operator_members() -> None:
    for op in ComparisonOperator:
        assert isinstance(op.value, str)


def test_all_of_requires_tuple() -> None:
    with pytest.raises(ContractTypeMismatchError):
        AllOf([BooleanConstant(True), BooleanConstant(False)])  # type: ignore[arg-type]


def test_all_of_requires_at_least_two() -> None:
    with pytest.raises(ContractInputError):
        AllOf((BooleanConstant(True),))


def test_all_of_requires_boolean_elements() -> None:
    with pytest.raises(ContractTypeMismatchError):
        AllOf((BooleanConstant(True), _scalar("1")))  # type: ignore[arg-type]


def test_all_of_valid() -> None:
    a = AllOf((BooleanConstant(True), BooleanConstant(False)))
    assert isinstance(a, BooleanExpression)


def test_any_of_valid() -> None:
    a = AnyOf((BooleanConstant(True), BooleanConstant(False)))
    assert isinstance(a, BooleanExpression)


def test_not_requires_boolean() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Not(_scalar("1"))  # type: ignore[arg-type]


def test_not_valid() -> None:
    n = Not(BooleanConstant(True))
    assert isinstance(n, BooleanExpression)


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


def test_scalar_nodes_immutable() -> None:
    n = Add((_scalar("1"), _scalar("2")))
    with pytest.raises(AttributeError):
        n.unit = Unit.scalar()  # type: ignore[misc]
