from pathlib import Path
import cv2
import numpy as np
from app.forensics.base import BaseDetector, DetectorOutput

class SyntheticImageDetector(BaseDetector):
    check_id = "synthetic_image"
    name = "Synthetic / AI Image Detection"

    def run(self, file_path: Path, evidence_id: str, **kwargs) -> DetectorOutput:
        try:
            img = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                return DetectorOutput(
                    check_id=self.check_id,
                    name=self.name,
                    state="error",
                    summary="Unable to read image for synthetic analysis.",
                )

            h, w = img.shape
            # Resize to standardized 512x512 for frequency spectrum evaluation
            standard_size = 512
            resized = cv2.resize(img, (standard_size, standard_size)).astype(np.float32)

            # 2D Fast Fourier Transform (FFT)
            f_transform = np.fft.fft2(resized)
            f_shift = np.fft.fftshift(f_transform)
            magnitude_spectrum = 20 * np.log(np.abs(f_shift) + 1e-6)

            # Analyze high-frequency radial distribution vs low-frequency
            cy, cx = standard_size // 2, standard_size // 2
            y, x = np.ogrid[:standard_size, :standard_size]
            r = np.sqrt((x - cx)**2 + (y - cy)**2)

            # High-frequency zone (radius > 160 to 240)
            high_freq_mask = (r >= 160) & (r <= 240)
            mid_freq_mask = (r >= 40) & (r < 160)

            high_freq_vals = magnitude_spectrum[high_freq_mask]
            mid_freq_vals = magnitude_spectrum[mid_freq_mask]

            high_energy = float(np.mean(high_freq_vals))
            mid_energy = float(np.mean(mid_freq_vals))
            hf_ratio = float(high_energy / (mid_energy + 1e-6))

            # Detect isolated high-frequency spectral spikes (characteristic of GAN/Diffusion upsamplers)
            hf_std = float(np.std(high_freq_vals))
            hf_max = float(np.max(high_freq_vals))
            spike_prominence = float((hf_max - high_energy) / (hf_std + 1e-6))

            findings = []
            synthetic_score = float(np.clip((hf_ratio - 0.72) * 2.5 + (spike_prominence - 3.8) * 0.15, 0.05, 0.95))
            
            state = "passed"
            summary = "Frequency domain spectrum conforms to natural continuous optical scene decay (1/f)."

            if spike_prominence > 4.8 and hf_ratio > 0.78:
                state = "warning"
                summary = "Spectral frequency spikes detected in high-frequency bands, consistent with neural generative upsampling or diffusion grid artifacts."
                findings.append({
                    "detector": self.check_id,
                    "severity": "high",
                    "title": "Synthetic Generation Artifacts in Frequency Domain",
                    "description": f"Abnormal high-frequency spectral prominence ({spike_prominence:.2f}σ) and energy ratio ({hf_ratio:.2f}) characteristic of synthetic/AI image generators.",
                    "location": {"spectral_spike_prominence": round(spike_prominence, 2)},
                    "confidence": 0.82,
                })
            elif spike_prominence > 4.0:
                state = "inconclusive"
                summary = "Mild periodic frequency patterns detected. Could be synthetic upsampling or fine repeating natural textures (halftone/mesh)."

            details = {
                "method": "2D-FFT Radial Power Spectrum Analysis",
                "high_frequency_ratio": round(hf_ratio, 3),
                "spectral_spike_prominence": round(spike_prominence, 2),
                "estimated_synthetic_likelihood": f"{synthetic_score * 100:.1f}%",
                "model_adapter": "SpectralArtifactDetector_v1.0 (Built-in)",
            }

            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state=state,
                summary=summary,
                details=details,
                findings=findings,
                score=round(synthetic_score, 3),
                confidence=0.85,
            )

        except Exception as e:
            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state="error",
                summary=f"Synthetic image analysis failed: {str(e)}",
            )
