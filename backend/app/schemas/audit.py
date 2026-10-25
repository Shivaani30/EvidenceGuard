from pydantic import BaseModel

class AuditEventSchema(BaseModel):
    id: int
    ts: str
    action: str
    detail: str
    prevHash: str
    hash: str

class AuditVerifyResponse(BaseModel):
    intact: bool
    event_count: int
    broken_at: int | None = None
    message: str
