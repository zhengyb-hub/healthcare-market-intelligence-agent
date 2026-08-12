# Claim to Evidence Traceability Specification

## Contract

Every Competitor Brief references one Evidence Pack. Every cited Evidence ID on a Claim must:

1. exist in the `evidence` table;
2. occur in that Brief's Evidence Pack;
3. have an allowed validation/lifecycle pair (`Valid` + `Validated`, or opted-in `Warning` + `Needs Review`);
4. resolve to source title, source type, publication date, Vendor, URL, summary, source text, and synthetic flag.

The LLM receives the exact stored Evidence IDs. Unknown IDs are rejected during structured-output validation, then checked again by the independent traceability validator after persistence.

## Evidence Pack eligibility

Default:

- include only `Valid` + `Validated` Evidence;
- exclude Invalid, Rejected, Archived, and records carrying `duplicate_of_evidence_id`;
- preserve source metadata and Evidence identity.

Optional Warning mode includes `Warning` + `Needs Review`. The Pack records that choice. Ranking is deterministic and explained in `selection_criteria`: authority High-to-Low, publication date newest-to-oldest, source type, then Evidence ID. Filters and per-Vendor limits are also recorded.

## Claim types

- `FACT`: direct objective statement. Evidence is mandatory.
- `INFERENCE`: analytical interpretation. Evidence basis is expected; absence is retained as unsupported.
- `RECOMMENDATION`: proposed action. Evidence basis is expected; absence is retained as unsupported.

These labels are displayed in UI and exports and are not interchangeable.

## Rule-based support assessment

| Condition | Support | Traceable |
|---|---|---:|
| FACT cites one or more eligible Valid records in the Pack | `SUPPORTED` | Yes |
| Inference/recommendation cites eligible records | `PARTIALLY_SUPPORTED` | Yes |
| Any Claim includes opted-in Warning Evidence | `PARTIALLY_SUPPORTED` | Yes |
| No Evidence IDs | `UNSUPPORTED` | No |
| Nonexistent, invalid, rejected, archived, or out-of-Pack ID | `UNSUPPORTED` | No |

The LLM-proposed `support_level` is validated syntactically but is not trusted as the final decision. `ClaimService` and `TraceabilityService` recompute it from stored data.

An unsupported inference/recommendation remains visibly marked so evidence gaps are auditable. An unsupported FACT causes Brief validation to fail and is omitted from final Markdown section content.

## Validator output

`TraceabilityService.validate_brief` returns total, supported, partially supported, unsupported, and traceable Claim counts; invalid-citation details/count; unsupported FACT Claim IDs; and `PASS` or `FAIL`.

`PASS` means there are no invalid citations and no unsupported FACTs. It is a structural traceability result, not a semantic accuracy score or production KPI.

## Human review

Claim review supports Approve, Reject, Edit, Claim-type change, Evidence-link add/remove, and Mark Unsupported. Review recomputes support. An unsupported Claim cannot be approved, and an explicit human `UNSUPPORTED` decision is not overwritten by later automatic validation. Claim status and timestamps are persisted with append-only reviewer notes.

Brief review uses `DRAFT`, `IN_REVIEW`, `NEEDS_REVISION`, `APPROVED`, and `FINAL`. Approval requires traceability `PASS` and no remaining `PENDING` supported/partially supported Claims. Unsupported analytical gaps may remain visible; unsupported FACTs still fail traceability.

## Phase 5 Claim-level Source Traceability Rate

The Claim-level metric is not the Brief-level `PASS` count. A reviewed Claim is traceable only when it cites at least one Evidence ID, every cited ID exists, every cited ID belongs to the owning Brief's Evidence Pack, and no invalid citation is present.

```text
Source Traceability Rate =
  Traceable Reviewed Claims / Total Reviewed Claims * 100
```

`Reviewed` means the Claim has an explicit review timestamp or belongs to a Brief with a completed review. Automatically classified unsupported Claims in unreviewed draft Briefs do not enter the denominator. Support level remains a separate distribution: a `PARTIALLY_SUPPORTED` Claim can still be fully traceable, while an evidence-free `UNSUPPORTED` Claim is not traceable.

## Demo and export rules

Deterministic demo Claims cite real synthetic Evidence IDs from the generated Pack and pass the same validator. Demo state remains visible on Evidence, Pack, Profile/Brief, and Generation Log.

- Markdown prints Claim type/support and inline Evidence IDs, followed by source details.
- JSON retains the entire structured Brief, Pack, Claim list, and resolved Evidence.
- CSV exports required Claim fields and semicolon-separated Evidence IDs.

## Phase 4 derived-product rules

- Market Map cells use only `Valid` + `Validated`, non-duplicate Evidence and expose every supporting ID.
- Opportunities require at least one existing Evidence ID. Their Evidence statement, Inference, and Recommendation are stored separately; related Claim/Vendor IDs must exist.
- Solution/market white space is scoped to the selected monitored Vendor set and must not be phrased as proof of a whole-market opportunity.
- Executive Brief sections reuse Claim IDs from one existing Competitor Brief. Unsupported FACTs and rejected Claims are excluded.
- Sales outputs reuse the same Brief Claims/Evidence. Generated discovery questions and talking points are explicitly `RECOMMENDATION` with the source Claim and Evidence IDs.
- Saved Detailed, Executive, and Sales comparison views reuse one Comparison Brief; they do not trigger three independent analyses.
- If any cited basis is synthetic, the derived Opportunity/Brief/Sales record is marked synthetic.

Phase 4 integrity validation checks all new Evidence/Claim/Vendor/Brief references and reports synthetic flag loss. These structural results remain distinct from accuracy, productivity, ROI, or production KPI measurement.
