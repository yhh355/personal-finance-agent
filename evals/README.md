# Evaluation

The repository separates deterministic offline evaluation from optional live Agent evaluation.

## Offline evaluation

Run:

```powershell
python eval.py --mode offline
```

The offline suite uses `data/demo_statement.xlsx` and checks four reproducible behaviours: monthly insights, bounded transaction querying, protected-category saving plans, and the availability of the three-tool workflow. It does not call OpenRouter and does not incur API cost.

## Live evaluation

Run only after configuring `OPENROUTER_API_KEY` in `.env`:

```powershell
python eval.py --mode live
```

The live suite asks two multi-step questions and checks whether required tools appear in the Agent trace. It measures tool-coverage success, not subjective writing quality. Results can vary by model and prompt; live metrics must be reported with the model name and run date rather than copied from offline results.

## Metric definitions

- **Offline case pass rate:** offline cases whose expected deterministic values match exactly, divided by all offline cases.
- **Required-tool coverage:** live cases whose trace contains every required tool, divided by all live cases.
- **Tool calls per response:** number of returned trace entries. The current Agent requires at least two observations before it can finalise a response.

`offline_results.json` is the version-controlled baseline. It records the expected result of the checked-in synthetic dataset. Do not replace it with a live result.
