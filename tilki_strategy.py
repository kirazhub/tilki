"""
Tilki Kripto Ajanı - Teknik Analiz ve Karar Motoru
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Any, Tuple

try:
    import ta
    TA_MEVCUT = True
except ImportError:
    TA_MEVCUT = False
    logging.warning("'ta' kütüphanesi bulunamadı. Manuel hesaplama kullanılacak.")

from tilki_config import (
    RSI_PERIYOT_UZUN, RSI_PERIYOT_KISA, MACD_HIZLI, MACD_YAVAS, MACD_SINYAL,
    BB_PERIYOT, BB_STD, ATR_PERIYOT, STOCH_RSI_PERIYOT,
    MA_PERIYOTLAR, HACIM_MA_PERIYOT, OBV_MA_PERIYOT,
    RSI_ASIRI_SATIM, RSI_ASIRI_ALIM, RSI_KUVVETLI_SATIM, RSI_KUVVETLI_ALIM,
    MIN_GUVEN_SKORU,
)

logger = logging.getLogger("tilki.strategy")


# ============================================================
# YARDIMCI HESAPLAMA FONKSİYONLARI
# ============================================================

def _rsi_hesapla(seri: pd.Series, period: int = 14) -> pd.Series:
    """RSI hesaplar."""
    delta = seri.diff()
    kazanc = delta.clip(lower=0)
    kayip = -delta.clip(upper=0)
    avg_kazanc = kazanc.ewm(com=period - 1, min_periods=period).mean()
    avg_kayip = kayip.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_kazanc / avg_kayip.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _macd_hesapla(seri: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD, sinyal ve histogram döndürür."""
    ema_fast = seri.ewm(span=fast, adjust=False).mean()
    ema_slow = seri.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _bb_hesapla(seri: pd.Series, period: int = 20, std: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands: (orta, üst, alt)"""
    orta = seri.rolling(window=period).mean()
    std_dev = seri.rolling(window=period).std()
    ust = orta + std * std_dev
    alt = orta - std * std_dev
    return orta, ust, alt


def _atr_hesapla(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range hesaplar."""
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def _obv_hesapla(df: pd.DataFrame) -> pd.Series:
    """On Balance Volume hesaplar."""
    obv = pd.Series(index=df.index, dtype=float)
    obv.iloc[0] = df["volume"].iloc[0]
    for i in range(1, len(df)):
        if df["close"].iloc[i] > df["close"].iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] + df["volume"].iloc[i]
        elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] - df["volume"].iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i - 1]
    return obv


def _stoch_rsi_hesapla(rsi: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series]:
    """Stochastic RSI (%K ve %D) hesaplar."""
    min_rsi = rsi.rolling(window=period).min()
    max_rsi = rsi.rolling(window=period).max()
    diff = max_rsi - min_rsi
    k = 100 * (rsi - min_rsi) / diff.replace(0, np.nan)
    d = k.rolling(window=3).mean()
    return k, d


def _fibonacci_seviyeleri(yuksek: float, dusuk: float) -> Dict[str, float]:
    """Fibonacci retracement seviyelerini hesaplar."""
    fark = yuksek - dusuk
    return {
        "0.0": dusuk,
        "0.236": dusuk + fark * 0.236,
        "0.382": dusuk + fark * 0.382,
        "0.5": dusuk + fark * 0.5,
        "0.618": dusuk + fark * 0.618,
        "0.786": dusuk + fark * 0.786,
        "1.0": yuksek,
    }


# ============================================================
# ANA ANALİZ FONKSİYONU
# ============================================================

def teknik_analiz_yap(df: pd.DataFrame, sembol: str = "") -> Optional[Dict[str, Any]]:
    """
    Kapsamlı teknik analiz yapar.
    Döndürür: tüm indikatörler + son değerler
    """
    if df is None or len(df) < 50:
        logger.warning(f"Yetersiz veri ({sembol}): {len(df) if df is not None else 0} satır")
        return None

    try:
        df = df.copy()
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        # RSI
        df["rsi_14"] = _rsi_hesapla(close, RSI_PERIYOT_UZUN)
        df["rsi_7"] = _rsi_hesapla(close, RSI_PERIYOT_KISA)

        # MACD
        df["macd"], df["macd_sinyal"], df["macd_hist"] = _macd_hesapla(
            close, MACD_HIZLI, MACD_YAVAS, MACD_SINYAL
        )

        # Bollinger Bands
        df["bb_orta"], df["bb_ust"], df["bb_alt"] = _bb_hesapla(close, BB_PERIYOT, BB_STD)
        bb_genislik = (df["bb_ust"] - df["bb_alt"]) / df["bb_orta"].replace(0, np.nan)
        df["bb_genislik"] = bb_genislik
        df["bb_pozisyon"] = (close - df["bb_alt"]) / (df["bb_ust"] - df["bb_alt"]).replace(0, np.nan)

        # Hareketli Ortalamalar
        for ma in MA_PERIYOTLAR:
            df[f"ma_{ma}"] = close.rolling(window=ma).mean()
        df["hacim_ma"] = volume.rolling(window=HACIM_MA_PERIYOT).mean()

        # ATR
        df["atr"] = _atr_hesapla(df, ATR_PERIYOT)

        # OBV
        df["obv"] = _obv_hesapla(df)
        df["obv_ma"] = df["obv"].rolling(window=OBV_MA_PERIYOT).mean()

        # Stochastic RSI
        df["stoch_k"], df["stoch_d"] = _stoch_rsi_hesapla(df["rsi_14"], STOCH_RSI_PERIYOT)

        # Fibonacci (son 90 günlük yüksek/düşük)
        lookback = min(90, len(df))
        fib_high = high.iloc[-lookback:].max()
        fib_low = low.iloc[-lookback:].min()
        df["fib_seviyeleri"] = None  # dict olarak son satırda tutulacak
        fib_dict = _fibonacci_seviyeleri(float(fib_high), float(fib_low))

        # Momentum (ROC)
        df["roc_10"] = close.pct_change(periods=10) * 100
        df["roc_20"] = close.pct_change(periods=20) * 100

        # EMA'lar
        df["ema_9"] = close.ewm(span=9, adjust=False).mean()
        df["ema_21"] = close.ewm(span=21, adjust=False).mean()

        # Son satır değerleri
        son = df.iloc[-1]
        son_2 = df.iloc[-2] if len(df) >= 2 else son

        sonuclar = {
            "df": df,
            "fib": fib_dict,
            "son": {
                "fiyat": float(son["close"]),
                "hacim": float(son["volume"]),
                # RSI
                "rsi_14": safe_float(son.get("rsi_14")),
                "rsi_7": safe_float(son.get("rsi_7")),
                # MACD
                "macd": safe_float(son.get("macd")),
                "macd_sinyal": safe_float(son.get("macd_sinyal")),
                "macd_hist": safe_float(son.get("macd_hist")),
                "macd_hist_onceki": safe_float(son_2.get("macd_hist")),
                # BB
                "bb_ust": safe_float(son.get("bb_ust")),
                "bb_alt": safe_float(son.get("bb_alt")),
                "bb_orta": safe_float(son.get("bb_orta")),
                "bb_pozisyon": safe_float(son.get("bb_pozisyon")),
                "bb_genislik": safe_float(son.get("bb_genislik")),
                # MA'lar
                "ma_7": safe_float(son.get("ma_7")),
                "ma_20": safe_float(son.get("ma_20")),
                "ma_50": safe_float(son.get("ma_50")),
                "ma_100": safe_float(son.get("ma_100")),
                "ma_200": safe_float(son.get("ma_200")),
                "ema_9": safe_float(son.get("ema_9")),
                "ema_21": safe_float(son.get("ema_21")),
                # ATR
                "atr": safe_float(son.get("atr")),
                "atr_yuzde": safe_float(son.get("atr")) / float(son["close"]) * 100 if son["close"] > 0 else 0,
                # OBV
                "obv": safe_float(son.get("obv")),
                "obv_ma": safe_float(son.get("obv_ma")),
                # Stoch RSI
                "stoch_k": safe_float(son.get("stoch_k")),
                "stoch_d": safe_float(son.get("stoch_d")),
                # Momentum
                "roc_10": safe_float(son.get("roc_10")),
                "roc_20": safe_float(son.get("roc_20")),
                # Hacim
                "hacim_ma": safe_float(son.get("hacim_ma")),
                "hacim_oran": float(son["volume"]) / max(safe_float(son.get("hacim_ma"), 1), 1),
            },
        }

        return sonuclar

    except Exception as e:
        logger.error(f"Teknik analiz hatası ({sembol}): {e}", exc_info=True)
        return None


def safe_float(val: Any, default: float = 0.0) -> float:
    """None veya NaN güvenli float dönüşümü."""
    try:
        if val is None:
            return default
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


# ============================================================
# PİYASA REJİMİ TESPİTİ
# ============================================================

def piyasa_rejimi_tespit(
    btc_analiz: Optional[Dict[str, Any]],
    fear_greed_deger: int = 50,
) -> Tuple[str, str]:
    """
    Piyasa rejimini tespit eder.
    Döndürür: (rejim_kodu, rejim_aciklamasi)
    """
    if btc_analiz is None:
        return "BELIRSIZ", "BTC verisi yok, rejim tespit edilemedi"

    son = btc_analiz.get("son", {})
    fiyat = son.get("fiyat", 0)
    ma_50 = son.get("ma_50", 0)
    ma_200 = son.get("ma_200", 0)
    rsi = son.get("rsi_14", 50)
    macd_hist = son.get("macd_hist", 0)

    aciklamalar = []

    # Altın çapraz / Ölüm çaprazı
    if ma_50 > 0 and ma_200 > 0:
        if fiyat > ma_50 > ma_200:
            aciklamalar.append("BTC altın çaprazda (MA50 > MA200)")
            btc_trend = "GUCLU_YUKARI"
        elif fiyat > ma_200:
            aciklamalar.append("BTC MA200 üzerinde")
            btc_trend = "YUKARI"
        elif fiyat < ma_50 < ma_200:
            aciklamalar.append("BTC ölüm çaprazında (MA50 < MA200)")
            btc_trend = "GUCLU_ASAGI"
        elif fiyat < ma_200:
            aciklamalar.append("BTC MA200 altında")
            btc_trend = "ASAGI"
        else:
            btc_trend = "YATAY"
            aciklamalar.append("BTC MA'lar arası sıkışmış")
    else:
        btc_trend = "BELIRSIZ"

    # Fear & Greed yorumu
    if fear_greed_deger >= 75:
        duygu = "ASIRI_AÇGOZLULUK"
        aciklamalar.append(f"Aşırı açgözlülük (F&G: {fear_greed_deger})")
    elif fear_greed_deger >= 55:
        duygu = "AÇGOZLULUK"
        aciklamalar.append(f"Açgözlülük bölgesi (F&G: {fear_greed_deger})")
    elif fear_greed_deger >= 45:
        duygu = "NOTRAL"
        aciklamalar.append(f"Nötr piyasa (F&G: {fear_greed_deger})")
    elif fear_greed_deger >= 25:
        duygu = "KORKU"
        aciklamalar.append(f"Korku bölgesi (F&G: {fear_greed_deger})")
    else:
        duygu = "ASIRI_KORKU"
        aciklamalar.append(f"Aşırı korku (F&G: {fear_greed_deger}) - Alım fırsatı!")

    # Rejim kararı
    if btc_trend in ["GUCLU_YUKARI"] and duygu in ["AÇGOZLULUK", "ASIRI_AÇGOZLULUK"]:
        rejim = "BOGA_KUVVETLI"
    elif btc_trend in ["YUKARI", "GUCLU_YUKARI"] and duygu in ["NOTRAL", "AÇGOZLULUK"]:
        rejim = "BOGA_ZAYIF"
    elif btc_trend in ["GUCLU_ASAGI"] and duygu in ["KORKU", "ASIRI_KORKU"]:
        rejim = "AYI_KUVVETLI"
    elif btc_trend in ["ASAGI"] or duygu in ["KORKU", "ASIRI_KORKU"]:
        rejim = "AYI_ZAYIF"
    else:
        rejim = "SIDEWAYS"

    aciklama = " | ".join(aciklamalar)
    return rejim, aciklama


# ============================================================
# SİNYAL ÜRETİMİ
# ============================================================

def sinyal_uret(
    sembol: str,
    gunluk_analiz: Optional[Dict[str, Any]],
    saatlik_analiz: Optional[Dict[str, Any]],
    fear_greed: int = 50,
    piyasa_rejimi: str = "SIDEWAYS",
    coingecko_veri: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Çok zaman dilimli sinyal üretir.
    Döndürür: {sinyal, guven, puan_detay, neden, stop_loss, take_profit}
    """
    sonuc: Dict[str, Any] = {
        "sembol": sembol,
        "sinyal": "BEKLE",
        "guven": 0,
        "puan_detay": {},
        "neden": [],
        "stop_loss_yuzde": -0.07,
        "take_profit_yuzde": 0.15,
        "fiyat": 0.0,
    }

    if gunluk_analiz is None:
        sonuc["neden"].append("Günlük veri yok")
        return sonuc

    g = gunluk_analiz.get("son", {})
    fiyat = g.get("fiyat", 0)
    sonuc["fiyat"] = fiyat

    puanlar: Dict[str, int] = {}  # pozitif = AL, negatif = SAT
    aciklamalar: List[str] = []

    # ---- 1. RSI ANALİZİ ----
    rsi = g.get("rsi_14", 50)
    rsi_7 = g.get("rsi_7", 50)

    if rsi < RSI_KUVVETLI_ALIM:
        puanlar["rsi"] = 25
        aciklamalar.append(f"RSI(14)={rsi:.1f} AŞIRI SATIM (kuvvetli AL)")
    elif rsi < RSI_ASIRI_SATIM:
        puanlar["rsi"] = 15
        aciklamalar.append(f"RSI(14)={rsi:.1f} aşırı satım bölgesi")
    elif rsi > RSI_KUVVETLI_SATIM:
        puanlar["rsi"] = -25
        aciklamalar.append(f"RSI(14)={rsi:.1f} AŞIRI ALIM (kuvvetli SAT)")
    elif rsi > RSI_ASIRI_ALIM:
        puanlar["rsi"] = -15
        aciklamalar.append(f"RSI(14)={rsi:.1f} aşırı alım bölgesi")
    else:
        puanlar["rsi"] = 5 if rsi < 50 else -5
        aciklamalar.append(f"RSI(14)={rsi:.1f} nötr")

    # RSI 7 teyidi
    if rsi_7 < 25 and rsi < 30:
        puanlar["rsi_7"] = 10
        aciklamalar.append(f"RSI(7)={rsi_7:.1f} kısa vadeli aşırı satım teyidi")
    elif rsi_7 > 75 and rsi > 70:
        puanlar["rsi_7"] = -10
        aciklamalar.append(f"RSI(7)={rsi_7:.1f} kısa vadeli aşırı alım teyidi")
    else:
        puanlar["rsi_7"] = 0

    # ---- 2. MACD ANALİZİ ----
    macd = g.get("macd", 0)
    macd_sig = g.get("macd_sinyal", 0)
    macd_hist = g.get("macd_hist", 0)
    macd_hist_onceki = g.get("macd_hist_onceki", 0)

    if macd > macd_sig and macd_hist > 0:
        if macd_hist > macd_hist_onceki:  # güçleniyor
            puanlar["macd"] = 20
            aciklamalar.append("MACD pozitif ve güçleniyor (AL)")
        else:
            puanlar["macd"] = 10
            aciklamalar.append("MACD pozitif bölgede")
    elif macd < macd_sig and macd_hist < 0:
        if macd_hist < macd_hist_onceki:  # zayıflıyor
            puanlar["macd"] = -20
            aciklamalar.append("MACD negatif ve zayıflıyor (SAT)")
        else:
            puanlar["macd"] = -10
            aciklamalar.append("MACD negatif bölgede")
    else:
        puanlar["macd"] = 0
        aciklamalar.append("MACD kesişim bölgesinde")

    # ---- 3. BOLLINGER BANDS ----
    bb_pos = g.get("bb_pozisyon", 0.5)
    bb_gen = g.get("bb_genislik", 0)

    if bb_pos is not None:
        if bb_pos < 0.1:
            puanlar["bb"] = 20
            aciklamalar.append(f"Fiyat alt BB'ye yakın ({bb_pos:.2f}) - dönüş sinyali")
        elif bb_pos < 0.25:
            puanlar["bb"] = 10
            aciklamalar.append(f"Fiyat alt BB bölgesinde ({bb_pos:.2f})")
        elif bb_pos > 0.9:
            puanlar["bb"] = -20
            aciklamalar.append(f"Fiyat üst BB'ye yakın ({bb_pos:.2f}) - aşırı alım")
        elif bb_pos > 0.75:
            puanlar["bb"] = -10
            aciklamalar.append(f"Fiyat üst BB bölgesinde ({bb_pos:.2f})")
        else:
            puanlar["bb"] = 0
            aciklamalar.append(f"Fiyat BB ortasında ({bb_pos:.2f})")

    # ---- 4. HAREKETLİ ORTALAMALAR ----
    ma_puan = 0
    ma_acik = []

    if fiyat > 0:
        for ma_period in [7, 20, 50]:
            ma_val = g.get(f"ma_{ma_period}", 0)
            if ma_val and ma_val > 0:
                if fiyat > ma_val:
                    ma_puan += 3
                    ma_acik.append(f"MA{ma_period} üstünde")
                else:
                    ma_puan -= 3
                    ma_acik.append(f"MA{ma_period} altında")

        ma_200 = g.get("ma_200", 0)
        if ma_200 and ma_200 > 0:
            if fiyat > ma_200:
                ma_puan += 8
                ma_acik.append("MA200 üstünde (boğa piyasası)")
            else:
                ma_puan -= 8
                ma_acik.append("MA200 altında (ayı piyasası)")

    puanlar["ma"] = ma_puan
    if ma_acik:
        aciklamalar.append(", ".join(ma_acik))

    # ---- 5. STOCHASTIC RSI ----
    stoch_k = g.get("stoch_k", 50)
    stoch_d = g.get("stoch_d", 50)

    if stoch_k is not None and stoch_d is not None:
        if stoch_k < 20 and stoch_d < 20:
            puanlar["stoch"] = 15
            aciklamalar.append(f"Stoch RSI aşırı satım ({stoch_k:.0f}/{stoch_d:.0f})")
        elif stoch_k > 80 and stoch_d > 80:
            puanlar["stoch"] = -15
            aciklamalar.append(f"Stoch RSI aşırı alım ({stoch_k:.0f}/{stoch_d:.0f})")
        elif stoch_k > stoch_d and stoch_k < 50:
            puanlar["stoch"] = 8
            aciklamalar.append("Stoch RSI yükseliş kesişimi")
        elif stoch_k < stoch_d and stoch_k > 50:
            puanlar["stoch"] = -8
            aciklamalar.append("Stoch RSI düşüş kesişimi")
        else:
            puanlar["stoch"] = 0

    # ---- 6. OBV (HACIM TEYIDI) ----
    obv = g.get("obv", 0)
    obv_ma = g.get("obv_ma", 0)

    if obv and obv_ma and obv_ma != 0:
        if obv > obv_ma:
            puanlar["obv"] = 10
            aciklamalar.append("OBV MA üstünde (güçlü hacim desteği)")
        else:
            puanlar["obv"] = -10
            aciklamalar.append("OBV MA altında (hacim zayıf)")

    # ---- 7. HACIM ANALİZİ ----
    hacim_oran = g.get("hacim_oran", 1.0)
    if hacim_oran > 2.0:
        # Güçlü hacim var, yönü teyid et
        mevcut_puan = sum(puanlar.values())
        if mevcut_puan > 0:
            puanlar["hacim"] = 15
            aciklamalar.append(f"Hacim {hacim_oran:.1f}x ortalama - AL sinyali güçlü")
        elif mevcut_puan < 0:
            puanlar["hacim"] = -15
            aciklamalar.append(f"Hacim {hacim_oran:.1f}x ortalama - SAT sinyali güçlü")
    elif hacim_oran > 1.5:
        puanlar["hacim"] = 5
        aciklamalar.append(f"Hacim normalin üstünde ({hacim_oran:.1f}x)")
    else:
        puanlar["hacim"] = 0

    # ---- 8. SAATLIK ONAY ----
    if saatlik_analiz is not None:
        s = saatlik_analiz.get("son", {})
        s_rsi = s.get("rsi_14", 50)
        s_macd_hist = s.get("macd_hist", 0)

        gunden_oy = sum(puanlar.values())
        saatlik_puan = 0

        if gunden_oy > 0:  # Günlük AL sinyali
            if s_rsi < 50 and s_macd_hist > 0:
                saatlik_puan = 15
                aciklamalar.append("Saatlik grafik günlük AL sinyalini teyid ediyor")
            elif s_rsi > 65:
                saatlik_puan = -10
                aciklamalar.append("Uyarı: Saatlik RSI yüksek, acele etme")
        elif gunden_oy < 0:  # Günlük SAT sinyali
            if s_rsi > 50 and s_macd_hist < 0:
                saatlik_puan = -15
                aciklamalar.append("Saatlik grafik günlük SAT sinyalini teyid ediyor")

        puanlar["saatlik"] = saatlik_puan

    # ---- 9. FEAR & GREED ETKİSİ ----
    fg_puan = 0
    if fear_greed < 20:
        fg_puan = 20
        aciklamalar.append(f"Aşırı korku (F&G:{fear_greed}) = Alım fırsatı")
    elif fear_greed < 35:
        fg_puan = 10
        aciklamalar.append(f"Korku bölgesi (F&G:{fear_greed})")
    elif fear_greed > 80:
        fg_puan = -20
        aciklamalar.append(f"Aşırı açgözlülük (F&G:{fear_greed}) = Sat/dikkat")
    elif fear_greed > 65:
        fg_puan = -10
        aciklamalar.append(f"Açgözlülük bölgesi (F&G:{fear_greed})")
    puanlar["fear_greed"] = fg_puan

    # ---- 10. PİYASA REJİMİ AYARLAMASI ----
    rejim_carp = 1.0
    if piyasa_rejimi == "BOGA_KUVVETLI":
        rejim_carp = 1.3
        aciklamalar.append("Boğa piyasası: AL sinyalleri güçlendirildi")
    elif piyasa_rejimi == "AYI_KUVVETLI":
        rejim_carp = 0.6
        aciklamalar.append("Ayı piyasası: Dikkatli ol, SAT ağırlıklı")
    elif piyasa_rejimi == "AYI_ZAYIF":
        rejim_carp = 0.8

    # ---- TOPLAM PUAN VE KARAR ----
    toplam = sum(puanlar.values())
    normalize = min(100, max(-100, toplam))
    normalize_rejim = int(normalize * rejim_carp)
    normalize_rejim = min(100, max(-100, normalize_rejim))

    # Güven skoru (0-100)
    guven = abs(normalize_rejim)

    if normalize_rejim >= 15 and guven >= MIN_GUVEN_SKORU:
        sinyal = "AL"
    elif normalize_rejim <= -15 and guven >= MIN_GUVEN_SKORU:
        sinyal = "SAT"
    else:
        sinyal = "BEKLE"

    # ATR bazlı stop-loss/take-profit
    atr = g.get("atr", 0)
    if atr and fiyat > 0:
        atr_yuzde = atr / fiyat
        stop_loss = max(-0.12, min(-0.03, -atr_yuzde * 2.0))
        take_profit = min(0.25, max(0.08, atr_yuzde * 3.5))
    else:
        stop_loss = -0.07
        take_profit = 0.15

    sonuc.update({
        "sinyal": sinyal,
        "guven": guven,
        "ham_puan": normalize_rejim,
        "puan_detay": puanlar,
        "neden": aciklamalar,
        "stop_loss_yuzde": round(stop_loss, 4),
        "take_profit_yuzde": round(take_profit, 4),
        "fiyat": fiyat,
        "rsi": rsi,
        "macd_hist": g.get("macd_hist", 0),
        "bb_pozisyon": g.get("bb_pozisyon", 0.5),
    })

    return sonuc


def tum_sinyalleri_uret(
    gunluk_veriler: Dict[str, Any],
    saatlik_veriler: Dict[str, Any],
    fear_greed_deger: int = 50,
    piyasa_rejimi: str = "SIDEWAYS",
    coingecko_market: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """
    Tüm semboller için teknik analiz ve sinyal üretir.
    """
    from tilki_config import KRIPTO_SEMBOLLER

    sinyaller: Dict[str, Dict[str, Any]] = {}
    analizler: Dict[str, Any] = {}

    logger.info("Teknik analiz başlıyor...")

    for sembol in KRIPTO_SEMBOLLER:
        try:
            df_gunluk = gunluk_veriler.get(sembol)
            df_saatlik = saatlik_veriler.get(sembol)

            analiz_g = teknik_analiz_yap(df_gunluk, sembol) if df_gunluk is not None else None
            analiz_s = teknik_analiz_yap(df_saatlik, sembol) if df_saatlik is not None else None

            analizler[sembol] = {"gunluk": analiz_g, "saatlik": analiz_s}

            cg_veri = coingecko_market.get(sembol) if coingecko_market else None

            sinyal = sinyal_uret(
                sembol=sembol,
                gunluk_analiz=analiz_g,
                saatlik_analiz=analiz_s,
                fear_greed=fear_greed_deger,
                piyasa_rejimi=piyasa_rejimi,
                coingecko_veri=cg_veri,
            )

            # CoinGecko verilerini ekle
            if cg_veri:
                sinyal["degisim_24h"] = cg_veri.get("degisim_24h", 0)
                sinyal["degisim_7g"] = cg_veri.get("degisim_7g", 0)
                sinyal["piyasa_degeri"] = cg_veri.get("piyasa_degeri_usd", 0)
                sinyal["hacim_24h"] = cg_veri.get("hacim_24h_usd", 0)
                sinyal["sparkline"] = cg_veri.get("sparkline", [])

            sinyaller[sembol] = sinyal

        except Exception as e:
            logger.error(f"Sinyal üretme hatası ({sembol}): {e}")
            sinyaller[sembol] = {"sembol": sembol, "sinyal": "HATA", "guven": 0, "neden": [str(e)]}

    al_sayisi = sum(1 for s in sinyaller.values() if s.get("sinyal") == "AL")
    sat_sayisi = sum(1 for s in sinyaller.values() if s.get("sinyal") == "SAT")
    bekle_sayisi = sum(1 for s in sinyaller.values() if s.get("sinyal") == "BEKLE")
    logger.info(f"Sinyal özeti: AL={al_sayisi}, SAT={sat_sayisi}, BEKLE={bekle_sayisi}")

    return sinyaller, analizler
