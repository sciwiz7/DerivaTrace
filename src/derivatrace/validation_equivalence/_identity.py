from __future__ import annotations

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


__all__: list[str] = ["_digest", "report_identity"]
