from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from src.calculators import cost_for_litres, litres_for_budget, trip_estimate
from src.data import (
    FUEL_COLUMNS,
    get_price,
    load_component_history,
    load_components,
    load_history,
    load_official_prices,
    load_sources,
)
from src.hybrid import AGGREGATE_COMPONENTS, component_shares, reconstruct_price, scenario_estimate

FEATURE_COLUMNS = ["Month_num", "Month_sin", "Month_cos", "Lag_1", "Lag_2", "Rolling_3"]
REQUIRED_COLUMNS = ["Cycle", "Effective_From", "Effective_To", "Super_Petrol", "Diesel", "Kerosene", "Source_ID"]

FUEL_META = {
    "Super Petrol": {"code": "PMS", "tone": "coral", "description": "Private vehicles and petrol engines"},
    "Diesel": {"code": "AGO", "tone": "blue", "description": "Transport, logistics and diesel engines"},
    "Kerosene": {"code": "DPK", "tone": "gold", "description": "Household and commercial use"},
}


@st.cache_data
def load_data() -> pd.DataFrame:
    return load_history()


@st.cache_data(show_spinner="Testing forecasting methods on time-ordered Nairobi data...")
def get_forecast(fuel_column: str):
    from src.modeling import forecast_fuel

    return forecast_fuel(load_data(), fuel_column)


def validate_dataset(dataframe: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError(f"The dataset is missing required columns: {', '.join(missing)}")


def format_table_dates(dataframe: pd.DataFrame) -> pd.DataFrame:
    result = dataframe.copy()
    for column in ["Cycle", "Effective_From", "Effective_To", "Accessed_On"]:
        if column in result:
            result[column] = pd.to_datetime(result[column]).dt.strftime("%d %b %Y")
    return result


def _style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #10251f;
            --muted: #60726c;
            --forest: #083d35;
            --forest-2: #0d594d;
            --mint: #dff4ec;
            --canvas: #f5f7f4;
            --card: #ffffff;
            --line: #dfe7e2;
            --coral: #ff7657;
            --gold: #e9a83a;
            --blue: #3978a8;
        }

        html, body, [class*="css"] {
            font-family: Inter, "Segoe UI", Arial, sans-serif;
            color: var(--ink);
        }

        .stApp { background: var(--canvas); }
        [data-testid="stAppViewContainer"] > .main { background: var(--canvas); }
        .block-container { max-width: 1180px; padding: 1.4rem 2.2rem 2.5rem; }
        [data-testid="stHeader"] { background: transparent; }
        #MainMenu, footer { visibility: hidden; }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #062f2b 0%, #0b473e 100%);
            border-right: 0;
        }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1.1rem; }
        [data-testid="stSidebar"] * { color: #f4fffb; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #c8ddd6; }
        [data-testid="stSidebar"] div[role="radiogroup"] { gap: .45rem; }
        [data-testid="stSidebar"] div[role="radiogroup"] label {
            background: rgba(255,255,255,.055);
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 12px;
            padding: .66rem .7rem;
            transition: all .18s ease;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
            background: rgba(255,255,255,.11);
            border-color: rgba(255,255,255,.18);
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
            background: #ffffff;
            border-color: #ffffff;
            box-shadow: 0 8px 24px rgba(0,0,0,.18);
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
            color: var(--forest) !important;
            font-weight: 750;
        }

        .brand { padding: .35rem .2rem 1.15rem; }
        .brand-mark {
            display: inline-flex; align-items: center; justify-content: center;
            width: 42px; height: 42px; border-radius: 13px;
            background: var(--coral); color: white; font-weight: 900; font-size: 1.05rem;
            box-shadow: 0 7px 18px rgba(0,0,0,.18); margin-bottom: .75rem;
        }
        .brand-name { color: white; font-weight: 850; font-size: 1.35rem; letter-spacing: -.03em; }
        .brand-sub { color: #a8c9bf; font-size: .78rem; margin-top: .15rem; }
        .side-note {
            margin-top: 1rem; padding: .9rem; border-radius: 13px;
            background: rgba(0,0,0,.12); border: 1px solid rgba(255,255,255,.08);
            color: #c8ddd6; font-size: .78rem; line-height: 1.45;
        }
        .verified-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:#66dfb5; margin-right:.38rem; }

        .hero {
            position: relative; overflow: hidden; padding: 2rem 2.1rem;
            border-radius: 24px; background: linear-gradient(125deg, #063a33 0%, #0b5b4e 72%, #147263 100%);
            color: white; box-shadow: 0 18px 46px rgba(8,61,53,.16); margin-bottom: .85rem;
        }
        .hero:after {
            content: ""; position: absolute; width: 300px; height: 300px;
            border-radius: 50%; right: -90px; top: -160px;
            border: 45px solid rgba(255,255,255,.055);
        }
        .hero-grid { display:grid; grid-template-columns: 1fr auto; gap: 2rem; align-items:end; position:relative; z-index:1; }
        .eyebrow { font-size: .72rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: #9ee2ce; }
        .hero h1 { margin: .45rem 0 .55rem; color: white; font-size: clamp(2rem, 4vw, 3.15rem); line-height: 1.02; letter-spacing: -.052em; max-width: 760px; }
        .hero p { margin: 0; color: #d3ebe4; max-width: 710px; line-height: 1.55; font-size: .97rem; }
        .hero-badge {
            min-width: 175px; padding: .95rem 1rem; border-radius: 16px;
            background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.16); backdrop-filter: blur(8px);
        }
        .hero-badge strong { display:block; color:white; font-size:1.05rem; margin-top:.25rem; }
        .hero-badge span { color:#bde1d7; font-size:.74rem; }

        .status-strip {
            display:flex; flex-wrap:wrap; align-items:center; gap:.55rem 1.2rem;
            padding:.8rem 1rem; margin-bottom:1.65rem; background:#fff;
            border:1px solid var(--line); border-radius:14px; color:var(--muted); font-size:.79rem;
        }
        .status-pill { color:var(--forest); background:var(--mint); border-radius:999px; padding:.32rem .62rem; font-weight:800; }
        .status-item strong { color:var(--ink); font-weight:750; }

        .section-head { margin: .25rem 0 1.05rem; }
        .section-head .kicker { color: var(--forest-2); font-weight: 850; text-transform: uppercase; letter-spacing: .1em; font-size: .69rem; }
        .section-head h2 { margin: .24rem 0 .28rem; font-size: 1.72rem; letter-spacing: -.035em; color:var(--ink); }
        .section-head p { margin:0; color:var(--muted); font-size:.9rem; max-width:760px; }

        .price-card {
            position:relative; overflow:hidden; background:var(--card); border:1px solid var(--line);
            border-radius:18px; padding:1.15rem 1.15rem 1.05rem; min-height:148px;
            box-shadow:0 7px 24px rgba(26,55,46,.055);
        }
        .price-card:before { content:""; position:absolute; left:0; right:0; top:0; height:4px; background:var(--accent); }
        .price-top { display:flex; justify-content:space-between; align-items:center; }
        .fuel-name { font-size:.84rem; color:var(--muted); font-weight:750; }
        .fuel-code { font-size:.66rem; font-weight:850; color:var(--accent); background:var(--soft); padding:.28rem .45rem; border-radius:7px; }
        .big-price { margin:.62rem 0 .2rem; font-weight:900; color:var(--ink); font-size:1.9rem; letter-spacing:-.04em; }
        .big-price small { font-size:.78rem; font-weight:750; color:var(--muted); letter-spacing:0; }
        .fuel-desc { color:#7a8a85; font-size:.72rem; line-height:1.35; }
        .price-card.coral { --accent: var(--coral); --soft:#fff0ec; }
        .price-card.blue { --accent: var(--blue); --soft:#eaf3f9; }
        .price-card.gold { --accent: var(--gold); --soft:#fff6e4; }

        .panel {
            background:#fff; border:1px solid var(--line); border-radius:20px;
            padding:1.2rem 1.25rem .8rem; box-shadow:0 8px 26px rgba(26,55,46,.045); margin-top:1rem;
        }
        .panel-title { font-size:1rem; color:var(--ink); font-weight:850; margin-bottom:.1rem; }
        .panel-copy { color:var(--muted); font-size:.8rem; margin-bottom:.65rem; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background:#fff; border-color:var(--line) !important; border-radius:20px !important;
            box-shadow:0 8px 26px rgba(26,55,46,.045); padding:.25rem .35rem;
        }
        .result-card {
            background:linear-gradient(135deg,#edf8f4,#f8fbf9); border:1px solid #cce8de;
            border-radius:16px; padding:1rem 1.05rem; margin:.55rem 0 .75rem;
        }
        .result-label { color:#56716a; font-size:.72rem; font-weight:800; text-transform:uppercase; letter-spacing:.08em; }
        .result-value { color:var(--forest); font-size:1.82rem; font-weight:900; letter-spacing:-.04em; margin:.15rem 0; }
        .result-note { color:#668079; font-size:.75rem; }

        div[data-testid="stMetric"] {
            background:#fff; border:1px solid var(--line); padding:.9rem 1rem;
            border-radius:16px; box-shadow:0 6px 20px rgba(26,55,46,.045);
        }
        div[data-testid="stMetricLabel"] { color:var(--muted); }
        div[data-testid="stMetricValue"] { color:var(--ink); font-weight:850; letter-spacing:-.025em; }
        div[data-baseweb="select"] > div, [data-testid="stNumberInput"] input {
            border-color:#d7e2dc; border-radius:11px;
        }
        div[role="radiogroup"] { gap:.5rem; }
        div[role="radiogroup"] label { border-radius:10px; }
        [data-testid="stAlert"] { border-radius:14px; }
        [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:14px; overflow:hidden; }
        [data-testid="stExpander"] { background:#fff; border:1px solid var(--line); border-radius:14px; overflow:hidden; }
        hr { border-color:var(--line); margin-top:2rem; }
        .source-link a { display:inline-block; color:var(--forest-2); font-size:.78rem; font-weight:800; text-decoration:none; margin-top:.65rem; }
        .footer-note { color:#7b8b86; font-size:.72rem; text-align:center; padding:.3rem 0 1rem; }
        .journey-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.75rem; margin:.8rem 0 1.2rem; }
        .journey-step { background:#fff; border:1px solid var(--line); border-radius:15px; padding:.85rem; min-height:112px; }
        .journey-number { color:var(--coral); font-size:.7rem; font-weight:900; letter-spacing:.08em; }
        .journey-step strong { display:block; color:var(--ink); margin:.25rem 0; font-size:.86rem; }
        .journey-step span { color:var(--muted); font-size:.72rem; line-height:1.4; }
        .method-card { background:#f0f8f5; border-left:4px solid var(--forest-2); border-radius:12px; padding:.9rem 1rem; color:#45655d; font-size:.82rem; }

        @media (max-width: 760px) {
            .block-container { padding: 1rem 1rem 2rem; }
            .hero { padding:1.5rem 1.3rem; border-radius:19px; }
            .hero-grid { grid-template-columns:1fr; gap:1.1rem; }
            .hero-badge { min-width:0; }
            .status-strip { align-items:flex-start; flex-direction:column; }
            .journey-grid { grid-template-columns:1fr 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar() -> str:
    st.sidebar.markdown(
        """
        <div class="brand">
            <div class="brand-mark">MP</div>
            <div class="brand-name">MafutaPlan</div>
            <div class="brand-sub">Nairobi fuel intelligence</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    page = st.sidebar.radio(
        "Navigation",
        ["Overview", "Fuel price journey", "Cost reconstruction", "Forecast & scenarios", "Planning calculator", "Evidence & methodology"],
        label_visibility="collapsed",
    )
    st.sidebar.markdown(
        """
        <div class="side-note">
            <span class="verified-dot"></span><strong>Verified Nairobi scope</strong><br>
            Official records are linked to EPRA evidence. Forecasts are clearly marked as experimental.
        </div>
        """,
        unsafe_allow_html=True,
    )
    return page


def _hero(current: pd.Series, active: bool) -> None:
    status = "Active official cycle" if active else "Latest verified record"
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-grid">
            <div>
              <div class="eyebrow">Bachelor of Science in IT final project</div>
              <h1>From landed fuel<br>to Nairobi pump price.</h1>
              <p>A source-backed decision-support system that reconstructs the regulated fuel-price chain, tests next-cycle forecasting methods and explains every input.</p>
            </div>
            <div class="hero-badge">
              <span>{status}</span>
              <strong>{current['Effective_From']:%d %b} - {current['Effective_To']:%d %b %Y}</strong>
              <span>Nairobi maximum retail prices</span>
            </div>
          </div>
        </div>
        <div class="status-strip">
          <span class="status-pill">EPRA verified</span>
          <span class="status-item"><strong>Market</strong> &nbsp;Nairobi</span>
          <span class="status-item"><strong>Products</strong> &nbsp;Petrol, Diesel, Kerosene</span>
          <span class="status-item"><strong>Verified</strong> &nbsp;{date.today():%d %b %Y}</span>
          <span class="status-item">Prices shown are regulatory caps</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section(kicker: str, title: str, copy: str) -> None:
    st.markdown(
        f'<div class="section-head"><div class="kicker">{kicker}</div><h2>{title}</h2><p>{copy}</p></div>',
        unsafe_allow_html=True,
    )


def _price_card(fuel: str, price: float) -> None:
    meta = FUEL_META[fuel]
    st.markdown(
        f"""
        <div class="price-card {meta['tone']}">
          <div class="price-top"><span class="fuel-name">{fuel}</span><span class="fuel-code">{meta['code']}</span></div>
          <div class="big-price">KSh {price:,.2f} <small>/ litre</small></div>
          <div class="fuel-desc">{meta['description']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _result(label: str, value: str, note: str) -> None:
    st.markdown(
        f'<div class="result-card"><div class="result-label">{label}</div><div class="result-value">{value}</div><div class="result-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


def _overview_page(official: pd.DataFrame, current: pd.Series, source_urls: dict[str, str], history: pd.DataFrame) -> None:
    _section("Current price cycle", "Official Nairobi pump-price caps", "The latest verified maximum retail prices for the active EPRA cycle.")
    columns = st.columns(3, gap="medium")
    for column, fuel in zip(columns, FUEL_COLUMNS):
        with column:
            _price_card(fuel, get_price(official, fuel))

    st.markdown(f'<div class="source-link"><a href="{source_urls[current["Source_ID"]]}" target="_blank">View recorded EPRA evidence &rarr;</a></div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown('<div class="panel-title">Price movement</div><div class="panel-copy">Official monthly Nairobi caps across the complete research period.</div>', unsafe_allow_html=True)
        st.line_chart(history.set_index("Cycle")[["Super_Petrol", "Diesel", "Kerosene"]], color=["#ff7657", "#3978a8", "#e9a83a"])


def _calculator_page(official: pd.DataFrame) -> None:
    _section("Personal planning", "Fuel cost calculator", "Convert the official Nairobi cap into a purchase, budget or trip estimate.")
    with st.container(border=True):
        st.markdown('<div class="panel-title">Fuel cost planner</div><div class="panel-copy">Choose a fuel and planning task. Results use the current official Nairobi cap.</div>', unsafe_allow_html=True)
        fuel = st.selectbox("Fuel product", list(FUEL_COLUMNS), key="calc_fuel")
        price = get_price(official, fuel)
        mode = st.radio("Planning task", ["Cost for litres", "Litres for a budget", "Trip cost"], horizontal=True)

        if mode == "Cost for litres":
            litres = st.number_input("Litres to purchase", min_value=0.1, value=20.0, step=1.0)
            _result("Estimated purchase cost", f"KSh {cost_for_litres(litres, price):,.2f}", f"{litres:g} litres at KSh {price:.2f} per litre")
        elif mode == "Litres for a budget":
            budget = st.number_input("Available budget (KSh)", min_value=1.0, value=3000.0, step=100.0)
            _result("Fuel within budget", f"{litres_for_budget(budget, price):,.2f} litres", f"KSh {budget:,.2f} budget at KSh {price:.2f} per litre")
        else:
            a, b, c = st.columns(3)
            distance = a.number_input("Complete journey (km)", min_value=0.1, value=100.0)
            efficiency = b.number_input("Vehicle efficiency (km/L)", min_value=0.1, value=12.0)
            contingency = c.slider("Traffic allowance", 0, 30, 10, format="%d%%")
            result = trip_estimate(distance, efficiency, price, contingency)
            r1, r2 = st.columns(2)
            with r1:
                _result("Estimated fuel required", f"{result['litres']:.2f} litres", f"Includes a {contingency}% traffic allowance")
            with r2:
                _result("Estimated journey cost", f"KSh {result['cost']:,.2f}", f"Based on {fuel} at KSh {price:.2f}/L")
            st.caption("Enter the complete distance, including the return leg where applicable.")


def _forecast_page(history: pd.DataFrame, component_history: pd.DataFrame) -> None:
    _section("Planning outlook", "Forecast and cost scenarios", "Separate a tested statistical forecast from a transparent, user-controlled EPRA cost scenario.")
    fuel = st.selectbox("Fuel product", list(FUEL_COLUMNS), key="forecast_fuel")
    result = get_forecast(FUEL_COLUMNS[fuel])

    forecast_tab, scenario_tab, answer_tab = st.tabs(["Next-cycle forecast", "Cost scenario", "Is this regression?"])

    with forecast_tab:
        c1, c2, c3 = st.columns([1.25, 1, 1])
        c1.metric(f"{result.next_date:%B %Y} estimate", f"KSh {result.prediction:,.2f}/L")
        c2.metric("Observed error band", f"{result.lower:,.2f} - {result.upper:,.2f}")
        c3.metric("Holdout MAE", f"KSh {result.mae:.2f}")

        from src.modeling import build_trend_chart

        with st.container(border=True):
            st.markdown('<div class="panel-title">Historical path and next-cycle estimate</div><div class="panel-copy">The forecast line connects the latest official cycle with the experimental next-cycle point.</div>', unsafe_allow_html=True)
            st.line_chart(build_trend_chart(history, FUEL_COLUMNS[fuel], result), color=["#9aaba5", "#ff7657"])

        comparison = "outperformed" if result.mae < result.baseline_mae else "did not outperform"
        st.info(f"**Selected method:** {result.model_name}. It was selected on {result.selection_points} earlier sequential forecasts and tested once on {result.validation_points} untouched cycles. It {comparison} the previous-cycle benchmark, whose MAE was KSh {result.baseline_mae:.2f}.")
        st.warning("Academic planning estimate only. It is not an EPRA announcement, and the observed error band is not a guaranteed confidence interval.")

    with scenario_tab:
        basis = component_history.loc[component_history["Fuel"].eq(fuel)].sort_values("Effective_From").iloc[-1]
        st.caption(f"Real EPRA component basis: {basis['Effective_From']:%d %b %Y} to {basis['Effective_To']:%d %b %Y}. This is a what-if calculation, not a claim that those components are current.")
        a, b, c = st.columns(3)
        landed_change = a.slider("Landed-cost change", -30, 40, 0, format="%d%%")
        distribution_change = b.slider("Distribution/storage change", -20, 30, 0, format="%d%%")
        margin_change = c.slider("Margin change", -20, 30, 0, format="%d%%")
        d, e = st.columns(2)
        tax_change = d.number_input("Tax/levy policy change (KSh/L)", value=0.0, step=1.0)
        stabilization = e.number_input("Stabilization adjustment (KSh/L)", value=float(basis["Stabilization_Adjustment"]), step=0.5)
        scenario = scenario_estimate(
            basis,
            landed_change_pct=landed_change,
            distribution_change_pct=distribution_change,
            margin_change_pct=margin_change,
            tax_change=tax_change,
            stabilization_adjustment=stabilization,
        )
        s1, s2, s3 = st.columns(3)
        s1.metric("Reviewed basis", f"KSh {scenario.base_price:.2f}/L")
        s2.metric("Scenario estimate", f"KSh {scenario.estimated_price:.2f}/L")
        s3.metric("Scenario change", f"KSh {scenario.change:+.2f}/L")
        chart = pd.DataFrame({"Component": list(scenario.components), "KSh per litre": list(scenario.components.values())})
        st.bar_chart(chart.set_index("Component"), horizontal=True, color="#0d7463")

    with answer_tab:
        st.markdown("""
        <div class="method-card"><strong>Yes—regression is evaluated, but it is not automatically the winner.</strong><br>
        The application compares linear regression, ridge regression, random forest and gradient boosting with a previous-cycle baseline using time-ordered validation. The method with the lowest earlier error is selected, then tested on untouched final cycles. The cost reconstruction itself is deterministic arithmetic, not regression.</div>
        """, unsafe_allow_html=True)
        st.write("**Forecast inputs:** month index, seasonal sine/cosine, previous one- and two-cycle prices, and the previous three-cycle mean.")
        st.write("**Cost-scenario inputs:** official landed cost, Mombasa-to-Nairobi pipeline/distribution and losses, regulated margins, taxes/levies, and price stabilization.")
        st.caption("A future version can forecast landed cost directly when a longer verified monthly Annex panel is available. The present system does not leak same-cycle costs into a next-cycle prediction.")


def _components_page(components: pd.DataFrame, source_urls: dict[str, str]) -> None:
    _section("End-to-end supply chain", "The journey from imported product to Nairobi pump", "Kenya imports refined fuel. The system follows the real regulated path and never assumes that the international product price equals the Nairobi retail price.")
    steps = [
        ("01", "International procurement", "Refined PMS, AGO and DPK are procured under Kenya's import arrangements."),
        ("02", "Ocean freight & insurance", "Freight, premium, marine insurance and financing contribute to landed cost."),
        ("03", "Mombasa landing", "Port, jetty, inspection, handling, storage and allowable ocean losses are recognized."),
        ("04", "Pipeline to Nairobi", "KPC primary transport, pipeline losses and depot costs move product inland."),
        ("05", "Nairobi depot & delivery", "Secondary storage and delivery within the regulated radius reach stations."),
        ("06", "Wholesale & retail", "EPRA-approved importer and dealer margins support distribution and operations."),
        ("07", "Taxes & levies", "Excise, road, development, regulatory, railway, anti-adulteration and import levies apply."),
        ("08", "Price stabilization", "A deficit or surplus adjustment can cushion or recover price changes before the cap."),
    ]
    cards = "".join(f'<div class="journey-step"><div class="journey-number">STEP {n}</div><strong>{title}</strong><span>{copy}</span></div>' for n, title, copy in steps)
    st.markdown(f'<div class="journey-grid">{cards}</div>', unsafe_allow_html=True)
    st.info("Kenya's refinery ceased processing crude oil in 2013. The relevant present-day path is therefore **imported refined petroleum product → Mombasa → Nairobi → retail station**, not crude oil refined locally.")

    _section("Worked official example", "What makes up one litre?", "A detailed EPRA Annex III example with each charge preserved in Kenya shillings per litre.")
    fuel = st.selectbox("Fuel product", list(FUEL_COLUMNS), key="component_fuel")
    detail = components.loc[components["Fuel"].eq(fuel)].copy()
    grouped = detail.groupby("Category", as_index=False)["KES_Per_Litre"].sum()
    total = float(grouped["KES_Per_Litre"].sum())

    left, right = st.columns([.8, 1.55], gap="large")
    with left:
        _result("Published retail total", f"KSh {total:.2f}/L", f"Effective {detail['Effective_From'].iloc[0]:%d %b} - {detail['Effective_To'].iloc[0]:%d %b %Y}")
        st.caption("Historical composition retained for explanation; it is not the current July 2026 component mix.")
    with right:
        st.bar_chart(grouped.set_index("Category")["KES_Per_Litre"], horizontal=True, color="#0d7463")

    with st.container(border=True):
        st.markdown('<div class="panel-title">Detailed component register</div><div class="panel-copy">Rounded values are shown in Kenya shillings per litre.</div>', unsafe_allow_html=True)
        st.dataframe(detail[["Component", "Category", "KES_Per_Litre"]].rename(columns={"KES_Per_Litre": "KSh per litre"}), hide_index=True, width="stretch")
    st.markdown(f'<div class="source-link"><a href="{source_urls["EPRA_JUNE2025_COSTS"]}" target="_blank">Open EPRA Annex III source &rarr;</a></div>', unsafe_allow_html=True)

    with st.expander("How EPRA builds the pump price"):
        st.latex(r"P_r = P_w + T_s + M_{ri} + M_{ro} + Z + VAT")
        st.write("The build-up includes landed product cost, handling, storage, allowable losses, transport, financing, wholesale and retail margins, taxes, levies and approved adjustments.")
        st.markdown(f"[Read EPRA's formula explanation]({source_urls['EPRA_FORMULA']})")


def _reconstruction_page(component_history: pd.DataFrame) -> None:
    _section("Regulated arithmetic", "Reconstruct an official Nairobi price", "Select a real EPRA cycle and verify that landed cost, inland distribution, margins, stabilization and taxes reproduce the pump-price cap.")
    cycles = sorted(component_history["Effective_From"].unique(), reverse=True)
    selected_cycle = st.selectbox("EPRA component cycle", cycles, format_func=lambda value: pd.Timestamp(value).strftime("%d %B %Y"))
    fuel = st.selectbox("Fuel product", list(FUEL_COLUMNS), key="reconstruction_fuel")
    row = component_history.loc[
        component_history["Effective_From"].eq(pd.Timestamp(selected_cycle)) & component_history["Fuel"].eq(fuel)
    ].iloc[0]

    calculated = reconstruct_price(row)
    c1, c2, c3 = st.columns(3)
    c1.metric("Official EPRA price", f"KSh {row['Retail_Price']:.2f}/L")
    c2.metric("Reconstructed price", f"KSh {calculated:.2f}/L")
    c3.metric("Reconstruction error", f"KSh {calculated - row['Retail_Price']:+.2f}")

    labels = {
        "Landed_Cost": "Landed product cost",
        "Distribution_Storage": "Mombasa–Nairobi distribution & storage",
        "Margins": "Wholesale & retail margins",
        "Stabilization_Adjustment": "Price stabilization adjustment",
        "Taxes_Levies": "Taxes & levies",
    }
    chart = pd.DataFrame({
        "Component": [labels[column] for column in AGGREGATE_COMPONENTS],
        "KSh per litre": [float(row[column]) for column in AGGREGATE_COMPONENTS],
    })
    st.bar_chart(chart.set_index("Component"), horizontal=True, color="#0d7463")
    shares = component_shares(row)
    table = pd.DataFrame({
        "Component": [labels[column] for column in AGGREGATE_COMPONENTS],
        "KSh per litre": [float(row[column]) for column in AGGREGATE_COMPONENTS],
        "Share of price": [f"{shares[column]:.1f}%" for column in AGGREGATE_COMPONENTS],
    })
    st.table(table)
    st.markdown(f"[Open the exact EPRA release used for this record]({row['PDF_URL']})")
    st.caption(row["Quality_Notes"])


def _evidence_page(history: pd.DataFrame, component_history: pd.DataFrame, sources: pd.DataFrame) -> None:
    _section("Research evidence", "Data, validation and methodology", "Inspect the verified history, evaluation design and first-party source register behind the application.")
    fuel = st.selectbox("Fuel product", list(FUEL_COLUMNS), key="trend_fuel")
    with st.container(border=True):
        st.markdown('<div class="panel-title">Nairobi price history</div><div class="panel-copy">55 continuous monthly cycles from January 2022 to July 2026.</div>', unsafe_allow_html=True)
        st.line_chart(history.set_index("Cycle")[[FUEL_COLUMNS[fuel]]].rename(columns={FUEL_COLUMNS[fuel]: "KSh per litre"}), color="#0d7463")

    result = get_forecast(FUEL_COLUMNS[fuel])
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Selected method", result.model_name)
    q2.metric("Holdout MAE", f"KSh {result.mae:.2f}")
    q3.metric("Holdout RMSE", f"KSh {result.rmse:.2f}")
    q4.metric("Baseline MAE", f"KSh {result.baseline_mae:.2f}")

    st.markdown("#### Evaluation design")
    st.write("Five candidate methods are compared through expanding-window forecasts on an earlier selection period. The selected method is then assessed once on the final ten cycles, which are not used to choose the winner.")
    st.caption("The sample remains small and policy-sensitive. Future taxes, subsidies, stabilization, exchange rates and landed-product costs are unknown to this price-lag model.")

    with st.expander("Model features and leakage controls"):
        st.code(", ".join(FEATURE_COLUMNS))
        st.write("Every feature is derived from the calendar or prices published before the target cycle. Same-cycle exchange-rate and crude-oil values are excluded.")
    with st.expander("Verified Nairobi history"):
        shown = history[["Cycle", "Effective_From", "Effective_To", *FUEL_COLUMNS.values(), "Source_ID"]]
        st.dataframe(format_table_dates(shown), hide_index=True, width="stretch")
    with st.expander("Reviewed EPRA component panel"):
        st.dataframe(format_table_dates(component_history), hide_index=True, width="stretch")
    with st.expander("First-party source register"):
        st.dataframe(format_table_dates(sources), hide_index=True, width="stretch")


def main() -> None:
    st.set_page_config(page_title="MafutaPlan | Nairobi Fuel Planner", page_icon="⛽", layout="wide", initial_sidebar_state="expanded")
    _style()

    history = load_data()
    official = load_official_prices()
    components = load_components()
    component_history = load_component_history()
    sources = load_sources()
    validate_dataset(history)
    current = official.iloc[0]
    source_urls = sources.set_index("Source_ID")["URL"].to_dict()
    active = current["Effective_From"].date() <= date.today() <= current["Effective_To"].date()

    page = _sidebar()
    _hero(current, active)

    if page == "Overview":
        _overview_page(official, current, source_urls, history)
    elif page == "Fuel price journey":
        _components_page(components, source_urls)
    elif page == "Cost reconstruction":
        _reconstruction_page(component_history)
    elif page == "Forecast & scenarios":
        _forecast_page(history, component_history)
    elif page == "Planning calculator":
        _calculator_page(official)
    else:
        _evidence_page(history, component_history, sources)

    st.divider()
    st.markdown('<div class="footer-note">MafutaPlan &nbsp;·&nbsp; Nairobi-only academic decision-support project &nbsp;·&nbsp; Official evidence from EPRA and KNBS</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
