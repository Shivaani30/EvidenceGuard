import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Empty, Hash, Page, PageHeader } from "@/components/eg";
import { syncFromBackend, useStore, verifyChain } from "@/lib/store";

export const Route = createFileRoute("/audit")({
  head: () => ({ meta: [
    { title: "Audit trail — EvidenceGuard" },
    { name: "description", content: "Hash-linked audit events for every registration and check." },
    { property: "og:title", content: "Audit trail — EvidenceGuard" },
    { property: "og:description", content: "Tamper-evident, hash-chained investigation log." },
  ] }),
  component: Audit,
});

function Audit() {
  const { audit } = useStore();
  const [q, setQ] = useState("");
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    syncFromBackend();
  }, []);

  const list = audit.filter((a) => `${a.action} ${a.detail}`.toLowerCase().includes(q.toLowerCase())).slice().reverse();

  return (
    <Page>
      <PageHeader eyebrow="AUDIT TRAIL" title="Hash-linked events">Each event's cryptographic hash covers the previous event, so any unauthorized edit breaks the chain.</PageHeader>
      <div className="mb-6 flex flex-wrap gap-3">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter events…" aria-label="Filter events" className="flex-1 rounded-md border border-input bg-secondary px-3 py-2 text-sm" />
        <button onClick={async () => {
          const bad = await verifyChain(audit);
          setResult(bad === null ? `Chain intact (${audit.length} events verified cryptographically).` : `Chain broken at event #${bad}.`);
        }} className="rounded-md border border-border px-4 py-2 text-sm hover:bg-secondary">Verify chain</button>
      </div>
      {result && <p role="status" className={`mb-4 text-sm ${result.startsWith("Chain intact") ? "text-success" : "text-destructive"}`}>{result}</p>}
      {audit.length === 0 ? <Empty title="No events recorded">Events appear when evidence is registered or analysed.</Empty> : (
        <ol className="space-y-2">
          {list.map((a) => (
            <li key={a.id} className="glass p-3 text-sm">
              <div className="flex flex-wrap gap-3">
                <span className="font-mono text-muted-foreground">#{a.id}</span>
                <span className="font-medium text-foreground">{a.action}</span>
                <span className="text-muted-foreground">{new Date(a.ts).toLocaleString()}</span>
              </div>
              <p className="mt-1 break-all text-muted-foreground">{a.detail}</p>
              <Hash value={a.hash} />
            </li>
          ))}
        </ol>
      )}
    </Page>
  );
}
