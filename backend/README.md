# EvidenceGuard — Digital Evidence Authenticity & Integrity Verification Platform Backend

This backend powers the EvidenceGuard platform, providing real-time, multi-layer forensic analysis of digital images, audio recordings, video streams, CCTV footage, and associated metadata.

---

## Architectural Principles

1. **Multi-Layer Forensic Fusion**:
   Authenticity cannot be established by a single model or heuristic. The platform executes independent forensic detectors across container metadata, physical signal dynamics, frequency domains, and temporal continuity, fusing evidence using a weighted reliability model.
2. **Cryptographic Chain of Custody**:
   Every uploaded file is stored immutably. Pre- and post-analysis SHA-256 and SHA-512 hashes are compared to guarantee that no forensic check modifies source evidence bytes. An append-only SHA-256 hash-chained audit trail logs every registration, analysis stage, and report generation.
3. **Factual Observations vs. Model Inferences**:
   Reports clearly separate raw mathematical observations (byte hashes, 8x8 DCT grid alignment, spectral flux, PTS gaps) from investigative inferences. The system acts as a forensic decision-support tool.
4. **Court-Ready PDF Reports**:
   Generates comprehensive, professional forensic reports complete with chain-of-custody tables, detector matrices, embedded visual artifacts (original vs ELA maps, spectrograms), and examiner attestation blocks.

---

## Supported Media & Forensics Modules

### 1. Image Forensics
- **EXIF & Segment Forensics**: Scans camera Make, Model, DateTimeOriginal, DateTimeDigitized, ModifyDate, GPS, and identifies editing software signatures (Photoshop, Lightroom, GIMP, Canva, etc.).
- **JPEG Error Level Analysis (ELA)**: Recompresses image at configurable quality (90%/95%), calculates normalized amplified error residual, and saves visual PNG artifacts.
- **8x8 Block Compression Analysis**: Measures blocking artifact factor (BAF) across grid boundaries and detects localized double-compression variance across tiles.
- **Copy-Move & Noise Splicing**: ORB keypoint matching with spatial clustering to detect cloned regions combined with high-pass patch noise variance disparity.
- **Synthetic / AI Image Detection**: 2D Fast Fourier Transform (FFT) radial power spectrum evaluation to detect high-frequency grid artifacts typical of diffusion and GAN generators.

### 2. Video & CCTV Forensics
- **Container & Stream Metadata**: Extracts codec, container, FPS, frame count, resolution, and presentation timestamps (PTS/DTS).
- **Duplicate & Frozen Frame Analysis**: Perceptual difference hashing (dHash) to flag suspicious frozen video loops and static footage insertion.
- **Temporal Continuity & Cadence**: HSV color histogram correlation across frames to detect abrupt scene cuts and dropped frame bursts.
- **CCTV Timestamp Verification**: Audits internal presentation timestamps for backward inversions and abnormal temporal gaps.
- **Deepfake Video Screening**: Facial detection across keyframes to screen temporal boundary jitter characteristic of face-swapping models.

### 3. Audio Forensics
- **Waveform & Header Observations**: Validates PCM format, sample rate, channels, RMS energy, and digital clipping ratios.
- **Spectral Analysis & Spectrogram**: Computes Short-Time Fourier Transform (STFT) and generates high-resolution spectrogram PNG artifacts.
- **Splice & Edit Boundary Detection**: Detects sharp spectral flux impulses and acoustic energy discontinuities.
- **AI Voice & Synthetic Speech Screening**: Measures Spectral Flatness (SFM) to flag vocoder and neural text-to-speech resonances.

### 4. Cross-Modal Correlation & Consensus Graph
- **Temporal Alignment**: Aligns video anomalies with acoustic discontinuities occurring within a ±0.5s temporal window.
- **Forensic Consensus Graph**: Represents evidence, metadata, detectors, media regions/segments, and correlated events as nodes and edges for explainability.

---

## Directory Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── analysis.py
│   │       ├── audit.py
│   │       ├── dashboard.py
│   │       ├── evidence.py
│   │       ├── reports.py
│   │       ├── tools.py
│   │       └── ws.py
│   ├── config.py
│   ├── database.py
│   ├── forensics/
│   │   ├── base.py
│   │   ├── compare.py
│   │   ├── pipeline.py
│   │   ├── audio/
│   │   │   ├── spectral.py
│   │   │   ├── splice.py
│   │   │   ├── synthetic.py
│   │   │   └── waveform.py
│   │   ├── fusion/
│   │   │   ├── consensus_graph.py
│   │   │   ├── cross_modal.py
│   │   │   └── fusion_engine.py
│   │   ├── image/
│   │   │   ├── compression.py
│   │   │   ├── ela.py
│   │   │   ├── metadata.py
│   │   │   ├── splicing.py
│   │   │   └── synthetic.py
│   │   └── video/
│   │       ├── continuity.py
│   │       ├── deepfake.py
│   │       ├── duplicate.py
│   │       ├── frames.py
│   │       └── timestamp.py
│   ├── main.py
│   ├── models/
│   │   ├── audit.py
│   │   └── evidence.py
│   ├── reports/
│   │   └── pdf_generator.py
│   ├── schemas/
│   │   ├── audit.py
│   │   ├── dashboard.py
│   │   └── evidence.py
│   ├── services/
│   │   ├── audit_service.py
│   │   ├── evidence_service.py
│   │   ├── hash_service.py
│   │   └── job_service.py
│   ├── storage/
│   │   └── file_storage.py
│   └── utils/
│       └── security.py
├── requirements.txt
├── run_server.py
├── storage_data/
│   ├── artifacts/
│   ├── evidence/
│   └── reports/
└── tests/
    ├── test_api.py
    ├── test_audio_forensics.py
    ├── test_image_forensics.py
    ├── test_integrity.py
    └── test_video_forensics.py
```

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Install Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Run the Backend Server
```bash
python run_server.py
```
The FastAPI backend will start on `http://127.0.0.1:8000`.
- API Documentation (Swagger): `http://127.0.0.1:8000/docs`
- Healthcheck: `http://127.0.0.1:8000/api/health`

### 3. Run the Frontend
In another terminal:
```bash
npm run dev
```
The frontend will start on `http://localhost:3000` (or `http://localhost:5173`) and automatically proxy `/api`, `/artifacts`, and `/ws` to the backend.

### 4. Run Backend Tests
```bash
python -m pytest backend/tests --basetemp=./test_temp
```
