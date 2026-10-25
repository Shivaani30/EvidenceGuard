import { createFileRoute } from "@tanstack/react-router";
import { Page, PageHeader } from "@/components/eg";

export const Route = createFileRoute("/methodology")({
  head: () => ({ meta: [
    { title: "Methodology — EvidenceGuard" },
    { name: "description", content: "How EvidenceGuard computes hashes, runs ELA, reads metadata and records audit events." },
    { property: "og:title", content: "Methodology — EvidenceGuard" },
    { property: "og:description", content: "The forensic methods behind EvidenceGuard, and their limits." },
  ] }),
  component: Methodology,
});

const ITEMS = [
  ["SHA-256", "A cryptographic digest of every byte. Identical files produce identical hashes; a single changed bit produces a completely different one. A mismatch means the bytes differ — not that someone acted maliciously."],
  ["Metadata", "JPEG APP segments and EXIF are scanned for timestamps and editing-software signatures. Metadata can be stripped or forged, so it is an indicator only."],
  ["Error Level Analysis", "The image is re-saved at 90% JPEG quality and the per-pixel difference is amplified. Regions saved at a different compression history can appear brighter, but edges and textures do too."],
  ["WAV observations", "The RIFF/WAVE header is parsed for format, channels and sample rate, and the declared size is compared with the actual size."],
  ["Audit chain", "Every event stores the SHA-256 of its content plus the previous event's hash. Verifying the chain recomputes each link."],
  ["Privacy", "All processing runs in your browser. Evidence files are never uploaded; records are stored in this browser's local storage, so clearing site data removes them."],
];

function Methodology() {
  return (
    <Page>
      <PageHeader eyebrow="METHODOLOGY" title="How the checks work">EvidenceGuard reports indicators, never AI authenticity verdicts.</PageHeader>
      <div className="grid gap-4 md:grid-cols-2">
        {ITEMS.map(([t, d]) => <section key={t} className="glass p-6"><h2 className="font-semibold text-cyan">{t}</h2><p className="mt-2 text-sm text-muted-foreground">{d}</p></section>)}
      </div>
    </Page>
  );
}
