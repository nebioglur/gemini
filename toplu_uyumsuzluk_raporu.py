import os
import re
from datetime import datetime

def _get_safe_user_dir():
    """Güvenli bir şekilde kullanıcının ana dizinini bulur (örn: C:\\Users\\kullanici)."""
    for p in [os.environ.get("USERPROFILE"), os.path.expanduser("~"), os.environ.get("PUBLIC")]:
        if p and os.path.exists(p):
            return p
    # Hiçbiri bulunamazsa, betiğin çalıştığı klasörü varsay
    return os.path.dirname(os.path.abspath(__file__))

# --- AYARLAR ---
# Yıl ve klasör yollarını buradan değiştirebilirsiniz.
YEAR = "2025"
USER_DATA_DIR = os.path.join(_get_safe_user_dir(), "KardelenLogs")
SOURCE_DIR = os.path.join(USER_DATA_DIR, "Aylik_Kayitlar", YEAR)
OUTPUT_FILE = os.path.join(SOURCE_DIR, f"{YEAR}_UYUMSUZ.txt")

# Türkçe ayları doğru sıralamak için
MONTH_ORDER = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

def topla_uyumsuz_rasatlar():
    """
    Belirtilen yıldaki tüm aylık log dosyalarını tarar, 'UYUMSUZ' ve 'F/UYUMSUZ'
    kayıtlarını bulur ve tek bir dosyada birleştirir.
    """
    if not os.path.exists(SOURCE_DIR):
        print(f"HATA: Kaynak klasör bulunamadı: {SOURCE_DIR}")
        return

    print(f"Kaynak klasör taranıyor: {SOURCE_DIR}")
    
    all_incompatible_blocks = []
    
    # Ayları doğru sırada işlemek için dosyaları sırala
    try:
        monthly_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.txt') and f.replace('.txt', '') in MONTH_ORDER]
        monthly_files.sort(key=lambda f: MONTH_ORDER.index(f.replace('.txt', '')))
    except ValueError:
        # Eğer listede olmayan bir ay ismi varsa (örn: "Ocak_raw.json"), hata vermeden devam et
        monthly_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.txt')]
        print("Uyarı: Dosya isimleri standart ay isimleriyle eşleşmiyor, alfabetik sıralama yapılıyor.")


    for filename in monthly_files:
        file_path = os.path.join(SOURCE_DIR, filename)
        month_name = filename.replace('.txt', '')
        print(f"-> İşleniyor: {filename}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Kayıtları ayırıcıya ('----------') göre böl
            blocks = re.split(r'(-{50,}\n)', content)
            
            # blocks listesi şöyle olur: [header, separator1, content1, separator2, content2, ...]
            # Bu yüzden 1'den başlayıp 2'şer atlayarak geziyoruz.
            for i in range(1, len(blocks), 2):
                separator = blocks[i]
                block_content = blocks[i+1]
                
                # Blok içinde uyumsuzluk anahtar kelimelerini ara
                if "DURUM: UYUMSUZ" in block_content or "DURUM: F/UYUMSUZ" in block_content:
                    # Ay başlığını bloğun başına ekle
                    header = f"\n{'='*20} {month_name.upper()} AYINDAN {'='*20}\n"
                    full_block = header + separator + block_content
                    all_incompatible_blocks.append(full_block)
        except Exception as e:
            print(f"  !! Hata ({filename}): {e}")

    if not all_incompatible_blocks:
        print("\nHiç uyumsuz kayıt bulunamadı.")
        return

    print(f"\nToplam {len(all_incompatible_blocks)} uyumsuz kayıt bulundu.")
    
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(f"{YEAR} YILI UYUMSUZ RASATLAR TOPLU RAPORU\n")
            f.write(f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
            f.write("="*70 + "\n")
            
            for block in all_incompatible_blocks:
                f.write(block)
                
        print(f"\n✅ Rapor başarıyla oluşturuldu: {OUTPUT_FILE}")
        # Kullanıcıya dosyayı açma seçeneği sun
        if input("Rapor dosyasını şimdi açmak ister misiniz? (e/h): ").lower() == 'e':
            os.startfile(OUTPUT_FILE)
            
    except Exception as e:
        print(f"\n❌ Rapor dosyası yazılırken hata oluştu: {e}")

if __name__ == "__main__":
    topla_uyumsuz_rasatlar()
    input("\nİşlem tamamlandı. Çıkmak için Enter'a basın...")
