import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─────────────────────────────────────────────
# CONFIG — fill these in
# ─────────────────────────────────────────────
SENDER_EMAIL    = "your_email@gmail.com"       # Gmail address you send FROM
SENDER_PASSWORD = "your_app_password_here"     # Gmail App Password
SUBSCRIBERS_FILE = "subscribers.csv"
ALERTS_LOG_FILE  = "alerts_log.csv"

# SMS via Email-to-SMS gateways (free, no Twilio needed)
SMS_GATEWAYS = {
    "AT&T":       "txt.att.net",
    "T-Mobile":   "tmomail.net",
    "Verizon":    "vtext.com",
    "Sprint":     "messaging.sprintpcs.com",
    "US Cellular":"email.uscc.net",
    "Boost":      "sms.myboostmobile.com",
    "Cricket":    "sms.cricketwireless.net",
    "Metro PCS":  "mymetropcs.com",
}

# ─────────────────────────────────────────────
# STORAGE HELPERS
# ─────────────────────────────────────────────
def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        return pd.read_csv(SUBSCRIBERS_FILE)
    return pd.DataFrame(columns=["email","phone","carrier","ticker","subscribed_at"])

def save_subscriber(email, ticker, phone="", carrier=""):
    df = load_subscribers()
    email  = email.strip().lower()
    ticker = ticker.strip().upper()
    exists = ((df["email"] == email) & (df["ticker"] == ticker)).any()
    if not exists:
        new_row = pd.DataFrame([{
            "email":  email,
            "phone":  phone.strip(),
            "carrier": carrier,
            "ticker": ticker,
            "subscribed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(SUBSCRIBERS_FILE, index=False)
        return True
    return False

def load_alerts_log():
    if os.path.exists(ALERTS_LOG_FILE):
        return pd.read_csv(ALERTS_LOG_FILE)
    return pd.DataFrame(columns=["ticker","cross_type","cross_date","emailed_at","emails_sent_to"])

def log_alert(ticker, cross_type, cross_date, emails):
    df = load_alerts_log()
    new_row = pd.DataFrame([{
        "ticker":         ticker,
        "cross_type":     cross_type,
        "cross_date":     str(cross_date),
        "emailed_at":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "emails_sent_to": ", ".join(emails)
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(ALERTS_LOG_FILE, index=False)

# ─────────────────────────────────────────────
# INDICATOR CALCULATIONS
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_data(ticker, period="2y"):
    raw = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    df  = raw[["Close","High","Low"]].copy()
    df.columns = ["Close","High","Low"]

    # SMA Golden/Death Cross + MA Ribbon
    for w in [10, 20, 30, 50, 100, 200]:
        df[f"SMA{w}"] = df["Close"].rolling(w).mean()

    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"]        = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"]   = df["MACD"] - df["MACD_Signal"]

    # RSI (14)
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # ADX (14)
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    dm_pos = np.where((high - high.shift()) > (low.shift() - low),
                      np.maximum(high - high.shift(), 0), 0)
    dm_neg = np.where((low.shift() - low) > (high - high.shift()),
                      np.maximum(low.shift() - low, 0), 0)
    atr14  = pd.Series(tr).rolling(14).mean()
    di_pos = 100 * pd.Series(dm_pos).rolling(14).mean() / atr14
    di_neg = 100 * pd.Series(dm_neg).rolling(14).mean() / atr14
    dx     = (100 * (di_pos - di_neg).abs() / (di_pos + di_neg)).fillna(0)
    df["ADX"]    = dx.rolling(14).mean().values
    df["DI_pos"] = di_pos.values
    df["DI_neg"] = di_neg.values

    df.dropna(subset=["SMA50","SMA200","MACD","RSI","ADX"], inplace=True)
    return df

# ─────────────────────────────────────────────
# SIGNAL DETECTION
# ─────────────────────────────────────────────
def detect_sma_crosses(df):
    crosses, prev = [], df["SMA50"].iloc[0] > df["SMA200"].iloc[0]
    for i in range(1, len(df)):
        curr = df["SMA50"].iloc[i] > df["SMA200"].iloc[i]
        if not prev and curr:
            crosses.append((df.index[i], "Golden Cross"))
        elif prev and not curr:
            crosses.append((df.index[i], "Death Cross"))
        prev = curr
    return crosses

def detect_macd_crosses(df):
    crosses, prev = [], df["MACD"].iloc[0] > df["MACD_Signal"].iloc[0]
    for i in range(1, len(df)):
        curr = df["MACD"].iloc[i] > df["MACD_Signal"].iloc[i]
        if not prev and curr:
            crosses.append((df.index[i], "MACD Bullish"))
        elif prev and not curr:
            crosses.append((df.index[i], "MACD Bearish"))
        prev = curr
    return crosses

def get_ribbon_signal(df):
    mas = [df[f"SMA{w}"].iloc[-1] for w in [10, 20, 30, 50, 100, 200]]
    if all(mas[i] > mas[i+1] for i in range(len(mas)-1)):
        return "Bullish", "#00c851"
    elif all(mas[i] < mas[i+1] for i in range(len(mas)-1)):
        return "Bearish", "#d0021b"
    return "Mixed", "#888888"

def get_rsi_signal(df):
    rsi = df["RSI"].iloc[-1]
    if rsi > 70:   return f"{rsi:.1f} Overbought", "#d0021b"
    elif rsi < 30: return f"{rsi:.1f} Oversold",   "#00c851"
    return f"{rsi:.1f} Neutral", "#888888"

def get_adx_signal(df):
    adx = df["ADX"].iloc[-1]
    if adx >= 25:   return f"{adx:.1f} Strong Trend", "#f5a623"
    elif adx >= 15: return f"{adx:.1f} Developing",   "#888888"
    return f"{adx:.1f} Weak/No Trend", "#aaaaaa"

# ─────────────────────────────────────────────
# EMAIL + SMS
# ─────────────────────────────────────────────
def send_email(to_email, ticker, cross_type, cross_date, close_price,
               rsi_val=None, adx_val=None, macd_val=None):
    is_golden = "Golden" in cross_type or "Bullish" in cross_type
    color  = "#f5a623" if is_golden else "#d0021b"
    signal = "BUY signal" if is_golden else "SELL/caution signal"
    emoji  = "🟡" if is_golden else "💀"

    extra_rows = ""
    if rsi_val  is not None:
        extra_rows += f"<tr style='background:#f9f9f9;'><td style='padding:12px;border:1px solid #eee;color:#666;'>RSI (14)</td><td style='padding:12px;border:1px solid #eee;font-weight:bold;'>{rsi_val:.1f}</td></tr>"
    if adx_val  is not None:
        extra_rows += f"<tr><td style='padding:12px;border:1px solid #eee;color:#666;'>ADX (14)</td><td style='padding:12px;border:1px solid #eee;font-weight:bold;'>{adx_val:.1f}</td></tr>"
    if macd_val is not None:
        extra_rows += f"<tr style='background:#f9f9f9;'><td style='padding:12px;border:1px solid #eee;color:#666;'>MACD Histogram</td><td style='padding:12px;border:1px solid #eee;font-weight:bold;'>{macd_val:.4f}</td></tr>"

    subject   = f"{emoji} {cross_type} detected for {ticker}!"
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
      <div style="max-width:560px;margin:auto;background:white;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
        <div style="background:{color};padding:24px;text-align:center;">
          <h1 style="color:white;margin:0;font-size:28px;">{emoji} {cross_type}</h1>
          <p style="color:white;margin:8px 0 0;opacity:0.9;">Stock Alert Notification</p>
        </div>
        <div style="padding:32px;">
          <p style="font-size:16px;color:#333;">A <strong>{cross_type}</strong> was detected for <strong>{ticker}</strong>.</p>
          <table style="width:100%;border-collapse:collapse;margin:20px 0;">
            <tr style="background:#f9f9f9;"><td style="padding:12px;border:1px solid #eee;color:#666;">Ticker</td><td style="padding:12px;border:1px solid #eee;font-weight:bold;">{ticker}</td></tr>
            <tr><td style="padding:12px;border:1px solid #eee;color:#666;">Cross Date</td><td style="padding:12px;border:1px solid #eee;font-weight:bold;">{cross_date}</td></tr>
            <tr style="background:#f9f9f9;"><td style="padding:12px;border:1px solid #eee;color:#666;">Close Price</td><td style="padding:12px;border:1px solid #eee;font-weight:bold;">${close_price:.2f}</td></tr>
            <tr><td style="padding:12px;border:1px solid #eee;color:#666;">Signal</td><td style="padding:12px;border:1px solid #eee;font-weight:bold;color:{color};">{signal}</td></tr>
            {extra_rows}
          </table>
          <p style="font-size:13px;color:#999;">Automated alert. Past signals do not guarantee future performance.</p>
        </div>
      </div>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Email error: {e}")
        return False

def send_sms(phone, carrier, ticker, cross_type, cross_date, close_price):
    """Free SMS via email-to-SMS carrier gateway."""
    gateway = SMS_GATEWAYS.get(carrier)
    if not gateway or not phone:
        return False
    sms_address = f"{phone.strip()}@{gateway}"
    is_golden   = "Golden" in cross_type or "Bullish" in cross_type
    body = (f"{'GOLDEN' if is_golden else 'DEATH'} CROSS: {ticker}\n"
            f"Date: {cross_date}\nPrice: ${close_price:.2f}\n"
            f"{'BUY signal' if is_golden else 'SELL/caution'}")
    msg = MIMEText(body)
    msg["Subject"] = ""
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = sms_address
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, sms_address, msg.as_string())
        return True
    except Exception as e:
        st.error(f"SMS error: {e}")
        return False

def check_and_alert(ticker, df):
    crosses = detect_sma_crosses(df)
    if not crosses:
        st.info("No crosses detected.")
        return
    cross_date, cross_type = crosses[-1]
    if pd.Timestamp(cross_date) < pd.Timestamp(datetime.now() - timedelta(days=3)):
        st.info("No recent crosses within the last 3 days.")
        return
    close_price = float(df.loc[cross_date, "Close"])
    rsi_val  = float(df["RSI"].loc[cross_date])
    adx_val  = float(df["ADX"].loc[cross_date])
    macd_val = float(df["MACD_Hist"].loc[cross_date])

    subscribers = load_subscribers()
    ticker_subs = subscribers[subscribers["ticker"] == ticker]
    if ticker_subs.empty:
        st.info("No subscribers for this ticker yet.")
        return
    log = load_alerts_log()
    already_sent = ((log["ticker"] == ticker) & (log["cross_date"] == str(cross_date))).any()
    if already_sent:
        st.info("Alerts already sent for this cross event.")
        return

    sent_to = []
    for _, row in ticker_subs.iterrows():
        ok = send_email(row["email"], ticker, cross_type, cross_date.date(),
                        close_price, rsi_val, adx_val, macd_val)
        if ok:
            sent_to.append(row["email"])
        phone   = str(row.get("phone","")).strip()
        carrier = str(row.get("carrier","")).strip()
        if phone and carrier and carrier in SMS_GATEWAYS:
            send_sms(phone, carrier, ticker, cross_type, cross_date.date(), close_price)

    if sent_to:
        log_alert(ticker, cross_type, cross_date, sent_to)
        st.success(f"Alerts sent to {len(sent_to)} subscriber(s)!")

# ─────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────
def build_main_chart(df, ticker, crosses):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Close",
                             line=dict(color="#4a90d9", width=1.5), opacity=0.9))
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"],  name="SMA 50",
                             line=dict(color="#f5a623", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], name="SMA 200",
                             line=dict(color="#d0021b",  width=2, dash="dash")))
    for date, ctype in crosses:
        is_golden = "Golden" in ctype
        fig.add_vline(x=date, line_width=1.5, line_dash="dash",
                      line_color="#f5a623" if is_golden else "#d0021b")
        fig.add_annotation(x=date, y=float(df.loc[date, "Close"]),
                           text="GC" if is_golden else "DC",
                           showarrow=True, arrowhead=2,
                           bgcolor="#f5a623" if is_golden else "#d0021b",
                           font=dict(color="white", size=11),
                           arrowcolor="#f5a623" if is_golden else "#d0021b")
    fig.update_layout(title=f"{ticker} — Golden & Death Cross (SMA 50/200)",
                      xaxis_title="Date", yaxis_title="Price (USD)",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      hovermode="x unified", template="plotly_dark", height=460)
    return fig

def build_ribbon_chart(df, ticker):
    colors  = ["#ff6b6b","#ffa94d","#ffe066","#69db7c","#4dabf7","#cc5de8"]
    periods = [10, 20, 30, 50, 100, 200]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Close",
                             line=dict(color="white", width=1), opacity=0.35))
    for w, c in zip(periods, colors):
        fig.add_trace(go.Scatter(x=df.index, y=df[f"SMA{w}"], name=f"SMA {w}",
                                 line=dict(color=c, width=1.5)))
    fig.update_layout(title=f"{ticker} — Moving Average Ribbon",
                      xaxis_title="Date", yaxis_title="Price",
                      hovermode="x unified", template="plotly_dark", height=420)
    return fig

def build_macd_chart(df, ticker):
    macd_crosses = detect_macd_crosses(df)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.55, 0.45],
                        subplot_titles=[f"{ticker} Close Price", "MACD (12, 26, 9)"])
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Close",
                             line=dict(color="#4a90d9")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD",
                             line=dict(color="#f5a623", width=1.5)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_Signal"], name="Signal",
                             line=dict(color="#d0021b", width=1.5, dash="dot")), row=2, col=1)
    bar_colors = ["#00c851" if v >= 0 else "#d0021b" for v in df["MACD_Hist"]]
    fig.add_trace(go.Bar(x=df.index, y=df["MACD_Hist"], name="Histogram",
                         marker_color=bar_colors, opacity=0.6), row=2, col=1)
    for date, ctype in macd_crosses[-8:]:
        is_bull = "Bullish" in ctype
        fig.add_vline(x=date, line_width=1, line_dash="dash",
                      line_color="#00c851" if is_bull else "#d0021b")
    fig.update_layout(hovermode="x unified", template="plotly_dark", height=500)
    return fig

def build_rsi_adx_chart(df, ticker):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.5, 0.5],
                        subplot_titles=["RSI (14)", "ADX (14) with +DI / -DI"])
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
                             line=dict(color="#4dabf7", width=2)), row=1, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#d0021b",
                  annotation_text="Overbought 70", annotation_position="top left", row=1, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00c851",
                  annotation_text="Oversold 30",   annotation_position="bottom left", row=1, col=1)
    fig.add_hrect(y0=70,  y1=100, fillcolor="#d0021b", opacity=0.06, row=1, col=1)
    fig.add_hrect(y0=0,   y1=30,  fillcolor="#00c851", opacity=0.06, row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["ADX"],    name="ADX",
                             line=dict(color="#ffe066", width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["DI_pos"], name="+DI",
                             line=dict(color="#00c851", width=1.2, dash="dot")), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["DI_neg"], name="-DI",
                             line=dict(color="#d0021b", width=1.2, dash="dot")), row=2, col=1)
    fig.add_hline(y=25, line_dash="dash", line_color="#f5a623",
                  annotation_text="Strong Trend (25)", row=2, col=1)
    fig.update_layout(hovermode="x unified", template="plotly_dark", height=500)
    return fig

# ─────────────────────────────────────────────
# STREAMLIT UI
# ─────────────────────────────────────────────
st.set_page_config(page_title="Cross Signal Tracker", page_icon="📈", layout="wide")
st.markdown("""
    <style>
        .main { background-color: #0f1117; }
        .block-container { padding-top: 2rem; }
        h1 { color: #f5a623; }
        .stMetric label { color: #aaa; }
        .indicator-box {
            background: #1e2130; border-radius: 10px; padding: 16px 20px;
            margin-bottom: 10px; border-left: 4px solid #f5a623;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Golden & Death Cross Tracker")
st.caption("SMA crossovers · MACD · MA Ribbon · RSI · ADX — with email & SMS alerts")

# ── Sidebar ──
with st.sidebar:
    st.header("🔍 Analyze a Stock")
    ticker_input = st.text_input("Ticker Symbol", value="AAPL", max_chars=10).upper()
    period       = st.selectbox("Lookback Period", ["1y","2y","5y"], index=1)
    analyze_btn  = st.button("Analyze", use_container_width=True)

    st.divider()
    st.header("📧 Subscribe to Alerts")
    sub_ticker  = st.text_input("Ticker to Watch", value="AAPL", max_chars=10).upper()
    sub_email   = st.text_input("Email Address")
    st.caption("📱 Optional — add phone for SMS texts")
    sub_phone   = st.text_input("Phone Number (digits only)", placeholder="6125551234")
    sub_carrier = st.selectbox("Carrier", [""] + list(SMS_GATEWAYS.keys()))
    subscribe_btn = st.button("Subscribe", use_container_width=True)

    if subscribe_btn:
        if sub_email and "@" in sub_email:
            added = save_subscriber(sub_email, sub_ticker, sub_phone, sub_carrier)
            if added:
                st.success(f"Subscribed to {sub_ticker}!")
                if sub_phone and sub_carrier:
                    st.success("SMS alerts enabled!")
            else:
                st.info("Already subscribed to this ticker.")
        else:
            st.error("Enter a valid email.")

    st.divider()
    st.header("📋 Subscribers")
    subs_df = load_subscribers()
    if not subs_df.empty:
        st.dataframe(subs_df[["email","ticker","carrier"]], use_container_width=True, hide_index=True)
    else:
        st.caption("No subscribers yet.")

# ── Fetch Data ──
if analyze_btn or "df" not in st.session_state:
    with st.spinner(f"Fetching data for {ticker_input}..."):
        try:
            df = fetch_data(ticker_input, period)
            st.session_state["df"]     = df
            st.session_state["ticker"] = ticker_input
        except Exception as e:
            st.error(f"Could not fetch data: {e}")
            st.stop()

if "df" not in st.session_state:
    st.stop()

df      = st.session_state["df"]
ticker  = st.session_state["ticker"]
crosses = detect_sma_crosses(df)
latest  = crosses[-1] if crosses else None

# ── Top Metrics Row ──
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Current Price", f"${df['Close'].iloc[-1]:.2f}")
with col2:
    st.metric("SMA 50",  f"${df['SMA50'].iloc[-1]:.2f}")
with col3:
    st.metric("SMA 200", f"${df['SMA200'].iloc[-1]:.2f}")
with col4:
    if latest:
        d, c = latest
        label = "Golden Cross" if "Golden" in c else "Death Cross"
        st.metric("Latest SMA Cross", label, delta=str(d.date()))
    else:
        st.metric("Latest SMA Cross", "None detected")
with col5:
    ribbon_sig, _ = get_ribbon_signal(df)
    st.metric("MA Ribbon", ribbon_sig)

st.divider()

# ── Indicator Summary Cards ──
st.subheader("📊 Indicator Summary")
ic1, ic2, ic3, ic4 = st.columns(4)

with ic1:
    ribbon_label, ribbon_color = get_ribbon_signal(df)
    st.markdown(f"""<div class='indicator-box' style='border-color:{ribbon_color}'>
        <b style='color:{ribbon_color}'>MA Ribbon</b><br>
        <span style='font-size:20px;font-weight:bold'>{ribbon_label}</span><br>
        <small style='color:#888'>10/20/30/50/100/200 alignment</small>
    </div>""", unsafe_allow_html=True)

with ic2:
    macd_crosses = detect_macd_crosses(df)
    last_macd    = macd_crosses[-1] if macd_crosses else None
    macd_color   = "#00c851" if (last_macd and "Bullish" in last_macd[1]) else "#d0021b"
    macd_label   = last_macd[1] if last_macd else "No cross yet"
    macd_hist    = df["MACD_Hist"].iloc[-1]
    st.markdown(f"""<div class='indicator-box' style='border-color:{macd_color}'>
        <b style='color:{macd_color}'>MACD</b><br>
        <span style='font-size:20px;font-weight:bold'>{macd_label}</span><br>
        <small style='color:#888'>Histogram: {macd_hist:.4f}</small>
    </div>""", unsafe_allow_html=True)

with ic3:
    rsi_label, rsi_color = get_rsi_signal(df)
    st.markdown(f"""<div class='indicator-box' style='border-color:{rsi_color}'>
        <b style='color:{rsi_color}'>RSI (14)</b><br>
        <span style='font-size:20px;font-weight:bold'>{rsi_label}</span><br>
        <small style='color:#888'>&gt;70 overbought · &lt;30 oversold</small>
    </div>""", unsafe_allow_html=True)

with ic4:
    adx_label, adx_color = get_adx_signal(df)
    st.markdown(f"""<div class='indicator-box' style='border-color:{adx_color}'>
        <b style='color:{adx_color}'>ADX (14)</b><br>
        <span style='font-size:20px;font-weight:bold'>{adx_label}</span><br>
        <small style='color:#888'>25+ = strong trend confirmed</small>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── Tabbed Charts ──
tab1, tab2, tab3, tab4 = st.tabs(["📈 Golden/Death Cross", "🎀 MA Ribbon", "⚡ MACD", "📉 RSI & ADX"])

with tab1:
    st.plotly_chart(build_main_chart(df, ticker, crosses), use_container_width=True)
    st.subheader("SMA Cross History")
    if crosses:
        cross_df = pd.DataFrame(crosses, columns=["Date","Type"])
        cross_df["Date"] = cross_df["Date"].dt.date
        st.dataframe(cross_df[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("No SMA crosses detected in this time range.")

with tab2:
    st.plotly_chart(build_ribbon_chart(df, ticker), use_container_width=True)
    st.markdown("""
    **How to read the ribbon:** When shorter MAs (10, 20) fan above longer MAs (100, 200) in descending order,
    the trend is **bullish**. When they invert, the trend is **bearish**. A tightly compressed ribbon signals
    consolidation — a potential breakout may be ahead. Full alignment in one direction is the strongest signal.
    """)

with tab3:
    st.plotly_chart(build_macd_chart(df, ticker), use_container_width=True)
    st.markdown("""
    **MACD = EMA(12) − EMA(26).** The signal line is a 9-period EMA of the MACD line.
    A **bullish crossover** (MACD crosses above signal) suggests accelerating upward momentum —
    it typically triggers *faster* than a golden cross. A **bearish crossover** signals weakening.
    The histogram shows the spread between MACD and signal: growing bars = strengthening momentum, shrinking = weakening.
    """)

with tab4:
    st.plotly_chart(build_rsi_adx_chart(df, ticker), use_container_width=True)
    r1, r2 = st.columns(2)
    with r1:
        st.markdown("""
        **RSI (14)** measures momentum on a 0–100 scale.
        - **> 70** = Overbought — rally may be exhausted; golden cross less reliable here
        - **< 30** = Oversold — potential reversal; best confirmation for a death cross bounce
        - Ideal golden cross entry: RSI between 40–60 and rising
        """)
    with r2:
        st.markdown("""
        **ADX (14)** measures trend *strength*, not direction.
        - **< 20** = Weak/no trend — crossovers are more likely to be false signals
        - **20–25** = Trend developing
        - **> 25** = Strong trend — cross signals carry significantly more weight
        - **+DI > -DI** = bullish pressure; **-DI > +DI** = bearish pressure
        """)

st.divider()

# ── Alerts & Testing ──
st.subheader("🔔 Alerts")
alert_col, test_col = st.columns([1, 2])

with alert_col:
    st.markdown("**Send live alerts to subscribers**")
    if st.button("Check for New Crosses & Send Alerts", use_container_width=True):
        check_and_alert(ticker, df)

with test_col:
    st.markdown("**Test the email system**")
    test_email = st.text_input("Test email address", placeholder="you@gmail.com")
    tb1, tb2 = st.columns(2)
    with tb1:
        if st.button("Send Test Golden Cross Email"):
            if test_email and "@" in test_email:
                ok = send_email(test_email, "TEST", "Golden Cross", datetime.now().date(),
                                150.00, rsi_val=df["RSI"].iloc[-1],
                                adx_val=df["ADX"].iloc[-1], macd_val=df["MACD_Hist"].iloc[-1])
                st.success("Sent!") if ok else st.error("Failed — check email config.")
            else:
                st.error("Enter a valid email first.")
    with tb2:
        if st.button("Send Test Death Cross Email"):
            if test_email and "@" in test_email:
                ok = send_email(test_email, "TEST", "Death Cross", datetime.now().date(),
                                150.00, rsi_val=df["RSI"].iloc[-1],
                                adx_val=df["ADX"].iloc[-1], macd_val=df["MACD_Hist"].iloc[-1])
                st.success("Sent!") if ok else st.error("Failed — check email config.")
            else:
                st.error("Enter a valid email first.")

st.divider()
st.subheader("📬 Alert Log")
log_df = load_alerts_log()
if not log_df.empty:
    st.dataframe(log_df[::-1], use_container_width=True, hide_index=True)
else:
    st.caption("No alerts sent yet.")
