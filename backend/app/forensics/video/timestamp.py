from pathlib import Path
import cv2
from app.forensics.base import BaseDetector, DetectorOutput
from app.forensics.video.frames import VideoStreamExtractor

class CctvTimestampDetector(BaseDetector):
    check_id = "cctv_timestamp"
    name = "CCTV Timestamp & Cadence Verification"

    def run(self, file_path: Path, evidence_id: str, **kwargs) -> DetectorOutput:
        try:
            meta = VideoStreamExtractor.get_metadata(file_path)
            fps = float(meta["fps"]) or 25.0
            expected_interval = 1.0 / fps

            cap = cv2.VideoCapture(str(file_path))
            timestamps_ms = []
            frame_idx = 0
            max_samples = 400

            while cap.isOpened() and frame_idx < max_samples:
                ret = cap.grab()
                if not ret:
                    break
                pos_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
                timestamps_ms.append((frame_idx, pos_msec))
                frame_idx += 1
            cap.release()

            findings = []
            timeline_events = []
            state = "passed"
            summary = "Internal timestamp progression matches declared container FPS with zero timing inversions."

            backward_jumps = 0
            unexpected_gaps = 0

            for i in range(1, len(timestamps_ms)):
                prev_f, prev_t = timestamps_ms[i - 1]
                curr_f, curr_t = timestamps_ms[i]
                delta_sec = (curr_t - prev_t) / 1000.0

                # Check backward jump
                if delta_sec < -0.01:
                    backward_jumps += 1
                    findings.append({
                        "detector": self.check_id,
                        "severity": "critical",
                        "title": "Backward Timestamp Inversion",
                        "description": f"Frame {curr_f} timestamp ({curr_t/1000.0:.2f}s) is earlier than frame {prev_f} ({prev_t/1000.0:.2f}s). Strong indicator of spliced or reordered video segments.",
                        "location": {"frame": curr_f, "timestamp": curr_t / 1000.0},
                        "confidence": 0.95,
                    })
                    timeline_events.append({
                        "start_time": max(0.0, prev_t / 1000.0),
                        "end_time": curr_t / 1000.0,
                        "event_type": "timestamp_jump",
                        "severity": "critical",
                        "detector": self.check_id,
                        "confidence": 0.95,
                        "description": "Backward timestamp inversion detected",
                    })

                # Check gap larger than 3x normal frame interval
                elif delta_sec > expected_interval * 3.5:
                    unexpected_gaps += 1
                    findings.append({
                        "detector": self.check_id,
                        "severity": "high",
                        "title": "Temporal PTS Gap / Dropped Footage",
                        "description": f"Unusual time gap of {delta_sec:.2f}s between frame {prev_f} and {curr_f}. Indicates dropped frames or cut recording.",
                        "location": {"start_time": prev_t / 1000.0, "end_time": curr_t / 1000.0},
                        "confidence": 0.90,
                    })
                    timeline_events.append({
                        "start_time": prev_t / 1000.0,
                        "end_time": curr_t / 1000.0,
                        "event_type": "timestamp_gap",
                        "severity": "high",
                        "detector": self.check_id,
                        "confidence": 0.90,
                        "description": f"Timestamp gap ({delta_sec:.2f}s)",
                    })

            if backward_jumps > 0 or unexpected_gaps > 0:
                state = "failed" if backward_jumps > 0 else "warning"
                summary = f"Detected {backward_jumps} timestamp inversions and {unexpected_gaps} abnormal temporal gap(s)."

            details = {
                "expected_interval_sec": round(expected_interval, 4),
                "backward_inversions": backward_jumps,
                "temporal_gaps": unexpected_gaps,
                "frames_audited": len(timestamps_ms),
            }

            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state=state,
                summary=summary,
                details=details,
                findings=findings,
                timeline_events=timeline_events,
                score=round(min(1.0, backward_jumps * 0.5 + unexpected_gaps * 0.25), 3),
            )

        except Exception as e:
            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state="error",
                summary=f"Timestamp analysis failed: {str(e)}",
            )
