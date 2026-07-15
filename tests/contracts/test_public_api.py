from __future__ import annotations

import importlib

import derivatrace
import derivatrace.contracts
from derivatrace.contracts import __all__ as PUBLIC_NAMES

EXPECTED_PUBLIC_NAMES = frozenset(
    {
        "Add",
        "AllOf",
        "AnyOf",
        "BooleanConstant",
        "Both",
        "Comparison",
        "ComparisonOperator",
        "ConditionalContract",
        "ConditionalValue",
        "Contract",
        "ContractComplexityError",
        "ContractCycleError",
        "ContractError",
        "ContractInputError",
        "ContractMetrics",
        "ContractTypeMismatchError",
        "ContractValidationError",
        "Currency",
        "DerivaTraceError",
        "Divide",
        "ExactNumber",
        "Maximum",
        "Minimum",
        "Multiply",
        "Negate",
        "Not",
        "Number",
        "Observable",
        "ObservableId",
        "ObservationTime",
        "Payment",
        "ScalarExpression",
        "SettlementTime",
        "Scale",
        "Subtract",
        "Unit",
        "UnitKind",
        "ValidationLimits",
        "Zero",
        "validate_contract",
    }
)


def test_all_expected_public_names_present() -> None:
    assert set(PUBLIC_NAMES) >= EXPECTED_PUBLIC_NAMES


def test_no_private_helpers_leak() -> None:
    for name in PUBLIC_NAMES:
        assert not name.startswith("_"), name


def test_private_submodules_not_in_all() -> None:
    for private in ("_errors", "_values", "_expressions", "_contracts", "_validation"):
        assert private not in PUBLIC_NAMES


def test_private_helpers_not_importable_from_package() -> None:
    for helper in ("_multiply_unit", "_validate_node_invariants", "format_path"):
        assert not hasattr(derivatrace.contracts, helper), helper


def test_every_public_name_importable() -> None:
    for name in PUBLIC_NAMES:
        assert hasattr(derivatrace.contracts, name), name


def test_root_package_exports_remain_deliberate() -> None:
    # The root package must not silently re-export the contract API.
    assert "validate_contract" not in derivatrace.__all__
    assert not hasattr(derivatrace, "validate_contract")
    assert derivatrace.__all__ == [
        "ProjectMetadata",
        "__version__",
        "project_metadata",
    ]


def test_py_typed_marker_present() -> None:
    import pathlib

    marker = pathlib.Path(derivatrace.__file__).resolve().parent / "py.typed"
    assert marker.is_file(), "py.typed must remain present in the package"


def test_package_metadata_unchanged() -> None:
    assert derivatrace.__version__ == "0.1.0.dev0"


def test_contracts_module_importable() -> None:
    mod = importlib.import_module("derivatrace.contracts")
    assert mod is derivatrace.contracts
