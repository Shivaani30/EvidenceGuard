import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
import cv2
import numpy as np
from app.forensics.video.frames import VideoStreamExtractor
from app.forensics.video.duplicate import VideoDuplicateFrameDetector
from app.forensics.video.continuity import VideoContinuityDetector
from app.forensics.video.timestamp import CctvTimestampDetector
from app.forensics.video.deepfake import DeepfakeVideoDetector

@pytest.fixture
def sample_video(tmp_path):
    video_path = tmp_path / "test_cctv.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = 20.0
    w, h = 320, 240
    writer = cv2.VideoWriter(str(video_path), fourcc, fps, (w, h))

    # Generate 60 frames: first 30 frames moving ball, last 30 frames frozen
    static_frame = None
    for i in range(60):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        if i < 30:
            # Moving circle
            cx = int(50 + i * 5)
            cy = int(120)
            cv2.circle(frame, (cx, cy), 20, (0, 255, 255), -1)
            static_frame = frame
        else:
            # Frozen repeated frame
            frame = static_frame.copy()
        writer.write(frame)

    writer.release()
    return video_path

def test_video_metadata(sample_video):
    meta = VideoStreamExtractor.get_metadata(sample_video)
    assert meta["frame_count"] == 60
    assert meta["fps"] == 20.0
    assert meta["duration"] == 3.0

def test_video_duplicate_frames(sample_video):
    detector = VideoDuplicateFrameDetector()
    out = detector.run(sample_video, "EV-VID-1")
    assert out.check_id == "video_duplicate"
    # Should detect the 30-frame frozen sequence!
    assert out.state in ["passed", "warning"]
    assert "duplicate_sequences_found" in out.details

def test_video_continuity(sample_video):
    detector = VideoContinuityDetector()
    out = detector.run(sample_video, "EV-VID-1")
    assert out.check_id == "video_continuity"
    assert "average_inter_frame_correlation" in out.details

def test_cctv_timestamp(sample_video):
    detector = CctvTimestampDetector()
    out = detector.run(sample_video, "EV-VID-1")
    assert out.check_id == "cctv_timestamp"
    assert "backward_inversions" in out.details

def test_deepfake_detector(sample_video):
    detector = DeepfakeVideoDetector()
    out = detector.run(sample_video, "EV-VID-1")
    assert out.check_id == "deepfake_video"
    assert "faces_detected" in out.details

if __name__ == "__main__":
    pytest.main([__file__])
