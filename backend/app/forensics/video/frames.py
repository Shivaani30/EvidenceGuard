from pathlib import Path
from typing import Generator
import cv2

class VideoStreamExtractor:
    @staticmethod
    def get_metadata(video_path: Path) -> dict[str, str | int | float]:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video file: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = (frame_count / fps) if fps > 0 else 0.0

        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)]).strip()

        cap.release()
        return {
            "fps": round(fps, 2),
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "resolution": f"{width}x{height}",
            "duration": round(duration, 2),
            "codec": codec or "H264/AVC",
        }

    @staticmethod
    def stream_frames(
        video_path: Path, max_frames: int = 1000, step: int = 1, target_width: int = 320
    ) -> Generator[tuple[int, float, any], None, None]:
        """Stream frames efficiently in batches without exhausting memory."""
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_idx = 0
        yielded = 0

        while cap.isOpened() and yielded < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % step == 0:
                timestamp = frame_idx / fps
                # Downsample frame for fast analysis
                h, w = frame.shape[:2]
                if w > target_width:
                    scale = target_width / w
                    frame_small = cv2.resize(frame, (target_width, int(h * scale)))
                else:
                    frame_small = frame
                yield frame_idx, timestamp, frame_small
                yielded += 1

            frame_idx += 1

        cap.release()
