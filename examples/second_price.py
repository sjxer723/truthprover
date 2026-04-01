"""
Example: Verify second-price (Vickrey) auction is truthful using Z3 directly.
Run: python examples/second_price.py
"""
from z3 import *

print("=== Second-Price Auction: IC Verification ===\n")
print("Setting: 2 agents, 1 item, integer valuations in [1, 10]")
print("Allocation: highest bidder wins (ties to agent 1)")
print("Payment: winner pays the second-highest bid\n")

N = 10
s = Solver()

v1, v2 = Ints('v1 v2')   # true valuations
r1 = Int('r1')            # agent 1 misreport

for x in [v1, v2, r1]:
    s.add(x >= 1, x <= N)

def alloc1(b1, b2):
    return If(b1 >= b2, 1, 0)

def pay1(b1, b2):
    return If(b1 >= b2, b2, 0)

def util1(val, b1, b2):
    return val * alloc1(b1, b2) - pay1(b1, b2)

s.add(util1(v1, r1, v2) > util1(v1, v1, v2))

result = s.check()
if result == sat:
    m = s.model()
    print(f"COUNTEREXAMPLE FOUND (mechanism NOT truthful):")
    print(f"  v1={m[v1]}, v2={m[v2]}, misreport r1={m[r1]}")
else:
    print("UNSAT: No IC violation found.")
    print("Result: Second-price auction is VERIFIED TRUTHFUL on integer grid [1,10].")
