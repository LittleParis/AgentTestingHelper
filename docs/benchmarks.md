# Benchmark Set

This repository ships with three stable benchmark cases for resume demos and CI smoke checks.

For an interview-ready evidence page with command examples, artifact snippets, and a real screenshot, see `docs/demo_run.md`.

## Cases

- `login-success`: bounded login flow with runtime credential injection and a fixed success signal.
- `form-validation`: invalid form submission with field-level validation assertions.
- `list-search`: search/list flow with deterministic result assertions.

## Usage

```bash
python main_v2.py demo --demo-case login-success --no-ui
python main_v2.py demo --demo-case list-search --output-dir output/runs
```

Each run writes a stable artifact contract under `output/runs/<run_id>/`:

- `requirements.json`
- `test_strategy.json`
- `test_cases.json`
- `review.json`
- `script_plan.json`
- `execution.json`
- `run_summary.json`
- `run_manifest.json`
