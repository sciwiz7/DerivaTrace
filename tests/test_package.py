from __future__ import annotations

import tomllib
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import derivatrace
from derivatrace import ProjectMetadata, project_metadata

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_imports() -> None:
    assert derivatrace is not None


def test_version_exact() -> None:
    assert derivatrace.__version__ == "0.1.0.dev0"


def test_metadata_type() -> None:
    meta = project_metadata()
    assert isinstance(meta, ProjectMetadata)


def test_metadata_immutable() -> None:
    meta = project_metadata()
    attribute = "version"
    with pytest.raises(FrozenInstanceError):
        setattr(meta, attribute, "0.1.0.dev1")


def test_metadata_deterministic() -> None:
    assert project_metadata() == project_metadata()


def test_metadata_values() -> None:
    meta = project_metadata()
    assert meta.project_name == "DerivaTrace"
    assert meta.package_name == "derivatrace"
    assert meta.version == "0.1.0.dev0"
    assert meta.development_status == "2 - Pre-Alpha"
    assert meta.minimum_python_version == "3.11"
    assert meta.core_architectural_principle == (
        "A valuation without evidence is an incomplete output."
    )


def test_py_typed_exists() -> None:
    assert (REPO_ROOT / "src" / "derivatrace" / "py.typed").is_file()


def test_no_runtime_dependencies() -> None:
    with open(REPO_ROOT / "pyproject.toml", "rb") as handle:
        data = tomllib.load(handle)
    assert data["project"]["dependencies"] == []


def test_pyproject_metadata() -> None:
    with open(REPO_ROOT / "pyproject.toml", "rb") as handle:
        data = tomllib.load(handle)
    project = data["project"]
    assert project["name"] == "derivatrace"
    assert project["version"] == "0.1.0.dev0"
    assert project["requires-python"] == ">=3.11"
    assert project["license"] == "MIT"
    assert "Development Status :: 2 - Pre-Alpha" in project["classifiers"]


def test_major_docs_exist() -> None:
    required = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "CHANGELOG.md",
        REPO_ROOT / "ROADMAP.md",
        REPO_ROOT / "CONTRIBUTING.md",
        REPO_ROOT / "CODE_OF_CONDUCT.md",
        REPO_ROOT / "SECURITY.md",
        REPO_ROOT / "GOVERNANCE.md",
        REPO_ROOT / "LICENSE",
        REPO_ROOT / "docs" / "index.md",
        REPO_ROOT / "docs" / "vision.md",
        REPO_ROOT / "docs" / "product-spec.md",
        REPO_ROOT / "docs" / "architecture.md",
        REPO_ROOT / "docs" / "contract-semantics.md",
        REPO_ROOT / "docs" / "certificate-spec.md",
        REPO_ROOT / "docs" / "threat-model.md",
        REPO_ROOT / "docs" / "glossary.md",
        REPO_ROOT / "docs" / "adr" / "0001-separation-of-contract-model-engine.md",
        REPO_ROOT / "docs" / "adr" / "0002-deterministic-canonicalization.md",
        REPO_ROOT / "docs" / "adr" / "0003-evidence-carrying-results.md",
        REPO_ROOT
        / "docs"
        / "adr"
        / "0004-exact-contract-terms-and-numerical-boundaries.md",
        REPO_ROOT / "docs" / "adr" / "0005-no-hidden-model-selection.md",
    ]
    for path in required:
        assert path.is_file(), str(path)
