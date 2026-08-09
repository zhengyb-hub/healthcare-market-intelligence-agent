# CV Evidence

> Environment: **Synthetic Evaluation / Portfolio**, not live production usage.

## Active Healthcare IT Vendors

Metric: Active Healthcare IT Vendors

CV Value: 12

Definition: Vendors with status Active.

Formula: COUNT(vendors WHERE status='Active')

Data Source: SQLite analytics_service snapshot

Database Table / File: vendors

Sample Size: 12

Evaluation Period: Current database snapshot

Synthetic / Real: Synthetic evaluation

How to Reproduce: `python scripts/export_cv_metrics.py`

Limitations: Portfolio evaluation only; do not describe as client production usage.

## Evidence Records

Metric: Evidence Records

CV Value: 183

Definition: All persisted Evidence records.

Formula: COUNT(evidence)

Data Source: SQLite analytics_service snapshot

Database Table / File: evidence

Sample Size: 183

Evaluation Period: Current database snapshot

Synthetic / Real: Synthetic evaluation

How to Reproduce: `python scripts/export_cv_metrics.py`

Limitations: Portfolio evaluation only; do not describe as client production usage.

## Structured Competitor Briefs

Metric: Structured Competitor Briefs

CV Value: 12

Definition: All persisted structured competitor Briefs.

Formula: COUNT(competitor_briefs)

Data Source: SQLite analytics_service snapshot

Database Table / File: competitor_briefs

Sample Size: 12

Evaluation Period: Current database snapshot

Synthetic / Real: Synthetic evaluation

How to Reproduce: `python scripts/export_cv_metrics.py`

Limitations: Portfolio evaluation only; do not describe as client production usage.

## Claim-Level Source Traceability

Metric: Claim-Level Source Traceability

CV Value: 87.5%

Definition: Claim-level source traceability across reviewed Claims; support level is independent.

Formula: traceable_claim_count / reviewed_claim_count * 100

Data Source: SQLite analytics_service snapshot

Database Table / File: claims, competitor_briefs, evidence_packs, evidence

Sample Size: 8

Evaluation Period: Current database snapshot

Synthetic / Real: Synthetic evaluation

How to Reproduce: `python scripts/export_cv_metrics.py`

Limitations: The reviewed sample contains one completed synthetic Brief review; the frozen Phase 5 tasks still require human review before a fixed-set rate can be reported.

## Median Brief Preparation Time Reduction

Metric: Median Brief Preparation Time Reduction

CV Value: NOT AVAILABLE

Definition: Median reduction between comparable paired Manual and AI-assisted workflows.

Formula: (manual median - AI median) / manual median * 100

Data Source: SQLite analytics_service snapshot

Database Table / File: benchmark_runs

Sample Size: 0

Evaluation Period: Current benchmark history

Synthetic / Real: Synthetic evaluation workflow; manually entered human timing

How to Reproduce: `python scripts/export_cv_metrics.py`

Limitations: No valid paired sample is available; do not use this KPI on a CV.

## Recommended English CV bullets

1. Built a healthcare IT intelligence workflow covering 12 synthetic vendor profiles and 183 synthetic evidence records, generating 12 structured competitor briefs.
2. Implemented Streamlit and GitHub Actions validation, achieving 87.5% claim-level source traceability across 8 reviewed synthetic-evaluation claims.

The preparation-time claim must not be used until at least five complete comparable paired runs exist.
