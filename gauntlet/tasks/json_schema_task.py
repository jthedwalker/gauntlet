"""JSON schema compliance task."""

import json
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .base import EvalResult, Task


class Person(BaseModel):
    """Schema for the JSON output task."""
    
    name: str
    age: int
    city: str


class JSONSchemaTask(Task):
    """Task to evaluate JSON schema compliance."""
    
    @property
    def name(self) -> str:
        return "json_schema"
    
    def get_prompt(self) -> list[dict[str, str]]:
        schema_str = json.dumps(Person.model_json_schema(), indent=2)
        
        return [
            {
                "role": "system",
                "content": "You are a precise coding assistant. Follow instructions exactly.",
            },
            {
                "role": "user",
                "content": f"""Return ONLY valid JSON matching this schema. No explanations, no markdown, just the raw JSON object.

Schema:
{schema_str}

Generate a JSON object for a fictional person. Return ONLY the JSON object, nothing else.""",
            },
        ]
    
    def evaluate(self, response_text: str, artifact_dir: Path) -> EvalResult:
        """
        Evaluate if the response is valid JSON matching the Person schema.
        
        Steps:
        1. Try to parse as JSON
        2. Try to validate against Pydantic model
        """
        # Clean up response - strip whitespace and potential markdown
        text = response_text.strip()
        
        # Try to extract JSON from markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (code fence markers)
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        
        # Step 1: Try to parse as JSON
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return EvalResult(
                success=False,
                score=0.0,
                error_type="json_parse_error",
                details={
                    "error_message": f"JSON parse error: {e}",
                    "raw_response": response_text,
                },
            )
        
        # Step 2: Validate against Pydantic model
        try:
            person = Person.model_validate(data)
            return EvalResult(
                success=True,
                score=1.0,
                details={
                    "parsed_data": person.model_dump(),
                },
            )
        except ValidationError as e:
            return EvalResult(
                success=False,
                score=0.0,
                error_type="schema_error",
                details={
                    "error_message": f"Schema validation error: {e}",
                    "parsed_json": data,
                },
            )
