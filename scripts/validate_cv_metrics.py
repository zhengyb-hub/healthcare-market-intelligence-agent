"""Verify that CV_METRICS.json exactly matches the current SQLite source."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.healthcare.bootstrap import DEFAULT_DATABASE_PATH, bootstrap_product_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--metrics", type=Path, default=PROJECT_ROOT / "CV_METRICS.json")
    args = parser.parse_args()
    _, _, workflow = bootstrap_product_workflow(args.database, seed_demo=False)
    result = workflow.analytics_service.validate_cv_file(args.metrics)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["result"] == "PASS" else 1)


if __name__ == "__main__":
    main()
