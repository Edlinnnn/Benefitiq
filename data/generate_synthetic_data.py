"""
BenefitIQ synthetic data generator
------------------------------------
Generates a realistic (but entirely synthetic) dataset that mirrors the
shape of real card-issuer data:

  - card_products.json      benefit-entitlement catalog per card tier
  - cardholders.csv         synthetic members and their card tier
  - transactions.csv        synthetic transaction stream (with MCC codes)
  - redemption_history.csv  which entitlements have already been claimed
  - engagement_history.csv  past nudge outcomes, used to train the
                             propensity-to-act model

No real cardholder, transaction, or issuer data is used anywhere in this
project. Run with: python generate_synthetic_data.py
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

OUT_DIR = Path(__file__).parent
N_MEMBERS = 1200
N_DAYS_HISTORY = 365
TODAY = datetime(2026, 7, 23)

# --------------------------------------------------------------------------
# 1. Benefit-entitlement catalog (this is the "graph" BenefitIQ reads from)
# --------------------------------------------------------------------------
CARD_PRODUCTS = {
    "Gold": {
        "annual_fee": 250,
        "benefits": [
            {"id": "purchase_protection", "name": "Purchase Protection", "trigger_mcc": [5732, 5311, 5651, 5941],
             "min_amount": 50, "window_days": 90, "value_range": [30, 250]},
            {"id": "extended_warranty", "name": "Extended Warranty", "trigger_mcc": [5732, 5722],
             "min_amount": 100, "window_days": 365, "value_range": [40, 300]},
            {"id": "dining_credit", "name": "Dining Statement Credit", "trigger_mcc": [5812, 5814],
             "min_amount": 0, "window_days": 30, "value_range": [10, 100]},
        ],
    },
    "Platinum": {
        "annual_fee": 695,
        "benefits": [
            {"id": "purchase_protection", "name": "Purchase Protection", "trigger_mcc": [5732, 5311, 5651, 5941],
             "min_amount": 50, "window_days": 120, "value_range": [30, 300]},
            {"id": "extended_warranty", "name": "Extended Warranty", "trigger_mcc": [5732, 5722],
             "min_amount": 100, "window_days": 365, "value_range": [40, 350]},
            {"id": "travel_delay", "name": "Travel Delay Insurance", "trigger_mcc": [3000, 3001, 3002, 4511],
             "min_amount": 0, "window_days": 45, "value_range": [50, 500]},
            {"id": "lounge_access", "name": "Airport Lounge Access", "trigger_mcc": [3000, 3001, 3002, 4511],
             "min_amount": 0, "window_days": 60, "value_range": [35, 75]},
            {"id": "hotel_credit", "name": "Hotel Statement Credit", "trigger_mcc": [3501, 3502, 3503, 7011],
             "min_amount": 0, "window_days": 30, "value_range": [50, 200]},
        ],
    },
    "Centurion": {
        "annual_fee": 5000,
        "benefits": [
            {"id": "purchase_protection", "name": "Purchase Protection", "trigger_mcc": [5732, 5311, 5651, 5941],
             "min_amount": 25, "window_days": 180, "value_range": [30, 500]},
            {"id": "extended_warranty", "name": "Extended Warranty", "trigger_mcc": [5732, 5722],
             "min_amount": 50, "window_days": 730, "value_range": [40, 600]},
            {"id": "travel_delay", "name": "Travel Delay Insurance", "trigger_mcc": [3000, 3001, 3002, 4511],
             "min_amount": 0, "window_days": 60, "value_range": [75, 750]},
            {"id": "lounge_access", "name": "Airport Lounge Access", "trigger_mcc": [3000, 3001, 3002, 4511],
             "min_amount": 0, "window_days": 90, "value_range": [50, 100]},
            {"id": "hotel_credit", "name": "Hotel Statement Credit", "trigger_mcc": [3501, 3502, 3503, 7011],
             "min_amount": 0, "window_days": 30, "value_range": [100, 400]},
            {"id": "return_protection", "name": "Return Protection", "trigger_mcc": [5311, 5651, 5732, 5941],
             "min_amount": 40, "window_days": 90, "value_range": [25, 200]},
        ],
    },
}

MCC_POOL = [5732, 5311, 5651, 5941, 5722, 5812, 5814, 3000, 3001, 3002,
            4511, 3501, 3502, 3503, 7011, 5411, 5541, 4900]

with open(OUT_DIR / "card_products.json", "w") as f:
    json.dump(CARD_PRODUCTS, f, indent=2)

# --------------------------------------------------------------------------
# 2. Cardholders
# --------------------------------------------------------------------------
tiers = list(CARD_PRODUCTS.keys())
tier_weights = [0.55, 0.35, 0.10]  # Gold most common, Centurion rarest

members = []
for i in range(N_MEMBERS):
    tier = random.choices(tiers, weights=tier_weights, k=1)[0]
    tenure_days = int(np.random.exponential(scale=700))
    tenure_days = min(tenure_days, 4000)
    members.append({
        "member_id": f"M{i:05d}",
        "card_tier": tier,
        "tenure_days": tenure_days,
        "signup_date": (TODAY - timedelta(days=tenure_days)).strftime("%Y-%m-%d"),
        # behavioral trait used only to *generate* realistic data;
        # not exposed to the model as a feature directly
        "engagement_propensity": np.clip(np.random.beta(2, 3), 0, 1),
    })
members_df = pd.DataFrame(members)
members_df.to_csv(OUT_DIR / "cardholders.csv", index=False)

# --------------------------------------------------------------------------
# 3. Transactions
# --------------------------------------------------------------------------
tx_rows = []
tx_id = 0
for m in members:
    n_tx = np.random.poisson(lam=45)
    for _ in range(n_tx):
        days_ago = random.randint(0, N_DAYS_HISTORY)
        mcc = random.choice(MCC_POOL)
        amount = round(float(np.random.lognormal(mean=4.2, sigma=1.0)), 2)
        tx_rows.append({
            "transaction_id": f"T{tx_id:07d}",
            "member_id": m["member_id"],
            "date": (TODAY - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
            "mcc": mcc,
            "amount": amount,
        })
        tx_id += 1
tx_df = pd.DataFrame(tx_rows)
tx_df.to_csv(OUT_DIR / "transactions.csv", index=False)

# --------------------------------------------------------------------------
# 4. Redemption history (ground truth for "already claimed")
#    Higher engagement_propensity members claim more of what they're
#    entitled to.
# --------------------------------------------------------------------------
redemptions = []
for m in members:
    catalog = CARD_PRODUCTS[m["card_tier"]]["benefits"]
    for b in catalog:
        # probability this member claimed this benefit type at least once
        p_claim = 0.15 + 0.5 * m["engagement_propensity"]
        if random.random() < p_claim:
            value = round(random.uniform(*b["value_range"]), 2)
            days_ago = random.randint(0, N_DAYS_HISTORY)
            redemptions.append({
                "member_id": m["member_id"],
                "benefit_id": b["id"],
                "claimed_date": (TODAY - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
                "value_claimed": value,
            })
redemptions_df = pd.DataFrame(redemptions)
redemptions_df.to_csv(OUT_DIR / "redemption_history.csv", index=False)

# --------------------------------------------------------------------------
# 5. Engagement / nudge outcome history (training labels for the
#    propensity model: did the member act within 14 days of a nudge?)
# --------------------------------------------------------------------------
engagement_rows = []
for m in members:
    n_nudges = np.random.poisson(lam=9)
    for _ in range(n_nudges):
        days_ago = random.randint(0, N_DAYS_HISTORY)
        # base act-rate driven by engagement_propensity + noise, this is
        # the *true* generating process the model will try to recover
        p_act = np.clip(0.10 + 0.72 * m["engagement_propensity"]
                         + np.random.normal(0, 0.05), 0.02, 0.97)
        acted = random.random() < p_act
        engagement_rows.append({
            "member_id": m["member_id"],
            "nudge_date": (TODAY - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
            "channel": random.choice(["push", "email", "in_app"]),
            "acted_within_14d": int(acted),
        })
engagement_df = pd.DataFrame(engagement_rows)
engagement_df.to_csv(OUT_DIR / "engagement_history.csv", index=False)

print(f"Members:            {len(members_df):>6}")
print(f"Transactions:       {len(tx_df):>6}")
print(f"Redemptions:        {len(redemptions_df):>6}")
print(f"Engagement records: {len(engagement_df):>6}")
print("Synthetic data written to:", OUT_DIR)
