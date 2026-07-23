import { ReactNode } from "react";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-2xl bg-white shadow-sm ring-1 ring-navy/5 ${className}`}>
      {children}
    </div>
  );
}

export function DarkCard({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-2xl bg-navy text-white shadow-lg ${className}`}>{children}</div>
  );
}

export function Badge({
  children,
  tone = "gold",
}: {
  children: ReactNode;
  tone?: "gold" | "slate" | "green" | "red";
}) {
  const tones: Record<string, string> = {
    gold: "bg-gold/15 text-gold border-gold/30",
    slate: "bg-slate-custom/10 text-slate-custom border-slate-custom/20",
    green: "bg-emerald-100 text-emerald-700 border-emerald-200",
    red: "bg-red-100 text-red-700 border-red-200",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function SectionKicker({ children }: { children: ReactNode }) {
  return (
    <p className="text-xs font-bold uppercase tracking-widest text-gold mb-2">{children}</p>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center rounded-2xl border border-dashed border-navy/20 p-12 text-sm text-slate-custom">
      {message}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
      <p className="font-semibold mb-1">Couldn&apos;t reach the BenefitIQ API</p>
      <p>{message}</p>
      <p className="mt-2 text-red-600/80">
        Make sure the backend is running:{" "}
        <code className="rounded bg-red-100 px-1.5 py-0.5">
          cd backend && uvicorn app.main:app --reload
        </code>
      </p>
    </div>
  );
}
