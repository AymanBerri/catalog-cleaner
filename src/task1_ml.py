# run >> python -m src.task1_ml
"""
Task 1 — ML classifier for pending_ml rows.

After the rule matcher, ~9.4% of rows (49,538) had no keyword match.
These are the "pending_ml" rows. This script:

    1. Loads the rule matcher results.
    2. Trains TF-IDF + LinearSVC on the "ok" subset (trusted rows).
    3. Predicts on the "pending_ml" rows.
    4. Attaches a confidence score to each prediction.
    5. Assigns a final status: "predicted" or "to_review_ml".
    6. Saves ML results to output/task1_ml_results.parquet.

Why train on "ok" rows only?
    - They have clean labels (rule + source label agree).
    - Training on the full dataset would include noisy labels,
      teaching the model bad patterns.

Why LinearSVC?
    - Fast on 380k rows / 596 classes.
    - Works well for high-dimensional sparse text (TF-IDF).
    - Multi-class via one-vs-rest.

Output:
    output/task1_ml_results.parquet
        Columns: nature_predicted, confidence, status
        Index:   matches the pending_ml rows from the rule results.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from src.preprocess import normalize_for_matching

# ---------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

RULE_RESULTS = OUTPUT_DIR / "task1_rule_results.parquet"
ML_RESULTS = OUTPUT_DIR / "task1_ml_results.parquet"
ML_REPORT = OUTPUT_DIR / "task1_ml_report.txt"

TITLE_COL = "Libellé produit"
NATURE_COL = "Nature"

# Confidence threshold: predictions below this go to human review.
CONFIDENCE_THRESHOLD = 0.15


# ---------------------------------------------------------------------
# Train
# ---------------------------------------------------------------------
def train_classifier(df: pd.DataFrame) -> Pipeline:
    """
    Train a TF-IDF + LinearSVC pipeline on the trusted subset
    (rows where status = "ok").

    Returns the fitted sklearn Pipeline.
    """
    # Trusted subset: rule matcher agreed with the source label.
    trusted = df[df["status"] == "ok"].copy()
    print(f"[ml] Training on {len(trusted):,} trusted rows.")

    # Normalize titles for consistency (same normalization as the matcher).
    X_train = trusted[TITLE_COL].fillna("").apply(normalize_for_matching)
    y_train = trusted[NATURE_COL].astype(str)

    print(f"[ml] Number of classes (Natures): {y_train.nunique():,}")

    # TF-IDF + LinearSVC pipeline.
    # - TF-IDF: text → sparse numeric matrix, weighted by TF × IDF.
    # - LinearSVC: fast linear classifier, multi-class via one-vs-rest.
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.9,
            sublinear_tf=True,
            max_features=100_000,   # cap the vocabulary → faster training
        )),
        ("clf", LinearSVC(
            C=1.0,                  # regularization strength
            max_iter=500,           # convergence rarely needs more
            dual=True,              # recommended when features > samples
            verbose=1,              # print iteration progress
        )),
    ])

    print("[ml] Fitting pipeline (this may take a few minutes)...")
    pipeline.fit(X_train, y_train)
    print("[ml] Training complete.")

    return pipeline


# ---------------------------------------------------------------------
# Confidence — margin.
# ---------------------------------------------------------------------
def _svc_scores_to_confidence(decision_scores: np.ndarray) -> np.ndarray:
    """
    Confidence = margin between the top-1 and top-2 decision scores.

    Big gap → model is decisive → high confidence.
    Small gap → model is unsure → low confidence.

    Unlike softmax over 421 classes, this doesn't depend on the number
    of classes and produces meaningful separation.
    """
    top1 = decision_scores.max(axis=1)
    top2 = np.partition(decision_scores, -2, axis=1)[:, -2]
    return top1 - top2


# ---------------------------------------------------------------------
# Predict
# ---------------------------------------------------------------------
def predict_pending(pipeline: Pipeline, df: pd.DataFrame) -> pd.DataFrame:
    """
    Predict Nature for rows with status == "pending_ml".
    Returns a DataFrame with: nature_predicted, confidence, status.
    """
    pending = df[df["status"] == "pending_ml"].copy()
    print(f"[ml] Predicting on {len(pending):,} pending_ml rows.")

    if len(pending) == 0:
        return pd.DataFrame(
            columns=["nature_predicted", "confidence", "status"]
        )

    # Same normalization as during training.
    X_pending = pending[TITLE_COL].fillna("").apply(normalize_for_matching)

    # 1. Predicted class per row.
    preds = pipeline.predict(X_pending) #here gives out a list of the predictions "classes/natur"

    # 2a. Raw scores → confidence (margin between top-1 and top-2).
    raw_scores = pipeline.decision_function(X_pending)  #here give matrix of raw scores "distances from the decision boundary"
    confidences = _svc_scores_to_confidence(raw_scores)


    # 2b. Print margin percentiles to help pick the threshold
    print("[ml] Margin percentiles (for threshold tuning):")
    for p in [10, 25, 50, 75, 90, 95, 99]:
        print(f"[ml]   {p:>3}th: {np.percentile(confidences, p):.4f}")

    # 3. Assemble results, aligned with pending rows' index.
    result = pd.DataFrame(
        {
            "nature_predicted": preds,
            "confidence": confidences,
        },
        index=pending.index,
    )

    # 4. Status based on the confidence threshold.
    result["status"] = np.where(
        result["confidence"] >= CONFIDENCE_THRESHOLD,
        "predicted",
        "to_review_ml",
    )

    # Quick stats
    n_predicted = int((result["status"] == "predicted").sum())
    n_review = int((result["status"] == "to_review_ml").sum())
    print(f"[ml]   predicted      (>= {CONFIDENCE_THRESHOLD}): {n_predicted:,}")
    print(f"[ml]   to_review_ml   (<  {CONFIDENCE_THRESHOLD}): {n_review:,}")

    return result


# ---------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------
def build_ml_report(ml_df: pd.DataFrame) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("TASK 1 — ML CLASSIFIER REPORT")
    lines.append("=" * 70)
    lines.append(f"Pending rows processed: {len(ml_df):,}")
    lines.append("")

    counts = ml_df["status"].value_counts(dropna=False)
    total = len(ml_df)
    for status, count in counts.items():
        pct = 100 * count / total if total else 0
        lines.append(f"  {status:>18}: {count:>10,}  ({pct:5.1f}%)")
    lines.append("")

    if "confidence" in ml_df.columns and len(ml_df) > 0:
        lines.append("Confidence distribution:")
        lines.append(f"  min    : {ml_df['confidence'].min():.3f}")
        lines.append(f"  median : {ml_df['confidence'].median():.3f}")
        lines.append(f"  mean   : {ml_df['confidence'].mean():.3f}")
        lines.append(f"  max    : {ml_df['confidence'].max():.3f}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------
# Samples
# ---------------------------------------------------------------------
def show_ml_samples(ml_df: pd.DataFrame, source_df: pd.DataFrame, n: int = 15) -> None:
    """Print sample rows for each ML status, with the source title."""
    for status in ["predicted", "to_review_ml"]:
        subset = ml_df[ml_df["status"] == status]
        if len(subset) == 0:
            continue

        print(f"\n{'=' * 70}")
        print(f"SAMPLE {n} ROWS WITH STATUS = {status!r}")
        print(f"{'=' * 70}")

        sample = subset.sample(min(n, len(subset)), random_state=42)
        for i, (idx, row) in enumerate(sample.iterrows(), 1):
            title = str(source_df.loc[idx, TITLE_COL])[:90]
            pred = row["nature_predicted"]
            conf = row["confidence"]
            print(f"  {i:>2}. pred={pred!r:32}  conf={conf:.2f}")
            print(f"      {title}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> None:
    print(f"[ml] Loading rule results: {RULE_RESULTS.name}")
    df = pd.read_parquet(RULE_RESULTS)
    print(f"[ml] Loaded {len(df):,} rows.")

    # Train on the trusted subset.
    pipeline = train_classifier(df)

    # Predict on pending_ml rows.
    ml_df = predict_pending(pipeline, df)

    # Save results.
    print(f"\n[ml] Saving results: {ML_RESULTS.name}")
    ml_df.to_parquet(ML_RESULTS)

    # Report.
    report = build_ml_report(ml_df)
    print("\n" + report)
    ML_REPORT.write_text(report, encoding="utf-8")
    print(f"[save] Report: {ML_REPORT.name}")

    # Samples.
    show_ml_samples(ml_df, df, n=15)

    print("\n[done]")


if __name__ == "__main__":
    main()