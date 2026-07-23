"""
Integration tests for the FastAPI backend.

Run with: pytest backend/tests/ -v
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

client = TestClient(app)


def test_root_ok():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_list_members():
    res = client.get("/api/members?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert len(data) <= 5
    assert all("member_id" in m for m in data)


def test_member_summary_shape():
    members = client.get("/api/members?limit=1").json()
    member_id = members[0]["member_id"]
    res = client.get(f"/api/members/{member_id}/summary")
    assert res.status_code == 200
    body = res.json()
    for key in ["member_id", "card_tier", "total_unclaimed_value", "gaps"]:
        assert key in body
    assert body["total_unclaimed_value"] >= 0
    # gaps must be sorted descending by value
    values = [g["estimated_value"] for g in body["gaps"]]
    assert values == sorted(values, reverse=True)


def test_member_summary_404_for_unknown_member():
    res = client.get("/api/members/DOES_NOT_EXIST/summary")
    assert res.status_code == 404


def test_nudge_score_bounds():
    members = client.get("/api/members?limit=1").json()
    member_id = members[0]["member_id"]
    res = client.get(f"/api/members/{member_id}/nudge")
    assert res.status_code == 200
    body = res.json()
    assert 0.0 <= body["propensity_score"] <= 1.0
    assert body["confidence_band"] in {"high", "medium", "low"}
    assert len(body["top_reasons"]) == 3


def test_portfolio_analytics_consistency():
    res = client.get("/api/analytics/portfolio?sample_size=40")
    assert res.status_code == 200
    body = res.json()
    assert body["sample_size"] == 40
    assert 0.0 <= body["underutilization_rate"] <= 1.0
    assert body["members_with_unclaimed_value"] <= body["sample_size"]
    tier_members = sum(t["members"] for t in body["by_card_tier"])
    assert tier_members == body["sample_size"]


def test_model_metrics_reasonable():
    res = client.get("/api/model/metrics")
    assert res.status_code == 200
    body = res.json()
    # a real, non-trivial model should beat a coin flip by a meaningful margin
    assert body["xgboost_auc_roc"] > 0.6
    assert body["xgboost_auc_roc"] >= body["logistic_regression_baseline_auc_roc"]
