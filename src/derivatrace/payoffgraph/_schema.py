from __future__ import annotations

from dataclasses import dataclass

from ._errors import PayoffGraphInputError

SUPPORTED_SCHEMA_NAME: str = "derivatrace.payoffgraph"
SUPPORTED_SCHEMA_VERSION: str = "1.0.0"

DOMAIN_PAYOFF_NODE: str = "derivatrace.payoffgraph.node"
DOMAIN_PAYOFF_GRAPH: str = "derivatrace.payoffgraph.graph"

COMPILER_TAG: str = "derivatrace.payoffgraph.compiler/1.0.0"
PROVENANCE_KEY_COMPILER: str = "compiler"
PROVENANCE_KEY_SOURCE: str = "source_contract_identity"


def _validate_payoff_schema_version(schema: object) -> None:
    """Validate a PayoffGraphSchemaVersion at the API boundary.

    The exact-type guards run before any equality comparison so a hostile
    object that overrides ``__eq__`` cannot bypass the type gate. No untrusted
    field value is interpolated into the error message.
    """
    if type(schema) is not PayoffGraphSchemaVersion:
        raise PayoffGraphInputError("payoff schema must be a PayoffGraphSchemaVersion")
    if type(schema.name) is not str:
        raise PayoffGraphInputError("payoff schema.name must be an exact str")
    if type(schema.version) is not str:
        raise PayoffGraphInputError("payoff schema.version must be an exact str")
    if schema.name != SUPPORTED_SCHEMA_NAME:
        raise PayoffGraphInputError("unsupported payoff schema name")
    if schema.version != SUPPORTED_SCHEMA_VERSION:
        raise PayoffGraphInputError("unsupported payoff schema version")


def _validate_payoff_graph_limits(limits: object) -> None:
    """Validate a PayoffGraphLimits at the API boundary.

    Each limit must be an exact positive ``int`` (never a ``bool``). The
    structural limit must remain coherent with the document limit.
    """
    if type(limits) is not PayoffGraphLimits:
        raise PayoffGraphInputError("payoff limits must be a PayoffGraphLimits")
    if type(limits.max_payoff_nodes) is not int:
        raise PayoffGraphInputError(
            "PayoffGraphLimits.max_payoff_nodes must be an exact int"
        )
    if type(limits.max_structural_bytes) is not int:
        raise PayoffGraphInputError(
            "PayoffGraphLimits.max_structural_bytes must be an exact int"
        )
    if type(limits.max_document_bytes) is not int:
        raise PayoffGraphInputError(
            "PayoffGraphLimits.max_document_bytes must be an exact int"
        )
    if limits.max_payoff_nodes <= 0:
        raise PayoffGraphInputError(
            "PayoffGraphLimits.max_payoff_nodes must be a positive int"
        )
    if limits.max_structural_bytes <= 0:
        raise PayoffGraphInputError(
            "PayoffGraphLimits.max_structural_bytes must be a positive int"
        )
    if limits.max_document_bytes <= 0:
        raise PayoffGraphInputError(
            "PayoffGraphLimits.max_document_bytes must be a positive int"
        )
    if limits.max_structural_bytes > limits.max_document_bytes:
        raise PayoffGraphInputError(
            "payoff structural limit must not exceed the document limit"
        )


@dataclass(frozen=True)
class PayoffGraphSchemaVersion:
    """Immutable, strictly typed payoff-graph schema identity.

    Only ``derivatrace.payoffgraph`` version ``1.0.0`` is accepted by the Stage
    1B-R2 runtime. Constructing any other name/version raises
    :class:`PayoffGraphInputError` at construction time.
    """

    name: str = SUPPORTED_SCHEMA_NAME
    version: str = SUPPORTED_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_payoff_schema_version(self)

    @classmethod
    def supported(cls) -> PayoffGraphSchemaVersion:
        """Return the single supported Stage 1B-R2 schema version."""
        return PayoffGraphSchemaVersion(SUPPORTED_SCHEMA_NAME, SUPPORTED_SCHEMA_VERSION)


@dataclass(frozen=True)
class PayoffGraphLimits:
    """Conservative, documented complexity limits for payoff-graph output.

    These bound the *final reachable payoff graph*, not discarded compilation
    intermediates. Each limit is an exact positive ``int``.
    """

    max_payoff_nodes: int = 4096
    max_document_bytes: int = 4_194_304
    max_structural_bytes: int = 2_097_152

    def __post_init__(self) -> None:
        _validate_payoff_graph_limits(self)

    @classmethod
    def default(cls) -> PayoffGraphLimits:
        return PayoffGraphLimits()


__all__: list[str] = [
    "COMPILER_TAG",
    "DOMAIN_PAYOFF_GRAPH",
    "DOMAIN_PAYOFF_NODE",
    "PROVENANCE_KEY_COMPILER",
    "PROVENANCE_KEY_SOURCE",
    "SUPPORTED_SCHEMA_NAME",
    "SUPPORTED_SCHEMA_VERSION",
    "PayoffGraphLimits",
    "PayoffGraphSchemaVersion",
    "_validate_payoff_graph_limits",
    "_validate_payoff_schema_version",
]
