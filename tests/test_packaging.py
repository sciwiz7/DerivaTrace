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

REQUIRED_SDIST_PATHS = [
    "src/derivatrace/__init__.py",
    "src/derivatrace/_metadata.py",
    "src/derivatrace/py.typed",
    "tests/test_package.py",
    "tests/test_documentation.py",
    "docs/index.md",
    "docs/vision.md",
    "docs/product-spec.md",
    "docs/architecture.md",
    "docs/contract-semantics.md",
    "docs/certificate-spec.md",
    "docs/threat-model.md",
    "docs/glossary.md",
    "docs/adr/0001-separation-of-contract-model-engine.md",
    "docs/adr/0002-deterministic-canonicalization.md",
    "docs/adr/0003-evidence-carrying-results.md",
    "docs/adr/0004-exact-contract-terms-and-numerical-boundaries.md",
    "docs/adr/0005-no-hidden-model-selection.md",
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
