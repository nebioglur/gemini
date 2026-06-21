# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
import tkintermapview
import threading
import time
import requests
from tkinter import messagebox
import os
import sys
import logging
import webbrowser
import json
from PIL import Image, ImageTk

class MapViewerMixin:
    """
    Canlı haritayı ve OpenSky API üzerinden gerçek zamanlı uçuş
    verilerini yöneten Mixin sınıfı.
    Web tabanlı canlı veri (Flightradar.py) yöneticisi.
    (Eski gömülü Canlı Harita özelliği performansı ve bağımlılıkları nedeniyle kaldırılmış,
    yerine dışarıdan çalışan Canlı Veri modülüne bağlanmıştır.)
    """
    def setup_map_ui(self, parent_tab):
        """Harita sekmesinin arayüzünü oluşturur."""
        self.map_frame = ttk.Frame(parent_tab)
        self.map_frame.pack(fill="both", expand=True)

        # --- Üst Kontrol Paneli ---
        control_frame = ttk.Frame(self.map_frame)
        control_frame.pack(fill="x", side="top", pady=(0, 5))
        
        ttk.Label(control_frame, text="Harita Tipi:").pack(side="left", padx=(5,2))
        self.map_type_combo = ttk.Combobox(control_frame, values=["Sokak Haritası", "Uydu Görünümü"], state="readonly", width=15)
        self.map_type_combo.set("Sokak Haritası")
        self.map_type_combo.pack(side="left", padx=5)
        self.map_type_combo.bind("<<ComboboxSelected>>", self.change_map_type)
        
        # --- YENİ: WEB RADAR BUTONU ---
        self.btn_web_radar = ttk.Button(control_frame, text="🌐 WEB RADAR AÇ (FlightRadar24 Tarzı)", command=self.open_web_radar)
        self.btn_web_radar.pack(side="right", padx=10)

        # --- Alt Bilgi Paneli (Tıklanan öğe detayları için) ---
        self.info_frame = ttk.Frame(self.map_frame)
        self.info_frame.pack(fill="x", side="bottom")
        self.info_label = ttk.Label(self.info_frame, text="Haritadan detayını görmek istediğiniz bir uçağa veya istasyona tıklayın.", font=("Arial", 10, "bold"), padding=5)
        self.info_label.pack(side="left")

        # --- Harita Widget'ı ---
        # Harita Widget'ını oluştur
        self.map_widget = tkintermapview.TkinterMapView(self.map_frame, corner_radius=0)
        self.map_widget.pack(fill="both", expand=True)

        # Başlangıç konumu: Türkiye
        self.map_widget.set_position(39.0, 35.0)
        self.map_widget.set_zoom(6)

        # Tekerlek ile zoom yapabilmek için haritaya fare geldiğinde odaklanmayı sağla
        self.map_widget.bind("<Enter>", lambda e: self.map_widget.focus_set())

        # Uçuş marker'larını ve rotalarını bellekte tutmak için sözlükler
        self.flight_markers = {}
        self.flight_paths = {}      # Uçakların rotalarını (çizgileri) tutar
        self.flight_trails = {}     # Uçakların koordinat geçmişini tutar
        self.is_tracking_flights = True

        # Veri çekme işlemini arka planda (Thread) başlat (Arayüzü dondurmaz)
        threading.Thread(target=self.fetch_flights_loop, daemon=True).start()

    def open_web_radar(self):
        """FlightRadar24 Tarzı uygulamayı harici pencere olarak başlatır."""
        import subprocess
        from tkinter import messagebox
        
        # Zaten açıksa (arkada çalışıyorsa) tekrar yeni pencere açılmasını engelle
        if hasattr(self, 'web_radar_process') and self.web_radar_process.poll() is None:
            return
            
        if hasattr(self, 'btn_web_radar'):
            self.btn_web_radar.config(state="disabled", text="BEKLEYİN...")
        if hasattr(self, 'cp_widgets') and 'btn_live_data' in self.cp_widgets:
            self.cp_widgets['btn_live_data'].config(state="disabled", text="BEKLEYİN...")
        if hasattr(self, 'lbl_status'):
            self.lbl_status.config(text="Lütfen bekleyin, canlı veri servisi başlatılıyor...", fg="#F57C00")
        self.root.update()
            
        try:
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            script_path = os.path.join(base_dir, "flightradar.py")
            
            # Seçili istasyonun koordinatlarını bul (Argüman olarak pasla)
            lat, lon = "39.0", "35.0"
            if hasattr(self, 'settings_vars'): 
                last_st = self.settings_vars.get('var_last_station')
                if last_st and last_st.get():
                    # Örn: "LTAN - KONYA (17244)" içinden "LTAN" kodunu al
                    code = last_st.get().split(" ")[0]
                    try:
                        from ayarlar import TURKEY_STATIONS
                        if code in TURKEY_STATIONS:
                            lat, lon = str(TURKEY_STATIONS[code]['lat']), str(TURKEY_STATIONS[code]['lon'])
                    except Exception: pass

            kwargs = {}
            # Sadece PyInstaller ile EXE yapıldığında konsolu gizle. 
            # Aksi halde koddan çalıştırırken hata mesajlarını görebilmek için açık bırak.
            if sys.platform == "win32" and getattr(sys, 'frozen', False):
                kwargs["creationflags"] = 0x08000000

            if os.path.exists(script_path):
                    if getattr(sys, 'frozen', False):
                        # EXE içindeysek argüman olarak --flightradar geçiyoruz
                        self.web_radar_process = subprocess.Popen([sys.executable, "--flightradar", lat, lon], **kwargs)
                    else:
                        self.web_radar_process = subprocess.Popen([sys.executable, script_path, lat, lon], **kwargs)
            else:
                messagebox.showerror("Hata", "flightradar.py dosyası bulunamadı!")
        except Exception as e:
            messagebox.showerror("Hata", f"Canlı Veri başlatılamadı: {e}")
        finally:
            def restore_buttons():
                if hasattr(self, 'btn_web_radar'):
                    self.btn_web_radar.config(state="normal", text="🌐 WEB RADAR AÇ (FlightRadar24 Tarzı)")
                if hasattr(self, 'cp_widgets') and 'btn_live_data' in self.cp_widgets:
                    self.cp_widgets['btn_live_data'].config(state="normal", text="📡 CANLI VERİ")
            if hasattr(self, 'lbl_status'):
                self.lbl_status.config(text="Hazır.", fg="black")
            self.root.after(1500, restore_buttons)

    def open_webview_map(self):
        """Webview Harita Analiz modülünü harici pencere olarak başlatır."""
        import subprocess
        from tkinter import messagebox
        
        if hasattr(self, 'btn_web_map'):
            self.btn_web_map.config(state="disabled", text="🌍 HARİTA AÇILIYOR...\nLütfen bekleyin")
        self.root.update()
        
        try:
            import sys
            kwargs = {}
            if sys.platform == "win32" and getattr(sys, 'frozen', False):
                kwargs["creationflags"] = 0x08000000
                
            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable, "--webview-map"], **kwargs)
            else:
                base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
                script_path = os.path.join(base_dir, "webview_harita_analiz.py")
                if os.path.exists(script_path):
                    subprocess.Popen([sys.executable, script_path], **kwargs)
                else:
                    messagebox.showerror("Hata", "webview_harita_analiz.py dosyası bulunamadı!")
        except Exception as e:
            messagebox.showerror("Hata", f"Web Harita başlatılamadı: {e}")
        finally:
            if hasattr(self, 'btn_web_map'):
                self.root.after(1500, lambda: self.btn_web_map.config(state="normal", text="🌍 ETKİLEŞİMLİ WEB HARİTA\n(Animasyonlu Harita Analizi ve Detaylı Görünüm)"))

    def focus_station_on_map(self, station_code):
        """Verilen istasyon koduna göre dahili haritayı odaklar."""
        try:
            from ayarlar import TURKEY_STATIONS
            if station_code in TURKEY_STATIONS:
                st_info = TURKEY_STATIONS[station_code]
                lat, lon = st_info['lat'], st_info['lon']
                
                if hasattr(self, 'notebook') and hasattr(self, 'tab_map'):
                    self.notebook.select(self.tab_map)
                
                if hasattr(self, 'map_widget'):
                    self.map_widget.set_position(lat, lon)
                    self.map_widget.set_zoom(10)
        except Exception as e:
            logging.error(f"Haritaya odaklanma hatası: {e}")

    def change_map_type(self, event=None):
        """Harita sağlayıcısını (tile server) değiştirir."""
        selected_map = self.map_type_combo.get()
        
        if selected_map == "Uydu Görünümü":
            # Google Satellite
            self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
        else: # "Sokak Haritası"
            self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")

    def _get_plane_icon(self, angle):
        """
        ucak.png ikonunu alır, belirtilen açıya göre döndürür ve önbelleğe (cache) alır.
        """
        if not hasattr(self, '_plane_icons_cache'):
            self._plane_icons_cache = {}
            
        angle = angle if angle is not None else 0
        # Performans için açıları 10 derecelik dilimlere yuvarlıyoruz
        rounded_angle = int(round(angle / 10.0)) * 10 % 360
        
        if rounded_angle in self._plane_icons_cache:
            return self._plane_icons_cache[rounded_angle]
            
        try:
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_dir, 'icons', 'ucak.png')
            
            if os.path.exists(icon_path):
                img = Image.open(icon_path).convert("RGBA")
                img = img.resize((32, 32)) # İkon boyutu
                # PIL saat yönünün tersine, Pusula(Heading) saat yönüne döner. Bu yüzden -angle kullanıyoruz.
                rotated_img = img.rotate(-rounded_angle, resample=Image.BICUBIC)
                icon = ImageTk.PhotoImage(rotated_img)
                self._plane_icons_cache[rounded_angle] = icon
                return icon
        except Exception as e:
            logging.error(f"Uçak ikonu yükleme hatası: {e}")
            
        return None

    def _get_altitude_color(self, altitude):
        """İrtifaya (metre) göre rota izinin rengini döndürür."""
        if altitude < 2500:
            return "#FF5252" # Kırmızı (Alçak)
        elif altitude < 6000:
            return "#FFCA28" # Sarı (Orta)
        elif altitude < 10000:
            return "#69F0AE" # Yeşil (Yüksek)
        else:
            return "#40C4FF" # Mavi (Çok Yüksek / Seyir İrtifası)

    def _get_weather_icon_name(self, metar_text):
        """METAR metnine göre uygun ikon dosya adını döndürür."""
        if not isinstance(metar_text, str): return "bilinmiyor.png"
        metar_text = metar_text.upper()
        if "RA" in metar_text or "SH" in metar_text or "DZ" in metar_text: return "yagmur.png"
        if "SN" in metar_text: return "kar.png"
        if "FG" in metar_text or "BR" in metar_text: return "sis.png"
        if "TS" in metar_text: return "firtina.png"
        if "FEW" in metar_text or "SCT" in metar_text: return "parcali_bulutlu.png"
        if "BKN" in metar_text or "OVC" in metar_text: return "bulutlu.png"
        if "CAVOK" in metar_text or "SKC" in metar_text or "NSC" in metar_text: return "gunesli.png"
        return "bilinmiyor.png"

    def _get_weather_icon(self, icon_name):
        """Hava durumu ikonlarını yükler ve önbelleğe (cache) alır."""
        if not hasattr(self, '_weather_icons_cache'):
            self._weather_icons_cache = {}
            
        if icon_name in self._weather_icons_cache:
            return self._weather_icons_cache[icon_name]
            
        try:
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_dir, 'icons', icon_name)
            if os.path.exists(icon_path):
                img = Image.open(icon_path).convert("RGBA").resize((32, 32))
                icon = ImageTk.PhotoImage(img)
                self._weather_icons_cache[icon_name] = icon
                return icon
        except Exception as e:
            logging.error(f"Hava durumu ikonu yükleme hatası ({icon_name}): {e}")
        return None

    def update_station_markers(self, stations):
        """Gelen istasyon verilerine göre haritaya hava durumu ikonlarını yerleştirir."""
        if not hasattr(self, 'station_markers'):
            self.station_markers = []
            
        # Eski istasyonları temizle
        for sm in self.station_markers:
            sm.delete()
        self.station_markers.clear()
        
        for st in stations:
            if 'lat' not in st or 'lon' not in st: continue
            
            icon_name = self._get_weather_icon_name(st.get('metar', ''))
            icon = self._get_weather_icon(icon_name)
            
            m = self.map_widget.set_marker(
                st['lat'], st['lon'], text=st.get('icao', ''), icon=icon,
                command=lambda m, s=st: self.on_station_click(m, s)
            )
            self.station_markers.append(m)

    def on_station_click(self, marker, st):
        """İstasyona tıklandığında alt bilgi panelini günceller."""
        text = f"🏢 İstasyon: {st.get('icao')} | METAR: {st.get('metar')}"
        self.info_label.config(text=text, foreground="green")

    def fetch_flights_loop(self):
        """Arka planda periyodik olarak uçuş verilerini çeker."""
        
        while self.is_tracking_flights:
            try:
                # Haritanın o anki merkezini ve yakınlaştırma seviyesini al (Tüm dünyaya esneme)
                if hasattr(self, 'map_widget') and self.map_widget.canvas_winfo_exists():
                    pos = self.map_widget.get_position()
                    zoom = self.map_widget.zoom
                    # Ekranda görünen alanı (Bounding Box) zoom seviyesine göre yaklaşık hesapla
                    delta = 20.0 / max(1, zoom)
                    lamin = max(-90, pos[0] - delta)
                    lamax = min(90, pos[0] + delta)
                    lomin = max(-180, pos[1] - delta)
                    lomax = min(180, pos[1] + delta)
                    
                    url = f"https://opensky-network.org/api/states/all?lamin={lamin}&lomin={lomin}&lamax={lamax}&lomax={lomax}"
                else:
                    # Başlangıç Türkiye geneli sınırları
                    url = "https://opensky-network.org/api/states/all?lamin=35.8&lomin=25.6&lamax=42.1&lomax=44.8"

                # OpenSky API anonim kullanıcılar için 10 saniyede bir isteğe izin verir
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    flights = data.get('states', [])
                    
                    # Arayüz güncellemeleri GÜVENLİ bir şekilde ana Thread'de (after ile) yapılmalıdır
                    if hasattr(self, 'root') and self.root:
                        self.root.after(0, self.update_flight_markers, flights)
            except Exception as e:
                pass # Ağ hatası anlık olabilir, loglamaya gerek yok
            
            time.sleep(15) # 15 saniyede bir güncelle

    def on_flight_click(self, marker, details):
        """Uçağa tıklandığında alt bilgi panelini günceller."""
        text = f"✈️ Uçuş: {details['callsign']} | İrtifa: {details['altitude']} m | Hız: {details['speed']} km/s | Yön: {details['heading']}°"
        self.info_label.config(text=text, foreground="blue")
        
        # YENİ: Detaylı Uçuş Penceresini Aç
        self.show_flight_details_popup(details)

    def show_flight_details_popup(self, details):
        """Tıklanan uçağın kalkış/iniş rotasını ve detaylarını pop-up olarak gösterir."""
        pop = tk.Toplevel()
        pop.title(f"✈️ {details['callsign']} Uçuş Detayları")
        pop.geometry("320x400")
        pop.configure(bg="#263238")
        pop.attributes('-topmost', True) # Her zaman üstte
        
        tk.Label(pop, text=details['callsign'], font=("Segoe UI", 16, "bold"), bg="#263238", fg="#00E676").pack(pady=(10,5))
        
        # Rota Alanı
        f_route = tk.Frame(pop, bg="#37474F", bd=1, relief="solid")
        f_route.pack(fill="x", padx=10, pady=5)
        lbl_route = tk.Label(f_route, text="Rota bilgisi aranıyor...\nLütfen bekleyin.", font=("Segoe UI", 10), bg="#37474F", fg="#B0BEC5", justify="center")
        lbl_route.pack(pady=10)
        
        # Alt Bilgiler
        f_info = tk.Frame(pop, bg="#263238")
        f_info.pack(fill="both", expand=True, padx=15, pady=5)
        
        infos = [
            ("Menşei Ülke:", details['country']),
            ("İrtifa:", f"{details['altitude']} metre"),
            ("Hız:", f"{details['speed']} km/saat"),
            ("Yön Açısı:", f"{details['heading']}°"),
            ("Dikey Hız:", f"{details['v_rate']} m/s"),
            ("Squawk Kodu:", details['squawk'])
        ]
        for i, (lbl, val) in enumerate(infos):
            tk.Label(f_info, text=lbl, font=("Segoe UI", 10, "bold"), bg="#263238", fg="#CFD8DC").grid(row=i, column=0, sticky="w", pady=4)
            tk.Label(f_info, text=val, font=("Segoe UI", 10), bg="#263238", fg="white").grid(row=i, column=1, sticky="w", padx=10, pady=4)
            
        # Arka planda Flightradar24'ten Rota Çek
        def fetch_route():
            try:
                url = f"https://api.flightradar24.com/common/v1/flight/list.json?query={details['callsign'].strip()}&fetchBy=callsign"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json',
                    'Referer': 'https://www.flightradar24.com/'
                }
                r = requests.get(url, headers=headers, timeout=5)
                flights = r.json().get("result", {}).get("response", {}).get("data", [])
                if flights and hasattr(pop, 'winfo_exists') and pop.winfo_exists():
                    f = flights[0]
                    org = f.get("airport", {}).get("origin", {}).get("name", "Bilinmiyor")
                    dst = f.get("airport", {}).get("destination", {}).get("name", "Bilinmiyor")
                    lbl_route.config(text=f"🛫 Kalkış: {org}\n\n🛬 İniş: {dst}", fg="#69F0AE")
                elif hasattr(pop, 'winfo_exists') and pop.winfo_exists():
                    lbl_route.config(text="Bu uçuş için rota bilgisi bulunamadı.", fg="#FFCA28")
            except Exception:
                if hasattr(pop, 'winfo_exists') and pop.winfo_exists(): lbl_route.config(text="Rota servisine ulaşılamadı.", fg="#FF5252")
                    
        threading.Thread(target=fetch_route, daemon=True).start()

    def update_flight_markers(self, flights):
        """Gelen verilere göre haritadaki uçak ikonlarını ve rotalarını günceller."""
        current_flight_ids = set()
        
        for f in flights:
            f_id = f[0]          # Eşsiz Uçuş Kimliği
            callsign = f[1].strip() if f[1] else "N/A" # Uçuş Kodu (Örn: THY123)
            lon, lat = f[5], f[6]
            altitude = f[7] if f[7] else 0
            speed_ms = f[9] if f[9] else 0
            heading = f[10]      # Yön Açısı
            vertical_rate = f[11] if len(f) > 11 and f[11] else 0
            squawk = f[14] if len(f) > 14 and f[14] else "Bilinmiyor"
            country = f[2] if len(f) > 2 and f[2] else "Bilinmiyor"
            
            # İrtifa Filtresi: Belirtilen metrenin (örn: 10000) üzerindeki uçakları atla
            if altitude > 10000:
                continue
            
            speed_kmh = int(speed_ms * 3.6) # m/s'yi km/h'ye çevir
            details = {'callsign': callsign, 'altitude': int(altitude), 'speed': speed_kmh, 'heading': heading, 'v_rate': vertical_rate, 'squawk': squawk, 'country': country}
            
            if lat is None or lon is None: continue
            current_flight_ids.add(f_id)
            
            # --- Rota (Trail) Yönetimi ---
            if f_id not in self.flight_trails:
                self.flight_trails[f_id] = []
            self.flight_trails[f_id].append((lat, lon))
            # Performans için son 30 koordinatı tut
            if len(self.flight_trails[f_id]) > 30:
                self.flight_trails[f_id].pop(0)

            # --- Marker (İkon) Yönetimi ---
            # Uçak zaten haritada varsa silip yeni açıyla tekrar ekle
            if f_id in self.flight_markers:
                self.flight_markers[f_id].delete()
                
            icon = self._get_plane_icon(heading)
            
            # Harita üzerinde uçağın yanına yazılacak metin (Kod, İrtifa ve Hız)
            marker_text = f"{callsign}\n{int(altitude)}m | {speed_kmh}km/h"
            marker = self.map_widget.set_marker(
                lat, lon, text=marker_text, icon=icon,
                command=lambda m, d=details: self.on_flight_click(m, d)
            )
            self.flight_markers[f_id] = marker
            
            # --- Path (Çizgi) Yönetimi ---
            if f_id in self.flight_paths:
                self.flight_paths[f_id].delete()
            
            if len(self.flight_trails[f_id]) > 1:
                path_color = self._get_altitude_color(altitude)
                path = self.map_widget.set_path(self.flight_trails[f_id], color=path_color, width=3)
                self.flight_paths[f_id] = path
            
        # Türkiye sınırlarından çıkan veya kaybolan uçakları haritadan sil
        lost_flights = set(self.flight_markers.keys()) - current_flight_ids
        for f_id in lost_flights:
            # Marker'ı sil
            if f_id in self.flight_markers:
                self.flight_markers[f_id].delete()
                del self.flight_markers[f_id]
            # Path'i sil
            if f_id in self.flight_paths:
                self.flight_paths[f_id].delete()
                del self.flight_paths[f_id]
            # Trail verisini sil
            if f_id in self.flight_trails:
                del self.flight_trails[f_id]

if __name__ == "__main__":
    # Bu dosya doğrudan (standalone) çalıştırıldığında kendi başına bir pencere açar.
    class StandaloneMapApp(tk.Tk, MapViewerMixin):
        def __init__(self):
            super().__init__()
            self.title("✈️ Kardelen Canlı Uçuş Radarı (Bağımsız Çalışma Modu)")
            self.geometry("1200x800")
            self.root = self  # Mixin içerisindeki self.root kullanımları için gerekli
            
            main_frame = ttk.Frame(self)
            main_frame.pack(fill="both", expand=True)
            
            # Harita arayüzünü mixin üzerinden kur
            self.setup_map_ui(main_frame)
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            
        def on_closing(self):
            self.is_tracking_flights = False
            self.destroy()
            sys.exit(0)
            
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    app = StandaloneMapApp()
    app.mainloop()