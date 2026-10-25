import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { TOOLS } from "@/lib/tools";
import { Page, PageHeader } from "@/components/eg";

export const Route = createFileRoute("/tools")({
  head: () => ({ meta: [
    { title: "Forensic tools — EvidenceGuard" },
    { name: "description", content: "Searchable catalogue of EvidenceGuard integrity, image, audio and evidence-management checks." },
    { property: "og:title", content: "Forensic tools — EvidenceGuard" },
    { property: "og:description", content: "Category-based directory of available and planned forensic checks." },
  ] }),
  component: Tools,
});

const MEDIA = ["All", "Any", "Image", "Video", "Audio"];
const AVAIL = ["All", "available", "planned"];
const PURPOSE = ["All", ...new Set(TOOLS.map((t) => t.purpose))];

function Select({ label, value, set, opts }: { label: string; value: string; set: (v: string) => void; opts: string[] }) {
  return (
    <label className="text-sm text-muted-foreground">{label}
      <select value={value} onChange={(e) => set(e.target.value)} className="ml-2 rounded-md border border-input bg-secondary px-2 py-1.5 text-foreground">
        {opts.map((o) => <option key={o}>{o}</option>)}
      </select>
    </label>
  );
}

function Tools() {
  const [q, setQ] = useState(""); const [m, setM] = useState("All"); const [a, setA] = useState("All"); const [p, setP] = useState("All");
  const list = useMemo(() => TOOLS.filter((t) =>
    (m === "All" || t.media === m) && (a === "All" || t.availability === a) && (p === "All" || t.purpose === p) &&
    (t.name + t.desc + t.category).toLowerCase().includes(q.toLowerCase())), [q, m, a, p]);
  const cats = [...new Set(list.map((t) => t.category))];
  return (
    <Page>
      <PageHeader eyebrow="TOOL EXPLORER" title="Forensic tools">Listed tools are labelled honestly: “planned” means not implemented.</PageHeader>
      <div className="glass mb-8 flex flex-wrap items-center gap-4 p-4">
        <div className="relative min-w-60 flex-1">
          <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search tools…" aria-label="Search tools" className="w-full rounded-md border border-input bg-secondary py-2 pl-9 pr-3 text-sm" />
        </div>
        <Select label="Media" value={m} set={setM} opts={MEDIA} />
        <Select label="Availability" value={a} set={setA} opts={AVAIL} />
        <Select label="Purpose" value={p} set={setP} opts={PURPOSE} />
      </div>
      {cats.length === 0 && <p className="text-muted-foreground">No tools match these filters.</p>}
      {cats.map((c) => (
        <section key={c} className="mb-10">
          <h2 className="mb-3 font-mono text-xs tracking-[0.2em] text-cyan">{c.toUpperCase()}</h2>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {list.filter((t) => t.category === c).map((t) => (
              <article key={t.name} className="glass flex flex-col p-5 transition-colors hover:border-cyan/50">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold">{t.name}</h3>
                  <span className={`rounded border px-2 py-0.5 font-mono text-[10px] uppercase ${t.availability === "available" ? "border-success/40 text-success" : "border-border text-muted-foreground"}`}>{t.availability}</span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{t.desc}</p>
                <p className="mt-3 text-xs"><span className="text-muted-foreground">Types:</span> {t.types}</p>
                <p className="mt-1 text-xs text-warning/90">Limit: {t.limits}</p>
                {t.availability === "available" && (
                  <Link to={t.category === "Evidence Management" ? "/vault" : "/investigate"} className="mt-4 self-start text-sm font-medium text-cyan hover:underline">Run check →</Link>
                )}
              </article>
            ))}
          </div>
        </section>
      ))}
    </Page>
  );
}
