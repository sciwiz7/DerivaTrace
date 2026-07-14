from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"

INLINE_LINK_RE = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
REF_DEF_RE = re.compile(r"^\s*\[([^\]]+)\]:\s*(\S+)", re.MULTILINE)
REF_USE_RE = re.compile(r"\!?\[[^\]]+\]\[([^\]]+)\]")
REF_USE_EMPTY_RE = re.compile(r"\!?\[([^\]]+)\]\[\]")

ABS_PATH_RE = re.compile(r"(/Users/|/home/|/Documents/|[A-Za-z]:[\\/](?!/))")

FORBIDDEN_CLAIMS = [
    "first ever",
    "first-of-its-kind",
    "formally verified",
    "formally proven",
    "mathematically proven",
    "proven correct",
]

PYPI_CLAIMS = [
    "available on pypi",
    "published on pypi",
    "install derivatrace",
    "pip install derivatrace",
    "on pypi",
    "pypi package",
    "released on pypi",
]

PRICING_CLAIMS = [
    "can price",
    "can value",
    "calculates prices",
    "calculates price",
    "prices derivatives",
    "values derivatives",
    "perform pricing",
    "performs pricing",
    "provides pricing",
    "derivatrace prices",
    "derivatrace values",
    "derivatrace calculates",
]

NEGATIONS = [
    "not ",
    "never ",
    "no ",
    "without ",
    "cannot",
    "can't",
    "don't",
    "do not",
    "isn't",
    "aren't",
    "won't",
    "does not",
    "doesn't",
]

SECRET_RES = [
    re.compile(r"AKIA[0-9A-Z]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"-----BEGIN CERTIFICATE-----"),
    re.compile(r"ghp_[A-Za-z0-9]{16,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[0-9]{10,}"),
    re.compile(
        r"(?:api[_]?key|secret[_]?key|client[_]?secret|password|passwd|access[_]?token)\s*[:=]"
    ),
]

CONFIG_FILES = [
    REPO_ROOT / "pyproject.toml",
    REPO_ROOT / ".github" / "workflows" / "ci.yml",
    REPO_ROOT / ".pre-commit-config.yaml",
]


def markdown_files() -> list[Path]:
    files: list[Path] = [REPO_ROOT / "README.md"]
    files.extend(sorted(REPO_ROOT.glob("*.md")))
    files.extend(sorted(DOCS_DIR.glob("*.md")))
    files.extend(sorted((DOCS_DIR / "adr").glob("*.md")))
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in files:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def extract_local_targets(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    targets: list[str] = []
    for match in INLINE_LINK_RE.finditer(text):
        targets.append(match.group(1))
    definitions: dict[str, str] = {}
    for match in REF_DEF_RE.finditer(text):
        definitions[match.group(1).lower()] = match.group(2)
    for match in REF_USE_RE.finditer(text):
        label = match.group(1).lower()
        if label in definitions:
            targets.append(definitions[label])
    for match in REF_USE_EMPTY_RE.finditer(text):
        label = match.group(1).lower()
        if label in definitions:
            targets.append(definitions[label])
    return targets


def link_resolves(source: Path, target: str) -> bool:
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return True
    path_part = target.split("#", 1)[0]
    if path_part == "":
        return True
    if target.startswith("/"):
        candidate = REPO_ROOT / path_part.lstrip("/")
    else:
        candidate = (source.parent / path_part).resolve()
    return candidate.exists()


def lines_without_negation(text: str, claim: str) -> list[str]:
    offending: list[str] = []
    for line in text.splitlines():
        lower = line.lower()
        index = lower.find(claim)
        while index != -1:
            before = lower[:index]
            if not any(negation in before for negation in NEGATIONS):
                offending.append(line)
            index = lower.find(claim, index + 1)
    return offending


def test_all_local_markdown_links_resolve() -> None:
    broken: list[tuple[str, str]] = []
    for markdown in markdown_files():
        for target in extract_local_targets(markdown):
            if not link_resolves(markdown, target):
                broken.append((str(markdown), target))
    assert not broken, f"Broken local links: {broken}"


def test_readme_states_prealpha_not_published() -> None:
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "pre-alpha" in text
    assert "not published" in text


def test_readme_does_not_claim_pricing_exists() -> None:
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    offending = []
    for claim in PRICING_CLAIMS:
        if lines_without_negation(text, claim):
            offending.append(claim)
    assert not offending, f"Pricing claims in README: {offending}"


def test_docs_do_not_claim_pypi_availability() -> None:
    for markdown in markdown_files():
        text = markdown.read_text(encoding="utf-8")
        for claim in PYPI_CLAIMS:
            offending = lines_without_negation(text, claim)
            assert not offending, f"{markdown}: PyPI claim '{claim}': {offending}"


def test_docs_do_not_make_forbidden_claims() -> None:
    for markdown in markdown_files():
        text = markdown.read_text(encoding="utf-8")
        for claim in FORBIDDEN_CLAIMS:
            offending = lines_without_negation(text, claim)
            assert not offending, f"{markdown}: forbidden claim '{claim}': {offending}"


def test_no_absolute_local_paths() -> None:
    files = markdown_files() + CONFIG_FILES
    hits: list[tuple[str, str]] = []
    for path in files:
        for match in ABS_PATH_RE.finditer(path.read_text(encoding="utf-8")):
            hits.append((str(path), match.group(0)))
    assert not hits, f"Absolute local paths: {hits}"


def test_no_secrets_or_credentials() -> None:
    files = markdown_files() + CONFIG_FILES
    hits: list[tuple[str, str]] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_RES:
            match = pattern.search(text)
            if match is not None:
                hits.append((str(path), pattern.pattern))
    assert not hits, f"Possible secrets: {hits}"


def test_no_codex_context_file() -> None:
    assert not (REPO_ROOT / "CODEX_CONTEXT.md").exists()


def test_project_urls_point_to_intended_repo() -> None:
    with open(REPO_ROOT / "pyproject.toml", "rb") as handle:
        data = tomllib.load(handle)
    urls = data["project"].get("urls", {})
    for name, url in urls.items():
        assert "github.com/sciwiz7/DerivaTrace" in url, (name, url)
    for markdown in markdown_files():
        text = markdown.read_text(encoding="utf-8")
        for match in re.finditer(r"github\.com/[A-Za-z0-9_./-]+", text):
            assert "sciwiz7/DerivaTrace" in match.group(0), (
                str(markdown),
                match.group(0),
            )


def test_ci_matrix_includes_311_to_314() -> None:
    text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for version in ['"3.11"', '"3.12"', '"3.13"', '"3.14"']:
        assert version in text, version


def test_ci_has_no_publishing_or_oidc_permissions() -> None:
    text = (
        (REPO_ROOT / ".github" / "workflows" / "ci.yml")
        .read_text(encoding="utf-8")
        .lower()
    )
    assert "id-token" not in text
    assert "publish" not in text
    assert "write" not in text
    assert "secrets" not in text


def test_separation_of_concerns_referenced() -> None:
    architecture = (
        (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8").lower()
    )
    assert "separation of concerns" in architecture
    layers = [
        "contract semantics",
        "market data",
        "model",
        "numerical engine",
        "risk",
        "validation",
        "evidence certificate",
    ]
    for layer in layers:
        assert layer in architecture, layer
    for doc in [
        REPO_ROOT / "docs" / "index.md",
        REPO_ROOT / "docs" / "product-spec.md",
        REPO_ROOT / "docs" / "contract-semantics.md",
    ]:
        content = doc.read_text(encoding="utf-8").lower()
        assert "separation of concerns" in content, str(doc)


def _strip_emphasis(text: str) -> str:
    return re.sub(r"\*+", "", text)


def test_certificate_spec_denies_proof_and_signature() -> None:
    text = _strip_emphasis(
        (REPO_ROOT / "docs" / "certificate-spec.md").read_text(encoding="utf-8")
    ).lower()
    assert "not a mathematical proof" in text
    assert "not a digital signature" in text


def test_certificate_spec_hash_excludes_itself() -> None:
    text = (
        (REPO_ROOT / "docs" / "certificate-spec.md").read_text(encoding="utf-8").lower()
    )
    assert "certificate_hash" in text
    assert "omit" in text
    assert "reproducibility_hash" in text


def test_threat_model_covers_required_threats() -> None:
    text = (REPO_ROOT / "docs" / "threat-model.md").read_text(encoding="utf-8").lower()
    required = [
        "arbitrary-code execution",
        "untrusted deserialization",
        "schema confusion",
        "canonicalization collision",
        "hash confusion",
        "deeply nested",
        "cyclic graph",
        "path counts",
        "extreme numeric",
        "overflow",
        "infinity",
        "path traversal",
        "archive extraction",
        "denial of service",
        "plugin",
        "model or engine substitution",
        "dependency confusion",
        "release workflows",
        "certificate tampering",
        "misleading validation",
        "secret leakage",
    ]
    missing = [t for t in required if t not in text]
    assert not missing, f"threat model missing coverage: {missing}"
