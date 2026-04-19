"""
Tilki Kripto Ajanı - SQLite Veritabanı İşlemleri
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from tilki_config import DB_DOSYASI

logger = logging.getLogger("tilki.db")


def baglanti_al() -> sqlite3.Connection:
    """Veritabanı bağlantısı döndür."""
    conn = sqlite3.connect(DB_DOSYASI, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def tablolari_olustur() -> None:
    """Gerekli tabloları oluştur."""
    conn = baglanti_al()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS islemler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zaman TEXT NOT NULL,
                sembol TEXT NOT NULL,
                islem_turu TEXT NOT NULL,  -- AL veya SAT
                miktar REAL NOT NULL,
                fiyat_usd REAL NOT NULL,
                toplam_usd REAL NOT NULL,
                toplam_tl REAL NOT NULL,
                usd_tl_kur REAL NOT NULL,
                neden TEXT,
                guven_skoru INTEGER,
                stop_loss REAL,
                take_profit REAL,
                pozisyon_id TEXT,
                durum TEXT DEFAULT 'ACIK'  -- ACIK, KAPALI
            );

            CREATE TABLE IF NOT EXISTS kapali_pozisyonlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pozisyon_id TEXT UNIQUE NOT NULL,
                sembol TEXT NOT NULL,
                acilis_zamani TEXT NOT NULL,
                kapanis_zamani TEXT NOT NULL,
                giris_fiyati REAL NOT NULL,
                cikis_fiyati REAL NOT NULL,
                miktar REAL NOT NULL,
                giris_toplam_usd REAL NOT NULL,
                cikis_toplam_usd REAL NOT NULL,
                kar_zarar_usd REAL NOT NULL,
                kar_zarar_tl REAL NOT NULL,
                kar_zarar_yuzde REAL NOT NULL,
                kapanis_nedeni TEXT,  -- STOP_LOSS, TAKE_PROFIT, MANUEL, TRAILING_STOP
                neden_detay TEXT
            );

            CREATE TABLE IF NOT EXISTS portfoy_gecmisi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zaman TEXT NOT NULL,
                toplam_deger_usd REAL NOT NULL,
                toplam_deger_tl REAL NOT NULL,
                nakit_usd REAL NOT NULL,
                pozisyon_degeri_usd REAL NOT NULL,
                acik_pozisyon_sayisi INTEGER NOT NULL,
                gunluk_kar_zarar_usd REAL,
                btc_fiyat REAL
            );

            CREATE TABLE IF NOT EXISTS market_verisi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zaman TEXT NOT NULL,
                sembol TEXT NOT NULL,
                fiyat REAL,
                hacim_24h REAL,
                piyasa_degeri REAL,
                degisim_24h REAL,
                degisim_7g REAL,
                rsi_14 REAL,
                rsi_7 REAL,
                macd REAL,
                macd_sinyal REAL,
                bb_ust REAL,
                bb_alt REAL,
                ma_20 REAL,
                ma_50 REAL,
                ma_200 REAL,
                sinyal TEXT,
                guven_skoru INTEGER,
                raw_json TEXT
            );

            CREATE TABLE IF NOT EXISTS dusunce_logu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zaman TEXT NOT NULL,
                baslik TEXT NOT NULL,
                icerik TEXT NOT NULL,
                oncelik TEXT DEFAULT 'NORMAL',  -- KRITIK, YUKSEK, NORMAL, DUSUK
                sembol TEXT,
                market_rejimi TEXT
            );

            CREATE TABLE IF NOT EXISTS fear_greed_gecmisi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zaman TEXT NOT NULL,
                deger INTEGER NOT NULL,
                siniflandirma TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_islemler_sembol ON islemler(sembol);
            CREATE INDEX IF NOT EXISTS idx_islemler_zaman ON islemler(zaman);
            CREATE INDEX IF NOT EXISTS idx_market_verisi_sembol ON market_verisi(sembol);
            CREATE INDEX IF NOT EXISTS idx_market_verisi_zaman ON market_verisi(zaman);
            CREATE INDEX IF NOT EXISTS idx_dusunce_logu_zaman ON dusunce_logu(zaman);
        """)
        conn.commit()
        logger.info("Veritabanı tabloları hazır.")
    except Exception as e:
        logger.error(f"Tablo oluşturma hatası: {e}")
    finally:
        conn.close()


def islem_kaydet(
    sembol: str,
    islem_turu: str,
    miktar: float,
    fiyat_usd: float,
    usd_tl_kur: float,
    neden: str = "",
    guven_skoru: int = 0,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    pozisyon_id: Optional[str] = None,
) -> int:
    """İşlem kaydeder, yeni ID döndürür."""
    conn = baglanti_al()
    try:
        toplam_usd = miktar * fiyat_usd
        toplam_tl = toplam_usd * usd_tl_kur
        zaman = datetime.utcnow().isoformat()

        cursor = conn.execute("""
            INSERT INTO islemler
            (zaman, sembol, islem_turu, miktar, fiyat_usd, toplam_usd, toplam_tl,
             usd_tl_kur, neden, guven_skoru, stop_loss, take_profit, pozisyon_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (zaman, sembol, islem_turu, miktar, fiyat_usd, toplam_usd, toplam_tl,
              usd_tl_kur, neden, guven_skoru, stop_loss, take_profit, pozisyon_id))
        conn.commit()
        new_id = cursor.lastrowid
        logger.info(f"İşlem kaydedildi: {islem_turu} {sembol} @ {fiyat_usd:.2f} USD (ID: {new_id})")
        return new_id or 0
    except Exception as e:
        logger.error(f"İşlem kaydetme hatası: {e}")
        return 0
    finally:
        conn.close()


def pozisyon_kapat(
    pozisyon_id: str,
    sembol: str,
    acilis_zamani: str,
    giris_fiyati: float,
    cikis_fiyati: float,
    miktar: float,
    giris_toplam_usd: float,
    usd_tl_kur: float,
    kapanis_nedeni: str = "MANUEL",
    neden_detay: str = "",
) -> None:
    """Pozisyon kapanışını kaydeder."""
    conn = baglanti_al()
    try:
        kapanis_zamani = datetime.utcnow().isoformat()
        cikis_toplam_usd = miktar * cikis_fiyati
        kar_zarar_usd = cikis_toplam_usd - giris_toplam_usd
        kar_zarar_tl = kar_zarar_usd * usd_tl_kur
        kar_zarar_yuzde = (kar_zarar_usd / giris_toplam_usd * 100) if giris_toplam_usd > 0 else 0

        conn.execute("""
            INSERT OR REPLACE INTO kapali_pozisyonlar
            (pozisyon_id, sembol, acilis_zamani, kapanis_zamani, giris_fiyati,
             cikis_fiyati, miktar, giris_toplam_usd, cikis_toplam_usd,
             kar_zarar_usd, kar_zarar_tl, kar_zarar_yuzde, kapanis_nedeni, neden_detay)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (pozisyon_id, sembol, acilis_zamani, kapanis_zamani, giris_fiyati,
              cikis_fiyati, miktar, giris_toplam_usd, cikis_toplam_usd,
              kar_zarar_usd, kar_zarar_tl, kar_zarar_yuzde, kapanis_nedeni, neden_detay))

        conn.execute("UPDATE islemler SET durum='KAPALI' WHERE pozisyon_id=?", (pozisyon_id,))
        conn.commit()

        emoji = "✅" if kar_zarar_usd >= 0 else "❌"
        logger.info(f"{emoji} Pozisyon kapandı: {sembol} K/Z: {kar_zarar_usd:+.2f} USD ({kar_zarar_yuzde:+.1f}%)")
    except Exception as e:
        logger.error(f"Pozisyon kapatma hatası: {e}")
    finally:
        conn.close()


def portfoy_snapshot_kaydet(
    toplam_deger_usd: float,
    toplam_deger_tl: float,
    nakit_usd: float,
    pozisyon_degeri_usd: float,
    acik_pozisyon_sayisi: int,
    gunluk_kar_zarar_usd: float = 0.0,
    btc_fiyat: float = 0.0,
) -> None:
    """Portföy anlık görüntüsünü kaydeder."""
    conn = baglanti_al()
    try:
        conn.execute("""
            INSERT INTO portfoy_gecmisi
            (zaman, toplam_deger_usd, toplam_deger_tl, nakit_usd,
             pozisyon_degeri_usd, acik_pozisyon_sayisi, gunluk_kar_zarar_usd, btc_fiyat)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.utcnow().isoformat(), toplam_deger_usd, toplam_deger_tl,
              nakit_usd, pozisyon_degeri_usd, acik_pozisyon_sayisi,
              gunluk_kar_zarar_usd, btc_fiyat))
        conn.commit()
    except Exception as e:
        logger.error(f"Portföy snapshot hatası: {e}")
    finally:
        conn.close()


def market_verisi_kaydet(sembol: str, veri: Dict[str, Any]) -> None:
    """Market verisi kaydeder."""
    conn = baglanti_al()
    try:
        conn.execute("""
            INSERT INTO market_verisi
            (zaman, sembol, fiyat, hacim_24h, piyasa_degeri, degisim_24h, degisim_7g,
             rsi_14, rsi_7, macd, macd_sinyal, bb_ust, bb_alt, ma_20, ma_50, ma_200,
             sinyal, guven_skoru, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            sembol,
            veri.get("fiyat"),
            veri.get("hacim_24h"),
            veri.get("piyasa_degeri"),
            veri.get("degisim_24h"),
            veri.get("degisim_7g"),
            veri.get("rsi_14"),
            veri.get("rsi_7"),
            veri.get("macd"),
            veri.get("macd_sinyal"),
            veri.get("bb_ust"),
            veri.get("bb_alt"),
            veri.get("ma_20"),
            veri.get("ma_50"),
            veri.get("ma_200"),
            veri.get("sinyal"),
            veri.get("guven_skoru"),
            json.dumps(veri, default=str),
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"Market verisi kaydetme hatası ({sembol}): {e}")
    finally:
        conn.close()


def dusunce_kaydet(
    baslik: str,
    icerik: str,
    oncelik: str = "NORMAL",
    sembol: Optional[str] = None,
    market_rejimi: Optional[str] = None,
) -> None:
    """Düşünce/karar logu kaydeder."""
    conn = baglanti_al()
    try:
        conn.execute("""
            INSERT INTO dusunce_logu (zaman, baslik, icerik, oncelik, sembol, market_rejimi)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (datetime.utcnow().isoformat(), baslik, icerik, oncelik, sembol, market_rejimi))
        conn.commit()
    except Exception as e:
        logger.error(f"Düşünce log hatası: {e}")
    finally:
        conn.close()


def fear_greed_kaydet(deger: int, siniflandirma: str) -> None:
    """Fear & Greed verisi kaydeder."""
    conn = baglanti_al()
    try:
        conn.execute("""
            INSERT INTO fear_greed_gecmisi (zaman, deger, siniflandirma)
            VALUES (?, ?, ?)
        """, (datetime.utcnow().isoformat(), deger, siniflandirma))
        conn.commit()
    except Exception as e:
        logger.error(f"F&G kaydetme hatası: {e}")
    finally:
        conn.close()


def son_islemleri_getir(limit: int = 50) -> List[Dict[str, Any]]:
    """Son işlemleri döndürür."""
    conn = baglanti_al()
    try:
        rows = conn.execute("""
            SELECT * FROM islemler ORDER BY zaman DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"İşlem getirme hatası: {e}")
        return []
    finally:
        conn.close()


def kapali_pozisyonlari_getir(limit: int = 100) -> List[Dict[str, Any]]:
    """Kapanmış pozisyonları döndürür."""
    conn = baglanti_al()
    try:
        rows = conn.execute("""
            SELECT * FROM kapali_pozisyonlar ORDER BY kapanis_zamani DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Kapalı pozisyon getirme hatası: {e}")
        return []
    finally:
        conn.close()


def portfoy_gecmisini_getir(limit: int = 500) -> List[Dict[str, Any]]:
    """Portföy geçmişini döndürür."""
    conn = baglanti_al()
    try:
        rows = conn.execute("""
            SELECT * FROM portfoy_gecmisi ORDER BY zaman ASC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Portföy geçmiş hatası: {e}")
        return []
    finally:
        conn.close()


def dusunce_loglarini_getir(limit: int = 100) -> List[Dict[str, Any]]:
    """Düşünce loglarını döndürür."""
    conn = baglanti_al()
    try:
        rows = conn.execute("""
            SELECT * FROM dusunce_logu ORDER BY zaman DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Düşünce log hatası: {e}")
        return []
    finally:
        conn.close()


def istatistikleri_hesapla() -> Dict[str, Any]:
    """Genel istatistikleri hesaplar."""
    conn = baglanti_al()
    try:
        rows = conn.execute("""
            SELECT
                COUNT(*) as toplam_islem,
                SUM(CASE WHEN kar_zarar_usd > 0 THEN 1 ELSE 0 END) as kazanan,
                SUM(CASE WHEN kar_zarar_usd <= 0 THEN 1 ELSE 0 END) as kaybeden,
                SUM(kar_zarar_usd) as toplam_kar_zarar_usd,
                SUM(kar_zarar_tl) as toplam_kar_zarar_tl,
                MAX(kar_zarar_yuzde) as en_iyi_islem_yuzde,
                MIN(kar_zarar_yuzde) as en_kotu_islem_yuzde,
                AVG(kar_zarar_yuzde) as ortalama_kar_zarar_yuzde
            FROM kapali_pozisyonlar
        """).fetchone()

        if rows and rows["toplam_islem"] > 0:
            kazanma_orani = (rows["kazanan"] / rows["toplam_islem"] * 100) if rows["toplam_islem"] > 0 else 0
            return {
                "toplam_islem": rows["toplam_islem"],
                "kazanan": rows["kazanan"],
                "kaybeden": rows["kaybeden"],
                "kazanma_orani": round(kazanma_orani, 1),
                "toplam_kar_zarar_usd": round(rows["toplam_kar_zarar_usd"] or 0, 2),
                "toplam_kar_zarar_tl": round(rows["toplam_kar_zarar_tl"] or 0, 2),
                "en_iyi_yuzde": round(rows["en_iyi_islem_yuzde"] or 0, 2),
                "en_kotu_yuzde": round(rows["en_kotu_islem_yuzde"] or 0, 2),
                "ortalama_yuzde": round(rows["ortalama_kar_zarar_yuzde"] or 0, 2),
            }
        return {
            "toplam_islem": 0, "kazanan": 0, "kaybeden": 0,
            "kazanma_orani": 0.0, "toplam_kar_zarar_usd": 0.0,
            "toplam_kar_zarar_tl": 0.0, "en_iyi_yuzde": 0.0,
            "en_kotu_yuzde": 0.0, "ortalama_yuzde": 0.0,
        }
    except Exception as e:
        logger.error(f"İstatistik hesaplama hatası: {e}")
        return {}
    finally:
        conn.close()


def son_market_verilerini_getir() -> List[Dict[str, Any]]:
    """Her sembol için en son market verisini döndürür."""
    conn = baglanti_al()
    try:
        rows = conn.execute("""
            SELECT m.* FROM market_verisi m
            INNER JOIN (
                SELECT sembol, MAX(zaman) as max_zaman
                FROM market_verisi GROUP BY sembol
            ) latest ON m.sembol = latest.sembol AND m.zaman = latest.max_zaman
            ORDER BY m.sembol
        """).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Son market verisi hatası: {e}")
        return []
    finally:
        conn.close()
