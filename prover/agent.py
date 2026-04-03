import os
import json
import anthropic
from typing import Optional
from .prompts import SYSTEM_PROMPT
from .z3_runner import run_z3_code
from .lean_check import check_lean_proof

MODEL = "claude-sonnet-4-6"
MAX_ITERATIONS = 4


def _make_client() -> anthropic.Anthropic:
    """Create Anthropic client, handling both API keys and OAuth tokens."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    auth_token = os.environ.get("ANTHROPIC_TOKEN")

    if api_key:
        return anthropic.Anthropic(api_key=api_key)
    elif auth_token:
        return anthropic.Anthropic(auth_token=auth_token)
    else:
        raise ValueError(
            "No credentials found. Set ANTHROPIC_API_KEY (API key) or ANTHROPIC_TOKEN (OAuth token)."
        )

TOOLS = [
    {
        "name": "execute_python_z3_code",
        "description": (
            "Execute Python code that uses the Z3 SMT solver. "
            "Use this to check for IC violations or verify their absence. "
            "The code must use `from z3 import *` and print results to stdout. "
            "Returns stdout/stderr from the execution."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Valid Python code using Z3. Must print the result (sat/unsat/counterexample values) to stdout.",
                }
            },
            "required": ["code"],
        },
    },
    {
        "name": "check_lean_proof",
        "description": (
            "Check a Lean 4 proof using the Axle verification engine. "
            "Call this after writing a `lean_proof` to validate it. "
            "Returns 'Valid: True' and any warnings if the proof compiles, "
            "or 'Valid: False' with error messages if it fails. "
            "Use the error feedback to fix the proof before calling `write_formal_proof`."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lean_code": {
                    "type": "string",
                    "description": "Complete Lean 4 code to verify, including imports.",
                }
            },
            "required": ["lean_code"],
        },
    },
    {
        "name": "write_formal_proof",
        "description": (
            "Record your final verdict and formal proof. "
            "CALL THIS AS YOUR LAST ACTION once you have determined whether the mechanism is truthful. "
            "This terminates the analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mechanism_name": {
                    "type": "string",
                    "description": "Short descriptive name of the mechanism (e.g. 'Second-Price Auction', 'First-Price Auction')",
                },
                "verdict": {
                    "type": "string",
                    "enum": ["truthful", "not_truthful", "unknown"],
                    "description": "Whether the mechanism is strategy-proof",
                },
                "proof": {
                    "type": "string",
                    "description": (
                        "If truthful: a formal proof with mathematical argument. "
                        "If not truthful: a precise counterexample with specific values. "
                        "If unknown: your best analysis with reasons for uncertainty."
                    ),
                },
                "z3_result": {
                    "type": "string",
                    "description": "The key Z3 output that supports your verdict (UNSAT for truthful, SAT + model for not truthful)",
                },
                "lean_proof": {
                    "type": "string",
                    "description": (
                        "A Lean 4 proof of strategy-proofness (only when verdict is 'truthful'). "
                        "Should be syntactically valid Lean 4 + Mathlib code capturing the key theorem and proof steps. "
                        "May include `sorry` for hard sub-goals but should sketch the full proof structure."
                    ),
                },
            },
            "required": ["mechanism_name", "verdict", "proof"],
        },
    },
]


def _dispatch_tool(name: str, inputs: dict) -> str:
    if name == "execute_python_z3_code":
        return run_z3_code(inputs["code"])
    elif name == "check_lean_proof":
        return check_lean_proof(inputs["lean_code"])
    elif name == "write_formal_proof":
        return "PROOF_RECORDED"
    return f"ERROR: Unknown tool '{name}'"


def run_analysis(description: str, verbose: bool = False) -> dict:
    """
    Run the game theory truthfulness analysis agent.

    Returns a dict with keys: mechanism_name, verdict, proof, z3_result (optional),
    z3_calls (list of {code, output} dicts for each Z3 execution)
    """
    client = _make_client()

    messages = [{"role": "user", "content": description}]
    final_result: Optional[dict] = None
    z3_calls: list[dict] = []
    counterexample_found = False

    iteration = 0
    while True:
        # Stop only if we have no pending counterexample to evaluate
        if iteration >= MAX_ITERATIONS and not counterexample_found:
            break
        iteration += 1
        print(f"\n[Agent iteration {iteration}]", flush=True)

        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Collect all content blocks (text + tool_use)
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        # Print a summary of what the agent is doing this iteration
        for block in assistant_content:
            if block.type == "text" and block.text.strip():
                if verbose:
                    print(f"\n[Reasoning]\n{block.text}", flush=True)
                else:
                    # Print first non-empty line as a brief summary
                    first_line = next(
                        (line.strip() for line in block.text.splitlines() if line.strip()),
                        ""
                    )
                    if first_line:
                        print(f"  {first_line}", flush=True)

        # Find tool calls
        tool_use_blocks = [b for b in assistant_content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" or not tool_use_blocks:
            break

        # Execute tools and collect results
        tool_results = []
        for tool_block in tool_use_blocks:
            tool_name = tool_block.name
            tool_input = tool_block.input

            if verbose:
                if tool_name == "execute_python_z3_code":
                    print(f"\n[Z3 Code]\n{tool_input.get('code', '')}", flush=True)
                elif tool_name == "write_formal_proof":
                    print(f"\n[Final Verdict: {tool_input.get('verdict', '?').upper()}]", flush=True)

            result_str = _dispatch_tool(tool_name, tool_input)

            if tool_name == "execute_python_z3_code":
                z3_calls.append({"code": tool_input.get("code", ""), "output": result_str})
                if "sat" in result_str.lower() and "unsat" not in result_str.lower():
                    counterexample_found = True

            if verbose and tool_name == "execute_python_z3_code":
                print(f"[Z3 Output]\n{result_str}", flush=True)

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": result_str,
                }
            )

            if tool_name == "write_formal_proof":
                final_result = dict(tool_input)
                break

        messages.append({"role": "user", "content": tool_results})

        if final_result is not None:
            break

    if final_result is not None:
        final_result["z3_calls"] = z3_calls
        return final_result

    return {
        "mechanism_name": "Unknown",
        "verdict": "unknown",
        "proof": "Analysis reached maximum iterations without a definitive conclusion.",
        "z3_result": None,
        "z3_calls": z3_calls,
    }
