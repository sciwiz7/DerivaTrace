from __future__ import annotations

import json as _json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from derivatrace.contracts._values import (
    _CURRENCY_RE,
    _IDENTIFIER_RE,
    _SLUG_RE,
    FIELD_MAX_LEN,
    IDENTIFIER_MAX_LEN,
    NAMESPACE_MAX_LEN,
    Currency,
    ExactNumber,
    ObservableId,
    ObservationTime,
    SettlementTime,
    Unit,
    UnitKind,
)

from ._errors import CanonicalizationEncodingError

# Exact decimal bounds (canonicalization-spec.md section 4.4). These are applied
# when normalizing a Decimal into its canonical tuple form; they are stricter and
# independent of the ambient decimal context.
MAX_COEFF_DIGITS: int = 50
EXP_MIN: int = -(2**31)
EXP_MAX: int = 2**31 - 1

# Internal exact-coefficient representation of a Decimal value: a triple
# ``(sign, coefficient, exponent)`` where ``sign`` is ``0`` for non-negative or
# ``1`` for negative, ``coefficient`` is a non-negative Python ``int``, and
# ``exponent`` is an ``int``. This form is independent of the decimal context and
# never rounds.
_Coeff = tuple[int, int, int]


def canonical_json(obj: object) -> bytes:
    """Serialize a JSON-compatible structure to byte-exact canonical bytes.

    UTF-8, no BOM, no trailing newline, compact separators, ASCII-escaped, with
    object keys sorted by their (ASCII) byte sequence. This is the single
    serialization primitive used for payloads and documents.
    """
    return _json.dumps(
        obj, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Exact Decimal encoding (tuple semantics, context independent)
# ---------------------------------------------------------------------------


def _int_coeff_from_decimal(d: Decimal) -> _Coeff:
    t = d.as_tuple()
    neg = t.sign == 1
    coeff = 0
    for digit in t.digits:
        coeff = coeff * 10 + digit
    exponent = t.exponent
    if not isinstance(exponent, int):
        raise CanonicalizationEncodingError("only finite decimals are canonicalizable")
    return (neg, coeff, exponent)


def _coeff_to_value_dict(neg: int, coeff: int, exp: int) -> dict[str, Any]:
    if coeff == 0:
        return {"sign": 0, "digits": "0", "exponent": 0}
    working = coeff
    e = exp
    while working % 10 == 0:
        working //= 10
        e += 1
    digits = str(working)
    if len(digits) > MAX_COEFF_DIGITS:
        raise CanonicalizationEncodingError(
            f"decimal coefficient exceeds {MAX_COEFF_DIGITS} digits"
        )
    if e < EXP_MIN or e > EXP_MAX:
        raise CanonicalizationEncodingError("decimal exponent out of range")
    return {"sign": 1 if neg else 0, "digits": digits, "exponent": e}


def _decode_value_dict(d: dict[str, Any]) -> _Coeff:
    neg = 1 if d["sign"] == 1 else 0
    coeff = int(d["digits"]) if d["digits"] else 0
    exp = d["exponent"]
    return (neg, coeff, exp)


def encode_decimal(d: Decimal) -> dict[str, Any]:
    """Encode a finite :class:`decimal.Decimal` to its canonical tuple dict.

    Applies the normative algorithm (strip trailing zeros, force canonical
    zero, preserve sign) without ``Decimal.normalize`` and without any decimal
    context dependence.
    """
    neg, coeff, exp = _int_coeff_from_decimal(d)
    return _coeff_to_value_dict(neg, coeff, exp)


def _safe_number_payload(
    coeff: _Coeff, unit_dict: dict[str, Any]
) -> dict[str, Any] | None:
    neg, c, exp = coeff
    if c == 0:
        return {
            "type": "Number",
            "unit": unit_dict,
            "value": {"sign": 0, "digits": "0", "exponent": 0},
        }
    working = c
    e = exp
    while working % 10 == 0:
        working //= 10
        e += 1
    digits = str(working)
    if len(digits) > MAX_COEFF_DIGITS or e < EXP_MIN or e > EXP_MAX:
        return None
    return {
        "type": "Number",
        "unit": unit_dict,
        "value": {"sign": 1 if neg else 0, "digits": digits, "exponent": e},
    }


# ---------------------------------------------------------------------------
# Exact integer-coefficient arithmetic (no float, no rounding)
# ---------------------------------------------------------------------------


def _exact_neg(a: _Coeff) -> _Coeff:
    neg, coeff, exp = a
    if coeff == 0:
        return (False, 0, 0)
    return (not neg, coeff, exp)


def _exact_add(a: _Coeff, b: _Coeff) -> _Coeff:
    neg1, c1, e1 = a
    neg2, c2, e2 = b
    if c1 == 0:
        return b
    if c2 == 0:
        return a
    emin = min(e1, e2)
    a_int = (c1 if not neg1 else -c1) * (10 ** (e1 - emin))
    b_int = (c2 if not neg2 else -c2) * (10 ** (e2 - emin))
    s = a_int + b_int
    if s == 0:
        return (False, 0, 0)
    return (s < 0, abs(s), emin)


def _exact_sub(a: _Coeff, b: _Coeff) -> _Coeff:
    return _exact_add(a, _exact_neg(b))


def _exact_mul(a: _Coeff, b: _Coeff) -> _Coeff:
    neg1, c1, e1 = a
    neg2, c2, e2 = b
    if c1 == 0 or c2 == 0:
        return (False, 0, 0)
    return (neg1 != neg2, c1 * c2, e1 + e2)


def _fold_number_payload(
    coeff: _Coeff, unit_dict: dict[str, Any]
) -> dict[str, Any] | None:
    """Fold an exact-coefficient value into a canonical ``Number`` payload.

    Returns ``None`` only when the value exceeds the canonical numeric bounds
    (coefficient digit count or exponent range). Callers that fold the result of
    arithmetic on *validated* operands treat ``None`` as "do not fold, keep the
    operator node"; callers that fold a single validated operand (negation, or a
    maximum/minimum over validated operands) may rely on the value always being
    in bounds and unwrap with :func:`_unwrap_folded_number`.
    """
    return _safe_number_payload(coeff, unit_dict)


def _unwrap_folded_number(coeff: _Coeff, unit_dict: dict[str, Any]) -> dict[str, Any]:
    """Total variant of :func:`_fold_number_payload` for validated operands.

    A validated operand is guaranteed within canonical numeric bounds, so folding
    is total; if the bounds were somehow exceeded this is a deterministic
    encoding error rather than a silent skip. Use this only where the operand
    value is already known to be a constructible, in-bounds number.
    """
    payload = _safe_number_payload(coeff, unit_dict)
    if payload is None:
        raise CanonicalizationEncodingError(
            "number literal exceeds canonical numeric bounds"
        )
    return payload


def _exact_cmp(a: _Coeff, b: _Coeff) -> int:
    neg1, c1, e1 = a
    neg2, c2, e2 = b
    emin = min(e1, e2)
    a_int = (c1 if not neg1 else -c1) * (10 ** (e1 - emin))
    b_int = (c2 if not neg2 else -c2) * (10 ** (e2 - emin))
    if a_int < b_int:
        return -1
    if a_int > b_int:
        return 1
    return 0


def _apply_comparison_operator(symbol: str, a: _Coeff, b: _Coeff) -> bool:
    c = _exact_cmp(a, b)
    if symbol == "<":
        return c < 0
    if symbol == "<=":
        return c <= 0
    if symbol == "==":
        return c == 0
    if symbol == "!=":
        return c != 0
    if symbol == ">=":
        return c >= 0
    if symbol == ">":
        return c > 0
    raise CanonicalizationEncodingError(f"unknown comparison operator: {symbol!r}")


# ---------------------------------------------------------------------------
# Value-object encoding (revalidate stored invariants before encoding)
# ---------------------------------------------------------------------------


def encode_exact_number(en: ExactNumber) -> dict[str, Any]:
    if type(en) is not ExactNumber:
        raise CanonicalizationEncodingError(
            "ExactNumber must be exactly the approved type"
        )
    d = en.value
    if not isinstance(d, Decimal) or not d.is_finite():
        raise CanonicalizationEncodingError("ExactNumber must wrap a finite Decimal")
    return encode_decimal(d)


def encode_currency(cur: Currency) -> str:
    if type(cur) is not Currency:
        raise CanonicalizationEncodingError(
            "Currency must be exactly the approved type"
        )
    if not _CURRENCY_RE.match(cur.code):
        raise CanonicalizationEncodingError(
            "Currency must be three uppercase ASCII letters"
        )
    return cur.code


def encode_unit(unit: Unit) -> dict[str, Any]:
    if type(unit) is not Unit:
        raise CanonicalizationEncodingError("Unit must be exactly the approved type")
    if unit.kind is UnitKind.SCALAR:
        if unit.currency is not None:
            raise CanonicalizationEncodingError("scalar unit cannot carry a currency")
        return {"kind": "scalar"}
    if type(unit.currency) is not Currency:
        raise CanonicalizationEncodingError("money unit requires a Currency")
    return {"kind": "money", "currency": encode_currency(unit.currency)}


def encode_observable_id(oid: ObservableId) -> dict[str, Any]:
    if type(oid) is not ObservableId:
        raise CanonicalizationEncodingError(
            "ObservableId must be exactly the approved type"
        )
    if not _SLUG_RE.match(oid.namespace) or len(oid.namespace) > NAMESPACE_MAX_LEN:
        raise CanonicalizationEncodingError("ObservableId.namespace invalid")
    if not _SLUG_RE.match(oid.field) or len(oid.field) > FIELD_MAX_LEN:
        raise CanonicalizationEncodingError("ObservableId.field invalid")
    if (
        not _IDENTIFIER_RE.match(oid.identifier)
        or len(oid.identifier) > IDENTIFIER_MAX_LEN
    ):
        raise CanonicalizationEncodingError("ObservableId.identifier invalid")
    return {
        "field": oid.field,
        "identifier": oid.identifier,
        "namespace": oid.namespace,
    }


def encode_timestamp(ts: object) -> str:
    if type(ts) not in (ObservationTime, SettlementTime):
        raise CanonicalizationEncodingError(
            "timestamp must be ObservationTime or SettlementTime"
        )
    value: datetime = ts.value  # type: ignore[attr-defined]
    if value.utcoffset() != timedelta(0):
        raise CanonicalizationEncodingError("timestamp must be stored in canonical UTC")
    return value.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _encode_operator_symbol(value: object) -> str:
    # ``ComparisonOperator`` is a plain ``Enum`` whose members carry the stable
    # symbol string as their value (e.g. LESS_THAN == "<").
    if not hasattr(value, "value"):
        raise CanonicalizationEncodingError("operator must be a ComparisonOperator")
    return str(value.value)


__all__: list[str] = [
    "EXP_MAX",
    "EXP_MIN",
    "MAX_COEFF_DIGITS",
    "_apply_comparison_operator",
    "_coeff_to_value_dict",
    "_decode_value_dict",
    "_encode_operator_symbol",
    "_exact_add",
    "_exact_cmp",
    "_exact_mul",
    "_exact_neg",
    "_exact_sub",
    "_fold_number_payload",
    "_int_coeff_from_decimal",
    "_safe_number_payload",
    "_unwrap_folded_number",
    "canonical_json",
    "encode_currency",
    "encode_decimal",
    "encode_exact_number",
    "encode_observable_id",
    "encode_timestamp",
    "encode_unit",
]
