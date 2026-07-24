"""
BenefitIQ backend API
------------------------
FastAPI service exposing the entitlement mapping, gap quantification, and
propensity-scored nudge pipeline described in the project's architecture
(Section 5-7 of the project description). This is the API the Next.js
frontend calls for both the card-member dashboard and the analyst view.

Run with:  uvicorn app.main:app --reload --port 8000
Docs at:   http://localhost:8000/docs
"""
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.entitlement_engine import DataStore, EntitlementMapper, GapQuantifier
from app.propensity import PropensityScorer

app = FastAPI(
    title="BenefitIQ API",
    description="Entitlement mapping, gap quantification, and propensity-ranked nudges — "
                 "built for the CodeStreet Benefit-Underutilization Analytics challenge.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    # Open for a public hackathon demo — there's no auth or PII in this API,
    # so a permissive origin policy is fine here. Tighten to specific
    # origins before handling any real user data.
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache
def get_store() -> DataStore:
    return DataStore()


@lru_cache
def get_scorer() -> PropensityScorer:
    return PropensityScorer()


@app.get("/")
def root():
    return {"service": "BenefitIQ API", "status": "ok", "docs": "/docs"}


@app.get("/api/members/{member_id}/summary")
def member_summary(member_id: str):
    store = get_store()
    member = store.member(member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    mapper = EntitlementMapper(store)
    quantifier = GapQuantifier(store)
    scorer = get_scorer()

    unclaimed = mapper.unclaimed_for_member(member_id)
    gaps = quantifier.price(member_id, unclaimed)
    total = quantifier.total_value(gaps)

    nudge = scorer.score(store, member_id) if gaps else None

    return {
        "member_id": member_id,
        "card_tier": member["card_tier"],
        "tenure_days": int(member["tenure_days"]),
        "total_unclaimed_value": total,
        "unclaimed_count": len(gaps),
        "gaps": [
            {
                "benefit_id": g.benefit_id,
                "benefit_name": g.benefit_name,
                "estimated_value": g.estimated_value,
                "value_low": g.value_low,
                "value_high": g.value_high,
                "days_until_window_closes": g.days_until_window_closes,
                "matched_transaction_id": g.matched_transaction_id,
                "matched_date": g.matched_date,
            }
            for g in sorted(gaps, key=lambda x: -x.estimated_value)
        ],
        "recommended_nudge": nudge,
    }


@app.get("/api/members/{member_id}/nudge")
def member_nudge(member_id: str, channel: str = "push"):
    store = get_store()
    if store.member(member_id) is None:
        raise HTTPException(status_code=404, detail="Member not found")
    scorer = get_scorer()
    return scorer.score(store, member_id, channel)


@app.get("/api/members")
def list_members(limit: int = 20, card_tier: str | None = None):
    store = get_store()
    df = store.members
    if card_tier:
        df = df[df.card_tier == card_tier]
    return df.head(limit)[["member_id", "card_tier", "tenure_days"]].to_dict(orient="records")


@app.get("/api/analytics/portfolio")
def portfolio_analytics(sample_size: int = 150):
    """Aggregates unclaimed value across a sample of members — the data
    behind the analyst / business dashboard."""
    store = get_store()
    mapper = EntitlementMapper(store)
    quantifier = GapQuantifier(store)

    sample = store.members.sample(n=min(sample_size, len(store.members)), random_state=7)

    by_tier: dict[str, dict] = {}
    by_benefit: dict[str, dict] = {}
    total_portfolio_value = 0.0
    members_with_gaps = 0

    for _, member in sample.iterrows():
        mid = member["member_id"]
        tier = member["card_tier"]
        unclaimed = mapper.unclaimed_for_member(mid)
        gaps = quantifier.price(mid, unclaimed)
        if gaps:
            members_with_gaps += 1
        value = quantifier.total_value(gaps)
        total_portfolio_value += value

        tier_bucket = by_tier.setdefault(tier, {"members": 0, "total_unclaimed": 0.0})
        tier_bucket["members"] += 1
        tier_bucket["total_unclaimed"] += value

        for g in gaps:
            b = by_benefit.setdefault(g.benefit_name, {"unclaimed_count": 0, "total_value": 0.0})
            b["unclaimed_count"] += 1
            b["total_value"] += g.estimated_value

    n = len(sample)
    return {
        "sample_size": n,
        "members_with_unclaimed_value": members_with_gaps,
        "underutilization_rate": round(members_with_gaps / n, 4) if n else 0,
        "total_unclaimed_value_sampled": round(total_portfolio_value, 2),
        "avg_unclaimed_value_per_member": round(total_portfolio_value / n, 2) if n else 0,
        "by_card_tier": [
            {
                "card_tier": tier,
                "members": v["members"],
                "avg_unclaimed_value": round(v["total_unclaimed"] / v["members"], 2) if v["members"] else 0,
            }
            for tier, v in sorted(by_tier.items(), key=lambda kv: -kv[1]["total_unclaimed"])
        ],
        "by_benefit_type": [
            {
                "benefit_name": name,
                "unclaimed_count": v["unclaimed_count"],
                "total_value": round(v["total_value"], 2),
            }
            for name, v in sorted(by_benefit.items(), key=lambda kv: -kv[1]["total_value"])
        ],
    }


@app.get("/api/model/metrics")
def model_metrics():
    """Exposes the propensity model's training metrics — precision/recall
    style transparency for the analyst dashboard and for judges inspecting
    the API directly."""
    return get_scorer().metrics
