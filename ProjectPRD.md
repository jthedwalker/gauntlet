Here’s a condensed “handoff spec” you can paste into Codex/Cursor. It’s the minimal, working vertical slice: **LM Studio (OpenAI-compatible)** + **uv** + **sqlite-utils** + **2 tasks** + **2 strategies** + **runs/ artifacts** + **SQLite metrics**.

---

## Project: Local Model Gauntlet (minimal vertical slice)

### Goal

A CLI that runs a small eval harness against a local LM Studio model (`liquid/lfm2.5-1.2b`) with:

* **2 tasks**: (1) JSON schema output, (2) tiny Python coding task with pytest
* **2 strategies**: baseline, critique-then-fix (retry loop)
* **Persistence**:

  * `runs/<run_id>/attempt_<n>/...` artifacts (prompt, response, logs)
  * `results.sqlite` metrics via **sqlite-utils**
* No scheduling, no n8n.

---

## Assumptions

* LM Studio is running an OpenAI-compatible server at something like:

 [LM STUDIO SERVER] Supported endpoints:
 [LM STUDIO SERVER] ->	GET  http://localhost:1234/v1/models
 [LM STUDIO SERVER] ->	POST http://localhost:1234/v1/responses
 [LM STUDIO SERVER] ->	POST http://localhost:1234/v1/chat/completions
 [LM STUDIO SERVER] ->	POST http://localhost:1234/v1/completions
 [LM STUDIO SERVER] ->	POST http://localhost:1234/v1/embeddings
* whatever LM Studio expects; keep configurable

---

## Stack

* Python 3.11+ with **uv**
* deps: `httpx`, `pydantic`, `sqlite-utils`, `pytest`
* optional nice-to-have: `rich` (logs)

---

## Repo layout

```
gauntlet/
  providers/lmstudio.py
  tasks/json_schema_task.py
  tasks/pyfunc_task.py
  strategies/baseline.py
  strategies/critique_fix.py
  runner.py
  db.py
  report.py
runs/
results.sqlite
pyproject.toml
```

---

## Setup commands (uv)

* `uv init` (or create pyproject manually)
* `uv add httpx pydantic sqlite-utils pytest`
* `uv run python -m gauntlet.runner --model liquid/lfm2.5-1.2b`

---

## Config (CLI args)

Minimum CLI args:

* `--base-url http://localhost:1234/v1`
* `--model liquid/lfm2.5-1.2b`
* `--max-attempts 3`
* `--run-id` optional (else auto timestamp)
* `--tasks json,pyfunc` optional
* `--strategies baseline,critique_fix` optional
* `--timeout 120` seconds

---

## Provider: LM Studio client (OpenAI-compatible)

Implement a thin wrapper using `httpx`:

* POST `{base_url}/chat/completions`
* Body:

  * `model`
  * `messages`: list of `{role, content}`
  * `temperature` (0–0.3)
  * `max_tokens` (e.g., 1024–2048)
* Parse `choices[0].message.content` (text only; no tool calls required for v1).
* Return: `text`, raw JSON, latency, token usage if present.

---

## Tasks (mechanical eval)

### Task 1: JSON schema compliance

Prompt: “Return ONLY valid JSON matching this schema…”
Schema (Pydantic):

```python
class Person(pydantic.BaseModel):
    name: str
    age: int
    city: str
```

Evaluation:

* Extract response text
* Attempt `json.loads`
* Attempt `Person.model_validate(...)`
  Score:
* `pass=1` if validates else `0`
* also record `error_type` (json_parse_error, schema_error)

### Task 2: Python function with pytest

Provide prompt asking for a function only:

* Function name: `normalize_phone(s: str) -> str`
* Requirements:

  * strip non-digits
  * if 10 digits: format `AAA-BBB-CCCC`
  * if 11 digits and starts with `1`: drop leading 1 then format
  * otherwise raise `ValueError`
    Evaluation (mechanical):
* Create temp workspace in `runs/<run_id>/attempt_<n>/pyfunc/`
* Write `solution.py` with model output (wrap if needed)
* Write `test_solution.py` with tests
* Run `pytest -q` as subprocess
  Score:
* pass if exit code 0
* record stderr/stdout and failing tests

Important: enforce response constraints:

* If model includes explanations, try to extract code block; if none, wrap content into a function stub or mark fail.

---

## Strategies (mutation/retry)

### Strategy A: baseline

One-shot:

* system: “You are a precise coding assistant. Follow instructions exactly.”
* user: task prompt

### Strategy B: critique-then-fix

Two-step per attempt (or single retry step):

* Step 1: run baseline prompt
* If eval fails:

  * send a second prompt including:

    * original prompt
    * the model’s previous output
    * the evaluator failure message (pytest failure output or schema errors)
  * instruction: “Return ONLY corrected output. No commentary.”
    This is the “mutation after failure.”

---

## Runner logic

Nested loops:

* for each (task × strategy):

  * attempts up to `max_attempts`
  * run provider call
  * evaluate
  * persist artifacts + DB row
  * if success: stop attempts for that (task,strategy)
  * else: if strategy supports mutation, feed failure back and retry

Hard limits:

* timeout per call
* max_attempts
* write all outputs even on failure

Artifacts per attempt:

* `prompt.json` (messages)
* `response.txt`
* `raw.json` (full API response)
* `eval.json` (score, errors)
* `pytest_stdout.txt` / `pytest_stderr.txt` when relevant

---

## SQLite schema (sqlite-utils)

`runs` table:

* `run_id` (pk)
* `started_at`, `model`, `base_url`, `git_commit` optional

`attempts` table:

* `id` (pk autoinc)
* `run_id` (fk)
* `task_name`
* `strategy_name`
* `attempt_num`
* `success` (0/1)
* `score` (float)
* `latency_ms`
* `error_type` (nullable)
* `artifact_dir` (string path)
* `created_at`

Optional `metrics` table later; not needed now.

---

## Report output

After run, generate:

* `report.md` summarizing:

  * pass rate per task/strategy
  * attempts-to-success
  * avg latency
* `results.csv` export of `attempts` table

---

## Done definition (minimal working)

Running:
`uv run python -m gauntlet.runner --base-url http://localhost:1234/v1 --model liquid/lfm2.5-1.2b --max-attempts 3`

Produces:

* populated `results.sqlite`
* a `runs/<run_id>/...` folder with prompts/responses/evals
* `report.md` + `results.csv`

---