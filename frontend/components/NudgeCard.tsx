import { Nudge } from "@/lib/api";
import { Badge, DarkCard } from "./ui";

const bandCopy: Record<string, { label: string; tone: "green" | "gold" | "slate" }> = {
  high: { label: "High likelihood to act", tone: "green" },
  medium: { label: "Medium likelihood to act", tone: "gold" },
  low: { label: "Low likelihood to act", tone: "slate" },
};

export function NudgeCard({ nudge }: { nudge: Nudge }) {
  const copy = bandCopy[nudge.confidence_band] ?? bandCopy.low;
  return (
    <DarkCard className="p-6">
      <div className="flex items-center justify-between">
        <p className="text-xs font-bold uppercase tracking-widest text-gold-light text-gold">
          Recommended Nudge
        </p>
        <Badge tone={copy.tone === "gold" ? "gold" : copy.tone}>{copy.label}</Badge>
      </div>
      <div className="mt-4 flex items-baseline gap-2">
        <span className="font-serif text-4xl font-bold">
          {Math.round(nudge.propensity_score * 100)}%
        </span>
        <span className="text-sm text-white/60">propensity to act within 14 days</span>
      </div>
      <div className="mt-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-white/50 mb-2">
          Why this score (SHAP)
        </p>
        <ul className="space-y-1.5 text-sm text-white/85">
          {nudge.top_reasons.map((r, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-gold">•</span>
              <span className="capitalize">{r}</span>
            </li>
          ))}
        </ul>
      </div>
      <p className="mt-5 text-xs text-white/40">
        Model AUC-ROC on held-out synthetic data: {nudge.model_auc_roc.toFixed(3)}
      </p>
    </DarkCard>
  );
}
