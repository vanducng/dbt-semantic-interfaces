from dbt_semantic_interfaces.implementations.semantic_manifest import (
    PydanticSemanticManifest,
)


def test_model_serialization_deserialization(simple_semantic_manifest: PydanticSemanticManifest) -> None:
    """Tests Pydantic serialization and deserialization of a SemanticManifest.

    This ensures any custom parsing operations internal to our Pydantic models are properly applied to not only
    user-provided YAML input, but also to internal parsing operations based on serialized model objects.
    """
    serialized_model = simple_semantic_manifest.model_dump_json()
    deserialized_model = simple_semantic_manifest.model_validate_json(serialized_model)
    assert deserialized_model == simple_semantic_manifest
