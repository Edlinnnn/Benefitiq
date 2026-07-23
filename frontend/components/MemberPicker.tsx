"use client";

import { MemberListItem } from "@/lib/api";

export function MemberPicker({
  members,
  selected,
  onSelect,
}: {
  members: MemberListItem[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <label htmlFor="member-select" className="text-sm font-medium text-navy/70">
        Viewing as
      </label>
      <select
        id="member-select"
        value={selected}
        onChange={(e) => onSelect(e.target.value)}
        className="rounded-lg border border-navy/15 bg-white px-3 py-2 text-sm font-medium text-navy shadow-sm focus:border-gold focus:outline-none focus:ring-1 focus:ring-gold"
      >
        {members.map((m) => (
          <option key={m.member_id} value={m.member_id}>
            {m.member_id} — {m.card_tier}
          </option>
        ))}
      </select>
    </div>
  );
}
