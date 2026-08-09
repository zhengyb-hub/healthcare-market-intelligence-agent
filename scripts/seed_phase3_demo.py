"""Pre-generate traceable Phase 3 demo profiles and comparisons."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.healthcare.bootstrap import DEFAULT_DATABASE_PATH, bootstrap_market_intelligence
from src.healthcare.demo_market_seed import seed_phase3_demo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument(
        "--reset-intelligence",
        action="store_true",
        help="Replace only generated Phase 3 rows; preserve Vendors and Evidence.",
    )
    args = parser.parse_args()
    foundation, intelligence = bootstrap_market_intelligence(
        args.database,
        seed_demo=True,
        seed_intelligence_demo=False,
    )
    if args.reset_intelligence:
        foundation.category_repository.database.reset_intelligence_data()
    stats = seed_phase3_demo(foundation, intelligence)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
