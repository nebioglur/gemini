# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import time
import traceback
import logging
from PIL import Image, ImageTk
import gui_utils
import TAF_METAR_TREND
from rasat_alarm import RasatAlarmSistemi

# Diğer parçaları dahil et (Mixin yapısı)
from gui_app_2 import SettingsMixin
from gui_app_3 import AnalysisMixin
from gui_analysis_alarms import AnalysisAlarmMixin
from gui_app_logging import IncompatibilityLoggingMixin
from gui_app_logs_viewer import LogViewerMixin
from gui_app_map import MapViewerMixin
from gui_app_history import HistoryMixin

class KardelenApp(SettingsMixin, AnalysisMixin, HistoryMixin, AnalysisAlarmMixin, IncompatibilityLoggingMixin, LogViewerMixin, MapViewerMixin):
    def __init__(self):
        # Temel Bileşenler  
        self.robot = TAF_METAR_TREND.HavacilikRobotModulu()
        self.rasat_alarm = RasatAlarmSistemi()
        self.alarm_motoru = self.rasat_alarm
        self.tooltip_manager = gui_utils.ToolTipManager()
        
        # Arayüzü Kur
        self.setup_ui()

        # Uyumsuzluk Kayıt Sistemini Başlat
        self.setup_incompatibility_logger()

    def apply_dpi_scaling(self):
        """Ekran çözünürlüğü ve DPI değerine göre Tkinter font ölçeklemesini otomatik ayarlar."""
        try:
            # 1 inç'in piksel karşılığını alır (Standart ekranlarda 96, yüksek DPI'da 120, 144 vb. döner)
            dpi = self.root.winfo_fpixels('1i')
            
            # Tkinter varsayılan olarak 72 point = 1 inch kabul eder. Bunu gerçek DPI ile güncelliyoruz.
            # scale_factor = dpi / 72.0
            # self.root.tk.call('tk', 'scaling', scale_factor)
            # İPTAL: Arayüzün başka PC'lerde taşmasını ve bozulmasını engellemek için iptal edildi. Windows'un kendi ölçeklemesi yeterlidir.
            
            # Aşırı yüksek çözünürlüklerde (2K, 4K vb.) temel tablo yazı boyutunu otomatik büyüt
            ws = self.root.winfo_screenwidth()
            if ws >= 2560 and hasattr(self, 'settings_vars'):
                if self.settings_vars['var_yazi_boyutu'].get() < 12:
                    self.settings_vars['var_yazi_boyutu'].set(12)
        except Exception as e:
            logging.error(f"DPI ölçekleme hatası: {e}")

    def setup_ui(self):
        # --- ANA PENCERE ---
        self.root = tk.Tk()
        self.root.withdraw() # Arayüz hazırlanana kadar pencereyi gizle
        
        # Değişkenleri Başlat (Mixin'lerden) - Root oluşturulduktan sonra
        self.init_settings_vars()
        self.init_analysis_vars()
        
        self.root.title("PRO KARDELEN")
        
        # DPI Tabanlı Global Font Ölçeklendirmesini Uygula
        self.apply_dpi_scaling()

        try:
            icon_path = gui_utils.get_resource_path("logo.ico")
            if os.path.exists(icon_path): self.root.iconbitmap(icon_path)
        except: pass

        # Dinamik Ekran Boyutlandırması (Çözünürlüğe tam uyum)
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        
        # Dinamik ve güvenli boyutlandırma (Ekranın %70'ini kaplar, küçük ekranlarda %85)
        width = int(ws * 0.70)
        height = int(hs * 0.70)
        
        if ws <= 1366:
            width = int(ws * 0.85)
            height = int(hs * 0.80)
            
        self.root.geometry(f"{width}x{height}")
        
        # Düşük/Yüksek çözünürlüklü ekranlarda taşmaları önlemek için minimum boyut daha da küçültüldü
        self.root.minsize(800, 550)
        # self.root.state('zoomed')

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Notebook (Sekmeler)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Sekme Değiştirme Olayını Dinle
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.tab_analiz = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_analiz, text=" 📋 Veri Analiz ")

        self.tab_logs = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_logs, text=" ⚠️ Uyumsuzluk Kayıtları ")

        self.tab_ayarlar = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ayarlar, text=" ⚙️ Genel Ayarlar ")

        self.tab_system_logs = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_system_logs, text=" 📋 Sistem Logları ")

        self.tab_web = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_web, text=" 🌐 Web Servisleri ")

        # Sekme İçeriklerini Yükle
        self.setup_analysis_ui(self.tab_analiz)
        self.setup_log_viewer_ui(self.tab_logs)
        self.setup_settings_ui(self.tab_ayarlar)
        self.setup_system_logs_ui(self.tab_system_logs)
        self.setup_web_ui(self.tab_web)
        
        # Tüm yerleşim bitti, native (PyInstaller) splash ekranını kapat
        try:
            import pyi_splash
            pyi_splash.close()
        except: pass
        
        self.root.deiconify() # Pencereyi göster
        self.root.iconify()   # Ve hemen arka plana (simge durumuna) küçült
        # Saat Döngüsünü Başlat
        self.update_clock()

    def on_tab_changed(self, event):
        """Kullanıcı sekme değiştirdiğinde tetiklenir."""
        try:
            selected_tab_text = self.notebook.tab(self.notebook.select(), "text")
            # Eğer "Uyumsuzluk Kayıtları" sekmesi seçildiyse, içeriği otomatik yenile
            if "Uyumsuzluk Kayıtları" in selected_tab_text:
                self.load_incompatibility_log()
        except tk.TclError:
            pass # Pencere kapanırken bu hata oluşabilir, normaldir.

    def ornek_veri_isleme_ve_loglama(self, istasyon_verisi):
        """
        ÖRNEK FONKSİYON: Bir istasyonun verilerini işler ve uyumsuzluk kontrolü yapar.
        Bu fonksiyon, kendi veri işleme döngünüze (örneğin, periyodik veri yenileme)
        nasıl entegrasyon yapabileceğinizi göstermek için bir örnektir.
        """
        # Bu kısım, sizin TAF ve METAR karşılaştırma mantığınızın olduğu yerdir.
        # self.robot.analyze() veya self.alarm_motoru.check() gibi bir metodun sonucu olabilir.
        # Örnek bir senaryo:
        # 'analiz_sonucu' bir sözlük ve 'uyumlu' ve 'sebep' anahtarlarını içeriyor varsayalım.
        analiz_sonucu = self.robot.karsilastir(istasyon_verisi['taf'], istasyon_verisi['metar']) # Bu metot varsayımsaldır
        
        if not analiz_sonucu.get('uyumlu', True):
            # Uyumsuzluk tespit edildi! Loglama fonksiyonunu çağır.
            self.log_incompatibility(
                station_name=istasyon_verisi['icao'],
                reason=analiz_sonucu.get('sebep', 'Bilinmeyen Neden'),
                metar_data=istasyon_verisi['metar'],
                taf_data=istasyon_verisi['taf']
            )

    def setup_web_ui(self, parent):
        """WEB servisleri (Web Sunucu ve Web Harita) sekmesinin arayüzü"""
        frame = tk.Frame(parent, bg="#ECEFF1")
        frame.pack(fill="both", expand=True)
        
        lbl = tk.Label(frame, text="🌐 WEB SERVİSLERİ", font=("Segoe UI", 16, "bold"), bg="#ECEFF1", fg="#37474F")
        lbl.pack(pady=(50, 10))
        
        desc = tk.Label(frame, text="Aşağıdaki butonları kullanarak Kardelen Pro'nun yerel ağ ve web tabanlı modüllerini başlatabilirsiniz.", font=("Segoe UI", 11), bg="#ECEFF1")
        desc.pack(pady=10)
        
        btn_harita = tk.Button(frame, text="🌍 ETKİLEŞİMLİ WEB HARİTA\n(Animasyonlu Harita Analizi ve Detaylı Görünüm)", command=self.open_webview_map, bg="#00ACC1", fg="white", font=("Segoe UI", 11, "bold"), padx=30, pady=15, cursor="hand2")
        btn_harita.pack(pady=15)
        self.btn_web_map = btn_harita

        btn_sunucu = tk.Button(frame, text="📡 AĞ (LAN) WEB SUNUCUSU\n(Telefonunuzdan veya Ağdaki Diğer Bilgisayarlardan Web Paneline Erişim)", command=self.start_web_server, bg="#004D40", fg="white", font=("Segoe UI", 11, "bold"), padx=30, pady=15, cursor="hand2")
        btn_sunucu.pack(pady=15)
        self.btn_web_server = btn_sunucu

    def start_web_server(self):
        import subprocess
        import sys
        import os
        from tkinter import messagebox
        import socket
        
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
            
        if hasattr(self, 'btn_web_server'):
            self.btn_web_server.config(state="disabled", text="📡 SUNUCU BAŞLATILIYOR...\nLütfen bekleyin")
            self.root.update()
            
        try:
            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable, "--flask"])
            else:
                script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flask_app.py")
                subprocess.Popen([sys.executable, script_path])
            messagebox.showinfo("Web Sunucu Başlatıldı", f"Web sunucusu arka planda başlatıldı.\n\nAğınızdaki diğer bilgisayarlar, tarayıcılarından şu adrese girerek sisteme ulaşabilirler:\n\nhttp://{ip}:5000\n\n(Not: Ağınızda Windows Güvenlik Duvarı uyarısı çıkarsa 'İzin Ver' seçeneğini işaretlemelisiniz.)")
        except Exception as e:
            messagebox.showerror("Hata", f"Web sunucu başlatılamadı: {e}")
        finally:
            if hasattr(self, 'btn_web_server'):
                self.root.after(1500, lambda: self.btn_web_server.config(state="normal", text="📡 AĞ (LAN) WEB SUNUCUSU\n(Telefonunuzdan veya Ağdaki Diğer Bilgisayarlardan Web Paneline Erişim)"))

    def on_closing(self):
        current_state = self.get_current_settings_state()
        if current_state != self.last_saved_state:
            if not messagebox.askyesno("Kaydedilmemiş Değişiklikler", "Ayarlarda kaydedilmemiş değişiklikler var.\nÇıkmak istiyor musunuz?"):
                return
        
        self.is_tracking_flights = False # Arka planda çalışan harita motorunu (Thread) durdur
        self.root.destroy()
        os._exit(0)

    def run(self):
        try:
            self.root.mainloop()
        except Exception as e:
            logging.critical("Uygulama hatası:", exc_info=True)

if __name__ == "__main__":
    app = KardelenApp()
    app.run()