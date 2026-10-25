from abc import ABC, abstractmethod
from typing import Any
from pathlib import Path

class DetectorOutput:
    def __init__(
        self,
        check_id: str,
        name: str,
        state: str,  # passed, failed, warning, inconclusive, skipped, unavailable, error
        summary: str,
        details: dict[str, Any] | None = None,
        artifact: str | None = None,
        score: float | None = None,
        confidence: float | None = None,
        findings: list[dict[str, Any]] | None = None,
        timeline_events: list[dict[str, Any]] | None = None,
    ):
        self.check_id = check_id
        self.name = name
        self.state = state
        self.summary = summary
        self.details = details or {}
        self.artifact = artifact
        self.score = score
        self.confidence = confidence if confidence is not None else 1.0
        self.findings = findings or []
        self.timeline_events = timeline_events or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.check_id,
            "name": self.name,
            "state": self.state,
            "summary": self.summary,
            "details": self.details,
            "artifact": self.artifact,
            "score": self.score,
            "confidence": self.confidence,
        }

class BaseDetector(ABC):
    check_id: str
    name: str

    @abstractmethod
    def run(self, file_path: Path, evidence_id: str, **kwargs) -> DetectorOutput:
        pass
