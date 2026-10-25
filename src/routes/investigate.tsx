import { createFileRoute, Link } from "@tanstack/react-router";
import { Fragment, useState } from "react";
import { Upload } from "lucide-react";
import { toast } from "sonner";
import { Page, PageHeader, Hash, StateBadge } from "@/components/eg";
import { addEvidence, audit, updateEvidence, useStore, type Evidence } from "@/lib/store";
import { compareHashes, inspectImageMetadata, inspectWav, runELA, safeName, sha256Hex, sniffType, validateFile, type CheckResult } from "@/lib/forensics";
import { api } from "@/lib/api";

export const Route = createFileRoute("/investigate")({
  head: () => ({ meta: [
    { title: "New investigation — EvidenceGuard" },
    { name: "description", content: "Upload evidence, compute SHA-256, compare to a reference and run multi-layer forensic checks." },
    { property: "og:title", content: "New investigation — EvidenceGuard" },
    { property: "og:description", content: "Guided digital evidence registration and multi-layer forensic analysis workflow." },
  ] }),
  component: Investigate,
});

const CHECKS = [
  // Image Forensics
  { id: "metadata", label: "Metadata & EXIF inspection", kinds: ["jpeg", "png", "webp"] },
  { id: "ela", label: "JPEG Error Level Analysis (ELA)", kinds: ["jpeg", "png", "webp"] },
  { id: "compression", label: "JPEG 8x8 block & double-compression analysis", kinds: ["jpeg"] },
  { id: "splicing", label: "Copy-move & noise splicing screening", kinds: ["jpeg", "png", "webp"] },
  { id: "synthetic_image", label: "Synthetic / AI image screening (2D-FFT)", kinds: ["jpeg", "png", "webp"] },
  // Video & CCTV Forensics
  { id: "video_duplicate", label: "Duplicate & frozen frame loop analysis", kinds: ["mp4", "avi", "mov", "mkv"] },
  { id: "video_continuity", label: "Temporal continuity & frame cadence", kinds: ["mp4", "avi", "mov", "mkv"] },
  { id: "cctv_timestamp", label: "CCTV timestamp & cadence verification", kinds: ["mp4", "avi", "mov", "mkv"] },
  { id: "deepfake_video", label: "Facial consistency & deepfake screening", kinds: ["mp4", "avi", "mov"] },
  // Audio Forensics
  { id: "wav", label: "WAV header & waveform observations", kinds: ["wav"] },
  { id: "audio_spectral", label: "Spectral analysis & STFT spectrogram", kinds: ["wav", "mp3"] },
  { id: "audio_splice", label: "Audio splice & edit boundary detection", kinds: ["wav", "mp3"] },
  { id: "synthetic_speech", label: "AI voice & synthetic speech screening", kinds: ["wav", "mp3"] },
];

function Investigate() {
  const { evidence } = useStore();
  const [caseName, setCaseName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [info, setInfo] = useState<{ hash: string; kind: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [asRef, setAsRef] = useState(false);
  const [refId, setRefId] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<string>("");
  const [progressPercent, setProgressPercent] = useState<number>(0);

  const job = evidence.find((e) => e.id === jobId);
  const refs = evidence.filter((e) => e.isReference);
  const cases = [...new Set(evidence.map((e) => e.caseName))];

  async function onFile(f: File) {
    setErr(null); setInfo(null); setFile(null); setJobId(null);
    const v = validateFile(f);
    if (v) { setErr(v); return; }
    const buf = await f.arrayBuffer();
    const kind = sniffType(new Uint8Array(buf.slice(0, 16)));
    setFile(f); setInfo({ hash: await sha256Hex(buf), kind });
    setSelected(CHECKS.filter((c) => c.kinds.includes(kind)).map((c) => c.id));
  }

  async function start() {
    if (!file || !info) return;

    let id = `EV-${Date.now().toString(36).toUpperCase()}`;
    const name = safeName(file.name);
    let preview: string | undefined = undefined;

    if (info.kind === "jpeg" || info.kind === "png" || info.kind === "webp") {
      try {
        preview = await thumb(file);
      } catch {
        preview = undefined;
      }
    }

    const pending: CheckResult[] = [
      ...(refId ? [{ id: "compare", name: "Reference SHA-256 comparison", state: "pending" as const, summary: "Queued" }] : []),
      ...CHECKS.map((c) => selected.includes(c.id)
        ? { id: c.id, name: c.label, state: "pending" as const, summary: "Queued" }
        : { id: c.id, name: c.label, state: "skipped" as const, summary: c.kinds.includes(info.kind) ? "Not selected by investigator." : `Not applicable to ${info.kind.toUpperCase()} files.` }),
    ];

    let backendSuccess = false;
    try {
      // 1. Upload to backend
      const uploaded = await api.uploadEvidence(file, caseName, asRef, refId);
      id = uploaded.id;
      if (uploaded.preview) preview = uploaded.preview;
      backendSuccess = true;
    } catch (uploadErr) {
      console.warn("Backend upload failed, operating in browser mode:", uploadErr);
    }

    const ev: Evidence = {
      id,
      name,
      size: file.size,
      kind: info.kind,
      sha256: info.hash,
      registeredAt: new Date().toISOString(),
      isReference: asRef,
      caseName: caseName.trim() || "Untitled investigation",
      referenceId: refId || undefined,
      checks: pending,
      jobStatus: "running",
      preview,
    };

    addEvidence(ev);
    setJobId(id);
    setProgressPercent(5);
    setCurrentStage("Initializing analysis");

    await audit(asRef ? "reference.registered" : "evidence.registered", `${id} ${name} sha256=${info.hash}`);

    if (backendSuccess) {
      // Run on Python backend with live progress
      try {
        const activeCheckIds = pending.filter((c) => c.state === "pending").map((c) => c.id);
        await api.startAnalysis(id, activeCheckIds);

        // Subscribe to live progress
        const unsubscribe = api.subscribeProgress(id, (update) => {
          setProgressPercent(update.progress);
          setCurrentStage(update.message || update.stage);
        });

        // Poll status until completion
        const poll = setInterval(async () => {
          try {
            const st = await api.getJobStatus(id);
            if (st.checks && st.checks.length > 0) {
              updateEvidence(id, { checks: st.checks, jobStatus: st.status === "completed" ? "done" : "running" });
            }
            if (st.status === "completed" || st.status === "failed") {
              clearInterval(poll);
              unsubscribe();
              updateEvidence(id, { jobStatus: "done" });
              toast.success("Forensic analysis completed");
            }
          } catch {
            // poll retry
          }
        }, 1000);

        return;
      } catch (runErr) {
        console.error("Backend analysis error, falling back to client checks:", runErr);
      }
    }

    // In-browser fallback if backend is unavailable
    const bytes = new Uint8Array(await file.arrayBuffer());
    const set = (r: CheckResult) => updateEvidence(id, (e) => ({ checks: e.checks.map((c) => c.id === r.id ? r : c) }));

    for (const c of pending.filter((c) => c.state === "pending")) {
      set({ ...c, state: "running", summary: "Running…" });
      let r: CheckResult;
      try {
        if (c.id === "compare") r = compareHashes(info.hash, refs.find((x) => x.id === refId)!.sha256);
        else if (c.id === "metadata") r = inspectImageMetadata(bytes, info.kind);
        else if (c.id === "ela") r = await runELA(file, info.kind);
        else if (c.id === "wav") r = inspectWav(bytes, info.kind);
        else r = { ...c, state: "skipped", summary: "Advanced detector requires backend service." };
      } catch {
        r = { ...c, state: "error", summary: "The check could not complete on this file." };
      }
      set(r);
      await audit("check.completed", `${id} ${r.id}=${r.state}`);
    }
    updateEvidence(id, { jobStatus: "done" });
    setProgressPercent(100);
    setCurrentStage("Complete");
    toast.success("Analysis complete");
  }

  return (
    <Page>
      <PageHeader eyebrow="NEW INVESTIGATION" title="Register and analyse evidence">Multi-layer digital evidence forensic pipeline. The original bytes are preserved as immutable.</PageHeader>
      <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <div className="space-y-5">
          <Step n={1} title="Investigation">
            <input list="cases" value={caseName} onChange={(e) => setCaseName(e.target.value)} placeholder="Case name, e.g. Case 2026-014" className="w-full rounded-md border border-input bg-secondary px-3 py-2 text-sm" />
            <datalist id="cases">{cases.map((c) => <option key={c} value={c} />)}</datalist>
          </Step>
          <Step n={2} title="Evidence file">
            <label className="flex cursor-pointer flex-col items-center gap-2 rounded-md border border-dashed border-cyan/40 p-8 text-center hover:bg-secondary/50"
              onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) onFile(f); }}>
              <Upload className="size-6 text-cyan" />
              <span className="text-sm">{file ? safeName(file.name) : "Drop a file or click to choose"}</span>
              <span className="text-xs text-muted-foreground">JPEG, PNG, WebP, WAV, MP3, MP4, AVI, MOV, PDF · max 100 MB</span>
              <input type="file" className="sr-only" onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
            </label>
            {err && <p role="alert" className="mt-2 text-sm text-destructive">{err}</p>}
            {info && file && (
              <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
                <dt className="text-muted-foreground">Size</dt><dd>{file.size.toLocaleString()} bytes</dd>
                <dt className="text-muted-foreground">Detected</dt><dd className="uppercase">{info.kind}</dd>
                <dt className="text-muted-foreground">SHA-256</dt><dd><Hash value={info.hash} /></dd>
              </dl>
            )}
          </Step>
          <Step n={3} title="Reference">
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={asRef} onChange={(e) => setAsRef(e.target.checked)} /> Register this file as a trusted reference</label>
            <select value={refId} onChange={(e) => setRefId(e.target.value)} className="mt-3 w-full rounded-md border border-input bg-secondary px-3 py-2 text-sm" aria-label="Compare against reference">
              <option value="">No comparison</option>
              {refs.map((r) => <option key={r.id} value={r.id}>{r.id} · {r.name}</option>)}
            </select>
            {refs.length === 0 && <p className="mt-2 text-xs text-muted-foreground">No references registered yet.</p>}
          </Step>
          <Step n={4} title="Checks">
            <div className="space-y-1">
              {CHECKS.map((c) => {
                const ok = !!info && c.kinds.includes(info.kind);
                return (
                  <label key={c.id} className={`flex items-center gap-2 py-1 text-sm ${ok ? "" : "opacity-50"}`}>
                    <input type="checkbox" disabled={!ok} checked={selected.includes(c.id)} onChange={(e) => setSelected(e.target.checked ? [...selected, c.id] : selected.filter((s) => s !== c.id))} />
                    <span>{c.label}</span> {!ok && info && <span className="text-xs text-muted-foreground">(not applicable)</span>}
                  </label>
                );
              })}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">SHA-256 and SHA-512 are always computed. Multi-layer fusion engine correlates cross-modal findings.</p>
          </Step>
          <button disabled={!file || !info || job?.jobStatus === "running"} onClick={start} className="w-full rounded-md bg-primary py-3 font-medium text-primary-foreground glow disabled:opacity-40">Start analysis</button>
        </div>
        <div className="glass p-6">
          <h2 className="font-semibold">Job status</h2>
          {!job ? (
            <p className="mt-3 text-sm text-muted-foreground">Results appear here once you start the analysis.</p>
          ) : (
            <div>
              {currentStage && job.jobStatus === "running" && (
                <div className="mb-4 rounded border border-cyan/30 bg-cyan/10 p-3 text-xs font-mono text-cyan">
                  Stage: {currentStage} ({progressPercent}%)
                </div>
              )}
              <JobView ev={job} />
            </div>
          )}
        </div>
      </div>
    </Page>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="glass p-5">
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold"><span className="font-mono text-cyan">0{n}</span>{title}</h2>
      {children}
    </section>
  );
}

export function JobView({ ev }: { ev: Evidence }) {
  const done = ev.checks.filter((c) => !["pending", "running"].includes(c.state)).length;
  const assessment = ev.assessment;

  return (
    <div className="mt-3 space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-mono">{ev.id}</span>
        <span className="text-muted-foreground">{done}/{ev.checks.length} checks</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded bg-secondary">
        <div className="h-full bg-cyan transition-all" style={{ width: `${ev.checks.length > 0 ? (done / ev.checks.length) * 100 : 0}%` }} />
      </div>

      {assessment && (
        <div className="rounded-md border border-cyan/40 bg-secondary/60 p-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-foreground">Forensic Assessment</span>
            <span className="font-mono text-xs font-bold uppercase text-cyan">{assessment.classification}</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground">{assessment.summary}</div>
          <div className="mt-2 flex gap-4 font-mono text-xs">
            <span>Integrity: <strong className="text-foreground">{assessment.integrity_score}%</strong></span>
            <span>Confidence: <strong className="text-foreground">{assessment.confidence ? `${(assessment.confidence * 100).toFixed(0)}%` : "N/A"}</strong></span>
          </div>
        </div>
      )}

      {ev.checks.map((c) => (
        <details key={c.id} className="rounded-md border border-border p-3" open={c.state !== "skipped"}>
          <summary className="flex cursor-pointer items-center justify-between gap-2 text-sm font-medium">
            <span>{c.name}</span>
            <StateBadge state={c.state} />
          </summary>
          <p className="mt-2 text-sm text-muted-foreground">{c.summary}</p>
          {c.details && (
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 font-mono text-xs">
              {Object.entries(c.details).map(([k, v]) => (
                <Fragment key={k}>
                  <dt className="text-muted-foreground">{k}</dt>
                  <dd className="break-all">{String(v)}</dd>
                </Fragment>
              ))}
            </dl>
          )}
          {c.artifact && (
            <div className="mt-3 grid grid-cols-2 gap-2">
              {ev.preview && (
                <figure>
                  <img src={ev.preview} alt="Original" className="rounded max-h-48 object-contain bg-black/40" />
                  <figcaption className="mt-1 text-xs text-muted-foreground">Original Evidence</figcaption>
                </figure>
              )}
              <figure>
                <img src={c.artifact} alt={c.name} className="rounded max-h-48 object-contain bg-black/40" />
                <figcaption className="mt-1 text-xs text-muted-foreground">{c.name} Visual Artifact</figcaption>
              </figure>
            </div>
          )}
        </details>
      ))}

      {ev.jobStatus === "done" && (
        <div className="pt-2">
          <Link to="/reports" search={{ id: ev.id }} className="inline-block text-sm font-medium text-cyan hover:underline">
            View full forensic report & export PDF →
          </Link>
        </div>
      )}
    </div>
  );
}

async function thumb(f: File): Promise<string> {
  const bmp = await createImageBitmap(f);
  const s = Math.min(1, 600 / Math.max(bmp.width, bmp.height));
  const c = new OffscreenCanvas(Math.round(bmp.width * s), Math.round(bmp.height * s));
  c.getContext("2d")!.drawImage(bmp, 0, 0, c.width, c.height);
  const b = await c.convertToBlob({ type: "image/jpeg", quality: 0.8 });
  return new Promise((r) => { const fr = new FileReader(); fr.onload = () => r(fr.result as string); fr.readAsDataURL(b); });
}
