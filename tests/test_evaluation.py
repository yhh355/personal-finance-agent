import json
from pathlib import Path

from eval import run_offline_evaluation


def test_offline_evaluation_passes_on_versioned_demo_data():
    result = run_offline_evaluation()
    assert result["total_cases"] == 4
    assert result["passed_cases"] == 4
    assert result["offline_case_pass_rate"] == 1.0


def test_live_suite_contains_ten_varied_tool_coverage_cases():
    cases_path = Path(__file__).resolve().parents[1] / "evals" / "cases.json"
    live_cases = json.loads(cases_path.read_text(encoding="utf-8"))["live_cases"]
    assert len(live_cases) == 10
    assert sum("create_saving_plan" in item["required_tools"] for item in live_cases) == 5
