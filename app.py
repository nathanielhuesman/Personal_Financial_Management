# ============================================================
# PERSONAL FINANCE APP — Built with Streamlit
# ============================================================
# Streamlit is a Python library that turns Python scripts
# into beautiful web apps — no HTML or JavaScript needed!
#
# Every time the user moves a slider or types a number,
# Streamlit re-runs the whole script from top to bottom.
# This is how the app stays "live" and reactive.
# ============================================================

# --- IMPORTS ---
# streamlit  → the web app framework (pip install streamlit)
# math       → built-in Python library for math functions
import streamlit as st
import math


# ============================================================
# PAGE CONFIGURATION
# st.set_page_config() must be the VERY FIRST Streamlit command.
# It sets the browser tab title, icon, and layout width.
# layout="wide" uses the full screen width — good for finance apps
# ============================================================
st.set_page_config(
    page_title="Personal Finance App",
    page_icon="💰",
    layout="wide"
)


# ============================================================
# CUSTOM CSS STYLING
# st.markdown() lets us inject raw HTML or CSS into the page.
# unsafe_allow_html=True is required to render actual HTML.
# We use this to make the app look polished and professional.
# ============================================================
st.markdown("""
<style>
    /* Import a clean, professional font from Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap');

    /* Apply font to the whole app */
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    /* Style the big metric number cards */
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-label {
        font-size: 13px;
        color: #64748b;
        margin-bottom: 4px;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 600;
        color: #0f172a;
        font-family: 'DM Mono', monospace;
    }
    .metric-value.highlight {
        color: #2563eb;
    }
    .metric-value.green {
        color: #16a34a;
    }

    /* Style the tip/advice boxes */
    .tip-box {
        background: #eff6ff;
        border-left: 4px solid #2563eb;
        border-radius: 0 8px 8px 0;
        padding: 1rem 1.25rem;
        margin-top: 1rem;
        font-size: 15px;
        color: #1e3a5f;
        line-height: 1.7;
    }

    /* Style allocation rows */
    .alloc-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px solid #f1f5f9;
        font-size: 15px;
    }
    .alloc-label { color: #374151; }
    .alloc-value { font-weight: 600; color: #0f172a; font-family: 'DM Mono', monospace; }

    /* Make Streamlit's default metric look nicer */
    [data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem 1.25rem;
    }

    /* Section header style */
    .section-intro {
        font-size: 16px;
        color: #475569;
        margin-bottom: 1.5rem;
        line-height: 1.7;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPER FUNCTION: format_currency
# Turns a plain number into a currency string.
# f"${value:,.2f}" means: dollar sign + commas + 2 decimal places
# Example: format_currency(2500) → "$2,500.00"
# ============================================================
def format_currency(value):
    return f"${value:,.2f}"


# ============================================================
# APP TITLE & NAVIGATION
# st.title() shows a big heading
# st.tabs() creates clickable tab panels — one per module
# ============================================================
st.title("💰 Personal Finance App")
st.markdown("*Learn the money rules that financial advisors teach their clients.*")

# Create three tabs — one for each module
# These return "tab objects" we assign to variables
tab1, tab2, tab3 = st.tabs([
    "🏦  Emergency Fund",
    "📊  Savings Allocation",
    "📈  TVM Calculator"
])


# ============================================================
# TAB 1: EMERGENCY FUND CALCULATOR
#
# CONCEPT: Before you invest a single dollar, build a cash
# safety net worth 3–6 months of your living expenses.
# Keep it in a high-yield savings account — not invested.
#
# HOW STREAMLIT WORKS HERE:
# st.number_input() creates a number input box.
# st.slider() creates a draggable slider.
# Every time the user changes a value, Streamlit re-runs
# this entire tab and recalculates instantly.
# ============================================================
with tab1:

    st.header("Emergency Fund Calculator")
    st.markdown("""
    <p class="section-intro">
    Financial experts agree: before you invest anything, you need a cash safety net.
    This is money stored in a savings account — NOT invested — that you can access
    instantly if you lose your job, have a medical bill, or face any emergency.
    <br><br>
    <strong>The standard rule: save 3 to 6 months of your living expenses.</strong>
    </p>
    """, unsafe_allow_html=True)

    # --- INPUT SECTION ---
    st.subheader("Your monthly expenses")

    # st.columns(n) splits the page into n side-by-side columns
    # This lets us put two inputs on the same row
    col1, col2 = st.columns(2)

    with col1:
        # st.number_input() creates a number field
        # label = text shown above the field
        # min_value = lowest allowed value
        # value = the default starting value
        # step = how much it changes per click of the +/- arrows
        housing = st.number_input("🏠 Housing (rent/mortgage)", min_value=0.0, value=1200.0, step=50.0)
        transport = st.number_input("🚗 Transportation", min_value=0.0, value=300.0, step=25.0)
        insurance = st.number_input("🛡️ Insurance", min_value=0.0, value=150.0, step=25.0)

    with col2:
        food = st.number_input("🛒 Food & groceries", min_value=0.0, value=400.0, step=25.0)
        utilities = st.number_input("💡 Utilities & bills", min_value=0.0, value=200.0, step=25.0)
        other = st.number_input("📦 Other monthly costs", min_value=0.0, value=250.0, step=25.0)

    # --- MONTHS SLIDER ---
    # st.slider() creates a draggable bar
    # min_value, max_value = the range
    # value = starting position
    # format = how to display the number ("%d" means whole number, no decimals)
    st.subheader("How many months to save?")
    months = st.slider(
        "Choose between 3 months (minimum) and 6 months (fully secure)",
        min_value=3,
        max_value=6,
        value=3,
        format="%d months"
    )

    # --- CALCULATIONS ---
    # Add up all the expenses the user entered
    total_monthly = housing + food + transport + utilities + insurance + other

    # Multiply monthly total by number of months = the goal
    emergency_goal = total_monthly * months

    # To reach the goal in 1 year, divide by 12
    # round() removes ugly decimals like 208.3333...
    save_per_month = round(emergency_goal / 12)

    # --- DISPLAY RESULTS ---
    st.subheader("Your results")

    # Three columns for three metric cards
    m1, m2, m3 = st.columns(3)

    # st.metric() is a built-in Streamlit card that shows a big number with a label
    with m1:
        st.metric("Monthly expenses", format_currency(total_monthly))
    with m2:
        st.metric("Your fund goal", format_currency(emergency_goal), f"{months} months of expenses")
    with m3:
        st.metric("Save per month", format_currency(save_per_month), "to reach goal in 12 months")

    # --- PROGRESS BAR (if user has entered current savings) ---
    st.subheader("How close are you?")

    # Ask how much they already have saved
    current_savings = st.number_input(
        "How much do you currently have saved? (enter 0 if starting from scratch)",
        min_value=0.0,
        value=0.0,
        step=100.0
    )

    # Calculate progress as a fraction between 0.0 and 1.0
    # min() makes sure it never goes above 1.0 (100%) even if they overshoot
    if emergency_goal > 0:
        progress = min(current_savings / emergency_goal, 1.0)

        # st.progress() draws a progress bar (accepts a value from 0.0 to 1.0)
        st.progress(progress)

        # Show the percentage as text
        # int(progress * 100) converts 0.73 → 73
        st.caption(f"You're {int(progress * 100)}% of the way there — {format_currency(current_savings)} saved of {format_currency(emergency_goal)} goal")

    # --- ADVICE BOX ---
    # f-strings let us embed variables directly inside a string using {curly braces}
    st.markdown(f"""
    <div class="tip-box">
        <strong>What this means for you:</strong><br><br>
        Your total monthly expenses are <strong>{format_currency(total_monthly)}</strong>.
        To have {months} months of security, your goal is <strong>{format_currency(emergency_goal)}</strong>.<br><br>
        If you save <strong>{format_currency(save_per_month)}/month</strong>, you'll reach this goal in 12 months.<br><br>
        Keep this money in a <strong>high-yield savings account</strong> — never invest it.
        It must be instantly accessible. Don't touch it unless it's a real emergency.
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# TAB 2: SAVINGS & INVESTMENT ALLOCATION
#
# CONCEPT: The 50/30/20 Rule
# Split your take-home pay into three buckets:
#   50% → Needs  (things you must pay: rent, food, bills)
#   30% → Wants  (things you enjoy: dining, hobbies)
#   20% → Saving (emergency fund + investing + debt payoff)
#
# Within that 20%, we split further:
#   40% of savings → long-term investing/retirement
#   30% of savings → emergency fund (until it's fully funded)
#   20% of savings → short-term goals (vacation, car, etc.)
#   10% of savings → extra debt payments
# ============================================================
with tab2:

    st.header("Savings & Investment Allocation")
    st.markdown("""
    <p class="section-intro">
    The <strong>50/30/20 Rule</strong> is the most widely used personal budgeting framework in the world,
    popularized by Senator Elizabeth Warren. It gives every dollar a job — so your money
    works intentionally instead of disappearing.
    </p>
    """, unsafe_allow_html=True)

    # --- INCOME INPUT ---
    st.subheader("Your monthly take-home income")
    st.caption("Enter your income AFTER taxes — the amount that actually hits your bank account")

    income = st.number_input(
        "Monthly take-home pay",
        min_value=0.0,
        value=5000.0,
        step=100.0,
        label_visibility="collapsed"   # Hides the label (we used st.subheader above instead)
    )

    # --- CALCULATE THE THREE BUCKETS ---
    # Multiplying by 0.50 = 50%, by 0.30 = 30%, by 0.20 = 20%
    needs   = income * 0.50
    wants   = income * 0.30
    savings = income * 0.20

    # --- DISPLAY THE BIG THREE ---
    st.subheader("Your 50/30/20 split")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🏠 Needs (50%)", format_currency(needs), "rent, food, bills, insurance")
    with c2:
        st.metric("🎉 Wants (30%)", format_currency(wants), "dining, fun, subscriptions")
    with c3:
        st.metric("💰 Savings (20%)", format_currency(savings), "investing + emergency + debt")

    # --- VISUAL BAR using st.progress for each bucket ---
    st.subheader("Visual allocation")
    st.caption("Needs — 50%")
    st.progress(0.50)
    st.caption("Wants — 30%")
    st.progress(0.30)
    st.caption("Savings — 20%")
    st.progress(0.20)

    # --- BREAK DOWN THE 20% SAVINGS ---
    st.subheader("Inside your savings bucket")
    st.markdown(f"""
    <div>
        <div class="alloc-row">
            <span class="alloc-label">📈 Long-term investing / retirement (40%)</span>
            <span class="alloc-value">{format_currency(savings * 0.40)}</span>
        </div>
        <div class="alloc-row">
            <span class="alloc-label">🏦 Emergency fund (30%)</span>
            <span class="alloc-value">{format_currency(savings * 0.30)}</span>
        </div>
        <div class="alloc-row">
            <span class="alloc-label">✈️ Short-term savings — vacation, car, etc. (20%)</span>
            <span class="alloc-value">{format_currency(savings * 0.20)}</span>
        </div>
        <div class="alloc-row" style="border-bottom:none;">
            <span class="alloc-label">💳 Extra debt payoff (10%)</span>
            <span class="alloc-value">{format_currency(savings * 0.10)}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- VERIFY THE MATH ---
    # Always good practice to show students the verification step
    total_check = needs + wants + savings

    # --- PRO TIP ---
    st.markdown(f"""
    <div class="tip-box">
        <strong>Pro tip:</strong><br><br>
        Right now you're directing <strong>{format_currency(savings * 0.30)}/month</strong> to your emergency fund.
        Once your emergency fund is fully funded, redirect that money to investing.
        That would give you <strong>{format_currency(savings * 0.70)}/month</strong> going into your investments —
        a massive wealth-building acceleration.<br><br>
        Total check: {format_currency(needs)} + {format_currency(wants)} + {format_currency(savings)}
        = <strong>{format_currency(total_check)}</strong> ✓
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# TAB 3: TIME VALUE OF MONEY (TVM) CALCULATOR
#
# CONCEPT: The most powerful idea in all of finance.
# Money invested TODAY grows over time through compound interest.
# Compound interest = your money earns interest,
# then THAT interest also earns interest, and so on.
# The longer you wait, the more explosive the growth.
#
# THE FORMULA: Future Value of an Annuity
# FV = PMT × [ ((1 + r)^n - 1) / r ]
#
# WHY 9-11%?
# The S&P 500 index has returned ~10% average annually
# over the past 100 years. It's the benchmark for investing.
# ============================================================
with tab3:

    st.header("Time Value of Money Calculator")
    st.markdown("""
    <p class="section-intro">
    If you invest the same amount every single month, how much will you have in the future?
    This calculator uses the industry-standard <strong>Future Value of an Annuity</strong> formula,
    compounded monthly at a 9–11% annual return (the S&P 500 historical average).
    </p>
    """, unsafe_allow_html=True)

    # --- INPUTS VIA SLIDERS ---
    st.subheader("Set your investment parameters")

    # Monthly investment slider
    # The user drags this to choose how much they invest each month
    monthly_investment = st.slider(
        "💵 Monthly investment amount",
        min_value=50,
        max_value=2000,
        value=300,
        step=50,
        format="$%d"    # Shows value as "$300" on the slider
    )

    # Years slider
    years = st.slider(
        "📅 Number of years to invest",
        min_value=1,
        max_value=40,
        value=20,
        step=1,
        format="%d years"
    )

    # Annual return rate slider (9% to 11%)
    annual_rate = st.slider(
        "📊 Expected annual return rate",
        min_value=9.0,
        max_value=11.0,
        value=10.0,
        step=0.5,
        format="%.1f%%"    # Shows as "10.0%"
    )

    # --- CONVERT FOR THE FORMULA ---
    # The formula needs MONTHLY rate, not annual
    # 10% annual → divide by 100 (to get 0.10) → divide by 12 (monthly)
    monthly_rate = (annual_rate / 100) / 12

    # The formula needs total MONTHS, not years
    total_months = years * 12

    # --- THE FUTURE VALUE FORMULA ---
    # This is the core calculation — the same formula used by
    # every financial calculator and Excel's FV() function
    #
    # math.pow(base, exponent) = base raised to the power of exponent
    # Example: math.pow(2, 3) = 2³ = 8
    #
    # (1 + monthly_rate)^total_months = compound growth factor
    # Subtracting 1 and dividing by rate = adjusts for regular payments
    # Multiplying by PMT = scales to the actual payment amount

    compound_growth = math.pow(1 + monthly_rate, total_months)
    future_value = monthly_investment * ((compound_growth - 1) / monthly_rate)

    # Total money the person actually put in themselves
    total_invested = monthly_investment * total_months

    # Free money from compound interest (the magic number!)
    interest_earned = future_value - total_invested

    # How many times did the money multiply?
    money_multiplier = future_value / total_invested

    # --- DISPLAY MAIN RESULTS ---
    st.subheader("Your results")

    r1, r2 = st.columns(2)
    r3, r4 = st.columns(2)

    with r1:
        st.metric(
            "💼 Total you invested",
            format_currency(total_invested),
            f"{monthly_investment * 12:,.0f}/year × {years} years"
        )
    with r2:
        st.metric(
            "🚀 Future value",
            format_currency(future_value),
            f"at {annual_rate}% compounded monthly"
        )
    with r3:
        st.metric(
            "✨ Free money (compound interest)",
            format_currency(interest_earned),
            "the market gave you this"
        )
    with r4:
        st.metric(
            "✖️ Money multiplier",
            f"{money_multiplier:.1f}x",
            "your money multiplied this many times"
        )

    # --- GROWTH MILESTONE TABLE ---
    st.subheader("Growth milestones — watch compound interest accelerate")

    # We'll build a list of dictionaries (rows of data) for different years
    # Then show it as a table using st.dataframe()
    milestone_data = []

    # Loop through checkpoint years: 5, 10, 15, 20... up to the chosen year
    # range(start, stop, step) generates numbers: 5, 10, 15, 20...
    milestone_years = list(range(5, years + 1, 5))

    # Make sure the final year is always included
    if years not in milestone_years:
        milestone_years.append(years)

    for y in milestone_years:
        n = y * 12                                                          # months at this checkpoint
        growth = math.pow(1 + monthly_rate, n)                             # compound growth factor
        fv_at_year = monthly_investment * ((growth - 1) / monthly_rate)    # future value at this year
        invested_at_year = monthly_investment * n                           # total invested so far
        gain = fv_at_year - invested_at_year                               # free money so far
        gain_pct = (gain / fv_at_year) * 100 if fv_at_year > 0 else 0     # what % is pure gain

        # Append a dictionary (row) to our list
        # Each key becomes a column header in the table
        milestone_data.append({
            "Year": y,
            "You Invested": format_currency(invested_at_year),
            "Total Value": format_currency(fv_at_year),
            "Free Earnings": format_currency(gain),
            "% From Growth": f"{gain_pct:.0f}%"
        })

    # st.table() displays a static table from a list of dictionaries
    st.table(milestone_data)

    # --- VISUAL CHART ---
    # Build data for a line chart showing growth over every year
    chart_data = {}
    chart_years = list(range(1, years + 1))

    # Two lines: one for what you invested, one for total value
    invested_line = []
    value_line = []

    for y in chart_years:
        n = y * 12
        growth = math.pow(1 + monthly_rate, n)
        fv = monthly_investment * ((growth - 1) / monthly_rate)
        invested_line.append(round(monthly_investment * n))    # round() keeps numbers clean
        value_line.append(round(fv))

    # st.line_chart() takes a dictionary where keys = line labels, values = lists of numbers
    st.subheader("Investment growth chart")
    st.line_chart({
        "What you invested": invested_line,
        "Total value with growth": value_line
    })
    st.caption("The gap between the two lines = your compound interest earnings")

    # --- THE BIG INSIGHT ---
    st.markdown(f"""
    <div class="tip-box">
        <strong>The lesson that changes everything:</strong><br><br>
        You personally put in <strong>{format_currency(total_invested)}</strong> over {years} years.<br>
        The market handed you an extra <strong>{format_currency(interest_earned)}</strong> for free.<br>
        You ended up with <strong>{format_currency(future_value)}</strong> — that's <strong>{money_multiplier:.1f}x</strong> your money.<br><br>
        The secret? <strong>Compound interest.</strong> Your money earns interest.
        Then that interest earns interest. Then THAT earns interest.
        The longer you leave it alone, the faster it snowballs.<br><br>
        Start early. Stay consistent. Never stop.
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# FOOTER
# st.divider() draws a horizontal line
# st.caption() shows small gray text
# ============================================================
st.divider()
st.caption("Built with Python & Streamlit · Based on industry-standard personal finance principles · For educational purposes")

