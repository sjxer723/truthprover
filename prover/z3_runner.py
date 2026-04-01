import subprocess
import sys
import textwrap

MAX_OUTPUT_CHARS = 4096


def run_z3_code(code: str) -> str:
    """
    Execute Python/Z3 code in a subprocess with timeout.
    Returns stdout + stderr, truncated to MAX_OUTPUT_CHARS.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            # Filter out minor Z3 warnings but keep actual errors
            stderr_lines = [
                line for line in result.stderr.splitlines()
                if not line.startswith("WARNING:") and line.strip()
            ]
            if stderr_lines:
                output += "\n[stderr]\n" + "\n".join(stderr_lines)

        if not output.strip():
            output = "(no output produced)"

        if len(output) > MAX_OUTPUT_CHARS:
            output = output[:MAX_OUTPUT_CHARS] + f"\n... [truncated at {MAX_OUTPUT_CHARS} chars]"

        return output

    except subprocess.TimeoutExpired:
        return "ERROR: Z3 execution timed out after 30 seconds. Try a smaller type grid or simpler constraints."
    except Exception as e:
        return f"ERROR: Failed to execute code: {e}"
