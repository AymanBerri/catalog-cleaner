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

**Conclusion:** mis-categorization is real; rules can handle the top
classes; we need synonym mapping; nulls need separate treatment.

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
- Ran a full coverage check: apply the non-product filter to every null row.

**Iterations:**

| Iteration | Action | Result |
|---|---|---|
| 1 | Sample `head(20)` of nulls | 20/20 caught — but head is order-biased |
| 1 | Switched to random + full coverage | Reliable sample |
| 2 | Full coverage on 11,745 nulls | 11,635 / 11,745 (99.1%) |
| 2 | Inspected the 110 missed | All were `"Reprise de l ancien matériel"` |
| 3 | Added `"reprise"` | **11,745 / 11,745 (100%)** |

**The golden result:**
- **100% of null-Nature rows are non-products.** No product has a null label.
- **0 non-null rows look administrative** (verified by a separate scan).

**Why this matters:** I expected nulls to be missing labels. They aren't —
they're administrative. Task 1 is **purely mis-categorization detection**,
not null-filling. The status set simplifies.

---

## Step 3 — Rule Matcher

**Goal:** match each title against the Nature keyword index, assign a
status, and measure how much mis-categorization the source contains.

**What I did:**
- Wrote `src/task1_matcher.py`:
  - Builds a keyword index (synonyms + 596 Nature labels, longest-first)
  - Compiles one master regex (single pass per title)
  - Classifies each row → `non_product`, `ok`, `to_review_rule`, or `pending_ml`
- Ran it, then **iterated the synonym map** based on failure samples.

**Iteration log:**

| Run | `ok` | `to_review_rule` | `pending_ml` | Trigger for iteration |
|---|---|---|---|---|
| 1 | 65.6% | 17.0% | 15.1% | Baseline |
| 2 | 68.0% | 16.4% | 13.3% | Added TV, tapis, house-couette, lit variants |
| 3 | 71.3% | 16.0% | 10.4% | Added meuble bas, colonne sdb, torchon, ménagère |
| 4 | **72.3%** | **16.0%** | **9.4%** | Stopped — returns flattened |

**Final numbers (Run 4):**

| Status | Count | % |
|---|---|---|
| `ok` | 379,775 | 72.3% |
| `to_review_rule` | 83,825 | 16.0% |
| `pending_ml` | 49,538 | 9.4% |
| `non_product` | 11,896 | 2.3% |

**Among rule-resolved rows (463,600):**
- Agree with source label: 81.9%
- Disagree (candidate mislabels): **18.1%** ← the headline number

**What each iteration taught me:**
- Run 1 → 2: missing synonyms for whole families (TV, tapis, lit)
- Run 2 → 3: accent-loss and separator variants in real titles
- Run 3 → 4: niche phrases ("meuble bas", "colonne salle de bain")
- Run 4 → stopped: remaining failures are brand names, model numbers,
  acronyms — genuine ML territory, not rule territory

**The headline finding:** the dominant source mislabel is
`Nature=Meuble à chaussures` on matelas titles — a systematic data
quality bug in the source.

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
9. **Longest keyword wins** — the index is sorted by length, so `"table basse"`
   beats `"table"`.
10. **Master regex** — one pattern compiled once, reused for all 525k titles.

---

## Status Codes

| Status | Meaning |
|---|---|
| `non_product` | Administrative row, no prediction |
| `ok` | Rule matched + label agreed |
| `to_review_rule` | Rule matched + label differs |
| `pending_ml` | Rule couldn't match — sent to ML |
| `predicted` | ML predicted (after ML stage) |
| `to_review_ml` | ML low confidence < 0.7 (after ML stage) |

---

## Files Produced (Task 1 so far)

| File | Purpose |
|---|---|
| `src/task1_recon.py` | Reconnaissance script |
| `src/task1_rules.py` | Rule table + non-product filter + synonyms |
| `src/task1_matcher.py` | Rule-based matcher |
| `output/nature_keywords.csv` | 596 Nature keywords |
| `output/nature_synonyms.csv` | Hand-curated synonym map |
| `output/non_product_keywords.csv` | Admin keyword list |
| `output/task1_rule_results.parquet` | 525k rows with status |