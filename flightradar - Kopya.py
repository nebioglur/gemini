# -*- coding: utf-8 -*-
import sys
import os
import subprocess

try:
    import webview
    import requests
except ImportError as e:
    if getattr(sys, 'frozen', False):
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Eksik Kütüphane", f"Gerekli kütüphane bulunamadı:\n{e}")
        sys.exit(1)
        
    print(f"Eksik kütüphane tespit edildi ({e}). Otomatik yükleniyor...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview", "requests"])
        import webview
        import requests
    except Exception as install_err:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Eksik Kütüphane", f"Canlı Veri (Web Radar) için kütüphaneler otomatik yüklenemedi:\n{install_err}\n\nLütfen terminalden 'pip install pywebview requests' komutunu manuel çalıştırın.")
        sys.exit(1)

import logging
import time
import math
import csv
import re

# Terminal çökmelerini önlemek için güvenli stream
class SafeStream:
    def __init__(self, logger_func):
        self.logger_func = logger_func
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

    def write(self, msg):
        if isinstance(msg, bytes):
            msg = msg.decode('utf-8', errors='ignore')
        if msg.strip(): self.logger_func(msg.strip())
        return len(msg)
    def flush(self): pass
    def isatty(self): return False

# --- LOG SİSTEMİ KURULUMU ---
safe_user_dir = next((p for p in [os.environ.get("USERPROFILE"), os.path.expanduser("~"), os.environ.get("PUBLIC")] if p and os.path.exists(p)), os.path.dirname(os.path.abspath(__file__)))
log_dir = os.path.join(safe_user_dir, "KardelenLogs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "flightradar_debug.log")

log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler(sys.__stdout__)
console_handler.setFormatter(log_formatter)

# Hem dosyaya hem de aktif açık olan Terminal (Konsol) ekranına bas
logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])

import sys
if sys.stdout is None: sys.stdout = SafeStream(logging.info)
if sys.stderr is None: sys.stderr = SafeStream(logging.error)

import traceback
def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Uygulama arka planda çökerse, hatayı yutmak yerine ekrana mesaj kutusu çıkartır ve terminale yazar."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # Hataları kesinlikle gerçek terminale/konsola yazdır:
    print(f"\n[CRITICAL ERROR] flightradar.py ÇÖKTÜ:\n{err_msg}", file=sys.__stderr__)
    
    logging.critical(f"FATAL CRASH:\n{err_msg}")
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("FlightRadar Çöktü", f"Kritik Hata Oluştu:\n\n{err_msg}")
        root.destroy()
    except:
        pass
    sys.exit(1)

sys.excepthook = global_exception_handler

from concurrent.futures import ThreadPoolExecutor, as_completed

# --- ADSB.LOL (TOPLULUK RADAR AĞI) ---
# Herhangi bir üyelik, şifre veya limit gerektirmeden, dünya çapındaki gönüllülerin
# verileriyle tamamen özgür bir şekilde uçuşları çeker.

try:
    from ayarlar import TURKEY_STATIONS
except ImportError:
    TURKEY_STATIONS = {}

class RadarApi:
    def __init__(self):
        self.last_429_time = 0
        self.backoff_duration = 60
        self.cached_stations = {}
        self.last_station_fetch = 0

    def _safe_request(self, url, headers=None, timeout=5, retries=3, delay=1):
        """Ağ kopmalarına karşı otomatik tekrar deneme (Retry) mantığı."""
        for attempt in range(retries):
            try:
                res = requests.get(url, headers=headers, timeout=timeout)
                return res
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    raise e
                logging.warning(f"Ağ hatası ({url}). {delay}sn sonra tekrar deneniyor... ({attempt+1}/{retries})")
                time.sleep(delay)
        return None

    def _fetch_bolge_data(self, bolge):
        """Bir bölge için uçuş verilerini çeken yardımcı fonksiyon (thread için)."""
        b_lat, b_lon, b_dist = bolge['lat'], bolge['lon'], bolge['dist']
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        # 1. Ana Kaynak: airplanes.live
        try:
            url_al = f"https://api.airplanes.live/v2/point/{b_lat}/{b_lon}/{b_dist}"
            logging.info(f"Bölge taranıyor (Airplanes.live): Lat={b_lat}, Lon={b_lon}")
            res_al = self._safe_request(url_al, headers=headers, timeout=5, retries=2)
            
            if res_al.status_code == 200:
                data_al = res_al.json()
                if data_al and "ac" in data_al:
                    return {"status": "success", "data": data_al["ac"]}
            elif res_al.status_code == 429:
                logging.warning(f"Airplanes.live 429 Rate Limit (Bölge: {b_lat},{b_lon})")
                return {"status": "rate_limit"}
            else:
                logging.warning(f"Airplanes.live HTTP {res_al.status_code} (Bölge: {b_lat},{b_lon})")
        except Exception as e:
            logging.error(f"Airplanes.live Bağlantı hatası (Bölge: {b_lat},{b_lon}): {e}")
            return {"status": "error", "message": str(e)}

        # 2. Yedek Kaynak: adsb.lol
        try:
            url = f"https://api.adsb.lol/v2/point/{b_lat}/{b_lon}/{b_dist}"
            logging.info(f"Yedek kaynak deneniyor (ADSB.lol): Lat={b_lat}, Lon={b_lon}")
            res = self._safe_request(url, headers=headers, timeout=5, retries=2)
            if res.status_code == 200:
                data = res.json()
                if data and "ac" in data:
                    return {"status": "success", "data": data["ac"]}
            elif res.status_code == 429:
                logging.warning(f"ADSB.lol 429 Rate Limit (Bölge: {b_lat},{b_lon})")
                return {"status": "rate_limit"}
        except Exception as e:
            logging.error(f"ADSB.lol Bağlantı hatası (Bölge: {b_lat},{b_lon}): {e}")
            return {"status": "error", "message": str(e)}
            
        return {"status": "failure"}

    def get_flights(self, lat=39.0, lon=35.0, dist=500):
        # Bu fonksiyon artık harita merkezinden bağımsız olarak tüm Türkiye'yi tarar.
        # Kullanıcının "Ankara, Antalya'da uçak yok" sorununu çözmek için.
        
        # Türkiye'yi kapsayacak 3 ana merkez noktası (Batı, Orta, Doğu - 250 NM yarıçap ile tüm TR'yi kapsar)
        bolgeler = [
            {"lat": 39.0, "lon": 28.5, "dist": 250}, # Batı (İstanbul, İzmir, Batı Akdeniz)
            {"lat": 39.0, "lon": 34.5, "dist": 250}, # Orta (Ankara, Konya, Adana, Antalya, Samsun)
            {"lat": 38.5, "lon": 41.0, "dist": 250}  # Doğu (Erzurum, Diyarbakır, Van)
        ]

        # Mükerrer kayıtları önlemek için uçakları 'hex' koduna göre saklayacak bir sözlük
        tum_ucaklar = {}
        rate_limit_hit = False
        last_error_msg = "Bilinmeyen bir bağlantı hatası oluştu."

        # Bölgeleri paralel olarak tara (Performans artışı)
        with ThreadPoolExecutor(max_workers=len(bolgeler)) as executor:
            future_to_bolge = {executor.submit(self._fetch_bolge_data, bolge): bolge for bolge in bolgeler}
            for future in as_completed(future_to_bolge):
                try:
                    result = future.result()
                    if result['status'] == 'success':
                        for ucak in result['data']:
                            if 'hex' in ucak:
                                tum_ucaklar[ucak['hex']] = ucak
                    elif result['status'] == 'rate_limit':
                        rate_limit_hit = True
                    elif result['status'] == 'error':
                        last_error_msg = result['message']
                except Exception as exc:
                    bolge = future_to_bolge[future]
                    logging.error(f'{bolge} için thread hatası: {exc}')
                    last_error_msg = str(exc)

        if not tum_ucaklar:
            if rate_limit_hit:
                return {"error": "429 Too Many Requests (Limit Aşıldı). Lütfen bekleyin."}
            return {"error": f"Veri alınamadı. Hata: {last_error_msg}"}

        # Sözlükteki tüm uçakları (artık mükerrer olmayan) bir listeye çevir
        final_list = list(tum_ucaklar.values())
        
        return {"ac": final_list}
            
    def get_stations(self, lamin=None, lomin=None, lamax=None, lomax=None):
        now = time.time()
        # 5 dakikalık (300 sn) önbellekleme
        if now - self.last_station_fetch < 300 and self.cached_stations:
            return self.cached_stations

        try:
            logging.info("Tüm dünya METAR verileri CSV'den çekiliyor...")
            csv_url = "https://aviationweather.gov/data/cache/metars.cache.csv"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/csv',
                'Connection': 'close' # SSL EOF hatasını (UNEXPECTED_EOF_WHILE_READING) önlemek için eklendi
            }
            r_csv = self._safe_request(csv_url, headers=headers, timeout=15, retries=3, delay=2)
            
            if r_csv.status_code == 200:
                lines = r_csv.text.splitlines()
                skip = 5
                for i, line in enumerate(lines[:30]):
                    if "raw_text" in line and "station_id" in line:
                        skip = i
                        break
                
                reader = csv.DictReader(lines[skip:])
                stations_data = {}
                
                for row in reader:
                    try:
                        lat = float(row['latitude'])
                        lon = float(row['longitude'])
                        code = row['station_id']
                        raw_text = row.get('raw_text', '')
                        
                        # Bulutluluk ve Hadiseye göre ikon belirleme
                        metar_upper = raw_text.upper()
                        icon = "🌤️" # Varsayılan (Parçalı Bulutlu)
                        if "TS" in metar_upper: icon = "⛈️"
                        elif "SN" in metar_upper: icon = "🌨️"
                        elif any(x in metar_upper for x in ["RA", "SH", "DZ"]): icon = "🌧️"
                        elif any(x in metar_upper for x in ["FG", "BR", "HZ"]): icon = "🌫️"
                        elif any(x in metar_upper for x in ["BKN", "OVC"]): icon = "☁️"
                        elif any(x in metar_upper for x in ["FEW", "SCT"]): icon = "⛅"
                        elif any(x in metar_upper for x in ["CAVOK", "SKC", "NSC", "CLR"]): icon = "☀️"
                        
                        altim_val = "N/A"
                        if row.get('altim_in_hg'):
                            try:
                                altim_val = float(row['altim_in_hg']) * 33.8639
                            except: pass
                            
                        stations_data[code] = {
                            "lat": lat,
                            "lon": lon,
                            "name": code,
                            "metar": raw_text,
                            "temp": row.get('temp_c', "N/A"),
                            "dewp": row.get('dewpoint_c', "N/A"),
                            "wspd": row.get('wind_speed_kt', "N/A"),
                            "wdir": row.get('wind_dir_degrees', "N/A"),
                            "visib": row.get('visibility_statute_mi', "N/A"),
                            "altim": altim_val,
                            "wxString": row.get('wx_string', ""),
                            "icon": icon
                        }
                    except Exception:
                        continue
                
                if stations_data: # Sadece başarılı ve dolu veri setini önbelleğe al
                    self.cached_stations = stations_data
                    self.last_station_fetch = now
                return stations_data
            else:
                return {"error": f"CSV API Hatası HTTP {r_csv.status_code}"}
        except Exception as e:
            logging.error(f"Yer istasyonu veri çekme hatası: {e}")
            return {"error": str(e)}

    def get_route(self, callsign):
        if not callsign or callsign.strip() == "N/A" or callsign.strip() == "":
            return {"error": "Çağrı kodu yok"}
            
        callsign = callsign.strip()
        
        # 1. KAYNAK: FlightRadar24 API
        try:
            url = f"https://api.flightradar24.com/common/v1/flight/list.json?query={callsign}&fetchBy=callsign"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Origin': 'https://www.flightradar24.com',
                'Referer': 'https://www.flightradar24.com/',
                'Connection': 'close'
            }
            res = self._safe_request(url, headers=headers, timeout=5, retries=2)
            if res.status_code == 200:
                data = res.json()
                flights = data.get("result", {}).get("response", {}).get("data", [])
                if flights:
                    org = flights[0].get("airport", {}).get("origin", {}).get("name", "Bilinmiyor")
                    dst = flights[0].get("airport", {}).get("destination", {}).get("name", "Bilinmiyor")
                    if org != "Bilinmiyor" and dst != "Bilinmiyor":
                        return {"org": org, "dst": dst}
        except Exception as e:
            logging.warning(f"FR24 Rota Hatası: {e}")
            
        # 2. KAYNAK: OpenSky Network (Statik Rota Veritabanı Yedek)
        try:
            os_url = f"https://opensky-network.org/api/routes?callsign={callsign}"
            headers_os = {'User-Agent': 'Mozilla/5.0', 'Connection': 'close'}
            res_os = self._safe_request(os_url, headers=headers_os, timeout=5, retries=2)
            if res_os.status_code == 200:
                data = res_os.json()
                route = data.get("route", [])
                if route and len(route) >= 2:
                    return {"org": f"ICAO: {route[0]}", "dst": f"ICAO: {route[1]}"}
        except Exception as e:
            logging.warning(f"OpenSky Rota Hatası: {e}")

        return {"error": "Bulunamadı"}

    def toggle_fullscreen(self):
        try:
            if webview.windows:
                webview.windows[0].toggle_fullscreen()
        except Exception as e: pass
        
    def log_from_js(self, message):
        """Javascript'ten gelen mesajları log dosyasına yazar"""
        logging.info(f"[JAVASCRIPT] {message}")
        
    def open_log_file(self):
        """Log dosyasını varsayılan metin editörüyle açar."""
        try: os.startfile(log_file)
        except Exception as e: logging.error(f"Log dosyası açılamadı: {e}")

    def get_satellite_layers(self):
        layers = []
        # 1. MGM (Türkiye Özel)
        try:
            url = "http://uzal.mgm.gov.tr/uydu.aspx?m=nwcgeo6&r=eu"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            res = self._safe_request(url, headers=headers, timeout=4, retries=3) # Zaman aşımı düşürüldü (Donmayı önler)
            if res.status_code == 200:
                images = re.findall(r'(rsm/uydu/[a-zA-Z0-9_/-]+\.(?:jpg|png|gif))', res.text)
                if images:
                    mtg_images = [img for img in images if 'mtg' in img.lower()]
                    if not mtg_images:
                        mtg_images = [img for img in images if 'nwcgeo' in img.lower()]
                    
                    best_img = mtg_images[-1] if mtg_images else images[-1]
                    bounds = [[20.0, -20.0], [60.0, 50.0]] 
                    layers.append({
                        "name": "MGM (Türkiye)",
                        "type": "image", 
                        "url": "http://uzal.mgm.gov.tr/" + best_img, 
                        "bounds": bounds,
                        "attribution": "© MGM"
                    })
        except requests.exceptions.RequestException as e:
            logging.warning(f"Ağ Bağlantısı Hatası (MGM Uydu): İnternet koptu veya sunucu yanıt vermiyor. Atlandı.")
        except Exception as e:
            logging.error(f"MGM Uydu tarama hatası: {e}")

        # 2. EUMETSAT WMS Layers
        eumetsat_url = "https://view.eumetsat.int/geoserver/wms"
        eumetsat_attribution = "© EUMETSAT"
        layers.extend([
            {
                "name": "EUMETSAT Hava Kütlesi", "type": "wms", "url": eumetsat_url,
                "layer": "msg_fes:rgb_airmass", "attribution": eumetsat_attribution
            },
            {
                "name": "EUMETSAT Doğal Renk", "type": "wms", "url": eumetsat_url,
                "layer": "msg_fes:rgb_natural", "attribution": eumetsat_attribution
            },
            {
                "name": "EUMETSAT Toz", "type": "wms", "url": eumetsat_url,
                "layer": "msg_fes:dust", "attribution": eumetsat_attribution
            }
        ])

        # 3. NASA GIBS WMS Layers
        nasa_wms_url = "https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi"
        nasa_attribution = "© NASA GIBS"
        layers.extend([
             { "name": "NASA VIIRS (Gerçek Renk)", "type": "wms", "url": nasa_wms_url, "layer": "VIIRS_SNPP_CorrectedReflectance_TrueColor", "attribution": nasa_attribution },
             { "name": "NASA MODIS (Gerçek Renk)", "type": "wms", "url": nasa_wms_url, "layer": "MODIS_Terra_CorrectedReflectance_TrueColor", "attribution": nasa_attribution }
        ])
        
        # 4. NOAA (IEM) Global Satellite (Kızılötesi)
        noaa_wms_url = "https://mesonet.agron.iastate.edu/cgi-bin/wms/goes/global_ir.cgi"
        layers.append({
             "name": "NOAA Global Kızılötesi (IR)", "type": "wms", "url": noaa_wms_url, "layer": "global_ir", "attribution": "© NOAA / IEM"
        })

        # 5. Yeni EUMETSAT Kızılötesi Bulut Tabakaları
        layers.extend([
            { "name": "EUMETSAT Bulut (Kızılötesi 10.8)", "type": "wms", "url": eumetsat_url, "layer": "msg_fes:ir108", "attribution": eumetsat_attribution },
            { "name": "EUMETSAT Su Buharı (6.2)", "type": "wms", "url": eumetsat_url, "layer": "msg_fes:wv062", "attribution": eumetsat_attribution },
            { "name": "EUMETSAT Renkli Kızılötesi", "type": "wms", "url": eumetsat_url, "layer": "msg_fes:rgb_eview", "attribution": eumetsat_attribution }
        ])

        return layers

HTML = r"""
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<title>Kardelen Radar</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>

<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>

<style>
html, body { width: 100%; height: 100%; margin:0; padding:0; background:#050f1a; font-family:Arial; overflow: hidden; }
#map { width: 100%; height: 100%; }

#hud {
 position:absolute; top:5px; left:5px;
 background:rgba(15, 32, 39, 0.8);
 color:#00E676;
 padding:5px;
 border-radius:4px;
 font-size:10px;
 z-index:1001; /* Katman kontrolünün altında kalması için artırıldı */
 border: 1px solid #455A64;
 backdrop-filter: blur(5px);
 transition: all 0.3s ease;
 width: 170px;
}

#hud-header {
 font-weight: bold;
 cursor: pointer;
 display: flex;
 justify-content: space-between;
 align-items: center;
 gap: 5px;
 font-size: 11px;
}

#hud-header .arrow {
 font-size: 9px;
 transition: transform 0.3s;
}

#hud:hover #hud-header .arrow {
 transform: rotate(180deg);
}

/* Leaflet katman kontrolü için */
.leaflet-control-layers { background: rgba(15, 32, 39, 0.8) !important; border: 1px solid #455A64 !important; backdrop-filter: blur(5px) !important; color: white !important; }
.leaflet-control-layers-selector { margin-top: 2px !important; }

#hud-content {
 max-height: 0;
 opacity: 0;
 overflow: hidden;
 transition: max-height 0.4s ease, opacity 0.3s ease;
}

#hud:hover #hud-content {
 max-height: 400px;
 opacity: 1;
 margin-top: 4px;
}

#hud-content button {
 padding: 4px !important;
 font-size: 9px !important;
 margin-top: 3px !important;
 width: 100%;
}

.plane-container { position: relative; width: 0; height: 0; }
.plane-img { position: absolute; top: -16px; left: -16px; width: 32px; height: 32px; filter: drop-shadow(0px 3px 3px rgba(0,0,0,0.8)); }
.plane-label { position: absolute; top: 12px; left: -25px; width: 50px; text-align: center; font-weight: bold; font-size: 11px; color: #00E676; text-shadow: 1px 1px 2px #000, -1px -1px 2px #000, 1px -1px 2px #000, -1px 1px 2px #000; }
.station-label { font-size: 10px; color: #B0BEC5; font-weight: bold; text-shadow: 1px 1px 2px #000; margin-top: 5px; margin-left: -10px; }
.leaflet-popup-content-wrapper { background: #263238; color: #fff; border-radius: 8px; border: 1px solid #4FC3F7; }
.leaflet-popup-tip { background: #263238; border: 1px solid #4FC3F7; }

@keyframes strike {
    0% { opacity: 1; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.5); }
    100% { opacity: 0; transform: scale(0.5); }
}
.lightning-strike {
    animation: strike 2s ease-out forwards;
    font-size: 20px;
    color: #FFEB3B;
    text-shadow: 0 0 10px #FF0000, 0 0 20px #FF0000;
}

/* RÜZGAR AKIŞI ANİMASYONLARI */
.wind-particle {
    position: absolute;
    bottom: 0px;
    left: -1px;
    width: 2px;
    height: 15px;
    border-radius: 2px;
    opacity: 0;
    animation-name: windFlow;
    animation-iteration-count: infinite;
    animation-timing-function: linear;
}
@keyframes windFlow {
    0% { transform: translateY(0px) scaleY(0.5); opacity: 0; }
    20% { opacity: 1; transform: translateY(-10px) scaleY(1); }
    80% { opacity: 1; transform: translateY(-30px) scaleY(1); }
    100% { transform: translateY(-40px) scaleY(0.5); opacity: 0; }
}
</style>
</head>

<body>

<div id="hud">
<div id="hud-header">
<span>✈️ KARDELEN RADAR PRO</span>
<span class="arrow">▼</span>
</div>
<div id="hud-content">
<hr style="border-color:#455A64; margin:0 0 3px 0;">
Uçak: <span id="count">0</span><br>
⚡ Şimşek: <span id="lightning-count">0</span> (<span id="lightning-screen">0</span>)<br>
🎯 Seçili: <span id="selected">Yok</span><br>
🔍 Filtre:<br><input type="text" id="callsign-filter" placeholder="Örn: THY, PGT" onkeyup="applyFilter()" style="width: 110px; background: rgba(0,0,0,0.5); color: #00E676; border: 1px solid #4FC3F7; border-radius: 4px; padding: 2px 2px; outline:none; font-size:9px; margin-top:2px;">
<hr style="border-color:#455A64; margin:3px 0;">
<span style="font-size: 9px;">
<b style="color:#FF5252">●</b> &lt;5k &nbsp; <b style="color:#FF9800">●</b> &lt;10k &nbsp; <b style="color:#FFEB3B">●</b> &lt;20k<br>
<b style="color:#00E676">●</b> &lt;30k &nbsp;&nbsp; <b style="color:#4FC3F7">●</b> &gt;30k (İrtifa - ft)
</span>
<hr style="border-color:#455A64; margin:3px 0;">
<button id="btn-fullscreen" onclick="toggleFullScreen()" style="width:100%; padding:6px; background:#0288D1; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold; margin-top:3px; transition: 0.3s;">🖥️ Tam Ekran</button>
<button onclick="openLog()" style="background:#FF9800; color:black; border:none; border-radius:4px; cursor:pointer; font-weight:bold; transition: 0.3s;">📝 Log Dosyasını Aç</button>
<button id="btn-toggle-planes" onclick="togglePlanes()" style="background:#37474F; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold; transition: 0.3s;">✈️ Uçakları Gizle</button>
<button id="btn-toggle-sat" onclick="toggleSatellite()" style="background:#303F9F; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold; transition: 0.3s;">🛰️ Uydu Görüntüsü Göster</button>
<select id="sat-select" onchange="changeSatelliteLayer()" style="width:100%; margin-top:5px; background: #37474F; color: white; border: 1px solid #4FC3F7; padding: 4px; border-radius: 4px; display: none;"></select>
<button id="btn-toggle-stations" onclick="toggleStations()" style="background:#455A64; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold; transition: 0.3s;">🏢 İstasyonları Gizle</button>
<button id="btn-toggle-wind" onclick="toggleWind()" style="background:#00897B; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold; transition: 0.3s; margin-top:3px;">🌬️ Rüzgar Akışı Göster</button>
<button id="btn-toggle-trails" onclick="toggleTrails()" style="background:#8E24AA; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold; transition: 0.3s;">🛤️ Rotaları Gizle</button>
<button id="btn-toggle-lightning" onclick="toggleLightning()" style="background:#F57C00; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold; transition: 0.3s;">⚡ Şimşek Göster</button>
<button id="btn-toggle-lightning-tr" onclick="toggleTurkeyOnlyLightning()" style="background:#00695C; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold; transition: 0.3s;">⚡ Sadece TR (Kapalı)</button>
<button id="btn-toggle-radar" onclick="toggleRadar()" style="background:#00ACC1; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold; transition: 0.3s;">🌧️ Yağış (Radar) Göster</button>
</div>
</div>

<div id="map"></div>

<script>
const map = L.map('map', {zoomControl: false, wheelPxPerZoomLevel: 100, zoomSnap: 0.1, zoomDelta: 0.5}).setView([39.0, 35.0], 6);
L.control.zoom({position: 'bottomright'}).addTo(map);
 
// --- HARİTA KATMANLARI ---
const satelliteMap = L.tileLayer('https://mt0.google.com/vt/lyrs=s&hl=tr&x={x}&y={y}&z={z}&s=Ga', {
    attribution: '&copy; Google',
    maxZoom: 22
});

const darkMap = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO'
});

const streetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
});

// Varsayılan olarak karanlık haritayı yükle
darkMap.addTo(map);

const baseLayers = { "Karanlık": darkMap, "Uydu": satelliteMap, "Sokak": streetMap };
L.control.layers(baseLayers, null, { position: 'topright' }).addTo(map);

let planes = {};
let selected = null;
let planesLayer = L.layerGroup().addTo(map);
let planesVisible = true;
let stationsLayer = L.layerGroup().addTo(map);
let stationsVisible = true;
let trailsLayer = L.layerGroup().addTo(map);
let trailsVisible = true;

let lightningSocket = null;
let lightningLayer = L.layerGroup().addTo(map);
let lightningVisible = false;
let totalLightning = 0;
let screenLightning = 0;

// YENİ: Türkiye Şimşek Filtresi
let turkeyOnlyLightning = false;
const turkeyBorderPolygon = []; // Bu Python tarafından doldurulacak

function isPointInPolygon(point, vs) {
    // ray-casting algorithm, point is [lon, lat]
    var x = point[0], y = point[1];
    var inside = false;
    for (var i = 0, j = vs.length - 1; i < vs.length; j = i++) {
        var xi = vs[i][0], yi = vs[i][1];
        var xj = vs[j][0], yj = vs[j][1];
        var intersect = ((yi > y) != (yj > y))
            && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
};

function toggleTurkeyOnlyLightning() {
    let btn = document.getElementById("btn-toggle-lightning-tr");
    turkeyOnlyLightning = !turkeyOnlyLightning;
    if (turkeyOnlyLightning) {
        btn.innerText = "⚡ Sadece TR (Açık)";
        btn.style.background = "#004D40";
    } else {
        btn.innerText = "⚡ Sadece TR (Kapalı)";
        btn.style.background = "#00695C";
    }
}

function toggleLightning() {
    let btn = document.getElementById("btn-toggle-lightning");
    if (lightningVisible) {
        map.removeLayer(lightningLayer);
        lightningVisible = false;
        btn.innerText = "⚡ Şimşek Göster";
        btn.style.background = "#F57C00";
        if (lightningSocket) {
            lightningSocket.close();
            lightningSocket = null;
        }
    } else {
        map.addLayer(lightningLayer);
        lightningVisible = true;
        btn.innerText = "⚡ Şimşek Gizle";
        btn.style.background = "#E65100";
        totalLightning = 0;
        document.getElementById("lightning-count").innerText = "0";
        connectBlitzortung();
    }
}

function connectBlitzortung() {
    if (!lightningVisible) return;
    
    // Blitzortung sunucuları (ws1 ve ws7 sık kullanılır, LightningMaps de iyidir)
    let wsServers = ["wss://ws1.blitzortung.org/", "wss://ws7.blitzortung.org/", "wss://ws.lightningmaps.org/", "wss://ws.blitzortung.org:3000/"];
    let wsUrl = wsServers[Math.floor(Math.random() * wsServers.length)];
    
    try {
        lightningSocket = new WebSocket(wsUrl);
        lightningSocket.onopen = function() {
            lightningSocket.send(JSON.stringify({time: 0}));
            lightningSocket.send('{"a":111}'); // Eski/Alternatif sunucular için uyumluluk
        };
        lightningSocket.onmessage = function(e) {
            try {
                let data = JSON.parse(e.data);
                if (data) {
                    let lat = data.lat !== undefined ? data.lat : data.y;
                    let lon = data.lon !== undefined ? data.lon : data.x;
                    
                    if (lat !== undefined && lon !== undefined) {
                        totalLightning++;
                        document.getElementById("lightning-count").innerText = totalLightning;
                        drawLightning(lat, lon);
                    }
                }
            } catch(err) {}
        };
        lightningSocket.onclose = function() {
            if (lightningVisible) setTimeout(connectBlitzortung, 5000);
        };
    } catch(err) {
        console.log("Şimşek verisi bağlantısı başarısız.");
    }
}

function drawLightning(lat, lon) {
    // YENİ: Türkiye filtresi kontrolü
    if (turkeyOnlyLightning && (turkeyBorderPolygon.length > 0) && !isPointInPolygon([lon, lat], turkeyBorderPolygon)) {
        return;
    }

    let bounds = map.getBounds();
    if (!bounds.contains([lat, lon])) return; // Sadece ekrandaki şimşekleri çiz (Performans)
    
    screenLightning++;
    document.getElementById("lightning-screen").innerText = screenLightning;
    
    let icon = L.divIcon({
        html: '<div class="lightning-strike">⚡</div>',
        className: '', iconSize: [20, 20], iconAnchor: [10, 10]
    });
    let marker = L.marker([lat, lon], {icon: icon, interactive: false}).addTo(lightningLayer);
    setTimeout(() => { 
        if (lightningLayer.hasLayer(marker)) {
            lightningLayer.removeLayer(marker);
            screenLightning--;
            document.getElementById("lightning-screen").innerText = screenLightning;
        }
    }, 2000);
}

let radarLayer = null;
let radarVisible = false;

function toggleRadar() {
    let btn = document.getElementById("btn-toggle-radar");
    if (radarVisible) {
        if (radarLayer) map.removeLayer(radarLayer);
        radarVisible = false;
        btn.innerText = "🌧️ Yağış (Radar) Göster";
        btn.style.background = "#00ACC1";
    } else {
        radarVisible = true;
        btn.innerText = "🌧️ Yağış (Radar) Gizle";
        btn.style.background = "#00838F";
        
        fetch("https://api.rainviewer.com/public/weather-maps.json")
        .then(res => {
            if (!res.ok) throw new Error("API Yanıt Vermedi veya Bağlantı Koptu");
            return res.json();
        })
        .then(data => {
            if (!radarVisible) return; // Kullanıcı yüklenmeden kapatmışsa ekleme
            let past = data.radar.past;
            let latestPath = past[past.length - 1].path; // En güncel radar taraması
            let host = data.host || "https://tilecache.rainviewer.com";
            
            if (radarLayer) map.removeLayer(radarLayer);
            radarLayer = L.tileLayer(host + latestPath + "/256/{z}/{x}/{y}/4/1_1.png", {
                opacity: 0.65, // %65 Saydamlık ile alttaki haritayı kapatmaz
                zIndex: 10,
                attribution: 'Weather data © RainViewer'
            });
            radarLayer.addTo(map);
        }).catch(err => console.log("Radar verisi alınamadı: " + err));
    }
}

function toggleTrails() {
    let btn = document.getElementById("btn-toggle-trails");
    if (trailsVisible) {
        map.removeLayer(trailsLayer);
        trailsVisible = false;
        btn.innerText = "🛤️ Rotaları Göster";
        btn.style.background = "#607D8B";
    } else {
        map.addLayer(trailsLayer);
        trailsVisible = true;
        btn.innerText = "🛤️ Rotaları Gizle";
        btn.style.background = "#8E24AA";
    }
}

function toggleStations() {
    let btn = document.getElementById("btn-toggle-stations");
    if (stationsVisible) {
        map.removeLayer(stationsLayer);
        stationsVisible = false;
        btn.innerText = "🏢 İstasyonları Göster";
        btn.style.background = "#607D8B";
    } else {
        map.addLayer(stationsLayer);
        stationsVisible = true;
        btn.innerText = "🏢 İstasyonları Gizle";
        btn.style.background = "#455A64";
    }
}

let filterText = "";
function applyFilter() {
    filterText = document.getElementById("callsign-filter").value.toUpperCase();
    for (let id in planes) {
        let p = planes[id];
        let isMatch = filterText === "" || p.callsign.includes(filterText);
        let imgEl = document.getElementById(`img-${id}`);
        let lblEl = document.getElementById(`lbl-${id}`);
        if (imgEl && lblEl) {
            if (isMatch) {
                imgEl.style.opacity = "1";
                lblEl.style.display = "block";
                imgEl.style.filter = (filterText !== "") ? "drop-shadow(0px 0px 8px #FF5252) drop-shadow(0px 0px 8px #ffffff)" : "drop-shadow(0px 3px 3px rgba(0,0,0,0.8))";
                if(p.polyline) p.polyline.setStyle({opacity: 0.6});
            } else {
                imgEl.style.opacity = "0.15";
                imgEl.style.filter = "none";
                lblEl.style.display = "none";
                if(p.polyline) p.polyline.setStyle({opacity: 0.0});
            }
        }
    }
}

function getAltitudeColor(alt_ft) {
    if (!alt_ft) return "#FFCA28"; // Veri yoksa standart sarı
    if (alt_ft < 5000) return "#FF5252"; // Kırmızı (Alçak İrtifa - < 5000 ft)
    if (alt_ft < 10000) return "#FF9800"; // Turuncu (< 10000 ft)
    if (alt_ft < 20000) return "#FFEB3B"; // Sarı (< 20000 ft)
    if (alt_ft < 30000) return "#00E676"; // Yeşil (< 30000 ft)
    return "#4FC3F7"; // Mavi (Seyir İrtifası)
}

function getPlaneSvg(color, isMil, isHeli) {
    let stroke = isMil ? "#FF1744" : "#ffffff"; // Askeri/Polis araçları için Kırmızı Çerçeve
    let strokeW = isMil ? "1.5" : "0.5";
    let path = "M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z";
    
    if (isHeli) {
        // Helikopter Şekli (Özel SVG Yolu)
        path = "M10.5,2 L10.5,8 L7,8 L7,10 L10.5,10 L10.5,18 L8,21 L8,22 L16,22 L16,21 L13.5,18 L13.5,10 L17,10 L17,8 L13.5,8 L13.5,2 Z";
    }
    return encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="${color}" stroke="${stroke}" stroke-width="${strokeW}" d="${path}"/></svg>`);
}

let isFullScreen = false;
function toggleFullScreen() {
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.toggle_fullscreen();
    } else {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            if (document.exitFullscreen) document.exitFullscreen();
        }
    }
    
    let btn = document.getElementById("btn-fullscreen");
    isFullScreen = !isFullScreen;
    if (isFullScreen) {
        btn.innerText = "↙️ Tam Ekrandan Çık";
        btn.style.background = "#D32F2F";
    } else {
        btn.innerText = "🖥️ Tam Ekran";
        btn.style.background = "#0288D1";
    }
}

function togglePlanes() {
    let btn = document.getElementById("btn-toggle-planes");
    if (planesVisible) {
        map.removeLayer(planesLayer);
        planesVisible = false;
        btn.innerText = "✈️ Uçakları Göster";
        btn.style.background = "#607D8B";
    } else {
        map.addLayer(planesLayer);
        planesVisible = true;
        btn.innerText = "✈️ Uçakları Gizle";
        btn.style.background = "#37474F";
    }
}

let windVisible = false;
function toggleWind() {
    let btn = document.getElementById("btn-toggle-wind");
    windVisible = !windVisible;
    if (windVisible) {
        btn.innerText = "🌬️ Rüzgar Akışı Gizle";
        btn.style.background = "#00695C";
    } else {
        btn.innerText = "🌬️ Rüzgar Akışı Göster";
        btn.style.background = "#00897B";
    }
    loadStations(true); // İstasyonları yeniden yükleyerek rüzgar akışını uygula
}

let satelliteLayers = [];
let satLayer = null;
let satVisible = false;

async function populateSatelliteOptions() {
    if (window.pywebview && window.pywebview.api) {
        satelliteLayers = await window.pywebview.api.get_satellite_layers();
        const select = document.getElementById('sat-select');
        select.innerHTML = '';
        satelliteLayers.forEach((layer, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = layer.name;
            select.appendChild(option);
        });
    }
}

async function toggleSatellite() {
    let btn = document.getElementById("btn-toggle-sat");
    let select = document.getElementById("sat-select");

    if (satVisible) {
        if (satLayer) map.removeLayer(satLayer);
        satVisible = false;
        btn.innerText = "🛰️ Uydu Görüntüsü Göster";
        btn.style.background = "#303F9F";
        select.style.display = "none";
    } else {
        satVisible = true;
        btn.innerText = "🛰️ Uydu Görüntüsü Gizle";
        btn.style.background = "#1A237E";
        select.style.display = "block";
        changeSatelliteLayer(); // Seçili olan katmanı yükle
    }
}

function changeSatelliteLayer() {
    if (satLayer) {
        map.removeLayer(satLayer);
        satLayer = null;
    }

    if (!satVisible || satelliteLayers.length === 0) return;

    const select = document.getElementById('sat-select');
    const selectedIndex = select.value;
    if (selectedIndex < 0 || selectedIndex >= satelliteLayers.length) return;

    const layerData = satelliteLayers[selectedIndex];

    if (layerData.type === "wms") {
        satLayer = L.tileLayer.wms(layerData.url, { layers: layerData.layer, format: 'image/png', transparent: true, opacity: 0.65, attribution: layerData.attribution }).addTo(map);
    } else if (layerData.type === "image") {
        satLayer = L.imageOverlay(layerData.url, layerData.bounds, { opacity: 0.65, attribution: layerData.attribution }).addTo(map);
    }
}

function openLog() {
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.open_log_file();
    }
}

let fetchDelay = 15000; // Varsayılan 15 saniye (429 Rate Limit önlemi)
let loopStarted = false;

async function fetchFlightsLoop() {
    await fetchFlights();
    setTimeout(fetchFlightsLoop, fetchDelay);
}

async function fetchFlights(){
 try{
  let center = map.getCenter();
  let bounds = map.getBounds();
  // Haritanın merkezinden sol üstüne olan mesafeyi deniz miline (nm) çevir, alanı hesapla
  let dist_nm = Math.round(center.distanceTo(bounds.getNorthWest()) / 1852);
  if(dist_nm > 250) dist_nm = 250; // API max 250 NM destekler, üzeri HTTP 400 verir
  if(dist_nm < 50) dist_nm = 50;

  let data = null;
  if (window.pywebview && window.pywebview.api) {
      data = await window.pywebview.api.get_flights(center.lat, center.lng, dist_nm);
  } else {
      const res = await fetch(`https://api.adsb.lol/v2/point/${center.lat}/${center.lng}/${dist_nm}`);
      data = await res.json();
  }

  if(data && data.error){
      document.getElementById("count").innerText = "HATA";
      if (data.error.includes("429")) {
          document.getElementById("selected").innerText = data.error;
          fetchDelay = 60000; // Limite takılınca süreyi uzat
      } else {
          document.getElementById("selected").innerText = "Bağlantı Hatası";
      }
      if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.log_from_js("Veri çekme hatası: " + data.error);
      }
      return;
  }
  
  fetchDelay = 15000; // Başarılı olunca normale dön

  if(!data || !data.ac){
      if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.log_from_js("Uçak listesi (ac) bulunamadı veya boş döndü.");
      }
      return;
  }

  let seen = new Set();

  document.getElementById("count").innerText = data.ac.length;

  data.ac.forEach(f=>{
      let id = f.hex;
      let lon = f.lon, lat = f.lat;
      if(!lat||!lon) return;

      let heading = f.track || 0;
      let callsign = (f.flight || "N/A").trim();
      
      // ADSB.lol irtifayı doğrudan FEET (ft) olarak verir. 'ground' ise 0 kabul et.
      let alt_ft = f.alt_baro === "ground" ? 0 : (f.alt_baro || 0);
      
      // ADSB.lol hızı KNOTS (kt) olarak verir. Animasyon algoritması m/s istediği için çeviriyoruz:
      let speed_kt = f.gs || 0;
      let speed = speed_kt * 0.514444; // m/s çevirimi
      
      let color = getAltitudeColor(alt_ft);
      
      // Askeri Uçak / Helikopter Tespiti
      let isMil = f.mil || callsign.startsWith("TUAF") || callsign.startsWith("HVK") || callsign.startsWith("TURAF") || callsign.startsWith("JANDARMA") || callsign.startsWith("POLIS"); // Askeri ve Kolluk Kuvvetleri
      let isHeli = f.category === "A7" || f.category === "A6" || (f.t && (f.t.startsWith("H") || f.t.includes("UH") || f.t.includes("AH") || f.t.includes("S70"))); // A7 Rotorcraft ve Bilinen Helikopter Tipleri
      
      let planeSvg = getPlaneSvg(color, isMil, isHeli);

      seen.add(id);
      
      let isMatch = filterText === "" || callsign.includes(filterText);
      let opacity = isMatch ? "1" : "0.15";
      let lblDisplay = isMatch ? "block" : "none";
      let filterStyle = (filterText !== "" && isMatch) ? "drop-shadow(0px 0px 8px #FF5252) drop-shadow(0px 0px 8px #ffffff)" : (isMil ? "drop-shadow(0px 0px 6px #FF1744)" : "drop-shadow(0px 3px 3px rgba(0,0,0,0.8))");
      
      let popupHtml = `<div style="font-size:13px; line-height:1.5; min-width:200px;">
          <b style="font-size:16px; color:#FFCA28;">✈️ ${callsign}</b><hr style="border-color:#455A64; margin:5px 0;">
          ${isMil ? '<b style="color:#FF1744;">🛡️ Askeri / Devlet Uçuşu</b><br>' : ''}
          ${isHeli ? '<b style="color:#29B6F6;">🚁 Helikopter</b><br>' : ''}
          <b>İrtifa:</b> ${alt_ft} ft<br>
          <b>Hız:</b> ${Math.round(speed_kt * 1.852)} km/s<br>
          <b>Yön:</b> ${Math.round(heading)}°<br>
          <div id="route-${id}" style="background:#1c262f; padding:5px; border-radius:4px; font-size:12px; text-align:center; margin-top:5px;">
              <a href="#" onclick="fetchRoute('${id}', '${callsign}'); return false;" style="color:#4FC3F7; text-decoration:none;">🔄 Rotayı Göster</a>
          </div>
      </div>`;

      if(!planes[id]){
        let iconHtml = `<div class="plane-container"><img class="plane-img" id="img-${id}" src="data:image/svg+xml;charset=utf-8,${planeSvg}" style="transform: rotate(${heading}deg); opacity: ${opacity}; filter: ${filterStyle};"></div><div class="plane-label" id="lbl-${id}" style="display: ${lblDisplay};">${callsign}</div>`;
        
        let customIcon = L.divIcon({
            html: iconHtml,
            className: '', iconSize: [0, 0]
        });

        let marker = L.marker([lat, lon], {icon: customIcon}).addTo(planesLayer);
        marker.bindPopup(popupHtml);
        
        // Uçağın arkasındaki kuyruk çizgisi (Polyline)
        let polyline = L.polyline([[lat, lon]], {color: color, weight: 2, opacity: isMatch ? 0.6 : 0.0, dashArray: '4, 4'}).addTo(trailsLayer);
        
        // Tıklama event'i
        marker.on('click', () => selectPlane(id));
        
        planes[id]={
          id, lat, lon, alt: alt_ft, speed, heading, marker, callsign,
          path: [[lat, lon]], polyline: polyline,
          last_update: Date.now()
        };
      } else {
        let p=planes[id];
        
        // Eğer uçak yer değiştirdiyse rotaya (path) yeni noktayı ekle
        let lastPoint = p.path[p.path.length - 1];
        if (lastPoint[0] !== lat || lastPoint[1] !== lon) {
            p.path.push([lat, lon]);
            if (p.path.length > 50) p.path.shift(); // En fazla son 50 konumu (yaklaşık 15 dk) hafızada tut
        }
        
        p.lat=lat;
        p.lon=lon;
        p.alt=alt_ft;
        p.speed=speed;
        p.heading=heading;
        p.polyline.setStyle({color: color, opacity: isMatch ? 0.6 : 0.0});
        
        // Pop-up kapalıyken arka planda güncel içeriği yenile
        if(!planes[id].marker.isPopupOpen()) {
            planes[id].marker.setPopupContent(popupHtml);
        }
        
        // İkon yönünü ve rengini güncelle
        let imgEl = document.getElementById(`img-${id}`);
        let lblEl = document.getElementById(`lbl-${id}`);
        if(imgEl) {
            imgEl.style.transform = `rotate(${heading}deg)`;
            imgEl.src = `data:image/svg+xml;charset=utf-8,${planeSvg}`;
            if (isMatch && lblEl) {
                imgEl.style.opacity = "1";
                lblEl.style.display = "block";
                imgEl.style.filter = (filterText !== "") ? "drop-shadow(0px 0px 8px #FF5252) drop-shadow(0px 0px 8px #ffffff)" : "drop-shadow(0px 3px 3px rgba(0,0,0,0.8))";
            } else if (lblEl) {
                imgEl.style.opacity = "0.15";
                imgEl.style.filter = "none";
                lblEl.style.display = "none";
            }
        }
      }
  }); 

  for(let id in planes){
    if(!seen.has(id)){
      planesLayer.removeLayer(planes[id].marker);
      trailsLayer.removeLayer(planes[id].polyline);
      delete planes[id];
    }
  }

 }catch(e){
  if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.log_from_js("JS Çalışma Zamanı Hatası: " + e.message);
  }
 }
}

function animate(){
  var now = Date.now();
  for(let id in planes){
    let p = planes[id];
    let dt = (now - p.last_update) / 1000.0;
    p.last_update = now;
    
    if(p.speed > 0 && p.heading !== null){
      let dist = p.speed * dt;
      let R = 6378137.0; 
      let lat1 = p.lat * Math.PI / 180, lon1 = p.lon * Math.PI / 180, brng = p.heading * Math.PI / 180;
      let lat2 = Math.asin(Math.sin(lat1)*Math.cos(dist/R) + Math.cos(lat1)*Math.sin(dist/R)*Math.cos(brng));
      let lon2 = lon1 + Math.atan2(Math.sin(brng)*Math.sin(dist/R)*Math.cos(lat1), Math.cos(dist/R)-Math.sin(lat1)*Math.sin(lat2));
      p.lat = lat2 * 180 / Math.PI; p.lon = lon2 * 180 / Math.PI;
      p.marker.setLatLng([p.lat, p.lon]);
      
      // Rota çizgisini animasyonlu olarak uçağın arkasından uzat
      p.polyline.setLatLngs([...p.path, [p.lat, p.lon]]);
    }
  }
  requestAnimationFrame(animate);
}

function selectPlane(id){
 selected=id;
 let p=planes[id];
 if(!p) return;
 let speed_kmh = Math.round(p.speed * 3.6);
 document.getElementById("selected").innerText=`${p.callsign || id} (${p.alt} ft | ${speed_kmh} km/h)`;
 map.flyTo([p.lat, p.lon], 8);
}

function follow(){
 if(selected && planes[selected]){
   let p=planes[selected];
   let c=map.getCenter();

   map.setView([
     c.lat + (p.lat - c.lat)*0.1,
     c.lng + (p.lon - c.lng)*0.1
   ], map.getZoom(), {animate: false});
 }

 requestAnimationFrame(follow);
}

// Haritaya boş tıklanırsa seçimi kaldır
map.on('click', function(e) {
  selected = null;
  document.getElementById("selected").innerText="Yok";
});

window.fetchRoute = async function(id, callsign) {
    var routeDiv = document.getElementById('route-' + id);
    if(routeDiv) {
        routeDiv.innerHTML = "<span style='color:#B0BEC5'><i>Aranıyor...</i></span>";
        if (window.pywebview && window.pywebview.api) {
            let res = await window.pywebview.api.get_route(callsign);
            if (res.error) {
                routeDiv.innerHTML = `<span style='color:#FFCA28'>Gizli veya bulunamadı.</span><br><a href="#" onclick="fetchRoute('${id}', '${callsign}'); return false;" style="color:#4FC3F7; text-decoration:none; font-size:11px; margin-top:3px; display:inline-block;">🔄 Tekrar Dene</a>`;
            } else {
                routeDiv.innerHTML = `<span style='color:#69F0AE; font-weight:bold;'>🛫 ${res.org}<br>🛬 ${res.dst}</span>`;
            }
        } else {
            routeDiv.innerHTML = "<span style='color:#FF5252'>Bağlantı Hatası</span>";
        }
    }
};

let stationMarkers = {};

async function loadStations(forceReload = false) {
    if (!forceReload && Object.keys(stationMarkers).length > 1000) return;
    
    if (window.pywebview && window.pywebview.api) {
        let stations = await window.pywebview.api.get_stations();
        if (stations.error) return;
        
        if (forceReload) {
            stationsLayer.clearLayers();
            stationMarkers = {};
        }
        
        for (let code in stations) {
            if (stationMarkers[code]) continue;
            
            let st = stations[code];
            let color = "#0288D1";
            
            let tempStr = (st.temp !== "N/A" && st.temp !== null) ? st.temp + " °C" : "-";
            let windStr = (st.wdir !== "N/A" && st.wspd !== "N/A" && st.wdir !== null) ? st.wdir + "° / " + st.wspd + " kt" : "-";
            let altimStr = (st.altim !== "N/A" && st.altim !== null && !isNaN(st.altim)) ? Math.round(st.altim) + " hPa" : "-";
            let wxStr = st.wxString ? st.wxString : "Yok";
            let iconEmoji = st.icon || "🏢";
            
            let windHtml = "";
            // Rüzgar akışını hesapla ve çiz
            if (windVisible && st.wdir !== "N/A" && st.wspd !== "N/A" && st.wdir !== null && st.wspd > 0 && !isNaN(st.wdir)) {
                let speed = parseFloat(st.wspd);
                let dir = parseFloat(st.wdir);
                let animDur = Math.max(0.3, 2.5 - (speed * 0.05)); // Hızlı rüzgarda kısa/seri animasyon
                let pColor = speed > 25 ? "#FF5252" : (speed > 15 ? "#FFCA28" : "#00E676"); // Hıza göre partikül rengi
                
                windHtml = `
                <div style="position:absolute; top:0px; left:0px; width:0px; height:0px; transform: rotate(${dir + 180}deg); pointer-events: none; z-index:-1;">
                    <div class="wind-particle" style="animation-duration: ${animDur}s; background: linear-gradient(to top, transparent, ${pColor});"></div>
                    <div class="wind-particle" style="animation-duration: ${animDur}s; animation-delay: ${animDur/2}s; background: linear-gradient(to top, transparent, ${pColor});"></div>
                </div>`;
            }

            let stIcon = L.divIcon({
                html: `<div style="position:relative;">
                    ${windHtml}
                    <div style="position:absolute; left:-12px; top:-12px; font-size: 18px; text-shadow: 1px 1px 2px #000; text-align: center;">${iconEmoji}</div>
                    <div class="station-label" style="position:absolute; left:-20px; top:10px; width:40px; text-align:center;">${code}</div>
                </div>`,
                className: '', iconSize: [0,0], iconAnchor: [0,0]
            });
            
            let popupHtml = `
            <div style="font-family: Arial; font-size: 13px; min-width: 250px;">
                <b style="font-size:15px; color:${color};">${iconEmoji} ${code}</b><hr style="border-color:#455A64; margin:5px 0;">
                <table style="width:100%; color:#CFD8DC; font-size:12px; margin-bottom:5px;">
                    <tr><td><b>🌡️ Sıcaklık:</b></td><td>${tempStr}</td></tr>
                    <tr><td><b>💨 Rüzgar:</b></td><td>${windStr}</td></tr>
                    <tr><td><b>⏱️ Basınç:</b></td><td>${altimStr}</td></tr>
                    <tr><td><b>⛈️ Hadise:</b></td><td>${wxStr}</td></tr>
                </table>
                <b>Ham METAR:</b><br>
                <div style="background:#1c262f; padding:8px; border-radius:4px; margin-top:2px; color:#4FC3F7; font-family:Consolas; font-size:12px; line-height:1.4;">${st.metar}</div>
            </div>`;
            
            let marker = L.marker([st.lat, st.lon], {icon: stIcon});
            marker.bindPopup(popupHtml);
            marker.addTo(stationsLayer);
            stationMarkers[code] = marker;
        }
    }
}

setInterval(() => {
    if (stationsVisible) {
        loadStations(true);
    }
}, 300000); // 5 dakikada bir istasyon verilerini yenile

// API Köprüsü Hazır Olduğunda Başlat
window.addEventListener('pywebviewready', function() {
    if (loopStarted) return;
    loopStarted = true;
    populateSatelliteOptions();
    fetchFlightsLoop();
    animate();
    follow();
    loadStations();
});

// Köprü yüklenmezse (Normal Tarayıcıda açılırsa) yedeği çalıştır
setTimeout(() => {
    if (!window.pywebview && !loopStarted) {
        loopStarted = true;
        fetchFlightsLoop(); animate(); follow();
    }
}, 2000);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    import sys
    import json
    from ayarlar import TURKEY_BORDER
    
    start_lat = 39.0
    start_lon = 35.0
    start_zoom = 6
    
    if len(sys.argv) >= 3:
        try:
            start_lat = float(sys.argv[1])
            start_lon = float(sys.argv[2])
            if start_lat != 39.0 or start_lon != 35.0:
                start_zoom = 9 # Spesifik bir meydana odaklanıyorsa daha yakından başla
        except: pass
        
    # HTML içindeki varsayılan setView koordinatlarını dinamik olarak değiştir
    html_content = HTML.replace("setView([39.0, 35.0], 6)", f"setView([{start_lat}, {start_lon}], {start_zoom})")

    # YENİ: Türkiye sınır poligonunu Javascript'e enjekte et
    turkey_polygon_js = json.dumps(TURKEY_BORDER)
    html_content = html_content.replace("const turkeyBorderPolygon = [];", f"const turkeyBorderPolygon = {turkey_polygon_js};")

    webview.create_window(
        "✈️ Kardelen Radar Pro (Leaflet API Sürümü)",
        html=html_content,
        js_api=RadarApi(),
        width=1200,
        height=800
    )
    webview.start()
   