# Personal Finance Statement Agent Demo Script

Target duration: 5 to 7 minutes. Keep your face visible in a small webcam frame and share the Streamlit application window. Use `data/demo_statement.xlsx`; do not show `.env`, an API key, or a real statement.

## 0:00 to 0:30 Introduction

Hello, this is my PE6201 end-of-course project, the Personal Finance Statement Agent.

The goal is to help a student or early-career user understand an uploaded payment statement, identify spending patterns, and discuss possible saving actions. The system does not connect to a bank account. Instead, the user uploads an XLSX statement, the application creates a transparent local CSV file, and an OpenRouter-powered Agent investigates the data through controlled local tools.

## 0:30 to 1:20 Upload and local extraction

I will use this synthetic WeChat-style statement for the demonstration. It contains no real personal data.

I upload `demo_statement.xlsx` and click **Extract XLSX to local CSV**. The extractor detects the transaction table even when a WeChat export contains introductory rows before the headers. It retains only expense transactions and standardises the data into Date, Merchant, Description, Amount, and Category.

The result is stored locally as a CSV named after the billing period. This is a deliberate design choice. Bank synchronisation would be more convenient, but local upload makes the data flow visible and avoids requesting access to a financial account.

## 1:20 to 2:15 Constraints and initial analysis

I select September 2026 as the billing month. I set the maximum spending to S$1,800 and the default saving target to S$200.

I choose **Food and Dining** and **Transport** under **Categories to keep**. These protected categories must not appear in a later saving recommendation.

Before analysing, the category-review panel lets the user correct ambiguous categories. This matters because a transfer or merchant description may not always reveal the true purpose of a payment.

Now I click **Analyse statement and open chat**. The initial summary is deterministic Python output, not an LLM estimate. It reports total spending, category totals, the highest category, and the status against the S$1,800 budget. At this stage, it deliberately does not recommend reductions.

## 2:15 to 4:20 Multi-step Agent demonstration

In the chat, I enter this question:

> I want to save S$200 this month. First analyse the overall spending pattern and inspect transaction evidence. Then create a practical plan without reducing Food and Dining or Transport.

The Agent now performs a ReAct-style action-observation loop. It does not calculate directly from the prompt.

First, it calls `get_spending_insights`. Python calculates the month total, category shares, budget status, and the largest transactions. The result becomes an observation for the model.

Second, the Agent calls `query_transactions` to investigate supporting transaction evidence. This tool is read-only and bounded: the model cannot edit the CSV, access another month, write arbitrary SQL, or request unlimited transactions.

Finally, for a saving request, it calls `create_saving_plan`. Python calculates the reduction plan and excludes Food and Dining and Transport because I selected them as categories to keep.

I expand **Agent tool-call trace** to show each tool name, arguments, and JSON observation. This demonstrates that the final response is based on evidence collected step by step, rather than an unsupported answer from the original prompt.

## 4:20 to 5:20 Reliability and evaluation

The responsibility split is important. The language model decides how to investigate and explains the result in natural language. Python performs the extraction, filtering, grouping, totals, budget comparison, and saving calculation. This keeps financial amounts reproducible and makes the process easier to audit.

The repository includes synthetic data, offline evaluation cases, and unit tests. The deterministic offline evaluation passed 4 out of 4 cases. I also ran a live evaluation of ten multi-step prompts with `openai/gpt-4.1-mini` through OpenRouter. Nine out of ten cases achieved the required tool coverage, or 90 percent, in that run.

This is not a claim that the Agent is always correct. The metric checks whether the required tools appeared in the trace; it does not fully measure answer quality or every possible user prompt.

## 5:20 to 6:00 Limitations and conclusion

The current limitations are manual statement upload, categories that may need user correction, analysis of one selected month at a time, and no bank integration, investment advice, or long-term planning.

In conclusion, this project combines a Streamlit interface, local XLSX-to-CSV extraction, deterministic finance tools, and an OpenRouter Agent. The user controls the statement and constraints, while the Agent provides a transparent multi-step analysis based on tool observations. Thank you.

## Recording checklist

- Your face and the application screen are visible throughout.
- Use the synthetic `data/demo_statement.xlsx` only.
- Show upload, extraction, constraints, initial analysis, one chat request, and the expanded tool trace.
- Do not reveal `.env`, API keys, terminal history containing keys, or personal data.
- Keep the final video between 5 and 8 minutes.
