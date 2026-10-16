"""Deterministic marketing-activation demo outputs."""

from __future__ import annotations

from typing import Any

from .services import DataFoundationService
from .workflow_services import ProductWorkflowServices


def seed_activation_demo(
    foundation: DataFoundationService,
    workflow: ProductWorkflowServices,
) -> dict[str, Any]:
    database = foundation.category_repository.database
    with database.connect() as connection:
        seeded = connection.execute(
            "SELECT value FROM schema_metadata WHERE key = 'phase7_demo_seeded'"
        ).fetchone()
    if seeded and seeded[0] == "1":
        return workflow.statistics()

    vendors = foundation.vendor_service.list_vendors()
    selected_ids = [vendor.vendor_id for vendor in vendors[:3]]
    workflow.change_detection_service.scan(selected_ids)
    workflow.marketing_action_service.create(
        selected_ids,
        objective="Build an evidence-led Q4 demand-generation campaign",
        audience="Hospital CIOs and healthcare digital-transformation leaders",
        channels=["LinkedIn", "Short Video", "Email", "Sales Enablement"],
        target_brand="Northstar Health Intelligence",
    )
    workflow.weekly_digest_service.create(lookback_days=30)
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO schema_metadata(key, value) VALUES ('phase7_demo_seeded', '1')
            ON CONFLICT(key) DO UPDATE SET value='1'
            """
        )
    return workflow.statistics()
