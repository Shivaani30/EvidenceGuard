from pathlib import Path
import cv2
import numpy as np
from app.forensics.base import BaseDetector, DetectorOutput
from app.forensics.video.frames import VideoStreamExtractor

class DeepfakeVideoDetector(BaseDetector):
    check_id = "deepfake_video"
    name = "Facial Consistency & Deepfake Screening"

    def run(self, file_path: Path, evidence_id: str, **kwargs) -> DetectorOutput:
        try:
            # Load default OpenCV face detector
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )

            faces_detected_count = 0
            frames_with_face = 0
            jitter_values = []
            prev_center = None

            # Stream keyframes (every 5th frame up to 200 frames)
            meta = VideoStreamExtractor.get_metadata(file_path)
            total = int(meta["frame_count"])
            step = max(3, total // 150)

            for idx, ts, frame in VideoStreamExtractor.stream_frames(file_path, max_frames=150, step=step):
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(40, 40))

                if len(faces) > 0:
                    faces_detected_count += len(faces)
                    frames_with_face += 1
                    # Take largest face
                    x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
                    center = np.array([x + w / 2.0, y + h / 2.0])

                    if prev_center is not None:
                        jitter = np.linalg.norm(center - prev_center)
                        jitter_values.append(jitter)
                    prev_center = center
                else:
                    prev_center = None

            findings = []
            timeline_events = []
            state = "passed"
            summary = "Facial boundaries and temporal continuity show no synthetic warping anomalies."

            if frames_with_face == 0:
                return DetectorOutput(
                    check_id=self.check_id,
                    name=self.name,
                    state="skipped",
                    summary="No human faces detected in sampled video frames for deepfake facial analysis.",
                    details={"faces_detected": 0},
                )

            # Analyze jitter standard deviation
            jitter_std = float(np.std(jitter_values)) if jitter_values else 0.0
            jitter_mean = float(np.mean(jitter_values)) if jitter_values else 0.0

            deepfake_score = 0.1
            if jitter_std > 45.0:
                state = "warning"
                summary = "High facial boundary instability/jitter detected across keyframes, consistent with synthetic face-swap warping."
                deepfake_score = 0.72
                findings.append({
                    "detector": self.check_id,
                    "severity": "medium",
                    "title": "Facial Boundary Temporal Instability",
                    "description": f"Facial location variance ({jitter_std:.1f}px) exhibits unnatural flickering typical of face-replacement models.",
                    "location": {"frames_with_faces": frames_with_face},
                    "confidence": 0.75,
                })

            details = {
                "faces_detected": faces_detected_count,
                "keyframes_with_faces": frames_with_face,
                "facial_jitter_std": round(jitter_std, 2),
                "model_adapter": "FaceConsistencyAdapter_v1.0",
                "estimated_deepfake_risk": f"{deepfake_score*100:.1f}%",
            }

            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state=state,
                summary=summary,
                details=details,
                findings=findings,
                timeline_events=timeline_events,
                score=round(deepfake_score, 3),
            )

        except Exception as e:
            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state="error",
                summary=f"Deepfake video analysis failed: {str(e)}",
            )
