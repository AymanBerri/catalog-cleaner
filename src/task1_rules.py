"""
Task 1 — Generate the rule table.

For each of the 596 Natures, derive a keyword (the Nature label itself, normalized). 

Then attach a manually made synonym map and a non-product
keyword list. Save everything to output/nature_keywords.csv for review.
"""

from pathlib import Path
import pandas as pd

from src.preprocess import normalize_for_matching   # Whole reason to start with task2 before 1

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

NATURE_KEYWORDS_CSV = OUTPUT_DIR / "nature_keywords.csv"
NON_PRODUCT_CSV = OUTPUT_DIR / "non_product_keywords.csv"

NATURE_COL = "Nature"


# ---------------------------------------------------------------------
# Synonym map: title word(s) -> canonical Nature
# ---------------------------------------------------------------------
# Anything the title says that maps to a Nature different from what the
# Nature label literally is.
#
#   These list were created only after analyzing the recon output, 
#     and is updated through iteration.
# ---------------------------------------------------------------------
SYNONYMS = {
    # Buffet family
    "bahut": "Buffet",
    "enfilade": "Buffet",

    # Table family
    "table a cafe": "Table basse",
    "table de salon": "Table basse",
    "table de cuisine": "Table",
    "table de salle a manger": "Table",
    "table a manger": "Table",
    "table repas": "Table",

    # Plaque de cuisson family
    "table de cuisson": "Plaque de cuisson",
    "plaque induction": "Plaque de cuisson",

    # Canape family
    "canape fixe": "Canape droit",
    "canape convertible": "Canape droit",
    "canape clic clac": "Canape droit",
    "canape d angle": "Canapé d'angle",

    # Lit family
    "lits superposes": "Lit jeune",
    "lit mezzanine": "Lit jeune",
    "lit combine": "Lit jeune",
    "lit junior": "Lit jeune",
    "lit coffre": "Lit adulte",
    "rideaux cabane": "Lit jeune",

    # Chaise family
    "fauteuil de bureau": "Chaise de bureau",

    # Meuble tv family
    "meuble tele": "Meuble tv",
    "banc tv": "Meuble tv",

    # Table de chevet
    "table de chevet": "Chevet",
    "table de nuit": "Chevet",

    # Sommier
    "sommier tapissier": "Sommier",
    "cadre a lattes": "Cadre à lattes",

    # Etagere
    "etagere murale": "Etagère",

    # Tapis
    "tapis de salon": "Tapis de Salon et Ch",

    # Porte manteau
    "portemanteau": "Porte manteau",

    # Refrigerateur
    "frigo": "Refrigerateur",

    # Lave-vaisselle
    "lave vaisselle": "Lave vaisselle",

    # --- NEW ADDITIONS from pending_ml & to_review_rule samples ---

    # TV family
    "televiseur": "Tv ecran plat",
    "tv": "Tv ecran plat",
    "ecran plat": "Tv ecran plat",

    # Housse de couette
    "parure de couette": "Housse de couette",

    # Chiffonnier ≈ commode
    "chiffonnier": "Commode",

    # Bathroom furniture
    "meuble sous vasque": "Rangement sdb",
    "vasque": "Rangement sdb",

    # Notes: 
    # Lit generic fallback (must be last resort — 3 chars, high false-match risk)
    # "lit" is intentionally NOT added here to avoid matching "litre", "litige", etc.
    # Instead, "lit 140x190" style titles will match via more specific synonyms
    # or fall through to pending_ml for the ML stage to handle.
}


# ---------------------------------------------------------------------
# Non-product keywords — administrative rows, not products
# ---------------------------------------------------------------------
NON_PRODUCT_KEYWORDS = [
    "adherer au programme",
    "programme fidelite",
    "ma carte confo",
    "reprise",                 # ← catches all reprise variants
    "1 an d assistance",
    "1 an d'assistance",
    "assistance telephonique",
    "extension de garantie",
    "sav",
]


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def is_non_product(title: str) -> bool:
    """Check if a title matches any non-product keyword (normalized).
        Returns True is the title is adminstrative.

    """
    if title is None or not isinstance(title, str): #not a string
        return False
    norm = normalize_for_matching(title)
    return any(kw in norm for kw in NON_PRODUCT_KEYWORDS)


def generate_nature_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a table of:
      nature (original), keyword (normalized label), count (in dataset)
    """
    counts = df[NATURE_COL].value_counts(dropna=True)

    rows = []
    for nature, count in counts.items():
        rows.append({
            "nature": nature,
            "keyword": normalize_for_matching(nature),  # Always Normalize
            "count": int(count),
        })

    return pd.DataFrame(rows)


# Orchestration
def main() -> None:
    # Load the parquet (via the loader, so we get the fast path)
    from src.load_data import load_data
    df = load_data()
    print(f"[rules] Loaded {len(df):,} rows.")

    # Generate the Nature keyword table
    table = generate_nature_table(df)
    table.to_csv(NATURE_KEYWORDS_CSV, index=False, encoding="utf-8-sig")
    print(f"[rules] Saved {len(table)} Nature keywords to: {NATURE_KEYWORDS_CSV.name}")

    # Save the synonym map
    syn_df = pd.DataFrame(
        [(k, v) for k, v in SYNONYMS.items()],
        columns=["title_keyword", "mapped_nature"],
    )
    syn_path = OUTPUT_DIR / "nature_synonyms.csv"
    syn_df.to_csv(syn_path, index=False, encoding="utf-8-sig")
    print(f"[rules] Saved {len(syn_df)} synonyms to: {syn_path.name}")

    # Save the non-product keyword list
    np_df = pd.DataFrame({"keyword": NON_PRODUCT_KEYWORDS})
    np_df.to_csv(NON_PRODUCT_CSV, index=False, encoding="utf-8-sig")
    print(f"[rules] Saved {len(np_df)} non-product keywords to: {NON_PRODUCT_CSV.name}")


    # ---- Sanity checks (both random sample AND full coverage) ----
    null_subset = df[df[NATURE_COL].isna()]["Libellé produit"].dropna()
    total_nulls = len(null_subset)

    # Full coverage
    print("\n[rules] Non-product filter — full coverage on null-Nature rows:")
    caught_all = sum(1 for t in null_subset if is_non_product(t))
    pct = 100 * caught_all / total_nulls if total_nulls else 0
    print(f"[rules]   {caught_all:,}/{total_nulls:,} caught ({pct:.1f}%)")

    # Random sample (for reproducibility, not order bias)
    print("\n[rules] Non-product filter — random sample of 50 null-Nature rows:")
    sample_size = min(50, total_nulls)
    sample = null_subset.sample(sample_size, random_state=42)
    caught_sample = sum(1 for t in sample if is_non_product(t))
    print(f"[rules]   {caught_sample}/{sample_size} caught")


if __name__ == "__main__":
    main()