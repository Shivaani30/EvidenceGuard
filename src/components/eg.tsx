import { Link } from "@tanstack/react-router";
import { useState, type ReactNode } from "react";
import { Shield, Menu, X } from "lucide-react";
import type { CheckState } from "@/lib/forensics";

const NAV = [
  { to: "/", label: "Overview" },
  { to: "/investigate", label: "Investigations" },
  { to: "/tools", label: "Forensic tools" },
  { to: "/vault", label: "Evidence vault" },
  { to: "/audit", label: "Audit trail" },
  { to: "/reports", label: "Reports" },
  { to: "/methodology", label: "Methodology" },
] as const;

export function SiteNav() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-6 px-5 py-3">
        <Link to="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <Shield className="size-5 text-cyan" /> EvidenceGuard
        </Link>
        <nav className="hidden flex-1 gap-1 lg:flex" aria-label="Main">
          {NAV.map((n) => (
            <Link key={n.to} to={n.to} activeOptions={{ exact: n.to === "/" }}
              className="rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground data-[status=active]:bg-secondary data-[status=active]:text-foreground">
              {n.label}
            </Link>
          ))}
        </nav>
        <Link to="/investigate" className="ml-auto hidden rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 lg:inline-flex">New investigation</Link>
        <button className="ml-auto lg:hidden" aria-label="Toggle menu" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? <X /> : <Menu />}
        </button>
      </div>
      {open && (
        <nav className="flex flex-col gap-1 border-t border-border px-5 py-3 lg:hidden" aria-label="Mobile">
          {NAV.map((n) => <Link key={n.to} to={n.to} onClick={() => setOpen(false)} className="rounded px-2 py-2 text-sm">{n.label}</Link>)}
          <Link to="/investigate" onClick={() => setOpen(false)} className="mt-2 rounded-md bg-primary px-4 py-2 text-center text-sm font-medium text-primary-foreground">New investigation</Link>
        </nav>
      )}
    </header>
  );
}

const STATE_STYLE: Record<CheckState, string> = {
  passed: "bg-success/15 text-success border-success/40",
  failed: "bg-destructive/15 text-destructive border-destructive/40",
  error: "bg-destructive/15 text-destructive border-destructive/40",
  warning: "bg-warning/15 text-warning border-warning/40",
  inconclusive: "bg-warning/10 text-warning border-warning/30",
  skipped: "bg-muted text-muted-foreground border-border",
  unavailable: "bg-muted text-muted-foreground border-border",
  running: "bg-primary/15 text-primary border-primary/40 animate-pulse",
  pending: "bg-muted text-muted-foreground border-border",
};
export function StateBadge({ state }: { state: CheckState }) {
  return <span className={`inline-flex rounded border px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider ${STATE_STYLE[state]}`}>{state}</span>;
}

export function PageHeader({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) {
  return (
    <div className="mb-8">
      <p className="font-mono text-xs tracking-[0.2em] text-cyan">{eyebrow}</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">{title}</h1>
      {children && <p className="mt-3 max-w-2xl text-muted-foreground">{children}</p>}
    </div>
  );
}

export function Page({ children }: { children: ReactNode }) {
  return <main className="mx-auto max-w-7xl px-5 py-12">{children}</main>;
}

export function Hash({ value }: { value: string }) {
  return <code className="break-all font-mono text-xs text-cyan">{value}</code>;
}

export function Empty({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="glass p-10 text-center">
      <p className="font-medium">{title}</p>
      <div className="mt-2 text-sm text-muted-foreground">{children}</div>
    </div>
  );
}
