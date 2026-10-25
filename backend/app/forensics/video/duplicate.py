from pathlib import Path
import cv2
import numpy as np
from app.forensics.base import BaseDetector, DetectorOutput
from app.forensics.video.frames import VideoStreamExtractor

def compute_dhash(image_gray, hash_size=8):
    resized = cv2.resize(image_gray, (hash_size + 1, hash_size))
    diff = resized[:, 1:] > resized[:, :-1]
    return diff.flatten()

class VideoDuplicateFrameDetector(BaseDetector):
    check_id = "video_duplicate"
    name = "Duplicate & Frozen Frame Analysis"

    def run(self, file_path: Path, evidence_id: str, **kwargs) -> DetectorOutput:
        try:
            meta = VideoStreamExtractor.get_metadata(file_path)
            fps = float(meta["fps"]) or 25.0
            
            # Sample frames (every frame up to 600 frames, or step for longer videos)
            total = int(meta["frame_count"])
            step = 1 if total <= 600 else max(2, total // 600)

            prev_hash = None
            prev_idx = 0
            prev_ts = 0.0

            duplicate_runs = []
            current_run = []

            for idx, ts, frame in VideoStreamExtractor.stream_frames(file_path, max_frames=600, step=step):
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                curr_hash = compute_dhash(gray)

                if prev_hash is not None:
                    # Hamming distance between dHashes
                    hamming_dist = np.count_nonzero(curr_hash != prev_hash)
                    # If identical or near-identical (< 2 bit differences out of 64)
                    if hamming_dist <= 1:
                        if not current_run:
                            current_run = [prev_idx, idx, prev_ts, ts]
                        else:
                            current_run[1] = idx
                            current_run[3] = ts
                    else:
                        if current_run:
                            dur = current_run[3] - current_run[2]
                            frames_frozen = (current_run[1] - current_run[0]) // step + 1
                            if frames_frozen >= 5:  # significant freeze
                                duplicate_runs.append({
                                    "start_frame": current_run[0],
                                    "end_frame": current_run[1],
                                    "start_ts": round(current_run[2], 2),
                                    "end_ts": round(current_run[3], 2),
                                    "duration_sec": round(dur, 2),
                                    "frozen_frames": frames_frozen,
                                })
                            current_run = []

                prev_hash = curr_hash
                prev_idx = idx
                prev_ts = ts

            if current_run:
                frames_frozen = (current_run[1] - current_run[0]) // step + 1
                if frames_frozen >= 5:
                    duplicate_runs.append({
                        "start_frame": current_run[0],
                        "end_frame": current_run[1],
                        "start_ts": round(current_run[2], 2),
                        "end_ts": round(current_run[3], 2),
                        "duration_sec": round(current_run[3] - current_run[2], 2),
                        "frozen_frames": frames_frozen,
                    })

            findings = []
            timeline_events = []
            state = "passed"
            summary = "Natural frame variability observed across the video sequence."

            if duplicate_runs:
                # Filter long freezes
                long_freezes = [r for r in duplicate_runs if r["duration_sec"] >= 1.0]
                if long_freezes:
                    state = "warning"
                    summary = f"Detected {len(long_freezes)} frozen/duplicate frame sequence(s). Indicates potential CCTV video loop or frozen camera feed."
                    for r in long_freezes:
                        findings.append({
                            "detector": self.check_id,
                            "severity": "high" if r["duration_sec"] >= 3.0 else "medium",
                            "title": "Suspicious Frozen / Repeated Video Frames",
                            "description": f"Video frozen for {r['duration_sec']}s (frames {r['start_frame']} to {r['end_frame']}).",
                            "location": {"start_time": r["start_ts"], "end_time": r["end_ts"], "frames": [r["start_frame"], r["end_frame"]]},
                            "confidence": 0.90,
                        })
                        timeline_events.append({
                            "start_time": r["start_ts"],
                            "end_time": r["end_ts"],
                            "event_type": "duplicate_frames",
                            "severity": "high" if r["duration_sec"] >= 3.0 else "medium",
                            "detector": self.check_id,
                            "confidence": 0.90,
                            "description": f"Frozen video sequence ({r['duration_sec']}s, {r['frozen_frames']} frames)",
                        })

            details = {
                "total_frames_in_file": meta["frame_count"],
                "fps": meta["fps"],
                "duration_seconds": meta["duration"],
                "duplicate_sequences_found": len(duplicate_runs),
                "sampling_step": step,
            }

            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state=state,
                summary=summary,
                details=details,
                findings=findings,
                timeline_events=timeline_events,
                score=round(min(1.0, len(duplicate_runs) * 0.25), 3),
            )

        except Exception as e:
            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state="error",
                summary=f"Duplicate frame analysis failed: {str(e)}",
            )
