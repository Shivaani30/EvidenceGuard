import re
from pathlib import Path
from PIL import Image, ExifTags
from app.forensics.base import BaseDetector, DetectorOutput

EDITING_SOFTWARE_PATTERNS = [
    r"Adobe\s*Photoshop",
    r"Lightroom",
    r"GIMP",
    r"Snapseed",
    r"Canva",
    r"Pixlr",
    r"Photoscape",
    r"Affinity\s*Photo",
    r"Corel",
    r"Paint\.NET",
]

class ImageMetadataDetector(BaseDetector):
    check_id = "metadata"
    name = "Metadata inspection"

    def run(self, file_path: Path, evidence_id: str, **kwargs) -> DetectorOutput:
        details: dict[str, str | int] = {}
        findings: list[dict] = []
        state = "passed"
        summary = "EXIF metadata present with no editing signatures detected."

        # Read binary bytes for segment counting and software markers
        try:
            with open(file_path, "rb") as f:
                bytes_data = f.read(512 * 1024)  # first 512KB
        except Exception as e:
            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state="error",
                summary=f"Unable to read file bytes: {e}",
            )

        # Segment scanning for JPEG
        segments = 0
        has_exif_marker = False
        if bytes_data[:2] == b"\xff\xd8":
            i = 2
            while i < len(bytes_data) - 4 and bytes_data[i] == 0xff:
                marker = bytes_data[i + 1]
                if marker == 0xda:  # SOS
                    break
                length = (bytes_data[i + 2] << 8) | bytes_data[i + 3]
                segments += 1
                if marker == 0xe1 and bytes_data[i + 4 : i + 8] == b"Exif":
                    has_exif_marker = True
                i += 2 + length
            details["jpeg_segments"] = segments

        # Read via Pillow
        try:
            with Image.open(file_path) as img:
                details["format"] = img.format or "UNKNOWN"
                details["dimensions"] = f"{img.width}x{img.height}"
                details["mode"] = img.mode

                exif = img.getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = ExifTags.TAGS.get(tag_id, str(tag_id))
                        if tag in ["Make", "Model", "Software", "DateTime", "DateTimeOriginal", "DateTimeDigitized"]:
                            val_str = str(value).strip()
                            if val_str:
                                details[tag] = val_str[:100]

                    # Check for GPS info
                    gps_info = exif.get_ifd(ExifTags.IFD.GPSInfo) if hasattr(ExifTags, "IFD") else None
                    if gps_info:
                        details["gps_coordinates"] = "present"

        except Exception as e:
            details["pillow_error"] = str(e)[:100]

        # Scan text for editing software signatures
        text_content = bytes_data.decode("latin1", errors="ignore")
        detected_software = None
        for pattern in EDITING_SOFTWARE_PATTERNS:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                detected_software = match.group(0)
                break

        if detected_software:
            details["software_signature"] = detected_software
            state = "warning"
            summary = f"Editing software signature found: {detected_software}. Indicates processing, not necessarily malicious manipulation."
            findings.append({
                "detector": self.check_id,
                "severity": "medium",
                "title": "Editing Software Signature Detected",
                "description": f"File contains byte signature for '{detected_software}'.",
                "location": {"container": details.get("format", "image")},
                "confidence": 0.95,
            })
        elif "DateTimeOriginal" in details and "DateTime" in details:
            # Check timestamp anomalies
            try:
                orig_dt = str(details["DateTimeOriginal"])
                mod_dt = str(details["DateTime"])
                if mod_dt < orig_dt:
                    state = "warning"
                    summary = "ModifyDate precedes DateTimeOriginal; indicates potential timestamp tampering."
                    findings.append({
                        "detector": self.check_id,
                        "severity": "high",
                        "title": "Chronological Inversion in Timestamps",
                        "description": f"Modified timestamp ({mod_dt}) is earlier than original creation timestamp ({orig_dt}).",
                        "location": {"fields": ["DateTime", "DateTimeOriginal"]},
                        "confidence": 0.88,
                    })
            except Exception:
                pass
        elif not has_exif_marker and "Make" not in details:
            state = "inconclusive"
            summary = "No standard EXIF block found. Metadata is commonly stripped by messaging and social platforms."

        return DetectorOutput(
            check_id=self.check_id,
            name=self.name,
            state=state,
            summary=summary,
            details=details,
            findings=findings,
        )
