import io
import os
from datetime import datetime
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic total page numbers and running footers."""

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
        self.setFillColor(colors.HexColor("#64748B"))

        # Printable width: 612 - 72 = 540 pt
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 36, 576, 36)

        footer_text = "CONFIDENTIAL & PROPRIETARY — HEALTHSTACK ANALYTICS NETWORK"
        page_str = f"Page {self._pageNumber} of {page_count}"

        self.drawString(36, 24, footer_text)
        self.drawRightString(576, 24, page_str)
        self.restoreState()


def _get_column_name(df: pd.DataFrame, candidates: list) -> str:
    """Helper function to find matching column names case-insensitively."""
    if df is None or df.empty:
        return None

    for col in candidates:
        if col in df.columns:
            return col

    df_cols_lower = {str(c).lower().strip(): c for c in df.columns}
    for col in candidates:
        if col.lower().strip() in df_cols_lower:
            return df_cols_lower[col.lower().strip()]

    return None


def generate_facility_pdf(
    selected_facility: str = "All Facilities",
    selected_department: str = "All Departments",
    selected_duration: str = "All Time",
    df_appts: pd.DataFrame = None,
    df_sales: pd.DataFrame = None,
    df_consults: pd.DataFrame = None,
    df_lab: pd.DataFrame = None,
    df_clients: pd.DataFrame = None,
    **kwargs
) -> bytes:
    """Generates an enterprise operational summary PDF with universal data schema resilience."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=54,
    )

    story = []
    styles = getSampleStyleSheet()

    # --- Typography Styles ---
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
    )

    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0284C7"),
        spaceBefore=10,
        spaceAfter=6,
    )

    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
    )

    meta_val = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0F172A"),
    )

    kpi_title_style = ParagraphStyle(
        "KPITitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )

    kpi_num_style = ParagraphStyle(
        "KPINum",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0F766E"),
        alignment=1,
    )

    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )

    cell_header = ParagraphStyle(
        "CellHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=colors.white,
    )

    # --- 1. Header Section ---
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        header_img = Image(logo_path, width=150, height=40)
    else:
        header_img = Paragraph("<b>HEALTHSTACK</b>", title_style)

    meta_text = [
        [
            Paragraph("Generated Date:", meta_label),
            Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M"), meta_val),
        ],
        [
            Paragraph("Target Facility:", meta_label),
            Paragraph(str(selected_facility or "All Facilities").title(), meta_val),
        ],
        [
            Paragraph("Department / Duration:", meta_label),
            Paragraph(f"{str(selected_department or 'All').title()} ({selected_duration})", meta_val),
        ],
        [
            Paragraph("Security / Standard:", meta_label),
            Paragraph("Confidential / EMR Audit", meta_val),
        ],
    ]

    meta_table = Table(meta_text, colWidths=[100, 130])
    meta_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )

    header_table = Table([[header_img, meta_table]], colWidths=[310, 230])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )

    story.append(header_table)
    story.append(Spacer(1, 6))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=colors.HexColor("#0284C7"),
            spaceBefore=2,
            spaceAfter=6,
        )
    )

    story.append(
        Paragraph("Executive Operational & Clinical Summary", title_style)
    )
    story.append(
        Paragraph(
            f"Comprehensive performance audit for <b>{str(selected_facility or 'All Facilities').title()}</b> — Filter: <i>{selected_department}</i> ({selected_duration}).",
            cell_style,
        )
    )
    story.append(Spacer(1, 10))

    # --- 2. Metric Aggregations ---
    total_appts = len(df_appts) if df_appts is not None and not df_appts.empty else 0

    if df_consults is not None and not df_consults.empty:
        total_consults = len(df_consults)
    else:
        total_consults = total_appts

    completed_appts = 0
    if df_appts is not None and not df_appts.empty:
        status_col = _get_column_name(
            df_appts, ["status", "appointmentStatus", "state", "encounter_status", "status_name"]
        )
        if status_col:
            valid_statuses = [
                "COMPLETED", "SERVED", "FINAL", "APPROVED",
                "DONE", "CLOSED", "FULFILLED", "CHECKED OUT", "OTHER (CHECKED OUT)"
            ]
            completed_appts = df_appts[
                df_appts[status_col].astype(str).str.upper().str.strip().isin(valid_statuses)
            ].shape[0]

            if completed_appts == 0 and total_appts > 0:
                completed_appts = total_appts
        else:
            completed_appts = total_appts

    total_labs = len(df_lab) if df_lab is not None and not df_lab.empty else 0

    total_revenue = 0.0
    if df_sales is not None and not df_sales.empty:
        rev_col = _get_column_name(
            df_sales, ["lineRevenue", "revenue", "totalPrice", "amount", "total_revenue", "cost"]
        )
        if rev_col:
            total_revenue = pd.to_numeric(df_sales[rev_col], errors="coerce").fillna(0.0).sum()

    total_registrations = len(df_clients) if df_clients is not None and not df_clients.empty else 0

    # --- 3. Executive KPI Scorecard Grid ---
    kpi_matrix = [
        [
            [
                Paragraph("TOTAL APPOINTMENTS", kpi_title_style),
                Paragraph(f"{total_appts:,}", kpi_num_style),
            ],
            [
                Paragraph("COMPLETED VISITS", kpi_title_style),
                Paragraph(f"{completed_appts:,}", kpi_num_style),
            ],
            [
                Paragraph("CLINICAL CONSULTATIONS", kpi_title_style),
                Paragraph(f"{total_consults:,}", kpi_num_style),
            ],
        ],
        [
            [
                Paragraph("PHARMACY REVENUE", kpi_title_style),
                Paragraph(f"NGN {total_revenue:,.2f}", kpi_num_style),
            ],
            [
                Paragraph("LAB DIAGNOSTICS", kpi_title_style),
                Paragraph(f"{total_labs:,}", kpi_num_style),
            ],
            [
                Paragraph("PATIENT REGISTRATIONS", kpi_title_style),
                Paragraph(f"{total_registrations:,}", kpi_num_style),
            ],
        ],
    ]

    formatted_kpi_cells = []
    for row in kpi_matrix:
        row_cells = []
        for cell in row:
            t = Table([[cell[0]], [cell[1]]], colWidths=[174])
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            row_cells.append(t)
        formatted_kpi_cells.append(row_cells)

    kpi_grid_table = Table(formatted_kpi_cells, colWidths=[180, 180, 180])
    kpi_grid_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    story.append(kpi_grid_table)
    story.append(Spacer(1, 10))

    # --- 4. Visual Analytics Section (Page 1 Charts) ---
    if df_appts is not None and not df_appts.empty:
        story.append(Paragraph("Clinical Workload & Peak Day Demand Analytics", section_style))

        # CHART 1: Vertical Bar Chart — Specialty Department Distribution
        dept_col = _get_column_name(df_appts, ["type", "department", "appointment_type", "clinic"])
        if dept_col:
            dept_counts = df_appts[dept_col].value_counts().head(5)
            if not dept_counts.empty:
                chart_drawing = Drawing(540, 150)
                
                # Title & Axis Labels with Clean Vertical Offsets
                chart_drawing.add(String(55, 138, "Top Specialty Departments by Appointment Volume", fontName="Helvetica-Bold", fontSize=8, fillColor=colors.HexColor("#0F172A")))
                chart_drawing.add(String(270, -18, "Medical Specialty / Unit", fontName="Helvetica-Bold", fontSize=7, textAnchor="middle", fillColor=colors.HexColor("#475569")))
                chart_drawing.add(String(10, 75, "Appointments", fontName="Helvetica-Bold", fontSize=7, textAnchor="middle", fillColor=colors.HexColor("#475569")))

                bc = VerticalBarChart()
                bc.x = 55
                bc.y = 22
                bc.height = 100
                bc.width = 440
                bc.data = [dept_counts.values.tolist()]
                
                max_val = max(dept_counts.values) if len(dept_counts.values) > 0 else 10
                bc.valueAxis.valueMin = 0
                bc.valueAxis.valueMax = max_val * 1.25
                bc.valueAxis.valueStep = max(1, int(max_val / 4))
                bc.valueAxis.labels.fontSize = 7
                
                cat_names = [str(x)[:14] for x in dept_counts.index]
                bc.categoryAxis.categoryNames = cat_names
                bc.categoryAxis.labels.fontSize = 7.5
                bc.categoryAxis.labels.dy = -10
                bc.bars[0].fillColor = colors.HexColor("#0284C7")
                
                chart_drawing.add(bc)

                # Draw value annotations above each vertical bar
                num_bars = len(dept_counts)
                bar_width = bc.width / max(1, num_bars)
                for i, val in enumerate(dept_counts.values):
                    x_center = bc.x + (i + 0.5) * bar_width
                    y_pos = bc.y + (val / bc.valueAxis.valueMax) * bc.height + 4
                    chart_drawing.add(
                        String(x_center, y_pos, f"{val:,}", fontName="Helvetica-Bold", fontSize=7, textAnchor="middle", fillColor=colors.HexColor("#0F172A"))
                    )

                story.append(chart_drawing)
                story.append(Spacer(1, 14))

        # CHART 2: Horizontal Bar Chart — Day of Week Distribution
        date_col = _get_column_name(df_appts, ["date", "createdAt", "appointment_date"])
        if date_col:
            df_appts_copy = df_appts.copy()
            df_appts_copy['clean_date'] = pd.to_datetime(df_appts_copy[date_col], errors='coerce')
            df_valid = df_appts_copy.dropna(subset=['clean_date'])
            
            if not df_valid.empty:
                days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_counts = df_valid['clean_date'].dt.day_name().value_counts().reindex(days_order).fillna(0)

                chart_day = Drawing(540, 145)
                chart_day.add(String(65, 133, "Appointment Demand by Day of Week", fontName="Helvetica-Bold", fontSize=8, fillColor=colors.HexColor("#0F172A")))
                chart_day.add(String(270, -12, "Total Visits Handled", fontName="Helvetica-Bold", fontSize=7, textAnchor="middle", fillColor=colors.HexColor("#475569")))

                hc = HorizontalBarChart()
                hc.x = 65
                hc.y = 18
                hc.height = 100
                hc.width = 420
                hc.data = [day_counts.values[::-1].tolist()]
                
                max_day_val = max(day_counts.values) if max(day_counts.values) > 0 else 10
                hc.valueAxis.valueMin = 0
                hc.valueAxis.valueMax = max_day_val * 1.25
                hc.valueAxis.valueStep = max(1, int(max_day_val / 4))
                hc.valueAxis.labels.fontSize = 7
                
                hc.categoryAxis.categoryNames = days_order[::-1]
                hc.categoryAxis.labels.fontSize = 7.5
                hc.categoryAxis.labels.dx = -5
                hc.bars[0].fillColor = colors.HexColor("#0F766E")

                chart_day.add(hc)

                # Draw value annotations to the right of each horizontal bar
                reversed_vals = day_counts.values[::-1]
                num_hbars = len(reversed_vals)
                hbar_height = hc.height / max(1, num_hbars)
                for i, val in enumerate(reversed_vals):
                    y_center = hc.y + (i + 0.3) * hbar_height
                    x_pos = hc.x + (val / hc.valueAxis.valueMax) * hc.width + 4
                    chart_day.add(
                        String(x_pos, y_center, f"{int(val):,}", fontName="Helvetica-Bold", fontSize=7, textAnchor="start", fillColor=colors.HexColor("#0F172A"))
                    )

                story.append(chart_day)

    # --- Force PageBreak so Pharmacy & Lab tables move cleanly to Page 2 ---
    story.append(PageBreak())

    # --- 5. Pharmacy Section (Page 2) ---
    pharmacy_elements = [
        Paragraph("Pharmacy Operations & High-Volume Dispensing", section_style)
    ]

    item_col = _get_column_name(
        df_sales, ["itemName", "drugName", "item_name", "product", "medication", "drug_description"]
    )
    qty_col = _get_column_name(
        df_sales, ["qtySold", "quantity", "qty", "units", "dispensed_qty"]
    )
    rev_col = _get_column_name(
        df_sales, ["lineRevenue", "revenue", "totalPrice", "amount", "total_revenue"]
    )

    if df_sales is not None and not df_sales.empty and item_col and qty_col:
        df_sales_copy = df_sales.copy()
        df_sales_copy[qty_col] = pd.to_numeric(df_sales_copy[qty_col], errors="coerce").fillna(0)

        agg_dict = {qty_col: "sum"}
        if rev_col:
            df_sales_copy[rev_col] = pd.to_numeric(df_sales_copy[rev_col], errors="coerce").fillna(0.0)
            agg_dict[rev_col] = "sum"

        top_sales = (
            df_sales_copy.groupby(item_col)
            .agg(agg_dict)
            .reset_index()
            .sort_values(by=qty_col, ascending=False)
            .head(5)
        )

        med_data = [
            [
                Paragraph("Medication Description", cell_header),
                Paragraph("Units Sold", cell_header),
                Paragraph("Total Revenue (NGN)", cell_header),
            ]
        ]

        for _, row in top_sales.iterrows():
            rev_val = f"NGN {row[rev_col]:,.2f}" if rev_col else "Subsidized / Free"
            med_data.append(
                [
                    Paragraph(str(row[item_col] or "Unknown Drug").title(), cell_style),
                    Paragraph(f"{int(row[qty_col]):,}", cell_style),
                    Paragraph(rev_val, cell_style),
                ]
            )

        med_table = Table(med_data, colWidths=[280, 120, 140])
        med_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.HexColor("#F0FDF4"), colors.white],
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ]
            )
        )
        pharmacy_elements.append(med_table)
    else:
        pharmacy_elements.append(
            Paragraph(
                "No pharmacy dispensing records available for this facility selection.",
                cell_style,
            )
        )

    story.append(KeepTogether(pharmacy_elements))
    story.append(Spacer(1, 14))

    # --- 6. Laboratory Diagnostics Section (Page 2) ---
    lab_elements = [
        Paragraph("Laboratory Diagnostics & Test Orders", section_style)
    ]

    lab_col = _get_column_name(
        df_lab,
        ["testName", "investigationName", "serviceName", "test_name", "investigation", "test", "lab_test_name", "investigation_name"],
    )

    if df_lab is not None and not df_lab.empty and lab_col:
        top_labs = (
            df_lab.groupby(lab_col)
            .size()
            .reset_index(name="test_count")
            .sort_values(by="test_count", ascending=False)
            .head(5)
        )

        lab_data = [
            [
                Paragraph("Diagnostic Test Name", cell_header),
                Paragraph("Total Orders Handled", cell_header),
            ]
        ]

        for _, row in top_labs.iterrows():
            lab_data.append(
                [
                    Paragraph(str(row[lab_col] or "Unknown Diagnostic").title(), cell_style),
                    Paragraph(f"{int(row['test_count']):,}", cell_style),
                ]
            )

        lab_table = Table(lab_data, colWidths=[380, 160])
        lab_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284C7")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.HexColor("#F0F9FF"), colors.white],
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ]
            )
        )
        lab_elements.append(lab_table)
    else:
        lab_elements.append(
            Paragraph(
                "No laboratory diagnostic records available for this facility selection.",
                cell_style,
            )
        )

    story.append(KeepTogether(lab_elements))

    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
