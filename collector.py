"""Legacy: collect consumer-App evidence from the Apple iTunes Search API.

The collector intentionally uses a public, keyless API and stores the exact
source URL with every observation. It does not crawl login-protected pages and
does not use an AI model. Phase 2 retains this module as a compatibility adapter;
it is not part of the Healthcare Vendor/Evidence core path.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import requests

from brief_generator import REQUIRED_COLUMNS, validate_competitor_data


OPTIONAL_COLUMNS = ["source_url", "collected_at", "item_id"]
OUTPUT_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
ITUNES_LOOKUP_URL = "https://itunes.apple.com/lookup"


def load_collector_config(path: Path) -> dict[str, Any]:
    """Load and minimally validate the collector configuration."""
    with path.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    competitors = config.get("competitors")
    if not isinstance(competitors, list) or not competitors:
        raise ValueError("Collector config must contain a non-empty competitors list.")

    for competitor in competitors:
        if not str(competitor.get("name", "")).strip():
            raise ValueError("Every competitor must have a name.")
        if not str(competitor.get("track_id", "")).strip():
            raise ValueError("Every competitor must have an Apple App Store track_id.")
    return config


def fetch_app_store_record(
    track_id: int,
    country: str = "cn",
    timeout: int = 30,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Fetch one exact app record from Apple's public lookup endpoint."""
    http = session or requests.Session()
    response = http.get(
        ITUNES_LOOKUP_URL,
        params={"id": track_id, "country": country, "entity": "software"},
        timeout=timeout,
        headers={"User-Agent": "competitor-marketing-brief-agent/1.0"},
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results", [])
    if not results:
        raise ValueError(f"Apple App Store returned no result for track_id={track_id}.")
    return results[0]


def _clean_text(value: Any, limit: int = 1400) -> str:
    """Collapse whitespace and cap stored evidence to a reviewable length."""
    return " ".join(str(value or "").split())[:limit]


def _date_from_iso(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return fallback


def _fingerprint(*values: Any) -> str:
    joined = "\n".join(str(value or "") for value in values)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def build_app_store_observations(
    app: dict[str, Any],
    competitor_name: str,
    collected_on: str | None = None,
) -> list[dict[str, str]]:
    """Turn one App Store record into grounded marketing observations."""
    collected_date = collected_on or date.today().isoformat()
    track_id = str(app.get("trackId", "")).strip()
    version = _clean_text(app.get("version"), 80) or "unknown"
    source_url = _clean_text(app.get("trackViewUrl"), 800)
    release_date = _date_from_iso(
        app.get("currentVersionReleaseDate"),
        collected_date,
    )
    observations: list[dict[str, str]] = []

    release_notes = _clean_text(app.get("releaseNotes"))
    if release_notes:
        observations.append(
            {
                "competitor": competitor_name,
                "date": release_date,
                "source": "Apple App Store",
                "title": f"Version {version} release notes",
                "content": release_notes,
                "category": "Product Feature",
                "source_url": source_url,
                "collected_at": collected_date,
                "item_id": f"appstore:{track_id}:release:{version}",
            }
        )

    description = _clean_text(app.get("description"))
    if description:
        description_hash = _fingerprint(track_id, description)
        observations.append(
            {
                "competitor": competitor_name,
                "date": collected_date,
                "source": "Apple App Store",
                "title": f"App Store positioning snapshot · v{version}",
                "content": description,
                "category": "Brand Positioning",
                "source_url": source_url,
                "collected_at": collected_date,
                "item_id": f"appstore:{track_id}:positioning:{description_hash}",
            }
        )

    rating = app.get("averageUserRatingForCurrentVersion")
    rating_count = app.get("userRatingCountForCurrentVersion")
    if rating is not None and rating_count is not None:
        rating_text = (
            f"Version {version} has an App Store rating of {float(rating):.2f}/5 "
            f"from {int(rating_count):,} ratings at collection time."
        )
        rating_hash = _fingerprint(track_id, version, f"{float(rating):.2f}", rating_count)
        observations.append(
            {
                "competitor": competitor_name,
                "date": collected_date,
                "source": "Apple App Store",
                "title": f"App Store rating snapshot · v{version}",
                "content": rating_text,
                "category": "User Engagement",
                "source_url": source_url,
                "collected_at": collected_date,
                "item_id": f"appstore:{track_id}:rating:{rating_hash}",
            }
        )

    return observations


def merge_observations(
    existing: pd.DataFrame,
    incoming: pd.DataFrame,
    max_records_per_competitor: int = 60,
) -> pd.DataFrame:
    """Merge new evidence, deduplicate stable items, and bound repository growth."""
    frames = [frame for frame in (existing, incoming) if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    combined = pd.concat(frames, ignore_index=True, sort=False)
    for column in OUTPUT_COLUMNS:
        if column not in combined.columns:
            combined[column] = ""

    combined = combined[OUTPUT_COLUMNS].fillna("")
    item_ids = combined["item_id"].astype(str).str.strip()
    fallback_ids = combined.apply(
        lambda row: "row:" + _fingerprint(
            row["competitor"],
            row["date"],
            row["title"],
            row["content"],
        ),
        axis=1,
    )
    combined["item_id"] = item_ids.where(item_ids.ne(""), fallback_ids)
    # Existing rows come first, so unchanged observations retain their original
    # observation date. A scheduled run therefore creates a commit only when an
    # actual version, description, or rating fingerprint changes.
    combined = combined.drop_duplicates(subset=["item_id"], keep="first")
    combined = validate_competitor_data(combined)

    if "item_id" not in combined.columns:
        raise ValueError("Collector output lost its item_id column during validation.")

    combined = (
        combined.sort_values(
            ["competitor", "date", "collected_at"],
            ascending=[True, False, False],
        )
        .groupby("competitor", group_keys=False)
        .head(max_records_per_competitor)
        .sort_values(["date", "competitor"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return combined[OUTPUT_COLUMNS]


def collect_competitor_data(
    config: dict[str, Any],
    output_path: Path,
    fetcher: Callable[[int, str], dict[str, Any]] | None = None,
    collected_on: str | None = None,
) -> pd.DataFrame:
    """Collect configured apps, merge with history, and persist a CSV dataset."""
    country = str(config.get("country", "cn")).strip() or "cn"
    max_records = int(config.get("max_records_per_competitor", 60))
    collection_date = collected_on or datetime.now(timezone.utc).date().isoformat()
    fetch = fetcher or (
        lambda track_id, market: fetch_app_store_record(track_id, market)
    )

    rows: list[dict[str, str]] = []
    failures: list[str] = []
    for competitor in config["competitors"]:
        name = str(competitor["name"]).strip()
        track_id = int(competitor["track_id"])
        try:
            app = fetch(track_id, country)
            rows.extend(build_app_store_observations(app, name, collection_date))
        except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
            failures.append(f"{name}: {exc}")

    if not rows:
        details = "; ".join(failures) or "No observations were generated."
        raise RuntimeError(f"Collection failed for every competitor. {details}")

    incoming = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    existing = (
        pd.read_csv(output_path)
        if output_path.exists() and output_path.stat().st_size
        else pd.DataFrame(columns=OUTPUT_COLUMNS)
    )
    merged = merge_observations(existing, incoming, max_records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False, encoding="utf-8")

    if failures:
        print("Partial collection warnings:")
        for failure in failures:
            print(f"- {failure}")
    print(
        f"Saved {len(merged)} observations for "
        f"{merged['competitor'].nunique()} competitors to {output_path}."
    )
    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/competitors.json"),
        help="Path to the competitor configuration JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/collected_competitor_data.csv"),
        help="Path to the generated CSV dataset.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_collector_config(args.config)
    collect_competitor_data(config, args.output)


if __name__ == "__main__":
    main()
