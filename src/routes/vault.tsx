import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Empty, Hash, Page, PageHeader, StateBadge } from "@/components/eg";
import { audit, removeEvidence, syncFromBackend, useStore } from "@/lib/store";

export const Route = createFileRoute("/vault")({
  head: () => ({ meta: [
    { title: "Evidence vault — EvidenceGuard" },
    { name: "description", content: "Search registered digital evidence, hashes and multi-layer analysis results." },
    { property: "og:title", content: "Evidence vault — EvidenceGuard" },
    { property: "og:description", content: "Searchable record of registered digital evidence." },
  ] }),
  component: Vault,
});

function Vault() {
  const { evidence } = useStore();
  const [q, setQ] = useState("");

  useEffect(() => {
    syncFromBackend();
  }, []);

  const list = evidence.filter((e) => `${e.id} ${e.name} ${e.sha256} ${e.caseName}`.toLowerCase().includes(q.toLowerCase()));

  return (
    <Page>
      <PageHeader eyebrow="EVIDENCE VAULT" title="Registered evidence">Searchable repository of registered evidence with cryptographic hashes and multi-layer analysis results.</PageHeader>
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by ID, filename, hash or case…" aria-label="Search evidence" className="mb-6 w-full rounded-md border border-input bg-secondary px-3 py-2 text-sm" />
      {evidence.length === 0 ? (
        <Empty title="No evidence yet"><Link to="/investigate" className="text-cyan hover:underline">Start an investigation</Link> to register your first file.</Empty>
      ) : (
        <div className="space-y-3">
          {list.map((e) => (
            <div key={e.id} className="glass grid gap-3 p-4 md:grid-cols-[1fr_auto]">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-mono text-cyan">{e.id}</span>
                  <span className="font-medium">{e.name}</span>
                  {e.isReference && <span className="rounded border border-success/40 px-1.5 text-[10px] uppercase text-success">reference</span>}
                  <span className="text-muted-foreground">· {e.caseName} · {new Date(e.registeredAt).toLocaleString()}</span>
                </div>
                <div className="mt-1"><Hash value={e.sha256} /></div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {e.checks.map((c) => (
                    <span key={c.id} className="flex items-center gap-1 text-xs text-muted-foreground">
                      {c.id}
                      <StateBadge state={c.state} />
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex items-start gap-3 text-sm">
                <Link to="/reports" search={{ id: e.id }} className="text-cyan hover:underline">Report</Link>
                <button className="text-destructive hover:underline" onClick={() => {
                  if (confirm(`Remove ${e.id} from the vault? The audit trail keeps a permanent record of this removal.`)) {
                    removeEvidence(e.id);
                    audit("evidence.removed", `${e.id} ${e.name}`);
                  }
                }}>Remove</button>
              </div>
            </div>
          ))}
          {list.length === 0 && <p className="text-sm text-muted-foreground">No matches.</p>}
        </div>
      )}
    </Page>
  );
}
