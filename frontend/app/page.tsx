"use client";

import { useEffect, useState } from "react";
import { api, MemberListItem, MemberSummary } from "@/lib/api";
import { Card, SectionKicker, EmptyState, ErrorState, Badge } from "@/components/ui";
import { MemberPicker } from "@/components/MemberPicker";
import { GapCard } from "@/components/GapCard";
import { NudgeCard } from "@/components/NudgeCard";

export default function MemberDashboardPage() {
  const [members, setMembers] = useState<MemberListItem[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [summary, setSummary] = useState<MemberSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .members(30)
      .then((list) => {
        setMembers(list);
        if (list.length > 0) setSelected(list[0].member_id);
      })
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    api
      .memberSummary(selected)
      .then(setSummary)
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setLoading(false));
  }, [selected]);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div>
          <SectionKicker>Card Member Experience</SectionKicker>
          <h1 className="font-serif text-3xl font-bold text-navy">
            The value you&apos;ve already paid for
          </h1>
        </div>
        {members.length > 0 && (
          <MemberPicker members={members} selected={selected} onSelect={setSelected} />
        )}
      </div>

      {error && <ErrorState message={error} />}

      {!error && loading && !summary && (
        <EmptyState message="Loading member data…" />
      )}

      {!error && summary && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <Card className="p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest text-slate-custom">
                    Your unclaimed value
                  </p>
                  <p className="mt-1 font-serif text-5xl font-bold text-navy">
                    ${summary.total_unclaimed_value.toFixed(0)}
                  </p>
                  <p className="mt-1 text-sm text-slate-custom">
                    across {summary.unclaimed_count} benefit
                    {summary.unclaimed_count === 1 ? "" : "s"} this year
                  </p>
                </div>
                <Badge tone="gold">{summary.card_tier} Card</Badge>
              </div>
            </Card>

            <Card className="p-6">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-custom mb-1">
                Detected entitlements
              </p>
              {summary.gaps.length === 0 ? (
                <EmptyState message="No unclaimed entitlements detected for this member right now — everything eligible has been claimed." />
              ) : (
                <div className="divide-y divide-navy/10">
                  {summary.gaps.map((g) => (
                    <GapCard
                      key={g.benefit_id}
                      gap={g}
                      maxValue={Math.max(...summary.gaps.map((x) => x.estimated_value))}
                    />
                  ))}
                </div>
              )}
            </Card>
          </div>

          <div>
            {summary.recommended_nudge ? (
              <NudgeCard nudge={summary.recommended_nudge} />
            ) : (
              <EmptyState message="No nudge needed — no unclaimed entitlements to prioritize." />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
