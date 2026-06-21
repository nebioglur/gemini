"""
╔══════════════════════════════════════════════════════════════════════════╗
║                     HIZLI REFERANS KILAVUZU                             ║
║            Otomatik Veri Saat Eşleştirme Sistemi (v2.0)                 ║
╚══════════════════════════════════════════════════════════════════════════╝

[SORU] 23:50 METAR ve 00:00 SİNOPTİK'te sıcaklık farkı var - bu hata mı?
[CEVAP] Hayır! Saatler eşleşti sayılır (10 dakika fark). Eğer sıcaklıklar 
        1.2°C'den fazla farklıysa → HATA. Aksi takdirde → OK.

[SORU] Sistem nasıl saat eşleştirmesi yapıyor?
[CEVAP] Gün sınırını göz önüne alarak en kısa zamansal mesafeyi hesaplar.
        23:50 → 00:30 = 40 dakika (doğru hesap)

[SORU] Tolerans değeri nedir?
[CEVAP] Otomatik veriler (rüzgar, basınç, sıcaklık): 15 dakika
        Gözlemsel veriler (bulut, görüş, vb): 60 dakika

[SORU] Tolerans dışında saatler varsa ne oluyor?
[CEVAP] Veriler karşılaştırılmaz - HATA verilmez.
        (Farklı gözlem dönemlerinin rasatı olarak kabul edilir)

[SORU] Sistem hala hata yakalar mı?
[CEVAP] Evet! Eğer saatler eşleşiyorsa ve değerler farklıysa → HATA.
        Birim hataları, gözlemsel uyumsuzluklar da yine raporlanır.

═══════════════════════════════════════════════════════════════════════════

                        ⚙️ SİSTEM DİYAGRAMI

    METAR (23:50)              SİNOPTİK (00:00)
         │                           │
         └───────────┬───────────────┘
                     │
        Saat Eşleştirme Motoru
        (saat_eslestirme.py)
                     │
         ┌───────────┴───────────┐
         │                       │
    Fark 15 dakika?          Tolerans dışı?
    Saatler eşleşir          Kontrol yapılmaz
         │                      │
         ▼                       ▼
    Veriler kontrol et      Rasat görmezden gel
    Hata raporla                │
                           HATA YOK
═══════════════════════════════════════════════════════════════════════════

                    🔍 HATA RAPOR ÖRNEK MESAJLARI

✗ HATA BELİRTİSİ 1:
  "Sıcaklık Uyumsuzluğu (SAATLER EŞLEŞTİ): Sin(T)=25°C, Met(Kuru)=27°C (5dk fark)"
  → Saatler eşleşti, değerler tolerans dışı fark → GERÇEK HATA

✓ HATA YOK 1:
  Sıcaklık: 25°C vs 26°C, Saatler: 03:00 vs 00:00
  → 180 dakika fark (tolerans dışı) → Kontrol yapılmaz

✗ HATA BELİRTİSİ 2:
  "KRİTİK BİRİM HATASI: SİNOPTİK ff=10, METAR Hız=10"
  → Knot vs m/s karışması (birim hatası) → HATA

═══════════════════════════════════════════════════════════════════════════

                   🛠️ KODDA NASIL KULLANILIR?

1. WeatherLogValidator'ı çağırmak:
   ────────────────────────────────
   from validator import WeatherLogValidator

   v = WeatherLogValidator(
       sin_row={'T': 25, 'ff': 5, ...},
       met_row={'Kuru': 26, 'Hız': 10, ...},
       metar_gmt=2350,    # 23:50 UTC
       sinoptik_gmt=0     # 00:00 UTC
   )
   hatalar = v.run_all_checks()

2. Direkt saat eşleştirmesi:
   ──────────────────────────
   from saat_eslestirme import SaatEslestirici

   e = SaatEslestirici(tolerans_dakika=15)
   eslesir, msg, fark = e.saatler_esilestirilebilir_mi(
       metar_gmt=2350,
       sinoptik_gmt=0,
       otomat_veri_mi=True
   )
   print(f"Eşleşiyor: {eslesir} ({fark} dakika)")

3. Hızlı kontrol:
   ──────────────
   from saat_eslestirme import otomat_veriler_eslestirilebilir_mi

   if otomat_veriler_eslestirilebilir_mi(2350, 0):
       # Veriler karşılaştırılabilir
       pass

═══════════════════════════════════════════════════════════════════════════

                    📊 TEST SONUÇLARI (Özet)

Test Adı                          GMT1   GMT2   Fark    Sonuç
─────────────────────────────────────────────────────────────
Gece Yarısı (gün sınırı)          00:00  23:50   10dk    ✅ EŞLEŞ
Tam Eşleşme                        12:00  12:00   0dk     ✅ EŞLEŞ
30 Dakika Fark                     12:00  11:30  30dk     ❌ EŞ.DEĞİL
3 Saat Fark                        06:00  03:00 180dk     ❌ EŞ.DEĞİL
3 Saatlik Ara Rasat                03:00  00:00 180dk     ❌ EŞ.DEĞİL

═══════════════════════════════════════════════════════════════════════════

                  📋 DOSYA VE FONKSİYON ÖZETI

Dosya: saat_eslestirme.py
────────────────────────
✓ SaatEslestirici                - Ana sınıf
  - gmt_saat_normalize_et()      - Saat formatlarını normalize et
  - saat_farki_hesapla()         - İki saat arasındaki fark
  - saatler_esilestirilebilir_mi()  - Eşleşme kontrolü
  - en_yakin_eslesmeyi_bul()     - En yakın eşleşme ara

✓ otomat_veriler_eslestirilebilir_mi()  - Hızlı kontrol fonksiyonu

Dosya: validator.py
──────────────────
✓ WeatherLogValidator
  - __init__(sin_row, met_row, metar_gmt, sinoptik_gmt)
  - check_temperature()          - ✅ Güncellendi
  - check_dewpoint()             - ✅ Güncellendi
  - check_humidity()             - ✅ Güncellendi
  - check_pressure()             - ✅ Güncellendi
  - check_pressure_reduction()   - ✅ Güncellendi
  - check_wind_speed()           - ✅ Güncellendi
  - check_wind_unit()            - ✅ Güncellendi
  - check_wind_dir()             - ✅ Güncellendi
  - run_all_checks()             - ✅ Güncellendi

═══════════════════════════════════════════════════════════════════════════

                        🎯 DEV CHECKLIST

Yeni kod yazerken kontrol et:
☐ WeatherLogValidator'ı metar_gmt ve sinoptik_gmt ile çağrıyor musunuz?
☐ Saat formatları tutarlı mı? (0-23, string, 1430 formatı)
☐ Gün sınırı geçişleri test ettiniz mi?
☐ Tolerans değerini ayarladınız mı?
☐ Hata mesajlarında saat bilgisi var mı?

═══════════════════════════════════════════════════════════════════════════

                    ❓ SIKI SORULAR & CEVAPLAR

S: 15 dakika neden tolerans olarak seçildi?
C: Meteoroloji rasatlarında sistem senkronizasyon ve iletim gecikmesi nedeniyle
   15 dakika içindeki farklar normal kabul edilir.

S: Gün sınırı geçişi nasıl hesaplanıyor?
C: Gün 1440 dakikadır. 23:50=1430 dakika, 00:30=30 dakika.
   Doğru fark = min(|1430-30|, 1440-|1430-30|) = min(1400, 40) = 40 dakika

S: Eski kodlar çalışır mı?
C: Evet! GMT parametreleri verilmezse, sistem eski kurallara döner.

S: Hata payı %kaçtır?
C: Yaklaşık 1/3600 = 0.03% (15 dakika / 12 saatlik gözlem periyodu)
   Kabul edilebilir bir toleranstır.

S: Diğer meteoroloji parametreleri nasıl kontrol edilir?
C: Gözlemsel veriler (bulut, hadise, vb.) daha esnek kontrol edilir (60 dakika).

═══════════════════════════════════════════════════════════════════════════

                    🚀 QUICK START (3 ADİM)

1. Kodunuza import ekleyin:
   from validator import WeatherLogValidator
   from saat_eslestirme import SaatEslestirici

2. GMT saatleri ile validator çağırın:
   validator = WeatherLogValidator(sin, met, metar_gmt=gmt1, sinoptik_gmt=gmt2)

3. Kontrolleri çalıştırın:
   hatalar = validator.run_all_checks()

═══════════════════════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    print(__doc__)
