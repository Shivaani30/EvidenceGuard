// Real, in-browser forensic checks. Nothing leaves the device.
export type CheckState = "passed" | "failed" | "warning" | "inconclusive" | "skipped" | "unavailable" | "running" | "error" | "pending";

export interface CheckResult {
  id: string;
  name: string;
  state: CheckState;
  summary: string;
  details?: Record<string, string | number> | undefined;
  artifact?: string | undefined; // derived data URL (ELA), stored separately from the original
}

export const MAX_BYTES = 25 * 1024 * 1024;
export const ACCEPTED = ["image/jpeg", "image/png", "image/webp", "audio/wav", "audio/x-wav", "audio/wave", "video/mp4", "application/pdf"];

export function validateFile(f: File): string | null {
  if (f.size === 0) return "This file is empty.";
  if (f.size > MAX_BYTES) return `File is larger than the ${MAX_BYTES / 1024 / 1024} MB limit.`;
  const ok = ACCEPTED.includes(f.type) || /\.(jpe?g|png|webp|wav|mp4|pdf)$/i.test(f.name);
  if (!ok) return "Unsupported file type. Use JPEG, PNG, WebP, WAV, MP4 or PDF.";
  return null;
}

export function safeName(n: string) {
  return n.replace(/[^\w.\- ()]/g, "_").slice(0, 120);
}

export async function sha256Hex(data: ArrayBuffer | string): Promise<string> {
  const buf = typeof data === "string" ? new TextEncoder().encode(data) : data;
  const h = await crypto.subtle.digest("SHA-256", buf);
  return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function sniffType(bytes: Uint8Array): string {
  const s = (o: number, n: number) => String.fromCharCode(...bytes.slice(o, o + n));
  if (bytes[0] === 0xff && bytes[1] === 0xd8) return "jpeg";
  if (s(1, 3) === "PNG") return "png";
  if (s(0, 4) === "RIFF" && s(8, 4) === "WEBP") return "webp";
  if (s(0, 4) === "RIFF" && s(8, 4) === "WAVE") return "wav";
  if (s(4, 4) === "ftyp") return "mp4";
  if (s(0, 4) === "%PDF") return "pdf";
  return "unknown";
}

/** Minimal JPEG/EXIF scan: lists segments and reads a few ASCII tags. */
export function inspectImageMetadata(bytes: Uint8Array, kind: string): CheckResult {
  const base = { id: "metadata", name: "Metadata inspection" };
  if (kind !== "jpeg") {
    return { ...base, state: "inconclusive", summary: `Container is ${kind.toUpperCase()}; EXIF parsing is implemented for JPEG only.`, details: { container: kind } };
  }
  const details: { software?: string; datetime?: string; segments?: number; exif?: string } = {};
  let i = 2, segments = 0, hasExif = false;
  while (i < bytes.length - 4 && bytes[i] === 0xff) {
    const marker = bytes[i + 1];
    const len = (bytes[i + 2]! << 8) | bytes[i + 3]!;
    segments++;
    if (marker === 0xe1 && String.fromCharCode(...bytes.slice(i + 4, i + 8)) === "Exif") {
      hasExif = true;
      const text = new TextDecoder("latin1").decode(bytes.slice(i + 10, i + 2 + len));
      const soft = text.match(/(Adobe Photoshop[^\0]*|GIMP[^\0]*|Snapseed[^\0]*|Lightroom[^\0]*)/);
      if (soft) details.software = soft[1]!.slice(0, 60);
      const date = text.match(/\d{4}:\d{2}:\d{2} \d{2}:\d{2}:\d{2}/);
      if (date) details.datetime = date[0];
    }
    if (marker === 0xda) break;
    i += 2 + len;
  }
  details.segments = segments;
  details.exif = hasExif ? "present" : "absent";
  if (details.software) return { ...base, state: "warning", summary: `Editing software signature found: ${details.software}. This indicates processing, not necessarily manipulation.`, details };
  if (!hasExif) return { ...base, state: "inconclusive", summary: "No EXIF block. Metadata is often stripped by messaging apps; absence proves nothing.", details };
  return { ...base, state: "passed", summary: "EXIF present with no editing-software signature detected.", details };
}

/** JPEG Error Level Analysis: recompress at q=0.9 and amplify differences. */
export async function runELA(file: File, kind: string): Promise<CheckResult> {
  const base = { id: "ela", name: "JPEG Error Level Analysis" };
  if (kind !== "jpeg") return { ...base, state: "skipped", summary: "ELA applies to JPEG files only." };
  const bmp = await createImageBitmap(file);
  const scale = Math.min(1, 1200 / Math.max(bmp.width, bmp.height));
  const w = Math.round(bmp.width * scale), h = Math.round(bmp.height * scale);
  const c = new OffscreenCanvas(w, h);
  const ctx = c.getContext("2d")!;
  ctx.drawImage(bmp, 0, 0, w, h);
  const orig = ctx.getImageData(0, 0, w, h);
  const blob = await c.convertToBlob({ type: "image/jpeg", quality: 0.9 });
  const re = await createImageBitmap(blob);
  ctx.drawImage(re, 0, 0);
  const rec = ctx.getImageData(0, 0, w, h);
  const out = ctx.createImageData(w, h);
  let sum = 0, max = 0;
  for (let p = 0; p < orig.data.length; p += 4) {
    let d = 0;
    for (let k = 0; k < 3; k++) {
      const v = Math.abs(orig.data[p + k]! - rec.data[p + k]!);
      d += v;
      out.data[p + k] = Math.min(255, v * 15);
    }
    out.data[p + 3] = 255;
    sum += d / 3; if (d / 3 > max) max = d / 3;
  }
  ctx.putImageData(out, 0, 0);
  const elaBlob = await c.convertToBlob({ type: "image/png" });
  const artifact = await new Promise<string>((r) => { const fr = new FileReader(); fr.onload = () => r(fr.result as string); fr.readAsDataURL(elaBlob); });
  const mean = sum / (w * h);
  return {
    ...base,
    state: "inconclusive",
    summary: "ELA map generated. Bright, uneven regions may deserve review; ELA alone cannot prove manipulation.",
    details: { meanError: mean.toFixed(2), maxError: max.toFixed(0), resolution: `${w}×${h}` },
    artifact,
  };
}

/** Bounded PCM WAV header observations. */
export function inspectWav(bytes: Uint8Array, kind: string): CheckResult {
  const base = { id: "wav", name: "WAV observations" };
  if (kind !== "wav") return { ...base, state: "skipped", summary: "Applies to WAV audio only." };
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (bytes.length < 44) return { ...base, state: "error", summary: "WAV header truncated." };
  const fmt = dv.getUint16(20, true), ch = dv.getUint16(22, true), rate = dv.getUint32(24, true), bits = dv.getUint16(34, true);
  const declared = dv.getUint32(4, true) + 8;
  const details = { format: fmt === 1 ? "PCM" : `code ${fmt}`, channels: ch, sampleRate: rate, bitsPerSample: bits, declaredSize: declared, actualSize: bytes.length, durationSec: ((bytes.length - 44) / (rate * ch * (bits / 8) || 1)).toFixed(2) };
  if (fmt !== 1) return { ...base, state: "inconclusive", summary: "Non-PCM WAV; only basic header read.", details };
  if (declared !== bytes.length) return { ...base, state: "warning", summary: "Declared RIFF size differs from actual size (possible truncation or appended data).", details };
  return { ...base, state: "passed", summary: "PCM header consistent with file size. This is a structural check, not audio authentication.", details };
}

export function compareHashes(a: string, b: string): CheckResult {
  const base = { id: "compare", name: "Reference SHA-256 comparison" };
  return a === b
    ? { ...base, state: "passed", summary: "Byte-for-byte identical to the registered reference.", details: { submitted: a, reference: b } }
    : { ...base, state: "failed", summary: "Bytes differ from the registered reference. This does not by itself prove malicious manipulation.", details: { submitted: a, reference: b } };
}
