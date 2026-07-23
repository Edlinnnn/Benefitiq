"""
BenefitIQ nudge scoring & explanation
----------------------------------------
Loads the trained XGBoost propensity model and its SHAP explainer once,
then scores candidate nudges and attaches a plain-language explanation
built from the top SHAP contributors for that specific prediction.

This is what Section 4 of the project description calls "built-in
explainability": every nudge the API returns carries a reason, not just
a score.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import shap
import xgboost as xgb

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACT_DIR = REPO_ROOT / "ml" / "model_artifacts"
TODAY = pd.Timestamp("2026-07-23")

FEATURE_LABELS = {
    "tenure_days": "account tenure",
    "past_redemptions": "history of claiming benefits",
    "days_since_last_redemption": "time since last claimed benefit",
    "tx_count_365d": "transaction activity in the past year",
    "days_since_last_tx": "recency of last transaction",
    "prior_engagement_rate": "past response rate to nudges",
    "card_tier_gold": "Gold tier",
    "card_tier_platinum": "Platinum tier",
    "card_tier_centurion": "Centurion tier",
    "channel_push": "push notification channel",
    "channel_email": "email channel",
    "channel_in_app": "in-app channel",
}


class PropensityScorer:
    def __init__(self):
        self.feature_columns = json.loads((ARTIFACT_DIR / "feature_columns.json").read_text())
        self.metrics = json.loads((ARTIFACT_DIR / "metrics.json").read_text())
        self.model = xgb.XGBClassifier()
        self.model.load_model(str(ARTIFACT_DIR / "propensity_model.json"))
        self.explainer = shap.TreeExplainer(self.model)

    def _row_for_member(self, store, member_id: str, channel: str = "push") -> pd.DataFrame:
        member = store.member(member_id)
        redemptions = store.redemptions[store.redemptions.member_id == member_id]
        tx = store.transactions_for(member_id)
        engagement = store.engagement[store.engagement.member_id == member_id]

        past_redemptions = len(redemptions)
        days_since_last_redemption = (
            (TODAY - redemptions["claimed_date"].max()).days if not redemptions.empty else 999
        )
        tx_count_365d = len(tx)
        days_since_last_tx = (TODAY - tx["date"].max()).days if not tx.empty else 999
        if len(engagement) > 0:
            prior_engagement_rate = float(engagement["acted_within_14d"].mean())
        else:
            prior_engagement_rate = 0.3

        row = {
            "tenure_days": member["tenure_days"],
            "past_redemptions": past_redemptions,
            "days_since_last_redemption": days_since_last_redemption,
            "tx_count_365d": tx_count_365d,
            "days_since_last_tx": days_since_last_tx,
            "prior_engagement_rate": prior_engagement_rate,
            "card_tier_gold": int(member["card_tier"] == "Gold"),
            "card_tier_platinum": int(member["card_tier"] == "Platinum"),
            "card_tier_centurion": int(member["card_tier"] == "Centurion"),
            "channel_push": int(channel == "push"),
            "channel_email": int(channel == "email"),
            "channel_in_app": int(channel == "in_app"),
        }
        return pd.DataFrame([row])[self.feature_columns]

    def score(self, store, member_id: str, channel: str = "push") -> dict:
        X = self._row_for_member(store, member_id, channel)
        prob = float(self.model.predict_proba(X)[0, 1])
        shap_vals = self.explainer.shap_values(X)[0]

        contributions = sorted(
            zip(self.feature_columns, shap_vals.tolist(), X.iloc[0].tolist()),
            key=lambda t: -abs(t[1]),
        )
        top = contributions[:3]
        reasons = []
        for feat, val, raw in top:
            direction = "increases" if val > 0 else "decreases"
            reasons.append(f"{FEATURE_LABELS.get(feat, feat)} {direction} the likelihood of action")

        return {
            "propensity_score": round(prob, 4),
            "confidence_band": _band(prob),
            "top_reasons": reasons,
            "model_auc_roc": self.metrics["xgboost_auc_roc"],
        }


def _band(prob: float) -> str:
    if prob >= 0.6:
        return "high"
    if prob >= 0.35:
        return "medium"
    return "low"
