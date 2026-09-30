# Personal Finance Statement Agent

A Streamlit course-demo app for a simple, transparent finance workflow:

```text
Upload XLSX statement
  -> direct XLSX-to-CSV import
  -> data/statements/<billing-period>.csv
  -> deterministic initial summary + an agent that can query the local statement
```

## Inputs

1. An `.xlsx` statement. Its first worksheet needs `Date` and `Amount` columns. `Merchant`, `Description`, and `Category` are optional.
2. Your maximum monthly spending in SGD.
3. Your saving target in SGD.
4. The budget categories you want to keep. The saving tool will exclude these categories and analyse all other spending for possible reductions.

The extraction tool normalises the worksheet into `Date, Merchant, Description, Amount, Category` and saves it under `data/statements/`. A single-month statement becomes `YYYY-MM.csv`; a multi-month statement becomes `YYYY-MM_to_YYYY-MM.csv`.

WeChat Pay XLSX exports are supported: the extractor finds their Chinese transaction header after the introductory rows, maps `交易时间`, `交易对方`, `商品`, `收/支`, and `金额(元)`, and retains only `支出` rows. It suggests one of seven budgeting categories: `生活`, `餐饮`, `交通`, `娱乐`, `购物`, `生活娱乐`, or `其他`. Review and correct the suggestions in the UI before analysis.

## Data import

`extract_xlsx_statement` is a direct Streamlit data operation, not an agent or analysis tool. It runs only when a user uploads an XLSX file and clicks **Extract XLSX to CSV**.

## Agent analysis tools

- `query_transactions`: a bounded, read-only query over the selected month. The agent can filter by category or merchant text and group the result by transaction, category, merchant, or date.
- `get_spending_insights`: deterministic total, category shares, largest transactions, and monthly budget status.
- `create_saving_plan`: deterministic reductions for the saving target, excluding categories you marked to keep.

This is deliberately a composable data-agent design: the model decides which tool to call and can make several bounded queries before answering. It cannot supply arbitrary SQL, write to a statement, access another month, or request more than 20 items from one query.

All arithmetic is deterministic Python. Streamlit invokes the extraction tool after an upload and runs the multi-tool analysis workflow after you provide the three finance inputs. This avoids using an LLM to parse or alter a financial statement.

## OpenRouter agent

To use a real agent, copy `.env.example` to `.env`, set `OPENROUTER_API_KEY`, restart Streamlit, and use the chat at the bottom of the page. The model decides which local analysis tool is useful, Python executes it against the extracted CSV, and the model writes the final explanation. The XLSX import function is never exposed as an agent tool.

```powershell
Copy-Item .env.example .env
# Edit .env and set OPENROUTER_API_KEY
```

## Run

```powershell
cd C:\Users\ROG\personal-finance-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

## Test

```powershell
pytest
```

## Limitations

- The app treats all retained statement amounts as expenses by absolute value. Review the extracted CSV before using a statement that includes refunds, income, or transfers.
- It stores only local CSV files and does not connect to a bank.
- Recommendations are budgeting information, not professional financial advice.
