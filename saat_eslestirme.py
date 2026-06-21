"""
SAAT EŞLEŞTİRME MODÜLÜ
======================
METAR ve SİNOPTİK rasatlarının saatlerini otomatik çekilen veriler (rüzgar, basınç, sıcaklık) 
için akıllı biçimde eşleştiren modul.

Özellikler:
- Gün sınırları aşan saatleri yönetme (23:50 → 00:00)
- Hata payı toleransı (±15 dakika varsayılan)
- Otomatik veri için katı eşleştirme, gözlemsel veriler için daha esnek kural
"""

import pandas as pd
import datetime
import math


class SaatEslestirici:
    """
    METAR ve SİNOPTİK rasatlarının saatlerini akıllı biçimde eşleştiriyor.
    """
    
    def __init__(self, tolerans_dakika=15):
        """
        :param tolerans_dakika: Rüzgar/basınç/sıcaklık gibi otomatik veriler için 
                                saatlerin eşleşmesi için kabul edilen maksimum fark (dakika cinsinden)
        """
        self.tolerans_dakika = tolerans_dakika
    
    @staticmethod
    def gmt_saat_normalize_et(gmt_value):
        """
        GMT değerini standart saat formatına çevirir.
        
        Giriş:
            - 0-23 aralığı (standard saat)
            - "14:30" formatı (saat:dakika)
            - 1430 formatı (24'lü saat kodlaması)
            
        Çıkış: (saat, dakika) tuple
        """
        try:
            if pd.isna(gmt_value):
                return None
            
            # String formatı "14:30" şeklindeyse
            if isinstance(gmt_value, str):
                if ':' in gmt_value:
                    parts = gmt_value.split(':')
                    h = int(parts[0])
                    m = int(parts[1]) if len(parts) > 1 else 0
                    return (h, m)
                else:
                    # 1430 formatı (4 haneli)
                    gmt_value = int(float(gmt_value))
            else:
                gmt_value = int(float(gmt_value))
            
            # 1-23 aralığı ise doğrudan saat
            if 0 <= gmt_value <= 23:
                return (gmt_value, 0)
            
            # 100-2359 formatı ise
            if 100 <= gmt_value <= 2359:
                h = gmt_value // 100
                m = gmt_value % 100
                if h <= 23 and m <= 59:
                    return (h, m)
            
            return None
            
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def dakikaya_cevir(saat_tuple):
        """(saat, dakika) -> dakika (00:00 bağlantılı olarak) """
        if saat_tuple is None:
            return None
        return saat_tuple[0] * 60 + saat_tuple[1]
    
    @staticmethod
    def dakikadan_saate_cevir(dakika):
        """dakika (00:00 bağlantılı) -> (saat, dakika)"""
        if dakika is None:
            return None
        return (dakika // 60, dakika % 60)
    
    def saat_farki_hesapla(self, gmt1_saatler, gmt2_saatler, tum_gunu_kirsa_bilir=True):
        """
        İki saat arasındaki farkı dakika cinsinden hesaplar.
        
        :param gmt1_saatler: (saat, dakika) tuple
        :param gmt2_saatler: (saat, dakika) tuple
        :param tum_gunu_kirsa_bilir: True ise gün sınırını aşan farkları da hesapla (23:50→00:30 = 40dk)
        :return: Mutlak dakika farkı
        """
        if gmt1_saatler is None or gmt2_saatler is None:
            return None
        
        d1 = self.dakikaya_cevir(gmt1_saatler)
        d2 = self.dakikaya_cevir(gmt2_saatler)
        
        fark = abs(d1 - d2)
        
        if tum_gunu_kirsa_bilir:
            # Gün sınırından geçerse minimum mesafeyi kullan
            # Örn: 23:50 = 1430 dk, 00:30 = 30 dk => diff=1400 veya (1440-1400)=40
            bir_gun_dakika = 24 * 60
            fark = min(fark, bir_gun_dakika - fark)
        
        return fark
    
    def saatler_esilestirilebilir_mi(self, metar_gmt, sinoptik_gmt, otomat_veri_mi=True):
        """
        METAR ve SİNOPTİK saatlerinin uyumlu olup olmadığını kontrol eder.
        
        :param metar_gmt: METAR GMT saati (int, str, tuple)
        :param sinoptik_gmt: SİNOPTİK GMT saati (int, str, tuple)
        :param otomat_veri_mi: True ise katı kural (rüzgar, basınç, sıcaklık). 
                               False ise esnek kural (gözlemsel veriler)
        :return: (eşleşir_mi: bool, açıklama: str, fark_dakika: int)
        """
        metar_st = self.gmt_saat_normalize_et(metar_gmt)
        sinoptik_st = self.gmt_saat_normalize_et(sinoptik_gmt)
        
        if metar_st is None or sinoptik_st is None:
            return False, "Geçersiz saat formatı", None
        
        fark = self.saat_farki_hesapla(metar_st, sinoptik_st)
        
        if fark is None:
            return False, "Saat hesaplaması başarısız", None
        
        # Otomatik veriler (rüzgar, basınç, sıcaklık) katı eşleştirme
        if otomat_veri_mi:
            if fark <= self.tolerans_dakika:
                return True, f"✓ Eşleşiyor ({fark} dakika fark)", fark
            else:
                return False, f"✗ Eşleşmiyor ({fark} dakika > {self.tolerans_dakika} tolerans)", fark
        
        # Gözlemsel veriler daha esnek
        else:
            # 3 saat ana rasatları arasında 1 saat kadar fark kabul edilebilir
            if fark <= 60:  # 1 saat
                return True, f"✓ Eşleşiyor ({fark} dakika fark)", fark
            else:
                return False, f"✗ Eşleşmiyor ({fark} dakika > 60 dakika tolerans)", fark
    
    def en_yakin_eslesmeyi_bul(self, hedef_gmt, alternatif_gmtler, otomat_veri_mi=True):
        """
        Verilen hedef saate en yakın eşleşmeyi bulur.
        
        :param hedef_gmt: Referans saat (örn: 12:00)
        :param alternatif_gmtler: Kontrol edilecek saatler listesi
        :param otomat_veri_mi: Otomatik veriler için katı kural
        :return: (eşlesen_gmt, fark_dakika, açıklama) veya (None, None, "Uygun eşleşme bulunamadı")
        """
        hedef_st = self.gmt_saat_normalize_et(hedef_gmt)
        if hedef_st is None:
            return None, None, "Hedef saat geçersiz"
        
        en_yakin = None
        en_kucuk_fark = float('inf')
        
        for alt_gmt in alternatif_gmtler:
            alt_st = self.gmt_saat_normalize_et(alt_gmt)
            if alt_st is None:
                continue
            
            fark = self.saat_farki_hesapla(hedef_st, alt_st)
            
            if fark is not None and fark < en_kucuk_fark:
                en_kucuk_fark = fark
                en_yakin = alt_gmt
        
        if en_yakin is None:
            return None, None, "Uygun eşleşme bulunamadı"
        
        eslestirilebilir, aciklama, _ = self.saatler_esilestirilebilir_mi(
            hedef_gmt, en_yakin, otomat_veri_mi
        )
        
        return en_yakin, en_kucuk_fark, aciklama


def otomat_veriler_eslestirilebilir_mi(metar_gmt, sinoptik_gmt, tolerans_dakika=15):
    """
    Rüzgar, basınç, sıcaklık gibi otomatik veriler için hızlı kontrol.
    
    Kullanım örneği:
        eslestir = otomat_veriler_eslestirilebilir_mi(0, 2350)  # 00:00 vs 23:50
        # True döner (50 dakika fark ama gün sınırını aşıyor, gerçek fark 10 dakika)
    """
    eslestirici = SaatEslestirici(tolerans_dakika)
    eslestir_mi, _, _ = eslestirici.saatler_esilestirilebilir_mi(
        metar_gmt, sinoptik_gmt, otomat_veri_mi=True
    )
    return eslestir_mi


# Test ve Demo
if __name__ == "__main__":
    eslestirici = SaatEslestirici(tolerans_dakika=15)
    
    print("=" * 60)
    print("SAAT EŞLEŞTİRME MODÜLÜ - TEST")
    print("=" * 60)
    
    # Test Senaryoları
    test_durumlar = [
        (0, 2350, "Gece yarısı geçişi (00:00 vs 23:50)"),
        (3, 0, "Ara rasat ile ana rasat (03:00 vs 00:00)"),
        (12, 12, "Tam eşleşme (12:00 vs 12:00)"),
        (12, 1130, "Yaklaşık eşleşme (12:00 vs 11:30)"),
        (6, 3, "Geniş fark (06:00 vs 03:00)"),
    ]
    
    for metar_gmt, sinoptik_gmt, aciklama in test_durumlar:
        eslestir_mi, msg, fark = eslestirici.saatler_esilestirilebilir_mi(metar_gmt, sinoptik_gmt)
        print(f"\n{aciklama}")
        print(f"  METAR: {metar_gmt:02d}:00  SİNOPTİK: {sinoptik_gmt:02d}:00")
        print(f"  Fark: {fark} dakika")
        print(f"  Sonuç: {'✓ UYUM' if eslestir_mi else '✗ UYUMSUZ'} - {msg}")
