import { useSyncExternalStore } from "react";
import { sha256Hex, type CheckResult } from "./forensics";
import { api } from "./api";

export interface Evidence {
  id: string;
  name: string;
  size: number;
  kind: string;
  sha256: string;
  registeredAt: string;
  isReference: boolean;
  caseName: string;
  referenceId?: string | undefined;
  checks: CheckResult[];
  jobStatus: "idle" | "running" | "done";
  preview?: string | undefined;
  assessment?: any;
}
export interface AuditEvent { id: number; ts: string; action: string; detail: string; prevHash: string; hash: string; }
interface State { evidence: Evidence[]; audit: AuditEvent[]; }

const KEY = "evidenceguard.v1";
let state: State = { evidence: [], audit: [] };
let loaded = false;
let backendSynced = false;
const listeners = new Set<() => void>();
const empty: State = { evidence: [], audit: [] };

function load() {
  if (loaded || typeof window === "undefined") return;
  loaded = true;
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) state = JSON.parse(raw);
  } catch { /* keep empty */ }
  
  state.evidence = state.evidence.map((e) => e.jobStatus === "running"
    ? { ...e, jobStatus: "done", checks: e.checks.map((c) => c.state === "running" || c.state === "pending" ? { ...c, state: "error", summary: "Interrupted by page reload. Re-run the analysis." } : c) }
    : e);

  if (!backendSynced) {
    backendSynced = true;
    syncFromBackend();
  }
}

export async function syncFromBackend() {
  try {
    const [evList, auditList] = await Promise.all([
      api.listEvidence(),
      api.getAuditTrail(),
    ]);
    if (evList && evList.length >= 0) {
      state = {
        ...state,
        evidence: evList,
        audit: auditList && auditList.length > 0 ? auditList : state.audit,
      };
      save();
    }
  } catch {
    // Backend offline / initializing fallback
  }
}

function save() {
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch {
    state = { ...state, evidence: state.evidence.map((e) => ({ ...e, preview: undefined, checks: e.checks.map((c) => ({ ...c, artifact: undefined })) })) };
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* ignore */ }
  }
  listeners.forEach((l) => l());
}

export function useStore(): State {
  return useSyncExternalStore(
    (l) => { load(); listeners.add(l); l(); return () => listeners.delete(l); },
    () => { load(); return state; },
    () => empty,
  );
}

let chain = Promise.resolve();
export function audit(action: string, detail: string) {
  chain = chain.then(async () => {
    load();
    const prev = state.audit[state.audit.length - 1];
    const prevHash = prev?.hash ?? "0".repeat(64);
    const ts = new Date().toISOString();
    const id = (prev?.id ?? 0) + 1;
    const hash = await sha256Hex(`${id}|${ts}|${action}|${detail}|${prevHash}`);
    state = { ...state, audit: [...state.audit, { id, ts, action, detail, prevHash, hash }] };
    save();
  });
  return chain;
}

export async function verifyChain(events: AuditEvent[]): Promise<number | null> {
  // First try backend API verification
  try {
    const res = await api.verifyAuditTrail();
    if (res.intact) return null;
    return res.broken_at ?? 1;
  } catch {
    // Local fallback
    let prev = "0".repeat(64);
    for (const e of events) {
      const h = await sha256Hex(`${e.id}|${e.ts}|${e.action}|${e.detail}|${prev}`);
      if (e.prevHash !== prev || h !== e.hash) return e.id;
      prev = e.hash;
    }
    return null;
  }
}

export function addEvidence(e: Evidence) {
  load();
  state = { ...state, evidence: [e, ...state.evidence.filter((x) => x.id !== e.id)] };
  save();
}

export function updateEvidence(id: string, patch: Partial<Evidence> | ((e: Evidence) => Partial<Evidence>)) {
  state = {
    ...state,
    evidence: state.evidence.map((e) => e.id === id ? { ...e, ...(typeof patch === "function" ? patch(e) : patch) } : e)
  };
  save();
}

export function removeEvidence(id: string) {
  state = { ...state, evidence: state.evidence.filter((e) => e.id !== id) };
  save();
  api.deleteEvidence(id).catch(() => {});
}

export function buildReport(e: Evidence, all: Evidence[], events: AuditEvent[]) {
  const ref = all.find((r) => r.id === e.referenceId);
  return {
    generator: "EvidenceGuard Multi-Layer Forensic Engine",
    generatedAt: new Date().toISOString(),
    investigation: e.caseName,
    evidence: { id: e.id, filename: e.name, sizeBytes: e.size, container: e.kind, sha256: e.sha256, registeredAt: e.registeredAt },
    reference: ref ? { id: ref.id, filename: ref.name, sha256: ref.sha256 } : null,
    checks: e.checks.map(({ artifact: _a, ...c }) => c),
    audit: events.filter((a) => a.detail.includes(e.id)),
    limitations: [
      "Checks calculate mathematical and signal indicators; results do not establish legal intent.",
      "A SHA-256 mismatch proves bytes differ, but does not identify the author.",
      "All processing uses verified multi-layer detector pipelines preserving source evidence immutability.",
    ],
  };
}
