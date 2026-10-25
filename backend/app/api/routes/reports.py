from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.evidence_service import evidence_service
from app.services.audit_service import audit_service
from app.models.audit import AuditEvent
from app.reports.pdf_generator import pdf_generator
from app.schemas.evidence import ReportResponse

router = APIRouter(prefix="/evidence", tags=["Reports"])

def build_report_data(db: Session, ev) -> dict:
    all_audit = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()
    ev_audit = [
        {"id": a.id, "ts": a.ts, "action": a.action, "detail": a.detail, "hash": a.hash}
        for a in all_audit
        if ev.id in a.detail or ev.name in a.detail
    ]

    ref_data = None
    if ev.reference_id:
        ref_ev = evidence_service.get_by_id(db, ev.reference_id)
        if ref_ev:
            ref_data = {
                "id": ref_ev.id,
                "filename": ref_ev.name,
                "sha256": ref_ev.sha256,
            }

    checks_data = [
        {
            "id": c.check_id,
            "name": c.name,
            "state": c.state,
            "summary": c.summary,
            "details": c.details or {},
            "artifact": c.artifact,
        }
        for c in ev.checks
    ]

    findings_data = [
        {
            "id": f.id,
            "detector": f.detector,
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "location": f.location,
        }
        for f in ev.findings
    ]

    timeline_data = [
        {
            "id": t.id,
            "start_time": t.start_time,
            "end_time": t.end_time,
            "event_type": t.event_type,
            "severity": t.severity,
            "detector": t.detector,
            "description": t.description,
        }
        for t in ev.timeline_events
    ]

    limitations = [
        "Forensic detector outputs are mathematical indicators and decision-support metrics, not legal proof of intent.",
        "A SHA-256 mismatch confirms byte discrepancy, but does not identify author identity or motive.",
        "Audio and video timeline boundaries are estimated based on inter-frame flux and spectral derivatives within algorithmic window tolerances.",
        "All tests run on immutable local storage without modifying source evidence bytes.",
    ]

    return {
        "generator": "EvidenceGuard Forensic Engine (v1.0)",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "investigation": ev.case_name,
        "evidence": {
            "id": ev.id,
            "filename": ev.name,
            "sizeBytes": ev.size,
            "container": ev.kind,
            "sha256": ev.sha256,
            "registeredAt": ev.registered_at,
        },
        "reference": ref_data,
        "assessment": ev.assessment or {
            "classification": "INCONCLUSIVE",
            "integrity_score": 50.0,
            "tampering_likelihood": 0.5,
            "confidence": 0.5,
            "summary": "Pending comprehensive analysis",
        },
        "checks": checks_data,
        "findings": findings_data,
        "timeline": timeline_data,
        "audit": ev_audit,
        "limitations": limitations,
    }

@router.get("/{evidence_id}/report", response_model=ReportResponse)
def get_report_json(evidence_id: str, db: Session = Depends(get_db)):
    ev = evidence_service.get_by_id(db, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    report_data = build_report_data(db, ev)
    audit_service.log(db, "report.exported", f"{ev.id} json")
    return report_data

@router.get("/{evidence_id}/report/pdf")
def get_report_pdf(evidence_id: str, db: Session = Depends(get_db)):
    ev = evidence_service.get_by_id(db, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    report_data = build_report_data(db, ev)
    pdf_bytes = pdf_generator.generate(report_data)

    audit_service.log(db, "report.exported", f"{ev.id} pdf")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{ev.id}-forensic-report.pdf"'
        },
    )
