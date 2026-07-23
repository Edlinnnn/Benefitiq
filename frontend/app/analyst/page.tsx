"use client";

import { useEffect, useState } from "react";
import { api, PortfolioAnalytics, ModelMetrics } from "@/lib/api";
import { Card, SectionKicker, EmptyState, ErrorState } from "@/components/ui";
import {
  TierValueChart,
  BenefitTypeChart,
  ModelComparisonChart,
} from "@/components/PortfolioCharts";

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card className="p-5">
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-custom">
        {label}
      </p>
      <p className="mt-1 font-serif text-3xl font-bold text-navy">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-custom">{sub}</p>}
    </Card>
  );
}

export default function AnalystDashboardPage() {
  const [portfolio, setPortfolio] = useState<PortfolioAnalytics | null>(null);
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.portfolio(150), api.modelMetrics()])
      .then(([p, m]) => {
        setPortfolio(p);
        setMetrics(m);
      })
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8">
        <SectionKicker>Business Analyst Experience</SectionKicker>
        <h1 className="font-serif text-3xl font-bold text-navy">
          Portfolio-wide unclaimed value
        </h1>
        <p className="mt-1 text-sm text-slate-custom">
          Live aggregation over a sampled slice of the synthetic member portfolio — the same
          signal that powers every individual member&apos;s dashboard.
        </p>
      </div>

      {error && <ErrorState message={error} />}
      {!error && loading && <EmptyState message="Crunching portfolio numbers…" />}

      {!error && portfolio && metrics && (
        <div className="space-y-8">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              label="Underutilization rate"
              value={`${Math.round(portfolio.underutilization_rate * 100)}%`}
              sub={`${portfolio.members_with_unclaimed_value} of ${portfolio.sample_size} sampled members`}
            />
            <KpiCard
              label="Total unclaimed (sampled)"
              value={`$${portfolio.total_unclaimed_value_sampled.toLocaleString()}`}
            />
            <KpiCard
              label="Avg per member"
              value={`$${portfolio.avg_unclaimed_value_per_member.toFixed(0)}`}
            />
            <KpiCard
              label="Propensity model AUC-ROC"
              value={metrics.xgboost_auc_roc.toFixed(3)}
              sub={`vs. ${metrics.logistic_regression_baseline_auc_roc.toFixed(3)} linear baseline`}
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card className="p-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-custom mb-4">
                Avg unclaimed value by card tier
              </p>
              <TierValueChart data={portfolio.by_card_tier} />
            </Card>
            <Card className="p-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-custom mb-4">
                Model quality: XGBoost vs. interpretable baseline
              </p>
              <ModelComparisonChart
                xgboost={metrics.xgboost_auc_roc}
                baseline={metrics.logistic_regression_baseline_auc_roc}
              />
              <p className="mt-2 text-xs text-slate-custom">
                Calibration gap: {metrics.calibration_mean_abs_gap.toFixed(3)} · trained on{" "}
                {metrics.train_rows.toLocaleString()} synthetic engagement records
              </p>
            </Card>
          </div>

          <Card className="p-6">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-custom mb-4">
              Unclaimed value by benefit type — where the ecosystem underperforms
            </p>
            <BenefitTypeChart data={portfolio.by_benefit_type} />
          </Card>

          <Card className="p-6">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-custom mb-4">
              Top drivers of nudge propensity (mean |SHAP value|)
            </p>
            <div className="space-y-2">
              {metrics.top_features_by_mean_abs_shap.slice(0, 6).map((f) => {
                const max = metrics.top_features_by_mean_abs_shap[0].mean_abs_shap;
                const pct = Math.round((f.mean_abs_shap / max) * 100);
                return (
                  <div key={f.feature} className="flex items-center gap-3">
                    <span className="w-48 shrink-0 text-sm text-navy/80">
                      {f.feature.replaceAll("_", " ")}
                    </span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-navy/10">
                      <div className="h-full rounded-full bg-gold" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="w-14 text-right text-xs text-slate-custom">
                      {f.mean_abs_shap.toFixed(3)}
                    </span>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
