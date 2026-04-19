"""
Tilki Kripto Ajanı - Portföy Yönetimi (Paper Trading)
"""

import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any

from tilki_config import (
    BASLANGIC_SERMAYE_USD, BASLANGIC_SERMAYE_TL,
    MAX_POZISYON_YUZDE, STOP_LOSS_YUZDE, TAKE_PROFIT_YUZDE,
    TRAILING_STOP_YUZDE, MAX_ACIK_POZISYON, USD_TL_KUR,
)
from tilki_database import (
    islem_kaydet, pozisyon_kapat, portfoy_snapshot_kaydet, dusunce_kaydet,
)

logger = logging.getLogger("tilki.portfolio")


class Pozisyon:
    """Açık bir pozisyonu temsil eder."""

    def __init__(
        self,
        sembol: str,
        giris_fiyati: float,
        miktar: float,
        toplam_usd: float,
        stop_loss_yuzde: float = STOP_LOSS_YUZDE,
        take_profit_yuzde: float = TAKE_PROFIT_YUZDE,
        giris_nedeni: str = "",
        guven_skoru: int = 0,
        usd_tl_kur: float = USD_TL_KUR,
    ):
        self.pozisyon_id = str(uuid.uuid4())[:12]
        self.sembol = sembol
        self.giris_fiyati = giris_fiyati
        self.miktar = miktar
        self.toplam_usd = toplam_usd
        self.stop_loss_fiyat = giris_fiyati * (1 + stop_loss_yuzde)
        self.take_profit_fiyat = giris_fiyati * (1 + take_profit_yuzde)
        self.stop_loss_yuzde = stop_loss_yuzde
        self.take_profit_yuzde = take_profit_yuzde
        self.trailing_stop_fiyat = giris_fiyati * (1 + stop_loss_yuzde)
        self.en_yuksek_fiyat = giris_fiyati
        self.giris_nedeni = giris_nedeni
        self.guven_skoru = guven_skoru
        self.giris_zamani = datetime.utcnow().isoformat()
        self.usd_tl_kur = usd_tl_kur

    def guncel_deger_usd(self, guncel_fiyat: float) -> float:
        return self.miktar * guncel_fiyat

    def kar_zarar_usd(self, guncel_fiyat: float) -> float:
        return self.guncel_deger_usd(guncel_fiyat) - self.toplam_usd

    def kar_zarar_yuzde(self, guncel_fiyat: float) -> float:
        if self.toplam_usd <= 0:
            return 0.0
        return (self.kar_zarar_usd(guncel_fiyat) / self.toplam_usd) * 100

    def trailing_stop_guncelle(self, guncel_fiyat: float) -> None:
        """Trailing stop-loss günceller."""
        if guncel_fiyat > self.en_yuksek_fiyat:
            self.en_yuksek_fiyat = guncel_fiyat
            yeni_trailing = guncel_fiyat * (1 - TRAILING_STOP_YUZDE)
            if yeni_trailing > self.trailing_stop_fiyat:
                self.trailing_stop_fiyat = yeni_trailing

    def stop_kontrolu(self, guncel_fiyat: float) -> Optional[str]:
        """
        Pozisyon kapatma gereksinimi var mı kontrol eder.
        Döndürür: 'STOP_LOSS', 'TAKE_PROFIT', 'TRAILING_STOP' veya None
        """
        self.trailing_stop_guncelle(guncel_fiyat)

        if guncel_fiyat <= self.stop_loss_fiyat:
            return "STOP_LOSS"
        if guncel_fiyat >= self.take_profit_fiyat:
            return "TAKE_PROFIT"
        if guncel_fiyat <= self.trailing_stop_fiyat and guncel_fiyat > self.stop_loss_fiyat:
            return "TRAILING_STOP"
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pozisyon_id": self.pozisyon_id,
            "sembol": self.sembol,
            "giris_fiyati": self.giris_fiyati,
            "miktar": self.miktar,
            "toplam_usd": self.toplam_usd,
            "stop_loss_fiyat": self.stop_loss_fiyat,
            "take_profit_fiyat": self.take_profit_fiyat,
            "trailing_stop_fiyat": self.trailing_stop_fiyat,
            "en_yuksek_fiyat": self.en_yuksek_fiyat,
            "giris_nedeni": self.giris_nedeni,
            "guven_skoru": self.guven_skoru,
            "giris_zamani": self.giris_zamani,
        }


class Portfoy:
    """Paper trading portföyü yönetir."""

    def __init__(self, usd_tl_kur: float = USD_TL_KUR):
        self.nakit_usd = BASLANGIC_SERMAYE_USD
        self.baslangic_usd = BASLANGIC_SERMAYE_USD
        self.usd_tl_kur = usd_tl_kur
        self.acik_pozisyonlar: Dict[str, Pozisyon] = {}  # sembol -> Pozisyon
        self.toplam_islem = 0
        self.kazanan_islem = 0
        self.kaybeden_islem = 0
        self.toplam_kar_zarar_usd = 0.0
        self.max_drawdown = 0.0
        self.zirve_deger = BASLANGIC_SERMAYE_USD
        logger.info(f"Portföy başlatıldı: {self.nakit_usd:.2f} USD")

    def toplam_deger_hesapla(self, guncel_fiyatlar: Dict[str, float]) -> float:
        """Tüm varlıkların toplam USD değerini hesaplar."""
        pozisyon_degeri = sum(
            poz.guncel_deger_usd(guncel_fiyatlar.get(sembol, poz.giris_fiyati))
            for sembol, poz in self.acik_pozisyonlar.items()
        )
        return self.nakit_usd + pozisyon_degeri

    def pozisyon_degeri_hesapla(self, guncel_fiyatlar: Dict[str, float]) -> float:
        """Açık pozisyonların toplam değerini hesaplar."""
        return sum(
            poz.guncel_deger_usd(guncel_fiyatlar.get(sembol, poz.giris_fiyati))
            for sembol, poz in self.acik_pozisyonlar.items()
        )

    def max_pozisyon_buyuklugu_hesapla(self, guncel_fiyatlar: Dict[str, float]) -> float:
        """Bir pozisyon için maksimum USD miktarı."""
        toplam = self.toplam_deger_hesapla(guncel_fiyatlar)
        return toplam * MAX_POZISYON_YUZDE

    def al(
        self,
        sembol: str,
        fiyat: float,
        sinyal_verisi: Dict[str, Any],
        guncel_fiyatlar: Dict[str, float],
    ) -> bool:
        """
        Alım işlemi gerçekleştirir.
        Döndürür: True/False başarı durumu
        """
        # Kontroller
        if sembol in self.acik_pozisyonlar:
            logger.info(f"Zaten açık pozisyon var: {sembol}")
            return False

        if len(self.acik_pozisyonlar) >= MAX_ACIK_POZISYON:
            logger.info(f"Maksimum pozisyon sayısına ulaşıldı ({MAX_ACIK_POZISYON})")
            return False

        max_miktar = self.max_pozisyon_buyuklugu_hesapla(guncel_fiyatlar)
        if self.nakit_usd < max_miktar * 0.5:  # En az yarı boyut
            logger.info(f"Yetersiz nakit: {self.nakit_usd:.2f} USD (gerekli: {max_miktar * 0.5:.2f})")
            return False

        if fiyat <= 0:
            logger.error(f"Geçersiz fiyat: {sembol} @ {fiyat}")
            return False

        # İşlem büyüklüğü (nakit ve max'ın minimumu)
        islem_miktari_usd = min(max_miktar, self.nakit_usd * 0.95)  # %5 tampon
        islem_miktari_usd = max(islem_miktari_usd, 10)  # minimum $10

        if islem_miktari_usd > self.nakit_usd:
            islem_miktari_usd = self.nakit_usd * 0.9

        coin_miktari = islem_miktari_usd / fiyat

        stop_loss_yuzde = sinyal_verisi.get("stop_loss_yuzde", STOP_LOSS_YUZDE)
        take_profit_yuzde = sinyal_verisi.get("take_profit_yuzde", TAKE_PROFIT_YUZDE)
        guven_skoru = sinyal_verisi.get("guven", 0)
        neden = " | ".join(sinyal_verisi.get("neden", []))

        # Pozisyon oluştur
        poz = Pozisyon(
            sembol=sembol,
            giris_fiyati=fiyat,
            miktar=coin_miktari,
            toplam_usd=islem_miktari_usd,
            stop_loss_yuzde=stop_loss_yuzde,
            take_profit_yuzde=take_profit_yuzde,
            giris_nedeni=neden,
            guven_skoru=guven_skoru,
            usd_tl_kur=self.usd_tl_kur,
        )

        self.nakit_usd -= islem_miktari_usd
        self.acik_pozisyonlar[sembol] = poz

        # Veritabanına kaydet
        islem_kaydet(
            sembol=sembol,
            islem_turu="AL",
            miktar=coin_miktari,
            fiyat_usd=fiyat,
            usd_tl_kur=self.usd_tl_kur,
            neden=neden,
            guven_skoru=guven_skoru,
            stop_loss=poz.stop_loss_fiyat,
            take_profit=poz.take_profit_fiyat,
            pozisyon_id=poz.pozisyon_id,
        )

        dusunce_kaydet(
            baslik=f"AL: {sembol}",
            icerik=f"Fiyat: ${fiyat:.4f} | Miktar: {coin_miktari:.4f} | Tutar: ${islem_miktari_usd:.2f}\n"
                   f"Stop-Loss: ${poz.stop_loss_fiyat:.4f} ({stop_loss_yuzde*100:.1f}%) | "
                   f"Hedef: ${poz.take_profit_fiyat:.4f} ({take_profit_yuzde*100:.1f}%)\n"
                   f"Güven: {guven_skoru}/100\nNeden: {neden}",
            oncelik="YUKSEK",
            sembol=sembol,
        )

        logger.info(f"✅ AL: {sembol} @ ${fiyat:.4f} | ${islem_miktari_usd:.2f} | Güven: {guven_skoru}")
        return True

    def sat(
        self,
        sembol: str,
        fiyat: float,
        kapanis_nedeni: str = "MANUEL",
        ek_neden: str = "",
    ) -> bool:
        """
        Satış işlemi gerçekleştirir.
        Döndürür: True/False başarı durumu
        """
        if sembol not in self.acik_pozisyonlar:
            logger.warning(f"Açık pozisyon yok: {sembol}")
            return False

        poz = self.acik_pozisyonlar[sembol]
        cikis_toplam = poz.miktar * fiyat
        kar_zarar = cikis_toplam - poz.toplam_usd
        kar_zarar_yuzde = (kar_zarar / poz.toplam_usd * 100) if poz.toplam_usd > 0 else 0

        self.nakit_usd += cikis_toplam
        self.toplam_kar_zarar_usd += kar_zarar
        self.toplam_islem += 1

        if kar_zarar >= 0:
            self.kazanan_islem += 1
        else:
            self.kaybeden_islem += 1

        # Drawdown güncelle
        mevcut_toplam = self.nakit_usd + sum(p.toplam_usd for p in self.acik_pozisyonlar.values() if p.sembol != sembol)
        if mevcut_toplam > self.zirve_deger:
            self.zirve_deger = mevcut_toplam
        elif self.zirve_deger > 0:
            drawdown = (self.zirve_deger - mevcut_toplam) / self.zirve_deger * 100
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown

        # Veritabanına kaydet
        islem_kaydet(
            sembol=sembol,
            islem_turu="SAT",
            miktar=poz.miktar,
            fiyat_usd=fiyat,
            usd_tl_kur=self.usd_tl_kur,
            neden=f"{kapanis_nedeni}: {ek_neden}",
            guven_skoru=poz.guven_skoru,
            pozisyon_id=poz.pozisyon_id,
        )

        pozisyon_kapat(
            pozisyon_id=poz.pozisyon_id,
            sembol=sembol,
            acilis_zamani=poz.giris_zamani,
            giris_fiyati=poz.giris_fiyati,
            cikis_fiyati=fiyat,
            miktar=poz.miktar,
            giris_toplam_usd=poz.toplam_usd,
            usd_tl_kur=self.usd_tl_kur,
            kapanis_nedeni=kapanis_nedeni,
            neden_detay=ek_neden,
        )

        emoji = "🟢" if kar_zarar >= 0 else "🔴"
        log_msg = (
            f"{emoji} SAT: {sembol} @ ${fiyat:.4f} | "
            f"K/Z: ${kar_zarar:+.2f} ({kar_zarar_yuzde:+.1f}%) | "
            f"Neden: {kapanis_nedeni}"
        )

        dusunce_kaydet(
            baslik=f"SAT: {sembol} ({kapanis_nedeni})",
            icerik=f"Giriş: ${poz.giris_fiyati:.4f} → Çıkış: ${fiyat:.4f}\n"
                   f"Kar/Zarar: ${kar_zarar:+.2f} ({kar_zarar_yuzde:+.1f}%)\n"
                   f"Neden: {kapanis_nedeni} | {ek_neden}",
            oncelik="YUKSEK" if abs(kar_zarar_yuzde) > 5 else "NORMAL",
            sembol=sembol,
        )

        del self.acik_pozisyonlar[sembol]
        logger.info(log_msg)
        return True

    def pozisyonlari_kontrol_et(self, guncel_fiyatlar: Dict[str, float]) -> List[str]:
        """
        Tüm açık pozisyonları kontrol eder, gerekirse kapatır.
        Döndürür: Kapatılan sembollerin listesi
        """
        kapatilan = []
        for sembol, poz in list(self.acik_pozisyonlar.items()):
            guncel_fiyat = guncel_fiyatlar.get(sembol)
            if guncel_fiyat is None or guncel_fiyat <= 0:
                continue

            neden = poz.stop_kontrolu(guncel_fiyat)
            if neden:
                ek_aciklama = (
                    f"Giriş: ${poz.giris_fiyati:.4f} | Güncel: ${guncel_fiyat:.4f} | "
                    f"K/Z: {poz.kar_zarar_yuzde(guncel_fiyat):+.1f}%"
                )
                if self.sat(sembol, guncel_fiyat, neden, ek_aciklama):
                    kapatilan.append(sembol)

        return kapatilan

    def snapshot_kaydet(self, guncel_fiyatlar: Dict[str, float], btc_fiyat: float = 0.0) -> None:
        """Portföy anlık görüntüsünü veritabanına kaydeder."""
        toplam = self.toplam_deger_hesapla(guncel_fiyatlar)
        poz_degeri = self.pozisyon_degeri_hesapla(guncel_fiyatlar)

        portfoy_snapshot_kaydet(
            toplam_deger_usd=toplam,
            toplam_deger_tl=toplam * self.usd_tl_kur,
            nakit_usd=self.nakit_usd,
            pozisyon_degeri_usd=poz_degeri,
            acik_pozisyon_sayisi=len(self.acik_pozisyonlar),
            gunluk_kar_zarar_usd=self.toplam_kar_zarar_usd,
            btc_fiyat=btc_fiyat,
        )

    def kazanma_orani(self) -> float:
        if self.toplam_islem == 0:
            return 0.0
        return (self.kazanan_islem / self.toplam_islem) * 100

    def durum_ozeti(self, guncel_fiyatlar: Dict[str, float]) -> Dict[str, Any]:
        """Portföy durumu özeti döndürür."""
        toplam = self.toplam_deger_hesapla(guncel_fiyatlar)
        poz_degeri = self.pozisyon_degeri_hesapla(guncel_fiyatlar)
        kar_zarar = toplam - self.baslangic_usd
        kar_zarar_yuzde = (kar_zarar / self.baslangic_usd * 100) if self.baslangic_usd > 0 else 0

        pozisyon_detaylari = []
        for sembol, poz in self.acik_pozisyonlar.items():
            gfiyat = guncel_fiyatlar.get(sembol, poz.giris_fiyati)
            kz = poz.kar_zarar_yuzde(gfiyat)
            pozisyon_detaylari.append({
                "sembol": sembol,
                "giris_fiyati": poz.giris_fiyati,
                "guncel_fiyat": gfiyat,
                "miktar": poz.miktar,
                "deger_usd": poz.guncel_deger_usd(gfiyat),
                "kar_zarar_usd": poz.kar_zarar_usd(gfiyat),
                "kar_zarar_yuzde": kz,
                "stop_loss": poz.stop_loss_fiyat,
                "take_profit": poz.take_profit_fiyat,
                "trailing_stop": poz.trailing_stop_fiyat,
                "giris_zamani": poz.giris_zamani,
                "guven_skoru": poz.guven_skoru,
            })

        return {
            "toplam_deger_usd": round(toplam, 2),
            "toplam_deger_tl": round(toplam * self.usd_tl_kur, 2),
            "nakit_usd": round(self.nakit_usd, 2),
            "pozisyon_degeri_usd": round(poz_degeri, 2),
            "kar_zarar_usd": round(kar_zarar, 2),
            "kar_zarar_tl": round(kar_zarar * self.usd_tl_kur, 2),
            "kar_zarar_yuzde": round(kar_zarar_yuzde, 2),
            "acik_pozisyon_sayisi": len(self.acik_pozisyonlar),
            "toplam_islem": self.toplam_islem,
            "kazanan_islem": self.kazanan_islem,
            "kaybeden_islem": self.kaybeden_islem,
            "kazanma_orani": round(self.kazanma_orani(), 1),
            "toplam_kar_zarar_usd": round(self.toplam_kar_zarar_usd, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "pozisyonlar": pozisyon_detaylari,
            "usd_tl_kur": self.usd_tl_kur,
        }
