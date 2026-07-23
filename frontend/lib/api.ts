export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Gap {
  benefit_id: string;
  benefit_name: string;
  estimated_value: number;
  value_low: number;
  value_high: number;
  days_until_window_closes: number;
  matched_transaction_id: string;
  matched_date: string;
}

export interface Nudge {
  propensity_score: number;
  confidence_band: "high" | "medium" | "low";
  top_reasons: string[];
  model_auc_roc: number;
}

export interface MemberSummary {
  member_id: string;
  card_tier: string;
  tenure_days: number;
  total_unclaimed_value: number;
  unclaimed_count: number;
  gaps: Gap[];
  recommended_nudge: Nudge | null;
}

export interface MemberListItem {
  member_id: string;
  card_tier: string;
  tenure_days: number;
}

export interface PortfolioAnalytics {
  sample_size: number;
  members_with_unclaimed_value: number;
  underutilization_rate: number;
  total_unclaimed_value_sampled: number;
  avg_unclaimed_value_per_member: number;
  by_card_tier: { card_tier: string; members: number; avg_unclaimed_value: number }[];
  by_benefit_type: { benefit_name: string; unclaimed_count: number; total_value: number }[];
}

export interface ModelMetrics {
  xgboost_auc_roc: number;
  logistic_regression_baseline_auc_roc: number;
  calibration_mean_abs_gap: number;
  train_rows: number;
  test_rows: number;
  positive_rate_test: number;
  top_features_by_mean_abs_shap: { feature: string; mean_abs_shap: number }[];
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Request to ${path} failed with status ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  members: (limit = 20, tier?: string) =>
    getJSON<MemberListItem[]>(`/api/members?limit=${limit}${tier ? `&card_tier=${tier}` : ""}`),
  memberSummary: (memberId: string) => getJSON<MemberSummary>(`/api/members/${memberId}/summary`),
  portfolio: (sampleSize = 150) =>
    getJSON<PortfolioAnalytics>(`/api/analytics/portfolio?sample_size=${sampleSize}`),
  modelMetrics: () => getJSON<ModelMetrics>("/api/model/metrics"),
};
