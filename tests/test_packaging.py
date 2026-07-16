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

# The complete Stage 1B-R1 canonical runtime package (every intended module).
CANONICAL_MODULES = [
    "src/derivatrace/canonical/__init__.py",
    "src/derivatrace/canonical/_encoding.py",
    "src/derivatrace/canonical/_equivalence.py",
    "src/derivatrace/canonical/_errors.py",
    "src/derivatrace/canonical/_identity.py",
    "src/derivatrace/canonical/_nodes.py",
    "src/derivatrace/canonical/_normalization.py",
    "src/derivatrace/canonical/_schema.py",
    "src/derivatrace/canonical/_serialization.py",
    "src/derivatrace/canonical/py.typed",
]

# Every intended canonical test module (must ship in the sdist, never the wheel).
CANONICAL_TESTS = [
    "tests/canonical/test_api_surface.py",
    "tests/canonical/test_coverage.py",
    "tests/canonical/test_encoding.py",
    "tests/canonical/test_equivalence.py",
    "tests/canonical/test_errors.py",
    "tests/canonical/test_folding.py",
    "tests/canonical/test_vectors.py",
]

# Canonical documentation / specs that must remain in the sdist.
CANONICAL_DOCS = [
    "docs/canonicalization-spec.md",
    "docs/payoff-graph-spec.md",
    "docs/canonical-test-vectors.md",
    "docs/adr/0007-canonical-contract-identity-and-payoff-graph.md",
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
    "docs/canonicalization-spec.md",
    "docs/payoff-graph-spec.md",
    "docs/canonical-test-vectors.md",
    "docs/adr/0001-separation-of-contract-model-engine.md",
    "docs/adr/0002-deterministic-canonicalization.md",
    "docs/adr/0003-evidence-carrying-results.md",
    "docs/adr/0004-exact-contract-terms-and-numerical-boundaries.md",
    "docs/adr/0005-no-hidden-model-selection.md",
    "docs/adr/0006-stage-1-contract-algebra-and-runtime-type-system.md",
    "docs/adr/0007-canonical-contract-identity-and-payoff-graph.md",
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


def test_pytest_no_source_path_injection() -> None:
    """Ensure pyproject.toml does not inject src/ via pytest pythonpath."""
    pyproject = REPO_ROOT / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert "pythonpath" not in text.lower(), (
        "pyproject.toml must not contain a pythonpath setting; "
        "the test suite must exercise an installed editable distribution, "
        "not receive src/ through pytest path injection"
    )


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
    # The complete canonical runtime package must ship in the wheel.
    for module in CANONICAL_MODULES:
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
    # The canonical runtime modules and tests must ship in the sdist.
    for module in (*CANONICAL_MODULES, *CANONICAL_TESTS, *CANONICAL_DOCS):
        assert module in stripped, f"missing from sdist: {module}"
    bad = [
        n for n in names for forbidden in FORBIDDEN_SDIST_SUBSTRINGS if forbidden in n
    ]
    assert not bad, f"forbidden content in sdist: {bad}"


def test_canonical_packaging_inventory(artifacts: Path) -> None:
    import zipfile as _zipfile

    wheel = next(artifacts.glob("*.whl"))
    with _zipfile.ZipFile(wheel) as zf:
        wheel_names = zf.namelist()

    sdist = next(artifacts.glob("*.tar.gz"))
    with tarfile.open(sdist) as tf:
        sdist_names = tf.getnames()
    sdist_stripped = {n.split("/", 1)[1] if "/" in n else n for n in sdist_names}

    # Every canonical module appears in the wheel ...
    for module in CANONICAL_MODULES:
        assert f"derivatrace/{module.split('src/derivatrace/')[1]}" in wheel_names, (
            f"canonical module missing from wheel: {module}"
        )
    # ... and in the sdist.
    for module in CANONICAL_MODULES:
        assert module in sdist_stripped, (
            f"canonical module missing from sdist: {module}"
        )

    # Every canonical test appears in the sdist ...
    for test in CANONICAL_TESTS:
        assert test in sdist_stripped, f"canonical test missing from sdist: {test}"

    # ... but canonical tests and docs do NOT appear in the wheel.
    for test in CANONICAL_TESTS:
        assert not any(
            name == test or name.endswith("/" + test.split("/")[-1])
            for name in wheel_names
        ), f"canonical test leaked into wheel: {test}"
    for name in wheel_names:
        assert not name.startswith("docs/"), f"docs leaked into wheel: {name}"

    # Canonical specs, normative vectors and ADR 0007 remain in the sdist.
    for doc in CANONICAL_DOCS:
        assert doc in sdist_stripped, f"canonical doc missing from sdist: {doc}"
