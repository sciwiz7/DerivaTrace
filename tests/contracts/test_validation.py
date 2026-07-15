from __future__ import annotations

from datetime import UTC, datetime

import pytest

from derivatrace.contracts import (
    Add,
    AllOf,
    BooleanConstant,
    BooleanExpression,
    Both,
    Comparison,
    ComparisonOperator,
    ConditionalContract,
    Contract,
    ContractComplexityError,
    ContractCycleError,
    ContractError,
    ContractInputError,
    ContractTypeMismatchError,
    ContractValidationError,
    Currency,
    DerivaTraceError,
    Divide,
    ExactNumber,
    Multiply,
    Number,
    Observable,
    ObservableId,
    ObservationTime,
    Payment,
    ScalarExpression,
    Scale,
    SettlementTime,
    Unit,
    ValidationLimits,
    Zero,
    validate_contract,
)


def _usd() -> Currency:
    return Currency.from_code("USD")


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


def _obs() -> Observable:
    return Observable(
        ObservableId.from_parts("equity", "ACME", "spot"),
        ObservationTime(datetime(2030, 1, 1, tzinfo=UTC)),
        Unit.scalar(),
    )


def _condition() -> Comparison:
    return Comparison(_scalar("1"), _scalar("2"), ComparisonOperator.LESS_THAN)


def build_chain(depth: int) -> Contract:
    leaf: Contract = Zero()
    for _ in range(depth):
        leaf = Scale(_scalar("1"), leaf)
    return leaf


# ---------------------------------------------------------------------------
# Valid contracts
# ---------------------------------------------------------------------------


def test_validate_zero() -> None:
    metrics = validate_contract(Zero())
    assert metrics.node_count == 1
    assert metrics.max_depth == 1


def test_validate_simple_payment() -> None:
    metrics = validate_contract(_payment())
    assert metrics.node_count == 2
    assert metrics.max_depth == 2


def test_validate_nested_within_limits() -> None:
    contract = Both((_payment("1"), Scale(_scalar("2"), _payment("2"))))
    metrics = validate_contract(contract)
    assert metrics.node_count == 7
    assert metrics.max_depth == 4


def test_validate_deep_chain_no_recursion_failure() -> None:
    metrics = validate_contract(build_chain(60))
    assert metrics.max_depth == 61
    assert metrics.node_count == 121


def test_validate_deterministic_metrics() -> None:
    contract = Both((_payment("1"), _payment("2")))
    assert validate_contract(contract) == validate_contract(contract)


# ---------------------------------------------------------------------------
# DAG sharing
# ---------------------------------------------------------------------------


def test_validate_shared_subexpression_counted_once() -> None:
    shared = _payment("1")
    contract = Both((shared, shared))
    metrics = validate_contract(contract)
    # Both + shared Payment + shared Payment.amount (Number). Value objects such
    # as Currency/SettlementTime are leaves, not graph nodes.
    assert metrics.node_count == 3
    assert metrics.max_depth == 3


def test_validate_dag_equal_depth_hits_skip_branch() -> None:
    shared = _payment("1")
    contract = Both((Scale(_scalar("2"), shared), Scale(_scalar("3"), shared)))
    metrics = validate_contract(contract)
    assert metrics.node_count == 7


def test_validate_dag_deeper_path_hits_proceed_branch() -> None:
    shared = _payment("1")
    contract = Both((shared, Scale(_scalar("2"), shared)))
    metrics = validate_contract(contract)
    assert metrics.node_count == 5
    assert metrics.max_depth == 4


# ---------------------------------------------------------------------------
# Complexity limits
# ---------------------------------------------------------------------------


def test_validate_max_depth_rejection() -> None:
    with pytest.raises(ContractComplexityError):
        validate_contract(
            build_chain(10),
            limits=ValidationLimits(max_depth=5, max_unique_nodes=1000),
        )


def test_validate_max_node_rejection() -> None:
    many = Both(tuple(_payment(str(i)) for i in range(3)))
    with pytest.raises(ContractComplexityError):
        validate_contract(
            many, limits=ValidationLimits(max_depth=100, max_unique_nodes=5)
        )


# ---------------------------------------------------------------------------
# Root / limits guards
# ---------------------------------------------------------------------------


def test_validate_rejects_non_contract_root() -> None:
    with pytest.raises(ContractValidationError):
        validate_contract(_scalar("1"))  # type: ignore[arg-type]


def test_validate_rejects_bad_limits() -> None:
    with pytest.raises(ContractTypeMismatchError):
        validate_contract(Zero(), limits="bad")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------


def test_validate_detects_self_cycle() -> None:
    both = Both((_payment("1"), _payment("2")))
    object.__setattr__(both, "operands", (both, _payment("3")))
    with pytest.raises(ContractCycleError):
        validate_contract(both)


def test_validate_detects_deep_cycle() -> None:
    outer = Both((_payment("1"), _payment("2")))
    inner = Both((outer, _payment("3")))
    object.__setattr__(outer, "operands", (inner, _payment("4")))
    with pytest.raises(ContractCycleError):
        validate_contract(outer)


# ---------------------------------------------------------------------------
# Malformed / forged objects
# ---------------------------------------------------------------------------


def test_validate_rejects_forged_value_field() -> None:
    n = _money("1")
    object.__setattr__(n, "value", 12345)
    payment = Payment(n, _usd(), _settlement())
    with pytest.raises(ContractValidationError):
        validate_contract(payment)


def test_validate_rejects_forged_operands_list() -> None:
    add = Add((_scalar("1"), _scalar("2")))
    object.__setattr__(add, "operands", [_scalar("1"), _scalar("2")])
    contract = Scale(add, _payment("1"))
    with pytest.raises(ContractTypeMismatchError):
        validate_contract(contract)


def test_validate_rejects_forged_unit_mismatch() -> None:
    add = Add((_scalar("1"), _scalar("2")))
    object.__setattr__(add, "unit", Unit.money(_usd()))
    contract = Payment(add, _usd(), _settlement())
    with pytest.raises(ContractValidationError):
        validate_contract(contract)


def test_validate_rejects_forged_observable_id() -> None:
    obs = _obs()
    object.__setattr__(obs, "observable_id", "equity:ACME:spot")
    contract = Scale(obs, _payment("1"))
    with pytest.raises(ContractValidationError):
        validate_contract(contract)


def test_validate_rejects_money_times_money() -> None:
    mul = Multiply(_scalar("1"), _scalar("2"))
    object.__setattr__(mul, "left", _money("1"))
    object.__setattr__(mul, "right", _money("2"))
    contract = Scale(mul, _payment("1"))
    with pytest.raises(ContractValidationError):
        validate_contract(contract)


def test_validate_rejects_forged_zero_denominator() -> None:
    div = Divide(_scalar("1"), _scalar("2"))
    object.__setattr__(div, "denominator", _scalar("0"))
    contract = Scale(div, _payment("1"))
    with pytest.raises(ContractValidationError):
        validate_contract(contract)


def test_validate_rejects_forged_non_scalar_denominator() -> None:
    div = Divide(_scalar("1"), _scalar("2"))
    object.__setattr__(div, "denominator", _money("2"))
    contract = Scale(div, _payment("1"))
    with pytest.raises(ContractValidationError):
        validate_contract(contract)


def test_validate_rejects_forged_boolean_constant() -> None:
    bc = BooleanConstant(True)
    object.__setattr__(bc, "value", 1)
    contract = ConditionalContract(
        AllOf((bc, BooleanConstant(False))),
        _payment("1"),
        _payment("2"),
    )
    with pytest.raises(ContractValidationError):
        validate_contract(contract)


def test_validate_rejects_forged_payment_currency() -> None:
    p = _payment("100")
    object.__setattr__(p, "currency", Currency.from_code("EUR"))
    with pytest.raises(ContractValidationError):
        validate_contract(p)


def test_validate_rejects_forged_scale_factor_unit() -> None:
    s = Scale(_scalar("2"), _payment("1"))
    object.__setattr__(s, "factor", _money("2"))
    with pytest.raises(ContractValidationError):
        validate_contract(s)


# ---------------------------------------------------------------------------
# Unsupported subclasses
# ---------------------------------------------------------------------------


def test_validate_rejects_unsupported_contract_subclass() -> None:
    class Evil(Contract):
        pass

    with pytest.raises(ContractValidationError):
        validate_contract(Evil())


def test_validate_rejects_unsupported_scalar_subclass() -> None:
    class EvilS(ScalarExpression):
        __slots__ = ("unit",)

        def __init__(self) -> None:
            object.__setattr__(self, "unit", Unit.scalar())

    evil = EvilS()
    contract = Scale(Add((evil, _scalar("2"))), _payment("1"))
    with pytest.raises(ContractValidationError):
        validate_contract(contract)


def test_validate_rejects_unsupported_boolean_subclass() -> None:
    class EvilB(BooleanExpression):
        pass

    evil = EvilB()
    contract = ConditionalContract(
        AllOf((evil, BooleanConstant(False))),
        _payment("1"),
        _payment("2"),
    )
    with pytest.raises(ContractValidationError):
        validate_contract(contract)


# ---------------------------------------------------------------------------
# Error taxonomy
# ---------------------------------------------------------------------------


def test_error_codes_stable() -> None:
    assert DerivaTraceError("x").code == "derivatrace.error"
    assert ContractError("x").code == "contract.error"
    assert ContractInputError("x").code == "contract.input"
    assert ContractTypeMismatchError("x").code == "contract.input.type_mismatch"
    assert ContractValidationError("x").code == "contract.validation"
    assert ContractCycleError("x").code == "contract.validation.cycle"
    assert ContractComplexityError("x").code == "contract.validation.complexity"


def test_error_path_formatting() -> None:
    from derivatrace.contracts._errors import format_path

    assert format_path(()) == "<root>"
    assert format_path(("operands", 0, "amount")) == "operands.0.amount"
    err = ContractValidationError("boom", path=("operands", 0, "amount"))
    assert "operands.0.amount" in str(err)


def test_error_carries_immutable_path() -> None:
    err = ContractValidationError("boom", path=("a", 1))
    assert err.path == ("a", 1)


def test_errors_are_contract_error_subtypes() -> None:
    assert issubclass(ContractCycleError, ContractValidationError)
    assert issubclass(ContractComplexityError, ContractValidationError)
    assert issubclass(ContractValidationError, ContractError)
    assert issubclass(ContractInputError, ContractError)
    assert issubclass(ContractTypeMismatchError, ContractInputError)
