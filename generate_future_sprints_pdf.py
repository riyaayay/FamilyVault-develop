import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas providing 'Page X of Y' numbering and running header/footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(36, 756, getattr(self, "_doc_header_title", "FamilyVault — Master Deliverables Blueprint"))
            self.setFont("Helvetica", 8)
            self.drawRightString(576, 756, "Confidential • Internal Team Blueprint")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(36, 748, 576, 748)
        
        # Footer
        self.setFont("Helvetica", 8)
        self.drawString(36, 25, "FamilyVault Generational Operating System • Lead Architect: Runeet (realruneett01)")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(576, 25, page_text)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 35, 576, 35)
        self.restoreState()


def get_styles():
    styles = getSampleStyleSheet()
    PRIMARY = colors.HexColor("#0f172a")       # Slate 900
    SECONDARY = colors.HexColor("#1e293b")     # Slate 800
    BLUE_DARK = colors.HexColor("#1d4ed8")     # Blue 700
    EMERALD_DARK = colors.HexColor("#047857")  # Emerald 700
    AMBER_DARK = colors.HexColor("#b45309")    # Amber 700
    TEXT_MUTED = colors.HexColor("#64748b")    # Slate 500

    return {
        "title": ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=PRIMARY, spaceAfter=2),
        "subtitle": ParagraphStyle('DocSubtitle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=11.5, textColor=TEXT_MUTED, spaceAfter=5),
        "h1": ParagraphStyle('SectionH1', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=PRIMARY, spaceBefore=6, spaceAfter=3, keepWithNext=True),
        "h2": ParagraphStyle('SectionH2', parent=styles['Heading3'], fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=SECONDARY, spaceBefore=4, spaceAfter=2, keepWithNext=True),
        "body": ParagraphStyle('DocBody', parent=styles['Normal'], fontName='Helvetica', fontSize=7.6, leading=10.2, textColor=SECONDARY),
        "cell": ParagraphStyle('TableCell', parent=styles['Normal'], fontName='Helvetica', fontSize=6.8, leading=8.8, textColor=SECONDARY),
        "cell_bold": ParagraphStyle('TableCellBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=6.8, leading=8.8, textColor=SECONDARY),
        "cell_hdr": ParagraphStyle('TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.0, leading=9.2, textColor=colors.white),
        "badge_done": ParagraphStyle('BadgeDone', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=6.5, leading=8.0, textColor=EMERALD_DARK),
        "badge_prog": ParagraphStyle('BadgeProg', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=6.5, leading=8.0, textColor=AMBER_DARK),
        "badge_ready": ParagraphStyle('BadgeReady', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=6.5, leading=8.0, textColor=BLUE_DARK),
    }


def build_sprint_4_pdf(filename="FamilyVault_Sprint_4_Master_Workflow.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=45)
    st = get_styles()
    story = []

    # Title & Subtitle
    story.append(Paragraph("FamilyVault — Sprint 4 Master Workflow", st["title"]))
    story.append(Paragraph(
        "Media Ingestion, Multi-Face Clustering & Cultural Kinship • Serial Deliverable Blueprint • "
        f"Generated {datetime.now().strftime('%B %d, %Y')} • Branch: develop", st["subtitle"]
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=6))

    # Architecture Overview Callout
    meta_table = Table([
        [
            Paragraph("<b>Sprint Theme:</b> AI Media Intelligence & Kinship", st["cell"]),
            Paragraph("<b>Lead Architect:</b> Runeet (realruneett01)", st["cell"]),
            Paragraph("<b>Target Branch:</b> develop", st["cell"])
        ],
        [
            Paragraph("<b>Key AI Models:</b> InsightFace ArcFace 512D", st["cell"]),
            Paragraph("<b>Storage:</b> Cloudflare R2 Presigned URLs", st["cell"]),
            Paragraph("<b>Graph Engine:</b> Neo4j Cypher Traversal", st["cell"])
        ]
    ], colWidths=[180, 180, 180])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph("1. Executive Summary & Sprint Objectives", st["h1"]))
    story.append(Paragraph(
        "Sprint 4 establishes automated AI media intelligence, multi-person facial recognition, and dynamic cultural kinship. "
        "Group photos uploaded to Cloudflare R2 are processed via InsightFace ArcFace 512D embeddings and matched against known Vance Clan member face banks. "
        "Matches with cosine similarity &ge; 0.85 are auto-tagged to generational member timelines, while ambiguous or multi-person matches are queued "
        "in the Household Media Inbox for head review with interactive bounding boxes and confidence meters. "
        "Simultaneously, the Graph Service calculates deep Indian cultural kinship terms (Chacha, Tauji, Mama, Bua, Masi) and renders glowing traversal paths.",
        st["body"]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("2. Master Chronological Deliverables Sequence by Owner (Serial Dependency Chain)", st["h1"]))
    story.append(Paragraph(
        "Each deliverable is executed in strict sequence: completion of deliverable N unlocks deliverable N+1. "
        "Below is the exact execution chain across Core Backend, Biometrics, Frontend, Graph, and QA:",
        st["body"]
    ))
    story.append(Spacer(1, 4))

    # Deliverables Table
    headers = [
        Paragraph("Deliverable & Owner", st["cell_hdr"]),
        Paragraph("Preceding Work (Must Be Done First)", st["cell_hdr"]),
        Paragraph("Scope & Technical Work Executed", st["cell_hdr"]),
        Paragraph("Output Artifact / Contract", st["cell_hdr"]),
        Paragraph("Next Owner & Work Triggered", st["cell_hdr"]),
        Paragraph("Status", st["cell_hdr"]),
    ]
    rows = [
        [
            Paragraph("<b>Deliverable 1</b><br/><b>Runeet</b><br/><i>Core Backend Lead</i>", st["cell"]),
            Paragraph("PostgreSQL schema with media_contributions table.", st["cell"]),
            Paragraph("Builds Core Media schemas, registration endpoint <code>POST /api/v1/media/</code>, and timeline query <code>GET /api/v1/media/timeline/{id}</code> with strict RLS.", st["cell"]),
            Paragraph("<code>backend/app/schemas/media.py</code><br/><code>endpoints/media.py</code>", st["cell"]),
            Paragraph("<b>Ayushman</b> (Biometrics)<br/>Triggered to connect multi-face detection.", st["cell"]),
            Paragraph("<b>COMPLETED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Deliverable 2</b><br/><b>Ayushman</b><br/><i>Biometrics Lead</i>", st["cell"]),
            Paragraph("<b>Deliverable 1</b><br/>(Runeet's media schema & R2 presigned upload pipeline).", st["cell"]),
            Paragraph("Extends InsightFace 512D ArcFace pipeline to extract multi-face embeddings from group photos, evaluating cosine similarity against Vance Clan face banks (&ge;0.85).", st["cell"]),
            Paragraph("<code>biometrics/face_processor.py</code><br/><code>biometrics/main.py</code>", st["cell"]),
            Paragraph("<b>Runeet</b> (Core Backend)<br/>Triggered to build Single & Batch Triage API.", st["cell"]),
            Paragraph("<b>COMPLETED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Deliverable 3</b><br/><b>Runeet</b><br/><i>Core Backend Lead</i>", st["cell"]),
            Paragraph("<b>Deliverable 2</b><br/>(Ayushman's biometric match response contract).", st["cell"]),
            Paragraph("Builds <code>PATCH /api/v1/media/{id}/triage</code> and <code>POST /api/v1/media/batch-triage</code> endpoints with status transitions and audit logging (approved_by).", st["cell"]),
            Paragraph("<code>endpoints/media.py</code><br/><code>test_sprint4_and_sprint5.py</code>", st["cell"]),
            Paragraph("<b>Raghuvendra</b> (Dashboard UI)<br/>Triggered to wire live media inbox UI.", st["cell"]),
            Paragraph("<b>COMPLETED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Deliverable 4</b><br/><b>Raghuvendra</b><br/><i>Dashboard Frontend</i>", st["cell"]),
            Paragraph("<b>Deliverable 3</b><br/>(Runeet's triage endpoints and Ayushman's inbox API).", st["cell"]),
            Paragraph("Builds <code>/dashboard/inbox</code> with multi-select checkboxes, bounding box SVG overlays, color-coded confidence meters, and single/batch triage action buttons.", st["cell"]),
            Paragraph("<code>inbox/inbox-grid.tsx</code><br/><code>lib/media-inbox.ts</code>", st["cell"]),
            Paragraph("<b>Riya</b> (Graph Service Lead)<br/>Triggered to supply kinship badges.", st["cell"]),
            Paragraph("<b>COMPLETED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Deliverable 5</b><br/><b>Riya</b><br/><i>Graph Service Lead</i>", st["cell"]),
            Paragraph("Seeded Neo4j graph and Vance Clan relationships.", st["cell"]),
            Paragraph("Implements dynamic cultural kinship deduction (<code>GET /api/graph/kinship</code>) resolving Indian terminology (Chacha, Tauji, Mama, Bua, Masi) and paradox validation.", st["cell"]),
            Paragraph("<code>graph-service/kinship.py</code><br/><code>api/graph/kinship</code>", st["cell"]),
            Paragraph("<b>Anushka</b> (Tree Frontend)<br/>Triggered to render kinship glowing path.", st["cell"]),
            Paragraph("<b>COMPLETED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Deliverable 6</b><br/><b>Anushka</b><br/><i>Tree Frontend Engineer</i>", st["cell"]),
            Paragraph("<b>Deliverable 5</b><br/>(Riya's dynamic cultural kinship endpoint).", st["cell"]),
            Paragraph("Wires cultural kinship endpoint to React Flow canvas; clicking any two members calculates relationship and highlights genealogical traversal path with glowing SVG edges.", st["cell"]),
            Paragraph("<code>KinshipPathGlow.tsx</code><br/><code>dashboard/family/page.tsx</code>", st["cell"]),
            Paragraph("<b>Ayush</b> (Security & QA)<br/>Triggered to run biometric test suite.", st["cell"]),
            Paragraph("<b>COMPLETED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Deliverable 7</b><br/><b>Ayush</b><br/><i>Security & QA Lead</i>", st["cell"]),
            Paragraph("<b>Deliverables 1 to 6</b><br/>(All services operational).", st["cell"]),
            Paragraph("Executes automated edge-case test suite verifying 0-face landscape photos, multi-face group reunions, threshold boundary conditions (0.849 vs 0.850), and persistence invariance.", st["cell"]),
            Paragraph("<code>test_biometric_edgecases.py</code><br/>5/5 Tests Passed (100%)", st["cell"]),
            Paragraph("<b>Entire Team</b><br/>Sprint 4 Deliverables Verified & Closed.", st["cell"]),
            Paragraph("<b>COMPLETED</b>", st["badge_done"]),
        ],
    ]

    t = Table([headers] + rows, colWidths=[90, 85, 155, 95, 80, 35])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. Sprint 4 Quality Gate Sign-Off", st["h1"]))
    story.append(Paragraph(
        "<b>Certification:</b> All 7 deliverables have met 100% acceptance criteria. "
        "Multi-face biometric recognition operates at &ge; 0.85 cosine precision, the inbox batch triage functions transactionally, "
        "and cultural kinship traversal renders with zero cyclic paradoxes.<br/>"
        "<b>Signed:</b> Runeet (Lead Architect & Core Backend) • Ayush (Lead QA)", st["body"]
    ))

    def on_first(c, d):
        c._doc_header_title = "FamilyVault — Sprint 4 Master Workflow Blueprint"
    doc.build(story, canvasmaker=NumberedCanvas, onFirstPage=on_first)
    print(f"[OK] Generated {filename}")


def build_sprint_5_pdf(filename="FamilyVault_Sprint_5_Master_Workflow.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=45)
    st = get_styles()
    story = []

    # Title & Subtitle
    story.append(Paragraph("FamilyVault — Sprint 5 Master Workflow", st["title"]))
    story.append(Paragraph(
        "Milestone Time Capsules, Multi-Trustee Governance & Emergency Red Alert • Serial Deliverable Blueprint • "
        f"Generated {datetime.now().strftime('%B %d, %Y')} • Branch: develop", st["subtitle"]
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=6))

    # Architecture Overview Callout
    meta_table = Table([
        [
            Paragraph("<b>Sprint Theme:</b> Milestone Governance & Red Alert", st["cell"]),
            Paragraph("<b>Lead Architect:</b> Runeet (realruneett01)", st["cell"]),
            Paragraph("<b>Target Branch:</b> develop", st["cell"])
        ],
        [
            Paragraph("<b>Security:</b> Three-Tier Row Level Security (RLS)", st["cell"]),
            Paragraph("<b>Verification:</b> Cryptographic SHA-256 Hashes", st["cell"]),
            Paragraph("<b>Governance:</b> Multi-Trustee Quorum Signatures", st["cell"])
        ]
    ], colWidths=[180, 180, 180])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph("1. Executive Summary & Sprint Objectives", st["h1"]))
    story.append(Paragraph(
        "Sprint 5 operationalizes generational legacy security and life-saving emergency medical response: "
        "(1) Milestone-locked time capsules and digital wills remain cryptographically sealed until a scheduled timestamp or multi-trustee quorum is fulfilled. "
        "(2) Multi-trustee sign-off API (<code>POST /api/v1/vault/{id}/sign</code>) records verified signatures and unlocks the capsule when quorum is met. "
        "(3) The Emergency Red Alert Protocol instantly compiles Eleanor Vance's critical health telemetry (pacemaker specifications, contraindicated allergies) "
        "and exposes a 24-hour verifiable offline pass (<code>GET /api/v1/health/emergency-pass/{token}</code>) with an active broadcast trigger.",
        st["body"]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("2. Master Chronological Deliverables Sequence by Owner (Serial Dependency Chain)", st["h1"]))
    story.append(Paragraph(
        "Each deliverable is executed in strict sequence: completion of deliverable N unlocks deliverable N+1. "
        "Below is the exact execution chain across Core Backend, Tree Frontend, Dashboard UI, Graph, and Security:",
        st["body"]
    ))
    story.append(Spacer(1, 4))

    headers = [
        Paragraph("Deliverable & Owner", st["cell_hdr"]),
        Paragraph("Preceding Work (Must Be Done First)", st["cell_hdr"]),
        Paragraph("Scope & Technical Work Executed", st["cell_hdr"]),
        Paragraph("Output Artifact / Contract", st["cell_hdr"]),
        Paragraph("Next Owner & Work Triggered", st["cell_hdr"]),
        Paragraph("Status", st["cell_hdr"]),
    ]
    rows = [
        [
            Paragraph("<b>Deliverable 1</b><br/><b>Runeet</b><br/><i>Core Backend Lead</i>", st["cell"]),
            Paragraph("PostgreSQL schema with documents table and time_capsule_status enum.", st["cell"]),
            Paragraph("Builds milestone time capsule engine: timestamp unlock triggers, multi-trustee sign-off endpoint <code>POST /api/v1/vault/{id}/sign</code>, and badge query API <code>GET /api/v1/vault/milestones/badges</code>.", st["cell"]),
            Paragraph("<code>endpoints/vault.py</code><br/><code>schemas/document.py</code>", st["cell"]),
            Paragraph("<b>Runeet</b> (Core Backend)<br/>Triggered to build Emergency Pass & Alert API.", st["cell"]),
            Paragraph("<b>COMPLETED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Deliverable 2</b><br/><b>Runeet</b><br/><i>Core Backend Lead</i>", st["cell"]),
            Paragraph("Eleanor Vance emergency medical profile and SHA-256 tamper hash.", st["cell"]),
            Paragraph("Implements scannable 24-hour Emergency Telemetry Pass <code>GET /api/v1/health/emergency-pass/{token}</code> with HMAC/SHA-256 verification and Red Alert Broadcast trigger.", st["cell"]),
            Paragraph("<code>endpoints/health.py</code><br/><code>test_sprint4_and_sprint5.py</code>", st["cell"]),
            Paragraph("<b>Anushka</b> (Tree Frontend)<br/>Triggered to render milestone & alert UI.", st["cell"]),
            Paragraph("<b>COMPLETED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Deliverable 3</b><br/><b>Anushka</b><br/><i>Tree Frontend Engineer</i>", st["cell"]),
            Paragraph("<b>Deliverables 1 & 2</b><br/>(Runeet's milestone badge metadata & emergency pass API).", st["cell"]),
            Paragraph("Implements <code>MilestoneNodeBadge.tsx</code> and <code>EmergencyAlertOverlay.tsx</code> on the family tree canvas. Members with locked items show lock pills with signature progress (1/2); distress triggers red beacon.", st["cell"]),
            Paragraph("<code>MilestoneNodeBadge.tsx</code><br/><code>EmergencyAlertOverlay.tsx</code>", st["cell"]),
            Paragraph("<b>Raghuvendra</b> (Dashboard UI)<br/>Triggered to wire milestone clocks.", st["cell"]),
            Paragraph("<b>COMPLETED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Deliverable 4</b><br/><b>Raghuvendra</b><br/><i>Dashboard Frontend</i>", st["cell"]),
            Paragraph("<b>Deliverable 3</b><br/>(Anushka's milestone badges and Runeet's vault APIs).", st["cell"]),
            Paragraph("Updates <code>/dashboard/nuclear-family</code> with live milestone countdown clocks, digital will trustee approval status cards, and one-click trustee approval trigger.", st["cell"]),
            Paragraph("<code>nuclear-family/page.tsx</code>", st["cell"]),
            Paragraph("<b>Riya</b> (Graph Service Lead)<br/>Triggered to map trustee relationships.", st["cell"]),
            Paragraph("<b>COMPLETED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Deliverable 5</b><br/><b>Riya</b><br/><i>Graph Service Lead</i>", st["cell"]),
            Paragraph("Runeet's trustee relationship data in PostgreSQL.", st["cell"]),
            Paragraph("Creates <code>TRUSTEE_FOR</code> relationship in Neo4j graph, enabling graph traversal queries that identify authorized family trustees and their generational distance from testator.", st["cell"]),
            Paragraph("<code>trustee_graph.cypher</code>", st["cell"]),
            Paragraph("<b>Ayush</b> (Security Engineer)<br/>Triggered to execute RLS pentest suite.", st["cell"]),
            Paragraph("<b>COMPLETED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Deliverable 6</b><br/><b>Ayush</b><br/><i>Security & QA Lead</i>", st["cell"]),
            Paragraph("<b>Deliverables 1 to 5</b><br/>(All governance and security APIs complete).", st["cell"]),
            Paragraph("Executes multi-tenant breach attack simulation against locked time capsules, unreleased digital wills, and private medical dossiers. Validates zero data leaks across household boundaries.", st["cell"]),
            Paragraph("<code>test_cross_tenant_pentest.py</code><br/><code>test_rls_policies.py</code>", st["cell"]),
            Paragraph("<b>Entire Team</b><br/>Sprint 5 Deliverables Verified & Closed.", st["cell"]),
            Paragraph("<b>COMPLETED</b>", st["badge_done"]),
        ],
    ]

    t = Table([headers] + rows, colWidths=[90, 85, 155, 95, 80, 35])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. Sprint 5 Quality Gate Sign-Off", st["h1"]))
    story.append(Paragraph(
        "<b>Certification:</b> Multi-trustee quorum governance and emergency telemetry passes validated with zero security leaks. "
        "Time capsule release logic preserves strict private isolation until quorum completion.<br/>"
        "<b>Signed:</b> Runeet (Lead Architect & Core Backend) • Ayush (Lead QA)", st["body"]
    ))

    def on_first(c, d):
        c._doc_header_title = "FamilyVault — Sprint 5 Master Workflow Blueprint"
    doc.build(story, canvasmaker=NumberedCanvas, onFirstPage=on_first)
    print(f"[OK] Generated {filename}")


def build_sprint_6_pdf(filename="FamilyVault_Sprint_6_Final_Checkup_Release_Gate.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=45)
    st = get_styles()
    story = []

    # Title & Subtitle
    story.append(Paragraph("FamilyVault — Sprint 6 Final Check-Up & Release Gate", st["title"]))
    story.append(Paragraph(
        "Zero-Feature Quality Hardening, Cross-Tenant Security Audit & Production Release Gate v1.0.0 • "
        f"Generated {datetime.now().strftime('%B %d, %Y')} • Target: main (v1.0.0)", st["subtitle"]
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=6))

    # Architecture Overview Callout
    meta_table = Table([
        [
            Paragraph("<b>Sprint Mandate:</b> Zero Feature Additions • Pure Quality", st["cell"]),
            Paragraph("<b>Lead Architect:</b> Runeet (realruneett01)", st["cell"]),
            Paragraph("<b>Target Tag:</b> v1.0.0 Production", st["cell"])
        ],
        [
            Paragraph("<b>Security Standard:</b> Zero P0/P1 Leaks Across RLS", st["cell"]),
            Paragraph("<b>Frontend Target:</b> 60 FPS Tree Canvas & WCAG 2.1 AA", st["cell"]),
            Paragraph("<b>Build Standard:</b> 100% Typecheck & Turbopack 0 Errors", st["cell"])
        ]
    ], colWidths=[180, 180, 180])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph("1. Executive Summary & Sprint Mandate", st["h1"]))
    story.append(Paragraph(
        "Sprint 6 is the final production release gate for FamilyVault v1.0.0. "
        "Strictly following enterprise engineering standards, this sprint prohibits new feature creation and focuses entirely on: "
        "(1) Complete system invariant and UUID parity checks between PostgreSQL and Neo4j. "
        "(2) Automated cross-tenant breach simulations and multi-tier RLS penetration audits. "
        "(3) Tree canvas 60 FPS performance benchmarking under 100+ node loads and WCAG 2.1 AA accessibility compliance. "
        "(4) Cross-device responsive audits across mobile, tablet, and desktop viewports. "
        "(5) Final production compilation, fast-forward merge from develop to main, and production release tagging.",
        st["body"]
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("2. Master Chronological Deliverables Sequence by Owner (Serial Dependency Chain)", st["h1"]))
    story.append(Paragraph(
        "Quality check-ups are executed sequentially: each gate must pass 100% before the next gate begins. "
        "Below is the exact execution chain across the entire engineering team:",
        st["body"]
    ))
    story.append(Spacer(1, 4))

    headers = [
        Paragraph("Check-Up Gate & Owner", st["cell_hdr"]),
        Paragraph("Preceding Work (Must Be Done First)", st["cell_hdr"]),
        Paragraph("Scope & Quality Audit Executed", st["cell_hdr"]),
        Paragraph("Output Audit Report / Artifact", st["cell_hdr"]),
        Paragraph("Next Owner & Gate Triggered", st["cell_hdr"]),
        Paragraph("Status", st["cell_hdr"]),
    ]
    rows = [
        [
            Paragraph("<b>Gate 1</b><br/><b>Runeet</b><br/><i>Repo Admin & Architect</i>", st["cell"]),
            Paragraph("All Sprint 1–5 feature branches merged into develop.", st["cell"]),
            Paragraph("System invariant verification: UUID synchronization parity between PostgreSQL users.id and Neo4j Person.id; clean git index without trailing space artifacts.", st["cell"]),
            Paragraph("<code>verify_uuid_sync.py</code><br/>Canonical develop baseline", st["cell"]),
            Paragraph("<b>Ayush</b> (Lead QA)<br/>Triggered to run master pentest suite.", st["cell"]),
            Paragraph("<b>PASSED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Gate 2</b><br/><b>Ayush</b><br/><i>Lead QA & Security</i>", st["cell"]),
            Paragraph("<b>Gate 1</b><br/>(Runeet's clean system baseline).", st["cell"]),
            Paragraph("Comprehensive security audit: RLS Three-Tier Penetration Test, cross-DB orphan detection, biometric boundary and invariance tests (100% pass on 5/5 tests).", st["cell"]),
            Paragraph("Certified Security Report<br/>0 P0/P1 vulnerabilities", st["cell"]),
            Paragraph("<b>Anushka</b> (Frontend Perf)<br/>Triggered to benchmark tree canvas.", st["cell"]),
            Paragraph("<b>PASSED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Gate 3</b><br/><b>Anushka</b><br/><i>Frontend Performance</i>", st["cell"]),
            Paragraph("<b>Gate 2</b><br/>(Ayush's security clearance).", st["cell"]),
            Paragraph("Tree canvas 60 FPS rendering benchmark under 100+ node loads, WCAG 2.1 AA accessibility audit (@axe-core/playwright), and zero layout shifts on pan/zoom.", st["cell"]),
            Paragraph("<code>tree-canvas.perf.ts</code><br/>0 Accessibility Violations", st["cell"]),
            Paragraph("<b>Raghuvendra</b> (Cross-Device)<br/>Triggered for responsive validation.", st["cell"]),
            Paragraph("<b>PASSED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Gate 4</b><br/><b>Raghuvendra</b><br/><i>Cross-Device UI Lead</i>", st["cell"]),
            Paragraph("<b>Gate 3</b><br/>(Anushka's performance benchmark pass).", st["cell"]),
            Paragraph("Responsive validation across mobile, tablet, and desktop viewports (375px, 768px, 1280px, 1920px), verifying living character auth, media inbox, and nuclear dashboard.", st["cell"]),
            Paragraph("Cross-Device Verification Log<br/>All 9 Routes Responsive", st["cell"]),
            Paragraph("<b>Riya & Ayushman</b> (Services)<br/>Triggered for health checks.", st["cell"]),
            Paragraph("<b>PASSED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Gate 5</b><br/><b>Riya & Ayushman</b><br/><i>Microservices Leads</i>", st["cell"]),
            Paragraph("<b>Gate 4</b><br/>(Frontend validation sign-off).", st["cell"]),
            Paragraph("Service resilience checks: graph shortest-path query execution &le; 15ms, biometrics memory profiling during multi-face embedding extraction, and graceful offline fallback.", st["cell"]),
            Paragraph("Microservice Health Reports<br/>:8001 & :8002 Operational", st["cell"]),
            Paragraph("<b>Runeet</b> (Repo Admin)<br/>Triggered for final release gate.", st["cell"]),
            Paragraph("<b>PASSED</b>", st["badge_done"]),
        ],
        [
            Paragraph("<b>Gate 6</b><br/><b>Runeet</b><br/><i>Lead Architect & Admin</i>", st["cell"]),
            Paragraph("<b>Gates 1 to 5</b><br/>(100% sign-off across all engineering teams).", st["cell"]),
            Paragraph("Final Production Release Gate: Turbopack production build compilation (npm run build), full backend test suite execution, fast-forward merge develop -> main, and tag v1.0.0.", st["cell"]),
            Paragraph("Production Tag v1.0.0<br/>Vercel & Railway Deployment", st["cell"]),
            Paragraph("<b>FAMILYVAULT LIVE</b><br/>Ready for Production Users", st["cell"]),
            Paragraph("<b>PASSED</b>", st["badge_done"]),
        ],
    ]

    t = Table([headers] + rows, colWidths=[90, 85, 155, 95, 80, 35])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. Production Release Gate Certification", st["h1"]))
    story.append(Paragraph(
        "<b>Final Release Verdict: 100% PASSED.</b> All system contracts, tests, security policies, and performance benchmarks "
        "have satisfied production standards. Authorization granted to tag <b>v1.0.0</b> and deploy.<br/>"
        "<b>Signed and Released:</b> Runeet (Lead System Architect, FamilyVault)", st["body"]
    ))

    def on_first(c, d):
        c._doc_header_title = "FamilyVault — Sprint 6 Production Release Gate Blueprint"
    doc.build(story, canvasmaker=NumberedCanvas, onFirstPage=on_first)
    print(f"[OK] Generated {filename}")


if __name__ == "__main__":
    build_sprint_4_pdf()
    build_sprint_5_pdf()
    build_sprint_6_pdf()
