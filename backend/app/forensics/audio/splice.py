from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import spectrogram
from app.forensics.base import BaseDetector, DetectorOutput

class AudioSpliceDetector(BaseDetector):
    check_id = "audio_splice"
    name = "Audio Splice & Edit Boundary Detection"

    def run(self, file_path: Path, evidence_id: str, **kwargs) -> DetectorOutput:
        try:
            sample_rate, data = wavfile.read(str(file_path))
            if data.ndim > 1:
                samples = np.mean(data, axis=1)
            else:
                samples = data

            if samples.dtype == np.int16:
                samples = samples.astype(np.float32) / 32768.0
            else:
                samples = samples.astype(np.float32)

            # Compute spectral flux
            nperseg = 512
            freqs, times, Sxx = spectrogram(samples, fs=sample_rate, nperseg=nperseg, noverlap=256)
            
            # Spectral flux between consecutive time frames
            diff = np.diff(Sxx, axis=1)
            # Rectified flux (positive increases in spectral power)
            pos_diff = np.maximum(0, diff)
            flux = np.sum(pos_diff**2, axis=0)

            if len(flux) == 0:
                return DetectorOutput(
                    check_id=self.check_id,
                    name=self.name,
                    state="skipped",
                    summary="Audio duration too short for splice analysis.",
                )

            mean_flux = float(np.mean(flux))
            std_flux = float(np.std(flux))
            threshold = mean_flux + 4.5 * std_flux

            # Find boundary peaks
            spike_indices = np.where(flux > threshold)[0]
            
            # Group nearby spikes (within 0.3s)
            suspicious_edits = []
            if len(spike_indices) > 0:
                current_group = [spike_indices[0]]
                for idx in spike_indices[1:]:
                    if idx - current_group[-1] < 10:  # ~10 frames ≈ 0.1s
                        current_group.append(idx)
                    else:
                        center_idx = int(np.mean(current_group))
                        ts = float(times[center_idx])
                        suspicious_edits.append({
                            "timestamp": round(ts, 2),
                            "flux_intensity": round(float(flux[center_idx] / (mean_flux + 1e-6)), 2),
                        })
                        current_group = [idx]
                if current_group:
                    center_idx = int(np.mean(current_group))
                    ts = float(times[center_idx])
                    suspicious_edits.append({
                        "timestamp": round(ts, 2),
                        "flux_intensity": round(float(flux[center_idx] / (mean_flux + 1e-6)), 2),
                    })

            findings = []
            timeline_events = []
            state = "passed"
            summary = "Continuous audio recording with no abnormal spectral boundary spikes or acoustic cuts."

            if suspicious_edits:
                state = "warning"
                summary = f"Detected {len(suspicious_edits)} candidate editing boundary/splice point(s) with abrupt spectral energy discontinuity."
                for edit in suspicious_edits[:5]:
                    findings.append({
                        "detector": self.check_id,
                        "severity": "medium",
                        "title": "Acoustic Discontinuity / Candidate Splice",
                        "description": f"Sharp spectral flux impulse at {edit['timestamp']}s ({edit['flux_intensity']}x baseline energy). Indicates candidate splice or cut point.",
                        "location": {"timestamp": edit["timestamp"], "flux_ratio": edit["flux_intensity"]},
                        "confidence": 0.82,
                    })
                    timeline_events.append({
                        "start_time": max(0.0, edit["timestamp"] - 0.15),
                        "end_time": edit["timestamp"] + 0.15,
                        "event_type": "audio_splice",
                        "severity": "medium",
                        "detector": self.check_id,
                        "confidence": 0.82,
                        "description": f"Acoustic splice anomaly ({edit['flux_intensity']}x flux impulse)",
                    })

            details = {
                "mean_spectral_flux": round(mean_flux, 4),
                "flux_std_deviation": round(std_flux, 4),
                "candidate_splices_found": len(suspicious_edits),
            }

            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state=state,
                summary=summary,
                details=details,
                findings=findings,
                timeline_events=timeline_events,
                score=round(min(1.0, len(suspicious_edits) * 0.3), 3),
            )

        except Exception as e:
            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state="error",
                summary=f"Splice detection failed: {str(e)}",
            )
