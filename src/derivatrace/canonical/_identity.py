from __future__ import annotations

from ._schema import DOMAIN_CANONICAL_CONTRACT, DOMAIN_CANONICAL_NODE


def _digest(domain: str, version: str, payload: bytes) -> str:
    """Domain-separated SHA-256 preimage over ``payload``.

    This is the single, private hashing seam used for every canonical identity.
    The preimage framing is exactly::

        <DOMAIN> + 0x00 + <SCHEMA_VERSION> + 0x00 + <payload>

    It returns a lowercase 64-character hexadecimal digest. Tests may monkeypatch
    this function to simulate a SHA-256 collision between distinct payloads.
    """
    import hashlib

    preimage = (
        domain.encode("ascii") + b"\x00" + version.encode("ascii") + b"\x00" + payload
    )
    return hashlib.sha256(preimage).hexdigest()


def node_identity(payload_bytes: bytes, version: str) -> str:
    """Bare 64-hex canonical node identity for ``payload_bytes``."""
    return _digest(DOMAIN_CANONICAL_NODE, version, payload_bytes)


def contract_identity(document_bytes: bytes, version: str) -> str:
    """Prefixed canonical contract identity for ``document_bytes``."""
    return "canonical:sha256:" + _digest(
        DOMAIN_CANONICAL_CONTRACT, version, document_bytes
    )


__all__: list[str] = ["_digest", "contract_identity", "node_identity"]
