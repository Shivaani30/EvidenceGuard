import os
from pathlib import Path
from app.config import settings

class FileStorage:
    @staticmethod
    def save_evidence(evidence_id: str, filename: str, content: bytes) -> Path:
        """Save original uploaded evidence to immutable evidence directory."""
        safe_name = f"{evidence_id}_{filename}"
        target_path = settings.EVIDENCE_DIR / safe_name
        with open(target_path, "wb") as f:
            f.write(content)
        return target_path

    @staticmethod
    def save_artifact(evidence_id: str, artifact_name: str, content: bytes) -> tuple[Path, str]:
        """Save a generated forensic artifact (ELA, heatmap, spectrogram) and return (path, url)."""
        safe_name = f"{evidence_id}_{artifact_name}"
        target_path = settings.ARTIFACTS_DIR / safe_name
        with open(target_path, "wb") as f:
            f.write(content)
        url = f"/artifacts/{safe_name}"
        return target_path, url

    @staticmethod
    def get_artifact_url(artifact_name: str) -> str:
        return f"/artifacts/{artifact_name}"

    @staticmethod
    def delete_evidence_files(evidence_id: str):
        """Remove evidence file and all associated artifacts upon explicit deletion."""
        for p in settings.EVIDENCE_DIR.glob(f"{evidence_id}_*"):
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
        for p in settings.ARTIFACTS_DIR.glob(f"{evidence_id}_*"):
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
        for p in settings.REPORTS_DIR.glob(f"{evidence_id}_*"):
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass

storage = FileStorage()
