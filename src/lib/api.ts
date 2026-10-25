import type { CheckResult, CheckState } from "./forensics";
import type { Evidence, AuditEvent } from "./store";

const API_BASE = "/api";

export interface DashboardStats {
  total_evidence: number;
  images_analyzed: number;
  videos_analyzed: number;
  audio_analyzed: number;
  high_suspicion_cases: number;
  pending_analyses: number;
  completed_analyses: number;
  audit_events_count: number;
  chain_intact: boolean;
}

export interface JobProgressUpdate {
  evidence_id: string;
  progress: number;
  stage: string;
  message: string;
  status?: string;
}

export const api = {
  async uploadEvidence(
    file: File,
    caseName: string,
    isReference: boolean = false,
    referenceId?: string
  ): Promise<Evidence> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("caseName", caseName || "Untitled investigation");
    formData.append("isReference", String(isReference));
    if (referenceId) {
      formData.append("referenceId", referenceId);
    }

    const res = await fetch(`${API_BASE}/evidence/upload`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Evidence upload failed");
    }

    const data = await res.json();
    return {
      id: data.id,
      name: data.name,
      size: data.size,
      kind: data.kind,
      sha256: data.sha256,
      registeredAt: new Date().toISOString(),
      isReference: data.isReference,
      caseName: data.caseName,
      referenceId: data.referenceId || undefined,
      checks: [],
      jobStatus: "idle",
      preview: data.preview || undefined,
    };
  },

  async listEvidence(query: string = ""): Promise<Evidence[]> {
    const res = await fetch(`${API_BASE}/evidence?q=${encodeURIComponent(query)}`);
    if (!res.ok) return [];
    return await res.json();
  },

  async getEvidence(evidenceId: string): Promise<Evidence | null> {
    const res = await fetch(`${API_BASE}/evidence/${encodeURIComponent(evidenceId)}`);
    if (!res.ok) return null;
    return await res.json();
  },

  async deleteEvidence(evidenceId: string): Promise<boolean> {
    const res = await fetch(`${API_BASE}/evidence/${encodeURIComponent(evidenceId)}`, {
      method: "DELETE",
    });
    return res.ok;
  },

  async startAnalysis(evidenceId: string, checks: string[]): Promise<void> {
    const res = await fetch(`${API_BASE}/evidence/${encodeURIComponent(evidenceId)}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ checks }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Analysis request failed" }));
      throw new Error(err.detail || "Analysis request failed");
    }
  },

  async getJobStatus(evidenceId: string): Promise<{
    id: string;
    status: "idle" | "running" | "completed" | "failed";
    progress: number;
    stage: string;
    message: string;
    checks: CheckResult[];
  }> {
    const res = await fetch(`${API_BASE}/evidence/${encodeURIComponent(evidenceId)}/status`);
    if (!res.ok) throw new Error("Failed to fetch job status");
    const data = await res.json();
    return {
      ...data,
      status: data.status === "completed" ? "completed" : data.status,
    };
  },

  async getReport(evidenceId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/evidence/${encodeURIComponent(evidenceId)}/report`);
    if (!res.ok) throw new Error("Failed to fetch report");
    return await res.json();
  },

  getReportPdfUrl(evidenceId: string): string {
    return `${API_BASE}/evidence/${encodeURIComponent(evidenceId)}/report/pdf`;
  },

  async getAuditTrail(): Promise<AuditEvent[]> {
    const res = await fetch(`${API_BASE}/audit`);
    if (!res.ok) return [];
    return await res.json();
  },

  async verifyAuditTrail(): Promise<{ intact: boolean; event_count: number; broken_at: number | null; message: string }> {
    const res = await fetch(`${API_BASE}/audit/verify`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to verify audit chain");
    return await res.json();
  },

  async getDashboardStats(): Promise<DashboardStats> {
    const res = await fetch(`${API_BASE}/dashboard/stats`);
    if (!res.ok) {
      return {
        total_evidence: 0,
        images_analyzed: 0,
        videos_analyzed: 0,
        audio_analyzed: 0,
        high_suspicion_cases: 0,
        pending_analyses: 0,
        completed_analyses: 0,
        audit_events_count: 0,
        chain_intact: true,
      };
    }
    return await res.json();
  },

  subscribeProgress(
    evidenceId: string,
    onProgress: (data: JobProgressUpdate) => void
  ): () => void {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/ws/evidence/${encodeURIComponent(evidenceId)}/progress`;

    let ws: WebSocket | null = null;
    let pollInterval: any = null;

    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onProgress(data);
        } catch {
          // ignore ping/pong
        }
      };

      ws.onerror = () => {
        // Fallback to polling if WebSocket fails
        startPolling();
      };
    } catch {
      startPolling();
    }

    function startPolling() {
      if (pollInterval) return;
      pollInterval = setInterval(async () => {
        try {
          const st = await api.getJobStatus(evidenceId);
          onProgress({
            evidence_id: evidenceId,
            progress: st.progress,
            stage: st.stage,
            message: st.message,
            status: st.status,
          });
          if (st.status === "completed" || st.status === "failed") {
            clearInterval(pollInterval);
          }
        } catch {
          // poll retry
        }
      }, 800);
    }

    return () => {
      if (ws) {
        ws.close();
      }
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  },
};
