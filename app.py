"""STR Deal Finder — Streamlit Dashboard.

Run with: streamlit run app.py
"""

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
import yaml

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent))

from src.financial_analyzer import analyze_deal, calculate_cash_invested, calculate_expenses
from src.improvement_estimator import (
    MARKET_COMP_AMENITIES,
    AmenityItem,
    ImprovementEstimator,
)
from src.models import (
    Confidence,
    PermitInfo,
    PermitStatus,
    Property,
    RevenueEstimate,
    RevenueSource,
)
from src.permit_checker import PermitChecker
from src.revenue_estimator import MARKET_DEFAULTS, RevenueEstimator


def load_config():
    config_path = Path("config/settings.yaml")
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return None


def format_currency(val):
    if val >= 0:
        return f"${val:,.0f}"
    return f"-${abs(val):,.0f}"


def format_pct(val):
    return f"{val:.1%}"


# --- Page Config ---
st.set_page_config(
    page_title="STR Deal Finder",
    page_icon="🏠",
    layout="wide",
)

config = load_config()
if not config:
    st.error("Could not load config/settings.yaml")
    st.stop()

permit_checker = PermitChecker()
improvement_estimator = ImprovementEstimator(config)
revenue_estimator = RevenueEstimator()

# --- Sidebar ---
st.sidebar.title("STR Deal Finder")
page = st.sidebar.radio(
    "Navigate",
    ["Analyze Property", "Market Overview", "Settings"],
)

# ============================================================
# PAGE: Analyze Property
# ============================================================
if page == "Analyze Property":
    st.title("Analyze a Property")
    st.markdown("Enter property details to get a full STR investment analysis with comp-driven improvement costs.")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("Property Details")

        market_names = [m["name"] for m in config["markets"]]
        market = st.selectbox("Market", market_names, index=0)

        address = st.text_input("Address", "123 Mountain View Dr")

        col_price, col_beds = st.columns(2)
        with col_price:
            price = st.number_input("Purchase Price ($)", min_value=50000, max_value=5000000, value=450000, step=25000)
        with col_beds:
            bedrooms = st.number_input("Bedrooms", min_value=1, max_value=10, value=3)

        col_bath, col_sqft = st.columns(2)
        with col_bath:
            bathrooms = st.number_input("Bathrooms", min_value=1.0, max_value=10.0, value=2.0, step=0.5)
        with col_sqft:
            sqft = st.number_input("Sqft", min_value=400, max_value=10000, value=1800, step=100)

        col_tax, col_hoa = st.columns(2)
        with col_tax:
            prop_tax = st.number_input("Annual Property Tax ($)", min_value=0, max_value=50000, value=4000, step=500)
        with col_hoa:
            hoa = st.number_input("Monthly HOA ($)", min_value=0, max_value=2000, value=0, step=50)

        year_built = st.number_input("Year Built", min_value=1900, max_value=2026, value=2010)

        # Existing amenities
        st.subheader("Existing Amenities")
        st.caption("Check off amenities the property already has — these won't be added to improvement costs.")

        market_amenities = MARKET_COMP_AMENITIES.get(market, [])
        amenity_names = [a.name for a in market_amenities]

        existing_amenities = []
        if amenity_names:
            cols = st.columns(2)
            for i, name in enumerate(amenity_names):
                with cols[i % 2]:
                    if st.checkbox(name, key=f"amenity_{name}"):
                        existing_amenities.append(name)
        else:
            st.info("No comp amenity data for this market.")

    with col_right:
        st.subheader("Revenue Assumptions")
        st.caption("Auto-filled from market data. Adjust if you have better numbers.")

        # Get market defaults for auto-fill
        market_data = MARKET_DEFAULTS.get(market, {})
        default_rate, default_occ = market_data.get(min(bedrooms, 6), (200, 0.60))

        col_rate, col_occ = st.columns(2)
        with col_rate:
            nightly_rate = st.number_input("Nightly Rate ($)", min_value=50, max_value=2000, value=int(default_rate), step=25)
        with col_occ:
            occupancy = st.slider("Occupancy Rate", min_value=0.20, max_value=0.95, value=float(default_occ), step=0.01, format="%.0f%%")

        annual_revenue = nightly_rate * occupancy * 365
        st.metric("Projected Annual Revenue", format_currency(annual_revenue))

        st.divider()
        st.subheader("Financial Assumptions")

        fa = config["financial_assumptions"]
        col_dp, col_rate2 = st.columns(2)
        with col_dp:
            down_pct = st.slider("Down Payment %", min_value=0.05, max_value=0.30, value=fa["down_payment_pct"], step=0.05, format="%.0f%%")
        with col_rate2:
            interest_rate = st.slider("Interest Rate %", min_value=0.04, max_value=0.12, value=fa["interest_rate"], step=0.0025, format="%.2f%%")

    # --- Run Analysis ---
    st.divider()
    if st.button("Run Full Analysis", type="primary", use_container_width=True):

        # Build property object
        market_cfg = next(m for m in config["markets"] if m["name"] == market)
        city_parts = market.split(", ")
        city = city_parts[0] if city_parts else market
        state = city_parts[1] if len(city_parts) > 1 else ""

        prop = Property(
            zpid="manual",
            address=address,
            city=city,
            state=state,
            zipcode="00000",
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            sqft=sqft,
            hoa_monthly=hoa if hoa > 0 else None,
            property_tax_annual=prop_tax if prop_tax > 0 else None,
            year_built=year_built,
            market=market,
        )

        revenue = RevenueEstimate(
            annual_revenue=annual_revenue,
            nightly_rate=nightly_rate,
            occupancy_rate=occupancy,
            source=RevenueSource.MANUAL,
            confidence=Confidence.MEDIUM,
        )

        # Override config with user's financial assumptions
        analysis_config = dict(config)
        analysis_config["financial_assumptions"] = dict(fa)
        analysis_config["financial_assumptions"]["down_payment_pct"] = down_pct
        analysis_config["financial_assumptions"]["interest_rate"] = interest_rate

        # Estimate improvements
        imp_estimate = improvement_estimator.estimate(prop, existing_amenities=existing_amenities)

        # Check permit
        permit = permit_checker.check(prop)

        # Run deal analysis
        deal = analyze_deal(prop, revenue, permit, analysis_config, imp_estimate)

        # --- Results ---
        st.divider()

        # Top-line metrics
        col1, col2, col3, col4 = st.columns(4)
        coc_color = "normal" if deal.cash_on_cash_return >= 0.10 else "off"
        with col1:
            st.metric("Cash-on-Cash Return", format_pct(deal.cash_on_cash_return))
        with col2:
            st.metric("Annual Cash Flow", format_currency(deal.annual_cash_flow))
        with col3:
            st.metric("Total Cash Invested", format_currency(deal.cash_invested))
        with col4:
            status_emoji = {"ALLOWED": "✅", "CONDITIONAL": "⚠️", "RESTRICTED": "🚫", "BANNED": "❌", "UNKNOWN": "❓"}
            st.metric("Permit Status", f"{status_emoji.get(permit.status.value, '❓')} {permit.status.value}")

        if deal.is_good_deal:
            st.success("This looks like a GOOD DEAL — CoC >= 10% and permits OK")
        elif deal.cash_on_cash_return >= 0.07:
            st.warning("MARGINAL — CoC is between 7-10%. May work with better revenue assumptions.")
        else:
            st.error(f"POOR DEAL — CoC is only {format_pct(deal.cash_on_cash_return)}")

        # Detailed breakdown
        tab_invest, tab_expenses, tab_improvements, tab_chart = st.tabs(
            ["Investment Summary", "Expense Breakdown", "Improvement Plan", "Visual Breakdown"]
        )

        with tab_invest:
            inv_col1, inv_col2 = st.columns(2)
            with inv_col1:
                st.markdown("**Cash Required to Close & Prep**")
                down = price * down_pct
                closing = price * analysis_config["financial_assumptions"]["closing_cost_pct"]
                data = {
                    "Down Payment": down,
                    "Closing Costs (3%)": closing,
                    "Improvements & Furnishing": deal.improvements.total,
                }
                for label, val in data.items():
                    st.markdown(f"- {label}: **{format_currency(val)}**")
                st.markdown(f"### Total: {format_currency(deal.cash_invested)}")

            with inv_col2:
                st.markdown("**Annual P&L**")
                st.markdown(f"- Revenue: **{format_currency(annual_revenue)}**")
                st.markdown(f"- Expenses: **{format_currency(deal.expenses.total)}**")
                st.markdown(f"- **Net Cash Flow: {format_currency(deal.annual_cash_flow)}**")
                st.markdown(f"- **Monthly Cash Flow: {format_currency(deal.annual_cash_flow / 12)}**")

        with tab_expenses:
            exp = deal.expenses
            expense_items = [
                ("Mortgage (P&I)", exp.mortgage_annual),
                ("Property Tax", exp.property_tax),
                ("Insurance", exp.insurance),
                ("HOA", exp.hoa_annual),
                ("Property Management (22%)", exp.property_management),
                ("Utilities", exp.utilities),
                ("Maintenance (1.5%)", exp.maintenance),
                ("Cleaning", exp.cleaning),
                ("Platform Fees (3%)", exp.platform_fees),
                ("Supplies", exp.supplies),
                ("STR Permit", exp.str_permit),
                ("Accounting", exp.accounting),
                ("Furniture Reserve (3%)", exp.furniture_reserve),
                ("Landscaping", exp.landscaping),
            ]

            exp_col1, exp_col2 = st.columns([2, 1])
            with exp_col1:
                for label, val in expense_items:
                    if val > 0:
                        pct_of_rev = val / annual_revenue * 100 if annual_revenue > 0 else 0
                        st.markdown(f"- {label}: **{format_currency(val)}** ({pct_of_rev:.1f}% of revenue)")
                st.markdown(f"### Total: {format_currency(exp.total)}")

            with exp_col2:
                # Pie chart of expenses
                labels = [label for label, val in expense_items if val > 0]
                values = [val for _, val in expense_items if val > 0]
                fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
                fig.update_layout(height=400, margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

        with tab_improvements:
            imp = deal.improvements

            st.markdown("**What top comps in this market have that this property needs:**")

            if imp.amenity_details:
                for amenity_name, amenity_cost in imp.amenity_details:
                    # Find the full amenity item for materials/labor breakdown
                    amenity_item = None
                    for a in market_amenities:
                        if a.name == amenity_name:
                            amenity_item = a
                            break

                    if amenity_item:
                        st.markdown(
                            f"- **Add {amenity_name}**: {format_currency(amenity_cost)} "
                            f"(materials: {format_currency(amenity_item.materials_cost)} + "
                            f"labor: {format_currency(amenity_item.labor_cost)})"
                        )
                    else:
                        st.markdown(f"- **Add {amenity_name}**: {format_currency(amenity_cost)}")
            else:
                st.success("This property already has all the key amenities for this market!")

            st.divider()

            imp_col1, imp_col2, imp_col3 = st.columns(3)
            with imp_col1:
                st.metric("Furnishing", format_currency(imp.furnishing_cost))
                st.caption(f"{bedrooms} bedrooms + common areas + {sqft} sqft")
            with imp_col2:
                st.metric("Amenity Additions", format_currency(imp.amenity_cost))
                st.caption(f"{len(imp.amenity_details)} items to add")
            with imp_col3:
                st.metric("Cosmetic Rehab", format_currency(imp.cosmetic_rehab))
                st.caption(f"Built {year_built} ({2026 - year_built} years old)")

            st.markdown(f"### Total Improvement Budget: {format_currency(imp.total)}")

            if existing_amenities:
                st.info(f"Skipped (already has): {', '.join(existing_amenities)}")

        with tab_chart:
            # Cash flow waterfall
            fig = go.Figure(go.Waterfall(
                orientation="v",
                measure=["absolute", "relative", "relative", "relative", "relative", "total"],
                x=["Revenue", "Mortgage + Tax", "Operations", "Management", "Other", "Net Cash Flow"],
                y=[
                    annual_revenue,
                    -(exp.mortgage_annual + exp.property_tax + exp.insurance + exp.hoa_annual),
                    -(exp.utilities + exp.maintenance + exp.cleaning + exp.supplies),
                    -(exp.property_management + exp.platform_fees),
                    -(exp.str_permit + exp.accounting + exp.furniture_reserve + exp.landscaping),
                    0,
                ],
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                increasing={"marker": {"color": "#2ecc71"}},
                decreasing={"marker": {"color": "#e74c3c"}},
                totals={"marker": {"color": "#3498db"}},
            ))
            fig.update_layout(
                title="Annual Cash Flow Waterfall",
                height=450,
                yaxis_title="$",
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

            # Investment breakdown bar
            fig2 = go.Figure(data=[
                go.Bar(
                    x=["Down Payment", "Closing Costs", "Furnishing", "Amenities", "Cosmetic Rehab"],
                    y=[
                        price * down_pct,
                        price * analysis_config["financial_assumptions"]["closing_cost_pct"],
                        imp.furnishing_cost,
                        imp.amenity_cost,
                        imp.cosmetic_rehab,
                    ],
                    marker_color=["#3498db", "#3498db", "#2ecc71", "#e67e22", "#e74c3c"],
                )
            ])
            fig2.update_layout(
                title="Cash Investment Breakdown",
                height=350,
                yaxis_title="$",
            )
            st.plotly_chart(fig2, use_container_width=True)


# ============================================================
# PAGE: Market Overview
# ============================================================
elif page == "Market Overview":
    st.title("Market Overview")
    st.markdown("Compare all configured markets at a glance.")

    # Build comparison data for a reference property
    ref_beds = st.slider("Reference Bedrooms", 1, 6, 3)
    ref_price = st.slider("Reference Price ($)", 200000, 900000, 450000, step=50000)

    markets_data = []
    for market_cfg in config["markets"]:
        market_name = market_cfg["name"]
        market_data = MARKET_DEFAULTS.get(market_name, {})
        beds = min(ref_beds, 6)

        if beds in market_data:
            rate, occ = market_data[beds]
        else:
            rate, occ = 200, 0.55

        annual_rev = rate * occ * 365

        # Quick improvement estimate
        city_parts = market_name.split(", ")
        prop = Property(
            zpid="compare", address="", city=city_parts[0],
            state=city_parts[1] if len(city_parts) > 1 else "",
            zipcode="00000", price=ref_price, bedrooms=ref_beds,
            bathrooms=2.0, sqft=1800, year_built=2010, market=market_name,
        )
        rev = RevenueEstimate(annual_revenue=annual_rev, nightly_rate=rate, occupancy_rate=occ)
        permit = permit_checker.check(prop)
        imp_est = improvement_estimator.estimate(prop, existing_amenities=[])
        deal = analyze_deal(prop, rev, permit, config, imp_est)

        market_amenities = MARKET_COMP_AMENITIES.get(market_name, [])
        top_amenities = [a.name for a in market_amenities[:3]]

        markets_data.append({
            "Market": market_name,
            "Nightly Rate": f"${rate}",
            "Occupancy": f"{occ:.0%}",
            "Annual Revenue": format_currency(annual_rev),
            "Improvement Cost": format_currency(imp_est.total),
            "Cash Invested": format_currency(deal.cash_invested),
            "Cash Flow": format_currency(deal.annual_cash_flow),
            "CoC Return": format_pct(deal.cash_on_cash_return),
            "Permit": permit.status.value,
            "Top Amenities": ", ".join(top_amenities),
            "_coc": deal.cash_on_cash_return,
        })

    # Sort by CoC
    markets_data.sort(key=lambda x: x["_coc"], reverse=True)

    # Display as table
    display_data = [{k: v for k, v in m.items() if not k.startswith("_")} for m in markets_data]
    st.dataframe(display_data, use_container_width=True, hide_index=True)

    # Bar chart comparison
    fig = go.Figure()
    names = [m["Market"] for m in markets_data]
    cocs = [m["_coc"] * 100 for m in markets_data]
    colors = ["#2ecc71" if c >= 10 else "#e67e22" if c >= 7 else "#e74c3c" for c in cocs]

    fig.add_trace(go.Bar(x=names, y=cocs, marker_color=colors))
    fig.add_hline(y=10, line_dash="dash", line_color="green", annotation_text="10% Target")
    fig.update_layout(
        title=f"Cash-on-Cash Return by Market ({ref_beds}BR at {format_currency(ref_price)})",
        yaxis_title="CoC Return (%)",
        xaxis_tickangle=-45,
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Improvement cost comparison
    fig2 = go.Figure()
    imp_costs = []
    for market_cfg in config["markets"]:
        mn = market_cfg["name"]
        match = next((m for m in markets_data if m["Market"] == mn), None)
        if match:
            imp_costs.append(match)

    fig2.add_trace(go.Bar(
        x=[m["Market"] for m in markets_data],
        y=[
            float(m["Improvement Cost"].replace("$", "").replace(",", ""))
            for m in markets_data
        ],
        marker_color="#e67e22",
    ))
    fig2.update_layout(
        title="Total Improvement Cost by Market (worst case — no existing amenities)",
        yaxis_title="$",
        xaxis_tickangle=-45,
        height=400,
    )
    st.plotly_chart(fig2, use_container_width=True)


# ============================================================
# PAGE: Settings
# ============================================================
elif page == "Settings":
    st.title("Settings")
    st.markdown("Current configuration from `config/settings.yaml`")

    st.subheader("Financial Assumptions")
    fa = config["financial_assumptions"]
    settings_data = {
        "Down Payment": f"{fa['down_payment_pct']:.0%}",
        "Loan Term": f"{fa['loan_term_years']} years",
        "Interest Rate": f"{fa['interest_rate']:.2%}",
        "Closing Costs": f"{fa['closing_cost_pct']:.0%}",
    }
    for k, v in settings_data.items():
        st.markdown(f"- **{k}**: {v}")

    st.subheader("Expense Assumptions")
    exp_cfg = config["expenses"]
    for k, v in exp_cfg.items():
        st.markdown(f"- **{k}**: {v}")

    st.subheader("Improvement Settings")
    imp_cfg = config.get("improvements", {})
    if imp_cfg:
        for k, v in imp_cfg.items():
            st.markdown(f"- **{k}**: {v}")
    else:
        st.info("Using default improvement settings")

    st.subheader("Configured Markets")
    for m in config["markets"]:
        amenities = MARKET_COMP_AMENITIES.get(m["name"], [])
        amenity_str = ", ".join(f"{a.name} ({format_currency(a.install_cost)})" for a in amenities)
        with st.expander(m["name"]):
            st.markdown(f"**Location**: {m['location']}")
            if amenities:
                st.markdown(f"**Top comp amenities**: {amenity_str}")
            # Revenue defaults
            mdata = MARKET_DEFAULTS.get(m["name"], {})
            if mdata:
                st.markdown("**Revenue defaults (nightly rate / occupancy):**")
                for beds, (rate, occ) in sorted(mdata.items()):
                    st.markdown(f"- {beds}BR: ${rate}/night, {occ:.0%} occupancy")

    st.subheader("Thresholds")
    st.markdown(f"- **Min Cash-on-Cash**: {config['thresholds']['min_cash_on_cash']:.0%}")
    st.markdown(f"- **Min Occupancy**: {config['thresholds']['min_occupancy']:.0%}")

    st.divider()
    st.subheader("API Keys")
    api = config.get("api_keys", {})
    zillow_set = api.get("zillow_rapidapi", "") not in ("", "YOUR_RAPIDAPI_KEY")
    airdna_set = bool(api.get("airdna_rapidapi", ""))
    mashvisor_set = bool(api.get("mashvisor", ""))

    st.markdown(f"- **Zillow RapidAPI**: {'Configured' if zillow_set else 'Not set'}")
    st.markdown(f"- **AirDNA RapidAPI**: {'Configured' if airdna_set else 'Not set'}")
    st.markdown(f"- **Mashvisor**: {'Configured' if mashvisor_set else 'Not set (using heuristic fallback)'}")
