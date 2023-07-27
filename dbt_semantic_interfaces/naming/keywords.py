# A double underscore used as a seperator
DUNDER = "__"

# The name for the time dimension that metrics are tabulated / plotted.
METRIC_TIME_ELEMENT_NAME = "metric_time"


def is_metric_time_name(element_name: str) -> bool:
    """Returns True if the given element name corresponds to metric time."""
    return element_name == METRIC_TIME_ELEMENT_NAME
