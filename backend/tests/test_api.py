import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app

client = TestClient(app)

@pytest.fixture
def test_image_bytes():
    img = Image.new("RGB", (100, 100), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()

def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_upload_and_lifecycle(test_image_bytes):
    # 1. Upload
    res = client.post(
        "/api/evidence/upload",
        files={"file": ("test_pic.jpg", test_image_bytes, "image/jpeg")},
        data={"caseName": "Test Case 2026", "isReference": "false"},
    )
    assert res.status_code == 200
    data = res.json()
    ev_id = data["id"]
    assert ev_id.startswith("EV-")
    assert data["kind"] == "jpeg"
    assert len(data["sha256"]) == 64

    # 2. Get Evidence
    res_get = client.get(f"/api/evidence/{ev_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == ev_id

    # 3. Start Analysis
    res_an = client.post(
        f"/api/evidence/{ev_id}/analyze",
        json={"checks": ["metadata", "ela", "compression", "splicing", "synthetic_image"]},
    )
    assert res_an.status_code == 200
    assert res_an.json()["status"] == "running"

    # Wait for synchronous pipeline in test
    import time
    time.sleep(1.5)

    # 4. Get Status
    res_st = client.get(f"/api/evidence/{ev_id}/status")
    assert res_st.status_code == 200
    st_data = res_st.json()
    assert len(st_data["checks"]) > 0

    # 5. Get JSON Report
    res_rep = client.get(f"/api/evidence/{ev_id}/report")
    assert res_rep.status_code == 200
    rep_data = res_rep.json()
    assert "evidence" in rep_data
    assert "assessment" in rep_data
    assert "checks" in rep_data

    # 6. Get PDF Report
    res_pdf = client.get(f"/api/evidence/{ev_id}/report/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000  # valid PDF binary

    # 7. Audit Trail & Verification
    res_audit = client.get("/api/audit")
    assert res_audit.status_code == 200
    assert len(res_audit.json()) > 0

    res_verify = client.post("/api/audit/verify")
    assert res_verify.status_code == 200
    assert res_verify.json()["intact"] is True

    # 8. Dashboard Stats
    res_dash = client.get("/api/dashboard/stats")
    assert res_dash.status_code == 200
    assert res_dash.json()["total_evidence"] >= 1

if __name__ == "__main__":
    pytest.main([__file__])
