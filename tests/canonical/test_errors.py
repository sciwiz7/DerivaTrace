from __future__ import annotations

from datetime import UTC, datetime

import pytest

from derivatrace.canonical import (
    CanonicalContract,
    CanonicalizationCollisionError,
    CanonicalizationComplexityError,
    CanonicalizationCycleError,
    CanonicalizationEncodingError,
    CanonicalizationError,
    CanonicalizationInputError,
    CanonicalizationLimits,
    CanonicalizationNotValidatedError,
    canonicalize_contract,
)
from derivatrace.contracts import (
    Add,
    Currency,
    DerivaTraceError,
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


def _money(value: str) -> Number:
    return Number(ExactNumber.from_string(value), Unit.money(usd))


def _payment() -> Payment:
    return Payment(_money("1"), usd, T0)


def _scalar(value: str) -> Number:
    return Number(ExactNumber.from_string(value), Unit.scalar())


def test_error_hierarchy() -> None:
    assert issubclass(CanonicalizationError, DerivaTraceError)
    for cls in (
        CanonicalizationInputError,
        CanonicalizationNotValidatedError,
        CanonicalizationCycleError,
        CanonicalizationComplexityError,
        CanonicalizationEncodingError,
        CanonicalizationCollisionError,
    ):
        assert issubclass(cls, CanonicalizationError)


def test_not_validated_is_input_subtype() -> None:
    assert issubclass(CanonicalizationNotValidatedError, CanonicalizationInputError)


def test_non_contract_root_raises_input_error() -> None:
    # A bare scalar expression / non-Contract value is not a valid root.
    with pytest.raises(CanonicalizationInputError):
        canonicalize_contract(_scalar("1"))  # type: ignore[arg-type]
    with pytest.raises(CanonicalizationInputError):
        canonicalize_contract(42)  # type: ignore[arg-type]


def test_complexity_error_on_excess_nodes() -> None:
    # A Payment whose amount is an Add of two observables yields 4 canonical
    # nodes (two Observables, the Add, the Payment); a 3-node budget rejects it.
    wide = Payment(Add((_obs("equity", "AAA"), _obs("equity", "BBB"))), usd, T0)
    with pytest.raises(CanonicalizationComplexityError):
        canonicalize_contract(
            wide, limits=CanonicalizationLimits(max_canonical_nodes=3)
        )


def test_canonical_contract_is_not_a_contract() -> None:
    result = canonicalize_contract(_payment())
    assert isinstance(result, CanonicalContract)
    # It must not satisfy the live Contract root check.
    with pytest.raises(CanonicalizationInputError):
        canonicalize_contract(result)  # type: ignore[arg-type]


def test_canonicalization_reachability_missing_node_error() -> None:
    # Exercise the internal sanity check for a missing referenced node.
    # We monkey-patch _build_payload to inject a reference to a non-existent node.
    from typing import Any

    from derivatrace.canonical import _normalization as norm

    original_build = norm._build_payload

    def bad_build(
        node: object,
        lookup: Any,
        canon_nodes: dict[str, Any],
        path: tuple[str | int, ...],
    ) -> dict[str, Any]:
        payload = original_build(node, lookup, canon_nodes, path)
        # Inject a reference to a non-existent node ID
        if payload.get("type") == "Payment":
            payload["amount"] = "deadbeef" * 8  # 64 hex chars, not in canon_nodes
        return payload

    try:
        norm._build_payload = bad_build
        with pytest.raises(CanonicalizationError, match="referenced but not produced"):
            canonicalize_contract(_payment())
    finally:
        norm._build_payload = original_build
