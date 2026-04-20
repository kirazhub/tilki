#!/usr/bin/env python3
import streamlit as st
import time
from datetime import datetime

st.set_page_config(page_title="🦊 Tilki", page_icon="🦊", layout="wide")

# Auto-refresh
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 15:
    st.session_state.last_refresh = time.time()
    st.rerun()

# BAŞLIK
st.markdown("# 🦊 TİLKİ")
now = datetime.now().strftime("%H:%M:%S")
st.caption(f"🔄 {now}")

st.divider()

# PORTFÖY ÖZETİ
st.subheader("💰 Portföy Özeti")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("💵 Başlangıç", "$20,000")
with col2:
    st.metric("🎯 Hedef", "+50%")
with col3:
    st.metric("📈 Mevcut", "+28%")
with col4:
    st.metric("📊 Kripto", "30")
with col5:
    st.metric("⏰ Gün", "~90")

st.divider()

# AÇIK POZİSYONLAR
st.subheader("📈 Açık Pozisyonlar")

# Veri (Kripto)
positions = [
    {"sym": "BTC", "name": "Bitcoin", "entry": 42500, "moc": 45230, "amt": 2500},
    {"sym": "ETH", "name": "Ethereum", "entry": 2200, "moc": 2850, "amt": 2300},
    {"sym": "BNB", "name": "BNB", "entry": 620, "moc": 710, "amt": 2000},
    {"sym": "SOL", "name": "Solana", "entry": 140, "moc": 165, "amt": 1800},
    {"sym": "XRP", "name": "XRP", "entry": 2.10, "moc": 2.45, "amt": 1600},
    {"sym": "ADA", "name": "Cardano", "entry": 1.05, "moc": 1.25, "amt": 1400},
    {"sym": "DOGE", "name": "Dogecoin", "entry": 0.38, "moc": 0.42, "amt": 1200},
    {"sym": "AVAX", "name": "Avalanche", "entry": 55, "moc": 65, "amt": 1100},
    {"sym": "MATIC", "name": "Polygon", "entry": 0.95, "moc": 1.10, "amt": 1000},
    {"sym": "DOT", "name": "Polkadot", "entry": 8.50, "moc": 10.20, "amt": 900},
    {"sym": "LINK", "name": "Chainlink", "entry": 18.00, "moc": 20.50, "amt": 800},
    {"sym": "UNI", "name": "Uniswap", "entry": 12.30, "moc": 14.80, "amt": 750},
    {"sym": "ATOM", "name": "Cosmos", "entry": 10.20, "moc": 12.50, "amt": 700},
    {"sym": "LTC", "name": "Litecoin", "entry": 800, "moc": 920, "amt": 650},
    {"sym": "BCH", "name": "Bitcoin Cash", "entry": 450, "moc": 510, "amt": 600},
    {"sym": "ALGO", "name": "Algorand", "entry": 0.65, "moc": 0.72, "amt": 550},
    {"sym": "XLM", "name": "Stellar", "entry": 0.12, "moc": 0.14, "amt": 500},
    {"sym": "VET", "name": "VeChain", "entry": 0.045, "moc": 0.052, "amt": 450},
    {"sym": "FIL", "name": "Filecoin", "entry": 18.50, "moc": 21.00, "amt": 400},
    {"sym": "TRX", "name": "TRON", "entry": 0.12, "moc": 0.14, "amt": 350},
]

# Hesapla
total_amt = sum(p["amt"] for p in positions)
total_pnl = sum(p["amt"] * ((p["moc"] - p["entry"]) / p["entry"]) for p in positions)
total_pct = (total_pnl / total_amt * 100) if total_amt > 0 else 0
win = sum(1 for p in positions if ((p["moc"] - p["entry"]) / p["entry"]) > 0.005)
lose = sum(1 for p in positions if ((p["moc"] - p["entry"]) / p["entry"]) < -0.005)
flat = len(positions) - win - lose

# Top bar
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
with col1:
    st.metric("💰 Toplam", f"${total_amt:,.0f}")
with col2:
    if total_pnl >= 0:
        st.metric("📊 P&L", f"${total_pnl:+,.0f}", delta=f"+${abs(total_pnl):.0f}")
    else:
        st.metric("📊 P&L", f"${total_pnl:+,.0f}", delta=f"-${abs(total_pnl):.0f}")
with col3:
    if total_pct >= 0:
        st.metric("📈 %", f"{total_pct:+.1f}%", delta=f"+{total_pct:.1f}%")
    else:
        st.metric("📈 %", f"{total_pct:+.1f}%", delta=f"{total_pct:.1f}%")
with col4:
    st.metric("✅ Kazanan", win)
with col5:
    st.metric("❌ Kaybeden", lose)
with col6:
    st.metric("🟡 Flat", flat)
with col7:
    st.metric("📍 Açık", len(positions))

st.divider()

# KARTLAR
cols = st.columns(4)
for idx, p in enumerate(positions):
    pnl_pct = ((p["moc"] - p["entry"]) / p["entry"]) * 100
    pnl_usd = p["amt"] * ((p["moc"] - p["entry"]) / p["entry"])
    
    with cols[idx % 4]:
        # Renk belirle
        if pnl_pct > 0.5:
            emoji = "🟢"
        elif pnl_pct < -0.5:
            emoji = "🔴"
        else:
            emoji = "🟡"
        
        st.write(f"### {p['sym']} {emoji}")
        st.write(f"*{p['name']}*")
        st.write(f"Entry: ${p['entry']:.2f}")
        st.write(f"MOC: ${p['moc']:.2f}")
        st.write(f"Pos: ${p['amt']:,.0f}")
        
        # P&L - Renkli
        if pnl_pct >= 0:
            st.success(f"**+{pnl_pct:.1f}%** | **+${pnl_usd:,.0f}**")
        else:
            st.error(f"**{pnl_pct:.1f}%** | **-${abs(pnl_usd):,.0f}**")

st.divider()
st.caption("🔄 15 saniye refresh | 🦊 Turuncu = Tilki | 🟢 Yeşil=Kar | 🔴 Kırmızı=Zarar")
