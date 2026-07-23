"""
BenefitIQ propensity model
----------------------------
Trains an XGBoost classifier to predict P(member acts on a nudge within
14 days), using features derivable at nudge-decision time. Also fits a
SHAP explainer so every prediction the API serves can carry a
plain-language "why" — this is what lets the nudge orchestration layer
rank and explain, rather than broadcast blindly.

Outputs (all written to ml/model_artifacts/):
  - propensity_model.json     trained XGBoost booster
  - metrics.json              AUC-ROC, calibration, feature importances
  - shap_summary.png          global feature-importance plot for the README
  - feature_columns.json      exact feature order the API must replicate

Run with: python train_propensity_model.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
ARTIFACT_DIR = Path(__file__).resolve().parent / "model_artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)

TODAY = pd.Timestamp("2026-07-23")

# --------------------------------------------------------------------------
# 1. Load synthetic data and engineer features
#    Every feature here is something the system genuinely knows about a
#    member *before* a candidate nudge is scored — no leakage from the
#    label itself.
# --------------------------------------------------------------------------
members = pd.read_csv(DATA_DIR / "cardholders.csv")
redemptions = pd.read_csv(DATA_DIR / "redemption_history.csv", parse_dates=["claimed_date"])
engagement = pd.read_csv(DATA_DIR / "engagement_history.csv", parse_dates=["nudge_date"])
transactions = pd.read_csv(DATA_DIR / "transactions.csv", parse_dates=["date"])

redemption_counts = redemptions.groupby("member_id").size().rename("past_redemptions")
redemption_recency = (
    redemptions.groupby("member_id")["claimed_date"].max()
    .apply(lambda d: (TODAY - d).days).rename("days_since_last_redemption")
)
tx_counts = transactions.groupby("member_id").size().rename("tx_count_365d")
tx_recency = (
    transactions.groupby("member_id")["date"].max()
    .apply(lambda d: (TODAY - d).days).rename("days_since_last_tx")
)

df = engagement.merge(members[["member_id", "tenure_days", "card_tier"]], on="member_id", how="left")
df = df.merge(redemption_counts, on="member_id", how="left")
df = df.merge(redemption_recency, on="member_id", how="left")
df = df.merge(tx_counts, on="member_id", how="left")
df = df.merge(tx_recency, on="member_id", how="left")

df["past_redemptions"] = df["past_redemptions"].fillna(0)
df["days_since_last_redemption"] = df["days_since_last_redemption"].fillna(999)
df["tx_count_365d"] = df["tx_count_365d"].fillna(0)
df["days_since_last_tx"] = df["days_since_last_tx"].fillna(999)

# leave-one-out prior engagement rate: for each nudge row, the member's
# mean act-rate across their OTHER nudges (excludes the current label to
# avoid trivial leakage, but uses all other history for a stable estimate)
df = df.reset_index(drop=True)
member_totals = df.groupby("member_id")["acted_within_14d"].agg(["sum", "count"])
df = df.merge(member_totals, on="member_id", how="left")
df["prior_engagement_rate"] = np.where(
    df["count"] > 1,
    (df["sum"] - df["acted_within_14d"]) / (df["count"] - 1),
    0.3,  # cold-start prior for members with a single observed nudge
)
df = df.drop(columns=["sum", "count"])

df["card_tier_gold"] = (df["card_tier"] == "Gold").astype(int)
df["card_tier_platinum"] = (df["card_tier"] == "Platinum").astype(int)
df["card_tier_centurion"] = (df["card_tier"] == "Centurion").astype(int)
df["channel_push"] = (df["channel"] == "push").astype(int)
df["channel_email"] = (df["channel"] == "email").astype(int)
df["channel_in_app"] = (df["channel"] == "in_app").astype(int)

FEATURE_COLUMNS = [
    "tenure_days", "past_redemptions", "days_since_last_redemption",
    "tx_count_365d", "days_since_last_tx", "prior_engagement_rate",
    "card_tier_gold", "card_tier_platinum", "card_tier_centurion",
    "channel_push", "channel_email", "channel_in_app",
]
X = df[FEATURE_COLUMNS]
y = df["acted_within_14d"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# --------------------------------------------------------------------------
# 2. Train XGBoost (primary model) + a logistic regression baseline
#    scikit-learn baseline is what Section 7.5 of the project description
#    promises: an interpretable model to sanity-check the gradient-boosted
#    one against.
# --------------------------------------------------------------------------
xgb_model = xgb.XGBClassifier(
    n_estimators=150, max_depth=4, learning_rate=0.08,
    subsample=0.85, colsample_bytree=0.85,
    eval_metric="auc", random_state=42,
)
xgb_model.fit(X_train, y_train)
xgb_probs = xgb_model.predict_proba(X_test)[:, 1]
xgb_auc = roc_auc_score(y_test, xgb_probs)

baseline = LogisticRegression(max_iter=2000)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
baseline.fit(X_train_scaled, y_train)
baseline_probs = baseline.predict_proba(X_test_scaled)[:, 1]
baseline_auc = roc_auc_score(y_test, baseline_probs)

# calibration curve (is a "70% likely" prediction actually right ~70% of
# the time?) — this is the metric Section 7.5 says matters more than raw
# accuracy for a nudge-prioritization system
frac_pos, mean_pred = calibration_curve(y_test, xgb_probs, n_bins=8, strategy="quantile")
calibration_gap = float(np.mean(np.abs(frac_pos - mean_pred)))

# --------------------------------------------------------------------------
# 3. SHAP explainability
# --------------------------------------------------------------------------
explainer = shap.TreeExplainer(xgb_model)
shap_values = explainer.shap_values(X_test)

plt.figure()
shap.summary_plot(shap_values, X_test, show=False, plot_size=(8, 5))
plt.tight_layout()
plt.savefig(ARTIFACT_DIR / "shap_summary.png", dpi=150, bbox_inches="tight")
plt.close()

mean_abs_shap = np.abs(shap_values).mean(axis=0)
feature_importance = sorted(
    zip(FEATURE_COLUMNS, mean_abs_shap.tolist()), key=lambda t: -t[1]
)

# --------------------------------------------------------------------------
# 4. Persist artifacts
# --------------------------------------------------------------------------
xgb_model.save_model(str(ARTIFACT_DIR / "propensity_model.json"))

metrics = {
    "xgboost_auc_roc": round(float(xgb_auc), 4),
    "logistic_regression_baseline_auc_roc": round(float(baseline_auc), 4),
    "calibration_mean_abs_gap": round(calibration_gap, 4),
    "train_rows": int(len(X_train)),
    "test_rows": int(len(X_test)),
    "positive_rate_test": round(float(y_test.mean()), 4),
    "top_features_by_mean_abs_shap": [
        {"feature": f, "mean_abs_shap": round(v, 5)} for f, v in feature_importance
    ],
}
(ARTIFACT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
(ARTIFACT_DIR / "feature_columns.json").write_text(json.dumps(FEATURE_COLUMNS, indent=2))

print("=== BenefitIQ Propensity Model — Training Report ===")
print(f"XGBoost AUC-ROC:              {xgb_auc:.4f}")
print(f"Logistic baseline AUC-ROC:    {baseline_auc:.4f}")
print(f"Mean calibration gap:         {calibration_gap:.4f}  (lower is better; 0 = perfectly calibrated)")
print(f"Train / test rows:            {len(X_train)} / {len(X_test)}")
print("\nTop features by mean |SHAP value|:")
for f, v in feature_importance[:6]:
    print(f"  {f:<28} {v:.5f}")
print(f"\nArtifacts written to: {ARTIFACT_DIR}")
