# Metric Audit

All results below are calculated from the current SQLite database. The environment is synthetic evaluation, not production usage.

## 180 vs 183 reconciliation

Phase 2 seeded 180 Evidence records. Phase 4 added three distinct workflow/freshness Evidence records through EvidenceService, producing the current total of 183. No migration-created rows were found; duplicate members remain persisted and are reported separately rather than deleted.

| Metric | Definition | SQL / Formula | Included Records | Excluded Records | Actual Result |
| --- | --- | --- | --- | --- | ---: |
| vendor_count | All Vendor records. | COUNT(vendors) | Every Vendor status and environment. | None. | 12 |
| active_vendor_count | Vendors with status Active. | COUNT(vendors WHERE status='Active') | Active Vendors. | Inactive or archived Vendors. | 12 |
| evidence_count | All persisted Evidence records. | COUNT(evidence) | Valid, Warning, Invalid, primary, duplicate, and synthetic records. | None. | 183 |
| validated_evidence_count | Evidence that passed both workflow and validation status checks. | COUNT(evidence WHERE evidence_status='Validated' AND validation_status='Valid') | Valid Evidence, including explicitly flagged duplicate records. | Warning/Needs Review and Invalid/Rejected records. | 171 |
| duplicate_evidence_count | Evidence records linked to a canonical Evidence record. | COUNT(evidence WHERE duplicate_of_evidence_id <> '') | Duplicate member records. | Primary/canonical records. | 6 |
| brief_count | All persisted structured competitor Briefs. | COUNT(competitor_briefs) | Every Brief type/status in the evaluation database. | None. | 12 |
| final_brief_count | Briefs in FINAL workflow state. | COUNT(competitor_briefs WHERE status='FINAL') | Final Briefs. | Draft, in-review, revision, and approved Briefs. | 1 |
| claim_count | All Claims generated for structured Briefs. | COUNT(claims) | Every support and review status. | None. | 120 |
| supported_claim_count | Claims classified SUPPORTED. | COUNT(claims WHERE support_level='SUPPORTED') | Supported Claims. | Other support levels. | 44 |
| partially_supported_claim_count | Claims classified PARTIALLY_SUPPORTED. | COUNT(claims WHERE support_level='PARTIALLY_SUPPORTED') | Partially supported Claims. | Other support levels. | 64 |
| unsupported_claim_count | Claims classified UNSUPPORTED. | COUNT(claims WHERE support_level='UNSUPPORTED') | Unsupported Claims. | Other support levels. | 12 |
| invalid_citation_count | Citation references that are missing or outside the Claim's Evidence Pack. | COUNT(each cited Evidence ID that does not exist or is not in the owning Evidence Pack) | All Claim citation references. | Empty unsupported Claims are not invalid citations. | 0 |
| reviewed_claim_count | Claims explicitly reviewed or included in a completed Brief review. | COUNT(claims WHERE reviewed_at <> '' OR owning Brief review is complete) | Claims with a review timestamp plus every Claim in a completed Brief review. | Automatically classified Claims in unreviewed Briefs. | 8 |
| traceable_claim_count | Reviewed Claims with at least one citation where every Evidence ID exists and belongs to the owning Evidence Pack. | COUNT(traceable reviewed Claims) | Reviewed Claims with valid pack-contained Evidence identities. | Pending Claims, empty citations, missing Evidence, and out-of-pack citations. | 7 |
| traceability_rate | Claim-level source traceability across reviewed Claims; support level is independent. | traceable_claim_count / reviewed_claim_count * 100 | Reviewed Claims only. | Pending Claims. | 87.5 |
| comparison_count | Structured Briefs of type COMPARISON. | COUNT(competitor_briefs WHERE brief_type='COMPARISON') | Comparison Briefs. | Single-Vendor Briefs. | 4 |
| opportunity_count | Persisted Opportunity hypotheses. | COUNT(opportunities) | All review statuses. | None. | 5 |
| executive_brief_count | Persisted Executive Brief outputs. | COUNT(executive_briefs) | All Executive Brief outputs. | None. | 6 |
| sales_enablement_count | Persisted Sales Enablement outputs. | COUNT(sales_enablement_outputs) | All Sales outputs. | None. | 6 |
| review_count | Briefs with a completed review timestamp. | COUNT(brief_reviews WHERE review_completed_at <> '') | Completed Brief reviews. | Started or absent reviews. | 1 |
| average_review_time | Mean positive measured minutes across completed Brief reviews. | AVG(brief_reviews.review_minutes WHERE completed AND review_minutes > 0) | Completed reviews with a positive measured duration. | Incomplete reviews and zero-duration demo timestamps. | NOT AVAILABLE |
| average_edit_count | Mean revision count across completed Brief reviews. | AVG(brief_reviews.revision_count WHERE completed) | Completed reviews. | Incomplete reviews. | 0 |
| finalisation_rate | Share of all Briefs in FINAL state. | final_brief_count / brief_count * 100 | All Briefs. | None. | 8.333 |

## Environment classification

These are Evaluation Metrics from a synthetic portfolio dataset. They must not be described as live client or production usage.
