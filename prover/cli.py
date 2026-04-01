import sys
import re
import os
import argparse
from .agent import run_analysis


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          Game Theory Mechanism Truthfulness Prover           ║
║  Formally verifies strategy-proofness via Z3 + Claude        ║
╚══════════════════════════════════════════════════════════════╝
"""

VERDICT_SYMBOLS = {
    "truthful": "✓ TRUTHFUL",
    "not_truthful": "✗ NOT TRUTHFUL",
    "unknown": "? UNKNOWN",
}


def format_result(result: dict) -> str:
    verdict_str = VERDICT_SYMBOLS.get(result["verdict"], result["verdict"].upper())
    lines = [
        "",
        "=" * 64,
        f"  Mechanism: {result['mechanism_name']}",
        f"  Verdict:   {verdict_str}",
        "=" * 64,
        "",
        result["proof"],
    ]
    z3_calls = result.get("z3_calls", [])
    if z3_calls:
        lines += ["", "── Z3 Constraint Formalization ──────────────────────────────"]
        for i, call in enumerate(z3_calls, 1):
            if len(z3_calls) > 1:
                lines.append(f"\n  [Query {i}]")
            lines += [call["code"], "", f"  → {call['output'].strip()}"]
        lines.append("─────────────────────────────────────────────────────────────")
    elif result.get("z3_result"):
        lines += [
            "",
            "── Z3 Verification ──────────────────────────────────────────",
            result["z3_result"],
            "─────────────────────────────────────────────────────────────",
        ]
    lines.append("")
    return "\n".join(lines)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def save_result(result: dict, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    slug = _slug(result.get("mechanism_name", "unknown"))

    z3_calls = result.get("z3_calls", [])
    if z3_calls:
        z3_path = os.path.join(output_dir, f"{slug}_constraints.py")
        with open(z3_path, "w") as f:
            for i, call in enumerate(z3_calls, 1):
                if len(z3_calls) > 1:
                    f.write(f"# Query {i}\n")
                f.write(call["code"].rstrip() + "\n")
                output_lines = call["output"].strip().splitlines()
                f.write("\n# Output:\n")
                for line in output_lines:
                    f.write(f"# {line}\n")
                if i < len(z3_calls):
                    f.write("\n" + "#" * 60 + "\n\n")
        print(f"Z3 constraints saved to: {z3_path}", file=sys.stderr)

    verdict = result.get("verdict", "unknown")
    label = "counterexample" if verdict == "not_truthful" else "proof"
    proof_path = os.path.join(output_dir, f"{slug}_{label}.txt")
    with open(proof_path, "w") as f:
        f.write(f"Mechanism: {result.get('mechanism_name', 'Unknown')}\n")
        f.write(f"Verdict:   {verdict.upper()}\n")
        f.write("=" * 60 + "\n\n")
        f.write(result.get("proof", "") + "\n")
        if result.get("z3_result"):
            f.write("\nZ3 Result:\n" + result["z3_result"] + "\n")
    print(f"{'Counterexample' if verdict == 'not_truthful' else 'Proof'} saved to: {proof_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        prog="prover",
        description="Prove or disprove strategy-proofness of a game-theoretic mechanism",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m prover "Second-price auction with n bidders"
  python -m prover "First-price sealed-bid auction"
  python -m prover "VCG mechanism for combinatorial auctions"
  python -m prover --verbose "Majority voting with 3 agents over 2 alternatives"
  python -m prover  # interactive mode (reads from stdin)
        """,
    )
    parser.add_argument(
        "mechanism",
        nargs="?",
        help="Description of the mechanism to analyze. If omitted, reads from stdin interactively.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show agent reasoning, Z3 code, and intermediate steps",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON instead of formatted text",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        default="results",
        help="Directory to save Z3 constraints and proof/counterexample files (default: ./results)",
    )
    parser.add_argument(
        "--name",
        metavar="NAME",
        help="Override the mechanism name used for saved filenames (e.g. 'Random Round-Robin')",
    )

    args = parser.parse_args()

    print(BANNER, file=sys.stderr)

    if args.mechanism:
        description = args.mechanism
    else:
        print("Describe the mechanism to analyze (press Enter twice when done):\n", file=sys.stderr)
        lines = []
        try:
            while True:
                line = input()
                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)
        except EOFError:
            pass
        description = "\n".join(lines).strip()

    if not description:
        print("Error: No mechanism description provided.", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing: {description!r}\n", file=sys.stderr)

    try:
        result = run_analysis(description, verbose=args.verbose)
    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        sys.exit(1)

    if args.name:
        result["mechanism_name"] = args.name
    save_result(result, args.output_dir)

    if args.json:
        import json
        print(json.dumps(result, indent=2))
    else:
        print(format_result(result))

    # Exit code: 0 for truthful, 1 for not_truthful, 2 for unknown
    exit_codes = {"truthful": 0, "not_truthful": 1, "unknown": 2}
    sys.exit(exit_codes.get(result["verdict"], 2))
