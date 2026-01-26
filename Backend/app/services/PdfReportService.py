from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas


# GymAnalysis Design System Colors
CYAN_ACCENT = colors.HexColor("#00b4d8")
DARK_BG = colors.HexColor("#141414")
LIGHT_TEXT = colors.HexColor("#f2f2f2")
BORDER_COLOR = colors.HexColor("#404040")
SURFACE_COLOR = colors.HexColor("#1f1f1f")
MUTED_TEXT = colors.HexColor("#999999")
SUCCESS_GREEN = colors.HexColor("#10b981")
WARNING_RED = colors.HexColor("#ef4444")


def add_page_decorations(canvas_obj, doc):
    """
    Add background and footer decorations to each page.
    Called by ReportLab's onFirstPage and onLaterPages callbacks.
    """
    canvas_obj.saveState()

    # Draw dark background FIRST (under everything)
    canvas_obj.setFillColor(DARK_BG)
    canvas_obj.rect(0, 0, letter[0], letter[1], fill=1, stroke=0)

    # Draw subtle grid pattern (40x40px = ~14mm)
    canvas_obj.setStrokeColor(colors.HexColor("#1a1a1a"))
    canvas_obj.setLineWidth(0.5)

    # Vertical lines
    for x in range(0, int(letter[0]), 14):
        canvas_obj.line(x, 0, x, letter[1])

    # Horizontal lines
    for y in range(0, int(letter[1]), 14):
        canvas_obj.line(0, y, letter[0], y)

    # Draw footer with branding
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(MUTED_TEXT)

    # Left: Brand name
    canvas_obj.drawString(2*cm, 1*cm, "GYMANALYSIS")

    # Center: Generation date
    date_str = datetime.now().strftime("%B %d, %Y • %H:%M")
    canvas_obj.drawCentredString(letter[0]/2, 1*cm, date_str)

    # Right: Page number
    canvas_obj.drawRightString(letter[0] - 2*cm, 1*cm, f"PAGE {doc.page}")

    canvas_obj.restoreState()


def generate_pdf_report(analysis: dict, output_path: str):
    """
    Generate brutalist-style PDF analysis report matching GymAnalysis design system

    Args:
        analysis: Dictionary containing analysis results with overall_score, categories, poses
        output_path: Path where PDF will be saved

    Returns:
        output_path: Path to generated PDF
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
    )

    story = []
    styles = getSampleStyleSheet()

    # Debug: Print analysis structure
    print(f"PDF Generation - Analysis keys: {analysis.keys() if analysis else 'None'}")
    if analysis and 'categories' in analysis:
        print(f"PDF Generation - Categories: {len(analysis['categories'])}")
        for cat in analysis['categories']:
            print(f"  Category '{cat.get('name')}' has {len(cat.get('poses', []))} poses")

    # Check if analysis is empty
    if not analysis or not analysis.get('categories'):
        no_data_style = ParagraphStyle(
            "NoData",
            parent=styles["Normal"],
            fontSize=36,
            textColor=LIGHT_TEXT,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            spaceAfter=20,
        )
        story.append(Spacer(1, 5*cm))
        story.append(Paragraph("NO EXERCISE DETECTED", no_data_style))
        doc.build(story, onFirstPage=add_page_decorations, onLaterPages=add_page_decorations)
        return output_path

    # ==================== CUSTOM STYLES ====================

    # Badge style (small label)
    badge_style = ParagraphStyle(
        "Badge",
        parent=styles["Normal"],
        fontSize=10,
        textColor=CYAN_ACCENT,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        spaceAfter=10,
        spaceBefore=0,
        leading=14,
    )

    # Hero title style (main heading)
    hero_style = ParagraphStyle(
        "Hero",
        parent=styles["Heading1"],
        fontSize=48,
        textColor=LIGHT_TEXT,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        spaceAfter=30,
        spaceBefore=0,
        leading=50,
    )

    # Section heading style
    section_heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=24,
        textColor=LIGHT_TEXT,
        alignment=TA_LEFT,
        fontName="Helvetica-Bold",
        spaceAfter=20,
        spaceBefore=30,
        leading=28,
    )

    # Muted text style
    muted_style = ParagraphStyle(
        "Muted",
        parent=styles["Normal"],
        fontSize=10,
        textColor=MUTED_TEXT,
        alignment=TA_CENTER,
        fontName="Helvetica",
        leading=14,
    )

    # Score display style
    score_style = ParagraphStyle(
        "ScoreDisplay",
        parent=styles["Normal"],
        fontSize=72,
        textColor=CYAN_ACCENT,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        spaceAfter=10,
        leading=80,
    )

    # ==================== HEADER SECTION ====================

    story.append(Spacer(1, 1*cm))

    # Accent badge at top
    badge_data = [[Paragraph("AI-POWERED ANALYSIS", badge_style)]]
    badge_table = Table(badge_data, colWidths=[6*cm])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0, 0.706, 0.847, alpha=0.1)),
        ('BOX', (0, 0), (-1, -1), 2, CYAN_ACCENT),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    # Center the badge
    badge_wrapper = Table([[badge_table]], colWidths=[letter[0] - 5*cm])
    badge_wrapper.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(badge_wrapper)

    story.append(Spacer(1, 0.8*cm))

    # Main title
    story.append(Paragraph("PERFORMANCE", hero_style))
    story.append(Paragraph("ANALYSIS", hero_style))

    story.append(Spacer(1, 0.5*cm))

    # Horizontal line with accent color
    line_data = [[""]]
    line_table = Table(line_data, colWidths=[10*cm])
    line_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 3, CYAN_ACCENT),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))

    line_wrapper = Table([[line_table]], colWidths=[letter[0] - 5*cm])
    line_wrapper.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(line_wrapper)

    story.append(Spacer(1, 1.5*cm))

    # ==================== OVERALL SCORE SECTION ====================

    story.append(Paragraph("OVERALL SCORE", muted_style))
    story.append(Spacer(1, 0.3*cm))

    # Large score display
    score_value = analysis.get('overall_score', 0)
    max_score = analysis.get('max_score', 100)

    story.append(Paragraph(f"{score_value:.0f}", score_style))
    story.append(Paragraph(f"<font color='{MUTED_TEXT}'>OUT OF {max_score}</font>", muted_style))

    story.append(Spacer(1, 2*cm))

    # ==================== CATEGORY BREAKDOWN ====================

    story.append(Paragraph("PHASE BREAKDOWN", section_heading_style))
    story.append(Spacer(1, 0.5*cm))

    # Build table data
    table_data = []

    # Header row
    header_style_para = ParagraphStyle("HeaderText", parent=styles["Normal"],
                                       fontSize=11, textColor=DARK_BG,
                                       alignment=TA_CENTER, fontName="Helvetica-Bold")

    table_data.append([
        Paragraph("PHASE", header_style_para),
        Paragraph("SCORE", header_style_para),
        Paragraph("MAX", header_style_para),
        Paragraph("STATUS", header_style_para),
    ])

    # Data rows
    for cat in analysis.get('categories', []):
        for pose_data in cat.get('poses', []):
            pose_score = pose_data.get('score', 0)
            pose_max = pose_data.get('max_score', 100)
            pose_percentage = (pose_score / pose_max * 100) if pose_max > 0 else 0

            # Determine status
            if pose_percentage >= 70:
                status_text = "✓ GOOD"
                status_color = SUCCESS_GREEN
            elif pose_percentage >= 50:
                status_text = "○ OK"
                status_color = CYAN_ACCENT
            else:
                status_text = "✗ IMPROVE"
                status_color = WARNING_RED

            # Create paragraph objects
            name_para = Paragraph(f"<b>{pose_data.get('name', 'Unknown').upper()}</b>",
                ParagraphStyle("PhaseName", parent=styles["Normal"],
                              fontSize=11, textColor=LIGHT_TEXT,
                              alignment=TA_LEFT, fontName="Helvetica-Bold"))

            score_para = Paragraph(f"{pose_score:.0f}",
                ParagraphStyle("Score", parent=styles["Normal"],
                              fontSize=11, textColor=LIGHT_TEXT,
                              alignment=TA_CENTER, fontName="Helvetica"))

            max_para = Paragraph(f"{pose_max}",
                ParagraphStyle("Max", parent=styles["Normal"],
                              fontSize=11, textColor=MUTED_TEXT,
                              alignment=TA_CENTER, fontName="Helvetica"))

            status_para = Paragraph(status_text,
                ParagraphStyle("Status", parent=styles["Normal"],
                              fontSize=10, textColor=status_color,
                              alignment=TA_CENTER, fontName="Helvetica-Bold"))

            table_data.append([name_para, score_para, max_para, status_para])

    # Create table
    breakdown_table = Table(table_data,
                           colWidths=[7*cm, 2.5*cm, 2.5*cm, 3.5*cm],
                           repeatRows=1)

    breakdown_table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), CYAN_ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), DARK_BG),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

        # Data row styling
        ('BACKGROUND', (0, 1), (-1, -1), SURFACE_COLOR),
        ('TEXTCOLOR', (0, 1), (-1, -1), LIGHT_TEXT),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),

        # Borders (brutalist style - thick borders)
        ('BOX', (0, 0), (-1, -1), 3, BORDER_COLOR),
        ('LINEBELOW', (0, 0), (-1, 0), 2, DARK_BG),
        ('INNERGRID', (0, 1), (-1, -1), 1, BORDER_COLOR),

        # Alignment
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    story.append(breakdown_table)

    story.append(Spacer(1, 2*cm))

    # ==================== DETAILED ERRORS SECTION ====================

    # Check if there are errors to display
    has_errors = False
    for cat in analysis.get('categories', []):
        for pose_data in cat.get('poses', []):
            if pose_data.get('errors') and len(pose_data.get('errors', [])) > 0:
                has_errors = True
                break
        if has_errors:
            break

    if has_errors:
        story.append(Paragraph("IMPROVEMENT AREAS", section_heading_style))
        story.append(Spacer(1, 0.5*cm))

        for cat in analysis.get('categories', []):
            for pose_data in cat.get('poses', []):
                errors = pose_data.get('errors', [])
                if errors and len(errors) > 0:
                    # Phase title
                    phase_title_para = Paragraph(
                        f"<b>{pose_data.get('name', 'Unknown').upper()}</b>",
                        ParagraphStyle("PhaseTitle", parent=styles["Normal"],
                                      fontSize=14, textColor=CYAN_ACCENT,
                                      alignment=TA_LEFT, fontName="Helvetica-Bold",
                                      spaceAfter=8, spaceBefore=12)
                    )
                    story.append(phase_title_para)

                    # Error list
                    for idx, error in enumerate(errors, 1):
                        criterion = error.get('criterion', 'Unknown')
                        improvement = error.get('improvement', 'No suggestion available')
                        frequency = error.get('frequency', 0) * 100

                        # Create error card
                        error_text = (
                            f"<b>{idx}. {criterion.replace('_', ' ').title()}</b><br/>"
                            f"<font color='{MUTED_TEXT}'>Tip: {improvement}</font><br/>"
                            f"<font color='{MUTED_TEXT}' size='9'>Occurred in {frequency:.0f}% of frames</font>"
                        )

                        error_para = Paragraph(error_text,
                            ParagraphStyle("ErrorText", parent=styles["Normal"],
                                          fontSize=10, textColor=LIGHT_TEXT,
                                          alignment=TA_LEFT, fontName="Helvetica",
                                          leading=14))

                        error_card_data = [[error_para]]
                        error_card = Table(error_card_data, colWidths=[15*cm])
                        error_card.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, -1), SURFACE_COLOR),
                            ('BOX', (0, 0), (-1, -1), 2, BORDER_COLOR),
                            ('LEFTPADDING', (0, 0), (-1, -1), 12),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                            ('TOPPADDING', (0, 0), (-1, -1), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ]))

                        story.append(error_card)
                        story.append(Spacer(1, 0.3*cm))

    # ==================== BUILD PDF ====================

    print(f"PDF Generation - Building PDF with {len(story)} elements")
    doc.build(story, onFirstPage=add_page_decorations, onLaterPages=add_page_decorations)
    print(f"PDF Generation - Successfully created: {output_path}")
    return output_path
