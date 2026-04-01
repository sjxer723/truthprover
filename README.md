# Game Theory Mechanism Prover

A CLI tool that searches for counterexamples to **strategy-proofness** (incentive compatibility) in game-theoretic mechanisms, and attempts to verify truthfulness on bounded type grids. It combines Claude as a game theory reasoning agent with the Z3 SMT solver for constraint-based verification.

## How It Works

Claude drives the entire analysis. Given a natural language description of a mechanism, it:

1. Formalizes the mechanism — type space, allocation rule, payment rule, utility function
2. Encodes the **IC violation condition** as a Z3 constraint:
   ```
   ∃ agent i, type vᵢ, misreport rᵢ, others v₋ᵢ:
     utility_i(rᵢ, v₋ᵢ) > utility_i(vᵢ, v₋ᵢ)
   ```
3. Runs Z3 to check satisfiability
   - **SAT** → counterexample found → mechanism is **not truthful** (definitive)
   - **UNSAT** → no violation found **within the encoded type grid** — this is not a general proof of truthfulness, only evidence on that specific instance (finite grid, bounded values, etc.)
4. Translates the result into a natural language proof or counterexample

Claude may iterate up to 3 times — e.g. to fix a Z3 encoding bug or check additional agents after seeing the first result.

## Installation

```bash
pip install -r requirements.txt
```

Requires an Anthropic API key:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```bash
# Analyze a mechanism
python -m prover "Second-price auction with n bidders"

# Name the output files explicitly
python -m prover --name "Second-Price Auction" "Second-price auction with n bidders"

# Show agent reasoning and Z3 code as it runs
python -m prover --verbose "First-price sealed-bid auction"

# Output structured JSON
python -m prover --json "VCG mechanism for combinatorial auctions"

# Save files to a custom directory (default: ./results)
python -m prover --output-dir ./out "Majority voting with 3 agents"

# Interactive mode (no argument → reads from stdin)
python -m prover
```

## Output Files

Every run saves two files to `./results/` (or `--output-dir`), named after the mechanism:

**`{mechanism}_constraints.py`** — The Z3 Python code Claude generated, with solver output as comments. A valid, runnable Python file.

```python
from z3 import *
v1, r1, v2 = Ints('v1 r1 v2')
s = Solver()
...
s.add(util1(v1, r1, v2) > util1(v1, v1, v2))  # IC violation?
print(s.check(), s.model())

# Output:
# sat
# [v1 = 3, r1 = 2, v2 = 1]
```

**`{mechanism}_counterexample.txt`** or **`{mechanism}_proof.txt`** — The natural language verdict with full reasoning, specific values (if a counterexample), and the raw Z3 result that supports the conclusion.

## Example

```
$ python -m prover --name "Random Round-Robin" \
    "2 agents, 3 items, uniformly random picking order, agents pick greedily"
```

**Counterexample output:**
```
True values  — Agent 1: A=3, B=4, C=5  |  Agent 2: A=2, B=3, C=1
Misreport    — Agent 1: A=3, B=5, C=4  (swaps B and C)

Truthful expected utility:  6.5
Misreport expected utility: 7.0   ← strictly higher

✗ NOT TRUTHFUL — Agent 1 benefits by misreporting their preference order.
```

## CLI Flags

| Flag | Description |
|------|-------------|
| `-v`, `--verbose` | Print agent reasoning, Z3 code, and intermediate steps to stderr |
| `--json` | Output result as JSON (includes `z3_calls` array) |
| `--name NAME` | Override the mechanism name used for saved filenames |
| `--output-dir DIR` | Directory for saved files (default: `./results`) |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Truthful (strategy-proof) |
| `1` | Not truthful (counterexample found) |
| `2` | Unknown (max iterations reached without conclusion) |

## Dependencies

- [`anthropic`](https://github.com/anthropics/anthropic-sdk-python) — Claude API client
- [`z3-solver`](https://github.com/Z3Prover/z3) — SMT solver for constraint checking
