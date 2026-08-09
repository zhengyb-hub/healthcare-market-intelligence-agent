"""Seed deterministic Phase 4 Healthcare product-workflow records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.healthcare.bootstrap import DEFAULT_DATABASE_PATH, bootstrap_product_workflow
from src.healthcare.demo_workflow_seed import seed_phase4_demo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    args = parser.parse_args()
    foundation, intelligence, workflow = bootstrap_product_workflow(
        args.database,
        seed_demo=True,
        seed_intelligence_demo=True,
        seed_workflow_demo=False,
    )
    print(json.dumps(
        seed_phase4_demo(foundation, intelligence, workflow),
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
