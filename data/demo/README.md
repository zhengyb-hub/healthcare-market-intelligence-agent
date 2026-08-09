# Synthetic Healthcare Demo Data

All vendors, hospitals, procurement entities, projects, URLs, and evidence facts generated from this directory are fictional.

- `healthcare_vendors.json` defines 12 stable synthetic Vendor records.
- `src/healthcare/demo_data.py` deterministically generates 15 Evidence records per vendor, for 180 total records.
- The generated dataset includes multiple source types, all 15 solution categories, varied dates and authority levels, six marked duplicates, warning records, and invalid records.
- `.invalid` URLs are reserved demonstration domains and are not real evidence sources.

Synthetic records are stored with `is_synthetic = true` and must be excluded from real market claims and production analytics.
