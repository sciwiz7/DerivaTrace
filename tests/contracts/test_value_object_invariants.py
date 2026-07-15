"""Regression tests for hardened Stage 1A value-object invariants.

These tests cover every case called out in the blocking-fix review:

* UnitKind runtime strictness (plain strings rejected, valid constructors kept).
* True timezone awareness (utcoffset() must be a concrete offset, not None).
* Revalidation of every value object's stored internals during graph
  validation, so objects forged via ``object.__setattr__`` cannot bypass the
  invariants. Includes the exact-type policy for deterministic value objects.
* ValidationLimits bool rejection plus revalidation at validate_contract entry.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone, tzinfo
from decimal import Decimal

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
    ContractInputError,
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
    UnitKind,
    ValidationLimits,
    validate_contract,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Blocker 1 - UnitKind runtime strictness
# ---------------------------------------------------------------------------


def test_unit_rejects_plain_scalar_string() -> None:
    # A plain string compares equal to UnitKind.SCALAR via StrEnum equality, so
    # it must be rejected explicitly rather than accepted.
    with pytest.raises(ContractInputError):
        Unit(kind="scalar", currency=None)  # type: ignore[arg-type]


def test_unit_rejects_plain_money_string() -> None:
    with pytest.raises(ContractInputError):
        Unit(kind="money", currency=_usd())  # type: ignore[arg-type]


def test_unit_rejects_unknown_string() -> None:
    with pytest.raises(ContractInputError):
        Unit(kind="bogus", currency=None)  # type: ignore[arg-type]


def test_unit_scalar_and_money_constructors_still_work() -> None:
    s = Unit.scalar()
    assert s.kind is UnitKind.SCALAR
    assert s.currency is None
    m = Unit.money(_usd())
    assert m.kind is UnitKind.MONEY
    assert m.currency == _usd()


def test_unit_scalar_cannot_carry_currency() -> None:
    with pytest.raises(ContractInputError):
        Unit(kind=UnitKind.SCALAR, currency=_usd())


def test_unit_money_requires_currency() -> None:
    with pytest.raises(ContractInputError):
        Unit(kind=UnitKind.MONEY, currency=None)


# ---------------------------------------------------------------------------
# Blocker 2 - true timezone awareness
# ---------------------------------------------------------------------------


class _NullOffsetTZ(tzinfo):
    """A custom tzinfo whose utcoffset() returns None (not a real instant)."""

    def utcoffset(self, dt: object) -> None:
        return None

    def tzname(self, dt: object) -> str:
        return "NULL"

    def dst(self, dt: object) -> None:
        return None


class _RaisingTZ(tzinfo):
    """A custom tzinfo whose utcoffset() raises instead of returning."""

    def utcoffset(self, dt: object) -> None:
        raise ValueError("offset computation exploded")

    def tzname(self, dt: object) -> str:
        return "RAISE"

    def dst(self, dt: object) -> None:
        return None


def test_observation_time_rejects_null_utcoffset() -> None:
    with pytest.raises(ContractInputError):
        ObservationTime(datetime(2030, 1, 1, tzinfo=_NullOffsetTZ()))


def test_observation_time_rejects_raising_utcoffset() -> None:
    with pytest.raises(ContractInputError):
        ObservationTime(datetime(2030, 1, 1, tzinfo=_RaisingTZ()))


def test_settlement_time_rejects_null_utcoffset() -> None:
    with pytest.raises(ContractInputError):
        SettlementTime(datetime(2030, 6, 1, tzinfo=_NullOffsetTZ()))


def test_settlement_time_rejects_raising_utcoffset() -> None:
    with pytest.raises(ContractInputError):
        SettlementTime(datetime(2030, 6, 1, tzinfo=_RaisingTZ()))


def test_observation_time_accepts_positive_and_negative_offsets() -> None:
    pos = ObservationTime(
        datetime(2030, 1, 1, 14, 0, tzinfo=timezone(timedelta(hours=2)))
    )
    neg = ObservationTime(
        datetime(2030, 1, 1, 5, 0, tzinfo=timezone(timedelta(hours=-2)))
    )
    assert pos.value.utcoffset() == timedelta(0)
    assert pos.value.hour == 12
    assert neg.value.hour == 7


def test_observation_time_normalises_to_utc_and_preserves_micros() -> None:
    aware = ObservationTime(datetime(2020, 1, 1, 12, 30, 15, 123456, tzinfo=UTC))
    assert aware.value.microsecond == 123456


def test_observation_time_equal_instants_across_offsets() -> None:
    a = ObservationTime(
        datetime(2020, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=5)))
    )
    b = ObservationTime(datetime(2020, 1, 1, 7, 0, tzinfo=UTC))
    assert a == b


def test_settlement_time_equal_instants_across_offsets() -> None:
    a = SettlementTime(datetime(2020, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=5))))
    b = SettlementTime(datetime(2020, 1, 1, 7, 0, tzinfo=UTC))
    assert a == b


# ---------------------------------------------------------------------------
# Blocker 3 - forged value-object regression (revalidated during validation)
# ---------------------------------------------------------------------------


def test_forge_exact_number_nan_rejected() -> None:
    n = _money("1")
    object.__setattr__(n.value, "_value", Decimal("NaN"))
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(n, _usd(), _settlement()))


def test_forge_exact_number_infinity_rejected() -> None:
    n = _money("1")
    object.__setattr__(n.value, "_value", Decimal("Infinity"))
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(n, _usd(), _settlement()))


def test_forge_exact_number_non_decimal_rejected() -> None:
    n = _money("1")
    object.__setattr__(n.value, "_value", "not-a-decimal")
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(n, _usd(), _settlement()))


def test_forge_exact_number_too_many_digits_rejected() -> None:
    n = _money("1")
    object.__setattr__(n.value, "_value", Decimal("1" * 60))
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(n, _usd(), _settlement()))


def test_forge_exact_number_too_large_exponent_rejected() -> None:
    n = _money("1")
    object.__setattr__(n.value, "_value", Decimal("1e200"))
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(n, _usd(), _settlement()))


class _BadExactNumber(ExactNumber):
    pass


def test_exact_number_subclass_rejected_by_exact_type_policy() -> None:
    bad = _BadExactNumber(Decimal(5))
    num = Number(bad, Unit.money(_usd()))
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(num, _usd(), _settlement()))


def test_forge_currency_lowercase_code_rejected() -> None:
    cur = _usd()
    object.__setattr__(cur, "_code", "usd")
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(_money("1", cur), cur, _settlement()))


def test_forge_currency_non_str_code_rejected() -> None:
    cur = _usd()
    object.__setattr__(cur, "_code", 12345)
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(_money("1", cur), cur, _settlement()))


class _BadCurrency(Currency):
    pass


def test_currency_subclass_rejected_by_exact_type_policy() -> None:
    bad = _BadCurrency("USD")
    num = Number(ExactNumber.from_string("1"), Unit.money(bad))
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(num, bad, _settlement()))


def test_forge_unit_plain_string_kind_rejected() -> None:
    u = Unit.scalar()
    object.__setattr__(u, "kind", "scalar")
    num = Number(ExactNumber.from_string("1"), u)
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(num, _payment()))


def test_forge_scalar_unit_with_currency_rejected() -> None:
    u = Unit.scalar()
    object.__setattr__(u, "currency", _usd())
    num = Number(ExactNumber.from_string("1"), u)
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(num, _payment()))


def test_forge_money_unit_without_currency_rejected() -> None:
    p = _payment("100")
    # Forge the money unit's stored currency to None after construction, so the
    # Payment's own currency-mismatch guard cannot fire first.
    object.__setattr__(p.amount.unit, "currency", None)
    with pytest.raises(ContractValidationError):
        validate_contract(p)


class _BadUnit(Unit):
    pass


def test_unit_subclass_rejected_by_exact_type_policy() -> None:
    bad = _BadUnit(kind=UnitKind.SCALAR, currency=None)
    num = Number(ExactNumber.from_string("1"), bad)
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(num, _payment()))


def test_forge_observable_id_bad_namespace_rejected() -> None:
    obs = _obs()
    object.__setattr__(obs.observable_id, "namespace", "Equity")
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


def test_forge_observable_id_empty_namespace_rejected() -> None:
    obs = _obs()
    object.__setattr__(obs.observable_id, "namespace", "")
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


def test_forge_observable_id_long_namespace_rejected() -> None:
    obs = _obs()
    object.__setattr__(obs.observable_id, "namespace", "a" * 65)
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


def test_forge_observable_id_bad_field_rejected() -> None:
    obs = _obs()
    object.__setattr__(obs.observable_id, "field", "spot!")
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


def test_forge_observable_id_empty_field_rejected() -> None:
    obs = _obs()
    object.__setattr__(obs.observable_id, "field", "")
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


def test_forge_observable_id_long_field_rejected() -> None:
    obs = _obs()
    object.__setattr__(obs.observable_id, "field", "x" * 65)
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


def test_forge_observable_id_empty_identifier_rejected() -> None:
    obs = _obs()
    object.__setattr__(obs.observable_id, "identifier", "")
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


def test_forge_observable_id_long_identifier_rejected() -> None:
    obs = _obs()
    object.__setattr__(obs.observable_id, "identifier", "x" * 129)
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


def test_forge_observable_id_bad_identifier_chars_rejected() -> None:
    obs = _obs()
    object.__setattr__(obs.observable_id, "identifier", "AC ME")
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


class _BadObservableId(ObservableId):
    pass


def test_observable_id_subclass_rejected_by_exact_type_policy() -> None:
    bad = _BadObservableId("equity", "ACME", "spot")
    obs = Observable(
        bad, ObservationTime(datetime(2030, 1, 1, tzinfo=UTC)), Unit.scalar()
    )
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


def test_forge_observation_time_naive_rejected() -> None:
    ot = ObservationTime(datetime(2030, 1, 1, tzinfo=UTC))
    object.__setattr__(ot, "_value", datetime(2030, 1, 1))
    obs = Observable(
        ObservableId.from_parts("equity", "ACME", "spot"), ot, Unit.scalar()
    )
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


def test_forge_observation_time_non_datetime_rejected() -> None:
    ot = ObservationTime(datetime(2030, 1, 1, tzinfo=UTC))
    object.__setattr__(ot, "_value", "2030-01-01")
    obs = Observable(
        ObservableId.from_parts("equity", "ACME", "spot"), ot, Unit.scalar()
    )
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


def test_forge_observation_time_null_offset_rejected() -> None:
    ot = ObservationTime(datetime(2030, 1, 1, tzinfo=UTC))
    object.__setattr__(ot, "_value", datetime(2030, 1, 1, tzinfo=_NullOffsetTZ()))
    obs = Observable(
        ObservableId.from_parts("equity", "ACME", "spot"), ot, Unit.scalar()
    )
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


def test_forge_observation_time_raising_offset_rejected() -> None:
    ot = ObservationTime(datetime(2030, 1, 1, tzinfo=UTC))
    object.__setattr__(ot, "_value", datetime(2030, 1, 1, tzinfo=_RaisingTZ()))
    obs = Observable(
        ObservableId.from_parts("equity", "ACME", "spot"), ot, Unit.scalar()
    )
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


class _BadObservationTime(ObservationTime):
    pass


def test_observation_time_subclass_rejected_by_exact_type_policy() -> None:
    bad = _BadObservationTime(datetime(2030, 1, 1, tzinfo=UTC))
    obs = Observable(
        ObservableId.from_parts("equity", "ACME", "spot"), bad, Unit.scalar()
    )
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


def test_forge_settlement_time_naive_rejected() -> None:
    st = _settlement()
    object.__setattr__(st, "_value", datetime(2030, 6, 1))
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(_money("1"), _usd(), st))


class _BadSettlementTime(SettlementTime):
    pass


def test_settlement_time_subclass_rejected_by_exact_type_policy() -> None:
    bad = _BadSettlementTime(datetime(2030, 6, 1, tzinfo=UTC))
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(_money("1"), _usd(), bad))


# ---------------------------------------------------------------------------
# Blocker 4 - ValidationLimits bool rejection and forgery revalidation
# ---------------------------------------------------------------------------


def test_validation_limits_rejects_bool_depth() -> None:
    with pytest.raises(ContractInputError):
        ValidationLimits(max_depth=True, max_unique_nodes=10)


def test_validation_limits_rejects_bool_nodes() -> None:
    with pytest.raises(ContractInputError):
        ValidationLimits(max_depth=10, max_unique_nodes=False)


def test_forge_validation_limits_bool_depth_rejected() -> None:
    limits = ValidationLimits.default()
    object.__setattr__(limits, "max_depth", True)
    with pytest.raises(ContractValidationError):
        validate_contract(_payment(), limits=limits)


def test_forge_validation_limits_bool_nodes_rejected() -> None:
    limits = ValidationLimits.default()
    object.__setattr__(limits, "max_unique_nodes", False)
    with pytest.raises(ContractValidationError):
        validate_contract(_payment(), limits=limits)


def test_forge_validation_limits_non_int_depth_rejected() -> None:
    limits = ValidationLimits.default()
    object.__setattr__(limits, "max_depth", "deep")
    with pytest.raises(ContractValidationError):
        validate_contract(_payment(), limits=limits)


def test_forge_validation_limits_zero_depth_rejected() -> None:
    limits = ValidationLimits.default()
    object.__setattr__(limits, "max_depth", 0)
    with pytest.raises(ContractValidationError):
        validate_contract(_payment(), limits=limits)


class _BadValidationLimits(ValidationLimits):
    pass


def test_validation_limits_subclass_rejected_by_exact_type_policy() -> None:
    bad = _BadValidationLimits()
    with pytest.raises(ContractValidationError):
        validate_contract(_payment(), limits=bad)


# ---------------------------------------------------------------------------
# Blocker 1 - validate children before parent invariants (post-order)
# ---------------------------------------------------------------------------
#
# The traversal validates a node only after every descendant has passed
# authoritative validation. A hostile/unsupported child subclass is therefore
# rejected by the exact-type policy before any parent reads its (possibly
# overridden) ``.unit``/``.value`` fields, so overridden behaviour can never be
# executed.


_hostile_accessed: list[str] = []


class _HostileScalar(ScalarExpression):
    @property
    def unit(self) -> Unit:  # type: ignore[override]
        _hostile_accessed.append("scalar")
        raise RuntimeError("hostile scalar unit executed")


class _HostileBoolean(BooleanExpression):
    @property
    def dummy(self) -> object:
        _hostile_accessed.append("boolean")
        raise RuntimeError("hostile boolean executed")


class _HostileContract(Contract):
    @property
    def dummy(self) -> object:
        _hostile_accessed.append("contract")
        raise RuntimeError("hostile contract executed")


def test_hostile_scalar_subclass_rejected_before_property() -> None:
    _hostile_accessed.clear()
    evil = _HostileScalar()
    add = Add((_scalar("1"), _scalar("2")))
    object.__setattr__(add, "operands", (add.operands[0], evil))
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(add, _payment()))
    assert _hostile_accessed == []


def test_hostile_boolean_subclass_rejected_before_behaviour() -> None:
    _hostile_accessed.clear()
    evil = _HostileBoolean()
    cond = AllOf((BooleanConstant(True), BooleanConstant(False)))
    object.__setattr__(cond, "operands", (cond.operands[0], evil))
    with pytest.raises(ContractValidationError):
        validate_contract(ConditionalContract(cond, _payment(), _payment()))
    assert _hostile_accessed == []


def test_hostile_contract_subclass_rejected_before_behaviour() -> None:
    _hostile_accessed.clear()
    evil = _HostileContract()
    both = Both((_payment(), _payment()))
    object.__setattr__(both, "operands", (both.operands[0], evil))
    with pytest.raises(ContractValidationError):
        validate_contract(both)
    assert _hostile_accessed == []


@pytest.mark.parametrize(
    "builder",
    ["multiply", "divide", "add", "comparison", "scale", "payment"],
)
def test_forge_number_unit_non_unit_rejected(builder: str) -> None:
    bad_unit = 12345  # not a Unit instance
    num = _scalar("2")
    if builder == "multiply":
        contract: Contract = Scale(Multiply(_scalar("1"), num), _payment())
    elif builder == "divide":
        contract = Scale(Divide(_scalar("4"), num), _payment())
    elif builder == "add":
        contract = Scale(Add((_scalar("1"), num)), _payment())
    elif builder == "comparison":
        contract = ConditionalContract(
            Comparison(num, _scalar("3"), ComparisonOperator.LESS_THAN),
            _payment(),
            _payment(),
        )
    elif builder == "scale":
        contract = Scale(num, _payment())
    else:  # payment
        money_num = _money("2")
        num = money_num
        contract = Payment(money_num, _usd(), _settlement())
    object.__setattr__(num, "unit", bad_unit)
    # Must fail with a DerivaTrace contract error, never AttributeError or
    # RuntimeError from the parent touching the forged ``.unit``.
    with pytest.raises(DerivaTraceError):
        validate_contract(contract)


def test_forge_divide_denominator_value_non_exact_rejected() -> None:
    denom = _scalar("2")
    div = Divide(_scalar("4"), denom)
    object.__setattr__(denom, "value", 12345)  # non-ExactNumber
    with pytest.raises(DerivaTraceError):
        validate_contract(Scale(div, _payment()))


# ---------------------------------------------------------------------------
# Blocker 2 - nested currency revalidation
# ---------------------------------------------------------------------------


def test_forge_nested_currency_in_comparison_rejected() -> None:
    forged = Currency.from_code("USD")
    object.__setattr__(forged, "_code", "usd")
    money_expr = Number(ExactNumber.from_string("1"), Unit.money(forged))
    cond = Comparison(money_expr, money_expr, ComparisonOperator.LESS_THAN)
    eur = Currency.from_code("EUR")
    gbp = Currency.from_code("GBP")
    p1 = Payment(_money("100", eur), eur, _settlement())
    p2 = Payment(_money("200", gbp), gbp, _settlement())
    contract = ConditionalContract(cond, p1, p2)
    with pytest.raises(ContractValidationError):
        validate_contract(contract)


# ---------------------------------------------------------------------------
# Blocker 3 - stored UTC invariant
# ---------------------------------------------------------------------------


def test_forge_observation_time_non_utc_stored_rejected() -> None:
    ot = ObservationTime(datetime(2030, 1, 1, tzinfo=UTC))
    object.__setattr__(
        ot, "_value", datetime(2030, 1, 1, 14, 0, tzinfo=timezone(timedelta(hours=2)))
    )
    obs = Observable(
        ObservableId.from_parts("equity", "ACME", "spot"), ot, Unit.scalar()
    )
    with pytest.raises(ContractValidationError):
        validate_contract(Scale(obs, _payment()))


def test_forge_settlement_time_non_utc_stored_rejected() -> None:
    st = _settlement()
    object.__setattr__(
        st, "_value", datetime(2030, 6, 1, 14, 0, tzinfo=timezone(timedelta(hours=2)))
    )
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(_money("1"), _usd(), st))


# ---------------------------------------------------------------------------
# Blocker 4 - canonical stored zero
# ---------------------------------------------------------------------------


def test_validate_accepts_canonical_zero() -> None:
    p = Payment(
        Number(ExactNumber.from_string("0"), Unit.money(_usd())),
        _usd(),
        _settlement(),
    )
    metrics = validate_contract(p)
    assert metrics.node_count >= 2


def test_forge_exact_number_neg_zero_rejected() -> None:
    n = _money("1")
    object.__setattr__(n.value, "_value", Decimal("-0"))
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(n, _usd(), _settlement()))


def test_forge_exact_number_noncanonical_zero_rejected() -> None:
    n = _money("1")
    object.__setattr__(n.value, "_value", Decimal("0.0"))
    with pytest.raises(ContractValidationError):
        validate_contract(Payment(n, _usd(), _settlement()))
