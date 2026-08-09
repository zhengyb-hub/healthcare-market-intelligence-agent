# Portfolio Screenshot Guide

Use this deterministic guide to capture consistent portfolio images from the same synthetic database without changing Evaluation results.

## Capture setup

1. Rebuild the deterministic dataset using the commands in `README.md`.
2. Run `streamlit run app.py` without `OPENAI_API_KEY`.
3. Use a desktop browser at 1440 × 1000 or a similar 16:10 viewport.
4. Keep browser zoom at 100% and the Streamlit sidebar expanded.
5. Confirm the top banner says `DEMO MODE · Synthetic Evaluation Data`.
6. Do not show the browser address bar, terminal, debug details, or Streamlit developer menu.
7. Capture PNG at native resolution. Use consistent light mode for every image.

## Required captures

| File name | Navigation and state | What must be visible | Suggested crop |
|---|---|---|---|
| `01-overview-command-center.png` | Overview, initial state | Product statement, four KPIs, recent intelligence, top of Watchlist | Full viewport from app header through first Watchlist cards |
| `02-vendor-intelligence.png` | Vendors; select the first active synthetic Vendor | Vendor header/status, key profile metadata, freshness, intelligence summary, timeline | Header through Intelligence Workspace and first timeline rows |
| `03-evidence-library.png` | Evidence; filters All; select a Valid/Fresh record with a source URL | Filter row, bounded library table, Evidence detail tabs, validation/freshness badges | Filter row through Metadata detail |
| `04-market-map.png` | Market → Market Map; all Vendors/categories; minimum 1 | Vendor × Solution matrix, legend, monitored-dataset caveat, selected-cell detail | Matrix plus selected cell metrics |
| `05-vendor-comparison.png` | Market → Compare; open the saved three-Vendor comparison; Overview tab | Workflow cue, saved comparison selector, three-Vendor overview table, synthetic/status badges | Comparison header through overview table |
| `06-competitor-brief.png` | Briefs → Competitor Briefs; open a single-Vendor Brief; Executive Summary tab | Library table, Brief status, summary, Claim/traceability metrics, citation validation PASS | Selected Brief header through validation state |
| `07-claim-traceability.png` | Briefs → Competitor Briefs; same Brief; Evidence Citations tab | Claim type/support labels, Evidence IDs, no invalid citation error | Two or three expanded Claim citation rows; avoid excessive page length |
| `08-analytics.png` | Analytics → Dashboard → Quality | Traceability denominator, reviewed/traceable Claims, invalid citations, Claim support and Evidence freshness charts | Quality tab header through both charts |

## Optional captures

- Intelligence → Watchlist with freshness metrics and alerts
- Market → Opportunities with FACT/EVIDENCE, INFERENCE, and RECOMMENDATION callouts
- Review → Claims with one focused review form and Open Evidence expander
- Settings → Runtime & Data showing deterministic no-key mode

## Final image QA

- Counts reconcile to 12 active Vendors, 183 Evidence records, 171 validated Evidence, 12 Briefs, and 120 Claims.
- Invalid Citations shows 0.
- Traceability is labeled as an Evaluation metric or shows its 7/8 denominator.
- Manual Median, AI-Assisted Median, Time Reduction, and Speed Multiple show `NOT AVAILABLE`.
- Synthetic labels are visible.
- No real company, hospital, procurement, client, patient, or production claim is implied.
- No error banner, raw stack trace, clipped table, horizontal page scrollbar, or large unused whitespace is visible.
