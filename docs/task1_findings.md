# Task 1 — Reconnaissance Findings

## Summary

Load the 525,034-row dataset and inspect the Nature vocabulary before building
the rule matcher and ML classifier.

## Findings

### 1. Source data has real mis-categorization
- Nature=`Friteuse` appears on title `"Canapé fixe 2 places en tissu"`
- Nature=`Meuble à chaussures` appears on matelas titles
- This is the problem Task 1 solves.

### 2. Nature labels have inconsistent accents and case
- `Canape droit` vs `Canapé d'angle`
- `Bibliotheque` vs (titles say) `Bibliothèque`
- `Tv ecran plat`, `Meuble tv`, `Meuble TV` mixed capitalization
- → Matcher must be accent-insensitive and case-insensitive.

### 3. Null-Nature rows are mostly non-products
- `"Adhérer au programme fidélité Ma Carte Confo +"`
- `"Reprise ancien produit"`
- `"1 an d assistance Téléphonique PC"`
- → Add a non-product pre-filter; don't try to predict their Nature.

### 4. Rarest Natures are noise
- 50 rarest have 1–4 rows
- Duplicates by case: `Défroisseur` / `défroisseur`
- → ML can't learn them. Flag low-confidence predictions for review.

### 5. Top Natures have clear leading keywords
- `"Matelas ..."` → `Matelas`
- `"Table basse ..."` → `Table basse`
- → Rule-based matcher will handle ~70% of rows.

### 6. Synonyms across Natures exist
- Title `Bahut` → Nature `Buffet`
- Title `Table de cuisson` → Nature `Plaque de cuisson`
- → Add a synonym map.

### 7. Truncated labels
- `Tapis de Salon et Ch` (truncated)
- → Document, don't modify. Source is immutable.

## Design Decisions

1. Three-stage pipeline: non-product filter → rule matcher → ML fallback.
2. ML trained on trusted subset (rows where rule agrees with source label).
3. Two human-review triggers: rule-label conflict, ML low-confidence.
4. Rare Natures preserved but flagged for review.
5. Source columns untouched — new columns added only.

## Status Codes

| Status | Meaning |
|---|---|
| `non_product` | Administrative row, no prediction |
| `ok` | Rule matched + label agreed |
| `null_corrected` | Rule matched + label was null → filled |
| `to_review_rule` | Rule matched + label differs |
| `null_predicted` | ML confident + label was null |
| `predicted` | ML confident + label existed |
| `to_review_ml` | ML low confidence |