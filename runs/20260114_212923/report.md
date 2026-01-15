# Gauntlet Run Report

## Run Information

- **Run ID**: 20260114_212923
- **Started**: 2026-01-14T21:29:23.457600
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
| json_schema | baseline | PASS | 1/1 | 2326 |
| json_schema | critique_fix | PASS | 1/1 | 247 |
| pyfunc | baseline | FAIL | 1/1 | 1044 |
| pyfunc | critique_fix | FAIL | 3/3 | 3201 |

## Statistics

- **Total Attempts**: 6
- **Total Latency**: 6818ms
- **Average Latency per Attempt**: 1136ms
