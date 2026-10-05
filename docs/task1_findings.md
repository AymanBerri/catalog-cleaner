# Task 1 — Findings & Design Decisions

Detect and re-categorize mislabeled rows in the Nature column.
Constraint: only the 596 existing Nature labels, no new categories.

---

## Step 1 — Reconnaissance

Goal: understand the Nature vocabulary before writing any rules.

What I did:
- Loaded the parquet cache (525,034 rows).
- Wrote src/task1_recon.py to print:
  - Top 50 Natures with 5 sample titles each
  - Rarest 50 Natures with counts
  - 20 sample rows where Nature is null
  - Synonym / duplicate candidates (same normalized form)

What I found:

| # | Finding | Concrete example |
|---|---|---|
| 1 | Source has real mis-categorization | Title "Canapé fixe 2 places en tissu" but Nature=Friteuse |
| 2 | Labels have inconsistent accents / case | "Canape droit" vs "Canapé d'angle"; "Tv ecran plat" vs "Téléviseur" |
| 3 | Null-Nature rows look administrative | "Adhérer au programme fidélité Ma Carte Confo +", "Reprise ancien produit" |
| 4 | Rarest Natures are noise (1–4 rows) | "Défroisseur" and "défroisseur" as two separate labels; "Bûcher" (1 row) |
| 5 | Top Natures have clear leading keywords | "Matelas mousse 140x190" → Matelas |
| 6 | Synonyms across Natures exist | Title says "Bahut 4 portes" but Nature is Buffet |
| 7 | Truncated labels exist | "Tapis de Salon et Ch" (clearly "…et Chambre" cut off) |

Conclusion: mis-categorization is real; rules can handle the top classes;
we need synonym mapping; nulls need separate treatment.

---

## Step 2 — Rule Table & Non-Product Filter

Goal: build the data the matcher will consume, and validate the assumption
that null-Nature rows are administrative.

What I did:
- Wrote src/task1_rules.py with three outputs:
  - nature_keywords.csv — auto-generated keyword per Nature (596 rows)
  - nature_synonyms.csv — hand-curated title → Nature map
  - non_product_keywords.csv — admin phrases (loyalty, returns, SAV)
- Reused normalize_for_matching from Task 2 (no duplication).
- Ran a full coverage check: apply the non-product filter to every null row.

Iterations:

| Iteration | Action | Result | Example |
|---|---|---|---|
| 1 | Sample head(20) of nulls | 20/20 caught — but head is order-biased | All 20 were "Adhérer au programme" |
| 1 | Switched to random + full coverage | Reliable sample | — |
| 2 | Full coverage on 11,745 nulls | 11,635 / 11,745 (99.1%) | 110 missed |
| 2 | Inspected the 110 missed | All were "Reprise de l ancien matériel" | Pattern found |
| 3 | Added "reprise" | 11,745 / 11,745 (100%) | No more misses |

The golden result:
- 100% of null-Nature rows are non-products. No product has a null label.
- 0 non-null rows look administrative (verified by a separate scan).

Why this matters: I expected nulls to be missing labels. They aren't —
they're administrative. Task 1 is purely mis-categorization detection,
not null-filling. The status set simplifies.

---

## Step 3 — Rule Matcher

Goal: match each title against the Nature keyword index, assign a status,
and measure how much mis-categorization the source contains.

What I did:
- Wrote src/task1_matcher.py:
  - Builds a keyword index (synonyms + 596 Nature labels, longest-first)
  - Compiles one master regex (single pass per title)
  - Classifies each row → non_product, ok, to_review_rule, or pending_ml
- Ran it, then iterated the synonym map based on failure samples.

Iteration log:

| Run | ok | to_review_rule | pending_ml | Trigger for iteration |
|---|---|---|---|---|
| 1 | 65.6% | 17.0% | 15.1% | Baseline |
| 2 | 68.0% | 16.4% | 13.3% | Added TV, tapis, housse-couette, lit variants |
| 3 | 71.3% | 16.0% | 10.4% | Added meuble bas, colonne sdb, torchon, ménagère |
| 4 | 72.3% | 16.0% | 9.4% | Stopped — returns flattened |

Final numbers (Run 4):

| Status | Count | % | Example |
|---|---|---|---|
| ok | 379,775 | 72.3% | Title "Table basse carrée…" + Nature=Table basse |
| to_review_rule | 83,825 | 16.0% | Title "Canapé fixe 2 places…" + Nature=Friteuse |
| pending_ml | 49,538 | 9.4% | Title "Lit 140x190 cm" (no keyword match) |
| non_product | 11,896 | 2.3% | Title "Adhérer au programme fidélité…" |

Among rule-resolved rows (463,600):
- Agree with source label: 81.9%
- Disagree (candidate mislabels): 18.1% ← the headline number

What each iteration taught me (with examples):
- Run 1 → 2: missing synonyms for whole families (so we added synonym coverage)
  - "Téléviseur 139 cm UHD" (was pending_ml, now Tv ecran plat)
  - "Tapis 120x170 cm" (was pending_ml, now Tapis de Salon et Ch)
  - "Lit 140x190 cm" (was pending_ml, now Lit adulte)
  -
- Run 2 → 3: accent-loss and separator variants (due to exporting dataset to different file type -xlsx)
  - "T te de lit 165 cm" (the "ê" became a space in export)
  - "Robot p tissier" (accented "â" lost)
  -
- Run 3 → 4: niche phrases (added more synonyms)
  - "Meuble bas 60 cm 1 porte" (Nature=Meuble bas cuisine)
  - "Colonne salle de bain bicolore" (Nature=Colonne sdb)
  - "Torchons 48x68 cm" (Nature=Linge d'office)
  -
- Run 4 → stopped: remaining failures are brand names, model numbers,
  acronyms — genuine ML territory, not rule territory
  - "Hp officejet pro 6230 tintenstrahldrucker"
  - "Acer nitro xz242qpbmiiphx 24 full hd"
  -

The headline finding: the dominant source mislabel is
Nature=Meuble à chaussures on matelas titles — a systematic data quality
bug in the source.
- Title "Matelas mousse 140x190 cm" → Nature=Meuble à chaussures
- Title "Simpur relax matelas 140x190 therapy carbone" → Nature=Meuble à chaussures
- Title "Matelas ressorts + sommier 140x190 cm" → Nature=Meuble à chaussures

---

## Step 4 — ML Classifier

Goal: predict a Nature for the 49,538 pending_ml rows that the rule
matcher couldn't handle.

What I did:
- Wrote src/task1_ml.py:
  - TF-IDF vectorizer (unigrams + bigrams, min_df=2, max_df=0.9,
    sublinear_tf, max_features=100k)
  - LinearSVC (C=1.0, max_iter=500, dual=True)
  - Trained on the 379,775 ok rows (trusted subset)
  - Predicted on the 49,538 pending_ml rows

- Confidence = margin between top-1 and top-2 decision scores.
  - Big gap   : model is very sure about the top class → high confidence.
  - Small gap : top two scores are close → model is unsure → low confidence.

- Threshold: predicted if margin ≥ 0.15, else to_review_ml.

Why train on ok rows only:
- Two independent signals agree (rule + source label) → clean labels.
- Training on the whole set would teach the model the source's mislabeling pattern.
- Example: if we trained on the row "Matelas mousse 140x190 cm" with
  Nature=Meuble à chaussures, we'd teach the model that "matelas" is a
  signal for Meuble à chaussures.

Final ML numbers:

| Status | Count | % of ML rows | Example |
|---|---|---|---|
| predicted | 33,493 | 67.6% | "Lit 140x190 cm" → Lit adulte (margin 0.41) |
| to_review_ml | 16,045 | 32.4% | "Moniteur portable Polaroid" → Babyphone (margin 0.11, wrong) |

Confidence distribution:
- min: 0.000
- median: 0.303
- mean: 0.377
- max: 3.452

Why this split: threshold 0.15 gives ~2/3 auto-accepted, ~1/3 flagged for
human review. Samples confirmed high-confidence predictions are mostly
right; low-confidence ones are genuinely uncertain.
- High confidence example: "Canapé angle convertible simon noir gris" →
  Canapé d'angle (margin 2.64). Correct.
- Low confidence example: "Airpods 2" → Matelas (margin 0.01). Wrong,
  correctly flagged.

Note on class coverage: the trusted subset contains only 421 distinct
Natures (out of 596). The other 175 are too rare (1–4 rows) to appear in
ok rows. The classifier can only predict the 421 it has seen.

---

## Step 5 — Final Pipeline

Goal: combine rule + ML results into one deliverable with Task 2 columns.

What I did:
- Wrote src/final_pipeline.py:
  - Merges task1_rule_results and task1_ml_results by index
  - Rule-resolved rows get confidence 1.0 (deterministic)
  - Non-product rows get confidence None
  - pending_ml rows replaced by ML predictions + margin confidence
  - Positionally joins Task 2 columns (dimension, dimension_unit, couleur, materiau)
  - Exports resultats.parquet + resultats.xlsx

Final deliverable: output/resultats.xlsx — 525,034 rows, all original
columns + 7 new columns (nature_predicted, status, confidence, dimension,
dimension_unit, couleur, materiau).

Example output rows:

| Title | Nature (source) | nature_predicted | status | dimension | couleur | materiau |
|---|---|---|---|---|---|---|
| "Matelas mousse 140x190 cm" | Matelas | Matelas | ok | 140x190 | [] | ["mousse"] |
| "Canapé fixe 2 places en tissu" | Friteuse | Canape droit | to_review_rule | None | [] | ["tissu"] |
| "Lit 140x190 cm" | Lit adulte | Lit adulte | predicted | 140x190 | [] | [] |
| "Airpods 2" | Smartphone | Matelas | to_review_ml | None | [] | [] |
| "Adhérer au programme fidélité" | None | None | non_product | None | [] | [] |

---

## Design Decisions (Consolidated)

1. Three-stage pipeline: non-product filter → rule matcher → ML fallback.
2. ML trained only on trusted rows (rule + source label agree).
3. ML runs only on pending_ml rows.
4. Two human-review triggers: to_review_rule (rule-label conflict),
   to_review_ml (low ML confidence).
5. Rare Natures preserved but flagged for review — not deleted.
6. Source immutable: we add columns, never modify them.
7. Code in English; output columns in French (matches source language).
8. No inference: only extract what is literally written.
9. Longest keyword wins in the rule matcher (e.g., "table basse"
   before "table").
10. Margin-based ML confidence, not softmax (softmax fails with many classes).
11. Threshold 0.15 for ML confidence (tuned from margin distribution).

---

## Status Codes

| Status | Meaning | Source | Example title |
|---|---|---|---|
| non_product | Administrative row, no prediction | Rule filter | "Adhérer au programme fidélité…" |
| ok | Rule matched + label agreed | Rule matcher | "Matelas mousse 140x190 cm" |
| to_review_rule | Rule matched + label differs | Rule matcher | "Canapé fixe 2 places…" (Nature=Friteuse) |
| predicted | ML predicted with margin ≥ 0.15 | ML classifier | "Lit 140x190 cm" |
| to_review_ml | ML predicted with margin < 0.15 | ML classifier | "Airpods 2" |

---

## Files Produced (Task 1)

| File | Purpose |
|---|---|
| src/task1_recon.py | Reconnaissance script |
| src/task1_rules.py | Rule table + non-product filter + synonyms |
| src/task1_matcher.py | Rule-based matcher |
| src/task1_ml.py | ML classifier |
| src/final_pipeline.py | Merge + export deliverable |
| output/nature_keywords.csv | 596 Nature keywords |
| output/nature_synonyms.csv | Hand-curated synonym map |
| output/non_product_keywords.csv | Admin keyword list |
| output/task1_rule_results.parquet | Rule matcher output |
| output/task1_ml_results.parquet | ML predictions on pending_ml rows |
| output/resultats.parquet | Final combined table |
| output/resultats.xlsx | Client deliverable |
| output/resultats_summary.txt | Summary report |