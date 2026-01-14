"""Base interface for execution strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..providers.lmstudio import ChatResponse
from ..tasks.base import EvalResult, Task


@dataclass
class AttemptResult:
    """Result of a single attempt within a strategy."""
    
    attempt_num: int
    response: ChatResponse
    eval_result: EvalResult
    prompt: list[dict[str, str]]


@dataclass 
class StrategyResult:
    """Result of executing a strategy."""
    
    success: bool
    final_score: float
    attempts: list[AttemptResult] = field(default_factory=list)
    total_latency_ms: float = 0.0
    error_type: str | None = None


class Strategy(ABC):
    """Abstract base class for execution strategies."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name identifying this strategy."""
        ...
    
    @property
    def supports_retry(self) -> bool:
        """Whether this strategy supports retry on failure."""
        return False
    
    @abstractmethod
    def execute(
        self,
        client: Any,  # LMStudioClient
        task: Task,
        artifact_dir: Path,
        max_attempts: int = 1,
    ) -> StrategyResult:
        """
        Execute the strategy for a given task.
        
        Args:
            client: The LM Studio client
            task: The task to execute
            artifact_dir: Directory for artifacts
            max_attempts: Maximum number of attempts
            
        Returns:
            StrategyResult with success status and attempt details
        """
        ...
