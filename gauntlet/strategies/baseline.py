"""Baseline one-shot execution strategy."""

import json
from pathlib import Path

from ..providers.lmstudio import LMStudioClient
from ..tasks.base import Task
from .base import AttemptResult, Strategy, StrategyResult


class BaselineStrategy(Strategy):
    """Simple one-shot execution strategy."""
    
    @property
    def name(self) -> str:
        return "baseline"
    
    @property
    def supports_retry(self) -> bool:
        return False
    
    def execute(
        self,
        client: LMStudioClient,
        task: Task,
        artifact_dir: Path,
        max_attempts: int = 1,
    ) -> StrategyResult:
        """
        Execute the task with a single attempt.
        
        Args:
            client: The LM Studio client
            task: The task to execute
            artifact_dir: Directory for artifacts
            max_attempts: Ignored for baseline (always 1 attempt)
            
        Returns:
            StrategyResult with the single attempt result
        """
        artifact_dir.mkdir(parents=True, exist_ok=True)
        attempt_dir = artifact_dir / "attempt_1"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        
        # Get the prompt
        prompt = task.get_prompt()
        
        # Save prompt
        (attempt_dir / "prompt.json").write_text(
            json.dumps(prompt, indent=2)
        )
        
        # Make the API call
        response = client.chat_completion(prompt)
        
        # Save response artifacts
        (attempt_dir / "response.txt").write_text(response.text)
        (attempt_dir / "raw.json").write_text(
            json.dumps(response.raw, indent=2)
        )
        
        # Evaluate
        eval_result = task.evaluate(response.text, attempt_dir)
        
        # Save eval result
        (attempt_dir / "eval.json").write_text(
            json.dumps(
                {
                    "success": eval_result.success,
                    "score": eval_result.score,
                    "error_type": eval_result.error_type,
                    "details": eval_result.details,
                },
                indent=2,
                default=str,
            )
        )
        
        attempt = AttemptResult(
            attempt_num=1,
            response=response,
            eval_result=eval_result,
            prompt=prompt,
        )
        
        return StrategyResult(
            success=eval_result.success,
            final_score=eval_result.score,
            attempts=[attempt],
            total_latency_ms=response.latency_ms,
            error_type=eval_result.error_type,
        )
