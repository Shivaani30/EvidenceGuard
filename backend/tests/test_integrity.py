import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from app.services.hash_service import hash_service
from app.services.audit_service import audit_service
from app.database import SessionLocal, Base, engine
from app.models.audit import AuditEvent

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_hash_calculation():
    test_bytes = b"Digital Forensic Evidence Test Stream 2026"
    h256 = hash_service.compute_sha256(test_bytes)
    assert len(h256) == 64
    h512 = hash_service.compute_sha512(test_bytes)
    assert len(h512) == 128

def test_audit_chain_and_tampering_detection(db):
    # Log events
    e1 = audit_service.log(db, "test.event.1", "Sample event detail 1")
    e2 = audit_service.log(db, "test.event.2", "Sample event detail 2")
    
    assert e2.prev_hash == e1.hash
    
    # Verify chain
    intact, count, broken_at, msg = audit_service.verify_chain(db)
    assert intact is True
    assert broken_at is None

    # Simulate malicious modification
    original_detail = e1.detail
    e1.detail = "MALICIOUSLY TAMPERED DETAIL"
    db.commit()

    intact, count, broken_at, msg = audit_service.verify_chain(db)
    assert intact is False
    assert broken_at == e1.id

    # Restore
    e1.detail = original_detail
    db.commit()
    intact, _, _, _ = audit_service.verify_chain(db)
    assert intact is True

if __name__ == "__main__":
    pytest.main([__file__])
