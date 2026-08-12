# Release Checklist — 1.1.0

Release classification: **Public Portfolio Release**
Not classified as: Production Ready

| Check | Status | Evidence |
|---|---|---|
| Application starts | PASS | Live Streamlit health endpoint returned HTTP 200 / `ok` |
| Demo works | PASS | Phase 6 E2E and AppTest |
| No API key works | PASS | Phase 6 all-workspace AppTest with key absent |
| Database works | PASS | SQLite bootstrap and repository tests |
| Exports work | PASS | Markdown, JSON, and CSV Phase 6 E2E assertions |
| All pages load | PASS | Nine primary workspaces plus inner workspace AppTest |
| No broken button | PASS | Core action services exercised by E2E tests; controls rendered across 22 AppTest states |
| No dead route | PASS | Nine-route AppTest |
| No debug content | PASS | Repository scan; technical error detail is collapsed |
| No secrets | PASS | Key/private-key/sensitive-medical-data pattern scan returned no matches |
| README works | PASS | Final setup, run, test, export, limitation, and portfolio sections |
| Tests pass | PASS | 67 passed / 0 failed; Phase 5 baseline was 61 / 0 |
| Synthetic labels visible | PASS | Persistent global banner and record-level status |
| Metrics consistent | PASS | Evaluation artifacts use the AnalyticsService snapshot; main DB counts unchanged after evaluation rerun |
| Traceability works | PASS | Claim/Evidence E2E and current 0 invalid citations |
| Benchmark limits honest | PASS | Manual/AI efficiency KPIs remain NOT AVAILABLE |
| Portfolio screenshots | GUIDE READY | Deterministic eight-screen capture guide supplied |

## Release blockers

Any failed full-suite test, data-integrity mismatch, Streamlit startup failure, AppTest exception, invalid citation, exposed secret, or changed Evaluation count blocks release sign-off.

The absence of a completed real paired human Benchmark remains an **Evaluation limitation**, not a core-program blocker, provided every associated KPI remains `NOT AVAILABLE`.

## Final sign-off

- Full suite: `67 passed / 0 failed`
- Data Integrity: `PASS`
- Streamlit Startup: `PASS`
- AppTest: `PASS` — 22 page/workspace states, 0 exceptions
- Demo Mode: `PASS`
- No API Key Mode: `PASS`
- Exports: `PASS`
- Invalid Citations: `0`
- Main database after idempotence check: 12 Vendors, 183 Evidence records, 12 Briefs, 120 Claims
- Benchmark: 6 DRAFT AI observations, 0 complete comparable pairs; time KPIs `NOT AVAILABLE`
