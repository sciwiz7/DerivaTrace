from __future__ import annotations

from dataclasses import dataclass

PROJECT_NAME: str = "DerivaTrace"
PACKAGE_NAME: str = "derivatrace"
PROJECT_VERSION: str = "0.1.0.dev0"
DEVELOPMENT_STATUS: str = "2 - Pre-Alpha"
MINIMUM_PYTHON_VERSION: str = "3.11"
CORE_ARCHITECTURAL_PRINCIPLE: str = (
    "A valuation without evidence is an incomplete output."
)


@dataclass(frozen=True)
class ProjectMetadata:
    """Immutable value object holding safe, static project facts.

    Instances contain only descriptive metadata that cannot influence
    deterministic calculations. The object is frozen and therefore cannot be
    mutated after construction.
    """

    project_name: str
    package_name: str
    version: str
    development_status: str
    minimum_python_version: str
    core_architectural_principle: str


def project_metadata() -> ProjectMetadata:
    """Return a deterministic :class:`ProjectMetadata` value object.

    The returned object is rebuilt on every call but is value-identical and
    immutable, so repeated calls are guaranteed to be deterministic.
    """
    return ProjectMetadata(
        project_name=PROJECT_NAME,
        package_name=PACKAGE_NAME,
        version=PROJECT_VERSION,
        development_status=DEVELOPMENT_STATUS,
        minimum_python_version=MINIMUM_PYTHON_VERSION,
        core_architectural_principle=CORE_ARCHITECTURAL_PRINCIPLE,
    )
