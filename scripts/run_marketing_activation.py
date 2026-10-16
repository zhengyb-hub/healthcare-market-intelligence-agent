"""Run the deterministic Evidence-to-Activation workflow and export a digest."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.healthcare.activation_services import ACTIVATION_CHANNELS
from src.healthcare.bootstrap import DEFAULT_DATABASE_PATH, bootstrap_product_workflow


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--output", type=Path, default=Path("outputs/latest_weekly_digest.md"))
    parser.add_argument("--lookback", type=int, choices=(7, 30, 90, 365), default=30)
    parser.add_argument("--target-brand", default="Northstar Health Intelligence")
    args = parser.parse_args()

    foundation, _, workflow = bootstrap_product_workflow(
        args.database,
        seed_demo=False,
        seed_intelligence_demo=False,
        seed_workflow_demo=False,
    )
    vendors = foundation.vendor_service.list_vendors()
    if not vendors:
        raise SystemExit("No Vendors found. Seed or import data before running activation.")
    vendor_ids = [vendor.vendor_id for vendor in vendors[:3]]
    changes = workflow.change_detection_service.scan(vendor_ids)
    if not workflow.marketing_action_repository.list_all():
        workflow.marketing_action_service.create(
            vendor_ids,
            "Build an evidence-led demand-generation campaign",
            "Healthcare IT decision-makers",
            list(ACTIVATION_CHANNELS),
            args.target_brand,
        )
    digest = workflow.weekly_digest_service.create(args.lookback)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        workflow.weekly_digest_service.markdown(digest),
        encoding="utf-8",
    )
    print(
        f"Activation complete: {len(changes)} compared change signals; "
        f"digest={digest.digest_id}; output={args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
