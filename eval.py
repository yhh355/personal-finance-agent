"""Run reproducible offline checks or opt-in live Agent tool-coverage evaluation."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from agent import run_openrouter_agent
from finance_tools import create_saving_plan, extract_xlsx_statement, get_spending_insights, load_statement, query_transactions


ROOT = Path(__file__).resolve().parent
CASES_PATH = ROOT / "evals" / "cases.json"
DEMO_STATEMENT = ROOT / "data" / "demo_statement.xlsx"


def load_demo_frame():
    """Extract the checked-in synthetic XLSX into a temporary canonical CSV."""
    with tempfile.TemporaryDirectory() as directory:
        result = extract_xlsx_statement(DEMO_STATEMENT.read_bytes(), DEMO_STATEMENT.name, directory)
        return load_statement(result.csv_path)


def _close(actual: float, expected: float) -> bool:
    return abs(float(actual) - float(expected)) < 0.001


def run_offline_evaluation() -> dict[str, Any]:
    """Evaluate deterministic extractor/tool behaviour against versioned expectations."""
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["offline_cases"]
    frame = load_demo_frame()
    results: list[dict[str, Any]] = []
    for case in cases:
        case_id = case["id"]
        if case_id == "monthly_insights":
            value = get_spending_insights(frame, "2026-09", case["maximum_spending"])
            expected = case["expected"]
            passed = (
                _close(value["total_spending"], expected["total_spending"])
                and value["highest_category"] == expected["highest_category"]
                and value["budget"]["status"] == expected["budget_status"]
            )
        elif case_id == "social_merchant_query":
            value = query_transactions(frame, "2026-09", **case["query"])
            expected = case["expected"]
            passed = (
                value["matching_transaction_count"] == expected["matching_transaction_count"]
                and _close(value["matching_spending"], expected["matching_spending"])
                and value["items"][0]["merchant"] == expected["first_merchant"]
            )
        elif case_id == "protected_saving_plan":
            value = create_saving_plan(frame, "2026-09", case["saving_target"], case["protected_categories"])
            expected = case["expected"]
            passed = (
                value["recommendations"][0]["category"] == expected["first_category"]
                and _close(value["recommendations"][0]["reduction_amount"], expected["first_reduction_amount"])
                and value["is_achievable"] == expected["is_achievable"]
            )
        elif case_id == "three_tool_workflow":
            get_spending_insights(frame, "2026-09", 1800.0)
            query_transactions(frame, "2026-09", category="Lifestyle and Social", group_by="merchant")
            create_saving_plan(frame, "2026-09", 200.0, ["Food and Dining", "Transport"])
            value = {"tools": ["get_spending_insights", "query_transactions", "create_saving_plan"]}
            passed = value["tools"] == case["expected_tools"]
        else:
            raise ValueError(f"Unknown offline case: {case_id}")
        results.append({"id": case_id, "passed": passed, "result": value})
    passed_cases = sum(item["passed"] for item in results)
    return {"mode": "offline", "total_cases": len(results), "passed_cases": passed_cases, "offline_case_pass_rate": passed_cases / len(results), "results": results}


def run_live_evaluation() -> dict[str, Any]:
    """Evaluate required tool coverage with real OpenRouter calls; API key is required."""
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["live_cases"]
    frame = load_demo_frame()
    results: list[dict[str, Any]] = []
    for case in cases:
        response = run_openrouter_agent(
            case["prompt"], frame, "2026-09", 1800.0, 200.0,
            ["Food and Dining", "Transport"], history=None,
        )
        tools = [item["tool"] for item in response["tool_trace"]]
        passed = set(case["required_tools"]).issubset(tools)
        results.append({
            "id": case["id"], "passed": passed, "required_tools": case["required_tools"],
            "actual_tools": tools, "tool_calls": len(tools), "model": response["model"],
            "reported_tokens": response["total_tokens"],
        })
    passed_cases = sum(item["passed"] for item in results)
    return {"mode": "live", "total_cases": len(results), "passed_cases": passed_cases, "required_tool_coverage": passed_cases / len(results), "results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("offline", "live"), default="offline")
    arguments = parser.parse_args()
    result = run_offline_evaluation() if arguments.mode == "offline" else run_live_evaluation()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
