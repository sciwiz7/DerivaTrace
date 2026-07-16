from __future__ import annotations

import json as _json


def payoff_document_json(obj: object) -> bytes:
    """Serialize a JSON-compatible structure to byte-exact document bytes.

    UTF-8, no BOM, no trailing newline, compact separators, ASCII-escaped, with
    object keys sorted by their (ASCII) byte sequence. This is used for the
    ``document_bytes`` presentation form of the payoff-graph document. It follows
    the same canonical byte rules as ``canonical_json`` from the R1 encoding
    module.
    """
    return _json.dumps(
        obj, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


__all__: list[str] = ["payoff_document_json"]
