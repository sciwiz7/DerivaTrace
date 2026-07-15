from __future__ import annotations

from typing import Final

Path = tuple[str | int, ...]


def format_path(path: Path) -> str:
    """Render a structural path as a stable, human-readable string.

    The path never contains the ``repr`` of any untrusted node, only the
    structural labels supplied by the traversal.
    """
    if not path:
        return "<root>"
    return ".".join(str(segment) for segment in path)


class DerivaTraceError(Exception):
    """Base class for all DerivaTrace errors.

    Every error carries a stable, machine-readable ``code`` and an optional
    immutable structural ``path``. Messages are human-readable and never embed
    filesystem paths, secrets, or the ``repr`` of untrusted nodes.
    """

    code: str = "derivatrace.error"

    def __init__(self, message: str, *, path: Path | None = None) -> None:
        self.path: Path | None = tuple(path) if path is not None else None
        super().__init__(message)

    def __str__(self) -> str:
        base = super().__str__()
        if self.path:
            return f"{self.code}: {base} (path: {format_path(self.path)})"
        return f"{self.code}: {base}"


class ContractError(DerivaTraceError):
    """Base class for contract-related errors."""

    code: str = "contract.error"


class ContractInputError(ContractError):
    """Raised during construction of a single node for malformed input.

    These failures happen while building a value object or AST node from
    caller-supplied arguments, before any whole-contract graph validation.
    """

    code: str = "contract.input"


class ContractTypeMismatchError(ContractInputError):
    """Raised when an argument has the wrong runtime type."""

    code: str = "contract.input.type_mismatch"


class ContractValidationError(ContractError):
    """Raised during whole-contract graph validation.

    These failures happen while traversing and re-checking the complete contract
    graph, including objects that may have been forged or modified after
    construction to bypass constructor invariants.
    """

    code: str = "contract.validation"


class ContractCycleError(ContractValidationError):
    """Raised when the contract graph contains a reference cycle."""

    code: str = "contract.validation.cycle"


class ContractComplexityError(ContractValidationError):
    """Raised when the contract graph exceeds a configured complexity limit."""

    code: str = "contract.validation.complexity"


_UNEXPECTED_MESSAGE: Final[str] = "unexpected internal error"
