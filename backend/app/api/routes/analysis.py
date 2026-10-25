from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.evidence import Evidence, AnalysisJob
from app.services.evidence_service import evidence_service
from app.services.job_service import job_service
from app.schemas.evidence import AnalysisStartRequest, JobStatusResponse, CheckResultSchema, TimelineEventSchema
from app.forensics.fusion.consensus_graph import ConsensusGraphBuilder

router = APIRouter(prefix="/evidence", tags=["Analysis"])

@router.post("/{evidence_id}/analyze", response_model=JobStatusResponse)
def start_analysis(
    evidence_id: str,
    req: AnalysisStartRequest,
    db: Session = Depends(get_db),
):
    ev = evidence_service.get_by_id(db, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    # Determine reference hash if comparing
    ref_hash = None
    if ev.reference_id:
        ref_ev = evidence_service.get_by_id(db, ev.reference_id)
        if ref_ev:
            ref_hash = ref_ev.sha256

    # Determine default checks if none specified
    checks = req.checks
    if not checks:
        if ev.kind in ["jpeg", "png", "webp"]:
            checks = ["metadata", "ela", "compression", "splicing", "synthetic_image"]
        elif ev.kind in ["mp4", "avi", "mov", "mkv"]:
            checks = ["video_duplicate", "video_continuity", "cctv_timestamp", "deepfake_video"]
        elif ev.kind in ["wav", "mp3"]:
            checks = ["wav", "audio_spectral", "audio_splice", "synthetic_speech"]
        else:
            checks = ["metadata"]
        if ref_hash:
            checks.insert(0, "compare")

    # Launch background job
    job_service.start_job(
        evidence_id=evidence_id,
        selected_checks=checks,
        reference_hash=ref_hash,
    )

    return JobStatusResponse(
        id=f"job_{evidence_id}",
        evidence_id=evidence_id,
        status="running",
        progress=5,
        stage="Queued",
        message="Analysis job initiated",
        checks=[],
    )

@router.get("/{evidence_id}/status", response_model=JobStatusResponse)
def get_job_status(evidence_id: str, db: Session = Depends(get_db)):
    ev = evidence_service.get_by_id(db, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    job = db.query(AnalysisJob).filter(AnalysisJob.evidence_id == evidence_id).first()
    
    checks_dto = [
        CheckResultSchema(
            id=c.check_id,
            name=c.name,
            state=c.state,
            summary=c.summary,
            details=c.details,
            artifact=c.artifact,
            score=c.score,
            confidence=c.confidence,
        )
        for c in ev.checks
    ]

    return JobStatusResponse(
        id=job.id if job else f"job_{evidence_id}",
        evidence_id=evidence_id,
        status=job.status if job else ev.job_status,
        progress=job.progress if job else (100 if ev.job_status == "done" else 0),
        stage=job.stage if job else ("Completed" if ev.job_status == "done" else "Idle"),
        message=job.message if job else "Status retrieved",
        checks=checks_dto,
    )

@router.get("/{evidence_id}/timeline", response_model=list[TimelineEventSchema])
def get_timeline(evidence_id: str, db: Session = Depends(get_db)):
    ev = evidence_service.get_by_id(db, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return [
        TimelineEventSchema(
            id=t.id,
            start_time=t.start_time,
            end_time=t.end_time,
            event_type=t.event_type,
            severity=t.severity,
            detector=t.detector,
            confidence=t.confidence,
            description=t.description,
        )
        for t in ev.timeline_events
    ]

@router.get("/{evidence_id}/consensus")
def get_consensus_graph(evidence_id: str, db: Session = Depends(get_db)):
    ev = evidence_service.get_by_id(db, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    det_list = [
        {"id": c.check_id, "name": c.name, "state": c.state}
        for c in ev.checks
    ]
    findings_list = [
        {"detector": f.detector, "title": f.title, "severity": f.severity, "description": f.description}
        for f in ev.findings
    ]
    timeline_list = [
        {"start_time": t.start_time, "end_time": t.end_time, "event_type": t.event_type, "severity": t.severity, "detector": t.detector}
        for t in ev.timeline_events
    ]

    graph = ConsensusGraphBuilder.build(
        evidence_id=ev.id,
        evidence_name=ev.name,
        detector_results=det_list,
        findings=findings_list,
        timeline=timeline_list,
    )
    return graph
