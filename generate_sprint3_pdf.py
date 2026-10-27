import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, HRFlowable
)
from reportlab.pdfgen import canvas
from PIL import Image as PILImage

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
            self.drawString(36, 756, "FamilyVault Enterprise — Sprint 3 Deliverables & Ownership Specification")
            self.drawRightString(576, 756, "Confidential — Internal Team Roadmap")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(36, 748, 576, 748)
        
        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawString(36, 25, "FamilyVault Generational Operating System • Sprint 3 Deliverables by Owner")
        self.drawRightString(576, 25, page_text)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 35, 576, 35)
        self.restoreState()


def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=40,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    
    # Custom Color Palette
    PRIMARY = colors.HexColor("#0f172a")        # Slate 900
    SECONDARY = colors.HexColor("#1e293b")      # Slate 800
    INDIGO = colors.HexColor("#4338ca")         # Indigo 700
    INDIGO_LIGHT = colors.HexColor("#e0e7ff")   # Indigo 100
    EMERALD_LIGHT = colors.HexColor("#d1fae5")  # Emerald 100
    AMBER_LIGHT = colors.HexColor("#fef3c7")    # Amber 100
    ROSE_LIGHT = colors.HexColor("#ffe4e6")     # Rose 100
    PURPLE_LIGHT = colors.HexColor("#f5f3ff")   # Violet 100
    TEXT_MUTED = colors.HexColor("#475569")     # Slate 600
    BORDER_COLOR = colors.HexColor("#cbd5e1")   # Slate 300
    BG_LIGHT = colors.HexColor("#f8fafc")       # Slate 50

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=PRIMARY,
        spaceAfter=3
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=TEXT_MUTED,
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=PRIMARY,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=SECONDARY,
        spaceBefore=4,
        spaceAfter=2,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=SECONDARY
    )

    body_bold = ParagraphStyle(
        'DocBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    caption_style = ParagraphStyle(
        'ImgCaption',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=PRIMARY,
        alignment=1
    )

    caption_sub = ParagraphStyle(
        'ImgCaptionSub',
        parent=body_style,
        fontName='Helvetica',
        fontSize=7,
        leading=9,
        textColor=TEXT_MUTED,
        alignment=1
    )

    badge_critical = ParagraphStyle(
        'BadgeCrit',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#991b1b"),
        alignment=1
    )

    badge_new = ParagraphStyle(
        'BadgeNew',
        parent=body_style,
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#4338ca"),
        alignment=1
    )

    elements = []

    # =========================================================
    # PAGE 1: HEADER, EXECUTIVE CONTEXT & RUNEET'S DELIVERABLES
    # =========================================================
    elements.append(Paragraph("FamilyVault — Sprint 3 Deliverables by Owner", title_style))
    elements.append(Paragraph(
        "<b>Sprint Duration:</b> Aug 28 – Aug 30, 2026 &nbsp;|&nbsp; <b>Final Demo:</b> Sept 03, 2026 &nbsp;|&nbsp; "
        "<b>Repository:</b> <font color='#4338ca'>realruneett01/FamilyVault</font> (Branch: <code>develop</code>)<br/>"
        "<b>Sprint 3 Core Theme:</b> Biometric Pipeline, Media Inbox Approval, Lineage Tree Polish, Cross-Database UUID Parity &amp; <b>Living Character Authentication Suite</b>",
        subtitle_style
    ))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceBefore=0, spaceAfter=8))

    elements.append(Paragraph("1. Executive Context &amp; Sprint 2 Baseline Summary", h1_style))
    
    summary_text = (
        "<b>Repository State:</b> Following the successful closeout of Sprint 2, all baseline deliverables have been audited and merged into <code>develop</code>:<br/>"
        "• <b>PR #15:</b> Backend CORS whitelist (supporting <code>http://localhost:1111</code>) &amp; nuclear household roster API.<br/>"
        "• <b>PR #16:</b> Raghuvendra's Nuclear Family Dashboard views wired to core backend models with live/mock toggles.<br/>"
        "• <b>PR #18:</b> Ayush's automated multi-tenant Row Level Security (RLS) penetration test suite.<br/>"
        "• <b>PR #19:</b> Riya's Neo4j <code>/api/graph/tree</code> endpoint aligned to React Flow nodes/edges contract with deduplication fixes.<br/>"
        "• <b>PR #20:</b> Anushka's React Flow custom nodes (living members, ancestors, family heads) with live fetch and contract fallbacks.<br/>"
        "• <b>InsightFace Integration:</b> Ayushman's 512D face vector generation merged and validated.<br/>"
        "<b>Sprint 3 Strategic Shift:</b> Elevates FamilyVault into an AI-augmented generational operating system. A centerpiece of this sprint is "
        "Runeet's <b>Living Character Authentication Suite</b>, transforming the traditional login wall into an interactive, emotive experience."
    )
    
    t_summary = Table([[Paragraph(summary_text, body_style)]], colWidths=[540])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("2. Detailed Sprint 3 Deliverables by Individual Owner", h1_style))

    # --- RUNEET ---
    runeet_items = [
        [
            Paragraph("<b>OWNER: RUNEET — Lead System Architect &amp; Core Backend / Auth Engineer</b>", ParagraphStyle('RH1', parent=body_bold, textColor=colors.HexColor("#1e1b4b"))),
            Paragraph("<b>PRIORITY: P1 / FLAGSHIP</b>", badge_new)
        ],
        [
            Paragraph(
                "<b>Branches:</b> <code>feature/runeet-living-auth-ui</code> &nbsp;|&nbsp; <code>feature/runeet-riya-uuid-verify</code> &nbsp;|&nbsp; <code>feature/runeet-emergency-dossier</code><br/>"
                "<b>DELIVERABLE 1: Interactive Living Character Authentication Suite (Flagship Login Page Design)</b><br/>"
                "• <b>Living Vector Stage:</b> Implement the interactive 4-character dynamic SVG stage featuring <i>Purple Pillar</i> (<code>#6727FE</code>), "
                "<i>Black Sentinel</i> (<code>#1B1C21</code>), <i>Yellow Dome</i> (<code>#E5C90A</code>), and <i>Orange Blob</i> (<code>#FE8332</code>).<br/>"
                "• <b>Continuous Viewport Gaze Pursuit:</b> 60 FPS requestAnimationFrame Cartesian vector tracking (normalized [-1.0, 1.0]) with an adaptive biological "
                "lerp rate ensuring all 4 characters track the user's cursor seamlessly across the entire browser viewport.<br/>"
                "• <b>Hover-Triggered Password Mutual Gaze:</b> The instant the user's cursor points to or hovers over the Password field (without clicking), "
                "Purple immediately morphs into the banana curve (<code>d=purpleBananaPath</code>) arching forward over Black, and locks reciprocal eye contact "
                "directly into Black's upward-tilted gaze, while Orange watches in suspense with curious dots.<br/>"
                "• <b>Orange Head Shake &amp; Living Wobble:</b> Orange dome tilts organically toward the cursor (<code>rotate: pupil.x * 5.5deg</code>) "
                "with dynamic squash/stretch (<code>scaleX: 1 - |x|*0.035, scaleY: 1 + |y|*0.025</code>), maintaining a sweet persistent upward smile "
                "during free tracking, and executing an expressive 3-cycle horizontal head shake on invalid typing.<br/>"
                "• <b>Attentive Email Interest Transition:</b> Pointing at Email triggers Purple's 9.3° forward lean and sharp focused gaze across all characters.<br/>"
                "• <b>Live Keystroke Emotion Engine:</b> Cheerful bouncing smiles when password characters match valid prefixes; sad downturned frowns on typing errors.<br/>"
                "• <b>Password Reveal Shock State:</b> Eye toggle click triggers Purple &amp; Black peering at revealed credentials and Orange opening a wide ':O' mouth.<br/>"
                "• <b>Full Auth Pipeline Integration:</b> Integrated with Supabase Auth, React Hook Form, Zod schema validation, and Next.js SSR.<br/>"
                "<b>DELIVERABLE 2: PostgreSQL ↔ Neo4j 10-UUID Cross-Database Synchronization (Joint Pairing with Riya)</b><br/>"
                "• Pair with Riya to verify strict 1-to-1 UUIDv4 parity between Postgres <code>users.id</code> and Neo4j <code>(:Person {id})</code> across all 10 seeded users.<br/>"
                "• Re-run cross-database seeding script live to eliminate any ID drift or orphan records.<br/>"
                "<b>DELIVERABLE 3: Emergency 'Red Alert' Medical Dossier &amp; Milestone Vault Engine</b><br/>"
                "• Implement <code>POST /api/v1/health/emergency-dossier/{user_id}</code> compiling blood group, allergies, emergency contacts, and active prescriptions.<br/>"
                "• Implement milestone-locked vault unlock conditions based on future timestamps and trustee approvals.",
                body_style
            ),
            ""
        ]
    ]
    t_runeet = Table(runeet_items, colWidths=[440, 100])
    t_runeet.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), INDIGO_LIGHT),
        ('SPAN', (0,1), (1,1)),
        ('BOX', (0,0), (-1,-1), 1.2, colors.HexColor("#818cf8")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_runeet)
    
    # Force PageBreak to start Page 2 with visual mockups and next owners
    elements.append(PageBreak())

    # =========================================================
    # PAGE 2: VISUAL SHOWCASE OF LOGIN SUITE + AYUSHMAN + RAGHUVENDRA
    # =========================================================
    elements.append(Paragraph("Visual Showcase: Living Character Authentication Architecture", h1_style))
    
    # Side-by-side screenshots of Runeet's Login Page deliverable
    img_idle_path = r"c:\Users\realr\OneDrive\Desktop\FamilyVault\scratch\login_idle_preview.png"
    img_pwd_path = r"c:\Users\realr\OneDrive\Desktop\FamilyVault\scratch\login_card_preview.png"
    
    img_w, img_h = 245, 155
    im1 = Image(img_idle_path, width=img_w, height=img_h)
    im2 = Image(img_pwd_path, width=img_w, height=img_h)

    showcase_table_data = [
        [im1, im2],
        [
            Paragraph("<b>State A: Free Cursor Tracking &amp; Smiling Tilt</b>", caption_style),
            Paragraph("<b>State B: Password Hover (Reciprocal Mutual Gaze)</b>", caption_style)
        ],
        [
            Paragraph("All characters pursue cursor; Orange smiles and tilts head organically.", caption_sub),
            Paragraph("Pointing at Password triggers Purple banana arch &amp; mutual gaze with Black.", caption_sub)
        ]
    ]
    t_showcase = Table(showcase_table_data, colWidths=[270, 270])
    t_showcase.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_showcase)
    elements.append(Spacer(1, 10))

    # --- AYUSHMAN ---
    ayushman_items = [
        [
            Paragraph("<b>OWNER: AYUSHMAN — Biometrics &amp; Media Storage Lead</b>", ParagraphStyle('RH2', parent=body_bold, textColor=colors.HexColor("#065f46"))),
            Paragraph("<b>PRIORITY: P1 / HIGH</b>", badge_critical)
        ],
        [
            Paragraph(
                "<b>Branch:</b> <code>feature/ayushman-cosine-match</code> &nbsp;|&nbsp; <b>PR Target:</b> <code>develop</code> &nbsp;|&nbsp; <b>Reviewer:</b> Ayush<br/>"
                "<b>DELIVERABLE 1: Cosine Similarity Matching Engine</b><br/>"
                "• Implement vector similarity calculation matching extracted 512D InsightFace vectors against stored family member embedding profiles.<br/>"
                "• Adhere strictly to the contract constant <code>MATCH_THRESHOLD = 0.85</code> from <code>/contracts/MATCH_CONSTANTS.json</code>.<br/>"
                "<b>DELIVERABLE 2: Intelligent Smart Routing &amp; Media Queue</b><br/>"
                "• Confidence ≥ 0.85: Automatically tag matched Neo4j Person UUIDs and publish directly to the joint family timeline.<br/>"
                "• Confidence &lt; 0.85 or Ambiguous/Group Photos: Route directly to the household Media Inbox approval queue for manual review.<br/>"
                "• Non-image contributions (audio lore, home videos) automatically route to the Media Inbox queue.<br/>"
                "<b>DELIVERABLE 3: Cloudflare R2 Presigned Direct Upload API</b><br/>"
                "• Expose <code>POST /api/biometrics/upload-url</code> generating signed URLs with 15-minute expirations for direct-to-R2 uploads.",
                body_style
            ),
            ""
        ]
    ]
    t_ayushman = Table(ayushman_items, colWidths=[440, 100])
    t_ayushman.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), EMERALD_LIGHT),
        ('SPAN', (0,1), (1,1)),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#a7f3d0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_ayushman)
    elements.append(Spacer(1, 8))

    # --- RAGHUVENDRA ---
    raghuvendra_items = [
        [
            Paragraph("<b>OWNER: RAGHUVENDRA — Frontend Dashboard &amp; Media Inbox Lead</b>", ParagraphStyle('RH3', parent=body_bold, textColor=colors.HexColor("#92400e"))),
            Paragraph("<b>PRIORITY: P1 / HIGH</b>", badge_critical)
        ],
        [
            Paragraph(
                "<b>Branch:</b> <code>feature/raghuvendra-media-inbox-ui</code> &nbsp;|&nbsp; <b>PR Target:</b> <code>develop</code> &nbsp;|&nbsp; <b>Reviewer:</b> Anushka<br/>"
                "<b>DELIVERABLE 1: Media Inbox Management Interface</b><br/>"
                "• Build the responsive <code>/dashboard/inbox</code> approval page rendering pending media contributions in an interactive card grid.<br/>"
                "• Implement instant Accept and Reject actions wired to Ayushman's backend decision endpoints.<br/>"
                "<b>DELIVERABLE 2: Cultural Kinship Badges on Incoming Media</b><br/>"
                "• Display dynamic kinship relationship pills on incoming media items (e.g., <i>'Contributed by Chacha Marcus'</i>, <i>'Tag: Bua Priya'</i>) "
                "utilizing relationship badges generated from Riya's kinship graph.<br/>"
                "<b>DELIVERABLE 3: Member Profile Overview Popups</b><br/>"
                "• Build quick-preview modal cards displaying contributor bio, avatar, and nuclear household alignment upon clicking media tags.",
                body_style
            ),
            ""
        ]
    ]
    t_raghuvendra = Table(raghuvendra_items, colWidths=[440, 100])
    t_raghuvendra.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), AMBER_LIGHT),
        ('SPAN', (0,1), (1,1)),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#fde68a")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_raghuvendra)
    
    # Break to Page 3 for Anushka, Riya, and Ayush
    elements.append(PageBreak())

    # =========================================================
    # PAGE 3: ANUSHKA, RIYA, AND AYUSH DELIVERABLES
    # =========================================================
    # --- ANUSHKA ---
    anushka_items = [
        [
            Paragraph("<b>OWNER: ANUSHKA — Lineage Canvas &amp; Interactive Tree Lead</b>", ParagraphStyle('RH4', parent=body_bold, textColor=colors.HexColor("#831843"))),
            Paragraph("<b>PRIORITY: P1 / HIGH</b>", badge_critical)
        ],
        [
            Paragraph(
                "<b>Branch:</b> <code>feature/anushka-tree-polish</code> &nbsp;|&nbsp; <b>PR Target:</b> <code>develop</code> &nbsp;|&nbsp; <b>Reviewer:</b> Raghuvendra<br/>"
                "<b>DELIVERABLE 1: Canvas Search Bar &amp; Auto-Centering</b><br/>"
                "• Implement auto-complete search bar in <code>/dashboard/family</code> allowing instantaneous viewport panning and smooth centering "
                "on any of the 10 seeded family members.<br/>"
                "• Enforce viewport boundary constraints (min zoom 0.35x, max zoom 2.2x) to prevent canvas loss.<br/>"
                "<b>DELIVERABLE 2: Dynamic Kinship Path Highlighting</b><br/>"
                "• Implement multi-node selection highlighting the exact graph edges connecting two selected family members (e.g., David Vance to Marcus Vance).<br/>"
                "<b>DELIVERABLE 3: Interactive Member Detail Drawer</b><br/>"
                "• Build slide-out side sheet displaying selected member's personal milestones, emergency blood group, linked health alerts, and unlocked letters.",
                body_style
            ),
            ""
        ]
    ]
    t_anushka = Table(anushka_items, colWidths=[440, 100])
    t_anushka.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), ROSE_LIGHT),
        ('SPAN', (0,1), (1,1)),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#fbcfe8")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_anushka)
    elements.append(Spacer(1, 8))

    # --- RIYA ---
    riya_items = [
        [
            Paragraph("<b>OWNER: RIYA — Graph Database &amp; Cultural Kinship Engine Lead</b>", ParagraphStyle('RH5', parent=body_bold, textColor=colors.HexColor("#581c87"))),
            Paragraph("<b>PRIORITY: P1 / HIGH</b>", badge_critical)
        ],
        [
            Paragraph(
                "<b>Branch:</b> <code>feature/runeet-riya-uuid-verify</code> &nbsp;|&nbsp; <code>feature/riya-kinship-refinement</code> &nbsp;|&nbsp; <b>Reviewer:</b> Runeet<br/>"
                "<b>DELIVERABLE 1: Indian Cultural Kinship &amp; Lineage Engine</b><br/>"
                "• Author Cypher shortestPath algorithms resolving culturally specific kinship terms: Chacha, Mama, Bua, Masi, Tauji, and Gotra lineages.<br/>"
                "• Integrate kinship metadata into Neo4j graph tree query payload for consumption by Anushka's tree canvas.<br/>"
                "<b>DELIVERABLE 2: Graph Paradox &amp; Ancestry Cycle Validation</b><br/>"
                "• Implement validation checks preventing chronological or biological paradoxes (e.g. child older than parent, cyclic ancestry loops).<br/>"
                "<b>DELIVERABLE 3: Cross-Database UUID Synchronization with Runeet</b><br/>"
                "• Pair live with Runeet to verify 100% ID synchronization across PostgreSQL and Neo4j for all 10 seeded accounts.",
                body_style
            ),
            ""
        ]
    ]
    t_riya = Table(riya_items, colWidths=[440, 100])
    t_riya.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PURPLE_LIGHT),
        ('SPAN', (0,1), (1,1)),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#ddd6fe")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_riya)
    elements.append(Spacer(1, 8))

    # --- AYUSH ---
    ayush_items = [
        [
            Paragraph("<b>OWNER: AYUSH — QA Lead, Security Penetration Auditor &amp; Release Gatekeeper</b>", ParagraphStyle('RH6', parent=body_bold, textColor=colors.HexColor("#374151"))),
            Paragraph("<b>PRIORITY: P1 / RELEASE GATE</b>", badge_critical)
        ],
        [
            Paragraph(
                "<b>Branch:</b> <code>feature/ayush-biometric-edgecases</code> &nbsp;|&nbsp; <code>feature/ayush-cross-tenant-pentest</code> &nbsp;|&nbsp; <b>Reviewer:</b> Runeet / Ayushman<br/>"
                "<b>DELIVERABLE 1: Biometric Edge-Case &amp; Boundary Test Suite</b><br/>"
                "• Automated pytest suite verifying multi-person group photos, zero-face-detection uploads, and boundary comparisons (0.849 rejection vs 0.850 match).<br/>"
                "• Verify persistence invariance: rejected contributions remain securely archived in sender's private repository without disappearing.<br/>"
                "<b>DELIVERABLE 2: Cross-Database Orphan Detection Script</b><br/>"
                "• Write automated integrity check asserting that 100% of PostgreSQL <code>users.id</code> records match <code>(:Person {id})</code> in Neo4j.<br/>"
                "<b>DELIVERABLE 3: Cross-Tenant RLS Penetration Attack Suite</b><br/>"
                "• Execute automated penetration attacks simulating session token forgery to attempt cross-household and cross-clan data leaks.",
                body_style
            ),
            ""
        ]
    ]
    t_ayush = Table(ayush_items, colWidths=[440, 100])
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

    # Break to Page 4 for Step Sequence and Checklist
    elements.append(PageBreak())

    # =========================================================
    # PAGE 4: STEP-BY-STEP EXECUTION ORDER & SIGN-OFF CHECKLIST
    # =========================================================
    elements.append(Paragraph("3. Recommended Step-by-Step Execution Sequence (Sprint 3)", h1_style))
    
    seq_data = [
        [
            Paragraph("<b>Step</b>", body_bold),
            Paragraph("<b>Action Item &amp; Scope</b>", body_bold),
            Paragraph("<b>Assigned Owner</b>", body_bold),
            Paragraph("<b>Handoff / Target</b>", body_bold)
        ],
        [
            Paragraph("<b>1</b>", body_bold),
            Paragraph("Publish updated <code>/contracts/media-match-response.json</code> with confidence scores and inbox queues.", body_style),
            Paragraph("Ayushman", body_style),
            Paragraph("Handoff to Raghuvendra", body_style)
        ],
        [
            Paragraph("<b>2</b>", body_bold),
            Paragraph("Pair on live call to audit and execute 10-UUID synchronization between Supabase and Neo4j.", body_style),
            Paragraph("Runeet &amp; Riya", body_style),
            Paragraph("Joint PR to <code>develop</code>", body_style)
        ],
        [
            Paragraph("<b>3</b>", body_bold),
            Paragraph("Complete <b>Living Character Authentication Suite</b> with hover-triggered mutual gaze and Orange head tilt.", body_style),
            Paragraph("Runeet", body_style),
            Paragraph("Demo &amp; merge to <code>develop</code>", body_style)
        ],
        [
            Paragraph("<b>4</b>", body_bold),
            Paragraph("Build <code>/dashboard/inbox</code> UI with Accept/Reject actions and relative cultural kinship badges.", body_style),
            Paragraph("Raghuvendra", body_style),
            Paragraph("Review by Anushka", body_style)
        ],
        [
            Paragraph("<b>5</b>", body_bold),
            Paragraph("Implement search bar, auto-centering, zoom limits, and kinship edge glow on Tree Canvas.", body_style),
            Paragraph("Anushka", body_style),
            Paragraph("Review by Raghuvendra", body_style)
        ],
        [
            Paragraph("<b>6</b>", body_bold),
            Paragraph("Deploy InsightFace cosine similarity engine with 0.85 threshold and Cloudflare R2 upload endpoints.", body_style),
            Paragraph("Ayushman", body_style),
            Paragraph("Review by Ayush", body_style)
        ],
        [
            Paragraph("<b>7</b>", body_bold),
            Paragraph("Execute biometric boundary tests, cross-database orphan checks, and multi-tenant RLS pentest.", body_style),
            Paragraph("Ayush", body_style),
            Paragraph("Sprint 3 Sign-off Gate", body_style)
        ],
    ]
    t_seq = Table(seq_data, colWidths=[30, 270, 110, 130])
    t_seq.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_LIGHT),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_seq)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("4. Sprint 3 Quality Gate &amp; Tagging Sign-Off Checklist", h1_style))

    check_data = [
        [
            Paragraph("<b>[ &nbsp; ]</b> &nbsp; <b>Living Auth Suite Verified:</b> 4-character vector stage tracks cursor smoothly at 60 FPS; pointing at Password triggers mutual gaze between Purple and Black; Orange tilts head with happy smile; live keystroke mood feedback operational.", body_style)
        ],
        [
            Paragraph("<b>[ &nbsp; ]</b> &nbsp; <b>Biometric Pipeline Certified:</b> Uploaded photos match at 0.85 threshold; group photos detect multiple faces; rejected media persists in private archive; R2 presigned URLs function.", body_style)
        ],
        [
            Paragraph("<b>[ &nbsp; ]</b> &nbsp; <b>Media Inbox Flow Operational:</b> Accept action tags and publishes media; Reject action updates status; kinship badges accurately identify relationship of contributor.", body_style)
        ],
        [
            Paragraph("<b>[ &nbsp; ]</b> &nbsp; <b>Tree Canvas Polished:</b> Search bar centers on any of the 10 seeded users; path highlighting glows between selected nodes; member detail drawer slides smoothly.", body_style)
        ],
        [
            Paragraph("<b>[ &nbsp; ]</b> &nbsp; <b>UUID Parity 100%:</b> Zero orphan records between PostgreSQL <code>users.id</code> and Neo4j <code>(:Person {id})</code>; Cypher paradox validation blocks cycles.", body_style)
        ],
        [
            Paragraph("<b>[ &nbsp; ]</b> &nbsp; <b>Release Gate Sign-off:</b> Ayush executes full regression test suite (<code>pytest</code> + <code>npm run build</code> = 0 errors); Runeet merges <code>develop</code> → <code>main</code> and tags <code>sprint-3-release</code>.", body_style)
        ]
    ]
    t_check = Table(check_data, colWidths=[540])
    t_check.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_check)

    # Build document
    doc.build(elements, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {filename}")

if __name__ == "__main__":
    output_pdf = r"c:\Users\realr\OneDrive\Desktop\FamilyVault\FamilyVault_Sprint_3_Deliverables_By_Owner.pdf"
    build_pdf(output_pdf)
