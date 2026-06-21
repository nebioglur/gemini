import sys
import subprocess
def ensure_lxml():
    try:
        import lxml
        import html5lib
    except ImportError:
        print("HTML Ayrıştırma motorları (lxml, html5lib) eksik. Otomatik yükleniyor...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "lxml", "html5lib"])
            print("Yükleme başarılı!")
        except Exception as e:
            print(f"Yükleme hatası: {e}")
ensure_lxml()

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
import threading
import datetime
import calendar
import os
import re
import traceback
import glob
import logging
import json
import shutil
import time
import kurallar
import sys
import zipfile

# --- BAD CRC-32 (BOZUK EXCEL) BYPASS HACK ---
# Bazı kurumsal sistemlerin ürettiği Excel dosyalarının iç yapısında (docProps/core.xml vb.) CRC hataları olabilir.
# Python'un zipfile kütüphanesinin bu durumda çökmesini engellemek için CRC kontrolünü esnetiyoruz.
try:
    if hasattr(zipfile, 'ZipExtFile') and hasattr(zipfile.ZipExtFile, '_update_crc'):
        if not getattr(zipfile.ZipExtFile, '_crc_patched', False):
            _orig_update_crc = zipfile.ZipExtFile._update_crc
            def _patched_update_crc(self, newdata):
                self._expected_crc = None  # Zorla CRC kontrolünü kapat (BadZipFile hatasını önler)
                return _orig_update_crc(self, newdata)
            zipfile.ZipExtFile._update_crc = _patched_update_crc
            zipfile.ZipExtFile._crc_patched = True
except Exception:
    pass
# --------------------------------------------

# --- RENKLİ KONSOL ÇIKTISI İÇİN ---
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# --- SYNOP_DECODER ENTEGRASYONU ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
try:
    from synop_decoder import SynopDecoder
except ImportError:
    SynopDecoder = None

try:
    from metar_decoder import MetarDecoder
except ImportError:
    MetarDecoder = None
# ----------------------------------

# --- DOSYA ONARIM SİSTEMİ (JOKER / GENEL ÇÖZÜM) ---
def repair_duplicate_blocks():
    if getattr(sys, 'frozen', False):
        return # EXE olarak çalışırken .py dosyaları yoktur, bu adımı atla.
    # Kontrol edilecek dosyalar ve aranan anahtar kelimeler
    files_to_check = [
        ('validator.py', 'class WeatherLogValidator'),
        ('validator.py', 'def run_all_checks(self'),
        ('denetim_merkezi_2.py', 'def hata_analizi_yap'),
        ('synop_decoder.py', 'class SynopDecoder'),
        ('metar_decoder.py', 'class MetarDecoder'),
        ('kurallar.py', 'HATA_SOZLUGU = {')
    ]
    
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        repaired_any = False
        
        for file_name, marker in files_to_check:
            file_path = os.path.join(base_dir, file_name)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Marker'ın (sınıf/fonksiyon tanımı) geçtiği satırları bul
                defs = [i for i, line in enumerate(lines) if marker in line and not line.strip().startswith('#')]
                
                if len(defs) > 1:
                    # Onarımdan önce bozuk dosyanın yedeğini al (.bak uzantılı)
                    backup_path = os.path.join(base_dir, f"{file_name}.bak")
                    shutil.copy2(file_path, backup_path)
                    
                    # İkinci kopyadan sonrasını tamamen silerek dosyayı onar
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines[:defs[1]])
                    repaired_any = True
        
        if repaired_any:
            # Eğer herhangi bir dosya onarıldıysa önbelleği zorla temizle
            cache_dir = os.path.join(base_dir, '__pycache__')
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir, ignore_errors=True)
    except: pass
repair_duplicate_blocks()
# -------------------------------------------------

# --- ÖNBELLEK TEMİZLEME SİSTEMİ ---
def clear_pycache_on_startup():
    """Program her başladığında eski .pyc önbellek dosyalarını otomatik temizler."""
    if getattr(sys, 'frozen', False):
        return # EXE olarak çalışırken pycache temizliğine gerek yoktur.
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cache_dir = os.path.join(base_dir, '__pycache__')
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir, ignore_errors=True)
    except Exception:
        pass
clear_pycache_on_startup()
# -------------------------------------------------

# --- ESKİ GEÇİCİ DOSYALARI TEMİZLEME SİSTEMİ ---
def cleanup_old_temp_files():
    """Eski .bak yedeklerini, log arşivlerini ve geçici Excel (TEMP_, ~$) dosyalarını otomatik temizler."""
    try:
        now = time.time()
        otuz_gun = 30 * 24 * 60 * 60
        yedi_gun = 7 * 24 * 60 * 60
        
        # 1. Uygulama dizinindeki 30 günden eski .bak ve log dosyaları
        base_dir = os.path.dirname(os.path.abspath(__file__))
        for f in os.listdir(base_dir):
            if f.endswith('.bak') or '.log.' in f:
                f_path = os.path.join(base_dir, f)
                if os.path.isfile(f_path) and os.stat(f_path).st_mtime < now - otuz_gun:
                    try: os.remove(f_path)
                    except: pass
                    
        # 2. Çalışma klasöründeki (check) 7 günden eski geçici dosyalar
        check_dir = r"C:\Users\nebio\Desktop\check"
        if os.path.exists(check_dir):
            for f in os.listdir(check_dir):
                f_path = os.path.join(check_dir, f)
                if os.path.isfile(f_path) and (f.startswith("~$") or f.upper().startswith("TEMP_")):
                    if os.stat(f_path).st_mtime < now - yedi_gun:
                        try: os.remove(f_path)
                        except: pass

        # 3. Arşiv klasöründeki (check\Arsiv) 90 günden eski arşiv raporlarını otomatik temizle
        arsiv_dir = r"C:\Users\nebio\Desktop\check\Arsiv"
        doksan_gun = 90 * 24 * 60 * 60
        if os.path.exists(arsiv_dir):
            for root_d, dirs, files in os.walk(arsiv_dir, topdown=False):
                for f in files:
                    f_path = os.path.join(root_d, f)
                    if os.stat(f_path).st_mtime < now - doksan_gun:
                        try: os.remove(f_path)
                        except: pass
                # İçi boşalan arşiv klasörlerini (YYYY_MM) sil
                if not os.listdir(root_d) and root_d != arsiv_dir:
                    try: os.rmdir(root_d)
                    except: pass
    except Exception:
        pass
cleanup_old_temp_files()
# -------------------------------------------------

# --- ESKİ XLS DOSYALARINI SİLME (SADECE EN YENİLERİ TUT) ---
def sadece_en_yeni_dosyalari_tut():
    """CHECK klasöründeki eski tarihli METAR ve SİNOPTİK dosyalarını program açılışında siler."""
    hedef_klasor = r"C:\Users\nebio\Desktop\check"
    if not os.path.exists(hedef_klasor): return
    
    try:
        sin_dosyalari = []
        metar_dosyalari = []
        
        for f in os.listdir(hedef_klasor):
            tam_yol = os.path.join(hedef_klasor, f)
            if not os.path.isfile(tam_yol): continue
            
            f_upper = f.upper()
            if f_upper.startswith("~$") or f_upper.startswith("TEMP_"): continue
            
            if f_upper.endswith('.XLS') or f_upper.endswith('.XLSX') or f_upper.endswith('.HTML') or f_upper.endswith('.CSV'):
                if "SIN" in f_upper or "SİN" in f_upper:
                    sin_dosyalari.append(tam_yol)
                elif "METAR" in f_upper:
                    metar_dosyalari.append(tam_yol)
                    
        # En yenileri bulmak için tarihe göre sırala
        sin_dosyalari.sort(key=os.path.getmtime, reverse=True)
        metar_dosyalari.sort(key=os.path.getmtime, reverse=True)
        
        # En yeni 1 SİNOPTİK hariç diğerlerini sil
        for eski_f in sin_dosyalari[1:]:
            try: os.remove(eski_f)
            except: pass
            
        # En yeni 1 METAR hariç diğerlerini sil
        for eski_f in metar_dosyalari[1:]:
            try: os.remove(eski_f)
            except: pass
    except: pass

sadece_en_yeni_dosyalari_tut()
# -------------------------------------------------

try:
    import validator
    import importlib
    importlib.reload(validator)
except ImportError:
    validator = None

console_mode = False
iptal_istendi = False
btn_cancel = None

def safe_showerror(title, message):
    try:
        if console_mode:
            print(f"ERROR - {title}: {message}")
        else:
            messagebox.showerror(title, message)
    except Exception:
        print(f"ERROR - {title}: {message}")


def safe_showinfo(title, message):
    try:
        if console_mode:
            print(f"INFO - {title}: {message}")
        else:
            messagebox.showinfo(title, message)
    except Exception:
        print(f"INFO - {title}: {message}")

# EXE UYUMLULUĞU: Yetki hatalarını önlemek için Log ve Ayar dosyalarını AppData/Kullanıcı dizinine al
_USER_LOG_DIR = os.path.join(os.path.expanduser("~"), "HATARAMA_Logs")
os.makedirs(_USER_LOG_DIR, exist_ok=True)

# Log dosyasının her zaman arayuz.py ile aynı klasörde olmasını sağla
log_dosyasi = os.path.join(_USER_LOG_DIR, 'denetim_merkezi.log')

# Log dosyasını boyut limitli aç (Maks 5 MB) ve en fazla 2 yedek tut
from logging.handlers import RotatingFileHandler
logging_handler = RotatingFileHandler(log_dosyasi, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
logging_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging_handler]
)

# --- YENİ: GLOBAL HATA YAKALAYICILAR (Ne olursa olsun terminale yazar) ---
def global_exception_handler(exctype, value, tb):
    if issubclass(exctype, KeyboardInterrupt):
        logging.info("Program kullanıcı tarafından sonlandırıldı.")
        return
    logging.error("SİSTEM KRİTİK HATASI (GLOBAL CRASH):", exc_info=(exctype, value, tb))
sys.excepthook = global_exception_handler

def thread_exception_handler(args):
    logging.error("ARKA PLAN İŞLEM HATASI (THREAD CRASH):", exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
threading.excepthook = thread_exception_handler
# -------------------------------------------------------------------------

SETTINGS_FILE = os.path.join(_USER_LOG_DIR, 'ayarlar.json')

def ayarlari_yukle():
    """Kayıtlı ayarları json dosyasından okur."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Ayarlar dosyası okunamadı: {e}")
    return {}

def ayarlari_kaydet(ayarlar):
    """Mevcut seçimleri json dosyasına kaydeder."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(ayarlar, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.warning(f"Ayarlar dosyası kaydedilemedi: {e}")

def get_button_text():
    return "RAPOR OLUŞTUR"

def safe_after(delay, func):
    """Python 3.13 ve Threading kaynaklı 'main thread is not in main loop' hatasını önler."""
    try:
        if not console_mode and 'root' in globals() and root:
            root.after(delay, func)
    except RuntimeError:
        try: func() # Olay döngüsü dışında kalındıysa doğrudan çalıştır
        except: pass

def aylik_rapor_olustur(run_async=True):
    ayarlar = ayarlari_yukle()
    global iptal_istendi
    iptal_istendi = False
    
    # --- UI Geri Bildirimini Başlat ---
    if not console_mode:
        try:
            btn_run.config(state=tk.DISABLED, text="Çalışıyor...")
            if btn_cancel: btn_cancel.config(state=tk.NORMAL)
            lbl_status.config(text="İşlem başlatılıyor...")
            root.config(cursor="watch")
            pb_loading.pack(side="right", padx=5, pady=2)
            pb_loading.start(10)
        except Exception:
            pass

    def islem_yurut():
        # --- OPTİMİZASYON (Gecikmeli Yükleme / Lazy Loading) ---
        # Arayüzün donmasını önlemek için ağır kütüphaneleri arka plan iş parçacığında içe aktarıyoruz.
        global pd, dm1, dm2, dm3, sutun_duzeltici, btn_run, btn_cancel
        import pandas as pd
        import warnings
        warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)
        import denetim_merkezi_1 as dm1
        import denetim_merkezi_2 as dm2
        import denetim_merkezi_3 as dm3
        import sutun_duzeltici

        sin_yolu = None
        metar_yolu = None
        try:
            # Raporlamaya başlamadan hemen önce, eski dosyaları silip sadece en son inen 1 Metar ve 1 Sinoptik bırak:
            sadece_en_yeni_dosyalari_tut()

            # --- Dosya Arama ve Ön İşleme ---
            if not console_mode:
                safe_after(0, lambda: lbl_status.config(text="Dosyalar aranıyor..."))

            if iptal_istendi: raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
            hedef_klasor = r"C:\Users\nebio\Desktop\check"
            if not os.path.exists(hedef_klasor):
                error_msg = f"Hata: Hedef klasör bulunamadı:\n{hedef_klasor}"
                print(f"{Colors.FAIL}{error_msg}{Colors.ENDC}")
                safe_showerror("Hata", error_msg)
                return

            tum_dosyalar = glob.glob(os.path.join(hedef_klasor, "*"))
            sin_dosyalari = []
            metar_dosyalari = []

            for f in tum_dosyalar:
                if not os.path.isfile(f): continue # Klasörleri (Örn: Arsiv) atla
                f_name = os.path.basename(f).upper()
                if f_name.startswith("~$"): continue # Excel'in gizli geçici dosyalarını atla
                if f_name.startswith("TEMP_"): continue # Önceki işlemlerden kalan geçici dosyaları atla

                # İsmin neresinde olursa olsun SIN/SİN veya METAR içeriyorsa kabul et
                if ("SIN" in f_name or "SİN" in f_name) and "DENETIM" not in f_name and f.lower().endswith(('.xls', '.xlsx', '.txt', '.csv', '.htm', '.html')):
                    sin_dosyalari.append(f)
                elif ("METAR" in f_name) and "DENETIM" not in f_name and f.lower().endswith(('.xls', '.xlsx', '.txt', '.csv', '.htm', '.html')):
                    metar_dosyalari.append(f)

            if not sin_dosyalari or not metar_dosyalari:
                bulunan_isimler = [os.path.basename(x) for x in tum_dosyalar if os.path.isfile(x) and not os.path.basename(x).startswith("~$")]
                bulunan_str = "\n".join(bulunan_isimler[:10]) # Çok uzunsa listeyi kısalt
                if len(bulunan_isimler) > 10: bulunan_str += "\n... (ve daha fazlası)"
                if not bulunan_isimler: bulunan_str = "Klasör tamamen boş!"

                if not sin_dosyalari:
                    error_msg = f"SİNOPTİK dosyası bulunamadı!\n\nKlasörde isminde 'SIN' veya 'SİN' geçen bir dosya bulunamadı.\n\nKlasördeki Mevcut Dosyalar:\n{bulunan_str}"
                    print(f"{Colors.FAIL}{error_msg}{Colors.ENDC}")
                    safe_showerror("Hata", error_msg)
                    return
                if not metar_dosyalari:
                    error_msg = f"METAR dosyası bulunamadı!\n\nKlasörde isminde 'METAR' geçen bir dosya bulunamadı.\n\nKlasördeki Mevcut Dosyalar:\n{bulunan_str}"
                    print(f"{Colors.FAIL}{error_msg}{Colors.ENDC}")
                    safe_showerror("Hata", error_msg)
                    return

            sin_yolu = sin_dosyalari[0]
            metar_yolu = metar_dosyalari[0]

            if iptal_istendi: raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
            # --- OTOMATİK SÜTUN DÜZELTİCİ ENTEGRASYONU ---
            if not console_mode:
                safe_after(0, lambda: lbl_status.config(text="Dosyalar düzeltiliyor..."))

            print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")

            yedek_klasoru = os.path.join(hedef_klasor, "orijinal_yedekler")
            if not os.path.exists(yedek_klasoru):
                os.makedirs(yedek_klasoru)

            print(f"{Colors.OKBLUE}Orijinal dosyalar '{yedek_klasoru}' klasörüne yedekleniyor...{Colors.ENDC}")
            for dosya in (sin_dosyalari + metar_dosyalari):
                try:
                    shutil.copy2(dosya, yedek_klasoru)
                except Exception as e:
                    print(f"{Colors.FAIL}Yedekleme Hatası ({os.path.basename(dosya)}): {e}{Colors.ENDC}")
                    traceback.print_exc()

            print(f"{Colors.OKCYAN}SÜTUN DÜZELTİCİ OTOMATİK OLARAK ÇALIŞTIRILIYOR...{Colors.ENDC}")
            for dosya in (sin_dosyalari + metar_dosyalari):
                if hasattr(sutun_duzeltici, "sessiz_duzelt"):
                    try:
                        sutun_duzeltici.sessiz_duzelt(dosya)
                    except Exception as e:
                        print(f"{Colors.FAIL}Hata: {os.path.basename(dosya)} düzeltilemedi - {e}{Colors.ENDC}")
                        traceback.print_exc()
                        raise Exception(f"Sütun Düzeltici Hatası ({os.path.basename(dosya)}):\n{e}")
                else:
                    print(f"{Colors.WARNING}Uyarı: 'sessiz_duzelt' fonksiyonu bulunamadığı için {os.path.basename(dosya)} düzeltilmedi.{Colors.ENDC}")
            print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

            if iptal_istendi: raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
            # --- Ana İşlem ---
            if not console_mode:
                safe_after(0, lambda: lbl_status.config(text="Veriler okunuyor..."))

            import concurrent.futures
            
            # 1. Veri Okuma (Threading ile Paralel İşlem - Performans Artışı)
            print(f"\n{Colors.OKCYAN}Veriler paralel (eşzamanlı) olarak okunuyor, lütfen bekleyin...{Colors.ENDC}")
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_sin = executor.submit(dm1.dosya_oku_akilli, sin_yolu)
                future_metar = executor.submit(dm1.dosya_oku_akilli, metar_yolu)
                
                while not (future_sin.done() and future_metar.done()):
                    if iptal_istendi: raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
                    time.sleep(0.5)
                
                if iptal_istendi: raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
                df_sin = future_sin.result()
                df_metar = future_metar.result()

            # Terminal ekranının taşmasını önlemek için sadece ilk 15 satırı göster
            pd.set_option('display.max_rows', 15)
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 1000)

            # Okunan verilerin boyutlarını ve ilk satırlarını konsola yazdır
            print(f"\n{Colors.HEADER}{'='*50}{Colors.ENDC}")
            print(f"{Colors.BOLD}>>> SİNOPTİK VERİSİ OKUNDU <<<{Colors.ENDC}")
            print(f"Boyut: {len(df_sin)} Satır, {len(df_sin.columns)} Sütun")
            print(df_sin)
            print(f"\n{Colors.BOLD}>>> METAR VERİSİ OKUNDU <<<{Colors.ENDC}")
            print(f"Boyut: {len(df_metar)} Satır, {len(df_metar.columns)} Sütun")
            print(df_metar)
            print(f"{Colors.HEADER}{'='*50}{Colors.ENDC}\n")

            # Diğer işlemlerde performansı etkilememesi için ayarları sıfırla
            pd.reset_option('display.max_rows')
            pd.reset_option('display.max_columns')

            # --- YIL VE AY TESPİTİ ---
            yil, ay = None, None
            
            # 1. Adım: Orijinal dosyanın içinden (J1, K1 vb. hücrelerden) kesin tarihi bul (Kullanıcı İsteği)
            for yol in [sin_yolu, metar_yolu]:
                try:
                    # Sadece ilk 10 satırı okuyarak hücrelerde tarih/ay ara
                    raw = pd.read_excel(yol, sheet_name=0, header=None, nrows=10)
                    for r in range(len(raw)):
                        for c in range(len(raw.columns)):
                            val = str(raw.iloc[r, c]).strip().upper()
                            # GG.AA.YYYY veya GG/AA/YYYY
                            m1 = re.search(r'\b\d{2}[\./-](\d{2})[\./-](\d{4})\b', val)
                            if m1: yil, ay = int(m1.group(2)), int(m1.group(1)); break
                            
                            # YYYY-AA-GG
                            m2 = re.search(r'\b(\d{4})[\./-](\d{2})[\./-]\d{2}\b', val)
                            if m2: yil, ay = int(m2.group(1)), int(m2.group(2)); break
                        if yil and ay: break
                except: pass
                if yil and ay: break

            # 2. Adım: Dosya isimlerinden (örneğin 2026_01 veya 01_2026) tespit etmeye çalış
            if not yil or not ay:
                for yol in [sin_yolu, metar_yolu]:
                    yol_str = os.path.basename(yol).upper()
                    m1 = re.search(r'\b(20[0-2]\d)[_-](0[1-9]|1[0-2])\b', yol_str) # Örn: 2023_05
                    if m1: yil, ay = int(m1.group(1)), int(m1.group(2)); break
                    
                    m2 = re.search(r'\b(0[1-9]|1[0-2])[_-](20[0-2]\d)\b', yol_str) # Örn: 05-2023
                    if m2: ay, yil = int(m2.group(1)), int(m2.group(2)); break
                    
                    aylar_sz = {"OCAK":1, "SUBAT":2, "ŞUBAT":2, "MART":3, "NISAN":4, "NİSAN":4, "MAYIS":5, "HAZIRAN":6, "HAZİRAN":6, "TEMMUZ":7, "AGUSTOS":8, "AĞUSTOS":8, "EYLUL":9, "EYLÜL":9, "EKIM":10, "EKİM":10, "KASIM":11, "ARALIK":12}
                    y_match = re.search(r'\b(20[0-2]\d)\b', yol_str)
                    if y_match:
                        for ay_isim, ay_no in aylar_sz.items():
                            if ay_isim in yol_str: yil, ay = int(y_match.group(1)), ay_no; break
                    if yil and ay: break

            # 3. Adım: Dosya isminden bulunamazsa veri içinden (GG.AA.YYYY) en çok tekrar eden tarihi bul
            if not yil or not ay:
                olasi_tarihler = []
                hedef_sutunlar = ['sayfa', 'tarih', 'kayit', 'kayıt', 'date', 'zaman']
                
                for df in [df_metar, df_sin]:
                    for col in df.columns:
                        if not any(hs in str(col).lower() for hs in hedef_sutunlar):
                            continue
                            
                        # GG.AA.YYYY, GG/AA/YYYY, GG-AA-YYYY formatı
                        sample = df[col].astype(str).str.extract(r'\b\d{2}[\./-](\d{2})[\./-](\d{4})\b').dropna()
                        if not sample.empty:
                            for _, r in sample.iterrows():
                                if 1 <= int(r[0]) <= 12 and 2000 <= int(r[1]) <= 2050:
                                    olasi_tarihler.append((int(r[1]), int(r[0])))
                            
                        # YYYY.AA.GG, YYYY-AA-GG, YYYY/AA/GG formatı
                        sample_rev = df[col].astype(str).str.extract(r'\b(\d{4})[\./-](\d{2})[\./-]\d{2}\b').dropna()
                        if not sample_rev.empty:
                            for _, r in sample_rev.iterrows():
                                if 1 <= int(r[1]) <= 12 and 2000 <= int(r[0]) <= 2050:
                                    olasi_tarihler.append((int(r[0]), int(r[1])))
                
                if olasi_tarihler:
                    from collections import Counter
                    en_cok_gecen = Counter(olasi_tarihler).most_common(1)[0][0]
                    yil, ay = en_cok_gecen[0], en_cok_gecen[1]

            # 4. Adım: Hiçbir şekilde bulunamazsa varsayılan olarak geçerli tarihten bir önceki ayı al
            if not yil or not ay:
                simdi = datetime.datetime.now()
                yil = simdi.year if simdi.month > 1 else simdi.year - 1
                ay = simdi.month - 1 if simdi.month > 1 else 12

            if iptal_istendi: raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
            print(f"\n{Colors.OKGREEN}>>> KULLANILACAK RAPOR DÖNEMİ: {ay:02d}/{yil} <<<{Colors.ENDC}")
            
            if not console_mode and btn_run is not None:
                try:
                    safe_after(0, lambda: btn_run.config(text=f"İşleniyor... ({ay:02d}/{yil})"))
                    safe_after(0, lambda: lbl_status.config(text=f"Dönem: {ay:02d}/{yil} - Veriler işleniyor..."))
                except Exception:
                    pass

            # dm1.tarih_olustur_helper fonksiyonu kullanılarak 1, 2, 3 gibi günlerin
            # kaybolması ve sheet2, sheet4 gibi isimlerin doğru ayrıştırılması sağlanır.

            # Okuma Raporu
            okuma_raporu = ""
            try:
                if not df_sin.empty and "sayfa" in df_sin.columns:
                    sheets = sorted(df_sin["sayfa"].unique().astype(str), key=lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else 0)
                    mapped = []
                    for s in sheets:
                        t = dm1.tarih_olustur_helper(s, yil, ay)
                        if t: mapped.append(f"[{s}] -> {t}")
                    okuma_raporu = "SİNOPTİK SAYFA - TARİH EŞLEŞMELERİ:\n" + "-"*40 + "\n" + ("\n".join(mapped) if mapped else "⚠️ Eşleşme yok")
            except: pass

            # GMT Kontrolü (Sütun İsimlendirme - Temizlikten Önce Yapılmalı)
            if "gmt" not in df_sin.columns:
                # 1. Adım: Birleşik Tarih-Saat (Datetime) sütunu varsa saati oradan ayıkla
                gmt_extracted = False
                for col in list(df_sin.columns):
                    col_str = str(col).lower()
                    if col_str in ["kayıt", "kayit", "kayıt zamanı", "kayit zamani", "tarih", "date", "sayfa"]:
                        try:
                            # Sütunun gerçekten bir saat barındırıp barındırmadığını test et
                            ornek = pd.to_datetime(df_sin[col].dropna().astype(str), errors='coerce')
                            if not ornek.isna().all():
                                if len(ornek.dt.hour.unique()) > 1 or (ornek.dt.hour > 0).any():
                                    df_sin["gmt"] = ornek.dt.hour
                                    gmt_extracted = True
                                    break
                        except: pass

                # 2. Adım: Akıllı GMT Sütunu Bulma (Eğer datetime'dan çıkarılamadıysa)
                gmt_col_found = None
                if not gmt_extracted:
                    for col in df_sin.columns:
                        try:
                            vals = df_sin[col].dropna().unique()
                            target_hours = {0, 3, 6, 9, 12, 15, 18, 21, '00', '03', '06', '09', '12', '15', '18', '21'}
                            match_count = sum(1 for v in vals if v in target_hours)
                            
                            # Sayısal Aralık Kontrolü (0-23 arası mı?) - İstasyon No (17xxx) karışmasını önler
                            is_valid_range = False
                            try:
                                nums = pd.to_numeric(vals, errors='coerce')
                                nums = nums[~pd.isna(nums)]
                                if len(nums) > 0 and nums.min() >= 0 and nums.max() <= 23:
                                    is_valid_range = True
                            except: pass
    
                            if match_count >= 2 or (is_valid_range and len(vals) >= 2):
                                gmt_col_found = col; break
                        except: pass
                
                if gmt_col_found: 
                    df_sin.rename(columns={gmt_col_found: "gmt"}, inplace=True)
                elif not gmt_extracted:
                    # Fallback: Bilinen sütunları atla, ilk uygun sütunu GMT yap
                    known_cols = ['istasyon_no', 'sayfa', 'tarih', 'personel', 'rasatci']
                    for col in df_sin.columns:
                        if str(col).lower() not in known_cols:
                            df_sin.rename(columns={col: "gmt"}, inplace=True)
                            break
            if "gmt" not in df_metar.columns:
                gmt_found = False
                
                # Önce METAR için Datetime saat ayıklama dene
                for col in list(df_metar.columns):
                    col_str = str(col).lower()
                    if col_str in ["kayıt", "kayit", "kayıt zamanı", "kayit zamani", "tarih", "date", "sayfa"]:
                        try:
                            ornek = pd.to_datetime(df_metar[col].dropna().astype(str), errors='coerce')
                            if not ornek.isna().all() and (len(ornek.dt.hour.unique()) > 1 or (ornek.dt.hour > 0).any()):
                                df_metar["gmt"] = ornek.dt.hour
                                gmt_found = True
                                break
                        except: pass

                if not gmt_found and "sayfa" in df_metar.columns:
                    extracted = df_metar["sayfa"].astype(str).str.extract(r'(\d{2}:\d{2}Z?)')[0]
                    if not extracted.isna().all():
                        df_metar["gmt"] = extracted
                        df_metar["sayfa"] = df_metar["sayfa"].astype(str).str.split().str[0]
                        gmt_found = True
                        
                if not gmt_found and len(df_metar.columns) > 0:
                    # Rastgele ilk sütunu almak yerine, gerçekten saat formatına (13:50 veya 1350Z) benzeyen bir sütun bul
                    for col in df_metar.columns:
                        if col == 'sayfa': continue
                        sample = df_metar[col].dropna().astype(str).head(20)
                        if sample.str.contains(r'\d{2}:\d{2}').any() or sample.str.match(r'^\d{3,4}Z?$', flags=re.IGNORECASE).any():
                            df_metar.rename(columns={col: "gmt"}, inplace=True); break
                            
                # YENİ EKLENEN GÜVENLİK: Hala GMT bulunamadıysa çökmemesi için boş oluştur
                if "gmt" not in df_metar.columns:
                    df_metar["gmt"] = "00:00"

            # Veri Temizliği ve Hazırlığı
            for i, df in enumerate([df_sin, df_metar]):
                is_metar = (i == 1) # 1. indeks METAR
                
                # METAR Bülteninden Görüş ve Hadise Ayıklama
                if is_metar:
                    # Eğer "bulten" sütunu yanlışlıkla "M" veya "S" gibi tip harflerini aldıysa düzelt
                    if "bulten" in df.columns:
                        bulten_sample = df["bulten"].dropna().astype(str)
                        if not bulten_sample.empty and bulten_sample.map(len).max() < 10:
                            df.rename(columns={"bulten": "mesaj_tipi"}, inplace=True)

                    if "bulten" not in df.columns:
                        # Gerçek bülten sütununu bul (İçeriği en uzun olan metin sütunu)
                        best_col = None
                        max_len = 0
                        for c in df.columns:
                            if c not in ["sayfa", "gmt", "tarih", "saat"]:
                                sample = df[c].replace(['nan', 'NAN', 'NaN', 'None', 'NONE'], pd.NA).dropna().astype(str)
                                if not sample.empty:
                                    avg_len = sample.map(len).mean()
                                    if avg_len > max_len:
                                        max_len = avg_len
                                        best_col = c
                        if best_col and max_len > 15:
                            df.rename(columns={best_col: "bulten"}, inplace=True)
                                
                    if "bulten" in df.columns:
                        def extract_vis(b):
                            m = re.search(r"\s(\d{4})\s", str(b))
                            return float(m.group(1)) if m else None
                        if "vv" not in df.columns:
                            df["vv"] = df["bulten"].apply(extract_vis)
                        if "ww" not in df.columns:
                            df["ww"] = df["bulten"]

                # Güvenlik Kontrolü: sayfa (Gün/Tarih) sütunu yoksa oluştur
                if "sayfa" not in df.columns:
                    for col in df.columns:
                        if col not in ["gmt", "bulten", "tarih", "saat"]:
                            df.rename(columns={col: "sayfa"}, inplace=True); break
                    if "sayfa" not in df.columns: df["sayfa"] = "1"

                # GÜVENLİK: Excel sayfa ismi yerine, gerçekten bir Tarih/Kayıt sütunu varsa daima onu kullan
                for col in list(df.columns):
                    col_str = str(col).lower()
                    if col_str in ["kayıt", "kayit", "kayıt zamanı", "kayit zamani", "tarih", "date"]:
                        df["sayfa"] = df[col]
                        break

                # Önce Tarih Formatını Düzenle (Tarih kaydırma için gerekli)
                df["sayfa"] = df["sayfa"].astype(str)
                df["sayfa"] = df["sayfa"].apply(lambda x: dm1.tarih_olustur_helper(x, yil, ay))
                
                # KESİN ÇÖZÜM: Dosyadan gelen yıl/ay ile kullanıcının girdiği yıl/ay uyuşmazsa 
                # SİNOPTİK verisi şablonla eşleşemez ve tamamen BOŞ çıkar.
                # Bu yüzden tüm tarihleri kullanıcının arayüzde girdiği YIL ve AYA zorluyoruz!
                def yili_ayi_zorla(tarih_str):
                    if pd.isna(tarih_str): return tarih_str
                    try:
                        dt = pd.to_datetime(tarih_str, format='%d.%m.%Y', errors='coerce')
                        if pd.notna(dt):
                            _, max_gun = calendar.monthrange(yil, ay)
                            safe_day = min(dt.day, max_gun)
                            return pd.Timestamp(year=yil, month=ay, day=safe_day).strftime('%d.%m.%Y')
                    except: pass
                    return tarih_str
                    
                df["sayfa"] = df["sayfa"].apply(yili_ayi_zorla)
                df.dropna(subset=["sayfa"], inplace=True)

                if "gmt" in df.columns:
                    # Saat Temizliği ve Ayrıştırma
                    df["gmt_raw"] = df["gmt"].astype(str).str.upper().str.replace('Z', '').str.strip()
                    
                    if is_metar:
                        # METAR için en yakın Sinoptik saatini bul (0050 -> 00, 2350 -> 00 ertesi gün)
                        def match_time(row):
                            val = str(row["gmt_raw"]).strip()
                            if val.endswith('.0'): val = val[:-2]
                            date_val = row["sayfa"]
                            h, m = 0, 0
                            try:
                                time_match = re.search(r'(\d{1,2}):(\d{2})', val)
                                if time_match: h, m = int(time_match.group(1)), int(time_match.group(2))
                                else:
                                    if ' ' in val:
                                        last_part = val.split()[-1]
                                        if last_part.isdigit() or re.match(r'\d{3,4}Z?', last_part):
                                            val = last_part
                                        
                                    val = re.sub(r'[^0-9]', '', val)
                                    if len(val) >= 4: h, m = int(val[-4:-2]), int(val[-2:])
                                    elif len(val) == 3: h, m = int(val[:1]), int(val[1:])
                                    elif val.isdigit() and len(val) <= 2: h, m = int(val), 0
                                    else: return None, None, None
                            except: return None, None, None

                            orig_h, orig_m = h, m

                            # Dakika 40'tan büyükse bir sonraki saate yuvarla (Örn: 23:50 -> 24:00)
                            if m >= 40:
                                h += 1
                                
                            if h >= 24:
                                h = 0
                                try:
                                    dt = pd.to_datetime(date_val, format="%d.%m.%Y") + datetime.timedelta(days=1)
                                    date_val = dt.strftime("%d.%m.%Y")
                                except: pass
                            
                            exact_gmt = f"{orig_h:02d}{orig_m:02d}"
                            return float(h), date_val, exact_gmt

                        if not df.empty:
                            res = df.apply(match_time, axis=1, result_type='expand')
                            if isinstance(res, pd.DataFrame) and 0 in res.columns and 1 in res.columns:
                                df["gmt"] = res[0]
                                df["sayfa"] = res[1]
                                df["gmt_exact"] = res[2] if 2 in res.columns else float('nan')
                    else:
                        # Sinoptik
                        def fix_sinoptik_time(row):
                            v = str(row["gmt_raw"]).strip()
                            date_val = row["sayfa"]
                            if not v or v.upper() == 'NAN' or v.upper() == 'NONE':
                                return float('nan'), date_val, float('nan')

                            h = None
                            m = 0
                            time_match = re.search(r'\b(\d{1,2}):(\d{2})', v)
                            if time_match:
                                h = int(time_match.group(1))
                                m = int(time_match.group(2))
                            else:
                                if ' ' in v:
                                    last_part = v.split()[-1]
                                    if last_part.isdigit() or re.match(r'\d{3,4}Z?', last_part):
                                        v = last_part
                                
                                match = re.match(r'^\d+', v)
                                if match:
                                    ext = match.group(0)
                                    if len(ext) == 6: h = int(ext[2:4])
                                    elif len(ext) == 5: h = int(ext[2:4])
                                    elif len(ext) >= 3: h = int(ext[:2]); m = int(ext[2:4]) if len(ext)>=4 else 0
                                    else: h = int(ext)
                                else:
                                    try: h = int(float(v))
                                    except: return float('nan'), date_val, float('nan')

                            if h is not None:
                                orig_h = h
                                orig_m = m
                                if h >= 24:
                                    h = 0
                                    try:
                                        dt = pd.to_datetime(date_val, format="%d.%m.%Y") + datetime.timedelta(days=1)
                                        date_val = dt.strftime("%d.%m.%Y")
                                    except: pass
                                exact_gmt = f"{orig_h:02d}{orig_m:02d}"
                                return float(h), date_val, exact_gmt
                            return float('nan'), date_val, float('nan')

                        if not df.empty:
                            res = df.apply(fix_sinoptik_time, axis=1, result_type='expand')
                            if isinstance(res, pd.DataFrame) and 0 in res.columns and 1 in res.columns:
                                df["gmt"] = res[0]
                                df["sayfa"] = res[1]
                                df["gmt_exact"] = res[2] if 2 in res.columns else float('nan')

                    df.dropna(subset=["gmt"], inplace=True)
                
                numeric_cols = ['ir', 'ix', 'rrr', 'ww', 'w1', 'w2', 't', 'td', 'n', 'nh', 'cl', 'cm', 'ch', 'dd', 'ff', 'vv', 'a', 'ppp', 'tx', 'tn', 'tg', 'p', 'p0', 'e', 'h', 'tr', 'g924', 'g910', 'g911', 'g931', 'g932', 'g960', 'rh']
                for col in numeric_cols:
                    # Eğer zorunlu bir meteorolojik sütun veride hiç yoksa çökmeyi önlemek için boş olarak ekle
                    if col not in df.columns:
                        df[col] = float('nan')

                    if col in df.columns:
                        if df[col].dtype == 'object':
                            # 1. Görünmez karakterleri (non-breaking space vb.) ve boşlukları temizle
                            df[col] = df[col].astype(str).str.replace(r'[\xa0\u200b]', '', regex=True).str.strip()
                            # 2. Virgülü noktaya çevir
                            df[col] = df[col].str.replace(',', '.', regex=False)
                            # 3. 'nan' metinlerini gerçek NaN'a dönüştür
                            df[col] = df[col].replace(['nan', 'NAN', 'None', 'NONE', '', '-', ' - '], float('nan'))
                        
                        if is_metar and col in ['ww', 'ww2', 'ww3']:
                            pass # METAR'da halihazır hava metin (RA, BR vb.) olabilir, sayısal değere zorlama
                        else:
                            if df[col].dtype == 'object':
                                # 4. Hücreye yanlışlıkla "15 C" veya "1012 hPa" gibi metin girilmişse sadece sayıyı kurtar
                                mask = df[col].notna()
                                df.loc[mask, col] = df.loc[mask, col].astype(str).str.extract(r'([+-]?\d+\.?\d*)', expand=False)
                                
                            df[col] = pd.to_numeric(df[col], errors="coerce")

            # Eşleşme sorunlarını (Veri Yok hatasını) önlemek için tarih formatlarını (%d.%m.%Y) ve saat tiplerini (float) GARANTİYE alıyoruz
            df_sin["sayfa"] = pd.to_datetime(df_sin["sayfa"], format='%d.%m.%Y', errors='coerce').dt.strftime('%d.%m.%Y')
            df_sin["gmt"] = pd.to_numeric(df_sin["gmt"], errors='coerce').astype(float)
            if "sayfa" in df_sin.columns:
                df_sin["sayfa"] = pd.to_datetime(df_sin["sayfa"], format='%d.%m.%Y', errors='coerce').dt.strftime('%d.%m.%Y')
            if "gmt" in df_sin.columns:
                df_sin["gmt"] = pd.to_numeric(df_sin["gmt"], errors='coerce').astype(float)
            
            df_metar["sayfa"] = pd.to_datetime(df_metar["sayfa"], format='%d.%m.%Y', errors='coerce').dt.strftime('%d.%m.%Y')
            df_metar["gmt"] = pd.to_numeric(df_metar["gmt"], errors='coerce').astype(float)
            if "sayfa" in df_metar.columns:
                df_metar["sayfa"] = pd.to_datetime(df_metar["sayfa"], format='%d.%m.%Y', errors='coerce').dt.strftime('%d.%m.%Y')
            if "gmt" in df_metar.columns:
                df_metar["gmt"] = pd.to_numeric(df_metar["gmt"], errors='coerce').astype(float)

            # Gruplama esnasında first() metodunun boş stringleri alıp asıl metni ezmemesi için boş hücreleri gerçek NaN yap
            df_metar.replace(r'^\s*-\s*$', pd.NA, regex=True, inplace=True)
            df_metar.replace(r'^\s*$', pd.NA, regex=True, inplace=True)
            df_sin.replace(r'^\s*-\s*$', pd.NA, regex=True, inplace=True)
            df_sin.replace(r'^\s*$', pd.NA, regex=True, inplace=True)

            if iptal_istendi: raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
            if '_raw_line' in df_sin.columns:
                df_sin['_raw_line'] = df_sin['_raw_line'].apply(lambda x: float('nan') if pd.isna(x) or str(x).strip().lower() in ['', 'nan', 'none', '-', '<na>'] else str(x).strip())

            if '_raw_line' in df_metar.columns:
                df_metar['_raw_line'] = df_metar['_raw_line'].apply(lambda x: float('nan') if pd.isna(x) or str(x).strip().lower() in ['', 'nan', 'none', '-', '<na>'] else str(x).strip())
                if 'bulten' in df_metar.columns:
                    df_metar['bulten'] = df_metar['bulten'].apply(lambda x: float('nan') if pd.isna(x) or str(x).strip().lower() in ['', 'nan', 'none', '-', '<na>'] or len(str(x).strip()) < 10 else str(x).strip())
                    df_metar['bulten'] = df_metar['bulten'].fillna(df_metar['_raw_line'])
                else:
                    df_metar['bulten'] = df_metar['_raw_line']

            # KESİN GÜVENLİK: Pandas 'sayfa' veya 'gmt' sütun eksikliğinden dolayı programın çökmemesi için
            if "sayfa" not in df_sin.columns: df_sin["sayfa"] = "1"
            if "gmt" not in df_sin.columns: df_sin["gmt"] = 0.0
            if "sayfa" not in df_metar.columns: df_metar["sayfa"] = "1"
            if "gmt" not in df_metar.columns: df_metar["gmt"] = 0.0

            if df_sin.empty:
                raise ValueError("Sinoptik verileri işlendikten sonra boş kaldı! Tarih veya Saat sütunları okunamamış olabilir.\nLütfen Excel sayfa isimlerinin (1, 2, 3...) veya tarih formatının doğru olduğundan emin olun.")

            # Rasatlar Sütunu
            if not df_sin.empty:
                def raw_rasat_olustur(row):
                    if 'bulten' in row and pd.notna(row['bulten']) and str(row['bulten']).strip().lower() not in ["", "nan", "none"]:
                        return str(row['bulten'])
                    if '_raw_line' in row and pd.notna(row['_raw_line']) and str(row['_raw_line']).strip().lower() not in ["", "nan", "none"]:
                        return str(row['_raw_line'])

                    items = []
                    exclude = ['sayfa', 'gmt', 'tarih', 'istasyon_no', 'personel', 'g924', 'hadise_kayit', 'gmt_raw', '_raw_line', 'bulten']
                    for col in df_sin.columns:
                        if col not in exclude:
                            val = row.get(col)
                            if pd.notna(val):
                                val_str = str(val).strip()
                                if val_str:
                                    col_name = str(col).upper()
                                    if "UNNAMED" in col_name: items.append(val_str)
                                    else: items.append(f"{col_name}:{val_str}")
                    return " ".join(items)
                df_sin["RASATLAR"] = df_sin.apply(raw_rasat_olustur, axis=1)

            # Sadece geçerli Sinoptik saatlerini filtrele ve tekrarları temizle
            df_sin = df_sin[df_sin["gmt"].isin([0.0, 3.0, 6.0, 9.0, 12.0, 15.0, 18.0, 21.0])]
            df_sin = df_sin.drop_duplicates(subset=["sayfa", "gmt"])
            if "gmt" in df_sin.columns:
                df_sin = df_sin[df_sin["gmt"].isin([0.0, 3.0, 6.0, 9.0, 12.0, 15.0, 18.0, 21.0])]
            if "sayfa" in df_sin.columns and "gmt" in df_sin.columns:
                df_sin = df_sin.drop_duplicates(subset=["sayfa", "gmt"])

            sinoptik_sayisi = len(df_sin)
            metar_sayisi = len(df_metar)
            
            # SPECI ve METAR ayrımı
            speci_sayisi = 0
            metar_normal_sayisi = metar_sayisi
            
            speci_mask = pd.Series(False, index=df_metar.index)
            if "mesaj_tipi" in df_metar.columns:
                speci_mask = speci_mask | df_metar["mesaj_tipi"].astype(str).str.contains(r'\b(SPECI|SP|S)\b', case=False, na=False)
            
            b_col_m = "bulten" if "bulten" in df_metar.columns else "_raw_line"
            if b_col_m in df_metar.columns:
                speci_mask = speci_mask | df_metar[b_col_m].astype(str).str.contains(r'\bSPECI\b', case=False, na=False)
                
            # YENİ: Dakikası 50, 20 veya 00 olmayan rasatları da SPECI (Özel Rasat) kabul et
            if 'gmt_exact' in df_metar.columns:
                gmt_exact_str = df_metar['gmt_exact'].astype(str)
                dakika_mask = ~gmt_exact_str.str.endswith(('50', '20', '00', 'nan', 'NAN', 'None'))
                speci_mask = speci_mask | dakika_mask
                
            speci_sayisi = int(speci_mask.sum())
            metar_normal_sayisi = metar_sayisi - speci_sayisi

            # Şablon ve Birleştirme
            _, son_gun = calendar.monthrange(yil, ay)
            sablon_data = []
            for d in range(1, son_gun + 1):
                t_str = pd.Timestamp(year=yil, month=ay, day=d).strftime('%d.%m.%Y')
                for h in range(24): # 23:50'ler ertesi gün 0'a devredeceği için şablon tekrar standart 24 saate (0-23) döndürüldü
                    sablon_data.append({"sayfa": t_str, "gmt": float(h)})
            df_sablon = pd.DataFrame(sablon_data)

            # --- KESİN ÇÖZÜM (REINDEXING HATASI İÇİN): SÜTUNLARI VE İNDEKSLERİ TEMİZLE ---
            for df_temp in [df_sin, df_metar]:
                df_temp.reset_index(drop=True, inplace=True) # İndeks çakışmalarını önler
                if any(df_temp.columns.duplicated()):
                    cols = pd.Series(df_temp.columns)
                    for dup in cols[cols.duplicated()].unique():
                        dup_indices = cols[cols == dup].index.tolist()
                        for idx_num, idx in enumerate(dup_indices):
                            if idx_num != 0:
                                cols[idx] = f"{dup}_{idx_num}"
                    df_temp.columns = cols
            # ----------------------------------------------------------------------------

            df_sin = pd.merge(df_sablon, df_sin, on=["sayfa", "gmt"], how="left")
            if "sayfa" in df_sin.columns and "gmt" in df_sin.columns:
                df_sin = pd.merge(df_sablon, df_sin, on=["sayfa", "gmt"], how="left")
            
            # KESİN ÇÖZÜM: METAR verisindeki saat tekrarlarını (Ham mesajlar ve Meteorolojik veriler ayrı satırlardadır) ezmeden birleştir
            df_metar['is_speci'] = speci_mask
            df_metar = df_metar.sort_values(by=['sayfa', 'gmt', 'is_speci'], ascending=[True, True, True]) # Rutin METAR'lar (False) üstte olsun
            df_metar_tekil = df_metar.groupby(["sayfa", "gmt"], as_index=False).first()
            if "sayfa" in df_metar.columns and "gmt" in df_metar.columns:
                df_metar = df_metar.sort_values(by=['sayfa', 'gmt', 'is_speci'], ascending=[True, True, True])
                df_metar_tekil = df_metar.groupby(["sayfa", "gmt"], as_index=False).first()
            else:
                df_metar_tekil = df_metar
            df_metar.drop(columns=['is_speci'], inplace=True, errors='ignore')
            df_metar_tekil.drop(columns=['is_speci'], inplace=True, errors='ignore')
            
            # YENİ: SİNOPTİK VE METAR SÜTUNLARINI BİRLEŞTİRME VE RAPORLAMA İÇİN GARANTİLEME
            # _sin ve _metar eklerinin çiftlenmesini önlemek için replace yapıyoruz
            df_sin.columns = [str(c) if str(c) in ['sayfa', 'gmt', 'RASATLAR'] else ("gmt_exact_sin" if c == "gmt_exact" else f"{str(c).replace('_sin', '')}_sin") for c in df_sin.columns]
            df_metar_tekil.columns = [str(c) if str(c) in ['sayfa', 'gmt', 'RASATLAR'] else ("gmt_exact_metar" if c == "gmt_exact" else f"{str(c).replace('_metar', '')}_metar") for c in df_metar_tekil.columns]
            
            # DEBUG: Merge öncesi sütunları göster
            print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
            print(f"{Colors.BOLD}MERGE ÖNCESI SÜTUNLar:{Colors.ENDC}")
            print(f"df_sin sütun sayısı: {len(df_sin.columns)}")
            print(f"df_sin ilk 10 sütun: {list(df_sin.columns)[:10]}")
            print(f"\ndf_metar_tekil sütun sayısı: {len(df_metar_tekil.columns)}")
            print(f"df_metar_tekil ilk 10 sütun: {list(df_metar_tekil.columns)[:10]}")
            print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
            
            birlesik = pd.merge(df_sin, df_metar_tekil, on=["sayfa", "gmt"], how="left")
            if "sayfa" in df_sin.columns and "gmt" in df_sin.columns and "sayfa" in df_metar_tekil.columns and "gmt" in df_metar_tekil.columns:
                birlesik = pd.merge(df_sin, df_metar_tekil, on=["sayfa", "gmt"], how="left")
            else:
                birlesik = pd.concat([df_sin, df_metar_tekil], ignore_index=True)
            
            # DEBUG: Merge sonrası sütunları göster
            print(f"\n{Colors.BOLD}MERGE SONRASI SÜTUNLar:{Colors.ENDC}")
            print(f"Birleşik sütun sayısı: {len(birlesik.columns)}")
            print(f"Birleşik ilk 20 sütun: {list(birlesik.columns)[:20]}")
            print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
            
            # --- YENİ EKLENEN: PANDAS NaN DAVRANIŞLARINI GÜVENLİ HALE GETİRME ---
            # Metin (Object) sütunlarındaki NaN değerlerini boş stringe ("") çeviriyoruz.
            # Bu sayede validator ve analiz tarafında str(NaN) sonucu oluşan "nan" kelimesinin
            # sahte hadise eşleşmelerine (Örn: FG, N vb.) yol açmasını kesin olarak önlüyoruz.
            for col in birlesik.columns:
                if birlesik[col].dtype == 'object' or birlesik[col].dtype.name == 'category':
                    birlesik[col] = birlesik[col].replace(['nan', 'NAN', 'NaN', 'None', 'NONE', '-', ' - '], "")
                    birlesik[col] = birlesik[col].fillna("")
            
            # Geçmiş METAR aramalarında 'nan' kelimesi oluşmasını önlemek için aynı işlemi df_metar'a da uygula
            for col in df_metar.columns:
                if df_metar[col].dtype == 'object' or df_metar[col].dtype.name == 'category':
                    df_metar[col] = df_metar[col].replace(['nan', 'NAN', 'NaN', 'None', 'NONE', '-', ' - '], "")
                    df_metar[col] = df_metar[col].fillna("")
            # ------------------------------------------------------------------

            # --- YENİ EKLENEN: 3 Saatlik METAR WW (Geçmiş Hadise) Mantığı ---
            def get_ww_logic(hadise_listesi):
                priority = {'TS':(9,95), 'SQ':(8,18), 'RASN':(7.5,68), 'SNRA':(7.5,68), 'GR':(7,90), 'SN':(7,70), 'RA':(6,60), 'DZ':(5,50), 'FG':(4,45), 'BR':(3,10), 'HZ':(2,5), 'FU':(2,4), 'SA':(2,7), 'DU':(2,6)}
                max_prio = -1; best_code = 0
                for h_str in hadise_listesi:
                    if pd.isna(h_str) or str(h_str).strip() == "": continue
                    h = re.split(r'\b(TEMPO|BECMG|NOSIG|RMK|PROB\d{2})\b', str(h_str).upper())[0].strip()
                    p, c = 0, 0
                    for token in h.split():
                        # Geçerli bir METAR hava hadisesi grubu mu kontrol et
                        if not re.match(r'^(RE|-|\+|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?(DZ|RA|SN|SG|IC|PE|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PO|SQ|FC|SS|DS)*$', token) or token in ['+', '-', 'RE', 'VC']:
                            continue
                        
                        for kod_adi, (oncelik, cikti_kodu) in priority.items():
                            if kod_adi in token and oncelik > p:
                                p = oncelik; c = cikti_kodu
                                ilgili_kelime = token
                                if "SH" in ilgili_kelime:
                                    if kod_adi == 'RA': c = 82 if "+" in ilgili_kelime else (80 if "-" in ilgili_kelime else 81)
                                    elif kod_adi == 'SN': c = 86 if "+" in ilgili_kelime else (85 if "-" in ilgili_kelime else 86)
                                    elif kod_adi == 'GR': c = 90 if "+" in ilgili_kelime else (89 if "-" in ilgili_kelime else 90)
                                    elif kod_adi in ['RASN', 'SNRA']: c = 84 if "+" in ilgili_kelime else (83 if "-" in ilgili_kelime else 84)
                                elif kod_adi in ['RA', 'SN', 'DZ']: c = cikti_kodu + 5 if "+" in ilgili_kelime else (cikti_kodu + 1 if "-" in ilgili_kelime else cikti_kodu + 3)
                                elif kod_adi in ['RASN', 'SNRA']: c = 69 if "+" in ilgili_kelime else 68
                                elif kod_adi == 'TS': c = 97 if "+" in ilgili_kelime else c
                    if p > max_prio: max_prio = p; best_code = c
                return best_code if best_code != 0 else float('nan')

            if iptal_istendi: raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
            hesaplanan_ww_list = []
            for idx, row in birlesik.iterrows():
                try:
                    gmt_s = float(row.get("gmt"))
                    dt_s_str = str(row.get("sayfa"))
                    g, a, y = map(int, dt_s_str.split('.'))
                    dt_hedef = datetime.datetime(y, a, g, int(gmt_s))
                    lb = 6 if gmt_s in [0.0, 6.0, 12.0, 18.0] else 3
                    dt_bas = dt_hedef - datetime.timedelta(hours=lb)
                    
                    hadiseler = []
                    
                    for _, m_row in df_metar.iterrows():
                        m_tarih = str(m_row.get("sayfa"))
                        m_saat = float(m_row.get("gmt")) if pd.notna(m_row.get("gmt")) else -1
                        m_exact = m_row.get("gmt_exact")
                        if pd.notna(m_tarih) and m_saat >= 0:
                            try:
                                mg, ma, my = map(int, m_tarih.split('.'))
                                if pd.notna(m_exact):
                                    exact_str = str(m_exact).replace('.0', '').zfill(4)
                                    e_h, e_m = int(exact_str[:2]), int(exact_str[2:])
                                    if e_h == 23 and int(m_saat) == 0:
                                        m_dt = datetime.datetime(my, ma, mg) - datetime.timedelta(days=1)
                                        m_dt = m_dt.replace(hour=e_h, minute=e_m)
                                    else:
                                        m_dt = datetime.datetime(my, ma, mg, e_h, e_m)
                                    gecerli = dt_bas < m_dt <= dt_hedef
                                else:
                                    m_dt = datetime.datetime(my, ma, mg, int(m_saat))
                                    gecerli = dt_bas < m_dt <= dt_hedef
                                
                                if gecerli:
                                    if "ww" in m_row and pd.notna(m_row["ww"]): hadiseler.append(str(m_row["ww"]))
                                    if "ww2" in m_row and pd.notna(m_row["ww2"]): hadiseler.append(str(m_row["ww2"]))
                                    if "ww3" in m_row and pd.notna(m_row["ww3"]): hadiseler.append(str(m_row["ww3"]))
                            except: pass
                    
                    hesaplanan_ww_list.append(get_ww_logic(hadiseler))
                except:
                    hesaplanan_ww_list.append(float('nan'))
            birlesik["ww_hesaplanan"] = hesaplanan_ww_list
            # ----------------------------------------------------------------

            # 2. Hata Analizi
            # --- dm2 Çökmesini Önlemek İçin Son Güvenlik ---
            beklenen_sutunlar = [
                'p_sin', 'ff_sin', 'n_sin', 'p_metar', 'ff_metar', 'n_metar', 
                't_sin', 't_metar', 'td_sin', 'td_metar', 'p0_sin', 'p0_metar', 
                'dd_sin', 'dd_metar', 'vv_sin', 'vv_metar', 'w1_sin', 'w2_sin', 
                'ww_sin', 'ww_metar', 'rrr_sin', 'tr_sin', 'tx_sin', 'tn_sin', 
                'tg_sin', 'a_sin', 'ppp_sin'
            ]
            for b in beklenen_sutunlar:
                if b not in birlesik.columns:
                    birlesik[b] = float('nan')
                else:
                    # İçerisinde boşluk/metin kalmış hücreleri güvenli NaN değerine zorla
                    birlesik[b] = pd.to_numeric(birlesik[b], errors='coerce')
                    
            if iptal_istendi: raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
            birlesik = dm2.hata_analizi_yap(birlesik, df_metar)
            
            # DEBUG: Hata analizi ÖNCE ve SONRA
            print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
            print(f"{Colors.BOLD}HATA ANALİZİ SONRASI - SÜTUNLAR:{Colors.ENDC}")
            print(f"Toplam satır: {len(birlesik)}, Toplam sütun: {len(birlesik.columns)}")
            print(f"İlk 10 sütun adı: {list(birlesik.columns)[:10]}")
            print(f"{Colors.BOLD}DURUM Sütunu İçeriği (benzersiz değerler):{Colors.ENDC}")
            if 'ANALİZ_SONUCU' in birlesik.columns:
                print(birlesik['ANALİZ_SONUCU'].value_counts())
            elif 'DURUM' in birlesik.columns:
                print(birlesik['DURUM'].value_counts())
            else:
                print(f"{Colors.WARNING}DURUM sütunu bulunamadı!{Colors.ENDC}")
            print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

            # --- YENİ EKLENEN: GEÇMİŞ HAVA (W1/W2) UYUMSUZLUK KONTROLÜ ---
            for idx, row in birlesik.iterrows():
                # ŞİFRELİ MESAJDA W1/W2 BAŞARIYLA ÇÖZÜMLENDİYSE EXCEL HATASINI GÖRMEZDEN GEL
                rasat_raw = str(row.get('RASATLAR', ''))
                w1_ok_in_raw = False
                if ":" not in rasat_raw and len(rasat_raw.strip()) > 5 and SynopDecoder is not None:
                    decoder_tmp = SynopDecoder()
                    s_data_tmp = decoder_tmp.decode_line(rasat_raw)
                    if s_data_tmp and ('gecmis_hava1' in s_data_tmp or 'gecmis_hava2' in s_data_tmp):
                        w1_ok_in_raw = True
                        
                ww_calc = row.get("ww_hesaplanan")
                w1 = row.get("w1_sin")
                w2 = row.get("w2_sin")
                
                # SADECE ANA VE ARA SİNOPTİK SAATLERİNDE ÇALIŞSIN (Ara saatlerde SİNOPTİK beklenmez)
                try:
                    if float(row.get("gmt")) not in [0.0, 3.0, 6.0, 9.0, 12.0, 15.0, 18.0, 21.0]:
                        continue
                except: pass
                
                if pd.notna(ww_calc) and not w1_ok_in_raw:
                    c = int(ww_calc)
                    expected_W1 = None
                    if c >= 90: expected_W1 = 9
                    elif 80 <= c <= 89: expected_W1 = 8
                    elif 70 <= c <= 79: expected_W1 = 7
                    elif 60 <= c <= 69: expected_W1 = 6
                    elif 50 <= c <= 59: expected_W1 = 5
                    elif 40 <= c <= 49: expected_W1 = 4
                    elif 30 <= c <= 39: expected_W1 = 3
                    
                    if expected_W1 is not None:
                        match = False
                        if pd.notna(w1) and str(w1).strip() != "":
                            try:
                                w1_int = int(float(w1))
                                w2_int = int(float(w2)) if pd.notna(w2) and str(w2).strip() != "" else -1
                                if w1_int == expected_W1 or w2_int == expected_W1: match = True
                                elif expected_W1 == 6 and w1_int == 8: match = True # Yağmur - Sağanak toleransı
                                elif expected_W1 == 8 and w1_int == 6: match = True
                                elif expected_W1 == 7 and w1_int == 8: match = True # Kar - Sağanak toleransı
                                elif expected_W1 == 9 and w1_int == 8: match = True # Oraj - Sağanak toleransı
                            except: pass
                        
                        if not match:
                            gmt = row.get("gmt")
                            saat_tipi = "6" if gmt in [0.0, 6.0, 12.0, 18.0] else "3"
                            hata_kodu = "h361"
                            hata_aciklama = f"Son {saat_tipi} saatlik METAR'da hadise var ancak SİNOPTİK Geçmiş Hava (W1/W2) eksik veya uyumsuz (Beklenen W1: {expected_W1})."
                            
                            mevcut_durum = str(birlesik.at[idx, 'ANALİZ_SONUCU'])
                            if mevcut_durum in ["Hata Yok", "Veri Yok", "Ara Rasat"]:
                                birlesik.at[idx, 'ANALİZ_SONUCU'] = "Hatalı"
                                birlesik.at[idx, 'HATA_KODLARI'] = hata_kodu
                                birlesik.at[idx, 'HATA_ACIKLAMALARI'] = hata_aciklama
                            else:
                                birlesik.at[idx, 'HATA_KODLARI'] = str(birlesik.at[idx, 'HATA_KODLARI']) + f", {hata_kodu}"
                                birlesik.at[idx, 'HATA_ACIKLAMALARI'] = str(birlesik.at[idx, 'HATA_ACIKLAMALARI']) + f" | {hata_aciklama}"
            # -------------------------------------------------------------

            # --- YENİ EKLENEN: GEÇMİŞ METARLARI GARANTİLEME (Validator çalışmadan önce) ---
            b_col = "bulten_metar" if "bulten_metar" in birlesik.columns else "bulten"
            if b_col in birlesik.columns:
                for idx, row in birlesik.iterrows():
                    durum_str = str(row.get('ANALİZ_SONUCU', row.get('DURUM', '')))
                    if "Veri Yok" not in durum_str:
                        mevcut_bulten = str(birlesik.at[idx, b_col]).strip()
                        if mevcut_bulten.replace('"', '').replace("'", "").strip().lower() in ['nan', 'none', '<na>', '-', '']:
                            mevcut_bulten = ""
                        if "İLGİLİ METAR GEÇMİŞİ:" not in mevcut_bulten:
                            try:
                                gmt_s = float(row.get("gmt"))
                                dt_s_str = str(row.get("sayfa"))
                                g, a, y = map(int, dt_s_str.split('.'))
                                dt_hedef = datetime.datetime(y, a, g, int(gmt_s))
                                lb = 12 if gmt_s in [6.0, 18.0] else (6 if gmt_s in [0.0, 12.0] else 3)
                                dt_bas = dt_hedef - datetime.timedelta(hours=lb)
                                
                                m_list = []
                                bulten_col_m = "bulten" if "bulten" in df_metar.columns else None
                                if bulten_col_m:
                                    for _, m_row in df_metar.iterrows():
                                        m_tarih = str(m_row.get("sayfa"))
                                        m_saat = float(m_row.get("gmt")) if pd.notna(m_row.get("gmt")) else -1
                                        m_exact = m_row.get("gmt_exact")
                                        if pd.notna(m_tarih) and m_saat >= 0:
                                            try:
                                                mg, ma, my = map(int, m_tarih.split('.'))
                                                if pd.notna(m_exact):
                                                    exact_str = str(m_exact).replace('.0', '').zfill(4)
                                                    e_h, e_m = int(exact_str[:2]), int(exact_str[2:])
                                                    if e_h == 23 and int(m_saat) == 0:
                                                        m_dt = datetime.datetime(my, ma, mg) - datetime.timedelta(days=1)
                                                        m_dt = m_dt.replace(hour=e_h, minute=e_m)
                                                    else:
                                                        m_dt = datetime.datetime(my, ma, mg, e_h, e_m)
                                                    gecerli = (dt_bas - datetime.timedelta(minutes=10)) <= m_dt <= dt_hedef
                                                    is_boundary = m_dt <= dt_bas
                                                else:
                                                    m_dt = datetime.datetime(my, ma, mg, int(m_saat))
                                                    gecerli = dt_bas <= m_dt <= dt_hedef
                                                    is_boundary = m_dt <= dt_bas
                                                
                                                if gecerli:
                                                    m_raw = str(m_row[bulten_col_m]).strip()
                                                    if m_raw.replace('"', '').replace("'", "").strip().lower() in ['nan', 'none', '<na>', '-', '']:
                                                        continue
                                                    if is_boundary:
                                                        m_raw = re.sub(r'\bRE[A-Z]{2,}\b', '', m_raw)
                                                        m_raw = re.sub(r'\s+', ' ', m_raw).strip()
                                                    z_match = re.search(r'\b\d{2}(\d{4}Z?)\b', m_raw)
                                                    z_saat = z_match.group(1) if z_match else f"{int(m_saat):02d}00Z"
                                                    m_list.append(f"[{z_saat}] {m_raw}")
                                            except: pass
                                    if m_list:
                                        m_list.reverse()
                                        ek_metar_bilgisi = "İLGİLİ METAR GEÇMİŞİ:\n" + "\n".join(m_list)
                                        
                                        if not mevcut_bulten:
                                            m_reg = re.match(r'^\[.*?\]\s*(.*)', m_list[0])
                                            if m_reg:
                                                mevcut_bulten = m_reg.group(1)
                                                
                                        if mevcut_bulten:
                                            if ek_metar_bilgisi not in mevcut_bulten:
                                                birlesik.at[idx, b_col] = mevcut_bulten + "\n\n" + ek_metar_bilgisi
                                            else:
                                                birlesik.at[idx, b_col] = mevcut_bulten
                                        else:
                                            birlesik.at[idx, b_col] = ek_metar_bilgisi
                            except: pass
            # -------------------------------------------------------------

            # --- YENİ EKLENEN: VALIDATOR.PY ENTEGRASYONU ---
            if validator is not None:
                for idx, row in birlesik.iterrows():
                    sin_dict = {
                        'T': row.get('t_sin'), 'Td': row.get('td_sin'), 'Rh': row.get('rh_sin'),
                        'ff': row.get('ff_sin'), 'dd': row.get('dd_sin'), 
                        '4P': row.get('p_sin'), '3Po': row.get('p0_sin'), 'N': row.get('n_sin'),
                        'h': row.get('h_sin'),
                        'Nh': row.get('nh_sin'),
                        'Bg1': row.get('bg1_sin', row.get('cl_sin')), 
                        'Bg2': row.get('bg2_sin', row.get('cm_sin')),
                        'Bg3': row.get('bg3_sin', row.get('ch_sin')), 
                        'Bg4': row.get('bg4_sin'),
                        '910': row.get('g910_sin'),
                        '911': row.get('g911_sin'),
                        '924': row.get('g924_sin'),
                        'VV': row.get('vv_sin'),
                        'ww': row.get('ww_sin'),
                        'w1': row.get('w1_sin'),
                        'w2': row.get('w2_sin'),
                        'istasyon_no': row.get('istasyon_no_sin'),
                        '960': row.get('g960_sin'),
                        'RASATLAR': row.get('RASATLAR', '')
                    }
                    
                    bulten_combined = str(row.get('bulten_metar', ''))
                    
                    met_dict = {
                        'Kuru': row.get('t_metar'), 'İşba': row.get('td_metar'), '%': row.get('rh_metar'),
                        'Hız': row.get('ff_metar'), 'Yön': row.get('dd_metar'), 
                        'QFE': row.get('p_metar'), 'QNH': row.get('p0_metar'), 'T. Kp.': row.get('n_metar'),
                        '1. BULUT Cins': row.get('1. bulut cins_metar', row.get('1. bulut_cins_metar')),
                        '2. BULUT Cins': row.get('2. bulut cins_metar', row.get('2. bulut_cins_metar')),
                        '3. BULUT Cins': row.get('3. bulut cins_metar', row.get('3. bulut_cins_metar')),
                        '4. BULUT Cins': row.get('4. bulut cins_metar', row.get('4. bulut_cins_metar')),
                        'Hakim': row.get('vv_metar'),
                        'Hadise': row.get('ww_metar'),
                        'WS': row.get('ws_metar'),
                        'Bulten': bulten_combined
                    }
                    
                    # KULLANICI ŞİFREYİ DOĞRU GİRDİ AMA EXCEL SÜTUNUNU BOŞ BIRAKTIYSA VAL_HADISE HATALARINI ÖNLE
                    rasat_raw = str(row.get('RASATLAR', ''))
                    if ":" not in rasat_raw and len(rasat_raw.strip()) > 5 and SynopDecoder is not None:
                        dec_tmp = SynopDecoder()
                        s_data_val = dec_tmp.decode_line(rasat_raw)
                        if s_data_val:
                            def is_empty(v): return pd.isna(v) or str(v).strip() == ""
                            
                            if not is_empty(sin_dict.get('w1')):
                                try:
                                    w1_v = int(float(sin_dict['w1']))
                                    if w1_v > 9:
                                        w1_s = str(w1_v)
                                        if len(w1_s) == 2:
                                            sin_dict['w1'] = float(w1_s[0])
                                            sin_dict['w2'] = float(w1_s[1])
                                except: pass

                            if is_empty(sin_dict.get('w1')) and 'gecmis_hava1' in s_data_val: sin_dict['w1'] = s_data_val['gecmis_hava1']
                            if is_empty(sin_dict.get('w2')) and 'gecmis_hava2' in s_data_val: sin_dict['w2'] = s_data_val['gecmis_hava2']
                            if is_empty(sin_dict.get('ww')) and 'halihazir_hava' in s_data_val: sin_dict['ww'] = s_data_val['halihazir_hava']
                            if is_empty(sin_dict.get('960')) and 'halihazir_hava_2' in s_data_val: sin_dict['960'] = s_data_val['halihazir_hava_2']
                            if is_empty(sin_dict.get('910')) and 'hamle_hizi' in s_data_val: sin_dict['910'] = s_data_val['hamle_hizi']
                            if is_empty(sin_dict.get('911')) and 'max_ruzgar_hizi' in s_data_val: sin_dict['911'] = s_data_val['max_ruzgar_hizi']
                            if is_empty(sin_dict.get('924')) and 'raw_groups' in s_data_val and 'deniz_durumu' in s_data_val['raw_groups']: sin_dict['924'] = s_data_val['raw_groups']['deniz_durumu']
                            if is_empty(sin_dict.get('931')) and 'kar_kalinligi_toplam' in s_data_val: sin_dict['931'] = s_data_val['kar_kalinligi_toplam']
                            if is_empty(sin_dict.get('932')) and 'kar_kalinligi_taze' in s_data_val: sin_dict['932'] = s_data_val['kar_kalinligi_taze']

                    val_instance = validator.WeatherLogValidator(
                        sin_dict, 
                        met_dict,
                        metar_gmt=row.get('gmt_exact_metar') if pd.notna(row.get('gmt_exact_metar')) else row.get('gmt'),
                        sinoptik_gmt=row.get('gmt_exact_sin') if pd.notna(row.get('gmt_exact_sin')) else row.get('gmt')
                    )
                    
                    try:
                        if not hasattr(val_instance, 'check_cloud_base_crosscheck'):
                            setattr(val_instance, 'check_cloud_base_crosscheck', lambda: None)
                        v_hatalar = val_instance.run_all_checks()
                    except AttributeError as e:
                        logging.warning(f"Validator metodu eksik, atlandı: {e}")
                        v_hatalar = val_instance.errors
                    
                    if v_hatalar:
                        for h_dict in v_hatalar:
                            hata_kod_ek = h_dict["kod"]
                            # Eski bellekten gelen iptal edilmiş kuralı zorla atla
                            if hata_kod_ek == "VAL_MANTIK_SPREAD":
                                continue
                            
                            # VALIDATOR.PY REGEX BUG FIX: N=7 iken 7ddff grubunu 7wwW1W2 sanması
                            ww_error_codes = [f"h{i}" for i in range(78, 112)] + [f"h{i}" for i in range(364, 374)] + ["h380", "h381", "h382"]
                            w1w2_error_codes = ["h116", "h117", "h118"]
                            
                            if hata_kod_ek in ww_error_codes + w1w2_error_codes:
                                n_val = sin_dict.get('N')
                                dd_val = sin_dict.get('dd')
                                ff_val = sin_dict.get('ff')
                                if pd.notna(n_val) and int(float(n_val)) == 7 and pd.notna(dd_val) and pd.notna(ff_val):
                                    wrong_ww = float(dd_val)
                                    wrong_w1 = float(ff_val) // 10
                                    wrong_w2 = float(ff_val) % 10
                                    actual_ww = sin_dict.get('ww')
                                    actual_w1 = sin_dict.get('w1')
                                    actual_w2 = sin_dict.get('w2')
                                    if hata_kod_ek in ww_error_codes and (pd.isna(actual_ww) or float(actual_ww) != wrong_ww):
                                        continue
                                    if hata_kod_ek in w1w2_error_codes and (pd.isna(actual_w1) or pd.isna(actual_w2) or float(actual_w1) != wrong_w1 or float(actual_w2) != wrong_w2):
                                        continue

                            mevcut_durum = str(birlesik.at[idx, 'ANALİZ_SONUCU'])
                            hata_aciklama_ek = h_dict["mesaj"]
                            
                            if mevcut_durum in ["Hata Yok", "Veri Yok", "Ara Rasat"]:
                                birlesik.at[idx, 'ANALİZ_SONUCU'] = "Hatalı"
                                birlesik.at[idx, 'HATA_KODLARI'] = hata_kod_ek
                                birlesik.at[idx, 'HATA_ACIKLAMALARI'] = hata_aciklama_ek
                            else:
                                mevcut_kodlar = str(birlesik.at[idx, 'HATA_KODLARI'])
                                if hata_kod_ek not in mevcut_kodlar:
                                    birlesik.at[idx, 'HATA_KODLARI'] = mevcut_kodlar + f", {hata_kod_ek}"
                                birlesik.at[idx, 'HATA_ACIKLAMALARI'] = str(birlesik.at[idx, 'HATA_ACIKLAMALARI']) + f" | {hata_aciklama_ek}"
            # -------------------------------------------------------------

            # --- YENİ EKLENEN: SYNOP DECODER (FORMAT KONTROLÜ) ENTEGRASYONU ---
            if SynopDecoder is not None:
                for idx, row in birlesik.iterrows():
                    rasatlar_str = str(row.get('RASATLAR', ''))
                    # Sadece ham mesajları denetle (":" içermeyenler, yani programca birleştirilmiş değil gerçek ham veriler)
                    if rasatlar_str and ":" not in rasatlar_str and len(rasatlar_str.strip()) >= 5:
                        decoder = SynopDecoder()
                        decoder.decode_line(rasatlar_str)
                        if not decoder.validate():
                            for err in decoder.get_errors():
                                mevcut_durum = str(birlesik.at[idx, 'ANALİZ_SONUCU'])
                                hata_kod_ek = "h362"
                                hata_aciklama_ek = f"SİNOPTİK Format Hatası: {err}"
                                
                                if mevcut_durum in ["Hata Yok", "Veri Yok", "Ara Rasat"]:
                                    birlesik.at[idx, 'ANALİZ_SONUCU'] = "Hatalı"
                                    birlesik.at[idx, 'HATA_KODLARI'] = hata_kod_ek
                                    birlesik.at[idx, 'HATA_ACIKLAMALARI'] = hata_aciklama_ek
                                else:
                                    mevcut_kodlar = str(birlesik.at[idx, 'HATA_KODLARI'])
                                    if hata_kod_ek not in mevcut_kodlar:
                                        birlesik.at[idx, 'HATA_KODLARI'] = mevcut_kodlar + f", {hata_kod_ek}"
                                    birlesik.at[idx, 'HATA_ACIKLAMALARI'] = str(birlesik.at[idx, 'HATA_ACIKLAMALARI']) + f" | {hata_aciklama_ek}"
            # -------------------------------------------------------------

            # --- YENİ EKLENEN: TAZE KAR (931ss) VE TOPLAM KAR (4E'sss) KONTROLÜ ---
            for idx, row in birlesik.iterrows():
                rasatlar_str = str(row.get('RASATLAR', ''))
                gmt = float(row.get("gmt")) if pd.notna(row.get("gmt")) else -1.0
                
                # Yalnızca 333 (Bölgesel Veriler) bölümünden sonrasını tara
                m_333 = re.search(r'\b333\b', rasatlar_str)
                has_4e = False
                
                if m_333:
                    try:
                        bolum_3 = rasatlar_str[m_333.end():]
                        
                        # 1. Toplam Kar Kalınlığı (4E'sss) Kontrolü
                        m_4e = re.search(r'\b4(\d)(\d{3})\b', bolum_3)
                        if m_4e:
                            has_4e = True
                            e_durumu = int(m_4e.group(1))
                            sss = int(m_4e.group(2))
                            
                            hata_kodu = None
                            hata_aciklama = ""
                            
                            # Kural: Rasat saatinde yerdeki kar erimiş ise bu grup koda dahil edilmez.
                            if sss == 0:
                                hata_kodu = "h245"
                                hata_aciklama = "Kar erimiş (0 cm) ise 4E'sss grubu (Toplam Kar) rapora dahil edilmemelidir."
                            # Aşırı yüksek toplam kar kalınlığı (örn: 500 cm üstü - 997,998,999 özel kodlardır)
                            elif 500 < sss < 997:
                                hata_kodu = "h243"
                                hata_aciklama = f"Toplam kar kalınlığı için aşırı yüksek bir değer ({sss} cm)"
                                
                            if hata_kodu:
                                mevcut_durum = str(birlesik.at[idx, 'ANALİZ_SONUCU'])
                                if mevcut_durum in ["Hata Yok", "Veri Yok", "Ara Rasat"]:
                                    birlesik.at[idx, 'ANALİZ_SONUCU'] = "Hatalı"
                                    birlesik.at[idx, 'HATA_KODLARI'] = hata_kodu
                                    birlesik.at[idx, 'HATA_ACIKLAMALARI'] = hata_aciklama
                                else:
                                    mevcut_kodlar = str(birlesik.at[idx, 'HATA_KODLARI'])
                                    if hata_kodu not in mevcut_kodlar:
                                        birlesik.at[idx, 'HATA_KODLARI'] = mevcut_kodlar + f", {hata_kodu}"
                                    birlesik.at[idx, 'HATA_ACIKLAMALARI'] = str(birlesik.at[idx, 'HATA_ACIKLAMALARI']) + f" | {hata_aciklama}"

                        # 2. Taze Kar (931ss) Kontrolü
                        m_931 = re.search(r'\b931(\d{2})\b', bolum_3)
                        if m_931:
                            ss = int(m_931.group(1))
                            gercek_kar_mm = -1
                            aciklama = ""
                            
                            if 0 <= ss <= 55:
                                gercek_kar_mm = ss * 10
                                aciklama = f"{ss} cm"
                            elif 56 <= ss <= 90:
                                gercek_kar_mm = (ss - 50) * 100
                                aciklama = f"{gercek_kar_mm // 10} cm"
                            elif 91 <= ss <= 96:
                                gercek_kar_mm = ss - 90
                                aciklama = f"{gercek_kar_mm} mm"
                            elif ss == 97:
                                gercek_kar_mm = 0
                                aciklama = "1 mm'den az"
                            elif ss == 98:
                                gercek_kar_mm = 4001
                                aciklama = "4000 mm'den fazla"
                            elif ss == 99:
                                gercek_kar_mm = -1
                                aciklama = "Ölçüm hatalı veya imkansız"
                                
                            # Eşik değer: 90 cm (900 mm) ve üzeri için h242 hatasını fırlat
                            if gercek_kar_mm >= 900:
                                hata_kodu = "h242"
                                hata_aciklama = f"Taze kar için yüksek bir değer ({aciklama})"
                                
                                mevcut_durum = str(birlesik.at[idx, 'ANALİZ_SONUCU'])
                                if mevcut_durum in ["Hata Yok", "Veri Yok", "Ara Rasat"]:
                                    birlesik.at[idx, 'ANALİZ_SONUCU'] = "Hatalı"
                                    birlesik.at[idx, 'HATA_KODLARI'] = hata_kodu
                                    birlesik.at[idx, 'HATA_ACIKLAMALARI'] = hata_aciklama
                                else:
                                    mevcut_kodlar = str(birlesik.at[idx, 'HATA_KODLARI'])
                                    if hata_kodu not in mevcut_kodlar:
                                        birlesik.at[idx, 'HATA_KODLARI'] = mevcut_kodlar + f", {hata_kodu}"
                                    birlesik.at[idx, 'HATA_ACIKLAMALARI'] = str(birlesik.at[idx, 'HATA_ACIKLAMALARI']) + f" | {hata_aciklama}"
                    except: pass

                # 3. 0600 GMT'de Taze Kar Varsa Toplam Kar (4E) Eksiklik Kontrolü
                if gmt == 6.0 and re.search(r'\b931\d{2}\b', rasatlar_str) and not has_4e:
                    hata_kodu = "h244"
                    hata_aciklama = "0600 GMT rasadında taze kar (931) bildirilmiş ancak toplam kar kalınlığı (4E'sss) grubu eksik."
                    
                    mevcut_durum = str(birlesik.at[idx, 'ANALİZ_SONUCU'])
                    if mevcut_durum in ["Hata Yok", "Veri Yok", "Ara Rasat"]:
                        birlesik.at[idx, 'ANALİZ_SONUCU'] = "Hatalı"
                        birlesik.at[idx, 'HATA_KODLARI'] = hata_kodu
                        birlesik.at[idx, 'HATA_ACIKLAMALARI'] = hata_aciklama
                    else:
                        mevcut_kodlar = str(birlesik.at[idx, 'HATA_KODLARI'])
                        if hata_kodu not in mevcut_kodlar:
                            birlesik.at[idx, 'HATA_KODLARI'] = mevcut_kodlar + f", {hata_kodu}"
                        birlesik.at[idx, 'HATA_ACIKLAMALARI'] = str(birlesik.at[idx, 'HATA_ACIKLAMALARI']) + f" | {hata_aciklama}"
            # -------------------------------------------------------------
            
            # --- YENİ EKLENEN: METAR DECODER (FORMAT KONTROLÜ) ENTEGRASYONU ---
            if MetarDecoder is not None:
                b_col_metar = "METAR - Şifreli Mesaj" if "METAR - Şifreli Mesaj" in birlesik.columns else ("bulten_metar" if "bulten_metar" in birlesik.columns else "bulten")
                if b_col_metar in birlesik.columns:
                    for idx, row in birlesik.iterrows():
                        metar_str = str(row.get(b_col_metar, ''))
                        if metar_str and len(metar_str.strip()) >= 10:
                            try:
                                decoder = MetarDecoder()
                                decoder.decode_line(metar_str)
                                if hasattr(decoder, 'errors') and decoder.errors:
                                    for err in decoder.errors:
                                        mevcut_durum = str(birlesik.at[idx, 'ANALİZ_SONUCU'])
                                        hata_kod_ek = "h363"
                                        hata_aciklama_ek = f"METAR Format Hatası: {err}"
                                        
                                        if mevcut_durum in ["Hata Yok", "Veri Yok", "Ara Rasat"]:
                                            birlesik.at[idx, 'ANALİZ_SONUCU'] = "Hatalı"
                                            birlesik.at[idx, 'HATA_KODLARI'] = hata_kod_ek
                                            birlesik.at[idx, 'HATA_ACIKLAMALARI'] = hata_aciklama_ek
                                        else:
                                            mevcut_kodlar = str(birlesik.at[idx, 'HATA_KODLARI'])
                                            if hata_kod_ek not in mevcut_kodlar:
                                                birlesik.at[idx, 'HATA_KODLARI'] = mevcut_kodlar + f", {hata_kod_ek}"
                                            birlesik.at[idx, 'HATA_ACIKLAMALARI'] = str(birlesik.at[idx, 'HATA_ACIKLAMALARI']) + f" | {hata_aciklama_ek}"
                            except Exception as e:
                                logging.error(f"MetarDecoder Çöktü: {e} | Şifre: {metar_str}")
                                mevcut_durum = str(birlesik.at[idx, 'ANALİZ_SONUCU'])
                                hata_kod_ek = "h363"
                                hata_aciklama_ek = f"METAR Çözümleme Hatası: Beklenmeyen format veya karakter ({e})"
                                
                                if mevcut_durum in ["Hata Yok", "Veri Yok", "Ara Rasat"]:
                                    birlesik.at[idx, 'ANALİZ_SONUCU'] = "Hatalı"
                                    birlesik.at[idx, 'HATA_KODLARI'] = hata_kod_ek
                                    birlesik.at[idx, 'HATA_ACIKLAMALARI'] = hata_aciklama_ek
                                else:
                                    mevcut_kodlar = str(birlesik.at[idx, 'HATA_KODLARI'])
                                    if hata_kod_ek not in mevcut_kodlar:
                                        birlesik.at[idx, 'HATA_KODLARI'] = mevcut_kodlar + f", {hata_kod_ek}"
                                    birlesik.at[idx, 'HATA_ACIKLAMALARI'] = str(birlesik.at[idx, 'HATA_ACIKLAMALARI']) + f" | {hata_aciklama_ek}"
            # -------------------------------------------------------------

            # --- ZORUNLU GÜVENLİK: İptal edilmiş VAL_MANTIK_SPREAD hatasını DataFrame'den kazı ---
            if 'HATA_KODLARI' in birlesik.columns:
                def scrub_spread_error(row):
                    kod_metni = str(row.get('HATA_KODLARI', ''))
                    if 'VAL_MANTIK_SPREAD' in kod_metni:
                        yeni_kodlar = [x.strip() for x in kod_metni.split(',') if x.strip() and x.strip() != 'VAL_MANTIK_SPREAD']
                        row['HATA_KODLARI'] = ', '.join(yeni_kodlar)
                        
                        aciklama_metni = str(row.get('HATA_ACIKLAMALARI', ''))
                        yeni_aciklamalar = [x.strip() for x in aciklama_metni.split('|') if 'Sıcaklık ve İşba' not in x and 'VAL_MANTIK_SPREAD' not in x]
                        row['HATA_ACIKLAMALARI'] = ' | '.join(yeni_aciklamalar)
                        
                        if not yeni_kodlar and str(row.get('ANALİZ_SONUCU')) == 'Hatalı':
                            row['ANALİZ_SONUCU'] = 'Hata Yok'
                    return row
                birlesik = birlesik.apply(scrub_spread_error, axis=1)
                
            # --- YENİ EKLENEN: GEÇMİŞ METARLARI GARANTİLEME (h361 ve diğerleri için) ---
            b_col = "bulten_metar" if "bulten_metar" in birlesik.columns else "bulten"
            if b_col in birlesik.columns:
                for idx, row in birlesik.iterrows():
                    kodlar_str = str(row.get('HATA_KODLARI', ''))
                    if kodlar_str and "Veri Yok" not in kodlar_str and "Hata Yok" not in kodlar_str:
                        mevcut_bulten = str(birlesik.at[idx, b_col]).strip()
                        if mevcut_bulten.replace('"', '').replace("'", "").strip().lower() in ['nan', 'none', '<na>', '-', '']:
                            mevcut_bulten = ""
                        if "İLGİLİ METAR GEÇMİŞİ:" not in mevcut_bulten:
                            try:
                                gmt_s = float(row.get("gmt"))
                                dt_s_str = str(row.get("sayfa"))
                                g, a, y = map(int, dt_s_str.split('.'))
                                dt_hedef = datetime.datetime(y, a, g, int(gmt_s))
                                lb = 6 if gmt_s in [0.0, 6.0, 12.0, 18.0] else 3
                                dt_bas = dt_hedef - datetime.timedelta(hours=lb)
                                
                                m_list = []
                                bulten_col_m = "bulten" if "bulten" in df_metar.columns else None
                                if bulten_col_m:
                                    for _, m_row in df_metar.iterrows():
                                        m_tarih = str(m_row.get("sayfa"))
                                        m_saat = float(m_row.get("gmt")) if pd.notna(m_row.get("gmt")) else -1
                                        m_exact = m_row.get("gmt_exact")
                                        if pd.notna(m_tarih) and m_saat >= 0:
                                            try:
                                                mg, ma, my = map(int, m_tarih.split('.'))
                                                if pd.notna(m_exact):
                                                    exact_str = str(m_exact).replace('.0', '').zfill(4)
                                                    e_h, e_m = int(exact_str[:2]), int(exact_str[2:])
                                                    if e_h == 23 and int(m_saat) == 0:
                                                        m_dt = datetime.datetime(my, ma, mg) - datetime.timedelta(days=1)
                                                        m_dt = m_dt.replace(hour=e_h, minute=e_m)
                                                    else:
                                                        m_dt = datetime.datetime(my, ma, mg, e_h, e_m)
                                                    # DÜZELTME: Gelecekteki SPECI/METAR'ları dahil etme (örn: 12:02Z, 12:00Z SİNOPTİK'inden sonradır)
                                                    gecerli = (dt_bas - datetime.timedelta(minutes=10)) <= m_dt <= dt_hedef
                                                    is_boundary = m_dt <= dt_bas
                                                else:
                                                    m_dt = datetime.datetime(my, ma, mg, int(m_saat))
                                                    gecerli = dt_bas <= m_dt <= dt_hedef
                                                    is_boundary = m_dt <= dt_bas
                                                
                                                if gecerli:
                                                    m_raw = str(m_row[bulten_col_m]).strip()
                                                    if m_raw.replace('"', '').replace("'", "").strip().lower() in ['nan', 'none', '<na>', '-', '']:
                                                        continue
                                                    if is_boundary:
                                                        m_raw = re.sub(r'\bRE[A-Z]{2,}\b', '', m_raw)
                                                        m_raw = re.sub(r'\s+', ' ', m_raw).strip()
                                                    z_match = re.search(r'\b\d{2}(\d{4}Z?)\b', m_raw)
                                                    z_saat = z_match.group(1) if z_match else f"{int(m_saat):02d}00Z"
                                                    m_list.append(f"[{z_saat}] {m_raw}")
                                            except: pass
                                    if m_list:
                                        m_list.reverse()
                                        ek_metar_bilgisi = "İLGİLİ METAR GEÇMİŞİ:\n" + "\n".join(m_list)
                                        
                                        if not mevcut_bulten:
                                            m_reg = re.match(r'^\[.*?\]\s*(.*)', m_list[0])
                                            if m_reg:
                                                mevcut_bulten = m_reg.group(1)
                                                
                                        if mevcut_bulten:
                                            if ek_metar_bilgisi not in mevcut_bulten:
                                                birlesik.at[idx, b_col] = mevcut_bulten + "\n\n" + ek_metar_bilgisi
                                            else:
                                                birlesik.at[idx, b_col] = mevcut_bulten
                                        else:
                                            birlesik.at[idx, b_col] = ek_metar_bilgisi
                            except: pass

            # --- METAR HALİHAZIR HAVA (1, 2 ve 3. GRUP) SÜTUNLARINI BİRLEŞTİR ---
            ww_metar_cols = [c for c in ['ww_metar', 'ww2_metar', 'ww3_metar'] if c in birlesik.columns]
            if len(ww_metar_cols) > 1:
                def metar_ww_birlestir(row):
                    vals = []
                    for c in ww_metar_cols:
                        val = str(row[c]).strip()
                        if val and val.lower() != 'nan':
                            if val not in vals: # Aynı hadise tekrarlanmasın (Örn: RA RA -> RA)
                                vals.append(val)
                    return " ".join(vals) if vals else float('nan')
                
                birlesik['ww_metar'] = birlesik.apply(metar_ww_birlestir, axis=1)
                birlesik.drop(columns=[c for c in ww_metar_cols if c != 'ww_metar'], inplace=True, errors='ignore')
                
            # SAAT YAZIMLARINI 0000, 1500, 1200 ŞEKLİNDE GÖSTER
            def format_saat_str(x):
                try: return f"{int(float(x)):02d}00"
                except: return str(x)
            
            birlesik["gmt"] = birlesik["gmt"].apply(format_saat_str)

            # Sütun İsimlendirme ve Sıralama
            col_map = {
                'sayfa': 'Tarih', 'gmt': 'Saat (GMT)', 'gmt_exact': 'Saat', 
                'ir': 'İndikatör (ir)', 'ix': 'İndikatör (ix)',
                'h': 'Bulut Yük. (h)', 'vv': 'Görüş (VV)', 'n': 'Toplam Bulut (N)',
                'dd': 'Rüzgar Yönü (dd)', 'ff': 'Rüzgar Hızı (ff)', 't': 'Sıcaklık (T)',
                'td': 'İşba (Td)', 'p0': 'Deniz Basıncı (P0)', 'p': 'İstasyon Basıncı (P)',
                'a': 'Basınç Karakteri (a)', 'ppp': 'Basınç Değişimi (ppp)',
                'ww': 'Halihazır Hava (ww)', 'ww2': 'Halihazır Hava 2 (ww2)', 'ww3': 'Halihazır Hava 3 (ww3)', 'w1': 'Geçmiş Hava 1 (W1)', 'w2': 'Geçmiş Hava 2 (W2)',
                'nh': 'Alçak/Orta Bulut (Nh)', 'cl': 'Alçak Bulut (CL)', 'cm': 'Orta Bulut (CM)',
                'ch': 'Yüksek Bulut (CH)', 'tx': 'Maks. Sıcaklık (Tx)', 'tn': 'Min. Sıcaklık (Tn)',
                'tg': 'Toprak Sıcaklığı (Tg)', 'e': 'Yerin Hali (E)', 'rrr': 'Yağış Miktarı (RRR)',
                'tr': 'Yağış Süresi (tR)', 'g910': '910 Grubu (Hamle)', 'g911': '911 Grubu (Hamle)',
                'g931': '931 Grubu (Kar)', 'g932': '932 Grubu (Taze Kar)', 'g960': '960 Grubu (Hadise)', 
                'rh': 'Bağıl Nem (%)', 'tw': 'Islak Sıcaklık (Tw)', 
                'buhar': 'Buharlaşma', 'rad_tipi': 'Radyasyon Tipi', 'radyasyon': 'Radyasyon Miktarı',
                'gunes': 'Güneşlenme Süresi', 'deniz_suyu': 'Deniz Suyu Sıc.', 'rrr_toplam': 'Toplam Yağış',
                'buh_alet_tipi': 'Buhar Aleti Tipi', 'e_kar': 'Yerin Hali (Kar)',
                'top_ustu_min': 'Toprak Üstü Min.',
                'mak_deger': 'Mak',
                '1. bulut kap': '1. Bulut Kap.', '1. bulut cins': '1. Bulut Cinsi', '1. bulut yuk': '1. Bulut Yük.',
                '2. bulut kap': '2. Bulut Kap.', '2. bulut cins': '2. Bulut Cinsi', '2. bulut yuk': '2. Bulut Yük.',
                '3. bulut kap': '3. Bulut Kap.', '3. bulut cins': '3. Bulut Cinsi', '3. bulut yuk': '3. Bulut Yük.',
                '4. bulut kap': '4. Bulut Kap.', '4. bulut cins': '4. Bulut Cinsi', '4. bulut yuk': '4. Bulut Yük.',
                'ww_hesaplanan': 'RE/GEÇMİŞ HADİSE', 
                'ANALİZ_SONUCU': 'DURUM', 'HATA_KODLARI': 'HATA KODU', 'HATA_ACIKLAMALARI': 'AÇIKLAMA',
                'RASATLAR': 'SİNOPTİK - Şifreli Mesaj', 'g924': '924 Grubu', 'hadise_kayit': 'Hadise Kayıtları',
                'personel': 'Personel',
                'bulten': 'METAR - Şifreli Mesaj'
            }
            new_columns = {}
            for c in birlesik.columns:
                base = c.replace('_sin', '').replace('_metar', '')
                suffix = '_sin' if '_sin' in c else ('_metar' if '_metar' in c else '')
                if base in col_map:
                    new_name = col_map[base]
                    if new_name.startswith("SİNOPTİK") or new_name.startswith("METAR"):
                        new_columns[c] = new_name
                    elif suffix == '_sin': new_name = f"SİNOPTİK - {new_name}"
                    elif suffix == '_metar': new_name = f"METAR - {new_name}"
                    new_columns[c] = new_name
                else: 
                    if suffix == '_sin': new_columns[c] = f"SİNOPTİK - {base.upper()}"
                    elif suffix == '_metar': new_columns[c] = f"METAR - {base.upper()}"
                    else: new_columns[c] = c.upper()
            birlesik.rename(columns=new_columns, inplace=True)

            # Aynı isme sahip sütunlar oluşursa (Örn: iki tane PERSONEL) Pandas'ın çökmesini engellemek için tekilleştir
            if any(birlesik.columns.duplicated()):
                cols = pd.Series(birlesik.columns)
                for dup in cols[cols.duplicated()].unique():
                    dup_indices = cols[cols == dup].index.tolist()
                    for idx_num, idx in enumerate(dup_indices):
                        if idx_num != 0:
                            cols[idx] = f"{dup}_{idx_num}"
                birlesik.columns = cols

            # --- İSTENEN KESİN SÜTUN SIRALAMASI ---
            istenen_siralama = [
                'Tarih', 'Saat (GMT)', 'SİNOPTİK - Saat', 'METAR - Saat', 'SİNOPTİK - Şifreli Mesaj', 'METAR - Şifreli Mesaj', 'DURUM', 'HATA KODU', 'AÇIKLAMA',
                'SİNOPTİK - İndikatör (ir)', 'SİNOPTİK - İndikatör (ix)', 'SİNOPTİK - Bulut Yük. (h)', 'SİNOPTİK - Görüş (VV)', 'METAR - Görüş (VV)',
                'SİNOPTİK - Toplam Bulut (N)', 'METAR - Toplam Bulut (N)', 'SİNOPTİK - Rüzgar Yönü (dd)', 'METAR - Rüzgar Yönü (dd)',
                'SİNOPTİK - Rüzgar Hızı (ff)', 'METAR - Rüzgar Hızı (ff)', 'SİNOPTİK - Sıcaklık (T)', 'METAR - Sıcaklık (T)',
                'SİNOPTİK - İşba (Td)', 'METAR - İşba (Td)', 'SİNOPTİK - Deniz Basıncı (P0)', 'METAR - Deniz Basıncı (P0)',
                'SİNOPTİK - İstasyon Basıncı (P)', 'METAR - İstasyon Basıncı (P)', 'SİNOPTİK - Basınç Karakteri (a)', 'SİNOPTİK - Basınç Değişimi (ppp)',
                'SİNOPTİK - Halihazır Hava (ww)', 'METAR - Halihazır Hava (ww)', 'SİNOPTİK - Geçmiş Hava 1 (W1)', 'SİNOPTİK - Geçmiş Hava 2 (W2)',
                'SİNOPTİK - Alçak/Orta Bulut (Nh)', 'SİNOPTİK - Alçak Bulut (CL)', 'SİNOPTİK - Orta Bulut (CM)', 'SİNOPTİK - Yüksek Bulut (CH)',
                'SİNOPTİK - Maks. Sıcaklık (Tx)', 'SİNOPTİK - Min. Sıcaklık (Tn)', 'SİNOPTİK - Toprak Sıcaklığı (Tg)', 'SİNOPTİK - Yerin Hali (E)',
                'SİNOPTİK - Yağış Miktarı (RRR)', 'SİNOPTİK - Yağış Süresi (tR)', 'SİNOPTİK - 910 Grubu (Hamle)', 'SİNOPTİK - 911 Grubu (Hamle)',
                'SİNOPTİK - 924 Grubu', 'SİNOPTİK - 931 Grubu (Kar)', 'SİNOPTİK - 932 Grubu (Taze Kar)', 'SİNOPTİK - 960 Grubu (Hadise)',
                'SİNOPTİK - Bağıl Nem (%)', 'METAR - Bağıl Nem (%)', 'METAR - Islak Sıcaklık (Tw)', 'SİNOPTİK - Toplam Yağış', 'SİNOPTİK - Yerin Hali (Kar)',
                'METAR - 1. Bulut Kap.', 'METAR - 1. Bulut Cinsi', 'METAR - 1. Bulut Yük.', 'METAR - 2. Bulut Kap.', 'METAR - 2. Bulut Cinsi', 'METAR - 2. Bulut Yük.',
                'METAR - 3. Bulut Kap.', 'METAR - 3. Bulut Cinsi', 'METAR - 3. Bulut Yük.', 'METAR - 4. Bulut Kap.', 'METAR - 4. Bulut Cinsi', 'METAR - 4. Bulut Yük.',
                'RE/GEÇMİŞ HADİSE', 'SİNOPTİK - Personel', 'METAR - Personel', 'SİNOPTİK - BG4', 'METAR - DIKINE_GORUS', 'SİNOPTİK - GMT_RAW', 'METAR - INCH'
            ]
            
            mevcut_istenen = [c for c in istenen_siralama if c in birlesik.columns]

            # UNNAMED, NAN veya isimsiz anlamsız sütunları nihai Excel raporundan tamamen gizle (Zaten RASATLAR sütununa eklendiler)
            def anlamsiz_mi(kolon_adi):
                k_str = str(kolon_adi).upper()
                if "UNNAMED" in k_str or "NAN" == k_str.strip():
                    return True
                if "METAR - " in k_str:
                    istenmeyen_metar_sutunlari = [
                        "911 GRUBU", "MİN. SICAKLIK", "MIN. SICAKLIK", "BULUT YÜK. (H)", "2. GRUP", "GMT_RAW", "İNDİKATÖR", "INDIKATOR",
                        "YAĞIŞ MİKTARI", "GEÇMİŞ HAVA", "GECMIS HAVA", "ALÇAK/ORTA BULUT", "ALCAK/ORTA BULUT", "ALÇAK BULUT", "ALCAK BULUT",
                        "ORTA BULUT", "YÜKSEK BULUT", "YUKSEK BULUT", "BASINÇ KARAKTERİ", "BASINC KARAKTERI", "BASINÇ DEĞİŞİMİ", "BASINC DEGISIMI",
                        "MAKS. SICAKLIK", "TOPRAK SICAKLIĞI", "TOPRAK SICAKLIGI", "YERİN HALİ", "YERIN HALI", "YAĞIŞ SÜRESİ", "YAGIS SURESI",
                        "924 GRUBU", "910 GRUBU", "931 GRUBU", "932 GRUBU", "960 GRUBU", "3. GRUP"
                    ]
                    if any(istenmeyen in k_str for istenmeyen in istenmeyen_metar_sutunlari):
                        return True
                # Eksiksiz tam döküm için METAR veri alanlarının filtrelenerek gizlenmesi iptal edildi.
                return False
                
            digerleri = [c for c in birlesik.columns if c not in mevcut_istenen and not anlamsiz_mi(c)]
            
            # Geriye kalan ve listede olmayan ekstra sütunları da isim benzerliğine göre yan yana getir
            kalan_gruplar = {}
            for c in digerleri:
                base = str(c).replace("SİNOPTİK - ", "").replace("METAR - ", "")
                if base not in kalan_gruplar:
                    kalan_gruplar[base] = []
                kalan_gruplar[base].append(c)
                
            sirali_digerleri = []
            for base in sorted(kalan_gruplar.keys()):
                # Alfabetik ters sıralama ile (S)İNOPTİK'in (M)ETAR'dan önce gelmesini sağlar
                sirali_grup = sorted(kalan_gruplar[base], reverse=True) 
                sirali_digerleri.extend(sirali_grup)

            birlesik = birlesik[mevcut_istenen + sirali_digerleri]
            # -------------------------------------------------------------------------------------

            # LOG DOSYASI ÇIKTISI: İşlem Özeti ve Hatalar
            print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
            print(f"{Colors.BOLD}İŞLEM ÖZETİ VE HATALI RASATLAR ({ay}/{yil}){Colors.ENDC}")
            print(f"{Colors.HEADER}{'-' * 60}{Colors.ENDC}")
            print(f"Okunan SİNOPTİK Sayısı : {Colors.OKBLUE}{sinoptik_sayisi}{Colors.ENDC}")
            print(f"Okunan METAR Sayısı    : {Colors.OKBLUE}{metar_sayisi}{Colors.ENDC}")
            print(f"Şablon Kayıt Sayısı    : {Colors.OKBLUE}{len(birlesik)}{Colors.ENDC}")

            logging.info("="*60)
            logging.info(f"İŞLEM ÖZETİ VE HATALI RASATLAR ({ay}/{yil})")
            logging.info("-" * 60)
            logging.info(f"Okunan SİNOPTİK Sayısı : {sinoptik_sayisi}")
            logging.info(f"Okunan METAR Sayısı    : {metar_sayisi}")
            logging.info(f"Şablon Kayıt Sayısı    : {len(birlesik)}")
            
            hatali_kayitlar = birlesik[~birlesik["DURUM"].isin(["Hata Yok", "Ara Rasat"])]
            print(f"Hatalı Kayıt Sayısı    : {Colors.FAIL}{len(hatali_kayitlar)}{Colors.ENDC}")
            print(f"{Colors.HEADER}{'-' * 60}{Colors.ENDC}")
            logging.info(f"Hatalı Kayıt Sayısı    : {len(hatali_kayitlar)}")
            logging.info("-" * 60)
            
            if iptal_istendi: raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
            if not hatali_kayitlar.empty:
                print(f"{Colors.BOLD}{'TARİH':<15} {'SAAT':<10} {'HATA KODU'}{Colors.ENDC}")
                print(f"{Colors.HEADER}{'-' * 60}{Colors.ENDC}")
                print(f"{Colors.BOLD}HATALI KAYIT DETAYLARI:{Colors.ENDC}")
                print(f"{Colors.HEADER}{'-' * 80}{Colors.ENDC}")
                logging.info("HATALI KAYIT DETAYLARI:")
                logging.info("-" * 80)
                for _, row in hatali_kayitlar.iterrows():
                    tarih = str(row.get('Tarih', ''))
                    saat = str(row.get('Saat (GMT)', ''))
                    hata_kodu = str(row.get('HATA KODU', ''))
                    aciklama = str(row.get('AÇIKLAMA', ''))
                    sin_ham = str(row.get('SİNOPTİK - Şifreli Mesaj', ''))
                    met_ham = str(row.get('METAR - Şifreli Mesaj', ''))
                    personel = str(row.get('SİNOPTİK - Personel', row.get('Personel', 'Bilinmiyor/Belirtilmemiş')))
                    
                    print(f"{tarih: <15} {saat: <10} {Colors.FAIL}{hata_kodu}{Colors.ENDC}")
                    logging.info(f"[{tarih} - {saat} GMT] HATA: {hata_kodu}")
                    logging.info(f" -> AÇIKLAMA : {aciklama}")
                    logging.info(f" -> SİNOPTİK : {sin_ham}")
                    logging.info(f" -> METAR    : {met_ham}")
                    logging.info(f" -> PERSONEL : {personel}")
                    logging.info("-" * 80)
            else:
                print(f"{Colors.OKGREEN}Tebrikler! Hiçbir hata bulunamadı.{Colors.ENDC}")
                logging.info("Tebrikler! Hiçbir hata bulunamadı.")
            print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
            logging.info("="*60)
            
            # LOG HANDLER'INI FLUSH ET (Verilerin disk'e yazılması için)
            logging_handler.flush()
            
            # --- YENİ: EXCEL YERİNE EKRANDA HIZLI GÖSTERİM ---
            def arayuzde_goster():
                if iptal_istendi: return
                pencere = tk.Toplevel(root)
                pencere.title(f"Detaylı Test Raporu - {ay}/{yil}")
                pencere.geometry("1200x650")
                pencere.configure(bg="#F8F9FA")
                
                top_ctrl = tk.Frame(pencere, bg="#ECEFF1", pady=5)
                top_ctrl.pack(fill="x", side="top")
                tk.Label(top_ctrl, text="  SİNOPTİK / METAR ANALİZ ARAYÜZÜ", font=("Segoe UI", 11, "bold"), bg="#ECEFF1", fg="#37474F").pack(side="left")
                tk.Button(top_ctrl, text="❌ KAPAT", command=pencere.destroy, bg="#D32F2F", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10).pack(side="right", padx=5)
                tk.Button(top_ctrl, text="🗖 TAM EKRAN", command=lambda: pencere.state('zoomed') if pencere.state() != 'zoomed' else pencere.state('normal'), bg="#90A4AE", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10).pack(side="right", padx=5)
                tk.Button(top_ctrl, text="➖ SİMGE DURUMU", command=pencere.iconify, bg="#90A4AE", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10).pack(side="right", padx=5)
                
                def ekrandakileri_excele_aktar():
                    dosya_yolu = filedialog.asksaveasfilename(
                        parent=pencere,
                        defaultextension=".xlsx",
                        filetypes=[("Excel Dosyası", "*.xlsx")],
                        initialfile=f"Filtrelenmis_Rapor_{ay}_{yil}.xlsx",
                        title="Excel Olarak Kaydet"
                    )
                    if not dosya_yolu: return
                    
                    try:
                        veri = []
                        for item in tree.get_children():
                            vals = tree.item(item, "values")
                            if vals[0] == "☑":
                                veri.append(vals[1:])
                        
                        if not veri:
                            if messagebox.askyesno("Uyarı", "Hiçbir kayıt seçilmemiş (☑). Ekranda görünen TÜM kayıtlar dışa aktarılsın mı?", parent=pencere):
                                for item in tree.get_children():
                                    veri.append(tree.item(item, "values")[1:])
                            else:
                                return
                        
                        if not veri:
                            messagebox.showwarning("Uyarı", "Aktarılacak veri yok.", parent=pencere)
                            return
                        
                        df_export = pd.DataFrame(veri, columns=cols[1:])
                        df_export.to_excel(dosya_yolu, index=False)
                        messagebox.showinfo("Başarılı", f"{len(veri)} kayıt Excel'e aktarıldı:\n{dosya_yolu}", parent=pencere)
                        os.startfile(dosya_yolu)
                    except Exception as ex:
                        messagebox.showerror("Hata", f"Dışa aktarım sırasında hata:\n{ex}", parent=pencere)

                tk.Button(top_ctrl, text="📥 EKRANDAKİLERİ EXCEL'E AKTAR", command=ekrandakileri_excele_aktar, bg="#107C41", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10).pack(side="right", padx=5)

                # --- BİLGİ PANELİ ---
                info_frame = tk.Frame(pencere, bg="#F8F9FA")
                info_frame.pack(fill="x", padx=15, pady=10)
                
                def create_info_card(parent, title, value, bg_color):
                    card = tk.Frame(parent, bg=bg_color, bd=0, relief="flat", padx=10, pady=10)
                    card.pack(side="left", fill="both", expand=True, padx=5)
                    tk.Label(card, text=title, font=("Segoe UI", 11, "bold"), bg=bg_color, fg="white").pack()
                    tk.Label(card, text=value, font=("Segoe UI", 20, "bold"), bg=bg_color, fg="white").pack()

                create_info_card(info_frame, "SİNOPTİK", str(sinoptik_sayisi), "#0066CC")
                create_info_card(info_frame, "METAR", str(metar_normal_sayisi), "#107C41")
                create_info_card(info_frame, "SPECI", str(speci_sayisi), "#673AB7")
                create_info_card(info_frame, "Hatalı Kayıt", str(len(hatali_kayitlar)), "#D32F2F")
                
                # Sekmeli yapı (Notebook) oluştur
                notebook = ttk.Notebook(pencere)
                notebook.pack(fill="both", expand=True, padx=15, pady=5)
                
                # --- SÜTUN SIRALAMA FONKSİYONU ---
                def treeview_sort_column(tv, col, reverse):
                    l = [(tv.set(k, col), k) for k in tv.get_children('')]
                    
                    def try_float(val):
                        try:
                            # Özel formatlar (h1, h2) için sıralama
                            match = re.search(r'\d+', str(val))
                            if match and "h" in str(val).lower() and len(str(val)) < 6:
                                return float(match.group())
                            return float(val)
                        except:
                            return str(val).lower()
                            
                    l.sort(key=lambda t: try_float(t[0]), reverse=reverse)
                    for index, (val, k) in enumerate(l):
                        tv.move(k, '', index)
                    tv.heading(col, command=lambda: treeview_sort_column(tv, col, not reverse))

                # --- SEÇİM (CHECKBOX) VE SİLME FONKSİYONLARI ---
                def tree_toggle_checkbox(event, tv):
                    region = tv.identify("region", event.x, event.y)
                    if region == "heading":
                        col = tv.identify_column(event.x)
                        if col == "#1":
                            current = tv.heading(col)["text"]
                            new_val = "☑" if current == "☐" else "☐"
                            tv.heading(col, text=new_val)
                            for item in tv.get_children():
                                vals = list(tv.item(item, "values"))
                                vals[0] = new_val
                                tv.item(item, values=vals)
                            return "break"
                    elif region == "cell":
                        col = tv.identify_column(event.x)
                        if col == "#1":
                            item = tv.identify_row(event.y)
                            if item:
                                vals = list(tv.item(item, "values"))
                                vals[0] = "☑" if vals[0] == "☐" else "☐"
                                tv.item(item, values=vals)
                                return "break"

                def to_csv_value(v):
                    s = str(v)
                    if ';' in s or '"' in s or '\n' in s:
                        return '"' + s.replace('"', '""') + '"'
                    return s

                def secilenleri_sil(tv):
                    silinecekler = [item for item in tv.get_children() if tv.item(item, "values")[0] == "☑"]
                    if not silinecekler:
                        messagebox.showwarning("Uyarı", "Silinecek/Gizlenecek kayıt seçilmedi.", parent=pencere)
                        return
                    if messagebox.askyesno("Onay", f"Seçili {len(silinecekler)} kaydı gizlemek/silmek istediğinize emin misiniz?", parent=pencere):
                        for item in silinecekler:
                            tv.delete(item)

                def secilileri_panoya_kopyala(tv, kolonlar):
                    secililer = [item for item in tv.get_children() if tv.item(item, "values")[0] == "☑"]
                    if not secililer:
                        messagebox.showwarning("Uyarı", "Kopyalanacak kayıt seçilmedi.", parent=pencere)
                        return
                    
                    basliklar = [str(col) for col in kolonlar if col != "Seç"]
                    metin = ";".join(to_csv_value(b) for b in basliklar) + "\n"
                    
                    for item in secililer:
                        vals = tv.item(item, "values")[1:]
                        metin += ";".join(to_csv_value(v) for v in vals) + "\n"
                        
                    pencere.clipboard_clear()
                    pencere.clipboard_append(metin)
                    messagebox.showinfo("Başarılı", f"{len(secililer)} kayıt panoya kopyalandı.", parent=pencere)

                # --- ORTAK ŞİFRE ÇÖZÜMLEYİCİ PENCERELERİ ---
                def goster_sinoptik_cozumleyici(sinoptik_sifresi, parent_widget):
                    if SynopDecoder is None:
                        messagebox.showerror("Hata", "SynopDecoder modülü yüklenemedi.", parent=parent_widget)
                        return
                        
                    if not sinoptik_sifresi or sinoptik_sifresi.lower() in ["-", "nan", ""]:
                        messagebox.showinfo("Bilgi", "Çözümlenecek geçerli bir SİNOPTİK şifresi bulunamadı.", parent=parent_widget)
                        return
                        
                    try:
                        decoder = SynopDecoder()
                        ayiklanan_veri = decoder.decode_line(sinoptik_sifresi)
                        # anakardelenden temizlik mantığı
                        temiz_sifre = re.sub(r'^(?:SİNOPTİK|SYNOP|SINOPTIK|KAYIT:.*?BULTEN\s*:|BULTEN\s*:|.*GELDİ:|.*YENİ RASAT)\s*', '', sinoptik_sifresi, flags=re.IGNORECASE|re.DOTALL).strip()
                        ayiklanan_veri = decoder.decode_line(temiz_sifre)
                        is_valid = decoder.validate()
                        hatalar = decoder.get_errors() if hasattr(decoder, 'get_errors') else []
                        
                        cozum_pop = tk.Toplevel(parent_widget)
                        cozum_pop.title("SİNOPTİK Şifre Çözümleyici")
                        cozum_pop.geometry("600x450")
                        cozum_pop.geometry("750x550")
                        cozum_pop.configure(bg="#F8F9FA")
                        
                        # Dikey ve Yatay Kaydırma Çubukları (Scrollbar)
                        f_txt = tk.Frame(cozum_pop, bg="#37474F")
                        f_txt.pack(expand=True, fill="both", padx=15, pady=15)
                        
                        v_scroll = tk.Scrollbar(f_txt, orient="vertical")
                        v_scroll.pack(side="right", fill="y")
                        h_scroll = tk.Scrollbar(f_txt, orient="horizontal")
                        h_scroll.pack(side="bottom", fill="x")
                        
                        txt = tk.Text(f_txt, wrap="none", font=("Consolas", 11), bg="#37474F", fg="#69F0AE", padx=15, pady=15, xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
                        txt.pack(expand=True, fill="both")
                        
                        v_scroll.config(command=txt.yview)
                        h_scroll.config(command=txt.xview)
                        
                        sonuc = f"--- ORİJİNAL ŞİFRE ---\n{sinoptik_sifresi}\n\n"
                        sonuc = f"--- ORİJİNAL ŞİFRE ---\n{temiz_sifre}\n\n"
                        sonuc += f"Format Geçerli mi? : {'EVET ✅' if is_valid else 'HAYIR ❌'}\n"
                        
                        if hatalar:
                            sonuc += "\nTespit Edilen Format Hataları:\n"
                            for h in hatalar: sonuc += f" - {h}\n"
                                
                        sonuc += "\n--- AYIKLANAN VERİLER ---\n"
                        if ayiklanan_veri:
                            if hasattr(decoder, 'generate_human_readable'):
                                sonuc += decoder.generate_human_readable(ayiklanan_veri) + "\n"
                            else:
                                for k, v in ayiklanan_veri.items():
                                    if not k.startswith('_') and k not in ['errors', 'raw_line', 'raw_groups', 'ham_veri']:
                                        sonuc += f"{str(k).upper():<20}: {v}\n"
                        else:
                            sonuc += "Çözümlenebilecek geçerli bir veri bulunamadı.\n"
                                
                        txt.insert("1.0", sonuc)
                        txt.config(state=tk.DISABLED)
                        
                        def metni_kopyala():
                            cozum_pop.clipboard_clear()
                            cozum_pop.clipboard_append(sonuc)
                            messagebox.showinfo("Başarılı", "Çözümlenen veriler panoya kopyalandı!", parent=cozum_pop)
                            
                        def metni_kaydet():
                            dosya_yolu = filedialog.asksaveasfilename(
                                parent=cozum_pop,
                                title="SİNOPTİK Çözümünü Kaydet",
                                defaultextension=".txt",
                                filetypes=[("Metin Belgesi", "*.txt"), ("Tüm Dosyalar", "*.*")],
                                initialfile="SINOPTIK_Cozum_Raporu.txt"
                            )
                            if dosya_yolu:
                                try:
                                    with open(dosya_yolu, "w", encoding="utf-8") as f:
                                        f.write(sonuc)
                                    messagebox.showinfo("Başarılı", f"Dosya kaydedildi:\n{dosya_yolu}", parent=cozum_pop)
                                except Exception as ex:
                                    messagebox.showerror("Hata", f"Kayıt sırasında hata oluştu:\n{ex}", parent=cozum_pop)
                                    
                        btn_frame = tk.Frame(cozum_pop, bg="#F8F9FA")
                        btn_frame.pack(pady=(0, 15))
                            
                        btn_kopyala = tk.Button(btn_frame, text="Panoya Kopyala", command=metni_kopyala, font=("Segoe UI", 10, "bold"), bg="#0066CC", fg="white", activebackground="#0052A3", activeforeground="white", cursor="hand2", padx=20, pady=5)
                        btn_kopyala.pack(side=tk.LEFT, padx=10)
                        
                        btn_kaydet = tk.Button(btn_frame, text="TXT Kaydet", command=metni_kaydet, font=("Segoe UI", 10, "bold"), bg="#107C41", fg="white", activebackground="#0C5D31", activeforeground="white", cursor="hand2", padx=20, pady=5)
                        btn_kaydet.pack(side=tk.LEFT, padx=10)
                    except Exception as e:
                        messagebox.showerror("Hata", f"Çözümleme Hatası:\n{e}", parent=parent_widget)

                def goster_metar_cozumleyici(metar_sifresi, parent_widget):
                    if MetarDecoder is None:
                        messagebox.showerror("Hata", "MetarDecoder modülü yüklenemedi.", parent=parent_widget)
                        return

                    if not metar_sifresi or metar_sifresi.lower() in ["-", "nan", ""]:
                        messagebox.showinfo("Bilgi", "Çözümlenecek geçerli bir METAR şifresi bulunamadı.", parent=parent_widget)
                        return
                        
                    try:
                        decoder = MetarDecoder()
                        ayiklanan_veri = decoder.decode_line(metar_sifresi)
                        # anakardelenden temizlik mantığı
                        temiz_sifre = re.sub(r'^(?:KAYIT:.*?BULTEN\s*:|BULTEN\s*:|.*GELDİ:|.*YENİ RASAT)\s*', '', metar_sifresi, flags=re.IGNORECASE|re.DOTALL).strip()
                        m_match = re.search(r'(METAR|SPECI|SATT\d*|SA[A-Z0-9]{2}|SP[A-Z0-9]{2})', temiz_sifre)
                        if m_match: temiz_sifre = temiz_sifre[m_match.start():]
                        
                        ayiklanan_veri = decoder.decode_line(temiz_sifre)
                        
                        metar_pop = tk.Toplevel(parent_widget)
                        metar_pop.title("METAR Şifre Çözümleyici")
                        metar_pop.geometry("600x450")
                        metar_pop.geometry("750x550")
                        metar_pop.configure(bg="#F8F9FA")
                        
                        f_txt_m = tk.Frame(metar_pop, bg="#37474F")
                        f_txt_m.pack(expand=True, fill="both", padx=15, pady=15)
                        
                        v_scroll_m = tk.Scrollbar(f_txt_m, orient="vertical")
                        v_scroll_m.pack(side="right", fill="y")
                        h_scroll_m = tk.Scrollbar(f_txt_m, orient="horizontal")
                        h_scroll_m.pack(side="bottom", fill="x")
                        
                        txt = tk.Text(f_txt_m, wrap="none", font=("Consolas", 11), bg="#37474F", fg="#81D4FA", padx=15, pady=15, xscrollcommand=h_scroll_m.set, yscrollcommand=v_scroll_m.set)
                        txt.pack(expand=True, fill="both")
                        
                        v_scroll_m.config(command=txt.yview)
                        h_scroll_m.config(command=txt.xview)
                        
                        if ayiklanan_veri:
                            sonuc = decoder.generate_human_readable(ayiklanan_veri)
                        else:
                            sonuc = f"--- ORİJİNAL METAR ŞİFRESİ ---\n{metar_sifresi}\n\nÇözümlenebilecek geçerli bir veri bulunamadı."
                            sonuc = f"--- ORİJİNAL METAR ŞİFRESİ ---\n{temiz_sifre}\n\nÇözümlenebilecek geçerli bir veri bulunamadı."
                            
                        txt.insert("1.0", sonuc)
                        txt.config(state=tk.DISABLED)
                        
                        def metni_kopyala():
                            metar_pop.clipboard_clear()
                            metar_pop.clipboard_append(sonuc)
                            messagebox.showinfo("Başarılı", "METAR verileri panoya kopyalandı!", parent=metar_pop)
                            
                        def metni_kaydet():
                            dosya_yolu = filedialog.asksaveasfilename(
                                parent=metar_pop,
                                title="METAR Çözümünü Kaydet",
                                defaultextension=".txt",
                                filetypes=[("Metin Belgesi", "*.txt"), ("Tüm Dosyalar", "*.*")],
                                initialfile="METAR_Cozum_Raporu.txt"
                            )
                            if dosya_yolu:
                                try:
                                    with open(dosya_yolu, "w", encoding="utf-8") as f:
                                        f.write(sonuc)
                                    messagebox.showinfo("Başarılı", f"Dosya kaydedildi:\n{dosya_yolu}", parent=metar_pop)
                                except Exception as ex:
                                    messagebox.showerror("Hata", f"Kayıt sırasında hata oluştu:\n{ex}", parent=metar_pop)
                                    
                        btn_frame = tk.Frame(metar_pop, bg="#F8F9FA")
                        btn_frame.pack(pady=(0, 15))
                            
                        btn_kopyala = tk.Button(btn_frame, text="Panoya Kopyala", command=metni_kopyala, font=("Segoe UI", 10, "bold"), bg="#0066CC", fg="white", activebackground="#0052A3", activeforeground="white", cursor="hand2", padx=20, pady=5)
                        btn_kopyala.pack(side=tk.LEFT, padx=10)
                        
                        btn_kaydet = tk.Button(btn_frame, text="TXT Kaydet", command=metni_kaydet, font=("Segoe UI", 10, "bold"), bg="#107C41", fg="white", activebackground="#0C5D31", activeforeground="white", cursor="hand2", padx=20, pady=5)
                        btn_kaydet.pack(side=tk.LEFT, padx=10)
                    except Exception as e:
                        messagebox.showerror("Hata", f"Çözümleme Hatası:\n{e}", parent=parent_widget)

                # --- SAĞ TIK MENÜSÜ FONKSİYONU ---
                def show_context_menu(event, tv):
                    # Sağ tıklanan satırı seç
                    iid = tv.identify_row(event.y)
                    if iid and iid not in tv.selection():
                        tv.selection_set(iid)
                        
                    menu = tk.Menu(tv, tearoff=0)
                    
                    def copy_selection():
                        selected = tv.selection()
                        if not selected: return
                        text_to_copy = ""
                        for item in selected:
                            vals = tv.item(item, "values")
                            if tv["columns"][0] == "Seç":
                                vals = vals[1:]
                            text_to_copy += ";".join(to_csv_value(v) for v in vals) + "\n"
                        tv.clipboard_clear()
                        tv.clipboard_append(text_to_copy.strip())
                        
                    def select_all():
                        tv.selection_set(tv.get_children())
                        
                    def tr_lower(metin):
                        if not metin: return ""
                        return str(metin).replace("I", "ı").replace("İ", "i").replace("Ğ", "ğ").replace("Ü", "ü").replace("Ş", "ş").replace("Ö", "ö").replace("Ç", "ç").lower()

                    def find_text():
                        search_term = simpledialog.askstring("Bul", "Aranacak kelime(ler):", parent=tv)
                        if not search_term: return
                        
                        # Kullanıcının girdiği kelimeleri boşluklara göre ayır (Örn: "h37 06:00")
                        arananlar = tr_lower(search_term.strip()).split()
                        tv.selection_remove(tv.selection())
                        found = False
                        for item in tv.get_children():
                            values = tv.item(item, "values")
                            satir_metni = tr_lower(" ".join(str(v) for v in values))
                            
                            # Aranan TÜM kelimeler bu satırda geçiyorsa seç (Akıllı çoklu arama)
                            if all(kelime in satir_metni for kelime in arananlar):
                                tv.selection_add(item)
                                if not found:
                                    tv.see(item)
                                    found = True
                                    
                        if not found:
                            messagebox.showinfo("Bulunamadı", "Eşleşen kayıt bulunamadı.", parent=tv)

                    def cozumle_sinoptik():
                        selected = tv.selection()
                        if not selected: return
                        degerler = tv.item(selected[0], "values")
                        kolonlar = tv["columns"]
                        s_idx = list(kolonlar).index("SİNOPTİK Şifresi") if "SİNOPTİK Şifresi" in kolonlar else -1
                        if s_idx != -1:
                            sinoptik_sifresi = str(degerler[s_idx]).strip() 
                            goster_sinoptik_cozumleyici(sinoptik_sifresi, tv)

                    def cozumle_metar():
                        selected = tv.selection()
                        if not selected: return
                        degerler = tv.item(selected[0], "values")
                        kolonlar = tv["columns"]
                        m_idx = list(kolonlar).index("METAR Şifresi") if "METAR Şifresi" in kolonlar else -1
                        if m_idx != -1:
                            metar_sifresi = str(degerler[m_idx]).strip() 
                            goster_metar_cozumleyici(metar_sifresi, tv)

                    menu.add_command(label="Satırı Kopyala", command=copy_selection)
                    menu.add_command(label="Hepsini Seç", command=select_all)
                    menu.add_separator()
                    menu.add_command(label="SİNOPTİK Şifresini Çözümle", command=cozumle_sinoptik)
                    menu.add_command(label="METAR Şifresini Çözümle", command=cozumle_metar)
                    menu.add_separator()
                    menu.add_command(label="Bul...", command=find_text)
                    
                    try:
                        menu.tk_popup(event.x_root, event.y_root)
                    finally:
                        menu.grab_release()

                # --- YENİ: Çift tıklama ile detay okuma fonksiyonu ---
                def satir_detay_goster(event, tree_widget, pencere_baslik):
                    secili = tree_widget.selection()
                    if not secili: return
                    
                    degerler = tree_widget.item(secili[0], "values")
                    kolonlar = tree_widget["columns"]
                    
                    detay_pop = tk.Toplevel(pencere)
                    detay_pop.title(pencere_baslik)
                    detay_pop.geometry("600x450")
                    detay_pop.geometry("750x550")
                    detay_pop.configure(bg="#F8F9FA")
                    
                    f_txt_d = tk.Frame(detay_pop, bg="white")
                    f_txt_d.pack(expand=True, fill="both", padx=15, pady=15)
                    v_scroll_d = tk.Scrollbar(f_txt_d, orient="vertical")
                    v_scroll_d.pack(side="right", fill="y")
                    
                    text_alan = tk.Text(f_txt_d, wrap="word", font=("Segoe UI", 11), bg="white", yscrollcommand=v_scroll_d.set)
                    text_alan.pack(expand=True, fill="both")
                    v_scroll_d.config(command=text_alan.yview)
                    
                    detay_metni = ""
                    for col, val in zip(kolonlar, degerler):
                        if str(col).upper() == "SEÇ": continue
                        detay_metni += f"■ {str(col).upper()}:\n{val}\n\n"
                        
                    text_alan.insert("1.0", detay_metni.strip())
                    text_alan.config(state=tk.DISABLED) # Sadece okunabilir yapar

                    # --- Sağ Tık Menüsü (Detay Penceresi İçin) ---
                    sag_tik_menu = tk.Menu(text_alan, tearoff=0)
                    
                    def kopyala():
                        try:
                            secili_metin = text_alan.selection_get()
                            detay_pop.clipboard_clear()
                            detay_pop.clipboard_append(secili_metin)
                        except tk.TclError:
                            pass
                            
                    def tumunu_kopyala():
                        tum_metin = text_alan.get("1.0", tk.END).strip()
                        detay_pop.clipboard_clear()
                        detay_pop.clipboard_append(tum_metin)

                    def hepsini_sec():
                        text_alan.tag_add("sel", "1.0", "end")
                        return 'break'

                    sag_tik_menu.add_command(label="Kopyala", command=kopyala)
                    sag_tik_menu.add_command(label="Tümünü Kopyala", command=tumunu_kopyala)
                    sag_tik_menu.add_separator()
                    sag_tik_menu.add_command(label="Hepsini Seç", command=hepsini_sec)

                    # Şifre çözümleme butonlarını detay penceresinde sağ tıka ekle
                    sinoptik_idx = -1
                    metar_idx = -1
                    for i, col in enumerate(kolonlar):
                        col_str = str(col).upper()
                        if "SİNOPTİK" in col_str and "ŞİFRE" in col_str:
                            sinoptik_idx = i
                        elif "METAR" in col_str and "ŞİFRE" in col_str:
                            metar_idx = i
                            
                    if sinoptik_idx != -1 or metar_idx != -1:
                        sag_tik_menu.add_separator()
                        
                        if sinoptik_idx != -1:
                            def detay_cozumle_sinoptik():
                                goster_sinoptik_cozumleyici(str(degerler[sinoptik_idx]).strip(), detay_pop)
                            sag_tik_menu.add_command(label="SİNOPTİK Şifresini Çözümle", command=detay_cozumle_sinoptik)
                            
                        if metar_idx != -1:
                            def detay_cozumle_metar():
                                goster_metar_cozumleyici(str(degerler[metar_idx]).strip(), detay_pop)
                            sag_tik_menu.add_command(label="METAR Şifresini Çözümle", command=detay_cozumle_metar)

                    text_alan.bind("<Button-3>", lambda e: sag_tik_menu.tk_popup(e.x_root, e.y_root))

                # --- 1. SEKME: HATALI RASATLAR ---
                tree_frame = tk.Frame(notebook, bg="white")
                notebook.add(tree_frame, text="📊 Rasatlar (Hatalı / Tüm)")
                
                # FİLTRELEME ALANI
                filter_frame = tk.Frame(tree_frame, bg="white")
                filter_frame.pack(fill="x", padx=5, pady=5)
                
                btn_sil = tk.Button(filter_frame, text="🗑️ Seçili Olanları Gizle/Sil", command=lambda: secilenleri_sil(tree), bg="#D32F2F", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10)
                btn_sil.pack(side="right", padx=5)

                btn_kopyala = tk.Button(filter_frame, text="📋 Seçilileri Kopyala", command=lambda: secilileri_panoya_kopyala(tree, cols), bg="#008CBA", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10)
                btn_kopyala.pack(side="right", padx=5)

                tk.Label(filter_frame, text="🔍 Gösterim Filtresi:", bg="white", font=("Segoe UI", 11, "bold"), fg="#343A40").pack(side="left", padx=5)
                filtre_combo = ttk.Combobox(filter_frame, values=["Hatalı Rasatlar (Tümü)", "Tüm Kayıtlar (Hatalı + Doğru)", "Tüm METAR/SPECI Rasatları", "Tüm SİNOPTİK Rasatları", "Sadece Çapraz Kontrol Hataları", "Sadece WMO / Standart Hatalar", "Veri Yok / Eksik Hataları", "Sadece 7. Grup (Halihazır/Geçmiş Hava) Hataları", "Sadece 8. Grup (Bulut) Hataları"], state="readonly", width=45, font=("Segoe UI", 11))
                filtre_combo.set("Hatalı Rasatlar (Tümü)")
                filtre_combo.pack(side="left", padx=5)
                
                cols = ("Seç", "Tarih", "Saat", "SİNOPTİK Saat", "METAR Saat", "Hata Kodu", "Açıklama", "SİNOPTİK Şifresi", "METAR Şifresi")
                tree = ttk.Treeview(tree_frame, columns=cols, show="headings", style="Treeview")
                
                tree.heading("Seç", text="☐")
                tree.heading("Tarih", text="Tarih")
                tree.heading("Saat", text="Saat")
                tree.heading("SİNOPTİK Saat", text="SİNOPTİK Saat")
                tree.heading("METAR Saat", text="METAR Saat")
                tree.heading("Hata Kodu", text="Hata Kodu")
                tree.heading("Açıklama", text="Açıklama")
                tree.heading("SİNOPTİK Şifresi", text="SİNOPTİK Şifresi")
                tree.heading("METAR Şifresi", text="METAR Şifresi")
                
                tree.column("Seç", width=40, anchor="center")
                tree.column("Tarih", width=90, anchor="center")
                tree.column("Saat", width=50, anchor="center")
                tree.column("SİNOPTİK Saat", width=100, anchor="center")
                tree.column("METAR Saat", width=100, anchor="center")
                tree.column("Hata Kodu", width=120, anchor="center")
                tree.column("Açıklama", width=350, anchor="w")
                tree.column("SİNOPTİK Şifresi", width=250, anchor="w")
                tree.column("METAR Şifresi", width=250, anchor="w")
                
                yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
                yscroll.pack(side="right", fill="y")
                xscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
                xscroll.pack(side="bottom", fill="x")
                tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
                tree.pack(side="left", fill="both", expand=True)
                
                tree.bind("<Button-1>", lambda e: tree_toggle_checkbox(e, tree))
                tree.bind("<Double-1>", lambda e: satir_detay_goster(e, tree, "Rasat Hata Detayı"))
                tree.bind("<Button-3>", lambda e: show_context_menu(e, tree))
                for col in cols:
                    if col != "Seç":
                        tree.heading(col, command=lambda c=col: treeview_sort_column(tree, c, False))
                
                def populate_tree(filter_type="Hatalı Rasatlar (Tümü)"):
                    for item in tree.get_children():
                        tree.delete(item)

                    if filter_type in ["Tüm Kayıtlar (Hatalı + Doğru)", "Tüm METAR/SPECI Rasatları", "Tüm SİNOPTİK Rasatları"]:
                        hedef_df = birlesik
                    else:
                        hedef_df = hatali_kayitlar

                    if hedef_df.empty:
                        tree.insert("", tk.END, values=("-", "-", "-", "-", "BİLGİ", "Gösterilecek kayıt bulunamadı.", "-", "-"))
                        return

                    def safe_tree_str(val):
                        if pd.isna(val) or str(val).strip().lower() in ["nan", "none", "na", "<na>", ""]:
                            return "-"
                        return str(val).strip()

                    hazirlanan_veriler = []

                    for _, row in hedef_df.iterrows():
                        hata_kodu = str(row.get("HATA KODU", ""))
                        if not hata_kodu and row.get("DURUM") == "Veri Yok":
                            hata_kodu = "Veri Yok"
                        elif not hata_kodu:
                            hata_kodu = "Hata Yok"

                        hk_upper = hata_kodu.upper()
                        is_capraz = "ÇAPRAZ" in hk_upper or "UYUM" in hk_upper or "VAL_" in hk_upper
                        is_veri_yok = "VERİ YOK" in hk_upper or "VERI YOK" in hk_upper

                        if filter_type == "Sadece Çapraz Kontrol Hataları" and not is_capraz:
                            continue
                        if filter_type == "Sadece WMO / Standart Hatalar" and (is_capraz or is_veri_yok or hata_kodu == "Hata Yok"):
                            continue
                        if filter_type == "Veri Yok / Eksik Hataları" and not is_veri_yok:
                            continue
                            
                        # 7. Grup (ww, W1, W2) filtreleme mantığı
                        is_7_grup = False
                        aciklama = str(row.get("AÇIKLAMA", "")).upper()
                        hk_list = [k.strip() for k in hk_upper.split(",")]
                        for hk in hk_list:
                            if hk.startswith("H"):
                                try:
                                    import re
                                    num = int(re.sub(r'\D', '', hk))
                                    if 76 <= num <= 118 or 286 <= num <= 289 or 318 <= num <= 339 or 361 <= num <= 374 or num in [378, 379]:
                                        is_7_grup = True
                                        break
                                except: pass
                        if not is_7_grup and any(k in aciklama for k in ["WW=", "W1", "W2", "HALİHAZIR", "GEÇMİŞ HAVA", "7. GRUP", "ŞİMŞEK", "ORAJ", "SİS", "PUS", "KAR ", "YAĞMUR"]):
                            is_7_grup = True

                        if filter_type == "Sadece 7. Grup (Halihazır/Geçmiş Hava) Hataları" and not is_7_grup:
                            continue
                            
                        # 8. Grup (N, Nh, CL, CM, CH, h) filtreleme mantığı
                        is_8_grup = False
                        if filter_type == "Sadece 8. Grup (Bulut) Hataları":
                            for hk in hk_list:
                                if hk.startswith("H"):
                                    try:
                                        import re
                                        num = int(re.sub(r'\D', '', hk))
                                        if 26 <= num <= 36 or 120 <= num <= 172 or 278 <= num <= 280 or 284 <= num <= 285 or 311 <= num <= 314 or 353 <= num <= 358:
                                            is_8_grup = True
                                            break
                                    except: pass
                            if not is_8_grup and any(k in aciklama for k in ["BULUT", "TAVAN", "DİKEY", "KAPALILIK", "CİNS", "8. GRUP", "N=", "NH=", "CL=", "CM=", "CH="]):
                                is_8_grup = True
                            if not is_8_grup:
                                continue
                            
                        sin_msg = safe_tree_str(row.get("SİNOPTİK - Şifreli Mesaj"))
                        met_msg = safe_tree_str(row.get("METAR - Şifreli Mesaj"))
                        
                        if filter_type == "Tüm SİNOPTİK Rasatları" and sin_msg == "-":
                            continue
                        if filter_type == "Tüm METAR/SPECI Rasatları" and met_msg == "-":
                            continue

                        hazirlanan_veriler.append((
                            "☐",
                            safe_tree_str(row.get("Tarih")),
                            safe_tree_str(row.get("Saat (GMT)")),
                            safe_tree_str(row.get("SİNOPTİK - Saat")),
                            safe_tree_str(row.get("METAR - Saat")),
                            hata_kodu,
                            safe_tree_str(row.get("AÇIKLAMA")),
                            sin_msg,
                            met_msg
                        ))
                        
                    if not hazirlanan_veriler:
                        tree.insert("", tk.END, values=("☐", "-", "-", "-", "-", "BİLGİ", "Gösterilecek kayıt bulunamadı.", "-", "-"))
                        return

                    def chunk_insert(index=0, chunk_size=100):
                        for i in range(index, min(index + chunk_size, len(hazirlanan_veriler))):
                            tree.insert("", tk.END, values=hazirlanan_veriler[i])
                        
                        if index + chunk_size < len(hazirlanan_veriler):
                            tree.after(10, chunk_insert, index + chunk_size, chunk_size)

                    chunk_insert()

                filtre_combo.bind("<<ComboboxSelected>>", lambda e: populate_tree(filtre_combo.get()))
                populate_tree()
                        
                # --- 2. SEKME: TÜM KURAL TESTLERİ DETAYI ---
                kural_frame = tk.Frame(notebook, bg="white")
                notebook.add(kural_frame, text="✅ Test Edilen Tüm Kurallar (h1..h267)")
                
                kural_top_frame = tk.Frame(kural_frame, bg="white")
                kural_top_frame.pack(fill="x", padx=5, pady=5)
                
                btn_sil_k = tk.Button(kural_top_frame, text="🗑️ Seçili Olanları Gizle/Sil", command=lambda: secilenleri_sil(tree_k), bg="#D32F2F", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10)
                btn_sil_k.pack(side="right", padx=5)

                btn_kopyala_k = tk.Button(kural_top_frame, text="📋 Seçilileri Kopyala", command=lambda: secilileri_panoya_kopyala(tree_k, cols_k), bg="#008CBA", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10)
                btn_kopyala_k.pack(side="right", padx=5)

                cols_k = ("Seç", "Kural", "Durum", "Hata Sayısı", "Kural Açıklaması")
                tree_k = ttk.Treeview(kural_frame, columns=cols_k, show="headings", style="Treeview")
                tree_k.heading("Seç", text="☐")
                tree_k.heading("Kural", text="Kural Kodu")
                tree_k.heading("Durum", text="Test Durumu")
                tree_k.heading("Hata Sayısı", text="Tespit Edilen Hata")
                tree_k.heading("Kural Açıklaması", text="Kural Açıklaması")
                
                tree_k.column("Seç", width=40, anchor="center")
                tree_k.column("Kural", width=100, anchor="center")
                tree_k.column("Durum", width=130, anchor="center")
                tree_k.column("Hata Sayısı", width=110, anchor="center")
                tree_k.column("Kural Açıklaması", width=600, anchor="w")
                
                yscroll_k = ttk.Scrollbar(kural_frame, orient="vertical", command=tree_k.yview)
                yscroll_k.pack(side="right", fill="y")
                xscroll_k = ttk.Scrollbar(kural_frame, orient="horizontal", command=tree_k.xview)
                xscroll_k.pack(side="bottom", fill="x")
                tree_k.configure(yscrollcommand=yscroll_k.set, xscrollcommand=xscroll_k.set)
                tree_k.pack(side="left", fill="both", expand=True)
                
                tree_k.bind("<Button-1>", lambda e: tree_toggle_checkbox(e, tree_k))
                tree_k.bind("<Double-1>", lambda e: satir_detay_goster(e, tree_k, "Kural Test Detayı"))
                tree_k.bind("<Button-3>", lambda e: show_context_menu(e, tree_k))
                for col in cols_k:
                    if col != "Seç":
                        tree_k.heading(col, command=lambda c=col: treeview_sort_column(tree_k, c, False))
                
                # Tüm kuralların dökümünü listele
                from collections import Counter
                tum_kodlar = []
                if not hatali_kayitlar.empty:
                    for k in hatali_kayitlar["HATA KODU"].dropna():
                        tum_kodlar.extend([x.strip() for x in str(k).split(",") if x.strip()])
                kod_sayilari = Counter(tum_kodlar)
                
                tum_kural_listesi = []
                
                # 1. Sözlükte tanımlı olan tüm güncel kuralları ekle
                for k_kod, k_aciklama in kurallar.HATA_SOZLUGU.items():
                    adet = kod_sayilari.get(k_kod, 0)
                    tum_kural_listesi.append((k_kod, adet, k_aciklama))
                    
                # 2. Sözlükte olmayan ancak analizde tespit edilen sistem içi çapraz kontrolleri ekle
                mevcut_kodlar = [x[0] for x in tum_kural_listesi]
                for k_kod, adet in kod_sayilari.items():
                    if k_kod not in mevcut_kodlar:
                        k_aciklama = kurallar.HATA_SOZLUGU.get(k_kod, "Sistem İçi Dinamik Çapraz Kontrol")
                        if k_kod == "Veri Yok":
                            k_aciklama = "İlgili ana/ara sinoptik saatinde rasat verisi bulunamadı (Tüm zorunlu parametreler eksik)."
                        elif k_kod == "Ara Rasat":
                            k_aciklama = "Sadece METAR bulunur, SİNOPTİK beklenmez."
                        tum_kural_listesi.append((k_kod, adet, k_aciklama))
                        
                # Sıralama: h1, h2, h3... ve ardından diğerleri
                def sort_key(x):
                    match = re.search(r'\d+', x[0])
                    if x[0].startswith('h') and match: return (0, int(match.group()))
                    elif x[0].startswith('VAL'): return (1, x[0])
                    else: return (2, x[0])
                
                tum_kural_listesi.sort(key=sort_key)
                
                for k_kod, adet, k_aciklama in tum_kural_listesi:
                    durum = "BAŞARISIZ ❌" if adet > 0 else "BAŞARILI (Geçti) ✅"
                    hata_metni = f"{adet} Defa" if adet > 0 else "0"
                    tree_k.insert("", tk.END, values=("☐", k_kod, durum, hata_metni, k_aciklama))
            
            safe_after(0, arayuzde_goster)
            # ------------------------------------------------

            if iptal_istendi: raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
            # 3. Rapor Kaydetme
            islenen_dosyalar = {
                "sinoptik": os.path.basename(sin_yolu),
                "metar": os.path.basename(metar_yolu)
            }
            cikti_yolu = dm3.raporu_excel_olarak_kaydet(birlesik, yil, ay, okuma_raporu, hedef_klasor, islenen_dosyalar)

            # --- YENİ: İŞLEMİ BİTEN DOSYALARI ARŞİVLE ---
            final_message = f"İşlem Tamamlandı!\nSonuçlar ekrana yansıtıldı.\n(Yedek Excel: {cikti_yolu})"
            try:
                arsiv_klasoru = os.path.join(hedef_klasor, "Arsiv")
                if not os.path.exists(arsiv_klasoru):
                    os.makedirs(arsiv_klasoru)

                aylik_arsiv_klasoru = os.path.join(arsiv_klasoru, f"{yil}_{ay:02d}")
                if not os.path.exists(aylik_arsiv_klasoru):
                    os.makedirs(aylik_arsiv_klasoru)

                print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
                print(f"{Colors.OKBLUE}Oluşturulan rapor '{os.path.basename(aylik_arsiv_klasoru)}' klasörüne arşivleniyor...{Colors.ENDC}")
                for f_path in [cikti_yolu]:
                    if os.path.exists(f_path):
                        base_name = os.path.basename(f_path)
                        dest_path = os.path.join(aylik_arsiv_klasoru, base_name)
                        
                        if os.path.exists(dest_path):
                            name, ext = os.path.splitext(base_name)
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            dest_path = os.path.join(aylik_arsiv_klasoru, f"{name}_{timestamp}{ext}")
                            
                        shutil.move(f_path, dest_path)
                        print(f" - {Colors.OKGREEN}{os.path.basename(dest_path)} taşındı.{Colors.ENDC}")
                final_message = f"İşlem Tamamlandı!\nSonuçlar ekrana yansıtıldı.\n\nRapor dosyası '{os.path.basename(aylik_arsiv_klasoru)}' klasörüne arşivlendi."
            except Exception as e:
                logging.error(f"Arşivleme hatası: {e}", exc_info=True)
                logging_handler.flush()  # Arşivleme hatasını disk'e yaz
                print(f"{Colors.FAIL}ARŞİVLEME HATASI: {e}{Colors.ENDC}")
                traceback.print_exc()
                final_message = f"İşlem Tamamlandı!\n(Yedek Excel: {cikti_yolu})\n\nUYARI: Dosyalar arşivlenemedi!"

            safe_showinfo("Başarılı", final_message)
        except Exception as e:
            if isinstance(e, InterruptedError):
                logging.info("İşlem kullanıcı tarafından iptal edildi.")
                safe_showinfo("İptal", "İşlem iptal edildi.")
                print(f"\n{Colors.WARNING}İşlem kullanıcı tarafından iptal edildi!{Colors.ENDC}")
            else:
                logging.error("İşlem sırasında hata oluştu", exc_info=True)
                logging_handler.flush()
                print("\n--- DETAYLI HATA RAPORU ---")
                traceback.print_exc()
                safe_showerror("Hata", f"Bir hata oluştu:\n{e}")
        finally:
            # --- UI Geri Bildirimini Sonlandır ---
            if not console_mode:
                try:
                    def finalize_ui():
                        if btn_run: btn_run.config(state=tk.NORMAL, text=get_button_text())
                        if btn_cancel: btn_cancel.config(state=tk.DISABLED)
                        if lbl_status: lbl_status.config(text="Hazır")
                        if root: root.config(cursor="")
                        if pb_loading:
                            pb_loading.stop()
                            pb_loading.pack_forget()
                    safe_after(0, finalize_ui)
                except Exception:
                    pass

    if run_async and not console_mode:
        threading.Thread(target=islem_yurut, daemon=True).start()
    else:
        islem_yurut()

if not console_mode:
    root = tk.Tk()
    root.title("Meteoroloji Denetim")
    root.geometry("500x360")
    root.geometry("500x420")
    root.geometry("500x460")
    root.configure(bg="#F8F9FA")
    
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
        
    style.configure("TNotebook", background="#F8F9FA", borderwidth=0)
    style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"), padding=[15, 8], background="#E9ECEF", foreground="#495057", borderwidth=0)
    style.map("TNotebook.Tab", background=[('selected', '#FFFFFF')], foreground=[('selected', '#0066CC')])
    
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#343A40", foreground="white", borderwidth=0, padding=8)
    style.configure("Treeview", font=("Segoe UI", 10), rowheight=30, background="#FFFFFF", fieldbackground="#FFFFFF", borderwidth=0)
    style.map("Treeview", background=[('selected', '#0066CC')], foreground=[('selected', 'white')])

    main_frame = tk.Frame(root, padx=35, pady=30, bg="#F8F9FA")
    main_frame.pack(expand=True, fill="both")
    
    lbl_title = tk.Label(main_frame, text="METEOROLOJİK DENETİM", font=("Segoe UI", 16, "bold"), bg="#F8F9FA", fg="#212529")
    lbl_title.pack(pady=(0, 20))

    btn_run = tk.Button(main_frame, text=get_button_text(), command=aylik_rapor_olustur, font=("Segoe UI", 12, "bold"), bg="#0066CC", fg="white", activebackground="#0052A3", activeforeground="white", height=2, cursor="hand2", relief="flat", borderwidth=0)
    btn_run.pack(expand=True, fill="both", pady=(0, 10))
    
    def iptal_et():
        global iptal_istendi
        iptal_istendi = True
        if lbl_status: lbl_status.config(text="İşlem durduruluyor, lütfen bekleyin...")
        if btn_cancel: btn_cancel.config(state=tk.DISABLED)

    btn_cancel = tk.Button(main_frame, text="İŞLEMİ DURDUR / İPTAL ET", command=iptal_et, state=tk.DISABLED, font=("Segoe UI", 10, "bold"), bg="#D32F2F", fg="white", activebackground="#B71C1C", activeforeground="white", cursor="hand2", relief="flat", borderwidth=0, pady=8)
    btn_cancel.pack(fill="x", pady=(0, 8))

    def kurallari_goster():
        kural_pop = tk.Toplevel(root)
        kural_pop.title("Meteorolojik Denetim Kuralları")
        kural_pop.geometry("950x650")
        kural_pop.configure(bg="#F8F9FA")
        
        lbl = tk.Label(kural_pop, text="Sistemde Aktif Olan Kurallar", font=("Segoe UI", 14, "bold"), bg="#F8F9FA", fg="#212529")
        lbl.pack(pady=(15, 10))
        
        search_frame = tk.Frame(kural_pop, bg="#F8F9FA")
        search_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        tk.Label(search_frame, text="🔍 Kural Ara:", font=("Segoe UI", 11, "bold"), bg="#F8F9FA", fg="#495057").pack(side="left", padx=(0, 10))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, font=("Segoe UI", 11), width=40)
        search_entry.pack(side="left")
        
        columns = ("Kural Kodu", "Açıklama")
        tree = ttk.Treeview(kural_pop, columns=columns, show="headings", style="Treeview")
        tree.heading("Kural Kodu", text="Kural Kodu")
        tree.heading("Açıklama", text="Kural Açıklaması")
        
        tree.column("Kural Kodu", width=150, anchor="center")
        tree.column("Açıklama", width=750, anchor="w")
        
        yscroll = ttk.Scrollbar(kural_pop, orient="vertical", command=tree.yview)
        yscroll.pack(side="right", fill="y")
        tree.configure(yscrollcommand=yscroll.set)
        tree.pack(side="left", fill="both", expand=True, padx=20, pady=(0, 20))
        
        def sort_key(k):
            m = re.search(r'\d+', k)
            if k.startswith('h') and m: return (0, int(m.group()))
            elif k.startswith('VAL'): return (1, k)
            else: return (2, k)
            
        def filter_kurallar(*args):
            q = search_var.get().lower()
            tree.delete(*tree.get_children())
            for kod in sorted(kurallar.HATA_SOZLUGU.keys(), key=sort_key):
                acik = kurallar.HATA_SOZLUGU[kod]
                if q in kod.lower() or q in acik.lower():
                    tree.insert("", tk.END, values=(kod, acik))
                    
        search_var.trace_add("write", filter_kurallar)
        filter_kurallar() # İlk yükleme için çağır
            
    btn_kurallar = tk.Button(main_frame, text="KURALLARI GÖSTER", command=kurallari_goster, font=("Segoe UI", 10, "bold"), bg="#107C41", fg="white", activebackground="#0C5D31", activeforeground="white", cursor="hand2", relief="flat", borderwidth=0, pady=8)
    btn_kurallar.pack(fill="x", pady=(0, 8))

    def dosyalari_indir_ac():
        import datetime
        simdi = datetime.datetime.now()
        v_ay = simdi.month - 1 if simdi.month > 1 else 12
        v_yil = simdi.year if simdi.month > 1 else simdi.year - 1
        
        indirme_yili = simpledialog.askinteger("İndirme Yılı", "Hangi yılın verisini indireceksiniz?", initialvalue=v_yil, minvalue=2000, maxvalue=2030, parent=root)
        if not indirme_yili: return
        indirme_ayi = simpledialog.askinteger("İndirme Ayı", "Hangi ayın verisini indireceksiniz?", initialvalue=v_ay, minvalue=1, maxvalue=12, parent=root)
        if not indirme_ayi: return
        
        dosya_oneki = f"{indirme_ayi:02d}{indirme_yili}-"

        btn_indir.config(state="disabled", text="📥 TARAYICI AÇILIYOR...")
        pb_loading.pack(side="right", padx=5, pady=2)
        pb_loading.start(10)
        root.update()
        
        baslangic_zamani = time.time()

        try:
            ist_kodu_cache = ent_ist.get().strip()
        except Exception:
            ist_kodu_cache = "17244"

        def arkaplanda_tarayici_ac():
            try:
                hedef_klasor = r"C:\Users\nebio\Desktop\check"
                if not os.path.exists(hedef_klasor):
                    os.makedirs(hedef_klasor)
                    
                os.startfile(hedef_klasor)
                
                url = "http://kardelen.mgm.gov.tr/BultenGenel/Default.aspx"
                
                # SİSTEMİN VARSAYILAN TARAYICISINI ANINDA AÇ (SELENIUM İPTAL EDİLDİ)
                import webbrowser
                webbrowser.open(url)
                
                # Kullanıcı kolayca yapıştırabilsin diye istasyon kodunu panoya kopyala
                if ist_kodu_cache:
                    try:
                        root.clipboard_clear()
                        root.clipboard_append(ist_kodu_cache)
                        root.update()
                    except Exception: pass
                
                # Tarayıcı kendi varsayılan klasörüne (genelde Downloads) indireceği için o klasörü izliyoruz
                indirilenler_klasoru = os.path.join(os.path.expanduser("~"), "Downloads")
                
                def oto_tasima_ve_bekle():
                    zaman_asimi = 600
                    baslangic_z = time.time()
                    
                    safe_after(0, lambda: lbl_status.config(text="Tarayıcı açıldı. (Otomatik taşıma devrede)..."))
                    safe_after(0, lambda: btn_indir.config(text="İNDİRME BEKLENİYOR...", state="disabled"))
                    
                    while time.time() - baslangic_z < zaman_asimi:
                        if iptal_istendi:
                            break
                            
                        # 1. Kullanıcının İndirilenler klasörüne düşen yeni Kardelen dosyalarını otomatik 'check' klasörüne taşı
                        try:
                            if os.path.exists(indirilenler_klasoru):
                                for f in os.listdir(indirilenler_klasoru):
                                    if f.endswith('.crdownload') or f.endswith('.tmp') or f.endswith('.part'):
                                        continue
                                    tam_yol = os.path.join(indirilenler_klasoru, f)
                                    if os.path.isfile(tam_yol) and f.lower().endswith(('.xls', '.xlsx', '.csv', '.html')):
                                        # Sadece butona basıldıktan sonra indirilen dosyaları taşı
                                        try:
                                            if max(os.path.getmtime(tam_yol), os.path.getctime(tam_yol)) >= baslangic_z:
                                                yeni_dosya_adi = f
                                                f_lower = f.lower()
                                                if "sintum" in f_lower:
                                                    yeni_dosya_adi = f"{dosya_oneki}SinTum{os.path.splitext(f)[1]}"
                                                elif "metartum" in f_lower:
                                                    yeni_dosya_adi = f"{dosya_oneki}MetarTum{os.path.splitext(f)[1]}"
                                                hedef_yol = os.path.join(hedef_klasor, yeni_dosya_adi)
                                                import shutil
                                                shutil.move(tam_yol, hedef_yol)
                                        except Exception: pass
                        except Exception: pass
                        
                        # 2. Check klasöründeki dosyaları kontrol et (SİNOPTİK ve METAR ikisi de geldi mi?)
                        try:
                            dosyalar = os.listdir(hedef_klasor)
                            devam_eden_var = any(f.endswith('.crdownload') or f.endswith('.tmp') for f in dosyalar)
                            
                            if not devam_eden_var:
                                sin_yeni = met_yeni = False
                                for f in dosyalar:
                                    tam_yol = os.path.join(hedef_klasor, f)
                                    if not os.path.isfile(tam_yol): continue
                                    
                                    try:
                                        yeni_mi = max(os.path.getmtime(tam_yol), os.path.getctime(tam_yol)) >= baslangic_z
                                    except Exception:
                                        yeni_mi = False
                                        
                                    if yeni_mi and f.lower().endswith(('.xls', '.xlsx', '.csv', '.html')):
                                        f_upper = f.upper()
                                        if "SIN" in f_upper or "SİN" in f_upper: sin_yeni = True
                                        elif "METAR" in f_upper: met_yeni = True
                                        
                                if sin_yeni and met_yeni:
                                    time.sleep(1.5)
                                    def sor_ve_baslat():
                                        btn_indir.config(state="normal", text="📥 DOSYALARI İNDİR")
                                        lbl_status.config(text="Hazır")
                                        pb_loading.stop()
                                        pb_loading.pack_forget()
                                        cevap = messagebox.askyesno("İndirme Tamamlandı", "SİNOPTİK ve METAR dosyaları başarıyla indirildi!\n\nRaporlama işlemi hemen başlatılsın mı?", parent=root)
                                        if cevap:
                                            sadece_en_yeni_dosyalari_tut()
                                            aylik_rapor_olustur(run_async=True)
                                    safe_after(0, sor_ve_baslat)
                                    return
                        except Exception: pass
                        time.sleep(2)
                        
                    def reset_ui():
                        btn_indir.config(state="normal", text="📥 DOSYALARI İNDİR")
                        lbl_status.config(text="Hazır")
                        pb_loading.stop()
                        pb_loading.pack_forget()
                        if not iptal_istendi:
                            messagebox.showwarning("Zaman Aşımı / Bilgi", "İndirme otomatik algılanamadı veya zaman aşımına uğradı.\nDosyalar indiğinden eminseniz rapor oluşturmayı manuel başlatabilirsiniz.", parent=root)
                    safe_after(0, reset_ui)
                
                threading.Thread(target=oto_tasima_ve_bekle, daemon=True).start()
                    
            except Exception as e:
                def show_err():
                    messagebox.showerror("Hata", f"İşlem sırasında hata oluştu:\n{e}")
                    btn_indir.config(state="normal", text="📥 DOSYALARI İNDİR")
                    pb_loading.stop()
                    pb_loading.pack_forget()
                safe_after(0, show_err)

        # Selenium başlatma işlemini arka planda (ayrı thread) çalıştır
        threading.Thread(target=arkaplanda_tarayici_ac, daemon=True).start()

    btn_indir = tk.Button(main_frame, text="📥 DOSYALARI İNDİR", command=dosyalari_indir_ac, font=("Segoe UI", 10, "bold"), bg="#673AB7", fg="white", activebackground="#512DA8", activeforeground="white", cursor="hand2", relief="flat", borderwidth=0, pady=8)
    btn_indir.pack(fill="x", pady=(0, 8))

    def arsiv_sutun_guncelle():
        if sutun_duzeltici:
            sutun_duzeltici.arsivleri_toplu_duzelt()

    btn_arsiv_duzelt = tk.Button(main_frame, text="ARŞİV SÜTUNLARINI GÜNCELLE", command=arsiv_sutun_guncelle, font=("Segoe UI", 10, "bold"), bg="#FF9800", fg="black", activebackground="#F57C00", activeforeground="white", cursor="hand2", relief="flat", borderwidth=0, pady=8)
    btn_arsiv_duzelt.pack(fill="x", pady=(0, 8))

    def loglari_goster():
        log_pop = tk.Toplevel(root)
        log_pop.title("Sistem Logları")
        log_pop.geometry("850x600")
        log_pop.configure(bg="#F8F9FA")
        
        top_frame = tk.Frame(log_pop, bg="#F8F9FA")
        top_frame.pack(fill="x", padx=10, pady=10)
        
        txt_log = tk.Text(log_pop, font=("Consolas", 10), bg="#1E1E1E", fg="#00FF00", wrap="none")
        
        v_scroll = tk.Scrollbar(log_pop, orient="vertical", command=txt_log.yview)
        v_scroll.pack(side="right", fill="y")
        h_scroll = tk.Scrollbar(log_pop, orient="horizontal", command=txt_log.xview)
        h_scroll.pack(side="bottom", fill="x")
        
        txt_log.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        txt_log.pack(expand=True, fill="both", padx=10, pady=(0, 10))
        
        def load_logs(filter_text=None):
            txt_log.config(state="normal")
            txt_log.delete("1.0", tk.END)
            try:
                with open(log_dosyasi, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if filter_text:
                        lines = [l for l in lines if filter_text in l]
                    txt_log.insert(tk.END, "".join(lines))
            except Exception as e:
                txt_log.insert(tk.END, f"Log dosyası okunamadı: {e}")
            txt_log.see(tk.END)
            txt_log.config(state="disabled")

        tk.Button(top_frame, text="Tüm Logları Göster", command=lambda: load_logs(), bg="#0066CC", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=5).pack(side="left", padx=5)
        tk.Button(top_frame, text="🔍 Sütun Eşleşmeleri", command=lambda: load_logs("Eşleşen Sütunlar"), bg="#107C41", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=5).pack(side="left", padx=5)
        tk.Button(top_frame, text="Hataları Filtrele", command=lambda: load_logs("ERROR"), bg="#D32F2F", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=5).pack(side="left", padx=5)
        
        load_logs()

    btn_loglar = tk.Button(main_frame, text="SİSTEM LOGLARINI GÖSTER", command=loglari_goster, font=("Segoe UI", 10, "bold"), bg="#607D8B", fg="white", activebackground="#455A64", activeforeground="white", cursor="hand2", relief="flat", borderwidth=0, pady=8)
    btn_loglar.pack(fill="x", pady=(0, 8))

    def log_dosyasini_ac():
        try:
            if os.path.exists(log_dosyasi):
                os.startfile(log_dosyasi) # Windows'un varsayılan uygulamasıyla (Örn: Not Defteri) açar
            else:
                messagebox.showwarning("Bulunamadı", "Log dosyası henüz oluşturulmamış.", parent=root)
        except Exception as e:
            messagebox.showerror("Hata", f"Log dosyası açılamadı:\n{e}", parent=root)
            
    btn_log_dosyasi = tk.Button(main_frame, text="📝 LOG DOSYASINI AÇ (NOT DEFTERİ)", command=log_dosyasini_ac, font=("Segoe UI", 10, "bold"), bg="#546E7A", fg="white", activebackground="#37474F", activeforeground="white", cursor="hand2", relief="flat", borderwidth=0, pady=8)
    btn_log_dosyasi.pack(fill="x", pady=(0, 8))

    def manuel_temizlik_yap():
        clear_pycache_on_startup()
        cleanup_old_temp_files()
        
        temizlenen_arsiv = 0
        cevap = messagebox.askyesno("Arşiv Temizliği", "Sistemin önbellek ve logları temizlenecek.\n\nAyrıca 'check\\Arsiv' klasöründeki TÜM geçmiş Excel raporları da kalıcı olarak silinsin mi?", parent=root)
        if cevap:
            arsiv_dir = r"C:\Users\nebio\Desktop\check\Arsiv"
            if os.path.exists(arsiv_dir):
                try:
                    for root_d, dirs, files in os.walk(arsiv_dir, topdown=False):
                        for f in files:
                            try:
                                os.remove(os.path.join(root_d, f))
                                temizlenen_arsiv += 1
                            except: pass
                        if root_d != arsiv_dir:
                            try: os.rmdir(root_d)
                            except: pass
                except Exception as e:
                    logging.error(f"Arşiv temizleme hatası: {e}")
        
        mesaj = "Önbellek (Cache), eski loglar ve gereksiz geçici dosyalar başarıyla temizlendi."
        if cevap:
            mesaj += f"\n\nSilinen geçmiş arşiv dosyası: {temizlenen_arsiv} adet."
        messagebox.showinfo("Temizlik Tamamlandı", mesaj, parent=root)
        
    btn_temizle = tk.Button(main_frame, text="🧹 SİSTEMİ TEMİZLE (ARŞİV/LOG)", command=manuel_temizlik_yap, font=("Segoe UI", 10, "bold"), bg="#795548", fg="white", activebackground="#5D4037", activeforeground="white", cursor="hand2", relief="flat", borderwidth=0, pady=8)
    btn_temizle.pack(fill="x", pady=(0, 8))

    def dosya_icerigi_incele():
        dosya_yolu = filedialog.askopenfilename(
            title="İncelenecek Bozuk/Okunamayan Dosyayı Seçin",
            filetypes=[("Tüm Dosyalar", "*.*"), ("Excel/Metin", "*.xls *.xlsx *.csv *.html *.txt")]
        )
        if not dosya_yolu: return
        
        incele_pop = tk.Toplevel(root)
        incele_pop.title(f"Ham Dosya İnceleme - {os.path.basename(dosya_yolu)}")
        incele_pop.geometry("850x600")
        incele_pop.configure(bg="#F8F9FA")
        
        top_frame = tk.Frame(incele_pop, bg="#F8F9FA")
        top_frame.pack(fill="x", padx=10, pady=10)
        tk.Label(top_frame, text=f"Dosya Ham (Raw) İçeriği:\n{dosya_yolu}", font=("Segoe UI", 10, "bold"), bg="#F8F9FA", fg="#D32F2F", justify="left").pack(side="left")
        
        txt_icerik = tk.Text(incele_pop, font=("Consolas", 10), bg="#1E1E1E", fg="#00FF00", wrap="none")
        v_scroll = tk.Scrollbar(incele_pop, orient="vertical", command=txt_icerik.yview)
        v_scroll.pack(side="right", fill="y")
        h_scroll = tk.Scrollbar(incele_pop, orient="horizontal", command=txt_icerik.xview)
        h_scroll.pack(side="bottom", fill="x")
        
        txt_icerik.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        txt_icerik.pack(expand=True, fill="both", padx=10, pady=(0, 10))
        
        def load_content():
            try:
                dosya_boyutu = os.path.getsize(dosya_yolu)
                if dosya_boyutu == 0:
                    txt_icerik.insert(tk.END, "⚠️ BU DOSYA TAMAMEN BOŞ (0 BYTE)!\n\nKardelen sistemi bu dosyayı üretirken hata vermiş veya dosya eksik inmiş. Yeniden indirmeyi deneyin.")
                else:
                    txt_icerik.insert(tk.END, f"--- Dosya Boyutu: {dosya_boyutu / 1024:.2f} KB ---\n\n")
                    with open(dosya_yolu, 'r', encoding='utf-8', errors='ignore') as f:
                        satirlar = f.readlines()
                        if len(satirlar) > 1000:
                            icerik = "".join(satirlar[:1000]) + "\n\n... (DOSYA ÇOK UZUN OLDUĞU İÇİN SADECE İLK 1000 SATIR GÖSTERİLİYOR) ..."
                        else:
                            icerik = "".join(satirlar)
                        
                        if icerik.strip(): txt_icerik.insert(tk.END, icerik)
                        else: txt_icerik.insert(tk.END, "Dosyada okunabilir metin verisi bulunamadı.")
            except Exception as e:
                txt_icerik.insert(tk.END, f"Dosya okunurken hata oluştu:\n{e}")
            txt_icerik.config(state="disabled")
            
        load_content()

    btn_bozuk_incele = tk.Button(main_frame, text="OKUNMAYAN / BOZUK DOSYAYI İNCELE", command=dosya_icerigi_incele, font=("Segoe UI", 10, "bold"), bg="#8D6E63", fg="white", activebackground="#6D4C41", activeforeground="white", cursor="hand2", relief="flat", borderwidth=0, pady=8)
    btn_bozuk_incele.pack(fill="x", pady=(0, 8))

    # --- İSTASYON KODU GİRİŞİ ---
    frame_ist = tk.Frame(main_frame, bg="#F8F9FA")
    frame_ist.pack(fill="x", pady=(0, 8))
    tk.Label(frame_ist, text="İstasyon Kodu:", font=("Segoe UI", 10, "bold"), bg="#F8F9FA", fg="#495057").pack(side="left")
    ent_ist = ttk.Entry(frame_ist, font=("Segoe UI", 11), width=15)
    ent_ist.insert(0, "17244")
    ent_ist.pack(side="left", padx=(10, 0))

    # --- YENİ: DURUM ÇUBUĞU ---
    status_frame = tk.Frame(root, bg="#E9ECEF", relief="sunken", bd=1)
    status_frame.pack(side="bottom", fill="x")

    lbl_status = tk.Label(status_frame, text="Hazır", anchor="w", bg="#E9ECEF", font=("Segoe UI", 9))
    lbl_status.pack(side="left", padx=5, pady=2)

    pb_loading = ttk.Progressbar(status_frame, orient="horizontal", length=150, mode="indeterminate")

    root.mainloop()
else:
    print("Terminal modunda çalıştırılıyor. GUI devre dışı bırakıldı.")
    aylik_rapor_olustur(run_async=False)

# --- YENİ: LOG DOSYASINI OKUDAN ÖNCE HANDLER'LARI KAPAT VE FLUSH ET ---
for handler in logging.root.handlers[:]:
    handler.close()
    logging.root.removeHandler(handler)

# Eğer log dosyası varsa oku ve yazdır
if os.path.exists(log_dosyasi):
    try:
        with open(log_dosyasi, 'r', encoding='utf-8') as f:
            print(f.read())
    except Exception as e:
        print(f"{Colors.WARNING}Log dosyası okunamadı: {e}{Colors.ENDC}")
else:
    print(f"{Colors.WARNING}Log dosyası bulunamadı: {log_dosyasi}{Colors.ENDC}")

try:
    input(f"\n{Colors.OKGREEN}Program tamamlandı. Ekranı kapatmak için ENTER tuşuna basın...{Colors.ENDC}")
except KeyboardInterrupt:
    print("\nProgram kullanıcı tarafından sonlandırıldı.")
# Program başarıyla tamamlandı
sys.exit(0)
