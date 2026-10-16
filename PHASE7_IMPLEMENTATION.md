# Phase 7 — Evidence-to-Activation

## Outcome

Version `1.2.0` extends the evidence-grounded intelligence workflow into marketing activation without bypassing source identity or human review.

## Capabilities

- Evidence-to-evidence competitor change detection with idempotent fingerprints
- Previous/latest Evidence comparison and significance classification
- Marketing Action Briefs with campaign thesis, content gaps, differentiation, claim guardrails, and a 30-day plan
- LinkedIn, short-video, thought-leadership, email, and sales content opportunities
- Weekly Intelligence Digests with changes, implications, opportunities, and next actions
- CLI automation plus a scheduled GitHub Actions digest artifact
- Markdown export with retained Evidence IDs
- Deterministic no-key Demo outputs

## Architecture

New schema v6 tables persist `competitor_changes`, `marketing_action_briefs`, `content_opportunities`, and `weekly_digests`. Business rules live in `activation_services.py`; SQLite mapping lives in `activation_repositories.py`. The UI adds Intelligence → Changes and the Activation workspace.

## Trust boundary

Change detection is a review signal derived from successive records, not proof of a market-wide change. Every activation output retains the Evidence IDs that support it, preserves synthetic provenance, and repeats the monitored-dataset limitation.
