from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from derivatrace.contracts import (
    ContractInputError,
    ContractTypeMismatchError,
    Currency,
    ExactNumber,
    ObservableId,
    ObservationTime,
    SettlementTime,
    Unit,
    UnitKind,
    ValidationLimits,
)


def test_exact_number_from_int() -> None:
    n = ExactNumber.from_int(42)
    assert n.value == Decimal(42)


def test_exact_number_from_int_rejects_bool() -> None:
    with pytest.raises(ContractTypeMismatchError):
        ExactNumber.from_int(True)


def test_exact_number_from_int_rejects_non_int() -> None:
    with pytest.raises(ContractTypeMismatchError):
        ExactNumber.from_int("42")  # type: ignore[arg-type]


def test_exact_number_from_string() -> None:
    n = ExactNumber.from_string("123.456")
    assert n.value == Decimal("123.456")


def test_exact_number_from_string_rejects_non_str() -> None:
    with pytest.raises(ContractTypeMismatchError):
        ExactNumber.from_string(123)  # type: ignore[arg-type]


def test_exact_number_from_string_rejects_whitespace() -> None:
    with pytest.raises(ContractInputError):
        ExactNumber.from_string(" 1 ")


def test_exact_number_from_string_rejects_invalid() -> None:
    with pytest.raises(ContractInputError):
        ExactNumber.from_string("not-a-number")


def test_exact_number_rejects_nan() -> None:
    with pytest.raises(ContractInputError):
        ExactNumber.from_string("NaN")


def test_exact_number_rejects_infinity() -> None:
    with pytest.raises(ContractInputError):
        ExactNumber.from_string("Infinity")


def test_exact_number_rejects_negative_infinity() -> None:
    with pytest.raises(ContractInputError):
        ExactNumber.from_string("-Infinity")


def test_exact_number_rejects_excessive_digits() -> None:
    with pytest.raises(ContractInputError):
        ExactNumber.from_string("1" * 60)


def test_exact_number_rejects_excessive_exponent() -> None:
    with pytest.raises(ContractInputError):
        ExactNumber.from_string("1e200")


def test_exact_number_normalizes_negative_zero() -> None:
    n = ExactNumber.from_string("-0")
    assert n.value == Decimal(0)
    assert not n.value.is_signed()


def test_exact_number_equality_and_hash() -> None:
    a = ExactNumber.from_string("1.5")
    b = ExactNumber.from_string("1.5")
    c = ExactNumber.from_string("2")
    assert a == b
    assert a != c
    assert hash(a) == hash(b)
    assert a != "1.5"


def test_exact_number_immutable() -> None:
    n = ExactNumber.from_int(1)
    with pytest.raises(AttributeError):
        n.value = Decimal(2)  # type: ignore[misc]


def test_exact_number_repr() -> None:
    n = ExactNumber.from_int(7)
    assert "7" in repr(n)


def test_currency_valid() -> None:
    c = Currency.from_code("USD")
    assert c.code == "USD"


def test_currency_rejects_lowercase() -> None:
    with pytest.raises(ContractInputError):
        Currency.from_code("usd")


def test_currency_rejects_non_str() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Currency.from_code(123)  # type: ignore[arg-type]


def test_currency_rejects_punctuation() -> None:
    with pytest.raises(ContractInputError):
        Currency.from_code("US!")


def test_currency_rejects_unicode_lookalike() -> None:
    with pytest.raises(ContractInputError):
        Currency.from_code("UＳD")  # noqa: RUF001


def test_currency_rejects_wrong_length() -> None:
    with pytest.raises(ContractInputError):
        Currency.from_code("US")
    with pytest.raises(ContractInputError):
        Currency.from_code("USDX")


def test_currency_equality_and_hash() -> None:
    assert Currency.from_code("USD") == Currency.from_code("USD")
    assert Currency.from_code("USD") != Currency.from_code("EUR")
    assert hash(Currency.from_code("USD")) == hash(Currency.from_code("USD"))
    assert Currency.from_code("USD") != "USD"


def test_currency_immutable() -> None:
    c = Currency.from_code("USD")
    with pytest.raises(AttributeError):
        c.code = "EUR"  # type: ignore[misc]


def test_unit_scalar() -> None:
    u = Unit.scalar()
    assert u.kind == UnitKind.SCALAR
    assert u.currency is None


def test_unit_money() -> None:
    u = Unit.money(Currency.from_code("USD"))
    assert u.kind == UnitKind.MONEY
    assert u.currency == Currency.from_code("USD")


def test_unit_money_rejects_non_currency() -> None:
    with pytest.raises(ContractTypeMismatchError):
        Unit.money("USD")  # type: ignore[arg-type]


def test_unit_scalar_with_currency_rejected() -> None:
    with pytest.raises(ContractInputError):
        Unit(UnitKind.SCALAR, Currency.from_code("USD"))


def test_unit_money_without_currency_rejected() -> None:
    with pytest.raises(ContractInputError):
        Unit(UnitKind.MONEY, None)


def test_unit_equality_and_hash() -> None:
    usd = Currency.from_code("USD")
    assert Unit.scalar() == Unit.scalar()
    assert Unit.money(usd) == Unit.money(usd)
    assert Unit.money(usd) != Unit.scalar()
    assert hash(Unit.money(usd)) == hash(Unit.money(usd))


def test_unit_immutable() -> None:
    u = Unit.scalar()
    with pytest.raises(AttributeError):
        u.kind = UnitKind.MONEY  # type: ignore[misc]


def test_observable_id_valid() -> None:
    oid = ObservableId.from_parts("equity", "ACME", "spot")
    assert oid.namespace == "equity"
    assert oid.identifier == "ACME"
    assert oid.field == "spot"


def test_observable_id_rejects_empty_namespace() -> None:
    with pytest.raises(ContractInputError):
        ObservableId.from_parts("", "ACME", "spot")


def test_observable_id_rejects_long_namespace() -> None:
    with pytest.raises(ContractInputError):
        ObservableId.from_parts("a" * 65, "ACME", "spot")


def test_observable_id_rejects_bad_namespace_chars() -> None:
    with pytest.raises(ContractInputError):
        ObservableId.from_parts("Equity", "ACME", "spot")
    with pytest.raises(ContractInputError):
        ObservableId.from_parts("equity!", "ACME", "spot")


def test_observable_id_rejects_empty_field() -> None:
    with pytest.raises(ContractInputError):
        ObservableId.from_parts("equity", "ACME", "")


def test_observable_id_rejects_long_field() -> None:
    with pytest.raises(ContractInputError):
        ObservableId.from_parts("equity", "ACME", "x" * 65)


def test_observable_id_rejects_bad_field_chars() -> None:
    with pytest.raises(ContractInputError):
        ObservableId.from_parts("equity", "ACME", "spot!")


def test_observable_id_rejects_empty_identifier() -> None:
    with pytest.raises(ContractInputError):
        ObservableId.from_parts("equity", "", "spot")


def test_observable_id_rejects_long_identifier() -> None:
    with pytest.raises(ContractInputError):
        ObservableId.from_parts("equity", "x" * 129, "spot")


def test_observable_id_rejects_bad_identifier_chars() -> None:
    with pytest.raises(ContractInputError):
        ObservableId.from_parts("equity", "AC ME", "spot")
    with pytest.raises(ContractInputError):
        ObservableId.from_parts("equity", "AC\u00d0E", "spot")


def test_observable_id_rejects_non_str() -> None:
    with pytest.raises(ContractTypeMismatchError):
        ObservableId.from_parts(123, "ACME", "spot")  # type: ignore[arg-type]


def test_observable_id_equality_and_hash() -> None:
    a = ObservableId.from_parts("equity", "ACME", "spot")
    b = ObservableId.from_parts("equity", "ACME", "spot")
    c = ObservableId.from_parts("equity", "ACME", "close")
    assert a == b
    assert a != c
    assert hash(a) == hash(b)


def test_observation_time_accepts_aware() -> None:
    dt = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)
    t = ObservationTime(dt)
    assert t.value == dt


def test_observation_time_converts_to_utc() -> None:
    dt = datetime(2030, 1, 1, 14, 0, tzinfo=timezone(offset=timedelta(hours=2)))
    t = ObservationTime(dt)
    assert t.value.tzinfo == UTC
    assert t.value.hour == 12


def test_observation_time_rejects_naive() -> None:
    with pytest.raises(ContractInputError):
        ObservationTime(datetime(2030, 1, 1))


def test_observation_time_rejects_non_datetime() -> None:
    with pytest.raises(ContractTypeMismatchError):
        ObservationTime("2030-01-01")  # type: ignore[arg-type]


def test_observation_time_immutable() -> None:
    t = ObservationTime(datetime(2030, 1, 1, tzinfo=UTC))
    with pytest.raises(AttributeError):
        t.value = datetime(2031, 1, 1, tzinfo=UTC)  # type: ignore[misc]


def test_settlement_time_distinct_type() -> None:
    dt = datetime(2030, 1, 1, tzinfo=UTC)
    s = SettlementTime(dt)
    o = ObservationTime(dt)
    assert type(s) is not type(o)  # type: ignore[comparison-overlap]
    assert s.value == o.value


def test_settlement_time_rejects_naive() -> None:
    with pytest.raises(ContractInputError):
        SettlementTime(datetime(2030, 1, 1))


def test_settlement_time_immutable() -> None:
    s = SettlementTime(datetime(2030, 1, 1, tzinfo=UTC))
    with pytest.raises(AttributeError):
        s.value = datetime(2031, 1, 1, tzinfo=UTC)  # type: ignore[misc]


def test_validation_limits_default() -> None:
    limits = ValidationLimits.default()
    assert limits.max_depth == 64
    assert limits.max_unique_nodes == 4096


def test_validation_limits_rejects_bad_depth() -> None:
    with pytest.raises(ContractInputError):
        ValidationLimits(max_depth=0, max_unique_nodes=10)


def test_validation_limits_rejects_bad_nodes() -> None:
    with pytest.raises(ContractInputError):
        ValidationLimits(max_depth=10, max_unique_nodes=-1)


def test_contract_metrics_constructible() -> None:
    from derivatrace.contracts import ContractMetrics

    m = ContractMetrics(node_count=3, max_depth=2)
    assert m.node_count == 3
    assert m.max_depth == 2
