import { Gap } from "@/lib/api";
import { Badge } from "./ui";

export function GapCard({ gap, maxValue }: { gap: Gap; maxValue: number }) {
  const pct = Math.max(6, Math.round((gap.estimated_value / maxValue) * 100));
  const urgent = gap.days_until_window_closes <= 14;

  return (
    <div className="py-4 first:pt-0 last:pb-0">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-navy">{gap.benefit_name}</p>
          <p className="text-xs text-slate-custom mt-0.5">
            Matched to transaction {gap.matched_transaction_id} on {gap.matched_date}
          </p>
        </div>
        <div className="text-right shrink-0">
          <p className="font-serif text-xl font-bold text-navy">
            ${gap.estimated_value.toFixed(0)}
          </p>
          <p className="text-xs text-slate-custom">
            ${gap.value_low.toFixed(0)}–${gap.value_high.toFixed(0)} range
          </p>
        </div>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-navy/10">
        <div
          className="h-full rounded-full bg-gold"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-2">
        {urgent ? (
          <Badge tone="red">Expires in {gap.days_until_window_closes}d — act soon</Badge>
        ) : (
          <Badge tone="slate">{gap.days_until_window_closes}d left in window</Badge>
        )}
      </div>
    </div>
  );
}
