from pydantic import BaseModel

class DashboardStats(BaseModel):
    total_evidence: int
    images_analyzed: int
    videos_analyzed: int
    audio_analyzed: int
    high_suspicion_cases: int
    pending_analyses: int
    completed_analyses: int
    audit_events_count: int
    chain_intact: bool
