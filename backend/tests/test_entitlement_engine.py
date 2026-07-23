"""
Unit tests for the entitlement mapping and gap quantification engine.

Run with: pytest backend/tests/ -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.entitlement_engine import DataStore, EntitlementMapper, GapQuantifier


@pytest.fixture(scope="module")
def store():
    return DataStore()


@pytest.fixture(scope="module")
def mapper(store):
    return EntitlementMapper(store)


@pytest.fixture(scope="module")
def quantifier(store):
    return GapQuantifier(store)


def test_data_store_loads_all_tables(store):
    assert len(store.members) > 0
    assert len(store.transactions) > 0
    assert set(store.card_products.keys()) == {"Gold", "Platinum", "Centurion"}


def test_every_member_has_a_valid_tier(store):
    assert store.members["card_tier"].isin(["Gold", "Platinum", "Centurion"]).all()


def test_unclaimed_never_includes_already_claimed_benefits(store, mapper):
    """A benefit the member has already redeemed must never appear as a gap —
    this is the core correctness property of the mapping engine."""
    sample = store.members.sample(n=25, random_state=1)
    for _, member in sample.iterrows():
        mid = member["member_id"]
        claimed = store.claimed_benefits(mid)
        unclaimed = mapper.unclaimed_for_member(mid)
        unclaimed_ids = {u["benefit"]["id"] for u in unclaimed}
        assert claimed.isdisjoint(unclaimed_ids), (
            f"Member {mid} has an already-claimed benefit reported as a gap"
        )


def test_unclaimed_only_includes_benefits_in_members_tier_catalog(store, mapper):
    sample = store.members.sample(n=25, random_state=2)
    for _, member in sample.iterrows():
        mid = member["member_id"]
        tier = member["card_tier"]
        catalog_ids = {b["id"] for b in store.card_products[tier]["benefits"]}
        unclaimed = mapper.unclaimed_for_member(mid)
        for u in unclaimed:
            assert u["benefit"]["id"] in catalog_ids


def test_gap_values_are_positive_and_within_a_sane_range(store, mapper, quantifier):
    sample_id = store.members.iloc[3]["member_id"]
    unclaimed = mapper.unclaimed_for_member(sample_id)
    gaps = quantifier.price(sample_id, unclaimed)
    for g in gaps:
        assert g.estimated_value > 0
        assert g.value_low <= g.estimated_value <= g.value_high
        assert g.days_until_window_closes >= 0


def test_total_value_equals_sum_of_individual_gaps(store, mapper, quantifier):
    sample_id = store.members.iloc[10]["member_id"]
    unclaimed = mapper.unclaimed_for_member(sample_id)
    gaps = quantifier.price(sample_id, unclaimed)
    expected = round(sum(g.estimated_value for g in gaps), 2)
    assert quantifier.total_value(gaps) == expected


def test_unknown_member_returns_empty_list(mapper):
    assert mapper.unclaimed_for_member("NOT_A_REAL_MEMBER") == []


def test_mapping_is_deterministic(store, mapper):
    """Same member, same data → same result every time. This is the
    auditability property the project description promises for the
    eligibility layer."""
    sample_id = store.members.iloc[7]["member_id"]
    first = mapper.unclaimed_for_member(sample_id)
    second = mapper.unclaimed_for_member(sample_id)
    first_ids = sorted(u["benefit"]["id"] for u in first)
    second_ids = sorted(u["benefit"]["id"] for u in second)
    assert first_ids == second_ids
