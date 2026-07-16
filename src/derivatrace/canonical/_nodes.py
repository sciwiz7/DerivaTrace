from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._schema import CanonicalSchemaVersion


@dataclass(frozen=True)
class _CanonicalNode:
    """Immutable internal representation of a single canonical node.

    Holds the node's canonical payload (a JSON-ready dict) and the exact
    canonical payload bytes it serializes to. The payload is never mutated
    after construction.
    """

    payload: dict[str, Any]
    payload_bytes: bytes


@dataclass(frozen=True, eq=False)
class CanonicalContract:
    """Immutable result of canonicalizing a Stage 1A contract.

    Equality and hashing are based on the **canonical contract identity** (a
    structural fingerprint under the approved Stage 1B-R1 laws). Two
    ``CanonicalContract`` values are equal exactly when they carry the same
    identity, which is the precise notion of structural canonical equivalence.
    They are deliberately *not* equal under incidental differences in derived
    fields such as byte length; the identity already subsumes the complete
    canonical document.

    Instances expose only safe, deterministic, immutable data:

    * ``schema_version`` — the canonical schema identity used.
    * ``canonical_bytes`` — the byte-exact canonical document (``bytes`` are immutable).
    * ``identity`` — the prefixed SHA-256 canonical contract identity.
    * ``root_node_id`` — the bare 64-hex canonical id of the root node.
    * ``node_count`` — the number of canonical nodes in the (pruned) table.
    """

    schema_version: CanonicalSchemaVersion
    canonical_bytes: bytes
    identity: str
    root_node_id: str
    node_count: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CanonicalContract):
            return NotImplemented
        return self.identity == other.identity

    def __hash__(self) -> int:
        return hash(self.identity)

    def __repr__(self) -> str:
        return (
            f"CanonicalContract(identity={self.identity!r}, "
            f"node_count={self.node_count})"
        )


__all__: list[str] = ["CanonicalContract", "_CanonicalNode"]
