import io
import time
from pathlib import Path
from PIL import Image
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from app.config import settings
from app.models.evidence import Evidence, DetectorResult, ForensicFinding, TimelineEvent
from app.utils.security import sanitize_filename, validate_evidence_file
from app.storage.file_storage import storage
from app.services.hash_service import hash_service
from app.services.audit_service import audit_service
from app.schemas.evidence import EvidenceResponse, CheckResultSchema, ForensicFindingSchema, TimelineEventSchema

class EvidenceService:
    @staticmethod
    def upload_and_register(
        db: Session,
        file_bytes: bytes,
        filename: str,
        case_name: str = "Untitled investigation",
        is_reference: bool = False,
        reference_id: str | None = None,
    ) -> Evidence:
        # 1. Validation
        mime, kind = validate_evidence_file(file_bytes, filename, settings.MAX_FILE_SIZE_BYTES)
        safe_name = sanitize_filename(filename)

        # 2. Cryptographic Hashing
        sha256 = hash_service.compute_sha256(file_bytes)
        sha512 = hash_service.compute_sha512(file_bytes)

        # 3. Generate unique evidence ID (EVD-YYYY-XXXXX or EV-XXXXX)
        timestamp_part = hex(int(time.time()))[2:].upper()
        evidence_id = f"EV-{timestamp_part}"

        # 4. Save raw file immutably
        file_path = storage.save_evidence(evidence_id, safe_name, file_bytes)

        # 5. Generate preview thumbnail for image formats
        preview_data = None
        if kind in ["jpeg", "png", "webp"]:
            try:
                with Image.open(io.BytesIO(file_bytes)) as img:
                    img_rgb = img.convert("RGB")
                    img_rgb.thumbnail((600, 600))
                    buf = io.BytesIO()
                    img_rgb.save(buf, format="JPEG", quality=80)
                    _, preview_url = storage.save_artifact(evidence_id, "thumb.jpg", buf.getvalue())
                    preview_data = preview_url
            except Exception:
                preview_data = None

        # 6. Create Database Record
        ev = Evidence(
            id=evidence_id,
            name=safe_name,
            size=len(file_bytes),
            kind=kind,
            sha256=sha256,
            sha512=sha512,
            mime=mime,
            file_path=str(file_path),
            preview_path=preview_data,
            is_reference=is_reference,
            case_name=case_name.strip() or "Untitled investigation",
            reference_id=reference_id,
            job_status="idle",
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)

        # 7. Log to Audit Chain
        action = "reference.registered" if is_reference else "evidence.registered"
        detail = f"{evidence_id} {safe_name} sha256={sha256}"
        audit_service.log(db, action, detail)

        return ev

    @staticmethod
    def get_by_id(db: Session, evidence_id: str) -> Evidence | None:
        return db.query(Evidence).filter(Evidence.id == evidence_id).first()

    @staticmethod
    def list_all(db: Session, query: str = "") -> list[Evidence]:
        q = db.query(Evidence)
        if query:
            term = f"%{query}%"
            q = q.filter(
                (Evidence.id.ilike(term))
                | (Evidence.name.ilike(term))
                | (Evidence.sha256.ilike(term))
                | (Evidence.case_name.ilike(term))
            )
        return q.order_by(Evidence.registered_at.desc()).all()

    @staticmethod
    def delete(db: Session, evidence_id: str) -> bool:
        ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not ev:
            return False
            
        ev_name = ev.name
        # Delete files
        storage.delete_evidence_files(evidence_id)
        # Delete DB entity
        db.delete(ev)
        db.commit()

        # Audit log removal
        audit_service.log(db, "evidence.removed", f"{evidence_id} {ev_name}")
        return True

    @staticmethod
    def to_response_dto(ev: Evidence) -> EvidenceResponse:
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

        findings_dto = [
            ForensicFindingSchema(
                id=f.id,
                detector=f.detector,
                severity=f.severity,
                title=f.title,
                description=f.description,
                location=f.location,
                confidence=f.confidence,
            )
            for f in ev.findings
        ]

        timeline_dto = [
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

        return EvidenceResponse(
            id=ev.id,
            name=ev.name,
            size=ev.size,
            kind=ev.kind,
            sha256=ev.sha256,
            sha512=ev.sha512,
            mime=ev.mime,
            registeredAt=ev.registered_at,
            isReference=ev.is_reference,
            caseName=ev.case_name,
            referenceId=ev.reference_id,
            checks=checks_dto,
            jobStatus=ev.job_status,
            preview=ev.preview_path,
            assessment=ev.assessment,
            findings=findings_dto,
            timeline=timeline_dto,
        )

evidence_service = EvidenceService()
