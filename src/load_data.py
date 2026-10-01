"""
Load the sales data.

- Reads the raw .xlsx from data/raw/sales.xlsx
- Caches it as .parquet (fast re-loads)
- Prints basic EDA: shape, dtypes, nulls, value counts
- Saves Nature and Univers vocabularies for inspection

First run:
1. Check: does data/processed/sales.parquet exist?
   → No.
2. Load data/raw/sales.xlsx  (~3 min)
3. Save data/processed/sales.parquet  (~5 sec)
4. Print EDA
5. Save output/nature_vocabulary.csv and output/univers_vocabulary.csv
"""

from pathlib import Path
import pandas as pd

# ----- Paths -----
ROOT = Path(__file__).resolve().parent.parent
RAW_XLSX = ROOT / "data" / "raw" / "sales.xlsx"
PARQUET = ROOT / "data" / "processed" / "sales.parquet"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)



def load_data(force_reload: bool = False) -> pd.DataFrame:
    """
    Load the sales data.
    - If parquet exists and force_reload=False: load parquet (fast).
    - Otherwise: load xlsx, cast object columns to string, save as parquet, return df.
    """
    if PARQUET.exists() and not force_reload:
        print(f"[load] Reading cached parquet: {PARQUET.name}")
        return pd.read_parquet(PARQUET)     # if pargquet exists, return and exit this function, 
                                            # else go through the first time read excel

    print(f"[load] Reading xlsx (this may take a few minutes): {RAW_XLSX.name}")
    df = pd.read_excel(RAW_XLSX, engine="openpyxl")
    print(f"[load] Loaded {len(df):,} rows, {len(df.columns)} columns.")

    # Cast all object-dtype columns to string to avoid pyarrow mixed-type errors
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype("string") # "string" instead of str to save NaN and null values..

    print(f"[load] Saving parquet cache: {PARQUET.name}")
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PARQUET, index=False)

    return df


def run_eda(df: pd.DataFrame) -> None:
    """Print quick EDA and save Nature + Univers vocabularies.
    # Univers = Category of Natur
    # Nature  = Sub-category to Univer
    
    """
    print("\n" + "=" * 70)
    print("SHAPE")
    print("=" * 70)
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    print("\n" + "=" * 70)
    print("COLUMNS")
    print("=" * 70)
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. '{col}'  (dtype: {df[col].dtype})")

    print("\n" + "=" * 70)
    print("NULL COUNTS")
    print("=" * 70)
    nulls = df.isna().sum().sort_values(ascending=False)
    for col, n in nulls.items():
        pct = 100 * n / len(df)
        print(f"  {col!r:40} {n:>10,}  ({pct:5.1f}%)")

    # Locate key columns by fuzzy name matching
    nature_col = next((c for c in df.columns if "nature" in c.lower()), None)
    univers_col = next((c for c in df.columns if "univers" in c.lower()), None)
    title_col = next(
        (c for c in df.columns if "libell" in c.lower() or "produit" in c.lower()),
        None,
    )

    # ---- Univers ----
    if univers_col:
        print("\n" + "=" * 70)
        print(f"UNIVERS VALUE COUNTS ('{univers_col}')")
        print("=" * 70)
        print(df[univers_col].value_counts(dropna=False).to_string())

        univers_path = OUTPUT_DIR / "univers_vocabulary.csv"
        (
            df[univers_col]
            .value_counts(dropna=False)
            .rename_axis("univers")
            .reset_index(name="count")
            .to_csv(univers_path, index=False, encoding="utf-8-sig")                # CSV file of the 10ish Univers
        )
        print(f"\n[save] Full Univers vocabulary saved to: {univers_path}")

    # ---- Nature ----
    if nature_col:
        print("\n" + "=" * 70)
        print(f"NATURE VALUE COUNTS ('{nature_col}')")
        print("=" * 70)
        print(f"Unique natures: {df[nature_col].nunique(dropna=True):,}")
        print(f"Null natures:   {df[nature_col].isna().sum():,}")
        print("\nTop 30 natures:")
        print(df[nature_col].value_counts(dropna=False).head(30).to_string())

        vocab_path = OUTPUT_DIR / "nature_vocabulary.csv"
        (
            df[nature_col]
            .value_counts(dropna=False)
            .rename_axis("nature")
            .reset_index(name="count")
            .to_csv(vocab_path, index=False, encoding="utf-8-sig")                      # CSV file of the 300+ Nature
        )
        print(f"\n[save] Full Nature vocabulary saved to: {vocab_path}")

    # ---- Sample titles ----
    if title_col:
        print("\n" + "=" * 70)
        print(f"SAMPLE TITLES ('{title_col}')")
        print("=" * 70)
        sample = df[title_col].dropna().sample(10, random_state=42)
        for i, t in enumerate(sample, 1):
            print(f"  {i:>2}. {t}")


if __name__ == "__main__":
    df = load_data()
    run_eda(df)
    print("\n[done]")