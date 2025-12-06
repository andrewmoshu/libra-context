"""Code generation and execution tools for Agent Hive drones."""

from typing import Optional, Dict, Any, List
import subprocess
import tempfile
import os
from pathlib import Path


def execute_python(
    code: str,
    timeout: int = 30,
    capture_output: bool = True,
) -> Dict[str, Any]:
    """
    Execute Python code in a sandboxed environment.

    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds
        capture_output: Whether to capture stdout/stderr

    Returns:
        Dict containing execution results, output, and any errors
    """
    result = {
        "status": "success",
        "code": code,
        "stdout": "",
        "stderr": "",
        "return_code": 0,
        "execution_time": 0.0,
    }

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp_file:
            tmp_file.write(code)
            tmp_path = tmp_file.name

        try:
            import time

            start_time = time.time()

            proc = subprocess.run(
                ["python", tmp_path],
                capture_output=capture_output,
                timeout=timeout,
                text=True,
            )

            result["execution_time"] = time.time() - start_time
            result["stdout"] = proc.stdout
            result["stderr"] = proc.stderr
            result["return_code"] = proc.returncode

            if proc.returncode != 0:
                result["status"] = "error"

        finally:
            os.unlink(tmp_path)

    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["stderr"] = f"Execution timed out after {timeout} seconds"
    except Exception as e:
        result["status"] = "error"
        result["stderr"] = str(e)

    return result


def write_file(
    path: str,
    content: str,
    create_dirs: bool = True,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Write content to a file.

    Args:
        path: File path to write to
        content: Content to write
        create_dirs: Create parent directories if they don't exist
        overwrite: Overwrite existing file

    Returns:
        Dict containing operation status and file metadata
    """
    result = {
        "status": "success",
        "path": path,
        "bytes_written": 0,
        "message": "",
    }

    try:
        file_path = Path(path)

        if file_path.exists() and not overwrite:
            result["status"] = "error"
            result["message"] = f"File already exists: {path}. Set overwrite=True to replace."
            return result

        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            bytes_written = f.write(content)

        result["bytes_written"] = bytes_written
        result["message"] = f"Successfully wrote {bytes_written} bytes to {path}"

    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    return result


def read_file(
    path: str,
    max_lines: Optional[int] = None,
    encoding: str = "utf-8",
) -> Dict[str, Any]:
    """
    Read content from a file.

    Args:
        path: File path to read
        max_lines: Maximum number of lines to read (None for all)
        encoding: File encoding

    Returns:
        Dict containing file content and metadata
    """
    result = {
        "status": "success",
        "path": path,
        "content": "",
        "lines": 0,
        "size": 0,
    }

    try:
        file_path = Path(path)

        if not file_path.exists():
            result["status"] = "error"
            result["message"] = f"File not found: {path}"
            return result

        result["size"] = file_path.stat().st_size

        with open(file_path, "r", encoding=encoding) as f:
            if max_lines:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)
                result["content"] = "".join(lines)
                result["lines"] = len(lines)
            else:
                result["content"] = f.read()
                result["lines"] = result["content"].count("\n") + 1

    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    return result


def generate_code(
    task_description: str,
    language: str = "python",
    style_guide: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate code based on a task description.

    This is a placeholder that will be implemented by the LLM agent.

    Args:
        task_description: Description of what the code should do
        language: Programming language to generate
        style_guide: Optional style guide to follow

    Returns:
        Dict containing generated code and explanation
    """
    return {
        "status": "pending",
        "task_description": task_description,
        "language": language,
        "code": "",  # Will be generated by LLM
        "explanation": "",
        "tests": [],
    }


def review_code(
    code: str,
    language: str = "python",
    review_type: str = "full",
) -> Dict[str, Any]:
    """
    Review code for issues and improvements.

    Args:
        code: Code to review
        language: Programming language
        review_type: Type of review - "full", "security", "performance", "style"

    Returns:
        Dict containing review findings and suggestions
    """
    return {
        "status": "pending",
        "code": code,
        "language": language,
        "review_type": review_type,
        "issues": [],
        "suggestions": [],
        "score": 0.0,
    }
