# Demo Data

`demo_statement.xlsx` is the public dataset for the repository, tests, evaluation, and video demonstration. It is synthetic: merchant names, descriptions, amounts, and transactions are fictional. It contains no bank account number, wallet identifier, personal name, or real payment record.

The worksheet imitates the layout of a WeChat Pay export. It contains introductory rows, Chinese transaction headers, 19 September 2026 expense rows, and one income row. The income row exists to demonstrate that the extractor retains only `支出` rows.

After extraction, the expected expense total is **S$1,509.98**. The largest suggested category is **Lifestyle and Social** at **S$650.00**. These fixed values make the deterministic offline evaluation reproducible.

Real uploaded statements are stored only in `data/statements/` on the local machine and are excluded by `.gitignore`.
