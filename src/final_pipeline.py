"""
Final pipeline — merge Task 1 + Task 2 into the client deliverable.

Steps:
    1. Load the rule matcher output (525,034 rows).
    2. Load the ML output (49,538 rows for the pending_ml subset).
    3. Replace pending_ml rows with their ML prediction + status.
    4. Load the Task 2 output (dimension, couleur, materiau).
    5. Join Task 2 columns onto the Task 1 results.
    6. Save the combined results.
    7. Export the final client deliverable as .xlsx.

Outputs:
    output/resultats.parquet   — combined final table (fast for reuse)
    output/resultats.xlsx      — client deliverable (Excel)
"""

from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Inputs
RULE_RESULTS  = OUTPUT_DIR / "task1_rule_results.parquet"
ML_RESULTS    = OUTPUT_DIR / "task1_ml_results.parquet"
TASK2_RESULTS = OUTPUT_DIR / "task2_results.parquet"

# Outputs
RESULTS_PARQUET = OUTPUT_DIR / "resultats.parquet"
RESULTS_XLSX    = OUTPUT_DIR / "resultats.xlsx"
SUMMARY_TXT     = OUTPUT_DIR / "resultats_summary.txt"

# Column name for the source title (with accents, exact spelling)
TITLE_COL = "Libellé produit"


# ---------------------------------------------------------------------
# Step 1 & 2 — Load inputs (the parquets we generated for both tasks)
# ---------------------------------------------------------------------
def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the three intermediate results files."""
    print(f"[final] Loading rule results:    {RULE_RESULTS.name}")
    rule = pd.read_parquet(RULE_RESULTS)
    print(f"[final]   {len(rule):,} rows.")

    print(f"[final] Loading ML results:      {ML_RESULTS.name}")
    ml = pd.read_parquet(ML_RESULTS)
    print(f"[final]   {len(ml):,} rows.")

    print(f"[final] Loading Task 2 results:  {TASK2_RESULTS.name}")
    task2 = pd.read_parquet(TASK2_RESULTS)
    print(f"[final]   {len(task2):,} rows.")

    return rule, ml, task2


# ---------------------------------------------------------------------
# Step 3 — Merge Task 1 (rule + ML)
# ---------------------------------------------------------------------
def merge_task1(rule: pd.DataFrame, ml: pd.DataFrame) -> pd.DataFrame:
    """
    Replace rule-based rows with ML predictions where the rule had no
    match (status == "pending_ml").

    The rule results have: nature_predicted, status
    The ML results have:  nature_predicted, confidence, status

    ML rows share the same index values as the pending_ml rows in the
    rule results, so we align by index.
    """
    print("\n[final] Merging Task 1 (rule + ML)...")

    out = rule.copy()

    # Add a confidence column. Rule-resolved rows get confidence 1.0
    # (deterministic); non_product rows stay None.
    out["confidence"] = None
    out.loc[out["status"] == "ok", "confidence"] = 1.0
    out.loc[out["status"] == "to_review_rule", "confidence"] = 1.0

    # Overwrite the pending_ml rows with ML predictions.
    pending_idx = out[out["status"] == "pending_ml"].index
    ml_aligned = ml.reindex(pending_idx)

    out.loc[pending_idx, "nature_predicted"] = ml_aligned["nature_predicted"].values
    out.loc[pending_idx, "confidence"]       = ml_aligned["confidence"].values
    out.loc[pending_idx, "status"]           = ml_aligned["status"].values

    print(f"[final]   Final status counts:")
    for status, count in out["status"].value_counts().items():
        pct = 100 * count / len(out)
        print(f"[final]     {status:>18}: {count:>10,}  ({pct:5.1f}%)")

    return out


# ---------------------------------------------------------------------
# Step 4 & 5 — Join Task 2 columns
# ---------------------------------------------------------------------
def join_task2(task1: pd.DataFrame, task2: pd.DataFrame) -> pd.DataFrame:
    """
    Join Task 2 columns (dimension, dimension_unit, couleur, materiau)
    onto the Task 1 result, positionally.

    Both dataframes come from the same source (sales.parquet) with the
    same row order, so a positional join is safe and fast.
    """
    print("\n[final] Joining Task 2 columns...")

    assert len(task1) == len(task2), (
        f"Row count mismatch: task1={len(task1):,} vs task2={len(task2):,}"
    )

    task2_cols  = task2[["dimension", "dimension_unit", "couleur", "materiau"]].reset_index(drop=True)
    task1_reset = task1.reset_index(drop=True)

    combined = pd.concat([task1_reset, task2_cols], axis=1)
    print(f"[final]   Combined columns: {len(combined.columns)}")

    return combined


# ---------------------------------------------------------------------
# Step 6 — Save outputs
# ---------------------------------------------------------------------
def save_outputs(df: pd.DataFrame) -> None:
    """Save the final result as parquet (fast) and xlsx (client-facing)."""
    print(f"\n[final] Saving parquet: {RESULTS_PARQUET.name}")
    df.to_parquet(RESULTS_PARQUET, index=False)

    print(f"[final] Saving Excel:  {RESULTS_XLSX.name}")
    # Excel limit is ~1.05M rows — we have 525k, so it fits.
    df.to_excel(RESULTS_XLSX, index=False, engine="openpyxl")

    size_mb = RESULTS_XLSX.stat().st_size / 1e6
    print(f"[final] Excel file size: {size_mb:.1f} MB")


# ---------------------------------------------------------------------
# Step 7 — Summary report
# ---------------------------------------------------------------------
def build_summary(df: pd.DataFrame) -> str:
    """Human-readable summary of the final output."""
    lines = []
    lines.append("=" * 70)
    lines.append("FINAL DELIVERABLE — SUMMARY")
    lines.append("=" * 70)
    lines.append(f"Total rows: {len(df):,}")
    lines.append(f"Total columns: {len(df.columns)}")
    lines.append("")

    lines.append("Task 1 — status breakdown:")
    for status, count in df["status"].value_counts().items():
        pct = 100 * count / len(df)
        lines.append(f"  {status:>18}: {count:>10,}  ({pct:5.1f}%)")
    lines.append("")

    lines.append("Task 2 — extraction coverage:")
    dim_pct = 100 * df["dimension"].notna().mean()
    col_pct = 100 * df["couleur"].apply(len).gt(0).mean()
    mat_pct = 100 * df["materiau"].apply(len).gt(0).mean()
    lines.append(f"  Dimension found:  {df['dimension'].notna().sum():>10,}  ({dim_pct:5.1f}%)")
    lines.append(f"  Color found:      {df['couleur'].apply(len).gt(0).sum():>10,}  ({col_pct:5.1f}%)")
    lines.append(f"  Material found:   {df['materiau'].apply(len).gt(0).sum():>10,}  ({mat_pct:5.1f}%)")
    lines.append("")

    lines.append("Columns in the final file:")
    for col in df.columns:
        lines.append(f"  - {col!r}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> None:
    rule, ml, task2 = load_inputs()
    task1 = merge_task1(rule, ml)
    combined = join_task2(task1, task2)

    save_outputs(combined)

    summary = build_summary(combined)
    print("\n" + summary)
    SUMMARY_TXT.write_text(summary, encoding="utf-8")
    print(f"[save] Summary: {SUMMARY_TXT.name}")

    print("\n[done]")


if __name__ == "__main__":
    main()