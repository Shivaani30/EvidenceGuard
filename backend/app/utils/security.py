import re
from pathlib import Path
from fastapi import HTTPException

# MIME signatures (magic bytes)
MAGIC_SIGNATURES = {
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "webp": [b"RIFF"],  # check offset 8 for WEBP
    "wav": [b"RIFF"],   # check offset 8 for WAVE
    "mp4": [b"ftyp", b"\x00\x00\x00\x18ftyp", b"\x00\x00\x00\x20ftyp", b"\x00\x00\x00\x1cftyp"],
    "pdf": [b"%PDF"],
    "mkv": [b"\x1a\x45\xdf\xa3"],
}

def sanitize_filename(filename: str) -> str:
    """Strip dangerous characters and directory traversals."""
    name = Path(filename).name
    # Keep alphanumeric, dot, underscore, dash, space, parentheses
    clean = re.sub(r"[^\w.\- ()]", "_", name)
    return clean[:120] if clean else "unnamed_evidence"

def sniff_mime_and_kind(header_bytes: bytes, filename: str) -> tuple[str, str]:
    """Inspect magic bytes and return (mime_type, kind)."""
    if len(header_bytes) >= 3 and header_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg", "jpeg"
    if len(header_bytes) >= 8 and header_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", "png"
    if len(header_bytes) >= 12 and header_bytes[:4] == b"RIFF" and header_bytes[8:12] == b"WEBP":
        return "image/webp", "webp"
    if len(header_bytes) >= 12 and header_bytes[:4] == b"RIFF" and header_bytes[8:12] == b"WAVE":
        return "audio/wav", "wav"
    if len(header_bytes) >= 8 and b"ftyp" in header_bytes[:16]:
        return "video/mp4", "mp4"
    if len(header_bytes) >= 4 and header_bytes[:4] == b"%PDF":
        return "application/pdf", "pdf"
    if len(header_bytes) >= 4 and header_bytes[:4] == b"\x1a\x45\xdf\xa3":
        return "video/x-matroska", "mkv"
    
    # Fallback to extension matching if bytes are non-standard
    ext = Path(filename).suffix.lower()
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg", "jpeg"
    elif ext == ".png":
        return "image/png", "png"
    elif ext == ".webp":
        return "image/webp", "webp"
    elif ext == ".wav":
        return "audio/wav", "wav"
    elif ext == ".mp3":
        return "audio/mpeg", "mp3"
    elif ext in [".mp4", ".m4v"]:
        return "video/mp4", "mp4"
    elif ext in [".avi"]:
        return "video/x-msvideo", "avi"
    elif ext in [".mov"]:
        return "video/quicktime", "mov"
    elif ext == ".pdf":
        return "application/pdf", "pdf"
        
    return "application/octet-stream", "unknown"

def validate_evidence_file(file_bytes: bytes, filename: str, max_bytes: int):
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds maximum allowed size ({max_bytes // (1024*1024)} MB).")
    
    mime, kind = sniff_mime_and_kind(file_bytes[:32], filename)
    if kind == "unknown":
        raise HTTPException(
            status_code=400,
            detail="Unsupported or unrecognized file format. Supported: JPEG, PNG, WebP, WAV, MP3, MP4, AVI, MOV, PDF."
        )
    return mime, kind
