"""LM Studio OpenAI-compatible API client."""

import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class ChatResponse:
    """Response from a chat completion request."""
    
    text: str
    raw: dict[str, Any]
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class LMStudioClient:
    """Thin wrapper for LM Studio's OpenAI-compatible API."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: str = "liquid/lfm2.5-1.2b",
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)
    
    def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> ChatResponse:
        """
        Send a chat completion request to LM Studio.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            
        Returns:
            ChatResponse with text, raw JSON, latency, and token usage
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        start_time = time.perf_counter()
        response = self._client.post(url, json=payload)
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        response.raise_for_status()
        data = response.json()
        
        # Extract text from response
        text = data["choices"][0]["message"]["content"]
        
        # Extract token usage if present
        usage = data.get("usage", {})
        
        return ChatResponse(
            text=text,
            raw=data,
            latency_ms=latency_ms,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
        )
    
    def list_models(self) -> list[str]:
        """List available models from the LM Studio server."""
        url = f"{self.base_url}/models"
        response = self._client.get(url)
        response.raise_for_status()
        data = response.json()
        return [model["id"] for model in data.get("data", [])]
    
    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
    
    def __enter__(self) -> "LMStudioClient":
        return self
    
    def __exit__(self, *args: Any) -> None:
        self.close()
