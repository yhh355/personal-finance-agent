# Personal Finance Statement Agent Final Report

## Problem and project outcome

Many students and early-career adults receive payment statements but do not have the time or spreadsheet skills to translate dozens of transactions into practical budgeting decisions. Existing budgeting applications can require bank access, manual categorisation, or persistent personal-data storage. This project explores a narrower alternative: a user uploads a payment-statement XLSX file, reviews a transparent local CSV extraction, sets a spending limit and protected categories, then asks a conversational Agent to investigate spending and discuss a saving target.

The final outcome is a working Streamlit application with local XLSX-to-CSV extraction, deterministic financial calculations, and an OpenRouter-powered tool-calling Agent. The app can answer summary, diagnosis, and saving-plan questions while showing a tool-call trace. It does not connect to a bank, make investment decisions, or change a statement. The practical difference from a normal spreadsheet is that the user can ask a high-level question such as “Why did I spend so much?” and the Agent can obtain an overview, inspect selected transaction evidence, and explain a constrained answer without the user manually creating pivot tables.

## Design reasoning and trade-offs

The key design decision was to separate financial computation from language generation. Python performs XLSX extraction, filtering, grouping, sums, budget comparison, and saving-plan calculations. The language model receives structured tool observations, selects the next useful tool, and writes the explanation. This is more work than prompting a model with a whole statement, but it addresses a central reliability problem: totals and budget remaining should be reproducible whenever the CSV is unchanged.

The tool design evolved during development. Early tools were fixed report buttons, such as a total-spending report and a special lifestyle-and-entertainment detail report. They worked, but the conversation felt mechanical because a user’s question could only trigger a pre-defined output. The final design uses three composable functions: `get_spending_insights` for a deterministic monthly overview, `query_transactions` for bounded filtering and grouping, and `create_saving_plan` for user-constrained reductions. This lets the Agent combine overall evidence, a focused query, and a recommendation in one response.

I deliberately did not expose arbitrary SQL or Python execution to the model. A fully flexible database Agent would support more questions, but it would also complicate security, testing, and explanation. `query_transactions` is read-only, limited to the selected month, supports a small set of filters and groupings, and returns at most 20 items. The model therefore has meaningful analytical freedom without being able to modify the CSV, access a different statement, or return unlimited personal transaction text.

The other major trade-off is convenience versus privacy. Direct bank synchronisation would make the product more useful over time, but it would require authentication, consent, secure storage, and a substantially larger compliance scope. The MVP uses a user-initiated upload and stores extracted statements locally. It also includes a category-review control because merchant text is ambiguous. A transfer, for example, may be a social activity, repayment, or something else. The cost is additional user effort; the benefit is that the user can see and correct the information before it affects the analysis.

## Evaluation and performance critique

The repository includes a synthetic, version-controlled WeChat-style statement with 19 expense rows and one income row. No real personal data is checked in. The income row tests that the extractor retains only expense records. The expected extracted spending total is S$1,509.98, and the largest category is Lifestyle and Social at S$650.00.

I implemented an offline evaluation suite with four deterministic cases. It tests monthly insights, bounded merchant aggregation, protected-category saving plans, and availability of the intended three-tool workflow. Running `python eval.py --mode offline` produced 4/4 passing cases, or a 100% offline case pass rate. The repository also contains seven unit tests covering XLSX extraction, WeChat headers, financial calculations, protected-category exclusion, Agent tool schemas, and the offline evaluation. The latest local run passed 7/7 tests.

These results demonstrate deterministic correctness for the checked-in dataset, but they are not sufficient evidence that the language model is always correct. In particular, they do not measure whether an OpenRouter model consistently chooses the best tools, explains results well, or handles every phrasing of a question. Live Agent evaluation is implemented separately because it requires an API key, uses paid requests, and can vary by chosen model. The live suite measures required-tool coverage for a diagnostic prompt and a protected-savings prompt. I intentionally do not claim a live accuracy number before running it with the final model configuration.

The Agent loop is tuned for demonstration of evidence gathering rather than minimum latency. It requires at least two tool observations before the final answer. This prevents the model from answering a complex diagnostic question after seeing only one aggregate. The drawback is extra model turns, response time, and token cost even for simple questions. A production version should classify question complexity or allow the user to choose a fast one-tool mode. The current choice is reasonable for the course objective because the tool trace makes the action-observation loop visible and auditable.

## Difficulties and rough edges

The main engineering difficulty was balancing “agentic” behaviour with financial control. If Python forces every tool sequence, the model appears scripted. If the model has unrestricted freedom, it may stop after one shallow query or choose an irrelevant function. The compromise is that the model selects tools and arguments, while the orchestration loop requires two complementary observations and the functions impose clear limits.

Another difficulty was category migration. The original WeChat-oriented labels were Chinese, while the course demo and documentation need an English interface. Converting only the display labels created a mismatch between lowercase CSV values and title-case editor options. The final implementation normalises legacy Chinese and lowercase English values to one canonical English form, so existing local CSV files remain usable and protected-category matching is case-insensitive.

The most visible rough edge is that the current tool set only analyses one selected month. It cannot yet compare months, learn a user’s changing preferences across sessions, identify subscriptions reliably, or explain the true purpose of an ambiguous transfer. The model also receives tool observations through OpenRouter, so a real user should understand that selected transaction details are included in those requests. The public demo avoids this risk by using only synthetic data.

## Future path

The next development step would be safe cross-month analysis using multiple locally selected CSV files, followed by recurring-spending detection and user-approved category rules. A production version could use encrypted database storage, authenticated accounts, and a clear retention policy. It should retain deterministic calculation tools and bounded query parameters rather than replacing them with an LLM-only approach. Evaluation should expand to paraphrased prompts, category-correction accuracy, live tool-coverage measurements, answer-quality review, latency, and API cost.

## Conclusion

The project demonstrates that a small personal-finance Agent can be useful without pretending to be a complete banking platform. Its main contribution is a transparent division of responsibility: the user controls the statement and constraints, Python controls financial arithmetic and data access, and the model controls conversational investigation and explanation. The result is narrower than a commercial app, but it is privacy-conscious, reproducible on synthetic data, and suitable for an auditable course demonstration.
