"""Python function task with pytest evaluation."""

import re
import subprocess
import sys
from pathlib import Path

from .base import EvalResult, Task

# Test cases for the normalize_phone function
TEST_FILE_CONTENT = '''"""Tests for normalize_phone function."""

import pytest
from solution import normalize_phone


def test_ten_digits():
    """Test 10-digit phone number formatting."""
    assert normalize_phone("1234567890") == "123-456-7890"


def test_ten_digits_with_symbols():
    """Test stripping non-digits from 10-digit number."""
    assert normalize_phone("(123) 456-7890") == "123-456-7890"
    assert normalize_phone("123.456.7890") == "123-456-7890"


def test_eleven_digits_with_leading_one():
    """Test 11-digit number starting with 1."""
    assert normalize_phone("11234567890") == "123-456-7890"
    assert normalize_phone("1-123-456-7890") == "123-456-7890"


def test_invalid_length():
    """Test that invalid lengths raise ValueError."""
    with pytest.raises(ValueError):
        normalize_phone("123456789")  # 9 digits
    with pytest.raises(ValueError):
        normalize_phone("12345678901")  # 11 digits not starting with 1
    with pytest.raises(ValueError):
        normalize_phone("123456789012")  # 12 digits


def test_eleven_digits_not_starting_with_one():
    """Test 11 digits not starting with 1 raises ValueError."""
    with pytest.raises(ValueError):
        normalize_phone("21234567890")
'''


class PyFuncTask(Task):
    """Task to generate and test a Python function."""
    
    @property
    def name(self) -> str:
        return "pyfunc"
    
    def get_prompt(self) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": "You are a precise coding assistant. Follow instructions exactly.",
            },
            {
                "role": "user",
                "content": """Write a Python function with this exact signature:

def normalize_phone(s: str) -> str:

Requirements:
1. Strip all non-digit characters from the input
2. If the result is exactly 10 digits, format as AAA-BBB-CCCC
3. If the result is exactly 11 digits AND starts with '1', drop the leading '1' and format as AAA-BBB-CCCC
4. Otherwise, raise a ValueError

Return ONLY the function definition. No explanations, no examples, no imports, no markdown code fences - just the raw Python function.""",
            },
        ]
    
    def evaluate(self, response_text: str, artifact_dir: Path) -> EvalResult:
        """
        Evaluate the response by running pytest on the generated code.
        
        Steps:
        1. Extract code from response
        2. Write solution.py
        3. Write test_solution.py
        4. Run pytest
        5. Parse results
        """
        artifact_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract code from response
        code = self._extract_code(response_text)
        
        if not code:
            return EvalResult(
                success=False,
                score=0.0,
                error_type="code_extraction_error",
                details={
                    "error_message": "Could not extract valid Python code from response",
                    "raw_response": response_text,
                },
            )
        
        # Write solution file
        solution_path = artifact_dir / "solution.py"
        solution_path.write_text(code)
        
        # Write test file
        test_path = artifact_dir / "test_solution.py"
        test_path.write_text(TEST_FILE_CONTENT)
        
        # Run pytest
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", str(test_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=artifact_dir,
            )
            
            stdout = result.stdout
            stderr = result.stderr
            
            # Save pytest output
            (artifact_dir / "pytest_stdout.txt").write_text(stdout)
            (artifact_dir / "pytest_stderr.txt").write_text(stderr)
            
            if result.returncode == 0:
                return EvalResult(
                    success=True,
                    score=1.0,
                    details={
                        "stdout": stdout,
                        "stderr": stderr,
                    },
                )
            else:
                return EvalResult(
                    success=False,
                    score=0.0,
                    error_type="pytest_failure",
                    details={
                        "error_message": f"Pytest failed:\n{stdout}\n{stderr}",
                        "stdout": stdout,
                        "stderr": stderr,
                        "exit_code": result.returncode,
                    },
                )
                
        except subprocess.TimeoutExpired:
            return EvalResult(
                success=False,
                score=0.0,
                error_type="timeout",
                details={
                    "error_message": "Pytest execution timed out after 30 seconds",
                },
            )
        except Exception as e:
            return EvalResult(
                success=False,
                score=0.0,
                error_type="execution_error",
                details={
                    "error_message": f"Error running pytest: {e}",
                },
            )
    
    def _extract_code(self, response_text: str) -> str | None:
        """Extract Python code from response, handling various formats."""
        text = response_text.strip()
        
        # Try to extract from markdown code blocks
        code_block_pattern = r"```(?:python)?\s*\n(.*?)```"
        matches = re.findall(code_block_pattern, text, re.DOTALL)
        if matches:
            text = matches[0].strip()
        
        # Check if it looks like a function definition
        if "def normalize_phone" in text:
            # Find the function definition and extract it
            lines = text.split("\n")
            func_lines = []
            in_function = False
            indent_level = None
            
            for line in lines:
                if line.strip().startswith("def normalize_phone"):
                    in_function = True
                    indent_level = len(line) - len(line.lstrip())
                    func_lines.append(line)
                elif in_function:
                    # Check if we're still in the function
                    if line.strip() == "":
                        func_lines.append(line)
                    elif line.startswith(" " * (indent_level + 1)) or line.startswith("\t"):
                        func_lines.append(line)
                    elif line.strip().startswith("#"):
                        func_lines.append(line)
                    else:
                        # New top-level definition, stop
                        break
            
            if func_lines:
                return "\n".join(func_lines)
        
        # If response doesn't contain function def, try to wrap it
        if "def " not in text and text:
            # Assume the response is the function body
            return None
        
        return text if text else None
