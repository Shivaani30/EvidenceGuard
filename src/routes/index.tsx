import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Fingerprint, ScanSearch, ShieldCheck, FileText, Database, Layers, Activity } from "lucide-react";
import { Hero3D } from "@/components/Hero3D";
import { api, type DashboardStats } from "@/lib/api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "EvidenceGuard — Digital evidence integrity verification" },
      { name: "description", content: "Inspect digital evidence, compare SHA-256 integrity, examine forensic indicators and keep an auditable record." },
      { property: "og:title", content: "EvidenceGuard — Verify the evidence" },
      { property: "og:description", content: "Multi-layer digital evidence authenticity & integrity verification platform." },
    ],
  }),
  component: Index,
});

const STEPS = [
  { icon: Fingerprint, t: "Register", d: "Immutable storage with SHA-256 and SHA-512 cryptographic digests." },
  { icon: ScanSearch, t: "Analyse", d: "Multi-layer image, audio, video and metadata forensic pipelines." },
  { icon: ShieldCheck, t: "Verify", d: "Cross-modal temporal correlation and weighted evidence fusion." },
  { icon: FileText, t: "Report", d: "Court-ready structured PDF and JSON forensic reports." },
];

function Index() {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    api.getDashboardStats().then(setStats).catch(() => {});
  }, []);

  return (
    <main>
      <section className="mx-auto grid max-w-7xl items-center gap-10 px-5 py-16 md:grid-cols-2 md:py-24">
        <div>
          <p className="font-mono text-xs tracking-[0.25em] text-cyan">DIGITAL EVIDENCE FORENSICS</p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-tight md:text-6xl">Every file has a story. Verify the evidence.</h1>
          <p className="mt-5 max-w-lg text-lg text-muted-foreground">Inspect digital evidence, compare file integrity, examine multi-layer forensic indicators, and preserve a tamper-evident audit record of every investigation.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/investigate" className="rounded-md bg-primary px-5 py-3 font-medium text-primary-foreground glow hover:opacity-90">Start an investigation</Link>
            <Link to="/tools" className="rounded-md border border-border px-5 py-3 font-medium hover:bg-secondary">Explore forensic tools</Link>
          </div>
          <p className="mt-8 font-mono text-xs tracking-widest text-muted-foreground">REGISTER <span className="text-cyan">→</span> ANALYSE <span className="text-cyan">→</span> VERIFY <span className="text-cyan">→</span> REPORT</p>
        </div>
        <Hero3D />
      </section>

      {/* Live System Metrics */}
      {stats && stats.total_evidence > 0 && (
        <section className="mx-auto max-w-7xl px-5 pb-12">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="glass p-5">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-xs uppercase font-mono tracking-wider">Total Evidence</span>
                <Database className="size-4 text-cyan" />
              </div>
              <p className="mt-2 text-2xl font-semibold">{stats.total_evidence}</p>
              <p className="mt-1 text-xs text-muted-foreground">{stats.completed_analyses} completed analyses</p>
            </div>
            <div className="glass p-5">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-xs uppercase font-mono tracking-wider">Modalities Analyzed</span>
                <Layers className="size-4 text-cyan" />
              </div>
              <p className="mt-2 text-2xl font-semibold">{stats.images_analyzed + stats.videos_analyzed + stats.audio_analyzed}</p>
              <p className="mt-1 text-xs text-muted-foreground">{stats.images_analyzed} img · {stats.videos_analyzed} vid · {stats.audio_analyzed} aud</p>
            </div>
            <div className="glass p-5">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-xs uppercase font-mono tracking-wider">Forensic Alerts</span>
                <Activity className="size-4 text-warning" />
              </div>
              <p className="mt-2 text-2xl font-semibold text-warning">{stats.high_suspicion_cases}</p>
              <p className="mt-1 text-xs text-muted-foreground">Elevated suspicion flagged</p>
            </div>
            <div className="glass p-5">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-xs uppercase font-mono tracking-wider">Audit Chain</span>
                <ShieldCheck className="size-4 text-success" />
              </div>
              <p className="mt-2 text-2xl font-semibold text-success">{stats.chain_intact ? "Intact" : "Broken"}</p>
              <p className="mt-1 text-xs text-muted-foreground">{stats.audit_events_count} cryptographically hashed events</p>
            </div>
          </div>
        </section>
      )}

      <section className="mx-auto max-w-7xl px-5 pb-16">
        <div className="grid gap-px overflow-hidden rounded-lg border border-border bg-border md:grid-cols-4">
          {STEPS.map((s, i) => (
            <div key={s.t} className="bg-background p-6">
              <span className="font-mono text-xs text-muted-foreground">0{i + 1}</span>
              <s.icon className="mt-3 size-6 text-cyan" />
              <h3 className="mt-3 font-semibold">{s.t}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-5 pb-24 md:grid-cols-2">
        <div className="glass p-6">
          <h2 className="font-semibold text-success">Active Multi-Layer Forensic Capabilities</h2>
          <ul className="mt-3 space-y-1.5 text-sm text-muted-foreground">
            <li>• <strong>Cryptographic Integrity:</strong> SHA-256 and SHA-512 immutable hashing & reference verification</li>
            <li>• <strong>Image Forensics:</strong> EXIF metadata anomalies, genuine JPEG ELA, 8x8 block compression & copy-move</li>
            <li>• <strong>Synthetic Screening:</strong> 2D-FFT frequency spectrum analysis for diffusion/GAN grid artifacts</li>
            <li>• <strong>Video & CCTV Forensics:</strong> Duplicate/frozen frame loops, temporal cadence & PTS/DTS timeline verification</li>
            <li>• <strong>Audio Forensics:</strong> PCM waveform dynamics, STFT spectrogram artifact generation & splice detection</li>
            <li>• <strong>Reporting:</strong> Court-ready PDF reports with embedded visual artifacts and chain-of-custody tables</li>
          </ul>
        </div>
        <div className="glass p-6">
          <h2 className="font-semibold text-cyan">Forensic Decision Support Principles</h2>
          <ul className="mt-3 space-y-1.5 text-sm text-muted-foreground">
            <li>• <strong>Factual Observations vs Inferences:</strong> Statistical divergence indicates processing history, not legal intent.</li>
            <li>• <strong>Zero Byte Modification:</strong> Evidence files are stored immutably; pre- and post-analysis hashes are strictly verified.</li>
            <li>• <strong>Tamper-Evident Audit Trail:</strong> Every registration, analysis, and report export is cryptographically chained.</li>
            <li>• <strong>Cross-Modal Correlation:</strong> Audio-visual temporal anomalies reinforce investigative significance.</li>
          </ul>
          <p className="mt-4 text-xs text-muted-foreground">Engineered with real deterministic algorithms. No synthetic or randomized values.</p>
        </div>
      </section>
    </main>
  );
}
