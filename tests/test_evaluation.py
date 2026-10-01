from eval import run_offline_evaluation


def test_offline_evaluation_passes_on_versioned_demo_data():
    result = run_offline_evaluation()
    assert result["total_cases"] == 4
    assert result["passed_cases"] == 4
    assert result["offline_case_pass_rate"] == 1.0
