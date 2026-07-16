from __future__ import annotations

import hashlib

from ._schema import DOMAIN_PAYOFF_GRAPH, DOMAIN_PAYOFF_NODE


def _digest(domain: str, version: str, payload: bytes) -> str:
    """Domain-separated SHA-256 preimage over ``payload``.

    This is the single, private hashing seam used for every payoff-graph
    identity. The preimage framing is exactly::

        <DOMAIN> + 0x00 + <SCHEMA_VERSION> + 0x00 + <payload>

    It returns a lowercase 64-character hexadecimal digest. Tests may monkeypatch
    this function to simulate a SHA-256 collision between distinct payloads.
    """
    preimage = (
        domain.encode("ascii") + b"\x00" + version.encode("ascii") + b"\x00" + payload
    )
    return hashlib.sha256(preimage).hexdigest()


def payoff_node_identity(payload_bytes: bytes, version: str) -> str:
    """Bare 64-hex payoff-node identity for ``payload_bytes``."""
    return _digest(DOMAIN_PAYOFF_NODE, version, payload_bytes)


def payoff_graph_identity(structural_bytes: bytes, version: str) -> str:
    """Prefixed payoff-graph identity for ``structural_bytes``."""
    return "payoffgraph:sha256:" + _digest(
        DOMAIN_PAYOFF_GRAPH, version, structural_bytes
    )


__all__: list[str] = [
    "_digest",
    "payoff_graph_identity",
    "payoff_node_identity",
]
