# Portfolio Guide

## One-line positioning

An evidence-grounded healthcare IT market intelligence product that turns structured sources into traceable, reviewable, and exportable competitor intelligence.

## 60-second portfolio story

Healthcare IT competitor research is not only a generation problem; it is an evidence-governance and workflow problem. I designed a product that stores Vendor and Evidence identities, validates and deduplicates sources, builds reproducible Evidence Packs, generates structured Claims, checks every citation against the originating Pack, separates fact from inference and recommendation, and routes outputs through human review before export.

The final portfolio release demonstrates the full Evidence → Decision workflow with 12 synthetic Vendors, 183 Evidence records, 12 Briefs, 120 Claims, and zero invalid citations in current structured validation. It also shows measurement discipline: because real paired human timing is incomplete, efficiency KPIs remain `NOT AVAILABLE`.

## Problem, product, workflow, stack, evaluation

| Dimension | Portfolio evidence |
|---|---|
| Problem | Fragmented healthcare IT research, weak source traceability, inconsistent reuse across marketing and sales |
| Product | Streamlit decision workspace with Vendor, Evidence, Market, Brief, Review, and Analytics workflows |
| AI role | Optional structured intelligence generation constrained by Evidence Packs and post-generation validation |
| Human role | Claim and Brief review, revision, approval, and finalisation |
| Data | Additive SQLite schema v5.0 with typed repositories and synthetic provenance |
| Evaluation | Reproducible snapshot, integrity checks, AppTest, E2E workflows, metric audit, and honest Benchmark gating |

## Recommended demo path

1. **Overview:** explain monitored scope and required action in under 20 seconds.
2. **Vendor:** open one Vendor and show Evidence-backed solution coverage and freshness.
3. **Evidence:** show validation, authority, quality, freshness, source URL, and related Claims.
4. **Market Map:** explain that coverage is evidence count in the monitored dataset—not market share.
5. **Compare:** open the saved three-Vendor comparison and move from coverage to analysis.
6. **Brief:** show Claim types, support levels, citations, review, and export.
7. **Analytics:** show 0 invalid citations and the reviewed traceability denominator.
8. **Benchmark:** end by showing why unavailable efficiency metrics are not rendered as 0%.

## Role-based final review

### Healthcare IT Marketing Manager

- **Value:** creates one place to monitor messages, solutions, case/procurement signals, and reusable Briefs.
- **Immature:** no live source ownership, scheduled refresh, or team collaboration.
- **Potential confusion:** Market Map coverage could be mistaken for market share; the UI and docs now state the boundary next to the map.
- **Remove:** low-value duplicate distribution tables and implementation-phase copy were removed from Overview.
- **Improve later:** approved source refresh and campaign-specific output templates.

### Market Intelligence Analyst

- **Value:** Evidence identity, Pack reproducibility, citation scope, duplicate retention, quality/freshness rules, and human review make conclusions auditable.
- **Immature:** synthetic sources do not establish real-market validity; the manually reviewed traceability sample is small.
- **Potential confusion:** support level and traceability are different measures; the UI now states both definitions together.
- **Remove:** raw JSON as the primary reading experience; JSON remains only for technical detail and export.
- **Improve later:** reviewer calibration, longitudinal Evidence, and source-health monitoring.

### Sales Enablement Manager

- **Value:** reuses the same reviewed Claims and sources across detailed, Executive, and Sales outputs without regenerating facts.
- **Immature:** no CRM, account context, permissions, or content approval workflow.
- **Potential confusion:** recommendations are not verified facts; the Opportunity view now separates FACT/EVIDENCE, INFERENCE, and RECOMMENDATION.
- **Remove:** dozens of row-level actions; the Review page now focuses action on one selected item.
- **Improve later:** approved account-level context and controlled publishing.

### Singapore AI Marketing / MarTech Recruiter

- **Value:** demonstrates business framing, domain taxonomy, persistent data design, evidence-grounded AI, human-in-the-loop UX, Analytics, evaluation governance, testing, and productisation.
- **Immature:** not hosted, not multi-user, and not validated on production healthcare data.
- **Potential confusion:** portfolio metrics could be misread as client impact; synthetic scope and Benchmark limits are repeated in the UI, README, evaluation artifacts, and release docs.
- **Remove:** student-demo visual signals, 13 peer tabs, large phase descriptions, and decorative emoji.
- **Improve later:** approved screenshots, deployment walkthrough, and real paired workflow evaluation.

## Portfolio readiness

The repository is suitable for formal portfolio presentation as a **Portfolio Release Candidate**. The principal remaining evaluation gap is real paired human timing; the principal presentation gap is final static screenshot capture in an unrestricted local browser. Neither is a core-program defect.
