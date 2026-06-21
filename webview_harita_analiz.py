# -*- coding: utf-8 -*-
import datetime
import sys
import os
import traceback

try:
    import webview
except ImportError:
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview"])
        import webview
    except Exception as e:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("Hata", f"pywebview kütüphanesi yüklenemedi:\n{e}\n\nLütfen terminalden 'pip install pywebview' komutunu çalıştırın.")
        sys.exit(1)

# Arka planda çalışırken (Konsol yokken) PyWebView'un log yazdırmaya çalışıp çökmesini engeller
class SafeStream:
    def __init__(self, filename):
        self.filename = filename
    def write(self, msg):
        try:
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(str(msg))
        except: pass
    def flush(self): pass
    def isatty(self): return False
    @property
    def buffer(self):
        class _Buf:
            def write(self, m): pass
            def flush(self): pass
        return _Buf()

try:
    log_dir = os.path.join(os.path.expanduser("~"), "KardelenLogs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "webview_harita_debug.log")
    if sys.stdout is None: sys.stdout = SafeStream(log_file)
    if sys.stderr is None: sys.stderr = SafeStream(log_file)
except: pass

from kardelen_scraper import KardelenScraper
from log_processor import process_and_analyze_logs
import TAF_METAR_TREND
from sinoptik_METAR_ROTA import SinoptikRobotModulu
from ayarlar import TURKEY_STATIONS, ICAO_TO_WMO

class HaritaAnalizApi:
    def __init__(self):
        self.scraper = KardelenScraper()
        self.robot = TAF_METAR_TREND.HavacilikRobotModulu()
        self.sin_robot = SinoptikRobotModulu()
        self.scraper.analyze_site()

    def get_stations(self):
        """JS tarafına çizilmesi için Türkiye istasyonlarını gönderir."""
        return TURKEY_STATIONS

    def analyze_station(self, station_code, day, month, year):
        """Haritadaki pinden tıklanınca çağrılır. İstasyonun analizini yapıp HTML döner."""
        wmo_code = ICAO_TO_WMO.get(station_code)
        if not wmo_code:
            return {"html": f"<b style='color:red;'>WMO kodu bulunamadı ({station_code})</b>", "color": "#B0BEC5"}

        try:
            self.scraper.set_station(wmo_code)
            logs = self.scraper.fetch_logs(day, month, year, "500")
            
            if not logs:
                return {"html": "<b style='color:orange;'>Kriterlere uygun veri bulunamadı.</b>", "color": "#F57F17"}
            
            analiz_sonuclari = process_and_analyze_logs(logs, self.robot)
            
            all_metars = []
            for group in analiz_sonuclari:
                for obs in group['observations']:
                    if "METAR" in obs['type'] or "SPECI" in obs['type']:
                        all_metars.append(obs)
            
            # Son 3 analiz sonucunu (en güncel) alarak HTML şablonuna çevir
            html_out = f"<div style='max-height:250px; overflow-y:auto; padding-right:5px;'>"
            html_out += f"<h4 style='margin:0 0 10px 0; color:#0277BD;'>{station_code} Son Rasatlar</h4>"
            
            hata_sayisi = 0
            gosterilen = 0
            for group in reversed(analiz_sonuclari):
                for obs in reversed(group['observations']):
                    if gosterilen >= 10: break # Sadece son 10 rasatı göster
                    
                    turu = obs['type']
                    saat = obs['raw'][3] if len(obs['raw']) > 3 else "-"
                    bulten = obs['bulten']
                    
                    reasons = []
                    if "SİNOPTİK" in turu or "SYNOP" in turu:
                        target_metar_raw = "-"
                        for m in reversed(all_metars):
                            if m['dt'] <= obs['dt']:
                                target_metar_raw = m['bulten']
                                break
                        skor, s_durum, s_hatalar = self.sin_robot.analiz_et(bulten, target_metar_raw, ref_date=obs['dt'], all_metars=all_metars)
                        durum = s_durum
                        reasons = [h for h in s_hatalar if "❌" in h or "Çelişkisi" in h or "Uyumsuz" in h or "Hatası" in h]
                    else:
                        durum = obs.get('analysis', {}).get('durum', '-')
                        reasons = obs.get('analysis', {}).get('reasons', [])

                    renk = "#000"
                    if "F/UYUMSUZ" in durum:
                        renk = "#D84315"
                        hata_sayisi += 1
                    elif "UYUMSUZ" in durum: 
                        renk = "#D32F2F"
                        hata_sayisi += 1
                    elif "UYUMLU" in durum: renk = "#2E7D32"
                    elif "DİKKAT" in durum: renk = "#F57F17"
                    
                    if durum == "-": continue # Boş analizleri atla

                    html_out += f"<div style='border-bottom:1px solid #ccc; padding-bottom:5px; margin-bottom:5px;'>"
                    html_out += f"<strong style='color:{renk};'>[{saat}] {turu}</strong> - {durum}<br>"
                    html_out += f"<span style='font-family:monospace; font-size:10px;'>{bulten}</span>"
                    if ("UYUMSUZ" in durum or "DİKKAT" in durum) and reasons:
                        html_out += "<ul style='margin:2px 0 0 15px; font-size:10px; color:#555;'>"
                        for r in reasons:
                            if r.startswith('='): continue
                            html_out += f"<li>{r}</li>"
                        html_out += "</ul>"
                    html_out += f"</div>"
                    gosterilen += 1
                    
            if hata_sayisi > 0:
                html_out += f"<br><b style='color:red;'>⚠️ {hata_sayisi} Uyumsuzluk/Hata var!</b>"
                marker_color = "#D32F2F"
            else:
                marker_color = "#2E7D32" if gosterilen > 0 else "#B0BEC5"
                
            html_out += "</div>"
            return {"html": html_out, "color": marker_color}
            
        except Exception as e:
            return {"html": f"<b style='color:red;'>Hata: {str(e)}</b>", "color": "#B0BEC5"}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="utf-8">
    <title>Kardelen Harita Analiz</title>
    <style>
        html, body { width: 100%; height: 100%; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #E0E0E0; }
        #map { width: 100%; height: 100%; background-color: #121212; }
        .control-panel { position: absolute; top: 10px; right: 10px; z-index: 1000; background: rgba(38, 50, 56, 0.9); padding: 15px; border-radius: 8px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .control-panel input { width: 40px; margin-right: 5px; text-align: center; }
        .control-panel input#month { width: 80px; }
    </style>
</head>
<body>
    <div id="loadingScreen" style="position:fixed; width:100%; height:100%; background:#121212; color:#00E676; display:flex; flex-direction:column; justify-content:center; align-items:center; z-index:9999; font-size:20px;">
        <div style="font-size:40px; margin-bottom:10px;">🌍</div>
        <div>Harita Altyapısı Yükleniyor...</div>
        <div id="jsErrorLog" style="color:#FF5252; font-size:14px; margin-top:20px; max-width:80%; text-align:center;">Eğer bu ekran uzun süre gitmezse, Python ile iletişim kurulamamış demektir.</div>
    </div>
    <div class="control-panel">
        <b>📅 ANALİZ DÖNEMİ</b><br><br>
        
        <!-- Tarih Seçimi İçin Dropdown (Seçim Kutuları) -->
        <div style="display: flex; gap: 5px; margin-bottom: 10px;">
            <select id="day" style="flex: 1; padding: 6px; background: #37474F; color: white; border: 1px solid #546E7A; border-radius: 4px; outline: none; cursor: pointer;"></select>
            <select id="month" style="flex: 2; padding: 6px; background: #37474F; color: white; border: 1px solid #546E7A; border-radius: 4px; outline: none; cursor: pointer;"></select>
            <select id="year" style="flex: 1.5; padding: 6px; background: #37474F; color: white; border: 1px solid #546E7A; border-radius: 4px; outline: none; cursor: pointer;"></select>
        </div>
        <small style="color:#B0BEC5; display:block; margin-bottom: 5px;">Haritadan istasyon seçin.</small>
        <div style="display: flex; gap: 5px; margin-top: 10px;">
            <button id="btnAnalyzeAll" onclick="analizTumIstasyonlar()" style="flex: 1; padding: 8px; background-color: #00E676; color: #121212; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; transition: 0.3s; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">🌍 TÜMÜNÜ ANALİZ ET</button>
            <button id="btnCancelAll" onclick="iptalEt()" style="display: none; padding: 8px; background-color: #D32F2F; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">⛔ İPTAL</button>
        </div>
        
        <!-- İSTATİSTİK TABLOSU (Varsayılan olarak gizli, tarama başlayınca açılır) -->
        <div id="statsPanel" style="display: none; margin-top: 15px; font-size: 12px; background: rgba(0,0,0,0.4); padding: 10px; border-radius: 6px; border: 1px solid #455A64;">
            <div style="margin-bottom: 8px; font-weight: bold; text-align: center; color: #E0E0E0; border-bottom: 1px solid #546E7A; padding-bottom: 4px;">📊 TARAMA İSTATİSTİKLERİ</div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span style="color: #00E676;">✅ Uyumlu:</span> <span id="statSuccess" style="font-weight: bold; color: #00E676;">0</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span style="color: #FF5252;">❌ Hatalı/Uyumsuz:</span> <span id="statError" style="font-weight: bold; color: #FF5252;">0</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #FFCA28;">⚠️ Veri Yok/Gri:</span> <span id="statOther" style="font-weight: bold; color: #FFCA28;">0</span>
            </div>
        </div>
    </div>
    <div id="map"></div>
    
    <script>
        var map;
        var markers = {};
        var globalStations = {};
        var isApiReady = false;
        var isMapReady = false;
        
        // CDN engeline takılıp beyaz/boş ekran çıkmasını engellemek için hata yakalayıcı
        window.onerror = function(msg, url, line) {
            let errBox = document.getElementById('jsErrorLog');
            if (errBox) {
                errBox.innerHTML += `Hata: ${msg} (Satır: ${line})<br><br>Güvenlik duvarınız Leaflet (Harita) sunucularını engelliyor olabilir.`;
            } else {
                document.body.innerHTML += `<div style='position:absolute; top:10px; left:10px; background:rgba(0,0,0,0.8); color:#FF5252; padding:10px; z-index:9999;'>Hata: ${msg} (Satır: ${line})</div>`;
            }
        };

        document.addEventListener("DOMContentLoaded", function() {
            var today = new Date();
            
            // Günleri Doldur
            var dSel = document.getElementById('day');
            for(let i=1; i<=31; i++) { 
                let v = String(i).padStart(2, '0'); 
                dSel.add(new Option(v, v, false, i === today.getDate())); 
            }
            
            // Ayları Doldur
            var mSel = document.getElementById('month');
            var months = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"];
            months.forEach((m, idx) => {
                mSel.add(new Option(m, m, false, idx === today.getMonth()));
            });

            // Yılları Doldur
            var ySel = document.getElementById('year');
            var currYear = today.getFullYear();
            for(let i=2023; i<=currYear; i++) {
                ySel.add(new Option(i, i, false, i === currYear));
            }
        });

        // Asenkron kütüphane yükleyici (Sayfanın donmasını tamamen engeller)
        function loadLeaflet() {
            let link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css';
            document.head.appendChild(link);
            
            let script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js';
            script.onload = function() {
                isMapReady = true;
                map = L.map('map').setView([39.0, 35.0], 6);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '&copy; OpenStreetMap contributors'
                }).addTo(map);
                checkAndInit();
            };
            script.onerror = function() {
                let errBox = document.getElementById('jsErrorLog');
                if (errBox) errBox.innerHTML += `<br><br><b style="color:yellow;">DİKKAT:</b> Kurum güvenlik duvarı harita sunucusuna erişimi tamamen engelliyor (Bağlantı reddedildi).`;
            };
            document.head.appendChild(script);
        }

        async function checkAndInit() {
            if (!isApiReady || !isMapReady) return;
            let loadScreen = document.getElementById('loadingScreen');
            if (loadScreen) loadScreen.style.display = 'none';
            try {
                let stations = await pywebview.api.get_stations();
                globalStations = stations;
                for (let code in stations) {
                    let st = stations[code];
                    let customIcon = L.divIcon({
                        className: 'custom-pin',
                        html: `<div style="background-color: #0277BD; width: 26px; height: 26px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; color: white; font-size: 9px; font-weight: bold;">${code}</div>`,
                        iconSize: [26, 26],
                        iconAnchor: [13, 13]
                    });
                    let marker = L.marker([st.lat, st.lon], {icon: customIcon}).addTo(map);
                    markers[code] = marker;
                    marker.bindPopup("<div style='text-align:center;'><b>" + code + " - " + st.name + "</b><br><br><button style='padding:5px 15px; cursor:pointer; background:#0277BD; color:white; border:none; border-radius:4px;' onclick='analizIstek(\"" + code + "\")'>Bu İstasyonu Analiz Et</button></div><div id='res_" + code + "' style='margin-top:10px;'></div>", {maxWidth: 350, minWidth: 250});
                }
            } catch(e) { console.error(e); }
        }
        
        window.addEventListener('pywebviewready', function() {
            isApiReady = true;
            checkAndInit();
        });
        
        // Güvenlik Duvarı/Edge takılmasına karşı yedek tetikleyici
        setTimeout(() => { if(window.pywebview) { isApiReady = true; checkAndInit(); } }, 2000);
        
        loadLeaflet();

        async function analizIstek(code) {
            document.getElementById('res_' + code).innerHTML = "<div style='text-align:center;'><br>⏳ <i>Veriler çekilip analiz ediliyor...</i></div>";
            let d = document.getElementById('day').value;
            let m = document.getElementById('month').value;
            let y = document.getElementById('year').value;
            let response = await pywebview.api.analyze_station(code, d, m, y);
            document.getElementById('res_' + code).innerHTML = response.html;
            
            if (response.color && markers[code]) {
                let newIcon = L.divIcon({
                    className: 'custom-pin',
                    html: `<div style="background-color: ${response.color}; width: 26px; height: 26px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; color: white; font-size: 9px; font-weight: bold;">${code}</div>`,
                    iconSize: [26, 26],
                    iconAnchor: [13, 13]
                });
                markers[code].setIcon(newIcon);
            }
        }

        var iptalIstegi = false; // Tarama iptali için bayrak
        function iptalEt() {
            iptalIstegi = true;
            let btnCancel = document.getElementById('btnCancelAll');
            if (btnCancel) { 
                btnCancel.innerHTML = "⏳ Durduruluyor..."; 
                btnCancel.disabled = true; 
            }
        }

        async function analizTumIstasyonlar() {
            iptalIstegi = false;
            let btn = document.getElementById('btnAnalyzeAll');
            let btnCancel = document.getElementById('btnCancelAll');
            btn.disabled = true;
            btn.style.backgroundColor = "#546E7A";
            btn.style.color = "white";
            
            if (btnCancel) { btnCancel.style.display = "block"; btnCancel.innerHTML = "⛔ İPTAL"; btnCancel.disabled = false; }
            
            let d = document.getElementById('day').value;
            let m = document.getElementById('month').value;
            let y = document.getElementById('year').value;
            
            let codes = Object.keys(markers);
            let total = codes.length;
            let current = 0;
            
            // Sayaçları sıfırla ve İstatistik tablosunu göster
            let cSuccess = 0, cError = 0, cOther = 0;
            document.getElementById('statsPanel').style.display = 'block';
            document.getElementById('statSuccess').innerText = "0";
            document.getElementById('statError').innerText = "0";
            document.getElementById('statOther').innerText = "0";
            
            // İstasyonları sırayla (sistemi yormadan) tarıyoruz
            for (let code of codes) {
                if (iptalIstegi) {
                    break; // İptal butonuna basıldıysa döngüyü kır
                }
                current++;
                btn.innerHTML = `⏳ Taranıyor (${current}/${total})...`;
                
                try {
                    let response = await pywebview.api.analyze_station(code, d, m, y);
                    if (response.color && markers[code]) {
                        let newIcon = L.divIcon({
                            className: 'custom-pin',
                            html: `<div style="background-color: ${response.color}; width: 26px; height: 26px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; color: white; font-size: 9px; font-weight: bold;">${code}</div>`,
                            iconSize: [26, 26],
                            iconAnchor: [13, 13]
                        });
                        markers[code].setIcon(newIcon);
                        
                        // Renge göre anlık istatistikleri güncelle
                        if (response.color === "#D32F2F") { cError++; document.getElementById('statError').innerText = cError; }
                        else if (response.color === "#2E7D32") { cSuccess++; document.getElementById('statSuccess').innerText = cSuccess; }
                        else { cOther++; document.getElementById('statOther').innerText = cOther; }
                        
                        // Pin'e tıklanırsa sonucun görünmesi için Popup içeriğini arka planda güncelle
                        let stName = globalStations[code].name;
                        let newPopupHTML = `<div style='text-align:center;'><b>${code} - ${stName}</b><br><br><button style='padding:5px 15px; cursor:pointer; background:#0277BD; color:white; border:none; border-radius:4px;' onclick='analizIstek("${code}")'>Tekrar Analiz Et</button></div><div id='res_${code}' style='margin-top:10px;'>${response.html}</div>`;
                        markers[code].setPopupContent(newPopupHTML);
                    }
                } catch(e) {
                    console.error("Hata: " + code, e);
                }
            }
            
            if (iptalIstegi) {
                btn.innerHTML = "🚫 İPTAL EDİLDİ";
                btn.style.backgroundColor = "#D32F2F";
                btn.style.color = "white";
            } else {
                btn.innerHTML = "✅ TARAMA TAMAMLANDI";
                btn.style.backgroundColor = "#00E676";
                btn.style.color = "#121212";
            }
            
            if (btnCancel) btnCancel.style.display = "none";
            
            setTimeout(() => { 
                btn.innerHTML = "🌍 TÜMÜNÜ ANALİZ ET"; 
                btn.style.backgroundColor = "#00E676";
                btn.style.color = "#121212";
                btn.disabled = false; 
            }, 3000);
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    try:
        api = HaritaAnalizApi()
        webview.create_window('Kardelen Etkileşimli Harita Analizi', html=HTML_TEMPLATE, js_api=api, width=1280, height=800)
        webview.start(debug=True)
    except Exception as e:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Harita Çöktü", f"Web Harita başlatılırken kritik bir hata oluştu:\n\n{traceback.format_exc()}")
        sys.exit(1)