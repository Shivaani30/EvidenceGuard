from pathlib import Path
import wave
import numpy as np
from scipy.io import wavfile
from app.forensics.base import BaseDetector, DetectorOutput

class AudioWaveformDetector(BaseDetector):
    check_id = "wav"
    name = "Audio Waveform & Header Observations"

    def run(self, file_path: Path, evidence_id: str, **kwargs) -> DetectorOutput:
        try:
            # First check WAV header structure
            with open(file_path, "rb") as f:
                header = f.read(44)

            if len(header) < 44 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
                return DetectorOutput(
                    check_id=self.check_id,
                    name=self.name,
                    state="skipped",
                    summary="File is not a standard RIFF/WAVE container.",
                )

            # Read declared size vs actual file size
            declared_riff_size = int.from_bytes(header[4:8], "little") + 8
            actual_size = file_path.stat().st_size

            # Load audio signal via scipy.io.wavfile
            sample_rate, data = wavfile.read(str(file_path))

            # Normalize to mono float32 between -1.0 and 1.0
            if data.ndim > 1:
                mono = np.mean(data, axis=1)
                channels = data.shape[1]
            else:
                mono = data
                channels = 1

            if mono.dtype == np.int16:
                samples = mono.astype(np.float32) / 32768.0
            elif mono.dtype == np.int32:
                samples = mono.astype(np.float32) / 2147483648.0
            elif mono.dtype == np.uint8:
                samples = (mono.astype(np.float32) - 128.0) / 128.0
            else:
                samples = mono.astype(np.float32)

            duration = len(samples) / float(sample_rate)

            # Signal analysis:
            # 1. RMS Energy
            rms = float(np.sqrt(np.mean(samples**2)))

            # 2. Peak amplitude and clipping
            peak = float(np.max(np.abs(samples)))
            clipped_samples = int(np.sum(np.abs(samples) >= 0.999))
            clipping_ratio = float(clipped_samples / len(samples))

            # 3. Zero Crossing Rate (ZCR)
            zero_crossings = np.nonzero(np.diff(samples > 0))[0]
            zcr = float(len(zero_crossings) / (len(samples) + 1e-6))

            # 4. Silence intervals (energy < -45 dB)
            frame_len = int(sample_rate * 0.05)  # 50ms windows
            num_frames = len(samples) // frame_len
            silence_frames = 0
            if num_frames > 0:
                for i in range(num_frames):
                    chunk = samples[i * frame_len : (i + 1) * frame_len]
                    chunk_rms = np.sqrt(np.mean(chunk**2))
                    if chunk_rms < 0.005:
                        silence_frames += 1
                silence_ratio = float(silence_frames / num_frames)
            else:
                silence_ratio = 0.0

            findings = []
            state = "passed"
            summary = "PCM audio header and waveform dynamics are intact and consistent with continuous recording."

            if declared_riff_size != actual_size:
                state = "warning"
                summary = "Declared RIFF container size differs from actual file size (indicates truncation or appended metadata)."
                findings.append({
                    "detector": self.check_id,
                    "severity": "medium",
                    "title": "RIFF Header Size Inconsistency",
                    "description": f"Declared container size ({declared_riff_size} bytes) does not match physical file size ({actual_size} bytes).",
                    "location": {"declared": declared_riff_size, "actual": actual_size},
                    "confidence": 0.92,
                })

            if clipping_ratio > 0.02:
                findings.append({
                    "detector": self.check_id,
                    "severity": "low",
                    "title": "High Waveform Clipping",
                    "description": f"{clipping_ratio*100:.1f}% of samples are at full-scale digital clipping limit.",
                    "location": {"clipping_ratio": round(clipping_ratio, 3)},
                    "confidence": 0.85,
                })

            details = {
                "format": "PCM",
                "sampleRate": sample_rate,
                "channels": channels,
                "durationSec": f"{duration:.2f}",
                "declaredSize": declared_riff_size,
                "actualSize": actual_size,
                "rms_energy": f"{20*np.log10(rms + 1e-6):.1f} dBFS",
                "peak_amplitude": round(peak, 3),
                "zero_crossing_rate": round(zcr, 4),
                "silence_ratio": f"{silence_ratio*100:.1f}%",
            }

            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state=state,
                summary=summary,
                details=details,
                findings=findings,
                score=round(float(clipping_ratio), 3),
            )

        except Exception as e:
            return DetectorOutput(
                check_id=self.check_id,
                name=self.name,
                state="error",
                summary=f"Audio waveform inspection failed: {str(e)}",
            )
