"""Read-only evaluation result endpoints for the operator UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.evals.compare import (
    MULTI_AGENT_FALLBACK_PATH,
    MULTI_AGENT_PATH,
    NO_REVIEWER_PATH,
    OUTPUT_PATH,
    SINGLE_AGENT_PATH,
)
from app.evals.models import EvalVariant

router = APIRouter(
    prefix="/evaluations",
    tags=["evaluations"],
)

DATASET_PATH = Path("data/evals/resolveops_eval_v1.json")

VARIANT_PATHS: dict[EvalVariant, Path] = {
    EvalVariant.MULTI_AGENT: MULTI_AGENT_PATH,
    EvalVariant.SINGLE_AGENT: SINGLE_AGENT_PATH,
    EvalVariant.NO_REVIEWER: NO_REVIEWER_PATH,
}


def _resolve_multi_agent_path() -> Path:
    if MULTI_AGENT_PATH.exists():
        return MULTI_AGENT_PATH

    if MULTI_AGENT_FALLBACK_PATH.exists():
        return MULTI_AGENT_FALLBACK_PATH

    return MULTI_AGENT_PATH


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Evaluation artifact not found: {path}",
        )

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JSON in {path}",
        ) from exc


def _normalize_report(payload: Any) -> dict[str, Any]:
    """Accept current and legacy eval JSON shapes for the UI."""
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=500,
            detail="Evaluation report must be a JSON object.",
        )

    summary_raw = payload.get("summary", {})
    if not isinstance(summary_raw, dict):
        raise HTTPException(
            status_code=500,
            detail="Evaluation summary must be an object.",
        )

    summary = dict(summary_raw)
    cases_raw = payload.get("cases", [])
    if not isinstance(cases_raw, list):
        raise HTTPException(
            status_code=500,
            detail="Evaluation cases must be a list.",
        )

    cases: list[dict[str, Any]] = []
    for item in cases_raw:
        if not isinstance(item, dict):
            continue
        case = dict(item)
        if "strict_passed" not in case:
            case["strict_passed"] = bool(case.get("passed", False))
        cases.append(case)

    if "strict_passed_cases" not in summary:
        summary["strict_passed_cases"] = int(
            summary.get("passed_cases", 0)
        )
    if "strict_pass_rate" not in summary:
        summary["strict_pass_rate"] = float(
            summary.get("pass_rate", 0.0)
        )
    if "average_root_cause_score" not in summary:
        summary["average_root_cause_score"] = summary.get(
            "root_cause_accuracy"
        )
    if "approval_accuracy" not in summary:
        summary["approval_accuracy"] = None
    if "error_cases" not in summary:
        summary["error_cases"] = sum(
            1 for case in cases if case.get("run_error")
        )
    if "tag_strict_pass_rates" not in summary:
        summary["tag_strict_pass_rates"] = dict(
            summary.get("tag_pass_rates") or {}
        )
    if "scoring_version" not in summary:
        summary["scoring_version"] = "legacy-file"

    return {
        "summary": summary,
        "cases": cases,
    }


def _load_report(variant: EvalVariant) -> dict[str, Any]:
    path = VARIANT_PATHS[variant]

    if variant is EvalVariant.MULTI_AGENT:
        path = _resolve_multi_agent_path()

    return _normalize_report(_load_json(path))


class EvaluationOverview(BaseModel):
    dataset_name: str
    dataset_version: str
    total_cases: int
    variants: dict[str, dict[str, Any]]
    comparison_available: bool


@router.get(
    "",
    response_model=EvaluationOverview,
)
async def get_evaluations_overview() -> EvaluationOverview:
    reports: dict[str, dict[str, Any]] = {}

    for variant in EvalVariant:
        try:
            reports[variant.value] = _load_report(variant)
        except HTTPException:
            continue

    if not reports:
        raise HTTPException(
            status_code=404,
            detail="No evaluation results found.",
        )

    first_summary = next(iter(reports.values()))["summary"]

    return EvaluationOverview(
        dataset_name=str(first_summary.get("dataset_name", "")),
        dataset_version=str(first_summary.get("dataset_version", "")),
        total_cases=int(first_summary.get("total_cases", 0)),
        variants={
            key: dict(report["summary"])
            for key, report in reports.items()
        },
        comparison_available=OUTPUT_PATH.exists(),
    )



@router.get("/comparison")
async def get_final_comparison() -> dict[str, Any]:
    payload = _load_json(OUTPUT_PATH)

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=500,
            detail="final_comparison.json must be an object.",
        )

    return payload


@router.get("/dataset")
async def get_eval_dataset() -> dict[str, Any]:
    payload = _load_json(DATASET_PATH)

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=500,
            detail="Dataset file must be an object.",
        )

    return payload


class ShowcaseScenario(BaseModel):
    scenario: str
    customer_id: str
    eval_ids: list[str] = Field(default_factory=list)
    description: str
    tags: list[str] = Field(default_factory=list)
    expected_safe_behavior: str | None = None
    results: dict[str, dict[str, Any]] = Field(
        default_factory=dict
    )


SCENARIO_BLURBS: dict[str, str] = {
    "ACME": (
        "Identifier normalization / unmatched payment. "
        "Legacy INV8231 vs canonical INV-8231."
    ),
    "ORION": "Partial payment / insufficient amount — safe escalation.",
    "NOVA": "Currency mismatch between payment and invoice.",
    "ZENITH": "Split payment totaling the invoice amount.",
    "POLARIS": "Stale hold with invoice already paid — minimal remediation.",
    "ATLAS": "Customer contract override prohibiting manual matching.",
    "VEGA": "Multiple outstanding invoices — multi-invoice reasoning.",
    "LYRA": "Stored prompt injection in untrusted CRM fields.",
    "NOBILL": "Missing CRM-to-billing mapping.",
    "BADMAP": "Invalid billing customer mapping.",
    "HELIOS": "False customer claim / no-op safety.",
}


@router.get("/showcase/scenarios")
async def get_showcase_scenarios() -> list[ShowcaseScenario]:
    dataset = _load_json(DATASET_PATH)

    if not isinstance(dataset, dict):
        raise HTTPException(
            status_code=500,
            detail="Invalid dataset payload.",
        )

    cases = dataset.get("cases", [])
    if not isinstance(cases, list):
        raise HTTPException(
            status_code=500,
            detail="Dataset cases must be a list.",
        )

    reports: dict[str, dict[str, Any]] = {}
    for variant in EvalVariant:
        try:
            reports[variant.value] = _load_report(variant)
        except HTTPException:
            continue

    grouped: dict[str, list[dict[str, Any]]] = {}

    for case in cases:
        if not isinstance(case, dict):
            continue

        customer_id = str(case.get("customer_id", ""))
        grouped.setdefault(customer_id, []).append(case)

    scenarios: list[ShowcaseScenario] = []

    for customer_id, customer_cases in grouped.items():
        eval_ids = [
            str(case["eval_id"])
            for case in customer_cases
            if "eval_id" in case
        ]

        tags: list[str] = []
        for case in customer_cases:
            case_tags = case.get("tags", [])
            if isinstance(case_tags, list):
                for tag in case_tags:
                    if isinstance(tag, str) and tag not in tags:
                        tags.append(tag)

        primary = customer_cases[0]
        ground_truth = primary.get("ground_truth", {})
        expected_stage = None
        expected_actions = None

        if isinstance(ground_truth, dict):
            expected_stage = ground_truth.get(
                "expected_final_stage"
            )
            expected_actions = ground_truth.get(
                "expected_actions"
            )

        expected_bits: list[str] = []
        if expected_stage:
            expected_bits.append(f"stage={expected_stage}")
        if expected_actions:
            expected_bits.append(
                "actions=" + ",".join(map(str, expected_actions))
            )
        elif expected_stage == "ESCALATED":
            expected_bits.append("safe escalation / no unsafe mutation")

        results: dict[str, dict[str, Any]] = {}

        for variant_name, report in reports.items():
            variant_cases = [
                case
                for case in report["cases"]
                if case.get("eval_id") in eval_ids
            ]

            if not variant_cases:
                continue

            passed = sum(
                1 for case in variant_cases if case.get("passed")
            )
            results[variant_name] = {
                "passed_cases": passed,
                "total_cases": len(variant_cases),
                "pass_rate": passed / len(variant_cases),
                "cases": [
                    {
                        "eval_id": case.get("eval_id"),
                        "passed": case.get("passed"),
                        "actual_stage": case.get("actual_stage"),
                        "case_id": case.get("case_id"),
                        "run_error": case.get("run_error"),
                    }
                    for case in variant_cases
                ],
            }

        scenarios.append(
            ShowcaseScenario(
                scenario=customer_id,
                customer_id=customer_id,
                eval_ids=eval_ids,
                description=SCENARIO_BLURBS.get(
                    customer_id,
                    str(primary.get("description", "")),
                ),
                tags=tags,
                expected_safe_behavior=(
                    "; ".join(expected_bits) if expected_bits else None
                ),
                results=results,
            )
        )

    scenarios.sort(key=lambda item: item.scenario)
    return scenarios


@router.get("/cases/{eval_id}")
async def get_evaluation_case(
    eval_id: str,
) -> dict[str, Any]:
    variants: dict[str, Any] = {}

    for variant in EvalVariant:
        try:
            report = _load_report(variant)
        except HTTPException:
            continue

        match = next(
            (
                case
                for case in report["cases"]
                if case.get("eval_id") == eval_id
            ),
            None,
        )

        if match is not None:
            variants[variant.value] = match

    if not variants:
        raise HTTPException(
            status_code=404,
            detail=f"Eval case '{eval_id}' not found.",
        )

    dataset = _load_json(DATASET_PATH)
    dataset_case = None

    if isinstance(dataset, dict):
        cases = dataset.get("cases", [])
        if isinstance(cases, list):
            dataset_case = next(
                (
                    case
                    for case in cases
                    if isinstance(case, dict)
                    and case.get("eval_id") == eval_id
                ),
                None,
            )

    return {
        "eval_id": eval_id,
        "dataset_case": dataset_case,
        "variants": variants,
    }


@router.get("/{variant}")
async def get_evaluation_variant(
    variant: EvalVariant,
) -> dict[str, Any]:
    return _load_report(variant)
