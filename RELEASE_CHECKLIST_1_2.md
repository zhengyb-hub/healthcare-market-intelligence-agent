# Release Checklist — 1.2.0

Classification: **portfolio evaluation release**, not production-ready.

| Check | Result | Evidence |
|---|---|---|
| Full Python suite | PASS | 75 `unittest` tests, including activation services and Streamlit AppTest |
| No-key UI | PASS | All ten primary workspaces plus Intelligence → Changes render in AppTest |
| Activation CLI | PASS | Synthetic dataset produced 8 change signals, 1 action brief, 5 content opportunities, and 1 digest |
| Data integrity | PASS | No invalid Phase 7 JSON, orphan links, or invalid statuses after CLI run |
| Local service health | PASS | Streamlit `/_stcore/health` returned `ok` |
| Public-data boundary | PASS | Only synthetic demo records are used by the weekly digest workflow |
| CV materials | EXCLUDED | No CV evidence, CV metrics, or personal resume files are part of this release |
| Efficiency claims | NOT AVAILABLE | No completed real paired human benchmark |

The GitHub Actions digest is a reviewable artifact only. It does not publish posts, contact customers, or verify changes outside the synthetic dataset. Human review is required before using any generated claim or marketing recommendation.

The test runner exited successfully; on this Windows machine, Streamlit's temporary-directory cleanup printed a permissions warning after completion. The warning did not affect test results or database integrity.
