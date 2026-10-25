from typing import Any

class ConsensusGraphBuilder:
    @staticmethod
    def build(
        evidence_id: str,
        evidence_name: str,
        detector_results: list[dict[str, Any]],
        findings: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Construct a Forensic Consensus Graph demonstrating the causal chain of evidence."""
        nodes = []
        edges = []

        # Root Node: Evidence Artifact
        nodes.append({
            "id": "root",
            "label": f"Evidence: {evidence_name}",
            "type": "evidence",
            "severity": "neutral",
        })

        # Detector Nodes
        for d in detector_results:
            d_id = f"det_{d['id']}"
            nodes.append({
                "id": d_id,
                "label": d["name"],
                "type": "detector",
                "state": d["state"],
                "severity": "high" if d["state"] in ["failed", "error"] else ("medium" if d["state"] == "warning" else "low"),
            })
            edges.append({
                "source": "root",
                "target": d_id,
                "relationship": "evaluated_by",
            })

        # Finding Nodes
        for idx, f in enumerate(findings):
            f_id = f"find_{idx}"
            nodes.append({
                "id": f_id,
                "label": f["title"],
                "type": "finding",
                "severity": f.get("severity", "medium"),
                "description": f.get("description", ""),
            })
            # Link finding to its detector
            det_id = f"det_{f['detector']}"
            edges.append({
                "source": det_id,
                "target": f_id,
                "relationship": "flags",
            })

        # Timeline / Correlated Event Nodes
        for idx, t in enumerate(timeline):
            t_id = f"time_{idx}"
            nodes.append({
                "id": t_id,
                "label": f"Time {t['start_time']}s-{t['end_time']}s: {t['event_type']}",
                "type": "temporal_event",
                "severity": t.get("severity", "medium"),
            })
            det_id = f"det_{t['detector']}"
            edges.append({
                "source": det_id,
                "target": t_id,
                "relationship": "occurs_at",
            })

        return {"nodes": nodes, "edges": edges}
