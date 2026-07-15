from __future__ import annotations

from datetime import UTC, datetime

import pytest

from derivatrace.contracts._errors import (
    ContractInputError,
    ContractTypeMismatchError,
)
from derivatrace.contracts._values import (
    Currency,
    ExactNumber,
    ObservableId,
    ObservationTime,
    SettlementTime,
    Unit,
)


def _dt() -> datetime:
    return datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC)


def test_exact_number_direct_construction_rejects_non_decimal() -> None:
    with pytest.raises(ContractTypeMismatchError):
        ExactNumber(123)  # type: ignore[arg-type]


def test_currency_repr() -> None:
    assert repr(Currency.from_code("USD")) == "Currency('USD')"


def test_unit_rejects_unknown_kind() -> None:
    with pytest.raises(ContractInputError):
        Unit(kind="bogus", currency=None)  # type: ignore[arg-type]


def test_observable_id_direct_construction_rejects_bad_identifier() -> None:
    with pytest.raises(ContractTypeMismatchError):
        ObservableId("ns", 123, "f")  # type: ignore[arg-type]


def test_observable_id_direct_construction_rejects_bad_field() -> None:
    with pytest.raises(ContractTypeMismatchError):
        ObservableId("ns", "id", 123)  # type: ignore[arg-type]


def test_observable_id_is_immutable() -> None:
    oid = ObservableId.from_parts("ns", "id", "f")
    with pytest.raises(AttributeError):
        oid.namespace = "x"


def test_observable_id_eq_not_implemented_for_other() -> None:
    oid = ObservableId.from_parts("ns", "id", "f")
    assert (oid == 5) is False
    assert (oid == oid) is True


def test_observable_id_repr() -> None:
    oid = ObservableId.from_parts("ns", "id", "f")
    assert "ObservableId" in repr(oid)


def test_observation_time_from_datetime() -> None:
    assert ObservationTime.from_datetime(_dt()).value == _dt().astimezone(UTC)


def test_observation_time_eq_and_not_implemented() -> None:
    a = ObservationTime(_dt())
    b = ObservationTime(_dt())
    assert (a == b) is True
    assert (a == 5) is False


def test_observation_time_hash_and_repr() -> None:
    a = ObservationTime(_dt())
    assert isinstance(hash(a), int)
    assert "ObservationTime" in repr(a)


def test_settlement_time_direct_construction_rejects_non_datetime() -> None:
    with pytest.raises(ContractTypeMismatchError):
        SettlementTime("x")  # type: ignore[arg-type]


def test_settlement_time_from_datetime() -> None:
    assert SettlementTime.from_datetime(_dt()).value == _dt().astimezone(UTC)


def test_settlement_time_eq_not_implemented() -> None:
    a = SettlementTime(_dt())
    assert (a == 5) is False
    assert (a == a) is True


def test_settlement_time_repr() -> None:
    a = SettlementTime(_dt())
    assert "SettlementTime" in repr(a)
