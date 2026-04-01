# Query 1

from z3 import *

# ============================================================
# Random Round-Robin: 2 agents, 3 items
# ============================================================
# Agents: 1 and 2
# Items: A=0, B=1, C=2
# Types: cardinal values v_i[j] for agent i and item j
# 
# Round-Robin proceeds in TWO possible orderings (since random):
#   Order 1: Agent 1 picks first, then Agent 2, then Agent 1
#   Order 2: Agent 2 picks first, then Agent 1, then Agent 2
#
# Each ordering has probability 1/2.
# Agents are GREEDY: pick most preferred remaining item when it's their turn.
# Strategy-proofness = truth-telling maximizes EXPECTED utility.
# ============================================================

# We use INTEGER utilities on a discrete grid for tractability
# v1[j] = agent 1's value for item j, v2[j] = agent 2's value for item j
# r1[j] = agent 1's MISREPORTED value for item j (determines pick order)

# We'll search for:
#   - True values v1[0..2], v2[0..2]   (agent 1 and 2's true values)
#   - Misreport r1[0..2]               (agent 1's false report)
# Such that agent 1's EXPECTED utility under misreport > under truth

s = Solver()

# True values for both agents (integers 1..6 to allow rich preferences)
v1 = [Int(f'v1_{j}') for j in range(3)]
v2 = [Int(f'v2_{j}') for j in range(3)]
r1 = [Int(f'r1_{j}') for j in range(3)]  # agent 1's misreport

N = 6
for j in range(3):
    s.add(v1[j] >= 1, v1[j] <= N)
    s.add(v2[j] >= 1, v2[j] <= N)
    s.add(r1[j] >= 1, r1[j] <= N)

# True preferences are strict (no ties in true values)
s.add(Distinct(v1[0], v1[1], v1[2]))
s.add(Distinct(v2[0], v2[1], v2[2]))
# Misreport can have ties or not — we allow any report
s.add(Distinct(r1[0], r1[1], r1[2]))  # agent reports a strict ranking

# -------------------------------------------------------
# Greedy pick: given a preference vector and availability,
# returns the item with highest reported value among available items
# -------------------------------------------------------
def best_item(pref, available):
    """
    Returns the best available item index according to pref[].
    available[j] is a Z3 boolean: True if item j is still available.
    Returns a Z3 expression for the item index chosen.
    """
    # Item 0 vs 1 vs 2: pick the one with highest pref value
    # We encode this as nested If expressions
    best_val = If(available[0], pref[0], IntVal(-1))
    best_val = If(And(available[1], pref[1] > best_val), pref[1], best_val)
    best_val = If(And(available[2], pref[2] > best_val), pref[2], best_val)
    
    # Which item has best_val?
    chosen = If(And(available[0], pref[0] == best_val), IntVal(0),
             If(And(available[1], pref[1] == best_val), IntVal(1),
             If(And(available[2], pref[2] == best_val), IntVal(2),
             IntVal(-1))))
    return chosen

# -------------------------------------------------------
# Simulate round-robin: 2 agents, 3 items
# Order: first_agent picks first (round 1), second picks (round 2),
#        first_agent picks again (round 3)
# pref1, pref2: reported preference lists
# Returns (alloc1_item1, alloc1_item2, alloc2_item1):
#   items allocated to agent 1 (two items) and agent 2 (one item)
# -------------------------------------------------------
def simulate_rr(pref1, pref2, first_agent):
    """
    first_agent=1: agent 1 goes first → order: 1,2,1
    first_agent=2: agent 2 goes first → order: 2,1,2
    Returns (items_agent1, items_agent2) as lists of chosen item indices
    """
    avail = [True, True, True]  # all items available initially
    
    if first_agent == 1:
        # Round 1: Agent 1 picks
        pick1a = best_item(pref1, avail)
        avail_after_1a = [And(avail[j], IntVal(j) != pick1a) for j in range(3)]
        
        # Round 2: Agent 2 picks
        pick2a = best_item(pref2, avail_after_1a)
        avail_after_2a = [And(avail_after_1a[j], IntVal(j) != pick2a) for j in range(3)]
        
        # Round 3: Agent 1 picks again
        pick1b = best_item(pref1, avail_after_2a)
        
        return (pick1a, pick1b, pick2a)
    else:
        # Round 1: Agent 2 picks
        pick2a = best_item(pref2, avail)
        avail_after_2a = [And(avail[j], IntVal(j) != pick2a) for j in range(3)]
        
        # Round 2: Agent 1 picks
        pick1a = best_item(pref1, avail_after_2a)
        avail_after_1a = [And(avail_after_2a[j], IntVal(j) != pick1a) for j in range(3)]
        
        # Round 3: Agent 2 picks again
        pick2b = best_item(pref2, avail_after_1a)
        
        return (pick1a, None, pick2a)  # agent 1 gets 1 item when going second in 2-agent case

# -------------------------------------------------------
# For 2 agents, 3 items:
#   Order 1-2-1: Agent1 gets 2 items, Agent2 gets 1 item
#   Order 2-1-2: Agent2 gets 2 items, Agent1 gets 1 item
# -------------------------------------------------------

def compute_utility_1(pref1, pref2, true_v1):
    """Agent 1's EXPECTED utility = 0.5 * util(order 1-2-1) + 0.5 * util(order 2-1-2)"""
    
    # --- Order 1-2-1 ---
    avail = [True, True, True]
    
    p1a = best_item(pref1, avail)
    avail2 = [And(avail[j], IntVal(j) != p1a) for j in range(3)]
    
    p2a = best_item(pref2, avail2)
    avail3 = [And(avail2[j], IntVal(j) != p2a) for j in range(3)]
    
    p1b = best_item(pref1, avail3)
    
    # Agent 1's utility in order 1-2-1: value of p1a + value of p1b
    util_121 = (If(p1a == 0, true_v1[0], If(p1a == 1, true_v1[1], true_v1[2])) +
                If(p1b == 0, true_v1[0], If(p1b == 1, true_v1[1], true_v1[2])))
    
    # --- Order 2-1-2 ---
    avail_b = [True, True, True]
    
    p2a_b = best_item(pref2, avail_b)
    avail_b2 = [And(avail_b[j], IntVal(j) != p2a_b) for j in range(3)]
    
    p1a_b = best_item(pref1, avail_b2)
    avail_b3 = [And(avail_b2[j], IntVal(j) != p1a_b) for j in range(3)]
    
    p2b_b = best_item(pref2, avail_b3)
    
    # Agent 1's utility in order 2-1-2: value of p1a_b only
    util_212 = If(p1a_b == 0, true_v1[0], If(p1a_b == 1, true_v1[1], true_v1[2]))
    
    # Expected utility (multiply by 2 to avoid fractions)
    return util_121 + util_212  # proportional to E[utility] (sum = 2*E)

# -------------------------------------------------------
# IC Constraint: Agent 1 gains by misreporting r1 instead of v1
# -------------------------------------------------------
util_truth   = compute_utility_1(v1, v2, v1)
util_misrep  = compute_utility_1(r1, v2, v1)

# Agent 1 strictly benefits from misreporting
s.add(util_misrep > util_truth)

print("Checking for IC violation in Random Round-Robin (2 agents, 3 items)...")
result = s.check()

if result == sat:
    m = s.model()
    print(f"\n=== COUNTEREXAMPLE FOUND ===")
    print(f"True values  agent 1: v1 = {[m.evaluate(v1[j]) for j in range(3)]}  (items A,B,C)")
    print(f"True values  agent 2: v2 = {[m.evaluate(v2[j]) for j in range(3)]}")
    print(f"Misreport    agent 1: r1 = {[m.evaluate(r1[j]) for j in range(3)]}")
    print(f"\nExpected utility (x2) truthful : {m.evaluate(util_truth)}")
    print(f"Expected utility (x2) misreport: {m.evaluate(util_misrep)}")
    print(f"\n--- Detailed trace ---")
    v1_vals = [m.evaluate(v1[j]) for j in range(3)]
    v2_vals = [m.evaluate(v2[j]) for j in range(3)]
    r1_vals = [m.evaluate(r1[j]) for j in range(3)]
    print(f"Agent 1 TRUE values:    A={v1_vals[0]}, B={v1_vals[1]}, C={v1_vals[2]}")
    print(f"Agent 2 TRUE values:    A={v2_vals[0]}, B={v2_vals[1]}, C={v2_vals[2]}")
    print(f"Agent 1 MISREPORT:      A={r1_vals[0]}, B={r1_vals[1]}, C={r1_vals[2]}")
else:
    print(f"\nResult: {result}")
    print("No IC violation found on this grid.")

# Output:
# Checking for IC violation in Random Round-Robin (2 agents, 3 items)...
# 
# === COUNTEREXAMPLE FOUND ===
# True values  agent 1: v1 = [3, 4, 5]  (items A,B,C)
# True values  agent 2: v2 = [2, 3, 1]
# Misreport    agent 1: r1 = [3, 5, 4]
# 
# Expected utility (x2) truthful : 13
# Expected utility (x2) misreport: 14
# 
# --- Detailed trace ---
# Agent 1 TRUE values:    A=3, B=4, C=5
# Agent 2 TRUE values:    A=2, B=3, C=1
# Agent 1 MISREPORT:      A=3, B=5, C=4

############################################################

# Query 2

# ============================================================
# Manual trace of the counterexample to verify and explain clearly
# ============================================================
# Items: A=0, B=1, C=2
# Agent 1 TRUE values:    A=3, B=4, C=5   → prefers C > B > A
# Agent 2 TRUE values:    A=2, B=3, C=1   → prefers B > A > C
# Agent 1 MISREPORT:      A=3, B=5, C=4   → reports B > C > A (LIE: swaps B and C)

def greedy_pick(pref, available_items):
    best = max(available_items, key=lambda item: pref[item])
    return best

v1 = {0: 3, 1: 4, 2: 5}   # true: A=3, B=4, C=5 → order C>B>A
v2 = {0: 2, 1: 3, 2: 1}   # true: A=2, B=3, C=1 → order B>A>C
r1 = {0: 3, 1: 5, 2: 4}   # misrep: A=3, B=5, C=4 → reports B>C>A

items = [0, 1, 2]
item_name = {0: 'A', 1: 'B', 2: 'C'}

print("=" * 60)
print("COUNTEREXAMPLE TRACE")
print("=" * 60)
print(f"Agent 1 TRUE values:  A={v1[0]}, B={v1[1]}, C={v1[2]}  → prefers C > B > A")
print(f"Agent 2 TRUE values:  A={v2[0]}, B={v2[1]}, C={v2[2]}  → prefers B > A > C")
print(f"Agent 1 MISREPORT:    A={r1[0]}, B={r1[1]}, C={r1[2]}  → reports B > C > A")
print()

def simulate(pref1, pref2, order, label=""):
    print(f"  Order: {order}  {'('+label+')' if label else ''}")
    avail = [0, 1, 2]
    alloc1, alloc2 = [], []
    
    picks_sequence = order  # e.g. [1, 2, 1] or [2, 1, 2]
    
    for agent in picks_sequence:
        if agent == 1:
            pick = greedy_pick(pref1, avail)
            avail.remove(pick)
            alloc1.append(pick)
            print(f"    Agent 1 picks {item_name[pick]}  (remaining: {[item_name[x] for x in avail]})")
        else:
            pick = greedy_pick(pref2, avail)
            avail.remove(pick)
            alloc2.append(pick)
            print(f"    Agent 2 picks {item_name[pick]}  (remaining: {[item_name[x] for x in avail]})")
    
    util1 = sum(v1[item] for item in alloc1)
    util2 = sum(v2[item] for item in alloc2)
    print(f"    Agent 1 gets: {[item_name[x] for x in alloc1]}  → true utility = {util1}")
    print(f"    Agent 2 gets: {[item_name[x] for x in alloc2]}  → true utility = {util2}")
    return util1, util2

print("─" * 60)
print("SCENARIO A: Agent 1 REPORTS TRUTHFULLY")
print("─" * 60)
print()
u1_121_truth, _ = simulate(v1, v2, [1, 2, 1], "Agent 1 goes first")
print()
u1_212_truth, _ = simulate(v1, v2, [2, 1, 2], "Agent 2 goes first")
print()
exp_truth = 0.5 * u1_121_truth + 0.5 * u1_212_truth
print(f"  Expected utility (truth):   0.5×{u1_121_truth} + 0.5×{u1_212_truth} = {exp_truth}")

print()
print("─" * 60)
print("SCENARIO B: Agent 1 MISREPORTS (swaps B and C preference)")
print("─" * 60)
print()
u1_121_mis, _ = simulate(r1, v2, [1, 2, 1], "Agent 1 goes first")
print()
u1_212_mis, _ = simulate(r1, v2, [2, 1, 2], "Agent 2 goes first")
print()
exp_mis = 0.5 * u1_121_mis + 0.5 * u1_212_mis
print(f"  Expected utility (misrep):  0.5×{u1_121_mis} + 0.5×{u1_212_mis} = {exp_mis}")

print()
print("=" * 60)
print("VERDICT")
print("=" * 60)
print(f"  Expected utility truthful  : {exp_truth}")
print(f"  Expected utility misreport : {exp_mis}")
print(f"  Gain from lying            : {exp_mis - exp_truth} > 0  ← IC VIOLATION!")
print()
print("INTUITION:")
print("  Truthfully, agent 1 most prefers C, so they grab C first")
print("  when going first. Agent 2 then grabs B. Agent 1 is left with A in round 3.")
print()
print("  By lying and claiming to prefer B > C, agent 1 grabs B first.")
print("  Agent 2 then grabs... A (their 2nd choice). Agent 1 gets C in round 3!")
print("  Agent 1 ends up with {B, C} instead of {C, A} — strictly better!")

# Output:
# ============================================================
# COUNTEREXAMPLE TRACE
# ============================================================
# Agent 1 TRUE values:  A=3, B=4, C=5  → prefers C > B > A
# Agent 2 TRUE values:  A=2, B=3, C=1  → prefers B > A > C
# Agent 1 MISREPORT:    A=3, B=5, C=4  → reports B > C > A
# 
# ────────────────────────────────────────────────────────────
# SCENARIO A: Agent 1 REPORTS TRUTHFULLY
# ────────────────────────────────────────────────────────────
# 
#   Order: [1, 2, 1]  (Agent 1 goes first)
#     Agent 1 picks C  (remaining: ['A', 'B'])
#     Agent 2 picks B  (remaining: ['A'])
#     Agent 1 picks A  (remaining: [])
#     Agent 1 gets: ['C', 'A']  → true utility = 8
#     Agent 2 gets: ['B']  → true utility = 3
# 
#   Order: [2, 1, 2]  (Agent 2 goes first)
#     Agent 2 picks B  (remaining: ['A', 'C'])
#     Agent 1 picks C  (remaining: ['A'])
#     Agent 2 picks A  (remaining: [])
#     Agent 1 gets: ['C']  → true utility = 5
#     Agent 2 gets: ['B', 'A']  → true utility = 5
# 
#   Expected utility (truth):   0.5×8 + 0.5×5 = 6.5
# 
# ────────────────────────────────────────────────────────────
# SCENARIO B: Agent 1 MISREPORTS (swaps B and C preference)
# ────────────────────────────────────────────────────────────
# 
#   Order: [1, 2, 1]  (Agent 1 goes first)
#     Agent 1 picks B  (remaining: ['A', 'C'])
#     Agent 2 picks A  (remaining: ['C'])
#     Agent 1 picks C  (remaining: [])
#     Agent 1 gets: ['B', 'C']  → true utility = 9
#     Agent 2 gets: ['A']  → true utility = 2
# 
#   Order: [2, 1, 2]  (Agent 2 goes first)
#     Agent 2 picks B  (remaining: ['A', 'C'])
#     Agent 1 picks C  (remaining: ['A'])
#     Agent 2 picks A  (remaining: [])
#     Agent 1 gets: ['C']  → true utility = 5
#     Agent 2 gets: ['B', 'A']  → true utility = 5
# 
#   Expected utility (misrep):  0.5×9 + 0.5×5 = 7.0
# 
# ============================================================
# VERDICT
# ============================================================
#   Expected utility truthful  : 6.5
#   Expected utility misreport : 7.0
#   Gain from lying            : 0.5 > 0  ← IC VIOLATION!
# 
# INTUITION:
#   Truthfully, agent 1 most prefers C, so they grab C first
#   when going first. Agent 2 then grabs B. Agent 1 is left with A in round 3.
# 
#   By lying and claiming to prefer B > C, agent 1 grabs B first.
#   Agent 2 then grabs... A (their 2nd choice). Agent 1 gets C in round 3!
#   Agent 1 ends up with {B, C} instead of {C, A} — strictly better!
