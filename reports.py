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
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


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

        # Footer Separator Line
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 36, 576, 36)

        # Footer Text
        footer_text = "CONFIDENTIAL & PROPRIETARY — HEALTHSTACK ANALYTICS NETWORK"
        page_str = f"Page {self._pageNumber} of {page_count}"

        self.drawString(36, 24, footer_text)
        self.drawRightString(576, 24, page_str)
        self.restoreState()


def _get_column_name(df: pd.DataFrame, candidates: list) -> str:
    """Helper function to find matching column names case-insensitively."""
    if df is None or df.empty:
        return None
    
    # Exact check first
    for col in candidates:
        if col in df.columns:
            return col
            
    # Lowercase case-insensitive check
    df_cols_lower = {str(c).lower().strip(): c for c in df.columns}
    for col in candidates:
        if col.lower().strip() in df_cols_lower:
            return df_cols_lower[col.lower().strip()]
            
    return None


def generate_facility_pdf(
    selected_facility: str,
    df_appts: pd.DataFrame = None,
    df_sales: pd.DataFrame = None,
    df_consults: pd.DataFrame = None,
    df_lab: pd.DataFrame = None,
    df_clients: pd.DataFrame = None,
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
            Paragraph(str(selected_facility).title(), meta_val),
        ],
        [
            Paragraph("Security Classification:", meta_label),
            Paragraph("Confidential / Restricted", meta_val),
        ],
        [
            Paragraph("System Standard:", meta_label),
            Paragraph("EMR Performance Audit", meta_val),
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
    story.append(Spacer(1, 8))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=colors.HexColor("#0284C7"),
            spaceBefore=2,
            spaceAfter=8,
        )
    )

    story.append(
        Paragraph("Executive Operational & Clinical Summary", title_style)
    )
    story.append(
        Paragraph(
            f"Comprehensive performance audit for <b>{str(selected_facility).title()}</b>.",
            cell_style,
        )
    )
    story.append(Spacer(1, 10))

    # --- 2. Metric Aggregations ---
    total_appts = len(df_appts) if df_appts is not None and not df_appts.empty else 0

    # Total Consultations (Fallback to Appointments if Consults empty)
    if df_consults is not None and not df_consults.empty:
        total_consults = len(df_consults)
    else:
        total_consults = total_appts

    # Completed Appointments Resolution
    completed_appts = 0
    if df_appts is not None and not df_appts.empty:
        status_col = _get_column_name(df_appts, ["status", "appointmentStatus", "state", "encounter_status", "status_name"])
        if status_col:
            valid_statuses = ["COMPLETED", "SERVED", "FINAL", "APPROVED", "DONE", "CLOSED", "FULFILLED"]
            completed_appts = df_appts[
                df_appts[status_col].astype(str).str.upper().str.strip().isin(valid_statuses)
            ].shape[0]
            
            # Fallback if no specific status string matched but appts exist
            if completed_appts == 0 and total_appts > 0:
                completed_appts = total_appts
        else:
            completed_appts = total_appts

    # Laboratory Diagnostics Calculation
    total_labs = len(df_lab) if df_lab is not None and not df_lab.empty else 0

    # Pharmacy Revenue Calculation
    total_revenue = 0.0
    if df_sales is not None and not df_sales.empty:
        rev_col = _get_column_name(df_sales, ["lineRevenue", "revenue", "totalPrice", "amount", "total_revenue", "cost"])
        if rev_col:
            total_revenue = pd.to_numeric(df_sales[rev_col], errors="coerce").fillna(0.0).sum()

    # Patient Registrations Calculation
    total_registrations = len(df_clients) if df_clients is not None and not df_clients.empty else 0

    # --- 3. Executive KPI Scorecard Grid (3x2 Matrix) ---
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
            t = Table([[cell[0]], [cell[1]]], colWidths=[170])
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
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
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    story.append(kpi_grid_table)
    story.append(Spacer(1, 8))

    # --- 4. Pharmacy Section ---
    story.append(
        Paragraph("Pharmacy Operations & High-Volume Dispensing", section_style)
    )

    item_col = _get_column_name(df_sales, ["itemName", "drugName", "item_name", "product", "medication", "drug_description"])
    qty_col = _get_column_name(df_sales, ["qtySold", "quantity", "qty", "units", "dispensed_qty"])
    rev_col = _get_column_name(df_sales, ["lineRevenue", "revenue", "totalPrice", "amount", "total_revenue"])

    if df_sales is not None and not df_sales.empty and item_col and qty_col:
        df_sales[qty_col] = pd.to_numeric(df_sales[qty_col], errors="coerce").fillna(0)
        
        agg_dict = {qty_col: "sum"}
        if rev_col:
            df_sales[rev_col] = pd.to_numeric(df_sales[rev_col], errors="coerce").fillna(0.0)
            agg_dict[rev_col] = "sum"

        top_sales = (
            df_sales.groupby(item_col)
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
                    Paragraph(str(row[item_col]).title(), cell_style),
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
        story.append(med_table)
    else:
        story.append(
            Paragraph(
                "No pharmacy dispensing records available for this facility selection.",
                cell_style,
            )
        )

    story.append(Spacer(1, 8))

    # --- 5. Laboratory Diagnostics Section ---
    story.append(
        Paragraph("Laboratory Diagnostics & Test Orders", section_style)
    )

    lab_col = _get_column_name(
        df_lab, 
        ["testName", "investigationName", "serviceName", "test_name", "investigation", "test", "lab_test_name", "investigation_name"]
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
                    Paragraph(str(row[lab_col]).title(), cell_style),
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
        story.append(lab_table)
    else:
        story.append(
            Paragraph(
                "No laboratory diagnostic records available for this facility selection.",
                cell_style,
            )
        )

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes