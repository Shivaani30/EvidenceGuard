from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.audit import AuditEvent
from app.services.audit_service import audit_service
from app.schemas.audit import AuditEventSchema, AuditVerifyResponse

router = APIRouter(prefix="/audit", tags=["Audit Trail"])

@router.get("", response_model=list[AuditEventSchema])
def get_audit_trail(db: Session = Depends(get_db)):
    events = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()
    return [
        AuditEventSchema(
            id=e.id,
            ts=e.ts,
            action=e.action,
            detail=e.detail,
            prevHash=e.prev_hash,
            hash=e.hash,
        )
        for e in events
    ]

@router.post("/verify", response_model=AuditVerifyResponse)
def verify_audit_trail(db: Session = Depends(get_db)):
    intact, count, broken_at, message = audit_service.verify_chain(db)
    return AuditVerifyResponse(
        intact=intact,
        event_count=count,
        broken_at=broken_at,
        message=message,
    )
