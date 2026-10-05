# Task 2 — Findings & Design Decisions

Extract dimension, color, and material from product titles.
Rule: only extract what is literally written — never infer.

---

## What We Extract

| Field | Type | Example |
|---|---|---|
| dimension | String or null | "140x190" |
| dimension_unit | String or null | "cm", "mm" |
| couleur | List | ["blanc", "noir"] |
| materiau | List | ["métal"] |

Why these four:
- dimension + couleur → what the client asked for.
- dimension_unit → keeps the unit the source used (no guessing).
- materiau → bonus, resolves the "oak-look plastic" case.


---

## Design Choices

### 1. Regex, not LLM

Regex is deterministic, fast (~30 seconds for 525k rows), explainable, and
free. An LLM would take hours, cost money, and produce different outputs
on different runs.

Example:
Input: "Matelas mousse 140x190 cm" → Regex returns "140x190" every time.

### 2. Separate fields for color and material

A table can look like oak but be made of plastic. Two different truths.

Example:
"Table effet chêne en PVC"
→ couleur = ["chêne"]  (what it looks like)
→ materiau = ["PVC"]   (what it's made of)

### 3. Wood tones count as colors

In furniture, wood tone IS the color. Shoppers browse by appearance.
Amazon.fr lists Chêne, Noyer, Sonoma alongside Noir, Blanc.

Example:
"Table basse chêne sonoma" → couleur = ["chêne", "sonoma"]

### 4. Lists, not single values

Products are often multi-color.

Example:
"Fauteuil patchwork bleu et gris" → couleur = ["bleu", "gris"]

### 5. Regex cascade, specific first

Patterns are tried from most specific to least:

1. "L 110 x P 60 x H 36 cm"  (labeled 3D)
2. "90x50x45 cm"              (plain 3D)
3. "140x190 cm"               (plain 2D)
4. "80 cm"                    (single)

Why order matters: if the loose pattern ran first, "L 110 x P 60 x H 36 cm"
would match just "110 cm" and truncate.

### 6. False-positive guards

A number is a dimension ONLY if it has an x/×/* separator OR a cm/mm unit.

Rejected examples:
- "Lot de 2 tables" (2 is a quantity)
- "3 tiroirs" (count)
- "4 personnes" (capacity)
- "5 niveaux" (count)

Most of the work in regex is rejecting invalid matches.

### 7. Never infer

Only extract what is literally written.

Example:
"Table en chêne massif"
→ couleur = ["chêne"]
→ materiau = ["chêne massif"]
→ NOT "marron" (that would be inference)

### 8. Two normalization functions

preprocess.py has two functions, each tuned to its task:

- normalize_for_matching: lowercase + strip accents + remove punctuation.
  Used for color/material matching ("chêne" → "chene").
- normalize_light: lowercase + collapse spaces only. Preserves digits, "x",
  "×", "*", "cm". Used for dimension extraction.

Each normalization fits its consumer.

---

## Process — Test-Driven Development

Wrote tests first, using real examples from the dataset. Then wrote code
to make them pass. 28 tests cover dimensions, colors, materials.

Regex is fragile — small edits break old cases. Tests are the regression
guard.

### The "blanches" bug

Test: extract_colors("Lot de 2 tables blanches") should return ["blanc"].

It failed. French colors change with gender and number
(blanc → blanche → blanches). The lexicon stored only the masculine
singular, and the regex used exact word boundaries (\bblanc\b), which
missed "blanches".

Fix: switch to stem matching — a leading word boundary only (\bblanc).
One lexicon entry now matches every French variant. The test stayed
unchanged — the code was fixed.

That's the value of TDD: the test encoded a real requirement, and the fix
went into the code, not the test.

---

## Results on the Full Dataset

After running on 525,034 rows:

| Field | Rows found | Coverage |
|---|---|---|
| Dimension | 222,655 | 42.4% |
| Color | 120,150 | 22.9% |
| Material | 132,486 | 25.2% |

Coverage is limited by the data. Many titles genuinely don't mention a
color or dimension. 100% isn't achievable.

Sample failures were inspected manually (15 rows per extractor). Most
were correct behavior — the extractor rejected false positives like
"Lot de 2" and "4 foyers". One real gap was found (see below).

---

## Known Limitations

### The "140 190" case (missing "x")

Some titles write "140 190" instead of "140x190". I measured this:
4,497 rows (0.86% of the dataset). Visual inspection showed most are NOT
real dimensions — they're serial numbers, capacity ranges, or wattage.

Adding a pattern would introduce false positives like "6-8 personnes" and
"425w". Not worth the trade-off for 0.86% of rows. Documented, not fixed.

### Other units — "m" and "pouces"

- Meters (m): 2,186 titles, but 90% are false positives — airflow rates
  (m³/h), area (m²), or per-meter pricing.
- Inches (pouces): 2,387 titles, but describe the TV size the furniture
  supports ("meuble TV jusqu'à 48 pouces"), not the furniture's own size.

Both rejected. The cm/mm pair covers all real furniture dimensions here.


---

## Files Produced

| File | Purpose |
|---|---|
| src/config.py | Color + material lexicons, regex patterns |
| src/preprocess.py | Two normalization functions |
| src/task2_extraction.py | The three extractors |
| tests/test_task2.py | 28 TDD tests |
| src/run_task2.py | Pipeline runner + coverage report |
| output/task2_results.parquet | 525k rows with 4 new columns |
| output/task2_coverage.txt | Coverage statistics |

---

## One-Sentence Summary

> Extract dimension, color, and material from product titles using a
> specific-first regex cascade, with false-positive guards and literal-only
> extraction — chosen over an LLM for speed, determinism, and explainability.