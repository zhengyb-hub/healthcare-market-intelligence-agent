"""Operational Streamlit UI for the Healthcare intelligence product."""

from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from .bootstrap import DEFAULT_DATABASE_PATH, bootstrap_product_workflow
from .enums import (
    FEED_EVENT_TYPES,
    IMPORTANCE_LEVELS,
    OPPORTUNITY_TYPES,
    SOURCE_AUTHORITIES,
    SOURCE_TYPES,
    TARGET_CUSTOMER_TYPES,
    VALIDATION_STATUSES,
    VENDOR_TYPES,
    CLAIM_TYPES,
)
from .integrity import run_integrity_checks
from .ui_components import (
    demo_banner,
    empty_state,
    error_state,
    info_card,
    inject_design_system,
    metric_card,
    page_header,
    section_header,
    status_badge,
)


PRIMARY_NAVIGATION = (
    "Overview",
    "Intelligence",
    "Vendors",
    "Evidence",
    "Market",
    "Briefs",
    "Review",
    "Analytics",
    "Settings",
)
PORTFOLIO_VERSION = "1.0.0-rc1"


@st.cache_resource
def get_foundation(database_path: str):
    return bootstrap_product_workflow(
        database_path=database_path,
        seed_demo=True,
        seed_intelligence_demo=True,
        seed_workflow_demo=True,
    )


def _runtime_setting(name: str, default: str = "") -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        return str(st.secrets.get(name, default)).strip()
    except Exception:
        return default


def _category_maps(foundation):
    categories = foundation.category_repository.list_all()
    by_id = {category.category_id: category.name for category in categories}
    by_name = {category.name: category.category_id for category in categories}
    return categories, by_id, by_name


def _category_names(category_ids: list[str], by_id: dict[str, str]) -> str:
    return ", ".join(by_id.get(item, item) for item in category_ids)


def _refresh() -> None:
    st.cache_data.clear()
    st.rerun()


def _log_view_once(workflow, event_type: str, entity_type: str, entity_id: str, synthetic: bool) -> None:
    key = f"logged_{event_type}_{entity_id}"
    if not st.session_state.get(key):
        workflow.usage_service.record(
            event_type,
            entity_type,
            entity_id,
            is_synthetic=synthetic,
        )
        st.session_state[key] = True


def render_overview(foundation, intelligence, workflow, by_id: dict[str, str]) -> None:
    page_header(
        "Healthcare market intelligence",
        "Evidence-grounded competitor intelligence",
        "A decision workspace for healthcare IT marketing, market intelligence, and sales enablement teams.",
    )
    stats = foundation.statistics()
    analytics = workflow.analytics_service.snapshot()
    queue = workflow.brief_workflow_service.queue()
    watchlist = workflow.watchlist_service.list_details()
    vendors = foundation.vendor_service.list_vendors(include_archived=True)
    vendor_names = {vendor.vendor_id: vendor.vendor_name for vendor in vendors}

    kpis = st.columns(4)
    with kpis[0]:
        metric_card("Active vendors", analytics["active_vendor_count"], "Current monitored scope")
    with kpis[1]:
        metric_card("Evidence records", analytics["evidence_count"], f"{analytics['validated_evidence_count']} validated")
    with kpis[2]:
        metric_card("Competitor briefs", analytics["brief_count"], f"{analytics['claim_count']} structured claims")
    with kpis[3]:
        traceability = _metric_value(analytics["traceability_rate"], "%").upper()
        metric_card(
            "Source traceability",
            traceability,
            f"Evaluation metric · {analytics['traceable_claim_count']} / {analytics['reviewed_claim_count']} reviewed claims",
        )

    left, right = st.columns([1.45, 1], gap="large")
    with left:
        section_header("What changed", "Most recent 8 signals")
        recent = workflow.feed_repository.list_all(limit=8)
        if not recent:
            empty_state(
                "No intelligence signals yet",
                "The feed is populated when Evidence, Briefs, and review events are recorded.",
                "Import Evidence or generate a Brief.",
            )
        for event in recent:
            vendor = vendor_names.get(event.vendor_id, "Portfolio-wide")
            info_card(
                event.title,
                event.summary or "No additional summary supplied.",
                f"{event.event_date} · {vendor} · {event.event_type} · {event.importance}",
            )
    with right:
        section_header("Watchlist", "Monitored priorities")
        if not watchlist:
            empty_state(
                "No Vendors on the watchlist",
                "Follow priority Vendors to surface new Evidence and freshness alerts here.",
                "Open Intelligence → Watchlist.",
            )
        for item in watchlist[:5]:
            freshness = "OUTDATED" if item["freshness"]["needs_intelligence_refresh"] else "FRESH"
            latest_signal = item["latest_procurement_signal"]
            info_card(
                item["vendor"].vendor_name,
                (
                    f"{item['new_evidence_since_last_view']} new Evidence · "
                    f"{latest_signal.source_title if latest_signal else 'No procurement signal'}"
                ),
                f"{freshness.replace('_', ' ')} · {item['evidence_count']} Evidence records",
            )

    section_header("Action required", "Queues that need human attention")
    attention = st.columns(4)
    with attention[0]:
        metric_card("Briefs awaiting review", len(queue["briefs_awaiting_review"]), "Review before decision use")
    with attention[1]:
        metric_card("Unsupported claims", len(queue["unsupported_claims"]), "Require evidence or removal")
    with attention[2]:
        metric_card("Evidence needs review", len(queue["evidence_needing_validation"]), "Validation status unresolved")
    with attention[3]:
        metric_card(
            "Outdated intelligence",
            sum(item["freshness"]["needs_intelligence_refresh"] for item in watchlist),
            "Watchlist profiles needing refresh",
        )

    section_header("Market snapshot", "Current synthetic evaluation dataset")
    chart_left, chart_right = st.columns(2, gap="large")
    with chart_left:
        st.markdown("#### Solution coverage")
        category_frame = pd.DataFrame(
            [
                {"Solution category": by_id.get(key, key), "Evidence": value}
                for key, value in stats["solution_categories"].items()
            ]
        ).set_index("Solution category")
        if category_frame.empty:
            empty_state("No solution coverage", "Validated Evidence has not been mapped to the healthcare taxonomy.")
        else:
            st.bar_chart(category_frame, color="#176b87")
    with chart_right:
        st.markdown("#### Evidence source distribution")
        source_frame = pd.DataFrame(
            stats["source_types"].items(), columns=["Source type", "Evidence"]
        ).set_index("Source type")
        if source_frame.empty:
            empty_state("No source distribution", "No Evidence sources are available to summarize.")
        else:
            st.bar_chart(source_frame, color="#5f8799")
    st.caption(
        "Coverage reflects Evidence in the monitored synthetic evaluation dataset and does not represent total market share."
    )


def render_vendor_library(foundation, intelligence, workflow, by_id: dict[str, str]) -> None:
    vendor_service = foundation.vendor_service
    page_header(
        "Understand competitors",
        "Vendor intelligence",
        "Search the monitored Vendor library, inspect evidence-backed profiles, and refresh structured intelligence.",
    )

    search_col, type_col, archive_col = st.columns([2, 1, 1])
    search = search_col.text_input("Search vendors", key="vendor_search")
    type_filter = type_col.selectbox("Vendor Type", ["All", *VENDOR_TYPES], key="vendor_type_filter")
    include_archived = archive_col.checkbox("Include archived", value=False)
    vendors = vendor_service.list_vendors(include_archived, search)
    if type_filter != "All":
        vendors = [vendor for vendor in vendors if vendor.vendor_type == type_filter]

    vendor_frame = pd.DataFrame(
        [
            {
                "Vendor ID": vendor.vendor_id,
                "Vendor": vendor.vendor_name,
                "Type": vendor.vendor_type,
                "Primary Market": vendor.primary_market,
                "Solutions": _category_names(vendor.solution_categories, by_id),
                "Evidence": vendor.evidence_count,
                "Status": vendor.status,
                "Synthetic": vendor.is_synthetic,
                "Last Updated": vendor.last_updated,
            }
            for vendor in vendors
        ]
    )
    if vendor_frame.empty:
        empty_state(
            "No Vendors match these filters",
            "The Vendor library has no records for the selected search and type.",
            "Clear the filters or create a Vendor below.",
        )
    else:
        st.caption(f"{len(vendor_frame)} matching Vendor(s)")
        st.dataframe(vendor_frame.head(100), width="stretch", hide_index=True)

    with st.expander("Create Vendor", expanded=False):
        with st.form("create_vendor_form", clear_on_submit=True):
            name = st.text_input("Vendor Name")
            vendor_type = st.selectbox("Vendor Type", VENDOR_TYPES)
            primary_market = st.text_input("Primary Market")
            summary = st.text_area("Company Summary")
            headquarters = st.text_input("Headquarters")
            website = st.text_input("Website", placeholder="https://example.com")
            customer_types = st.multiselect("Target Customers", TARGET_CUSTOMER_TYPES)
            is_synthetic = st.checkbox("Synthetic / demonstration vendor")
            submitted = st.form_submit_button("Create Vendor", type="primary")
            if submitted:
                try:
                    vendor = vendor_service.create_vendor(
                        {
                            "vendor_name": name,
                            "vendor_type": vendor_type,
                            "primary_market": primary_market,
                            "company_summary": summary,
                            "headquarters": headquarters,
                            "website": website,
                            "target_customer_types": customer_types,
                            "is_synthetic": is_synthetic,
                        }
                    )
                    st.success(f"Created {vendor.vendor_name} ({vendor.vendor_id}).")
                    _refresh()
                except ValueError as exc:
                    st.error(str(exc))

    all_vendors = vendor_service.list_vendors(include_archived=True)
    if not all_vendors:
        empty_state("No Vendors yet", "A Vendor is required before Evidence can be monitored.", "Create a Vendor above.")
        return
    options = {f"{vendor.vendor_name} · {vendor.vendor_id}": vendor for vendor in all_vendors}
    selected_label = st.selectbox("View Vendor", options=list(options))
    selected = options[selected_label]
    _log_view_once(workflow, "vendor_view", "Vendor", selected.vendor_id, selected.is_synthetic)

    section_header(selected.vendor_name, selected.vendor_type)
    vendor_badges = status_badge(selected.status)
    if selected.is_synthetic:
        vendor_badges += " " + status_badge("SYNTHETIC")
    st.markdown(vendor_badges, unsafe_allow_html=True)
    detail_left, detail_right = st.columns(2)
    detail_left.markdown(
        f"**Summary:** {selected.company_summary}\n\n"
        f"**Primary Market:** {selected.primary_market}\n\n"
        f"**Headquarters:** {selected.headquarters}\n\n"
        f"**Website:** {selected.website}"
    )
    detail_right.markdown(
        f"**Solution Categories:** {_category_names(selected.solution_categories, by_id) or 'No evidence-backed categories'}\n\n"
        f"**Target Customers:** {', '.join(selected.target_customer_types)}\n\n"
        f"**Evidence Count:** {selected.evidence_count}\n\n"
        f"**Last Updated:** {selected.last_updated}\n\n"
        f"**Status:** {selected.status}"
    )

    with st.expander("Edit Vendor", expanded=False):
        with st.form(f"edit_vendor_{selected.vendor_id}"):
            edit_name = st.text_input("Vendor Name", value=selected.vendor_name)
            edit_type = st.selectbox(
                "Vendor Type",
                VENDOR_TYPES,
                index=VENDOR_TYPES.index(selected.vendor_type),
            )
            edit_market = st.text_input("Primary Market", value=selected.primary_market)
            edit_summary = st.text_area("Company Summary", value=selected.company_summary)
            edit_headquarters = st.text_input("Headquarters", value=selected.headquarters)
            edit_website = st.text_input("Website", value=selected.website)
            edit_customers = st.multiselect(
                "Target Customers",
                TARGET_CUSTOMER_TYPES,
                default=selected.target_customer_types,
            )
            if st.form_submit_button("Save Vendor Changes"):
                try:
                    vendor_service.update_vendor(
                        selected.vendor_id,
                        {
                            "vendor_name": edit_name,
                            "vendor_type": edit_type,
                            "primary_market": edit_market,
                            "company_summary": edit_summary,
                            "headquarters": edit_headquarters,
                            "website": edit_website,
                            "target_customer_types": edit_customers,
                        },
                    )
                    st.success("Vendor updated.")
                    _refresh()
                except ValueError as exc:
                    st.error(str(exc))

    if selected.status != "Archived":
        if st.button("Archive Vendor", key=f"archive_{selected.vendor_id}"):
            vendor_service.archive_vendor(selected.vendor_id)
            st.success("Vendor archived. Evidence was retained.")
            _refresh()

    st.markdown("#### Intelligence Workspace")
    watch_entry = workflow.watchlist_service.repository.get_by_vendor(selected.vendor_id)
    watch_col, freshness_col = st.columns([1, 3])
    if watch_entry:
        if watch_col.button("Unfollow Vendor", key=f"unfollow_vendor_{selected.vendor_id}"):
            workflow.watchlist_service.unfollow(selected.vendor_id)
            _refresh()
    else:
        if watch_col.button("Follow Vendor", key=f"follow_vendor_{selected.vendor_id}"):
            workflow.watchlist_service.follow(selected.vendor_id)
            _refresh()
    freshness = workflow.quality_service.vendor_freshness(selected.vendor_id)
    freshness_status = "OUTDATED" if freshness["needs_intelligence_refresh"] else "FRESH"
    freshness_col.markdown(
        status_badge(freshness_status)
        + f" <span style='color:#5c6b78;font-size:.82rem'>Last Evidence: {freshness.get('latest_evidence_date') or 'Not available'}</span>",
        unsafe_allow_html=True,
    )
    profiles = intelligence.profile_repository.list_all(selected.vendor_id)
    briefs = [brief for brief in intelligence.brief_repository.list_all() if selected.vendor_id in brief.vendor_ids]
    evidence = foundation.evidence_service.list_evidence(vendor_id=selected.vendor_id)
    signals = [
        item for item in evidence
        if item.source_type in {
            "Hospital Case Study", "Public Procurement", "Tender Announcement",
            "Solution Page", "Company Announcement", "Industry Report",
        }
    ]
    st.markdown(
        f"**Intelligence Summary:** {profiles[0].company_overview if profiles else 'No profile generated'}  \n"
        f"**Briefs:** {len(briefs)} · **Latest Signals:** {len(signals)} · "
        f"**Last Intelligence Update:** {profiles[0].last_intelligence_update if profiles else 'Not generated'}"
    )
    with st.expander("Generate or refresh Vendor intelligence", expanded=not bool(profiles)):
        include_warning = st.checkbox(
            "Include Warning Evidence", key=f"intel_warning_{selected.vendor_id}"
        )
        api_key = _runtime_setting("OPENAI_API_KEY")
        model = _runtime_setting("OPENAI_MODEL", "gpt-5.6")
        st.caption(
            "Generation mode: OpenAI with deterministic fallback"
            if api_key else
            "Generation mode: deterministic structured demo · No API key required"
        )
        if st.button(
            "Generate Vendor Intelligence",
            type="primary",
            key=f"generate_vendor_intelligence_{selected.vendor_id}",
        ):
            try:
                with st.spinner("Processing Evidence → generating intelligence → validating Claims..."):
                    profile, _, traceability = intelligence.vendor_intelligence_service.generate(
                        selected.vendor_id,
                        include_warning=include_warning,
                        api_key=api_key,
                        model=model,
                    )
                st.success(f"Generated {profile.profile_id}; traceability {traceability['result']}.")
                _refresh()
            except (ValueError, RuntimeError) as exc:
                error_state(
                    "Intelligence generation failed",
                    "Review the Vendor Evidence and runtime configuration, then try again.",
                    str(exc),
                )
    if signals:
        st.markdown("#### Evidence Timeline")
        st.dataframe(
            pd.DataFrame([
                {
                    "Date": item.publication_date,
                    "Type": item.source_type,
                    "Title": item.source_title,
                    "Evidence ID": item.evidence_id,
                    "Validation": item.validation_status,
                }
                for item in signals[:30]
            ]),
            hide_index=True,
            width="stretch",
        )
    procurement_signals = [
        item for item in evidence
        if item.source_type in {"Public Procurement", "Tender Announcement"}
    ]
    case_signals = [item for item in evidence if item.source_type == "Hospital Case Study"]
    positioning_claims = []
    for brief in briefs:
        claim_by_id = {claim.claim_id: claim for claim in brief.claims}
        for section_name, claim_ids in brief.sections.items():
            if section_name in {"Positioning", "Market Positioning", "Positioning Analysis"}:
                positioning_claims.extend(
                    claim_by_id[claim_id] for claim_id in claim_ids if claim_id in claim_by_id
                )
    procurement_tab, cases_tab, positioning_tab, briefs_tab = st.tabs(
        ["Procurement Signals", "Case Study Signals", "Positioning", "Briefs"]
    )
    with procurement_tab:
        st.dataframe(pd.DataFrame([asdict(item) for item in procurement_signals]), hide_index=True)
    with cases_tab:
        st.dataframe(pd.DataFrame([asdict(item) for item in case_signals]), hide_index=True)
    with positioning_tab:
        st.dataframe(pd.DataFrame([asdict(item) for item in positioning_claims]), hide_index=True)
    with briefs_tab:
        st.dataframe(
            pd.DataFrame([
                {"Brief ID": item.brief_id, "Title": item.title, "Status": item.status, "Generated": item.generated_at}
                for item in briefs
            ]),
            hide_index=True,
        )


def render_evidence_library(
    foundation,
    intelligence,
    workflow,
    by_id: dict[str, str],
    by_name: dict[str, str],
) -> None:
    evidence_service = foundation.evidence_service
    vendors = foundation.vendor_service.list_vendors(include_archived=True)
    categories = foundation.category_repository.list_all()
    vendor_by_id = {vendor.vendor_id: vendor for vendor in vendors}

    page_header(
        "Ground every claim",
        "Evidence library",
        "Search, filter, validate, and inspect the source records used by intelligence outputs.",
    )
    filter_cols = st.columns(4)
    vendor_labels = ["All"] + [f"{v.vendor_name} · {v.vendor_id}" for v in vendors]
    selected_vendor_label = filter_cols[0].selectbox("Vendor", vendor_labels, key="evidence_vendor_filter")
    selected_vendor = (
        ""
        if selected_vendor_label == "All"
        else selected_vendor_label.rsplit(" · ", 1)[1]
    )
    selected_source = filter_cols[1].selectbox("Source Type", ["All", *SOURCE_TYPES], key="evidence_source_filter")
    selected_category_name = filter_cols[2].selectbox(
        "Solution Category",
        ["All", *(category.name for category in categories)],
    )
    selected_validation = filter_cols[3].selectbox(
        "Validation",
        ["All", *VALIDATION_STATUSES],
        key="evidence_validation_filter",
    )
    filter_cols_2 = st.columns([2, 1, 1])
    search = filter_cols_2[0].text_input("Search title or Evidence text", key="evidence_search")
    selected_authority = filter_cols_2[1].selectbox(
        "Authority", ["All", *SOURCE_AUTHORITIES], key="evidence_authority_filter"
    )
    selected_freshness = filter_cols_2[2].selectbox(
        "Freshness", ["All", "FRESH", "AGING", "OUTDATED"], key="evidence_freshness_filter"
    )

    evidence = evidence_service.list_evidence(
        vendor_id=selected_vendor,
        source_type="" if selected_source == "All" else selected_source,
        solution_category=(
            "" if selected_category_name == "All" else by_name[selected_category_name]
        ),
        validation_status=(
            "" if selected_validation == "All" else selected_validation
        ),
        search=search,
        include_archived=False,
        limit=500,
    )
    assessments = {item.evidence_id: workflow.quality_service.assess(item) for item in evidence}
    if selected_authority != "All":
        evidence = [item for item in evidence if item.source_authority == selected_authority]
    if selected_freshness != "All":
        evidence = [
            item for item in evidence
            if assessments[item.evidence_id].freshness_status == selected_freshness
        ]
    evidence_frame = pd.DataFrame(
        [
            {
                "Evidence ID": item.evidence_id,
                "Vendor": vendor_by_id.get(item.vendor_id).vendor_name
                if item.vendor_id in vendor_by_id
                else item.vendor_id,
                "Title": item.source_title,
                "Source Type": item.source_type,
                "Publication Date": item.publication_date,
                "Solutions": _category_names(item.solution_categories, by_id),
                "Validation": item.validation_status,
                "Authority": item.source_authority,
                "Freshness": assessments[item.evidence_id].freshness_status,
                "Duplicate": bool(item.duplicate_of_evidence_id),
                "Synthetic": item.is_synthetic,
            }
            for item in evidence
        ]
    )
    st.caption(f"{len(evidence)} matching record(s) · table displays up to 100")
    if evidence:
        st.dataframe(evidence_frame.head(100), width="stretch", hide_index=True)
        labels = {f"{item.source_title} · {item.evidence_id}": item for item in evidence}
        selected_label = st.selectbox("View Evidence", list(labels))
        selected = labels[selected_label]
        _log_view_once(workflow, "evidence_view", "Evidence", selected.evidence_id, selected.is_synthetic)
        assessment = assessments[selected.evidence_id]
        section_header(selected.source_title, selected.evidence_id)
        badges = status_badge(selected.validation_status) + " " + status_badge(assessment.freshness_status)
        if selected.is_synthetic:
            badges += " " + status_badge("SYNTHETIC")
        st.markdown(badges, unsafe_allow_html=True)
        detail_tabs = st.tabs(["Metadata", "Summary", "Text", "Validation & Quality", "Related Claims"])
        with detail_tabs[0]:
            meta_cols = st.columns(3)
            meta_cols[0].metric("Vendor", vendor_by_id.get(selected.vendor_id).vendor_name if selected.vendor_id in vendor_by_id else selected.vendor_id)
            meta_cols[1].metric("Source Type", selected.source_type)
            meta_cols[2].metric("Published", selected.publication_date)
            st.markdown(f"**Solution coverage:** {_category_names(selected.solution_categories, by_id) or 'Not classified'}")
            st.markdown(f"**Authority:** {selected.source_authority}  \n**Duplicate group:** {selected.duplicate_of_evidence_id or 'Primary / unique'}")
            if selected.source_url:
                st.link_button("Open source", selected.source_url)
            else:
                st.caption("No source URL supplied for this manual/import record.")
        with detail_tabs[1]:
            st.markdown(selected.summary or "No summary supplied.")
        with detail_tabs[2]:
            text_tabs = st.tabs(["Cleaned Text", "Original Text"])
            text_tabs[0].text_area("Cleaned Evidence text", selected.cleaned_text, height=260, disabled=True, label_visibility="collapsed")
            text_tabs[1].text_area("Original Evidence text", selected.raw_text, height=260, disabled=True, label_visibility="collapsed")
        with detail_tabs[3]:
            quality_cols = st.columns(4)
            quality_cols[0].metric("Validation", selected.validation_status)
            quality_cols[1].metric("Evidence Status", selected.evidence_status)
            quality_cols[2].metric("Quality", assessment.quality_level)
            quality_cols[3].metric("Quality Score", f"{assessment.quality_score} / 10")
            st.markdown(f"**Freshness:** {assessment.freshness_status} · {assessment.age_days} days old")
            if assessment.quality_explanation:
                st.markdown("\n".join(f"- {message}" for message in assessment.quality_explanation))
            if selected.validation_messages:
                st.markdown("**Validation messages**")
                st.markdown("\n".join(f"- {message}" for message in selected.validation_messages))
        with detail_tabs[4]:
            related = []
            for brief in intelligence.brief_repository.list_all():
                for claim in brief.claims:
                    if selected.evidence_id in claim.evidence_ids:
                        related.append({
                            "Brief": brief.title,
                            "Claim": claim.claim_text,
                            "Type": claim.claim_type,
                            "Support": claim.support_level,
                            "Review": claim.review_status,
                        })
            if related:
                st.dataframe(pd.DataFrame(related), hide_index=True, width="stretch")
            else:
                empty_state("No related Claims", "This Evidence record is not cited by a stored Claim.")
    else:
        empty_state(
            "No Evidence matches these filters",
            "Broaden the filters or add a new source record.",
            "Clear a filter or use Import / Add Evidence below.",
        )

    with st.expander("Import or add Evidence", expanded=False):
        if not vendors:
            empty_state("A Vendor is required", "Evidence must be linked to a valid Vendor.", "Create a Vendor first.")
            return
        add_tab, csv_tab, json_tab = st.tabs(["Pasted Text", "CSV", "JSON"])
        with add_tab:
            with st.form("add_evidence_form", clear_on_submit=True):
                vendor_label = st.selectbox("Vendor", [f"{v.vendor_name} · {v.vendor_id}" for v in vendors], key="manual_vendor")
                source_type = st.selectbox("Source Type", SOURCE_TYPES)
                title = st.text_input("Source Title")
                source_url = st.text_input("Source URL (optional for manual/import records)")
                publication_date = st.date_input("Publication Date").isoformat()
                raw_text = st.text_area("Paste Raw Evidence Text", height=160)
                summary = st.text_area("Summary (optional)")
                category_names = st.multiselect("Solution Categories", [category.name for category in categories])
                authority = st.selectbox("Source Authority", SOURCE_AUTHORITIES)
                synthetic = st.checkbox("Synthetic / demonstration Evidence")
                submitted = st.form_submit_button("Add Evidence", type="primary")
            if submitted:
                try:
                    item = evidence_service.create_evidence({
                        "vendor_id": vendor_label.rsplit(" · ", 1)[1], "source_type": source_type,
                        "source_title": title, "source_url": source_url, "publication_date": publication_date,
                        "raw_text": raw_text, "summary": summary,
                        "solution_categories": [by_name[name] for name in category_names],
                        "source_authority": authority, "is_synthetic": synthetic,
                    })
                    st.success(f"Evidence persisted as {item.evidence_id} · {item.validation_status}.")
                    _refresh()
                except ValueError as exc:
                    error_state("Evidence could not be added", "Check the required fields and source metadata.", str(exc))
        with csv_tab:
            st.caption("Required: vendor_id, source_title, publication_date, raw_text, solution_categories.")
            csv_file = st.file_uploader("Evidence CSV", type=["csv"], key="evidence_csv")
            if st.button("Import CSV", disabled=csv_file is None):
                try:
                    with st.spinner("Importing and validating Evidence..."):
                        result = evidence_service.import_csv(csv_file.getvalue())
                    st.success(f"Created {result.created_count}; rejected {result.rejected_count}.")
                except (ValueError, TypeError) as exc:
                    error_state("Evidence import failed", "Check the CSV structure and field values.", str(exc))
        with json_tab:
            st.caption("JSON may be an Evidence list or an object containing an evidence list.")
            json_file = st.file_uploader("Evidence JSON", type=["json"], key="evidence_json")
            if st.button("Import JSON", disabled=json_file is None):
                try:
                    with st.spinner("Importing and validating Evidence..."):
                        result = evidence_service.import_json(json_file.getvalue())
                    st.success(f"Created {result.created_count}; rejected {result.rejected_count}.")
                except (ValueError, TypeError) as exc:
                    error_state("Evidence import failed", "Check that the file contains valid structured Evidence.", str(exc))


def render_integrity(foundation) -> None:
    st.markdown("#### Data integrity")
    st.caption(
        "Checks IDs, Vendor references, taxonomy values, source types, hashes, "
        "dates, statuses, orphan records, duplicate marking, and Vendor metrics."
    )
    if st.button("Run Data Integrity Checks", type="primary"):
        report = run_integrity_checks(foundation.category_repository.database)
        if report["status"] == "PASS":
            st.success("Data integrity: PASS")
        else:
            st.error("Data integrity: FAIL")
        st.json(report)


def render_intelligence_feed(foundation, workflow, by_id: dict[str, str]) -> None:
    section_header("Intelligence feed", "Newest signals first")
    vendors = foundation.vendor_service.list_vendors(include_archived=True)
    vendor_names = {vendor.vendor_id: vendor.vendor_name for vendor in vendors}
    categories = foundation.category_repository.list_all()
    scope = st.radio(
        "Signal scope",
        ["All", "Watchlist", "Procurement", "Case Study", "Solution Update", "Brief"],
        horizontal=True,
        key="feed_scope",
    )
    filters = st.columns(3)
    vendor_options = {"All": "", **{vendor.vendor_name: vendor.vendor_id for vendor in vendors}}
    vendor_name = filters[0].selectbox("Vendor", list(vendor_options), key="feed_vendor")
    event_type = filters[1].selectbox("Event Type", ["All", *FEED_EVENT_TYPES])
    importance = filters[2].selectbox("Importance", ["All", *IMPORTANCE_LEVELS])
    filters2 = st.columns(3)
    category_options = {"All": "", **{item.name: item.category_id for item in categories}}
    category_name = filters2[0].selectbox("Solution Category", list(category_options), key="feed_category")
    source_type = filters2[1].selectbox("Source Type", ["All", *SOURCE_TYPES], key="feed_source")
    date_from = filters2[2].date_input("From Date", value=None, key="feed_from")
    events = workflow.feed_repository.list_all(
        vendor_id=vendor_options[vendor_name],
        event_type="" if event_type == "All" else event_type,
        solution_category=category_options[category_name],
        source_type="" if source_type == "All" else source_type,
        date_from=date_from.isoformat() if date_from else "",
        importance="" if importance == "All" else importance,
        limit=300,
    )
    scope_types = {
        "Procurement": {"NEW_PROCUREMENT_SIGNAL"},
        "Case Study": {"NEW_CASE_STUDY"},
        "Solution Update": {"NEW_SOLUTION_SIGNAL"},
        "Brief": {"BRIEF_GENERATED"},
    }
    if scope == "Watchlist":
        followed = {entry.vendor_id for entry in workflow.watchlist_service.repository.list_all()}
        events = [event for event in events if event.vendor_id in followed]
    elif scope in scope_types:
        events = [event for event in events if event.event_type in scope_types[scope]]
    st.caption(f"{len(events)} matching event(s) · newest first · displaying up to 30")
    if not events:
        empty_state(
            "No intelligence signals match this view",
            "Signals appear when Evidence, Briefs, and reviews create monitored events.",
            "Change the scope or add Evidence.",
        )
        return
    for event in events[:30]:
        info_card(
            event.title,
            event.summary or "No additional summary supplied.",
            f"{event.event_date} · {vendor_names.get(event.vendor_id, 'Portfolio-wide')} · "
            f"{event.source_type or event.event_type} · {event.importance}",
        )
    evidence_events = [event for event in events if event.evidence_id]
    if evidence_events:
        selected_id = st.selectbox(
            "Inspect Feed Evidence",
            [event.evidence_id for event in evidence_events],
        )
        _render_evidence_citation(foundation, selected_id)


def render_watchlist(foundation, workflow, by_id: dict[str, str]) -> None:
    section_header("Vendor watchlist", "Priority monitoring")
    vendors = foundation.vendor_service.list_vendors()
    followed = {entry.vendor_id for entry in workflow.watchlist_service.repository.list_all()}
    addable = [vendor for vendor in vendors if vendor.vendor_id not in followed]
    if addable:
        labels = {f"{vendor.vendor_name} · {vendor.vendor_id}": vendor for vendor in addable}
        choice = st.selectbox("Add Vendor", list(labels), key="watchlist_add_choice")
        if st.button("Follow Vendor", key="watchlist_add_button"):
            workflow.watchlist_service.follow(labels[choice].vendor_id)
            _refresh()
    details = workflow.watchlist_service.list_details()
    if not details:
        empty_state(
            "No Vendors on the watchlist",
            "Follow priority Vendors to monitor new Evidence and intelligence freshness.",
            "Choose a Vendor above and select Follow Vendor.",
        )
        return
    st.dataframe(
        pd.DataFrame([
            {
                "Vendor": item["vendor"].vendor_name,
                "Primary Solution Areas": _category_names(item["primary_solution_areas"], by_id),
                "Evidence": item["evidence_count"],
                "New Since View": item["new_evidence_since_last_view"],
                "Latest Procurement": (
                    item["latest_procurement_signal"].publication_date
                    if item["latest_procurement_signal"] else ""
                ),
                "Latest Brief": item["latest_brief"].title if item["latest_brief"] else "",
                "Freshness": "NEEDS REFRESH" if item["freshness"]["needs_intelligence_refresh"] else "CURRENT",
                "Last Intelligence": item["latest_intelligence_update"],
            }
            for item in details
        ]),
        hide_index=True,
        width="stretch",
    )
    labels = {item["vendor"].vendor_name: item for item in details}
    selected_name = st.selectbox("Watchlist Vendor", list(labels))
    selected = labels[selected_name]
    if selected["alerts"]:
        for alert in selected["alerts"]:
            st.warning(alert)
    freshness = selected["freshness"]
    status = "OUTDATED" if freshness["needs_intelligence_refresh"] else "FRESH"
    st.markdown(status_badge(status), unsafe_allow_html=True)
    freshness_cols = st.columns(4)
    freshness_cols[0].metric("Fresh Evidence", freshness["fresh_evidence_count"])
    freshness_cols[1].metric("Aging Evidence", freshness["aging_evidence_count"])
    freshness_cols[2].metric("Outdated Evidence", freshness["outdated_evidence_count"])
    freshness_cols[3].metric("Latest Evidence", freshness["latest_evidence_date"] or "NOT AVAILABLE")
    col1, col2 = st.columns(2)
    if col1.button("Mark Updates Viewed", key=f"mark_viewed_{selected['vendor'].vendor_id}"):
        workflow.watchlist_service.mark_viewed(selected["vendor"].vendor_id)
        _refresh()
    if col2.button("Unfollow", key=f"watch_unfollow_{selected['vendor'].vendor_id}"):
        workflow.watchlist_service.unfollow(selected["vendor"].vendor_id)
        _refresh()


def render_market_map(foundation, workflow, by_id: dict[str, str]) -> None:
    section_header("Healthcare IT market map", "Vendor × Solution category")
    st.caption("Cells come only from Validated, non-duplicate Evidence; no LLM classification is used.")
    vendors = foundation.vendor_service.list_vendors()
    categories = foundation.category_repository.list_all()
    vendor_labels = {vendor.vendor_name: vendor.vendor_id for vendor in vendors}
    category_labels = {item.name: item.category_id for item in categories}
    selected_vendors = st.multiselect("Vendors", list(vendor_labels), default=list(vendor_labels))
    selected_categories = st.multiselect(
        "Solution Categories", list(category_labels), default=list(category_labels)
    )
    minimum = st.number_input("Minimum Evidence Count", min_value=1, max_value=20, value=1)
    result = workflow.market_map_service.build(
        [vendor_labels[item] for item in selected_vendors],
        [category_labels[item] for item in selected_categories],
        int(minimum),
    )
    cells = result["cells"]
    if not cells:
        empty_state(
            "No Market Map cells match these filters",
            "Cells require Validated, non-duplicate Evidence for the selected Vendor and Solution category.",
            "Broaden the filters or inspect Evidence validation.",
        )
        return
    vendor_names = {vendor.vendor_id: vendor.vendor_name for vendor in vendors}
    frame = pd.DataFrame([
        {
            "Vendor": vendor_names.get(cell["vendor_id"], cell["vendor_id"]),
            "Category": by_id.get(cell["category_id"], cell["category_id"]),
            "Evidence Count": cell["evidence_count"],
            "Support": cell["support_status"],
        }
        for cell in cells
    ])
    matrix = frame.pivot(index="Vendor", columns="Category", values="Evidence Count").fillna(0).astype(int)
    st.dataframe(matrix, width="stretch")
    st.caption("Legend: each cell is the eligible Evidence count. " + result["support_rule"])
    st.caption(
        "Coverage reflects Evidence in the monitored evaluation dataset and does not represent total market share."
    )
    cell_labels = {
        f"{vendor_names.get(cell['vendor_id'], cell['vendor_id'])} × {by_id.get(cell['category_id'], cell['category_id'])} ({cell['evidence_count']})": cell
        for cell in cells
    }
    selected = cell_labels[st.selectbox("Inspect Market Map Cell", list(cell_labels))]
    detail_cols = st.columns(3)
    detail_cols[0].metric("Vendor", vendor_names.get(selected["vendor_id"], selected["vendor_id"]))
    detail_cols[1].metric("Solution", by_id.get(selected["category_id"], selected["category_id"]))
    detail_cols[2].metric("Evidence", selected["evidence_count"])
    st.markdown(status_badge(selected["support_status"]), unsafe_allow_html=True)
    for evidence_id in selected["evidence_ids"]:
        _render_evidence_citation(foundation, evidence_id)


def render_opportunities(foundation, workflow) -> None:
    section_header("Opportunity finder", "Evidence-based hypotheses")
    st.caption("Every item separates Evidence, Inference, and Recommendation and is scoped to the monitored dataset.")
    vendors = foundation.vendor_service.list_vendors()
    vendor_labels = {vendor.vendor_name: vendor.vendor_id for vendor in vendors}
    selected = st.multiselect(
        "Monitored Vendors",
        list(vendor_labels),
        default=list(vendor_labels)[:3],
        max_selections=8,
    )
    if st.button("Generate Evidence-Based Opportunities", type="primary"):
        try:
            with st.spinner("Analyzing coverage → grounding hypotheses → validating Evidence links..."):
                created = workflow.opportunity_service.generate([vendor_labels[name] for name in selected])
            st.success(f"Generated {len(created)} opportunity hypotheses.")
            _refresh()
        except (ValueError, RuntimeError) as exc:
            error_state(
                "Opportunities could not be generated",
                "Select a valid monitored Vendor set with eligible Evidence.",
                str(exc),
            )
    type_filter = st.selectbox("Opportunity Type", ["All", *OPPORTUNITY_TYPES])
    items = workflow.opportunity_repository.list_all(
        opportunity_type="" if type_filter == "All" else type_filter
    )
    if not items:
        empty_state(
            "No opportunity hypotheses yet",
            "Opportunities are derived from monitored coverage, comparisons, and stored Claims.",
            "Select Vendors and generate evidence-based opportunities.",
        )
        return
    labels = {f"{item.opportunity_type} · {item.title}": item for item in items}
    item = labels[st.selectbox("Opportunity", list(labels))]
    section_header(item.title, item.opportunity_type.replace("_", " "))
    badges = status_badge(item.review_status)
    if item.is_synthetic:
        badges += " " + status_badge("SYNTHETIC")
    st.markdown(badges, unsafe_allow_html=True)
    info_card("FACT / EVIDENCE", item.evidence_statement, "Grounded source basis", css_class="hmi-callout-evidence")
    info_card("INFERENCE", item.inference, "Analytical interpretation", css_class="hmi-callout-inference")
    info_card("RECOMMENDATION", item.recommendation, "Decision support, not a verified fact", css_class="hmi-callout-recommendation")
    st.caption(f"Confidence basis: {item.confidence_basis}")
    for evidence_id in item.evidence_ids:
        _render_evidence_citation(foundation, evidence_id)
    with st.form(f"review_opportunity_{item.opportunity_id}"):
        reviewer = st.text_input("Reviewer", value=item.reviewer)
        status = st.selectbox(
            "Review Status", ["PENDING", "APPROVED", "REJECTED"],
            index=["PENDING", "APPROVED", "REJECTED"].index(item.review_status),
        )
        note = st.text_area("Reviewer Note", value=item.reviewer_note)
        if st.form_submit_button("Save Opportunity Review"):
            try:
                workflow.opportunity_service.review(item.opportunity_id, status, reviewer, note)
                _refresh()
            except ValueError as exc:
                st.error(str(exc))


def render_review_queue(foundation, intelligence, workflow) -> None:
    page_header(
        "Human oversight",
        "Review queue",
        "Resolve pending Briefs, Claims, and Evidence before intelligence is used for decisions.",
    )
    queue = workflow.brief_workflow_service.queue()
    cols = st.columns(4)
    cols[0].metric("Briefs Pending", len(queue["briefs_awaiting_review"]))
    cols[1].metric("Claims Pending", len(queue["claims_awaiting_review"]))
    cols[2].metric("Unsupported", len(queue["unsupported_claims"]))
    cols[3].metric("Evidence Needs Review", len(queue["evidence_needing_validation"]))
    briefs_tab, claims_tab, evidence_tab = st.tabs(["Briefs", "Claims", "Evidence"])
    with briefs_tab:
        items = list(queue["briefs_awaiting_review"])
        if not items:
            empty_state("No Briefs awaiting review", "All stored Briefs have moved beyond the pending review queue.")
        else:
            st.dataframe(pd.DataFrame([
                {"Title": item.title, "Type": item.brief_type, "Status": item.status, "Claims": len(item.claims), "Generated": item.generated_at}
                for item in items
            ]), hide_index=True, width="stretch")
            selected = {f"{item.title} · {item.brief_id}": item for item in items}
            brief = selected[st.selectbox("Open Brief", list(selected), key="review_brief_select")]
            reviewer = st.text_input("Reviewer", value="Local Reviewer", key="queue_brief_reviewer")
            note = st.text_input("Review note", key="queue_brief_note")
            if st.button("Start Review", type="primary", key=f"queue_start_{brief.brief_id}"):
                try:
                    workflow.brief_workflow_service.start_review(brief.brief_id, reviewer, note)
                    _refresh()
                except ValueError as exc:
                    error_state("Brief review could not start", "Check the current Brief state and reviewer name.", str(exc))
    with claims_tab:
        queue_name = st.selectbox(
            "Claim queue",
            ["claims_awaiting_review", "unsupported_claims", "partially_supported_claims"],
            format_func=lambda value: value.replace("_", " ").title(),
            key="claim_queue_name",
        )
        items = list(queue[queue_name])
        if not items:
            empty_state("No Claims in this queue", "No stored Claims match the selected review status.")
        else:
            st.dataframe(pd.DataFrame([
                {"Type": item.claim_type, "Claim": item.claim_text, "Support": item.support_level, "Review": item.review_status, "Evidence": len(item.evidence_ids)}
                for item in items
            ]), hide_index=True, width="stretch")
            selected = {f"{item.claim_type} · {item.claim_text[:90]} · {item.claim_id}": item for item in items}
            claim = selected[st.selectbox("Open Claim", list(selected), key="queue_claim_select")]
            with st.form(f"queue_claim_form_{claim.claim_id}"):
                reviewer = st.text_input("Reviewer", value="Local Reviewer")
                claim_text = st.text_area("Claim text", value=claim.claim_text)
                action = st.selectbox("Action", ["Approve", "Reject", "Edit", "Mark Unsupported"])
                note = st.text_area("Review note")
                submitted = st.form_submit_button("Save Claim Review", type="primary")
            if submitted:
                try:
                    workflow.brief_workflow_service.review_claim(
                        claim.claim_id,
                        action,
                        reviewer,
                        {
                            "claim_text": claim_text,
                            "claim_type": claim.claim_type,
                            "evidence_ids": claim.evidence_ids,
                            "explanation": claim.explanation,
                        },
                        note=note,
                    )
                    intelligence.traceability_service.validate_brief(claim.brief_id)
                    _refresh()
                except ValueError as exc:
                    error_state("Claim review could not be saved", "Check the action and required Evidence links.", str(exc))
            if claim.evidence_ids:
                with st.expander("Open Evidence", expanded=False):
                    for evidence_id in claim.evidence_ids:
                        _render_evidence_citation(foundation, evidence_id)
    with evidence_tab:
        items = list(queue["evidence_needing_validation"])
        if not items:
            empty_state("No Evidence awaiting validation", "All Evidence records have a resolved validation state.")
        else:
            st.dataframe(pd.DataFrame([
                {"Title": item.source_title, "Source Type": item.source_type, "Validation": item.validation_status, "Status": item.evidence_status, "Published": item.publication_date}
                for item in items
            ]), hide_index=True, width="stretch")
            selected = {f"{item.source_title} · {item.evidence_id}": item for item in items}
            evidence = selected[st.selectbox("Open Evidence", list(selected), key="queue_evidence_select")]
            _render_evidence_citation(foundation, evidence.evidence_id)


def _metric_value(value, suffix: str = "") -> str:
    if value is None:
        return "NOT AVAILABLE"
    if isinstance(value, float):
        return f"{value:.1f}{suffix}"
    return f"{value}{suffix}"


def render_analytics(foundation, workflow) -> None:
    st.caption(
        "Evaluation Metrics · Synthetic portfolio data · Current SQLite snapshot · Not live client usage"
    )
    stats = workflow.analytics_service.snapshot()
    vendor_names = {
        vendor.vendor_id: vendor.vendor_name
        for vendor in foundation.vendor_service.list_vendors(include_archived=True)
    }
    coverage_tab, quality_tab, output_tab, workflow_tab = st.tabs(
        ["Coverage", "Quality", "Output", "Workflow"]
    )
    with coverage_tab:
        cols = st.columns(4)
        cols[0].metric("Active Vendors", stats["active_vendor_count"])
        cols[1].metric("Evidence Records", stats["evidence_count"])
        cols[2].metric("Validated Evidence", stats["validated_evidence_count"])
        cols[3].metric("Solution Categories", stats["solution_category_count"])
        section_header("Evidence by Vendor", "Record count")
        coverage = pd.DataFrame(
            [
                {"Vendor": vendor_names.get(vendor_id, vendor_id), "Evidence": count}
                for vendor_id, count in stats["evidence_by_vendor"].items()
            ]
        ).set_index("Vendor")
        st.bar_chart(coverage, color="#176b87")
    with quality_tab:
        cols = st.columns(4)
        cols[0].metric("Traceability", _metric_value(stats["traceability_rate"], "%"))
        cols[1].metric("Reviewed Claims", stats["reviewed_claim_count"])
        cols[2].metric("Traceable Claims", stats["traceable_claim_count"])
        cols[3].metric("Invalid Citations", stats["invalid_citation_count"])
        st.caption(
            f"Evaluation metric: {stats['traceable_claim_count']} / {stats['reviewed_claim_count']} "
            "manually reviewed Claims. Traceability and support level are separate measures."
        )
        charts = st.columns(2, gap="large")
        with charts[0]:
            st.markdown("#### Claim support distribution")
            support_frame = pd.DataFrame(
                {"Claims": [
                    stats["supported_claim_count"],
                    stats["partially_supported_claim_count"],
                    stats["unsupported_claim_count"],
                ]},
                index=["Supported", "Partially supported", "Unsupported"],
            )
            st.bar_chart(support_frame, color="#315f8c")
        with charts[1]:
            st.markdown("#### Evidence freshness")
            freshness_frame = pd.DataFrame(
                stats["evidence_freshness"].items(), columns=["Freshness", "Evidence"]
            ).set_index("Freshness")
            st.bar_chart(freshness_frame, color="#5f8799")
    with output_tab:
        cols = st.columns(4)
        cols[0].metric("Competitor Briefs", stats["brief_count"])
        cols[1].metric("Comparisons", stats["comparison_count"])
        cols[2].metric("Opportunities", stats["opportunity_count"])
        cols[3].metric("Executive Briefs", stats["executive_brief_count"])
        output_frame = pd.DataFrame(
            {
                "Outputs": [
                    stats["brief_count"],
                    stats["comparison_count"],
                    stats["opportunity_count"],
                    stats["executive_brief_count"],
                    stats["sales_enablement_count"],
                ]
            },
            index=["Briefs", "Comparisons", "Opportunities", "Executive", "Sales enablement"],
        )
        st.bar_chart(output_frame, color="#176b87")
    with workflow_tab:
        cols = st.columns(4)
        cols[0].metric("Briefs Reviewed", stats["review_count"])
        cols[1].metric("Average Review Time", _metric_value(stats["average_review_time"], " min"))
        cols[2].metric("Average Edit Count", _metric_value(stats["average_edit_count"]))
        cols[3].metric("Finalisation Rate", _metric_value(stats["finalisation_rate"], "%"))
        benchmark = stats["benchmark"]
        st.warning("Manual benchmark not completed. Efficiency KPIs are unavailable.")
        benchmark_cols = st.columns(4)
        benchmark_cols[0].metric("Manual Median", _metric_value(benchmark["manual"]["median"], " min"))
        benchmark_cols[1].metric("AI-Assisted Median", _metric_value(benchmark["ai_assisted"]["median"], " min"))
        benchmark_cols[2].metric("Time Reduction", _metric_value(benchmark["time_reduction_pct"], "%"))
        benchmark_cols[3].metric("Speed Multiple", _metric_value(benchmark["speed_multiple"], "x"))
        st.caption(f"Complete comparable paired sample: {benchmark['paired_sample_size']} · Minimum required: 5")


def render_benchmark(workflow) -> None:
    section_header("Workflow benchmark", "Evaluation workspace")
    if workflow.benchmark_service.summary()["paired_sample_size"] < 5:
        st.warning(
            "Manual benchmark not completed. Manual Median, AI-Assisted Median, Time Reduction, "
            "and Speed Multiple remain NOT AVAILABLE."
        )
    st.caption(
        "Paired comparisons require identical frozen task, Vendor set, Evidence set, and output scope. "
        "Only COMPLETE + COMPARABLE pairs enter KPI calculations."
    )
    service = workflow.benchmark_service
    tasks = service.tasks()
    task_map = {item.task_id: item for item in tasks}
    new_tab, history_tab, comparison_tab, detail_tab, aggregate_tab = st.tabs(
        ["New Benchmark", "Benchmark History", "Manual vs AI", "Run Detail", "Aggregate Results"]
    )
    with new_tab:
        task_id = st.selectbox("Frozen Evaluation Task", list(task_map), key="benchmark_task")
        task = task_map[task_id]
        workflow_type = st.radio(
            "Workflow Type", ["MANUAL", "AI_ASSISTED"], horizontal=True, key="benchmark_workflow"
        )
        existing = service.repository.get_by_pair(f"pair_{task_id}", workflow_type)
        st.caption(
            f"{task.task_type} · {len(task.vendor_ids)} Vendor(s) · "
            f"{len(task.evidence_ids)} frozen Evidence records"
        )
        st.info(task.output_requirement)
        if workflow_type == "AI_ASSISTED" and existing is None:
            st.warning("Run scripts/run_evaluation.py first to measure the automated AI stages.")
        with st.form("benchmark_entry_form"):
            stage_times: dict[str, float] = {}
            machine_keys = {
                "ai_pack_minutes", "ai_generation_minutes", "ai_validation_minutes",
                "ai_qa_minutes", "ai_export_minutes",
            }
            for key in service.stage_keys(workflow_type):
                default = float(existing.stage_times.get(key, 0.0)) if existing else 0.0
                stage_times[key] = st.number_input(
                    key,
                    min_value=0.0,
                    value=default,
                    step=0.1,
                    format="%.6f",
                    disabled=(workflow_type == "AI_ASSISTED" and key in machine_keys),
                )
            left, right = st.columns(2)
            claim_count = left.number_input(
                "Claim Count", min_value=0, value=existing.claim_count if existing else 0, step=1
            )
            brief_length = right.number_input(
                "Brief Length (characters)", min_value=0,
                value=existing.brief_length if existing else 0, step=1,
            )
            review_result = st.selectbox("Reviewer Result", ["PASS", "NEEDS_REVISION", "FAIL"])
            edit_count = st.number_input(
                "Edit Count", min_value=0, value=existing.edit_count if existing else 0, step=1
            )
            notes = st.text_area("Notes", value=existing.notes if existing else "")
            submitted = st.form_submit_button("Save Complete Benchmark Run", type="primary")
        if submitted:
            if workflow_type == "AI_ASSISTED" and existing is None:
                st.error("No automatically measured AI draft exists for this task.")
            else:
                try:
                    saved = service.record_run(
                        task_id,
                        workflow_type,
                        stage_times,
                        run_status="COMPLETE",
                        notes=notes,
                        claim_count=int(claim_count),
                        brief_length=int(brief_length),
                        brief_id=existing.brief_id if existing else "",
                        review_result=review_result,
                        edit_count=int(edit_count),
                        unsupported_claims_found=(existing.unsupported_claims_found if existing else 0),
                        citation_errors_found=(existing.citation_errors_found if existing else 0),
                        measurement_method=(
                            "AUTO_TIMER_PLUS_HUMAN_ENTRY"
                            if workflow_type == "AI_ASSISTED" else "MANUAL_ENTRY"
                        ),
                    )
                    st.success(
                        f"Saved {saved.workflow_type}: {saved.total_minutes:.3f} minutes; "
                        f"pair status {service.evaluate_pair(saved.pair_id)['status']}."
                    )
                    _refresh()
                except ValueError as exc:
                    st.error(str(exc))

    history = service.history()
    history_rows = [
        {
            "Benchmark ID": item.benchmark_id,
            "Task": item.manifest_task_id,
            "Workflow": item.workflow_type,
            "Minutes": item.total_minutes,
            "Run Status": item.run_status,
            "Comparability": item.comparability_status,
            "Evidence": item.evidence_count,
            "Claims": item.claim_count,
            "Synthetic": item.is_synthetic,
        }
        for item in history
    ]
    with history_tab:
        st.dataframe(pd.DataFrame(history_rows), hide_index=True, width="stretch")
    with comparison_tab:
        complete = [item for item in history if item.run_status == "COMPLETE"]
        if complete:
            frame = pd.DataFrame(
                [{"Pair": item.pair_id, "Workflow": item.workflow_type, "Minutes": item.total_minutes}
                 for item in complete]
            )
            st.bar_chart(frame.pivot(index="Pair", columns="Workflow", values="Minutes"))
        else:
            st.info("No complete runs yet.")
    with detail_tab:
        if history:
            selected = st.selectbox(
                "Benchmark Run", [item.benchmark_id for item in history], key="benchmark_detail"
            )
            run = next(item for item in history if item.benchmark_id == selected)
            st.json(asdict(run))
        else:
            st.info("No benchmark history yet.")
    with aggregate_tab:
        summary = service.summary()
        cols = st.columns(3)
        cols[0].metric("Manual Median", _metric_value(summary["manual"]["median"], " min"))
        cols[1].metric("AI Median", _metric_value(summary["ai_assisted"]["median"], " min"))
        cols[2].metric("Time Saved", _metric_value(summary["time_saved_minutes"], " min"))
        cols = st.columns(3)
        cols[0].metric("Reduction", _metric_value(summary["time_reduction_pct"], "%"))
        cols[1].metric("Speed Multiple", _metric_value(summary["speed_multiple"], "x"))
        cols[2].metric("Paired Sample", summary["paired_sample_size"])
        st.json(summary)


def render_settings(view: str = "Rules") -> None:
    if view == "Runtime & Data":
        api_configured = bool(_runtime_setting("OPENAI_API_KEY"))
        cols = st.columns(3)
        cols[0].metric("Data Mode", "SYNTHETIC")
        cols[1].metric("Generation Mode", "OPENAI" if api_configured else "DETERMINISTIC")
        cols[2].metric("Portfolio Version", "1.0.0-rc1")
        st.info(
            "No API key is required for Demo Mode. When OPENAI_API_KEY is absent, the product uses "
            "deterministic structured demo intelligence and retains the same Evidence and traceability checks."
        )
        st.caption("Secret values are never displayed in the interface.")
        return
    st.markdown("#### Evidence freshness")
    st.markdown("FRESH ≤ 90 days · AGING 91–180 days · OUTDATED > 180 days")
    st.markdown("#### Evidence quality")
    st.markdown(
        "Source Authority (0–3) + Recency (0–3) + Completeness (0–2) + "
        "Traceability (0–1) + Relevance (0–1). HIGH ≥ 8; MEDIUM ≥ 5; otherwise LOW."
    )
    st.markdown("#### Claim grounding")
    st.markdown(
        "FACT Claims require eligible Evidence from their originating Evidence Pack. "
        "INFERENCE and RECOMMENDATION retain their Evidence basis. Unknown, missing, or out-of-Pack citations are invalid."
    )
    st.info("These are internal intelligence-maintenance rules, not Healthcare industry standards.")


def _render_evidence_citation(foundation, evidence_id: str) -> None:
    evidence = foundation.evidence_service.get_evidence(evidence_id)
    if evidence is None:
        st.error(f"Missing Evidence: {evidence_id}")
        return
    vendor = foundation.vendor_service.get_vendor(evidence.vendor_id)
    with st.expander(f"{evidence_id} · {evidence.source_title}"):
        st.markdown(
            f"**Vendor:** {vendor.vendor_name if vendor else evidence.vendor_id}\n\n"
            f"**Source Type:** {evidence.source_type}\n\n"
            f"**Publication Date:** {evidence.publication_date}\n\n"
            f"**Source URL:** {evidence.source_url or 'Not supplied'}\n\n"
            f"**Summary:** {evidence.summary}\n\n"
            f"**Authority:** {evidence.source_authority}\n\n"
            f"**Synthetic:** {evidence.is_synthetic}"
        )
        st.code(evidence.cleaned_text or evidence.raw_text, language="text")


def _render_brief(foundation, intelligence, brief) -> None:
    section_header(brief.title, f"{brief.brief_type} · {brief.generated_at}")
    badges = status_badge(brief.status)
    if brief.is_demo:
        badges += " " + status_badge("SYNTHETIC")
    st.markdown(badges, unsafe_allow_html=True)
    st.caption(f"Brief {brief.brief_id} · Evidence Pack {brief.evidence_pack_id} · Prompt {brief.prompt_version}")
    claim_by_id = {claim.claim_id: claim for claim in brief.claims}
    traceability = intelligence.traceability_service.validate_brief(
        brief.brief_id,
        update_claims=False,
    )
    pack = intelligence.evidence_pack_service.get_pack(brief.evidence_pack_id)
    summary_tab, intelligence_tab, claims_tab, citations_tab, sources_tab = st.tabs(
        ["Executive Summary", "Key Intelligence", "Claims", "Evidence Citations", "Sources"]
    )
    with summary_tab:
        st.markdown(brief.executive_summary)
        metrics = st.columns(4)
        metrics[0].metric("Claims", traceability["total_claims"])
        metrics[1].metric("Traceable", traceability["traceable_claims"])
        metrics[2].metric("Unsupported", traceability["unsupported_claims"])
        metrics[3].metric("Invalid Citations", traceability["invalid_citations_detected"])
        if traceability["result"] == "PASS":
            st.success("Structured citation validation: PASS")
        else:
            st.error("Structured citation validation: FAIL — review unsupported FACT Claims or invalid Evidence IDs.")
    with intelligence_tab:
        for section, claim_ids in brief.sections.items():
            with st.container(border=True):
                st.markdown(f"#### {section}")
                for claim_id in claim_ids:
                    claim = claim_by_id.get(claim_id)
                    if claim:
                        st.markdown(f"**{claim.claim_type.replace('_', ' ')} · {claim.support_level.replace('_', ' ')}**")
                        st.markdown(claim.claim_text)
    with claims_tab:
        st.dataframe(
            pd.DataFrame([
                {
                    "Type": claim.claim_type,
                    "Claim": claim.claim_text,
                    "Support": claim.support_level,
                    "Traceable": claim.traceable,
                    "Evidence": len(claim.evidence_ids),
                    "Review": claim.review_status,
                }
                for claim in brief.claims
            ]),
            hide_index=True,
            width="stretch",
        )
    with citations_tab:
        for claim in brief.claims:
            with st.expander(f"{claim.claim_type} · {claim.support_level} · {claim.claim_text[:95]}"):
                st.markdown(claim.claim_text)
                if claim.evidence_ids:
                    st.caption("Evidence IDs: " + ", ".join(claim.evidence_ids))
                else:
                    empty_state("No Evidence citation", "This Claim is classified without a valid citation and must not be presented as a supported FACT.")
    with sources_tab:
        if pack and pack.evidence_ids:
            for evidence_id in pack.evidence_ids:
                _render_evidence_citation(foundation, evidence_id)
        else:
            empty_state("No Evidence Pack", "The source Evidence Pack is unavailable for this Brief.")
        if pack:
            with st.expander("Evidence selection rules", expanded=False):
                st.markdown(f"**Pack:** {pack.evidence_pack_id}  \n**Evidence records:** {len(pack.evidence_ids)}")
                st.json(pack.selection_criteria)


def render_comparison(foundation, intelligence, workflow) -> None:
    section_header("Vendor comparison", "2–5 Vendors")
    st.caption(
        "Select 2–5 Vendors. Evidence-backed FACTS are separated from INFERENCE and RECOMMENDATION."
    )
    st.caption("Select Vendors → Review Evidence Coverage → Structured Comparison → AI Intelligence Analysis → Executive View")
    vendors = foundation.vendor_service.list_vendors()
    label_to_id = {f"{vendor.vendor_name} · {vendor.vendor_id}": vendor.vendor_id for vendor in vendors}
    selected_labels = st.multiselect(
        "Vendors",
        list(label_to_id),
        default=list(label_to_id)[:2],
        max_selections=5,
    )
    include_warning = st.checkbox("Include Warning Evidence", key="compare_warning")
    if st.button("Generate Comparison", type="primary"):
        if not 2 <= len(selected_labels) <= 5:
            error_state("Invalid selection", "Select between 2 and 5 unique Vendors.")
        else:
            api_key = _runtime_setting("OPENAI_API_KEY")
            model = _runtime_setting("OPENAI_MODEL", "gpt-5.6")
            try:
                with st.spinner("Processing Evidence → generating comparison → validating Claims..."):
                    brief, traceability = intelligence.comparison_service.generate(
                        [label_to_id[label] for label in selected_labels],
                        include_warning=include_warning,
                        api_key=api_key,
                        model=model,
                    )
                st.success(f"Generated {brief.brief_id}; traceability {traceability['result']}.")
                _refresh()
            except (ValueError, RuntimeError) as exc:
                error_state("Comparison generation failed", "Review the selected Vendors and eligible Evidence.", str(exc))

    comparisons = intelligence.brief_repository.list_all("COMPARISON")
    if comparisons:
        comparison_labels = {f"{brief.title} · {brief.brief_id}": brief for brief in comparisons}
        comparison_label = st.selectbox("View Comparison", list(comparison_labels))
        comparison = comparison_labels[comparison_label]
        if st.button("Save Comparison", key=f"save_comparison_{comparison.brief_id}"):
            workflow.saved_comparison_service.save(comparison.brief_id)
            st.success("Comparison saved without rerunning the model.")
            _refresh()
        overview_tab, coverage_tab, evidence_tab, positioning_tab, analysis_tab = st.tabs(
            ["Overview", "Solution Coverage", "Evidence", "Positioning", "AI Analysis"]
        )
        vendor_map = {vendor.vendor_id: vendor for vendor in vendors}
        category_map = {
            category.category_id: category.name
            for category in foundation.category_repository.list_all()
        }
        with overview_tab:
            st.markdown(f"### {comparison.title}")
            st.markdown(comparison.executive_summary)
            st.markdown(status_badge(comparison.status) + " " + status_badge("SYNTHETIC"), unsafe_allow_html=True)
            overview_rows = []
            for vendor_id in comparison.vendor_ids:
                vendor = vendor_map.get(vendor_id)
                overview_rows.append({
                    "Vendor": vendor.vendor_name if vendor else vendor_id,
                    "Primary Market": vendor.primary_market if vendor else "",
                    "Evidence": vendor.evidence_count if vendor else 0,
                    "Solutions": len(vendor.solution_categories) if vendor else 0,
                })
            st.dataframe(pd.DataFrame(overview_rows), hide_index=True, width="stretch")
        with coverage_tab:
            coverage_rows = []
            for vendor_id in comparison.vendor_ids:
                vendor = vendor_map.get(vendor_id)
                for category_id in (vendor.solution_categories if vendor else []):
                    coverage_rows.append({
                        "Vendor": vendor.vendor_name,
                        "Solution Category": category_map.get(category_id, category_id),
                    })
            if coverage_rows:
                st.dataframe(pd.DataFrame(coverage_rows), hide_index=True, width="stretch")
            else:
                empty_state("No solution coverage", "The selected Vendors have no evidence-backed taxonomy coverage.")
        with evidence_tab:
            pack = intelligence.evidence_pack_service.get_pack(comparison.evidence_pack_id)
            if pack:
                for evidence_id in pack.evidence_ids:
                    _render_evidence_citation(foundation, evidence_id)
            else:
                empty_state("Evidence Pack unavailable", "The saved comparison has no retrievable Evidence Pack.")
        with positioning_tab:
            claim_by_id = {claim.claim_id: claim for claim in comparison.claims}
            positioning_claims = [
                claim_by_id[claim_id]
                for section, claim_ids in comparison.sections.items()
                if "position" in section.lower()
                for claim_id in claim_ids
                if claim_id in claim_by_id
            ]
            if positioning_claims:
                for claim in positioning_claims:
                    info_card(claim.claim_type, claim.claim_text, f"{claim.support_level} · {claim.review_status}")
            else:
                empty_state("No positioning section", "This comparison does not contain a dedicated positioning section.")
        with analysis_tab:
            _render_brief(foundation, intelligence, comparison)
            st.markdown("#### Executive and sales views")
            executive = workflow.executive_brief_repository.get_by_brief(comparison.brief_id)
            sales = workflow.sales_enablement_repository.get_by_brief(comparison.brief_id)
            action_cols = st.columns(2)
            if executive:
                action_cols[0].success("Executive comparison available")
            elif action_cols[0].button("Create Executive Comparison", key=f"create_exec_{comparison.brief_id}"):
                workflow.executive_brief_service.create(comparison.brief_id)
                _refresh()
            if sales:
                action_cols[1].success("Sales comparison available")
            elif action_cols[1].button("Create Sales Comparison", key=f"create_sales_{comparison.brief_id}"):
                workflow.sales_enablement_service.create(comparison.brief_id)
                _refresh()
        history = workflow.saved_comparison_repository.list_all()
        if history:
            st.markdown("#### Comparison History")
            st.dataframe(
                pd.DataFrame([asdict(item) for item in history]),
                hide_index=True,
                width="stretch",
            )
    else:
        empty_state("No saved comparisons", "A comparison requires 2–5 Vendors and an eligible Evidence Pack.", "Select Vendors and generate a comparison.")


def render_briefs_and_claims(foundation, intelligence, workflow) -> None:
    page_header(
        "Decision outputs",
        "Brief library",
        "Open structured intelligence, inspect Claim-to-Evidence traceability, review, and export.",
    )
    library_view = st.radio(
        "Brief workspace",
        ["Competitor Briefs", "Executive Briefs", "Sales Enablement"],
        horizontal=True,
        label_visibility="collapsed",
        key="brief_workspace",
    )
    if library_view == "Executive Briefs":
        items = workflow.executive_brief_repository.list_all()
        if not items:
            empty_state("No Executive Briefs", "Executive outputs are derived from a stored structured Brief.", "Open a Competitor Brief and create an Executive Brief.")
            return
        st.dataframe(pd.DataFrame([
            {"Title": item.title, "Source Brief": item.brief_id, "Evidence": len(item.evidence_ids), "Created": item.created_at, "Synthetic": item.is_synthetic}
            for item in items
        ]), hide_index=True, width="stretch")
        selected = {f"{item.title} · {item.executive_brief_id}": item for item in items}
        item = selected[st.selectbox("Open Executive Brief", list(selected))]
        section_header(item.title, item.created_at)
        st.markdown(status_badge("SYNTHETIC") if item.is_synthetic else status_badge("APPROVED"), unsafe_allow_html=True)
        for section, lines in item.sections.items():
            with st.container(border=True):
                st.markdown(f"#### {section}")
                st.markdown("\n".join(f"- {line}" for line in lines) or "No content.")
        return
    if library_view == "Sales Enablement":
        items = workflow.sales_enablement_repository.list_all()
        if not items:
            empty_state("No Sales Enablement outputs", "Sales outputs reuse reviewed Claims and Evidence from a stored Brief.", "Open a Competitor Brief and create Sales Enablement.")
            return
        st.dataframe(pd.DataFrame([
            {"Title": item.title, "Source Brief": item.brief_id, "Claims": len(item.source_claim_ids), "Evidence": len(item.evidence_ids), "Created": item.created_at, "Synthetic": item.is_synthetic}
            for item in items
        ]), hide_index=True, width="stretch")
        selected = {f"{item.title} · {item.sales_output_id}": item for item in items}
        item = selected[st.selectbox("Open Sales Enablement", list(selected))]
        section_header(item.title, item.created_at)
        st.markdown(status_badge("SYNTHETIC") if item.is_synthetic else status_badge("APPROVED"), unsafe_allow_html=True)
        for section, entries in item.sections.items():
            with st.container(border=True):
                st.markdown(f"#### {section}")
                for entry in entries:
                    if isinstance(entry, dict):
                        st.markdown(" · ".join(f"**{key.replace('_', ' ').title()}:** {value}" for key, value in entry.items()))
                    else:
                        st.markdown(f"- {entry}")
        return
    briefs = intelligence.brief_repository.list_all()
    if not briefs:
        empty_state("No Competitor Briefs", "A Brief is generated from an eligible Evidence Pack.", "Generate Vendor Intelligence or a comparison.")
        return
    vendor_names = {
        vendor.vendor_id: vendor.vendor_name
        for vendor in foundation.vendor_service.list_vendors(include_archived=True)
    }
    library_rows = []
    for item in briefs:
        validation = intelligence.traceability_service.validate_brief(item.brief_id, update_claims=False)
        library_rows.append({
            "Title": item.title,
            "Vendor": ", ".join(vendor_names.get(vendor_id, vendor_id) for vendor_id in item.vendor_ids),
            "Type": item.brief_type,
            "Status": item.status,
            "Claims": len(item.claims),
            "Traceability": f"{validation['traceable_claims']} / {validation['total_claims']}",
            "Invalid Citations": validation["invalid_citations_detected"],
            "Generated": item.generated_at,
            "Synthetic": item.is_demo,
        })
    st.dataframe(pd.DataFrame(library_rows), hide_index=True, width="stretch")
    labels = {f"{brief.title} · {brief.brief_id}": brief for brief in briefs}
    selected_label = st.selectbox("Structured Brief", list(labels))
    brief = labels[selected_label]
    _render_brief(foundation, intelligence, brief)

    st.markdown("#### Brief Workflow")
    reviewer = st.text_input("Reviewer Name", value="Local Reviewer", key=f"reviewer_{brief.brief_id}")
    review_note = st.text_input("Brief Review Note", key=f"brief_note_{brief.brief_id}")
    workflow_cols = st.columns(4)
    actions = [
        ("Start Review", workflow.brief_workflow_service.start_review),
        ("Return for Revision", workflow.brief_workflow_service.return_for_revision),
        ("Approve Brief", workflow.brief_workflow_service.approve),
    ]
    for column, (label, action_fn) in zip(workflow_cols[:3], actions):
        if column.button(label, key=f"{label}_{brief.brief_id}"):
            try:
                action_fn(brief.brief_id, reviewer, review_note)
                _refresh()
            except ValueError as exc:
                st.error(str(exc))
    if workflow_cols[3].button("Mark Final", key=f"final_{brief.brief_id}"):
        try:
            workflow.brief_workflow_service.finalize(brief.brief_id)
            _refresh()
        except ValueError as exc:
            st.error(str(exc))
    metadata = workflow.review_repository.get(brief.brief_id)
    if metadata:
        review_cols = st.columns(4)
        review_cols[0].metric("Reviewer", metadata.reviewer or "NOT ASSIGNED")
        review_cols[1].metric("Review Minutes", _metric_value(metadata.review_minutes, " min"))
        review_cols[2].metric("Revisions", metadata.revision_count)
        review_cols[3].metric("Completed", metadata.review_completed_at or "PENDING")
        if metadata.review_notes:
            st.caption("Review notes: " + " · ".join(metadata.review_notes))

    st.markdown("#### Basic Claim Review")
    claim_labels = {
        f"{claim.claim_type} · {claim.claim_text[:80]} · {claim.claim_id}": claim
        for claim in brief.claims
    }
    claim_label = st.selectbox("Claim", list(claim_labels))
    claim = claim_labels[claim_label]
    pack = intelligence.evidence_pack_service.get_pack(brief.evidence_pack_id)
    pack_evidence_ids = pack.evidence_ids if pack else []
    with st.form(f"review_{claim.claim_id}"):
        claim_text = st.text_area("Claim Text", value=claim.claim_text)
        claim_type = st.selectbox(
            "Claim Type",
            CLAIM_TYPES,
            index=CLAIM_TYPES.index(claim.claim_type),
        )
        evidence_ids = st.multiselect(
            "Evidence Links",
            pack_evidence_ids,
            default=[item for item in claim.evidence_ids if item in pack_evidence_ids],
        )
        explanation = st.text_area("Review Explanation", value=claim.explanation)
        reviewer_note = st.text_area("Reviewer Note", key=f"claim_note_{claim.claim_id}")
        action = st.selectbox(
            "Review Action",
            ["Approve", "Reject", "Edit", "Mark Unsupported"],
        )
        if st.form_submit_button("Save Claim Review"):
            try:
                workflow.brief_workflow_service.review_claim(
                    claim.claim_id,
                    action,
                    reviewer,
                    {
                        "claim_text": claim_text,
                        "claim_type": claim_type,
                        "evidence_ids": evidence_ids,
                        "explanation": explanation,
                    },
                    note=reviewer_note,
                )
                intelligence.traceability_service.validate_brief(brief.brief_id)
                st.success("Claim review saved and traceability recalculated.")
                _refresh()
            except ValueError as exc:
                st.error(str(exc))

    export_col_1, export_col_2, export_col_3 = st.columns(3)
    markdown_downloaded = export_col_1.download_button(
        "Download Markdown",
        intelligence.export_service.markdown(brief),
        file_name=f"{brief.brief_id}.md",
        mime="text/markdown",
    )
    json_downloaded = export_col_2.download_button(
        "Download Structured JSON",
        intelligence.export_service.json(brief),
        file_name=f"{brief.brief_id}.json",
        mime="application/json",
    )
    csv_downloaded = export_col_3.download_button(
        "Download Claims CSV",
        intelligence.export_service.claims_csv(brief),
        file_name=f"{brief.brief_id}_claims.csv",
        mime="text/csv",
    )
    if markdown_downloaded or json_downloaded or csv_downloaded:
        workflow.usage_service.record(
            "export",
            "CompetitorBrief",
            brief.brief_id,
            metadata={
                "format": "markdown" if markdown_downloaded else "json" if json_downloaded else "csv"
            },
            is_synthetic=brief.is_demo,
        )

    st.markdown("#### Management & Sales Outputs")
    executive_tab, sales_tab = st.tabs(["Executive Brief", "Sales Enablement"])
    with executive_tab:
        executive = workflow.executive_brief_repository.get_by_brief(brief.brief_id)
        if executive:
            for section, lines in executive.sections.items():
                with st.container(border=True):
                    st.markdown(f"#### {section}")
                    st.markdown("\n".join(f"- {line}" for line in lines) or "No content.")
        elif st.button("Create Executive Brief", key=f"create_exec_brief_{brief.brief_id}"):
            with st.spinner("Creating an Executive view from reviewed Claims and Evidence..."):
                workflow.executive_brief_service.create(brief.brief_id)
            _refresh()
        else:
            empty_state("No Executive Brief", "This source Brief has no derived management view.", "Create an Executive Brief.")
    with sales_tab:
        sales = workflow.sales_enablement_repository.get_by_brief(brief.brief_id)
        if sales:
            for section, entries in sales.sections.items():
                with st.container(border=True):
                    st.markdown(f"#### {section}")
                    for entry in entries:
                        if isinstance(entry, dict):
                            st.markdown(" · ".join(f"**{key.replace('_', ' ').title()}:** {value}" for key, value in entry.items()))
                        else:
                            st.markdown(f"- {entry}")
        elif st.button("Create Sales Enablement", key=f"create_sales_brief_{brief.brief_id}"):
            with st.spinner("Creating Sales Enablement from reviewed Claims and Evidence..."):
                workflow.sales_enablement_service.create(brief.brief_id)
            _refresh()
        else:
            empty_state("No Sales Enablement output", "This source Brief has no derived sales view.", "Create Sales Enablement.")


def run_healthcare_app(database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    st.set_page_config(
        page_title="Healthcare Market Intelligence",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_design_system()
    with st.spinner("Loading the healthcare intelligence workspace..."):
        foundation, intelligence, workflow = get_foundation(str(database_path))
    _, by_id, by_name = _category_maps(foundation)

    with st.sidebar:
        st.markdown("### Healthcare Intelligence")
        st.caption("Portfolio Release Candidate")
        st.markdown(
            '<span class="hmi-badge hmi-badge-info">Demo mode</span> '
            '<span class="hmi-badge hmi-badge-neutral">Synthetic data</span>',
            unsafe_allow_html=True,
        )
        st.divider()
        navigation = st.radio(
            "Primary navigation",
            PRIMARY_NAVIGATION,
            label_visibility="collapsed",
            key="primary_navigation",
        )
        st.divider()
        with st.expander("Demo guide", expanded=False):
            st.markdown(
                "1. Explore monitored Vendors\n\n"
                "2. Open a Vendor profile\n\n"
                "3. Compare three Vendors\n\n"
                "4. Review traceable Claims\n\n"
                "5. Export decision-ready intelligence"
            )
        st.caption(f"v{PORTFOLIO_VERSION} · Synthetic evaluation environment")

    demo_banner()
    try:
        if navigation == "Overview":
            render_overview(foundation, intelligence, workflow, by_id)
        elif navigation == "Intelligence":
            page_header(
                "Monitor",
                "Intelligence",
                "Track recent healthcare IT signals and keep priority Vendors current.",
            )
            view = st.radio(
                "Intelligence workspace",
                ["Feed", "Watchlist"],
                horizontal=True,
                label_visibility="collapsed",
                key="intelligence_workspace",
            )
            if view == "Feed":
                render_intelligence_feed(foundation, workflow, by_id)
            else:
                render_watchlist(foundation, workflow, by_id)
        elif navigation == "Vendors":
            render_vendor_library(foundation, intelligence, workflow, by_id)
        elif navigation == "Evidence":
            render_evidence_library(foundation, intelligence, workflow, by_id, by_name)
        elif navigation == "Market":
            page_header(
                "Analyze",
                "Market",
                "Explore monitored solution coverage, structured comparisons, and evidence-based opportunities.",
            )
            view = st.radio(
                "Market workspace",
                ["Market Map", "Compare", "Opportunities"],
                horizontal=True,
                label_visibility="collapsed",
                key="market_workspace",
            )
            if view == "Market Map":
                render_market_map(foundation, workflow, by_id)
            elif view == "Compare":
                render_comparison(foundation, intelligence, workflow)
            else:
                render_opportunities(foundation, workflow)
        elif navigation == "Briefs":
            render_briefs_and_claims(foundation, intelligence, workflow)
        elif navigation == "Review":
            render_review_queue(foundation, intelligence, workflow)
        elif navigation == "Analytics":
            page_header(
                "Measure",
                "Analytics",
                "Monitor coverage, evidence quality, intelligence output, workflow activity, and evaluation limits.",
            )
            view = st.radio(
                "Analytics workspace",
                ["Dashboard", "Benchmark"],
                horizontal=True,
                label_visibility="collapsed",
                key="analytics_workspace",
            )
            if view == "Dashboard":
                render_analytics(foundation, workflow)
            else:
                render_benchmark(workflow)
        else:
            page_header(
                "Configure",
                "Settings",
                "Review runtime mode, evidence rules, and system health without exposing secrets.",
            )
            view = st.radio(
                "Settings workspace",
                ["Runtime & Data", "Rules", "System Health"],
                horizontal=True,
                label_visibility="collapsed",
                key="settings_workspace",
            )
            if view == "System Health":
                render_integrity(foundation)
            else:
                render_settings(view)
    except Exception as exc:
        error_state(
            "This workspace could not be loaded",
            "The underlying data or configuration is unavailable. Try the page again or review System Health.",
            repr(exc),
        )
