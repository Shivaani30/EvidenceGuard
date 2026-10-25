from pathlib import Path
import cv2
import numpy as np
from app.forensics.base import BaseDetector, DetectorOutput

class CompressionAnalysisDetector(BaseDetector):
    check_id = "compression"
    name = "JPEG Compression & Block Artifact Analysis"

    def run(self, file_path: Path, evidence_id: str, **kwargs) -> DetectorOutput:
        try:
            img = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                return DetectorOutput(
                    check_id=self.check_id,
                    name=self.name,
                    state="error",
                    summary="Unable to decode image for compression analysis.",
                )

            h, w = img.shape
            if h < 64 or w < 64:
                return DetectorOutput(
                    check_id=self.check_id,
                    name=self.name,
                    state="skipped",
                    summary="Image dimensions too small for 8x8 block analysis.",
                )

            # Crop to multiples of 8
            h_crop = (h // 8) * 8
            w_crop = (w // 8) * 8
            cropped = img[:h_crop, :w_crop].astype(np.float32)

            # 1. 8x8 Block Boundary Inconsistency (BAG - Blocking Artifact Grid)
            # Compare horizontal and vertical differences across 8x8 block boundaries vs inside blocks
            diff_h = np.abs(cropped[:, 1:] - cropped[:, :-1])
            diff_v = np.abs(cropped[1:, :] - cropped[:-1, :])

            # Horizontal boundary differences occur at columns 7, 15, 23, ...
            cols = np.arange(diff_h.shape[1])
            boundary_cols = (cols % 8 == 7)
            non_boundary_cols = ~boundary_cols

            mean_boundary_h = np.mean(diff_h[:, boundary_cols]) if np.any(boundary_cols) else 0
            mean_inner_h = np.mean(diff_h[:, non_boundary_cols]) if np.any(non_boundary_cols) else 1e-6
            block_ratio_h = float(mean_boundary_h / (mean_inner_h + 1e-6))

            # Vertical boundary differences occur at rows 7, 15, 23, ...
            rows = np.arange(diff_v.shape[0])
            boundary_rows = (rows % 8 == 7)
            non_boundary_rows = ~boundary_rows

            mean_boundary_v = np.mean(diff_v[boundary_rows, :]) if np.any(boundary_rows) else 0
            mean_inner_v = np.mean(diff_v[non_boundary_rows, :]) if np.any(non_boundary_rows) else 1e-6
            block_ratio_v = float(mean_boundary_v / (mean_inner_v + 1e-6))

            avg_blocking_ratio = float((block_ratio_h + block_ratio_v) / 2.0)

            # 2. Localized Block Artifact Divergence across 32x32 tiles
            tile_ratios = []
            for y in range(0, h_crop - 32, 32):
                for x in range(0, w_crop - 32, 32):
                    tile_diff = diff_h[y:y+32, x:x+31]
                    tile_cols = (np.arange(tile_diff.shape[1]) % 8 == 7)
                    if np.any(tile_cols) and np.any(~tile_cols):
                        b_mean = np.mean(tile_diff[:, tile_cols])
                        i_mean = np.mean(tile_diff[:, ~tile_cols])
                        tile_ratios.append(b_mean / (i_mean + 1e-6))

            tile_std = float(np.std(tile_ratios)) if tile_ratios else 0.0

            findings = []
            state = "passed"
            summary = "JPEG 8x8 block structure is consistent across the image."

            # If blocking ratio is distinct from 1.0, JPEG compression grid is present
            has_grid = avg_blocking_ratio > 1.08
            
            # If standard deviation of block strength across tiles is high, compression is inconsistent
            if tile_std > 0.45:
                state = "warning"
                summary = "Localized compression inconsistency detected across 8x8 block grid."
                findings.append({
                    "detector": self.check_id,
                    "severity": "medium",
                    "title": "Uneven Block Compression Artifacts",
                    "description": f"Standard deviation of block artifact strength across tiles is high ({tile_std:.2f}). Suggests localized editing or composite insertion.",
                    "location": {"blocking_variance": round(tile_std, 3)},
                    "confidence": 0.82,
                })
            elif not has_grid:
                state = "inconclusive"
                summary = "No prominent 8x8 JPEG grid detected (characteristic of uncompressed formats, high-quality images, or re-sampling)."

            details = {
                "blocking_artifact_ratio": round(avg_blocking_ratio, 3),
                "horizontal_boundary_ratio": round(block_ratio_h, 3),
                "vertical_boundary_ratio": round(block_ratio_v, 3),
                "grid_variance_across_tiles": round(tile_std, 3),
                "grid_detected": has_grid,
            }

            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state=state,
                summary=summary,
                details=details,
                findings=findings,
                score=round(tile_std, 3),
            )

        except Exception as e:
            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state="error",
                summary=f"Compression analysis encountered error: {str(e)}",
            )
