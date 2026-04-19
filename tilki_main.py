"""
Tilki Kripto Ajanı - Ana Döngü
"""

import time
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional

from tilki_config import (
    KRIPTO_SEMBOLLER, MIN_GUVEN_SKORU, YENILEME_SURESI,
    BASLANGIC_SERMAYE_USD, USD_TL_KUR,
)
from tilki_database import tablolari_olustur, dusunce_kaydet
from tilki_data import tam_veri_paketi_cek, anlık_fiyat_cek, usd_tl_kur_cek
from tilki_strategy import teknik_analiz_yap, piyasa_rejimi_tespit, tum_sinyalleri_uret
from tilki_portfolio import Portfoy

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("tilki_agent.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("tilki.main")


def banner_yazdir() -> None:
    print("""
╔══════════════════════════════════════════════════╗
║          🦊 TİLKİ — Kripto Simülasyon Ajanı     ║
║                                                  ║
║   30 Kripto · Teknik Analiz · Paper Trading      ║
║   yfinance + CoinGecko · SQLite Logging          ║
╚══════════════════════════════════════════════════╝
    """)


def guncel_fiyatlari_cek(veri_paketi: Dict[str, Any]) -> Dict[str, float]:
    """Veri paketinden güncel fiyatları çıkarır."""
    fiyatlar: Dict[str, float] = {}
    for sembol in KRIPTO_SEMBOLLER:
        # Önce CoinGecko'dan dene
        cg = veri_paketi.get("coingecko_market", {}).get(sembol, {})
        if cg and cg.get("guncel_fiyat", 0) > 0:
            fiyatlar[sembol] = float(cg["guncel_fiyat"])
            continue

        # Sonra günlük veri son kapanışından al
        df = veri_paketi.get("gunluk_veriler", {}).get(sembol)
        if df is not None and not df.empty:
            fiyatlar[sembol] = float(df["close"].iloc[-1])

    return fiyatlar


def karar_ver_ve_islem_yap(
    portfoy: Portfoy,
    sinyaller: Dict[str, Any],
    guncel_fiyatlar: Dict[str, float],
    piyasa_rejimi: str,
) -> None:
    """
    Sinyallere göre işlem kararı verir.
    """
    # Önce mevcut pozisyonları kontrol et (stop/take profit)
    kapatilan = portfoy.pozisyonlari_kontrol_et(guncel_fiyatlar)
    if kapatilan:
        logger.info(f"Otomatik kapanan pozisyonlar: {kapatilan}")

    # Ayı piyasasında küçük pozisyonlarla devam et
    if piyasa_rejimi == "AYI_KUVVETLI":
        logger.info("⚠️ Kuvvetli ayı — küçük pozisyonlarla devam")
        # return kaldırıldı — agresif mod

    # Al sinyallerini güven skoruna göre sırala
    al_sinyalleri = [
        (sembol, veri)
        for sembol, veri in sinyaller.items()
        if veri.get("sinyal") == "AL"
        and veri.get("guven", 0) >= MIN_GUVEN_SKORU
        and sembol not in portfoy.acik_pozisyonlar
        and guncel_fiyatlar.get(sembol, 0) > 0
    ]

    al_sinyalleri.sort(key=lambda x: x[1].get("guven", 0), reverse=True)

    # En güçlü sinyallere göre al
    for sembol, sinyal_veri in al_sinyalleri:
        if len(portfoy.acik_pozisyonlar) >= 8:
            break

        fiyat = guncel_fiyatlar.get(sembol, 0)
        if fiyat <= 0:
            continue

        basari = portfoy.al(sembol, fiyat, sinyal_veri, guncel_fiyatlar)
        if basari:
            logger.info(f"Yeni pozisyon açıldı: {sembol}")

    # SAT sinyallerini kontrol et
    sat_sinyalleri = [
        (sembol, veri)
        for sembol, veri in sinyaller.items()
        if veri.get("sinyal") == "SAT"
        and sembol in portfoy.acik_pozisyonlar
        and guncel_fiyatlar.get(sembol, 0) > 0
    ]

    for sembol, sinyal_veri in sat_sinyalleri:
        fiyat = guncel_fiyatlar.get(sembol, 0)
        neden = " | ".join(sinyal_veri.get("neden", ["Teknik sinyal"]))
        portfoy.sat(sembol, fiyat, "SINYAL_SAT", neden)


def ana_dongu() -> None:
    """Ana ajan döngüsü."""
    banner_yazdir()

    # Veritabanını başlat
    tablolari_olustur()

    # USD/TL kurunu al
    kur = usd_tl_kur_cek()
    logger.info(f"Başlangıç USD/TL kuru: {kur:.2f}")

    # Portföy başlat
    portfoy = Portfoy(usd_tl_kur=kur)

    dusunce_kaydet(
        baslik="🦊 Tilki Başlatıldı",
        icerik=f"Kripto ajanı aktif. Sermaye: ${BASLANGIC_SERMAYE_USD:.0f} (~{BASLANGIC_SERMAYE_USD * kur:.0f} TL)\n"
               f"Takip edilen coinler: {len(KRIPTO_SEMBOLLER)}\n"
               f"Strateji: Çok zaman dilimli analiz + Risk yönetimi\n"
               f"Başlangıç zamanı: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
        oncelik="KRITIK",
    )

    dongu_sayaci = 0
    son_tam_guncelleme = 0

    while True:
        try:
            dongu_sayaci += 1
            zaman_simdi = time.time()
            logger.info(f"\n{'='*60}")
            logger.info(f"🦊 Tilki döngüsü #{dongu_sayaci} - {datetime.utcnow().strftime('%H:%M:%S')} UTC")

            # Tam veri paketi çek (her döngüde - gerçek zamanlı)
            logger.info("📡 Veri çekiliyor...")
            veri_paketi = tam_veri_paketi_cek()

            # USD/TL kuru güncelle
            portfoy.usd_tl_kur = veri_paketi.get("usd_tl_kur", kur)

            # Güncel fiyatlar
            guncel_fiyatlar = guncel_fiyatlari_cek(veri_paketi)
            logger.info(f"Fiyat güncellendi: {len(guncel_fiyatlar)} sembol")

            # Fear & Greed
            fg = veri_paketi.get("fear_greed")
            fg_deger = fg["deger"] if fg else 50
            fg_sinif = fg["siniflandirma"] if fg else "Nötr"
            logger.info(f"Fear & Greed: {fg_deger} ({fg_sinif})")

            # CoinGecko global
            global_veri = veri_paketi.get("coingecko_global")
            if global_veri:
                btc_dom = global_veri.get("btc_dominance", 0)
                piyasa_degeri_t = global_veri.get("toplam_piyasa_degeri_usd", 0) / 1e12
                logger.info(f"BTC Dominance: {btc_dom:.1f}% | Toplam Piyasa: ${piyasa_degeri_t:.2f}T")

            # BTC analizi ile piyasa rejimi tespiti
            btc_df = veri_paketi.get("gunluk_veriler", {}).get("BTC-USD")
            btc_analiz = teknik_analiz_yap(btc_df, "BTC-USD") if btc_df is not None else None
            piyasa_rejimi, rejim_aciklama = piyasa_rejimi_tespit(btc_analiz, fg_deger)
            logger.info(f"Piyasa Rejimi: {piyasa_rejimi} | {rejim_aciklama}")

            dusunce_kaydet(
                baslik=f"Piyasa Analizi - {piyasa_rejimi}",
                icerik=f"Rejim: {piyasa_rejimi}\n{rejim_aciklama}\n"
                       f"F&G: {fg_deger} ({fg_sinif})\n"
                       f"BTC Dominance: {btc_dom if global_veri else 'N/A'}%",
                oncelik="NORMAL",
                market_rejimi=piyasa_rejimi,
            )

            # Teknik analiz ve sinyal üretimi
            logger.info("📊 Teknik analiz ve sinyal üretimi...")
            sinyaller, analizler = tum_sinyalleri_uret(
                gunluk_veriler=veri_paketi.get("gunluk_veriler", {}),
                saatlik_veriler=veri_paketi.get("saatlik_veriler", {}),
                fear_greed_deger=fg_deger,
                piyasa_rejimi=piyasa_rejimi,
                coingecko_market=veri_paketi.get("coingecko_market", {}),
            )

            # İşlem kararları
            logger.info("🎯 İşlem kararları alınıyor...")
            karar_ver_ve_islem_yap(portfoy, sinyaller, guncel_fiyatlar, piyasa_rejimi)

            # Portföy snapshot
            btc_fiyat = guncel_fiyatlar.get("BTC-USD", 0)
            portfoy.snapshot_kaydet(guncel_fiyatlar, btc_fiyat)

            # Portföy özeti
            ozet = portfoy.durum_ozeti(guncel_fiyatlar)
            logger.info(
                f"💼 Portföy: ${ozet['toplam_deger_usd']:.2f} "
                f"({ozet['kar_zarar_yuzde']:+.1f}%) | "
                f"Nakit: ${ozet['nakit_usd']:.2f} | "
                f"Açık: {ozet['acik_pozisyon_sayisi']}"
            )

            if ozet["pozisyonlar"]:
                logger.info("Açık pozisyonlar:")
                for poz in ozet["pozisyonlar"]:
                    logger.info(
                        f"  {poz['sembol']}: ${poz['guncel_fiyat']:.4f} "
                        f"({poz['kar_zarar_yuzde']:+.1f}%)"
                    )

            # Sonraki döngüye kadar bekle
            bitis = time.time()
            gecen = bitis - zaman_simdi
            bekleme = max(10, YENILEME_SURESI - gecen)
            logger.info(f"Döngü süresi: {gecen:.1f}s | Sonraki güncelleme: {bekleme:.0f}s")
            time.sleep(bekleme)

        except KeyboardInterrupt:
            logger.info("\n🛑 Tilki durduruldu (Ctrl+C)")
            ozet = portfoy.durum_ozeti({})
            logger.info(f"Son durum: ${ozet['toplam_deger_usd']:.2f} | {ozet['kar_zarar_yuzde']:+.1f}%")
            break
        except Exception as e:
            logger.error(f"Ana döngü hatası: {e}", exc_info=True)
            dusunce_kaydet(
                baslik="⚠️ Döngü Hatası",
                icerik=f"Hata: {str(e)}\nDöngü #{dongu_sayaci}",
                oncelik="KRITIK",
            )
            time.sleep(30)  # Hata sonrası bekle


if __name__ == "__main__":
    ana_dongu()
