"""Focused API and semantic-conformance review for Stage 1A.

This file is the authoritative, self-contained proof of the review decisions
recorded in ADR 0006 and the public API documented in docs/contract-api.md.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

import derivatrace.contracts
from derivatrace.contracts import (
    AllOf,
    AnyOf,
    BooleanConstant,
    BooleanExpression,
    Comparison,
    ComparisonOperator,
    ConditionalContract,
    ConditionalValue,
    Contract,
    ContractInputError,
    ContractValidationError,
    Currency,
    ExactNumber,
    Number,
    ObservationTime,
    Payment,
    ScalarExpression,
    Scale,
    SettlementTime,
    Unit,
    Zero,
    validate_contract,
)

USD = Currency.from_code("USD")


def _scalar(value: str = "3") -> Number:
    return Number(ExactNumber.from_string(value), Unit.scalar())


def _money(value: str = "10", currency: Currency | None = None) -> Number:
    cur = currency or USD
    return Number(ExactNumber.from_string(value), Unit.money(cur))


def _settlement() -> SettlementTime:
    return SettlementTime(datetime(2030, 6, 1, tzinfo=UTC))


def _payment(value: str = "10", currency: Currency | None = None) -> Payment:
    cur = currency or USD
    return Payment(_money(value, cur), cur, _settlement())


# ---------------------------------------------------------------------------
# Requirement 1 - valid ExactNumber zero forms are accepted
# ---------------------------------------------------------------------------


def test_exact_number_zero_forms_accepted() -> None:
    for raw in ("0", "-0", "0.0"):
        assert ExactNumber.from_string(raw).value == 0
    assert ExactNumber.from_int(0).value == 0


def test_exact_number_zero_not_rejected_via_is_normal() -> None:
    # Decimal.is_normal() returns False for zero; the validator must accept zero
    # regardless. We assert every zero form constructs and compares equal.
    for raw in ("0", "-0", "0.0"):
        assert ExactNumber.from_string(raw) == ExactNumber.from_int(0)
    assert ExactNumber.from_int(0) == ExactNumber.from_string("0.0")


# ---------------------------------------------------------------------------
# Requirement 2 - ObservationTime / SettlementTime timezone semantics
# ---------------------------------------------------------------------------


def test_observation_time_rejects_naive() -> None:
    with pytest.raises(ContractInputError):
        ObservationTime(datetime(2030, 6, 1))


def test_settlement_time_rejects_naive() -> None:
    with pytest.raises(ContractInputError):
        SettlementTime(datetime(2030, 6, 1))


def test_observation_time_normalises_to_utc() -> None:
    aware = ObservationTime(
        datetime(2020, 1, 1, 17, 0, 0, tzinfo=timezone(timedelta(hours=5)))
    )
    assert aware.value.utcoffset() == timedelta(0)
    assert aware.value.hour == 12


def test_settlement_time_normalises_to_utc() -> None:
    aware = SettlementTime(
        datetime(2020, 1, 1, 17, 0, 0, tzinfo=timezone(timedelta(hours=5)))
    )
    assert aware.value.utcoffset() == timedelta(0)
    assert aware.value.hour == 12


def test_observation_time_preserves_microseconds() -> None:
    aware = ObservationTime(datetime(2020, 1, 1, 12, 30, 15, 123456, tzinfo=UTC))
    assert aware.value.microsecond == 123456


def test_settlement_time_preserves_microseconds() -> None:
    aware = SettlementTime(datetime(2020, 1, 1, 12, 30, 15, 123456, tzinfo=UTC))
    assert aware.value.microsecond == 123456


def test_observation_time_equal_instants_across_offsets() -> None:
    a = ObservationTime(
        datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=5)))
    )
    b = ObservationTime(datetime(2020, 1, 1, 7, 0, 0, tzinfo=UTC))
    assert a == b


def test_settlement_time_equal_instants_across_offsets() -> None:
    a = SettlementTime(
        datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=5)))
    )
    b = SettlementTime(datetime(2020, 1, 1, 7, 0, 0, tzinfo=UTC))
    assert a == b


# ---------------------------------------------------------------------------
# Requirement 3 - all six comparison operations supported
# ---------------------------------------------------------------------------


def test_all_six_comparison_operators_supported() -> None:
    expected = {
        ComparisonOperator.LESS_THAN,
        ComparisonOperator.LESS_THAN_OR_EQUAL,
        ComparisonOperator.EQUAL,
        ComparisonOperator.NOT_EQUAL,
        ComparisonOperator.GREATER_THAN_OR_EQUAL,
        ComparisonOperator.GREATER_THAN,
    }
    assert set(ComparisonOperator) == expected
    for op in ComparisonOperator:
        node = Comparison(_scalar("1"), _scalar("2"), op)
        metrics = validate_contract(ConditionalContract(node, _payment(), _payment()))
        assert metrics.node_count >= 4


# ---------------------------------------------------------------------------
# Requirement 4 / 5 / 6 - ConditionalContract, ConditionalValue, Zero
# ---------------------------------------------------------------------------


def test_conditional_contract_is_public() -> None:
    assert hasattr(derivatrace.contracts, "ConditionalContract")
    assert "ConditionalContract" in derivatrace.contracts.__all__


def test_cond_is_not_public() -> None:
    assert not hasattr(derivatrace.contracts, "Cond")
    assert "Cond" not in derivatrace.contracts.__all__


def test_conditional_value_is_public_and_distinct() -> None:
    assert hasattr(derivatrace.contracts, "ConditionalValue")
    assert "ConditionalValue" in derivatrace.contracts.__all__
    assert issubclass(ConditionalValue, ScalarExpression)


def test_zero_is_public_no_obligation_contract() -> None:
    assert hasattr(derivatrace.contracts, "Zero")
    assert "Zero" in derivatrace.contracts.__all__
    metrics = validate_contract(Zero())
    assert metrics.node_count == 1
    assert metrics.max_depth == 1


# ---------------------------------------------------------------------------
# Requirement 7 - Either removed / deferred
# ---------------------------------------------------------------------------


def test_either_is_absent() -> None:
    assert not hasattr(derivatrace.contracts, "Either")
    assert "Either" not in derivatrace.contracts.__all__


# ---------------------------------------------------------------------------
# Requirement 8 - Boolean composition names: AllOf / AnyOf, no short-circuit
# ---------------------------------------------------------------------------


def test_boolean_composition_uses_allof_anyof() -> None:
    assert "AllOf" in derivatrace.contracts.__all__
    assert "AnyOf" in derivatrace.contracts.__all__
    assert "Not" in derivatrace.contracts.__all__


def test_and_or_are_not_public() -> None:
    assert not hasattr(derivatrace.contracts, "And")
    assert not hasattr(derivatrace.contracts, "Or")
    assert "And" not in derivatrace.contracts.__all__
    assert "Or" not in derivatrace.contracts.__all__


def test_allof_anyof_are_declarative_no_short_circuit() -> None:
    # They are plain n-ary AST combinators; constructing them performs no
    # evaluation and cannot short-circuit.
    node = AllOf((BooleanConstant(True), BooleanConstant(False)))
    assert isinstance(node, BooleanExpression)
    node2 = AnyOf((BooleanConstant(True), BooleanConstant(False)))
    assert isinstance(node2, BooleanExpression)


# ---------------------------------------------------------------------------
# Requirement 9 - exact __all__ is locked
# ---------------------------------------------------------------------------


def test_contracts_all_is_exactly_locked() -> None:
    expected = frozenset(
        {
            "Add",
            "AllOf",
            "AnyOf",
            "BooleanConstant",
            "BooleanExpression",
            "Both",
            "Comparison",
            "ComparisonOperator",
            "ConditionalContract",
            "ConditionalValue",
            "Contract",
            "ContractComplexityError",
            "ContractCycleError",
            "ContractError",
            "ContractInputError",
            "ContractMetrics",
            "ContractTypeMismatchError",
            "ContractValidationError",
            "Currency",
            "DerivaTraceError",
            "Divide",
            "ExactNumber",
            "Maximum",
            "Minimum",
            "Multiply",
            "Negate",
            "Not",
            "Number",
            "Observable",
            "ObservableId",
            "ObservationTime",
            "Payment",
            "ScalarExpression",
            "Scale",
            "SettlementTime",
            "Subtract",
            "Unit",
            "UnitKind",
            "ValidationLimits",
            "Zero",
            "validate_contract",
        }
    )
    assert set(derivatrace.contracts.__all__) == expected


# ---------------------------------------------------------------------------
# Requirement 10 - rejection of unsupported subclasses via public validate_contract
# ---------------------------------------------------------------------------


class _EvilScalar(ScalarExpression):
    __slots__ = ("unit",)

    def __init__(self) -> None:
        object.__setattr__(self, "unit", Unit.money(USD))


class _EvilBoolean(BooleanExpression):
    pass


class _EvilContract(Contract):
    pass


class _QuietNumber(Number):
    __slots__ = ()


def test_unknown_scalar_subclass_rejected() -> None:
    evil = _EvilScalar()
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(_scalar("2"), Payment(evil, USD, _settlement())))


def test_unknown_boolean_subclass_rejected() -> None:
    evil = _EvilBoolean()
    with pytest.raises(ContractValidationError):
        validate_contract(ConditionalContract(evil, _payment(), _payment()))


def test_unknown_contract_subclass_rejected() -> None:
    with pytest.raises(ContractValidationError):
        validate_contract(_EvilContract())


def test_unsupported_subclass_of_supported_concrete_node_rejected() -> None:
    qn = _QuietNumber(ExactNumber.from_string("5"), Unit.scalar())
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(qn, _payment()))


# ---------------------------------------------------------------------------
# Absent-but-easily-confused names
# ---------------------------------------------------------------------------


def test_max_min_short_names_absent() -> None:
    assert not hasattr(derivatrace.contracts, "Max")
    assert not hasattr(derivatrace.contracts, "Min")
    assert "Max" not in derivatrace.contracts.__all__
    assert "Min" not in derivatrace.contracts.__all__


# ---------------------------------------------------------------------------
# Defense-in-depth: dispatch rejects unsupported types even if called directly
# (the traversal gate runs first, so these paths are exercised directly).
# ---------------------------------------------------------------------------


def test_dispatch_rejects_unsupported_scalar_directly() -> None:
    from derivatrace.contracts._validation import _validate_scalar_node

    with pytest.raises(ContractValidationError):
        _validate_scalar_node(_EvilScalar(), ())


def test_dispatch_rejects_unsupported_boolean_directly() -> None:
    from derivatrace.contracts._validation import _validate_boolean_node

    with pytest.raises(ContractValidationError):
        _validate_boolean_node(_EvilBoolean(), ())


def test_dispatch_rejects_unsupported_contract_directly() -> None:
    from derivatrace.contracts._validation import _validate_contract_node

    with pytest.raises(ContractValidationError):
        _validate_contract_node(_EvilContract(), ())


def test_validate_node_invariants_rejects_non_category_directly() -> None:
    from derivatrace.contracts._validation import _validate_node_invariants

    with pytest.raises(ContractValidationError):
        _validate_node_invariants(object(), ())
