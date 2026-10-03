"""
Run Task 2 — extract dimension, color, material on the full dataset.

Loads the parquet cache, applies the three extractors to every row,
adds new columns (never modifies source), saves results, and prints
coverage stats + samples where extraction failed.
"""

from pathlib import Path
import pandas as pd
from tqdm import tqdm   # progress bars

from src.load_data import load_data
from src.task2_extraction import (  #extraction functions
    extract_dimension,
    extract_colors,
    extract_materials,
)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

RESULTS_PARQUET = OUTPUT_DIR / "task2_results.parquet"
COVERAGE_REPORT = OUTPUT_DIR / "task2_coverage.txt"

TITLE_COL = "Libellé produit"


def run_task2(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the three extractors to every title. Return df with new columns."""
    titles = df[TITLE_COL]

    # tqdm gives us progress bars for the 525k-row loop
    print("\n[task2] Extracting dimensions...")
    dims = [extract_dimension(t) for t in tqdm(titles, unit="row")]

    print("\n[task2] Extracting colors...")
    colors = [extract_colors(t) for t in tqdm(titles, unit="row")]

    print("\n[task2] Extracting materials...")
    materials = [extract_materials(t) for t in tqdm(titles, unit="row")]

    # Add new columns. Never touch the source columns.
    out = df.copy()         # copy -- never mutate the source dataframe
    out["dimension"] = [d["dimension"] if d else None for d in dims]
    out["dimension_unit"] = [d["unit"] if d else None for d in dims]
    out["couleur"] = colors
    out["materiau"] = materials

    return out


def coverage_report(df: pd.DataFrame, original_len: int) -> str:
    """Build a plain-text coverage summary."""
    lines = []
    lines.append("=" * 70)
    lines.append("TASK 2 — COVERAGE REPORT")
    lines.append("=" * 70)
    lines.append(f"Total rows:              {original_len:>10,}")
    lines.append("")
    lines.append("Extraction coverage:")
    lines.append(f"  Dimension found:       {df['dimension'].notna().sum():>10,}  ({100 * df['dimension'].notna().mean():5.1f}%)")
    lines.append(f"  Color found:           {df['couleur'].apply(len).gt(0).sum():>10,}  ({100 * df['couleur'].apply(len).gt(0).mean():5.1f}%)")
    lines.append(f"  Material found:        {df['materiau'].apply(len).gt(0).sum():>10,}  ({100 * df['materiau'].apply(len).gt(0).mean():5.1f}%)")
    lines.append("")
    lines.append("Unit distribution (dimensions only):")
    unit_counts = df["dimension_unit"].value_counts(dropna=False)
    for unit, count in unit_counts.items():
        label = unit if unit is not None else "(none)"
        lines.append(f"  {str(label):>10}: {count:>10,}")
    lines.append("")
    lines.append("Top 20 colors found:")
    all_colors = [c for lst in df["couleur"] for c in lst]
    color_series = pd.Series(all_colors).value_counts().head(20)
    for color, count in color_series.items():
        lines.append(f"  {color:>20}: {count:>10,}")
    lines.append("")
    lines.append("Top 20 materials found:")
    all_materials = [m for lst in df["materiau"] for m in lst]
    mat_series = pd.Series(all_materials).value_counts().head(20)
    for mat, count in mat_series.items():
        lines.append(f"  {mat:>20}: {count:>10,}")
    lines.append("")
    return "\n".join(lines)


# Main way to debug.
def show_failure_samples(df: pd.DataFrame, n: int = 15) -> None:
    """Print random titles where no color was found — to spot missing lexicon words."""
    print("\n" + "=" * 70)
    print(f"SAMPLE {n} TITLES WITH NO COLOR EXTRACTED")
    print("=" * 70)
    sample = df[df["couleur"].apply(len) == 0].sample(min(n, len(df)), random_state=42)
    for i, title in enumerate(sample[TITLE_COL], 1):
        print(f"  {i:>2}. {title[:120]}")

    print("\n" + "=" * 70)
    print(f"SAMPLE {n} TITLES WITH NO DIMENSION EXTRACTED")
    print("=" * 70)
    sample = df[df["dimension"].isna()].sample(min(n, len(df)), random_state=42)
    for i, title in enumerate(sample[TITLE_COL], 1):
        print(f"  {i:>2}. {title[:120]}")


# orchestration
def main() -> None:
    df = load_data()
    print(f"[task2] Loaded {len(df):,} rows.")

    out = run_task2(df)

    print(f"\n[task2] Saving results: {RESULTS_PARQUET.name}")
    out.to_parquet(RESULTS_PARQUET, index=False)

    report = coverage_report(out, len(df))
    print("\n" + report)
    COVERAGE_REPORT.write_text(report, encoding="utf-8")
    print(f"\n[save] Coverage report: {COVERAGE_REPORT.name}")

    show_failure_samples(out, n=15)

    print("\n[done]")


if __name__ == "__main__":
    main()