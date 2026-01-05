import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import requests
import time

# --- PAGE SETUP ---
st.set_page_config(page_title="Crypto Manager", layout="wide")
st.title("My Crypto Sell Advisor")

# --- SIDEBAR SETTINGS ---
st.sidebar.header("Settings")
symbol = st.sidebar.text_input("Coin Symbol (e.g., BTC/USDT)", value="BTC/USDT")
buy_price = st.sidebar.number_input("My Buy Price ($)", value=65000.0)
rsi_limit = st.sidebar.slider("RSI Sell Threshold", 50, 90, 70)

# Telegram Settings (Optional)
st.sidebar.subheader("Notifications")
enable_notify = st.sidebar.checkbox("Enable Telegram Alerts")
bot_token = st.sidebar.text_input("Bot Token", type="password")
chat_id = st.sidebar.text_input("Chat ID")

# --- FUNCTIONS ---
def get_data(symbol):
    exchange = ccxt.binance()
    bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def send_telegram(message, token, chat_id):
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": message})

# --- MAIN APP LOGIC ---
if st.button("Analyze Now"):
    with st.spinner(f"Fetching data for {symbol}..."):
        try:
            # 1. Get Data & Calculate
            df = get_data(symbol)
            df['rsi'] = ta.rsi(df['close'], length=14)

            current_price = df['close'].iloc[-1]
            current_rsi = df['rsi'].iloc[-1]

            # 2. Display Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Current Price", f"${current_price:,.2f}")

            # Color code the RSI
            rsi_color = "normal"
            if current_rsi > rsi_limit: rsi_color = "inverse" # Red highlighting if high
            col2.metric("RSI (Momentum)", f"{current_rsi:.1f}", delta=None, delta_color=rsi_color)

            # Profit Calculation
            profit_pct = ((current_price - buy_price) / buy_price) * 100
            col3.metric("Your Profit/Loss", f"{profit_pct:.2f}%",
                        delta=f"{current_price - buy_price:.2f}",
                        delta_color="normal")

            # 3. Charting
            fig = go.Figure(data=[go.Candlestick(x=df['timestamp'],
                            open=df['open'], high=df['high'],
                            low=df['low'], close=df['close'], name="Price")])

            # Add Buy Price Line
            fig.add_hline(y=buy_price, line_dash="dash", line_color="green", annotation_text="Your Buy Price")
            fig.update_layout(title=f"{symbol} Price Action", height=500)
            st.plotly_chart(fig, use_container_width=True)

            # 4. Sell Recommendation Engine
            st.subheader("Advisor Verdict")

            reasons = []
            if current_rsi > rsi_limit:
                st.error(f"SELL SIGNAL: Market is Overbought (RSI {current_rsi:.0f} > {rsi_limit})")
                reasons.append(f"RSI is high ({current_rsi:.0f}).")
            elif current_rsi < 30:
                st.success("BUY SIGNAL: Market is Oversold. Good time to accumulate.")
            else:
                st.info("HOLD: Market is neutral.")

            if profit_pct > 10:
                st.warning(f"TAKE PROFIT: You are up {profit_pct:.1f}%. Consider selling some.")
                reasons.append(f"Profit is up {profit_pct:.1f}%.")

            # 5. Send Alert if needed
            if enable_notify and (current_rsi > rsi_limit or profit_pct > 10):
                msg = f"ALERT: {symbol} at ${current_price:,.2f}\n" + "\n".join(reasons)
                send_telegram(msg, bot_token, chat_id)
                st.toast("Telegram Alert Sent!")

        except Exception as e:
            st.error(f"Error: {e}. Check your symbol name.")
