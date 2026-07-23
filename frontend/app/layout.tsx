import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "BenefitIQ — See the value you've already paid for",
  description:
    "AI-driven benefit-underutilization analytics for card issuers. Built for the CodeStreet Benefit-Underutilization Analytics challenge.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="sticky top-0 z-50 border-b border-navy/10 bg-cream/90 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gold text-navy font-serif font-bold">
                $
              </span>
              <span className="font-serif text-lg font-bold text-navy">BenefitIQ</span>
            </Link>
            <nav className="flex gap-6 text-sm font-medium text-navy/70">
              <Link href="/" className="hover:text-navy transition-colors">
                Member View
              </Link>
              <Link href="/analyst" className="hover:text-navy transition-colors">
                Analyst View
              </Link>
              <a
                href="https://github.com"
                target="_blank"
                rel="noreferrer"
                className="hover:text-navy transition-colors"
              >
                GitHub
              </a>
            </nav>
          </div>
        </header>
        <main>{children}</main>
        <footer className="border-t border-navy/10 py-8 mt-16">
          <div className="mx-auto max-w-6xl px-6 text-sm text-slate-custom">
            BenefitIQ — built for the CodeStreet Benefit-Underutilization Analytics challenge.
            All data shown is synthetically generated; no real cardholder data is used anywhere
            in this project.
          </div>
        </footer>
      </body>
    </html>
  );
}
