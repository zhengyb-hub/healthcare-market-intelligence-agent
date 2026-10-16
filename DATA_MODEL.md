# HEALTHCARE DATA MODEL

## 1. Scope

Phase 2 established Vendor, Evidence, and SolutionCategory. Phase 3 adds EvidencePack, Claim, CompetitorBrief, VendorIntelligenceProfile, and GenerationLog:

```text
Vendor 1 ---- * Evidence * ---- * SolutionCategory
Vendor * ---- * EvidencePack 1 ---- * CompetitorBrief 1 ---- * Claim
                                  |                       |
                                  +---- GenerationLog     +---- * Evidence (by stable ID)
Vendor 1 ---- * VendorIntelligenceProfile ---- 1 CompetitorBrief
```

- A Vendor may exist before Evidence is collected.
- Every Evidence record must reference one existing Vendor.
- Evidence may reference one or more Solution Categories.
- A Vendor's `solution_categories` are derived from its persisted Evidence. The code does not hard-code that a named Vendor owns a particular solution.
- Synthetic demo mappings are created by explicitly synthetic Evidence records.

Basic Claim review state is stored on Claim. Full review history is stored in Phase 4 entities, and Phase 5 benchmark observations are stored in `benchmark_runs`.

## 2. Persistence

SQLite database: `data/healthcare_intelligence.db`

Current schema version: `6.0`, recorded in `schema_metadata`. Earlier sections below document the additive Phase 2–5 foundation; Phase 7 adds marketing-activation tables and reference checks.

Tables:

- `solution_categories`
- `vendors`
- `evidence`
- `evidence_packs`
- `competitor_briefs`
- `claims`
- `vendor_intelligence_profiles`
- `generation_logs`
- `feed_events`
- `watchlist_entries`
- `opportunities`
- `duplicate_groups`, `duplicate_group_members`
- `brief_reviews`, `claim_review_notes`
- `saved_comparisons`
- `executive_briefs`
- `sales_enablement_outputs`
- `usage_events`
- `audit_events`
- `benchmark_runs`

## Phase 5 BenchmarkRun

`benchmark_runs` stores one Manual or AI-assisted observation per frozen task pair. It preserves the exact Vendor IDs, Evidence IDs, output requirement, workflow-specific stage times, total minutes, task/sample shape, generated Brief ID, review result, edit/review quality fields, measurement method, completion state, comparability decision, notes, timestamps, and synthetic flag.

The unique `(pair_id, workflow_type)` constraint prevents multiple competing observations for one side of a pair. Only pairs where both rows are `COMPLETE` and `COMPARABLE` enter median, mean, min, max, standard-deviation, time-saved, time-reduction, and speed-multiple calculations.
- `schema_metadata`

SQLite JSON text is used for controlled lists such as target customer types, solution category IDs, duplicate reasons, and validation messages. Repository methods perform serialisation and deserialisation. Foreign keys are enabled on every connection.

The application uses:

```text
UI
-> VendorService / EvidenceService
-> VendorRepository / EvidenceRepository / SolutionCategoryRepository
-> Database
-> SQLite
```

Streamlit session state is not the system of record.

## 3. Vendor

Implementation: `src/healthcare/models.py::Vendor`

Persistence table: `vendors`

| Field | Type | Required | Definition |
|---|---|---:|---|
| `vendor_id` | string | Yes | Stable unique identifier. Generated UUID-based IDs are used for new records; deterministic IDs are used for demo fixtures. Vendor name is not the primary key. |
| `vendor_name` | string | Yes | Human-readable company/vendor name. Duplicate names are allowed because names may change or collide. |
| `vendor_type` | enum string | Yes | Controlled Vendor type. |
| `primary_market` | string | Yes | Primary geographic, institutional, or segment focus described without implying verified market leadership. |
| `company_summary` | string | Yes | Concise Vendor description. |
| `headquarters` | string | Yes | Headquarters or declared location text. |
| `website` | URL string | Yes | HTTP/HTTPS Vendor website. |
| `solution_categories` | list of category IDs | Derived | Distinct categories found in the Vendor's persisted Evidence. Not stored as a Vendor-authored claim. |
| `target_customer_types` | list of enum strings | Yes | Target customer groups. |
| `evidence_count` | integer | Derived/stored | Count of non-archived Evidence currently linked to the Vendor. Refreshed after Evidence creation. |
| `last_updated` | ISO timestamp | Yes | Latest relevant stored Evidence update, or Vendor creation/update when no Evidence exists. |
| `created_at` | ISO timestamp | Yes | Record creation timestamp. |
| `updated_at` | ISO timestamp | Yes | Last Vendor record or metric update timestamp. |
| `status` | enum string | Yes | `Active` or `Archived`. |
| `is_synthetic` | boolean | Yes | Distinguishes demonstration records from real records. |

### Vendor types

- Healthcare IT Vendor
- Hospital Software Vendor
- Healthcare Data Vendor
- Digital Health Solution Provider
- Integrated Healthcare Technology Provider
- Other

### Target customer types

- Hospital
- Healthcare Group
- Regional Health Authority
- Government
- Medical Institution
- Insurance / Payer
- Other

### Vendor lifecycle

- `create`: validates and persists a new stable ID.
- `read`: loads one Vendor or lists Vendors.
- `update`: validates and updates mutable descriptive fields.
- `archive`: changes status to `Archived`; no physical delete is exposed.
- Evidence remains linked when a Vendor is archived.

## 4. SolutionCategory

Implementation: `src/healthcare/models.py::SolutionCategory`

Configuration: `config/healthcare_solution_taxonomy.json`

Persistence table: `solution_categories`

| Field | Type | Required | Definition |
|---|---|---:|---|
| `category_id` | string | Yes | Stable taxonomy identifier used by Evidence. |
| `name` | string | Yes | Display name. Unique within the taxonomy. |
| `description` | string | Yes | Scope definition for consistent classification. |
| `parent_id` | category ID/null | No | Optional parent category, reserved for later hierarchy use. |
| `status` | string | Yes | `Active` in the Phase 2 taxonomy. |
| `created_at` | ISO timestamp | Yes | Persistence timestamp. |
| `updated_at` | ISO timestamp | Yes | Last taxonomy entry update timestamp. |

### Phase 2 taxonomy

| ID | Name |
|---|---|
| `his` | HIS |
| `emr_ehr` | EMR / EHR |
| `clinical_information_systems` | Clinical Information Systems |
| `hospital_management` | Hospital Management |
| `healthcare_data_platform` | Healthcare Data Platform |
| `regional_healthcare_platform` | Regional Healthcare Platform |
| `digital_hospital` | Digital Hospital |
| `smart_healthcare` | Smart Healthcare |
| `patient_services` | Patient Services |
| `healthcare_analytics` | Healthcare Analytics |
| `healthcare_cloud` | Healthcare Cloud |
| `medical_insurance_information_systems` | Medical Insurance Information Systems |
| `data_governance` | Data Governance |
| `interoperability_integration` | Interoperability / Integration |
| `other` | Other |

The taxonomy is Vendor-independent. Category-to-Vendor relationships arise only through Evidence or explicitly synthetic demo Evidence.

## 5. Evidence

Implementation: `src/healthcare/models.py::Evidence`

Persistence table: `evidence`

| Field | Type | Required | Definition |
|---|---|---:|---|
| `evidence_id` | string | Yes | Stable unique Evidence identifier. UUID-based for new records, deterministic for demo fixtures. |
| `vendor_id` | Vendor ID | Yes | Foreign key to an existing Vendor. Orphan Evidence is rejected. |
| `source_type` | enum string | Yes | Controlled source family. Import mechanism may be represented as CSV/JSON Import. |
| `source_title` | string | Yes | Evidence/document/page title. |
| `source_url` | URL string | Conditional | Valid HTTP/HTTPS URL when present. Missing linkable-source URLs produce warnings; Manual/CSV/JSON imports may omit it. |
| `publication_date` | YYYY-MM-DD | Yes | Date the source was published or issued. |
| `collected_at` | ISO date/timestamp | Yes | Date/time the system received the Evidence. |
| `raw_text` | string | Yes | Source text as entered/imported. Empty raw text is invalid. |
| `cleaned_text` | string | Derived | Whitespace-normalised text capped at 20,000 characters. |
| `summary` | string | Yes | User/import-provided summary or deterministic text excerpt. No AI summary is generated in Phase 2. |
| `solution_categories` | list of category IDs | Recommended | Categories validated against the active taxonomy. Missing categories produce a warning; unknown IDs are invalid. |
| `hospital_name` | string | No | Hospital referenced by a case or project. |
| `procurement_entity` | string | No | Issuing procurement/tender organisation. |
| `project_name` | string | No | Named project or implementation. |
| `contract_value` | decimal string | No | Non-negative contract value. Stored as text to avoid binary floating-point loss. |
| `currency` | string | Conditional | Required when `contract_value` exists. |
| `evidence_status` | enum string | Yes | Lifecycle state. Automatically aligned to validation when first created. |
| `validation_status` | enum string | Yes | `Valid`, `Warning`, or `Invalid`, derived by the validation service. |
| `source_authority` | enum string | Yes | Transparent `High`, `Medium`, or `Low` source class; not an accuracy score. |
| `traceable` | boolean | Derived | Evidence-level provenance flag indicating a valid source URL. It is not Claim → Evidence traceability. |
| `content_hash` | SHA-256 string | Derived | Hash of case-folded, whitespace-normalised cleaned text. |
| `created_at` | ISO timestamp | Yes | Evidence record creation time. |
| `updated_at` | ISO timestamp | Yes | Last Evidence record update time. |
| `is_synthetic` | boolean | Yes | True for demonstration Evidence. |
| `duplicate_of_evidence_id` | Evidence ID/string | No | First matching Evidence when duplicate rules trigger. Empty when not marked duplicate. |
| `duplicate_reasons` | list of strings | No | Transparent matching reasons. |
| `validation_messages` | list of strings | No | Error and warning messages produced during validation/deduplication. |

### Evidence source types

- Vendor Website
- Solution Page
- Hospital Case Study
- Public Procurement
- Tender Announcement
- Industry Report
- Company Announcement
- Press Release
- News
- Manual Entry
- CSV Import
- JSON Import

App Store, App Rating, App Review, track ID, review score, and app category are not part of this schema.

### Evidence statuses

- `New`
- `Validated`
- `Needs Review`
- `Rejected`
- `Archived`

On creation:

- `Valid` Evidence defaults from `New` to `Validated`.
- `Warning` Evidence becomes `Needs Review`.
- `Invalid` Evidence becomes `Rejected`.

### Validation statuses

- `Valid`: no structural errors or warnings.
- `Warning`: usable but requires attention, such as a missing normally linkable URL or duplicate marker.
- `Invalid`: structural/business-rule error; retained as Rejected when it still has a valid Vendor reference.

Missing/invalid Vendor references are rejected before persistence because Evidence cannot be orphaned.

## 6. Source Authority

Source Authority classifies source provenance. It is deliberately simple, explainable, and not called an accuracy score.

### High

- official Vendor website or Solution page;
- government procurement/tender source;
- hospital official case study;
- official institutional announcement.

### Medium

- professional industry report;
- credible industry media/news;
- public company announcement or press release.

### Low

- manual observation without verified source URL;
- CSV/JSON import without verified original provenance;
- unclear secondary reproduction.

Authority does not validate the truth of every statement and must not be interpreted as model confidence. Later human review and Claim validation remain separate concepts.

## 7. Validation pipeline

```text
Manual / Pasted / CSV / JSON input
-> field normalisation
-> Vendor reference check
-> source/taxonomy/status validation
-> URL/date/text/contract validation
-> content hash
-> duplicate detection
-> Validation Status + Evidence Status
-> Repository
-> SQLite
-> Vendor metric refresh
```

Rules implemented:

- required Vendor and Evidence fields;
- valid Vendor reference;
- valid HTTP/HTTPS URL when supplied;
- valid ISO publication/collection dates;
- allowed source type;
- non-empty raw text;
- numeric non-negative contract value and currency pairing;
- allowed solution category IDs;
- allowed Evidence and Validation statuses;
- allowed source authority;
- allowed Vendor types, customer types, and status.

## 8. Deduplication

Deterministic duplicate checks run before persistence:

1. Same URL.
2. Exact cleaned-text duplicate.
3. Same SHA-256 content hash.
4. Near-duplicate title within the same Vendor using `difflib.SequenceMatcher` at `0.92` or higher.

Duplicate handling:

```text
detected duplicate
-> persist new Evidence record
-> set duplicate_of_evidence_id
-> record duplicate_reasons
-> validation_status = Warning
-> evidence_status = Needs Review
```

No embedding or AI similarity score is used. Duplicate Evidence is never silently deleted.

## 9. Imports

All import paths call `EvidenceService.create_evidence`, so they share validation, duplicate detection, persistence, and Vendor metric updates.

### Manual Entry / Pasted Text

The Streamlit form creates `Manual Entry` Evidence. A valid URL is optional; Evidence without one has `traceable = false` at the evidence-provenance level.

### CSV

- One row per Evidence record.
- `vendor_id` must reference an existing Vendor.
- `solution_categories` accepts JSON-list or semicolon/pipe/comma-separated IDs.
- Missing `source_type` defaults to `CSV Import`.
- Rows that cannot be persisted are reported as rejected; valid/Warning/Invalid non-orphan rows may be persisted.

### JSON

- Accepts a list of Evidence objects or `{ "evidence": [...] }`.
- Missing `source_type` defaults to `JSON Import`.
- Uses the same row result behavior as CSV.

## 10. Synthetic data

The deterministic demo seed contains:

```text
Vendors: 12
Evidence: 180
Solution Categories: 15
Marked Duplicates: 6
Validation: 168 Valid / 9 Warning / 3 Invalid
```

All demo Vendors and Evidence set `is_synthetic = true`. The UI displays a global demo warning and record-level synthetic warnings. Synthetic records must not be used as real Healthcare IT facts or production performance evidence.

## 11. Integrity checks

`scripts/check_data_integrity.py` verifies:

- duplicate Vendor IDs;
- duplicate Evidence IDs;
- missing Vendor references;
- invalid solution categories;
- invalid source types;
- missing content hashes;
- invalid dates;
- invalid statuses;
- orphan Evidence;
- duplicate hash groups whose later records are not marked;
- Vendor evidence-count mismatches.

Validation distributions may legitimately contain Warning and Invalid demo samples while structural integrity still passes.

## 12. EvidencePack

Implementation: `src/healthcare/intelligence_models.py::EvidencePack`

An Evidence Pack is the immutable, reproducible input manifest for one generation. It stores `evidence_pack_id`, ordered `vendor_ids`, ordered `evidence_ids`, transparent `selection_criteria`, `contains_synthetic_data`, and `created_at`. It resolves Evidence by ID instead of copying source text.

## 13. Claim

Implementation: `src/healthcare/intelligence_models.py::Claim`

| Field | Definition |
|---|---|
| `claim_id` | Stable Claim ID. |
| `brief_id` | Owning structured Brief. |
| `vendor_id` | Optional Vendor subject; must belong to the Pack. |
| `claim_text` | Atomic assertion, interpretation, or action. |
| `claim_type` | `FACT`, `INFERENCE`, or `RECOMMENDATION`. |
| `evidence_ids` | Stored Evidence IDs used as the basis. |
| `traceable` | True only when all citations exist, are eligible, and belong to the Pack. |
| `support_level` | `SUPPORTED`, `PARTIALLY_SUPPORTED`, or `UNSUPPORTED`; recomputed by rules. |
| `review_status` | `PENDING`, `APPROVED`, `EDITED`, `REJECTED`, or `UNSUPPORTED`. |
| `explanation` | Evidence/support rationale. |
| `reviewed_at` | Last basic review action timestamp. |
| `created_at`, `updated_at` | Audit timestamps. |

`FACT` is an objectively stated item directly supported by Evidence. `INFERENCE` is an analytical interpretation. `RECOMMENDATION` proposes a marketing, positioning, or sales action based on Evidence and analysis.

## 14. CompetitorBrief

`CompetitorBrief` stores `brief_id`, title, ordered Vendor IDs, `VENDOR_INTELLIGENCE` or `COMPARISON` type, Evidence Pack ID, executive summary, named sections containing Claim IDs, generation timestamp, status, model, prompt version, and demo flag. Claims are persisted separately and hydrated by the repository. Markdown is an export, not the system of record.

## 15. VendorIntelligenceProfile

The profile links one Vendor to its generated Brief and stores company overview, section-to-Claim mapping, Evidence coverage counts, last intelligence update, and demo flag.

## 16. GenerationLog

The audit record stores generation ID, task type, Vendor IDs, Evidence Pack ID, exact Evidence IDs, model, prompt version, generation time, success/error, and demo flag. This is operational metadata, not a benchmark or quality score.

## 17. Phase 3 integrity

In addition to Phase 2 checks, `scripts/check_data_integrity.py` validates:

- every Pack Vendor/Evidence reference;
- every Brief Pack/Vendor reference;
- every Claim Brief/Vendor reference;
- every Claim Evidence ID and its membership in the Brief's Pack;
- Profile and Generation Log references;
- controlled Claim/Brief/review/task vocabularies;
- JSON-backed Phase 3 fields.

The Evidence field `traceable` continues to mean source-URL provenance. Claim `traceable` separately means valid Claim-to-Evidence linkage under the originating Evidence Pack.

## 18. FeedEvent

`FeedEvent` stores `feed_id`, controlled event type, optional Vendor/Evidence/Brief IDs, title, summary, source type, solution categories, event/creation dates, importance, synthetic flag, and a unique dedupe key. Feed events are emitted after persisted domain operations or deterministically backfilled from stored records.

## 19. Watchlist

`WatchlistEntry` stores a stable ID, unique Vendor ID, `watchlist_created_at`, `last_viewed_at`, Evidence-count baseline, and synthetic flag. New-Evidence counts compare current persisted Evidence with the baseline captured on follow/last view. Alerts are derived from the count and Feed events; there is no hard-coded alert table.

## 20. EvidenceAssessment

Evidence quality/freshness is calculated, not persisted as an opaque model score:

| Component | Points |
|---|---:|
| Source Authority | 0–3 |
| Recency | 0–3 |
| Completeness | 0–2 |
| Traceability | 0–1 |
| Relevance | 0–1 |

Total `HIGH >= 8`, `MEDIUM >= 5`, otherwise `LOW`. Freshness is `FRESH <= 90 days`, `AGING 91–180`, `OUTDATED > 180`. Thresholds are centralized internal rules, not industry standards.

## 21. DuplicateGroup

`duplicate_groups` stores group ID, primary Evidence ID, reasons, and creation time. `duplicate_group_members` stores every retained member with role `PRIMARY` or `SUPPORTING_COPY`. Groups join existing duplicate links, shared content hashes, and shared URLs. Primary selection is deterministic: Valid status, source authority, traceable URL, then stable creation/ID order.

## 22. Opportunity

| Field | Definition |
|---|---|
| `opportunity_id`, `opportunity_type`, `title` | Identity and one of five controlled hypothesis types. |
| `evidence_ids` | Existing stored Evidence IDs; empty bases are rejected. |
| `related_claim_ids`, `related_vendor_ids` | Stored input relationships. |
| `evidence_statement` | Dataset observation, kept separate from interpretation. |
| `inference` | Labelled analytical hypothesis. |
| `recommendation` | Labelled action to investigate/test. |
| `confidence_basis` | Transparent rule/count basis, never an unexplained AI score. |
| `review_status`, reviewer fields | `PENDING`, `APPROVED`, or `REJECTED` with note/time. |
| `is_synthetic` | True when any cited basis is synthetic. |

White-space Opportunities are explicitly scoped to the monitored Vendor set.

## 23. Review metadata

Brief states are `DRAFT`, `IN_REVIEW`, `NEEDS_REVISION`, `APPROVED`, and `FINAL`. `brief_reviews` stores reviewer, start/completion timestamps, measured review minutes, notes, revision count, and update time. `claim_review_notes` stores append-only reviewer/name/note/timestamp records. Existing Phase 3 Claim support and traceability remain separate from human status.

## 24. SavedComparison, ExecutiveBrief, and SalesEnablementOutput

- SavedComparison references one Comparison Brief and preserves selected Vendor IDs, Claim IDs, summary, creation time, and synthetic flag.
- ExecutiveBrief references one existing Brief and maps management sections to existing Claim IDs, plus recent Feed IDs and resolved Evidence IDs.
- SalesEnablementOutput stores six structured sections whose items preserve Claim type, support, Evidence IDs, and source Claim ID. Discovery questions and talking points are `RECOMMENDATION` items.

None of these views invokes a second analysis model.

## 25. UsageEvent and AuditEvent

UsageEvent records the controlled interaction type, entity, actor, metadata, timestamp, and synthetic flag. AuditEvent records controlled business event, actor, entity, related IDs, details, time, and synthetic flag. These are raw operational records for future analysis, not Phase 5 metrics.

## 26. Phase 4 integrity and boundary

Integrity checks now validate Phase 4 JSON, vocabularies, Vendor/Evidence/Claim/Brief references, duplicate-group roles, Opportunity Evidence, and synthetic propagation. Phase 4 does not calculate workflow benchmarks, time savings, ROI, or production performance rates; it also does not implement full accounts/permissions, external notifications, CRM integration, or the Phase 6 visual design system.
