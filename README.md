# Game Theory Mechanism Prover

A CLI tool that uses Claude + Z3 + Lean 4 to find counterexamples to **strategy-proofness** in game-theoretic mechanisms, or formally verify truthfulness.

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
          ├─ truthful? ──▶  write Lean 4 theorem + proof
          │                 check_lean_proof ──▶ Axle/Lean
          │                 ◀── Valid / errors ──────────┘
          │                 iterate on proof if needed
          │
          └─ not truthful  ▶  encode IC violation:
             or unsure        ∃ i, vᵢ, rᵢ, v₋ᵢ: u(rᵢ,v₋ᵢ) > u(vᵢ,v₋ᵢ)
                              execute_python_z3_code ──▶ Z3
                              ◀── SAT / UNSAT ──────────┘
                              iterate up to 4× if needed
          │
          ▼
    Final verdict  →  {name}_constraints.py
                      {name}_counterexample.txt | _proof.txt
                      {name}_proof.lean          (if truthful)
```

> **SAT** is definitive. **UNSAT** is evidence on a bounded grid. **Lean proofs** give fully machine-checked guarantees over all reals.

## Installation

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

For Lean proof checking, the agent uses [Axle](https://github.com/oOo0oOo/axle) to verify proofs against Lean 4 + Mathlib without a local installation. Set `AXLE_API_KEY` if required by your Axle instance.

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

## Output files

| File | When produced |
|------|---------------|
| `{name}_constraints.py` | Always (Z3 constraint code + output) |
| `{name}_proof.txt` | Verdict is truthful |
| `{name}_counterexample.txt` | Verdict is not truthful |
| `{name}_proof.lean` | Verdict is truthful and Lean proof compiled |

The `.lean` file is a standalone Lean 4 + Mathlib theorem that can be checked with any Lean toolchain.

## Example Lean proof

For the second-price auction (2 bidders), the tool produces and verifies:

```lean
import Mathlib.Algebra.Order.Ring.Lemmas

noncomputable def sp_util (v b p : ℝ) : ℝ :=
  if b ≥ p then v - p else 0

theorem sp_truthful (v p r : ℝ) : sp_util v v p ≥ sp_util v r p := by
  unfold sp_util
  by_cases hv : v ≥ p
  ...
```

## Dependencies

- [`anthropic`](https://github.com/anthropics/anthropic-sdk-python) — Claude API client
- [`z3-solver`](https://github.com/Z3Prover/z3) — SMT solver
- [`axle`](https://github.com/oOo0oOo/axle) — remote Lean 4 proof checker (no local Lean install required)
