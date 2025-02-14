import logging

import pytest

from dbt_semantic_interfaces.call_parameter_sets import (
    DimensionCallParameterSet,
    EntityCallParameterSet,
    FilterCallParameterSets,
    ParseWhereFilterException,
    TimeDimensionCallParameterSet,
)
from dbt_semantic_interfaces.implementations.filters.where_filter import (
    PydanticWhereFilter,
    PydanticWhereFilterIntersection,
)
from dbt_semantic_interfaces.parsing.where_filter.parameter_set_factory import (
    ParameterSetFactory,
)
from dbt_semantic_interfaces.references import (
    DimensionReference,
    EntityReference,
    TimeDimensionReference,
)
from dbt_semantic_interfaces.type_enums import TimeGranularity

logger = logging.getLogger(__name__)


def test_extract_dimension_call_parameter_sets() -> None:  # noqa: D
    parse_result = PydanticWhereFilter(
        where_sql_template=(
            """\
                {{ Dimension('booking__is_instant') }} \
                AND {{ Dimension('user__country', entity_path=['listing']) }} == 'US'\
                """
        )
    ).call_parameter_sets

    assert parse_result == FilterCallParameterSets(
        dimension_call_parameter_sets=(
            DimensionCallParameterSet(
                dimension_reference=DimensionReference(element_name="is_instant"),
                entity_path=(EntityReference("booking"),),
            ),
            DimensionCallParameterSet(
                dimension_reference=DimensionReference(element_name="country"),
                entity_path=(
                    EntityReference("listing"),
                    EntityReference("user"),
                ),
            ),
        ),
        entity_call_parameter_sets=(),
    )


def test_extract_dimension_with_grain_call_parameter_sets() -> None:  # noqa: D
    parse_result = PydanticWhereFilter(
        where_sql_template=(
            """
                {{ Dimension('metric_time').grain('WEEK') }} > 2023-09-18
            """
        )
    ).call_parameter_sets

    assert parse_result == FilterCallParameterSets(
        dimension_call_parameter_sets=(),
        time_dimension_call_parameter_sets=(
            TimeDimensionCallParameterSet(
                entity_path=(),
                time_dimension_reference=TimeDimensionReference(element_name="metric_time"),
                time_granularity=TimeGranularity.WEEK,
            ),
        ),
        entity_call_parameter_sets=(),
    )


def test_extract_time_dimension_call_parameter_sets() -> None:  # noqa: D
    parse_result = PydanticWhereFilter(
        where_sql_template=(
            """{{ TimeDimension('user__created_at', 'month', entity_path=['listing']) }} = '2020-01-01'"""
        )
    ).call_parameter_sets

    assert parse_result == FilterCallParameterSets(
        time_dimension_call_parameter_sets=(
            TimeDimensionCallParameterSet(
                time_dimension_reference=TimeDimensionReference(element_name="created_at"),
                entity_path=(
                    EntityReference("listing"),
                    EntityReference("user"),
                ),
                time_granularity=TimeGranularity.MONTH,
            ),
        )
    )


def test_extract_metric_time_dimension_call_parameter_sets() -> None:  # noqa: D
    parse_result = PydanticWhereFilter(
        where_sql_template="""{{ TimeDimension('metric_time', 'month') }} = '2020-01-01'"""
    ).call_parameter_sets

    assert parse_result == FilterCallParameterSets(
        time_dimension_call_parameter_sets=(
            TimeDimensionCallParameterSet(
                time_dimension_reference=TimeDimensionReference(element_name="metric_time"),
                entity_path=(),
                time_granularity=TimeGranularity.MONTH,
            ),
        )
    )


def test_extract_entity_call_parameter_sets() -> None:  # noqa: D
    parse_result = PydanticWhereFilter(
        where_sql_template=(
            """{{ Entity('listing') }} AND {{ Entity('user', entity_path=['listing']) }} == 'TEST_USER_ID'"""
        )
    ).call_parameter_sets

    assert parse_result == FilterCallParameterSets(
        dimension_call_parameter_sets=(),
        entity_call_parameter_sets=(
            EntityCallParameterSet(
                entity_path=(),
                entity_reference=EntityReference("listing"),
            ),
            EntityCallParameterSet(
                entity_path=(EntityReference("listing"),),
                entity_reference=EntityReference("user"),
            ),
        ),
    )


def test_metric_time_in_dimension_call_error() -> None:  # noqa: D
    with pytest.raises(ParseWhereFilterException, match="so it should be referenced using TimeDimension"):
        assert (
            PydanticWhereFilter(where_sql_template="{{ Dimension('metric_time') }} > '2020-01-01'").call_parameter_sets
            is not None
        )


def test_invalid_entity_name_error() -> None:
    """Test to ensure we throw an error if an entity name is invalid."""
    bad_entity_filter = PydanticWhereFilter(where_sql_template="{{ Entity('order_id__is_food_order' )}}")

    with pytest.raises(ParseWhereFilterException, match="Entity name is in an incorrect format"):
        bad_entity_filter.call_parameter_sets


def test_where_filter_interesection_extract_call_parameter_sets() -> None:
    """Tests the collection of call parameter sets for a set of where filters."""
    time_filter = PydanticWhereFilter(
        where_sql_template=("""{{ TimeDimension('metric_time', 'month') }} = '2020-01-01'""")
    )
    entity_filter = PydanticWhereFilter(
        where_sql_template=(
            """{{ Entity('listing') }} AND {{ Entity('user', entity_path=['listing']) }} == 'TEST_USER_ID'"""
        )
    )
    filter_intersection = PydanticWhereFilterIntersection(where_filters=[time_filter, entity_filter])

    parse_result = dict(filter_intersection.filter_expression_parameter_sets)

    assert parse_result.get(time_filter.where_sql_template) == FilterCallParameterSets(
        time_dimension_call_parameter_sets=(
            TimeDimensionCallParameterSet(
                time_dimension_reference=TimeDimensionReference(element_name="metric_time"),
                entity_path=(),
                time_granularity=TimeGranularity.MONTH,
            ),
        )
    )
    assert parse_result.get(entity_filter.where_sql_template) == FilterCallParameterSets(
        dimension_call_parameter_sets=(),
        entity_call_parameter_sets=(
            EntityCallParameterSet(
                entity_path=(),
                entity_reference=EntityReference("listing"),
            ),
            EntityCallParameterSet(
                entity_path=(EntityReference("listing"),),
                entity_reference=EntityReference("user"),
            ),
        ),
    )


def test_where_filter_intersection_error_collection() -> None:
    """Tests the error behaviors when parsing where filters and collecting the call parameter sets for each.

    This should result in a single exception with all broken filters represented.
    """
    metric_time_in_dimension_error = PydanticWhereFilter(
        where_sql_template="{{ TimeDimension('order_id__order_time__month', 'week') }} > '2020-01-01'"
    )
    valid_dimension = PydanticWhereFilter(where_sql_template=" {Dimension('customer__has_delivery_address')} ")
    entity_format_error = PydanticWhereFilter(where_sql_template="{{ Entity('order_id__is_food_order') }}")
    filter_intersection = PydanticWhereFilterIntersection(
        where_filters=[metric_time_in_dimension_error, valid_dimension, entity_format_error]
    )

    with pytest.raises(ParseWhereFilterException) as exc_info:
        filter_intersection.filter_expression_parameter_sets

    error_string = str(exc_info.value)
    # These are a little too implementation-specific, but it demonstrates that we are collecting the errors we find.
    assert ParameterSetFactory._exception_message_for_incorrect_format("order_id__order_time__month") in error_string
    assert "Entity name is in an incorrect format: 'order_id__is_food_order'" in error_string
    # We cannot simply scan for name because the error message contains the filter list, so we assert against the error
    assert (
        ParameterSetFactory._exception_message_for_incorrect_format("customer__has_delivery_address")
        not in error_string
    )


def test_time_dimension_without_granularity() -> None:  # noqa: D
    parse_result = PydanticWhereFilter(
        where_sql_template="{{ TimeDimension('booking__created_at') }} > 2023-09-18"
    ).call_parameter_sets

    assert parse_result == FilterCallParameterSets(
        dimension_call_parameter_sets=(),
        time_dimension_call_parameter_sets=(
            TimeDimensionCallParameterSet(
                entity_path=(EntityReference("booking"),),
                time_dimension_reference=TimeDimensionReference(element_name="created_at"),
                time_granularity=None,
            ),
        ),
        entity_call_parameter_sets=(),
    )
