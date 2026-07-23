"""Build the submission-ready academic report from the verified project artifacts."""

from __future__ import annotations

import csv
import math
import sys
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "outputs"
CHARTS = OUT / "charts"
DIAGRAMS = OUT / "diagrams"
DOCS = ROOT / "docs"
REPORT = DOCS / "Ryan_Final_Project_Report.docx"

BLUE = "174A7E"
MID_BLUE = "2E74B5"
LIGHT_BLUE = "DDEBF7"
PALE = "F2F4F7"
INK = "202A35"
MUTED = "5B6573"
WHITE = "FFFFFF"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    element = OxmlElement("w:tblHeader")
    element.set(qn("w:val"), "true")
    tr_pr.append(element)


def set_cell_text(cell, value: object, bold: bool = False, color: str = INK) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(str(value))
    run.bold = bold
    run.font.name = "Calibri"
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor.from_string(color)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def add_table(doc: Document, headers: list[str], rows: list[list[object]], widths=None, caption=None):
    if caption:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(caption)
        run.bold = True
        run.font.size = Pt(9)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    header = table.rows[0]
    set_repeat_table_header(header)
    for i, title in enumerate(headers):
        set_cell_text(header.cells[i], title, bold=True, color=WHITE)
        set_cell_shading(header.cells[i], BLUE)
    for row_no, values in enumerate(rows):
        row = table.add_row()
        for i, value in enumerate(values):
            set_cell_text(row.cells[i], value)
            if row_no % 2:
                set_cell_shading(row.cells[i], PALE)
    if widths:
        for row in table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = Inches(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_caption(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor.from_string(MUTED)


def add_figure(doc: Document, path: Path, caption: str, width=6.35) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(width))
    add_caption(doc, caption)


def add_bullets(doc: Document, items: list[str], numbered=False) -> None:
    style = "List Number" if numbered else "List Bullet"
    for item in items:
        p = doc.add_paragraph(style=style)
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.first_line_indent = Inches(-0.18)
        p.add_run(item)


def add_heading(doc: Document, text: str, level=1) -> None:
    doc.add_heading(text, level=level)


def add_para(doc: Document, text: str, bold_lead: str | None = None) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if bold_lead and text.startswith(bold_lead):
        p.add_run(bold_lead).bold = True
        p.add_run(text[len(bold_lead):])
    else:
        p.add_run(text)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, end])


def add_toc(doc: Document) -> None:
    p = doc.add_paragraph()
    run = p.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "Right-click and choose Update Field if the table is not populated."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, placeholder, end])


def configure_document(doc: Document) -> None:
    section = doc.sections[0]
    # Narrative-proposal preset used for the formal academic report.
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.333

    for name, size, color, before, after in [
        ("Title", 24, BLUE, 0, 12),
        ("Heading 1", 16, BLUE, 16, 8),
        ("Heading 2", 13, MID_BLUE, 12, 6),
        ("Heading 3", 11, INK, 8, 4),
    ]:
        style = doc.styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    for sec in doc.sections:
        hp = sec.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = hp.add_run("MAFUTAPLAN  |  NAIROBI FUEL PRICE PROJECT")
        r.font.size = Pt(8)
        r.font.bold = True
        r.font.color.rgb = RGBColor.from_string(MUTED)
        add_page_number(sec.footer.paragraphs[0])

    settings = doc.settings._element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)


def generate_assets() -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    DIAGRAMS.mkdir(parents=True, exist_ok=True)
    history = pd.read_csv(DATA / "nairobi_price_history.csv", parse_dates=["Cycle"])
    components = pd.read_csv(DATA / "price_components.csv")
    component_history = pd.read_csv(DATA / "nairobi_component_history.csv", parse_dates=["Effective_From"])

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for column, label, color in [
        ("Super_Petrol", "Super Petrol", "#174A7E"),
        ("Diesel", "Diesel", "#E67E22"),
        ("Kerosene", "Kerosene", "#2E8B57"),
    ]:
        ax.plot(history["Cycle"], history[column], label=label, linewidth=2, color=color)
    ax.set(title="Nairobi EPRA Maximum Retail Pump Prices", ylabel="KES per litre", xlabel="Monthly cycle")
    ax.legend(ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "figure_3_1_fuel_price_trends.png", dpi=190)
    plt.close(fig)

    pivot = components.pivot(index="Component", columns="Fuel", values="KES_Per_Litre").fillna(0)
    order = [c for c in ["Super Petrol", "Diesel", "Kerosene"] if c in pivot.columns]
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    bottom = [0.0] * len(order)
    colors = plt.cm.tab20.colors
    for idx, (component, row) in enumerate(pivot.iterrows()):
        values = [float(row.get(fuel, 0)) for fuel in order]
        ax.bar(order, values, bottom=bottom, label=component, color=colors[idx % len(colors)])
        bottom = [a + b for a, b in zip(bottom, values)]
    ax.set(title="Published Nairobi Pump-Price Composition", ylabel="KES per litre")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "figure_3_2_price_components.png", dpi=190)
    plt.close(fig)

    aggregate_columns = ["Landed_Cost", "Distribution_Storage", "Margins", "Stabilization_Adjustment", "Taxes_Levies"]
    means = component_history.groupby("Fuel")[aggregate_columns].mean().reindex(["Super Petrol", "Diesel", "Kerosene"])
    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    means.plot(kind="bar", stacked=True, ax=ax, color=["#E67E22", "#4C78A8", "#72B7B2", "#B279A2", "#174A7E"])
    ax.set(title="Average Reviewed EPRA Nairobi Cost Composition", ylabel="KES per litre", xlabel="")
    ax.tick_params(axis="x", rotation=0)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "figure_3_3_component_history.png", dpi=190)
    plt.close(fig)

    metrics = pd.read_csv(ROOT / "appendices" / "Model_Metrics.csv")
    fig, ax = plt.subplots(figsize=(9.2, 4.7))
    x = range(len(metrics))
    ax.bar([i - 0.18 for i in x], metrics["Holdout_MAE"], width=0.36, label="Selected-method MAE", color="#174A7E")
    ax.bar([i + 0.18 for i in x], metrics["Baseline_MAE"], width=0.36, label="Baseline MAE", color="#9AA5B1")
    ax.set_xticks(list(x), metrics["Fuel"])
    ax.set(ylabel="KES per litre", title="Untouched Ten-Cycle Holdout Performance")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(CHARTS / "figure_4_1_holdout_mae.png", dpi=190)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.3))
    ax.axis("off")
    boxes = [
        (0.03, 0.33, 0.18, 0.34, "Official EPRA PDFs\nand live table"),
        (0.28, 0.33, 0.18, 0.34, "Validated CSV\ndata layer"),
        (0.54, 0.33, 0.18, 0.34, "Reconstruction, scenario,\nforecast and calculators"),
        (0.79, 0.33, 0.18, 0.34, "Six-workflow\nStreamlit interface"),
    ]
    for x0, y0, w, h, label in boxes:
        ax.add_patch(plt.Rectangle((x0, y0), w, h, facecolor="#DDEBF7", edgecolor="#174A7E", linewidth=1.5))
        ax.text(x0 + w / 2, y0 + h / 2, label, ha="center", va="center", fontsize=10, weight="bold", color="#174A7E")
    for a, b in zip(boxes, boxes[1:]):
        ax.annotate("", xy=(b[0], 0.5), xytext=(a[0] + a[2], 0.5), arrowprops=dict(arrowstyle="->", color="#5B6573", lw=1.7))
    ax.text(0.5, 0.92, "MafutaPlan Logical Architecture", ha="center", va="center", fontsize=15, weight="bold", color="#174A7E")
    fig.tight_layout()
    fig.savefig(DIAGRAMS / "system_architecture_diagram.png", dpi=190, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axis("off")
    nodes = [
        (0.04, 0.62, "Past Nairobi\npump prices"),
        (0.04, 0.19, "Reviewed EPRA\ncomponent panel"),
        (0.39, 0.40, "Hybrid decision-\nsupport services"),
        (0.73, 0.62, "Next-cycle\nexperimental forecast"),
        (0.73, 0.19, "Reconstruction, scenarios\nand planning decisions"),
    ]
    for x0, y0, label in nodes:
        ax.add_patch(plt.Rectangle((x0, y0), 0.22, 0.2, facecolor="#F2F4F7", edgecolor="#2E74B5", linewidth=1.5))
        ax.text(x0 + 0.11, y0 + 0.1, label, ha="center", va="center", fontsize=10, weight="bold")
    for start, end in [(nodes[0], nodes[2]), (nodes[1], nodes[2]), (nodes[2], nodes[3]), (nodes[3], nodes[4])]:
        ax.annotate("", xy=(end[0], end[1] + 0.1), xytext=(start[0] + 0.22, start[1] + 0.1), arrowprops=dict(arrowstyle="->", color="#174A7E", lw=1.5))
    ax.text(0.5, 0.94, "Conceptual Framework", ha="center", fontsize=15, weight="bold", color="#174A7E")
    fig.tight_layout()
    fig.savefig(DIAGRAMS / "conceptual_framework.png", dpi=190, bbox_inches="tight")
    plt.close(fig)


def front_matter(doc: Document) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Inches(0.6)
    r = p.add_run("JOMO KENYATTA UNIVERSITY OF\nAGRICULTURE AND TECHNOLOGY")
    r.bold = True
    r.font.size = Pt(14)
    r.font.color.rgb = RGBColor.from_string(BLUE)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Inches(0.8)
    r = p.add_run("DESIGN AND IMPLEMENTATION OF A HYBRID COST-BASED MODEL FOR\nFORECASTING REGULATED FUEL PRICES IN NAIROBI, KENYA")
    r.bold = True
    r.font.size = Pt(24)
    r.font.color.rgb = RGBColor.from_string(BLUE)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MAFUTAPLAN")
    r.bold = True
    r.font.size = Pt(15)
    r.font.color.rgb = RGBColor.from_string(MID_BLUE)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Inches(0.8)
    p.add_run("RYAN ALFRED NYAMBATI\nSCT222-0195/2021").bold = True
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Inches(0.65)
    p.add_run("A project report submitted in partial fulfilment of the requirements for the award of a Bachelor's degree at Jomo Kenyatta University of Agriculture and Technology.")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Inches(0.55)
    p.add_run("JULY 2026").bold = True
    doc.add_page_break()

    add_heading(doc, "DECLARATION", 1)
    add_para(doc, "I declare that this project report is my original work and has not been submitted to any other university for an academic award. All sources used have been acknowledged in the text and reference list.")
    doc.add_paragraph("Student: Ryan Alfred Nyambati     Signature: __________________     Date: ______________")
    doc.add_paragraph("Supervisor: ____________________     Signature: __________________     Date: ______________")
    doc.add_page_break()
    add_heading(doc, "DEDICATION", 1)
    add_para(doc, "This work is dedicated to my family, lecturers, classmates, and everyone who supported my education and encouraged the responsible use of computing to solve practical Kenyan problems.")
    doc.add_page_break()
    add_heading(doc, "ACKNOWLEDGEMENT", 1)
    add_para(doc, "I thank God for the strength to complete this project. I am grateful to my supervisor and the lecturers of Jomo Kenyatta University of Agriculture and Technology for their academic guidance. I also acknowledge the Energy and Petroleum Regulatory Authority and the Kenya National Bureau of Statistics for publishing the official information that made a transparent, evidence-based prototype possible. Finally, I thank my family and colleagues for their support during analysis, implementation, and testing.")
    doc.add_page_break()
    add_heading(doc, "ABSTRACT", 1)
    add_para(doc, "Fuel-price changes affect household budgets, transport operators, delivery businesses, and public planning. A defensible prediction system must account for the fact that Kenya currently imports refined petroleum products and that the Nairobi pump price includes more than the international product cost. This project designed and implemented MafutaPlan, a Nairobi-focused decision-support system that follows the regulated journey from international procurement and Mombasa landing through pipeline transport, depot delivery, margins, taxes, levies, stabilization, and the final retail cap.")
    add_para(doc, "The implementation uses 55 continuous monthly Nairobi pump-price cycles from January 2022 to July 2026 and a reviewed panel of 33 fuel-cycle component records from 11 official EPRA Annex releases. Twenty comparable records were independently matched against EPRA's live pump-price table. Every component record contains an official PDF link and reconstructs the corresponding Nairobi retail price with zero error after signed stabilization reconciliation and rounding. Forecast features remain restricted to information known before the target cycle. Five methods are compared through expanding-window selection and an untouched final ten-cycle holdout.")
    add_para(doc, "The previous-cycle baseline won for all three products, showing that regression is evaluated but not forced to win. MafutaPlan therefore separates three analytical layers: deterministic official-price reconstruction, a conservative statistical next-cycle forecast, and a user-controlled cost scenario. The interface provides six workflows and automated tests verify data scope, provenance, cost arithmetic, leakage controls, model evaluation, and output creation. The study concludes that the strongest contribution is an auditable hybrid information system rather than an unsupported claim that a small component sample can precisely predict future regulatory decisions.")
    p = doc.add_paragraph()
    p.add_run("Keywords: ").bold = True
    p.add_run("fuel prices, Nairobi, EPRA, landed cost, price reconstruction, regression, decision support, Streamlit")
    doc.add_page_break()
    add_heading(doc, "TABLE OF CONTENTS", 1)
    add_toc(doc)
    doc.add_page_break()
    add_heading(doc, "LIST OF ABBREVIATIONS", 1)
    add_table(doc, ["Abbreviation", "Meaning"], [
        ["EPRA", "Energy and Petroleum Regulatory Authority"],
        ["KPC", "Kenya Pipeline Company"],
        ["KES", "Kenya shilling"], ["KNBS", "Kenya National Bureau of Statistics"],
        ["PMS", "Premium Motor Spirit (Super Petrol)"], ["AGO", "Automotive Gas Oil (Diesel)"],
        ["DPK / IK", "Dual Purpose Kerosene / Illuminating Kerosene"], ["OCR", "Optical character recognition"],
        ["MAE", "Mean absolute error"], ["RMSE", "Root mean squared error"],
        ["CSV", "Comma-separated values"], ["UI", "User interface"],
        ["RBF", "Road Maintenance Levy Fund"], ["VAT", "Value Added Tax"],
    ], widths=[1.4, 5.2])
    doc.add_page_break()


def chapter_one(doc: Document) -> None:
    add_heading(doc, "CHAPTER ONE: INTRODUCTION", 1)
    add_heading(doc, "1.1 Background of the Study", 2)
    add_para(doc, "Petroleum products remain important inputs to mobility, agriculture, commerce, electricity backup, and household activity in Kenya. A change in the pump price can affect the direct cost of driving and the indirect cost of goods moved by road. Kenya applies a regulated maximum retail price framework administered by EPRA. Price notices normally identify an effective period and maximum price for each product and town. The figures are therefore regulatory ceilings, not a guarantee that every station sells at exactly the same value.")
    add_para(doc, "The announcement alone does not answer common planning questions. A motorist may ask how much 35 litres will cost, a household may ask how many litres a fixed budget can purchase, and a delivery operator may need to combine distance, vehicle efficiency, and traffic allowance. At the same time, students and policy readers may wish to understand how product cost, taxes, levies, margins, and other adjustments contribute to a published pump price. These needs motivated a combined evidence, calculation, and forecasting system rather than a stand-alone prediction form.")
    add_para(doc, "Kenya's refinery ceased crude-oil processing in 2013, so the present project follows imported refined Super Petrol, Diesel, and Kerosene rather than assuming local crude refining. Forecasting the regulated pump price is difficult because the observed sequence reflects procurement costs, exchange rates, ocean and port charges, Mombasa-to-Nairobi transport, taxes, margins, stabilization, subsidies, and revisions. A small monthly data set can make flexible models appear accurate in-sample while generalising poorly; the project therefore combines regulated-price reconstruction with a time-ordered forecast experiment.")
    add_heading(doc, "1.2 Problem Statement", 2)
    add_para(doc, "Existing price notices provide authoritative numbers but do not provide one compact workflow for tracing a litre from landed product to Nairobi, validating each source, reconstructing the cap, testing a forecast, and converting prices into personal costs. A price-only prototype would also fail to answer why two cycles change differently when landed cost, taxes, distribution or stabilization move. A credible degree project therefore requires one town, real official component data, an explicit revision policy, reproducible cost arithmetic, leakage-safe modelling, and honest uncertainty communication.")
    add_heading(doc, "1.3 Proposed Solution", 2)
    add_para(doc, "MafutaPlan is a Nairobi-only Streamlit application backed by validated CSV files and testable Python services. It presents the complete refined-product journey, reconstructs multiple official EPRA price build-ups, calculates fuel and journey costs, compares leakage-safe forecasting methods, and runs declared what-if component scenarios. Source and OCR audit registers make the evidence inspectable, while the application keeps official facts, deterministic calculations, statistical forecasts, and scenarios visually separate.")
    add_heading(doc, "1.4 Main Objective", 2)
    add_para(doc, "To design, implement, and evaluate a hybrid cost-based decision-support system that explains, reconstructs, and cautiously forecasts regulated fuel prices in Nairobi using traceable official data.")
    add_heading(doc, "1.5 Specific Objectives", 2)
    add_bullets(doc, [
        "To compile and validate a continuous Nairobi monthly price history and a reviewed multi-cycle EPRA component panel.",
        "To model the real imported-product journey through Mombasa handling, pipeline transport, Nairobi distribution, margins, taxes, and stabilization.",
        "To reconstruct official Nairobi prices from published component groups and measure reconciliation error.",
        "To implement current-price, budget-to-litres, litres-to-cost, and journey-cost tools.",
        "To compare a transparent baseline and selected regression or ensemble methods using time-ordered validation.",
        "To evaluate the selected method once on a final untouched holdout and communicate uncertainty honestly.",
        "To provide source inventory, OCR audit, live-table comparison, documentation, notebook, and automated tests suitable for academic review.",
    ])
    add_heading(doc, "1.6 Research Questions", 2)
    add_bullets(doc, [
        "Which costs connect an imported refined petroleum product to the final regulated Nairobi pump price?",
        "Can reviewed EPRA component groups reconstruct published Nairobi retail prices accurately?",
        "How can official Nairobi pump-price records be structured so that revisions and sources remain auditable?",
        "Which candidate method provides the lowest expanding-window error before the final holdout?",
        "How well does the selected method perform on the untouched final ten monthly cycles?",
        "Can one interface turn regulated prices into useful cost and journey estimates without overstating forecast certainty?",
    ], numbered=True)
    add_heading(doc, "1.7 Justification for Selecting Nairobi", 2)
    add_para(doc, "Nairobi is the most practical town for this project. It is consistently present in EPRA price notices and acts as a widely reported reference market. Selecting it maximises source continuity, makes manual cross-checking easier, and aligns the application with a large, diverse user base including private motorists, public-service operators, logistics businesses, students, and households. A multi-town design would require verified distribution-cost differences for every location and would multiply missing-data and interface risks without improving the core forecasting experiment. Nairobi therefore makes the project easier to complete rigorously, not merely easier to demonstrate.")
    add_heading(doc, "1.8 Scope", 2)
    add_para(doc, "The geographical scope is Nairobi. The product scope is Super Petrol, Diesel, and Kerosene. The statistical input contains 55 monthly cycles from January 2022 through July 2026; the reviewed component panel contains 33 rows across 11 official Annex cycles. The current record covers 15 July to 14 August 2026 and the experimental target is August 2026. The system is a local web prototype and does not publish, transact, or replace official EPRA notices.")
    add_heading(doc, "1.9 Limitations and Delimitations", 2)
    add_para(doc, "The price series is short and policy-sensitive, while the reviewed component panel is shorter and discontinuous because several official Annex scans are technically degraded. The current next-cycle forecast therefore remains price-lag based. Components support exact reconstruction, historical explanation, and declared scenarios; they are not misrepresented as known future inputs. The system does not claim to forecast future taxes, subsidies, stabilization or emergency revisions.")
    add_heading(doc, "1.10 Significance of the Study", 2)
    add_para(doc, "For end users, the project converts a price ceiling into concrete expenditure estimates. For academic reviewers, it demonstrates source governance, time-aware evaluation, baseline comparison, modular implementation, and testing. For future researchers, the revision audit trail and source register provide a reproducible foundation that can be extended when more official observations become available.")
    doc.add_page_break()


def chapter_two(doc: Document) -> None:
    add_heading(doc, "CHAPTER TWO: LITERATURE REVIEW", 1)
    add_heading(doc, "2.1 Introduction", 2)
    add_para(doc, "This chapter reviews the regulatory context, determinants of retail fuel prices, forecasting alternatives, validation practices, uncertainty communication, and usability considerations relevant to the project. The review focuses on concepts that directly informed system design.")
    add_heading(doc, "2.2 Kenya's Maximum Retail Price Framework", 2)
    add_para(doc, "EPRA publishes maximum retail petroleum prices under the applicable legal and regulatory framework. Its pump-price formula describes a build-up involving landed cost, storage and distribution charges, taxes and levies, wholesale and dealer margins, and relevant adjustments. The resulting prices vary by town because transport and distribution costs differ. This supports the decision to model one town rather than treat Kenyan prices as geographically identical (EPRA, 2026a).")
    add_para(doc, "Official values are effective for specified periods and can be revised. The April and May 2026 episodes demonstrate that a dataset should distinguish an original announcement from the price that finally prevailed. Replacing a revised observation without retaining the original would weaken auditability; keeping the original as the model target would misrepresent the price experienced after the revision. The project resolves the tension through separate revision and modelling tables.")
    add_heading(doc, "2.3 Petroleum Supply Journey to Nairobi", 2)
    add_para(doc, "Crude oil is extracted, transported and refined internationally into finished products such as PMS, AGO and DPK. Kenya's Mombasa refinery stopped processing crude oil in 2013; the present domestic supply path therefore begins with imported refined petroleum products rather than a local crude-refining stage. Procurement values include the international product price, freight or premium, letters of credit and financing, marine insurance and war-risk charges, quality certification, port and jetty handling, inspection, allowable ocean losses and other prudent import costs specified in the pricing regulations.")
    add_para(doc, "After landing in Mombasa, product enters primary storage and the Kenya Pipeline Company network. The Nairobi build-up recognizes pipeline transport, allowable pipeline and depot losses, storage, delivery to retail stations within the regulated radius, importer or wholesale margin, dealer margin, excise duty, road and petroleum levies, railway development levy, anti-adulteration levy where applicable, import declaration and merchant-shipping charges, VAT, and any approved stabilization deficit or surplus. This end-to-end chain is the reason the project cannot use crude oil or landed cost alone as the prediction target.")
    add_heading(doc, "2.4 Drivers and Structural Breaks", 2)
    add_para(doc, "Retail prices may respond to imported refined-product costs, foreign exchange, freight, financing, taxes, levies, local distribution expenses, margins, subsidies, and stabilization. Inflation reports from KNBS provide useful contextual cross-checks, but correlation does not imply that a value is available at the moment a forecast is made. Policy interventions can create structural breaks that are not learnable from price lags alone. Consequently, a forecast based only on historical pump prices should be interpreted as a conservative statistical extrapolation.")
    add_heading(doc, "2.5 Forecasting Approaches", 2)
    add_para(doc, "A previous-cycle or persistence forecast assumes that the next value equals the latest observed value. It has no fitted coefficients, is easy to explain, and can be difficult to beat when regulated prices remain unchanged for several cycles. Linear regression estimates an additive relationship between engineered time features and the target. Ridge regression adds coefficient shrinkage, which can reduce instability in small or correlated designs. Random forests combine decorrelated decision trees and can capture non-linear relationships, while gradient boosting sequentially corrects errors. Flexible models, however, require enough representative observations to avoid overfitting.")
    add_para(doc, "The project deliberately does not assume that machine learning must win. Hyndman and Athanasopoulos argue that forecasts should be evaluated against simple benchmarks and with procedures matching the intended use. This principle is especially important for a 55-observation policy-sensitive series. Candidate complexity is therefore bounded, hyperparameters are fixed in advance, and the baseline remains eligible for selection.")
    add_heading(doc, "2.6 Time-Series Validation and Leakage", 2)
    add_para(doc, "Random train-test splitting is inappropriate when the task is to predict the future from the past because it permits later regimes to influence earlier evaluation. Expanding-window evaluation instead trains on the first segment, predicts the next point, expands the training window, and repeats. Feature leakage occurs when a predictor contains information unavailable at the forecast origin. Same-cycle crude-oil or exchange-rate averages may be analytically interesting but cannot be treated as known next-cycle inputs unless they are themselves forecast through a separate validated process.")
    add_para(doc, "A further distinction is required between model selection and final evaluation. If the same holdout is used repeatedly to choose the winning model, the holdout becomes part of the tuning process. MafutaPlan selects the model on an earlier sequence of 18 expanding-window forecasts and evaluates that selected model once on the last ten cycles. This design gives the final metrics a clearer interpretation.")
    add_heading(doc, "2.7 Error Measures and Uncertainty", 2)
    add_para(doc, "Mean absolute error expresses average error in KES per litre and is easily interpretable. Root mean squared error gives more weight to large misses and exposes sensitivity to abrupt jumps. Both are reported because no single metric fully describes performance. The uncertainty range uses the 10th and 90th percentiles of final holdout residuals added to the point forecast. With only ten residuals, this is an empirical error band, not a calibrated confidence or prediction interval.")
    add_heading(doc, "2.8 Decision-Support Usability", 2)
    add_para(doc, "A technically correct number is useful only when a user can interpret it. The interface should state the town, fuel, unit, effective period, and evidence source; distinguish official current data from experimental forecasts; show formulas and assumptions for journey estimates; and prevent invalid inputs such as zero efficiency. The Streamlit framework supports these needs with responsive widgets, metrics, tables, charts, warnings, and cached computation.")
    add_heading(doc, "2.9 Empirical Review", 2)
    add_table(doc, ["Source or concept", "Relevant finding", "Use in this project"], [
        ["EPRA pump-price formula", "Retail caps combine product costs, taxes, levies, margins, and adjustments.", "Component explanation and Nairobi scope."],
        ["EPRA statistics reports", "Official historical price tables support longitudinal analysis.", "Source-backed monthly history."],
        ["KNBS CPI reports", "Fuel-price movements affect transport and household cost context.", "Independent contextual cross-check."],
        ["Forecasting literature", "Benchmarks and time-ordered validation are necessary for honest comparison.", "Baseline, expanding windows, separate holdout."],
        ["Scikit-learn guidance", "Pipelines, fixed random states, and explicit metrics improve reproducibility.", "Deterministic candidate models and tests."],
    ], widths=[1.65, 2.5, 2.5], caption="Table 2.1: Literature synthesis and design implications")
    add_heading(doc, "2.10 Research Gap", 2)
    add_para(doc, "There is a gap between official price publication and transparent personal planning. Many demonstrations focus only on fitting a model, omit source-level provenance, combine incompatible geographies, or report a score without a benchmark and untouched holdout. This project addresses the gap by integrating official evidence, revision governance, cost calculators, a conservative forecast experiment, and a reproducible test suite in one Nairobi-focused system.")
    add_heading(doc, "2.10 Conceptual Framework", 2)
    add_figure(doc, DIAGRAMS / "conceptual_framework.png", "Figure 2.1: Conceptual framework for the study")
    add_para(doc, "Historical Nairobi prices and calendar-derived lag features form the available inputs. Leakage-safe model selection transforms them into an experimental next-cycle estimate. The estimate, official current price, and explicit calculator assumptions support user planning. The framework does not claim that historical values cause future regulatory decisions; it describes the information flow implemented by the system.")
    doc.add_page_break()


def chapter_three(doc: Document) -> None:
    add_heading(doc, "CHAPTER THREE: METHODOLOGY, ANALYSIS AND DESIGN", 1)
    add_heading(doc, "3.1 Research Design", 2)
    add_para(doc, "The study used an applied quantitative design with iterative software development. The quantitative component validates pump-price and Annex data, reconstructs regulated prices, engineers past-only forecast features, compares forecasting methods, and measures future-point errors. The software component translates these layers into an interactive decision-support prototype. Iteration was used to correct scope, prevent leakage, preserve revisions, and align the application, notebook, tests, report, and appendices.")
    add_heading(doc, "3.2 Data Sources and Collection", 2)
    add_para(doc, "The primary publisher is EPRA. Historical observations were cross-checked from its statistics reports, pump-price table and official notices. Twenty-three monthly release pages and PDFs were inventoried. Because the Annexes are scanned, a reproducible OCR pipeline records the source URL, annex page, extraction status and SHA-256 text fingerprint. Thirty-three rows from 11 readable cycles were manually reviewed and reconciled. Degraded scans remain marked for manual review and are excluded rather than invented. KNBS publications provide independent context.")
    add_table(doc, ["Dataset", "Rows", "Purpose", "Integrity control"], [
        ["Nairobi price history", "55 cycles", "Model target and trend chart", "Unique, continuous monthly labels; official source key"],
        ["Current Nairobi price", "1 record", "Current caps and calculators", "Town fixed to Nairobi; effective dates checked"],
        ["2026 revision audit", "4 announcements", "Original-versus-final evidence", "Original and revised values retained"],
        ["Price components", "Detailed rows", "Explain historical build-up", "Component totals reconcile to published totals"],
        ["Component history", "33 rows / 11 cycles", "Multi-cycle reconstruction and scenarios", "Official PDF link; zero reconstruction error"],
        ["EPRA source and OCR audits", "23 releases", "Reproducible acquisition and review", "URL, page, hash, extraction status"],
        ["Live EPRA comparison", "21 rows", "Independent overlap validation", "20/20 comparable final records match"],
        ["Source register", "Evidence groups", "Publisher and URL provenance", "HTTPS and known source identifiers"],
    ], widths=[1.45, 0.7, 2.05, 2.6], caption="Table 3.1: Project datasets")
    add_heading(doc, "3.3 Data Preparation and Revision Policy", 2)
    add_para(doc, "Dates are parsed into typed values and numeric price columns are checked for positivity. The canonical Cycle field is a monthly label used for continuity and modelling, whereas Effective_Start and Effective_End preserve the real regulatory period. For April 2026, the final prevailing value begins on 16 April; for May 2026 it begins on 19 May. The revision audit retains the earlier announcements. This makes the model target operationally meaningful without erasing what was first published.")
    add_figure(doc, CHARTS / "figure_3_1_fuel_price_trends.png", "Figure 3.1: Verified Nairobi monthly maximum-price history, January 2022-July 2026")
    add_heading(doc, "3.4 Variables and Feature Engineering", 2)
    add_para(doc, "The cost-reconstruction variables are Landed_Cost, Distribution_Storage, Margins, Taxes_Levies, and Stabilization_Adjustment. Distribution includes the actual Mombasa-to-Nairobi pipeline path, allowable losses, depot storage, and delivery within the stated Nairobi radius. The signed stabilization value is computed as the residual required to reconcile the official aggregates to the published cap, avoiding ambiguity when a scanned Annex drops parentheses or deficit/surplus signs.")
    add_para(doc, "The target variable is the maximum retail price in KES per litre for one product. The feature vector for cycle t contains a monotonic cycle number, sine and cosine transformations of the calendar month, price at t-1, price at t-2, and the mean of t-1 through t-3. The first three observations are discarded after lag construction. The rolling mean is shifted before calculation, ensuring that the target cycle does not enter its own predictors.")
    add_table(doc, ["Feature", "Definition", "Availability rationale"], [
        ["Month_num", "Sequential monthly index", "Known at the forecast origin"],
        ["Month_sin / Month_cos", "Cyclical encoding of calendar month", "Known calendar information"],
        ["Lag_1", "Previous cycle's final prevailing price", "Already published"],
        ["Lag_2", "Price two cycles earlier", "Already published"],
        ["Rolling_3", "Mean of the preceding three prices", "Uses only completed cycles"],
    ], widths=[1.4, 2.4, 3.0], caption="Table 3.2: Leakage-safe forecast features")
    add_heading(doc, "3.5 Candidate Models", 2)
    add_table(doc, ["Method", "Configuration", "Reason for inclusion"], [
        ["Previous-cycle baseline", "Forecast equals Lag_1", "Transparent benchmark suited to unchanged regulated prices"],
        ["Linear regression", "Ordinary least squares", "Interpretable linear relationship"],
        ["Ridge regression", "alpha = 10", "Shrinkage for a small correlated design"],
        ["Random forest", "20 trees; fixed random state", "Bounded nonlinear ensemble"],
        ["Gradient boosting", "30 estimators; fixed random state", "Sequential nonlinear error correction"],
    ], widths=[1.55, 2.0, 3.25], caption="Table 3.3: Candidate forecasting methods")
    add_heading(doc, "3.6 Selection and Final Evaluation Protocol", 2)
    add_para(doc, "After feature construction, the final ten observations are reserved as an untouched holdout. Candidate methods are evaluated only on the preceding selection sequence using expanding windows with a minimum training history of 24 engineered observations. This produces 18 selection forecasts. The method with the lowest selection MAE is fixed. It is then run across the ten-point holdout using only information available before each point. The holdout does not decide the winner.")
    add_para(doc, "For actual values y_i and forecasts ŷ_i, MAE equals (1/n)Σ|y_i-ŷ_i|. RMSE equals the square root of (1/n)Σ(y_i-ŷ_i)^2. The baseline MAE is reported beside the selected-method MAE. Residual-band coverage is the proportion of holdout actuals falling between the empirical lower and upper limits generated at their origin.")
    add_heading(doc, "3.7 Functional Requirements", 2)
    add_bullets(doc, [
        "Display current Nairobi caps, fuel type, effective dates, and official source link.",
        "Calculate cost from litres and affordable litres from a budget.",
        "Estimate journey fuel use and cost from distance, efficiency, trip type, and traffic allowance.",
        "Produce separate experimental forecasts and evaluation metrics for all three fuels.",
        "Display the complete imported-product-to-Nairobi price journey.",
        "Reconstruct a selected official cycle from landed cost, distribution, margins, stabilization, and taxes.",
        "Run user-declared cost scenarios without labelling them official forecasts.",
        "Display history, historical price components, formulas, limitations, and evidence register.",
        "Reject inconsistent or untraceable project data before it reaches the user interface.",
    ])
    add_heading(doc, "3.8 Non-functional Requirements", 2)
    add_bullets(doc, [
        "Usability: plain-language labels, units, warnings, and immediate calculations.",
        "Reliability: deterministic model seeds, cached results, and automated tests.",
        "Maintainability: separate data, calculator, modelling, and interface modules.",
        "Transparency: evidence links, revision notes, model comparison, and limitations.",
        "Portability: CSV storage and a requirements file for local execution.",
    ])
    add_heading(doc, "3.9 System Architecture", 2)
    add_figure(doc, DIAGRAMS / "system_architecture_diagram.png", "Figure 3.2: Logical architecture of MafutaPlan")
    add_para(doc, "The evidence layer consists of official files, source inventory, OCR audit, live-table comparison, and the local source register. Validated loaders form the data boundary. Pure calculator, reconstruction, scenario, and forecasting modules supply application services. Streamlit presents six workflows: overview, price journey, reconstruction, forecast and scenarios, calculator, and evidence. Tests exercise the service boundary independently of browser presentation.")
    add_heading(doc, "3.10 Reconstruction, Scenario and Journey Formulae", 2)
    add_para(doc, "For an official fuel-cycle row, Nairobi retail price R = L + D + M + T + S, where L is landed refined-product cost, D is distribution and storage from Mombasa to Nairobi, M is the regulated wholesale and dealer margin, T is taxes and levies, and S is the signed stabilization adjustment. The reconstruction error is calculated price minus official price and is zero for all 33 reviewed rows after rounding. A scenario changes only user-declared terms and is labelled what-if analysis rather than an EPRA forecast.")
    add_figure(doc, CHARTS / "figure_3_3_component_history.png", "Figure 3.3: Average reviewed cost composition across 11 official EPRA Annex cycles")
    add_para(doc, "Purchase cost is C = P × L, where P is KES per litre and L is litres. Affordable litres are L = B / P for budget B. Journey fuel requirement is F = [D × M / E] × (1 + A/100), where D is one-way distance, M is 1 for one way or 2 for return, E is vehicle efficiency in kilometres per litre, and A is the selected traffic or contingency allowance. Journey cost is J = F × P. These deterministic formulas are separated from the forecast so a user can plan with the official price even if the experimental forecast is uncertain.")
    add_heading(doc, "3.11 Ethical and Data-Integrity Considerations", 2)
    add_para(doc, "The application avoids representing a model estimate as an official announcement. It states the forecast target, empirical nature of the range, sample size, and selected method. Source URLs are displayed, revisions are preserved, and historical components are date-labelled. The system collects no personal data and performs no payments or automated commercial decisions.")
    doc.add_page_break()


def chapter_four(doc: Document) -> None:
    add_heading(doc, "CHAPTER FOUR: IMPLEMENTATION, RESULTS AND TESTING", 1)
    add_heading(doc, "4.1 Development Environment", 2)
    add_para(doc, "The prototype was implemented in Python 3.12. Streamlit supplies the web interface, pandas handles tabular transformation, scikit-learn supplies candidate estimators and metrics, matplotlib produces report figures, and Python's unittest framework verifies data and service behaviour. Requests, Beautiful Soup, PyMuPDF and Tesseract support official-source inventory and OCR auditing. The code is organised into app.py, src/data.py, src/calculators.py, src/hybrid.py, src/modeling.py, reproducible scripts, and tests/test_project.py.")
    add_heading(doc, "4.2 Implemented User Workflows", 2)
    add_para(doc, "The Overview presents current caps and trend. Fuel price journey explains the eight stages from refined-product procurement to stabilization. Cost reconstruction lets a reviewer choose a real cycle and reproduce the EPRA cap from five aggregate groups. Forecast and scenarios separates the statistical estimate from a declared component what-if. Planning calculator supports purchase, budget and trip decisions. Evidence and methodology exposes history, component data, metrics, limitations and source links.")
    add_heading(doc, "4.3 Current Official Nairobi Record", 2)
    add_table(doc, ["Product", "Maximum price", "Effective period", "Status"], [
        ["Super Petrol", "KES 214.03/L", "15 Jul-14 Aug 2026", "Official current cap"],
        ["Diesel", "KES 222.86/L", "15 Jul-14 Aug 2026", "Official current cap"],
        ["Kerosene", "KES 191.38/L", "15 Jul-14 Aug 2026", "Official current cap"],
    ], widths=[1.4, 1.4, 2.0, 2.1], caption="Table 4.1: Current Nairobi maximum retail prices used by the application")
    add_heading(doc, "4.4 Price-Composition Result", 2)
    add_figure(doc, CHARTS / "figure_3_2_price_components.png", "Figure 4.1: Historical Nairobi price build-up from EPRA Annex III, 15 June-14 July 2025")
    add_para(doc, "The chart is an explanation of how a published pump-price total was built, not a representation of the current July 2026 mix. The component file includes an explicit one-cent rounding reconciliation for Super Petrol and Kerosene because the displayed component values sum one cent below the published total when rounded individually. Preserving this reconciliation prevents silent arithmetic inconsistency.")
    add_heading(doc, "4.5 Multi-cycle Reconstruction Result", 2)
    add_para(doc, "The reviewed panel contains 33 rows: 11 official EPRA cycles multiplied by three fuels. Each row links to the exact EPRA PDF and stores landed product cost, Nairobi distribution and storage, wholesale and retail margins, taxes and levies, stabilization, official retail price, reconstructed price, and a quality note. All 33 calculated prices equal their official retail price after rounding; the maximum absolute reconstruction error is KES 0.00/L.")
    add_figure(doc, CHARTS / "figure_3_3_component_history.png", "Figure 4.2: Average component composition in the reviewed EPRA panel")
    add_heading(doc, "4.6 Model Selection Results", 2)
    add_para(doc, "The previous-cycle baseline achieved the lowest selection MAE for each product across 18 earlier expanding-window forecasts. This result is substantively plausible because regulated prices sometimes remain unchanged, and the sample is too small to guarantee that a flexible estimator can learn policy-driven jumps. Model simplicity is therefore an empirical result rather than a predetermined conclusion.")
    metrics = load_csv(ROOT / "appendices" / "Model_Metrics.csv")
    add_table(doc, ["Fuel", "Winner", "Selection MAE", "Selection points"], [
        [r["Fuel"], r["Selected_Method"], f'{float(r["Selection_MAE"]):.3f}', r["Selection_Points"]] for r in metrics
    ], widths=[1.5, 2.5, 1.3, 1.3], caption="Table 4.2: Model-selection results")
    add_heading(doc, "4.7 Untouched Holdout Results", 2)
    add_table(doc, ["Fuel", "Holdout MAE", "Holdout RMSE", "Baseline MAE", "Band coverage"], [
        [r["Fuel"], f'{float(r["Holdout_MAE"]):.3f}', f'{float(r["Holdout_RMSE"]):.3f}', f'{float(r["Baseline_MAE"]):.3f}', f'{100*float(r["Observed_Band_Containment"]):.0f}%'] for r in metrics
    ], widths=[1.5, 1.25, 1.25, 1.25, 1.2], caption="Table 4.3: Final ten-cycle holdout performance (KES/L unless stated)")
    add_figure(doc, CHARTS / "figure_4_1_holdout_mae.png", "Figure 4.3: Selected-method and baseline MAE on the untouched holdout")
    add_para(doc, "Because the baseline was selected, selected-method and baseline MAE are equal. Diesel produced the largest average and squared error, indicating that its recent revisions and level changes were harder to extrapolate from lagged prices. Coverage of 80%, 80%, and 90% should not be interpreted as calibrated probability because each estimate is based on only ten holdout cases.")
    add_heading(doc, "4.8 August 2026 Experimental Forecast", 2)
    add_table(doc, ["Fuel", "Point forecast", "Empirical error band", "Interpretation"], [
        [r["Fuel"], f'KES {float(r["August_2026_Forecast"]):.2f}/L', f'KES {float(r["Empirical_Lower"]):.2f}-{float(r["Empirical_Upper"]):.2f}/L', "Experimental; not an EPRA cap"] for r in metrics
    ], widths=[1.45, 1.55, 2.0, 1.9], caption="Table 4.4: Next-cycle estimates produced from information available through July 2026")
    add_para(doc, "The point forecast for each product equals the July price because persistence won selection. This outcome does not mean prices will remain unchanged. It means that, among the tested candidates and using the available history, the latest value was the most defensible statistical estimate. Users should replace it with the official EPRA price immediately when the August notice is issued.")
    add_heading(doc, "4.9 Calculator Verification Examples", 2)
    add_table(doc, ["Scenario", "Input", "Expected result"], [
        ["Purchase Super Petrol", "20 L at KES 214.03/L", "KES 4,280.60"],
        ["Diesel from budget", "KES 5,000 at KES 222.86/L", "22.44 L"],
        ["Return Super Petrol trip", "30 km, 12 km/L, 10% allowance", "5.50 L; KES 1,177.17"],
        ["Purchase Kerosene", "10 L at KES 191.38/L", "KES 1,913.80"],
    ], widths=[1.7, 2.7, 2.2], caption="Table 4.5: Representative calculator checks")
    add_heading(doc, "4.10 Automated Testing", 2)
    add_para(doc, "Twenty-one automated tests cover data loading, calculators, component reconstruction, scenario arithmetic, modelling safeguards, and chart creation. The suite checks Nairobi-only scope, continuous and source-resolved history, current values, detailed and multi-cycle component reconciliation, official PDF coverage, past-only lags, finite forecasts, the August 2026 target, and separation of model-selection and holdout periods.")
    add_table(doc, ["Test group", "Examples", "Expected outcome"], [
        ["Data scope", "One official Nairobi row; 55 unique continuous cycles", "Pass"],
        ["Provenance", "Known source IDs and HTTPS URLs", "Pass"],
        ["Official values", "Historical spot checks and current July caps", "Pass"],
        ["Components", "Every fuel reconciles to published total", "Pass"],
        ["Component panel", "33 official rows; exact reconstruction; HTTPS EPRA links", "Pass"],
        ["Scenarios", "Only declared cost inputs change the calculated result", "Pass"],
        ["Calculators", "Purchase, budget, journey, and validation cases", "Pass"],
        ["Modelling", "Past-only lags, finite outputs, next cycle, split separation", "Pass"],
        ["Presentation", "Historical trend chart builds", "Pass"],
    ], widths=[1.4, 3.7, 1.4], caption="Table 4.6: Automated verification summary")
    add_heading(doc, "4.11 Discussion", 2)
    add_para(doc, "The implementation meets the main objective by combining evidence-backed current data and a reproducible forecast experiment in one Nairobi workflow. The most important modelling result is that added complexity did not improve selection error. Reporting this negative result strengthens the study: it demonstrates comparison rather than choosing an attractive algorithm in advance. The larger diesel error also shows why user-facing point estimates must be accompanied by observed error information.")
    add_para(doc, "The application provides value even when the forecast is conservative. Current-price calculations are deterministic, source-linked, and independent of model performance. The component explanation makes regulation more legible, and the evidence page lets a supervisor inspect sources and revision handling. This separation of official facts, exact calculations, and experimental estimates is central to the system's credibility.")
    doc.add_page_break()


def chapter_five(doc: Document) -> None:
    add_heading(doc, "CHAPTER FIVE: SUMMARY, CONCLUSIONS AND RECOMMENDATIONS", 1)
    add_heading(doc, "5.1 Summary of the Study", 2)
    add_para(doc, "The study corrected a broad price-only prototype into a hybrid Nairobi decision-support system. It assembled 55 monthly price cycles, inventoried 23 official release PDFs, reviewed 33 component records across 11 Annex cycles, matched 20 comparable records against EPRA's live table, preserved revisions, implemented reconstruction and scenario services, compared five forecasting methods, reserved an untouched holdout, and exposed evidence and limitations in the interface.")
    add_heading(doc, "5.2 Achievement of Objectives", 2)
    add_table(doc, ["Objective", "Evidence of achievement"], [
        ["Compile verified Nairobi data", "Validated history, current file, revision audit, and source register"],
        ["Represent the complete fuel-cost chain", "Eight-stage journey and detailed EPRA Annex component register"],
        ["Reconstruct official prices", "33 reviewed fuel-cycle records with zero rounding error"],
        ["Implement practical planning tools", "Litres-to-cost, budget-to-litres, and journey-cost workflows"],
        ["Compare forecasting methods", "Five fixed candidates evaluated on 18 expanding-window selection points"],
        ["Provide honest final evaluation", "One ten-cycle untouched holdout with MAE, RMSE, baseline, and empirical coverage"],
        ["Deliver an auditable degree prototype", "Modular application, documentation, evidence links, report, appendices, and tests"],
    ], widths=[2.35, 4.35], caption="Table 5.1: Objective-to-deliverable mapping")
    add_heading(doc, "5.3 Conclusions", 2)
    add_para(doc, "Nairobi is the appropriate town for this project because it offers strong evidence continuity, clear public relevance, and a coherent single-market target. The previous-cycle baseline is the preferred method under the implemented evaluation: it won all three product comparisons and avoids pretending that a small historical series can learn future policy decisions. August 2026 forecasts should therefore be read as conservative planning references, not official prices.")
    add_para(doc, "The broader conclusion is that data governance, regulated cost structure and communication matter as much as algorithm choice. A source-linked cap and exact reconstruction can be more useful than an opaque prediction. By distinguishing official records, deterministic reconstruction, declared scenarios and experimental forecasts, MafutaPlan addresses the supervisor's landing-to-Nairobi cost concern while remaining academically honest.")
    add_heading(doc, "5.4 Recommendations", 2)
    add_bullets(doc, [
        "Use Nairobi for the supervised submission and demonstrate one complete workflow rather than expanding prematurely to multiple towns.",
        "Refresh the current file and forecast after every official EPRA announcement; preserve any revision rather than overwriting its history.",
        "Complete a continuous component panel of at least 36 monthly Annex cycles before fitting a production landed-cost regression.",
        "If external economic variables are added, forecast them independently or use only values known at the pump-price forecast origin.",
        "Evaluate prediction intervals with a larger holdout or conformal procedure before presenting probability statements.",
        "For future deployment, add a scheduled evidence-ingestion review, cryptographic snapshots of source files, and mobile usability testing.",
    ])
    add_heading(doc, "5.5 Suggested Future Work", 2)
    add_para(doc, "Future research may compare town-specific models after constructing equally traceable histories, examine regime-switching methods for subsidies and revisions, use separately forecast landed-cost and exchange-rate variables, and conduct structured usability studies with motorists and transport operators. A production deployment would also require monitoring, source-availability alerts, accessibility review, security hardening, and a clear maintenance owner.")
    doc.add_page_break()


def references_and_appendices(doc: Document) -> None:
    add_heading(doc, "REFERENCES", 1)
    refs = [
        "Energy and Petroleum Regulatory Authority. (2022). Energy and petroleum statistics report FY 2021/2022. https://www.epra.go.ke/wp-content/uploads/2023/01/Energy-and-Petroleum-Statistics-Report.pdf",
        "Energy and Petroleum Regulatory Authority. (2024). Energy and petroleum statistics report FY 2023/2024. https://www.epra.go.ke/sites/default/files/2024-10/EPRA%20Energy%20and%20Petroleum%20Statistics%20Report%20FY%202023-2024_2.pdf",
        "Energy and Petroleum Regulatory Authority. (2025a). Energy and petroleum statistics report FY 2024/2025. https://www.epra.go.ke/sites/default/files/2025-09/Statistics-Report-June-2025-Web.pdf",
        "Energy and Petroleum Regulatory Authority. (2025b). Maximum retail petroleum prices for 15 June-14 July 2025. https://www.epra.go.ke/sites/default/files/2025-06/PRESS%20RELEASE-%20JUNE%20SIGNED%202025.pdf",
        "Energy and Petroleum Regulatory Authority. (2026a). Pump price formulae. https://www.epra.go.ke/pump-price-formulae",
        "Energy and Petroleum Regulatory Authority. (2026b). Biannual statistics report 2025/2026. https://www.epra.go.ke/sites/default/files/2026-03/Biannual%20Statistics%20Report%202025-2026_1.pdf",
        "Energy and Petroleum Regulatory Authority. (2026c). Addendum: Maximum retail petroleum prices in Kenya released 14 April 2026. https://www.epra.go.ke/index.php/addendum-maximum-retail-petroleum-prices-kenya-released-14th-april-2026",
        "Energy and Petroleum Regulatory Authority. (2022). Petroleum (Pricing) Regulations, Legal Notice No. 192 of 2022. https://petroleum.go.ke/sites/default/files/The%20Petroleum%20%28Pricing%29%20Regulations.pdf",
        "Ministry of Energy and Petroleum. (2026). Petroleum information: refined-product importation, storage and transport in Kenya. https://www.petroleum.go.ke/petroleum-information",
        "Kenya Pipeline Company. (2025). Service delivery charter and pipeline transport services. https://qmseldoret.kpc.co.ke/downloads/SERVICE_DELIVERY_CHARTER.pdf",
        "Hyndman, R. J., & Athanasopoulos, G. (2021). Forecasting: Principles and practice (3rd ed.). OTexts. https://otexts.com/fpp3/",
        "Kenya National Bureau of Statistics. (2026). Kenya consumer price indices and inflation rates, June 2026. https://www.knbs.or.ke/wp-content/uploads/2026/06/Kenya-Consumer-Price-Indices-and-Inflation-Rates-June-2026.pdf",
        "Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2825-2830.",
        "Streamlit. (2026). Streamlit documentation. https://docs.streamlit.io/",
    ]
    for item in refs:
        p = doc.add_paragraph(item)
        p.paragraph_format.left_indent = Inches(0.35)
        p.paragraph_format.first_line_indent = Inches(-0.35)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    doc.add_page_break()

    add_heading(doc, "APPENDICES", 1)
    add_heading(doc, "Appendix A: Data Dictionary", 2)
    dictionary = load_csv(ROOT / "appendices" / "Data_Extraction_Sheet.csv")
    add_table(doc, ["Field", "Type", "Unit", "Meaning", "Validation"], [[r["Field"], r["Type"], r["Unit"], r["Meaning"], r["Validation"]] for r in dictionary], widths=[1.15, 0.7, 0.85, 2.25, 1.65])
    add_heading(doc, "Appendix B: Source Register", 2)
    sources = load_csv(DATA / "sources.csv")
    add_table(doc, ["Source ID", "Publisher", "Title / scope", "Accessed"], [[r["Source_ID"], r["Publisher"], r["Title"], r["Accessed_On"]] for r in sources], widths=[1.35, 1.2, 3.5, 0.9])
    add_para(doc, "The full URLs and provenance notes remain in data/sources.csv so that this compact report table stays readable.")
    add_heading(doc, "Appendix C: Representative Verified Records", 2)
    sample = load_csv(ROOT / "appendices" / "Sample_Dataset.csv")
    add_table(doc, ["Cycle", "Effective start", "Super", "Diesel", "Kerosene", "Source"], [[r["Cycle"], r["Effective_Start"], r["Super_Petrol"], r["Diesel"], r["Kerosene"], r["Source_ID"]] for r in sample], widths=[1.1, 1.1, 0.85, 0.85, 0.85, 1.5])
    add_heading(doc, "Appendix D: User Guide", 2)
    add_bullets(doc, [
        "Install dependencies with: python -m pip install -r requirements.txt",
        "Start the application with: streamlit run app.py",
        "Open http://localhost:8501 in a browser.",
        "Use Overview for current caps and the complete price trend.",
        "Use Fuel price journey for the imported-product-to-Nairobi cost chain.",
        "Use Cost reconstruction to reproduce an official EPRA price.",
        "Use Forecast & scenarios for the August estimate and declared what-if costs.",
        "Use Planning calculator for purchase, budget and trip estimates.",
        "Use Evidence & methodology to inspect history, component records, sources, and limitations.",
    ], numbered=True)
    add_heading(doc, "Appendix E: Test and Reproduction Commands", 2)
    add_para(doc, "Run the following commands from the project root:")
    for command in [
        "python -m unittest discover -s tests -v",
        "python -m compileall app.py src scripts tests",
        "python scripts/audit_epra_pump_prices.py",
        "python scripts/build_component_history.py",
        "python -m pip check",
        "streamlit run app.py",
    ]:
        p = doc.add_paragraph()
        r = p.add_run(command)
        r.font.name = "Consolas"
        r.font.size = Pt(9)
        set_cell_shading if False else None
    add_heading(doc, "Appendix F: Project Schedule", 2)
    schedule = load_csv(ROOT / "appendices" / "Project_Schedule.csv")
    headers = list(schedule[0].keys())
    add_table(doc, headers, [[r[h] for h in headers] for r in schedule])
    add_heading(doc, "Appendix G: Project Budget", 2)
    budget = load_csv(ROOT / "appendices" / "Project_Budget.csv")
    headers = list(budget[0].keys())
    add_table(doc, headers, [[r[h] for h in headers] for r in budget])
    add_heading(doc, "Appendix H: Repository Structure", 2)
    add_para(doc, "The authoritative implementation is stored in app.py and src/. The appendices contain portable CSV extracts rather than duplicated modelling logic. DATA_PROVENANCE.md defines the evidence and refresh protocol; notebooks/FuelPriceAnalysis.ipynb provides reproducible exploratory analysis; outputs/ contains report figures and presentation artifacts; tests/test_project.py contains the automated verification suite.")


def build_report() -> Path:
    generate_assets()
    DOCS.mkdir(parents=True, exist_ok=True)
    doc = Document()
    configure_document(doc)
    front_matter(doc)
    chapter_one(doc)
    chapter_two(doc)
    chapter_three(doc)
    chapter_four(doc)
    chapter_five(doc)
    references_and_appendices(doc)
    core = doc.core_properties
    core.title = "Design and Implementation of a Hybrid Cost-Based Model for Forecasting Regulated Fuel Prices in Nairobi, Kenya"
    core.subject = "Final-year degree project report"
    core.author = "Ryan Alfred Nyambati"
    core.keywords = "Nairobi, EPRA, landed cost, price reconstruction, forecasting, Streamlit"
    doc.save(REPORT)
    return REPORT


if __name__ == "__main__":
    path = build_report()
    print(path)
