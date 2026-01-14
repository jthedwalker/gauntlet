"""Critique-then-fix retry strategy."""

import json
from pathlib import Path

from ..providers.lmstudio import LMStudioClient
from ..tasks.base import Task
from .base import AttemptResult, Strategy, StrategyResult


class CritiqueFixStrategy(Strategy):
    """Strategy that retries with critique feedback on failure."""
    
    @property
    def name(self) -> str:
        return "critique_fix"
    
    @property
    def supports_retry(self) -> bool:
        return True
    
    def execute(
        self,
        client: LMStudioClient,
        task: Task,
        artifact_dir: Path,
        max_attempts: int = 3,
    ) -> StrategyResult:
        """
        Execute the task with retry on failure using critique prompts.
        
        Steps:
        1. Run initial prompt
        2. If failed, construct critique prompt with error feedback
        3. Retry up to max_attempts
        
        Args:
            client: The LM Studio client
            task: The task to execute
            artifact_dir: Directory for artifacts
            max_attempts: Maximum retry attempts
            
        Returns:
            StrategyResult with all attempt results
        """
        artifact_dir.mkdir(parents=True, exist_ok=True)
        
        attempts: list[AttemptResult] = []
        total_latency_ms = 0.0
        last_response_text: str | None = None
        last_eval_result = None
        
        for attempt_num in range(1, max_attempts + 1):
            attempt_dir = artifact_dir / f"attempt_{attempt_num}"
            attempt_dir.mkdir(parents=True, exist_ok=True)
            
            # Get appropriate prompt
            if attempt_num == 1:
                prompt = task.get_prompt()
            else:
                # Use critique prompt with previous failure info
                prompt = task.get_critique_prompt(
                    original_response=last_response_text or "",
                    eval_result=last_eval_result,
                )
            
            # Save prompt
            (attempt_dir / "prompt.json").write_text(
                json.dumps(prompt, indent=2)
            )
            
            # Make the API call
            response = client.chat_completion(prompt)
            total_latency_ms += response.latency_ms
            
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
                attempt_num=attempt_num,
                response=response,
                eval_result=eval_result,
                prompt=prompt,
            )
            attempts.append(attempt)
            
            # Store for potential retry
            last_response_text = response.text
            last_eval_result = eval_result
            
            # Success - stop retrying
            if eval_result.success:
                return StrategyResult(
                    success=True,
                    final_score=eval_result.score,
                    attempts=attempts,
                    total_latency_ms=total_latency_ms,
                )
        
        # All attempts failed
        final_result = attempts[-1].eval_result
        return StrategyResult(
            success=False,
            final_score=final_result.score,
            attempts=attempts,
            total_latency_ms=total_latency_ms,
            error_type=final_result.error_type,
        )
