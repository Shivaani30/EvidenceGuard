import io
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from app.forensics.base import BaseDetector, DetectorOutput
from app.storage.file_storage import storage

class ErrorLevelAnalysisDetector(BaseDetector):
    check_id = "ela"
    name = "JPEG Error Level Analysis"

    def run(self, file_path: Path, evidence_id: str, quality: int = 90, **kwargs) -> DetectorOutput:
        try:
            with Image.open(file_path) as original:
                img_format = original.format
                if img_format not in ["JPEG", "JPG", "PNG", "WEBP"]:
                    return DetectorOutput(
                        check_id=self.check_id,
                        name=self.name,
                        state="skipped",
                        summary=f"ELA applies primarily to JPEG images (uploaded file is {img_format}).",
                    )

                # Convert to RGB
                orig_rgb = original.convert("RGB")
                
                # Scale if massive to prevent OOM
                max_dim = 1600
                if max(orig_rgb.size) > max_dim:
                    scale = max_dim / max(orig_rgb.size)
                    new_size = (int(orig_rgb.width * scale), int(orig_rgb.height * scale))
                    orig_rgb = orig_rgb.resize(new_size, Image.Resampling.LANCZOS)
                
                # Recompress to in-memory JPEG
                buf = io.BytesIO()
                orig_rgb.save(buf, "JPEG", quality=quality)
                buf.seek(0)
                recompressed = Image.open(buf)

                # Compute difference
                diff = ImageChops.difference(orig_rgb, recompressed)
                
                # Compute statistical measurements on difference
                diff_arr = np.array(diff, dtype=np.float32)
                mean_error = float(np.mean(diff_arr))
                max_error = float(np.max(diff_arr))
                std_error = float(np.std(diff_arr))
                p95_error = float(np.percentile(diff_arr, 95))

                # Amplify difference for visual artifact
                extrema = diff.getextrema()
                max_diff = max([ex[1] for ex in extrema])
                scale_factor = 255.0 / max_diff if max_diff > 0 else 1.0
                scale_factor = min(scale_factor, 15.0)  # capped amplification
                
                enhanced = ImageEnhance.Brightness(diff).enhance(scale_factor)
                
                # Save ELA artifact
                out_buf = io.BytesIO()
                enhanced.save(out_buf, "PNG")
                _, artifact_url = storage.save_artifact(
                    evidence_id, f"ela_q{quality}.png", out_buf.getvalue()
                )

                # Find candidate anomaly clusters (regions with high localized error)
                grayscale_diff = np.mean(diff_arr, axis=2)
                threshold = mean_error + 2.5 * std_error
                hot_pixels = grayscale_diff > threshold
                hot_ratio = float(np.sum(hot_pixels) / hot_pixels.size)

                findings = []
                state = "passed"
                summary = "Error Level Analysis complete. Error distribution is uniform across the surface."

                if hot_ratio > 0.03 and hot_ratio < 0.4:
                    # Non-uniform localized compression anomaly
                    state = "warning"
                    summary = "Non-uniform ELA distribution detected. Highlighted regions exhibit divergent compression history."
                    findings.append({
                        "detector": self.check_id,
                        "severity": "medium",
                        "title": "Localized Compression Discontinuity",
                        "description": f"Elevated residual error in localized regions ({hot_ratio*100:.1f}% of image). Consistent with spliced or re-saved elements.",
                        "location": {"hot_pixel_ratio": round(hot_ratio, 3)},
                        "confidence": 0.78,
                    })
                elif mean_error > 25:
                    state = "inconclusive"
                    summary = "High overall ELA error level across the entire image, consistent with heavy re-compression or high frequency textures."

                details = {
                    "mean_error": round(mean_error, 2),
                    "max_error": round(max_error, 2),
                    "std_error": round(std_error, 2),
                    "p95_error": round(p95_error, 2),
                    "recompression_quality": quality,
                    "resolution": f"{orig_rgb.width}x{orig_rgb.height}",
                    "hot_region_ratio": f"{hot_ratio*100:.1f}%",
                }

                return DetectorOutput(
                    check_id=self.check_id,
                    name=self.name,
                    state=state,
                    summary=summary,
                    details=details,
                    artifact=artifact_url,
                    findings=findings,
                    score=round(hot_ratio, 3),
                )

        except Exception as e:
            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state="error",
                summary=f"ELA processing failed: {str(e)}",
            )
