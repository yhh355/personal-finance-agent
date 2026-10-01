# Personal Finance Statement Agent Demo Script

**Suggested duration:** 5 to 6 minutes

## 0. Opening 0:00 to 0:30

**Show:** The Streamlit landing page.

**Say:**

> Hello, this is my PE6201 end-of-course project, the Personal Finance Statement Agent. It helps a user understand an uploaded payment statement, diagnose spending patterns, and discuss possible savings without connecting to a bank account. The user uploads an XLSX statement, the app creates a transparent local CSV, and an AI agent uses controlled read-only tools to analyse it.

> The important design choice is that the language model does not calculate financial totals itself. Python performs the calculations over the uploaded statement, while the model decides what evidence to request and explains the result.

## 1. Import and extract the statement 0:30 to 1:20

**Show:** Section 1, then choose the supplied WeChat Pay XLSX file.

**Action:** Click **Extract XLSX to local CSV**.

**Say:**

> I will begin by uploading a WeChat Pay statement. Extraction is deliberately a direct data operation, not an agent tool. The application detects the transaction header after the WeChat introductory rows, keeps expense transactions, normalises the fields into Date, Merchant, Description, Amount, and Category, and saves the result as a local CSV named after its billing period.

> This choice is a privacy and transparency trade-off. It is less convenient than bank synchronisation, but the user can inspect the data that will be analysed and no bank connection is required.

**Show:** The extraction success message and the extracted statement selector.

## 2. Set constraints and inspect the data 1:20 to 2:00

**Show:** Billing month, maximum spending, saving target, and categories-to-keep controls.

**Action:** Select the relevant month. Enter a realistic maximum monthly spending, for example **S$1,800**, and a default saving target, for example **S$200**. Select any categories that should not be reduced.

**Say:**

> The user controls the constraints. The maximum spending is used for the budget comparison. The saving target is used only if the user later asks for a savings plan. Categories selected here are protected, so a savings recommendation cannot suggest reducing them.

> If necessary, the user can also open this category-review panel and correct a suggested category before analysis. This matters because a transfer may represent social spending, repayment, or something else; automatic labels should be reviewable rather than treated as facts.

**Action:** Click **Analyse statement and open chat**.

## 3. Initial deterministic analysis 2:00 to 2:35

**Show:** Section 2 and the initial assistant message.

**Say:**

> The first message is deterministic Python analysis. It reports total spending, transaction count, the largest category, category totals, and whether the user is within the selected budget. It does not automatically tell the user to cut a category, because a useful reduction recommendation needs further context.

> This separates deterministic financial facts from language-model interpretation. The user can expand the tool trace to see which local calculations produced this initial result.

## 4. Demonstrate multi-tool investigation 2:35 to 4:15

**Action:** In the chat box, enter:

> `Why did I spend so much this month? Please analyse the overall pattern and the specific transactions that caused it.`

**Show:** The response, then expand **Agent tool-call trace**.

**Say:**

> This is the agentic part of the application. For this diagnostic question, the agent first uses `get_spending_insights` to understand the monthly total, budget status, category shares, and largest transactions. It then uses `query_transactions` to inspect relevant evidence, for example by category, merchant, or date.

> The trace shows the action and the observation returned by each local tool. The observation from the first tool is sent back to the model before it chooses the next tool. Therefore, the final explanation is based on multiple pieces of evidence, rather than a single pre-written report.

> The query tool is intentionally bounded. The model cannot write arbitrary SQL, change the statement, access another month, or request an unlimited number of raw transactions. This keeps the agent more controllable and auditable.

## 5. Demonstrate a savings recommendation 4:15 to 5:15

**Action:** Enter:

> `I want to save S$200. First analyse the evidence, then give me a practical plan without reducing my protected categories.`

**Show:** The response and expand its tool-call trace.

**Say:**

> For a recommendation question, the agent investigates the statement first and then calls `create_saving_plan`. The savings calculation is deterministic: it uses the target amount and excludes the categories I selected to keep. The model's role is to connect this result with the transaction evidence and explain the recommendation in natural language.

> This is a deliberate trade-off. A fully autonomous model could produce more flexible advice, but it could also invent figures or ignore constraints. Here, every amount comes from local Python calculations and the recommendation remains a budgeting option, not professional financial advice.

## 6. Closing 5:15 to 5:45

**Show:** The three tool descriptions and, if useful, the expanded trace from the previous answer.

**Say:**

> To summarise, the project combines a simple Streamlit interface, transparent XLSX-to-CSV processing, controlled local financial calculations, and an OpenRouter-powered conversational agent. The agent can compose read-only query tools for multi-step analysis, while the application keeps transaction data local and makes the evidence visible through tool traces.

> The current limitations are that the app depends on an uploaded statement, uses a small editable category taxonomy, and does not provide bank integration or investment advice. Future work could add secure database storage, authenticated accounts, and cross-month analysis while retaining the same controlled tool layer.

## Recording checklist

- Start Streamlit and confirm the OpenRouter API key is configured before recording.
- Use a statement with non-sensitive or anonymised transaction data.
- Keep the browser zoom around 100 percent so the tool trace is readable.
- Pause briefly after each tool trace is expanded.
- Do not show the `.env` file or API key during the recording.
