from typing import Any

class CrossModalCorrelator:
    @staticmethod
    def correlate(timeline_events: list[dict[str, Any]], window_sec: float = 0.6) -> list[dict[str, Any]]:
        """
        Identify time windows where both video and audio anomalies coincide.
        Coinciding anomalies exponentially increase forensic significance.
        """
        video_events = [e for e in timeline_events if e.get("detector", "").startswith("video")]
        audio_events = [e for e in timeline_events if e.get("detector", "").startswith("audio")]

        correlated = []
        for v in video_events:
            v_start, v_end = v["start_time"], v["end_time"]
            v_mid = (v_start + v_end) / 2.0

            for a in audio_events:
                a_start, a_end = a["start_time"], a["end_time"]
                a_mid = (a_start + a_end) / 2.0

                if abs(v_mid - a_mid) <= window_sec:
                    combined_start = min(v_start, a_start)
                    combined_end = max(v_end, a_end)
                    v_conf = v.get("confidence", 0.8)
                    a_conf = a.get("confidence", 0.8)
                    corr_score = min(0.98, 0.5 + (v_conf + a_conf) * 0.25)

                    correlated.append({
                        "id": f"corr_{int(combined_start*10)}_{int(combined_end*10)}",
                        "start_time": round(combined_start, 2),
                        "end_time": round(combined_end, 2),
                        "event_type": "cross_modal_correlation",
                        "severity": "critical",
                        "detector": "cross_modal_engine",
                        "confidence": round(corr_score, 2),
                        "description": f"Cross-modal anomaly: Video {v['event_type']} aligns with Audio {a['event_type']} at {combined_start:.1f}s-{combined_end:.1f}s.",
                        "video_event": v,
                        "audio_event": a,
                    })

        return correlated
