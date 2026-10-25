from pathlib import Path
from typing import Callable, Any
from app.forensics.base import BaseDetector, DetectorOutput
from app.forensics.compare import ReferenceComparisonDetector
from app.forensics.image.metadata import ImageMetadataDetector
from app.forensics.image.ela import ErrorLevelAnalysisDetector
from app.forensics.image.compression import CompressionAnalysisDetector
from app.forensics.image.splicing import SplicingAndCopyMoveDetector
from app.forensics.image.synthetic import SyntheticImageDetector
from app.forensics.video.duplicate import VideoDuplicateFrameDetector
from app.forensics.video.continuity import VideoContinuityDetector
from app.forensics.video.timestamp import CctvTimestampDetector
from app.forensics.video.deepfake import DeepfakeVideoDetector
from app.forensics.audio.waveform import AudioWaveformDetector
from app.forensics.audio.spectral import AudioSpectralDetector
from app.forensics.audio.splice import AudioSpliceDetector
from app.forensics.audio.synthetic import SyntheticSpeechDetector
from app.forensics.fusion.fusion_engine import ForensicFusionEngine
from app.services.hash_service import hash_service

ALL_DETECTORS: dict[str, type[BaseDetector]] = {
    # Reference
    "compare": ReferenceComparisonDetector,
    # Image
    "metadata": ImageMetadataDetector,
    "ela": ErrorLevelAnalysisDetector,
    "compression": CompressionAnalysisDetector,
    "splicing": SplicingAndCopyMoveDetector,
    "synthetic_image": SyntheticImageDetector,
    # Video
    "video_duplicate": VideoDuplicateFrameDetector,
    "video_continuity": VideoContinuityDetector,
    "cctv_timestamp": CctvTimestampDetector,
    "deepfake_video": DeepfakeVideoDetector,
    # Audio
    "wav": AudioWaveformDetector,
    "audio_spectral": AudioSpectralDetector,
    "audio_splice": AudioSpliceDetector,
    "synthetic_speech": SyntheticSpeechDetector,
}

class ForensicPipeline:
    @staticmethod
    def execute(
        file_path: Path,
        evidence_id: str,
        kind: str,
        selected_checks: list[str],
        reference_hash: str | None = None,
        progress_callback: Callable[[int, str, str], None] | None = None,
    ) -> tuple[list[DetectorOutput], dict[str, Any]]:
        """
        Execute selected forensic detectors with live stage progress reporting.
        Verifies original hash before and after execution to guarantee immutable evidence.
        """
        # 1. Pre-execution integrity check
        initial_hash = hash_service.compute_sha256(file_path)

        outputs: list[DetectorOutput] = []
        total_checks = len(selected_checks)
        completed = 0

        if progress_callback:
            progress_callback(5, "initialization", "Initializing forensic detectors and environment")

        for check_id in selected_checks:
            detector_cls = ALL_DETECTORS.get(check_id)
            if not detector_cls:
                continue

            detector = detector_cls()
            if progress_callback:
                progress = int(10 + (completed / max(1, total_checks)) * 80)
                progress_callback(progress, check_id, f"Running {detector.name}")

            try:
                out = detector.run(
                    file_path=file_path,
                    evidence_id=evidence_id,
                    reference_hash=reference_hash,
                )
                outputs.append(out)
            except Exception as e:
                outputs.append(
                    DetectorOutput(
                        check_id=check_id,
                        name=detector.name,
                        state="error",
                        summary=f"Detector failed with unexpected error: {str(e)}",
                    )
                )

            completed += 1

        if progress_callback:
            progress_callback(92, "fusion", "Fusing multi-layer forensic evidence")

        # 2. Post-execution immutability verification
        post_hash = hash_service.compute_sha256(file_path)
        if initial_hash.lower() != post_hash.lower():
            raise RuntimeError(
                f"FATAL INTEGRITY VIOLATION: Evidence bytes changed during analysis! Expected {initial_hash}, got {post_hash}"
            )

        # 3. Fuse evidence
        assessment = ForensicFusionEngine.fuse(
            evidence_kind=kind,
            detector_outputs=outputs,
            reference_present=bool(reference_hash),
        )

        if progress_callback:
            progress_callback(100, "completed", "Forensic analysis completed")

        return outputs, assessment
