from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    os.environ.get("DG_TEST_PACKAGING") != "1",
    reason="Set DG_TEST_PACKAGING=1 to build and validate wheel/sdist inventories.",
)

pytest.importorskip("build")

CONTRACTS_MODULES = [
    "src/derivatrace/contracts/__init__.py",
    "src/derivatrace/contracts/_errors.py",
    "src/derivatrace/contracts/_values.py",
    "src/derivatrace/contracts/_expressions.py",
    "src/derivatrace/contracts/_contracts.py",
    "src/derivatrace/contracts/_validation.py",
]

CONTRACT_TESTS = [
    "tests/contracts/test_values.py",
    "tests/contracts/test_expressions.py",
    "tests/contracts/test_contracts.py",
    "tests/contracts/test_validation.py",
    "tests/contracts/test_validation_coverage.py",
    "tests/contracts/test_values_extra.py",
    "tests/contracts/test_public_api.py",
    "tests/contracts/test_supported_node_policy.py",
]

REQUIRED_SDIST_PATHS = [
    "src/derivatrace/__init__.py",
    "src/derivatrace/_metadata.py",
    "src/derivatrace/py.typed",
    *CONTRACTS_MODULES,
    "tests/test_package.py",
    "tests/test_documentation.py",
    *CONTRACT_TESTS,
    "docs/index.md",
    "docs/vision.md",
    "docs/product-spec.md",
    "docs/architecture.md",
    "docs/contract-semantics.md",
    "docs/contract-api.md",
    "docs/certificate-spec.md",
    "docs/threat-model.md",
    "docs/glossary.md",
    "docs/adr/0001-separation-of-contract-model-engine.md",
    "docs/adr/0002-deterministic-canonicalization.md",
    "docs/adr/0003-evidence-carrying-results.md",
    "docs/adr/0004-exact-contract-terms-and-numerical-boundaries.md",
    "docs/adr/0005-no-hidden-model-selection.md",
    "docs/adr/0006-stage-1-contract-algebra-and-runtime-type-system.md",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "ROADMAP.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "GOVERNANCE.md",
    "pyproject.toml",
    ".editorconfig",
    ".pre-commit-config.yaml",
    ".github/workflows/ci.yml",
]

FORBIDDEN_SDIST_SUBSTRINGS = (
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".coverage",
    "htmlcov",
    ".venv",
    ".egg-info",
    "/dist/",
    "/build/",
)


@pytest.fixture(scope="module")
def artifacts(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("artifacts")
    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(out), str(REPO_ROOT)],
        check=True,
        capture_output=True,
        text=True,
    )
    return out


def test_distribution_installed() -> None:
    from importlib.metadata import PackageNotFoundError, version

    try:
        installed = version("derivatrace")
    except PackageNotFoundError:
        pytest.fail(
            "derivatrace is not installed as a distribution; pytest must exercise "
            "the installed package rather than source-path injection (src)."
        )
    assert installed == "0.1.0.dev0"


def test_wheel_inventory(artifacts: Path) -> None:
    wheel = next(artifacts.glob("*.whl"))
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
    for name in names:
        assert name.startswith("derivatrace/") or name.startswith(
            "derivatrace-0.1.0.dev0.dist-info/"
        ), f"unexpected wheel entry: {name}"
    assert "derivatrace/py.typed" in names
    assert "derivatrace/__init__.py" in names
    assert "derivatrace/_metadata.py" in names
    # The complete contracts package must ship in the wheel.
    for module in CONTRACTS_MODULES:
        assert f"derivatrace/{module.split('src/derivatrace/')[1]}" in names
    # No tests, docs, caches or generated files belong in the wheel.
    for name in names:
        assert not name.startswith("tests/")
        assert not name.startswith("docs/")
        assert ".pyc" not in name
        assert "__pycache__" not in name


def test_sdist_inventory(artifacts: Path) -> None:
    sdist = next(artifacts.glob("*.tar.gz"))
    with tarfile.open(sdist) as tf:
        names = tf.getnames()
    stripped = {n.split("/", 1)[1] if "/" in n else n for n in names}
    missing = [p for p in REQUIRED_SDIST_PATHS if p not in stripped]
    assert not missing, f"missing from sdist: {missing}"
    bad = [
        n for n in names for forbidden in FORBIDDEN_SDIST_SUBSTRINGS if forbidden in n
    ]
    assert not bad, f"forbidden content in sdist: {bad}"
