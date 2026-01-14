"""Base interface for evaluation tasks."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EvalResult:
    """Result of evaluating a task response."""
    
    success: bool
    score: float
    error_type: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class Task(ABC):
    """Abstract base class for evaluation tasks."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name identifying this task."""
        ...
    
    @abstractmethod
    def get_prompt(self) -> list[dict[str, str]]:
        """
        Get the prompt messages for this task.
        
        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        ...
    
    @abstractmethod
    def evaluate(self, response_text: str, artifact_dir: Path) -> EvalResult:
        """
        Evaluate the model's response.
        
        Args:
            response_text: The model's response text
            artifact_dir: Directory to write any evaluation artifacts
            
        Returns:
            EvalResult with success status, score, and any error details
        """
        ...
    
    def get_critique_prompt(
        self,
        original_response: str,
        eval_result: EvalResult,
    ) -> list[dict[str, str]]:
        """
        Get a critique prompt for retry after failure.
        
        Args:
            original_response: The model's previous response
            eval_result: The evaluation result with error details
            
        Returns:
            List of message dicts for the critique/fix prompt
        """
        original_prompt = self.get_prompt()
        user_content = next(
            (m["content"] for m in original_prompt if m["role"] == "user"),
            "",
        )
        
        error_msg = eval_result.details.get("error_message", str(eval_result.error_type))
        
        return [
            {
                "role": "system",
                "content": "You are a precise coding assistant. Fix the error and return ONLY the corrected output. No explanations or commentary.",
            },
            {
                "role": "user",
                "content": f"""Original task:
{user_content}

Your previous output:
{original_response}

Error:
{error_msg}

Return ONLY the corrected output.""",
            },
        ]
