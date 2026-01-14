"""Main runner CLI for the gauntlet."""

import argparse
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .db import init_db, insert_attempt, insert_run
from .providers.lmstudio import LMStudioClient
from .report import generate_report
from .strategies.base import Strategy
from .strategies.baseline import BaselineStrategy
from .strategies.critique_fix import CritiqueFixStrategy
from .tasks.base import Task
from .tasks.json_schema_task import JSONSchemaTask
from .tasks.pyfunc_task import PyFuncTask

console = Console()

# Registry of available tasks and strategies
TASKS: dict[str, type[Task]] = {
    "json": JSONSchemaTask,
    "pyfunc": PyFuncTask,
}

STRATEGIES: dict[str, type[Strategy]] = {
    "baseline": BaselineStrategy,
    "critique_fix": CritiqueFixStrategy,
}


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run eval gauntlet against local LM Studio model",
    )
    
    parser.add_argument(
        "--base-url",
        default="http://localhost:1234/v1",
        help="LM Studio API base URL (default: http://localhost:1234/v1)",
    )
    parser.add_argument(
        "--model",
        default="liquid/lfm2.5-1.2b",
        help="Model identifier (default: liquid/lfm2.5-1.2b)",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Maximum attempts per task/strategy (default: 3)",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run identifier (default: auto-generated timestamp)",
    )
    parser.add_argument(
        "--tasks",
        default="json,pyfunc",
        help="Comma-separated list of tasks (default: json,pyfunc)",
    )
    parser.add_argument(
        "--strategies",
        default="baseline,critique_fix",
        help="Comma-separated list of strategies (default: baseline,critique_fix)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="API timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--db-path",
        default="results.sqlite",
        help="Path to SQLite database (default: results.sqlite)",
    )
    
    return parser.parse_args()


def main() -> None:
    """Main entry point for the gauntlet runner."""
    args = parse_args()
    
    # Generate run_id if not provided
    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    
    console.print(f"\n[bold blue]Local Model Gauntlet[/bold blue]")
    console.print(f"Run ID: {run_id}")
    console.print(f"Model: {args.model}")
    console.print(f"Base URL: {args.base_url}")
    console.print()
    
    # Initialize database
    db = init_db(args.db_path)
    insert_run(db, run_id, args.model, args.base_url)
    
    # Create runs directory
    runs_dir = Path("runs") / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse task and strategy lists
    task_names = [t.strip() for t in args.tasks.split(",")]
    strategy_names = [s.strip() for s in args.strategies.split(",")]
    
    # Validate task and strategy names
    for name in task_names:
        if name not in TASKS:
            console.print(f"[red]Unknown task: {name}[/red]")
            console.print(f"Available tasks: {', '.join(TASKS.keys())}")
            return
    
    for name in strategy_names:
        if name not in STRATEGIES:
            console.print(f"[red]Unknown strategy: {name}[/red]")
            console.print(f"Available strategies: {', '.join(STRATEGIES.keys())}")
            return
    
    # Initialize client
    with LMStudioClient(
        base_url=args.base_url,
        model=args.model,
        timeout=args.timeout,
    ) as client:
        # Results table for summary
        results_table = Table(title="Results")
        results_table.add_column("Task", style="cyan")
        results_table.add_column("Strategy", style="magenta")
        results_table.add_column("Status", style="green")
        results_table.add_column("Attempts", style="yellow")
        results_table.add_column("Latency (ms)", style="blue")
        
        # Run each task × strategy combination
        for task_name in task_names:
            task = TASKS[task_name]()
            
            for strategy_name in strategy_names:
                strategy = STRATEGIES[strategy_name]()
                
                console.print(
                    f"[bold]Running:[/bold] {task.name} × {strategy.name}"
                )
                
                # Create artifact directory for this combination
                artifact_dir = runs_dir / f"{task.name}_{strategy.name}"
                
                # Determine max_attempts based on strategy
                max_attempts = args.max_attempts if strategy.supports_retry else 1
                
                try:
                    # Execute strategy
                    result = strategy.execute(
                        client=client,
                        task=task,
                        artifact_dir=artifact_dir,
                        max_attempts=max_attempts,
                    )
                    
                    # Insert attempt records
                    for attempt in result.attempts:
                        insert_attempt(
                            db=db,
                            run_id=run_id,
                            task_name=task.name,
                            strategy_name=strategy.name,
                            attempt_num=attempt.attempt_num,
                            success=attempt.eval_result.success,
                            score=attempt.eval_result.score,
                            latency_ms=attempt.response.latency_ms,
                            artifact_dir=str(artifact_dir / f"attempt_{attempt.attempt_num}"),
                            error_type=attempt.eval_result.error_type,
                        )
                    
                    # Add to results table
                    status = "[green]PASS[/green]" if result.success else "[red]FAIL[/red]"
                    results_table.add_row(
                        task.name,
                        strategy.name,
                        status,
                        str(len(result.attempts)),
                        f"{result.total_latency_ms:.0f}",
                    )
                    
                    if result.success:
                        console.print(
                            f"  [green]PASS[/green] "
                            f"(attempts: {len(result.attempts)}, "
                            f"latency: {result.total_latency_ms:.0f}ms)"
                        )
                    else:
                        console.print(
                            f"  [red]FAIL[/red] "
                            f"(attempts: {len(result.attempts)}, "
                            f"error: {result.error_type})"
                        )
                        
                except Exception as e:
                    console.print(f"  [red]ERROR: {e}[/red]")
                    results_table.add_row(
                        task.name,
                        strategy.name,
                        "[red]ERROR[/red]",
                        "-",
                        "-",
                    )
                
                console.print()
        
        # Print summary table
        console.print()
        console.print(results_table)
    
    # Generate report
    console.print("\n[bold]Generating report...[/bold]")
    generate_report(args.db_path, run_id, runs_dir)
    console.print(f"[green]Report saved to {runs_dir / 'report.md'}[/green]")
    console.print(f"[green]CSV saved to {runs_dir / 'results.csv'}[/green]")


if __name__ == "__main__":
    main()
