from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ._errors import (
    ContractInputError,
    ContractTypeMismatchError,
)
from ._values import (
    ExactNumber,
    ObservableId,
    ObservationTime,
    Unit,
    UnitKind,
)


class ScalarExpression:
    """Abstract base for scalar (numeric) expression nodes.

    Concrete nodes are immutable and carry an explicit :class:`Unit`. Runtime
    boundaries are enforced by every constructor; static typing alone is not
    sufficient.
    """

    __slots__ = ()
    unit: Unit


class BooleanExpression:
    """Abstract base for boolean expression nodes."""

    __slots__ = ()


def _require_scalar(node: object, name: str) -> None:
    if not isinstance(node, ScalarExpression):
        raise ContractTypeMismatchError(f"{name} must be a ScalarExpression")


def _require_boolean(node: object, name: str) -> None:
    if not isinstance(node, BooleanExpression):
        raise ContractTypeMismatchError(f"{name} must be a BooleanExpression")


def _require_same_unit(a: Unit, b: Unit, name: str) -> None:
    if a != b:
        raise ContractInputError(
            f"{name}: operand units must match ({a.kind.value} vs {b.kind.value})"
        )


def _multiply_unit(a: Unit, b: Unit) -> Unit:
    if a.kind == UnitKind.MONEY and b.kind == UnitKind.MONEY:
        raise ContractInputError("Multiply rejects money x money in Stage 1A")
    if a.kind == UnitKind.MONEY:
        return a
    if b.kind == UnitKind.MONEY:
        return b
    return Unit.scalar()


def _validate_scalar_operands(operands: object, name: str) -> Unit:
    if not isinstance(operands, tuple):
        raise ContractTypeMismatchError(f"{name} must be a tuple")
    if len(operands) < 2:
        raise ContractInputError(f"{name} requires at least two operands")
    first_unit: Unit | None = None
    for index, operand in enumerate(operands):
        if not isinstance(operand, ScalarExpression):
            raise ContractTypeMismatchError(
                f"{name}[{index}] must be a ScalarExpression"
            )
        if first_unit is None:
            first_unit = operand.unit
        elif operand.unit != first_unit:
            raise ContractInputError(
                f"{name}[{index}] unit mismatch with earlier operand"
            )
    assert first_unit is not None
    return first_unit


def _validate_boolean_operands(operands: object, name: str) -> None:
    if not isinstance(operands, tuple):
        raise ContractTypeMismatchError(f"{name} must be a tuple")
    if len(operands) < 2:
        raise ContractInputError(f"{name} requires at least two operands")
    for index, operand in enumerate(operands):
        if not isinstance(operand, BooleanExpression):
            raise ContractTypeMismatchError(
                f"{name}[{index}] must be a BooleanExpression"
            )


# ---------------------------------------------------------------------------
# Scalar leaf nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Number(ScalarExpression):
    """A literal scalar value: an :class:`ExactNumber` with an explicit unit."""

    value: ExactNumber
    unit: Unit

    def __post_init__(self) -> None:
        if not isinstance(self.value, ExactNumber):
            raise ContractTypeMismatchError("Number.value must be ExactNumber")
        if not isinstance(self.unit, Unit):
            raise ContractTypeMismatchError("Number.unit must be Unit")


@dataclass(frozen=True, slots=True)
class Observable(ScalarExpression):
    """A reference to a market observable by structured identity.

    Carries no market value and performs no lookup.
    """

    observable_id: ObservableId
    observation_time: ObservationTime
    unit: Unit

    def __post_init__(self) -> None:
        if not isinstance(self.observable_id, ObservableId):
            raise ContractTypeMismatchError(
                "Observable.observable_id must be ObservableId"
            )
        if not isinstance(self.observation_time, ObservationTime):
            raise ContractTypeMismatchError(
                "Observable.observation_time must be ObservationTime"
            )
        if not isinstance(self.unit, Unit):
            raise ContractTypeMismatchError("Observable.unit must be Unit")


# ---------------------------------------------------------------------------
# Scalar arithmetic nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Add(ScalarExpression):
    """Sum of two or more scalar expressions with identical units."""

    operands: tuple[ScalarExpression, ...]
    unit: Unit = field(init=False)

    def __post_init__(self) -> None:
        unit = _validate_scalar_operands(self.operands, "Add.operands")
        object.__setattr__(self, "unit", unit)


@dataclass(frozen=True, slots=True)
class Subtract(ScalarExpression):
    """Difference of two scalar expressions with identical units."""

    minuend: ScalarExpression
    subtrahend: ScalarExpression
    unit: Unit = field(init=False)

    def __post_init__(self) -> None:
        _require_scalar(self.minuend, "Subtract.minuend")
        _require_scalar(self.subtrahend, "Subtract.subtrahend")
        _require_same_unit(self.minuend.unit, self.subtrahend.unit, "Subtract")
        object.__setattr__(self, "unit", self.minuend.unit)


@dataclass(frozen=True, slots=True)
class Multiply(ScalarExpression):
    """Product of two scalar expressions.

    Allows scalar x scalar, scalar x money, money x scalar. Rejects money x
    money in Stage 1A.
    """

    left: ScalarExpression
    right: ScalarExpression
    unit: Unit = field(init=False)

    def __post_init__(self) -> None:
        _require_scalar(self.left, "Multiply.left")
        _require_scalar(self.right, "Multiply.right")
        unit = _multiply_unit(self.left.unit, self.right.unit)
        object.__setattr__(self, "unit", unit)


@dataclass(frozen=True, slots=True)
class Divide(ScalarExpression):
    """Quotient of two scalar expressions.

    The denominator must be dimensionless; the numerator unit is preserved.
    A literal zero denominator (a :class:`Number` whose value is zero) is
    rejected. Symbolic zero detection is not attempted.
    """

    numerator: ScalarExpression
    denominator: ScalarExpression
    unit: Unit = field(init=False)

    def __post_init__(self) -> None:
        _require_scalar(self.numerator, "Divide.numerator")
        _require_scalar(self.denominator, "Divide.denominator")
        if self.denominator.unit.kind != UnitKind.SCALAR:
            raise ContractInputError("Divide denominator must be dimensionless")
        if isinstance(self.denominator, Number) and self.denominator.value.value == 0:
            raise ContractInputError("Divide rejects a literal zero denominator")
        object.__setattr__(self, "unit", self.numerator.unit)


@dataclass(frozen=True, slots=True)
class Negate(ScalarExpression):
    """Arithmetic negation; preserves the operand unit."""

    operand: ScalarExpression
    unit: Unit = field(init=False)

    def __post_init__(self) -> None:
        _require_scalar(self.operand, "Negate.operand")
        object.__setattr__(self, "unit", self.operand.unit)


@dataclass(frozen=True, slots=True)
class Maximum(ScalarExpression):
    """Maximum of two or more scalar expressions with identical units."""

    operands: tuple[ScalarExpression, ...]
    unit: Unit = field(init=False)

    def __post_init__(self) -> None:
        unit = _validate_scalar_operands(self.operands, "Maximum.operands")
        object.__setattr__(self, "unit", unit)


@dataclass(frozen=True, slots=True)
class Minimum(ScalarExpression):
    """Minimum of two or more scalar expressions with identical units."""

    operands: tuple[ScalarExpression, ...]
    unit: Unit = field(init=False)

    def __post_init__(self) -> None:
        unit = _validate_scalar_operands(self.operands, "Minimum.operands")
        object.__setattr__(self, "unit", unit)


@dataclass(frozen=True, slots=True)
class ConditionalValue(ScalarExpression):
    """A scalar chosen by a boolean condition (both branches share a unit)."""

    condition: BooleanExpression
    true_value: ScalarExpression
    false_value: ScalarExpression
    unit: Unit = field(init=False)

    def __post_init__(self) -> None:
        _require_boolean(self.condition, "ConditionalValue.condition")
        _require_scalar(self.true_value, "ConditionalValue.true_value")
        _require_scalar(self.false_value, "ConditionalValue.false_value")
        _require_same_unit(
            self.true_value.unit,
            self.false_value.unit,
            "ConditionalValue",
        )
        object.__setattr__(self, "unit", self.true_value.unit)


# ---------------------------------------------------------------------------
# Boolean nodes
# ---------------------------------------------------------------------------


class ComparisonOperator(Enum):
    """Named comparison operators for :class:`Comparison`."""

    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    EQUAL = "=="
    NOT_EQUAL = "!="
    GREATER_THAN_OR_EQUAL = ">="
    GREATER_THAN = ">"


@dataclass(frozen=True, slots=True)
class BooleanConstant(BooleanExpression):
    """A literal boolean constant."""

    value: bool

    def __post_init__(self) -> None:
        if not isinstance(self.value, bool):
            raise ContractTypeMismatchError(
                "BooleanConstant.value must be a bool (int is rejected)"
            )


@dataclass(frozen=True, slots=True)
class Comparison(BooleanExpression):
    """A comparison between two scalar expressions of identical units."""

    left: ScalarExpression
    right: ScalarExpression
    operator: ComparisonOperator

    def __post_init__(self) -> None:
        _require_scalar(self.left, "Comparison.left")
        _require_scalar(self.right, "Comparison.right")
        if not isinstance(self.operator, ComparisonOperator):
            raise ContractTypeMismatchError(
                "Comparison.operator must be ComparisonOperator"
            )
        _require_same_unit(self.left.unit, self.right.unit, "Comparison")


@dataclass(frozen=True, slots=True)
class AllOf(BooleanExpression):
    """Conjunction of two or more boolean expressions."""

    operands: tuple[BooleanExpression, ...]

    def __post_init__(self) -> None:
        _validate_boolean_operands(self.operands, "AllOf.operands")


@dataclass(frozen=True, slots=True)
class AnyOf(BooleanExpression):
    """Disjunction of two or more boolean expressions."""

    operands: tuple[BooleanExpression, ...]

    def __post_init__(self) -> None:
        _validate_boolean_operands(self.operands, "AnyOf.operands")


@dataclass(frozen=True, slots=True)
class Not(BooleanExpression):
    """Logical negation of a single boolean expression."""

    operand: BooleanExpression

    def __post_init__(self) -> None:
        _require_boolean(self.operand, "Not.operand")


__all__: list[str] = [
    "Add",
    "AllOf",
    "AnyOf",
    "BooleanConstant",
    "BooleanExpression",
    "Comparison",
    "ComparisonOperator",
    "ConditionalValue",
    "Divide",
    "Maximum",
    "Minimum",
    "Multiply",
    "Negate",
    "Not",
    "Number",
    "Observable",
    "ScalarExpression",
    "Subtract",
]
