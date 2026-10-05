# catalog-cleaner

Data cleaning and catalog enrichment for furniture marketplace listings.

**What it does:**
- **Task 2** — extracts `dimension`, `unit`, `color`, and `material` from product titles.
- **Task 1** — detects mis-categorized products and re-assigns them to the correct `Nature` (596 existing labels, no new categories).

**Input:** 525,034 sales lines from a furniture marketplace.
**Output:** `output/resultats.xlsx` — the source data with 7 new columns.

---

## Results at a glance

| Task | Result |
|---|---|
| Task 2 — dimension | 42.4% of titles (unit captured separately: 78.7% cm, 0.3% mm) |
| Task 2 — color | 22.9% of titles |
| Task 2 — material | 25.2% of titles |
| Task 1 — rule matcher | 72.3% auto-resolved |
| Task 1 — mislabel rate | 18.1% of rule-resolved rows disagree with the source label |
| Task 1 — ML fallback | 6.4% auto-accepted, 3.1% flagged for review |

---

## Pipeline

```
Raw sales.xlsx (525,034 rows)
        │
        ▼
[load_data]       → convert to Parquet for fast iteration
        │
        ▼
┌───────────────────────────────────────────────┐
│  Task 2 — Extraction                          │
│                                               │
│  1. Dimension   (regex cascade)               │
│  2. Color       (dictionary)                  │
│  3. Material    (dictionary)                  │
└───────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────┐
│  Task 1 — Mis-categorization                  │
│                                               │
│  1. Non-product filter  (admin rows)          │
│  2. Rule matcher        (72.3% auto-resolved) │
│  3. ML classifier       (for the leftover)    │
└───────────────────────────────────────────────┘
        │
        ▼
[final_pipeline]  → resultats.parquet + resultats.xlsx
```

---

## Project structure

```
catalog-cleaner/
├── src/
│   ├── load_data.py            # xlsx → parquet cache + EDA
│   ├── preprocess.py           # two normalization functions
│   ├── config.py               # Task 2 lexicons + regex
│   ├── task2_extraction.py     # extract_dimension / colors / materials
│   ├── run_task2.py            # Task 2 pipeline + coverage report
│   ├── task1_recon.py          # Task 1 reconnaissance
│   ├── task1_rules.py          # rule table + synonyms + non-product filter
│   ├── task1_matcher.py        # Task 1 rule-based matcher
│   ├── task1_ml.py             # Task 1 ML classifier
│   └── final_pipeline.py       # merge everything + export
├── tests/
│   └── test_task2.py           # 28 unit tests
├── docs/
│   ├── task1_findings.md       # Task 1 design + results
│   └── task2_findings.md       # Task 2 design + results
├── output/                     # gitignored (results live here)
├── data/
│   ├── raw/                    # gitignored (client data)
│   └── processed/              # gitignored (parquet cache)
├── conftest.py
├── requirements.txt
└── README.md
```

---

## Quickstart

### 1. Clone the repository

```bash
git clone https://github.com/AymanBerri/catalog-cleaner.git
cd catalog-cleaner
```

### 2. Set up the environment

```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows
# source .venv/bin/activate      # macOS / Linux

pip install -r requirements.txt
```

### 3. Add the source file

Place `sales.xlsx` in `data/raw/`.

*(The file is not committed — client data is gitignored.)*

### 4. Run the full pipeline

```bash
# 1. Load + cache the source data (once, ~3 min for 525k rows)
python src/load_data.py

# 2. Task 2 — extract dimension, unit, color, material (~1 min)
python -m src.run_task2

# 3. Task 1 — rule matcher (~40 sec)
python -m src.task1_matcher

# 4. Task 1 — ML classifier (~3–5 min)
python -m src.task1_ml

# 5. Merge into the final deliverable (~4–8 min)
python -m src.final_pipeline
```

**Output:** `output/resultats.xlsx` — 525,034 rows, 17 columns.

### Run the tests

```bash
pytest tests/
```
---

## Final output

`output/resultats.xlsx` — 525,034 rows, 17 columns.

**Original columns (unchanged):**
`Cod_cmd`, `Libellé produit`, `Vendeur`, `Univers`, `Nature`, `Date de commande`, `Montant cmd`, `Quantité`, `Prix transport`, `Délai transport annoncé`

**New columns:**

| Column | Description | Example |
|---|---|---|
| `dimension` | Extracted dimension | "140x190" |
| `dimension_unit` | Unit from source | "cm" |
| `couleur` | Extracted colors (list) | ["blanc", "gris"] |
| `materiau` | Extracted materials (list) | ["bois"] |
| `nature_predicted` | Our predicted Nature (rule or ML) | "Table basse" |
| `status` | How the prediction was made | `ok`, `to_review_rule`, `predicted`, `to_review_ml`, `non_product` |
| `confidence` | 1.0 for rules, margin for ML, null for non-products | 0.84 |

### Example rows

| Libellé produit | Nature (source) | nature_predicted | status | conf | dimension | unit | couleur | materiau |
|---|---|---|---|---|---|---|---|---|
| "Matelas mousse 140x190 cm" | Matelas | Matelas | ok | 1.0 | 140x190 | cm | [] | ["mousse"] |
| "Table basse effet chêne en MDF noir 60x50x40cm" | Table basse | Table basse | ok | 1.0 | 60x50x40 | cm | ["chene", "noir"] | ["mdf"] |
| "Ours en peluche géant 150 cm brun" | Peluche | Peluche | ok | 1.0 | 150 | cm | ["brun"] | [] |
| "Canapé fixe 2 places en tissu" | Friteuse | Canape droit | to_review_rule | 1.0 | — | — | [] | ["tissu"] |
| "Lit 140x190 cm" | Lit adulte | Lit adulte | predicted | 0.41 | 140x190 | cm | [] | [] |
| "Airpods 2" | Smartphone | Matelas | to_review_ml | 0.01 | — | — | [] | [] |
| "Adhérer au programme fidélité" | — | — | non_product | — | — | — | [] | [] |
| "Fauteuil patchwork bleu et gris" | Fauteuil | Fauteuil | ok | 1.0 | — | — | ["bleu", "gris"] | [] |
| "Meuble tv falko bois blanc et gris 180 cm" | Meuble tv | Meuble tv | ok | 1.0 | 180 | cm | ["blanc", "gris"] | ["bois"] |
| "Roues gonflables 260mm pour diable" | Accessoire | Accessoire | ok | 1.0 | 260 | mm | [] | [] |

---

## Task 2 — Extraction

**Goal:** for each title, extract `dimension`, `dimension_unit`, `color`,
and `material` from the product title.

### Approach

- **Dimension + unit** — regex cascade, specific-first, with false-positive
  guards. The unit (`cm` or `mm`) is captured and stored separately — no
  conversion, no guessing.
- **Color / Material** — dictionary matching with phrase priority (multi-word
  phrases before single words).
- **Normalization** — two functions: one aggressive (for colors/materials,
  strips accents), one conservative (for dimensions, preserves `x`/`×`/`*`
  and digits).
- **Rule:** only extract what's literally written. Never infer.

### Coverage

| Field | Rows found | Coverage |
|---|---|---|
| Dimension | 222,655 | 42.4% |
| Color | 120,150 | 22.9% |
| Material | 132,486 | 25.2% |

**Unit distribution (dimensions only):**
- `cm` — 175,190 rows (78.7%)
- `mm` — 736 rows (0.3%)
- *(no unit in title)* — 46,729 rows (21.0%)

**Key design choices:**
- Regex over LLM — deterministic, fast (30 sec on 525k rows), explainable.
- Wood tones (chêne, noyer) count as colors — industry convention, matches
  Amazon.fr.
- Lists, not single values — products are often multi-color or multi-material.
- Separate `dimension_unit` column — preserves the source's unit instead of
  assuming.

### Known limitations

- **"140 190"** (dimension without "x") — measured at 0.86% of rows, mostly
  false positives. Documented, not fixed.
- **Other units ("m", "pouces")** — 90%+ false positives in the data (m³/h
  airflow, m² area, TV size in inches). Rejected.

Full details: [`docs/task2_findings.md`](docs/task2_findings.md).

---

## Task 1 — Mis-categorization

**Goal:** find and fix rows where the source `Nature` is wrong, using only the 596 existing Nature labels.

### Approach

Three stages, applied in order:

1. **Non-product filter** — administrative rows (loyalty signups, returns) are identified and excluded from prediction.
2. **Rule matcher** — the title is matched against a keyword index (synonyms + 596 Nature labels, longest-first). This resolves ~72% of the dataset deterministically.
3. **ML classifier** — for the remaining rows, a TF-IDF + LinearSVC model predicts a Nature. Trained only on trusted rows (rule + source label agree), so the model learns clean patterns.

### Status codes

| Status | Meaning | Count | % |
|---|---|---|---|
| `ok` | Rule matched + source label agreed | 379,775 | 72.3% |
| `to_review_rule` | Rule matched + source label differs | 83,825 | 16.0% |
| `predicted` | ML predicted with confidence ≥ 0.15 | 33,493 | 6.4% |
| `to_review_ml` | ML predicted with confidence < 0.15 | 16,045 | 3.1% |
| `non_product` | Administrative row, no prediction | 11,896 | 2.3% |

**Headline number:** among rule-resolved rows, **18.1% disagree** with the source label — that's the measured mis-categorization rate.

**Key finding:** the dominant source error is `Nature=Meuble à chaussures` applied to matelas titles — a systematic data quality bug.

Full details: [`docs/task1_findings.md`](docs/task1_findings.md).

---

## Tech stack

- **Python 3.11**
- **pandas** — data manipulation
- **pyarrow** — Parquet read/write
- **scikit-learn** — TF-IDF + LinearSVC (Task 1 ML)
- **openpyxl** — Excel read/write
- **pytest** — 28 unit tests for Task 2 extractors
- **tqdm** — progress bars

## Design principles

| Principle | Applied |
|---|---|
| Source is immutable | New columns only. Never modify the input. |
| Reproducibility | `requirements.txt` with pinned versions |
| Iterative coverage | Sample failures → expand lexicon → re-run |
| Measure before fixing | No pattern added without first measuring its frequency |
| Right tool for the job | Regex for patterns, ML for the long tail, no LLM |
| Testability | TDD for pure functions (Task 2 extractors) |

---

## Author

Built as a technical evaluation project.

For questions about the design decisions, see the two findings docs in `docs/`.