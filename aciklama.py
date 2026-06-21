"""
METEOROLOJİ DENETİM SİSTEMİ - PROJE AÇIKLAMASI

Bu proje, meteorolojik gözlem verilerini (Sinoptik ve METAR) okuyarak,
belirlenen kurallar çerçevesinde denetleyen ve sonuçları raporlayan bir otomasyon sistemidir.

SİSTEMİN ÇALIŞMA MANTIĞI VE MODÜLLER:

1. ARAYÜZ VE AKIŞ KONTROLÜ (arayuz.py)
   - Kullanıcıdan Tkinter arayüzü ile dosya seçimlerini (Sinoptik, METAR) alır.
   - Raporlanacak Yıl ve Ay bilgisini ister.
   - Ana işlem döngüsünü (Thread) başlatır ve diğer modülleri sırasıyla çağırır.
   - İşlem sonucunda oluşan Excel raporunu otomatik olarak açar.
   - Ayrıca işlem özetini ve hatalı kayıtları konsola yazdırır.

2. VERİ OKUMA VE NORMALİZASYON (denetim_merkezi_1.py)
   - `dosya_oku_akilli` fonksiyonu ile Excel, HTML veya Metin formatındaki dosyaları okur.
   - Dosya formatı ne olursa olsun (farklı başlık satırları, farklı sayfa yapıları) veriyi standart bir DataFrame'e dönüştürür.
   - Sütun isimlerini `sutun_adi_normalize_et` fonksiyonu ile standartlaştırır (Örn: 'Temp', 'Sıcaklık' -> 't').
   - Ham SYNOP kodlarını (`parse_synop_line`) ayrıştırarak anlamlı verilere dönüştürür.
   - Excel sayfa isimlerinden (Sheet1, Sayfa 01 vb.) tarih bilgisi türetir.

3. HATA ANALİZİ VE DENETİM (denetim_merkezi_2.py)
   - `hata_analizi_yap` fonksiyonu ile birleştirilmiş veriyi satır satır tarar.
   - `kurallar.py` dosyasındaki hata tanımlarını ve limitlerini kullanır.
   - Başlıca kontroller:
     * Tutarlılık Kontrolleri: (Örn: Yağış var ama bulut yok, Sıcaklık < 0 ama yağmur yağıyor vb.)
     * Limit Kontrolleri: (Örn: Sıcaklık > 60 derece olamaz, Basınç 800-1100 hPa arası olmalı)
     * Çapraz Kontrol: Sinoptik verisi ile METAR verisini karşılaştırır (Örn: Sinoptikte yağış yok ama METAR'da yağış raporlanmış).
     * Eksik Veri Kontrolü: Zorunlu grupların (Sıcaklık, Basınç vb.) varlığını denetler.

4. RAPORLAMA VE ÇIKTI (denetim_merkezi_3.py)
   - Analiz sonuçlarını Excel dosyasına yazar.
   - `openpyxl` kütüphanesi kullanılarak görselleştirme yapar:
     * Hatalı hücreleri kırmızı, veri olmayan hücreleri gri boyar.
     * Özet sayfası oluşturur ve hata istatistiklerini grafik (Bar Chart) olarak ekler.
     * Her hata türü için ayrı sekmeler oluşturarak detaylı inceleme imkanı sunar.
   - Dosya isimlendirmesini çakışmaları önleyecek şekilde yapar (Örn: DENETIM_2025_01 (1).xlsx).

5. KURALLAR (kurallar.py)
   - Hata kodlarını (h1, h2... h266) ve bunlara karşılık gelen açıklama metinlerini içeren sözlük yapısıdır.

NASIL ÇALIŞTIRILIR?
- `arayuz.py` dosyası çalıştırılır.
- Açılan pencereden "RAPOR OLUŞTUR" butonuna basılır.
- İstenen dosyalar ve tarih bilgileri girilir.
- Program işlemi tamamladığında Excel raporu açılır ve konsolda özet bilgi görüntülenir.
"""

def proje_ozeti_yazdir():
    print(__doc__)

if __name__ == "__main__":
    proje_ozeti_yazdir()