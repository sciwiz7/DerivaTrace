from __future__ import annotations

from datetime import UTC, datetime

import pytest

from derivatrace.canonical import (
    CanonicalizationInputError,
    structurally_equivalent,
)
from derivatrace.contracts import (
    Add,
    Both,
    Contract,
    Currency,
    ExactNumber,
    Number,
    Observable,
    ObservableId,
    ObservationTime,
    Payment,
    SettlementTime,
    Unit,
)

usd = Currency.from_code("USD")
T0 = SettlementTime.from_datetime(datetime(2030, 6, 1, tzinfo=UTC))
OT0 = ObservationTime.from_datetime(datetime(2030, 6, 1, tzinfo=UTC))


def _obs(nsp: str, ident: str, field: str = "close") -> Observable:
    return Observable(ObservableId.from_parts(nsp, ident, field), OT0, Unit.money(usd))


def _num(s: str) -> Number:
    return Number(ExactNumber.from_string(s), Unit.scalar())


def _payment() -> Contract:
    return Payment(Add((_obs("equity", "AAA"), _obs("equity", "BBB"))), usd, T0)


def test_equivalent_commutative_representations() -> None:
    a = Payment(Add((_obs("equity", "AAA"), _obs("equity", "BBB"))), usd, T0)
    b = Payment(Add((_obs("equity", "BBB"), _obs("equity", "AAA"))), usd, T0)
    assert structurally_equivalent(a, b) is True


def test_non_equivalent_contracts() -> None:
    a = Payment(Add((_obs("equity", "AAA"), _obs("equity", "BBB"))), usd, T0)
    b = Payment(_obs("equity", "AAA"), usd, T0)
    assert structurally_equivalent(a, b) is False


def test_equivalence_rejects_non_contract_input() -> None:
    # A bare expression node is not a Contract root.
    with pytest.raises(CanonicalizationInputError):
        structurally_equivalent(_num("1"), _num("1"))  # type: ignore[arg-type]


def test_equivalence_accepts_raw_contracts() -> None:
    a = Payment(_obs("equity", "AAA"), usd, T0)
    b = Payment(_obs("equity", "AAA"), usd, T0)
    assert structurally_equivalent(a, b) is True


def test_equivalence_matches_canonical_identity() -> None:
    from derivatrace.canonical import canonicalize_contract

    a = _payment()
    b = Payment(Add((_obs("equity", "BBB"), _obs("equity", "AAA"))), usd, T0)
    assert structurally_equivalent(a, b) == (
        canonicalize_contract(a).identity == canonicalize_contract(b).identity
    )


def test_both_wrapper_preserves_operand_order() -> None:
    # Per the canonical spec (CV-006) Both operand order is significant, so a
    # reordered Both is a distinct canonical contract.
    a = Both(
        (
            Payment(_obs("equity", "AAA"), usd, T0),
            Payment(_obs("equity", "BBB"), usd, T0),
        )
    )
    b = Both(
        (
            Payment(_obs("equity", "BBB"), usd, T0),
            Payment(_obs("equity", "AAA"), usd, T0),
        )
    )
    assert structurally_equivalent(a, b) is False
