from __future__ import annotations

from datetime import UTC, datetime

import pytest

from derivatrace.contracts import (
    Add,
    AllOf,
    BooleanConstant,
    BooleanExpression,
    Both,
    ConditionalContract,
    Contract,
    ContractValidationError,
    Currency,
    ExactNumber,
    Number,
    Payment,
    ScalarExpression,
    Scale,
    SettlementTime,
    Unit,
    ValidationLimits,
    validate_contract,
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


def _payment(value: str = "10", currency: Currency | None = None) -> Payment:
    cur = currency or _usd()
    return Payment(_money(value, cur), cur, _settlement())


class _EvilScalar(ScalarExpression):
    """An unsupported third-party ScalarExpression subclass."""

    __slots__ = ("unit",)

    def __init__(self) -> None:
        object.__setattr__(self, "unit", Unit.scalar())


class _EvilBoolean(BooleanExpression):
    """An unsupported third-party BooleanExpression subclass."""


class _EvilContract(Contract):
    """An unsupported third-party Contract subclass."""


def test_unknown_scalar_subclass_rejected() -> None:
    evil = _EvilScalar()
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(Add((evil, _scalar("2"))), _payment()))


def test_unknown_boolean_subclass_rejected() -> None:
    evil = _EvilBoolean()
    with pytest.raises(ContractValidationError):
        validate_contract(
            ConditionalContract(
                AllOf((evil, BooleanConstant(False))), _payment(), _payment()
            )
        )


def test_unknown_contract_subclass_rejected() -> None:
    with pytest.raises(ContractValidationError):
        validate_contract(_EvilContract())


def test_unsupported_subclass_of_supported_concrete_node_rejected() -> None:
    # The supported-node policy is closed and exact: a subclass of an approved
    # concrete node is NOT automatically approved. A malicious subclass could
    # override field access, so only the exact reviewed type is admitted.
    class QuietNumber(Number):
        __slots__ = ()

    qn = QuietNumber(ExactNumber.from_string("5"), Unit.scalar())
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(qn, _payment()))


def test_forged_scalar_value_rejected() -> None:
    n = _money()
    object.__setattr__(n, "value", 12345)
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(n, _usd(), _settlement()))


def test_forged_currency_mismatch_rejected() -> None:
    p = _payment()
    object.__setattr__(p, "currency", _eur())
    with pytest.raises(ContractValidationError):
        validate_contract(p)


def test_dag_sharing_accepted_and_counted_once() -> None:
    shared = _payment("1")
    contract = Both((shared, Scale(_scalar("2"), shared)))
    metrics = validate_contract(contract)
    assert metrics.node_count == 5
    assert metrics.max_depth == 4


def test_cycle_rejected() -> None:
    both = Both((_payment("1"), _payment("2")))
    object.__setattr__(both, "operands", (both, _payment("3")))
    with pytest.raises(ContractValidationError):
        validate_contract(both)


def test_max_depth_correct_for_shared_node_at_different_depths() -> None:
    shared = _payment("1")
    contract = Both((shared, Scale(_scalar("2"), shared)))
    metrics = validate_contract(contract)
    assert metrics.max_depth == 4


def test_depth_limit_still_enforced_through_shared_nodes() -> None:
    shared = _payment("1")
    deep = Both((shared, Scale(_scalar("2"), shared)))
    with pytest.raises(ContractValidationError):
        validate_contract(
            deep, limits=ValidationLimits(max_depth=2, max_unique_nodes=1000)
        )


def test_unique_node_metric_matches_explicit_count() -> None:
    contract = Both((_payment("1"), _payment("2")))
    metrics = validate_contract(contract)
    # Both + (Payment + Number) + (Payment + Number) = 5 unique nodes.
    # Both=1, each Payment=2 then its money Number child=3.
    assert metrics.node_count == 5
    assert metrics.max_depth == 3
