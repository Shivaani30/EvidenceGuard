import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import WebSocket
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.evidence import Evidence, AnalysisJob, DetectorResult, ForensicFinding, TimelineEvent
from app.forensics.pipeline import ForensicPipeline
from app.services.audit_service import audit_service

executor = ThreadPoolExecutor(max_workers=4)

class JobService:
    def __init__(self):
        # WebSocket subscriber registry: evidence_id -> set of active WebSockets
        self.subscribers: dict[str, set[WebSocket]] = {}

    def register_ws(self, evidence_id: str, ws: WebSocket):
        if evidence_id not in self.subscribers:
            self.subscribers[evidence_id] = set()
        self.subscribers[evidence_id].add(ws)

    def unregister_ws(self, evidence_id: str, ws: WebSocket):
        if evidence_id in self.subscribers:
            self.subscribers[evidence_id].discard(ws)
            if not self.subscribers[evidence_id]:
                del self.subscribers[evidence_id]

    async def broadcast_progress(self, evidence_id: str, data: dict[str, Any]):
        """Send live progress JSON message to all connected WebSockets for this evidence."""
        if evidence_id in self.subscribers:
            dead_ws = set()
            for ws in list(self.subscribers[evidence_id]):
                try:
                    await ws.send_json(data)
                except Exception:
                    dead_ws.add(ws)
            for ws in dead_ws:
                self.subscribers[evidence_id].discard(ws)

    def run_analysis_sync(
        self,
        evidence_id: str,
        selected_checks: list[str],
        reference_hash: str | None,
        loop: asyncio.AbstractEventLoop | None,
    ):
        """Synchronous worker executed in thread pool."""
        db = SessionLocal()
        try:
            ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
            if not ev:
                return

            ev.job_status = "running"
            job = db.query(AnalysisJob).filter(AnalysisJob.evidence_id == evidence_id).first()
            if not job:
                job = AnalysisJob(
                    id=f"job_{evidence_id}",
                    evidence_id=evidence_id,
                    status="running",
                    progress=0,
                    stage="Queued",
                    message="Analysis initialized",
                )
                db.add(job)
            else:
                job.status = "running"
                job.progress = 0
                job.stage = "Queued"
            db.commit()

            # Clear old checks/findings for this run if re-analyzing
            db.query(DetectorResult).filter(DetectorResult.evidence_id == evidence_id).delete()
            db.query(ForensicFinding).filter(ForensicFinding.evidence_id == evidence_id).delete()
            db.query(TimelineEvent).filter(TimelineEvent.evidence_id == evidence_id).delete()
            db.commit()

            def progress_callback(progress: int, stage: str, message: str):
                # Update DB job
                job.progress = progress
                job.stage = stage
                job.message = message
                db.commit()

                # Notify WebSockets asynchronously if event loop is running
                if loop and loop.is_running():
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self.broadcast_progress(
                                evidence_id,
                                {
                                    "evidence_id": evidence_id,
                                    "progress": progress,
                                    "stage": stage,
                                    "message": message,
                                },
                            ),
                            loop,
                        )
                    except Exception:
                        pass

            # Execute pipeline
            outputs, assessment = ForensicPipeline.execute(
                file_path=Path(ev.file_path),
                evidence_id=evidence_id,
                kind=ev.kind,
                selected_checks=selected_checks,
                reference_hash=reference_hash,
                progress_callback=progress_callback,
            )

            # Save DetectorResults
            for out in outputs:
                det_res = DetectorResult(
                    id=f"{evidence_id}_{out.check_id}",
                    evidence_id=evidence_id,
                    check_id=out.check_id,
                    name=out.name,
                    state=out.state,
                    summary=out.summary,
                    details=out.details,
                    artifact=out.artifact,
                    score=out.score,
                    confidence=out.confidence,
                )
                db.add(det_res)
                # Audit completed check
                audit_service.log(db, "check.completed", f"{evidence_id} {out.check_id}={out.state}")

            # Save Findings
            for idx, f in enumerate(assessment.get("findings", [])):
                finding_db = ForensicFinding(
                    id=f"f_{evidence_id}_{idx}",
                    evidence_id=evidence_id,
                    detector=f.get("detector", "fusion"),
                    severity=f.get("severity", "medium"),
                    title=f.get("title", "Forensic Finding"),
                    description=f.get("description", ""),
                    location=f.get("location"),
                    confidence=f.get("confidence", 1.0),
                )
                db.add(finding_db)

            # Save Timeline Events
            for idx, t in enumerate(assessment.get("timeline", [])):
                time_db = TimelineEvent(
                    id=f"t_{evidence_id}_{idx}",
                    evidence_id=evidence_id,
                    start_time=t.get("start_time", 0.0),
                    end_time=t.get("end_time", 0.0),
                    event_type=t.get("event_type", "event"),
                    severity=t.get("severity", "medium"),
                    detector=t.get("detector", "fusion"),
                    confidence=t.get("confidence", 1.0),
                    description=t.get("description", ""),
                )
                db.add(time_db)

            # Update Evidence & Job Status
            ev.assessment = assessment
            ev.job_status = "done"
            job.status = "completed"
            job.progress = 100
            job.stage = "Completed"
            job.message = "Analysis complete"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

            # Final broadcast
            if loop and loop.is_running():
                try:
                    asyncio.run_coroutine_threadsafe(
                        self.broadcast_progress(
                            evidence_id,
                            {
                                "evidence_id": evidence_id,
                                "progress": 100,
                                "stage": "completed",
                                "message": "Analysis complete",
                                "status": "completed",
                            },
                        ),
                        loop,
                    )
                except Exception:
                    pass

        except Exception as e:
            if "job" in locals() and job:
                job.status = "failed"
                job.message = f"Job failed: {str(e)}"
            if "ev" in locals() and ev:
                ev.job_status = "done"
            db.commit()
            if loop and loop.is_running():
                try:
                    asyncio.run_coroutine_threadsafe(
                        self.broadcast_progress(
                            evidence_id,
                            {
                                "evidence_id": evidence_id,
                                "progress": 100,
                                "stage": "failed",
                                "message": f"Error: {str(e)}",
                                "status": "failed",
                            },
                        ),
                        loop,
                    )
                except Exception:
                    pass
        finally:
            db.close()

    def start_job(
        self,
        evidence_id: str,
        selected_checks: list[str],
        reference_hash: str | None = None,
    ):
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None

        executor.submit(
            self.run_analysis_sync,
            evidence_id,
            selected_checks,
            reference_hash,
            loop,
        )

job_service = JobService()
