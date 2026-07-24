"""Create the verified explanation of MafutaPlan's linear regression model."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import load_prediction_dataset  # noqa: E402
from src.modeling import COMPONENT_FEATURES, evaluate_latest_cycle  # noqa: E402

OUTPUT = ROOT / "output" / "pdf" / "MafutaPlan_Linear_Regression_Explanation.pdf"
TEMP = ROOT / "tmp" / "pdfs"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2878B5")
PALE_BLUE = colors.HexColor("#EAF3F8")
RED = colors.HexColor("#C84C4C")
GREY = colors.HexColor("#5B6770")
LIGHT_GREY = colors.HexColor("#F3F5F7")


def page_header_footer(canvas, document) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#D8E0E6"))
    canvas.line(18 * mm, height - 16 * mm, width - 18 * mm, height - 16 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(18 * mm, height - 12 * mm, "MafutaPlan - Linear Regression")
    canvas.drawRightString(
        width - 18 * mm, 11 * mm, f"Ryan Alfred Nyambati | Page {document.page}"
    )
    canvas.restoreState()


def make_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=31,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=12,
            leading=18,
            textColor=GREY,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=NAVY,
            spaceBefore=4,
            spaceAfter=9,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Subsection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=BLUE,
            spaceBefore=8,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.6,
            leading=14,
            textColor=colors.HexColor("#27343D"),
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=GREY,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Formula",
            parent=styles["BodyText"],
            fontName="Courier-Bold",
            fontSize=8.5,
            leading=13,
            textColor=NAVY,
            backColor=PALE_BLUE,
            borderPadding=9,
            spaceBefore=6,
            spaceAfter=9,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Callout",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=14,
            textColor=NAVY,
            backColor=PALE_BLUE,
            borderPadding=9,
            spaceBefore=5,
            spaceAfter=9,
        )
    )
    return styles


def styled_table(data, widths=None, header=True, font_size=8.2):
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#27343D")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D7DFE5")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
        if len(data) > 1:
            commands.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]))
    table.setStyle(TableStyle(commands))
    return table


def build_charts(evaluation) -> tuple[Path, Path]:
    TEMP.mkdir(parents=True, exist_ok=True)
    actual_path = TEMP / "actual_vs_predicted.png"
    coefficient_path = TEMP / "coefficients.png"

    results = evaluation.results.copy()
    lower = min(
        results["Target_Retail_Price"].min(),
        results["Predicted_Retail_Price"].min(),
    ) - 5
    upper = max(
        results["Target_Retail_Price"].max(),
        results["Predicted_Retail_Price"].max(),
    ) + 5
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    palette = {"Super Petrol": "#2878B5", "Diesel": "#E28E2C", "Kerosene": "#48A868"}
    for _, row in results.iterrows():
        ax.scatter(
            row["Target_Retail_Price"],
            row["Predicted_Retail_Price"],
            s=95,
            color=palette[row["Fuel"]],
            label=row["Fuel"],
            edgecolor="white",
            linewidth=0.8,
            zorder=3,
        )
        ax.annotate(
            row["Fuel"],
            (row["Target_Retail_Price"], row["Predicted_Retail_Price"]),
            xytext=(6, 5),
            textcoords="offset points",
            fontsize=8,
        )
    ax.plot([lower, upper], [lower, upper], "--", color="#7F8C8D", label="Ideal fit")
    ax.set(xlim=(lower, upper), ylim=(lower, upper))
    ax.set_xlabel("Official April price (KSh/L)")
    ax.set_ylabel("Predicted April price (KSh/L)")
    ax.set_title("Chronological holdout: actual versus predicted")
    ax.grid(alpha=0.2)
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax.legend(unique.values(), unique.keys(), frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(actual_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    coefficients = evaluation.coefficients.loc[
        evaluation.coefficients["Term"].ne("Intercept")
    ].copy()
    labels = {
        "Landed_Cost": "Landed cost",
        "Distribution_Storage": "Distribution & storage",
        "Margins": "Margins",
        "Stabilization_Adjustment": "Stabilization adjustment",
        "Taxes_Levies": "Taxes & levies",
        "Fuel_Diesel": "Diesel fuel effect",
        "Fuel_Kerosene": "Kerosene fuel effect",
    }
    coefficients["Label"] = coefficients["Term"].map(labels)
    coefficients = coefficients.sort_values("Coefficient")
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    bar_colors = [
        "#C84C4C" if value < 0 else "#2878B5"
        for value in coefficients["Coefficient"]
    ]
    ax.barh(coefficients["Label"], coefficients["Coefficient"], color=bar_colors)
    ax.axvline(0, color="#27343D", linewidth=0.8)
    ax.set_xlabel("Regression coefficient")
    ax.set_title("Coefficients learned from the training records")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(coefficient_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return actual_path, coefficient_path


def build_pdf() -> Path:
    data = load_prediction_dataset()
    evaluation = evaluate_latest_cycle(data)
    actual_chart, coefficient_chart = build_charts(evaluation)
    styles = make_styles()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title="How MafutaPlan Achieved Multiple Linear Regression",
        author="Ryan Alfred Nyambati",
        subject="MafutaPlan model design, training, evaluation, and interpretation",
    )
    story = []

    story.extend(
        [
            Spacer(1, 37 * mm),
            Paragraph("How MafutaPlan Achieved<br/>Multiple Linear Regression", styles["CoverTitle"]),
            Paragraph(
                "Component-based fuel price prediction for Nairobi, Kenya",
                styles["CoverSubtitle"],
            ),
            Spacer(1, 15 * mm),
            styled_table(
                [
                    ["Project", "MafutaPlan"],
                    ["Author", "Ryan Alfred Nyambati"],
                    ["Registration", "SCT222-0195/2021"],
                    ["Institution", "Jomo Kenyatta University of Agriculture and Technology"],
                    ["Model", "Pooled multiple linear regression"],
                    ["Test cycle", f"{evaluation.test_cycle:%B %Y}"],
                ],
                widths=[38 * mm, 103 * mm],
                header=False,
                font_size=9,
            ),
            Spacer(1, 16 * mm),
            Paragraph(
                "Purpose: explain, in reproducible terms, how the application "
                "converted verified EPRA component records into a one-cycle-ahead "
                "fuel-price prediction and how the result was evaluated.",
                styles["Callout"],
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            Spacer(1, 8 * mm),
            Paragraph("1. What the model was designed to do", styles["SectionTitle"]),
            Paragraph(
                "MafutaPlan estimates the maximum Nairobi retail price for the next "
                "pricing cycle. The prediction is based on component information from "
                "the immediately preceding cycle. The target is continuous (KSh per "
                "litre), so linear regression is an appropriate transparent baseline.",
                styles["Body"],
            ),
            Paragraph("Prediction unit", styles["Subsection"]),
            Paragraph(
                "One row represents one fuel product in one input cycle, paired with "
                "that fuel's published retail price in the following target cycle. "
                "Super Petrol, Diesel, and Kerosene are pooled into one model.",
                styles["Body"],
            ),
            Paragraph("Model inputs", styles["Subsection"]),
            styled_table(
                [
                    ["Feature", "Meaning in the application"],
                    ["Landed_Cost", "Imported product, freight, financing, port, and exchange-rate effects"],
                    ["Distribution_Storage", "Handling, storage, pipeline, losses, depot, and delivery costs"],
                    ["Margins", "Approved wholesale and retail margins"],
                    ["Stabilization_Adjustment", "Signed subsidy, deficit, surplus, or reconciliation adjustment"],
                    ["Taxes_Levies", "Excise, VAT, road, petroleum, regulatory, and related charges"],
                    ["Fuel_Diesel", "1 for Diesel; 0 otherwise"],
                    ["Fuel_Kerosene", "1 for Kerosene; 0 otherwise"],
                ],
                widths=[48 * mm, 106 * mm],
            ),
            Spacer(1, 5 * mm),
            Paragraph(
                "Super Petrol is the reference fuel because both fuel indicator "
                "variables equal zero for its rows.",
                styles["Callout"],
            ),
            Paragraph("Target", styles["Subsection"]),
            Paragraph(
                "<b>Target_Retail_Price</b> is the official Nairobi maximum retail "
                "price in the following cycle. The feature rows and targets are stored "
                "in <b>data/component_prediction_dataset.csv</b>.",
                styles["Body"],
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            Paragraph("2. The regression formulation", styles["SectionTitle"]),
            Paragraph(
                "The application uses scikit-learn's ordinary least-squares "
                "<b>LinearRegression</b> estimator. It learns an intercept and one "
                "coefficient for each numerical or encoded input.",
                styles["Body"],
            ),
            Paragraph(
                "Predicted price = b0 + b1(Landed Cost) + b2(Distribution and Storage) "
                "+ b3(Margins) + b4(Stabilization) + b5(Taxes and Levies) "
                "+ b6(Diesel) + b7(Kerosene)",
                styles["Formula"],
            ),
            Paragraph(
                "The estimator chooses the coefficients that minimise the sum of "
                "squared differences between observed training prices and fitted "
                "training prices. In code, <b>design_matrix()</b> creates the seven "
                "columns, and <b>fit_linear_regression()</b> calls model.fit(X, y).",
                styles["Body"],
            ),
            Paragraph("Chronological split and leakage prevention", styles["Subsection"]),
            Paragraph(
                "Random splitting would allow later regulatory cycles to help predict "
                "earlier ones. MafutaPlan instead sorts rows by Target_Cycle, reserves "
                "the latest complete cycle as the test set, and trains only on earlier "
                "targets. This preserves the direction of time.",
                styles["Body"],
            ),
            styled_table(
                [
                    ["Stage", "Cycles / records", "Role"],
                    [
                        "Training",
                        f"{evaluation.training_start:%b %Y} to {evaluation.training_end:%b %Y}; "
                        f"{evaluation.training_records} rows",
                        "Learn coefficients",
                    ],
                    [
                        "Testing",
                        f"{evaluation.test_cycle:%b %Y}; {evaluation.test_records} rows",
                        "Unseen chronological holdout",
                    ],
                ],
                widths=[28 * mm, 62 * mm, 64 * mm],
            ),
            Spacer(1, 6 * mm),
            Paragraph("Implementation sequence", styles["Subsection"]),
            styled_table(
                [
                    ["Step", "Operation"],
                    ["1", "Load and validate the model-ready component dataset."],
                    ["2", "Sort by target cycle and fuel product."],
                    ["3", "Reserve the latest complete target cycle."],
                    ["4", "Encode Diesel and Kerosene indicators."],
                    ["5", "Fit LinearRegression on the earlier records."],
                    ["6", "Predict the three held-out April prices."],
                    ["7", "Calculate absolute error, percentage error, MAE, and RMSE."],
                ],
                widths=[16 * mm, 138 * mm],
            ),
        ]
    )

    results = evaluation.results.sort_values("Fuel")
    result_rows = [["Fuel", "Official", "Predicted", "Abs. error", "% error"]]
    for _, row in results.iterrows():
        result_rows.append(
            [
                row["Fuel"],
                f"{row['Target_Retail_Price']:.2f}",
                f"{row['Predicted_Retail_Price']:.2f}",
                f"{row['Absolute_Error']:.2f}",
                f"{row['Percentage_Error']:.2f}%",
            ]
        )
    story.extend(
        [
            PageBreak(),
            Paragraph("3. Held-out April 2026 results", styles["SectionTitle"]),
            Paragraph(
                f"The model achieved a mean absolute error (MAE) of "
                f"<b>{evaluation.mae:.2f} KSh/L</b> and a root mean squared error "
                f"(RMSE) of <b>{evaluation.rmse:.2f} KSh/L</b> across the three "
                "held-out fuel products.",
                styles["Body"],
            ),
            styled_table(
                result_rows,
                widths=[40 * mm, 28 * mm, 30 * mm, 28 * mm, 28 * mm],
            ),
            Spacer(1, 6 * mm),
            Image(str(actual_chart), width=154 * mm, height=92 * mm),
            Paragraph(
                "Figure 1. The dashed diagonal is perfect agreement. Kerosene is "
                "close to the line, while Diesel and Super Petrol are under-predicted.",
                styles["Small"],
            ),
            Spacer(1, 5 * mm),
            Paragraph(
                "MAE is the average absolute miss in KSh/L. RMSE gives larger errors "
                "more weight, which is why the Diesel error has a stronger influence.",
                styles["Callout"],
            ),
        ]
    )

    coefficient_rows = [["Term", "Coefficient"]]
    for _, row in evaluation.coefficients.iterrows():
        coefficient_rows.append([row["Term"], f"{row['Coefficient']:.6f}"])
    story.extend(
        [
            PageBreak(),
            Paragraph("4. What the fitted coefficients mean", styles["SectionTitle"]),
            Paragraph(
                "A positive coefficient means the fitted prediction rises when that "
                "input rises and the other inputs are held constant. A negative "
                "coefficient means the fitted prediction falls. These are model "
                "associations, not proof that an input causes the price change.",
                styles["Body"],
            ),
            Image(str(coefficient_chart), width=154 * mm, height=94 * mm),
            Paragraph(
                "Figure 2. Feature coefficients only; the intercept is omitted from "
                "the graph so that the feature bars remain readable.",
                styles["Small"],
            ),
            Spacer(1, 5 * mm),
            styled_table(coefficient_rows, widths=[105 * mm, 49 * mm]),
            Spacer(1, 5 * mm),
            Paragraph(
                "Caution: the component variables use different ranges and are often "
                "correlated. Raw coefficient magnitudes therefore should not be used "
                "as a simple ranking of real-world importance.",
                styles["Callout"],
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            Paragraph("5. How the app presents the model", styles["SectionTitle"]),
            Paragraph(
                "The Fuel Price Prediction page selects a fuel, displays its predicted "
                "April price, official April price, absolute error, and March component "
                "inputs. It then renders two linear-regression graphs:",
                styles["Body"],
            ),
            styled_table(
                [
                    ["Graph", "Purpose"],
                    [
                        "Actual versus predicted",
                        "Shows the three held-out observations against an ideal-fit line.",
                    ],
                    [
                        "Learned coefficients",
                        "Shows the direction and size of the fitted feature associations.",
                    ],
                ],
                widths=[52 * mm, 102 * mm],
            ),
            Spacer(1, 7 * mm),
            Paragraph("Reproducibility map", styles["Subsection"]),
            styled_table(
                [
                    ["File", "Responsibility"],
                    ["src/data.py", "Loads and validates the model-ready data."],
                    ["src/modeling.py", "Builds X, fits LinearRegression, predicts, and evaluates."],
                    ["app.py", "Displays metrics, tables, and interactive regression graphs."],
                    ["data/component_prediction_dataset.csv", "Stores one-cycle-ahead training and test rows."],
                    ["DATA_PROVENANCE.md", "Documents source and verification rules."],
                ],
                widths=[62 * mm, 92 * mm],
            ),
            Spacer(1, 7 * mm),
            Paragraph("Limitations", styles["Subsection"]),
            Paragraph(
                "The component panel is small and discontinuous. Regulatory changes, "
                "tax revisions, and stabilization decisions can shift abruptly. The "
                "model is pooled across three fuels and is intended as an academic, "
                "explainable baseline; it does not replace EPRA and should not be "
                "treated as a station-level price guarantee.",
                styles["Body"],
            ),
            Paragraph("Conclusion", styles["Subsection"]),
            Paragraph(
                "MafutaPlan achieved multiple linear regression by converting verified "
                "fuel build-up components into seven model features, pairing each input "
                "cycle with the following retail-price cycle, fitting ordinary least "
                "squares only on earlier observations, and testing on an unseen April "
                "2026 cycle. The implementation is transparent, reproducible, and now "
                "visually explained in both the application and this document.",
                styles["Body"],
            ),
        ]
    )

    document.build(
        story,
        onFirstPage=page_header_footer,
        onLaterPages=page_header_footer,
    )
    return OUTPUT


if __name__ == "__main__":
    print(build_pdf())
