"""Operational Streamlit UI for the Healthcare intelligence product."""

from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
import re

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
    priority_card,
    progress_card,
    section_header,
    signal_card,
    status_badge,
    workflow_steps,
    workspace_context,
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
PORTFOLIO_VERSION = "1.1.0"

UI_ZH = {
    "Overview": "概览",
    "Intelligence": "情报动态",
    "Vendors": "竞品库",
    "Evidence": "证据库",
    "Market": "市场分析",
    "Briefs": "简报",
    "Review": "审核",
    "Analytics": "数据分析",
    "Settings": "设置",
    "Feed": "情报流",
    "Watchlist": "关注列表",
    "Market Map": "市场地图",
    "Compare": "竞品对比",
    "Opportunities": "机会点",
    "Dashboard": "仪表盘",
    "Benchmark": "效率评估",
    "Runtime & Data": "运行与数据",
    "Rules": "规则",
    "System Health": "系统健康",
    "All": "全部",
    "All signals": "全部动态",
    "High priority": "高优先级",
    "Watchlist only": "仅看关注竞品",
    "Procurement": "招投标",
    "Case studies": "客户案例",
    "Solution updates": "产品更新",
    "Priority first": "优先级优先",
    "Newest first": "最新优先",
    "Oldest first": "最早优先",
    "HIGH": "高",
    "MEDIUM": "中",
    "LOW": "低",
    "FRESH": "最新",
    "AGING": "临近过期",
    "OUTDATED": "已过期",
    "VALID": "有效",
    "WARNING": "需注意",
    "INVALID": "无效",
    "PENDING": "待处理",
    "APPROVED": "已批准",
    "REJECTED": "已驳回",
    "SUPPORTED": "有证据支持",
    "PARTIALLY_SUPPORTED": "部分支持",
    "UNSUPPORTED": "无证据支持",
    "DRAFT": "草稿",
    "IN_REVIEW": "审核中",
    "NEEDS_REVISION": "需修改",
    "FINAL": "已定稿",
    "MANUAL": "人工流程",
    "AI_ASSISTED": "智能辅助流程",
    "PASS": "通过",
    "FAIL": "未通过",
    "COMPLETE": "已完成",
    "COMPARABLE": "可比",
    "SYNTHETIC": "模拟数据",
    "FACT": "事实",
    "INFERENCE": "分析推断",
    "RECOMMENDATION": "行动建议",
    "VENDOR_INTELLIGENCE": "竞品情报",
    "COMPARISON": "竞品对比",
    "Executive Summary": "执行摘要",
    "Key Intelligence": "核心情报",
    "Claims": "声明",
    "Evidence Citations": "证据引用",
    "Sources": "来源",
    "Overview": "概览",
    "Solution Coverage": "方案覆盖",
    "Positioning": "市场定位",
    "Synthesis": "综合分析",
    "NEW_EVIDENCE": "新增证据",
    "VENDOR_UPDATED": "竞品更新",
    "NEW_CASE_STUDY": "新增客户案例",
    "NEW_PROCUREMENT_SIGNAL": "新增招投标动态",
    "NEW_SOLUTION_SIGNAL": "新增产品动态",
    "BRIEF_GENERATED": "已生成简报",
    "CLAIM_REVIEWED": "声明已审核",
    "IMPORTANT_INTELLIGENCE": "重要情报",
    "SOLUTION_WHITE_SPACE": "方案空白",
    "MESSAGING_WHITE_SPACE": "传播空白",
    "COMPETITOR_WEAKNESS": "竞品薄弱点",
    "EVIDENCE_GAP": "证据缺口",
    "SALES_ENABLEMENT": "销售支持",
    "Active": "启用",
    "Archived": "已归档",
    "New": "新建",
    "Validated": "已验证",
    "Needs Review": "待审核",
    "Hospital": "医院",
    "Healthcare Group": "医疗集团",
    "Regional Health Authority": "区域卫生主管部门",
    "Government": "政府机构",
    "Medical Institution": "医疗机构",
    "Insurance / Payer": "医保／支付方",
    "Other": "其他",
    "Healthcare IT Vendor": "医疗信息化厂商",
    "Hospital Software Vendor": "医院软件厂商",
    "Healthcare Data Vendor": "医疗数据厂商",
    "Digital Health Solution Provider": "数字医疗解决方案商",
    "Integrated Healthcare Technology Provider": "综合医疗科技服务商",
    "Vendor Website": "厂商官网",
    "Solution Page": "产品页面",
    "Hospital Case Study": "医院案例",
    "Public Procurement": "公开采购",
    "Tender Announcement": "招标公告",
    "Industry Report": "行业报告",
    "Company Announcement": "公司公告",
    "Press Release": "新闻稿",
    "News": "新闻",
    "Manual Entry": "人工录入",
    "CSV Import": "CSV 导入",
    "JSON Import": "JSON 导入",
    "HIS": "医院信息系统（HIS）",
    "EMR / EHR": "电子病历／电子健康档案",
    "Clinical Information Systems": "临床信息系统",
    "Hospital Management": "医院运营管理",
    "Healthcare Data Platform": "医疗数据平台",
    "Regional Healthcare Platform": "区域医疗平台",
    "Digital Hospital": "数字医院",
    "Smart Healthcare": "智慧医疗",
    "Patient Services": "患者服务",
    "Healthcare Analytics": "医疗数据分析",
    "Healthcare Cloud": "医疗云",
    "Medical Insurance Information Systems": "医保信息系统",
    "Data Governance": "数据治理",
    "Interoperability / Integration": "互操作与系统集成",
}


def _zh(value: object) -> str:
    shown = str(value or "")
    return UI_ZH.get(shown, UI_ZH.get(shown.upper(), shown.replace("_", " ")))


def _zh_text(value: object) -> str:
    """Localise recurring demonstration titles without altering stored source data."""
    shown = str(value or "")
    replacements = (
        ("Evidence depth check for ", "证据深度检查："),
        ("Evidence-backed sales enablement opportunity", "证据驱动的销售支持机会"),
        ("Messaging white-space hypothesis", "市场传播空白假设"),
        ("Competitor weakness research hypothesis", "竞品薄弱点研究假设"),
        ("No solution white space detected in the monitored set", "当前监测范围内未发现方案空白"),
        ("New procurement signal: ", "新增招投标动态："),
        ("Integrated hospital platform overview", "一体化医院平台概览"),
        ("Clinical workflow solution description", "临床工作流解决方案说明"),
        ("Synthetic hospital deployment case", "模拟医院部署案例"),
        ("Regional platform procurement notice", "区域平台采购公告"),
        ("Interoperability tender announcement", "互操作项目招标公告"),
        ("Healthcare data market observation", "医疗数据市场观察"),
        ("Company product portfolio update", "公司产品组合更新"),
        ("Digital hospital programme release", "数字医院项目发布"),
        ("Patient service implementation news", "患者服务实施动态"),
        ("Manual analyst observation", "分析师人工观察"),
        ("Imported solution capability record", "导入的方案能力记录"),
        ("Imported data governance record", "导入的数据治理记录"),
        ("Healthcare cloud service description", "医疗云服务说明"),
        ("Analytics implementation case", "数据分析实施案例"),
        ("Evidence quality control sample", "证据质量控制样本"),
        ("Synthetic Phase 4", "模拟第四阶段"),
        ("Clinical Information Systems", "临床信息系统"),
        ("Hospital Case Study", "医院案例"),
        ("Public Procurement", "公开采购"),
        ("Solution Page", "产品页面"),
        ("Synthetic workflow signal; demonstration use only.", "模拟工作流信号，仅用于演示。"),
        ("workflow signal", "工作流信号"),
    )
    for source, target in replacements:
        shown = shown.replace(source, target)
    shown = shown.replace(
        "No binary coverage gap is detected; a quality/freshness gap may still exist and requires record-level assessment.",
        "未发现明确的覆盖缺口，但仍可能存在质量或时效性问题，需要逐条核查记录。",
    )
    shown = shown.replace(
        "The current intelligence can support a more consistent evidence-aware sales conversation.",
        "当前情报可帮助销售团队形成更一致、以证据为依据的客户沟通。",
    )
    shown = shown.replace(
        "Current messaging themes may leave room for a more explicitly evidence-led differentiation narrative.",
        "当前传播主题仍可强化以证据为核心的差异化表达。",
    )
    shown = shown.replace(
        "The interpretations may indicate a differentiable weakness, but require reviewer confirmation and more direct Evidence.",
        "现有分析可能反映可形成差异化的竞品薄弱点，但仍需审核确认并补充直接证据。",
    )
    shown = shown.replace(
        "Every monitored Vendor has at least one qualifying cell in every currently mapped category, so the current dataset does not support a solution white-space claim.",
        "当前监测竞品在各已映射类别中均至少有一项合格记录，因此现有数据不足以支持方案空白结论。",
    )
    shown = shown.replace("Healthcare Vendor Intelligence", "医疗信息化竞品情报")
    shown = shown.replace("Healthcare Vendor Comparison", "医疗信息化竞品对比")
    shown = shown.replace(" vs ", " 对比 ")
    shown = shown.replace("Evidence-grounded Vendor intelligence for ", "基于证据生成的竞品情报：")
    shown = shown.replace(", generated from ", "；使用 ")
    shown = shown.replace(" selected record(s). Facts, inferences, and recommendations are separated below.", " 条筛选记录生成。下方内容明确区分事实、推断和建议。")
    shown = shown.replace("Evidence-grounded comparison of ", "基于证据对比 ")
    shown = shown.replace(" Vendors using ", " 家竞品，使用 ")
    shown = shown.replace(" selected record(s). The first layer is factual coverage; the second layer contains labelled analysis and recommendations.", " 条筛选记录。第一层为事实覆盖，第二层为明确标注的分析与建议。")
    shown = shown.replace(" has selected Evidence associated with the observed solution areas: ", "的所选证据覆盖以下方案领域：")
    shown = shown.replace(" selected Hospital Case Study record(s).", " 条所选医院案例记录。")
    shown = shown.replace(" selected procurement or tender signal(s).", " 条所选采购或招标动态。")
    shown = shown.replace(" has observable institutional or customer signals through: ", "可通过以下来源观察到机构或客户信号：")
    shown = shown.replace(" selected Evidence record(s), including ", " 条所选证据记录，其中包括 ")
    shown = shown.replace(" High-authority record(s).", " 条高权威性记录。")
    shown = shown.replace("'s selected Evidence covers these observed solution areas: ", "的所选证据覆盖以下可观察方案领域：")
    shown = shown.replace("'s observable positioning and messaging themes must be interpreted from its selected source titles, summaries, and solution categories.", "的可观察定位与传播主题，必须根据所选来源标题、摘要和方案类别进行分析。")
    shown = shown.replace("The selected Evidence suggests that ", "所选证据显示，")
    shown = shown.replace("'s observed strength is breadth across ", "的可观察优势是覆盖 ")
    shown = shown.replace(" visible Healthcare IT solution areas.", " 个可见的医疗信息化方案领域。")
    shown = shown.replace("The current messaging evidence positions ", "当前传播证据显示，")
    shown = shown.replace(" around integrated Healthcare IT delivery and operational use cases.", "的定位围绕一体化医疗信息化交付和运营场景。")
    shown = shown.replace("The selected source mix provides observable target-customer signals for: ", "所选来源组合提供了以下可观察目标客户信号：")
    shown = shown.replace("Marketing and sales teams should prioritise claims that can cite ", "市场与销售团队应优先使用能够引用")
    shown = shown.replace("'s validated institutional, procurement, and solution Evidence.", "已验证机构、采购及方案证据的声明。")
    shown = shown.replace("INSUFFICIENT EVIDENCE: ", "证据不足：")
    shown = shown.replace("Market share, revenue, customer totals, and industry ranking cannot be determined from this Evidence Pack.", "无法根据当前证据包判断市场份额、收入、客户总数和行业排名。")
    shown = shown.replace("Comparative revenue, market share, customer totals, and implementation scale cannot be ranked from this Evidence Pack.", "无法根据当前证据包比较收入、市场份额、客户总数和实施规模。")
    shown = shown.replace("The compared Vendors share observed Evidence in: ", "参与对比的竞品在以下领域均有可观察证据：")
    shown = shown.replace("Differences in selected source coverage and solution-category breadth indicate distinct observable positioning patterns across the Vendors.", "所选来源覆盖和方案类别广度的差异，反映出各竞品不同的可观察定位模式。")
    shown = shown.replace("Position marketing and sales messages around Evidence-backed solution and institutional strengths while explicitly labelling areas with insufficient coverage.", "市场与销售表达应围绕有证据支持的方案和机构优势，并明确标注覆盖不足的领域。")
    category_terms = {
        "clinical_information_systems": "临床信息系统", "data_governance": "数据治理",
        "digital_hospital": "数字医院", "emr_ehr": "电子病历／电子健康档案",
        "healthcare_analytics": "医疗数据分析", "healthcare_cloud": "医疗云",
        "healthcare_data_platform": "医疗数据平台", "his": "医院信息系统",
    }
    for source, target in category_terms.items():
        shown = re.sub(rf"\b{re.escape(source)}\b", target, shown)
    return shown


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
    return "、".join(_zh(by_id.get(item, item)) for item in category_ids)


def _refresh() -> None:
    st.cache_data.clear()
    st.rerun()


def _navigate_to(page: str, workspace_key: str = "", workspace_value: str = "") -> None:
    """Route a quick action before Streamlit rebuilds the destination widgets."""
    st.session_state["primary_navigation"] = page
    if workspace_key and workspace_value:
        st.session_state[workspace_key] = workspace_value


def _percent(numerator: int | float, denominator: int | float) -> float:
    return round(float(numerator) / float(denominator) * 100, 1) if denominator else 0.0


def _readiness_rates(analytics: dict, queue: dict, watchlist: list[dict]) -> dict[str, float]:
    current_watchlist = sum(
        not item["freshness"]["needs_intelligence_refresh"] for item in watchlist
    )
    return {
        "evidence_validation": _percent(
            analytics["validated_evidence_count"], analytics["evidence_count"]
        ),
        "brief_review": _percent(analytics["review_count"], analytics["brief_count"]),
        "traceability": float(analytics["traceability_rate"] or 0.0),
        "watchlist_freshness": _percent(current_watchlist, len(watchlist)),
        "open_actions": float(
            len(queue["briefs_awaiting_review"])
            + len(queue["claims_awaiting_review"])
            + len(queue["evidence_needing_validation"])
        ),
    }


def _signal_priority(event) -> int:
    importance = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(event.importance, 0)
    event_weight = {
        "IMPORTANT_INTELLIGENCE": 6,
        "NEW_PROCUREMENT_SIGNAL": 5,
        "NEW_CASE_STUDY": 4,
        "NEW_SOLUTION_SIGNAL": 3,
        "BRIEF_GENERATED": 1,
    }.get(event.event_type, 0)
    return importance * 10 + event_weight


def _matches_signal(event, query: str, vendor_name: str) -> bool:
    if not query.strip():
        return True
    haystack = " ".join(
        str(value or "")
        for value in (
            event.title,
            event.summary,
            event.event_type,
            event.source_type,
            vendor_name,
        )
    ).lower()
    return query.strip().lower() in haystack


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
        "情报工作台",
        "医疗行业市场情报概览",
        "集中查看重要动态、证据缺口和待审核输出。",
    )
    stats = foundation.statistics()
    analytics = workflow.analytics_service.snapshot()
    queue = workflow.brief_workflow_service.queue()
    watchlist = workflow.watchlist_service.list_details()
    vendors = foundation.vendor_service.list_vendors(include_archived=True)
    vendor_names = {vendor.vendor_id: vendor.vendor_name for vendor in vendors}
    readiness = _readiness_rates(analytics, queue, watchlist)

    workspace_context(
        ("监测范围", f"{analytics['active_vendor_count']} 家活跃竞品"),
        ("数据来源", "当前 SQLite 数据快照"),
        ("数据模式", "模拟评估数据"),
        ("待办事项", int(readiness["open_actions"])),
    )

    kpis = st.columns(4)
    with kpis[0]:
        metric_card("活跃竞品", analytics["active_vendor_count"], "当前监测范围")
    with kpis[1]:
        metric_card(
            "证据记录",
            analytics["evidence_count"],
            f"已验证 {readiness['evidence_validation']:.0f}%",
        )
    with kpis[2]:
        metric_card(
            "情报简报",
            analytics["brief_count"],
            f"共 {analytics['claim_count']} 条声明",
        )
    with kpis[3]:
        traceability = _metric_value(analytics["traceability_rate"], "%").upper()
        metric_card(
            "来源可追溯率",
            traceability,
            f"已审核声明中 {analytics['traceable_claim_count']} / {analytics['reviewed_claim_count']} 可追溯",
        )

    workflow_steps(
        [
            ("监测", "收集竞品与市场记录"),
            ("研判", "按重要性和时间排序"),
            ("核验", "检查来源与引用状态"),
            ("分析", "比较方案覆盖和市场定位"),
            ("发布", "审核并导出情报输出"),
        ]
    )

    section_header("工作流健康度", "当前流程覆盖情况")
    health = st.columns(4)
    with health[0]:
        progress_card(
            "证据验证率",
            readiness["evidence_validation"],
            f"{analytics['validated_evidence_count']} / {analytics['evidence_count']} 条记录已验证",
        )
    with health[1]:
        progress_card(
            "简报审核覆盖率",
            readiness["brief_review"],
            f"{analytics['review_count']} / {analytics['brief_count']} 份简报已审核",
        )
    with health[2]:
        progress_card(
            "已审核声明可追溯率",
            readiness["traceability"],
            "仅用于评估样本；证据支持度单独计算",
        )
    with health[3]:
        progress_card(
            "关注列表新鲜度",
            readiness["watchlist_freshness"],
            f"{sum(not item['freshness']['needs_intelligence_refresh'] for item in watchlist)} / {len(watchlist)} 个档案保持最新",
        )

    section_header("待办队列", "需要人工处理的事项")
    attention = st.columns(4)
    with attention[0]:
        priority_card(
            "简报审核",
            len(queue["briefs_awaiting_review"]),
            "等待人工审核的简报。",
            "warning",
        )
    with attention[1]:
        priority_card(
            "证据缺口",
            len(queue["unsupported_claims"]),
            "需要补充证据、修改或删除的声明。",
            "danger",
        )
    with attention[2]:
        priority_card(
            "证据验证",
            len(queue["evidence_needing_validation"]),
            "验证状态尚未处理的证据记录。",
            "warning",
        )
    with attention[3]:
        outdated = sum(item["freshness"]["needs_intelligence_refresh"] for item in watchlist)
        priority_card(
            "情报更新",
            outdated,
            "情报基础已过期的重点竞品档案。",
            "success" if not outdated else "warning",
        )
    action_cols = st.columns(4)
    action_cols[0].button(
        "打开审核队列",
        type="primary",
        use_container_width=True,
        on_click=_navigate_to,
        args=("Review",),
    )
    action_cols[1].button(
        "打开情报流",
        use_container_width=True,
        on_click=_navigate_to,
        args=("Intelligence", "intelligence_workspace", "Feed"),
    )
    action_cols[2].button(
        "竞品对比",
        use_container_width=True,
        on_click=_navigate_to,
        args=("Market", "market_workspace", "Compare"),
    )
    action_cols[3].button(
        "查看数据分析",
        use_container_width=True,
        on_click=_navigate_to,
        args=("Analytics", "analytics_workspace", "Dashboard"),
    )

    left, right = st.columns([1.5, 1], gap="large")
    with left:
        section_header("重要动态", "按优先级和时间排序")
        recent = workflow.feed_repository.list_all(limit=30)
        recent = sorted(
            recent,
            key=lambda event: (_signal_priority(event), event.event_date),
            reverse=True,
        )[:6]
        if not recent:
            empty_state(
                "暂无情报动态",
                "新增证据、简报或审核事件后，系统会在此显示动态。",
                "请先导入证据或生成简报。",
            )
        for event in recent:
            vendor = vendor_names.get(event.vendor_id, "全局")
            signal_card(
                _zh_text(event.title),
                _zh_text(event.summary) or "暂无补充摘要。",
                f"{event.event_date} · {vendor} · {_zh(event.source_type or event.event_type)}",
                event.importance,
            )
    with right:
        section_header("关注竞品", "近期监测动态")
        if not watchlist:
            empty_state(
                "关注列表为空",
                "关注重点竞品后，可在此查看新增证据和情报更新提醒。",
                "请打开“情报动态 → 关注列表”。",
            )
        ordered_watchlist = sorted(
            watchlist,
            key=lambda item: (
                item["freshness"]["needs_intelligence_refresh"],
                item["new_evidence_since_last_view"],
            ),
            reverse=True,
        )
        for item in ordered_watchlist[:5]:
            freshness = "OUTDATED" if item["freshness"]["needs_intelligence_refresh"] else "FRESH"
            latest_signal = item["latest_procurement_signal"]
            signal_card(
                item["vendor"].vendor_name,
                _zh_text(latest_signal.source_title) if latest_signal else "暂无近期招投标动态",
                f"新增 {item['new_evidence_since_last_view']} 条 · 共 {item['evidence_count']} 条证据",
                "HIGH" if freshness == "OUTDATED" else "LOW",
            )

    section_header("覆盖情况", "证据覆盖，不代表市场份额")
    coverage_tab, sources_tab = st.tabs(["方案覆盖", "证据来源构成"])
    with coverage_tab:
        category_frame = pd.DataFrame(
            [
                {"方案类别": _zh(by_id.get(key, key)), "证据数量": value}
                for key, value in stats["solution_categories"].items()
            ]
        )
        if category_frame.empty:
            empty_state("暂无方案覆盖数据", "已验证证据尚未映射到医疗信息化分类体系。")
        else:
            st.bar_chart(category_frame.set_index("方案类别"), color="#0b7595")
    with sources_tab:
        source_frame = pd.DataFrame(
            [(_zh(key), value) for key, value in stats["source_types"].items()], columns=["来源类型", "证据数量"]
        )
        if source_frame.empty:
            empty_state("暂无来源分布", "目前没有可用于汇总的证据来源。")
        else:
            st.bar_chart(source_frame.set_index("来源类型"), color="#5f8799")
    st.caption(
        "覆盖情况仅反映当前模拟评估数据集中的证据记录，不代表整体市场份额。"
    )


def render_vendor_library(foundation, intelligence, workflow, by_id: dict[str, str]) -> None:
    vendor_service = foundation.vendor_service
    page_header(
        "竞品研究",
        "竞品情报库",
        "检索监测竞品、查看来源可追溯的档案，并更新结构化情报。",
    )

    search_col, type_col, archive_col = st.columns([2, 1, 1])
    search = search_col.text_input("搜索竞品", key="vendor_search")
    type_filter = type_col.selectbox("竞品类型", ["All", *VENDOR_TYPES], format_func=_zh, key="vendor_type_filter")
    include_archived = archive_col.checkbox("包含已归档竞品", value=False)
    vendors = vendor_service.list_vendors(include_archived, search)
    if type_filter != "All":
        vendors = [vendor for vendor in vendors if vendor.vendor_type == type_filter]

    followed_ids = {
        entry.vendor_id for entry in workflow.watchlist_service.repository.list_all()
    }
    vendor_summary = st.columns(4)
    with vendor_summary[0]:
        metric_card("匹配竞品", len(vendors), "当前筛选结果")
    with vendor_summary[1]:
        metric_card(
            "已关注",
            sum(vendor.vendor_id in followed_ids for vendor in vendors),
            "重点监测范围",
        )
    with vendor_summary[2]:
        metric_card(
            "证据覆盖",
            sum(vendor.evidence_count for vendor in vendors),
            "当前结果关联的证据记录",
        )
    with vendor_summary[3]:
        metric_card(
            "需要更新",
            sum(
                workflow.quality_service.vendor_freshness(vendor.vendor_id)[
                    "needs_intelligence_refresh"
                ]
                for vendor in vendors
            ),
            "情报基础已过期的档案",
        )

    vendor_frame = pd.DataFrame(
        [
            {
                "竞品 ID": vendor.vendor_id,
                "竞品名称": vendor.vendor_name,
                "类型": _zh(vendor.vendor_type),
                "主要市场": vendor.primary_market,
                "方案类别": _category_names(vendor.solution_categories, by_id),
                "证据数量": vendor.evidence_count,
                "状态": _zh(vendor.status),
                "模拟数据": "是" if vendor.is_synthetic else "否",
                "最后更新": vendor.last_updated,
            }
            for vendor in vendors
        ]
    )
    if vendor_frame.empty:
        empty_state(
            "没有符合条件的竞品",
            "竞品库中没有匹配当前搜索和类型筛选的记录。",
            "请清除筛选条件，或在下方新增竞品。",
        )
    else:
        st.caption(f"共找到 {len(vendor_frame)} 家竞品")
        st.dataframe(vendor_frame.head(100), width="stretch", hide_index=True)

    with st.expander("新增竞品", expanded=False):
        with st.form("create_vendor_form", clear_on_submit=True):
            name = st.text_input("竞品名称")
            vendor_type = st.selectbox("竞品类型", VENDOR_TYPES, format_func=_zh)
            primary_market = st.text_input("主要市场")
            summary = st.text_area("公司简介")
            headquarters = st.text_input("总部所在地")
            website = st.text_input("官网", placeholder="https://example.com")
            customer_types = st.multiselect("目标客户", TARGET_CUSTOMER_TYPES, format_func=_zh)
            is_synthetic = st.checkbox("标记为模拟／演示竞品")
            submitted = st.form_submit_button("新增竞品", type="primary")
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
                    st.success(f"已新增竞品：{vendor.vendor_name}（{vendor.vendor_id}）。")
                    _refresh()
                except ValueError as exc:
                    st.error(str(exc))

    all_vendors = vendor_service.list_vendors(include_archived=True)
    if not all_vendors:
        empty_state("竞品库为空", "需要先创建竞品，才能关联和监测证据。", "请在上方新增竞品。")
        return
    options = {f"{vendor.vendor_name} · {vendor.vendor_id}": vendor for vendor in all_vendors}
    selected_label = st.selectbox("查看竞品", options=list(options))
    selected = options[selected_label]
    _log_view_once(workflow, "vendor_view", "Vendor", selected.vendor_id, selected.is_synthetic)

    section_header(selected.vendor_name, _zh(selected.vendor_type))
    vendor_badges = status_badge(selected.status)
    if selected.is_synthetic:
        vendor_badges += " " + status_badge("SYNTHETIC")
    st.markdown(vendor_badges, unsafe_allow_html=True)
    detail_left, detail_right = st.columns(2)
    detail_left.markdown(
        f"**公司简介：** {selected.company_summary}\n\n"
        f"**主要市场：** {selected.primary_market}\n\n"
        f"**总部所在地：** {selected.headquarters}\n\n"
        f"**官网：** {selected.website}"
    )
    detail_right.markdown(
        f"**方案类别：** {_category_names(selected.solution_categories, by_id) or '暂无证据支持的类别'}\n\n"
        f"**目标客户：** {'、'.join(_zh(item) for item in selected.target_customer_types)}\n\n"
        f"**证据数量：** {selected.evidence_count}\n\n"
        f"**最后更新：** {selected.last_updated}\n\n"
        f"**状态：** {_zh(selected.status)}"
    )

    with st.expander("编辑竞品", expanded=False):
        with st.form(f"edit_vendor_{selected.vendor_id}"):
            edit_name = st.text_input("竞品名称", value=selected.vendor_name)
            edit_type = st.selectbox(
                "竞品类型",
                VENDOR_TYPES,
                index=VENDOR_TYPES.index(selected.vendor_type),
                format_func=_zh,
            )
            edit_market = st.text_input("主要市场", value=selected.primary_market)
            edit_summary = st.text_area("公司简介", value=selected.company_summary)
            edit_headquarters = st.text_input("总部所在地", value=selected.headquarters)
            edit_website = st.text_input("官网", value=selected.website)
            edit_customers = st.multiselect(
                "目标客户",
                TARGET_CUSTOMER_TYPES,
                default=selected.target_customer_types,
                format_func=_zh,
            )
            if st.form_submit_button("保存修改"):
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
                    st.success("竞品信息已更新。")
                    _refresh()
                except ValueError as exc:
                    st.error(str(exc))

    if selected.status != "Archived":
        if st.button("归档竞品", key=f"archive_{selected.vendor_id}"):
            vendor_service.archive_vendor(selected.vendor_id)
            st.success("竞品已归档，关联证据已保留。")
            _refresh()

    st.markdown("#### 竞品情报工作区")
    watch_entry = workflow.watchlist_service.repository.get_by_vendor(selected.vendor_id)
    watch_col, freshness_col = st.columns([1, 3])
    if watch_entry:
        if watch_col.button("取消关注", key=f"unfollow_vendor_{selected.vendor_id}"):
            workflow.watchlist_service.unfollow(selected.vendor_id)
            _refresh()
    else:
        if watch_col.button("关注竞品", key=f"follow_vendor_{selected.vendor_id}"):
            workflow.watchlist_service.follow(selected.vendor_id)
            _refresh()
    freshness = workflow.quality_service.vendor_freshness(selected.vendor_id)
    freshness_status = "OUTDATED" if freshness["needs_intelligence_refresh"] else "FRESH"
    freshness_col.markdown(
        status_badge(freshness_status)
        + f" <span style='color:#5c6b78;font-size:.9rem'>最近证据：{freshness.get('latest_evidence_date') or '暂无'}</span>",
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
        f"**情报摘要：** {_zh_text(profiles[0].company_overview) if profiles else '尚未生成竞品档案'}  \n"
        f"**简报：** {len(briefs)} · **近期动态：** {len(signals)} · "
        f"**最近情报更新：** {profiles[0].last_intelligence_update if profiles else '尚未生成'}"
    )
    with st.expander("生成或更新竞品情报", expanded=not bool(profiles)):
        include_warning = st.checkbox(
            "包含“需注意”状态的证据", key=f"intel_warning_{selected.vendor_id}"
        )
        api_key = _runtime_setting("OPENAI_API_KEY")
        model = _runtime_setting("OPENAI_MODEL", "gpt-5.6")
        st.caption(
            "生成模式：OpenAI；异常时使用确定性备用流程"
            if api_key else
            "生成模式：确定性结构化演示；无需 API 密钥"
        )
        if st.button(
            "生成竞品情报",
            type="primary",
            key=f"generate_vendor_intelligence_{selected.vendor_id}",
        ):
            try:
                with st.spinner("正在处理证据、生成竞品情报并验证声明……"):
                    profile, _, traceability = intelligence.vendor_intelligence_service.generate(
                        selected.vendor_id,
                        include_warning=include_warning,
                        api_key=api_key,
                        model=model,
                    )
                st.success(f"已生成情报档案 {profile.profile_id}；可追溯性校验：{_zh(traceability['result'])}。")
                _refresh()
            except (ValueError, RuntimeError) as exc:
                error_state(
                    "竞品情报生成失败",
                    "请检查该竞品的证据和运行配置后重试。",
                    str(exc),
                )
    if signals:
        st.markdown("#### 证据时间线")
        st.dataframe(
            pd.DataFrame([
                {
                    "日期": item.publication_date,
                    "类型": _zh(item.source_type),
                    "标题": _zh_text(item.source_title),
                    "证据 ID": item.evidence_id,
                    "验证状态": _zh(item.validation_status),
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
        ["招投标动态", "客户案例动态", "市场定位", "相关简报"]
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
                {"简报 ID": item.brief_id, "标题": _zh_text(item.title), "状态": _zh(item.status), "生成时间": item.generated_at}
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
        "来源管理",
        "证据库",
        "检索、筛选并验证简报和竞品对比所使用的来源记录。",
    )
    filter_cols = st.columns(4)
    vendor_labels = ["All"] + [f"{v.vendor_name} · {v.vendor_id}" for v in vendors]
    selected_vendor_label = filter_cols[0].selectbox("竞品", vendor_labels, format_func=_zh, key="evidence_vendor_filter")
    selected_vendor = (
        ""
        if selected_vendor_label == "All"
        else selected_vendor_label.rsplit(" · ", 1)[1]
    )
    selected_source = filter_cols[1].selectbox("来源类型", ["All", *SOURCE_TYPES], format_func=_zh, key="evidence_source_filter")
    selected_category_name = filter_cols[2].selectbox(
        "方案类别",
        ["All", *(category.name for category in categories)],
        format_func=_zh,
    )
    selected_validation = filter_cols[3].selectbox(
        "验证状态",
        ["All", *VALIDATION_STATUSES],
        format_func=_zh,
        key="evidence_validation_filter",
    )
    filter_cols_2 = st.columns([2, 1, 1])
    search = filter_cols_2[0].text_input("搜索标题或证据正文", key="evidence_search")
    selected_authority = filter_cols_2[1].selectbox(
        "来源权威性", ["All", *SOURCE_AUTHORITIES], format_func=_zh, key="evidence_authority_filter"
    )
    selected_freshness = filter_cols_2[2].selectbox(
        "时效性", ["All", "FRESH", "AGING", "OUTDATED"], format_func=_zh, key="evidence_freshness_filter"
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
    evidence_summary = st.columns(4)
    with evidence_summary[0]:
        metric_card("匹配证据", len(evidence), "当前筛选结果")
    with evidence_summary[1]:
        metric_card(
            "已验证",
            sum(item.validation_status == "Valid" for item in evidence),
            "应用去重规则前的有效记录",
        )
    with evidence_summary[2]:
        metric_card(
            "高质量证据",
            sum(
                assessments[item.evidence_id].quality_level == "HIGH" for item in evidence
            ),
            "基于透明规则的评分",
        )
    with evidence_summary[3]:
        metric_card(
            "最新证据",
            sum(
                assessments[item.evidence_id].freshness_status == "FRESH" for item in evidence
            ),
            "发布时间在时效阈值内",
        )
    evidence_frame = pd.DataFrame(
        [
            {
                "证据 ID": item.evidence_id,
                "竞品": vendor_by_id.get(item.vendor_id).vendor_name
                if item.vendor_id in vendor_by_id
                else item.vendor_id,
                "标题": _zh_text(item.source_title),
                "来源类型": _zh(item.source_type),
                "发布日期": item.publication_date,
                "方案类别": _category_names(item.solution_categories, by_id),
                "验证状态": _zh(item.validation_status),
                "来源权威性": _zh(item.source_authority),
                "时效性": _zh(assessments[item.evidence_id].freshness_status),
                "重复记录": "是" if item.duplicate_of_evidence_id else "否",
                "模拟数据": "是" if item.is_synthetic else "否",
            }
            for item in evidence
        ]
    )
    st.caption(f"共找到 {len(evidence)} 条记录 · 表格最多显示 100 条")
    if evidence:
        st.dataframe(evidence_frame.head(100), width="stretch", hide_index=True)
        labels = {f"{_zh_text(item.source_title)} · {item.evidence_id}": item for item in evidence}
        selected_label = st.selectbox("查看证据", list(labels))
        selected = labels[selected_label]
        _log_view_once(workflow, "evidence_view", "Evidence", selected.evidence_id, selected.is_synthetic)
        assessment = assessments[selected.evidence_id]
        section_header(_zh_text(selected.source_title), selected.evidence_id)
        badges = status_badge(selected.validation_status) + " " + status_badge(assessment.freshness_status)
        if selected.is_synthetic:
            badges += " " + status_badge("SYNTHETIC")
        st.markdown(badges, unsafe_allow_html=True)
        detail_tabs = st.tabs(["元数据", "摘要", "正文", "验证与质量", "关联声明"])
        with detail_tabs[0]:
            meta_cols = st.columns(3)
            meta_cols[0].metric("竞品", vendor_by_id.get(selected.vendor_id).vendor_name if selected.vendor_id in vendor_by_id else selected.vendor_id)
            meta_cols[1].metric("来源类型", _zh(selected.source_type))
            meta_cols[2].metric("发布日期", selected.publication_date)
            st.markdown(f"**方案覆盖：** {_category_names(selected.solution_categories, by_id) or '未分类'}")
            st.markdown(f"**来源权威性：** {_zh(selected.source_authority)}  \n**重复记录组：** {selected.duplicate_of_evidence_id or '主记录／唯一记录'}")
            if selected.source_url:
                st.link_button("打开原始来源", selected.source_url)
            else:
                st.caption("该人工录入／导入记录未提供来源链接。")
        with detail_tabs[1]:
            st.markdown(selected.summary or "暂无摘要。")
        with detail_tabs[2]:
            text_tabs = st.tabs(["清洗后文本", "原始文本"])
            text_tabs[0].text_area("清洗后的证据文本", selected.cleaned_text, height=260, disabled=True, label_visibility="collapsed")
            text_tabs[1].text_area("原始证据文本", selected.raw_text, height=260, disabled=True, label_visibility="collapsed")
        with detail_tabs[3]:
            quality_cols = st.columns(4)
            quality_cols[0].metric("验证状态", _zh(selected.validation_status))
            quality_cols[1].metric("证据状态", _zh(selected.evidence_status))
            quality_cols[2].metric("质量等级", _zh(assessment.quality_level))
            quality_cols[3].metric("质量评分", f"{assessment.quality_score} / 10")
            st.markdown(f"**时效性：** {_zh(assessment.freshness_status)} · 距今 {assessment.age_days} 天")
            if assessment.quality_explanation:
                st.markdown("\n".join(f"- {message}" for message in assessment.quality_explanation))
            if selected.validation_messages:
                st.markdown("**验证信息**")
                st.markdown("\n".join(f"- {message}" for message in selected.validation_messages))
        with detail_tabs[4]:
            related = []
            for brief in intelligence.brief_repository.list_all():
                for claim in brief.claims:
                    if selected.evidence_id in claim.evidence_ids:
                        related.append({
                            "简报": _zh_text(brief.title),
                            "声明": _zh_text(claim.claim_text),
                            "类型": _zh(claim.claim_type),
                            "证据支持": _zh(claim.support_level),
                            "审核状态": _zh(claim.review_status),
                        })
            if related:
                st.dataframe(pd.DataFrame(related), hide_index=True, width="stretch")
            else:
                empty_state("暂无关联声明", "现有声明尚未引用该证据记录。")
    else:
        empty_state(
            "没有符合条件的证据",
            "请放宽筛选条件或新增来源记录。",
            "可清除筛选条件，或使用下方的“导入／新增证据”。",
        )

    with st.expander("导入／新增证据", expanded=False):
        if not vendors:
            empty_state("需要先创建竞品", "证据必须关联到有效竞品。", "请先创建竞品。")
            return
        add_tab, csv_tab, json_tab = st.tabs(["粘贴文本", "CSV", "JSON"])
        with add_tab:
            with st.form("add_evidence_form", clear_on_submit=True):
                vendor_label = st.selectbox("竞品", [f"{v.vendor_name} · {v.vendor_id}" for v in vendors], key="manual_vendor")
                source_type = st.selectbox("来源类型", SOURCE_TYPES, format_func=_zh)
                title = st.text_input("来源标题")
                source_url = st.text_input("来源链接（人工录入／导入记录可不填）")
                publication_date = st.date_input("发布日期").isoformat()
                raw_text = st.text_area("粘贴原始证据文本", height=160)
                summary = st.text_area("摘要（选填）")
                category_names = st.multiselect("方案类别", [category.name for category in categories], format_func=_zh)
                authority = st.selectbox("来源权威性", SOURCE_AUTHORITIES, format_func=_zh)
                synthetic = st.checkbox("标记为模拟／演示证据")
                submitted = st.form_submit_button("新增证据", type="primary")
            if submitted:
                try:
                    item = evidence_service.create_evidence({
                        "vendor_id": vendor_label.rsplit(" · ", 1)[1], "source_type": source_type,
                        "source_title": title, "source_url": source_url, "publication_date": publication_date,
                        "raw_text": raw_text, "summary": summary,
                        "solution_categories": [by_name[name] for name in category_names],
                        "source_authority": authority, "is_synthetic": synthetic,
                    })
                    st.success(f"证据已保存为 {item.evidence_id} · {_zh(item.validation_status)}。")
                    _refresh()
                except ValueError as exc:
                    error_state("无法新增证据", "请检查必填字段和来源元数据。", str(exc))
        with csv_tab:
            st.caption("必填字段：vendor_id、source_title、publication_date、raw_text、solution_categories。")
            csv_file = st.file_uploader("证据 CSV 文件", type=["csv"], key="evidence_csv")
            if st.button("导入 CSV", disabled=csv_file is None):
                try:
                    with st.spinner("正在导入并校验证据……"):
                        result = evidence_service.import_csv(csv_file.getvalue())
                    st.success(f"已创建 {result.created_count} 条；拒绝 {result.rejected_count} 条。")
                except (ValueError, TypeError) as exc:
                    error_state("证据导入失败", "请检查 CSV 结构和字段值。", str(exc))
        with json_tab:
            st.caption("JSON 可直接为证据列表，也可为包含 evidence 列表的对象。")
            json_file = st.file_uploader("证据 JSON 文件", type=["json"], key="evidence_json")
            if st.button("导入 JSON", disabled=json_file is None):
                try:
                    with st.spinner("正在导入并校验证据……"):
                        result = evidence_service.import_json(json_file.getvalue())
                    st.success(f"已创建 {result.created_count} 条；拒绝 {result.rejected_count} 条。")
                except (ValueError, TypeError) as exc:
                    error_state("证据导入失败", "请确认文件包含有效的结构化证据。", str(exc))


def render_integrity(foundation) -> None:
    st.markdown("#### 数据完整性")
    st.caption(
        "检查 ID、竞品引用、分类值、来源类型、哈希、日期、状态、孤立记录、重复标记和竞品指标。"
    )
    if st.button("运行数据完整性检查", type="primary"):
        report = run_integrity_checks(foundation.category_repository.database)
        if report["status"] == "PASS":
            st.success("数据完整性检查：通过")
        else:
            st.error("数据完整性检查：未通过")
        st.json(report)


def render_intelligence_feed(foundation, workflow, by_id: dict[str, str]) -> None:
    section_header("情报流", "检索、筛选并排序监测动态")
    vendors = foundation.vendor_service.list_vendors(include_archived=True)
    vendor_names = {vendor.vendor_id: vendor.vendor_name for vendor in vendors}
    categories = foundation.category_repository.list_all()
    controls = st.columns([1.6, 1, 1])
    search = controls[0].text_input(
        "搜索动态",
        placeholder="竞品、标题、事件或来源类型",
        key="feed_search",
    )
    scope = controls[1].selectbox(
        "查看范围",
        ["All signals", "High priority", "Watchlist only", "Procurement", "Case studies", "Solution updates", "Briefs"],
        format_func=_zh,
        key="feed_scope",
    )
    sort_order = controls[2].selectbox(
        "排序方式",
        ["Priority first", "Newest first", "Oldest first"],
        format_func=_zh,
        key="feed_sort",
    )
    vendor_options = {"All": "", **{vendor.vendor_name: vendor.vendor_id for vendor in vendors}}
    category_options = {"All": "", **{item.name: item.category_id for item in categories}}
    with st.expander("高级筛选", expanded=False):
        filters = st.columns(3)
        vendor_name = filters[0].selectbox("竞品", list(vendor_options), format_func=_zh, key="feed_vendor")
        event_type = filters[1].selectbox("事件类型", ["All", *FEED_EVENT_TYPES], format_func=_zh)
        importance = filters[2].selectbox("重要程度", ["All", *IMPORTANCE_LEVELS], format_func=_zh)
        filters2 = st.columns(3)
        category_name = filters2[0].selectbox(
            "方案类别", list(category_options), format_func=_zh, key="feed_category"
        )
        source_type = filters2[1].selectbox(
            "来源类型", ["All", *SOURCE_TYPES], format_func=_zh, key="feed_source"
        )
        date_from = filters2[2].date_input("起始日期", value=None, key="feed_from")
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
        "Case studies": {"NEW_CASE_STUDY"},
        "Solution updates": {"NEW_SOLUTION_SIGNAL"},
        "Briefs": {"BRIEF_GENERATED"},
    }
    followed = {entry.vendor_id for entry in workflow.watchlist_service.repository.list_all()}
    if scope == "High priority":
        events = [event for event in events if event.importance == "HIGH"]
    elif scope == "Watchlist only":
        events = [event for event in events if event.vendor_id in followed]
    elif scope in scope_types:
        events = [event for event in events if event.event_type in scope_types[scope]]
    events = [
        event
        for event in events
        if _matches_signal(event, search, vendor_names.get(event.vendor_id, "全局"))
    ]
    if sort_order == "Priority first":
        events.sort(
            key=lambda event: (_signal_priority(event), event.event_date), reverse=True
        )
    elif sort_order == "Newest first":
        events.sort(key=lambda event: event.event_date, reverse=True)
    else:
        events.sort(key=lambda event: event.event_date)

    signal_stats = st.columns(4)
    with signal_stats[0]:
        metric_card("匹配动态", len(events), "当前筛选结果")
    with signal_stats[1]:
        metric_card(
            "高优先级",
            sum(event.importance == "HIGH" for event in events),
            "应优先审核的动态",
        )
    with signal_stats[2]:
        metric_card(
            "关注竞品动态",
            sum(event.vendor_id in followed for event in events),
            "重点竞品覆盖情况",
        )
    with signal_stats[3]:
        metric_card(
            "已关联证据",
            sum(bool(event.evidence_id) for event in events),
            "可打开底层来源记录",
        )

    st.caption(f"共找到 {len(events)} 条动态 · {_zh(sort_order)} · 最多显示 20 条")
    if not events:
        empty_state(
            "没有符合条件的情报动态",
            "新增证据、简报或审核事件后，系统会生成监测动态。",
            "请调整查看范围或新增证据。",
        )
        return
    for event in events[:20]:
        signal_card(
            _zh_text(event.title),
            _zh_text(event.summary) or "暂无补充摘要。",
            f"{event.event_date} · {vendor_names.get(event.vendor_id, '全局')} · "
            f"{_zh(event.source_type or event.event_type)}",
            event.importance,
        )
    evidence_events = [event for event in events if event.evidence_id]
    if evidence_events:
        with st.expander("查看关联证据", expanded=False):
            evidence_labels = {
                f"{_zh_text(event.title)} · {event.evidence_id}": event.evidence_id
                for event in evidence_events
            }
            selected_label = st.selectbox("动态关联证据", list(evidence_labels))
            _render_evidence_citation(foundation, evidence_labels[selected_label])


def render_watchlist(foundation, workflow, by_id: dict[str, str]) -> None:
    section_header("竞品关注列表", "监测竞品及其更新状态")
    vendors = foundation.vendor_service.list_vendors()
    followed = {entry.vendor_id for entry in workflow.watchlist_service.repository.list_all()}
    addable = [vendor for vendor in vendors if vendor.vendor_id not in followed]
    if addable:
        labels = {f"{vendor.vendor_name} · {vendor.vendor_id}": vendor for vendor in addable}
        choice = st.selectbox("添加竞品", list(labels), key="watchlist_add_choice")
        if st.button("关注竞品", key="watchlist_add_button"):
            workflow.watchlist_service.follow(labels[choice].vendor_id)
            _refresh()
    details = workflow.watchlist_service.list_details()
    if not details:
        empty_state(
            "关注列表为空",
            "关注重点竞品后，可监测新增证据和情报时效性。",
            "请在上方选择竞品并点击“关注竞品”。",
        )
        return
    watchlist_health = st.columns(4)
    refresh_count = sum(
        item["freshness"]["needs_intelligence_refresh"] for item in details
    )
    new_evidence = sum(item["new_evidence_since_last_view"] for item in details)
    with watchlist_health[0]:
        metric_card("重点竞品", len(details), "已保存的监测范围")
    with watchlist_health[1]:
        metric_card("最新档案", len(details) - refresh_count, "可用于当前审核")
    with watchlist_health[2]:
        metric_card("需要更新", refresh_count, "情报基础已过期")
    with watchlist_health[3]:
        metric_card("新增证据", new_evidence, "自上次查看以来")

    details = sorted(
        details,
        key=lambda item: (
            item["freshness"]["needs_intelligence_refresh"],
            item["new_evidence_since_last_view"],
        ),
        reverse=True,
    )
    st.dataframe(
        pd.DataFrame([
            {
                "竞品": item["vendor"].vendor_name,
                "主要方案领域": _category_names(item["primary_solution_areas"], by_id),
                "证据数量": item["evidence_count"],
                "新增证据": item["new_evidence_since_last_view"],
                "最近招投标": (
                    item["latest_procurement_signal"].publication_date
                    if item["latest_procurement_signal"] else ""
                ),
                "最近简报": item["latest_brief"].title if item["latest_brief"] else "",
                "时效状态": "需要更新" if item["freshness"]["needs_intelligence_refresh"] else "最新",
                "最近情报更新": item["latest_intelligence_update"],
            }
            for item in details
        ]),
        hide_index=True,
        width="stretch",
    )
    labels = {item["vendor"].vendor_name: item for item in details}
    selected_name = st.selectbox("查看关注竞品", list(labels))
    selected = labels[selected_name]
    if selected["alerts"]:
        for alert in selected["alerts"]:
            st.warning(alert)
    freshness = selected["freshness"]
    status = "OUTDATED" if freshness["needs_intelligence_refresh"] else "FRESH"
    workspace_context(
        ("竞品", selected["vendor"].vendor_name),
        ("状态", _zh(status)),
        ("新增证据", selected["new_evidence_since_last_view"]),
        ("最近情报更新", selected["latest_intelligence_update"] or "尚未生成"),
    )
    freshness_cols = st.columns(4)
    freshness_cols[0].metric("最新证据", freshness["fresh_evidence_count"])
    freshness_cols[1].metric("临近过期证据", freshness["aging_evidence_count"])
    freshness_cols[2].metric("已过期证据", freshness["outdated_evidence_count"])
    freshness_cols[3].metric("最近证据日期", freshness["latest_evidence_date"] or "暂无数据")
    col1, col2 = st.columns(2)
    if col1.button("标记更新为已读", key=f"mark_viewed_{selected['vendor'].vendor_id}"):
        workflow.watchlist_service.mark_viewed(selected["vendor"].vendor_id)
        _refresh()
    if col2.button("取消关注", key=f"watch_unfollow_{selected['vendor'].vendor_id}"):
        workflow.watchlist_service.unfollow(selected["vendor"].vendor_id)
        _refresh()


def render_market_map(foundation, workflow, by_id: dict[str, str]) -> None:
    section_header("医疗信息化市场地图", "竞品 × 方案类别")
    st.caption("单元格仅统计已验证且非重复的证据；不使用大模型进行分类。")
    vendors = foundation.vendor_service.list_vendors()
    categories = foundation.category_repository.list_all()
    vendor_labels = {vendor.vendor_name: vendor.vendor_id for vendor in vendors}
    category_labels = {item.name: item.category_id for item in categories}
    selected_vendors = st.multiselect("竞品", list(vendor_labels), default=list(vendor_labels))
    selected_categories = st.multiselect(
        "方案类别", list(category_labels), default=list(category_labels), format_func=_zh
    )
    minimum = st.number_input("最低证据数量", min_value=1, max_value=20, value=1)
    result = workflow.market_map_service.build(
        [vendor_labels[item] for item in selected_vendors],
        [category_labels[item] for item in selected_categories],
        int(minimum),
    )
    cells = result["cells"]
    if not cells:
        empty_state(
            "没有符合条件的市场地图数据",
            "单元格需要所选竞品和方案类别存在已验证且非重复的证据。",
            "请放宽筛选条件，或检查证据验证状态。",
        )
        return
    map_summary = st.columns(4)
    with map_summary[0]:
        metric_card("竞品数量", len(selected_vendors), "当前对比范围")
    with map_summary[1]:
        metric_card("方案类别", len(selected_categories), "医疗信息化分类范围")
    with map_summary[2]:
        metric_card("有证据单元格", len(cells), "达到证据数量阈值")
    with map_summary[3]:
        metric_card(
            "证据链接",
            sum(cell["evidence_count"] for cell in cells),
            "单元格级来源引用",
        )
    vendor_names = {vendor.vendor_id: vendor.vendor_name for vendor in vendors}
    frame = pd.DataFrame([
        {
            "竞品": vendor_names.get(cell["vendor_id"], cell["vendor_id"]),
            "方案类别": _zh(by_id.get(cell["category_id"], cell["category_id"])),
            "证据数量": cell["evidence_count"],
            "支持状态": _zh(cell["support_status"]),
        }
        for cell in cells
    ])
    matrix = frame.pivot(index="竞品", columns="方案类别", values="证据数量").fillna(0).astype(int)
    st.dataframe(matrix, width="stretch")
    st.caption("说明：每个单元格显示符合条件的证据数量。" + result["support_rule"])
    st.caption(
        "覆盖情况仅反映当前评估数据集中的证据，不代表整体市场份额。"
    )
    cell_labels = {
        f"{vendor_names.get(cell['vendor_id'], cell['vendor_id'])} × {by_id.get(cell['category_id'], cell['category_id'])} ({cell['evidence_count']})": cell
        for cell in cells
    }
    selected = cell_labels[st.selectbox("查看市场地图单元格", list(cell_labels))]
    detail_cols = st.columns(3)
    detail_cols[0].metric("竞品", vendor_names.get(selected["vendor_id"], selected["vendor_id"]))
    detail_cols[1].metric("方案类别", _zh(by_id.get(selected["category_id"], selected["category_id"])))
    detail_cols[2].metric("证据数量", selected["evidence_count"])
    st.markdown(status_badge(selected["support_status"]), unsafe_allow_html=True)
    for evidence_id in selected["evidence_ids"]:
        _render_evidence_citation(foundation, evidence_id)


def render_opportunities(foundation, workflow) -> None:
    section_header("机会点分析", "基于证据的分析假设")
    st.caption("每个机会点都区分事实证据、分析推断和行动建议，范围仅限当前监测数据集。")
    vendors = foundation.vendor_service.list_vendors()
    vendor_labels = {vendor.vendor_name: vendor.vendor_id for vendor in vendors}
    selected = st.multiselect(
        "监测竞品",
        list(vendor_labels),
        default=list(vendor_labels)[:3],
        max_selections=8,
    )
    if st.button("生成证据驱动的机会点", type="primary"):
        try:
            with st.spinner("正在分析覆盖情况、形成假设并验证证据链接……"):
                created = workflow.opportunity_service.generate([vendor_labels[name] for name in selected])
            st.success(f"已生成 {len(created)} 个机会点假设。")
            _refresh()
        except (ValueError, RuntimeError) as exc:
            error_state(
                "机会点生成失败",
                "请选择具有有效证据的监测竞品。",
                str(exc),
            )
    type_filter = st.selectbox("机会点类型", ["All", *OPPORTUNITY_TYPES], format_func=_zh)
    items = workflow.opportunity_repository.list_all(
        opportunity_type="" if type_filter == "All" else type_filter
    )
    if not items:
        empty_state(
            "暂无机会点假设",
            "机会点基于监测覆盖、竞品对比和已保存声明生成。",
            "请选择竞品并生成证据驱动的机会点。",
        )
        return
    labels = {f"{item.opportunity_type} · {item.title}": item for item in items}
    item = labels[st.selectbox("查看机会点", list(labels))]
    section_header(item.title, item.opportunity_type.replace("_", " "))
    badges = status_badge(item.review_status)
    if item.is_synthetic:
        badges += " " + status_badge("SYNTHETIC")
    st.markdown(badges, unsafe_allow_html=True)
    info_card("事实／证据", item.evidence_statement, "可追溯的来源基础", css_class="hmi-callout-evidence")
    info_card("分析推断", item.inference, "基于证据的分析解释", css_class="hmi-callout-inference")
    info_card("行动建议", item.recommendation, "用于决策支持，不属于已验证事实", css_class="hmi-callout-recommendation")
    st.caption(f"可信度依据：{item.confidence_basis}")
    for evidence_id in item.evidence_ids:
        _render_evidence_citation(foundation, evidence_id)
    with st.form(f"review_opportunity_{item.opportunity_id}"):
        reviewer = st.text_input("审核人", value=item.reviewer)
        status = st.selectbox(
            "审核状态", ["PENDING", "APPROVED", "REJECTED"],
            index=["PENDING", "APPROVED", "REJECTED"].index(item.review_status),
            format_func=_zh,
        )
        note = st.text_area("审核备注", value=item.reviewer_note)
        if st.form_submit_button("保存机会点审核"):
            try:
                workflow.opportunity_service.review(item.opportunity_id, status, reviewer, note)
                _refresh()
            except ValueError as exc:
                st.error(str(exc))


def render_review_queue(foundation, intelligence, workflow) -> None:
    page_header(
        "质量控制",
        "审核队列",
        "在情报内容对外共享前，处理待审核的简报、声明和证据。",
    )
    queue = workflow.brief_workflow_service.queue()
    analytics = workflow.analytics_service.snapshot()
    total_actions = (
        len(queue["briefs_awaiting_review"])
        + len(queue["claims_awaiting_review"])
        + len(queue["evidence_needing_validation"])
    )
    workspace_context(
        ("待办事项", total_actions),
        ("已审核简报", f"{analytics['review_count']} / {analytics['brief_count']}"),
        ("无效引用", analytics["invalid_citation_count"]),
        ("审核原则", "必须由人工决策"),
    )
    workflow_steps(
        [
            ("分诊", "优先处理无证据支持或无效的内容"),
            ("核验", "打开引用的原始证据"),
            ("决策", "批准、编辑、驳回或退回"),
            ("复核", "重新计算支持度和可追溯率"),
            ("发布", "仅在审核通过后定稿"),
        ]
    )
    cols = st.columns(4)
    with cols[0]:
        priority_card(
            "简报审核",
            len(queue["briefs_awaiting_review"]),
            "用于后续流程前必须审核。",
            "warning",
        )
    with cols[1]:
        priority_card(
            "声明审核",
            len(queue["claims_awaiting_review"]),
            "批准或修改原子化声明。",
            "info",
        )
    with cols[2]:
        priority_card(
            "无证据支持",
            len(queue["unsupported_claims"]),
            "风险最高的证据缺口。",
            "danger",
        )
    with cols[3]:
        priority_card(
            "证据验证",
            len(queue["evidence_needing_validation"]),
            "确认来源是否符合使用条件。",
            "warning",
        )
    briefs_tab, claims_tab, evidence_tab = st.tabs(
        ["简报审核", "声明审核", "证据验证"]
    )
    with briefs_tab:
        items = list(queue["briefs_awaiting_review"])
        if not items:
            empty_state("没有待审核简报", "所有已保存简报均已离开待审核队列。")
        else:
            st.dataframe(pd.DataFrame([
                {"标题": item.title, "类型": _zh(item.brief_type), "状态": _zh(item.status), "声明数量": len(item.claims), "生成时间": item.generated_at}
                for item in items
            ]), hide_index=True, width="stretch")
            selected = {f"{item.title} · {item.brief_id}": item for item in items}
            brief = selected[st.selectbox("打开简报", list(selected), key="review_brief_select")]
            reviewer = st.text_input("审核人", value="本地审核人", key="queue_brief_reviewer")
            note = st.text_input("审核备注", key="queue_brief_note")
            if st.button("开始审核", type="primary", key=f"queue_start_{brief.brief_id}"):
                try:
                    workflow.brief_workflow_service.start_review(brief.brief_id, reviewer, note)
                    _refresh()
                except ValueError as exc:
                    error_state("Brief review could not start", "Check the current Brief state and reviewer name.", str(exc))
    with claims_tab:
        queue_name = st.selectbox(
            "声明队列",
            ["claims_awaiting_review", "unsupported_claims", "partially_supported_claims"],
            format_func=lambda value: {"claims_awaiting_review": "待审核声明", "unsupported_claims": "无证据支持", "partially_supported_claims": "部分支持"}.get(value, value),
            key="claim_queue_name",
        )
        items = list(queue[queue_name])
        if not items:
            empty_state("当前队列没有声明", "没有已保存声明符合所选审核状态。")
        else:
            st.dataframe(pd.DataFrame([
                {"类型": _zh(item.claim_type), "声明": item.claim_text, "证据支持": _zh(item.support_level), "审核状态": _zh(item.review_status), "证据数量": len(item.evidence_ids)}
                for item in items
            ]), hide_index=True, width="stretch")
            selected = {f"{item.claim_type} · {item.claim_text[:90]} · {item.claim_id}": item for item in items}
            claim = selected[st.selectbox("打开声明", list(selected), key="queue_claim_select")]
            with st.form(f"queue_claim_form_{claim.claim_id}"):
                reviewer = st.text_input("审核人", value="本地审核人")
                claim_text = st.text_area("声明文本", value=_zh_text(claim.claim_text))
                action = st.selectbox("审核操作", ["Approve", "Reject", "Edit", "Mark Unsupported"], format_func=lambda value: {"Approve":"批准", "Reject":"驳回", "Edit":"编辑", "Mark Unsupported":"标记为无证据支持"}[value])
                note = st.text_area("审核备注")
                submitted = st.form_submit_button("保存声明审核", type="primary")
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
                with st.expander("打开证据", expanded=False):
                    for evidence_id in claim.evidence_ids:
                        _render_evidence_citation(foundation, evidence_id)
    with evidence_tab:
        items = list(queue["evidence_needing_validation"])
        if not items:
            empty_state("没有待验证证据", "所有证据记录均已有明确的验证状态。")
        else:
            st.dataframe(pd.DataFrame([
                {"标题": item.source_title, "来源类型": _zh(item.source_type), "验证状态": _zh(item.validation_status), "证据状态": _zh(item.evidence_status), "发布日期": item.publication_date}
                for item in items
            ]), hide_index=True, width="stretch")
            selected = {f"{item.source_title} · {item.evidence_id}": item for item in items}
            evidence = selected[st.selectbox("打开证据", list(selected), key="queue_evidence_select")]
            _render_evidence_citation(foundation, evidence.evidence_id)


def _metric_value(value, suffix: str = "") -> str:
    if value is None:
        return "暂无数据"
    if isinstance(value, float):
        return f"{value:.1f}{suffix}"
    return f"{value}{suffix}"


def render_analytics(foundation, workflow) -> None:
    stats = workflow.analytics_service.snapshot()
    queue = workflow.brief_workflow_service.queue()
    watchlist = workflow.watchlist_service.list_details()
    readiness = _readiness_rates(stats, queue, watchlist)
    workspace_context(
        ("指标类型", "评估指标"),
        ("数据集", "模拟数据"),
        ("刷新状态", "当前 SQLite 数据快照"),
        ("评估样本", stats["benchmark"]["paired_sample_size"]),
    )
    section_header("项目健康度", "证据、审核和发布状态")
    readiness_cols = st.columns(4)
    with readiness_cols[0]:
        progress_card(
            "证据验证率",
            readiness["evidence_validation"],
            f"已验证 {stats['validated_evidence_count']} 条记录",
        )
    with readiness_cols[1]:
        progress_card(
            "简报审核覆盖率",
            readiness["brief_review"],
            f"已审核 {stats['review_count']} 份简报",
        )
    with readiness_cols[2]:
        progress_card(
            "已审核声明可追溯率",
            readiness["traceability"],
            f"{stats['traceable_claim_count']} / {stats['reviewed_claim_count']} 条已审核声明可追溯",
        )
    with readiness_cols[3]:
        progress_card(
            "关注列表新鲜度",
            readiness["watchlist_freshness"],
            "具有最新证据基础的重点竞品档案",
        )
    vendor_names = {
        vendor.vendor_id: vendor.vendor_name
        for vendor in foundation.vendor_service.list_vendors(include_archived=True)
    }
    coverage_tab, quality_tab, output_tab, workflow_tab = st.tabs(
        ["覆盖情况", "质量", "输出", "工作流"]
    )
    with coverage_tab:
        cols = st.columns(4)
        cols[0].metric("活跃竞品", stats["active_vendor_count"])
        cols[1].metric("证据记录", stats["evidence_count"])
        cols[2].metric("已验证证据", stats["validated_evidence_count"])
        cols[3].metric("方案类别", stats["solution_category_count"])
        section_header("各竞品证据数量", "记录数量")
        coverage = pd.DataFrame(
            [
                {"竞品": vendor_names.get(vendor_id, vendor_id), "证据数量": count}
                for vendor_id, count in stats["evidence_by_vendor"].items()
            ]
        ).set_index("竞品")
        st.bar_chart(coverage, color="#0b7595")
    with quality_tab:
        cols = st.columns(4)
        cols[0].metric("可追溯率", _metric_value(stats["traceability_rate"], "%"))
        cols[1].metric("已审核声明", stats["reviewed_claim_count"])
        cols[2].metric("可追溯声明", stats["traceable_claim_count"])
        cols[3].metric("无效引用", stats["invalid_citation_count"])
        st.caption(
            f"评估指标：{stats['traceable_claim_count']} / {stats['reviewed_claim_count']} 条人工审核声明可追溯。"
            "可追溯率和证据支持度为两个独立指标。"
        )
        charts = st.columns(2, gap="large")
        with charts[0]:
            st.markdown("#### 声明证据支持分布")
            support_frame = pd.DataFrame(
                {"声明数量": [
                    stats["supported_claim_count"],
                    stats["partially_supported_claim_count"],
                    stats["unsupported_claim_count"],
                ]},
                index=["有证据支持", "部分支持", "无证据支持"],
            )
            st.bar_chart(support_frame, color="#315f8c")
        with charts[1]:
            st.markdown("#### 证据时效性")
            freshness_frame = pd.DataFrame(
                [(_zh(key), value) for key, value in stats["evidence_freshness"].items()], columns=["时效性", "证据数量"]
            ).set_index("时效性")
            st.bar_chart(freshness_frame, color="#5f8799")
    with output_tab:
        cols = st.columns(4)
        cols[0].metric("竞品简报", stats["brief_count"])
        cols[1].metric("竞品对比", stats["comparison_count"])
        cols[2].metric("机会点", stats["opportunity_count"])
        cols[3].metric("管理层简报", stats["executive_brief_count"])
        output_frame = pd.DataFrame(
            {
                "输出数量": [
                    stats["brief_count"],
                    stats["comparison_count"],
                    stats["opportunity_count"],
                    stats["executive_brief_count"],
                    stats["sales_enablement_count"],
                ]
            },
            index=["竞品简报", "竞品对比", "机会点", "管理层简报", "销售支持"],
        )
        st.bar_chart(output_frame, color="#0b7595")
    with workflow_tab:
        cols = st.columns(4)
        cols[0].metric("已审核简报", stats["review_count"])
        cols[1].metric("平均审核时间", _metric_value(stats["average_review_time"], " 分钟"))
        cols[2].metric("平均编辑次数", _metric_value(stats["average_edit_count"]))
        cols[3].metric("定稿率", _metric_value(stats["finalisation_rate"], "%"))
        benchmark = stats["benchmark"]
        st.warning("人工流程评估尚未完成，因此效率指标暂不可用。")
        benchmark_cols = st.columns(4)
        benchmark_cols[0].metric("人工流程中位数", _metric_value(benchmark["manual"]["median"], " 分钟"))
        benchmark_cols[1].metric("辅助流程中位数", _metric_value(benchmark["ai_assisted"]["median"], " 分钟"))
        benchmark_cols[2].metric("时间缩短比例", _metric_value(benchmark["time_reduction_pct"], "%"))
        benchmark_cols[3].metric("效率倍数", _metric_value(benchmark["speed_multiple"], " 倍"))
        st.caption(f"完整可比配对样本：{benchmark['paired_sample_size']} · 最低要求：5")


def render_benchmark(workflow) -> None:
    section_header("工作流效率评估", "评估工作区")
    if workflow.benchmark_service.summary()["paired_sample_size"] < 5:
        st.warning(
            "人工流程评估尚未完成，人工流程中位数、辅助流程中位数、时间缩短比例和效率倍数均暂无数据。"
        )
    st.caption(
        "配对比较必须使用相同的冻结任务、竞品范围、证据范围和输出要求。"
        "只有状态为“完整且可比”的配对才会进入指标计算。"
    )
    service = workflow.benchmark_service
    tasks = service.tasks()
    task_map = {item.task_id: item for item in tasks}
    new_tab, history_tab, comparison_tab, detail_tab, aggregate_tab = st.tabs(
        ["新建评估", "评估历史", "工作流对比", "运行详情", "汇总结果"]
    )
    with new_tab:
        task_id = st.selectbox("固定评估任务", list(task_map), key="benchmark_task")
        task = task_map[task_id]
        workflow_type = st.radio(
            "工作流类型", ["MANUAL", "AI_ASSISTED"], horizontal=True,
            format_func=_zh, key="benchmark_workflow"
        )
        existing = service.repository.get_by_pair(f"pair_{task_id}", workflow_type)
        st.caption(
            f"{_zh(task.task_type)} · {len(task.vendor_ids)} 家竞品 · "
            f"{len(task.evidence_ids)} 条固定证据记录"
        )
        st.info(task.output_requirement)
        if workflow_type == "AI_ASSISTED" and existing is None:
            st.warning("请先运行 scripts/run_evaluation.py，以测量智能辅助工作流各阶段耗时。")
        with st.form("benchmark_entry_form"):
            stage_times: dict[str, float] = {}
            machine_keys = {
                "ai_pack_minutes", "ai_generation_minutes", "ai_validation_minutes",
                "ai_qa_minutes", "ai_export_minutes",
            }
            for key in service.stage_keys(workflow_type):
                default = float(existing.stage_times.get(key, 0.0)) if existing else 0.0
                stage_times[key] = st.number_input(
                    _zh(key),
                    min_value=0.0,
                    value=default,
                    step=0.1,
                    format="%.6f",
                    disabled=(workflow_type == "AI_ASSISTED" and key in machine_keys),
                )
            left, right = st.columns(2)
            claim_count = left.number_input(
                "声明数量", min_value=0, value=existing.claim_count if existing else 0, step=1
            )
            brief_length = right.number_input(
                "简报长度（字符）", min_value=0,
                value=existing.brief_length if existing else 0, step=1,
            )
            review_result = st.selectbox("审核结果", ["PASS", "NEEDS_REVISION", "FAIL"], format_func=_zh)
            edit_count = st.number_input(
                "修改次数", min_value=0, value=existing.edit_count if existing else 0, step=1
            )
            notes = st.text_area("备注", value=existing.notes if existing else "")
            submitted = st.form_submit_button("保存完整评估记录", type="primary")
        if submitted:
            if workflow_type == "AI_ASSISTED" and existing is None:
                st.error("该任务尚无已测量的智能辅助流程草稿。")
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
                        f"已保存{_zh(saved.workflow_type)}：{saved.total_minutes:.3f} 分钟；"
                        f"配对状态：{_zh(service.evaluate_pair(saved.pair_id)['status'])}。"
                    )
                    _refresh()
                except ValueError as exc:
                    st.error(str(exc))

    history = service.history()
    history_rows = [
        {
            "评估 ID": item.benchmark_id,
            "任务": item.manifest_task_id,
            "工作流": _zh(item.workflow_type),
            "分钟": item.total_minutes,
            "运行状态": _zh(item.run_status),
            "可比性": _zh(item.comparability_status),
            "证据数量": item.evidence_count,
            "声明数量": item.claim_count,
            "模拟数据": item.is_synthetic,
        }
        for item in history
    ]
    with history_tab:
        st.dataframe(pd.DataFrame(history_rows), hide_index=True, width="stretch")
    with comparison_tab:
        complete = [item for item in history if item.run_status == "COMPLETE"]
        if complete:
            frame = pd.DataFrame(
                [{"配对": item.pair_id, "工作流": _zh(item.workflow_type), "分钟": item.total_minutes}
                 for item in complete]
            )
            st.bar_chart(frame.pivot(index="配对", columns="工作流", values="分钟"))
        else:
            st.info("暂无完整评估记录。")
    with detail_tab:
        if history:
            selected = st.selectbox(
                "评估记录", [item.benchmark_id for item in history], key="benchmark_detail"
            )
            run = next(item for item in history if item.benchmark_id == selected)
            st.json(asdict(run))
        else:
            st.info("暂无评估历史。")
    with aggregate_tab:
        summary = service.summary()
        cols = st.columns(3)
        cols[0].metric("人工流程中位数", _metric_value(summary["manual"]["median"], " 分钟"))
        cols[1].metric("辅助流程中位数", _metric_value(summary["ai_assisted"]["median"], " 分钟"))
        cols[2].metric("节省时间", _metric_value(summary["time_saved_minutes"], " 分钟"))
        cols = st.columns(3)
        cols[0].metric("耗时降幅", _metric_value(summary["time_reduction_pct"], "%"))
        cols[1].metric("效率倍数", _metric_value(summary["speed_multiple"], " 倍"))
        cols[2].metric("配对样本", summary["paired_sample_size"])
        st.json(summary)


def render_settings(view: str = "Rules") -> None:
    if view == "Runtime & Data":
        api_configured = bool(_runtime_setting("OPENAI_API_KEY"))
        cols = st.columns(3)
        cols[0].metric("数据模式", "模拟数据")
        cols[1].metric("生成模式", "OpenAI" if api_configured else "确定性流程")
        cols[2].metric("产品版本", PORTFOLIO_VERSION)
        st.info(
            "演示模式无需 API 密钥。未配置 OPENAI_API_KEY 时，产品使用确定性结构化演示情报，"
            "并继续执行相同的证据和可追溯性检查。"
        )
        st.caption("界面不会显示任何密钥内容。")
        return
    st.markdown("#### 证据时效性")
    st.markdown("最新 ≤ 90 天 · 临近过期 91–180 天 · 已过期 > 180 天")
    st.markdown("#### 证据质量")
    st.markdown(
        "来源权威性（0–3）+ 时效性（0–3）+ 完整性（0–2）+ "
        "可追溯性（0–1）+ 相关性（0–1）。高 ≥ 8；中 ≥ 5；其余为低。"
    )
    st.markdown("#### 声明与证据关联规则")
    st.markdown(
        "事实声明必须引用其原始证据包中的有效证据。"
        "分析推断和行动建议也必须保留证据基础。未知、缺失或证据包之外的引用均为无效。"
    )
    st.info("以上为内部情报维护规则，不属于医疗行业标准。")


def _render_evidence_citation(foundation, evidence_id: str) -> None:
    evidence = foundation.evidence_service.get_evidence(evidence_id)
    if evidence is None:
        st.error(f"证据不存在：{evidence_id}")
        return
    vendor = foundation.vendor_service.get_vendor(evidence.vendor_id)
    with st.expander(f"{evidence_id} · {_zh_text(evidence.source_title)}"):
        st.markdown(
            f"**竞品：** {vendor.vendor_name if vendor else evidence.vendor_id}\n\n"
            f"**来源类型：** {_zh(evidence.source_type)}\n\n"
            f"**发布日期：** {evidence.publication_date}\n\n"
            f"**来源链接：** {evidence.source_url or '未提供'}\n\n"
            f"**摘要：** {_zh_text(evidence.summary)}\n\n"
            f"**来源权威性：** {_zh(evidence.source_authority)}\n\n"
            f"**模拟数据：** {'是' if evidence.is_synthetic else '否'}"
        )
        st.code(evidence.cleaned_text or evidence.raw_text, language="text")


def _render_brief(foundation, intelligence, brief) -> None:
    section_header(_zh_text(brief.title), f"{_zh(brief.brief_type)} · {brief.generated_at}")
    badges = status_badge(brief.status)
    if brief.is_demo:
        badges += " " + status_badge("SYNTHETIC")
    st.markdown(badges, unsafe_allow_html=True)
    st.caption(f"简报 {brief.brief_id} · 证据包 {brief.evidence_pack_id} · 提示词版本 {brief.prompt_version}")
    claim_by_id = {claim.claim_id: claim for claim in brief.claims}
    traceability = intelligence.traceability_service.validate_brief(
        brief.brief_id,
        update_claims=False,
    )
    pack = intelligence.evidence_pack_service.get_pack(brief.evidence_pack_id)
    summary_tab, intelligence_tab, claims_tab, citations_tab, sources_tab = st.tabs(
        ["执行摘要", "核心情报", "声明", "证据引用", "来源"]
    )
    with summary_tab:
        st.markdown(_zh_text(brief.executive_summary))
        metrics = st.columns(4)
        metrics[0].metric("声明数量", traceability["total_claims"])
        metrics[1].metric("可追溯声明", traceability["traceable_claims"])
        metrics[2].metric("无证据支持", traceability["unsupported_claims"])
        metrics[3].metric("无效引用", traceability["invalid_citations_detected"])
        if traceability["result"] == "PASS":
            st.success("结构化引用验证：通过")
        else:
            st.error("结构化引用验证：未通过。请检查无证据支持的事实声明或无效证据 ID。")
    with intelligence_tab:
        for section, claim_ids in brief.sections.items():
            with st.container(border=True):
                st.markdown(f"#### {_zh(section)}")
                for claim_id in claim_ids:
                    claim = claim_by_id.get(claim_id)
                    if claim:
                        st.markdown(f"**{claim.claim_type.replace('_', ' ')} · {claim.support_level.replace('_', ' ')}**")
                        st.markdown(_zh_text(claim.claim_text))
    with claims_tab:
        st.dataframe(
            pd.DataFrame([
                {
                    "类型": _zh(claim.claim_type),
                    "声明": _zh_text(claim.claim_text),
                    "证据支持": _zh(claim.support_level),
                    "可追溯": "是" if claim.traceable else "否",
                    "证据数量": len(claim.evidence_ids),
                    "审核状态": _zh(claim.review_status),
                }
                for claim in brief.claims
            ]),
            hide_index=True,
            width="stretch",
        )
    with citations_tab:
        for claim in brief.claims:
            with st.expander(f"{_zh(claim.claim_type)} · {_zh(claim.support_level)} · {_zh_text(claim.claim_text)[:95]}"):
                st.markdown(_zh_text(claim.claim_text))
                if claim.evidence_ids:
                    st.caption("证据 ID：" + "、".join(claim.evidence_ids))
                else:
                    empty_state("没有证据引用", "该声明没有有效引用，不得作为有证据支持的事实呈现。")
    with sources_tab:
        if pack and pack.evidence_ids:
            for evidence_id in pack.evidence_ids:
                _render_evidence_citation(foundation, evidence_id)
        else:
            empty_state("证据包不可用", "该简报的来源证据包不可用。")
        if pack:
            with st.expander("证据筛选规则", expanded=False):
                st.markdown(f"**证据包：** {pack.evidence_pack_id}  \n**证据记录：** {len(pack.evidence_ids)}")
                st.json(pack.selection_criteria)


def render_comparison(foundation, intelligence, workflow) -> None:
    section_header("竞品对比", "选择 2–5 家竞品")
    workflow_steps(
        [
            ("选择", "选择 2–5 家可比竞品"),
            ("范围", "冻结符合条件的来源证据"),
            ("对比", "按竞品组织事实信息"),
            ("研判", "区分事实与分析推断"),
            ("输出", "创建管理层或销售视图"),
        ]
    )
    vendors = foundation.vendor_service.list_vendors()
    label_to_id = {f"{vendor.vendor_name} · {vendor.vendor_id}": vendor.vendor_id for vendor in vendors}
    selected_labels = st.multiselect(
        "竞品",
        list(label_to_id),
        default=list(label_to_id)[:2],
        max_selections=5,
    )
    include_warning = st.checkbox("包含“需注意”状态的证据", key="compare_warning")
    workspace_context(
        ("已选择", len(selected_labels)),
        ("证据规则", "已验证且非重复"),
        ("输出格式", "结构化竞品对比"),
    )
    if st.button("生成竞品对比", type="primary"):
        if not 2 <= len(selected_labels) <= 5:
            error_state("选择无效", "请选择 2–5 家不同的竞品。")
        else:
            api_key = _runtime_setting("OPENAI_API_KEY")
            model = _runtime_setting("OPENAI_MODEL", "gpt-5.6")
            try:
                with st.spinner("正在处理证据、生成竞品对比并验证声明……"):
                    brief, traceability = intelligence.comparison_service.generate(
                        [label_to_id[label] for label in selected_labels],
                        include_warning=include_warning,
                        api_key=api_key,
                        model=model,
                    )
                st.success(f"已生成竞品对比 {brief.brief_id}；可追溯性校验：{_zh(traceability['result'])}。")
                _refresh()
            except (ValueError, RuntimeError) as exc:
                error_state("竞品对比生成失败", "请检查已选竞品和符合条件的证据。", str(exc))

    comparisons = intelligence.brief_repository.list_all("COMPARISON")
    if comparisons:
        comparison_labels = {f"{brief.title} · {brief.brief_id}": brief for brief in comparisons}
        comparison_label = st.selectbox("查看竞品对比", list(comparison_labels))
        comparison = comparison_labels[comparison_label]
        validation = intelligence.traceability_service.validate_brief(
            comparison.brief_id, update_claims=False
        )
        comparison_kpis = st.columns(4)
        with comparison_kpis[0]:
            metric_card("竞品", len(comparison.vendor_ids), "固定对比范围")
        with comparison_kpis[1]:
            metric_card("声明", len(comparison.claims), "原子化结构声明")
        with comparison_kpis[2]:
            metric_card(
                "可追溯声明",
                f"{validation['traceable_claims']} / {validation['total_claims']}",
                "引用可在证据包内解析",
            )
        with comparison_kpis[3]:
            metric_card(
                "无效引用",
                validation["invalid_citations_detected"],
                "用于决策前必须保持为零",
            )
        if st.button("保存竞品对比", key=f"save_comparison_{comparison.brief_id}"):
            workflow.saved_comparison_service.save(comparison.brief_id)
            st.success("竞品对比已保存，无需重新运行生成流程。")
            _refresh()
        overview_tab, coverage_tab, evidence_tab, positioning_tab, analysis_tab = st.tabs(
            ["概览", "方案覆盖", "证据", "市场定位", "综合分析"]
        )
        vendor_map = {vendor.vendor_id: vendor for vendor in vendors}
        category_map = {
            category.category_id: category.name
            for category in foundation.category_repository.list_all()
        }
        with overview_tab:
            st.markdown(f"### {_zh_text(comparison.title)}")
            st.markdown(_zh_text(comparison.executive_summary))
            st.markdown(status_badge(comparison.status) + " " + status_badge("SYNTHETIC"), unsafe_allow_html=True)
            overview_rows = []
            for vendor_id in comparison.vendor_ids:
                vendor = vendor_map.get(vendor_id)
                overview_rows.append({
                    "竞品": vendor.vendor_name if vendor else vendor_id,
                    "主要市场": vendor.primary_market if vendor else "",
                    "证据数量": vendor.evidence_count if vendor else 0,
                    "方案数量": len(vendor.solution_categories) if vendor else 0,
                })
            st.dataframe(pd.DataFrame(overview_rows), hide_index=True, width="stretch")
        with coverage_tab:
            coverage_rows = []
            for vendor_id in comparison.vendor_ids:
                vendor = vendor_map.get(vendor_id)
                for category_id in (vendor.solution_categories if vendor else []):
                    coverage_rows.append({
                        "竞品": vendor.vendor_name,
                        "方案类别": _zh(category_map.get(category_id, category_id)),
                    })
            if coverage_rows:
                st.dataframe(pd.DataFrame(coverage_rows), hide_index=True, width="stretch")
            else:
                empty_state("暂无方案覆盖", "已选竞品暂无有证据支持的分类覆盖。")
        with evidence_tab:
            pack = intelligence.evidence_pack_service.get_pack(comparison.evidence_pack_id)
            if pack:
                for evidence_id in pack.evidence_ids:
                    _render_evidence_citation(foundation, evidence_id)
            else:
                empty_state("证据包不可用", "已保存的竞品对比没有可读取的证据包。")
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
                    info_card(_zh(claim.claim_type), _zh_text(claim.claim_text), f"{_zh(claim.support_level)} · {_zh(claim.review_status)}")
            else:
                empty_state("暂无市场定位章节", "该竞品对比未包含独立的市场定位章节。")
        with analysis_tab:
            _render_brief(foundation, intelligence, comparison)
            st.markdown("#### 管理层与销售视图")
            executive = workflow.executive_brief_repository.get_by_brief(comparison.brief_id)
            sales = workflow.sales_enablement_repository.get_by_brief(comparison.brief_id)
            action_cols = st.columns(2)
            if executive:
                action_cols[0].success("管理层对比已生成")
            elif action_cols[0].button("生成管理层对比", key=f"create_exec_{comparison.brief_id}"):
                workflow.executive_brief_service.create(comparison.brief_id)
                _refresh()
            if sales:
                action_cols[1].success("销售对比已生成")
            elif action_cols[1].button("生成销售对比", key=f"create_sales_{comparison.brief_id}"):
                workflow.sales_enablement_service.create(comparison.brief_id)
                _refresh()
        history = workflow.saved_comparison_repository.list_all()
        if history:
            st.markdown("#### 竞品对比历史")
            st.dataframe(
                pd.DataFrame([asdict(item) for item in history]),
                hide_index=True,
                width="stretch",
            )
    else:
        empty_state("暂无已保存的竞品对比", "竞品对比需要 2–5 家竞品及符合条件的证据包。", "请选择竞品并生成对比。")


def render_briefs_and_claims(foundation, intelligence, workflow) -> None:
    page_header(
        "情报输出",
        "简报库",
        "查看结构化简报、来源链接、审核状态和导出文件。",
    )
    library_view = st.radio(
        "简报工作区",
        ["Competitor Briefs", "Executive Briefs", "Sales Enablement"],
        format_func=lambda value: {"Competitor Briefs":"竞品简报", "Executive Briefs":"管理层简报", "Sales Enablement":"销售支持"}[value],
        horizontal=True,
        label_visibility="collapsed",
        key="brief_workspace",
    )
    if library_view == "Executive Briefs":
        items = workflow.executive_brief_repository.list_all()
        if not items:
            empty_state("暂无管理层简报", "管理层输出由已保存的结构化简报生成。", "请打开竞品简报并创建管理层简报。")
            return
        st.dataframe(pd.DataFrame([
            {"标题": _zh_text(item.title), "来源简报": item.brief_id, "证据数量": len(item.evidence_ids), "创建时间": item.created_at, "模拟数据": "是" if item.is_synthetic else "否"}
            for item in items
        ]), hide_index=True, width="stretch")
        selected = {f"{_zh_text(item.title)} · {item.executive_brief_id}": item for item in items}
        item = selected[st.selectbox("打开管理层简报", list(selected))]
        section_header(_zh_text(item.title), item.created_at)
        st.markdown(status_badge("SYNTHETIC") if item.is_synthetic else status_badge("APPROVED"), unsafe_allow_html=True)
        for section, lines in item.sections.items():
            with st.container(border=True):
                st.markdown(f"#### {_zh(section)}")
                st.markdown("\n".join(f"- {_zh_text(line)}" for line in lines) or "暂无内容。")
        return
    if library_view == "Sales Enablement":
        items = workflow.sales_enablement_repository.list_all()
        if not items:
            empty_state("暂无销售支持输出", "销售支持内容复用已保存简报中审核过的声明和证据。", "请打开竞品简报并创建销售支持内容。")
            return
        st.dataframe(pd.DataFrame([
            {"标题": _zh_text(item.title), "来源简报": item.brief_id, "声明数量": len(item.source_claim_ids), "证据数量": len(item.evidence_ids), "创建时间": item.created_at, "模拟数据": "是" if item.is_synthetic else "否"}
            for item in items
        ]), hide_index=True, width="stretch")
        selected = {f"{_zh_text(item.title)} · {item.sales_output_id}": item for item in items}
        item = selected[st.selectbox("打开销售支持内容", list(selected))]
        section_header(_zh_text(item.title), item.created_at)
        st.markdown(status_badge("SYNTHETIC") if item.is_synthetic else status_badge("APPROVED"), unsafe_allow_html=True)
        for section, entries in item.sections.items():
            with st.container(border=True):
                st.markdown(f"#### {_zh(section)}")
                for entry in entries:
                    if isinstance(entry, dict):
                        st.markdown(" · ".join(f"**{key.replace('_', ' ').title()}:** {value}" for key, value in entry.items()))
                    else:
                        st.markdown(f"- {_zh_text(entry)}")
        return
    briefs = intelligence.brief_repository.list_all()
    if not briefs:
        empty_state("暂无竞品简报", "简报由符合条件的证据包生成。", "请生成竞品情报或竞品对比。")
        return
    vendor_names = {
        vendor.vendor_id: vendor.vendor_name
        for vendor in foundation.vendor_service.list_vendors(include_archived=True)
    }
    library_rows = []
    for item in briefs:
        validation = intelligence.traceability_service.validate_brief(item.brief_id, update_claims=False)
        library_rows.append({
            "标题": _zh_text(item.title),
            "竞品": "、".join(vendor_names.get(vendor_id, vendor_id) for vendor_id in item.vendor_ids),
            "类型": _zh(item.brief_type),
            "状态": _zh(item.status),
            "声明数量": len(item.claims),
            "可追溯": f"{validation['traceable_claims']} / {validation['total_claims']}",
            "无效引用": validation["invalid_citations_detected"],
            "生成时间": item.generated_at,
            "模拟数据": "是" if item.is_demo else "否",
        })
    library_summary = st.columns(4)
    with library_summary[0]:
        metric_card("已保存简报", len(briefs), "结构化输出的统一来源")
    with library_summary[1]:
        metric_card(
            "审核中",
            sum(item.status in {"IN_REVIEW", "NEEDS_REVISION"} for item in briefs),
            "需要人工决策",
        )
    with library_summary[2]:
        metric_card(
            "已批准或已定稿",
            sum(item.status in {"APPROVED", "FINAL"} for item in briefs),
            "可在受控范围内复用",
        )
    with library_summary[3]:
        metric_card(
            "无效引用",
            sum(row["无效引用"] for row in library_rows),
            "导出前必须保持为零",
        )
    st.dataframe(pd.DataFrame(library_rows), hide_index=True, width="stretch")
    labels = {f"{_zh_text(brief.title)} · {brief.brief_id}": brief for brief in briefs}
    selected_label = st.selectbox("查看结构化简报", list(labels))
    brief = labels[selected_label]
    _render_brief(foundation, intelligence, brief)

    st.markdown("#### 简报审核流程")
    reviewer = st.text_input("审核人", value="本地审核人", key=f"reviewer_{brief.brief_id}")
    review_note = st.text_input("简报审核备注", key=f"brief_note_{brief.brief_id}")
    workflow_cols = st.columns(4)
    actions = [
        ("开始审核", workflow.brief_workflow_service.start_review),
        ("退回修改", workflow.brief_workflow_service.return_for_revision),
        ("批准简报", workflow.brief_workflow_service.approve),
    ]
    for column, (label, action_fn) in zip(workflow_cols[:3], actions):
        if column.button(label, key=f"{label}_{brief.brief_id}"):
            try:
                action_fn(brief.brief_id, reviewer, review_note)
                _refresh()
            except ValueError as exc:
                st.error(str(exc))
    if workflow_cols[3].button("标记为定稿", key=f"final_{brief.brief_id}"):
        try:
            workflow.brief_workflow_service.finalize(brief.brief_id)
            _refresh()
        except ValueError as exc:
            st.error(str(exc))
    metadata = workflow.review_repository.get(brief.brief_id)
    if metadata:
        review_cols = st.columns(4)
        review_cols[0].metric("审核人", metadata.reviewer or "未分配")
        review_cols[1].metric("审核时长", _metric_value(metadata.review_minutes, " 分钟"))
        review_cols[2].metric("修改次数", metadata.revision_count)
        review_cols[3].metric("完成时间", metadata.review_completed_at or "待处理")
        if metadata.review_notes:
            st.caption("审核备注：" + " · ".join(metadata.review_notes))

    st.markdown("#### 声明审核")
    claim_labels = {
        f"{_zh(claim.claim_type)} · {_zh_text(claim.claim_text)[:80]} · {claim.claim_id}": claim
        for claim in brief.claims
    }
    claim_label = st.selectbox("声明", list(claim_labels))
    claim = claim_labels[claim_label]
    pack = intelligence.evidence_pack_service.get_pack(brief.evidence_pack_id)
    pack_evidence_ids = pack.evidence_ids if pack else []
    with st.form(f"review_{claim.claim_id}"):
        claim_text = st.text_area("声明文本", value=_zh_text(claim.claim_text))
        claim_type = st.selectbox(
            "声明类型",
            CLAIM_TYPES,
            index=CLAIM_TYPES.index(claim.claim_type),
            format_func=_zh,
        )
        evidence_ids = st.multiselect(
            "证据链接",
            pack_evidence_ids,
            default=[item for item in claim.evidence_ids if item in pack_evidence_ids],
        )
        explanation = st.text_area("审核说明", value=claim.explanation)
        reviewer_note = st.text_area("审核备注", key=f"claim_note_{claim.claim_id}")
        action = st.selectbox(
            "审核操作",
            ["Approve", "Reject", "Edit", "Mark Unsupported"],
            format_func=lambda value: {"Approve":"批准", "Reject":"驳回", "Edit":"编辑", "Mark Unsupported":"标记为无证据支持"}[value],
        )
        if st.form_submit_button("保存声明审核"):
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
                st.success("声明审核已保存，可追溯率已重新计算。")
                _refresh()
            except ValueError as exc:
                st.error(str(exc))

    export_col_1, export_col_2, export_col_3 = st.columns(3)
    markdown_downloaded = export_col_1.download_button(
        "下载 Markdown",
        intelligence.export_service.markdown(brief),
        file_name=f"{brief.brief_id}.md",
        mime="text/markdown",
    )
    json_downloaded = export_col_2.download_button(
        "下载结构化 JSON",
        intelligence.export_service.json(brief),
        file_name=f"{brief.brief_id}.json",
        mime="application/json",
    )
    csv_downloaded = export_col_3.download_button(
        "下载声明 CSV",
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

    st.markdown("#### 管理层与销售输出")
    executive_tab, sales_tab = st.tabs(["管理层简报", "销售支持"])
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
        page_title="医疗行业市场情报",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_design_system()
    with st.spinner("正在加载医疗行业市场情报工作区……"):
        foundation, intelligence, workflow = get_foundation(str(database_path))
    _, by_id, by_name = _category_maps(foundation)

    with st.sidebar:
        st.markdown(
            '<div class="hmi-brand">'
            '<div class="hmi-brand-lockup">'
            '<div class="hmi-logo" aria-hidden="true">情报</div>'
            '<div><div class="hmi-brand-kicker">医疗信息化</div>'
            '<div class="hmi-brand-title">市场情报工作台</div></div>'
            '</div>'
            '<div class="hmi-brand-subtitle">竞品研究、证据管理与决策支持</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<span class="hmi-badge hmi-badge-info">评估环境</span> '
            '<span class="hmi-badge hmi-badge-neutral">模拟数据集</span>',
            unsafe_allow_html=True,
        )
        st.divider()
        st.caption("功能导航")
        navigation = st.radio(
            "Primary navigation",
            PRIMARY_NAVIGATION,
            format_func=_zh,
            label_visibility="collapsed",
            key="primary_navigation",
        )
        st.divider()
        snapshot = workflow.analytics_service.snapshot()
        st.caption(
            f"{snapshot['active_vendor_count']} 家竞品 · "
            f"{snapshot['evidence_count']} 条证据 · {snapshot['brief_count']} 份简报"
        )
        with st.expander("使用流程", expanded=False):
            st.markdown(
                "1. 查看高优先级动态\n\n"
                "2. 打开对应证据来源\n\n"
                "3. 对比重点竞品\n\n"
                "4. 处理审核队列\n\n"
                "5. 导出已批准的情报输出"
            )
        st.markdown(
            '<div class="hmi-sidebar-status"><span class="hmi-live-dot"></span>'
            '评估工作区已就绪<br>来源追溯与完整性检查已启用</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"v{PORTFOLIO_VERSION} · 本地评估工作区")

    demo_banner()
    try:
        if navigation == "Overview":
            render_overview(foundation, intelligence, workflow, by_id)
        elif navigation == "Intelligence":
            page_header(
                "动态监测",
                "市场情报动态",
                "查看重要变化、支持证据和关注列表状态。",
            )
            view = st.radio(
                "情报动态工作区",
                ["Feed", "Watchlist"],
                format_func=_zh,
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
                "市场研究",
                "竞争格局分析",
                "对比方案覆盖、竞品定位和有证据支持的机会点。",
            )
            view = st.radio(
                "市场分析工作区",
                ["Market Map", "Compare", "Opportunities"],
                format_func=_zh,
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
                "运营分析",
                "情报项目数据分析",
                "跟踪证据健康度、审核覆盖、输出数量和评估边界。",
            )
            view = st.radio(
                "数据分析工作区",
                ["Dashboard", "Benchmark"],
                format_func=_zh,
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
                "系统管理",
                "设置",
                "查看运行模式、证据规则和系统健康状态。",
            )
            view = st.radio(
                "设置工作区",
                ["Runtime & Data", "Rules", "System Health"],
                format_func=_zh,
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
            "工作区加载失败",
            "底层数据或配置不可用。请重试，或前往“系统健康”检查。",
            repr(exc),
        )
