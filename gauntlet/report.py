"""Report generation for gauntlet runs."""

import csv
from collections import defaultdict
from pathlib import Path

from .db import get_attempts, get_db, get_run


def generate_report(
    db_path: str,
    run_id: str,
    output_dir: Path,
) -> None:
    """
    Generate a markdown report and CSV export for a run.
    
    Args:
        db_path: Path to the SQLite database
        run_id: The run ID to report on
        output_dir: Directory to write report files
    """
    db = get_db(db_path)
    
    # Get run info
    run_info = get_run(db, run_id)
    if not run_info:
        raise ValueError(f"Run {run_id} not found")
    
    # Get all attempts for this run
    attempts = get_attempts(db, run_id)
    
    if not attempts:
        raise ValueError(f"No attempts found for run {run_id}")
    
    # Calculate metrics
    metrics = calculate_metrics(attempts)
    
    # Generate markdown report
    report_content = generate_markdown(run_info, attempts, metrics)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.md").write_text(report_content)
    
    # Export CSV
    export_csv(attempts, output_dir / "results.csv")


def calculate_metrics(attempts: list[dict]) -> dict:
    """Calculate summary metrics from attempts."""
    
    # Group by task/strategy
    by_task_strategy: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for attempt in attempts:
        key = (attempt["task_name"], attempt["strategy_name"])
        by_task_strategy[key].append(attempt)
    
    metrics = {
        "by_task_strategy": {},
        "by_task": defaultdict(lambda: {"pass": 0, "total": 0}),
        "by_strategy": defaultdict(lambda: {"pass": 0, "total": 0}),
        "total_latency_ms": 0,
        "total_attempts": len(attempts),
    }
    
    for (task, strategy), task_attempts in by_task_strategy.items():
        # Sort by attempt number
        task_attempts.sort(key=lambda x: x["attempt_num"])
        
        # Check if any attempt succeeded
        passed = any(a["success"] for a in task_attempts)
        
        # Attempts to success (or total if failed)
        if passed:
            attempts_to_success = next(
                i + 1 for i, a in enumerate(task_attempts) if a["success"]
            )
        else:
            attempts_to_success = len(task_attempts)
        
        # Total latency for this task/strategy
        total_latency = sum(a["latency_ms"] for a in task_attempts)
        
        metrics["by_task_strategy"][(task, strategy)] = {
            "passed": passed,
            "attempts_to_success": attempts_to_success,
            "total_attempts": len(task_attempts),
            "latency_ms": total_latency,
        }
        
        # Aggregate by task
        if passed:
            metrics["by_task"][task]["pass"] += 1
        metrics["by_task"][task]["total"] += 1
        
        # Aggregate by strategy
        if passed:
            metrics["by_strategy"][strategy]["pass"] += 1
        metrics["by_strategy"][strategy]["total"] += 1
        
        metrics["total_latency_ms"] += total_latency
    
    return metrics


def generate_markdown(
    run_info: dict,
    attempts: list[dict],
    metrics: dict,
) -> str:
    """Generate a markdown report."""
    
    lines = [
        f"# Gauntlet Run Report",
        "",
        f"## Run Information",
        "",
        f"- **Run ID**: {run_info['run_id']}",
        f"- **Started**: {run_info['started_at']}",
        f"- **Model**: {run_info['model']}",
        f"- **Base URL**: {run_info['base_url']}",
    ]
    
    if run_info.get("git_commit"):
        lines.append(f"- **Git Commit**: {run_info['git_commit']}")
    
    lines.extend([
        "",
        "## Summary",
        "",
        "### Pass Rate by Task",
        "",
        "| Task | Pass Rate |",
        "|------|-----------|",
    ])
    
    for task, stats in sorted(metrics["by_task"].items()):
        rate = stats["pass"] / stats["total"] * 100 if stats["total"] > 0 else 0
        lines.append(f"| {task} | {rate:.0f}% ({stats['pass']}/{stats['total']}) |")
    
    lines.extend([
        "",
        "### Pass Rate by Strategy",
        "",
        "| Strategy | Pass Rate |",
        "|----------|-----------|",
    ])
    
    for strategy, stats in sorted(metrics["by_strategy"].items()):
        rate = stats["pass"] / stats["total"] * 100 if stats["total"] > 0 else 0
        lines.append(f"| {strategy} | {rate:.0f}% ({stats['pass']}/{stats['total']}) |")
    
    lines.extend([
        "",
        "### Detailed Results",
        "",
        "| Task | Strategy | Status | Attempts to Success | Latency (ms) |",
        "|------|----------|--------|---------------------|--------------|",
    ])
    
    for (task, strategy), stats in sorted(metrics["by_task_strategy"].items()):
        status = "PASS" if stats["passed"] else "FAIL"
        lines.append(
            f"| {task} | {strategy} | {status} | "
            f"{stats['attempts_to_success']}/{stats['total_attempts']} | "
            f"{stats['latency_ms']:.0f} |"
        )
    
    lines.extend([
        "",
        "## Statistics",
        "",
        f"- **Total Attempts**: {metrics['total_attempts']}",
        f"- **Total Latency**: {metrics['total_latency_ms']:.0f}ms",
        f"- **Average Latency per Attempt**: {metrics['total_latency_ms'] / metrics['total_attempts']:.0f}ms" if metrics['total_attempts'] > 0 else "- **Average Latency**: N/A",
        "",
    ])
    
    return "\n".join(lines)


def export_csv(attempts: list[dict], output_path: Path) -> None:
    """Export attempts to CSV."""
    
    if not attempts:
        return
    
    fieldnames = [
        "run_id",
        "task_name",
        "strategy_name",
        "attempt_num",
        "success",
        "score",
        "latency_ms",
        "error_type",
        "artifact_dir",
        "created_at",
    ]
    
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(attempts)
