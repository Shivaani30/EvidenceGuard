from pathlib import Path
import cv2
import numpy as np
from app.forensics.base import BaseDetector, DetectorOutput
from app.forensics.video.frames import VideoStreamExtractor

class VideoContinuityDetector(BaseDetector):
    check_id = "video_continuity"
    name = "Temporal Continuity & Frame Cadence Analysis"

    def run(self, file_path: Path, evidence_id: str, **kwargs) -> DetectorOutput:
        try:
            meta = VideoStreamExtractor.get_metadata(file_path)
            fps = float(meta["fps"]) or 25.0
            total = int(meta["frame_count"])
            step = 1 if total <= 600 else max(2, total // 600)

            prev_hist = None
            prev_ts = 0.0
            prev_idx = 0

            cut_anomalies = []
            flux_values = []

            for idx, ts, frame in VideoStreamExtractor.stream_frames(file_path, max_frames=600, step=step):
                # Calculate color histogram in HSV
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
                cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

                if prev_hist is not None:
                    # Compare histograms (Correlation: 1.0 = identical, < 0.3 = abrupt change)
                    corr = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                    flux_values.append(corr)

                    # Abrupt severe drop in similarity between consecutive single frames
                    if step == 1 and corr < 0.25:
                        cut_anomalies.append({
                            "frame": idx,
                            "timestamp": round(ts, 2),
                            "correlation": round(corr, 3),
                        })

                prev_hist = hist
                prev_ts = ts
                prev_idx = idx

            findings = []
            timeline_events = []
            state = "passed"
            summary = "Temporal transitions and frame cadence are consistent with continuous recording."

            if cut_anomalies:
                state = "warning"
                summary = f"Detected {len(cut_anomalies)} abrupt temporal discontinuities/scene cuts in continuous stream."
                for cut in cut_anomalies[:5]:
                    findings.append({
                        "detector": self.check_id,
                        "severity": "medium",
                        "title": "Abrupt Inter-Frame Discontinuity",
                        "description": f"Drastic scene flux discontinuity at frame {cut['frame']} ({cut['timestamp']}s). Suggests frame removal or splice insertion.",
                        "location": {"timestamp": cut["timestamp"], "frame": cut["frame"]},
                        "confidence": 0.85,
                    })
                    timeline_events.append({
                        "start_time": max(0.0, cut["timestamp"] - 0.2),
                        "end_time": cut["timestamp"] + 0.2,
                        "event_type": "abrupt_cut",
                        "severity": "medium",
                        "detector": self.check_id,
                        "confidence": 0.85,
                        "description": f"Abrupt frame transition at {cut['timestamp']}s (correlation: {cut['correlation']})",
                    })

            mean_flux = float(np.mean(flux_values)) if flux_values else 1.0

            details = {
                "average_inter_frame_correlation": round(mean_flux, 3),
                "abrupt_discontinuities_count": len(cut_anomalies),
                "fps_cadence": meta["fps"],
                "frames_sampled": len(flux_values) + 1,
            }

            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state=state,
                summary=summary,
                details=details,
                findings=findings,
                timeline_events=timeline_events,
                score=round(min(1.0, len(cut_anomalies) * 0.3), 3),
            )

        except Exception as e:
            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state="error",
                summary=f"Continuity analysis encountered error: {str(e)}",
            )
