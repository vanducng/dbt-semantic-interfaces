from __future__ import annotations

from typing import List, Optional, Sequence

from pydantic import model_validator
from typing_extensions import override

from dbt_semantic_interfaces.implementations.base import (
    HashableBaseModel,
    ModelWithMetadataParsing,
)
from dbt_semantic_interfaces.implementations.elements.dimension import PydanticDimension
from dbt_semantic_interfaces.implementations.elements.entity import PydanticEntity
from dbt_semantic_interfaces.implementations.elements.measure import PydanticMeasure
from dbt_semantic_interfaces.implementations.metadata import PydanticMetadata
from dbt_semantic_interfaces.protocols import (
    ProtocolHint,
    SemanticModel,
    SemanticModelDefaults,
)
from dbt_semantic_interfaces.references import (
    EntityReference,
    LinkableElementReference,
    MeasureReference,
    SemanticModelReference,
    TimeDimensionReference,
)


class NodeRelation(HashableBaseModel):
    """Path object to where the data should be."""

    alias: str
    schema_name: str
    database: Optional[str] = None
    relation_name: str = ""

    @model_validator(mode="after")
    def __create_default_relation_name(self) -> "NodeRelation":
        """Dynamically build the dot path for `relation_name`, if not specified."""
        if not self.relation_name:
            if self.database is not None:
                self.relation_name = f"{self.database}.{self.schema_name}.{self.alias}"
            else:
                self.relation_name = f"{self.schema_name}.{self.alias}"
        return self

    @staticmethod
    def from_string(sql_str: str) -> NodeRelation:  # noqa: D
        sql_str_split = sql_str.split(".")
        if len(sql_str_split) == 2:
            return NodeRelation(schema_name=sql_str_split[0], alias=sql_str_split[1])
        elif len(sql_str_split) == 3:
            return NodeRelation(database=sql_str_split[0], schema_name=sql_str_split[1], alias=sql_str_split[2])
        raise RuntimeError(
            f"Invalid input for a SQL table, expected form '<schema>.<table>' or '<db>.<schema>.<table>' "
            f"but got: {sql_str}"
        )


class PydanticSemanticModelDefaults(HashableBaseModel, ProtocolHint[SemanticModelDefaults]):  # noqa: D
    @override
    def _implements_protocol(self) -> SemanticModelDefaults:  # noqa: D
        return self

    agg_time_dimension: Optional[str] = None


class PydanticSemanticModel(HashableBaseModel, ModelWithMetadataParsing, ProtocolHint[SemanticModel]):
    """Describes a semantic model."""

    @override
    def _implements_protocol(self) -> SemanticModel:
        return self

    name: str
    node_relation: NodeRelation
    defaults: Optional[PydanticSemanticModelDefaults] = None
    description: Optional[str] = None

    primary_entity: Optional[str] = None
    entities: Sequence[PydanticEntity] = []
    measures: Sequence[PydanticMeasure] = []
    dimensions: Sequence[PydanticDimension] = []
    label: Optional[str] = None

    metadata: Optional[PydanticMetadata] = None

    @property
    def entity_references(self) -> List[LinkableElementReference]:  # noqa: D
        return [i.reference for i in self.entities]

    @property
    def dimension_references(self) -> List[LinkableElementReference]:  # noqa: D
        return [i.reference for i in self.dimensions]

    @property
    def measure_references(self) -> List[MeasureReference]:  # noqa: D
        return [i.reference for i in self.measures]

    @property
    def has_validity_dimensions(self) -> bool:  # noqa: D
        return any([dim.validity_params is not None for dim in self.dimensions])

    @property
    def validity_start_dimension(self) -> Optional[PydanticDimension]:  # noqa: D
        validity_start_dims = [dim for dim in self.dimensions if dim.validity_params and dim.validity_params.is_start]
        if not validity_start_dims:
            return None
        assert (
            len(validity_start_dims) == 1
        ), "Found more than one validity start dimension. This should have been blocked in validation!"
        return validity_start_dims[0]

    @property
    def validity_end_dimension(self) -> Optional[PydanticDimension]:  # noqa: D
        validity_end_dims = [dim for dim in self.dimensions if dim.validity_params and dim.validity_params.is_end]
        if not validity_end_dims:
            return None
        assert (
            len(validity_end_dims) == 1
        ), "Found more than one validity end dimension. This should have been blocked in validation!"
        return validity_end_dims[0]

    @property
    def partitions(self) -> List[PydanticDimension]:  # noqa: D
        return [dim for dim in self.dimensions or [] if dim.is_partition]

    @property
    def partition(self) -> Optional[PydanticDimension]:  # noqa: D
        partitions = self.partitions
        if not partitions:
            return None
        if len(partitions) > 1:
            raise ValueError(f"too many partitions for semantic_model {self.name}")
        return partitions[0]

    @property
    def reference(self) -> SemanticModelReference:  # noqa: D
        return SemanticModelReference(semantic_model_name=self.name)

    def get_measure(self, measure_reference: MeasureReference) -> PydanticMeasure:  # noqa: D
        for measure in self.measures:
            if measure.reference == measure_reference:
                return measure

        raise ValueError(
            f"No dimension with name ({measure_reference.element_name}) in semantic_model with name ({self.name})"
        )

    def get_dimension(self, dimension_reference: LinkableElementReference) -> PydanticDimension:  # noqa: D
        for dim in self.dimensions:
            if dim.reference == dimension_reference:
                return dim

        raise ValueError(f"No dimension with name ({dimension_reference}) in semantic_model with name ({self.name})")

    def get_entity(self, entity_reference: LinkableElementReference) -> PydanticEntity:  # noqa: D
        for entity in self.entities:
            if entity.reference == entity_reference:
                return entity

        raise ValueError(f"No entity with name ({entity_reference}) in semantic_model with name ({self.name})")

    def checked_agg_time_dimension_for_measure(  # noqa: D
        self, measure_reference: MeasureReference
    ) -> TimeDimensionReference:
        measure = self.get_measure(measure_reference=measure_reference)
        default_agg_time_dimension = self.defaults.agg_time_dimension if self.defaults is not None else None

        agg_time_dimension_name = measure.agg_time_dimension or default_agg_time_dimension
        assert agg_time_dimension_name is not None, (
            f"Aggregation time dimension for measure {measure.name} is not set! This should either be set directly on "
            f"the measure specification in the model, or else defaulted to the primary time dimension in the data "
            f"source containing the measure."
        )
        return TimeDimensionReference(element_name=agg_time_dimension_name)

    @property
    def primary_entity_reference(self) -> Optional[EntityReference]:  # noqa: D
        return EntityReference(element_name=self.primary_entity) if self.primary_entity is not None else None
