# Legacy Consumer-App Adapter

`collector.py`, `brief_generator.py`, the Apple configuration, and their original tests are retained for compatibility and audit history.

- They are not imported by the Phase 2 Healthcare Streamlit application.
- Apple `track_id`, ratings, release notes, and App Store categories are not part of the Healthcare Vendor or Evidence schema.
- `legacy/app_store_adapter.py` provides an explicit compatibility import path.
- Removal is deferred until a later migration phase confirms that no legacy demonstration or test depends on them.
