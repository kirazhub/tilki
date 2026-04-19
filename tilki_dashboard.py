"""
Tilki Kripto Ajanı - Streamlit Dashboard
"""

import json
import time
import logging
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from tilki_config import (
    KRIPTO_SEMBOLLER, SEMBOL_ISIMLER, RENK_TEMA, COINGECKO_IDS,
    BASLANGIC_SERMAYE_USD, BASLANGIC_SERMAYE_TL, YENILEME_SURESI,
)
from tilki_database import (
    tablolari_olustur,
    son_islemleri_getir,
    kapali_pozisyonlari_getir,
    portfoy_gecmisini_getir,
    dusunce_loglarini_getir,
    istatistikleri_hesapla,
    son_market_verilerini_getir,
)

logger = logging.getLogger("tilki.dashboard")

# ============================================================
# SAYFA AYARLARI
# ============================================================
st.set_page_config(
    page_title="TİLKİ 🦊 — Kripto Ajanı",
    page_icon="🦊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS Teması
st.markdown("""
<style>
    /* Ana arka plan */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161B27;
        border-right: 1px solid #2D3748;
    }

    /* Metrik kartları */
    [data-testid="metric-container"] {
        background-color: #1E2130;
        border: 1px solid #2D3748;
        border-radius: 10px;
        padding: 15px;
    }

    /* Başlık */
    h1, h2, h3 {
        color: #FF8C00 !important;
    }

    /* Butonlar */
    .stButton button {
        background-color: #FF8C00;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
    }

    .stButton button:hover {
        background-color: #FFB347;
    }

    /* Tablo */
    [data-testid="stDataFrame"] {
        background-color: #1E2130;
    }

    /* AL/SAT rozetleri */
    .badge-al {
        background-color: #00C896;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 12px;
    }
    .badge-sat {
        background-color: #FF4B4B;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 12px;
    }
    .badge-bekle {
        background-color: #FFD700;
        color: #0E1117;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 12px;
    }

    /* Kart stili */
    .tilki-card {
        background-color: #1E2130;
        border: 1px solid #2D3748;
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
    }

    /* Pozisyon kartı */
    .pozisyon-card-green {
        background: linear-gradient(135deg, #1E2130, #0D2118);
        border: 1px solid #00C896;
        border-radius: 12px;
        padding: 15px;
        margin: 5px 0;
    }
    .pozisyon-card-red {
        background: linear-gradient(135deg, #1E2130, #210D0D);
        border: 1px solid #FF4B4B;
        border-radius: 12px;
        padding: 15px;
        margin: 5px 0;
    }

    /* Düşünce logu */
    .dusunce-item {
        background-color: #1A1F2E;
        border-left: 3px solid #FF8C00;
        padding: 10px 15px;
        margin: 5px 0;
        border-radius: 0 8px 8px 0;
        font-size: 14px;
    }
    .dusunce-item-kritik {
        border-left-color: #FF4B4B;
    }
    .dusunce-item-yuksek {
        border-left-color: #FFD700;
    }

    /* Fear & Greed gauge renkleri */
    .fg-extreme-fear { color: #FF4B4B; }
    .fg-fear { color: #FF8C00; }
    .fg-neutral { color: #FFD700; }
    .fg-greed { color: #90EE90; }
    .fg-extreme-greed { color: #00C896; }

    /* Footer */
    .tilki-footer {
        text-align: center;
        color: #8B9BB4;
        font-size: 12px;
        padding: 20px;
        border-top: 1px solid #2D3748;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def renk_kar_zarar(deger: float) -> str:
    return RENK_TEMA["success"] if deger >= 0 else RENK_TEMA["danger"]


def format_usd(deger: float) -> str:
    if abs(deger) >= 1e9:
        return f"${deger/1e9:.2f}B"
    elif abs(deger) >= 1e6:
        return f"${deger/1e6:.2f}M"
    elif abs(deger) >= 1e3:
        return f"${deger/1e3:.1f}K"
    return f"${deger:.2f}"


def format_tl(deger: float) -> str:
    if abs(deger) >= 1e6:
        return f"₺{deger/1e6:.2f}M"
    return f"₺{deger:,.0f}"


def fg_renk_sinifi(deger: int) -> str:
    if deger < 25:
        return "🔴 Aşırı Korku"
    elif deger < 45:
        return "🟠 Korku"
    elif deger < 55:
        return "🟡 Nötr"
    elif deger < 75:
        return "🟢 Açgözlülük"
    return "💚 Aşırı Açgözlülük"


def fg_renk(deger: int) -> str:
    if deger < 25:
        return "#FF4B4B"
    elif deger < 45:
        return "#FF8C00"
    elif deger < 55:
        return "#FFD700"
    elif deger < 75:
        return "#90EE90"
    return "#00C896"


def sinyal_badge(sinyal: str) -> str:
    if sinyal == "AL":
        return '<span class="badge-al">🟢 AL</span>'
    elif sinyal == "SAT":
        return '<span class="badge-sat">🔴 SAT</span>'
    return '<span class="badge-bekle">🟡 BEKLE</span>'


def guven_rengi(guven: int) -> str:
    if guven >= 80:
        return RENK_TEMA["success"]
    elif guven >= 60:
        return "#90EE90"
    elif guven >= 40:
        return RENK_TEMA["warning"]
    return RENK_TEMA["subtext"]


@st.cache_data(ttl=YENILEME_SURESI)
def veri_yukle_cache() -> Dict[str, Any]:
    """Veri çekme işlemini cache'ler."""
    try:
        from tilki_data import tam_veri_paketi_cek
        return tam_veri_paketi_cek()
    except Exception as e:
        logger.error(f"Veri yükleme hatası: {e}")
        return {}


@st.cache_data(ttl=YENILEME_SURESI)
def sinyalleri_hesapla_cache(veri_paketi_zaman: str) -> Dict[str, Any]:
    """Sinyal hesaplamasını cache'ler."""
    try:
        from tilki_data import tam_veri_paketi_cek
        from tilki_strategy import teknik_analiz_yap, piyasa_rejimi_tespit, tum_sinyalleri_uret

        veri_paketi = tam_veri_paketi_cek()

        fg = veri_paketi.get("fear_greed")
        fg_deger = fg["deger"] if fg else 50

        btc_df = veri_paketi.get("gunluk_veriler", {}).get("BTC-USD")
        btc_analiz = teknik_analiz_yap(btc_df, "BTC-USD") if btc_df is not None else None
        piyasa_rejimi, rejim_aciklama = piyasa_rejimi_tespit(btc_analiz, fg_deger)

        sinyaller, analizler = tum_sinyalleri_uret(
            gunluk_veriler=veri_paketi.get("gunluk_veriler", {}),
            saatlik_veriler=veri_paketi.get("saatlik_veriler", {}),
            fear_greed_deger=fg_deger,
            piyasa_rejimi=piyasa_rejimi,
            coingecko_market=veri_paketi.get("coingecko_market", {}),
        )

        return {
            "sinyaller": sinyaller,
            "analizler": analizler,
            "veri_paketi": veri_paketi,
            "piyasa_rejimi": piyasa_rejimi,
            "rejim_aciklama": rejim_aciklama,
            "fg_deger": fg_deger,
        }
    except Exception as e:
        logger.error(f"Sinyal hesaplama hatası: {e}")
        return {}


def sparkline_grafigi(prices: List[float], renk: str = "#FF8C00") -> Optional[go.Figure]:
    """Mini sparkline grafiği oluşturur."""
    if not prices or len(prices) < 2:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=prices,
        mode="lines",
        line=dict(color=renk, width=1.5),
        fill="tozeroy",
        fillcolor=f"rgba({int(renk[1:3], 16)}, {int(renk[3:5], 16)}, {int(renk[5:7], 16)}, 0.1)",
    ))
    fig.update_layout(
        height=50, width=120,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def candlestick_grafigi(df: pd.DataFrame, sembol: str, analiz: Optional[Dict] = None) -> go.Figure:
    """Tam kandle grafik + indikatörler oluşturur."""
    df = df.tail(120).copy()  # Son 120 gün

    # Alt grafikler: fiyat, RSI, MACD, hacim
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=("", "RSI", "MACD", "Hacim"),
    )

    # --- Mum grafiği ---
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"], high=df["high"],
        low=df["low"], close=df["close"],
        name="OHLCV",
        increasing_line_color=RENK_TEMA["success"],
        decreasing_line_color=RENK_TEMA["danger"],
    ), row=1, col=1)

    if analiz and analiz.get("df") is not None:
        adf = analiz["df"].tail(120)
        son = analiz.get("son", {})

        # Bollinger Bands
        if "bb_ust" in adf.columns:
            fig.add_trace(go.Scatter(
                x=adf.index, y=adf["bb_ust"],
                name="BB Üst", line=dict(color="#8B9BB4", width=1, dash="dash"),
                showlegend=False,
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=adf.index, y=adf["bb_alt"],
                name="BB Alt", line=dict(color="#8B9BB4", width=1, dash="dash"),
                fill="tonexty", fillcolor="rgba(139,155,180,0.05)",
                showlegend=False,
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=adf.index, y=adf["bb_orta"],
                name="BB Orta", line=dict(color="#8B9BB4", width=0.8),
                showlegend=False,
            ), row=1, col=1)

        # Moving Averages
        ma_renkler = {
            "ma_20": ("#4FC3F7", "MA20"),
            "ma_50": ("#FFD700", "MA50"),
            "ma_200": ("#FF8C00", "MA200"),
        }
        for ma_key, (renk, isim) in ma_renkler.items():
            if ma_key in adf.columns:
                fig.add_trace(go.Scatter(
                    x=adf.index, y=adf[ma_key],
                    name=isim, line=dict(color=renk, width=1.2),
                ), row=1, col=1)

        # Fibonacci seviyeleri
        fib = analiz.get("fib", {})
        fib_renkler = {"0.236": "#9C27B0", "0.382": "#3F51B5", "0.5": "#009688",
                       "0.618": "#F44336", "0.786": "#FF9800"}
        for seviye, renk in fib_renkler.items():
            if seviye in fib:
                fig.add_hline(
                    y=fib[seviye], line_dash="dot",
                    line_color=renk, line_width=0.8,
                    annotation_text=f"Fib {seviye}",
                    annotation_font_size=9,
                    row=1, col=1,
                )

        # RSI
        if "rsi_14" in adf.columns:
            fig.add_trace(go.Scatter(
                x=adf.index, y=adf["rsi_14"],
                name="RSI(14)", line=dict(color="#FF8C00", width=1.5),
            ), row=2, col=1)
            if "rsi_7" in adf.columns:
                fig.add_trace(go.Scatter(
                    x=adf.index, y=adf["rsi_7"],
                    name="RSI(7)", line=dict(color="#4FC3F7", width=1),
                ), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="#FF4B4B", line_width=0.8, row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#00C896", line_width=0.8, row=2, col=1)
            fig.add_hline(y=50, line_dash="dot", line_color="#8B9BB4", line_width=0.5, row=2, col=1)

        # MACD
        if "macd" in adf.columns:
            fig.add_trace(go.Scatter(
                x=adf.index, y=adf["macd"],
                name="MACD", line=dict(color="#4FC3F7", width=1.5),
            ), row=3, col=1)
            fig.add_trace(go.Scatter(
                x=adf.index, y=adf["macd_sinyal"],
                name="Sinyal", line=dict(color="#FF8C00", width=1),
            ), row=3, col=1)
            if "macd_hist" in adf.columns:
                renkler = [RENK_TEMA["success"] if v >= 0 else RENK_TEMA["danger"]
                           for v in adf["macd_hist"]]
                fig.add_trace(go.Bar(
                    x=adf.index, y=adf["macd_hist"],
                    name="Histogram", marker_color=renkler, opacity=0.7,
                ), row=3, col=1)

    # Hacim
    vol_renkler = [
        RENK_TEMA["success"] if df["close"].iloc[i] >= df["open"].iloc[i] else RENK_TEMA["danger"]
        for i in range(len(df))
    ]
    fig.add_trace(go.Bar(
        x=df.index, y=df["volume"],
        name="Hacim", marker_color=vol_renkler, opacity=0.7,
    ), row=4, col=1)

    fig.update_layout(
        title=dict(
            text=f"🦊 {SEMBOL_ISIMLER.get(sembol, sembol)} ({sembol})",
            font=dict(color=RENK_TEMA["primary"], size=16),
        ),
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        font=dict(color=RENK_TEMA["text"]),
        height=750,
        xaxis_rangeslider_visible=False,
        legend=dict(
            bgcolor="rgba(30,33,48,0.8)",
            bordercolor=RENK_TEMA["primary"],
            font=dict(size=11),
        ),
        margin=dict(l=60, r=20, t=60, b=20),
    )

    # Y ekseni renkleri
    for i in range(1, 5):
        fig.update_yaxes(
            gridcolor="#1E2130",
            zerolinecolor="#2D3748",
            tickfont=dict(color=RENK_TEMA["subtext"]),
            row=i, col=1,
        )
    fig.update_xaxes(
        gridcolor="#1E2130",
        tickfont=dict(color=RENK_TEMA["subtext"]),
    )

    return fig


def portfoy_grafigi(portfoy_gecmisi: List[Dict]) -> Optional[go.Figure]:
    """Portföy değer grafiği."""
    if not portfoy_gecmisi:
        return None

    df = pd.DataFrame(portfoy_gecmisi)
    df["zaman"] = pd.to_datetime(df["zaman"])

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(
        x=df["zaman"], y=df["toplam_deger_usd"],
        name="USD", fill="tozeroy",
        line=dict(color=RENK_TEMA["primary"], width=2),
        fillcolor="rgba(255,140,0,0.1)",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=df["zaman"], y=df["toplam_deger_tl"],
        name="TL", line=dict(color=RENK_TEMA["secondary"], width=1.5, dash="dash"),
    ), secondary_y=True)

    baslangic_usd = BASLANGIC_SERMAYE_USD
    fig.add_hline(
        y=baslangic_usd, line_dash="dot",
        line_color=RENK_TEMA["subtext"], line_width=1,
        annotation_text="Başlangıç",
    )

    fig.update_layout(
        title="Portföy Değeri",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        font=dict(color=RENK_TEMA["text"]),
        height=300,
        margin=dict(l=60, r=60, t=40, b=20),
        legend=dict(bgcolor="rgba(30,33,48,0.8)"),
    )
    fig.update_yaxes(
        title_text="USD", secondary_y=False,
        gridcolor="#1E2130", tickfont=dict(color=RENK_TEMA["subtext"]),
    )
    fig.update_yaxes(
        title_text="TL", secondary_y=True,
        gridcolor="#1E2130", tickfont=dict(color=RENK_TEMA["subtext"]),
    )
    fig.update_xaxes(gridcolor="#1E2130", tickfont=dict(color=RENK_TEMA["subtext"]))

    return fig


def kar_zarar_grafigi(kapali_pozisyonlar: List[Dict]) -> Optional[go.Figure]:
    """K/Z zaman grafiği."""
    if not kapali_pozisyonlar:
        return None

    df = pd.DataFrame(kapali_pozisyonlar)
    df["kapanis_zamani"] = pd.to_datetime(df["kapanis_zamani"])
    df = df.sort_values("kapanis_zamani")
    df["kumulatif_kar_zarar"] = df["kar_zarar_usd"].cumsum()

    fig = go.Figure()

    renkler = [RENK_TEMA["success"] if v >= 0 else RENK_TEMA["danger"]
               for v in df["kar_zarar_usd"]]

    fig.add_trace(go.Bar(
        x=df["kapanis_zamani"], y=df["kar_zarar_usd"],
        name="İşlem K/Z", marker_color=renkler,
        opacity=0.7,
    ))

    fig.add_trace(go.Scatter(
        x=df["kapanis_zamani"], y=df["kumulatif_kar_zarar"],
        name="Kümülatif K/Z",
        line=dict(color=RENK_TEMA["secondary"], width=2),
        yaxis="y2",
    ))

    fig.update_layout(
        title="İşlem Kar/Zarar Geçmişi",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        font=dict(color=RENK_TEMA["text"]),
        height=300,
        yaxis2=dict(overlaying="y", side="right", tickfont=dict(color=RENK_TEMA["subtext"]), gridcolor="#1E2130"),
        yaxis=dict(gridcolor="#1E2130", tickfont=dict(color=RENK_TEMA["subtext"])),
        xaxis=dict(gridcolor="#1E2130", tickfont=dict(color=RENK_TEMA["subtext"])),
        legend=dict(bgcolor="rgba(30,33,48,0.8)"),
        margin=dict(l=60, r=60, t=40, b=20),
    )

    return fig


def kazanan_kaybeden_pasta(istatistikler: Dict) -> Optional[go.Figure]:
    """Win/Loss pasta grafiği."""
    kazanan = istatistikler.get("kazanan", 0)
    kaybeden = istatistikler.get("kaybeden", 0)

    if kazanan + kaybeden == 0:
        return None

    fig = go.Figure(go.Pie(
        labels=["Kazanan", "Kaybeden"],
        values=[kazanan, kaybeden],
        hole=0.4,
        marker_colors=[RENK_TEMA["success"], RENK_TEMA["danger"]],
        textfont=dict(color="white", size=14),
        hovertemplate="<b>%{label}</b><br>Sayı: %{value}<br>Oran: %{percent}<extra></extra>",
    ))

    fig.update_layout(
        paper_bgcolor="#0E1117",
        font=dict(color=RENK_TEMA["text"]),
        height=250,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        annotations=[dict(
            text=f"{istatistikler.get('kazanma_orani', 0):.0f}%",
            x=0.5, y=0.5, font_size=22,
            font_color=RENK_TEMA["success"],
            showarrow=False,
        )],
    )
    return fig


def fg_gauge(deger: int) -> go.Figure:
    """Fear & Greed göstergesi."""
    renk = fg_renk(deger)
    sinif = fg_renk_sinifi(deger)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=deger,
        title={"text": "Fear & Greed", "font": {"color": RENK_TEMA["text"], "size": 14}},
        gauge={
            "axis": {"range": [0, 100], "tickfont": {"color": RENK_TEMA["subtext"]}},
            "bar": {"color": renk},
            "bgcolor": "#1E2130",
            "bordercolor": "#2D3748",
            "steps": [
                {"range": [0, 25], "color": "rgba(255,75,75,0.2)"},
                {"range": [25, 45], "color": "rgba(255,140,0,0.2)"},
                {"range": [45, 55], "color": "rgba(255,215,0,0.2)"},
                {"range": [55, 75], "color": "rgba(144,238,144,0.2)"},
                {"range": [75, 100], "color": "rgba(0,200,150,0.2)"},
            ],
            "threshold": {
                "line": {"color": renk, "width": 3},
                "thickness": 0.75,
                "value": deger,
            },
        },
        number={"font": {"color": renk, "size": 32}, "suffix": ""},
    ))

    fig.update_layout(
        paper_bgcolor="#0E1117",
        font=dict(color=RENK_TEMA["text"]),
        height=200,
        margin=dict(l=20, r=20, t=40, b=10),
        annotations=[dict(
            text=sinif, x=0.5, y=-0.1,
            font_size=13, font_color=renk,
            showarrow=False,
        )],
    )
    return fig


# ============================================================
# SAYFA 1: GENEL BAKIŞ
# ============================================================

def sayfa_genel_bakis(durum: Dict[str, Any]) -> None:
    st.title("🦊 TİLKİ — Genel Bakış")

    veri = durum.get("veri_paketi", {})
    sinyaller = durum.get("sinyaller", {})
    portfoy_gecmisi = portfoy_gecmisini_getir(500)
    son_islemler = son_islemleri_getir(20)

    # --- Üst metrikler ---
    col1, col2, col3, col4, col5 = st.columns(5)

    portfoy = portfoy_gecmisi[-1] if portfoy_gecmisi else {}
    toplam_usd = portfoy.get("toplam_deger_usd", BASLANGIC_SERMAYE_USD)
    toplam_tl = portfoy.get("toplam_deger_tl", BASLANGIC_SERMAYE_TL)
    nakit_usd = portfoy.get("nakit_usd", BASLANGIC_SERMAYE_USD)
    pozisyon_degeri = portfoy.get("pozisyon_degeri_usd", 0)
    acik_poz = portfoy.get("acik_pozisyon_sayisi", 0)

    kar_zarar = toplam_usd - BASLANGIC_SERMAYE_USD
    kar_zarar_yuzde = (kar_zarar / BASLANGIC_SERMAYE_USD * 100) if BASLANGIC_SERMAYE_USD > 0 else 0

    with col1:
        st.metric("💼 Portföy (USD)", format_usd(toplam_usd),
                  f"{kar_zarar_yuzde:+.2f}%",
                  delta_color="normal")

    with col2:
        st.metric("💴 Portföy (TL)", format_tl(toplam_tl),
                  f"{format_tl(toplam_tl - BASLANGIC_SERMAYE_TL)}")

    with col3:
        cg_global = veri.get("coingecko_global", {}) or {}
        btc_dom = cg_global.get("btc_dominance", 0)
        st.metric("₿ BTC Dominance", f"{btc_dom:.1f}%")

    with col4:
        piyasa_degeri = cg_global.get("toplam_piyasa_degeri_usd", 0)
        st.metric("🌍 Toplam Piyasa", format_usd(piyasa_degeri))

    with col5:
        fg = veri.get("fear_greed", {}) or {}
        fg_deger = fg.get("deger", 50)
        st.metric("😱 Fear & Greed", fg_deger, fg_renk_sinifi(fg_deger))

    st.divider()

    # --- Ana içerik ---
    col_sol, col_sag = st.columns([2, 1])

    with col_sol:
        # Portföy grafiği
        portfoy_fig = portfoy_grafigi(portfoy_gecmisi)
        if portfoy_fig:
            st.plotly_chart(portfoy_fig, use_container_width=True)
        else:
            st.info("📊 Portföy grafiği için veri bekleniyor...")

        # Açık pozisyonlar
        st.subheader("📌 Açık Pozisyonlar")
        if acik_poz > 0:
            for sinyal_sembol, sinyal_veri in sinyaller.items():
                fiyat = sinyal_veri.get("fiyat", 0)
                # Gerçek portföy durumunu DB'den al
                islemler = son_islemleri_getir(100)
                acik_islemler = [i for i in islemler if i.get("durum") == "ACIK" and i.get("islem_turu") == "AL"]

                if not acik_islemler:
                    st.info("Açık pozisyon bulunmuyor")
                    break

                for islem in acik_islemler[:8]:
                    sembol = islem.get("sembol", "")
                    giris = islem.get("fiyat_usd", 0)
                    toplam = islem.get("toplam_usd", 0)

                    sinyal_data = sinyaller.get(sembol, {})
                    guncel = sinyal_data.get("fiyat", giris)
                    kz_yuzde = ((guncel - giris) / giris * 100) if giris > 0 else 0
                    kz_usd = (guncel - giris) / giris * toplam if giris > 0 else 0

                    kart_sinifi = "pozisyon-card-green" if kz_yuzde >= 0 else "pozisyon-card-red"
                    emoji = "🟢" if kz_yuzde >= 0 else "🔴"

                    st.markdown(f"""
                    <div class="{kart_sinifi}">
                        <b>{emoji} {sembol}</b> — {SEMBOL_ISIMLER.get(sembol, sembol)}<br>
                        Giriş: ${giris:.4f} → Güncel: ${guncel:.4f}<br>
                        K/Z: <b style="color: {'#00C896' if kz_yuzde >= 0 else '#FF4B4B'}">{kz_yuzde:+.2f}% (${kz_usd:+.2f})</b><br>
                        Tutar: ${toplam:.2f}
                    </div>
                    """, unsafe_allow_html=True)
                break
        else:
            st.info("Açık pozisyon bulunmuyor. Ajan yeni fırsatlar tarıyor...")

    with col_sag:
        # Fear & Greed gauge
        fg_fig = fg_gauge(fg_deger)
        st.plotly_chart(fg_fig, use_container_width=True)

        # Piyasa rejimi
        rejim = durum.get("piyasa_rejimi", "BELIRSIZ")
        rejim_emojiler = {
            "BOGA_KUVVETLI": "🚀", "BOGA_ZAYIF": "📈",
            "SIDEWAYS": "↔️", "AYI_ZAYIF": "📉",
            "AYI_KUVVETLI": "💥", "BELIRSIZ": "❓",
        }
        rejim_emoji = rejim_emojiler.get(rejim, "❓")
        st.markdown(f"""
        <div class="tilki-card">
            <h4 style="color: #FF8C00;">🌡️ Piyasa Rejimi</h4>
            <h2 style="color: #FAFAFA;">{rejim_emoji} {rejim}</h2>
            <p style="color: #8B9BB4; font-size: 12px;">{durum.get('rejim_aciklama', '')}</p>
        </div>
        """, unsafe_allow_html=True)

        # Son işlemler feed
        st.subheader("📋 Son İşlemler")
        if son_islemler:
            for islem in son_islemler[:8]:
                tur = islem.get("islem_turu", "")
                sembol = islem.get("sembol", "")
                fiyat = islem.get("fiyat_usd", 0)
                zaman = islem.get("zaman", "")[:16]
                emoji = "🟢" if tur == "AL" else "🔴"

                st.markdown(f"""
                <div style="padding: 6px 10px; border-left: 3px solid {'#00C896' if tur == 'AL' else '#FF4B4B'};
                     margin: 3px 0; background: #1A1F2E; border-radius: 0 6px 6px 0;">
                    {emoji} <b>{tur}</b> {sembol} @ ${fiyat:.4f}<br>
                    <span style="color: #8B9BB4; font-size: 11px;">{zaman}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Henüz işlem yapılmadı")

        # Kazanan/kaybeden listesi
        st.subheader("🏆 Günlük Kazananlar")
        kazananlar = veri.get("kazananlar", [])[:5]
        for c in kazananlar:
            degisim = c.get("price_change_percentage_24h", 0) or 0
            st.markdown(f"🟢 **{c.get('symbol', '').upper()}** +{degisim:.1f}%")

        st.subheader("📉 Günlük Kaybedenler")
        kaybedenler = veri.get("kaybedenler", [])[:5]
        for c in kaybedenler:
            degisim = c.get("price_change_percentage_24h", 0) or 0
            st.markdown(f"🔴 **{c.get('symbol', '').upper()}** {degisim:.1f}%")


# ============================================================
# SAYFA 2: PİYASA TARAYICI
# ============================================================

def sayfa_piyasa_tarayici(durum: Dict[str, Any]) -> None:
    st.title("📡 TİLKİ — Piyasa Tarayıcı")

    sinyaller = durum.get("sinyaller", {})
    veri = durum.get("veri_paketi", {})
    cg_market = veri.get("coingecko_market", {})

    if not sinyaller:
        st.warning("Veri yükleniyor, lütfen bekleyin...")
        return

    # Filtre araçları
    col1, col2, col3 = st.columns(3)
    with col1:
        filtre_sinyal = st.selectbox("Sinyal Filtresi", ["Tümü", "AL", "SAT", "BEKLE"])
    with col2:
        siralama = st.selectbox("Sırala", ["Güven Skoru (Azalan)", "24s Değişim", "Piyasa Değeri"])
    with col3:
        min_guven = st.slider("Min Güven Skoru", 0, 100, 0)

    # Tablo verisi oluştur
    tablo_verisi = []
    for sembol in KRIPTO_SEMBOLLER:
        sinyal = sinyaller.get(sembol, {})
        cg = cg_market.get(sembol, {})

        sinyal_str = sinyal.get("sinyal", "BEKLE")
        guven = sinyal.get("guven", 0)
        fiyat = sinyal.get("fiyat", 0) or cg.get("guncel_fiyat", 0)
        deg_24h = sinyal.get("degisim_24h", 0) or cg.get("degisim_24h", 0) or 0
        deg_7g = sinyal.get("degisim_7g", 0) or cg.get("degisim_7g", 0) or 0
        piyasa = sinyal.get("piyasa_degeri", 0) or cg.get("piyasa_degeri_usd", 0) or 0
        sparkline = sinyal.get("sparkline", []) or cg.get("sparkline", [])
        rsi = sinyal.get("rsi", 0)

        if filtre_sinyal != "Tümü" and sinyal_str != filtre_sinyal:
            continue
        if guven < min_guven:
            continue

        tablo_verisi.append({
            "Sembol": sembol,
            "İsim": SEMBOL_ISIMLER.get(sembol, sembol),
            "Fiyat": fiyat,
            "24s %": deg_24h,
            "7g %": deg_7g,
            "RSI": round(rsi, 1) if rsi else 0,
            "Sinyal": sinyal_str,
            "Güven": guven,
            "Piyasa Değ.": piyasa,
            "_sparkline": sparkline,
        })

    if not tablo_verisi:
        st.info("Filtre kriterlerine uyan coin bulunamadı.")
        return

    # Sıralama
    if siralama == "Güven Skoru (Azalan)":
        tablo_verisi.sort(key=lambda x: x["Güven"], reverse=True)
    elif siralama == "24s Değişim":
        tablo_verisi.sort(key=lambda x: x["24s %"], reverse=True)
    elif siralama == "Piyasa Değeri":
        tablo_verisi.sort(key=lambda x: x["Piyasa Değ."], reverse=True)

    # Kolon başlıkları
    basliklar = st.columns([1.5, 2, 1.5, 1, 1, 1, 1.5, 1, 1.5, 2])
    col_isimler = ["Sembol", "İsim", "Fiyat", "24s %", "7g %", "RSI", "Sinyal", "Güven", "Piyasa D.", "Sparkline"]
    for baslik_col, isim in zip(basliklar, col_isimler):
        with baslik_col:
            st.markdown(f"**{isim}**")

    st.divider()

    # Satırlar
    for satir in tablo_verisi:
        cols = st.columns([1.5, 2, 1.5, 1, 1, 1, 1.5, 1, 1.5, 2])

        with cols[0]:
            st.text(satir["Sembol"].replace("-USD", ""))
        with cols[1]:
            st.text(satir["İsim"])
        with cols[2]:
            st.text(f"${satir['Fiyat']:.4f}" if satir["Fiyat"] < 10 else f"${satir['Fiyat']:,.2f}")
        with cols[3]:
            deg = satir["24s %"]
            renk = "#00C896" if deg >= 0 else "#FF4B4B"
            st.markdown(f'<span style="color:{renk}">{deg:+.1f}%</span>', unsafe_allow_html=True)
        with cols[4]:
            deg = satir["7g %"]
            renk = "#00C896" if deg >= 0 else "#FF4B4B"
            st.markdown(f'<span style="color:{renk}">{deg:+.1f}%</span>', unsafe_allow_html=True)
        with cols[5]:
            rsi = satir["RSI"]
            renk = "#FF4B4B" if rsi > 70 else ("#00C896" if rsi < 30 else "#FAFAFA")
            st.markdown(f'<span style="color:{renk}">{rsi:.0f}</span>', unsafe_allow_html=True)
        with cols[6]:
            st.markdown(sinyal_badge(satir["Sinyal"]), unsafe_allow_html=True)
        with cols[7]:
            guven = satir["Güven"]
            st.markdown(f'<span style="color:{guven_rengi(guven)}">{guven}</span>', unsafe_allow_html=True)
        with cols[8]:
            st.text(format_usd(satir["Piyasa Değ."]))
        with cols[9]:
            sparkline_data = satir["_sparkline"]
            if sparkline_data and len(sparkline_data) >= 2:
                deg = satir["24s %"]
                sp_renk = "#00C896" if deg >= 0 else "#FF4B4B"
                sp_fig = sparkline_grafigi(sparkline_data[-24:], sp_renk)
                if sp_fig:
                    st.plotly_chart(sp_fig, use_container_width=False, config={"displayModeBar": False})


# ============================================================
# SAYFA 3: COİN ANALİZİ
# ============================================================

def sayfa_coin_analizi(durum: Dict[str, Any]) -> None:
    st.title("🔍 TİLKİ — Coin Analizi")

    sinyaller = durum.get("sinyaller", {})
    analizler = durum.get("analizler", {})
    veri = durum.get("veri_paketi", {})

    # Coin seçici
    col1, col2 = st.columns([2, 4])
    with col1:
        secili_sembol = st.selectbox(
            "Coin seç",
            KRIPTO_SEMBOLLER,
            format_func=lambda s: f"{s} — {SEMBOL_ISIMLER.get(s, s)}",
        )

    sinyal = sinyaller.get(secili_sembol, {})
    analiz = analizler.get(secili_sembol, {})
    gunluk_analiz = analiz.get("gunluk")
    cg_veri = veri.get("coingecko_market", {}).get(secili_sembol, {})

    # Özet metrikler
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    fiyat = sinyal.get("fiyat", 0)
    deg_24h = sinyal.get("degisim_24h", 0) or cg_veri.get("degisim_24h", 0) or 0
    rsi = sinyal.get("rsi", 0)
    macd_h = sinyal.get("macd_hist", 0)
    bb_pos = sinyal.get("bb_pozisyon", 0.5)
    guven = sinyal.get("guven", 0)

    with col1:
        st.metric("Fiyat (USD)", f"${fiyat:,.4f}" if fiyat < 10 else f"${fiyat:,.2f}", f"{deg_24h:+.2f}%")
    with col2:
        rsi_renk = "🔴" if rsi > 70 else ("🟢" if rsi < 30 else "⚪")
        st.metric("RSI (14)", f"{rsi_renk} {rsi:.1f}")
    with col3:
        macd_renk = "📈" if macd_h > 0 else "📉"
        st.metric("MACD Hist.", f"{macd_renk} {macd_h:.4f}")
    with col4:
        bb_pct = (bb_pos or 0.5) * 100
        st.metric("BB Pozisyon", f"{bb_pct:.0f}%")
    with col5:
        sinyal_str = sinyal.get("sinyal", "BEKLE")
        st.metric("Sinyal", sinyal_str)
    with col6:
        st.metric("Güven Skoru", f"{guven}/100")

    st.divider()

    # Mum grafiği
    df_gunluk = veri.get("gunluk_veriler", {}).get(secili_sembol)
    if df_gunluk is not None and len(df_gunluk) > 20:
        fig = candlestick_grafigi(df_gunluk, secili_sembol, gunluk_analiz)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"{secili_sembol} için grafik verisi bulunamadı.")

    # Karar açıklaması
    st.subheader("🧠 Tilki'nin Kararı")
    nedenler = sinyal.get("neden", [])
    if nedenler:
        sinyal_renk = {"AL": "#00C896", "SAT": "#FF4B4B", "BEKLE": "#FFD700"}.get(
            sinyal_str, "#FAFAFA"
        )
        st.markdown(f"""
        <div class="tilki-card">
            <h3 style="color: {sinyal_renk};">{sinyal_str} — Güven: {guven}/100</h3>
            <hr style="border-color: #2D3748;">
        """, unsafe_allow_html=True)

        for neden in nedenler:
            st.markdown(f"""
            <div class="dusunce-item">
                📌 {neden}
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Fibonacci seviyeleri tablosu
    if gunluk_analiz and gunluk_analiz.get("fib"):
        st.subheader("📐 Fibonacci Seviyeleri")
        fib = gunluk_analiz["fib"]
        fib_df = pd.DataFrame([
            {"Seviye": f"Fib {k}", "Fiyat (USD)": f"${v:,.4f}",
             "Mesafe %": f"{((fiyat - v) / v * 100):+.1f}%" if v > 0 else "N/A"}
            for k, v in fib.items()
        ])
        st.dataframe(fib_df, use_container_width=True, hide_index=True)

    # CoinGecko detayları
    if cg_veri:
        st.subheader("🌐 Market Verileri")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Piyasa Değeri", format_usd(cg_veri.get("piyasa_degeri_usd", 0)))
        with col2:
            st.metric("24s Hacim", format_usd(cg_veri.get("hacim_24h_usd", 0)))
        with col3:
            st.metric("7 Günlük %", f"{cg_veri.get('degisim_7g', 0):+.2f}%")
        with col4:
            st.metric("30 Günlük %", f"{cg_veri.get('degisim_30g', 0):+.2f}%")


# ============================================================
# SAYFA 4: İŞLEM GEÇMİŞİ
# ============================================================

def sayfa_islem_gecmisi() -> None:
    st.title("📊 TİLKİ — İşlem Geçmişi")

    kapali = kapali_pozisyonlari_getir(200)
    istatistikler = istatistikleri_hesapla()

    # Özet metrikler
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Toplam İşlem", istatistikler.get("toplam_islem", 0))
    with col2:
        kz_orani = istatistikler.get("kazanma_orani", 0)
        st.metric("Kazanma Oranı", f"{kz_orani:.1f}%")
    with col3:
        toplam_kz = istatistikler.get("toplam_kar_zarar_usd", 0)
        st.metric("Toplam K/Z", format_usd(toplam_kz),
                  delta_color="normal")
    with col4:
        st.metric("En İyi İşlem", f"{istatistikler.get('en_iyi_yuzde', 0):+.1f}%")
    with col5:
        st.metric("En Kötü İşlem", f"{istatistikler.get('en_kotu_yuzde', 0):+.1f}%")

    st.divider()

    col_sol, col_sag = st.columns([2, 1])

    with col_sol:
        # K/Z grafiği
        kz_fig = kar_zarar_grafigi(kapali)
        if kz_fig:
            st.plotly_chart(kz_fig, use_container_width=True)

    with col_sag:
        # Win/Loss pasta
        pasta_fig = kazanan_kaybeden_pasta(istatistikler)
        if pasta_fig:
            st.plotly_chart(pasta_fig, use_container_width=True)
        else:
            st.info("Win/Loss grafiği için işlem bekleniyor")

    # İşlem tablosu
    st.subheader("📋 İşlem Listesi")
    if kapali:
        df_kapali = pd.DataFrame(kapali)
        df_kapali["zaman"] = pd.to_datetime(df_kapali["kapanis_zamani"]).dt.strftime("%Y-%m-%d %H:%M")
        df_kapali["kar_zarar_renkli"] = df_kapali["kar_zarar_yuzde"].apply(
            lambda x: f"{'▲' if x >= 0 else '▼'} {x:+.2f}%"
        )

        gosterilecek = df_kapali[[
            "zaman", "sembol", "giris_fiyati", "cikis_fiyati",
            "kar_zarar_usd", "kar_zarar_yuzde", "kapanis_nedeni",
        ]].copy()
        gosterilecek.columns = ["Tarih", "Sembol", "Giriş $", "Çıkış $", "K/Z $", "K/Z %", "Neden"]

        st.dataframe(
            gosterilecek,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Henüz kapatılmış pozisyon bulunmuyor.")

    # Son açık işlemler
    st.subheader("🔓 Açık İşlemler")
    acik = son_islemleri_getir(50)
    acik_islemler = [i for i in acik if i.get("durum") == "ACIK"]

    if acik_islemler:
        df_acik = pd.DataFrame(acik_islemler)
        gosterilecek = df_acik[["zaman", "sembol", "islem_turu", "fiyat_usd", "toplam_usd", "guven_skoru"]].copy()
        gosterilecek.columns = ["Tarih", "Sembol", "Tür", "Fiyat $", "Tutar $", "Güven"]
        st.dataframe(gosterilecek, use_container_width=True, hide_index=True)
    else:
        st.info("Şu an açık işlem yok.")


# ============================================================
# SAYFA 5: TİLKİ DÜŞÜNÜYOR
# ============================================================

def sayfa_dusunce_logu(durum: Dict[str, Any]) -> None:
    st.title("🧠 TİLKİ — Tilki Düşünüyor")

    loglar = dusunce_loglarini_getir(100)

    # Piyasa rejimi kartı
    rejim = durum.get("piyasa_rejimi", "BELIRSIZ")
    rejim_aciklama = durum.get("rejim_aciklama", "")
    fg_deger = durum.get("fg_deger", 50)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="tilki-card">
            <h4 style="color: #FF8C00;">🌡️ Piyasa Rejimi</h4>
            <h2>{rejim}</h2>
            <p style="color: #8B9BB4; font-size: 13px;">{rejim_aciklama}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        sinif = fg_renk_sinifi(fg_deger)
        renk = fg_renk(fg_deger)
        st.markdown(f"""
        <div class="tilki-card">
            <h4 style="color: #FF8C00;">😱 Fear & Greed</h4>
            <h2 style="color: {renk};">{fg_deger} — {sinif}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        sinyaller = durum.get("sinyaller", {})
        al_sayisi = sum(1 for s in sinyaller.values() if s.get("sinyal") == "AL")
        sat_sayisi = sum(1 for s in sinyaller.values() if s.get("sinyal") == "SAT")
        st.markdown(f"""
        <div class="tilki-card">
            <h4 style="color: #FF8C00;">📊 Sinyal Özeti</h4>
            <p>🟢 AL: <b style="color: #00C896;">{al_sayisi}</b></p>
            <p>🔴 SAT: <b style="color: #FF4B4B;">{sat_sayisi}</b></p>
            <p>🟡 BEKLE: <b style="color: #FFD700;">{len(KRIPTO_SEMBOLLER) - al_sayisi - sat_sayisi}</b></p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Güven skoru dağılımı
    if sinyaller:
        st.subheader("📈 Güven Skoru Dağılımı")
        guven_verileri = [
            {"sembol": s.replace("-USD", ""), "guven": v.get("guven", 0), "sinyal": v.get("sinyal", "BEKLE")}
            for s, v in sinyaller.items()
        ]
        guven_df = pd.DataFrame(guven_verileri).sort_values("guven", ascending=False)

        renk_map = {"AL": RENK_TEMA["success"], "SAT": RENK_TEMA["danger"], "BEKLE": RENK_TEMA["warning"]}
        bar_renkler = [renk_map.get(s, RENK_TEMA["subtext"]) for s in guven_df["sinyal"]]

        fig = go.Figure(go.Bar(
            x=guven_df["sembol"],
            y=guven_df["guven"],
            marker_color=bar_renkler,
            text=guven_df["sinyal"],
            textposition="auto",
        ))
        fig.update_layout(
            paper_bgcolor="#0E1117",
            plot_bgcolor="#0E1117",
            font=dict(color=RENK_TEMA["text"]),
            height=300,
            margin=dict(l=20, r=20, t=20, b=60),
            yaxis=dict(gridcolor="#1E2130", range=[0, 100]),
            xaxis=dict(gridcolor="#1E2130"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Düşünce logları
    st.subheader("💬 Karar Logu")

    # Öncelik filtresi
    filtre = st.selectbox("Öncelik Filtresi", ["Tümü", "KRİTİK", "YUKSEK", "NORMAL"])

    for log in loglar:
        oncelik = log.get("oncelik", "NORMAL")
        if filtre != "Tümü" and oncelik != filtre:
            continue

        sinif = "dusunce-item"
        if oncelik == "KRITIK":
            sinif += " dusunce-item-kritik"
        elif oncelik == "YUKSEK":
            sinif += " dusunce-item-yuksek"

        zaman = log.get("zaman", "")[:16]
        baslik = log.get("baslik", "")
        icerik = log.get("icerik", "").replace("\n", "<br>")
        sembol = log.get("sembol", "")
        market_rejimi = log.get("market_rejimi", "")

        meta = ""
        if sembol:
            meta += f" | <b>{sembol}</b>"
        if market_rejimi:
            meta += f" | Rejim: {market_rejimi}"

        st.markdown(f"""
        <div class="{sinif}">
            <b style="color: #FF8C00;">{baslik}</b>
            <span style="color: #8B9BB4; font-size: 11px; float: right;">{zaman}{meta}</span><br>
            <span style="font-size: 13px; color: #CCCDD1;">{icerik}</span>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# ANA DASHBOARD AKIŞI
# ============================================================

def main() -> None:
    # DB tablolarını oluştur
    tablolari_olustur()

    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 10px;">
            <h1 style="color: #FF8C00; font-size: 32px;">🦊 TİLKİ</h1>
            <p style="color: #8B9BB4; font-size: 14px;">Kripto Simülasyon Ajanı</p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        sayfa = st.radio(
            "Sayfa",
            [
                "🦊 Genel Bakış",
                "📡 Piyasa Tarayıcı",
                "🔍 Coin Analizi",
                "📊 İşlem Geçmişi",
                "🧠 Tilki Düşünüyor",
            ],
            label_visibility="collapsed",
        )

        st.divider()

        # Manuel yenileme
        if st.button("🔄 Yenile", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        # Otomatik yenileme
        auto_yenile = st.checkbox("⏰ Otomatik Yenile", value=False)
        if auto_yenile:
            yenileme_suresi = st.slider("Yenileme (s)", 15, 300, YENILEME_SURESI)
            st.info(f"Her {yenileme_suresi} saniyede yenileniyor")
            time.sleep(yenileme_suresi)
            st.rerun()

        st.divider()

        # Durum
        st.markdown(f"""
        <div style="color: #8B9BB4; font-size: 12px;">
            <p>📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p>🪙 {len(KRIPTO_SEMBOLLER)} sembol takip ediliyor</p>
            <p>💰 Başlangıç: ${BASLANGIC_SERMAYE_USD:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)

    # Veri yükleme (spinner ile)
    veri_yukleme_gerekli = sayfa in [
        "🦊 Genel Bakış", "📡 Piyasa Tarayıcı",
        "🔍 Coin Analizi", "🧠 Tilki Düşünüyor",
    ]

    durum: Dict[str, Any] = {}

    if veri_yukleme_gerekli:
        with st.spinner("🦊 Tilki verileri analiz ediyor..."):
            try:
                zaman_anahtar = datetime.now().strftime("%Y-%m-%d-%H-%M")
                # Her sayfada tam analiz yap (cache'li)
                from tilki_data import tam_veri_paketi_cek
                from tilki_strategy import teknik_analiz_yap, piyasa_rejimi_tespit, tum_sinyalleri_uret

                @st.cache_data(ttl=YENILEME_SURESI)
                def tam_analiz_cache(anahtar: str) -> Dict[str, Any]:
                    veri_paketi = tam_veri_paketi_cek()
                    fg = veri_paketi.get("fear_greed")
                    fg_deger = fg["deger"] if fg else 50

                    btc_df = veri_paketi.get("gunluk_veriler", {}).get("BTC-USD")
                    btc_analiz = teknik_analiz_yap(btc_df, "BTC-USD") if btc_df is not None else None
                    piyasa_rejimi, rejim_aciklama = piyasa_rejimi_tespit(btc_analiz, fg_deger)

                    sinyaller, analizler = tum_sinyalleri_uret(
                        gunluk_veriler=veri_paketi.get("gunluk_veriler", {}),
                        saatlik_veriler=veri_paketi.get("saatlik_veriler", {}),
                        fear_greed_deger=fg_deger,
                        piyasa_rejimi=piyasa_rejimi,
                        coingecko_market=veri_paketi.get("coingecko_market", {}),
                    )

                    return {
                        "sinyaller": sinyaller,
                        "analizler": analizler,
                        "veri_paketi": veri_paketi,
                        "piyasa_rejimi": piyasa_rejimi,
                        "rejim_aciklama": rejim_aciklama,
                        "fg_deger": fg_deger,
                    }

                durum = tam_analiz_cache(zaman_anahtar)

            except Exception as e:
                st.error(f"Veri yükleme hatası: {e}")
                st.info("Veritabanındaki son veriler kullanılıyor...")
                durum = {
                    "sinyaller": {},
                    "analizler": {},
                    "veri_paketi": {},
                    "piyasa_rejimi": "BELIRSIZ",
                    "rejim_aciklama": "Veri yüklenemedi",
                    "fg_deger": 50,
                }

    # Sayfa render
    if sayfa == "🦊 Genel Bakış":
        sayfa_genel_bakis(durum)
    elif sayfa == "📡 Piyasa Tarayıcı":
        sayfa_piyasa_tarayici(durum)
    elif sayfa == "🔍 Coin Analizi":
        sayfa_coin_analizi(durum)
    elif sayfa == "📊 İşlem Geçmişi":
        sayfa_islem_gecmisi()
    elif sayfa == "🧠 Tilki Düşünüyor":
        sayfa_dusunce_logu(durum)

    # Footer
    st.markdown("""
    <div class="tilki-footer">
        🦊 TİLKİ Kripto Ajanı — Paper Trading Simülasyonu — Gerçek Para Tavsiyesi Değildir
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
