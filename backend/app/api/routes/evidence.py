from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.evidence_service import evidence_service
from app.schemas.evidence import EvidenceResponse, EvidenceUploadResponse

router = APIRouter(prefix="/evidence", tags=["Evidence"])

@router.post("/upload", response_model=EvidenceUploadResponse)
async def upload_evidence(
    file: UploadFile = File(...),
    caseName: str = Form("Untitled investigation"),
    isReference: bool = Form(False),
    referenceId: str | None = Form(None),
    db: Session = Depends(get_db),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    ev = evidence_service.upload_and_register(
        db=db,
        file_bytes=content,
        filename=file.filename or "uploaded_file",
        case_name=caseName,
        is_reference=isReference,
        reference_id=referenceId if referenceId else None,
    )

    return EvidenceUploadResponse(
        id=ev.id,
        name=ev.name,
        size=ev.size,
        kind=ev.kind,
        sha256=ev.sha256,
        sha512=ev.sha512 or "",
        mime=ev.mime or "",
        preview=ev.preview_path,
        caseName=ev.case_name,
        isReference=ev.is_reference,
        referenceId=ev.reference_id,
    )

@router.get("", response_model=list[EvidenceResponse])
def list_evidence(q: str = "", db: Session = Depends(get_db)):
    items = evidence_service.list_all(db, query=q)
    return [evidence_service.to_response_dto(ev) for ev in items]

@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(evidence_id: str, db: Session = Depends(get_db)):
    ev = evidence_service.get_by_id(db, evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return evidence_service.to_response_dto(ev)

@router.delete("/{evidence_id}")
def delete_evidence(evidence_id: str, db: Session = Depends(get_db)):
    success = evidence_service.delete(db, evidence_id)
    if not success:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return {"status": "success", "message": f"Evidence {evidence_id} removed."}
