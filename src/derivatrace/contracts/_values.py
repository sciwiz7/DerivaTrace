from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Final

from ._errors import (
    ContractInputError,
    ContractTypeMismatchError,
)

MAX_SIGNIFICANT_DIGITS: Final[int] = 50
MAX_ABS_EXPONENT: Final[int] = 100

NAMESPACE_MAX_LEN: Final[int] = 64
IDENTIFIER_MAX_LEN: Final[int] = 128
FIELD_MAX_LEN: Final[int] = 64

_CURRENCY_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Z]{3}$", re.ASCII)
_SLUG_RE: Final[re.Pattern[str]] = re.compile(
    r"^[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?$", re.ASCII
)
_IDENTIFIER_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9._:\-/]+$", re.ASCII)


class ExactNumber:
    """Immutable, exact contractual number backed by :class:`decimal.Decimal`.

    Construction is restricted to :meth:`from_string` and :meth:`from_int` so that
    binary floating-point values can never silently enter the contract algebra.
    ``float`` and ``bool`` are explicitly rejected. Non-finite values
    (``NaN``/``Infinity``), excessive significant-digit counts and excessive
    exponents are rejected by conservative input-safety limits.
    """

    __slots__ = ("_value",)

    _value: Decimal

    def __init__(self, value: Decimal) -> None:
        # The public constructors validate and normalise; this constructor is an
        # internal helper used only by those constructors. It is immutable: the
        # slot cannot be reassigned through normal attribute assignment.
        if not isinstance(value, Decimal):
            raise ContractTypeMismatchError(
                "ExactNumber wraps a Decimal; use from_int/from_string"
            )
        if not value.is_finite():
            raise ContractInputError(
                "ExactNumber must be finite (NaN/Infinity rejected)"
            )
        if value.is_zero():
            value = Decimal(0)
        digits = value.as_tuple().digits
        if len(digits) > MAX_SIGNIFICANT_DIGITS:
            raise ContractInputError(
                f"ExactNumber has too many significant digits "
                f"(>{MAX_SIGNIFICANT_DIGITS})"
            )
        exponent = value.as_tuple().exponent
        if isinstance(exponent, int) and abs(exponent) > MAX_ABS_EXPONENT:
            raise ContractInputError(
                f"ExactNumber exponent magnitude exceeds limit (>{MAX_ABS_EXPONENT})"
            )
        object.__setattr__(self, "_value", value)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("ExactNumber is immutable")

    @classmethod
    def from_int(cls, value: int) -> ExactNumber:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ContractTypeMismatchError(
                "ExactNumber.from_int requires an int (bool is rejected)"
            )
        return cls(Decimal(value))

    @classmethod
    def from_string(cls, value: str) -> ExactNumber:
        if not isinstance(value, str):
            raise ContractTypeMismatchError("ExactNumber.from_string requires a str")
        if value != value.strip():
            raise ContractInputError(
                "ExactNumber string must not contain surrounding whitespace"
            )
        try:
            parsed = Decimal(value)
        except (ValueError, ArithmeticError) as exc:
            raise ContractInputError(
                f"ExactNumber string is not a valid decimal: {value!r}"
            ) from exc
        return cls(parsed)

    @property
    def value(self) -> Decimal:
        """Return the underlying :class:`decimal.Decimal`.

        :class:`decimal.Decimal` is immutable, so returning it directly is safe.
        """
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ExactNumber):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"ExactNumber({self._value!r})"


class Currency:
    """Immutable currency identity.

    Syntax validation only: exactly three uppercase ASCII letters. A lowercase or
    otherwise malformed code is rejected rather than silently normalised. Accepted
    codes are **not** guaranteed to be officially registered ISO currencies.
    """

    __slots__ = ("_code",)

    _code: str

    def __init__(self, code: str) -> None:
        if not isinstance(code, str):
            raise ContractTypeMismatchError("Currency requires a str")
        if not _CURRENCY_RE.match(code):
            raise ContractInputError(
                "Currency must be exactly three uppercase ASCII letters"
            )
        object.__setattr__(self, "_code", code)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Currency is immutable")

    @classmethod
    def from_code(cls, code: str) -> Currency:
        return cls(code)

    @property
    def code(self) -> str:
        return self._code

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Currency):
            return NotImplemented
        return self._code == other._code

    def __hash__(self) -> int:
        return hash(self._code)

    def __repr__(self) -> str:
        return f"Currency({self._code!r})"


class UnitKind(StrEnum):
    """The deliberately small set of unit categories supported in Stage 1A."""

    SCALAR = "scalar"
    MONEY = "money"


@dataclass(frozen=True, slots=True)
class Unit:
    """Immutable unit of measure carried by scalar expressions.

    A scalar unit carries no currency; a money unit must carry exactly one
    currency. Contradictory states are rejected.
    """

    kind: UnitKind
    currency: Currency | None

    @classmethod
    def scalar(cls) -> Unit:
        return cls(kind=UnitKind.SCALAR, currency=None)

    @classmethod
    def money(cls, currency: Currency) -> Unit:
        if not isinstance(currency, Currency):
            raise ContractTypeMismatchError("Unit.money requires a Currency")
        return cls(kind=UnitKind.MONEY, currency=currency)

    def __post_init__(self) -> None:
        if self.kind == UnitKind.SCALAR:
            if self.currency is not None:
                raise ContractInputError("scalar unit cannot carry a currency")
        elif self.kind == UnitKind.MONEY:
            if not isinstance(self.currency, Currency):
                raise ContractInputError("money unit requires a currency")
        else:
            raise ContractInputError("unknown unit kind")


class ObservableId:
    """Structured, unambiguous market-observable identity.

    Composed of a ``namespace``, an ``identifier`` and a ``field``. All parts are
    non-empty, bounded in length, and restricted to a conservative ASCII grammar.
    No market data is fetched or resolved.
    """

    __slots__ = ("field", "identifier", "namespace")

    namespace: str
    identifier: str
    field: str

    def __init__(self, namespace: str, identifier: str, field: str) -> None:
        if not isinstance(namespace, str):
            raise ContractTypeMismatchError("namespace must be a str")
        if not isinstance(identifier, str):
            raise ContractTypeMismatchError("identifier must be a str")
        if not isinstance(field, str):
            raise ContractTypeMismatchError("field must be a str")
        _check_slug(namespace, "namespace", NAMESPACE_MAX_LEN)
        _check_slug(field, "field", FIELD_MAX_LEN)
        _check_identifier(identifier, IDENTIFIER_MAX_LEN)
        object.__setattr__(self, "namespace", namespace)
        object.__setattr__(self, "identifier", identifier)
        object.__setattr__(self, "field", field)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("ObservableId is immutable")

    @classmethod
    def from_parts(cls, namespace: str, identifier: str, field: str) -> ObservableId:
        return cls(namespace=namespace, identifier=identifier, field=field)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ObservableId):
            return NotImplemented
        return (
            self.namespace == other.namespace
            and self.identifier == other.identifier
            and self.field == other.field
        )

    def __hash__(self) -> int:
        return hash((self.namespace, self.identifier, self.field))

    def __repr__(self) -> str:
        return (
            f"ObservableId(namespace={self.namespace!r}, "
            f"identifier={self.identifier!r}, field={self.field!r})"
        )


def _check_slug(value: str, name: str, max_len: int) -> None:
    if not value:
        raise ContractInputError(f"{name} must not be empty")
    if len(value) > max_len:
        raise ContractInputError(f"{name} exceeds maximum length {max_len}")
    if not _SLUG_RE.match(value):
        raise ContractInputError(
            f"{name} must be a lowercase ASCII slug (a-z0-9 with -/_)"
        )


def _check_identifier(value: str, max_len: int) -> None:
    if not value:
        raise ContractInputError("identifier must not be empty")
    if len(value) > max_len:
        raise ContractInputError(f"identifier exceeds maximum length {max_len}")
    if not _IDENTIFIER_RE.match(value):
        raise ContractInputError(
            "identifier must be conservative ASCII (A-Za-z0-9 . _ : - /)"
        )


class ObservationTime:
    """Distinct runtime type for a market observation timestamp.

    Wraps a timezone-aware :class:`datetime`, normalised to UTC. Microsecond
    precision is preserved. No calendar, holiday or day-count logic exists in
    Stage 1A.
    """

    __slots__ = ("_value",)

    _value: datetime

    def __init__(self, value: datetime) -> None:
        if not isinstance(value, datetime):
            raise ContractTypeMismatchError("ObservationTime requires datetime")
        if value.tzinfo is None:
            raise ContractInputError(
                "ObservationTime must be timezone-aware (naive rejected)"
            )
        object.__setattr__(self, "_value", value.astimezone(UTC))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("ObservationTime is immutable")

    @classmethod
    def from_datetime(cls, value: datetime) -> ObservationTime:
        return cls(value)

    @property
    def value(self) -> datetime:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ObservationTime):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"ObservationTime({self._value.isoformat()})"


class SettlementTime:
    """Distinct runtime type for a cash-settlement timestamp.

    Kept as a separate type from :class:`ObservationTime` so the two cannot be
    substituted silently. Same UTC-normalisation and precision guarantees.
    """

    __slots__ = ("_value",)

    _value: datetime

    def __init__(self, value: datetime) -> None:
        if not isinstance(value, datetime):
            raise ContractTypeMismatchError("SettlementTime requires datetime")
        if value.tzinfo is None:
            raise ContractInputError(
                "SettlementTime must be timezone-aware (naive rejected)"
            )
        object.__setattr__(self, "_value", value.astimezone(UTC))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("SettlementTime is immutable")

    @classmethod
    def from_datetime(cls, value: datetime) -> SettlementTime:
        return cls(value)

    @property
    def value(self) -> datetime:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SettlementTime):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"SettlementTime({self._value.isoformat()})"


@dataclass(frozen=True, slots=True)
class ValidationLimits:
    """Conservative, documented complexity limits for contract validation."""

    max_depth: int = 64
    max_unique_nodes: int = 4096

    def __post_init__(self) -> None:
        if not isinstance(self.max_depth, int) or self.max_depth <= 0:
            raise ContractInputError("ValidationLimits.max_depth must be > 0")
        if not isinstance(self.max_unique_nodes, int) or self.max_unique_nodes <= 0:
            raise ContractInputError("ValidationLimits.max_unique_nodes must be > 0")

    @classmethod
    def default(cls) -> ValidationLimits:
        return cls(max_depth=64, max_unique_nodes=4096)


@dataclass(frozen=True, slots=True)
class ContractMetrics:
    """Deterministic metrics produced by :func:`validate_contract`."""

    node_count: int
    max_depth: int


__all__: list[str] = [
    "ContractMetrics",
    "Currency",
    "ExactNumber",
    "ObservableId",
    "ObservationTime",
    "SettlementTime",
    "Unit",
    "UnitKind",
    "ValidationLimits",
]
