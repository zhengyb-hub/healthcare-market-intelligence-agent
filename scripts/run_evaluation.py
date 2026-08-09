"""Run the frozen Phase 5 synthetic evaluation and persist measured AI stages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.healthcare.analytics_models import AI_STAGE_KEYS
from src.healthcare.bootstrap import DEFAULT_DATABASE_PATH, bootstrap_product_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    args = parser.parse_args()
    foundation, intelligence, workflow = bootstrap_product_workflow(
        args.database,
        seed_demo=True,
        seed_intelligence_demo=True,
        seed_workflow_demo=True,
    )
    manifest_check = workflow.benchmark_service.validate_manifest()
    if manifest_check["result"] != "PASS":
        raise SystemExit(json.dumps(manifest_check, indent=2))

    generated: list[dict[str, object]] = []
    skipped: list[str] = []
    for task in workflow.benchmark_service.tasks():
        pair_id = f"pair_{task.task_id}"
        if workflow.benchmark_service.repository.get_by_pair(pair_id, "AI_ASSISTED"):
            skipped.append(task.task_id)
            continue
        timings = {key: 0.0 for key in AI_STAGE_KEYS}
        if task.task_type == "SINGLE_VENDOR_BRIEF":
            _, brief, traceability = intelligence.vendor_intelligence_service.generate(
                task.vendor_ids[0],
                stage_times=timings,
            )
        elif task.task_type == "THREE_VENDOR_COMPARISON":
            brief, traceability = intelligence.comparison_service.generate(
                task.vendor_ids,
                stage_times=timings,
            )
        else:
            raise ValueError(f"Unsupported evaluation task type: {task.task_type}")

        pack = intelligence.evidence_pack_service.get_pack(brief.evidence_pack_id)
        if pack is None or pack.evidence_ids != task.evidence_ids:
            raise RuntimeError(f"{task.task_id}: generated Evidence Pack differs from manifest")
        started = perf_counter()
        markdown = intelligence.export_service.markdown(brief)
        timings["ai_export_minutes"] = (perf_counter() - started) / 60
        started = perf_counter()
        qa = intelligence.traceability_service.validate_brief(brief.brief_id, update_claims=False)
        timings["ai_qa_minutes"] = (perf_counter() - started) / 60
        run = workflow.benchmark_service.record_run(
            task.task_id,
            "AI_ASSISTED",
            timings,
            run_status="DRAFT",
            notes=(
                "Automated Evidence Pack, generation, validation, QA, and export stages were "
                "measured. Human review and editing must be entered before completion."
            ),
            claim_count=len(brief.claims),
            brief_length=len(markdown),
            brief_id=brief.brief_id,
            unsupported_claims_found=qa["unsupported_claims"],
            citation_errors_found=qa["invalid_citations_detected"],
            measurement_method="AUTO_TIMER_PENDING_HUMAN",
        )
        generated.append(
            {
                "task_id": task.task_id,
                "brief_id": brief.brief_id,
                "claim_count": len(brief.claims),
                "evidence_count": len(task.evidence_ids),
                "traceability": traceability["result"],
                "benchmark_status": run.run_status,
                "stage_times": timings,
            }
        )
    workflow.analytics_service.export_artifacts(PROJECT_ROOT)
    print(json.dumps({
        "manifest": manifest_check,
        "generated": generated,
        "skipped": skipped,
        "benchmark_summary": workflow.benchmark_service.summary(),
        "note": "AI runs remain DRAFT until actual human review and editing times are entered.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
