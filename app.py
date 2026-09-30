"""Single-page Streamlit interface for the Excel-first finance agent."""
from pathlib import Path

import streamlit as st

from agent import run_openrouter_agent
from finance_tools import BUDGET_CATEGORIES, TOOL_DESCRIPTORS, available_months, extract_xlsx_statement, load_statement, run_monthly_workflow, serialise_extraction


ROOT = Path(__file__).resolve().parent
STATEMENTS_DIR = ROOT / "data" / "statements"
CHAT_SEED_VERSION = 3

st.set_page_config(page_title="Personal Finance Statement Agent", page_icon="💳", layout="wide")
st.title("Personal Finance Statement Agent")
st.caption("Upload an XLSX statement, set your constraints, then discuss the analysis with the agent on this same page.")


def statement_files() -> list[Path]:
    return sorted(STATEMENTS_DIR.glob("*.csv"))


def analysis_message(result: dict) -> str:
    summary, budget = result["summary"], result["budget"]
    category_lines = "\n".join(f"- {name}: S${amount:,.2f}" for name, amount in summary["by_category"].items()) or "- No spending records"
    return f"""I have completed the initial analysis for **{summary['month']}**.

**Spending:** S${summary['total_spending']:,.2f} across {summary['transaction_count']} transactions. Your highest category is **{summary['highest_category'] or 'none'}**.

**Budget:** {budget['status'].replace('_', ' ')}. Your limit is S${budget['maximum_spending']:,.2f}; remaining amount is S${budget['remaining']:,.2f}.

**Category totals:**
{category_lines}

I have not made a reduction recommendation yet. Ask me for a saving plan when you are ready, and I will analyse the details before proposing any amount."""


st.header("1. Import statement and set constraints")
uploaded = st.file_uploader("WeChat/XLSX statement", type=["xlsx"], help="The first worksheet must contain Date and Amount columns. Merchant, Description and Category are optional.")
if uploaded and st.button("Extract XLSX to local CSV", type="primary"):
    try:
        extraction = extract_xlsx_statement(uploaded.getvalue(), uploaded.name, STATEMENTS_DIR)
        st.session_state["selected_statement"] = str(Path(extraction.csv_path))
        st.session_state["last_extraction"] = serialise_extraction(extraction)
        st.session_state.pop("analysis", None)
        st.session_state["chat_messages"] = []
        st.success(f"Saved {extraction.rows_saved} expense transactions to {Path(extraction.csv_path).name}")
    except Exception as error:
        st.error(f"Could not extract this XLSX: {error}")

if st.session_state.get("last_extraction"):
    with st.expander("Last extraction details"):
        st.json(st.session_state["last_extraction"], expanded=False)

csv_files = statement_files()
if not csv_files:
    st.info("Upload and extract an XLSX file to unlock the analysis chat below.")
    st.stop()

previous_path = st.session_state.get("selected_statement")
selected_index = next((index for index, item in enumerate(csv_files) if str(item) == previous_path), 0)
selected_file = st.selectbox("Extracted statement", csv_files, index=selected_index, format_func=lambda item: item.name)
try:
    statement = load_statement(selected_file)
except Exception as error:
    st.error(f"Cannot read {selected_file.name}: {error}")
    st.stop()

months = available_months(statement)
with st.form("constraints"):
    month = st.selectbox("Billing month", months, index=len(months) - 1)
    categories = sorted(statement.loc[statement["Date"].dt.strftime("%Y-%m") == month, "Category"].unique().tolist())
    first, second, third = st.columns(3)
    with first:
        maximum_spending = st.number_input("Maximum spending this month (SGD)", min_value=0.01, value=1800.0, step=50.0)
    with second:
        saving_target = st.number_input("Default saving target (SGD)", min_value=0.01, value=200.0, step=25.0)
    with third:
        protected_types = st.multiselect("Categories to keep", categories, help="These categories are excluded from saving suggestions.")
    analyse = st.form_submit_button("Analyse statement and open chat", type="primary")

if analyse:
    try:
        st.session_state["selected_statement"] = str(selected_file)
        st.session_state["selected_month"] = month
        st.session_state["maximum_spending"] = maximum_spending
        st.session_state["saving_target"] = saving_target
        st.session_state["protected_types"] = protected_types
        st.session_state["analysis"] = run_monthly_workflow(statement, month, maximum_spending)
        st.session_state["analysis_version"] = st.session_state.get("analysis_version", 0) + 1
        st.session_state["chat_messages"] = []
        st.session_state.pop("pending_chat_request", None)
        st.success("Analysis is ready below. Ask the agent a follow-up question in the chat.")
    except Exception as error:
        st.error(f"Could not analyse this statement: {error}")

with st.expander("Review or correct budget categories"):
    st.caption("Categories are suggested from the merchant and description. Save any corrections before running analysis.")
    edited_statement = st.data_editor(statement, use_container_width=True, hide_index=True, disabled=["Date", "Merchant", "Description", "Amount"], column_config={"Category": st.column_config.SelectboxColumn("Budget category", options=BUDGET_CATEGORIES, required=True)})
    if st.button("Save category changes"):
        edited_statement.assign(Date=edited_statement["Date"].dt.strftime("%Y-%m-%d")).to_csv(selected_file, index=False)
        st.success("Category changes saved. Run analysis again to use them.")

st.divider()
st.header("2. Finance analysis chat")
result = st.session_state.get("analysis")
if not result:
    st.info("Complete the analysis above to start the chat. Nothing opens in a separate page.")
    st.stop()

selected_path = st.session_state.get("selected_statement")
chat_statement = load_statement(selected_path)
month = st.session_state["selected_month"]
maximum_spending = st.session_state["maximum_spending"]
saving_target = st.session_state["saving_target"]
protected_types = st.session_state["protected_types"]
if (st.session_state.get("chat_analysis_version") != st.session_state.get("analysis_version") or st.session_state.get("chat_seed_version") != CHAT_SEED_VERSION):
    st.session_state["chat_messages"] = [{"role": "assistant", "content": analysis_message(result), "model": "Deterministic Python tools", "tokens": None, "tool_trace": result["tool_trace"]}]
    st.session_state["chat_analysis_version"] = st.session_state.get("analysis_version")
    st.session_state["chat_seed_version"] = CHAT_SEED_VERSION

if st.button("Clear chat"):
    st.session_state["chat_messages"] = []
    st.session_state.pop("pending_chat_request", None)
    st.session_state["chat_analysis_version"] = None
    st.session_state["chat_seed_version"] = None
    st.rerun()

for message in st.session_state["chat_messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            st.caption(f"Model: {message['model']} · reported tokens: {message['tokens'] or 'unavailable'}")
            with st.expander("Agent tool-call trace"):
                st.json(message["tool_trace"])

chat_prompt = st.chat_input("For example: Help me create a saving plan while keeping my selected categories.")
if chat_prompt:
    st.session_state["chat_messages"].append({"role": "user", "content": chat_prompt})
    st.session_state["pending_chat_request"] = {"query": chat_prompt, "history": list(st.session_state["chat_messages"][:-1])}
    st.rerun()

pending_request = st.session_state.pop("pending_chat_request", None)
if pending_request:
    try:
        with st.chat_message("assistant"):
            with st.spinner("Agent is analysing your statement..."):
                agent_result = run_openrouter_agent(pending_request["query"], chat_statement, month, maximum_spending, saving_target, protected_types, pending_request["history"])
            st.markdown(agent_result["answer"])
            st.caption(f"Model: {agent_result['model']} · reported tokens: {agent_result['total_tokens'] or 'unavailable'}")
            with st.expander("Agent tool-call trace"):
                st.json(agent_result["tool_trace"])
        st.session_state["chat_messages"].append({"role": "assistant", "content": agent_result["answer"], "model": agent_result["model"], "tokens": agent_result["total_tokens"], "tool_trace": agent_result["tool_trace"]})
    except Exception as error:
        failure_message = f"I could not complete that request: `{error}`"
        with st.chat_message("assistant"):
            st.error(failure_message)
        st.session_state["chat_messages"].append({"role": "assistant", "content": failure_message, "model": "Agent error", "tokens": None, "tool_trace": [{"tool": "agent_request", "arguments": {}, "result": {"error": str(error)}}]})

with st.expander("Analysis tools"):
    for name, description in TOOL_DESCRIPTORS.items():
        st.markdown(f"- `{name}` — {description}")
