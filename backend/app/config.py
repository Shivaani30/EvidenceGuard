import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage_data"

class Settings(BaseModel):
    PROJECT_NAME: str = "EvidenceGuard Forensic Backend"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{STORAGE_DIR / 'evidenceguard.db'}")
    
    # Storage directories
    STORAGE_DIR: Path = STORAGE_DIR
    EVIDENCE_DIR: Path = STORAGE_DIR / "evidence"
    ARTIFACTS_DIR: Path = STORAGE_DIR / "artifacts"
    REPORTS_DIR: Path = STORAGE_DIR / "reports"
    
    # Limits & Security
    MAX_FILE_SIZE_BYTES: int = 100 * 1024 * 1024  # 100MB limit
    ALLOWED_IMAGE_EXTS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}
    ALLOWED_AUDIO_EXTS: set[str] = {".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg"}
    ALLOWED_VIDEO_EXTS: set[str] = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    ALLOWED_DOC_EXTS: set[str] = {".pdf"}
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ]

settings = Settings()

# Ensure directories exist
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
settings.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
