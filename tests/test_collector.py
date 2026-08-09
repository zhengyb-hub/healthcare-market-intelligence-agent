import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from collector import (
    OUTPUT_COLUMNS,
    build_app_store_observations,
    collect_competitor_data,
    merge_observations,
)


def fake_app(track_id=123, version="2.0"):
    return {
        "trackId": track_id,
        "trackName": "Example News",
        "version": version,
        "currentVersionReleaseDate": "2026-07-20T08:00:00Z",
        "releaseNotes": "Added a personalized topic page and improved sharing.",
        "description": "Fast, trustworthy news with local and national coverage.",
        "averageUserRatingForCurrentVersion": 4.6,
        "userRatingCountForCurrentVersion": 1250,
        "trackViewUrl": "https://apps.apple.com/app/id123",
    }


class CollectorTests(unittest.TestCase):
    def test_builds_grounded_observations_with_source_urls(self):
        rows = build_app_store_observations(
            fake_app(),
            "Example News",
            collected_on="2026-07-25",
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            {row["category"] for row in rows},
            {"Product Feature", "Brand Positioning", "User Engagement"},
        )
        self.assertTrue(all(row["source_url"].startswith("https://") for row in rows))
        self.assertTrue(all(row["item_id"].startswith("appstore:123:") for row in rows))

    def test_merge_deduplicates_stable_items(self):
        rows = build_app_store_observations(
            fake_app(),
            "Example News",
            collected_on="2026-07-25",
        )
        frame = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
        later_rows = build_app_store_observations(
            fake_app(),
            "Example News",
            collected_on="2026-07-26",
        )
        merged = merge_observations(
            frame,
            pd.DataFrame(later_rows, columns=OUTPUT_COLUMNS),
            max_records_per_competitor=60,
        )
        self.assertEqual(len(merged), 3)
        self.assertEqual(set(merged["collected_at"]), {"2026-07-25"})

    def test_collection_writes_csv_without_network(self):
        config = {
            "country": "cn",
            "max_records_per_competitor": 60,
            "competitors": [{"name": "Example News", "track_id": 123}],
        }

        output = Path("unused-collected.csv")
        with patch("collector.pd.DataFrame.to_csv") as write_csv:
            result = collect_competitor_data(
                config,
                output,
                fetcher=lambda track_id, country: fake_app(track_id),
                collected_on="2026-07-25",
            )
            write_csv.assert_called_once()
            self.assertEqual(len(result), 3)
            self.assertEqual(result.iloc[0]["competitor"], "Example News")


if __name__ == "__main__":
    unittest.main()
