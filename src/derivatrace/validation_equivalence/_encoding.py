from __future__ import annotations

import json as _json
from collections.abc import Callable
from typing import Any

from ._errors import ValidationEquivalenceEncodingError

ReportEncoder = Callable[[object], bytes]


def canonical_json(obj: object) -> bytes:
    """Serialize a JSON-compatible structure to byte-exact canonical bytes.

    UTF-8, no BOM, no trailing newline, compact separators, ASCII-escaped,
    with object keys sorted by their (ASCII) byte sequence.
    """
    return _json.dumps(
        obj, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _to_jsonable(obj: object) -> Any:
    """Convert a record tree to a JSON-serializable structure."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, tuple):
        return [_to_jsonable(item) for item in obj]
    if hasattr(obj, "__dataclass_fields__"):
        result: dict[str, Any] = {}
        for field_name in obj.__dataclass_fields__:
            value = getattr(obj, field_name)
            result[field_name] = _to_jsonable(value)
        return result
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    raise ValidationEquivalenceEncodingError(
        f"cannot serialize {type(obj).__name__} to JSON"
    )


def report_to_jsonable(report: object) -> dict[str, Any]:
    """Convert a CompleteReport to a JSON-serializable dict.

    Provenance is included in the complete serialized form but excluded
    from structural_bytes used for report_id.
    """
    if hasattr(report, "__dataclass_fields__"):
        raw = _to_jsonable(report)
        if isinstance(raw, dict):
            return raw
    raise ValidationEquivalenceEncodingError(
        "report must be a CompleteReport dataclass"
    )


def structural_bytes(report: object, encoder: ReportEncoder = canonical_json) -> bytes:
    """Compute the structural projection bytes of a report.

    The structural projection excludes ``provenance`` and ``report_id``.
    """
    d = report_to_jsonable(report)
    d.pop("provenance", None)
    d.pop("report_id", None)
    try:
        return encoder(d)
    except Exception as exc:
        raise ValidationEquivalenceEncodingError(
            f"failed to encode structural projection: {exc}"
        ) from exc


def encode_report(report: object, encoder: ReportEncoder = canonical_json) -> bytes:
    """Encode the complete report to canonical bytes."""
    d = report_to_jsonable(report)
    try:
        return encoder(d)
    except ValidationEquivalenceEncodingError:
        raise
    except Exception as exc:
        raise ValidationEquivalenceEncodingError(
            f"failed to encode report: {exc}"
        ) from exc


__all__: list[str] = [
    "ReportEncoder",
    "canonical_json",
    "encode_report",
    "report_to_jsonable",
    "structural_bytes",
]
