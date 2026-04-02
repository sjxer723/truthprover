# Game Theory Mechanism Prover

A CLI tool that uses Claude + Z3 to find counterexamples to **strategy-proofness** in game-theoretic mechanisms, or verify truthfulness on bounded type grids.

## Pipeline

```
natural language description
          │
          ▼
    Claude Agent
          │
          │  1. Formalize (type space, allocation,
          │     payment, utility)
          │  2. Classify (VCG? Myerson? first-price?)
          │     and analyze whether truthful or not
          │
          ├─ truthful? ──▶  formal proof sketch
          │                 (natural language, no Z3)
          │
          └─ not truthful  ▶  encode IC violation:
             or unsure        ∃ i, vᵢ, rᵢ, v₋ᵢ: u(rᵢ,v₋ᵢ) > u(vᵢ,v₋ᵢ)
                              execute_python_z3_code ──▶ Z3
                              ◀── SAT / UNSAT ──────────┘
                              iterate up to 3× if needed
          │
          ▼
    Final verdict  →  {name}_constraints.py
                      {name}_counterexample.txt | _proof.txt
```

> **SAT** is definitive. **UNSAT** is evidence only — bounded grid, not a general proof.

## Installation

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```bash
python -m prover "Second-price auction with n bidders"
python -m prover --name "SPA" --verbose "Second-price auction with n bidders"
python -m prover --json "VCG mechanism for combinatorial auctions"
python -m prover --output-dir ./out "Majority voting with 3 agents"
python -m prover  # interactive stdin mode
```

## Example

```
$ python -m prover --name "Random Round-Robin" \
    "2 agents, 3 items, uniformly random picking order, agents pick greedily"

True values  — Agent 1: A=3, B=4, C=5  |  Agent 2: A=2, B=3, C=1
Misreport    — Agent 1: A=3, B=5, C=4  (swaps B and C)

Truthful expected utility:  6.5
Misreport expected utility: 7.0   ← strictly higher

✗ NOT TRUTHFUL — Agent 1 benefits by misreporting their preference order.
```

## Flags & Exit Codes

| Flag | Description |
|------|-------------|
| `-v`, `--verbose` | Print agent reasoning and Z3 code to stderr |
| `--json` | Output result as JSON (includes `z3_calls` array) |
| `--name NAME` | Override mechanism name used for saved filenames |
| `--output-dir DIR` | Directory for saved files (default: `./results`) |

| Exit | Meaning |
|------|---------|
| `0` | Truthful |
| `1` | Not truthful |
| `2` | Unknown (max iterations reached) |

## Dependencies

- [`anthropic`](https://github.com/anthropics/anthropic-sdk-python) — Claude API client
- [`z3-solver`](https://github.com/Z3Prover/z3) — SMT solver
