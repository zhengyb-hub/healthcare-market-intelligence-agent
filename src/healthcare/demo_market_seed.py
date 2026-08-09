"""Pre-generate traceable Vendor and Comparison demo outputs."""

from __future__ import annotations

from typing import Any

from .intelligence_services import MarketIntelligenceServices
from .services import DataFoundationService


def seed_phase3_demo(
    foundation: DataFoundationService,
    intelligence: MarketIntelligenceServices,
) -> dict[str, Any]:
    """Generate three Vendor profiles and three Comparison briefs once."""
    if intelligence.brief_repository.count() > 0:
        return intelligence.statistics()
    vendors = foundation.vendor_service.list_vendors()
    if len(vendors) < 3:
        raise ValueError("Phase 3 demo generation requires at least three Vendors")
    selected = vendors[:3]
    for vendor in selected:
        intelligence.vendor_intelligence_service.generate(vendor.vendor_id)
    comparison_sets = [
        [selected[0].vendor_id, selected[1].vendor_id],
        [selected[1].vendor_id, selected[2].vendor_id],
        [vendor.vendor_id for vendor in selected],
    ]
    for vendor_ids in comparison_sets:
        intelligence.comparison_service.generate(vendor_ids)
    return intelligence.statistics()
