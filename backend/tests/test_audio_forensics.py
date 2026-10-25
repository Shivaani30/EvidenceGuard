import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
import numpy as np
from scipy.io import wavfile
from app.forensics.audio.waveform import AudioWaveformDetector
from app.forensics.audio.spectral import AudioSpectralDetector
from app.forensics.audio.splice import AudioSpliceDetector
from app.forensics.audio.synthetic import SyntheticSpeechDetector

@pytest.fixture
def sample_wav(tmp_path):
    wav_path = tmp_path / "test_audio.wav"
    sr = 16000
    t = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
    # Sine tone 440 Hz + harmonics
    tone = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.2 * np.sin(2 * np.pi * 880 * t)
    # Convert to int16
    samples = (tone * 32767).astype(np.int16)
    wavfile.write(str(wav_path), sr, samples)
    return wav_path

def test_audio_waveform(sample_wav):
    detector = AudioWaveformDetector()
    out = detector.run(sample_wav, "EV-AUDIO-1")
    assert out.check_id == "wav"
    assert out.state == "passed"
    assert "sampleRate" in out.details
    assert out.details["sampleRate"] == 16000

def test_audio_spectral(sample_wav):
    detector = AudioSpectralDetector()
    out = detector.run(sample_wav, "EV-AUDIO-1")
    assert out.check_id == "audio_spectral"
    assert out.artifact is not None
    assert "mean_spectral_centroid" in out.details

def test_audio_splice(sample_wav):
    detector = AudioSpliceDetector()
    out = detector.run(sample_wav, "EV-AUDIO-1")
    assert out.check_id == "audio_splice"
    assert "candidate_splices_found" in out.details

def test_audio_synthetic(sample_wav):
    detector = SyntheticSpeechDetector()
    out = detector.run(sample_wav, "EV-AUDIO-1")
    assert out.check_id == "synthetic_speech"
    assert "spectral_flatness_measure" in out.details

if __name__ == "__main__":
    pytest.main([__file__])
