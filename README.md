# 🦊 TİLKİ — Kripto Simülasyon Ajanı

Kapsamlı kripto para trading simülasyon ajanı. 30 kripto para birimini takip eder, teknik analiz yapar ve paper trading gerçekleştirir.

## Özellikler

- **30 Kripto Sembol**: BTC, ETH, BNB, SOL, XRP ve daha fazlası
- **Kapsamlı Teknik Analiz**: RSI, MACD, Bollinger Bands, Fibonacci, ATR, OBV, Stochastic RSI
- **Çok Zaman Dilimli**: 2 yıllık günlük + 60 günlük saatlik veri
- **CoinGecko Entegrasyonu**: Piyasa değeri, hacim, Fear & Greed Index
- **Paper Trading**: 134,000 TL (~$3,000) başlangıç sermayesi
- **Risk Yönetimi**: Stop-loss, take-profit, trailing stop, max %8 pozisyon
- **Güzel Dashboard**: 5 sayfalı Streamlit arayüzü, plotly grafikler

## Kurulum

### 1. Gereksinimler

- Python 3.9+
- İnternet bağlantısı

### 2. Kurulum

```bash
# Repo klasörüne gir
cd tilki

# Scripti çalıştırılabilir yap
chmod +x start_tilki.sh

# Başlat
./start_tilki.sh
```

### 3. Manuel Kurulum

```bash
# Virtual environment oluştur
python3 -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows

# Bağımlılıkları yükle
pip install -r requirements.txt

# Dashboard başlat
streamlit run tilki_dashboard.py

# VEYA Ajanı başlat
python3 tilki_main.py
```

## Dosya Yapısı

```
tilki/
├── tilki_config.py      # Konfigürasyon (semboller, parametreler)
├── tilki_database.py    # SQLite veritabanı işlemleri
├── tilki_data.py        # Veri çekme (yfinance + CoinGecko)
├── tilki_strategy.py    # Teknik analiz + karar motoru
├── tilki_portfolio.py   # Paper trading portföy yönetimi
├── tilki_main.py        # Ana ajan döngüsü
├── tilki_dashboard.py   # Streamlit dashboard (5 sayfa)
├── requirements.txt     # Python bağımlılıkları
├── start_tilki.sh       # Başlatma scripti
└── .env.example         # Ortam değişkenleri örneği
```

## Dashboard Sayfaları

| Sayfa | Açıklama |
|-------|----------|
| 🦊 Genel Bakış | Portföy değeri, F&G index, açık pozisyonlar, son işlemler |
| 📡 Piyasa Tarayıcı | 30 coin tablosu, sinyal, güven skoru, sparkline |
| 🔍 Coin Analizi | Candlestick grafik, RSI, MACD, Fibonacci seviyeleri |
| 📊 İşlem Geçmişi | Tüm işlemler, win/loss pasta, K/Z grafiği |
| 🧠 Tilki Düşünüyor | Karar logu, piyasa rejimi, güven skoru dağılımı |

## Teknik Göstergeler

- **RSI** (7 ve 14 periyot)
- **MACD** (12, 26, 9)
- **Bollinger Bands** (20, 2)
- **Hareketli Ortalamalar** (7, 20, 50, 100, 200 günlük)
- **ATR** (Average True Range)
- **OBV** (On Balance Volume)
- **Stochastic RSI**
- **Fibonacci Retracement** (son 90 günlük yüksek/düşük)

## Risk Yönetimi

| Parametre | Değer |
|-----------|-------|
| Max pozisyon | %8 portföy |
| Stop-loss | %-7 |
| Take-profit | %+15 |
| Trailing stop | %5 |
| Max açık pozisyon | 8 |

## Veri Kaynakları

- **yfinance**: OHLCV verisi (2 yıllık günlük, 60 günlük saatlik)
- **CoinGecko API** (ücretsiz): Piyasa değeri, hacim, sparkline
- **Alternative.me**: Fear & Greed Index

## Notlar

- Bu bir **simülasyon** ajanıdır, gerçek para işlemi yapmaz
- Gerçek yatırım tavsiyesi değildir
- CoinGecko ücretsiz API kullanır (rate limit: ~50 istek/dk)
- SQLite veritabanı: `tilki_trades.db`
- Log dosyası: `tilki_agent.log`

---

🦊 **Tilki — Zeki ve Hızlı Kripto Ajanı**
