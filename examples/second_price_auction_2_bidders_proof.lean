-- Mechanism: Second-Price Auction (2 Bidders)
-- Verdict:   TRUTHFUL
-- ==========================================================


import Mathlib.Algebra.Order.Ring.Lemmas

/-!
## Second-Price Auction with 2 Bidders — Strategy-Proofness

Setup:
  - Agent 1 has true valuation `v`, bids truthfully or misreports `r`.
  - Agent 2 bids `p` (the "price" / opponent's bid).
  - Allocation: highest bid wins (ties go to agent 1, i.e. bid ≥ p wins).
  - Payment: winner pays the opponent's bid `p`.
  - Utility: (v - p) if bid ≥ p, else 0.
-/

noncomputable def sp_util (v b p : ℝ) : ℝ :=
  if b ≥ p then v - p else 0

/-- Second-price auction is strategy-proof:
    For any true valuation v, opponent bid p, and misreport r,
    truth-telling utility ≥ misreport utility. -/
theorem sp_truthful (v p r : ℝ) : sp_util v v p ≥ sp_util v r p := by
  unfold sp_util
  by_cases hv : v ≥ p
  · -- Truth-telling WINS (v ≥ p)
    simp only [hv, ite_true]
    by_cases hr : r ≥ p
    · -- Misreport also wins: same utility (v - p)
      simp only [hr, ite_true]
      exact le_refl _
    · -- Misreport loses: utility 0 ≤ v - p
      simp only [hr, ite_false]
      linarith
  · -- Truth-telling LOSES (v < p)
    push_neg at hv
    simp only [show ¬(v ≥ p) from not_le.mpr hv, ite_false]
    by_cases hr : r ≥ p
    · -- Misreport wins: utility v - p < 0, but truth utility = 0 ≥ v - p
      simp only [hr, ite_true]
      linarith
    · -- Misreport also loses: 0 ≥ 0
      simp only [hr, ite_false]
      exact le_refl _
