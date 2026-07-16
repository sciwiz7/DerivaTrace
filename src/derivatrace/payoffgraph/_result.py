from __future__ import annotations

from dataclasses import dataclass

from ._errors import PayoffGraphInputError
from ._schema import SUPPORTED_SCHEMA_VERSION

_ID_PREFIX: str = "payoffgraph:sha256:"
_SOURCE_PREFIX: str = "canonical:sha256:"
_HEX_DIGITS: frozenset[str] = frozenset("0123456789abcdef")


def _check_hex64(value: str, label: str) -> None:
    if type(value) is not str:
        raise PayoffGraphInputError(f"{label} must be an exact str")
    if len(value) != 64:
        raise PayoffGraphInputError(f"{label} must be a 64-character lowercase hex id")
    for ch in value:
        if ch not in _HEX_DIGITS:
            raise PayoffGraphInputError(
                f"{label} must be a 64-character lowercase hex id"
            )


def _check_source_identity(value: str) -> None:
    # source_contract_identity is exactly `canonical:sha256:<64-lowercase-hex>`,
    # mirroring the canonical contract identity produced by derivatrace.canonical.
    # The malformed value is never interpolated into the raised message.
    if type(value) is not str:
        raise PayoffGraphInputError("source_contract_identity must be an exact str")
    if not value.startswith(_SOURCE_PREFIX):
        raise PayoffGraphInputError(
            "source_contract_identity must be a canonical:sha256 id"
        )
    _check_hex64(value[len(_SOURCE_PREFIX) :], "source_contract_identity")


@dataclass(frozen=True, slots=True)
class PayoffGraph:
    """Immutable result of compiling a contract into a payoff graph.

    Equality and hashing are based on the **payoff-graph identity** (a
    structural fingerprint under the approved Stage 1B-R2 laws). Two
    ``PayoffGraph`` values are equal exactly when they carry the same identity,
    which is the precise notion of structural payoff-graph equivalence. They are
    deliberately *not* equal under incidental differences in ``document_bytes``
    (which includes provenance).

    Instances expose only safe, deterministic, immutable data. All byte fields
    are immutable ``bytes``; no mutable dictionary is exposed through the
    result.
    """

    schema_version: str
    document_bytes: bytes
    structural_bytes: bytes
    identity: str
    root_node_id: str
    node_count: int
    source_contract_identity: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str:
            raise PayoffGraphInputError("schema_version must be an exact str")
        if self.schema_version != SUPPORTED_SCHEMA_VERSION:
            raise PayoffGraphInputError("unsupported payoff schema version")
        if type(self.document_bytes) is not bytes:
            raise PayoffGraphInputError("document_bytes must be exact bytes")
        if type(self.structural_bytes) is not bytes:
            raise PayoffGraphInputError("structural_bytes must be exact bytes")
        if type(self.identity) is not str or not self.identity.startswith(_ID_PREFIX):
            raise PayoffGraphInputError("identity must be a payoffgraph:sha256 id")
        _check_hex64(self.identity[len(_ID_PREFIX) :], "identity")
        _check_hex64(self.root_node_id, "root_node_id")
        if type(self.node_count) is not int or self.node_count < 1:
            raise PayoffGraphInputError("node_count must be a positive int")
        _check_source_identity(self.source_contract_identity)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PayoffGraph):
            return NotImplemented
        return self.identity == other.identity

    def __hash__(self) -> int:
        return hash(self.identity)

    def __repr__(self) -> str:
        return f"PayoffGraph(identity={self.identity!r}, node_count={self.node_count})"


__all__: list[str] = ["PayoffGraph"]
