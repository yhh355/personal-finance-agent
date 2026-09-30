from agent import AGENT_TOOL_SCHEMAS, MINIMUM_TOOL_CALLS, _system_prompt


def test_agent_exposes_three_composable_analysis_tools():
    assert {item["function"]["name"] for item in AGENT_TOOL_SCHEMAS} == {
        "query_transactions", "get_spending_insights", "create_saving_plan"
    }
    assert all(item["type"] == "function" and "function" in item for item in AGENT_TOOL_SCHEMAS)
    assert MINIMUM_TOOL_CALLS == 2


def test_agent_prompt_leaves_tool_selection_to_the_model():
    prompt = _system_prompt({"selected_month": "2026-09"})
    assert "You decide which tools to call" in prompt
    assert "social or entertainment activity" in prompt
    assert "Use query_transactions" in prompt
    assert "Use create_saving_plan only if the user explicitly asks" in prompt
    assert "multi-step investigation" in prompt
