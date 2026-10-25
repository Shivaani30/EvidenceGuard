import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
import io
import numpy as np
from PIL import Image
from app.forensics.image.metadata import ImageMetadataDetector
from app.forensics.image.ela import ErrorLevelAnalysisDetector
from app.forensics.image.compression import CompressionAnalysisDetector
from app.forensics.image.splicing import SplicingAndCopyMoveDetector
from app.forensics.image.synthetic import SyntheticImageDetector

@pytest.fixture
def sample_jpeg(tmp_path):
    img_path = tmp_path / "test_image.jpg"
    # Create an image with distinct geometric features
    arr = np.zeros((300, 300, 3), dtype=np.uint8)
    arr[50:120, 50:120] = [200, 50, 50]
    arr[180:250, 180:250] = [50, 200, 50]
    img = Image.fromarray(arr)
    img.save(img_path, "JPEG", quality=85)
    return img_path

def test_image_metadata(sample_jpeg):
    detector = ImageMetadataDetector()
    out = detector.run(sample_jpeg, "EV-TEST-1")
    assert out.check_id == "metadata"
    assert out.state in ["passed", "inconclusive"]
    assert "format" in out.details

def test_image_ela(sample_jpeg):
    detector = ErrorLevelAnalysisDetector()
    out = detector.run(sample_jpeg, "EV-TEST-1", quality=90)
    assert out.check_id == "ela"
    assert out.state in ["passed", "warning", "inconclusive"]
    assert out.artifact is not None
    assert "mean_error" in out.details

def test_image_compression(sample_jpeg):
    detector = CompressionAnalysisDetector()
    out = detector.run(sample_jpeg, "EV-TEST-1")
    assert out.check_id == "compression"
    assert "blocking_artifact_ratio" in out.details

def test_image_splicing_and_copy_move(sample_jpeg):
    detector = SplicingAndCopyMoveDetector()
    out = detector.run(sample_jpeg, "EV-TEST-1")
    assert out.check_id == "splicing"
    assert "noise_discrepancy_ratio" in out.details

def test_image_synthetic_spectral(sample_jpeg):
    detector = SyntheticImageDetector()
    out = detector.run(sample_jpeg, "EV-TEST-1")
    assert out.check_id == "synthetic_image"
    assert "high_frequency_ratio" in out.details

if __name__ == "__main__":
    pytest.main([__file__])
