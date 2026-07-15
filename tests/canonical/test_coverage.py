from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from derivatrace.canonical import (
    CanonicalizationCollisionError,
    CanonicalizationComplexityError,
    CanonicalizationEncodingError,
    CanonicalizationError,
    CanonicalizationInputError,
    CanonicalizationLimits,
    CanonicalizationNotValidatedError,
    CanonicalSchemaVersion,
    canonical_contract_bytes,
    canonical_contract_identity,
    canonicalize_contract,
    structurally_equivalent,
)
from derivatrace.canonical import (
    _normalization as _norm,
)
from derivatrace.canonical._encoding import (
    _apply_comparison_operator,
    _coeff_to_value_dict,
    _encode_operator_symbol,
    _exact_add,
    _exact_mul,
    _exact_neg,
    _fold_number_payload,
    _int_coeff_from_decimal,
    _unwrap_folded_number,
    encode_currency,
    encode_exact_number,
    encode_observable_id,
    encode_timestamp,
    encode_unit,
)
from derivatrace.canonical._normalization import _build_payload
from derivatrace.contracts import (
    Add,
    AllOf,
    AnyOf,
    BooleanConstant,
    Both,
    Comparison,
    ComparisonOperator,
    ConditionalContract,
    ConditionalValue,
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
    Payment,
    Scale,
    SettlementTime,
    Subtract,
    Unit,
    UnitKind,
    ValidationLimits,
    Zero,
)

usd = Currency.from_code("USD")
T0 = SettlementTime.from_datetime(datetime(2030, 6, 1, tzinfo=UTC))
OT0 = ObservationTime.from_datetime(datetime(2030, 6, 1, tzinfo=UTC))


def _obs(nsp: str, ident: str, field: str = "close") -> Observable:
    return Observable(ObservableId.from_parts(nsp, ident, field), OT0, Unit.money(usd))


def _num(s: str) -> Number:
    return Number(ExactNumber.from_string(s), Unit.scalar())


def _money(s: str) -> Number:
    return Number(ExactNumber.from_string(s), Unit.money(usd))


def _payment() -> Payment:
    return Payment(_money("1"), usd, T0)


# ---------------------------------------------------------------------------
# CanonicalSchemaVersion / CanonicalizationLimits validation
# ---------------------------------------------------------------------------


def test_schema_rejects_bad_name() -> None:
    with pytest.raises(CanonicalizationInputError):
        CanonicalSchemaVersion(name="wrong.name", version="1.0.0")


def test_schema_rejects_bad_version() -> None:
    with pytest.raises(CanonicalizationInputError):
        CanonicalSchemaVersion(name="derivatrace.contract.canonical", version="2.0.0")


def test_schema_supported_classmethod() -> None:
    sv = CanonicalSchemaVersion.supported()
    assert sv.name == "derivatrace.contract.canonical"
    assert sv.version == "1.0.0"


def test_limits_reject_non_int_nodes() -> None:
    with pytest.raises(CanonicalizationInputError):
        CanonicalizationLimits(max_canonical_nodes=True)
    with pytest.raises(CanonicalizationInputError):
        CanonicalizationLimits(max_canonical_nodes=0)
    with pytest.raises(CanonicalizationInputError):
        CanonicalizationLimits(max_canonical_bytes=-1)


def test_limits_default() -> None:
    assert CanonicalizationLimits.default().max_canonical_nodes == 16384
    assert CanonicalizationLimits.default().max_canonical_bytes == 8_000_000


# ---------------------------------------------------------------------------
# CanonicalContract equality / hashing / repr
# ---------------------------------------------------------------------------


def test_canonical_contract_eq_hash_repr() -> None:
    r = canonicalize_contract(_payment())
    assert r == r
    assert hash(r) == hash(canonicalize_contract(_payment()))
    assert repr(r).startswith("CanonicalContract(")
    assert (r == "not a canonical") is False


# ---------------------------------------------------------------------------
# encode_* validation error paths
# ---------------------------------------------------------------------------


def test_encode_exact_number_rejects_non_exact() -> None:
    with pytest.raises(CanonicalizationEncodingError):
        encode_exact_number("not exact")  # type: ignore[arg-type]


def _raw(cls: type, **fields: object) -> object:
    obj = cls.__new__(cls)  # type: ignore[call-overload]
    for name, value in fields.items():
        object.__setattr__(obj, name, value)
    return obj


def test_encode_exact_number_rejects_non_finite() -> None:
    en = _raw(ExactNumber, _value=Decimal("NaN"))
    with pytest.raises(CanonicalizationEncodingError):
        encode_exact_number(en)  # type: ignore[arg-type]


def test_encode_currency_rejects_type() -> None:
    with pytest.raises(CanonicalizationEncodingError):
        encode_currency("USD")  # type: ignore[arg-type]


def test_encode_currency_rejects_bad_code() -> None:
    bad = _raw(Currency, _code="US")
    with pytest.raises(CanonicalizationEncodingError):
        encode_currency(bad)  # type: ignore[arg-type]


def test_encode_unit_rejects_type() -> None:
    with pytest.raises(CanonicalizationEncodingError):
        encode_unit({"kind": "scalar"})  # type: ignore[arg-type]


def test_encode_unit_scalar_with_currency() -> None:
    bad = _raw(Unit, kind=UnitKind.SCALAR, currency=usd)
    with pytest.raises(CanonicalizationEncodingError):
        encode_unit(bad)  # type: ignore[arg-type]


def test_encode_unit_money_requires_currency() -> None:
    bad = _raw(Unit, kind=UnitKind.MONEY, currency=None)
    with pytest.raises(CanonicalizationEncodingError):
        encode_unit(bad)  # type: ignore[arg-type]


def test_encode_observable_id_rejects_type() -> None:
    with pytest.raises(CanonicalizationEncodingError):
        encode_observable_id("bad")  # type: ignore[arg-type]


def test_encode_observable_id_rejects_bad_namespace() -> None:
    bad = _raw(ObservableId, namespace="bad ns", identifier="A", field="f")
    with pytest.raises(CanonicalizationEncodingError):
        encode_observable_id(bad)  # type: ignore[arg-type]


def test_encode_timestamp_rejects_type() -> None:
    with pytest.raises(CanonicalizationEncodingError):
        encode_timestamp("2024-01-01T00:00:00Z")


def test_encode_timestamp_rejects_non_utc() -> None:
    non_utc = _raw(
        ObservationTime,
        _value=datetime(2030, 1, 1, tzinfo=timezone(timedelta(hours=1))),
    )
    with pytest.raises(CanonicalizationEncodingError):
        encode_timestamp(non_utc)


def test_coeff_to_value_dict_bounds() -> None:
    assert _coeff_to_value_dict(0, 0, 0) == {
        "sign": 0,
        "digits": "0",
        "exponent": 0,
    }
    with pytest.raises(CanonicalizationEncodingError):
        _coeff_to_value_dict(0, 10**50 + 1, 0)
    with pytest.raises(CanonicalizationEncodingError):
        _coeff_to_value_dict(0, 5, 2**31)


def test_int_coeff_from_decimal_rejects_non_finite() -> None:
    with pytest.raises(CanonicalizationEncodingError):
        _int_coeff_from_decimal(Decimal("Infinity"))


# ---------------------------------------------------------------------------
# canonicalize_contract input / limit error paths
# ---------------------------------------------------------------------------


def test_canonicalize_rejects_bad_schema() -> None:
    with pytest.raises(CanonicalizationInputError):
        canonicalize_contract(_payment(), schema="nope")  # type: ignore[arg-type]


def test_canonicalize_rejects_bad_limits() -> None:
    with pytest.raises(CanonicalizationInputError):
        canonicalize_contract(_payment(), limits="nope")  # type: ignore[arg-type]


def test_canonicalize_not_validated() -> None:
    # A graph that passes construction but fails `validate_contract` is rejected
    # with CanonicalizationNotValidatedError (validation cause preserved).
    from unittest import mock

    from derivatrace.canonical import _normalization as canon_mod
    from derivatrace.contracts import ContractError

    with (
        mock.patch.object(
            canon_mod, "validate_contract", side_effect=ContractError("invalid graph")
        ),
        pytest.raises(CanonicalizationNotValidatedError),
    ):
        canonicalize_contract(_payment())


def test_complexity_error_on_excess_bytes() -> None:
    wide = Payment(Add((_obs("equity", "AAA"), _obs("equity", "BBB"))), usd, T0)
    with pytest.raises(CanonicalizationComplexityError):
        canonicalize_contract(
            wide, limits=CanonicalizationLimits(max_canonical_bytes=1)
        )


def test_cycle_detection() -> None:
    from derivatrace.canonical import CanonicalizationCycleError

    s = Scale(_num("1"), _payment())
    object.__setattr__(s, "contract", s)
    with pytest.raises(CanonicalizationCycleError):
        canonicalize_contract(s)


# ---------------------------------------------------------------------------
# Serialization / equivalence helpers with explicit limits
# ---------------------------------------------------------------------------


def test_serialization_helpers_accept_limits() -> None:
    contract = _payment()
    limits = CanonicalizationLimits(max_canonical_nodes=1000)
    assert (
        canonical_contract_bytes(contract, limits=limits)
        == canonicalize_contract(contract, limits=limits).canonical_bytes
    )
    assert (
        canonical_contract_identity(contract, limits=limits)
        == canonicalize_contract(contract, limits=limits).identity
    )


def test_structurally_equivalent_accepts_limits() -> None:
    a = Payment(Add((_obs("equity", "AAA"), _obs("equity", "BBB"))), usd, T0)
    b = Payment(Add((_obs("equity", "BBB"), _obs("equity", "AAA"))), usd, T0)
    assert structurally_equivalent(a, b, limits=CanonicalizationLimits()) is True


# ---------------------------------------------------------------------------
# Operator nodes: non-folding / conditional-value / divide forms
# ---------------------------------------------------------------------------


def test_subtract_not_folded() -> None:
    r = canonicalize_contract(
        Payment(Subtract(_obs("equity", "AAA"), _obs("equity", "BBB")), usd, T0)
    )
    assert b"Subtract" in r.canonical_bytes


def test_negate_not_folded() -> None:
    r = canonicalize_contract(Payment(Negate(_obs("equity", "AAA")), usd, T0))
    assert b"Negate" in r.canonical_bytes


def test_negate_folds_to_number() -> None:
    r = canonicalize_contract(Scale(Negate(_num("5")), _payment()))
    assert b"Negate" not in r.canonical_bytes
    assert b'"digits":"5"' in r.canonical_bytes


def test_multiply_not_folded_with_observable() -> None:
    r = canonicalize_contract(
        Payment(Multiply(_obs("equity", "AAA"), _num("2")), usd, T0)
    )
    assert b"Multiply" in r.canonical_bytes


def test_add_not_folded() -> None:
    r = canonicalize_contract(
        Payment(Add((_obs("equity", "AAA"), _obs("equity", "BBB"))), usd, T0)
    )
    assert b"Add" in r.canonical_bytes


def test_maximum_not_folded() -> None:
    r = canonicalize_contract(
        Payment(Maximum((_obs("equity", "AAA"), _obs("equity", "BBB"))), usd, T0)
    )
    assert b"Maximum" in r.canonical_bytes


def test_minimum_not_folded() -> None:
    r = canonicalize_contract(
        Payment(Minimum((_obs("equity", "AAA"), _obs("equity", "BBB"))), usd, T0)
    )
    assert b"Minimum" in r.canonical_bytes


def test_divide_node_canonicalized() -> None:
    r = canonicalize_contract(
        Payment(Divide(_obs("equity", "AAA"), _num("2")), usd, T0)
    )
    assert b"Divide" in r.canonical_bytes


def test_conditional_value_node_canonicalized() -> None:
    cv = ConditionalValue(
        Comparison(
            _obs("equity", "AAA"), _obs("equity", "BBB"), ComparisonOperator.LESS_THAN
        ),
        _num("1"),
        _num("2"),
    )
    r = canonicalize_contract(Scale(cv, _payment()))
    assert b"ConditionalValue" in r.canonical_bytes


def test_conditional_value_folds_to_branch() -> None:
    cv = ConditionalValue(BooleanConstant(True), _num("1"), _num("2"))
    r = canonicalize_contract(Scale(cv, _payment()))
    assert b"ConditionalValue" not in r.canonical_bytes
    assert b'"digits":"1"' in r.canonical_bytes


# ---------------------------------------------------------------------------
# Boolean collections: non-constant + flattening
# ---------------------------------------------------------------------------


def test_allof_non_constant_builds_node() -> None:
    cond = AllOf(
        (
            BooleanConstant(True),
            Comparison(
                _obs("equity", "AAA"),
                _obs("equity", "BBB"),
                ComparisonOperator.LESS_THAN,
            ),
        )
    )
    r = canonicalize_contract(ConditionalContract(cond, _payment(), _payment()))
    assert b"AllOf" in r.canonical_bytes


def test_anyof_non_constant_builds_node() -> None:
    cond = AnyOf(
        (
            BooleanConstant(False),
            Comparison(
                _obs("equity", "AAA"),
                _obs("equity", "BBB"),
                ComparisonOperator.LESS_THAN,
            ),
        )
    )
    r = canonicalize_contract(ConditionalContract(cond, _payment(), _payment()))
    assert b"AnyOf" in r.canonical_bytes


def test_boolean_collection_flattens_nested() -> None:
    inner = AllOf((BooleanConstant(True), BooleanConstant(True)))
    nested = AllOf((inner, BooleanConstant(True)))
    flat = AllOf((BooleanConstant(True), BooleanConstant(True), BooleanConstant(True)))
    rn = canonicalize_contract(ConditionalContract(nested, _payment(), _payment()))
    rf = canonicalize_contract(ConditionalContract(flat, _payment(), _payment()))
    # Nested AllOf operands are spliced into the outer collection (flattening).
    assert rn.node_count == rf.node_count


def test_not_non_constant_builds_node() -> None:
    cond = Not(
        Comparison(
            _obs("equity", "AAA"), _obs("equity", "BBB"), ComparisonOperator.LESS_THAN
        )
    )
    r = canonicalize_contract(ConditionalContract(cond, _payment(), _payment()))
    assert b"Not" in r.canonical_bytes


def test_comparison_non_fold_builds_node() -> None:
    comp = Comparison(
        _obs("equity", "AAA"), _obs("equity", "BBB"), ComparisonOperator.LESS_THAN
    )
    r = canonicalize_contract(ConditionalContract(comp, _payment(), _payment()))
    assert b"Comparison" in r.canonical_bytes


def test_conditional_contract_non_constant() -> None:
    cond = Comparison(
        _obs("equity", "AAA"), _obs("equity", "BBB"), ComparisonOperator.LESS_THAN
    )
    r = canonicalize_contract(ConditionalContract(cond, _payment(), _payment()))
    assert b"ConditionalContract" in r.canonical_bytes


# --- Remaining branch coverage ---------------------------------------------


def test_encode_exact_number_strips_trailing_zeros() -> None:
    # "10" carries a trailing-zero coefficient; the encoder normalizes it to
    # digits "1" with exponent 1, exercising the coefficient-stripping loop.
    payload = encode_exact_number(ExactNumber.from_string("10"))
    assert payload == {"sign": 0, "digits": "1", "exponent": 1}


def test_add_of_numbers_with_trailing_zero_folds_via_strip_loop() -> None:
    # 5 + 5 = 10; the exact-arithmetic sum has a trailing-zero coefficient, so the
    # ``_coeff_to_value_dict`` strip loop runs while encoding the folded Number.
    r = canonicalize_contract(Scale(Add((_num("5"), _num("5"))), _payment()))
    numbers = _find_nodes(r, "Number")
    assert any(n["value"] == {"sign": 0, "digits": "1", "exponent": 1} for n in numbers)


def test_exact_arithmetic_zero_paths() -> None:
    assert _exact_neg((0, 0, 0)) == (0, 0, 0)
    assert _exact_add((0, 2, 0), (0, 0, 0)) == (0, 2, 0)
    assert _exact_add((0, 2, 0), (1, 2, 0)) == (0, 0, 0)
    assert _exact_mul((0, 0, 0), (0, 3, 0)) == (0, 0, 0)


def test_apply_comparison_unknown_symbol() -> None:
    with pytest.raises(CanonicalizationEncodingError):
        _apply_comparison_operator("?", (0, 0, 0), (0, 0, 0))


# --- Private dispatch / fold seams (previously coverage-excluded) ------------


def test_build_payload_unsupported_node_raises() -> None:
    # The private dispatch boundary must reject an unknown node type with a
    # deterministic CanonicalizationError rather than silently mishandling it.
    with pytest.raises(CanonicalizationError):
        _build_payload(object(), lambda c: ("", {}), {}, ())


def test_unwrap_folded_number_out_of_bounds_raises() -> None:
    # ``_unwrap_folded_number`` is total for validated operands but raises a
    # deterministic encoding error if the value somehow exceeds canonical bounds.
    with pytest.raises(CanonicalizationEncodingError):
        _unwrap_folded_number((0, 10**50 + 1, 0), {"kind": "scalar"})
    # The best-effort variant returns None instead of raising.
    assert _fold_number_payload((0, 10**50 + 1, 0), {"kind": "scalar"}) is None


def test_unwrap_folded_number_valid_returns_payload() -> None:
    payload = _unwrap_folded_number((0, 7, 0), {"kind": "scalar"})
    assert payload == {
        "type": "Number",
        "unit": {"kind": "scalar"},
        "value": {"sign": 0, "digits": "7", "exponent": 0},
    }


def test_encode_observable_id_bad_field() -> None:
    with pytest.raises(CanonicalizationEncodingError):
        encode_observable_id(
            _raw(ObservableId, namespace="eq", identifier="A", field="BAD FIELD")  # type: ignore[arg-type]
        )


def test_encode_observable_id_bad_identifier() -> None:
    with pytest.raises(CanonicalizationEncodingError):
        encode_observable_id(
            _raw(ObservableId, namespace="eq", identifier="BAD ID", field="f")  # type: ignore[arg-type]
        )


def test_encode_operator_symbol_without_value() -> None:
    with pytest.raises(CanonicalizationEncodingError):
        _encode_operator_symbol(123)


def test_canonicalize_identity_collision() -> None:
    from unittest import mock

    with (
        mock.patch.object(_norm, "node_identity", return_value="CONSTANT"),
        pytest.raises(CanonicalizationCollisionError),
    ):
        canonicalize_contract(Both((_payment(), _payment())))


def _find_nodes(r: object, node_type: str) -> list[dict[str, Any]]:
    doc: Any = json.loads(r.canonical_bytes)  # type: ignore[attr-defined]
    return [
        n["payload"]
        for n in doc["nodes"].values()
        if n["payload"].get("type") == node_type
    ]


def test_add_folded_number_exceeds_limits_keeps_operator() -> None:
    big = "9" * 50
    r = canonicalize_contract(Scale(Add((_num(big), _num(big))), _payment()))
    adds = _find_nodes(r, "Add")
    assert adds and len(adds[0]["operands"]) == 2


def test_maximum_of_numbers_folds_to_number() -> None:
    big = "9" * 50
    r = canonicalize_contract(Scale(Maximum((_num(big), _num(big))), _payment()))
    # Max of two constructible numbers stays within limits and folds to a Number.
    assert not _find_nodes(r, "Maximum")
    assert _find_nodes(r, "Number")


def test_minimum_of_numbers_folds_to_number() -> None:
    big = "9" * 50
    r = canonicalize_contract(Scale(Minimum((_num(big), _num(big))), _payment()))
    assert not _find_nodes(r, "Minimum")
    assert _find_nodes(r, "Number")


def test_subtract_folded_number_exceeds_limits_keeps_operator() -> None:
    big = "9" * 50
    r = canonicalize_contract(Scale(Subtract(_num(big), _num("-" + big)), _payment()))
    subtracts = _find_nodes(r, "Subtract")
    assert subtracts and subtracts[0]["minuend"] and subtracts[0]["subtrahend"]


def test_multiply_folded_number_exceeds_limits_keeps_operator() -> None:
    big = "9" * 50
    r = canonicalize_contract(Scale(Multiply(_num(big), _num(big)), _payment()))
    multiplies = _find_nodes(r, "Multiply")
    assert multiplies and multiplies[0]["left"] and multiplies[0]["right"]


def test_boolean_collection_splices_nested_nonconstant() -> None:
    comp = Comparison(
        _obs("equity", "AAA"), _obs("equity", "BBB"), ComparisonOperator.LESS_THAN
    )
    # An inner AnyOf of two comparisons does not fold (not all constants), so the
    # outer AnyOf splices its operands in, exercising the flattening extend path.
    nested = AnyOf((AnyOf((comp, comp)), comp))
    r = canonicalize_contract(ConditionalContract(nested, _payment(), _payment()))
    anyofs = _find_nodes(r, "AnyOf")
    assert anyofs and any(len(a["operands"]) == 3 for a in anyofs)


def test_zero_node_emitted() -> None:
    r = canonicalize_contract(Zero())
    assert b'"Zero"' in r.canonical_bytes


def test_anyof_all_true_folds_to_constant() -> None:
    cond = AnyOf((BooleanConstant(True), BooleanConstant(True)))
    r = canonicalize_contract(ConditionalContract(cond, _payment(), _payment()))
    # The AnyOf folds to BooleanConstant(True), the conditional selects the
    # true branch, and the condition/false branch are pruned. The result is
    # identical to the branch contract alone.
    assert r == canonicalize_contract(_payment())


def test_canonicalize_validation_complexity_error() -> None:
    with pytest.raises(CanonicalizationComplexityError):
        canonicalize_contract(
            _payment(), validation_limits=ValidationLimits(max_unique_nodes=1)
        )
