from dbt_semantic_interfaces.implementations.semantic_manifest import (
    PydanticSemanticManifest,
)
from dbt_semantic_interfaces.protocols.semantic_manifest import SemanticManifest
from dbt_semantic_interfaces.protocols.semantic_model import SemanticModel


def check_semantic_model(semantic_model: SemanticModel) -> None:  # noqa: D
    pass


def check_semantic_manifest(semantic_manifest: SemanticManifest) -> None:  # noqa: D
    pass


def test_protocol_compliance(simple_semantic_manifest: PydanticSemanticManifest) -> None:  # noqa: D
    """Check that the Pydantic objects comply with the protocol specification.

    If there are differences, the type checker should throw an error.
    """
    check_semantic_model(simple_semantic_manifest.semantic_models[0])
    check_semantic_manifest(simple_semantic_manifest)
