"""Transparent tools for the Excel-first personal-finance Streamlit app."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
import re
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = ("Date", "Merchant", "Description", "Amount", "Category")
BUDGET_CATEGORIES = ("Living", "Food and Dining", "Transport", "Entertainment", "Shopping", "Lifestyle and Social", "Other")
_LEGACY_CATEGORY_LABELS = {
    "生活": "Living",
    "餐饮": "Food and Dining",
    "交通": "Transport",
    "娱乐": "Entertainment",
    "购物": "Shopping",
    "生活娱乐": "Lifestyle and Social",
    "其他": "Other",
    "living": "Living",
    "food and dining": "Food and Dining",
    "transport": "Transport",
    "entertainment": "Entertainment",
    "shopping": "Shopping",
    "lifestyle and social": "Lifestyle and Social",
    "other": "Other",
}
TOOL_DESCRIPTORS = {
    "query_transactions": "Read-only transaction query with optional category or merchant filters, and grouping by transaction, category, merchant, or date.",
    "get_spending_insights": "Return deterministic monthly totals, category shares, largest transactions, and budget status.",
    "create_saving_plan": "Create a deterministic savings plan for the user target while excluding categories the user chose to keep.",
}

_ALIASES = {
    "date": "Date", "transactiondate": "Date", "posteddate": "Date", "valuedate": "Date",
    "merchant": "Merchant", "payee": "Merchant", "vendor": "Merchant", "store": "Merchant",
    "description": "Description", "details": "Description", "narration": "Description", "memo": "Description",
    "amount": "Amount", "transactionamount": "Amount", "debit": "Amount", "spent": "Amount",
    "category": "Category", "type": "Category", "transactioncategory": "Category",
    # WeChat Pay exported XLSX headings.
    "交易时间": "Date", "交易对方": "Merchant", "商品": "Description", "金额元": "Amount",
    "收支": "Direction", "交易类型": "TransactionType", "当前状态": "Status",
}


@dataclass(frozen=True)
class ExtractionResult:
    csv_path: str
    billing_period: str
    rows_saved: int
    source_filename: str


def _normalised_name(value: object) -> str:
    return re.sub(r"[\W_]", "", str(value).lower(), flags=re.UNICODE)


def _find_header_row(raw: pd.DataFrame) -> int:
    """Find a row that contains at least Date and Amount after heading normalisation."""
    for index in range(min(len(raw), 50)):
        headings = {_ALIASES.get(_normalised_name(value), str(value).strip()) for value in raw.iloc[index].tolist()}
        if {"Date", "Amount"} <= headings:
            return index
    raise ValueError("Could not find a transaction header row with Date and Amount columns.")


def _currency_number(value: object) -> float | None:
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"nan", "none"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[^0-9.\-]", "", text)
    try:
        number = float(text)
    except ValueError:
        return None
    return -abs(number) if negative else number


def _suggest_budget_category(merchant: object, description: object, transaction_type: object = "") -> str:
    """Provide a revisable initial budget category; the user can correct it in the UI."""
    text = " ".join(str(value).lower() for value in (merchant, description, transaction_type))
    if any(word in text for word in ("grabfood", "food", "restaurant", "cafe", "dining", "餐", "饭", "食", "茶", "咖啡", "火锅")):
        return "Food and Dining"
    if any(word in text for word in ("grab", "taxi", "mrt", "bus", "transport", "交通", "地铁", "出租", "停车")):
        return "Transport"
    if any(word in text for word in ("movie", "cinema", "netflix", "spotify", "game", "娱乐", "电影", "游戏")):
        return "Entertainment"
    if any(word in text for word in ("shopee", "lazada", "shopping", "购物", "服饰")):
        return "Shopping"
    if any(word in text for word in ("transfer", "转账", "红包", "群收款")):
        return "Lifestyle and Social"
    if any(word in text for word in ("ntuc", "fairprice", "supermarket", "grocer", "超市", "生鲜", "rent", "utilities", "房租", "水电")):
        return "Living"
    return "Other"


def _billing_period(dates: pd.Series) -> str:
    first, last = dates.min().strftime("%Y-%m"), dates.max().strftime("%Y-%m")
    return first if first == last else f"{first}_to_{last}"


def extract_xlsx_statement(file_bytes: bytes, source_filename: str, output_dir: Path | str) -> ExtractionResult:
    """Tool 1: extract the first worksheet of an XLSX statement into canonical CSV."""
    if not source_filename.lower().endswith(".xlsx"):
        raise ValueError("Please upload an .xlsx statement file.")
    raw = pd.read_excel(BytesIO(file_bytes), sheet_name=0, header=None)
    header_row = _find_header_row(raw)
    headers = raw.iloc[header_row].tolist()
    frame = raw.iloc[header_row + 1:].copy()
    frame.columns = [_ALIASES.get(_normalised_name(column), str(column).strip()) for column in headers]
    frame = frame.dropna(how="all")
    missing = {"Date", "Amount"} - set(frame.columns)
    if missing:
        raise ValueError(f"The worksheet needs columns for: {', '.join(sorted(missing))}.")
    for column in ("Merchant", "Description"):
        if column not in frame:
            frame[column] = ""
    if "Direction" in frame:
        direction = frame["Direction"].fillna("").astype(str).str.lower()
        expense_markers = ("支出", "expense", "outflow", "debit")
        frame = frame.loc[direction.str.contains("|".join(expense_markers), regex=True)].copy()
    if frame.empty:
        raise ValueError("No expense rows were found in this statement.")
    if "Category" not in frame:
        transaction_type = frame["TransactionType"] if "TransactionType" in frame else [""] * len(frame)
        # Convert statement fields to a small set of budgeting categories. The UI
        # exposes a category-only editor so the user can correct any suggestion.
        frame["Category"] = [
            _suggest_budget_category(merchant, description, kind)
            for merchant, description, kind in zip(frame["Merchant"], frame["Description"], transaction_type)
        ]

    frame = frame.loc[:, list(REQUIRED_COLUMNS)]
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame["Amount"] = frame["Amount"].map(_currency_number)
    frame = frame.dropna(subset=["Date", "Amount"]).copy()
    if frame.empty:
        raise ValueError("No usable rows were found. Check the Date and Amount columns.")
    # Statements commonly show debits as negatives. This app treats retained expense rows as positive spending.
    frame["Amount"] = frame["Amount"].astype(float).abs().round(2)
    frame["Date"] = frame["Date"].dt.strftime("%Y-%m-%d")
    for column in ("Merchant", "Description", "Category"):
        frame[column] = frame[column].fillna("").astype(str).str.strip()
    frame.loc[frame["Category"] == "", "Category"] = "Other"

    period = _billing_period(pd.to_datetime(frame["Date"]))
    destination_dir = Path(output_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    csv_path = destination_dir / f"{period}.csv"
    frame.to_csv(csv_path, index=False)
    return ExtractionResult(str(csv_path), period, len(frame), source_filename)


def load_statement(csv_path: Path | str) -> pd.DataFrame:
    frame = pd.read_csv(csv_path)
    if tuple(frame.columns) != REQUIRED_COLUMNS:
        raise ValueError("Extracted CSV has an unexpected format.")
    frame["Date"] = pd.to_datetime(frame["Date"], errors="raise")
    frame["Amount"] = pd.to_numeric(frame["Amount"], errors="raise")
    frame["Category"] = frame["Category"].astype(str).str.strip().map(
        lambda value: _LEGACY_CATEGORY_LABELS.get(value.casefold(), value)
    )
    return frame


def available_months(frame: pd.DataFrame) -> list[str]:
    return sorted(frame["Date"].dt.strftime("%Y-%m").unique().tolist())


def _month_rows(frame: pd.DataFrame, month: str) -> pd.DataFrame:
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError("Month must use YYYY-MM.")
    return frame.loc[frame["Date"].dt.strftime("%Y-%m") == month].copy()


def spending_summary(frame: pd.DataFrame, month: str) -> dict[str, Any]:
    """Tool 2: deterministic spending total and category breakdown."""
    rows = _month_rows(frame, month)
    by_category = rows.groupby("Category")["Amount"].sum().sort_values(ascending=False).round(2)
    return {
        "month": month,
        "transaction_count": int(len(rows)),
        "total_spending": round(float(rows["Amount"].sum()), 2),
        "by_category": {category: float(amount) for category, amount in by_category.items()},
        "highest_category": by_category.index[0] if not by_category.empty else None,
        "currency": "SGD",
    }


def budget_status(summary: dict[str, Any], maximum_spending: float) -> dict[str, Any]:
    """Tool 3: compare the supplied maximum with actual spending."""
    maximum_spending = round(float(maximum_spending), 2)
    if maximum_spending <= 0:
        raise ValueError("Maximum monthly spending must be greater than zero.")
    remaining = round(maximum_spending - float(summary["total_spending"]), 2)
    return {
        "month": summary["month"], "maximum_spending": maximum_spending,
        "actual_spending": summary["total_spending"], "remaining": remaining,
        "status": "within_limit" if remaining >= 0 else "over_limit", "currency": "SGD",
    }


def query_transactions(
    frame: pd.DataFrame,
    month: str,
    category: str | None = None,
    merchant_contains: str | None = None,
    group_by: str = "transaction",
    limit: int = 10,
) -> dict[str, Any]:
    """Read-only, bounded transaction exploration for the agent.

    The model may choose filters and a grouping, but cannot supply SQL, change the
    statement, access another month, or return an unbounded raw transaction list.
    """
    if group_by not in {"transaction", "category", "merchant", "date"}:
        raise ValueError("group_by must be transaction, category, merchant, or date.")
    limit = int(limit)
    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20.")
    rows = _month_rows(frame, month)
    if category:
        normalised_category = category.strip().casefold()
        rows = rows.loc[rows["Category"].str.casefold() == normalised_category].copy()
    if merchant_contains:
        rows = rows.loc[rows["Merchant"].str.contains(merchant_contains.strip(), case=False, regex=False, na=False)].copy()

    total = round(float(rows["Amount"].sum()), 2)
    response: dict[str, Any] = {
        "month": month,
        "filters": {"category": category or None, "merchant_contains": merchant_contains or None},
        "group_by": group_by,
        "matching_transaction_count": int(len(rows)),
        "matching_spending": total,
        "currency": "SGD",
    }
    if group_by == "transaction":
        ordered = rows.sort_values(["Amount", "Date"], ascending=[False, False]).head(limit).copy()
        ordered["Date"] = ordered["Date"].dt.strftime("%Y-%m-%d")
        response["items"] = ordered[["Date", "Merchant", "Description", "Amount", "Category"]].to_dict(orient="records")
        return response

    group_column = {"category": "Category", "merchant": "Merchant", "date": "Date"}[group_by]
    grouped = rows.groupby(group_column, dropna=False).agg(spending=("Amount", "sum"), transaction_count=("Amount", "size")).reset_index()
    grouped = grouped.sort_values(["spending", group_column], ascending=[False, True]).head(limit)
    items = []
    for _, row in grouped.iterrows():
        label = row[group_column].strftime("%Y-%m-%d") if group_by == "date" else str(row[group_column])
        items.append({group_by: label, "spending": round(float(row["spending"]), 2), "transaction_count": int(row["transaction_count"])})
    response["items"] = items
    return response


def get_spending_insights(frame: pd.DataFrame, month: str, maximum_spending: float) -> dict[str, Any]:
    """Return a compact deterministic monthly overview and budget comparison."""
    summary = spending_summary(frame, month)
    budget = budget_status(summary, maximum_spending)
    rows = _month_rows(frame, month).sort_values("Amount", ascending=False).head(5).copy()
    rows["Date"] = rows["Date"].dt.strftime("%Y-%m-%d")
    category_shares = {
        category: round(amount / summary["total_spending"] * 100, 1) if summary["total_spending"] else 0.0
        for category, amount in summary["by_category"].items()
    }
    return {**summary, "budget": budget, "category_shares_percent": category_shares, "largest_transactions": rows[["Date", "Merchant", "Description", "Amount", "Category"]].to_dict(orient="records")}


def create_saving_plan(frame: pd.DataFrame, month: str, saving_target: float, protected_categories: list[str]) -> dict[str, Any]:
    """Create deterministic reductions from every type except user-protected types."""
    saving_target = round(float(saving_target), 2)
    if saving_target <= 0:
        raise ValueError("Saving target must be greater than zero.")
    protected_labels = {item.strip() for item in protected_categories if item.strip()}
    protected = {item.casefold() for item in protected_labels}
    rows = _month_rows(frame, month)
    category_totals = rows.groupby("Category")["Amount"].sum().to_dict()
    candidates = sorted(((category, float(amount)) for category, amount in category_totals.items() if category.casefold() not in protected), key=lambda item: item[1], reverse=True)
    remaining = saving_target
    recommendations = []
    for category, spending in candidates:
        if remaining <= 0 or spending <= 0:
            continue
        reduction = round(min(spending, remaining), 2)
        recommendations.append({"category": category, "reduction_amount": reduction, "category_spending": round(spending, 2)})
        remaining = round(remaining - reduction, 2)
    return {
        "month": month, "target_amount": saving_target, "protected_categories": sorted(protected_labels),
        "recommendations": recommendations, "unmet_amount": max(0.0, remaining),
        "is_achievable": remaining == 0, "currency": "SGD",
    }


def run_monthly_workflow(frame: pd.DataFrame, month: str, maximum_spending: float) -> dict[str, Any]:
    """Initial deterministic analysis; saving recommendations belong to the agent chat."""
    trace = []
    summary = spending_summary(frame, month)
    trace.append("spending_summary")
    budget = budget_status(summary, maximum_spending)
    trace.append("budget_status")
    return {"tool_trace": trace, "summary": summary, "budget": budget}


def serialise_extraction(result: ExtractionResult) -> dict[str, Any]:
    return asdict(result)
