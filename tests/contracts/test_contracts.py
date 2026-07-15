from __future__ import annotations

from datetime import UTC, datetime

import pytest

from derivatrace.contracts import (
    BooleanConstant,
    Both,
    Comparison,
    ComparisonOperator,
    ConditionalContract,
    Contract,
    ContractInputError,
    ContractTypeMismatchError,
    Currency,
    ExactNumber,
    Number,
    Payment,
    Scale,
    SettlementTime,
    Unit,
    Zero,
)


def _usd() -> Currency:
    return Currency.from_code("USD")


def _eur() -> Currency:
    return Currency.from_code("EUR")


def _money(value: str, currency: Currency | None = None) -> Number:
    cur = currency or _usd()
    return Number(ExactNumber.from_string(value), Unit.money(cur))


def _scalar(value: str) -> Number:
    return Number(ExactNumber.from_string(value), Unit.scalar())


def _settlement() -> SettlementTime:
    return SettlementTime(datetime(2030, 6, 1, tzinfo=UTC))


def _payment(value: str = "100", currency: Currency | None = None) -> Payment:
    cur = currency or _usd()
    return Payment(_money(value, cur), cur, _settlement())


# ---------------------------------------------------------------------------
# Zero
# ---------------------------------------------------------------------------


def test_zero_is_contract() -> None:
    assert isinstance(Zero(), Contract)


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------


def test_payment_requires_scalar_amount() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Payment(BooleanConstant(True), _usd(), _settlement())  # type: ignore[arg-type]


def test_payment_requires_currency() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Payment(_money("1"), "USD", _settlement())  # type: ignore[arg-type]


def test_payment_requires_settlement_time() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Payment(_money("1"), _usd(), datetime(2030, 6, 1, tzinfo=UTC))  # type: ignore[arg-type]


def test_payment_requires_money_amount() -> None:
    with pytest.raises(ContractInputError):
        Payment(_scalar("1"), _usd(), _settlement())


def test_payment_currency_mismatch() -> None:
    with pytest.raises(ContractInputError):
        Payment(_money("1", _eur()), _usd(), _settlement())


def test_payment_valid() -> None:
    p = _payment()
    assert isinstance(p, Contract)
    assert p.amount.unit.currency == _usd()


# ---------------------------------------------------------------------------
# Both
# ---------------------------------------------------------------------------


def test_both_requires_tuple() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Both([_payment(), _payment()])  # type: ignore[arg-type]


def test_both_requires_at_least_two() -> None:
    with pytest.raises(ContractInputError):
        Both((_payment(),))


def test_both_requires_contract_elements() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Both((_payment(), _scalar("1")))  # type: ignore[arg-type]


def test_both_valid_preserves_order() -> None:
    a = _payment("1")
    b = _payment("2")
    both = Both((a, b))
    assert both.operands == (a, b)


# ---------------------------------------------------------------------------
# Scale
# ---------------------------------------------------------------------------


def test_scale_requires_scalar_factor() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Scale(BooleanConstant(True), _payment())  # type: ignore[arg-type]


def test_scale_requires_contract() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Scale(_scalar("2"), _scalar("1"))  # type: ignore[arg-type]


def test_scale_requires_dimensionless_factor() -> None:
    with pytest.raises(ContractInputError):
        Scale(_money("2"), _payment())


def test_scale_valid() -> None:
    s = Scale(_scalar("2"), _payment())
    assert isinstance(s, Contract)


# ---------------------------------------------------------------------------
# ConditionalContract
# ---------------------------------------------------------------------------


def _condition() -> Comparison:
    return Comparison(_scalar("1"), _scalar("2"), ComparisonOperator.LESS_THAN)


def test_conditional_contract_requires_boolean() -> None:
    with pytest.raises(ContractTypeMismatchError):
        ConditionalContract(_scalar("1"), _payment(), _payment())  # type: ignore[arg-type]


def test_conditional_contract_requires_contract_branches() -> None:
    with pytest.raises(ContractTypeMismatchError):
        ConditionalContract(_condition(), _scalar("1"), _payment())  # type: ignore[arg-type]


def test_conditional_contract_valid() -> None:
    c = ConditionalContract(_condition(), _payment("1"), _payment("2"))
    assert isinstance(c, Contract)


# ---------------------------------------------------------------------------
# Nested composition, equality, immutability
# ---------------------------------------------------------------------------


def test_nested_composition() -> None:
    inner = Both((_payment("1"), _payment("2")))
    scaled = Scale(_scalar("3"), inner)
    outer = Both((scaled, _payment("3")))
    assert isinstance(outer, Contract)


def test_contract_equality_and_hash() -> None:
    a = _payment("100")
    b = _payment("100")
    c = _payment("200")
    assert a == b
    assert a != c
    assert hash(a) == hash(b)
    assert isinstance(a, Contract)


def test_contract_immutable() -> None:
    p = _payment()
    with pytest.raises(AttributeError):
        p.currency = _eur()  # type: ignore[misc]


def test_operands_tuple_is_immutable() -> None:
    both = Both((_payment("1"), _payment("2")))
    with pytest.raises(AttributeError):
        both.operands = (_payment("3"),)  # type: ignore[misc]
