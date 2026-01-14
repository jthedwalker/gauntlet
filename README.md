# Local Model Gauntlet

A CLI eval harness for testing local LM Studio models with structured tasks and evaluation strategies.

## Features

- **2 Tasks**: JSON schema compliance and Python function generation with pytest evaluation
- **2 Strategies**: Baseline (one-shot) and critique-then-fix (retry with feedback)
- **Persistence**: SQLite database for metrics + artifact directories for all prompts/responses
- **Reporting**: Markdown reports and CSV exports

## Installation

```bash
uv sync
```

## Usage

```bash
uv run python -m gauntlet.runner --base-url http://localhost:1234/v1 --model liquid/lfm2.5-1.2b --max-attempts 3
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--base-url` | `http://localhost:1234/v1` | LM Studio API base URL |
| `--model` | `liquid/lfm2.5-1.2b` | Model identifier |
| `--max-attempts` | `3` | Maximum attempts per task/strategy |
| `--run-id` | auto timestamp | Run identifier |
| `--tasks` | `json,pyfunc` | Comma-separated task list |
| `--strategies` | `baseline,critique_fix` | Comma-separated strategy list |
| `--timeout` | `120` | API timeout in seconds |
| `--db-path` | `results.sqlite` | SQLite database path |

## Output

After a run, you'll find:

- `results.sqlite` - SQLite database with runs and attempts tables
- `runs/<run_id>/` - Artifacts directory containing:
  - `report.md` - Summary report
  - `results.csv` - CSV export of attempts
  - `<task>_<strategy>/attempt_<n>/` - Per-attempt artifacts:
    - `prompt.json` - The prompt sent to the model
    - `response.txt` - The model's response
    - `raw.json` - Full API response
    - `eval.json` - Evaluation results
    - `pytest_stdout.txt` / `pytest_stderr.txt` - For pyfunc task

## Tasks

### JSON Schema Task
Tests the model's ability to generate valid JSON matching a Pydantic schema.

### Python Function Task
Tests code generation by asking the model to implement a `normalize_phone()` function, then running pytest against the generated code.

## Strategies

### Baseline
Single-shot execution - one prompt, one response, evaluate.

### Critique-Fix
On failure, sends a follow-up prompt with the original task, the model's output, and the error message, asking for a corrected response. Retries up to max_attempts.

## Requirements

- Python 3.11+
- LM Studio running with an OpenAI-compatible endpoint
