from typing import Any
from app.forensics.base import DetectorOutput
from app.forensics.fusion.cross_modal import CrossModalCorrelator

# Detector reliability weights in fusion calculation
DETECTOR_WEIGHTS = {
    "compare": 1.0,           # Exact hash comparison has 100% cryptographic certainty
    "metadata": 0.85,          # Authoritative container/EXIF tags
    "ela": 0.75,               # Compression residual heuristic
    "compression": 0.80,       # 8x8 block grid math
    "splicing": 0.85,          # Feature descriptor cloning + noise variance
    "synthetic_image": 0.80,   # Spectral FFT artifact
    "video_duplicate": 0.88,   # Perceptual hash sequence
    "video_continuity": 0.82,  # Inter-frame flux
    "cctv_timestamp": 0.95,    # Hard timestamp progression
    "deepfake_video": 0.78,    # Facial boundary jitter
    "wav": 0.90,               # PCM structural headers
    "audio_spectral": 0.75,    # STFT spectral distribution
    "audio_splice": 0.84,      # Spectral flux impulse
    "synthetic_speech": 0.80,  # SFM vocal tract resonance
}

SEVERITY_SCORES = {
    "critical": 1.0,
    "high": 0.75,
    "medium": 0.45,
    "low": 0.20,
}

class ForensicFusionEngine:
    @staticmethod
    def fuse(
        evidence_kind: str,
        detector_outputs: list[DetectorOutput],
        reference_present: bool = False,
    ) -> dict[str, Any]:
        """Multi-layer forensic fusion combining independent detectors into an explainable assessment."""
        if not detector_outputs:
            return {
                "classification": "INCONCLUSIVE",
                "integrity_score": 50.0,
                "tampering_likelihood": 0.5,
                "confidence": 0.2,
                "summary": "No forensic detectors were evaluated on this evidence.",
                "supporting_findings": [],
                "contradicting_findings": [],
            }

        total_weight = 0.0
        weighted_tamper_sum = 0.0
        confidence_sum = 0.0
        executed_detectors_count = 0

        supporting_findings = []
        contradicting_findings = []

        all_timeline = []
        all_findings = []

        for out in detector_outputs:
            all_timeline.extend(out.timeline_events)
            all_findings.extend(out.findings)

            if out.state in ["skipped", "unavailable", "pending", "running"]:
                continue

            executed_detectors_count += 1
            weight = DETECTOR_WEIGHTS.get(out.check_id, 0.75)
            total_weight += weight
            confidence_sum += (out.confidence * weight)

            # Score computation per detector
            det_tamper = 0.0
            if out.state == "failed":
                det_tamper = 0.95
                supporting_findings.append(f"{out.name}: Failed — {out.summary}")
            elif out.state == "warning":
                det_tamper = 0.65
                supporting_findings.append(f"{out.name}: Warning — {out.summary}")
            elif out.state == "inconclusive":
                det_tamper = 0.35
            elif out.state == "passed":
                det_tamper = 0.05
                contradicting_findings.append(f"{out.name}: Passed — {out.summary}")

            weighted_tamper_sum += (det_tamper * weight)

        # Cross-modal correlation bonus
        correlated_events = CrossModalCorrelator.correlate(all_timeline)
        all_timeline.extend(correlated_events)
        if correlated_events:
            # Significant boost to tampering likelihood when multi-modal events align
            weighted_tamper_sum += len(correlated_events) * 0.4
            total_weight += len(correlated_events) * 0.3
            for c in correlated_events:
                supporting_findings.append(c["description"])

        if total_weight > 0:
            raw_tamper_likelihood = weighted_tamper_sum / total_weight
            overall_confidence = confidence_sum / total_weight
        else:
            raw_tamper_likelihood = 0.0
            overall_confidence = 0.5

        # Normalize tampering likelihood and integrity score
        tampering_likelihood = float(min(1.0, max(0.0, raw_tamper_likelihood)))
        integrity_score = float(round((1.0 - tampering_likelihood) * 100.0, 1))

        # Forensic classification
        if reference_present and any(o.check_id == "compare" and o.state == "passed" for o in detector_outputs):
            classification = "NO SIGNIFICANT ANOMALY DETECTED"
            integrity_score = 100.0
            tampering_likelihood = 0.0
            overall_confidence = 1.0
            summary = "Cryptographically verified byte-for-byte identical to the trusted reference evidence."
        elif tampering_likelihood >= 0.75:
            classification = "HIGH SUSPICION"
            summary = "Multiple independent forensic indicators detect significant manipulation or tampering markers."
        elif tampering_likelihood >= 0.45:
            classification = "MODERATE SUSPICION"
            summary = "Forensic tests flagged notable irregularities (e.g. localized compression divergence or editing signatures) warranting expert review."
        elif tampering_likelihood >= 0.20:
            classification = "LOW SUSPICION"
            summary = "Minor forensic observations detected, but no definitive evidence of tampering."
        elif executed_detectors_count < 2:
            classification = "INCONCLUSIVE"
            summary = "Insufficient forensic checks executed to establish confidence."
        else:
            classification = "NO SIGNIFICANT ANOMALY DETECTED"
            summary = "All executed forensic checks passed with uniform distributions and no detectable anomalies."

        return {
            "classification": classification,
            "integrity_score": integrity_score,
            "tampering_likelihood": round(tampering_likelihood, 3),
            "confidence": round(overall_confidence, 2),
            "summary": summary,
            "supporting_findings": supporting_findings,
            "contradicting_findings": contradicting_findings,
            "timeline": all_timeline,
            "findings": all_findings,
        }
