from typing import Any, Optional
from pydantic import BaseModel, Field

class CheckResultSchema(BaseModel):
    id: str
    name: str
    state: str  # passed, failed, warning, inconclusive, skipped, unavailable, running, error, pending
    summary: str
    details: Optional[dict[str, Any]] = None
    artifact: Optional[str] = None
    score: Optional[float] = None
    confidence: Optional[float] = None

class ForensicFindingSchema(BaseModel):
    id: str
    detector: str
    severity: str  # low, medium, high, critical
    title: str
    description: str
    location: Optional[dict[str, Any]] = None
    confidence: float = 1.0

class TimelineEventSchema(BaseModel):
    id: str
    start_time: float
    end_time: float
    event_type: str
    severity: str
    detector: str
    confidence: float
    description: str

class AssessmentSchema(BaseModel):
    classification: str
    integrity_score: float
    tampering_likelihood: float
    confidence: float
    summary: str
    supporting_findings: list[str] = []
    contradicting_findings: list[str] = []

class EvidenceResponse(BaseModel):
    id: str
    name: str
    size: int
    kind: str
    sha256: str
    sha512: Optional[str] = None
    mime: Optional[str] = None
    registeredAt: str
    isReference: bool
    caseName: str
    referenceId: Optional[str] = None
    checks: list[CheckResultSchema] = []
    jobStatus: str
    preview: Optional[str] = None
    assessment: Optional[AssessmentSchema] = None
    findings: list[ForensicFindingSchema] = []
    timeline: list[TimelineEventSchema] = []

class EvidenceUploadResponse(BaseModel):
    id: str
    name: str
    size: int
    kind: str
    sha256: str
    sha512: str
    mime: str
    preview: Optional[str] = None
    caseName: str
    isReference: bool
    referenceId: Optional[str] = None

class AnalysisStartRequest(BaseModel):
    checks: list[str] = []

class JobStatusResponse(BaseModel):
    id: str
    evidence_id: str
    status: str
    progress: int
    stage: str
    message: str
    checks: list[CheckResultSchema] = []

class ReportResponse(BaseModel):
    generator: str
    generatedAt: str
    investigation: str
    evidence: dict[str, Any]
    reference: Optional[dict[str, Any]] = None
    assessment: Optional[dict[str, Any]] = None
    checks: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    audit: list[dict[str, Any]]
    limitations: list[str]
