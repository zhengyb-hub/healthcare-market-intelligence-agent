"""Compatibility imports for the deprecated Apple App Store collector.

The Healthcare data foundation does not import this module. It exists so the
working Phase 1 collector and its tests remain available without contaminating
the Vendor or Evidence schemas.
"""

from collector import (
    ITUNES_LOOKUP_URL,
    OUTPUT_COLUMNS,
    build_app_store_observations,
    collect_competitor_data,
    fetch_app_store_record,
    load_collector_config,
    merge_observations,
)

__all__ = [
    "ITUNES_LOOKUP_URL",
    "OUTPUT_COLUMNS",
    "build_app_store_observations",
    "collect_competitor_data",
    "fetch_app_store_record",
    "load_collector_config",
    "merge_observations",
]
