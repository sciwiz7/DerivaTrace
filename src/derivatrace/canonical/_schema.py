from __future__ import annotations

from dataclasses import dataclass

from ._errors import CanonicalizationInputError

SUPPORTED_SCHEMA_NAME: str = "derivatrace.contract.canonical"
SUPPORTED_SCHEMA_VERSION: str = "1.0.0"

DOMAIN_CANONICAL_NODE: str = "derivatrace.canonical.node"
DOMAIN_CANONICAL_CONTRACT: str = "derivatrace.canonical.contract"


def _require_supported(condition: bool, message: str) -> None:
    if not condition:
        raise CanonicalizationInputError(message)


@dataclass(frozen=True)
class CanonicalSchemaVersion:
    """Immutable, strictly typed canonical schema identity.

    Only ``derivatrace.contract.canonical`` version ``1.0.0`` is accepted by the
    Stage 1B-R1 runtime. There is no implicit fallback to an unknown version:
    constructing any other name/version raises :class:`CanonicalizationInputError`
    at construction time.
    """

    name: str = SUPPORTED_SCHEMA_NAME
    version: str = SUPPORTED_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_supported(
            self.name == SUPPORTED_SCHEMA_NAME,
            "unsupported canonical schema name: " + str(self.name),
        )
        _require_supported(
            self.version == SUPPORTED_SCHEMA_VERSION,
            "unsupported canonical schema version: " + str(self.version),
        )

    @classmethod
    def supported(cls) -> CanonicalSchemaVersion:
        """Return the single supported Stage 1B-R1 schema version."""
        return cls(SUPPORTED_SCHEMA_NAME, SUPPORTED_SCHEMA_VERSION)


@dataclass(frozen=True)
class CanonicalizationLimits:
    """Conservative, documented complexity limits for canonicalization.

    These bound the *canonical* output (content-addressed node table and the
    final canonical byte string), independently of the Stage 1A validation
    limits that govern the input graph.
    """

    max_canonical_nodes: int = 16384
    max_canonical_bytes: int = 8_000_000

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_canonical_nodes, bool)
            or not isinstance(self.max_canonical_nodes, int)
            or self.max_canonical_nodes <= 0
        ):
            raise CanonicalizationInputError(
                "CanonicalizationLimits.max_canonical_nodes must be an int > 0"
            )
        if (
            isinstance(self.max_canonical_bytes, bool)
            or not isinstance(self.max_canonical_bytes, int)
            or self.max_canonical_bytes <= 0
        ):
            raise CanonicalizationInputError(
                "CanonicalizationLimits.max_canonical_bytes must be an int > 0"
            )

    @classmethod
    def default(cls) -> CanonicalizationLimits:
        return cls()


__all__: list[str] = [
    "DOMAIN_CANONICAL_CONTRACT",
    "DOMAIN_CANONICAL_NODE",
    "SUPPORTED_SCHEMA_NAME",
    "SUPPORTED_SCHEMA_VERSION",
    "CanonicalSchemaVersion",
    "CanonicalizationLimits",
]
