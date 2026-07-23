"""
BenefitIQ core engine
----------------------
Two responsibilities, kept deliberately separate:

1. EntitlementMapper  - deterministic, auditable rule matching. For a given
                         member, walks their card tier's benefit catalog and
                         their transaction history and decides which
                         benefits they are eligible for.

2. GapQuantifier       - takes "eligible but unclaimed" entitlements and
                          prices them using the historical redemption-value
                          distribution for that benefit type, rather than a
                          flat guess.

Both are pure functions over the synthetic CSV/JSON data in /data so they
can be unit-tested and reused unchanged by the FastAPI layer.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
TODAY = datetime(2026, 7, 23)


@dataclass
class EntitlementGap:
    member_id: str
    benefit_id: str
    benefit_name: str
    matched_transaction_id: str
    matched_date: str
    estimated_value: float
    value_low: float
    value_high: float
    days_until_window_closes: int


class DataStore:
    """Loads and caches the synthetic dataset once per process."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.card_products = json.loads((data_dir / "card_products.json").read_text())
        self.members = pd.read_csv(data_dir / "cardholders.csv")
        self.transactions = pd.read_csv(data_dir / "transactions.csv", parse_dates=["date"])
        self.redemptions = pd.read_csv(data_dir / "redemption_history.csv", parse_dates=["claimed_date"])
        self.engagement = pd.read_csv(data_dir / "engagement_history.csv", parse_dates=["nudge_date"])
        # index transactions by member for fast lookup — this is the
        # production analogue of indexing by merchant category code
        self._tx_by_member = {mid: df for mid, df in self.transactions.groupby("member_id")}
        self._redemptions_by_member = {
            mid: set(df["benefit_id"]) for mid, df in self.redemptions.groupby("member_id")
        }
        # historical redemption value distribution per benefit_id, used by
        # the gap quantifier for probability-weighted pricing
        self._value_distributions = {
            bid: df["value_claimed"].values
            for bid, df in self.redemptions.groupby("benefit_id")
        }

    def member(self, member_id: str) -> Optional[dict]:
        row = self.members[self.members.member_id == member_id]
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    def transactions_for(self, member_id: str) -> pd.DataFrame:
        return self._tx_by_member.get(member_id, self.transactions.iloc[0:0])

    def claimed_benefits(self, member_id: str) -> set:
        return self._redemptions_by_member.get(member_id, set())

    def value_distribution(self, benefit_id: str, fallback_range: list) -> np.ndarray:
        dist = self._value_distributions.get(benefit_id)
        if dist is None or len(dist) < 5:
            # not enough real redemptions yet — fall back to the catalog's
            # designed value range, sampled uniformly
            return np.random.uniform(fallback_range[0], fallback_range[1], size=200)
        return dist


class EntitlementMapper:
    """Task 1 — maps transactions to entitlements the member qualifies for
    but has not claimed, using indexed MCC lookups against the benefit
    catalog (O(transactions) per member, not O(transactions × catalog))."""

    def __init__(self, store: DataStore):
        self.store = store

    def unclaimed_for_member(self, member_id: str) -> list[dict]:
        member = self.store.member(member_id)
        if member is None:
            return []
        tier = member["card_tier"]
        catalog = self.store.card_products[tier]["benefits"]
        claimed = self.store.claimed_benefits(member_id)
        tx = self.store.transactions_for(member_id)
        if tx.empty:
            return []

        # index this member's transactions by MCC once
        tx_by_mcc: dict[int, pd.DataFrame] = {mcc: g for mcc, g in tx.groupby("mcc")}

        results = []
        for benefit in catalog:
            if benefit["id"] in claimed:
                continue  # already claimed — not a gap
            candidate_tx = None
            for mcc in benefit["trigger_mcc"]:
                group = tx_by_mcc.get(mcc)
                if group is None:
                    continue
                eligible = group[group["amount"] >= benefit["min_amount"]]
                eligible = eligible[(TODAY - eligible["date"]).dt.days <= benefit["window_days"]]
                if not eligible.empty:
                    row = eligible.sort_values("date", ascending=False).iloc[0]
                    if candidate_tx is None or row["date"] > candidate_tx["date"]:
                        candidate_tx = row
            if candidate_tx is not None:
                days_elapsed = (TODAY - candidate_tx["date"]).days
                window_left = max(benefit["window_days"] - days_elapsed, 0)
                results.append({
                    "benefit": benefit,
                    "matched_transaction_id": candidate_tx["transaction_id"],
                    "matched_date": candidate_tx["date"].strftime("%Y-%m-%d"),
                    "days_until_window_closes": window_left,
                })
        return results


class GapQuantifier:
    """Task 2 — prices each unclaimed entitlement using the historical
    redemption-value distribution for that benefit type, producing a point
    estimate plus a credible range rather than a flat number."""

    def __init__(self, store: DataStore):
        self.store = store

    def price(self, member_id: str, unclaimed: list[dict]) -> list[EntitlementGap]:
        gaps = []
        for item in unclaimed:
            benefit = item["benefit"]
            dist = self.store.value_distribution(benefit["id"], benefit["value_range"])
            point = float(np.median(dist))
            low = float(np.percentile(dist, 25))
            high = float(np.percentile(dist, 75))
            gaps.append(EntitlementGap(
                member_id=member_id,
                benefit_id=benefit["id"],
                benefit_name=benefit["name"],
                matched_transaction_id=item["matched_transaction_id"],
                matched_date=item["matched_date"],
                estimated_value=round(point, 2),
                value_low=round(low, 2),
                value_high=round(high, 2),
                days_until_window_closes=item["days_until_window_closes"],
            ))
        return gaps

    def total_value(self, gaps: list[EntitlementGap]) -> float:
        return round(sum(g.estimated_value for g in gaps), 2)


if __name__ == "__main__":
    store = DataStore()
    mapper = EntitlementMapper(store)
    quantifier = GapQuantifier(store)

    sample_id = store.members.iloc[0]["member_id"]
    unclaimed = mapper.unclaimed_for_member(sample_id)
    gaps = quantifier.price(sample_id, unclaimed)
    print(f"Sample member: {sample_id} ({store.member(sample_id)['card_tier']})")
    print(f"Unclaimed entitlements found: {len(gaps)}")
    for g in gaps:
        print(f"  - {g.benefit_name}: ~${g.estimated_value} (${g.value_low}-${g.value_high}), "
              f"{g.days_until_window_closes}d left")
    print(f"Total unclaimed value: ${quantifier.total_value(gaps)}")
