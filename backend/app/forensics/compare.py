from pathlib import Path
from app.forensics.base import BaseDetector, DetectorOutput
from app.services.hash_service import hash_service

class ReferenceComparisonDetector(BaseDetector):
    check_id = "compare"
    name = "Reference SHA-256 comparison"

    def run(self, file_path: Path, evidence_id: str, reference_hash: str | None = None, **kwargs) -> DetectorOutput:
        if not reference_hash:
            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state="skipped",
                summary="No reference evidence specified for comparison.",
            )

        current_hash = hash_service.compute_sha256(file_path)
        is_match = (current_hash.lower() == reference_hash.lower())

        findings = []
        if is_match:
            state = "passed"
            summary = "Byte-for-byte identical to the registered reference."
        else:
            state = "failed"
            summary = "Bytes differ from the registered reference. This does not by itself prove malicious manipulation."
            findings.append({
                "detector": self.check_id,
                "severity": "high",
                "title": "Reference Cryptographic Hash Mismatch",
                "description": "Evidence SHA-256 does not match the registered baseline reference hash.",
                "location": {"submitted": current_hash, "reference": reference_hash},
                "confidence": 1.0,
            })

        details = {
            "submitted": current_hash,
            "reference": reference_hash,
            "match": is_match,
        }

        return DetectorOutput(
            check_id=self.check_id,
            name=self.name,
            state=state,
            summary=summary,
            details=details,
            findings=findings,
            score=0.0 if is_match else 1.0,
        )
