import io
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.config import settings

class ForensicPdfReportGenerator:
    @staticmethod
    def generate(report_data: dict) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        
        # Custom styles with cyber-forensic color palette
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            fontName="Helvetica-Bold",
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#0284c7"),
            fontName="Helvetica-Bold",
        )
        h2_style = ParagraphStyle(
            "H2",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10,
            spaceAfter=4,
            fontName="Helvetica-Bold",
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#334155"),
        )
        mono_style = ParagraphStyle(
            "Mono",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#0284c7"),
            fontName="Courier",
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#64748b"),
        )

        elements = []

        # 1. Header
        elements.append(Paragraph("EVIDENCEGUARD · FORENSIC INVESTIGATION REPORT", subtitle_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"Case: {report_data.get('investigation', 'Digital Evidence Analysis')}", title_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"Generated: {report_data.get('generatedAt', '')} · System: {report_data.get('generator', 'EvidenceGuard')}", body_style))
        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=12))

        # 2. Executive Summary & Assessment
        assessment = report_data.get("assessment") or {}
        classification = assessment.get("classification", "INCONCLUSIVE")
        integrity_score = assessment.get("integrity_score", 50.0)
        tamper_likelihood = assessment.get("tampering_likelihood", 0.5)
        confidence = assessment.get("confidence", 0.8)

        # Badge color based on classification
        badge_bg = colors.HexColor("#dcfce7") if "NO SIGNIFICANT" in classification else (
            colors.HexColor("#fef3c7") if "LOW" in classification or "MODERATE" in classification else colors.HexColor("#fee2e2")
        )
        badge_txt = colors.HexColor("#166534") if "NO SIGNIFICANT" in classification else (
            colors.HexColor("#92400e") if "LOW" in classification or "MODERATE" in classification else colors.HexColor("#991b1b")
        )

        assessment_table_data = [
            [
                Paragraph("<b>FORENSIC ASSESSMENT</b>", body_style),
                Paragraph(f"<b>{classification}</b>", ParagraphStyle("B", parent=body_style, textColor=badge_txt, fontName="Helvetica-Bold", fontSize=10)),
            ],
            [
                Paragraph("Integrity Score", body_style),
                Paragraph(f"<b>{integrity_score} / 100</b>", body_style),
            ],
            [
                Paragraph("Tampering Likelihood", body_style),
                Paragraph(f"<b>{tamper_likelihood * 100:.1f}%</b>", body_style),
            ],
            [
                Paragraph("Confidence Level", body_style),
                Paragraph(f"<b>{confidence * 100:.1f}%</b>", body_style),
            ],
            [
                Paragraph("Synthesis", body_style),
                Paragraph(assessment.get("summary", "Analysis completed."), body_style),
            ],
        ]

        t_assess = Table(assessment_table_data, colWidths=[150, 390])
        t_assess.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("BACKGROUND", (1, 0), (1, 0), badge_bg),
        ]))
        elements.append(t_assess)
        elements.append(Spacer(1, 12))

        # 3. Evidence Provenance & Cryptographic Hashes
        ev = report_data.get("evidence", {})
        elements.append(Paragraph("Evidence Provenance & Cryptographic Integrity", h2_style))
        
        evidence_table_data = [
            [Paragraph("Evidence Identifier", body_style), Paragraph(f"<b>{ev.get('id', '')}</b>", body_style)],
            [Paragraph("Original Filename", body_style), Paragraph(ev.get("filename", ""), body_style)],
            [Paragraph("File Size", body_style), Paragraph(f"{ev.get('sizeBytes', 0):,} bytes", body_style)],
            [Paragraph("Media Container", body_style), Paragraph(str(ev.get("container", "")).upper(), body_style)],
            [Paragraph("SHA-256 Digest", body_style), Paragraph(ev.get("sha256", ""), mono_style)],
            [Paragraph("Registration Timestamp", body_style), Paragraph(ev.get("registeredAt", ""), body_style)],
        ]
        
        t_ev = Table(evidence_table_data, colWidths=[150, 390])
        t_ev.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_ev)
        elements.append(Spacer(1, 12))

        # 4. Factual Observations vs Model Inferences
        elements.append(Paragraph("Factual Observations vs. Forensic Inferences", h2_style))
        obs_text = (
            "<b>Distinction Notice:</b> Forensic authenticity verification systematically distinguishes raw mathematical observations "
            "(byte hashes, header fields, DCT coefficients, spectral flux) from investigative inferences. Statistical anomalies "
            "indicate candidate editing regions or processing history, not legal proof of malicious intent."
        )
        elements.append(Paragraph(obs_text, disclaimer_style))
        elements.append(Spacer(1, 8))

        # 5. Forensic Detector Results
        elements.append(Paragraph("Forensic Detector Evaluation Matrix", h2_style))
        checks = report_data.get("checks", [])
        
        check_table_data = [[
            Paragraph("<b>Detector</b>", body_style),
            Paragraph("<b>Status</b>", body_style),
            Paragraph("<b>Findings & Mathematical Observations</b>", body_style),
        ]]

        for c in checks:
            state = c.get("state", "passed").upper()
            st_color = colors.HexColor("#166534") if state == "PASSED" else (
                colors.HexColor("#92400e") if state in ["WARNING", "INCONCLUSIVE"] else colors.HexColor("#991b1b")
            )
            check_table_data.append([
                Paragraph(f"<b>{c.get('name', '')}</b>", body_style),
                Paragraph(f"<b>{state}</b>", ParagraphStyle("ST", parent=body_style, textColor=st_color)),
                Paragraph(c.get("summary", ""), body_style),
            ])

        t_checks = Table(check_table_data, colWidths=[140, 70, 330])
        t_checks.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_checks)
        elements.append(Spacer(1, 12))

        # 6. Embed Visual Artifacts (if present on disk)
        artifacts_to_embed = []
        for c in checks:
            artifact_rel = c.get("artifact")
            if artifact_rel and artifact_rel.startswith("/artifacts/"):
                artifact_filename = artifact_rel.replace("/artifacts/", "")
                artifact_path = settings.ARTIFACTS_DIR / artifact_filename
                if artifact_path.exists():
                    artifacts_to_embed.append((c.get("name", "Forensic Artifact"), artifact_path))

        if artifacts_to_embed:
            elements.append(Paragraph("Forensic Visual Artifacts", h2_style))
            for name, art_path in artifacts_to_embed:
                try:
                    elements.append(Paragraph(f"<b>Figure:</b> {name}", body_style))
                    elements.append(Spacer(1, 4))
                    elements.append(RLImage(str(art_path), width=350, height=140))
                    elements.append(Spacer(1, 8))
                except Exception:
                    pass

        # 7. Forensic Timeline (if applicable)
        timeline = report_data.get("timeline", [])
        if timeline:
            elements.append(Paragraph("Forensic Timeline & Temporal Discontinuities", h2_style))
            t_data = [[
                Paragraph("<b>Time Range</b>", body_style),
                Paragraph("<b>Event Type</b>", body_style),
                Paragraph("<b>Severity</b>", body_style),
                Paragraph("<b>Description</b>", body_style),
            ]]
            for ev_t in timeline[:10]:
                t_data.append([
                    Paragraph(f"{ev_t.get('start_time', 0):.2f}s - {ev_t.get('end_time', 0):.2f}s", body_style),
                    Paragraph(ev_t.get("event_type", ""), body_style),
                    Paragraph(ev_t.get("severity", "").upper(), body_style),
                    Paragraph(ev_t.get("description", ""), body_style),
                ])
            t_timeline = Table(t_data, colWidths=[90, 110, 60, 280])
            t_timeline.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(t_timeline)
            elements.append(Spacer(1, 12))

        # 8. Limitations & Methodology
        elements.append(Paragraph("Limitations & Scientific Scope", h2_style))
        limits = report_data.get("limitations", [
            "Forensic checks calculate mathematical and statistical indicators; results do not guarantee intent.",
            "SHA-256 match proves byte equality; a mismatch proves byte divergence without identifying the author.",
            "All analysis performed using verifiable, deterministic signal algorithms with full audit provenance.",
        ])
        for l in limits:
            elements.append(Paragraph(f"• {l}", disclaimer_style))
        elements.append(Spacer(1, 14))

        # 9. Sign-off block
        sign_block = [
            [
                Paragraph("<b>Forensic Examiner Attestation:</b><br/>I hereby certify that this analysis was conducted using validated forensic tools without unauthorized modification of source bytes.", disclaimer_style),
                Paragraph("<b>Signature:</b> ___________________________<br/><b>Date:</b> " + report_data.get("generatedAt", "")[:10], disclaimer_style),
            ]
        ]
        t_sign = Table(sign_block, colWidths=[340, 200])
        t_sign.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(KeepTogether(t_sign))

        # Build document
        doc.build(elements)
        return buf.getvalue()

pdf_generator = ForensicPdfReportGenerator()
