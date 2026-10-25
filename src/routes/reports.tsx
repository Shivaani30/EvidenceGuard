import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Empty, Hash, Page, PageHeader } from "@/components/eg";
import { JobView } from "./investigate";
import { audit, buildReport, useStore } from "@/lib/store";
import { api } from "@/lib/api";

export const Route = createFileRoute("/reports")({
  validateSearch: (s: Record<string, unknown>) => ({ id: typeof s['id'] === "string" ? (s['id'] as string) : undefined }),
  head: () => ({ meta: [
    { title: "Reports — EvidenceGuard" },
    { name: "description", content: "Structured digital evidence forensic investigation reports with hashes, checks, limitations and PDF export." },
    { property: "og:title", content: "Reports — EvidenceGuard" },
    { property: "og:description", content: "Review and export digital evidence forensic investigation reports." },
  ] }),
  component: Reports,
});

function Reports() {
  const { id } = Route.useSearch();
  const { evidence, audit: events } = useStore();
  const [backendReport, setBackendReport] = useState<any>(null);

  const ev = evidence.find((e) => e.id === id);

  useEffect(() => {
    if (ev) {
      api.getReport(ev.id)
        .then((data) => setBackendReport(data))
        .catch(() => {});
    }
  }, [ev?.id]);

  if (!ev) return (
    <Page>
      <PageHeader eyebrow="REPORTS" title="Choose an evidence record" />
      {evidence.length === 0 ? <Empty title="No reports yet">Run an investigation first.</Empty> : (
        <div className="grid gap-2 md:grid-cols-2">
          {evidence.map((e) => <Link key={e.id} to="/reports" search={{ id: e.id }} className="glass p-4 text-sm hover:border-cyan/50"><span className="font-mono text-cyan">{e.id}</span> · {e.name}<div className="text-muted-foreground">{e.caseName}</div></Link>)}
        </div>
      )}
    </Page>
  );

  const report = backendReport || buildReport(ev, evidence, events);

  const downloadJson = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${ev.id}-report.json`;
    a.click();
    URL.revokeObjectURL(url);
    audit("report.exported", `${ev.id} json`);
  };

  const assessment = report.assessment || ev.assessment;

  return (
    <Page>
      <PageHeader eyebrow="FORENSIC REPORT" title={report.investigation} />
      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <div className="space-y-4">
          {assessment && (
            <section className="glass p-5 text-sm border-cyan/40">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold">Executive Assessment</h2>
                <span className="font-mono text-xs uppercase font-bold text-cyan">{assessment.classification}</span>
              </div>
              <p className="mt-2 text-muted-foreground">{assessment.summary}</p>
              <div className="mt-3 grid grid-cols-3 gap-2 font-mono text-xs bg-secondary/50 p-3 rounded">
                <div>Integrity: <strong>{assessment.integrity_score}%</strong></div>
                <div>Tamper: <strong>{(assessment.tampering_likelihood * 100).toFixed(1)}%</strong></div>
                <div>Confidence: <strong>{(assessment.confidence * 100).toFixed(0)}%</strong></div>
              </div>
            </section>
          )}

          <section className="glass p-5 text-sm">
            <h2 className="mb-2 font-semibold">Evidence Details</h2>
            <p><span className="font-mono text-cyan">{ev.id}</span> · {ev.name} · {ev.size.toLocaleString()} bytes · {ev.kind.toUpperCase()}</p>
            <div className="mt-1"><Hash value={ev.sha256} /></div>
            {report.reference && (
              <>
                <h3 className="mt-4 font-semibold">Reference Comparison</h3>
                <p>{report.reference.id} · {report.reference.filename}</p>
                <Hash value={report.reference.sha256} />
              </>
            )}
          </section>

          <section className="glass p-5 text-sm">
            <h2 className="mb-2 font-semibold text-warning">Limitations & Standards</h2>
            <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
              {report.limitations.map((l: string) => <li key={l}>{l}</li>)}
            </ul>
          </section>

          <section className="glass p-5 text-sm">
            <h2 className="mb-2 font-semibold">Audit Chain History</h2>
            <ul className="space-y-1 text-muted-foreground">
              {report.audit.map((a: any) => (
                <li key={a.id}>#{a.id} {a.action} — {new Date(a.ts).toLocaleString()}</li>
              ))}
            </ul>
          </section>

          <div className="flex gap-3 pt-2">
            <button onClick={downloadJson} className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">
              Export JSON
            </button>
            <a
              href={api.getReportPdfUrl(ev.id)}
              download={`${ev.id}-forensic-report.pdf`}
              className="inline-flex items-center justify-center rounded-md border border-cyan/50 bg-secondary px-4 py-2 text-sm font-medium text-cyan hover:bg-secondary/80 glow"
            >
              Export PDF (Court-Ready)
            </a>
          </div>
        </div>

        <div className="glass p-5">
          <h2 className="font-semibold mb-3">Forensic Check Matrix</h2>
          <JobView ev={ev} />
        </div>
      </div>
    </Page>
  );
}
