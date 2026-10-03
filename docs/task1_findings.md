# Task 1 — Findings & Design Decisions

Detect and re-categorize mislabeled rows in the `Nature` column.
Constraint: only the 596 existing Nature labels, no new categories.

---

## Step 1 — Reconnaissance

**Goal:** understand the Nature vocabulary before writing any rules.

**What I did:**
- Loaded the parquet cache (525,034 rows).
- Wrote `src/task1_recon.py` to print:
  - Top 50 Natures with 5 sample titles each
  - Rarest 50 Natures with counts
  - 20 sample rows where `Nature` is null
  - Synonym / duplicate candidates (same normalized form)

**What I found:**

| # | Finding | Evidence |
|---|---|---|
| 1 | Source has real mis-categorization | `Nature=Friteuse` on `"Canapé fixe 2 places en tissu"` |
| 2 | Labels have inconsistent accents / case | `Canape droit` vs `Canapé d'angle`; `Tv ecran plat` |
| 3 | Null-Nature rows look administrative | `"Adhérer au programme fidélité Ma Carte Confo +"` |
| 4 | Rarest Natures are noise (1–4 rows) | `Défroisseur` and `défroisseur` as separate entries |
| 5 | Top Natures have clear leading keywords | `"Matelas ..."` → `Matelas` |
| 6 | Synonyms across Natures exist | Title `Bahut` → Nature `Buffet` |
| 7 | Truncated labels exist | `Tapis de Salon et Ch` |

**Conclusion:** the mis-categorization problem is real; rules can handle
the top classes; we need synonym mapping; nulls need separate treatment.

---

## Step 2 — Rule Table & Non-Product Filter

**Goal:** build the data the matcher will consume, and validate the
assumption that null-Nature rows are administrative.

**What I did:**
- Wrote `src/task1_rules.py` with three outputs:
  - `nature_keywords.csv` — auto-generated keyword per Nature (596 rows)
  - `nature_synonyms.csv` — hand-curated title → Nature map
  - `non_product_keywords.csv` — admin phrases (loyalty, returns, SAV)
- Reused `normalize_for_matching` from Task 2 (no duplication).
- Ran a **full coverage check**: apply the non-product filter to every
  null-Nature row.

**What I did — iterations:**

| Iteration | Action | Result |
|---|---|---|
| 1 | Sample `head(20)` of nulls | 20/20 caught → promising |
| 1 | Realized `head` is biased (rows may be sorted) | Switched to random + full coverage |
| 2 | Full coverage on 11,745 nulls | 11,635 / 11,745 (99.1%) |
| 2 | Inspected the 110 missed | All were `"Reprise de l ancien matériel"` |
| 3 | Added `"reprise"` to the keyword list | **11,745 / 11,745 (100%)** |

**What I found — the golden result:**

- **100% of null-Nature rows are non-products.** No product has a null label.
- **0 rows with non-null Nature look administrative** (verified by a
  separate scan for `programme|reprise|assistance|sav` in the Nature column).

**Why this matters:** I initially expected the nulls to be missing labels
to predict. They aren't — they're administrative rows. **Task 1 is purely
mis-categorization detection, not null-filling.** The status set simplifies.

---

## Design Decisions

1. **Three-stage pipeline:** non-product filter → rule matcher → ML fallback.
2. **ML trained only on trusted rows:** where rule and source label agree.
3. **ML runs only on rule-failed rows.**
4. **Two human-review triggers:** rule-label conflict, ML confidence < 0.7.
5. **Rare Natures preserved** but flagged for review — not deleted.
6. **Source immutable:** we add columns, never modify them.
7. **Code in English; output columns in French** (matches source language).
8. **No inference:** only extract what is literally written.

---

## Status Codes

| Status | Meaning |
|---|---|
| `non_product` | Administrative row, no prediction |
| `ok` | Rule matched + label agreed |
| `to_review_rule` | Rule matched + label differs |
| `predicted` | ML predicted, label existed |
| `to_review_ml` | ML low confidence (< 0.7) |

---

## Files Produced (Task 1 so far)

| File | Purpose |
|---|---|
| `src/task1_recon.py` | Reconnaissance script |
| `src/task1_rules.py` | Rule table generator + non-product filter |
| `output/nature_keywords.csv` | 596 Nature keywords |
| `output/nature_synonyms.csv` | Hand-curated synonym map |
| `output/non_product_keywords.csv` | Admin keyword list |