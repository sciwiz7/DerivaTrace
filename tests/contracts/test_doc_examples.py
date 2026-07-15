from __future__ import annotations

import pathlib
import re
from typing import Any

DOCS = pathlib.Path(__file__).resolve().parents[2] / "docs" / "contract-api.md"
PY_RE = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _blocks() -> list[str]:
    return PY_RE.findall(DOCS.read_text(encoding="utf-8"))


def test_contract_api_examples_run() -> None:
    namespace: dict[str, Any] = {}
    exec(
        "import pytest\n"
        "from datetime import datetime, timezone\n"
        "from derivatrace.contracts import *",
        namespace,
    )
    for idx, code in enumerate(_blocks()):
        try:
            exec(code, namespace)
        except Exception as exc:
            raise AssertionError(
                f"docs/contract-api.md example block {idx} failed: {exc}"
            ) from exc


def test_contract_api_has_no_float_construction() -> None:
    text = DOCS.read_text(encoding="utf-8")
    assert "ExactNumber(" not in text
    assert "from_float" not in text
