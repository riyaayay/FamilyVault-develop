import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Canvas that enables two-pass page numbering ('Page X of Y') and professional running header/footer."""
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
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(40, 760, "FamilyVault Enterprise — Sprint 2 Completion & Ownership Matrix")
            self.drawRightString(572, 760, "Confidential — Internal Team Roadmap")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(40, 752, 572, 752)
        
        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawString(40, 30, "FamilyVault Generational Operating System • Sprint 2 Deliverables")
        self.drawRightString(572, 30, page_text)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(40, 42, 572, 42)
        self.restoreState()


def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=45,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()
    
    # Custom Color Palette
    PRIMARY = colors.HexColor("#0f172a")     # Slate 900
    SECONDARY = colors.HexColor("#1e293b")   # Slate 800
    ACCENT_EMERALD = colors.HexColor("#059669")
    ACCENT_AMBER = colors.HexColor("#d97706")
    ACCENT_BLUE = colors.HexColor("#0284c7")
    BG_LIGHT = colors.HexColor("#f8fafc")
    TEXT_MUTED = colors.HexColor("#64748b")
    BORDER_COLOR = colors.HexColor("#cbd5e1")

    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=PRIMARY,
        spaceAfter=3
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=TEXT_MUTED,
        spaceAfter=12
    )

    h1_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=PRIMARY,
        spaceBefore=12,
        spaceAfter=5,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#334155")
    )

    body_bold = ParagraphStyle(
        'BodyDarkBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=PRIMARY
    )

    badge_done = ParagraphStyle(
        'BadgeDone',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#047857"),
        alignment=1
    )

    badge_pending = ParagraphStyle(
        'BadgePending',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#b45309"),
        alignment=1
    )

    badge_critical = ParagraphStyle(
        'BadgeCritical',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#b91c1c"),
        alignment=1
    )

    elements = []

    # ---------------------------------------------------------
    # COVER / HEADER BANNER
    # ---------------------------------------------------------
    banner_data = [
        [
            Paragraph("<b>FAMILYVAULT ENTERPRISE</b>", ParagraphStyle('B1', fontName='Helvetica-Bold', fontSize=9.5, leading=11, textColor=ACCENT_BLUE)),
            Paragraph(f"<b>Date:</b> {datetime.now().strftime('%B %d, %Y')} | <b>Version:</b> 2.1-Final", ParagraphStyle('B2', fontName='Helvetica', fontSize=8, leading=10, textColor=TEXT_MUTED, alignment=2))
        ],
        [
            Paragraph("Sprint 2 Completion Roadmap &amp; Ownership Matrix", title_style),
            ""
        ],
        [
            Paragraph("Detailed Audit of Current State, Member Deliverables &amp; Concrete Action Items to Close Sprint 2", subtitle_style),
            ""
        ]
    ]
    banner_table = Table(banner_data, colWidths=[380, 152])
    banner_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('SPAN', (0, 1), (1, 1)),
        ('SPAN', (0, 2), (1, 2)),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(banner_table)
    elements.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT_BLUE, spaceBefore=3, spaceAfter=10))

    # ---------------------------------------------------------
    # 1. EXECUTIVE STATUS OVERVIEW
    # ---------------------------------------------------------
    elements.append(Paragraph("1. Executive Sprint 2 Health Check", h1_style))
    elements.append(Paragraph(
        "All individual contributor branches have been merged into the local <code>develop</code> branch. "
        "The core domain data models, seed script, emergency dossier endpoint, tree canvas, and nuclear family explorer "
        "are successfully implemented. To achieve 100% completion of Sprint 2, remaining cross-service wiring, "
        "CORS configurations, and persona harmonizations must be completed as specified below.",
        body_style
    ))
    elements.append(Spacer(1, 6))

    summary_data = [
        [
            Paragraph("<b>Domain Track</b>", body_bold),
            Paragraph("<b>Lead / Owner</b>", body_bold),
            Paragraph("<b>Sprint 2 Deliverables</b>", body_bold),
            Paragraph("<b>Current Status</b>", body_bold),
            Paragraph("<b>Remaining to Complete</b>", body_bold)
        ],
        [
            Paragraph("<b>Backend &amp; Database</b>", body_style),
            Paragraph("Runeet (Lead)", body_style),
            Paragraph("CRUD APIs, Dossier, 3-Gen Seed, RLS Fix, CORS, Household API", body_style),
            Paragraph("<b>100% COMPLETED</b>", badge_done),
            Paragraph("<b>None — All deliverables completed &amp; verified (7/7 tests)</b>", badge_done)
        ],
        [
            Paragraph("<b>Frontend (Nuclear)</b>", body_style),
            Paragraph("Raghuvendra", body_style),
            Paragraph("Nuclear Family Views, RLS Badges, Nav", body_style),
            Paragraph("<b>85% MERGED</b>", badge_pending),
            Paragraph("Replace mock fetchers with live backend calls; fix 404 nav", body_style)
        ],
        [
            Paragraph("<b>Frontend (Tree Canvas)</b>", body_style),
            Paragraph("Anushka", body_style),
            Paragraph("React Flow 3-Gen Canvas, Controls, Palettes", body_style),
            Paragraph("<b>90% MERGED</b>", badge_done),
            Paragraph("Connect dynamic fetch to Graph Service; harmonize names", body_style)
        ],
        [
            Paragraph("<b>Graph &amp; Kinship</b>", body_style),
            Paragraph("Riya", body_style),
            Paragraph("shortestPath Cypher, /api/graph/tree, Contract", body_style),
            Paragraph("<b>95% MERGED</b>", badge_done),
            Paragraph("Allow CORS port 1111; run 10-UUID sync check", body_style)
        ],
        [
            Paragraph("<b>Biometrics &amp; Storage</b>", body_style),
            Paragraph("Ayushman", body_style),
            Paragraph("InsightFace 512D Embeddings, Multi-face", body_style),
            Paragraph("<b>90% MERGED</b>", badge_done),
            Paragraph("Verify Cloudflare R2 presigned URL pipeline", body_style)
        ],
        [
            Paragraph("<b>QA &amp; Security</b>", body_style),
            Paragraph("Ayush", body_style),
            Paragraph("CRUD Test Suite, RLS Isolation Audit", body_style),
            Paragraph("<b>100% PASSED</b>", badge_done),
            Paragraph("Run multi-service integration verification test", body_style)
        ],
    ]
    summary_table = Table(summary_data, colWidths=[90, 70, 142, 75, 155])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_LIGHT),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # 2. OWNER-BY-OWNER ACTION ITEMS
    # ---------------------------------------------------------
    elements.append(Paragraph("2. Ownership Matrix &amp; Required Action Items", h1_style))
    elements.append(Paragraph(
        "Status and remaining technical deliverables required to finalize Sprint 2 before tagging the release and entering Sprint 3.",
        body_style
    ))
    elements.append(Spacer(1, 5))

    # --- RUNEET ---
    runeet_items = [
        [
            Paragraph("<b>OWNER: RUNEET — Backend Lead &amp; Database Architect</b>", ParagraphStyle('RH', parent=body_bold, textColor=colors.HexColor("#065f46"))),
            Paragraph("<b>STATUS: 100% COMPLETED</b>", badge_done)
        ],
        [
            Paragraph(
                "<b>All Sprint 2 Deliverables Successfully Completed &amp; Verified:</b><br/>"
                "• <b>[DONE] Cross-Origin CORS Configuration:</b> Whitelisted port <code>1111</code>, <code>127.0.0.1:1111</code>, and <code>5173</code> in <code>backend/app/core/config.py</code> and <code>backend/.env</code>.<br/>"
                "• <b>[DONE] Household Member Roster APIs:</b> Built and registered <code>GET /api/v1/household/members</code> and <code>GET /api/v1/users/household/{id}/members</code> with initials, accents, roles, and pet mappings.<br/>"
                "• <b>[DONE] Red Alert Emergency Dossier:</b> Implemented instant clinical compilation in <code>POST /api/v1/health/emergency-dossier/{user_id}</code>.<br/>"
                "• <b>[DONE] Milestone-Locked Vault &amp; Digital Will:</b> Implemented time capsule unlock conditions and trustee approval endpoints.<br/>"
                "• <b>[DONE] Domain CRUD Endpoints:</b> Full CRUD for Vault documents, Pets, Health records, and Properties.<br/>"
                "• <b>[DONE] Three-Tier RLS Security Hardening:</b> Eliminated cross-member recursion and secured <code>SECURITY DEFINER</code> search paths in <code>contracts/schema.sql</code>.<br/>"
                "• <b>[DONE] 3-Generation Narrative Seed Script:</b> Populated deterministic Vance Clan personas (UUIDs 1–10) in <code>backend/scripts/seed.py</code>.<br/>"
                "• <b>[DONE] Automated Test Suite:</b> All <b>7 out of 7 backend unit tests passing</b> (100% pass rate).",
                body_style
            ),
            ""
        ]
    ]
    t_runeet = Table(runeet_items, colWidths=[432, 100])
    t_runeet.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#ecfdf5")),
        ('SPAN', (0,1), (1,1)),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#6ee7b7")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_runeet)
    elements.append(Spacer(1, 6))


    # --- RAGHUVENDRA ---
    raghu_items = [
        [
            Paragraph("<b>OWNER: RAGHUVENDRA — Frontend (Nuclear Family &amp; Dashboard Layout)</b>", ParagraphStyle('RH2', parent=body_bold, textColor=colors.HexColor("#1d4ed8"))),
            Paragraph("<b>PRIORITY: P0 / CRITICAL</b>", badge_critical)
        ],
        [
            Paragraph(
                "<b>Status:</b> <code>/dashboard/nuclear-family</code> page and <code>FamilyExplorer</code> UI components merged.<br/>"
                "<b>Action Item 1: Wire Live Backend Data Fetchers</b><br/>"
                "• In <code>frontend/lib/nuclear-family.ts</code> (lines 165–184), replace static arrays with live <code>fetch(process.env.NEXT_PUBLIC_API_URL + '/api/v1/...')</code> calls, retaining mock data as a try/catch offline fallback.<br/>"
                "<b>Action Item 2: Harmonize Persona Names with Database Contract</b><br/>"
                "• Change the mock family names from 'Amit/Anita Sharma' to David Vance's Nuclear Household ('David Vance', 'Sarah Vance', 'Lucas Vance', and pet 'Rusty') to align with <code>seed.py</code> and the Tree Canvas.<br/>"
                "<b>Action Item 3: Fix Broken Navbar &amp; Missing Links</b><br/>"
                "• In <code>frontend/app/dashboard/layout.tsx</code>, remove the link to <code>/dashboard/inbox</code> (which returns a 404 error) and add a direct link to Anushka's Family Tree Canvas (<code>/dashboard/family</code>).<br/>"
                "<b>Action Item 4: Enhance Dashboard Home</b><br/>"
                "• Upgrade <code>/dashboard</code> from the placeholder to show family quick-links and clan trust summary.",
                body_style
            ),
            ""
        ]
    ]
    t_raghu = Table(raghu_items, colWidths=[432, 100])
    t_raghu.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#eff6ff")),
        ('SPAN', (0,1), (1,1)),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#bfdbfe")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_raghu)
    elements.append(Spacer(1, 6))

    # --- ANUSHKA ---
    anushka_items = [
        [
            Paragraph("<b>OWNER: ANUSHKA — Frontend (Interactive Family Tree Canvas)</b>", ParagraphStyle('RH3', parent=body_bold, textColor=colors.HexColor("#7c2d12"))),
            Paragraph("<b>PRIORITY: P1 / HIGH</b>", badge_pending)
        ],
        [
            Paragraph(
                "<b>Status:</b> React Flow canvas running at <code>/dashboard/family</code> with minimap, controls, and generational styling.<br/>"
                "<b>Action Item 1: Connect Dynamic Tree Endpoint</b><br/>"
                "• In <code>frontend/app/dashboard/family/page.tsx</code>, implement a dynamic <code>useEffect()</code> fetch to Riya's Graph Service: <code>GET http://localhost:8001/api/graph/tree</code>. Use <code>graph-tree-response.json</code> as an offline fallback.<br/>"
                "<b>Action Item 2: Personas &amp; Label Display</b><br/>"
                "• Harmonize the node label mapping so that both Vance Ancestral Clan personas and Indian family names can be viewed consistently without breaking underlying contract UUIDs.<br/>"
                "<b>Action Item 3: Node Click Details Drawer</b><br/>"
                "• Add a side panel / drawer opening on node click to show the selected member's role, generation, and household.",
                body_style
            ),
            ""
        ]
    ]
    t_anushka = Table(anushka_items, colWidths=[432, 100])
    t_anushka.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#fff7ed")),
        ('SPAN', (0,1), (1,1)),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#fed7aa")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_anushka)
    elements.append(Spacer(1, 6))

    # --- RIYA ---
    riya_items = [
        [
            Paragraph("<b>OWNER: RIYA — Graph Database &amp; Kinship Architect</b>", ParagraphStyle('RH4', parent=body_bold, textColor=colors.HexColor("#4c1d95"))),
            Paragraph("<b>PRIORITY: P1 / HIGH</b>", badge_pending)
        ],
        [
            Paragraph(
                "<b>Status:</b> Cypher schema, shortestPath kinship solver, and <code>/api/graph/tree</code> endpoint implemented and merged.<br/>"
                "<b>Action Item 1: Enable CORS for Frontend</b><br/>"
                "• In <code>graph-service/main.py</code>, add FastAPI CORS middleware allowing <code>http://localhost:1111</code> and <code>http://localhost:3000</code> so Anushka's tree canvas can query the graph directly.<br/>"
                "<b>Action Item 2: 10-UUID Parity Verification</b><br/>"
                "• Run cross-validation between <code>backend/scripts/seed.py</code> (PERSON_IDS 1–10) and Neo4j Person nodes to ensure exact 1-to-1 UUID synchronization.<br/>"
                "<b>Action Item 3: Offline Graph Response Fallback</b><br/>"
                "• In <code>graph-service/db.py</code>, handle missing AuraDB credentials gracefully to prevent crash during local mock testing.",
                body_style
            ),
            ""
        ]
    ]
    t_riya = Table(riya_items, colWidths=[432, 100])
    t_riya.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f5f3ff")),
        ('SPAN', (0,1), (1,1)),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#ddd6fe")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_riya)
    elements.append(Spacer(1, 6))

    # --- AYUSHMAN ---
    ayushman_items = [
        [
            Paragraph("<b>OWNER: AYUSHMAN — Biometrics &amp; Media Storage Lead</b>", ParagraphStyle('RH5', parent=body_bold, textColor=colors.HexColor("#065f46"))),
            Paragraph("<b>PRIORITY: P2 / MEDIUM</b>", badge_done)
        ],
        [
            Paragraph(
                "<b>Status:</b> InsightFace 512D normalized embedding generator, multi-face extraction, and pydantic fix merged.<br/>"
                "<b>Action Item 1: R2 Presigned Upload URL Test</b><br/>"
                "• Provide a lightweight test script verifying that <code>POST /api/biometrics/upload-url</code> generates a valid signed URL for Cloudflare R2.<br/>"
                "<b>Action Item 2: Sample Group Photo Verification</b><br/>"
                "• Add a 3-person sample photo test in <code>biometrics/tests/</code> asserting <code>detect_and_extract_faces()</code> returns 3 distinct 512D arrays.<br/>"
                "<b>Action Item 3: Vector Schema Alignment for Sprint 3</b><br/>"
                "• Document embedding payload format for Runeet to store in PostgreSQL (using <code>pgvector</code> or binary JSON array).",
                body_style
            ),
            ""
        ]
    ]
    t_ayushman = Table(ayushman_items, colWidths=[432, 100])
    t_ayushman.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#ecfdf5")),
        ('SPAN', (0,1), (1,1)),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#a7f3d0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_ayushman)
    elements.append(Spacer(1, 6))

    # --- AYUSH ---
    ayush_items = [
        [
            Paragraph("<b>OWNER: AYUSH — QA Lead, Security Auditor &amp; Release Manager</b>", ParagraphStyle('RH6', parent=body_bold, textColor=colors.HexColor("#374151"))),
            Paragraph("<b>PRIORITY: P1 / RELEASE GATE</b>", badge_pending)
        ],
        [
            Paragraph(
                "<b>Status:</b> Automated pytest test suites created; verified all 6 core backend CRUD tests pass.<br/>"
                "<b>Action Item 1: Integration Test Run</b><br/>"
                "• Execute full end-to-end check: Next.js frontend build + backend pytest + contract JSON validation.<br/>"
                "<b>Action Item 2: Sign-off &amp; Sprint 2 Tagging</b><br/>"
                "• Following completion of Actions 1.1–3.1, authorize Runeet to merge <code>develop</code> → <code>main</code> and create the git tag <code>sprint-2-release</code>.",
                body_style
            ),
            ""
        ]
    ]
    t_ayush = Table(ayush_items, colWidths=[432, 100])
    t_ayush.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f3f4f6")),
        ('SPAN', (0,1), (1,1)),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#e5e7eb")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_ayush)
    elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # 3. CONCRETE STEP-BY-STEP COMPLETION SEQUENCE
    # ---------------------------------------------------------
    elements.append(Paragraph("3. Recommended Execution Order to Close Sprint 2", h1_style))
    
    seq_data = [
        [
            Paragraph("<b>Step</b>", body_bold),
            Paragraph("<b>Task Description</b>", body_bold),
            Paragraph("<b>Assigned Owner</b>", body_bold),
            Paragraph("<b>Est. Effort</b>", body_bold)
        ],
        [
            Paragraph("<b>1</b>", body_bold),
            Paragraph("Add port 1111 to backend CORS (<code>config.py</code>) and Graph Service CORS (<code>main.py</code>).", body_style),
            Paragraph("Runeet / Riya", body_style),
            Paragraph("10 mins", body_style)
        ],
        [
            Paragraph("<b>2</b>", body_bold),
            Paragraph("Fix <code>frontend/app/dashboard/layout.tsx</code> navbar (remove 404 inbox, add <code>/dashboard/family</code>).", body_style),
            Paragraph("Raghuvendra", body_style),
            Paragraph("15 mins", body_style)
        ],
        [
            Paragraph("<b>3</b>", body_bold),
            Paragraph("Harmonize personas in <code>frontend/lib/nuclear-family.ts</code> to David Vance's household (match <code>seed.py</code>).", body_style),
            Paragraph("Raghuvendra", body_style),
            Paragraph("25 mins", body_style)
        ],
        [
            Paragraph("<b>4</b>", body_bold),
            Paragraph("Wire <code>nuclear-family.ts</code> getters to live backend endpoints with offline fallback.", body_style),
            Paragraph("Raghuvendra", body_style),
            Paragraph("30 mins", body_style)
        ],
        [
            Paragraph("<b>5</b>", body_bold),
            Paragraph("Wire <code>/dashboard/family</code> to fetch from <code>GET http://localhost:8001/api/graph/tree</code> with JSON fallback.", body_style),
            Paragraph("Anushka", body_style),
            Paragraph("30 mins", body_style)
        ],
        [
            Paragraph("<b>6</b>", body_bold),
            Paragraph("Run complete regression test suite (<code>pytest</code> + <code>npm run build</code>) and tag <code>sprint-2-release</code>.", body_style),
            Paragraph("Ayush / Runeet", body_style),
            Paragraph("20 mins", body_style)
        ],
    ]
    t_seq = Table(seq_data, colWidths=[35, 310, 110, 77])
    t_seq.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_LIGHT),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_seq)

    # Build the document
    doc.build(elements, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {filename}")

if __name__ == "__main__":
    output_path = r"c:\Users\realr\OneDrive\Desktop\FamilyVault\FamilyVault_Sprint_2_Action_Items_By_Owner.pdf"
    build_pdf(output_path)
