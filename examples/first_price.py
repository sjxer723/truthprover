"""
Example: Show first-price auction is NOT truthful using Z3.
Run: python examples/first_price.py
"""
from z3 import *

print("=== First-Price Auction: IC Violation Search ===\n")
print("Setting: 2 agents, 1 item, integer valuations in [1, 10]")
print("Allocation: highest bidder wins (ties to agent 1)")
print("Payment: winner pays their own bid\n")

N = 10
s = Solver()

v1, v2 = Ints('v1 v2')
r1 = Int('r1')

for x in [v1, v2, r1]:
    s.add(x >= 1, x <= N)

def alloc1(b1, b2):
    return If(b1 >= b2, 1, 0)

def pay1_fp(b1, b2):  # first-price: pay your own bid
    return If(b1 >= b2, b1, 0)

def util1(val, b1, b2):
    return val * alloc1(b1, b2) - pay1_fp(b1, b2)

s.add(util1(v1, r1, v2) > util1(v1, v1, v2))

result = s.check()
if result == sat:
    m = s.model()
    print(f"COUNTEREXAMPLE FOUND (mechanism NOT truthful):")
    print(f"  True value v1={m[v1]}, Other agent v2={m[v2]}")
    print(f"  Misreport r1={m[r1]}")
    print(f"  Utility truthful (bid v1): {m.evaluate(util1(v1, v1, v2))}")
    print(f"  Utility misreport (bid r1): {m.evaluate(util1(v1, r1, v2))}")
    print(f"\nConclusion: Agent 1 benefits from bidding {m[r1]} instead of true value {m[v1]}.")
else:
    print("UNSAT: No IC violation found (unexpected).")
