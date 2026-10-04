"""
Task 1 — Rule-based matcher.

For each row of the dataset:
    1. Is it a non-product (administrative row)?
         Yes  → status = "non_product", no prediction.
    2. Does a Nature keyword match the title?
         No   → status = "pending_ml"  (the ML stage will handle it later).
         Yes  → compare the matched Nature with the source label:
             Agree  → status = "ok"
             Differ → status = "to_review_rule"

Output: output/task1_rule_results.parquet
Report: output/task1_rule_coverage.txt
"""

import re
from pathlib import Path
from typing import Optional

import pandas as pd
from tqdm import tqdm

from src.load_data import load_data
from src.preprocess import normalize_for_matching
from src.task1_rules import SYNONYMS, is_non_product

# ---------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

RULE_RESULTS = OUTPUT_DIR / "task1_rule_results.parquet"
COVERAGE_TXT = OUTPUT_DIR / "task1_rule_coverage.txt"

TITLE_COL = "Libellé produit"
NATURE_COL = "Nature"


# ---------------------------------------------------------------------
# Keyword index
# ---------------------------------------------------------------------
def build_keyword_index(df: pd.DataFrame) -> list[tuple[str, str]]:
    """
    LOOKUP TABLE
    Build a (keyword, canonical_nature) list from two sources:

    1. SYNONYMS         — hand-curated title keywords  → canonical Nature.
    2. Nature labels    — each label is also its own keyword (normalized).

    Sorted by keyword length DESC, so that longest matches win in the
    master regex (e.g., "table basse" beats "table").

    Explanation:
        We have 596 Nature labels and a synonym map. We need to match each title against all of them.
        Better approach than a nested loop is to build the keyword list once, ordered so longest matches 
            win, then use one regex.
        Builds ordered list of (keyword, canonical_nature) pairs — synonyms first, then Nature labels — 
            sorted longest-first, so the matcher knows what to look for and in what priority.
    """
    pairs: dict[str, str] = {} # Dict to prevent having duplicate keys, one on synonym and other on existing nature

    # 1. Synonyms first (hand-curated — higher priority) (the natures that are in title but exist in Nature only as a synonym)
    for title_kw, canonical in SYNONYMS.items():
        norm_kw = normalize_for_matching(title_kw)  #get it, normalize
        if norm_kw:
            pairs[norm_kw] = canonical  # add it to the dict if it still exists

    # 2. Nature labels themselves — do NOT override existing synonyms
    for nature in df[NATURE_COL].dropna().unique(): # loop through the Nature values, passed through the parameters
        norm_label = normalize_for_matching(nature)
        if norm_label and norm_label not in pairs:  # if it is not epty (after normalizing) and the key doesnt already exist, add it
            pairs[norm_label] = nature

    # 3. Longest keyword first
    # finally convert the dict into a list of (keyword, nature) tuples, sorted by keyword length, longest first
    # "table basse" gets tried before "table"
    return sorted(pairs.items(), key=lambda kv: -len(kv[0]))


# ---------------------------------------------------------------------
# Master regex
# ---------------------------------------------------------------------
def compile_master_pattern(
    keyword_index: list[tuple[str, str]],
) -> tuple[re.Pattern, dict[str, str]]:
    """
    Compile ONE alternation regex covering every keyword.

    This avoids iterating over 596 keywords per title:
    a single regex search per title, in C-optimized code.

    Notes:
    - '\\b' at the start prevents 'table' from matching inside 'comptable'.
    - No trailing '\\b' so French plurals/feminine still match
      (e.g., 'blanches' → keyword 'blanc').
    """
    # Reverse map: keyword → canonical Nature (for O(1) lookup after match)
    kw_to_nature = {kw: nat for kw, nat in keyword_index} # tuple to dict again. 

    # Keywords are already sorted longest-first
    keywords = list(kw_to_nature.keys()) # get only the keywords

    # '\\b' prefix + escaped keyword, joined by '|'  --> REGEX ALTERNATION
    parts = [rf"\b{re.escape(kw)}" for kw in keywords] # handles all special chars
    pattern = re.compile("|".join(parts)) # complie into an object, usable many times instead of recompiling everytime

    # so we create a regex that looks close to --> "\\btable basse|\\btable|\\bbahut|\\bmatelas|..."

    return pattern, kw_to_nature


# ---------------------------------------------------------------------
# Single-title matching
# ---------------------------------------------------------------------
def match_title(
    title: str,
    master_pattern: re.Pattern,
    kw_to_nature: dict[str, str],
) -> Optional[str]:
    """
    Return the canonical Nature whose keyword appears in this title,
    or None if nothing matches.

    Because the regex is sorted longest-first, the first match returned
    is the most specific one.

    RULE BASED

    Takes in title, master patter (REGEX ALTERNATION), and the diction of keyword:nature paris
    This function is a pure matching function, status decisions live in classify_row.
    """
    if title is None or not isinstance(title, str): # title is empty (after normalization), or not string
        return None

    norm = normalize_for_matching(title) # normalize title (accents, lower, remove punctuation)
    if not norm:
        return None

    m = master_pattern.search(norm) # search using the normalized title against the master pattern
    # returns a Match object, else it just returns None
    if not m:
        return None # also setting status to "pending_ml". title passed to next stage; ML

    matched_kw = m.group(0).strip() # get the actual substring that matched (from the Match obj)
    return kw_to_nature.get(matched_kw) # translate to the Natur label. 
                #look into the dict using the keyword to find the canonical natur
                # kw_to_nature["table basse"]  →  "Table basse"
                # kw_to_nature["bahut"]        →  "Buffet"


# ---------------------------------------------------------------------
# Row classification
# ---------------------------------------------------------------------
def classify_row(
    title: str,
    source_nature,
    master_pattern: re.Pattern,
    kw_to_nature: dict[str, str],
) -> tuple[Optional[str], str]:
    """
    Classify one row. Returns (predicted_nature, status).

    status ∈ {non_product, pending_ml, ok, to_review_rule}
    """
    # Step 1 — non-product filter
    if is_non_product(title):
        return None, "non_product" # like the adminstrative titles


    # Step 2 — rule match
    rule_nature = match_title(title, master_pattern, kw_to_nature)
    if rule_nature is None:
        return None, "pending_ml"   # this here means the matching 
        # couldnt find a keyword in the title (regardless of wether 
        # it has a nature or not, but in this particular dataset, ALL 
        # null natures are non_product)


    # Step 3 — compare the matched Nature with the source label
    # (defensive: source_nature should never be null here — all nulls
    #  are non-products — but we handle it anyway)
    if source_nature is None or pd.isna(source_nature): # doesnt happen in this datset. (this is just Grace code)
        return rule_nature, "ok"


    # STep 4 - if we have a match in the title and we have a nature ...
    same = normalize_for_matching(rule_nature) == normalize_for_matching(str(source_nature))
    # if they match -> "ok", otherwise we flag to be reviewed
    return rule_nature, "ok" if same else "to_review_rule"


# ---------------------------------------------------------------------
# Report + samples
# ---------------------------------------------------------------------
def build_report(df: pd.DataFrame) -> str:
    """Human-readable summary of the matcher's coverage.
    
    How many rows got each status? (non_product, ok, to_review_rule, pending_ml)
    Of the rows the rule resolved, how many agree with the source label?
    How many disagree (and need review)?
    """

    #Setup
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("TASK 1 — RULE MATCHER COVERAGE REPORT")
    lines.append("=" * 70)
    lines.append(f"Total rows: {len(df):,}")
    lines.append("")

    counts = df["status"].value_counts(dropna=False)
    total = len(df)
    for status, count in counts.items():
        pct = 100 * count / total
        lines.append(f"  {status:>18}: {count:>10,}  ({pct:5.1f}%)")
    lines.append("")

    # Sub-split of "ok" + "to_review_rule" (the rows the RULE resolved)
    resolved = df[df["status"].isin(["ok", "to_review_rule"])]
    if len(resolved) > 0:
        agree = int((resolved["status"] == "ok").sum())
        disagree = int((resolved["status"] == "to_review_rule").sum())
        lines.append(f"Among rule-resolved rows ({len(resolved):,}):")
        lines.append(f"  Agree with source label : {agree:>10,}  ({100 * agree / len(resolved):5.1f}%)")
        lines.append(f"  Disagree (to review)    : {disagree:>10,}  ({100 * disagree / len(resolved):5.1f}%)")
    lines.append("")
    return "\n".join(lines)


def show_samples(df: pd.DataFrame, n: int = 15) -> None:
    """Print sample rows for the interesting statuses. 
        To eyeball the labels and check for patterns.
    """
    for status in ["to_review_rule", "pending_ml"]:
        subset = df[df["status"] == status]
        if len(subset) == 0:
            continue

        print(f"\n{'=' * 70}")
        print(f"SAMPLE {n} ROWS WITH STATUS = {status!r}")
        print(f"{'=' * 70}")

        sample = subset.sample(min(n, len(subset)), random_state=42)
        for i, (_, row) in enumerate(sample.iterrows(), 1):
            title = str(row[TITLE_COL])[:90]
            src = row[NATURE_COL]
            pred = row["nature_predicted"]
            print(f"  {i:>2}. src={src!r:32}  rule={pred!r}")
            print(f"      {title}")


# ---------------------------------------------------------------------
# Main - Orchestration
# ---------------------------------------------------------------------
def main() -> None:
    df = load_data()
    print(f"[matcher] Loaded {len(df):,} rows.")

    print("[matcher] Building keyword index...")
    keyword_index = build_keyword_index(df)
    print(f"[matcher] {len(keyword_index)} keywords loaded.")

    print("[matcher] Compiling master regex...")
    master_pattern, kw_to_nature = compile_master_pattern(keyword_index)

    print("[matcher] Classifying rows...")
    predictions: list[Optional[str]] = []
    statuses: list[str] = []

    for _, row in tqdm(df.iterrows(), total=len(df), unit="row"):
        pred, status = classify_row(
            row[TITLE_COL], row[NATURE_COL], master_pattern, kw_to_nature
        )
        predictions.append(pred)
        statuses.append(status)

    # Add new columns to a copy — never mutate the source.
    out = df.copy()
    out["nature_predicted"] = predictions
    out["status"] = statuses

    print(f"\n[matcher] Saving results: {RULE_RESULTS.name}")
    out.to_parquet(RULE_RESULTS, index=False)

    report = build_report(out)
    print("\n" + report)
    COVERAGE_TXT.write_text(report, encoding="utf-8")
    print(f"[save] Coverage report: {COVERAGE_TXT.name}")

    show_samples(out, n=15)

    print("\n[done]")


if __name__ == "__main__":
    main()