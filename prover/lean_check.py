import asyncio
from axle import AxleClient

LEAN_ENV = "lean-4.28.0"


async def _check_async(lean_code: str) -> str:
    async with AxleClient() as client:
        result = await client.check(content=lean_code, environment=LEAN_ENV, ignore_imports=True)

    lines = [f"Valid: {result.okay}"]

    if result.failed_declarations:
        lines.append(f"Failed declarations: {', '.join(result.failed_declarations)}")

    errors = result.lean_messages.errors
    if errors:
        lines.append("Errors:")
        for e in errors:
            lines.append(f"  - {e}")

    warnings = result.lean_messages.warnings
    if warnings:
        lines.append("Warnings:")
        for w in warnings:
            lines.append(f"  - {w}")

    if result.okay and not errors:
        lines.append("Proof checked successfully.")

    return "\n".join(lines)


def check_lean_proof(lean_code: str) -> str:
    """Synchronously check a Lean 4 proof via Axle and return a feedback string."""
    return asyncio.run(_check_async(lean_code))


if __name__ == "__main__":
    feedback = check_lean_proof("import Mathlib\ndef x := 1")
    print(feedback)
