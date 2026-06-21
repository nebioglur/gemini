# =============================================================================
# KARDELEN LOG GÖRÜNTÜLEYİCİ VE ANALİZ ARACI
# Bu dosya, Kardelen web sitesinden hava durumu verilerini çeker,
# TAF ve METAR raporlarını eşleştirir ve uyumluluk analizi yapar.
# =============================================================================
import sys
import subprocess
import importlib.util

def auto_install_dependencies():
    """Uygulama açılırken (eğer koddan çalıştırılıyorsa) eksik kütüphaneleri otomatik yükler."""
    if getattr(sys, 'frozen', False):
        return # EXE modunda pip install yapılamaz
        
    # Gerekli kütüphaneler listesi (Modül Adı : Pip Paket Adı)
    required_packages = {
        'webview': 'pywebview',
        'pandas': 'pandas',
        'requests': 'requests',
        'PIL': 'Pillow',
        'openpyxl': 'openpyxl',
        'yaml': 'pyyaml',
        'folium': 'folium',
        'matplotlib': 'matplotlib',
        'geopandas': 'geopandas',
        'tkintermapview': 'tkintermapview',
        'pyttsx3': 'pyttsx3',
        'pygame': 'pygame',
        'gtts': 'gTTS',
        'playsound': 'playsound',
        'edge_tts': 'edge-tts',
        'webdriver_manager': 'webdriver-manager'
    }

    missing_packages = []
    for module_name, pip_name in required_packages.items():
        if importlib.util.find_spec(module_name) is None:
            missing_packages.append(pip_name)
            
    if missing_packages:
        import tkinter as tk
        from tkinter import messagebox
        import threading

        print(f"Eksik kütüphaneler: {', '.join(missing_packages)}")
        
        splash = tk.Tk()
        splash.overrideredirect(True) # Çerçevesiz pencere
        splash.attributes('-topmost', True) # Her zaman üstte
        splash.configure(bg="#263238", highlightbackground="#00E676", highlightthickness=2)
        
        w, h = 450, 180
        sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
        splash.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        
        tk.Label(splash, text="📦 KARDELEN PRO", font=("Segoe UI", 14, "bold"), fg="#00E676", bg="#263238").pack(pady=(20, 10))
        tk.Label(splash, text="İlk kurulum yapılıyor, gerekli kütüphaneler indiriliyor...\nLütfen bekleyin.", font=("Segoe UI", 10), fg="white", bg="#263238").pack()
        
        pkg_text = ", ".join(missing_packages[:5]) + ("..." if len(missing_packages) > 5 else "")
        tk.Label(splash, text=pkg_text, font=("Consolas", 8), fg="#B0BEC5", bg="#263238").pack(pady=5)

        lbl_anim = tk.Label(splash, text="⏳", font=("Segoe UI", 16), fg="#FFD700", bg="#263238")
        lbl_anim.pack(pady=5)

        install_error = None

        def install_process():
            nonlocal install_error
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            except Exception as e:
                install_error = str(e)

        install_thread = threading.Thread(target=install_process, daemon=True)
        install_thread.start()

        def check_thread():
            if install_thread.is_alive():
                lbl_anim.config(text="⌛" if lbl_anim.cget("text") == "⏳" else "⏳")
                splash.after(400, check_thread)
            else:
                if install_error: messagebox.showerror("Kurulum Hatası", f"Kütüphaneler yüklenemedi:\n{install_error}\n\nLütfen terminalden manuel yükleyin:\npip install {' '.join(missing_packages)}")
                splash.destroy()

        splash.after(400, check_thread)
        splash.mainloop()

auto_install_dependencies()

from gui_app import gui_baslat
import traceback
import logging
import os
from datetime import datetime , timezone
import tkinter as tk
from tkinter import messagebox
import ctypes
import sys
import shutil
import time
import threading 


# Terminal Hatalarını ve Kayıp Çıktıları Önlemek İçin Gelişmiş Logger Stream
class LoggerStream:
    def __init__(self, level):
        self.level = level
        self.encoding = 'utf-8'

    class _Buffer:
        def __init__(self, parent):
            self.parent = parent
        def write(self, message):
            return self.parent.write(message)
        def flush(self):
            pass

    @property
    def buffer(self):
        return self._Buffer(self)

    def write(self, message):
        try:
            if isinstance(message, str) and message.strip():
                self.level(message.strip())
            elif isinstance(message, bytes) and message.strip():
                self.level(message.decode('utf-8', errors='ignore').strip())
        except Exception:
            pass
        return len(message) if message else 0

    def flush(self):
        pass

    def isatty(self):
        return False

# --- PROFESYONEL ALTYAPI AYARLARI ---

# 1. Yüksek DPI Desteği (Bulanıklığı Önler)
try:
    # Modern Windows 10/11 için Per-Monitor V2 DPI (Daha net yazılar)
    ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
except:
    try:
        # Eski sistemler için Fallback
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except: pass

# 2. Merkezi Loglama Sistemi
def setup_logging():
    base_log_dir = os.path.join(os.path.expanduser("~"), "KardelenLogs")
    # Her gün için ayrı klasör (YYYY-MM-DD)
    today_folder = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    log_dir  = os.path.join(base_log_dir, today_folder)
    
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "kardelen_gunluk_log.txt")
    
    handlers = [logging.FileHandler(log_file, encoding='utf-8')]
    
    # Penceresiz (windowed) exe veya geçersiz stdout durumunda çökmeyi önlemek için
    original_stdout = sys.stdout
    if original_stdout:
        try:
            if hasattr(original_stdout, 'isatty') and original_stdout.isatty():
                handlers.append(logging.StreamHandler(original_stdout))
            elif not getattr(sys, 'frozen', False):
                handlers.append(logging.StreamHandler(original_stdout))
        except Exception:
            pass

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
        handlers=handlers
    )

    # Tüm print() ve standart hata çıktılarını (crash) log'a yönlendir
    sys.stdout = LoggerStream(logging.info)
    sys.stderr = LoggerStream(logging.error)

    return log_file

# 3. Global Hata Yakalayıcı (Crash Handler)
def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.critical("BEKLENMEYEN HATA:\n" + error_msg)
    
    try:
        # Hata penceresini göster
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Kritik Uygulama Hatası", 
            f"Uygulama beklenmedik bir hata ile karşılaştı.\n\n"
            f"Hata Detayı: {exc_value}\n\n"
            f"Log Dosyası: {logging.getLogger().handlers[0].baseFilename}")
        root.destroy()
    except: pass
    sys.exit(1)

def global_thread_exception_handler(args):
    """Arka planda (Thread) sessizce oluşan hataları log dosyasına yazar."""
    logging.critical(f"ARKA PLAN İŞLEM HATASI ({args.thread.name if args.thread else 'Bilinmeyen'}):\n" + "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))

def clean_old_logs():
    """365 günden (1 yıl) eski günlük log klasörlerini güvenlice temizler."""
    base_log_dir = os.path.join(os.path.expanduser("~"), "KardelenLogs")
    if not os.path.exists(base_log_dir): return
    
    cutoff = time.time() - (365 * 86400) # 365 gün (1 yıl) öncesi
    
    for item in os.listdir(base_log_dir):
        item_path = os.path.join(base_log_dir, item)
        if os.path.isdir(item_path):
            try:
                # Sadece YYYY-MM-DD formatındaki günlük klasörleri hedef al
                datetime.strptime(item, "%Y-%m-%d")
                if os.path.getmtime(item_path) < cutoff:
                    shutil.rmtree(item_path)
                    logging.info(f"Eski log klasörü temizlendi: {item}")
            except ValueError:
                pass # Format uymuyorsa (Aylik_Kayitlar, Cop_Kutusu vb.) atla
            except Exception:
                pass

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == "__main__":
    import sys
    
    # Terminal hatalarını önlemek için Loglamayı ve terminal yönlendirmesini en başta başlat
    setup_logging()

    # EĞER EXE İÇİNDEN ÇAĞRILDIYSA (Alt Süreç - FlightRadar Başlatıcı)
    if len(sys.argv) >= 2 and sys.argv[1] == "--flightradar":
        import runpy
        import os
        try:
            current_file_path = os.path.abspath(__file__)
        except NameError:
            current_file_path = os.path.abspath(sys.argv[0])
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(current_file_path))
        script_path = os.path.join(base_dir, "flightradar.py")
        if getattr(sys, 'frozen', False) and not os.path.exists(script_path):
            # Eğer _MEIPASS içinde yoksa exe'nin yanındaki klasöre bak
            script_path = os.path.join(os.path.dirname(sys.executable), "flightradar.py")
            
        sys.argv = [script_path] + sys.argv[2:]
        runpy.run_path(script_path, run_name="__main__")
        sys.exit(0)

    # Eski Logları Temizle
    clean_old_logs()
    
    # Global Hata Yakalayıcıyı Tanımla
    sys.excepthook = global_exception_handler
    threading.excepthook = global_thread_exception_handler

    # Yönetici hakları kontrolü ve yükseltme
    if not is_admin():
        logging.info("Yönetici hakları isteniyor...")
        # Windows UAC geçişinde System32'ye düşmemek için çalışma dizinini sabitle
        current_dir = os.getcwd()
        ret = 0
        if getattr(sys, 'frozen', False):
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join([f'"{a}"' for a in sys.argv[1:]]), current_dir, 1)
        else:
            # Scriptin tam yolunu (abspath) alarak dosyanın kaybolmasını engelle
            safe_args = [os.path.abspath(sys.argv[0])] + sys.argv[1:]
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join([f'"{a}"' for a in safe_args]), current_dir, 1)
            
        if ret <= 32:
            logging.warning(f"Yönetici hakları alınamadı (Hata Kodu: {ret}).")
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showwarning("Yetki Reddedildi", "Uygulamanın çalışabilmesi için yönetici haklarına ihtiyacı var.\n\nLütfen açılan uyarı penceresinde 'Evet'i seçiniz.")
                root.destroy()
            except:
                pass
            sys.exit(1)
        sys.exit(0)

    try:
        logging.info("Uygulama başlatılıyor...")
        gui_baslat()
    except Exception as e:
        # Buraya düşen hatalar sys.excepthook tarafından yakalanır ama yine de güvenlik için:
        logging.error(f"Ana döngü hatası: {e}")
        raise   