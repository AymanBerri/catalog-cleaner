"""
Task 1 — Reconnaissance.

Before building the rule matcher and ML classifier, we need to
understand the Nature vocabulary in detail:
  - Top 50 Natures with sample titles each (to design rules)
  - Rarest 50 Natures (noise? obscure categories?)
  - Candidates for synonyms / duplicates

Output: output/task1_recon.txt (and printed to terminal).
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

RESULTS_TXT = OUTPUT_DIR / "task1_recon.txt"

TITLE_COL = "Libellé produit"
NATURE_COL = "Nature"

SAMPLES_PER_NATURE = 5
TOP_N = 50
RARE_N = 50


def load_parquet() -> pd.DataFrame:
    path = ROOT / "data" / "processed" / "sales.parquet"
    print(f"[recon] Loading {path.name}...")
    return pd.read_parquet(path)


def section(title: str, width: int = 70) -> str:
    return "\n" + "=" * width + "\n" + title + "\n" + "=" * width


def top_natures_report(df: pd.DataFrame) -> list[str]:
    """Top N Natures with sample titles each."""
    lines = [section(f"TOP {TOP_N} NATURES — WITH SAMPLE TITLES")]

    counts = df[NATURE_COL].value_counts(dropna=True)
    top = counts.head(TOP_N)

    for i, (nature, count) in enumerate(top.items(), 1):
        lines.append(f"\n[{i:>2}] {nature}   (count: {count:,})")
        lines.append("-" * 60)

        # Sample titles for this Nature
        subset = df[df[NATURE_COL] == nature][TITLE_COL].dropna()
        if len(subset) == 0:
            lines.append("   (no titles)")
            continue

        n = min(SAMPLES_PER_NATURE, len(subset))
        samples = subset.sample(n, random_state=42)
        for j, t in enumerate(samples, 1):
            lines.append(f"   {j}. {t[:110]}")

    return lines


def rare_natures_report(df: pd.DataFrame) -> list[str]:
    """Rarest N Natures (likely noise or very niche)."""
    lines = [section(f"RAREST {RARE_N} NATURES (noise? niche?)")]

    counts = df[NATURE_COL].value_counts(dropna=True)
    rare = counts.tail(RARE_N)

    for nature, count in rare.items():
        lines.append(f"   {count:>5}×  {nature!r}")

    return lines


def null_nature_samples(df: pd.DataFrame) -> list[str]:
    """Sample titles where Nature is null (Task 1's primary targets)."""
    lines = [section("SAMPLE 20 TITLES WHERE NATURE IS NULL")]

    subset = df[df[NATURE_COL].isna()][TITLE_COL].dropna()
    if len(subset) == 0:
        lines.append("   (no null natures)")
        return lines

    sample = subset.sample(min(20, len(subset)), random_state=42)
    for i, t in enumerate(sample, 1):
        lines.append(f"   {i:>2}. {t[:110]}")

    return lines


def synonym_candidates(df: pd.DataFrame) -> list[str]:
    """
    Print Natures whose normalized form (lowercase, no accents, no punctuation)
    matches another Nature — likely duplicates.
    """
    import re
    import unicodedata

    def norm(s: str) -> str:
        s = s.lower()
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = re.sub(r"[^a-z0-9]+", " ", s).strip()
        return s

    lines = [section("SYNONYM / DUPLICATE CANDIDATES (same normalized form)")]

    natures = df[NATURE_COL].dropna().unique()
    buckets: dict[str, list[str]] = {}
    for n in natures:
        key = norm(n)
        buckets.setdefault(key, []).append(n)

    found_any = False
    for key, variants in buckets.items():
        if len(variants) > 1:
            found_any = True
            lines.append(f"   {key!r}:")
            for v in variants:
                count = (df[NATURE_COL] == v).sum()
                lines.append(f"      - {v!r}  ({count:,})")

    if not found_any:
        lines.append("   (none)")

    return lines


def main() -> None:
    df = load_parquet()
    print(f"[recon] Loaded {len(df):,} rows.")

    parts = []
    parts += top_natures_report(df)
    parts += rare_natures_report(df)
    parts += null_nature_samples(df)
    parts += synonym_candidates(df)

    report = "\n".join(parts)

    # Print to terminal
    print(report)

    # Save to file for eyeballing
    RESULTS_TXT.write_text(report, encoding="utf-8")
    print(f"\n[save] Report saved to: {RESULTS_TXT.name}")


if __name__ == "__main__":
    main()