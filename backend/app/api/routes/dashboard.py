from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.evidence import Evidence
from app.models.audit import AuditEvent
from app.services.audit_service import audit_service
from app.schemas.dashboard import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    all_ev = db.query(Evidence).all()
    total_evidence = len(all_ev)
    
    images = [e for e in all_ev if e.kind in ["jpeg", "png", "webp", "tiff", "bmp"]]
    videos = [e for e in all_ev if e.kind in ["mp4", "avi", "mov", "mkv", "webm"]]
    audios = [e for e in all_ev if e.kind in ["wav", "mp3", "m4a", "flac", "aac", "ogg"]]

    completed = [e for e in all_ev if e.job_status == "done"]
    pending = [e for e in all_ev if e.job_status in ["running", "idle"]]

    high_suspicion = 0
    for e in all_ev:
        if e.assessment and isinstance(e.assessment, dict):
            if e.assessment.get("classification") in ["HIGH SUSPICION", "MODERATE SUSPICION"]:
                high_suspicion += 1

    audit_count = db.query(AuditEvent).count()
    intact, _, _, _ = audit_service.verify_chain(db)

    return DashboardStats(
        total_evidence=total_evidence,
        images_analyzed=len(images),
        videos_analyzed=len(videos),
        audio_analyzed=len(audios),
        high_suspicion_cases=high_suspicion,
        pending_analyses=len(pending),
        completed_analyses=len(completed),
        audit_events_count=audit_count,
        chain_intact=intact,
    )
