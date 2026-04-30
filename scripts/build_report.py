from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
OUTPUTS_DIR = ROOT / "outputs"
CHARTS_DIR = OUTPUTS_DIR / "charts"
DIAGRAMS_DIR = OUTPUTS_DIR / "diagrams"
SCREENSHOTS_DIR = OUTPUTS_DIR / "screenshots"
APPENDICES_DIR = ROOT / "appendices"
REPORT_PATH = DOCS_DIR / "Ryan_Final_Project_Report.docx"


def set_cell_shading(cell, fill="D9E2F3"):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_landscape(section):
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Cm(29.7)
    section.page_height = Cm(21.0)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)


def set_portrait(section):
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)


def apply_run_format(run, size=14, bold=False, italic=False, font_name="Times New Roman"):
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn("w:ascii"), font_name)
    run._element.rPr.rFonts.set(qn("w:hAnsi"), font_name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic


def apply_paragraph_format(paragraph, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6, space_before=0, line_spacing=1.5):
    paragraph.alignment = alignment
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.space_before = Pt(space_before)
    paragraph.paragraph_format.line_spacing = line_spacing


def style_document(doc):
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Times New Roman"
    normal_style._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    normal_style._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    normal_style.font.size = Pt(14)

    for style_name in ["Title", "Heading 1", "Heading 2", "Heading 3"]:
        style = doc.styles[style_name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")

    doc.styles["Title"].font.size = Pt(16)
    doc.styles["Title"].font.bold = True
    doc.styles["Heading 1"].font.size = Pt(16)
    doc.styles["Heading 1"].font.bold = True
    doc.styles["Heading 2"].font.size = Pt(14)
    doc.styles["Heading 2"].font.bold = True
    doc.styles["Heading 3"].font.size = Pt(14)
    doc.styles["Heading 3"].font.bold = True

    if "CodeBlock" not in doc.styles:
        style = doc.styles.add_style("CodeBlock", WD_STYLE_TYPE.PARAGRAPH)
        style.font.name = "Consolas"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Consolas")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Consolas")
        style.font.size = Pt(11)


def add_paragraph(doc, text, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY, bold=False, italic=False, size=14, style_name=None, space_after=6):
    paragraph = doc.add_paragraph(style=style_name)
    run = paragraph.add_run(text)
    apply_run_format(run, size=size, bold=bold, italic=italic, font_name="Times New Roman" if style_name != "CodeBlock" else "Consolas")
    apply_paragraph_format(paragraph, alignment=alignment, space_after=space_after)
    return paragraph


def add_heading(doc, text, level=1, center=False):
    paragraph = doc.add_paragraph(style=f"Heading {level}")
    run = paragraph.add_run(text)
    apply_run_format(run, size=16 if level == 1 else 14, bold=True)
    apply_paragraph_format(
        paragraph,
        alignment=WD_ALIGN_PARAGRAPH.CENTER if center or level == 1 else WD_ALIGN_PARAGRAPH.LEFT,
        space_after=8,
    )
    return paragraph


def add_caption(doc, text):
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(text)
    apply_run_format(run, size=12, bold=False, italic=False)
    apply_paragraph_format(paragraph, alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
    paragraph.paragraph_format.keep_together = True
    return paragraph


def add_code_block(doc, code_text):
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    cell = table.cell(0, 0)
    set_cell_shading(cell, "F2F2F2")
    paragraph = cell.paragraphs[0]
    for line in code_text.strip().splitlines():
        run = paragraph.add_run(line)
        apply_run_format(run, size=10, font_name="Consolas")
        run.add_break()
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.15
    return table


def add_dataframe_table(doc, dataframe, caption, font_size=11, column_widths=None):
    if caption:
        add_caption(doc, caption)
    rows, cols = dataframe.shape
    table = doc.add_table(rows=rows + 1, cols=cols)
    table.style = "Table Grid"
    table.autofit = True

    for col_index, column_name in enumerate(dataframe.columns):
        cell = table.cell(0, col_index)
        cell.text = str(column_name)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_shading(cell, "D9E2F3")
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            apply_run_format(run, size=font_size, bold=True)

    for row_index in range(rows):
        for col_index in range(cols):
            value = dataframe.iloc[row_index, col_index]
            cell = table.cell(row_index + 1, col_index)
            cell.text = str(value)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            para = cell.paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER if isinstance(value, (int, float)) else WD_ALIGN_PARAGRAPH.LEFT
            for run in para.runs:
                apply_run_format(run, size=font_size)

    if column_widths:
        for row in table.rows:
            for cell, width_cm in zip(row.cells, column_widths):
                cell.width = Cm(width_cm)

    doc.add_paragraph("")
    return table


def add_chunked_dataframe_tables(doc, dataframe, caption_base, rows_per_table, font_size=8, column_widths=None):
    for part_index, start in enumerate(range(0, len(dataframe), rows_per_table), start=1):
        chunk = dataframe.iloc[start : start + rows_per_table].reset_index(drop=True)
        caption = f"{caption_base} (Part {part_index})"
        add_dataframe_table(doc, chunk, caption, font_size=font_size, column_widths=column_widths)
        if start + rows_per_table < len(dataframe):
            doc.add_page_break()


def add_figure(doc, image_path, caption, width_inches=6.3):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    paragraph.paragraph_format.keep_together = True
    run = paragraph.add_run()
    run.add_picture(str(image_path), width=Inches(width_inches))
    caption_paragraph = add_caption(doc, caption)
    caption_paragraph.paragraph_format.keep_with_next = True


def add_cover_page(doc):
    add_paragraph(doc, "FUEL PRICE PREDICTION SYSTEM USING MACHINE LEARNING", alignment=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=16, space_after=18)
    add_paragraph(doc, "RYAN ALFRED NYAMBATI", alignment=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=14)
    add_paragraph(doc, "SCT222-0195/2021", alignment=WD_ALIGN_PARAGRAPH.CENTER, size=14)
    add_paragraph(doc, "Department of Information Technology", alignment=WD_ALIGN_PARAGRAPH.CENTER, size=14)
    add_paragraph(doc, "Jomo Kenyatta University of Agriculture and Technology", alignment=WD_ALIGN_PARAGRAPH.CENTER, size=14)
    add_paragraph(doc, "Supervisor: ________________________________", alignment=WD_ALIGN_PARAGRAPH.CENTER, size=14, space_after=18)
    add_paragraph(
        doc,
        "A research project submitted to the Department of Information Technology in partial fulfillment of the requirement for the award of the degree of Bachelor of Science in Information Technology at Jomo Kenyatta University of Agriculture and Technology.",
        alignment=WD_ALIGN_PARAGRAPH.CENTER,
        italic=True,
        size=14,
        space_after=18,
    )
    add_paragraph(doc, "2026", alignment=WD_ALIGN_PARAGRAPH.CENTER, size=14)


def add_declaration(doc):
    add_heading(doc, "DECLARATION", level=1, center=True)
    add_paragraph(
        doc,
        "This research project is my original work and has not been presented for the award of a degree in any other university.",
    )
    add_paragraph(doc, "Student Name: Ryan Alfred Nyambati")
    add_paragraph(doc, "Signature: ________________________________        Date: __________________")
    doc.add_paragraph("")
    add_paragraph(
        doc,
        "This research project has been submitted for examination with my approval as the University Supervisor.",
    )
    add_paragraph(doc, "Supervisor Name: ________________________________")
    add_paragraph(doc, "Signature: ________________________________        Date: __________________")


def add_front_matter_placeholders(doc):
    add_heading(doc, "ABSTRACT", level=1, center=True)


def main():
    DOCS_DIR.mkdir(exist_ok=True)

    data = pd.read_csv(ROOT / "fuel_prices.csv")
    data["Date"] = pd.to_datetime(data["Date"], format="%b-%Y")
    data = data.sort_values("Date").reset_index(drop=True)
    data["Month_num"] = range(1, len(data) + 1)

    descriptive_stats = pd.read_csv(APPENDICES_DIR / "Descriptive_Statistics.csv")
    metrics_table = pd.read_csv(APPENDICES_DIR / "Model_Metrics.csv")
    test_cases = pd.read_csv(APPENDICES_DIR / "Test_Cases.csv")
    data_extraction = pd.read_csv(APPENDICES_DIR / "Data_Extraction_Sheet.csv")
    sample_dataset = pd.read_csv(APPENDICES_DIR / "Sample_Dataset.csv")
    project_schedule = pd.read_csv(APPENDICES_DIR / "Project_Schedule.csv")
    project_budget = pd.read_csv(APPENDICES_DIR / "Project_Budget.csv")

    doc = Document()
    style_document(doc)
    set_portrait(doc.sections[0])
    doc.sections[0].different_first_page_header_footer = True

    add_cover_page(doc)
    front_matter_section = doc.add_section(WD_SECTION.NEW_PAGE)
    set_portrait(front_matter_section)

    add_heading(doc, "DECLARATION", level=1, center=True)
    add_paragraph(
        doc,
        "This research project is my original work and has not been presented for the award of a degree in any other university.",
    )
    add_paragraph(doc, "Student Name: Ryan Alfred Nyambati")
    add_paragraph(doc, "Signature: ________________________________        Date: __________________")
    add_paragraph(
        doc,
        "This research project has been submitted for examination with my approval as the University Supervisor.",
    )
    add_paragraph(doc, "Supervisor Name: ________________________________")
    add_paragraph(doc, "Signature: ________________________________        Date: __________________")
    doc.add_page_break()

    add_heading(doc, "ABSTRACT", level=1, center=True)
    abstract_text = (
        "Fuel prices in Kenya change regularly due to movements in international crude oil prices, exchange rates, "
        "and domestic pricing decisions. These changes affect transport costs, household budgets, and business "
        "planning. This project developed a simple Fuel Price Prediction System Using Machine Learning to estimate "
        "next-month prices for Super Petrol, Diesel, and Kerosene. The system was implemented as a Streamlit web "
        "application that loads a verified CSV dataset, converts the date field to datetime format, sorts the records "
        "chronologically, generates Month_num, Lag_1, and Lag_2 features, and trains a Linear Regression model for the "
        "selected fuel type. The dataset used in the project contains 52 monthly observations covering January 2022 to "
        "April 2026 with the variables Date, USD_KES, Crude_Oil, Super_Petrol, Diesel, and Kerosene. The application "
        "accepts expected USD/KES and crude oil values from the user, predicts the next-month fuel price in Kenya "
        "shillings, and displays MAE, MSE, R² Score, a trend chart, and expandable dataset views. The live system was "
        "tested using smoke, unit, functional, integration, GUI, performance, compatibility, regression, and acceptance "
        "tests. The results show that the system works correctly as a school project prototype, although the model "
        "accuracy remains limited because of the small dataset and the simple linear approach. The project therefore "
        "demonstrates a working machine learning application for fuel price forecasting while also showing the need for "
        "broader data coverage and additional models in future work."
    )
    add_paragraph(doc, abstract_text)
    doc.add_page_break()

    add_heading(doc, "TABLE OF CONTENTS", level=1, center=True)
    add_paragraph(doc, "[[TOC]]", alignment=WD_ALIGN_PARAGRAPH.LEFT)
    doc.add_page_break()

    add_heading(doc, "LIST OF TABLES", level=1, center=True)
    add_paragraph(doc, "[[LIST_TABLES]]", alignment=WD_ALIGN_PARAGRAPH.LEFT)
    doc.add_page_break()

    add_heading(doc, "LIST OF FIGURES", level=1, center=True)
    add_paragraph(doc, "[[LIST_FIGURES]]", alignment=WD_ALIGN_PARAGRAPH.LEFT)
    doc.add_page_break()

    add_heading(doc, "ACRONYMS", level=1, center=True)
    acronyms = [
        "API - Application Programming Interface",
        "CBK - Central Bank of Kenya",
        "CSV - Comma-Separated Values",
        "EPRA - Energy and Petroleum Regulatory Authority",
        "GUI - Graphical User Interface",
        "KES - Kenya Shilling",
        "MAE - Mean Absolute Error",
        "ML - Machine Learning",
        "MSE - Mean Squared Error",
        "R² - Coefficient of Determination",
        "USD - United States Dollar",
    ]
    for item in acronyms:
        add_paragraph(doc, item, alignment=WD_ALIGN_PARAGRAPH.LEFT)
    doc.add_page_break()

    add_heading(doc, "DEFINITION OF TERMS", level=1, center=True)
    definitions = [
        "Crude oil price: The monthly global benchmark oil price used as one of the independent variables in the model.",
        "Fuel price forecasting: The process of estimating future prices of fuel products using historical data and analytical methods.",
        "Lagged variable: A previous value of the target variable used to help explain the current or future value.",
        "Linear regression: A supervised learning method that models the relationship between input variables and a continuous target value.",
        "Month_num: A sequential month counter created from the ordered dataset to represent the time position of each record.",
        "Prediction accuracy metrics: Numerical measures such as MAE, MSE, and R² used to assess model performance.",
    ]
    for item in definitions:
        add_paragraph(doc, item)

    chapter_section = doc.add_section(WD_SECTION.NEW_PAGE)
    set_portrait(chapter_section)

    add_heading(doc, "CHAPTER 1: INTRODUCTION", level=1, center=True)
    chapter_1 = {
        "1.1 Background": [
            "Fuel pricing remains an important economic issue because petroleum products directly affect transport, production, and household expenditure. Across the world, fuel prices respond to movements in crude oil markets, exchange rates, regulatory decisions, and supply chain conditions. When these drivers change, consumers and businesses experience immediate cost adjustments, making fuel price forecasting a useful planning tool (Hyndman & Athanasopoulos, 2021; World Bank, 2026).",
            "In Kenya, maximum retail prices for Super Petrol, Diesel, and Kerosene are published by the Energy and Petroleum Regulatory Authority (EPRA) on a regular cycle. At the same time, the Kenya shilling to United States dollar exchange rate influences the local cost of imported petroleum products, while international crude oil prices signal global market pressure (Central Bank of Kenya, 2025; Energy and Petroleum Regulatory Authority, n.d.). These linked factors provide a strong basis for building a simple prediction model using public monthly data."
        ],
        "1.2 Project Overview": [
            "This project focuses on the design and implementation of a Fuel Price Prediction System Using Machine Learning. The system was developed as a Streamlit web application that predicts the next-month price of Super Petrol, Diesel, or Kerosene after the user selects a fuel type and enters expected USD/KES and crude oil values.",
            "The project uses a verified monthly dataset stored in CSV format and applies a linear regression model trained on five input features: Month_num, USD_KES, Crude_Oil, Lag_1, and Lag_2. The system also displays model evaluation metrics, a fuel trend chart, and both the historical dataset and lagged dataset so that the output is easy to explain during project defense."
        ],
        "1.3 Statement of the Problem": [
            "Fuel prices in Kenya are important to households, transport operators, and small businesses, yet monthly price movements are difficult to estimate using observation alone. Users who need to plan transport budgets or compare fuel trends often depend on manual guesswork, scattered public notices, or simple spreadsheet checks that do not combine exchange rate data, crude oil prices, and previous fuel price patterns in one system.",
            "Although machine learning can support structured prediction, many existing examples are either too advanced, too data-heavy, or not localized for a small academic project. There was therefore a need for a simple and functional system that could use verified monthly public data to predict next-month Kenyan fuel prices in a way that is easy to implement, test, and explain."
        ],
        "1.4 Proposed Solution": [
            "This research proposes the development of a Fuel Price Prediction System Using Machine Learning that predicts next-month prices for Super Petrol, Diesel, and Kerosene. The system uses a verified CSV dataset and a Linear Regression model trained on Month_num, USD_KES, Crude_Oil, Lag_1, and Lag_2.",
            "The solution is implemented as a Streamlit application so that the user can select a fuel type, enter expected exchange rate and crude oil values, and receive a price estimate in Kenya shillings together with model accuracy metrics and trend visualization. The system therefore combines data preparation, prediction, evaluation, and presentation in one simple interface."
        ],
        "1.5 Objectives": [
            "General Objective: To design and implement a machine learning system for predicting next-month fuel prices in Kenya.",
            "Specific Objectives:",
            "1. To analyze verified monthly fuel price, exchange rate, and crude oil data relevant to the project.",
            "2. To design a fuel price prediction system that uses lagged variables and linear regression.",
            "3. To implement the designed system using Streamlit, Pandas, and Scikit-learn.",
            "4. To test and evaluate the developed system using functional, model, and interface-based tests."
        ],
        "1.6 Research Questions": [
            "1. Which monthly variables are most appropriate for a simple fuel price prediction model in this project?",
            "2. How can lagged fuel price variables be combined with exchange rate and crude oil data in a beginner-friendly machine learning system?",
            "3. How can a Streamlit application be used to present next-month fuel price predictions clearly to a user?",
            "4. How well does the developed system perform when evaluated using standard regression metrics and software testing procedures?"
        ],
        "1.7 Justification": [
            "The project is justified because fuel price changes affect planning and decision-making at both individual and organizational levels. A simple forecasting tool can help users understand the relationship between historical prices, crude oil prices, and exchange rate changes without requiring advanced data science knowledge.",
            "The project is also academically relevant because it demonstrates how a small, publicly sourced dataset can be prepared, modeled, and presented using a practical machine learning workflow. For the student researcher, the project provides experience in data preparation, feature engineering, user interface design, testing, and documentation."
        ],
        "1.8 Proposed Research and System Methodologies": [
            "The research component of the project followed an applied and quantitative approach. Public monthly data on fuel prices, exchange rates, and crude oil prices were compiled through document review and captured using a data extraction sheet. The resulting dataset was then cleaned, checked, summarized, and analyzed using Python tools.",
            "The system component followed an iterative prototyping methodology. This approach was suitable because the application was small in scope and benefited from repeated improvement of the dataset workflow, user interface, and prediction logic. The method allowed the system to be developed in manageable stages from data loading to model training, interface design, testing, and documentation."
        ],
        "1.9 Scope": [
            "The project is limited to monthly fuel price prediction for Kenya using three target variables: Super Petrol, Diesel, and Kerosene. The implemented system uses a verified CSV dataset with records from January 2022 to April 2026 and predicts one month ahead using Month_num, USD_KES, Crude_Oil, Lag_1, and Lag_2.",
            "The project does not include real-time data integration, mobile deployment, or advanced forecasting algorithms beyond Linear Regression. Its purpose is to provide a functional undergraduate prototype that is easy to understand, defend, and improve in future work."
        ],
    }

    for heading, paragraphs in chapter_1.items():
        add_heading(doc, heading, level=2)
        for paragraph in paragraphs:
            add_paragraph(doc, paragraph)

    doc.add_page_break()
    add_heading(doc, "CHAPTER 2: LITERATURE REVIEW", level=1, center=True)
    chapter_2 = {
        "2.1 Introduction": [
            "This chapter reviews the literature related to fuel price forecasting, machine learning, time-based feature engineering, and simple software architecture choices for predictive systems. The review supports the selection of the variables, model, and implementation approach used in this project."
        ],
        "2.2 Theoretical Review": [
            "Machine learning is commonly defined as the development of models that learn patterns from data and use those patterns to make predictions on unseen cases. In supervised learning, the model is trained using input variables and known target values. For this project, the targets are the monthly prices of Super Petrol, Diesel, and Kerosene, while the predictors are Month_num, USD_KES, Crude_Oil, Lag_1, and Lag_2 (Géron, 2022; James et al., 2021).",
            "Linear regression remains one of the most interpretable approaches for continuous prediction problems because it estimates how changes in predictor variables relate to changes in the target value. It is therefore suitable for an undergraduate project where transparency and ease of explanation are important. Scikit-learn documents LinearRegression as an ordinary least squares method that minimizes the residual sum of squares between observed and predicted values (scikit-learn developers, n.d.).",
            "Time-dependent problems also benefit from lagged variables because previous values often carry information about the next observation. Forecasting literature emphasizes that recent historical behavior is useful in short-term prediction, especially when the dataset is ordered in time and when future values are estimated from past trends rather than from random samples (Hyndman & Athanasopoulos, 2021; Montgomery et al., 2024). In this project, Lag_1 and Lag_2 were introduced to capture the most recent month-to-month behavior of the selected fuel."
        ],
        "2.3 Case Study Review": [
            "Kenya offers a useful local application context because monthly petroleum prices are formally published by EPRA and are influenced by both international and domestic factors. EPRA's monthly price publications and pump price formula show that fuel prices are linked to regulated pricing decisions, while the Central Bank of Kenya publishes exchange rate information that reflects currency conditions relevant to import costs (Energy and Petroleum Regulatory Authority, n.d.; Central Bank of Kenya, 2025).",
            "Recent studies also show continued interest in forecasting fuel-related prices using data-driven methods. Alwadi (2025) applied time series, machine learning, and deep learning models to fuel sales price forecasting and found that data-driven models can support operational decisions. Cohen (2025) compared econometric and machine learning techniques for short-term oil price forecasting and showed that lagged behavior and multiple external factors remain important when modeling energy price movements. These studies support the decision to use a data-based forecasting approach, although they are more advanced than the scope of this project."
        ],
        "2.4 Integration and Architecture": [
            "Several implementation choices are possible for a forecasting system. A spreadsheet-only approach is simple but limited in repeatability and interface quality. A database-backed enterprise application may be powerful but would add unnecessary complexity for an undergraduate prototype. A lightweight web-based interface with a flat CSV dataset and a simple model provides a better balance between usability and implementation effort.",
            "For this reason, the project adopted a small layered architecture. The data layer stores verified monthly records in CSV format, the processing layer handles cleaning and feature generation with Pandas, the model layer trains Linear Regression using Scikit-learn, and the presentation layer uses Streamlit to display predictions, charts, and datasets (pandas developers, n.d.; Streamlit, n.d.). This structure is appropriate for a school project because it is functional, minimal, and easy to defend."
        ],
        "2.5 Summary": [
            "The reviewed literature shows that fuel and oil price forecasting can be approached using both statistical and machine learning methods. It also confirms the value of time ordering, lagged variables, and transparent evaluation metrics in short-term prediction tasks."
        ],
        "2.6 Research Gaps": [
            "Many published studies focus on large datasets, advanced hybrid models, or specialized forecasting environments. Fewer examples address a small, transparent, Kenya-focused academic system that can be implemented with public monthly data and explained easily in an undergraduate defense. This project addresses that gap by providing a localized, beginner-friendly web application that uses interpretable features and a simple regression workflow."
        ],
    }

    for heading, paragraphs in chapter_2.items():
        add_heading(doc, heading, level=2)
        for paragraph in paragraphs:
            add_paragraph(doc, paragraph)

    doc.add_page_break()
    add_heading(doc, "CHAPTER 3: SYSTEM ANALYSIS AND DESIGN", level=1, center=True)

    add_heading(doc, "3.1 Introduction", level=2)
    add_paragraph(doc, "This chapter presents the analysis and design of the Fuel Price Prediction System. It explains the development methodology, feasibility study, requirements elicitation process, data analysis, system specification, logical design, and physical design that guided the final implementation.")

    add_heading(doc, "3.2 System Development Methodology", level=2)
    add_paragraph(doc, "The project used an iterative prototyping methodology. The work began with identifying the required dataset structure and core prediction workflow, followed by repeated refinement of the preprocessing logic, user interface, and output presentation. This methodology was suitable because the project requirements became clearer as the prototype was tested using real data and screenshots.")
    add_paragraph(doc, "The main stages were problem definition, data preparation, model design, interface implementation, testing, and documentation. The iterative approach allowed simple feedback loops without over-engineering the system.")

    add_heading(doc, "3.3 Feasibility Study", level=2)
    feasibility_df = pd.DataFrame(
        [
            ["Technical feasibility", "Python, Streamlit, Pandas, and Scikit-learn are readily available and were sufficient for data preparation, model training, and interface development.", "Feasible"],
            ["Economic feasibility", "The project used open-source tools and a lightweight CSV dataset, reducing development cost to normal academic expenses such as internet, printing, and consultation.", "Feasible"],
            ["Operational feasibility", "The system workflow is simple: choose a fuel type, enter expected values, and read the predicted price and metrics.", "Feasible"],
            ["Schedule feasibility", "The project scope was limited to a small forecasting prototype, which made it manageable within the academic project period.", "Feasible"],
        ],
        columns=["Aspect", "Observation", "Conclusion"],
    )
    add_dataframe_table(doc, feasibility_df, "Table 3.1: Feasibility Study Summary", font_size=11, column_widths=[4.0, 11.0, 3.0])

    add_heading(doc, "3.4 Requirements Elicitation", level=2)
    add_paragraph(doc, "Requirements were elicited through document review, observation, and the preparation of a data extraction sheet. Public monthly records were gathered from EPRA pump price releases, Central Bank of Kenya exchange rate publications, and World Bank commodity price resources. Because the project uses monthly public data rather than survey responses, the data extraction sheet served as the main collection instrument.")
    add_paragraph(doc, "For the dataset period used in the final system, the project considered all 52 monthly records from January 2022 to April 2026. This amounted to a census of the selected period rather than a sampled subset.")
    elicitation_df = pd.DataFrame(
        [
            ["Document review", "To identify verified monthly values for fuel prices, exchange rates, and crude oil prices.", "Provided the core numeric dataset."],
            ["Observation", "To understand what the user needs from the app interface and outputs.", "Guided the interface and visualization requirements."],
            ["Data extraction sheet", "To record the exact fields collected for the CSV dataset.", "Ensured consistency of variables and units."],
        ],
        columns=["Technique", "Purpose", "Outcome"],
    )
    add_dataframe_table(doc, elicitation_df, "Table 3.2: Requirements Elicitation Summary", font_size=11, column_widths=[4.2, 8.5, 5.3])

    add_heading(doc, "3.5 Data Analysis", level=2)
    add_paragraph(doc, f"The final verified dataset contains {len(data)} monthly records running from {data['Date'].iloc[0].strftime('%B %Y')} to {data['Date'].iloc[-1].strftime('%B %Y')}. No missing values were found during checking, which means the dataset was complete for the selected variables. Month_num was then created after sorting the data chronologically.")
    add_dataframe_table(doc, descriptive_stats, "Table 3.3: Descriptive Statistics of Project Variables", font_size=11, column_widths=[4.0, 3.2, 3.2, 3.2, 3.2])

    add_figure(doc, CHARTS_DIR / "figure_3_1_fuel_price_trends.png", "Figure 3.1: Fuel Price Trends for Super Petrol, Diesel, and Kerosene", width_inches=6.5)
    add_paragraph(doc, "Figure 3.1 shows that all three fuel prices generally moved upward from 2022, reached high levels around late 2023, and then moderated before rising again in selected months of 2025 and 2026. Super Petrol remained the highest-priced product for most of the period.")

    add_figure(doc, CHARTS_DIR / "figure_3_2_usd_kes_exchange_rate_trend.png", "Figure 3.2: USD/KES Exchange Rate Trend", width_inches=6.3)
    add_paragraph(doc, "Figure 3.2 indicates that the exchange rate generally increased across the study period, showing depreciation of the Kenya shilling against the US dollar. This trend supports the inclusion of USD/KES as an explanatory variable.")

    add_figure(doc, CHARTS_DIR / "figure_3_3_global_crude_oil_price_trend.png", "Figure 3.3: Global Crude Oil Price Trend", width_inches=6.3)
    add_paragraph(doc, "Figure 3.3 shows that crude oil prices were volatile, with a stronger spike in 2022 followed by lower levels in later periods. This variation provides a useful external price signal for the prediction model.")

    add_figure(doc, CHARTS_DIR / "figure_3_4_average_fuel_price_comparison.png", "Figure 3.4: Average Fuel Price Comparison", width_inches=5.6)
    add_paragraph(doc, "Figure 3.4 compares the average prices of the three fuel products. Super Petrol recorded the highest average price, followed by Diesel, while Kerosene had the lowest average price in the dataset.")

    add_heading(doc, "3.6 System Specification", level=2)
    add_paragraph(doc, "The system requirements were grouped into functional and non-functional categories. Functional requirements describe what the system must do, while non-functional requirements describe how well it should do it.")

    functional_df = pd.DataFrame(
        [
            ["FR1", "Load the verified CSV dataset from the project directory."],
            ["FR2", "Convert the Date field to datetime format and sort records chronologically."],
            ["FR3", "Create Month_num, Lag_1, and Lag_2 for the selected fuel type."],
            ["FR4", "Train a Linear Regression model for the selected target fuel."],
            ["FR5", "Accept expected USD/KES and crude oil values from the user."],
            ["FR6", "Predict the next-month price and display it in Kenya shillings."],
            ["FR7", "Display MAE, MSE, and R² Score for the selected model."],
            ["FR8", "Display a trend chart plus expandable historical and lagged datasets."],
        ],
        columns=["Requirement ID", "Functional Requirement"],
    )
    add_dataframe_table(doc, functional_df, "Table 3.4: Functional Requirements", font_size=11, column_widths=[4.0, 12.0])

    non_functional_df = pd.DataFrame(
        [
            ["NFR1", "Usability", "The interface should be simple and easy to understand."],
            ["NFR2", "Performance", "The local app should load and respond quickly for a small dataset."],
            ["NFR3", "Maintainability", "The code should remain short, readable, and beginner-friendly."],
            ["NFR4", "Reliability", "The system should handle the available dataset consistently without crashing."],
            ["NFR5", "Portability", "The project should run through `streamlit run app.py` on a standard Python environment."],
        ],
        columns=["Requirement ID", "Category", "Non-Functional Requirement"],
    )
    add_dataframe_table(doc, non_functional_df, "Table 3.5: Non-Functional Requirements", font_size=11, column_widths=[3.0, 4.0, 9.0])

    add_heading(doc, "3.7 Requirements Analysis and Modeling", level=2)
    add_paragraph(doc, "The analysis of the gathered requirements showed that the system needed a simple user role, a small set of verified input variables, and direct visibility of both prediction results and supporting data. These needs were modeled through the use case and data flow diagrams below.")
    add_figure(doc, DIAGRAMS_DIR / "use_case_diagram.png", "Figure 3.5: Use Case Diagram for the Fuel Price Prediction System", width_inches=6.3)
    add_paragraph(doc, "The use case diagram identifies the main actions performed by the user and the researcher in relation to the prediction system.")
    add_figure(doc, DIAGRAMS_DIR / "level_0_dfd.png", "Figure 3.6: Level 0 Data Flow Diagram", width_inches=6.2)
    add_paragraph(doc, "The level 0 DFD shows how user inputs and the verified CSV dataset move through the prediction process to produce charts, tables, and price estimates.")

    add_heading(doc, "3.8 Logical Design", level=2)
    add_paragraph(doc, "The logical design describes how the application components interact before actual deployment details are considered.")

    add_heading(doc, "3.8.1 System Architecture", level=3)
    add_paragraph(doc, "The chosen architecture follows a simple layered pattern. The dataset layer stores monthly records in CSV form, the processing layer prepares the dataset and lagged features, the model layer trains and applies linear regression, and the interface layer presents the outputs through Streamlit.")
    add_figure(doc, DIAGRAMS_DIR / "system_architecture_diagram.png", "Figure 3.7: System Architecture Diagram", width_inches=6.2)

    add_heading(doc, "3.8.2 Control Flow and Process Design", level=3)
    add_paragraph(doc, "At runtime, the system loads the dataset, prepares the time-based features, trains the model for the currently selected fuel type, accepts user inputs, predicts the next-month price, and then renders the outputs.")
    add_figure(doc, DIAGRAMS_DIR / "control_flow_diagram.png", "Figure 3.8: Control Flow Diagram", width_inches=5.6)
    add_paragraph(doc, "The sequence in Figure 3.8 matches the implementation in app.py and reflects the order in which prediction tasks are executed.")

    add_heading(doc, "3.8.3 Design for Non-Functional Requirements", level=3)
    add_paragraph(doc, "Usability was addressed by keeping the interface small and by presenting only one fuel selection, two numeric inputs, a prediction output, metric cards, and expandable dataset views. Maintainability was improved by separating the code into small helper functions for loading data, creating lagged features, training the model, and preparing the future input frame.")
    add_paragraph(doc, "Basic reliability was supported through dataset column validation and chronological sorting before training. Performance needs were modest because the project uses a small CSV dataset and a light regression model, making local execution fast enough for classroom demonstration.")

    add_heading(doc, "3.9 Physical Design", level=2)
    add_paragraph(doc, "The physical design defines the concrete storage structure and user interface used in the final implementation.")

    add_heading(doc, "3.9.1 Database Design", level=3)
    add_paragraph(doc, "The system uses a flat CSV file rather than a relational database. This choice was intentional because the project dataset is small, static, and easy to distribute within the repository. The physical design therefore focuses on field structure, data types, and the way the file is read into Pandas.")
    dataset_design_df = pd.DataFrame(
        [
            ["Date", "Text converted to datetime", "Month and year of the observation."],
            ["USD_KES", "Float", "Expected or observed exchange rate."],
            ["Crude_Oil", "Float", "Observed global crude oil price in USD per barrel."],
            ["Super_Petrol", "Float", "Monthly fuel price target for Super Petrol."],
            ["Diesel", "Float", "Monthly fuel price target for Diesel."],
            ["Kerosene", "Float", "Monthly fuel price target for Kerosene."],
        ],
        columns=["Field", "Data Type", "Description"],
    )
    add_dataframe_table(doc, dataset_design_df, "Table 3.6: CSV Dataset Design", font_size=11, column_widths=[4.0, 4.5, 10.0])

    add_heading(doc, "3.9.2 User Interface Design", level=3)
    add_paragraph(doc, "The interface design was kept deliberately minimal so that the application remains easy to explain during project defense. The input screen uses a fuel selector and two numeric fields, while the output screen shows prediction, model evaluation metrics, a chart, and expandable tables.")
    add_figure(doc, DIAGRAMS_DIR / "input_form_wireframe.png", "Figure 3.9: Input Form Wireframe", width_inches=6.3)
    add_paragraph(doc, "Figure 3.9 shows the input controls required before a prediction is made.")
    add_figure(doc, DIAGRAMS_DIR / "output_interface_wireframe.png", "Figure 3.10: Output Interface Wireframe", width_inches=5.9)
    add_paragraph(doc, "Figure 3.10 shows the prediction, metrics, chart, and dataset expanders.")

    doc.add_page_break()
    add_heading(doc, "CHAPTER 4: SYSTEM IMPLEMENTATION AND TESTING, CONCLUSIONS AND RECOMMENDATIONS", level=1, center=True)

    add_heading(doc, "4.1 Introduction", level=2)
    add_paragraph(doc, "This chapter explains the implementation environment, the system code generation process, the tests applied to the working application, the user guide, the main conclusions, and the recommendations for future improvement.")

    add_heading(doc, "4.2 Environment and Tools", level=2)
    env_df = pd.DataFrame(
        [
            ["Programming language", "Python 3.12", "Used for data processing, model training, and app logic."],
            ["Frontend and presentation", "Streamlit 1.56.0", "Used to build the web interface."],
            ["Data handling", "Pandas", "Used for CSV loading, sorting, and feature creation."],
            ["Machine learning", "Scikit-learn", "Used for Linear Regression and evaluation metrics."],
            ["Visualization", "Streamlit charts and Matplotlib", "Used for the live chart and report figures."],
            ["Notebook environment", "Jupyter Notebook", "Used for exploratory data analysis and chart generation."],
        ],
        columns=["Component", "Tool", "Purpose"],
    )
    add_dataframe_table(doc, env_df, "Table 4.1: Environment and Tools", font_size=11, column_widths=[4.5, 4.5, 8.0])

    add_heading(doc, "4.3 System Code Generation", level=2)
    add_paragraph(doc, "The final source code was simplified so that the main workflow could be explained clearly. The code first loads the verified CSV file, validates the expected schema, converts the Date field to datetime format, sorts the records, and creates Month_num.")
    add_code_block(
        doc,
        """
data = pd.read_csv(DATA_PATH)
validate_dataset(data)
data["Date"] = pd.to_datetime(data["Date"], format="%b-%Y")
data = data.sort_values("Date").reset_index(drop=True)
data["Month_num"] = range(1, len(data) + 1)
        """,
    )
    add_paragraph(doc, "After the dataset is prepared, the application creates the lagged variables for the selected fuel type. Lag_1 stores the previous month price and Lag_2 stores the price from two months earlier.")
    add_code_block(
        doc,
        """
lagged_data["Lag_1"] = lagged_data[fuel_column].shift(1)
lagged_data["Lag_2"] = lagged_data[fuel_column].shift(2)
lagged_data = lagged_data.dropna().reset_index(drop=True)
        """,
    )
    add_paragraph(doc, "The model is then trained using Month_num, USD_KES, Crude_Oil, Lag_1, and Lag_2. A future input frame is created from the user's expected values and the most recent historical lagged prices.")
    add_code_block(
        doc,
        """
model = LinearRegression()
model.fit(x_train, y_train)
future_input = pd.DataFrame({
    "Month_num": [next_month_num],
    "USD_KES": [usd_kes],
    "Crude_Oil": [crude_oil],
    "Lag_1": [last_price],
    "Lag_2": [second_last_price],
})
prediction = model.predict(future_input)[0]
        """,
    )
    add_paragraph(doc, "Finally, the system displays the predicted price, evaluation metrics, a trend chart, and the historical and lagged datasets in expandable sections. This design keeps the implementation short while still covering the full project requirement.")

    add_heading(doc, "4.4 Testing", level=2)
    add_paragraph(doc, "Testing was carried out to confirm that the application could load the dataset, create lag features, train the model, display the interface correctly, and respond to the required user actions. The project used a combination of smoke, unit, functional, integration, GUI, input validation, model, performance, compatibility, regression, and acceptance testing.")
    add_dataframe_table(doc, metrics_table, "Table 4.2: Model Evaluation Results by Fuel Type", font_size=11, column_widths=[6.0, 3.5, 3.5, 3.5])

    test_section = doc.add_section(WD_SECTION.NEW_PAGE)
    set_landscape(test_section)
    add_chunked_dataframe_tables(
        doc,
        test_cases,
        "Table 4.3: Test Cases and Results",
        rows_per_table=7,
        font_size=7.5,
        column_widths=[1.5, 2.7, 2.5, 4.8, 4.7, 5.2, 1.3],
    )

    portrait_back = doc.add_section(WD_SECTION.NEW_PAGE)
    set_portrait(portrait_back)

    add_figure(doc, SCREENSHOTS_DIR / "application_input_form.png", "Figure 4.1: Application Input Form", width_inches=6.6)
    add_figure(doc, SCREENSHOTS_DIR / "super_petrol_prediction_output.png", "Figure 4.2: Super Petrol Prediction Output", width_inches=6.6)
    add_figure(doc, SCREENSHOTS_DIR / "diesel_prediction_output.png", "Figure 4.3: Diesel Prediction Output", width_inches=6.6)
    add_figure(doc, SCREENSHOTS_DIR / "kerosene_prediction_output.png", "Figure 4.4: Kerosene Prediction Output", width_inches=6.6)
    add_figure(doc, SCREENSHOTS_DIR / "model_evaluation_section.png", "Figure 4.5: Model Evaluation Section", width_inches=6.6)
    add_figure(doc, SCREENSHOTS_DIR / "fuel_price_trend_chart.png", "Figure 4.6: Fuel Price Trend Chart", width_inches=6.6)
    add_figure(doc, SCREENSHOTS_DIR / "historical_dataset_display.png", "Figure 4.7: Historical Dataset Display", width_inches=6.6)
    add_figure(doc, SCREENSHOTS_DIR / "lagged_dataset_display.png", "Figure 4.8: Lagged Dataset Display", width_inches=6.6)

    add_heading(doc, "4.5 User Guide", level=2)
    add_paragraph(doc, "The system can be used through the following simple steps:")
    user_steps = [
        "1. Install the project dependencies using `pip install -r requirements.txt`.",
        "2. Start the application using `streamlit run app.py`.",
        "3. Open the local Streamlit URL shown in the terminal.",
        "4. Select the fuel type to predict: Super Petrol, Diesel, or Kerosene.",
        "5. Enter the expected USD/KES exchange rate and crude oil price for the next month.",
        "6. Read the predicted fuel price in Kenya shillings.",
        "7. Review the displayed MAE, MSE, and R² Score values.",
        "8. View the line chart, historical dataset, and lagged dataset for additional context.",
    ]
    for step in user_steps:
        add_paragraph(doc, step, alignment=WD_ALIGN_PARAGRAPH.LEFT)

    add_heading(doc, "4.6 Conclusions", level=2)
    add_paragraph(doc, "The project achieved its main objective by developing a functional Fuel Price Prediction System Using Machine Learning. The final system loads a verified dataset, prepares lagged variables, trains a Linear Regression model, predicts next-month fuel prices, and displays the required supporting outputs in a simple web interface.")
    add_paragraph(doc, "The most significant accomplishment is that the project integrates data preparation, model training, evaluation, visualization, and user interaction in one beginner-friendly application. However, the evaluation results also show a limitation: the small dataset and simple model reduce generalization performance, as indicated by low or negative R² values. This means the system is best presented as an academic prototype rather than a production forecasting tool.")

    add_heading(doc, "4.7 Recommendations", level=2)
    add_paragraph(doc, "Future work should extend the dataset to cover more years and possibly more explanatory variables, such as inflation, transport cost indicators, or international petroleum product benchmarks where appropriate and verified.")
    add_paragraph(doc, "The project can also be improved by comparing Linear Regression with other forecasting models such as Random Forest, ARIMA, or gradient boosting. In addition, future versions could store data in a database, automate data updates, and provide a downloadable prediction report for users.")

    doc.add_page_break()
    add_heading(doc, "REFERENCES", level=1, center=True)
    references = [
        "Alwadi, M. A. (2025). Fuel sales price forecasting using time series, machine learning, and deep learning models. Engineering, Technology & Applied Science Research, 15(3), 22360-22366. https://doi.org/10.48084/etasr.10348",
        "Central Bank of Kenya. (2025, April 2). Commercial banks' average exchange rates for major currencies / KES (closing of market) [PDF]. https://www.centralbank.go.ke/uploads/cbk_indicative_rates/620318092_CBK%20INDICATIVE%20RATES%203.4.2025.pdf",
        "Cohen, G. (2025). A comprehensive study on short-term oil price forecasting using econometric and machine learning techniques. Machine Learning and Knowledge Extraction, 7(4), 127. https://doi.org/10.3390/make7040127",
        "Energy and Petroleum Regulatory Authority. (n.d.). EPRA pump prices. Retrieved April 29, 2026, from https://www.epra.go.ke/EPRA%20Pump%20Prices",
        "Energy and Petroleum Regulatory Authority. (n.d.). Pump price formulae. Retrieved April 29, 2026, from https://www.epra.go.ke/pump-price-formulae",
        "Géron, A. (2022). Hands-on machine learning with Scikit-learn, Keras, and TensorFlow (3rd ed.). O'Reilly Media.",
        "Hyndman, R. J., & Athanasopoulos, G. (2021). Forecasting: Principles and practice (3rd ed.). OTexts. https://otexts.com/fpp3/",
        "James, G., Witten, D., Hastie, T., & Tibshirani, R. (2021). An introduction to statistical learning: With applications in R (2nd ed.). Springer. https://www.statlearning.com/",
        "Montgomery, D. C., Jennings, C. L., & Kulahci, M. (2024). Introduction to time series analysis and forecasting (3rd ed.). Wiley.",
        "pandas developers. (n.d.). pandas.read_csv. Retrieved April 29, 2026, from https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html",
        "scikit-learn developers. (n.d.). LinearRegression. Retrieved April 29, 2026, from https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html",
        "Streamlit. (n.d.). API reference. Retrieved April 29, 2026, from https://docs.streamlit.io/develop/api-reference",
        "World Bank. (2026). Commodity markets. https://www.worldbank.org/en/research/commodity-markets",
        "World Bank Prospects Group. (2026). World Bank commodities price data (The Pink Sheet). https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/world-bank-commodities-price-data-the-pink-sheet",
    ]
    for reference in references:
        paragraph = doc.add_paragraph()
        run = paragraph.add_run(reference)
        apply_run_format(run, size=12)
        apply_paragraph_format(paragraph, alignment=WD_ALIGN_PARAGRAPH.LEFT, space_after=6)
        paragraph.paragraph_format.left_indent = Cm(0.75)
        paragraph.paragraph_format.first_line_indent = Cm(-0.75)

    doc.add_page_break()
    add_heading(doc, "APPENDICES", level=1, center=True)

    add_heading(doc, "Appendix A: Data Extraction Sheet", level=2)
    add_dataframe_table(doc, data_extraction, "Appendix Table A.1: Data Extraction Sheet", font_size=10, column_widths=[3.5, 5.0, 3.0, 3.0, 5.0])

    add_heading(doc, "Appendix B: Sample Dataset", level=2)
    add_dataframe_table(doc, sample_dataset.head(10), "Appendix Table B.1: Sample Dataset", font_size=10, column_widths=[3.0, 2.5, 2.5, 3.0, 2.5, 2.5])

    add_heading(doc, "Appendix C: Source Code", level=2)
    add_paragraph(doc, "The full application source code is provided in the repository file `app.py` and duplicated in `appendices/App_Source_Code.py`. A short excerpt of the main workflow is shown below.")
    add_code_block(
        doc,
        """
def main() -> None:
    data = load_data()
    selected_fuel = st.selectbox("Select fuel type to predict:", list(FUEL_OPTIONS.keys()))
    fuel_column = FUEL_OPTIONS[selected_fuel]
    model_data = create_lagged_data(data, fuel_column)
    model, metrics = train_model(model_data, fuel_column)
    future_input = build_future_input(data, fuel_column, usd_kes, crude_oil)
    prediction = float(model.predict(future_input)[0])
        """,
    )

    add_heading(doc, "Appendix D: Testing Screenshots", level=2)
    add_paragraph(doc, "The testing screenshots used in Chapter 4 are stored in the `outputs/screenshots/` folder of the repository. These include the application input form, prediction outputs for each fuel type, the model evaluation section, the trend chart, and dataset views.")

    add_heading(doc, "Appendix E: Project Schedule", level=2)
    add_dataframe_table(doc, project_schedule, "Appendix Table E.1: Project Schedule", font_size=10, column_widths=[9.5, 4.0, 4.0])

    add_heading(doc, "Appendix F: Budget", level=2)
    add_dataframe_table(doc, project_budget, "Appendix Table F.1: Project Budget", font_size=10, column_widths=[10.0, 6.0])

    add_heading(doc, "Appendix G: GitHub Repository Link", level=2)
    add_paragraph(doc, "Repository URL: https://github.com/ryanair000/fuel-price-predictor", alignment=WD_ALIGN_PARAGRAPH.LEFT)

    add_heading(doc, "Appendix H: Jupyter Notebook Reference", level=2)
    add_paragraph(doc, "Notebook file: notebooks/FuelPriceAnalysis.ipynb", alignment=WD_ALIGN_PARAGRAPH.LEFT)

    doc.save(REPORT_PATH)
    print(f"Saved report draft to {REPORT_PATH}")


if __name__ == "__main__":
    main()
