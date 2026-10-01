from pathlib import Path

import pandas as pd

from finance_tools import create_saving_plan, extract_xlsx_statement, load_statement, query_transactions, run_monthly_workflow


def _statement() -> pd.DataFrame:
    return pd.DataFrame({
        "Transaction Date": ["2026-08-02", "2026-09-03", "2026-09-07", "2026-09-12"],
        "Merchant": ["NTUC", "NTUC", "MRT", "Gym"],
        "Amount": [-40.0, -120.0, -30.0, -80.0],
        "Category": ["Groceries", "Groceries", "Transport", "Gym"],
    })


def test_xlsx_extraction_uses_billing_period_as_csv_name(tmp_path: Path):
    source = tmp_path / "statement.xlsx"
    _statement().to_excel(source, index=False)
    result = extract_xlsx_statement(source.read_bytes(), source.name, tmp_path / "statements")
    assert Path(result.csv_path).name == "2026-08_to_2026-09.csv"
    assert result.rows_saved == 4
    assert set(load_statement(result.csv_path).columns) == {"Date", "Merchant", "Description", "Amount", "Category"}


def test_initial_workflow_has_no_unanalysed_saving_recommendation(tmp_path: Path):
    source = tmp_path / "statement.xlsx"
    _statement().to_excel(source, index=False)
    result = extract_xlsx_statement(source.read_bytes(), source.name, tmp_path / "statements")
    frame = load_statement(result.csv_path)
    workflow = run_monthly_workflow(frame, "2026-09", 300)
    assert workflow["tool_trace"] == ["spending_summary", "budget_status"]
    assert workflow["budget"]["status"] == "within_limit"
    assert "saving_plan" not in workflow
    plan = create_saving_plan(frame, "2026-09", 130, ["gym", "transport"])
    assert plan["recommendations"] == [{"category": "Groceries", "reduction_amount": 120.0, "category_spending": 120.0}]
    assert plan["unmet_amount"] == 10.0


def test_wechat_export_with_preamble_and_chinese_headers(tmp_path: Path):
    rows = [["微信支付账单明细"], ["开始时间：[2026-08-30 00:00:00]"], [], ["交易时间", "交易类型", "交易对方", "商品", "收/支", "金额(元)"]]
    rows += [
        ["2026-09-02 08:00:00", "商户消费", "NTUC", "NTUC", "支出", 32.5],
        ["2026-09-03 12:00:00", "商户消费", "GRAB", "GrabFood", "支出", 18.0],
        ["2026-09-04 12:00:00", "转账", "Alice", "转账", "收入", 100.0],
    ]
    source = tmp_path / "wechat.xlsx"
    pd.DataFrame(rows).to_excel(source, index=False, header=False)
    result = extract_xlsx_statement(source.read_bytes(), source.name, tmp_path / "statements")
    extracted = load_statement(result.csv_path)
    assert Path(result.csv_path).name == "2026-09.csv"
    assert len(extracted) == 2
    assert extracted["Category"].tolist() == ["Living", "Food and Dining"]


def test_query_transactions_groups_and_filters_local_rows():
    frame = pd.DataFrame({
        "Date": pd.to_datetime(["2026-09-01", "2026-09-02"]),
        "Merchant": ["Alice", "NTUC"], "Description": ["Transfer", "Groceries"],
        "Amount": [60.0, 20.0], "Category": ["Lifestyle and Social", "Living"],
    })
    result = query_transactions(frame, "2026-09", category="Lifestyle and Social", group_by="merchant")
    assert result["matching_transaction_count"] == 1
    assert result["matching_spending"] == 60.0
    assert result["items"] == [{"merchant": "Alice", "spending": 60.0, "transaction_count": 1}]
