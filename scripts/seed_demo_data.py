"""Create or reset the local synthetic Healthcare demonstration database."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.healthcare.bootstrap import DEFAULT_DATABASE_PATH, bootstrap_data_foundation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Explicitly clear existing domain rows before reseeding synthetic data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    foundation = bootstrap_data_foundation(
        database_path=args.database,
        seed_demo=True,
        reset_demo=args.reset,
    )
    print(json.dumps(foundation.statistics(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
