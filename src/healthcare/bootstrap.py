"""Application bootstrap and dependency wiring."""

from __future__ import annotations

from pathlib import Path

from .activation_repositories import (
    CompetitorChangeRepository,
    ContentOpportunityRepository,
    MarketingActionBriefRepository,
    WeeklyDigestRepository,
)
from .activation_services import (
    ChangeDetectionService,
    MarketingActionBriefService,
    WeeklyDigestService,
)
from .database import Database
from .analytics_repositories import BenchmarkRepository
from .analytics_service import AnalyticsService, BenchmarkService
from .demo_data import seed_demo_dataset
from .demo_market_seed import seed_phase3_demo
from .ai_service import AIService
from .claim_service import ClaimService
from .evidence_pack_service import EvidencePackService
from .intelligence_repositories import (
    BriefRepository,
    ClaimRepository,
    EvidencePackRepository,
    GenerationLogRepository,
    VendorProfileRepository,
)
from .intelligence_export import IntelligenceExportService
from .intelligence_services import (
    BriefService,
    ComparisonService,
    MarketIntelligenceServices,
    VendorIntelligenceService,
)
from .repositories import (
    EvidenceRepository,
    SolutionCategoryRepository,
    VendorRepository,
)
from .services import DataFoundationService, EvidenceService, VendorService
from .traceability_service import TraceabilityService
from .workflow_repositories import (
    AuditRepository,
    DuplicateGroupRepository,
    ExecutiveBriefRepository,
    FeedRepository,
    OpportunityRepository,
    ReviewRepository,
    SalesEnablementRepository,
    SavedComparisonRepository,
    UsageRepository,
    WatchlistRepository,
)
from .workflow_services import (
    AuditService,
    BriefWorkflowService,
    DuplicateGroupService,
    EvidenceQualityService,
    ExecutiveBriefService,
    MarketMapService,
    OpportunityService,
    ProductWorkflowServices,
    SalesEnablementService,
    SavedComparisonService,
    UsageService,
    WatchlistService,
    WorkflowEventService,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "healthcare_intelligence.db"
DEFAULT_TAXONOMY_PATH = PROJECT_ROOT / "config" / "healthcare_solution_taxonomy.json"
DEFAULT_VENDOR_SEED_PATH = PROJECT_ROOT / "data" / "demo" / "healthcare_vendors.json"
DEFAULT_EVALUATION_MANIFEST_PATH = PROJECT_ROOT / "evaluation_manifest.json"


def build_data_foundation(database: Database) -> DataFoundationService:
    category_repository = SolutionCategoryRepository(database)
    vendor_repository = VendorRepository(database)
    evidence_repository = EvidenceRepository(database)
    vendor_service = VendorService(vendor_repository)
    evidence_service = EvidenceService(
        evidence_repository,
        vendor_repository,
        category_repository,
    )
    return DataFoundationService(
        vendor_service,
        evidence_service,
        category_repository,
    )


def bootstrap_data_foundation(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
    seed_demo: bool = True,
    reset_demo: bool = False,
) -> DataFoundationService:
    database = Database(database_path)
    database.initialise()
    foundation = build_data_foundation(database)
    if seed_demo:
        seed_demo_dataset(
            foundation,
            foundation.category_repository,
            DEFAULT_TAXONOMY_PATH,
            DEFAULT_VENDOR_SEED_PATH,
            reset=reset_demo,
        )
    return foundation


def build_market_intelligence_services(
    foundation: DataFoundationService,
) -> MarketIntelligenceServices:
    database = foundation.category_repository.database
    pack_repository = EvidencePackRepository(database)
    claim_repository = ClaimRepository(database)
    brief_repository = BriefRepository(database, claim_repository)
    profile_repository = VendorProfileRepository(database)
    log_repository = GenerationLogRepository(database)
    pack_service = EvidencePackService(
        pack_repository,
        foundation.evidence_service.evidence_repository,
        foundation.vendor_service.repository,
    )
    traceability_service = TraceabilityService(
        claim_repository,
        brief_repository,
        pack_repository,
        foundation.evidence_service.evidence_repository,
    )
    claim_service = ClaimService(
        claim_repository,
        brief_repository,
        pack_repository,
        traceability_service,
    )
    brief_service = BriefService(brief_repository, claim_service)
    ai_service = AIService()
    vendor_intelligence_service = VendorIntelligenceService(
        foundation.vendor_service.repository,
        foundation.evidence_service.evidence_repository,
        pack_service,
        ai_service,
        brief_service,
        profile_repository,
        log_repository,
        traceability_service,
    )
    comparison_service = ComparisonService(
        foundation.vendor_service.repository,
        pack_service,
        ai_service,
        brief_service,
        log_repository,
        traceability_service,
    )
    export_service = IntelligenceExportService(
        pack_repository,
        foundation.evidence_service.evidence_repository,
        foundation.vendor_service.repository,
    )
    return MarketIntelligenceServices(
        evidence_pack_service=pack_service,
        claim_service=claim_service,
        traceability_service=traceability_service,
        brief_service=brief_service,
        vendor_intelligence_service=vendor_intelligence_service,
        comparison_service=comparison_service,
        brief_repository=brief_repository,
        claim_repository=claim_repository,
        profile_repository=profile_repository,
        generation_log_repository=log_repository,
        export_service=export_service,
    )


def bootstrap_market_intelligence(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
    seed_demo: bool = True,
    seed_intelligence_demo: bool = False,
) -> tuple[DataFoundationService, MarketIntelligenceServices]:
    foundation = bootstrap_data_foundation(database_path, seed_demo=seed_demo)
    intelligence = build_market_intelligence_services(foundation)
    if seed_intelligence_demo:
        seed_phase3_demo(foundation, intelligence)
    return foundation, intelligence


def build_product_workflow_services(
    foundation: DataFoundationService,
    intelligence: MarketIntelligenceServices,
) -> ProductWorkflowServices:
    database = foundation.category_repository.database
    feed_repository = FeedRepository(database)
    watchlist_repository = WatchlistRepository(database)
    opportunity_repository = OpportunityRepository(database)
    duplicate_group_repository = DuplicateGroupRepository(database)
    review_repository = ReviewRepository(database)
    saved_comparison_repository = SavedComparisonRepository(database)
    executive_brief_repository = ExecutiveBriefRepository(database)
    sales_enablement_repository = SalesEnablementRepository(database)
    usage_repository = UsageRepository(database)
    audit_repository = AuditRepository(database)
    change_repository = CompetitorChangeRepository(database)
    marketing_action_repository = MarketingActionBriefRepository(database)
    content_opportunity_repository = ContentOpportunityRepository(database)
    weekly_digest_repository = WeeklyDigestRepository(database)
    usage_service = UsageService(usage_repository)
    audit_service = AuditService(audit_repository)
    event_service = WorkflowEventService(
        feed_repository,
        audit_service,
        usage_service,
        foundation.vendor_service.repository,
    )
    quality_service = EvidenceQualityService(foundation.evidence_service.evidence_repository)
    market_map_service = MarketMapService(
        foundation.vendor_service.repository,
        foundation.evidence_service.evidence_repository,
        foundation.category_repository,
    )
    watchlist_service = WatchlistService(
        watchlist_repository,
        foundation.vendor_service.repository,
        foundation.evidence_service.evidence_repository,
        intelligence.brief_repository,
        intelligence.profile_repository,
        feed_repository,
        quality_service,
        usage_service,
    )
    duplicate_group_service = DuplicateGroupService(
        duplicate_group_repository,
        foundation.evidence_service.evidence_repository,
    )
    opportunity_service = OpportunityService(
        opportunity_repository,
        market_map_service,
        foundation.evidence_service.evidence_repository,
        intelligence.claim_repository,
        intelligence.brief_repository,
        foundation.category_repository,
        watchlist_repository,
        event_service,
    )
    brief_workflow_service = BriefWorkflowService(
        intelligence.brief_repository,
        intelligence.claim_repository,
        intelligence.claim_service,
        review_repository,
        foundation.evidence_service.evidence_repository,
        intelligence.traceability_service,
        event_service,
        audit_service,
        usage_service,
    )
    saved_comparison_service = SavedComparisonService(
        saved_comparison_repository, intelligence.brief_repository
    )
    executive_brief_service = ExecutiveBriefService(
        executive_brief_repository, intelligence.brief_repository, feed_repository
    )
    sales_enablement_service = SalesEnablementService(
        sales_enablement_repository, intelligence.brief_repository
    )
    benchmark_service = BenchmarkService(
        BenchmarkRepository(database),
        DEFAULT_EVALUATION_MANIFEST_PATH,
    )
    analytics_service = AnalyticsService(database, benchmark_service, quality_service)
    change_detection_service = ChangeDetectionService(
        change_repository,
        foundation.evidence_service.evidence_repository,
        foundation.vendor_service.repository,
    )
    marketing_action_service = MarketingActionBriefService(
        marketing_action_repository,
        content_opportunity_repository,
        change_repository,
        change_detection_service,
        foundation.evidence_service.evidence_repository,
        foundation.vendor_service.repository,
        foundation.category_repository,
    )
    weekly_digest_service = WeeklyDigestService(
        weekly_digest_repository,
        change_repository,
        change_detection_service,
        content_opportunity_repository,
        foundation.vendor_service.repository,
    )
    foundation.vendor_service.event_handler = event_service
    foundation.evidence_service.event_handler = event_service
    intelligence.claim_service.event_handler = event_service
    intelligence.brief_service.event_handler = event_service
    return ProductWorkflowServices(
        event_service=event_service,
        feed_repository=feed_repository,
        watchlist_service=watchlist_service,
        market_map_service=market_map_service,
        opportunity_service=opportunity_service,
        quality_service=quality_service,
        duplicate_group_service=duplicate_group_service,
        brief_workflow_service=brief_workflow_service,
        saved_comparison_service=saved_comparison_service,
        executive_brief_service=executive_brief_service,
        sales_enablement_service=sales_enablement_service,
        usage_service=usage_service,
        audit_service=audit_service,
        opportunity_repository=opportunity_repository,
        duplicate_group_repository=duplicate_group_repository,
        review_repository=review_repository,
        saved_comparison_repository=saved_comparison_repository,
        executive_brief_repository=executive_brief_repository,
        sales_enablement_repository=sales_enablement_repository,
        usage_repository=usage_repository,
        audit_repository=audit_repository,
        benchmark_service=benchmark_service,
        analytics_service=analytics_service,
        change_detection_service=change_detection_service,
        marketing_action_service=marketing_action_service,
        weekly_digest_service=weekly_digest_service,
        change_repository=change_repository,
        marketing_action_repository=marketing_action_repository,
        content_opportunity_repository=content_opportunity_repository,
        weekly_digest_repository=weekly_digest_repository,
    )


def bootstrap_product_workflow(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
    seed_demo: bool = True,
    seed_intelligence_demo: bool = False,
    seed_workflow_demo: bool = False,
) -> tuple[DataFoundationService, MarketIntelligenceServices, ProductWorkflowServices]:
    foundation, intelligence = bootstrap_market_intelligence(
        database_path,
        seed_demo=seed_demo,
        seed_intelligence_demo=seed_intelligence_demo,
    )
    workflow = build_product_workflow_services(foundation, intelligence)
    if seed_workflow_demo:
        from .demo_workflow_seed import seed_phase4_demo
        from .demo_activation_seed import seed_activation_demo

        seed_phase4_demo(foundation, intelligence, workflow)
        seed_activation_demo(foundation, workflow)
    return foundation, intelligence, workflow
