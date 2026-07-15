from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from derivatrace.canonical import (
    CanonicalizationLimits,
    CanonicalSchemaVersion,
)
from derivatrace.canonical._encoding import (
    _apply_comparison_operator,
    _decode_value_dict,
    _exact_add,
    _exact_cmp,
    _exact_mul,
    _exact_neg,
    _exact_sub,
    _safe_number_payload,
    canonical_json,
    encode_currency,
    encode_exact_number,
    encode_observable_id,
    encode_timestamp,
    encode_unit,
)
from derivatrace.canonical._identity import contract_identity, node_identity
from derivatrace.contracts import (
    ComparisonOperator,
    Currency,
    ExactNumber,
    ObservableId,
    ObservationTime,
    Unit,
)


def test_canonical_json_is_sorted_compact_ascii() -> None:
    obj = {"b": 1, "a": {"z": True, "y": "x"}, "c": [3, 1, 2]}
    out = canonical_json(obj)
    assert out == b'{"a":{"y":"x","z":true},"b":1,"c":[3,1,2]}'
    assert b" " not in out


def test_encode_exact_number_canonical_forms() -> None:
    assert encode_exact_number(ExactNumber.from_string("0")) == {
        "sign": 0,
        "digits": "0",
        "exponent": 0,
    }
    assert encode_exact_number(ExactNumber.from_string("-0")) == {
        "sign": 0,
        "digits": "0",
        "exponent": 0,
    }
    assert encode_exact_number(ExactNumber.from_string("2.0")) == {
        "sign": 0,
        "digits": "2",
        "exponent": 0,
    }
    assert encode_exact_number(ExactNumber.from_string("0.50")) == {
        "sign": 0,
        "digits": "5",
        "exponent": -1,
    }
    assert encode_exact_number(ExactNumber.from_string("-123.4500")) == {
        "sign": 1,
        "digits": "12345",
        "exponent": -2,
    }
    assert encode_exact_number(ExactNumber.from_string("100")) == {
        "sign": 0,
        "digits": "1",
        "exponent": 2,
    }


def _coeff_to_decimal(neg: int, coeff: int, exp: int) -> Decimal:
    digits = tuple(int(ch) for ch in str(coeff)) if coeff else (0,)
    return Decimal((1 if neg else 0, digits, exp))


def _to_decimal(triple: tuple[int, int, int]) -> object:
    payload = _safe_number_payload(triple, {"kind": "scalar"})
    assert payload is not None
    neg, coeff, exp = _decode_value_dict(payload["value"])
    return _coeff_to_decimal(neg, coeff, exp)


def test_exact_arithmetic_roundtrips() -> None:
    from decimal import Decimal

    assert _to_decimal(_exact_add((0, 0, 0), (0, 5, 0))) == Decimal("5")
    assert _to_decimal(_exact_add((0, 2, 0), (0, 3, 0))) == Decimal("5")
    assert _to_decimal(_exact_add((1, 2, 0), (0, 3, 0))) == Decimal("1")  # -2 + 3
    assert _to_decimal(_exact_sub((0, 5, 0), (0, 2, 0))) == Decimal("3")
    assert _to_decimal(_exact_sub((0, 2, 0), (0, 5, 0))) == Decimal("-3")
    assert _to_decimal(_exact_mul((0, 2, 0), (0, 3, 0))) == Decimal("6")
    assert _to_decimal(_exact_mul((1, 2, 0), (1, 3, 0))) == Decimal("6")
    assert _to_decimal(_exact_neg((1, 2, 0))) == Decimal("2")
    assert _to_decimal(_exact_neg((0, 2, 0))) == Decimal("-2")
    assert _exact_cmp((0, 2, 0), (0, 3, 0)) < 0
    assert _exact_cmp((0, 3, 0), (0, 3, 0)) == 0
    assert _exact_cmp((1, 2, 0), (0, 2, 0)) < 0


def test_apply_comparison_operator_all_symbols() -> None:
    a = (0, 2, 0)
    b = (0, 3, 0)
    mapping = {
        ComparisonOperator.LESS_THAN: True,
        ComparisonOperator.LESS_THAN_OR_EQUAL: True,
        ComparisonOperator.EQUAL: False,
        ComparisonOperator.NOT_EQUAL: True,
        ComparisonOperator.GREATER_THAN_OR_EQUAL: False,
        ComparisonOperator.GREATER_THAN: False,
    }
    for op, expected in mapping.items():
        assert _apply_comparison_operator(op.value, a, b) is expected


def test_safe_number_payload_forbids_forbidden_normalized_state() -> None:
    # A non-canonical zero (e.g. 0E+2) must always normalize to exponent 0;
    # Decimal.normalize is never used. The canonical zero form is emitted.
    assert _safe_number_payload((0, 0, 2), {"kind": "scalar"}) == {
        "type": "Number",
        "unit": {"kind": "scalar"},
        "value": {"sign": 0, "digits": "0", "exponent": 0},
    }


def test_safe_number_payload_enforces_bounds() -> None:
    huge = (0, 10**50 + 1, 0)
    assert _safe_number_payload(huge, {"kind": "scalar"}) is None
    big_exp = (0, 5, 2**31)
    assert _safe_number_payload(big_exp, {"kind": "scalar"}) is None
    assert _safe_number_payload((0, 5, 0), {"kind": "scalar"}) is not None


def test_decode_value_dict_inverts_encode() -> None:
    for raw in ("0", "-0", "2.0", "0.50", "-123.4500", "100", "3.14159"):
        enc = encode_exact_number(ExactNumber.from_string(raw))
        neg, coeff, exp = _decode_value_dict(enc)
        got = _coeff_to_decimal(neg, coeff, exp)
        assert got == ExactNumber.from_string(raw).value


def test_encode_unit_and_currency_and_observable_id() -> None:
    assert encode_unit(Unit.scalar()) == {"kind": "scalar"}
    money = Unit.money(Currency.from_code("USD"))
    assert encode_unit(money) == {"kind": "money", "currency": "USD"}
    assert encode_currency(Currency.from_code("USD")) == "USD"

    oid = encode_observable_id(ObservableId.from_parts("equity", "AAA", "close"))
    assert oid == {"namespace": "equity", "identifier": "AAA", "field": "close"}


def test_encode_timestamp_microsecond_precision() -> None:

    ts = ObservationTime.from_datetime(
        datetime(2030, 1, 1, 0, 0, 0, 500_000, tzinfo=UTC)
    )
    assert encode_timestamp(ts) == "2030-01-01T00:00:00.500000Z"


def test_identity_seams_are_versioned_and_deterministic() -> None:
    payload = b'{"type":"Zero"}'
    nid = node_identity(payload, "1.0.0")
    assert nid == node_identity(payload, "1.0.0")
    assert nid != node_identity(payload, "1.0.1")
    doc = b'{"nodes":{}}'
    assert contract_identity(doc, "1.0.0").startswith("canonical:sha256:")


def test_identity_digest_seam_is_monkeypatchable() -> None:
    import derivatrace.canonical._identity as identity_mod

    original = identity_mod._digest
    try:
        identity_mod._digest = lambda domain, version, payload: "0" * 64
        assert node_identity(b"x", "1.0.0") == "0" * 64
    finally:
        identity_mod._digest = original


def test_schema_and_limits_defaults() -> None:
    sv = CanonicalSchemaVersion()
    assert sv.version == "1.0.0"
    assert sv.name == "derivatrace.contract.canonical"
    limits = CanonicalizationLimits.default()
    assert limits.max_canonical_nodes == 16384
    assert limits.max_canonical_bytes == 8_000_000
    custom = CanonicalizationLimits(max_canonical_nodes=3, max_canonical_bytes=10)
    assert custom.max_canonical_nodes == 3
