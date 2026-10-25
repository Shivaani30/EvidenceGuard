from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    size = Column(Integer, nullable=False)
    kind = Column(String(50), nullable=False, index=True)
    sha256 = Column(String(64), nullable=False, index=True)
    sha512 = Column(String(128), nullable=True)
    mime = Column(String(100), nullable=True)
    file_path = Column(String(500), nullable=False)
    preview_path = Column(Text, nullable=True)
    registered_at = Column(String(50), default=lambda: datetime.now(timezone.utc).isoformat())
    is_reference = Column(Boolean, default=False)
    case_name = Column(String(255), default="Untitled investigation", index=True)
    reference_id = Column(String(50), ForeignKey("evidence.id"), nullable=True)
    job_status = Column(String(50), default="idle")
    assessment = Column(JSON, nullable=True)

    # Relationships
    checks = relationship("DetectorResult", back_populates="evidence", cascade="all, delete-orphan")
    findings = relationship("ForensicFinding", back_populates="evidence", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="evidence", cascade="all, delete-orphan")
    jobs = relationship("AnalysisJob", back_populates="evidence", cascade="all, delete-orphan")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(String(50), primary_key=True, index=True)
    evidence_id = Column(String(50), ForeignKey("evidence.id"), nullable=False, index=True)
    status = Column(String(50), default="idle")  # idle, running, completed, failed
    progress = Column(Integer, default=0)
    stage = Column(String(100), default="Queued")
    message = Column(Text, default="Analysis queued")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    evidence = relationship("Evidence", back_populates="jobs")


class DetectorResult(Base):
    __tablename__ = "detector_results"

    id = Column(String(100), primary_key=True)  # composite like f"{evidence_id}_{detector}"
    evidence_id = Column(String(50), ForeignKey("evidence.id"), nullable=False, index=True)
    check_id = Column(String(50), nullable=False)  # e.g. "metadata", "ela", "compression", "wav"
    name = Column(String(150), nullable=False)
    state = Column(String(50), default="pending")  # passed, failed, warning, inconclusive, skipped, unavailable, running, error, pending
    summary = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    artifact = Column(Text, nullable=True)  # URL or path to artifact image
    score = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)

    evidence = relationship("Evidence", back_populates="checks")


class ForensicFinding(Base):
    __tablename__ = "forensic_findings"

    id = Column(String(50), primary_key=True, index=True)
    evidence_id = Column(String(50), ForeignKey("evidence.id"), nullable=False, index=True)
    detector = Column(String(100), nullable=False)
    severity = Column(String(50), default="medium")  # low, medium, high, critical
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(JSON, nullable=True)  # e.g. {bbox: [...]} or {frame_range: [10, 20]} or {time_range: [1.2, 3.4]}
    confidence = Column(Float, default=1.0)

    evidence = relationship("Evidence", back_populates="findings")


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(String(50), primary_key=True, index=True)
    evidence_id = Column(String(50), ForeignKey("evidence.id"), nullable=False, index=True)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    event_type = Column(String(100), nullable=False)  # duplicate_frames, audio_splice, timestamp_jump, av_correlation
    severity = Column(String(50), default="medium")
    detector = Column(String(100), nullable=False)
    confidence = Column(Float, default=1.0)
    description = Column(Text, nullable=False)

    evidence = relationship("Evidence", back_populates="timeline_events")
