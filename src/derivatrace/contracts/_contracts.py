from __future__ import annotations

from dataclasses import dataclass

from ._errors import (
    ContractInputError,
    ContractTypeMismatchError,
)
from ._expressions import (
    BooleanExpression,
    ScalarExpression,
    _require_boolean,
    _require_scalar,
)
from ._values import (
    Currency,
    SettlementTime,
    UnitKind,
)


class Contract:
    """Abstract base for contract nodes.

    A contract declares *what is paid* under what conditions. It contains no
    stochastic model, pricing logic, or numerical-engine behaviour.
    """

    __slots__ = ()


def _require_contract(node: object, name: str) -> None:
    if not isinstance(node, Contract):
        raise ContractTypeMismatchError(f"{name} must be a Contract")


@dataclass(frozen=True, slots=True)
class Zero(Contract):
    """A contract with no obligations."""


@dataclass(frozen=True, slots=True)
class Payment(Contract):
    """A dated cash flow of an explicit amount and currency.

    The amount must be a money scalar expression denominated in the same
    currency as the payment. The payment is never evaluated or priced here.
    """

    amount: ScalarExpression
    currency: Currency
    settlement_time: SettlementTime

    def __post_init__(self) -> None:
        _require_scalar(self.amount, "Payment.amount")
        if not isinstance(self.currency, Currency):
            raise ContractTypeMismatchError("Payment.currency must be Currency")
        if not isinstance(self.settlement_time, SettlementTime):
            raise ContractTypeMismatchError(
                "Payment.settlement_time must be SettlementTime"
            )
        if self.amount.unit.kind != UnitKind.MONEY:
            raise ContractInputError("Payment amount must be money-denominated")
        if (
            self.amount.unit.currency is None
            or self.amount.unit.currency != self.currency
        ):
            raise ContractInputError("Payment currency mismatch")


@dataclass(frozen=True, slots=True)
class Both(Contract):
    """Combination of two or more contracts, preserving author order.

    No flattening or normalization is performed in Stage 1A.
    """

    operands: tuple[Contract, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.operands, tuple):
            raise ContractTypeMismatchError("Both.operands must be a tuple")
        if len(self.operands) < 2:
            raise ContractInputError("Both requires at least two contracts")
        for index, operand in enumerate(self.operands):
            if not isinstance(operand, Contract):
                raise ContractTypeMismatchError(
                    f"Both.operands[{index}] must be a Contract"
                )


@dataclass(frozen=True, slots=True)
class Scale(Contract):
    """Scale a contract by a dimensionless scalar factor.

    The multiplication is not evaluated here.
    """

    factor: ScalarExpression
    contract: Contract

    def __post_init__(self) -> None:
        _require_scalar(self.factor, "Scale.factor")
        _require_contract(self.contract, "Scale.contract")
        if self.factor.unit.kind != UnitKind.SCALAR:
            raise ContractInputError("Scale factor must be dimensionless")


@dataclass(frozen=True, slots=True)
class ConditionalContract(Contract):
    """Choose a contract based on a boolean condition.

    The condition is not evaluated here.
    """

    condition: BooleanExpression
    true_contract: Contract
    false_contract: Contract

    def __post_init__(self) -> None:
        _require_boolean(self.condition, "ConditionalContract.condition")
        _require_contract(self.true_contract, "ConditionalContract.true_contract")
        _require_contract(self.false_contract, "ConditionalContract.false_contract")


__all__: list[str] = [
    "Both",
    "ConditionalContract",
    "Contract",
    "Payment",
    "Scale",
    "Zero",
]
