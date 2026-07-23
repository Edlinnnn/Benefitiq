"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const NAVY = "#0A2342";
const GOLD = "#B8892B";
const SLATE = "#5B6B82";
const PALETTE = ["#B8892B", "#0A2342", "#8FA6C9", "#D9B45C", "#5B6B82", "#CADCFC", "#132A4C"];

export function TierValueChart({
  data,
}: {
  data: { card_tier: string; avg_unclaimed_value: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E8EDF4" vertical={false} />
        <XAxis dataKey="card_tier" tick={{ fill: SLATE, fontSize: 12 }} axisLine={{ stroke: "#E8EDF4" }} />
        <YAxis
          tick={{ fill: SLATE, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `$${v}`}
        />
        <Tooltip
          formatter={(v: number) => [`$${v.toFixed(2)}`, "Avg unclaimed value"]}
          contentStyle={{ borderRadius: 8, borderColor: "#E8EDF4" }}
        />
        <Bar dataKey="avg_unclaimed_value" radius={[6, 6, 0, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={i === 0 ? GOLD : NAVY} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function BenefitTypeChart({
  data,
}: {
  data: { benefit_name: string; total_value: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 10, right: 30, left: 10, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#E8EDF4" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: SLATE, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `$${v}`}
        />
        <YAxis
          type="category"
          dataKey="benefit_name"
          width={150}
          tick={{ fill: NAVY, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={(v: number) => [`$${v.toFixed(2)}`, "Total unclaimed value"]}
          contentStyle={{ borderRadius: 8, borderColor: "#E8EDF4" }}
        />
        <Bar dataKey="total_value" radius={[0, 6, 6, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ModelComparisonChart({
  xgboost,
  baseline,
}: {
  xgboost: number;
  baseline: number;
}) {
  const data = [
    { name: "Logistic Regression\n(baseline)", auc: baseline },
    { name: "XGBoost\n(BenefitIQ)", auc: xgboost },
  ];
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E8EDF4" vertical={false} />
        <XAxis dataKey="name" tick={{ fill: SLATE, fontSize: 11 }} axisLine={{ stroke: "#E8EDF4" }} />
        <YAxis
          domain={[0, 1]}
          tick={{ fill: SLATE, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip formatter={(v: number) => [v.toFixed(3), "AUC-ROC"]} />
        <Bar dataKey="auc" radius={[6, 6, 0, 0]}>
          <Cell fill={SLATE} />
          <Cell fill={GOLD} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
