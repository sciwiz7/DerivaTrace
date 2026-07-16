from __future__ import annotations

from dataclasses import dataclass

from ._errors import CanonicalizationInputError

SUPPORTED_SCHEMA_NAME: str = "derivatrace.contract.canonical"
SUPPORTED_SCHEMA_VERSION: str = "1.0.0"

DOMAIN_CANONICAL_NODE: str = "derivatrace.canonical.node"
DOMAIN_CANONICAL_CONTRACT: str = "derivatrace.canonical.contract"


def _validate_canonical_schema_version(schema: object) -> None:
    """Validate a CanonicalSchemaVersion at the API boundary.

    Raises CanonicalizationInputError if:
    - type(schema) is not exactly CanonicalSchemaVersion
    - type(schema.name) is not exactly str
    - type(schema.version) is not exactly str
    - schema.name != SUPPORTED_SCHEMA_NAME
    - schema.version != SUPPORTED_SCHEMA_VERSION

    The checks are ordered so the exact-type guard on ``name``/``version`` runs
    before the equality comparison: a hostile non-str that overrides ``__eq__``
    to compare equal to the supported name/version cannot bypass the type gate.
    No untrusted field value is interpolated into the error message.
    """
    if type(schema) is not CanonicalSchemaVersion:
        raise CanonicalizationInputError("schema must be a CanonicalSchemaVersion")
    if type(schema.name) is not str:
        raise CanonicalizationInputError("schema.name must be an exact str")
    if type(schema.version) is not str:
        raise CanonicalizationInputError("schema.version must be an exact str")
    if schema.name != SUPPORTED_SCHEMA_NAME:
        raise CanonicalizationInputError("unsupported canonical schema name")
    if schema.version != SUPPORTED_SCHEMA_VERSION:
        raise CanonicalizationInputError("unsupported canonical schema version")


def _validate_canonicalization_limits(limits: object) -> None:
    """Validate a CanonicalizationLimits at the API boundary.

    Raises CanonicalizationInputError if:
    - type(limits) is not exactly CanonicalizationLimits
    - max_canonical_nodes is not an exact int (not bool)
    - max_canonical_bytes is not an exact int (not bool)
    - either value is <= 0
    """
    if type(limits) is not CanonicalizationLimits:
        raise CanonicalizationInputError("limits must be a CanonicalizationLimits")
    if type(limits.max_canonical_nodes) is not int:
        raise CanonicalizationInputError(
            "CanonicalizationLimits.max_canonical_nodes must be an int > 0"
        )
    if type(limits.max_canonical_bytes) is not int:
        raise CanonicalizationInputError(
            "CanonicalizationLimits.max_canonical_bytes must be an int > 0"
        )
    if limits.max_canonical_nodes <= 0:
        raise CanonicalizationInputError(
            "CanonicalizationLimits.max_canonical_nodes must be an int > 0"
        )
    if limits.max_canonical_bytes <= 0:
        raise CanonicalizationInputError(
            "CanonicalizationLimits.max_canonical_bytes must be an int > 0"
        )


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
        _validate_canonical_schema_version(self)

    @classmethod
    def supported(cls) -> CanonicalSchemaVersion:
        """Return the single supported Stage 1B-R1 schema version."""
        return CanonicalSchemaVersion(SUPPORTED_SCHEMA_NAME, SUPPORTED_SCHEMA_VERSION)


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
        _validate_canonicalization_limits(self)

    @classmethod
    def default(cls) -> CanonicalizationLimits:
        return CanonicalizationLimits()


__all__: list[str] = [
    "DOMAIN_CANONICAL_CONTRACT",
    "DOMAIN_CANONICAL_NODE",
    "SUPPORTED_SCHEMA_NAME",
    "SUPPORTED_SCHEMA_VERSION",
    "CanonicalSchemaVersion",
    "CanonicalizationLimits",
    "_validate_canonical_schema_version",
    "_validate_canonicalization_limits",
]
