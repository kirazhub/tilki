"""
Tilki Kripto Ajanı - Konfigürasyon
"""

from typing import List, Dict, Any

# === KRİPTO SEMBOLLER ===
KRIPTO_SEMBOLLER: List[str] = [
    # Mega Cap
    "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD",
    # Top 10-20
    "ADA-USD", "DOGE-USD", "AVAX-USD", "MATIC-USD", "DOT-USD",
    "LINK-USD", "UNI-USD", "ATOM-USD", "LTC-USD", "BCH-USD",
    # Top 20-35
    "ALGO-USD", "XLM-USD", "VET-USD", "FIL-USD", "TRX-USD",
    "ETC-USD", "XMR-USD", "AAVE-USD", "NEAR-USD", "FTM-USD",
    # DeFi & Web3
    "SAND-USD", "MANA-USD", "AXS-USD", "GRT-USD", "CRV-USD",
    "MKR-USD", "SNX-USD", "COMP-USD", "YFI-USD", "SUSHI-USD",
    # Layer 1 & 2
    "OP-USD", "ARB-USD", "APT-USD", "SUI-USD", "SEI-USD",
    "INJ-USD", "TIA-USD", "KAVA-USD", "ONE-USD", "ZIL-USD",
    # Exchange Tokens
    "OKB-USD", "HT-USD", "CRO-USD", "GT-USD",
    # Gaming & NFT
    "IMX-USD", "ENJ-USD", "CHZ-USD", "FLOW-USD", "THETA-USD",
    # Infrastructure
    "HBAR-USD", "IOTA-USD", "EGLD-USD", "ROSE-USD", "CELO-USD",
    # Meme & Popular
    "SHIB-USD", "PEPE-USD", "FLOKI-USD",
    # Stablecoins (referans için)
    # "USDT-USD", "USDC-USD",  # Bunlar sabit, işlem yapılmaz
]

SEMBOL_ISIMLER: Dict[str, str] = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "BNB-USD": "BNB",
    "SOL-USD": "Solana",
    "XRP-USD": "XRP",
    "ADA-USD": "Cardano",
    "DOGE-USD": "Dogecoin",
    "AVAX-USD": "Avalanche",
    "MATIC-USD": "Polygon",
    "DOT-USD": "Polkadot",
    "LINK-USD": "Chainlink",
    "UNI-USD": "Uniswap",
    "ATOM-USD": "Cosmos",
    "LTC-USD": "Litecoin",
    "BCH-USD": "Bitcoin Cash",
    "ALGO-USD": "Algorand",
    "XLM-USD": "Stellar",
    "VET-USD": "VeChain",
    "FIL-USD": "Filecoin",
    "TRX-USD": "TRON",
    "ETC-USD": "Ethereum Classic",
    "THETA-USD": "Theta Network",
    "XMR-USD": "Monero",
    "EOS-USD": "EOS",
    "AAVE-USD": "Aave",
    "NEAR-USD": "NEAR Protocol",
    "FTM-USD": "Fantom",
    "SAND-USD": "The Sandbox",
    "MANA-USD": "Decentraland",
    "AXS-USD": "Axie Infinity",
}

# CoinGecko ID eşlemeleri
COINGECKO_IDS: Dict[str, str] = {
    "BTC-USD": "bitcoin",
    "ETH-USD": "ethereum",
    "BNB-USD": "binancecoin",
    "SOL-USD": "solana",
    "XRP-USD": "ripple",
    "ADA-USD": "cardano",
    "DOGE-USD": "dogecoin",
    "AVAX-USD": "avalanche-2",
    "MATIC-USD": "matic-network",
    "DOT-USD": "polkadot",
    "LINK-USD": "chainlink",
    "UNI-USD": "uniswap",
    "ATOM-USD": "cosmos",
    "LTC-USD": "litecoin",
    "BCH-USD": "bitcoin-cash",
    "ALGO-USD": "algorand",
    "XLM-USD": "stellar",
    "VET-USD": "vechain",
    "FIL-USD": "filecoin",
    "TRX-USD": "tron",
    "ETC-USD": "ethereum-classic",
    "THETA-USD": "theta-token",
    "XMR-USD": "monero",
    "EOS-USD": "eos",
    "AAVE-USD": "aave",
    "NEAR-USD": "near",
    "FTM-USD": "fantom",
    "SAND-USD": "the-sandbox",
    "MANA-USD": "decentraland",
    "AXS-USD": "axie-infinity",
}

# === PORTFÖY AYARLARI ===
BASLANGIC_SERMAYE_TL: float = 134000.0
BASLANGIC_SERMAYE_USD: float = 3000.0
USD_TL_KUR: float = 34.0  # Varsayılan kur, anlık güncellenir

# === RİSK YÖNETİMİ ===
MAX_POZISYON_YUZDE: float = 0.12      # %12 agresif pozisyon
STOP_LOSS_YUZDE: float = -0.07        # %-7 stop loss
TAKE_PROFIT_YUZDE: float = 0.15       # %+15 take profit
TRAILING_STOP_YUZDE: float = 0.05     # %5 trailing stop
MAX_ACIK_POZISYON: int = 20  # Çok fazla pozisyon            # Max 8 open positions

# === TEKNİK ANALİZ PARAMETRELERİ ===
RSI_PERIYOT_UZUN: int = 14
RSI_PERIYOT_KISA: int = 7
MACD_HIZLI: int = 12
MACD_YAVAS: int = 26
MACD_SINYAL: int = 9
BB_PERIYOT: int = 20
BB_STD: int = 2
ATR_PERIYOT: int = 14
STOCH_RSI_PERIYOT: int = 14
OBV_MA_PERIYOT: int = 20

MA_PERIYOTLAR: List[int] = [7, 20, 50, 100, 200]
HACIM_MA_PERIYOT: int = 20

# === SİNYAL EŞİKLERİ ===
RSI_ASIRI_SATIM: float = 30.0
RSI_ASIRI_ALIM: float = 70.0
RSI_KUVVETLI_SATIM: float = 80.0
RSI_KUVVETLI_ALIM: float = 20.0

# Minimum güven skoru (0-100)
MIN_GUVEN_SKORU: int = 20  # Çok agresif  # Simülasyon için düşük eşik

# === VERİ AYARLARI ===
YFINANCE_PERIOD: str = "2y"
YFINANCE_INTERVAL_GUNLUK: str = "1d"
YFINANCE_INTERVAL_SAATLIK: str = "1h"
SAATLIK_VERI_SURE: str = "60d"

# API Limitleri
COINGECKO_ISTEK_ARALIK: float = 3.0   # saniye, rate limit için

# === API URLs ===
FEAR_GREED_URL: str = "https://api.alternative.me/fng/?limit=30"
COINGECKO_GLOBAL_URL: str = "https://api.coingecko.com/api/v3/global"
COINGECKO_COINS_URL: str = "https://api.coingecko.com/api/v3/coins/markets"

# === VERİTABANI ===
DB_DOSYASI: str = "tilki_trades.db"

# === DASHBOARD ===
YENILEME_SURESI: int = 30  # saniye
DASHBOARD_BASLIK: str = "TİLKİ 🦊 — Kripto Ajanı"

# === PİYASA REJİMİ ===
MARKET_REJIM_ESIKLERI: Dict[str, Any] = {
    "BOGA_KUVVETLI": {"btc_trend": "yukari", "fg_min": 60, "vol_artis": True},
    "BOGA_ZAYIF": {"btc_trend": "yukari", "fg_min": 40, "vol_artis": False},
    "SIDEWAYS": {"btc_trend": "yatay", "fg_min": 30, "vol_artis": False},
    "AYI_ZAYIF": {"btc_trend": "asagi", "fg_min": 20, "vol_artis": False},
    "AYI_KUVVETLI": {"btc_trend": "asagi", "fg_max": 20, "vol_artis": True},
}

# FG index sınıfları
FG_SINIFLAR: Dict[str, str] = {
    "Aşırı Korku": "0-24",
    "Korku": "25-49",
    "Nötr": "50-54",
    "Açgözlülük": "55-74",
    "Aşırı Açgözlülük": "75-100",
}

# Renk teması
RENK_TEMA: Dict[str, str] = {
    "primary": "#FF8C00",      # Turuncu (tilki rengi)
    "secondary": "#FFD700",    # Altın sarı
    "background": "#0E1117",   # Koyu arka plan
    "surface": "#1E2130",      # Kart arka planı
    "success": "#00C896",      # Yeşil (AL)
    "danger": "#FF4B4B",       # Kırmızı (SAT)
    "warning": "#FFD700",      # Sarı (BEKLE)
    "text": "#FAFAFA",         # Beyaz metin
    "subtext": "#8B9BB4",      # Gri metin
}

# AGRESİF MOD
TAKE_PROFIT_YUZDESI: float = 0.08   # %8 hedef (agresif kâr)
STOP_LOSS_YUZDESI: float = 0.03     # %3 stop-loss (2.5:1 oran)
TRAILING_STOP_YUZDESI: float = 0.025  # %2.5 trailing
MIN_GUVEN_SKORU: int = 10           # Maksimum agresif
MAX_ACIK_POZISYON: int = 25         # Çok fazla pozisyon
