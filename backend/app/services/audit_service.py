import hashlib
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.audit import AuditEvent

class AuditService:
    @staticmethod
    def log(db: Session, action: str, detail: str) -> AuditEvent:
        """Append an event to the tamper-evident hash-linked audit chain."""
        last_event = db.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        prev_hash = last_event.hash if last_event else "0" * 64
        next_id = (last_event.id + 1) if last_event else 1
        ts = datetime.now(timezone.utc).isoformat()
        
        # Exact cryptographic link: id|ts|action|detail|prevHash
        chain_payload = f"{next_id}|{ts}|{action}|{detail}|{prev_hash}"
        event_hash = hashlib.sha256(chain_payload.encode("utf-8")).hexdigest()
        
        event = AuditEvent(
            id=next_id,
            ts=ts,
            action=action,
            detail=detail,
            prev_hash=prev_hash,
            hash=event_hash,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def verify_chain(db: Session) -> tuple[bool, int, int | None, str]:
        """Verify the integrity of the entire audit chain."""
        events = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()
        if not events:
            return True, 0, None, "Audit chain is empty."
            
        expected_prev = "0" * 64
        for event in events:
            recomputed = hashlib.sha256(
                f"{event.id}|{event.ts}|{event.action}|{event.detail}|{expected_prev}".encode("utf-8")
            ).hexdigest()
            
            if event.prev_hash != expected_prev or event.hash != recomputed:
                return False, len(events), event.id, f"Chain broken at event #{event.id}."
            expected_prev = event.hash
            
        return True, len(events), None, f"Chain intact ({len(events)} events)."

audit_service = AuditService()
