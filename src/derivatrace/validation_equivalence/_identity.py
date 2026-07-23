from __future__ import annotations

from ._errors import ValidationEquivalenceReportCollisionError
from ._schema import DOMAIN_REPORT, REPORT_ID_PREFIX, SUPPORTED_REPORT_SCHEMA_VERSION


def _digest(domain: str, version: str, payload: bytes) -> str:
    """Domain-separated SHA-256 preimage over ``payload``.

    This is the single, private hashing seam used for every report identity.
    The preimage framing is exactly::

        <DOMAIN> + 0x00 + <SCHEMA_VERSION> + 0x00 + <payload>

    It returns a lowercase 64-character hexadecimal digest. Tests may
    monkeypatch this function to simulate a SHA-256 collision between
    distinct payloads.
    """
    import hashlib

    preimage = (
        domain.encode("ascii") + b"\x00" + version.encode("ascii") + b"\x00" + payload
    )
    return hashlib.sha256(preimage).hexdigest()


def report_identity(structural_bytes: bytes) -> str:
    """Prefixed validation-equivalence report identity."""
    return REPORT_ID_PREFIX + _digest(
        DOMAIN_REPORT, SUPPORTED_REPORT_SCHEMA_VERSION, structural_bytes
    )


def _validate_report_format(result: str) -> None:
    """Validate that *result* has the exact report-identity format.

    Checks prefix, total length and hex suffix.  Raises
    ``ValidationEquivalenceReportCollisionError`` on any mismatch.
    """
    if not (
        result[:30] == "validation-equivalence:sha256:"
        and len(result) == 94
        and all(c in "0123456789abcdef" for c in result[30:])
    ):
        raise ValidationEquivalenceReportCollisionError(
            "failed to produce report identity"
        )


def _safe_report_identity(structural_bytes: bytes) -> str:
    """Single private helper for report identity with strict error handling.

    Validates structural_bytes is bytes, calls report_identity via the private
    digest seam, validates the output is exactly ``str`` with the correct
    prefix, length and hex suffix, and normalizes all exceptions into
    ValidationEquivalenceReportCollisionError with exact message.
    """
    if type(structural_bytes) is not bytes:
        raise ValidationEquivalenceReportCollisionError(
            "failed to produce report identity"
        )
    try:
        result = report_identity(structural_bytes)
    except Exception as exc:
        raise ValidationEquivalenceReportCollisionError(
            "failed to produce report identity"
        ) from exc
    try:
        if type(result) is not str:
            raise ValidationEquivalenceReportCollisionError(
                "failed to produce report identity"
            )
        _validate_report_format(result)
    except ValidationEquivalenceReportCollisionError:
        raise
    except Exception as exc:
        raise ValidationEquivalenceReportCollisionError(
            "failed to produce report identity"
        ) from exc
    return result


__all__: list[str] = [
    "_digest",
    "_safe_report_identity",
    "_validate_report_format",
    "report_identity",
]
