# Evals Assets

This directory stores CI-friendly evaluation and demo data.

- `golden/golden_v1.json`: default regression dataset used by `make eval`
- `golden/golden_minimal.json`: minimal local smoke dataset
- `demo_documents/`: minimal txt/markdown files for manual upload/index/chat flow
- `cases/`: reserved for custom case templates
- `reports/`: reserved output folder for exported reports

Run eval from backend root:

```bash
python -m app.evals.cli --dataset golden_v1 --name local-eval
python -m app.evals.cli --dataset golden_minimal --name smoke-eval
```
