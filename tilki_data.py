"""
Tilki Kripto Ajanı - Veri Çekme Modülü
yfinance + CoinGecko (ücretsiz API)
"""

import time
import logging
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple

from tilki_config import (
    KRIPTO_SEMBOLLER, COINGECKO_IDS, SEMBOL_ISIMLER,
    YFINANCE_PERIOD, YFINANCE_INTERVAL_GUNLUK, YFINANCE_INTERVAL_SAATLIK,
    SAATLIK_VERI_SURE, COINGECKO_ISTEK_ARALIK,
    FEAR_GREED_URL, COINGECKO_GLOBAL_URL, COINGECKO_COINS_URL,
)

logger = logging.getLogger("tilki.data")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Tilki-Kripto-Ajani/1.0)",
    "Accept": "application/json",
}


def gunluk_veri_cek(sembol: str, period: str = YFINANCE_PERIOD) -> Optional[pd.DataFrame]:
    """yfinance ile günlük OHLCV verisi çeker (2 yıllık)."""
    try:
        ticker = yf.Ticker(sembol)
        df = ticker.history(period=period, interval=YFINANCE_INTERVAL_GUNLUK, auto_adjust=True)
        if df is None or df.empty:
            logger.warning(f"Günlük veri boş: {sembol}")
            return None
        df.index = pd.to_datetime(df.index)
        df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        logger.debug(f"Günlük veri çekildi: {sembol} ({len(df)} satır)")
        return df
    except Exception as e:
        logger.error(f"Günlük veri hatası ({sembol}): {e}")
        return None


def saatlik_veri_cek(sembol: str, period: str = SAATLIK_VERI_SURE) -> Optional[pd.DataFrame]:
    """yfinance ile saatlik OHLCV verisi çeker (60 günlük)."""
    try:
        ticker = yf.Ticker(sembol)
        df = ticker.history(period=period, interval=YFINANCE_INTERVAL_SAATLIK, auto_adjust=True)
        if df is None or df.empty:
            logger.warning(f"Saatlik veri boş: {sembol}")
            return None
        df.index = pd.to_datetime(df.index)
        df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        logger.debug(f"Saatlik veri çekildi: {sembol} ({len(df)} satır)")
        return df
    except Exception as e:
        logger.error(f"Saatlik veri hatası ({sembol}): {e}")
        return None


def tum_gunluk_verileri_cek() -> Dict[str, pd.DataFrame]:
    """Tüm sembollerin günlük verilerini çeker."""
    logger.info(f"Tüm sembollerin günlük verisi çekiliyor ({len(KRIPTO_SEMBOLLER)} sembol)...")
    sonuclar: Dict[str, pd.DataFrame] = {}

    # yfinance toplu indirme (daha hızlı)
    try:
        sembol_str = " ".join(KRIPTO_SEMBOLLER)
        df_tumu = yf.download(
            sembol_str,
            period=YFINANCE_PERIOD,
            interval=YFINANCE_INTERVAL_GUNLUK,
            auto_adjust=True,
            group_by="ticker",
            progress=False,
            threads=True,
        )

        for sembol in KRIPTO_SEMBOLLER:
            try:
                if len(KRIPTO_SEMBOLLER) == 1:
                    df = df_tumu.copy()
                else:
                    if sembol not in df_tumu.columns.get_level_values(0):
                        continue
                    df = df_tumu[sembol].copy()

                df.index = pd.to_datetime(df.index)
                df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
                df.columns = [c.lower() for c in df.columns]
                df = df[["open", "high", "low", "close", "volume"]].dropna()
                if len(df) > 10:
                    sonuclar[sembol] = df
            except Exception as e:
                logger.warning(f"Toplu veri parse hatası ({sembol}): {e}")

        logger.info(f"Toplu günlük veri tamamlandı: {len(sonuclar)}/{len(KRIPTO_SEMBOLLER)} sembol")
    except Exception as e:
        logger.error(f"Toplu indirme hatası: {e}. Tek tek çekiliyor...")
        for sembol in KRIPTO_SEMBOLLER:
            df = gunluk_veri_cek(sembol)
            if df is not None and len(df) > 10:
                sonuclar[sembol] = df
            time.sleep(0.2)

    return sonuclar


def tum_saatlik_verileri_cek() -> Dict[str, pd.DataFrame]:
    """Tüm sembollerin saatlik verilerini çeker."""
    logger.info(f"Tüm sembollerin saatlik verisi çekiliyor...")
    sonuclar: Dict[str, pd.DataFrame] = {}

    try:
        sembol_str = " ".join(KRIPTO_SEMBOLLER)
        df_tumu = yf.download(
            sembol_str,
            period=SAATLIK_VERI_SURE,
            interval=YFINANCE_INTERVAL_SAATLIK,
            auto_adjust=True,
            group_by="ticker",
            progress=False,
            threads=True,
        )

        for sembol in KRIPTO_SEMBOLLER:
            try:
                if len(KRIPTO_SEMBOLLER) == 1:
                    df = df_tumu.copy()
                else:
                    if sembol not in df_tumu.columns.get_level_values(0):
                        continue
                    df = df_tumu[sembol].copy()

                df.index = pd.to_datetime(df.index)
                df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
                df.columns = [c.lower() for c in df.columns]
                df = df[["open", "high", "low", "close", "volume"]].dropna()
                if len(df) > 10:
                    sonuclar[sembol] = df
            except Exception as e:
                logger.warning(f"Saatlik parse hatası ({sembol}): {e}")

        logger.info(f"Saatlik veri tamamlandı: {len(sonuclar)}/{len(KRIPTO_SEMBOLLER)} sembol")
    except Exception as e:
        logger.error(f"Saatlik toplu indirme hatası: {e}")
        for sembol in KRIPTO_SEMBOLLER:
            df = saatlik_veri_cek(sembol)
            if df is not None and len(df) > 10:
                sonuclar[sembol] = df
            time.sleep(0.3)

    return sonuclar


def anlık_fiyat_cek(sembol: str) -> Optional[float]:
    """Anlık fiyat çeker."""
    try:
        ticker = yf.Ticker(sembol)
        info = ticker.fast_info
        price = getattr(info, "last_price", None)
        if price is None:
            hist = ticker.history(period="1d", interval="1m")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
        return float(price) if price else None
    except Exception as e:
        logger.error(f"Anlık fiyat hatası ({sembol}): {e}")
        return None


def fear_greed_cek() -> Optional[Dict[str, Any]]:
    """Alternative.me Fear & Greed Index verisi çeker."""
    try:
        resp = requests.get(FEAR_GREED_URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if "data" not in data or len(data["data"]) == 0:
            return None

        gecmis = []
        for item in data["data"]:
            gecmis.append({
                "zaman": datetime.fromtimestamp(int(item["timestamp"])).strftime("%Y-%m-%d"),
                "deger": int(item["value"]),
                "siniflandirma": item.get("value_classification", ""),
            })

        guncel = gecmis[0]
        return {
            "deger": guncel["deger"],
            "siniflandirma": guncel["siniflandirma"],
            "zaman": guncel["zaman"],
            "gecmis": gecmis,
        }
    except Exception as e:
        logger.error(f"Fear & Greed çekme hatası: {e}")
        return None


def coingecko_global_cek() -> Optional[Dict[str, Any]]:
    """CoinGecko global piyasa verisi çeker."""
    try:
        resp = requests.get(COINGECKO_GLOBAL_URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", {})

        return {
            "toplam_piyasa_degeri_usd": data.get("total_market_cap", {}).get("usd", 0),
            "toplam_hacim_24h_usd": data.get("total_volume", {}).get("usd", 0),
            "btc_dominance": data.get("market_cap_percentage", {}).get("btc", 0),
            "eth_dominance": data.get("market_cap_percentage", {}).get("eth", 0),
            "aktif_kripto_sayisi": data.get("active_cryptocurrencies", 0),
            "piyasa_degisim_24h": data.get("market_cap_change_percentage_24h_usd", 0),
        }
    except Exception as e:
        logger.error(f"CoinGecko global hatası: {e}")
        return None


def coingecko_coin_detay_cek(coingecko_id: str) -> Optional[Dict[str, Any]]:
    """Tek coin detay verisi (piyasa değeri, hacim, vb.)"""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
        }
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        md = data.get("market_data", {})

        return {
            "piyasa_degeri_usd": md.get("market_cap", {}).get("usd", 0),
            "hacim_24h_usd": md.get("total_volume", {}).get("usd", 0),
            "degisim_24h": md.get("price_change_percentage_24h", 0),
            "degisim_7g": md.get("price_change_percentage_7d", 0),
            "degisim_30g": md.get("price_change_percentage_30d", 0),
            "ath": md.get("ath", {}).get("usd", 0),
            "atl": md.get("atl", {}).get("usd", 0),
            "dolasimdaki_arz": md.get("circulating_supply", 0),
            "toplam_arz": md.get("total_supply", 0),
        }
    except Exception as e:
        logger.error(f"CoinGecko detay hatası ({coingecko_id}): {e}")
        return None


def coingecko_markets_cek(sayfa: int = 1, adet: int = 100) -> List[Dict[str, Any]]:
    """CoinGecko markets endpoint'ten toplu coin verisi."""
    try:
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": adet,
            "page": sayfa,
            "sparkline": "true",
            "price_change_percentage": "1h,24h,7d,30d",
        }
        resp = requests.get(COINGECKO_COINS_URL, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"CoinGecko markets hatası: {e}")
        return []


def tum_coingecko_market_cek() -> Dict[str, Dict[str, Any]]:
    """Tüm takip edilen coinlerin CoinGecko verisini çeker."""
    logger.info("CoinGecko market verisi çekiliyor...")
    sonuclar: Dict[str, Dict[str, Any]] = {}

    # İlk 100 coin'i çek (tüm sembollerimiz burada)
    coins = coingecko_markets_cek(sayfa=1, adet=100)
    time.sleep(COINGECKO_ISTEK_ARALIK)

    coins2 = coingecko_markets_cek(sayfa=2, adet=100)
    time.sleep(COINGECKO_ISTEK_ARALIK)
    coins.extend(coins2)

    # ID -> sembol eşleştirmesi
    id_to_sembol = {v: k for k, v in COINGECKO_IDS.items()}

    for coin in coins:
        coin_id = coin.get("id", "")
        if coin_id in id_to_sembol:
            sembol = id_to_sembol[coin_id]
            sparkline = coin.get("sparkline_in_7d", {})
            sparkline_prices = sparkline.get("price", []) if sparkline else []

            sonuclar[sembol] = {
                "piyasa_degeri_usd": coin.get("market_cap", 0),
                "hacim_24h_usd": coin.get("total_volume", 0),
                "degisim_1s": coin.get("price_change_percentage_1h_in_currency", 0),
                "degisim_24h": coin.get("price_change_percentage_24h", 0),
                "degisim_7g": coin.get("price_change_percentage_7d_in_currency", 0),
                "degisim_30g": coin.get("price_change_percentage_30d_in_currency", 0),
                "guncel_fiyat": coin.get("current_price", 0),
                "ath": coin.get("ath", 0),
                "rank": coin.get("market_cap_rank", 999),
                "sparkline": sparkline_prices[-48:] if len(sparkline_prices) >= 48 else sparkline_prices,
            }

    logger.info(f"CoinGecko verisi tamamlandı: {len(sonuclar)} sembol")
    return sonuclar


def usd_tl_kur_cek() -> float:
    """USD/TL kurunu çeker."""
    try:
        ticker = yf.Ticker("USDTRY=X")
        hist = ticker.history(period="1d", interval="1m")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    # Yedek: sabit kur
    return 34.0


def kazananlar_kaybedenler_cek() -> Tuple[List[Dict], List[Dict]]:
    """CoinGecko'dan günlük en çok kazanan ve kaybedenler."""
    try:
        coins = coingecko_markets_cek(sayfa=1, adet=250)
        time.sleep(COINGECKO_ISTEK_ARALIK)

        kazananlar = sorted(
            [c for c in coins if c.get("price_change_percentage_24h") is not None],
            key=lambda x: x.get("price_change_percentage_24h", 0),
            reverse=True,
        )[:10]

        kaybedenler = sorted(
            [c for c in coins if c.get("price_change_percentage_24h") is not None],
            key=lambda x: x.get("price_change_percentage_24h", 0),
        )[:10]

        return kazananlar, kaybedenler
    except Exception as e:
        logger.error(f"Kazanan/kaybeden hatası: {e}")
        return [], []


def tam_veri_paketi_cek() -> Dict[str, Any]:
    """Tüm verileri tek seferde çeken master fonksiyon."""
    logger.info("🦊 Tilki tam veri paketi çekiliyor...")
    paket: Dict[str, Any] = {
        "zaman": datetime.utcnow().isoformat(),
        "gunluk_veriler": {},
        "saatlik_veriler": {},
        "coingecko_market": {},
        "coingecko_global": None,
        "fear_greed": None,
        "usd_tl_kur": 34.0,
        "kazananlar": [],
        "kaybedenler": [],
    }

    # 1. USD/TL kuru
    paket["usd_tl_kur"] = usd_tl_kur_cek()
    logger.info(f"USD/TL: {paket['usd_tl_kur']:.2f}")

    # 2. Günlük OHLCV
    paket["gunluk_veriler"] = tum_gunluk_verileri_cek()

    # 3. Saatlik OHLCV
    paket["saatlik_veriler"] = tum_saatlik_verileri_cek()

    # 4. CoinGecko global
    paket["coingecko_global"] = coingecko_global_cek()
    time.sleep(COINGECKO_ISTEK_ARALIK)

    # 5. Fear & Greed
    paket["fear_greed"] = fear_greed_cek()
    time.sleep(COINGECKO_ISTEK_ARALIK)

    # 6. CoinGecko markets
    paket["coingecko_market"] = tum_coingecko_market_cek()
    time.sleep(COINGECKO_ISTEK_ARALIK)

    # 7. Kazanan/kaybeden
    paket["kazananlar"], paket["kaybedenler"] = kazananlar_kaybedenler_cek()

    logger.info(f"✅ Tam veri paketi hazır. {len(paket['gunluk_veriler'])} günlük, "
                f"{len(paket['saatlik_veriler'])} saatlik veri seti.")
    return paket
