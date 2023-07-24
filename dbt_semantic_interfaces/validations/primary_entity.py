import logging
from typing import Generic, List, Sequence

from dbt_semantic_interfaces.implementations.semantic_manifest import (
    PydanticSemanticManifest,
)
from dbt_semantic_interfaces.protocols import Entity, SemanticManifestT, SemanticModel
from dbt_semantic_interfaces.references import SemanticModelReference
from dbt_semantic_interfaces.type_enums import EntityType
from dbt_semantic_interfaces.validations.validator_helpers import (
    FileContext,
    SemanticManifestValidationRule,
    SemanticModelContext,
    ValidationError,
    ValidationIssue,
    validate_safely,
)

logger = logging.getLogger(__name__)


class PrimaryEntityRule(SemanticManifestValidationRule[SemanticManifestT], Generic[SemanticManifestT]):
    """If a semantic model contains dimensions, the primary entity must be available.

    The primary entity could be defined by the primary_entity field, or by one of the entities defined in a semantic
    model.
    """

    @staticmethod
    def _model_requires_primary_entity(semantic_model: SemanticModel) -> bool:
        return len(semantic_model.dimensions) > 0

    @staticmethod
    def _model_has_entity_with_primary_type(semantic_model: SemanticModel) -> bool:
        return any(entity.type == EntityType.PRIMARY for entity in semantic_model.entities)

    @staticmethod
    def _entity_with_primary_type_in_model(semantic_model: SemanticModel) -> Entity:
        for entity in semantic_model.entities:
            if entity.type == EntityType.PRIMARY:
                return entity
        entities_with_primary_type = tuple(
            entity for entity in semantic_model.entities if entity.type == EntityType.PRIMARY
        )

        if len(entities_with_primary_type) == 1:
            return entities_with_primary_type[0]

        raise RuntimeError(f"Did not find exactly one entity with entity type {EntityType.PRIMARY} in {semantic_model}")

    @staticmethod
    @validate_safely("Check that a semantic model has properly configured primary entities.")
    def _check_model(semantic_model: SemanticModel) -> Sequence[ValidationIssue]:
        context = SemanticModelContext(
            file_context=FileContext.from_metadata(metadata=semantic_model.metadata),
            semantic_model=SemanticModelReference(semantic_model_name=semantic_model.name),
        )

        # Check that the primary entity field and the listed entities don't conflict.
        if (
            semantic_model.primary_entity_reference is not None
            and PrimaryEntityRule._model_has_entity_with_primary_type(semantic_model)
        ):
            entity_with_primary_type = PrimaryEntityRule._entity_with_primary_type_in_model(semantic_model)
            if semantic_model.primary_entity_reference != entity_with_primary_type.reference:
                return (
                    ValidationError(
                        message=(
                            f"Semantic model {semantic_model.name} has an entity named {entity_with_primary_type.name} "
                            f"with type primary but it conflicts with the primary_entity field set to "
                            f"{semantic_model.primary_entity_reference.element_name}"
                        ),
                        context=context,
                    ),
                )

        # Check that a primary entity has been set if required.
        if (
            PrimaryEntityRule._model_requires_primary_entity(semantic_model)
            and semantic_model.primary_entity_reference is None
            and not PrimaryEntityRule._model_has_entity_with_primary_type(semantic_model)
        ):
            return (
                ValidationError(
                    message=(
                        f"The semantic model {semantic_model.name} contains dimensions, but it does not define a "
                        f"primary entity."
                    ),
                    context=context,
                ),
            )

        return []

    @staticmethod
    @validate_safely("Check that semantic models in the manifest have properly configured primary entities.")
    def validate_manifest(semantic_manifest: PydanticSemanticManifest) -> Sequence[ValidationIssue]:  # noqa: D
        issues: List[ValidationIssue] = []
        for semantic_model in semantic_manifest.semantic_models:
            issues += PrimaryEntityRule._check_model(semantic_model)

        return issues
