# Gauntlet Run Report

## Run Information

- **Run ID**: 20260113_221230
- **Started**: 2026-01-13T22:12:30.967949
- **Model**: liquid/lfm2.5-1.2b
- **Base URL**: http://localhost:1234/v1

## Summary

### Pass Rate by Task

| Task | Pass Rate |
|------|-----------|
| json_schema | 100% (2/2) |
| pyfunc | 0% (0/2) |

### Pass Rate by Strategy

| Strategy | Pass Rate |
|----------|-----------|
| baseline | 50% (1/2) |
| critique_fix | 50% (1/2) |

### Detailed Results

| Task | Strategy | Status | Attempts to Success | Latency (ms) |
|------|----------|--------|---------------------|--------------|
| json_schema | baseline | PASS | 1/1 | 2278 |
| json_schema | critique_fix | PASS | 1/1 | 260 |
| pyfunc | baseline | FAIL | 1/1 | 1076 |
| pyfunc | critique_fix | FAIL | 3/3 | 3463 |

## Statistics

- **Total Attempts**: 6
- **Total Latency**: 7077ms
- **Average Latency per Attempt**: 1179ms
