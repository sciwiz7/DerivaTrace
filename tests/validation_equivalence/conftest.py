from __future__ import annotations

from typing import Any


def _make_default_limits_used() -> Any:
    """Import and construct default LimitsUsed for tests."""
    from derivatrace.validation_equivalence._records import LimitsUsed

    return LimitsUsed()


def _make_default_schema_metadata() -> Any:
    """Import and construct default SchemaMetadataRecord for tests."""
    from derivatrace.validation_equivalence._records import SchemaMetadataRecord

    return SchemaMetadataRecord()
