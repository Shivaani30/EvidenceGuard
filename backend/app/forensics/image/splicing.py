import io
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from app.forensics.base import BaseDetector, DetectorOutput
from app.storage.file_storage import storage

class SplicingAndCopyMoveDetector(BaseDetector):
    check_id = "splicing"
    name = "Copy-Move & Noise Splicing Analysis"

    def run(self, file_path: Path, evidence_id: str, **kwargs) -> DetectorOutput:
        try:
            img_bgr = cv2.imread(str(file_path))
            if img_bgr is None:
                return DetectorOutput(
                    check_id=self.check_id,
                    name=self.name,
                    state="error",
                    summary="Unable to decode image for splicing/copy-move analysis.",
                )

            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape

            # Limit dimensions for performance
            max_size = 1200
            scale = 1.0
            if max(h, w) > max_size:
                scale = max_size / max(h, w)
                gray = cv2.resize(gray, (int(w * scale), int(h * scale)))
                img_bgr = cv2.resize(img_bgr, (int(w * scale), int(h * scale)))
                h, w = gray.shape

            findings = []
            state = "passed"
            summary = "No significant copy-move or noise variance anomalies detected."

            # -------------------------------------------------------------
            # 1. Copy-Move Detection via ORB Keypoint Matching
            # -------------------------------------------------------------
            orb = cv2.ORB_create(nfeatures=1500)
            keypoints, descriptors = orb.detectAndCompute(gray, None)

            copy_move_matches_count = 0
            clustered_clones = []
            if descriptors is not None and len(keypoints) > 20:
                # Use BFMatcher with 2 nearest neighbors
                bf = cv2.BFMatcher(cv2.NORM_HAMMING)
                matches = bf.knnMatch(descriptors, descriptors, k=3)

                # Filter self-matches and apply Lowe's ratio test
                valid_pairs = []
                for m in matches:
                    if len(m) >= 2:
                        m1, m2 = m[0], m[1]
                        # Discard self match
                        if m1.queryIdx == m1.trainIdx and len(m) >= 3:
                            m1, m2 = m[1], m[2]
                        if m1.queryIdx != m1.trainIdx:
                            pt1 = np.array(keypoints[m1.queryIdx].pt)
                            pt2 = np.array(keypoints[m1.trainIdx].pt)
                            dist = np.linalg.norm(pt1 - pt2)
                            # Must be sufficiently far apart to not be an adjacent texture
                            if dist > 35 and m1.distance < 0.72 * m2.distance:
                                valid_pairs.append((pt1, pt2, dist))

                copy_move_matches_count = len(valid_pairs)
                if copy_move_matches_count >= 12:
                    # Potential copy-move cloning detected
                    state = "failed"
                    summary = f"Detected {copy_move_matches_count} matching keypoint pairs across separated regions, indicative of copy-move cloning."
                    findings.append({
                        "detector": self.check_id,
                        "severity": "high",
                        "title": "Copy-Move Cloning Detected",
                        "description": f"Found {copy_move_matches_count} matching feature descriptors between spatially distinct image regions.",
                        "location": {"matching_keypoint_pairs": copy_move_matches_count},
                        "confidence": min(0.95, 0.65 + copy_move_matches_count * 0.02),
                    })

            # -------------------------------------------------------------
            # 2. Local Noise Inconsistency Analysis (Wavelet / Median Residual)
            # -------------------------------------------------------------
            # Compute high-pass noise by subtracting median filtered image
            median_blur = cv2.medianBlur(gray, 3)
            noise_residual = np.abs(gray.astype(np.float32) - median_blur.astype(np.float32))

            # Tile into 32x32 patches and calculate local noise variance
            tile_size = 32
            variances = []
            coords = []
            for y in range(0, h - tile_size, tile_size):
                for x in range(0, w - tile_size, tile_size):
                    patch = noise_residual[y : y + tile_size, x : x + tile_size]
                    var = float(np.var(patch))
                    variances.append(var)
                    coords.append((x, y, var))

            noise_discrepancy_ratio = 1.0
            if variances:
                var_arr = np.array(variances)
                median_var = float(np.median(var_arr)) + 1e-5
                std_var = float(np.std(var_arr))
                p95_var = float(np.percentile(var_arr, 95))
                noise_discrepancy_ratio = float(p95_var / median_var)

                # Flag outlier patches
                outlier_patches = [c for c in coords if c[2] > median_var + 3.0 * std_var]
                if len(outlier_patches) >= 3 and state != "failed":
                    state = "warning"
                    summary = "Localized noise variance inconsistency detected. Indicates potential composite/splice insertion."
                    findings.append({
                        "detector": self.check_id,
                        "severity": "medium",
                        "title": "Noise Discrepancy in Localized Patches",
                        "description": f"Several regions exhibit anomalous noise variance ({len(outlier_patches)} patches with >3σ deviation from background noise).",
                        "location": {"anomalous_patches_count": len(outlier_patches)},
                        "confidence": 0.80,
                    })

            details = {
                "orb_keypoints_analyzed": len(keypoints) if keypoints else 0,
                "copy_move_matches": copy_move_matches_count,
                "noise_discrepancy_ratio": round(noise_discrepancy_ratio, 2),
                "resolution_evaluated": f"{w}x{h}",
            }

            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state=state,
                summary=summary,
                details=details,
                findings=findings,
                score=round(copy_move_matches_count / 20.0, 3),
            )

        except Exception as e:
            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state="error",
                summary=f"Splicing analysis failed: {str(e)}",
            )
