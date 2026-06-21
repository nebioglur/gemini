# turkey_map_module.py
# Bu modül, Türkiye haritası ve ICAO analiz işlevselliğini kapsar.
# Kullanımı: Bir sınıf veya ana uygulamada içe aktarılıp çağrılabilir.
# Örneğin: from turkey_map_module import open_turkey_map
# Ardından: open_turkey_map(parent_window, self_instance, robot_instance, tooltip_manager_instance)

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from datetime import datetime, timedelta, timezone
import re
import pandas as pd
import math
import textwrap
import calendar
import requests
import io
import os
import logging
import tkintermapview
from PIL import Image, ImageTk, ImageDraw, ImageFont
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from kardelen_scraper import KardelenScraper
from veri_isleme import process_data
from log_processor import process_and_analyze_logs, extract_station_code
import file_ops
import gui_utils
import turkey_map_subwindows
import TR_harita
from ayarlar import TURKEY_STATIONS, TURKEY_BORDER, TURKEY_REGIONS, ICAO_TO_WMO
import weather_data_utils
import decoder_lookups

# KISTASLAR
ESIKLER_RUYET = [150, 350, 600, 800, 1500, 3000, 5000]
ESIKLER_TAVAN = [100, 200, 500, 1000, 1500]
ESIKLER_VV = [100, 200, 500, 1000]
KRITIK_HADISELER = {
    'TS': r'(?:\b|(?<=VC))TS', 
    'FZ': r'\bFZ', 
    'FG': r'(?:\b|(?<=VC))FG\b', 
    'SQ': r'\bSQ\b', 
    'FC': r'\bFC\b', 
    'SS': r'(?:\b|(?<=VC))SS\b', 
    'DS': r'(?:\b|(?<=VC))DS\b', 
    'BLSN': r'\bBLSN\b', 
    'DRSN': r'\bDRSN\b', 
    'BLDU': r'\bBLDU\b', 
    'DRDU': r'\bDRDU\b', 
    'BLSA': r'\bBLSA\b', 
    'DRSA': r'\bDRSA\b', 
    'RA': r'(?:\b|(?<=(?<!-)SH)|(?<=TS)|(?<=FZ)|(?<=VC))(?<!-)(?<!RE)RA\b', 
    'SN': r'(?:\b|(?<=(?<!-)SH)|(?<=TS)|(?<=FZ)|(?<=VC))(?<!-)(?<!RE)SN\b', 
    'GR': r'(?:\b|(?<=(?<!-)SH)|(?<=TS)|(?<=VC))(?<!-)GR\b'
}

def open_turkey_map(parent, self_ref, robot, tooltip_manager, initial_type="HEPSİ", initial_date=None):
    """Türkiye haritası ve toplu analiz penceresini açar.
    
    Args:
        parent: Ana pencere (tk.Tk veya tk.Toplevel)
        self_ref: Çağıran sınıfın referansı (self)
        robot: Robot instance for analysis
        tooltip_manager: Tooltip manager instance
    """
    map_win = tk.Toplevel(parent)
    map_win.title("Türkiye Geneli ICAO Analiz Haritası")
    map_win.geometry("1600x900")
    map_win.state('zoomed')  # Tam ekran (Maximized)
    map_win.configure(bg="#000000")
    
    # Üst Bilgi
    tk.Label(map_win, text="TÜRKİYE GENELİ METAR/TAF ANALİZİ", bg="#000000", fg="white", font=("Segoe UI", 14, "bold")).pack(side="top", pady=10)
    
    # OFFLINE Göstergesi (Gizli başlar, bağlantı hatasında görünür)
    lbl_offline = tk.Label(map_win, text="⚠️ OFFLINE", bg="#D32F2F", fg="white", font=("Segoe UI", 12, "bold"), padx=10, pady=5)
    # Not: pack/place yapılmadı, gerektiğinde place ile gösterilecek.

    # Alt Kontrol Paneli (Önce oluşturup alta yapıştırıyoruz - Layout sorunu için)
    ctrl_frame = tk.Frame(map_win, bg="#000000")
    ctrl_frame.pack(side="bottom", fill="x", padx=2, pady=2)
    
    # Ana Panel (PanedWindow - 2 Sütunlu Yapı)
    main_paned = tk.PanedWindow(map_win, orient=tk.HORIZONTAL, bg="#000000", sashwidth=4, sashrelief="raised")
    main_paned.pack(side="top", fill="both", expand=True, padx=5, pady=5)

    # SOL PANEL: Harita
    canvas_frame = tk.Frame(main_paned, bg="#000000", bd=2, relief="sunken")
    main_paned.add(canvas_frame, minsize=600, stretch="always")

    # --- İNTERAKTİF LEAFLET HARİTASI (VARSAYILAN) ---
    map_widget = tkintermapview.TkinterMapView(canvas_frame, corner_radius=0)
    map_widget.pack(fill="both", expand=True)
    # CartoDB Voyager açık tema OSM altlığı
    map_widget.set_tile_server("https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png", max_zoom=19)
    map_widget.set_position(39.0, 35.0)  # Türkiye merkez
    map_widget.set_zoom(6)
    
    # Tekerlek ile zoom yapmayı devre dışı bırak (İstasyonların kayma/titreme hissini önler)
    map_widget.canvas.unbind("<MouseWheel>")
    map_widget.canvas.unbind("<Button-4>")
    map_widget.canvas.unbind("<Button-5>")

    # SAĞ PANEL: Anlık Uyarı Listesi
    right_panel = tk.Frame(main_paned, bg="#000000", bd=2, relief="sunken")
    # Başlangıçta eklemiyoruz (Tam ekran harita için)

    tk.Label(right_panel, text="ANLIK UYARI LİSTESİ", bg="#000000", fg="#FF5252", font=("Segoe UI", 11, "bold")).pack(pady=5, fill="x")

    cols_alarm = ("Kod", "Durum")
    tree_alarm = ttk.Treeview(right_panel, columns=cols_alarm, show="headings", height=20)
    tree_alarm.heading("Kod", text="İSTASYON")
    tree_alarm.heading("Durum", text="DURUM")
    
    tree_alarm.column("Kod", width=70, anchor="center")
    tree_alarm.column("Durum", width=150, anchor="center")
    
    sb_alarm_y = ttk.Scrollbar(right_panel, orient="vertical", command=tree_alarm.yview)
    tree_alarm.configure(yscrollcommand=sb_alarm_y.set)
    sb_alarm_y.pack(side="right", fill="y")
    tree_alarm.pack(fill="both", expand=True)
    
    # Liste Renkleri
    tree_alarm.tag_configure('UYUMSUZ', background='#FF1744', foreground='white')
    tree_alarm.tag_configure('F_UYUMSUZ', background='#FFEA00', foreground='black')
    tree_alarm.tag_configure('DIKKAT', background='#FFEB3B', foreground='black')
    tree_alarm.tag_configure('TREND_YOK', background='#FF9800', foreground='black')
    
    lbl_map_status = tk.Label(ctrl_frame, text="Hazır.", bg="#000000", fg="#B0BEC5", font=("Segoe UI", 9))
    lbl_map_status.pack(side="left")
    
    now = datetime.now()
    AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    
    btn_start = tk.Button(ctrl_frame, text="BAŞLAT", bg="#00E676", fg="black", font=("Segoe UI", 8, "bold"), width=7)
    btn_start.pack(side="left", padx=2)
    
    # Durdur Butonu
    stop_scan_flag = threading.Event()
    def stop_scan():
        stop_scan_flag.set()
        if lbl_map_status.winfo_exists():
            lbl_map_status.config(text="Durduruluyor...", fg="#FF5252")
    
    btn_stop = tk.Button(ctrl_frame, text="DURDUR", command=stop_scan, bg="#FF5252", fg="white", font=("Segoe UI", 8, "bold"), width=7, state="disabled")
    btn_stop.pack(side="left", padx=2)

    # Liste Aç/Kapa Butonu
    is_list_open = [False]
    def toggle_list():
        if is_list_open[0]:
            main_paned.forget(right_panel)
            is_list_open[0] = False
            btn_toggle_list.config(bg="#455A64", fg="white")
        else:
            main_paned.add(right_panel, minsize=240, stretch="never")
            is_list_open[0] = True
            btn_toggle_list.config(bg="#00E676", fg="black")
    
    btn_toggle_list = tk.Button(ctrl_frame, text="LİSTE", command=toggle_list, bg="#455A64", fg="white", font=("Segoe UI", 8, "bold"), width=6)
    btn_toggle_list.pack(side="right", padx=5)

    # TAF Süresi Seçimi
    tk.Label(ctrl_frame, text="Süre:", bg="#000000", fg="white", font=("Segoe UI", 8)).pack(side="right", padx=(2, 1))
    cb_taf_duration = ttk.Combobox(ctrl_frame, values=["3", "6", "9", "12", "24"], state="readonly", width=3)
    cb_taf_duration.current(0)
    cb_taf_duration.pack(side="right", padx=1)
    
    # Auto Refresh (1dk)
    var_map_auto = tk.BooleanVar(value=True)
    def map_auto_loop():
        if var_map_auto.get():
            try:
                if map_win.winfo_exists():
                    if btn_start['state'] != 'disabled':
                        run_scan()
                    map_win.after(60000, map_auto_loop)  # 1 dakika
            except: pass
    
    def toggle_map_auto():
        if var_map_auto.get(): map_auto_loop()
    chk_map_auto = tk.Checkbutton(ctrl_frame, text="Oto. Yenile (1dk)", variable=var_map_auto, command=toggle_map_auto, bg="#000000", fg="white", selectcolor="#000000", activebackground="#000000", activeforeground="white", font=("Segoe UI", 10))
    chk_map_auto.pack(side="right", padx=10)
    
    # Filtre Combobox'ı
    tk.Label(ctrl_frame, text="Filtre:", bg="#000000", fg="white", font=("Segoe UI", 10)).pack(side="left", padx=(20, 5))
    cb_map_filter = ttk.Combobox(ctrl_frame, values=["HEPSİ", "❌ UYUMSUZ", "⚠️ DİKKAT", "✅ UYUMLU", "🔸 TREND YOK", "🟣 SİNOPTİK", "⚪ RASAT YOK", "🕒 SON 1 SAAT"], state="readonly", width=15)
    cb_map_filter.current(0)
    cb_map_filter.pack(side="left")

    # --- MOD SEÇİMİ ---
    frame_mode = tk.Frame(ctrl_frame, bg="#000000")
    frame_mode.pack(side="left", padx=10)
    var_map_mode = tk.StringVar(value="TAF/METAR Analiz")

    tk.Label(frame_mode, text="Mod:", bg="#000000", fg="white", font=("Segoe UI", 10)).pack(side="left", padx=2)
    
    mode_map = {"METAR / TAF": "TAF/METAR Analiz", "SİNOPTİK": "Sinoptik Harita", "HEPSİ": "Tümü"}
    
    def on_mode_combobox_change(event):
        selected = cb_mode.get()
        val = mode_map.get(selected, "TAF/METAR Analiz")
        var_map_mode.set(val)
        on_mode_change()
        refresh_markers()

    cb_mode = ttk.Combobox(frame_mode, values=list(mode_map.keys()), state="readonly", width=12)
    cb_mode.set("METAR / TAF")
    cb_mode.pack(side="left", padx=2)
    cb_mode.bind("<<ComboboxSelected>>", on_mode_combobox_change)

    def on_mode_change():
        mode = var_map_mode.get()

        # Analiz moduna özel butonları göster/gizle
        if mode == "Sinoptik Harita":
            btn_score.pack_forget()
            cb_map_filter.config(values=["HEPSİ"])
        else: # TAF/METAR ve Tümü modları
            if not btn_score.winfo_ismapped():
                btn_score.pack(side="left", padx=10)
            cb_map_filter.config(values=["HEPSİ", "❌ UYUMSUZ", "⚠️ DİKKAT", "✅ UYUMLU", "🔸 TREND YOK", "🟣 SİNOPTİK", "⚪ RASAT YOK", "🕒 SON 1 SAAT"])
        
        cb_map_filter.set("HEPSİ")

    # GEÇMİŞ HATALAR BUTONU VE FONKSİYONU
    def open_history_window_wrapper():
        turkey_map_subwindows.open_history_window(map_win, self_ref)
        
    # TAF SKOR BUTONU VE FONKSİYONU
    def open_score_window_wrapper():
        turkey_map_subwindows.open_score_window(map_win, self_ref)
        
    btn_score = tk.Button(ctrl_frame, text="TAF SKOR", command=open_score_window_wrapper, bg="#7E57C2", fg="white", font=("Segoe UI", 10, "bold"))
    btn_score.pack(side="left", padx=10)
    
    # AYARLAR PENCERESİ
    def open_settings_window_wrapper():
        turkey_map_subwindows.open_settings_window(map_win, robot)
        
    btn_settings = tk.Button(ctrl_frame, text="AYAR", command=open_settings_window_wrapper, bg="#607D8B", fg="white", font=("Segoe UI", 8, "bold"))
    btn_settings.pack(side="left", padx=5)

    station_markers = {}
    station_colors = {}
    map_results = {}  # Detaylı verileri sakla
    
    def open_folium_map():
        try:
            import folium
            import webbrowser
            import os

            # 🌍 MODERN HARİTA
            m = folium.Map(
                location=[39.0, 35.0],
                zoom_start=6,
                tiles="CartoDB positron",  # 🔥 modern açık tema
                prefer_canvas=True # 🔥 Daha hızlı render için (Web 3D)
            )

            def get_color(status):
                status = str(status).upper()

                if "UYUMSUZ" in status:
                    return "#FF0000"
                elif "DİKKAT" in status:
                    return "#FFEA00"
                elif "UYUMLU" in status:
                    return "#00FF00"
                elif "TREND" in status:
                    return "#fb923c"
                else:
                    return "#94a3b8"

            for code, info in TURKEY_STATIONS.items():
                data = map_results.get(code, {})
                status = data.get('status_msg', 'VERİ YOK')
                source = data.get('source', 'KARDELEN')

                # 🔥 VERİ YOK olanları haritaya ekleme (Hızlandırır ve kalabalığı önler)
                if status == 'VERİ YOK':
                    continue
                    
                lat, lon = info['lat'], info['lon']
                name = info.get('name', '')
                
                # HTML içindeki satır atlamalarını güvenli hale getir
                metar = str(data.get('metar', '-')).replace('\n', '<br>')
                taf = str(data.get('taf', '-')).replace('\n', '<br>')

                color = get_color(status)
                is_backup = source in ['AWC', 'OGIMET']
                border_color = "#FF9800" if is_backup else "white"

                reasons_html = ""
                reasons = data.get('reasons', [])
                if reasons and ("UYUMSUZ" in status or "DİKKAT" in status):
                    reasons_html = "<b>Nedenler:</b><ul style='margin-top:2px; margin-bottom:10px; padding-left:20px;'>"
                    for r in reasons:
                        color_li = "#ef4444" if "UYUMSUZ" in status else "#f59e0b"
                        reasons_html += f"<li style='color:{color_li};'>{r}</li>"
                    reasons_html += "</ul>"

                # 🧠 MODERN POPUP
                popup_html = f"""
                <div style="font-family: Arial; font-size: 13px;">
                    <h4 style="margin-bottom:5px;">{code} - {name}</h4>
                    <b>Durum:</b> {status}<br><br>
                    <b>Veri Kaynağı:</b> {source}<br><br>
                    {reasons_html}

                    <b>METAR:</b><br>
                    <div style="color:#374151;">{metar}</div><br>

                    <b>TAF:</b><br>
                    <div style="color:#374151;">{taf}</div>
                </div>
                """

                icon_html = f"""
                <div style="position: relative; width: 32px; height: 32px;">
                    <div style="
                        background-color: {color};
                        border: 2px solid {border_color};
                        border-radius: 50%;
                        width: 100%; height: 100%;
                        display: flex; align-items: center; justify-content: center;
                        font-size: 10px; font-weight: bold; letter-spacing: -0.5px;
                        color: {'#000000' if color in ['#00FF00', '#FFEA00', '#fb923c'] else '#FFFFFF'};
                        box-shadow: 0px 2px 4px rgba(0,0,0,0.5);
                        box-sizing: border-box;
                    ">{code}</div>
                    {'<div style="position:absolute; top:-2px; right:-2px; width:10px; height:10px; background-color:#2196F3; border:1px solid white; border-radius:50%;" title="Yedek Veri Kaynağı"></div>' if is_backup else ''}
                </div>
                """

                folium.Marker(
                    location=[lat, lon],
                    icon=folium.DivIcon(html=icon_html, icon_size=(32, 32), icon_anchor=(16, 16)),
                    popup=folium.Popup(popup_html, max_width=320),
                    tooltip=f"{code} - {status}"
                ).add_to(m)

            # 📌 LEGEND (HARİTA ÜZERİ)
            legend_html = """
            <div style="
                position: fixed; 
                bottom: 40px; left: 40px; width: 220px; 
                background-color: white; 
                border:2px solid #ccc; 
                z-index:9999; 
                font-size:16px;
                padding:15px;
                border-radius:8px;
                line-height: 1.6;
            ">
            <b style="font-size:18px;">DURUM</b><br>
            <i style="color:#00FF00; font-size:22px; vertical-align: middle;">●</i> UYUMLU<br>
            <i style="color:#FFEA00; font-size:22px; vertical-align: middle;">●</i> DİKKAT<br>
            <i style="color:#FF0000; font-size:22px; vertical-align: middle;">●</i> UYUMSUZ<br>
            <i style="color:#fb923c; font-size:22px; vertical-align: middle;">●</i> TREND YOK<br>
            <i style="color:#94a3b8; font-size:22px; vertical-align: middle;">●</i> VERİ YOK
            </div>
            """
            m.get_root().html.add_child(folium.Element(legend_html))

            # 💾 KAYDET
            log_dir = os.path.join(os.path.expanduser("~"), "KardelenLogs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            out_path = os.path.join(log_dir, "Kardelen_Modern_Harita.html")
            m.save(out_path)

            # 🌐 AÇ
            # Windows tarayıcılarının yolu doğru algılaması için file:/// formatına çevrilir
            file_url = f"file:///{out_path.replace(os.sep, '/')}"
            webbrowser.open(file_url)

        except ImportError:
            messagebox.showerror("Hata", "Folium kütüphanesi bulunamadı.\nLütfen terminalden 'pip install folium' komutunu çalıştırın.")
        except Exception as e:
            messagebox.showerror("Hata", f"Harita oluşturulurken bir hata oluştu: {e}")

    btn_folium = tk.Button(ctrl_frame, text="🌐 WEB HARİTA (3D)", command=open_folium_map, bg="#0288D1", fg="white", font=("Segoe UI", 9, "bold"))
    btn_folium.pack(side="left", padx=5)
    
    def show_detail(code):
        if code not in map_results:
            gui_utils.show_auto_close_info(map_win, f"{code}", "Detaylı veri bulunamadı.", 2000)
            return
        data = map_results[code]
        
        # Ana ekrandaki gelişmiş detay penceresini kullan (dış fonksiyon çağrısı varsayalım)
        gui_utils.show_detail_window(
            parent=map_win,
            station=code,
            date=data.get('date', ''),
            metar_text=data.get('metar', ''),
            taf_text=data.get('taf', ''),
            analysis_detail=data.get('detail', ''),
            fm_start_idx=0,  # Harita taramasında FM analizi basitleştirildiği için 0
            metar_dt=data.get('metar_dt', datetime.now()),
            robot_instance=robot
        )

    def on_alarm_double_click(event):
        item = tree_alarm.selection()
        if not item: return
        code = tree_alarm.item(item, "values")[0]
        show_detail(code)

    tree_alarm.bind("<Double-1>", on_alarm_double_click)

    def update_alarm_list(code, status, time_str):
        if not map_win.winfo_exists(): return
        
        tag = ""
        if "F/UYUMSUZ" in status: tag = "F_UYUMSUZ"
        elif "UYUMSUZ" in status: tag = "UYUMSUZ"
        elif "DİKKAT" in status: tag = "DIKKAT"
        elif "TREND YOK" in status: tag = "TREND_YOK"
        
        if tag:
             # Varsa sil (Güncelleme için)
             for item in tree_alarm.get_children():
                 if tree_alarm.item(item, "values")[0] == code:
                     tree_alarm.delete(item)
                     break
             # En üste ekle
             tree_alarm.insert("", 0, values=(code, status), tags=(tag,))
    
    # Marker İkon Ön Belleği (Varsayılan devasa iğne yerine daha küçük dairesel ikonlar için)
    icon_cache = {}
    def get_circle_icon(color_hex, code, is_backup=False):
        cache_key = (color_hex, code, is_backup)
        if cache_key not in icon_cache:
            size = 32  # Kodun sığacağı optimum boyut (Büyütüldü)
            img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            border_color = "#FF9800" if is_backup else "#FFFFFF"
            draw.ellipse((1, 1, size-2, size-2), fill=color_hex, outline=border_color, width=2)
            
            try: font = ImageFont.truetype("arialbd.ttf", 10)
            except: font = ImageFont.load_default()
            
            bbox = draw.textbbox((0, 0), code, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            
            text_col = "#000000" if color_hex in ["#00FF00", "#FFEA00", "#FF9800", "#66BB6A", "#FFEE58"] else "#FFFFFF"
            draw.text(((size - tw) / 2.0, (size - th) / 2.0 - 1), code, fill=text_col, font=font)
            
            if is_backup:
                # Mavi renkli ufak nokta (Verinin AWC/Ogimet'ten geldiğini belirtmek için)
                draw.ellipse((size-10, 0, size-2, 8), fill="#2196F3", outline="#FFFFFF", width=1)

            icon_cache[cache_key] = ImageTk.PhotoImage(img)
        return icon_cache[cache_key]

    def refresh_markers(event=None):
        """Filtrelere göre haritayı Leaflet (tkintermapview) üzerinde tazeler."""
        map_widget.delete_all_marker()
        station_markers.clear()

        mode = var_map_mode.get()
        filter_mode = cb_map_filter.get()
        
        for code, info in sorted(TURKEY_STATIONS.items()):
            st_type = info.get('type', 'MEYDAN')
            
            # MOD FİLTRESİ
            if mode == "TAF/METAR Analiz" and st_type != "MEYDAN": continue
            if mode == "Sinoptik Harita" and st_type != "SİNOPTİK": continue
            
            fill_color = station_colors.get(code, "#78909C")
            if st_type == "SİNOPTİK" and code in map_results:
                temp = map_results[code].get('temp')
                temps = [res['temp'] for res in map_results.values() if res.get('temp') is not None]
                vmin, vmax = (min(temps) if temps else -10), (max(temps) if temps else 30)
                norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
                cmap = plt.get_cmap('seismic')
                if temp is not None: fill_color = mcolors.to_hex(cmap(norm(temp)))
                
            # Durum Filtrelerini Uygula
            if filter_mode != "HEPSİ":
                if filter_mode == "❌ UYUMSUZ" and fill_color not in ["#EF5350", "#FF0000"]: continue
                elif filter_mode == "⚠️ DİKKAT" and fill_color not in ["#FFEE58", "#FFEA00"]: continue
                elif filter_mode == "✅ UYUMLU" and fill_color not in ["#66BB6A", "#00FF00"]: continue
                elif filter_mode == "🔸 TREND YOK" and fill_color != "#FF9800": continue
                elif filter_mode == "⚪ RASAT YOK" and fill_color not in ["#455A64", "#78909C", "#90A4AE"]: continue
                elif filter_mode == "🕒 SON 1 SAAT":
                    if code not in map_results: continue
                    m_data = map_results[code]
                    if 'metar_dt' not in m_data: continue
                    if (datetime.now(timezone.utc).replace(tzinfo=None) - m_data['metar_dt']).total_seconds() > 5400: continue
                
            is_backup = False
            if code in map_results:
                if map_results[code].get('source') in ['AWC', 'OGIMET']: is_backup = True

            marker_icon = get_circle_icon(fill_color, code, is_backup)

            # Haritaya iğneyi (Marker) ekle ve Click (Tıklama) olayını show_detail'e bağla
            m = map_widget.set_marker(
                info['lat'], info['lon'],
                icon=marker_icon,
                command=lambda marker, c=code: show_detail(c)
            )
            station_markers[code] = m
            
    cb_map_filter.bind("<<ComboboxSelected>>", refresh_markers)
    
    def run_scan():
        if btn_start['state'] == 'disabled': return
        # Alarm listesini temizle
        for item in tree_alarm.get_children(): tree_alarm.delete(item)
        
        btn_start.config(state="disabled")
        btn_stop.config(state="normal")
        stop_scan_flag.clear()
        try:
            th = int(cb_taf_duration.get())
        except: th = 3
        
        # Tarih belirle (UTC bazlı)
        dt_now = datetime.now(timezone.utc)
        
        # Oto yenileme açıksa güncel tarihi kullan (Gece yarısı geçişi için), yoksa seçili tarihi koru
        if var_map_auto.get():
            sel_g = str(dt_now.day).zfill(2)
            sel_a = AYLAR[dt_now.month - 1]
            sel_y = str(dt_now.year)
        elif initial_date:
            sel_g = initial_date.get("day", str(dt_now.day).zfill(2))
            sel_a = initial_date.get("month", AYLAR[dt_now.month - 1])
            sel_y = initial_date.get("year", str(dt_now.year))
        else:
            sel_g = str(dt_now.day).zfill(2)
            sel_a = AYLAR[dt_now.month - 1]
            sel_y = str(dt_now.year)
            
        sel_saat = "SON"
        
        mode = var_map_mode.get()
        threading.Thread(target=scan_worker, args=(th, sel_g, sel_a, sel_y, sel_saat, mode), daemon=True).start()
    
    def scan_worker(taf_hours, s_gun, s_ay, s_yil, s_saat, mode):
        # Seçili tarih üzerinden işlem yap
        # now = datetime.now(timezone.utc).replace(tzinfo=None) # Eski kod
        
        incompatible_list = []
        map_incompatible_rows = []
        calculated_scores = [] # Skor listesi
        total = len(TURKEY_STATIONS)
        map_data_store = {} # { 'LTAN': {'tafs': [], 'metars': []} }

        # --- SİNOPTİK TARAMASI ---
        if mode in ["Sinoptik Harita", "Tümü"]:
            map_win.after(0, lambda: lbl_map_status.config(text="Sinoptik veriler taranıyor...", fg="#64B5F6") if lbl_map_status.winfo_exists() else None)
            scraper = KardelenScraper()
            
            sinoptik_stations = {k:v for k,v in TURKEY_STATIONS.items() if v.get('type') == 'SİNOPTİK'}
            total_synop = len(sinoptik_stations)

            for i, (code, info) in enumerate(sorted(sinoptik_stations.items()), 1):
                if not map_win.winfo_exists() or stop_scan_flag.is_set(): break
                
                map_win.after(0, lambda c=code, idx=i: lbl_map_status.config(text=f"Taranıyor ({idx}/{total_synop}): {c}...", fg="#FFD740") if lbl_map_status.winfo_exists() else None)
                
                wmo_id = ICAO_TO_WMO.get(code)
                if not wmo_id: continue

                scraper.set_station(wmo_id)
                try:
                    logs = []
                    try:
                        logs = scraper.fetch_logs(s_gun, s_ay, s_yil, "3") # Filtre "3" SİNOPTİK için
                    except Exception as sc_err:
                        logging.warning(f"Kardelen SİNOPTİK hatası ({code}): {sc_err}")

                    # --- YEDEK: OGIMET SİNOPTİK ---
                    if not logs:
                        try:
                            map_win.after(0, lambda c=code: lbl_map_status.config(text=f"Yedek (Ogimet Sinoptik): {c}...", fg="#FF9800") if lbl_map_status.winfo_exists() else None)
                            ay_num = AYLAR.index(s_ay) + 1
                            ogi_url = f"https://ogimet.com/cgi-bin/getsynop?block={wmo_id}&begin={s_yil}{ay_num:02d}{int(s_gun):02d}0000"
                            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                            ogi_req = requests.get(ogi_url, headers=headers, timeout=5)
                            if ogi_req.status_code == 200:
                                for line in ogi_req.text.splitlines():
                                    if 'AAXX' in line and str(wmo_id) in line:
                                        bulten = line[line.find('AAXX'):].strip()
                                        dt_str = f"{s_gun}.{s_ay}.{s_yil} 00:00"
                                        logs.append(["SİNOPTİK", "OGIMET", "-", "-", dt_str, bulten])
                        except Exception as e:
                            logging.error(f"Ogimet Synop Hata ({code}): {e}")

                    if logs:
                        # Saat seçimi varsa ilgili saati bul, yoksa en sonuncuyu al
                        target_log = logs[0] # Varsayılan: En son
                        if s_saat != "SON":
                            for log in logs:
                                # log[4] -> Rasat Tarihi (DD.MM.YYYY HH:MM)
                                if f" {s_saat}:" in log[4]:
                                    target_log = log
                                    break
                        
                        latest_log_text = target_log[5]
                        parsed_data = weather_data_utils.parse_synop_report(latest_log_text)
                        
                        dt_str = target_log[4]
                        parsed_data['date'] = dt_str
                        try:
                            parsed_data['metar_dt'] = datetime.strptime(dt_str, "%d.%m.%Y %H:%M") - timedelta(hours=3)
                        except:
                            parsed_data['metar_dt'] = datetime.now()
                        
                        # UI güncellemesi için ana thread'e gönder
                        map_win.after(0, lambda c=code, d=parsed_data: update_station_ui(c, None, "SİNOPTİK", d))
                        map_win.after(0, lambda: lbl_offline.place_forget() if lbl_offline.winfo_exists() else None) # Bağlantı başarılı, gizle
                    else:
                        logging.info(f"Sinoptik veri yok: {code}")
                        # Veri yoksa bile bağlantı başarılı sayılabilir, ancak hata durumunda except bloğu çalışır
                        map_win.after(0, lambda: lbl_offline.place_forget() if lbl_offline.winfo_exists() else None)
                except Exception as e:
                    logging.error(f"Sinoptik tarama hatası ({code}): {e}")
        
        
        # --- TAF/METAR TARAMASI ---
        if mode in ["TAF/METAR Analiz", "Tümü"]:
            # Scraper'ı döngü dışında başlat (Performans ve Session yönetimi için)
            scraper = KardelenScraper()
            
            # --- TOPLU VERİ ÇEKME (METCAP YÖNTEMİ) ---
            bulk_data_cache = {}
            try:
                map_win.after(0, lambda: lbl_map_status.config(text="Toplu veri çekiliyor (AviationWeather)...", fg="#64B5F6") if lbl_map_status.winfo_exists() else None)
                metars, tafs = weather_data_utils.get_bulk_weather_data(hours=24)
                logging.info(f"Bulk Data: {len(metars)} METARs, {len(tafs)} TAFs fetched.")
                
                # METAR'ları İşle
                for m in metars:
                    icao = m.get('icaoId')
                    if not icao: continue
                    raw = m.get('rawOb', '')
                    t_str = m.get('reportTime', '')
                    try:
                        if 'T' in t_str: dt_utc = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                        else: dt_utc = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                        
                        dt_local = (dt_utc + timedelta(hours=3)).replace(tzinfo=None)
                        date_str = dt_local.strftime("%d.%m.%Y %H:%M")
                        
                        if icao not in bulk_data_cache: bulk_data_cache[icao] = []
                        bulk_data_cache[icao].append(("METAR", "-", "-", "-", date_str, raw))
                    except: pass

                # TAF'ları İşle
                for t in tafs:
                    icao = t.get('icaoId')
                    if not icao: continue
                    raw = t.get('rawTAF', '')
                    t_str = t.get('issueTime', '')
                    try:
                        if 'T' in t_str: dt_utc = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                        else: dt_utc = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                        
                        dt_local = (dt_utc + timedelta(hours=3)).replace(tzinfo=None)
                        date_str = dt_local.strftime("%d.%m.%Y %H:%M")
                        
                        if icao not in bulk_data_cache: bulk_data_cache[icao] = []
                        bulk_data_cache[icao].append(("TAF", "-", "-", "-", date_str, raw))
                    except: pass
            except Exception as e: logging.error(f"Bulk fetch error: {e}")

            # Taramayı A'dan Z'ye sıralı yap
            for i, code in enumerate(sorted(TURKEY_STATIONS.keys()), 1):
                if not map_win.winfo_exists() or stop_scan_flag.is_set(): break
                
                st_info = TURKEY_STATIONS[code]
                if st_info.get('type', 'MEYDAN') != 'MEYDAN': continue
                
                try:
                    if not map_win.winfo_exists(): break
                    map_win.after(0, lambda c=code, idx=i: lbl_map_status.config(text=f"Taranıyor ({idx}/{total}): {c}...", fg="#FFD740") if lbl_map_status.winfo_exists() else None)
                except: break
                
                try:
                    logs = []
                    # 1. Toplu Veriden Olanları Ekle
                    if code in bulk_data_cache:
                        logs.extend(bulk_data_cache[code])
                        
                    has_metar = any(l[0] in ["METAR", "SPECI"] for l in logs)
                    has_taf = any(l[0] == "TAF" for l in logs)
                        
                    # 2. METAR veya TAF'tan BİRİ BİLE EKSİKSE Kardelen'e Sor
                    if (not has_metar or not has_taf) and code in ICAO_TO_WMO:
                        wmo_id = ICAO_TO_WMO[code]
                        scraper.set_station(wmo_id)
                        time.sleep(0.05)
                        
                        try:
                            logs = scraper.fetch_logs(s_gun, s_ay, s_yil, "500")
                            if len(logs) < 5:
                                try:
                                    ay_num = AYLAR.index(s_ay) + 1
                                    last_day = calendar.monthrange(int(s_yil), ay_num)[1]
                                    safe_day = min(int(s_gun), last_day)
                                    dt_sel = datetime(int(s_yil), ay_num, safe_day)
                                    yesterday = dt_sel - timedelta(days=1)
                                    logs_y = scraper.fetch_logs(yesterday.day, AYLAR[yesterday.month-1], yesterday.year, "500")
                                    k_logs.extend(logs_y)
                                except: pass
                            if k_logs: logs.extend(k_logs)
                            map_win.after(0, lambda: lbl_offline.place_forget() if lbl_offline.winfo_exists() else None) # Başarılı
                        except Exception as e:
                            # Hata analizi
                            err_str = str(e)
                            if "Sunucu" in err_str or "bağlanılamadı" in err_str or "Timeout" in err_str:
                                map_win.after(0, lambda: lbl_offline.place(relx=1.0, rely=0.0, anchor="ne", x=-20, y=20) if lbl_offline.winfo_exists() else None)
                            else:
                                # Diğer hatalarda (parse vb) offline demeyelim
                                pass
                    
                    has_metar = any(l[0] in ["METAR", "SPECI"] for l in logs)
                    has_taf = any(l[0] == "TAF" for l in logs)
                    
                    # 3. HALA METAR veya TAF EKSİKSE YEDEK API'LER (AWC & OGIMET) ÇALIŞTIR
                    if not has_metar or not has_taf:
                        try:
                            map_win.after(0, lambda c=code: lbl_map_status.config(text=f"Yedek API'ler (Ogimet/AWC) taranıyor: {c}...", fg="#FF9800") if lbl_map_status.winfo_exists() else None)
                            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                            ay_num = AYLAR.index(s_ay) + 1
                            
                            # 1. Aviation Weather Center (AWC) Single Station
                            try:
                                if not has_metar:
                                    m_url = f"https://aviationweather.gov/api/data/metar?ids={code}&format=json&hours=24"
                                    m_res = requests.get(m_url, headers=headers, timeout=5).json()
                                    for m in m_res:
                                        raw = m.get('rawOb', '')
                                        t_str = m.get('reportTime', '')
                                        dt_utc = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc) if 'T' not in t_str else datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                                        dt_local = (dt_utc + timedelta(hours=3)).replace(tzinfo=None)
                                        logs.append(["METAR", "AWC", "-", "-", dt_local.strftime("%d.%m.%Y %H:%M"), raw])
                                        
                                if not has_taf:
                                    t_url = f"https://aviationweather.gov/api/data/taf?ids={code}&format=json&hours=24"
                                    t_res = requests.get(t_url, headers=headers, timeout=5).json()
                                    for t in t_res:
                                        raw = t.get('rawTAF', '')
                                        t_str = t.get('issueTime', '')
                                        dt_utc = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc) if 'T' not in t_str else datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                                        dt_local = (dt_utc + timedelta(hours=3)).replace(tzinfo=None)
                                        logs.append(["TAF", "AWC", "-", "-", dt_local.strftime("%d.%m.%Y %H:%M"), raw])
                            except Exception as e:
                                logging.warning(f"AWC Backup error {code}: {e}")

                            # 2. Ogimet Fallback
                            has_metar = any(l[0] in ["METAR", "SPECI"] for l in logs)
                            has_taf = any(l[0] == "TAF" for l in logs)
                            if not has_metar or not has_taf:
                                ogi_url = f"https://ogimet.com/display_metars2.php?lang=en&lugar={code}&tipo=ALL&ord=REV&nil=SI&fmt=txt&ano={s_yil}&mes={ay_num:02d}&day={int(s_gun):02d}&ndays=2"
                                ogi_req = requests.get(ogi_url, headers=headers, timeout=5)
                                if ogi_req.status_code == 200:
                                    for line in ogi_req.text.splitlines():
                                        line = line.strip()
                                        if not line: continue
                                        if code in line and ('METAR' in line or 'SPECI' in line or 'TAF' in line or '=' in line):
                                            parts = line.split(maxsplit=2)
                                            if len(parts) >= 3 and len(parts[0]) >= 12 and parts[0][:12].isdigit():
                                                typ = "METAR"
                                                if "TAF" in parts[1]: typ = "TAF"
                                                elif "SPECI" in parts[1]: typ = "SPECI"
                                                bulten = parts[2].strip()
                                                dt_str = f"{s_gun}.{s_ay}.{s_yil} {parts[0][8:10]}:{parts[0][10:12]}"
                                                logs.append([typ, "OGIMET", "-", "-", dt_str, bulten])
                        except Exception as e:
                            logging.error(f"Yedek API hatası {code}: {e}")

                    if not logs: continue

                    # --- VERİ İŞLEME VE ANALİZ ---
                    grouped_data = process_and_analyze_logs(logs, robot)
                    map_color, map_msg, map_detail, st_points = "#455A64", "Veri Yok", None, []
                    
                    all_metars = [obs for g in grouped_data for obs in g['observations'] if obs['type'] in ['METAR', 'SPECI']]
                    all_metars.sort(key=lambda x: x['dt'])
                    
                    temp_error_rows = []
                    for obs in all_metars:
                        analysis = obs.get('analysis')
                        if not analysis: continue
                        
                        durum = analysis['durum']
                        status_msg = analysis.get('display_text', durum)
                        detay_str = "\n".join(analysis.get('reasons', []))
                        
                        has_trend_obs = re.search(r'\b(BECMG|TEMPO|NOSIG)\b', obs['bulten'])
                        is_format_error = "F/UYUMSUZ" in detay_str or "Format Hatası" in detay_str
                        if is_format_error: status_msg = "❌ F/UYUMSUZ"
                        
                        if "UYUMSUZ" in durum: st_points.append(0)
                        elif "DİKKAT" in durum: st_points.append(50)
                        else: st_points.append(100)
                        
                        if "UYUMLU" in durum:
                            temp_error_rows.clear()
                            continue
                        
                        if "UYUMSUZ" in durum or "DİKKAT" in durum:
                            if "UYUMSUZ" in durum and not has_trend_obs and not is_format_error: continue

                            row_data = {
                                "date": obs['tarih_str'], "Türü": obs['type'], "İstasyon": code,
                                "Bülten": obs['bulten'], "_dt": obs['dt'], "KULL.": obs['raw'][1],
                                "GÖND.": obs['raw'][2], "KAYIT TAR.": obs['raw'][3], "_uyum": status_msg,
                                "_detay": detay_str, "_ref_taf": analysis.get('ref_taf', '')
                            }
                            temp_error_rows.append(row_data)

                            # Türkiye Geneli Tarama Sırasında Uyumsuzluk Loglama
                            if "UYUMSUZ" in durum:
                                if hasattr(self_ref, 'log_incompatibility'):
                                    if obs.get('dt') and abs((datetime.now(timezone.utc).replace(tzinfo=None) - obs['dt']).total_seconds()) < 86400:
                                        if not hasattr(self_ref, 'logged_incompatibilities'):
                                            self_ref.logged_incompatibilities = set()
                                        
                                        log_key = f"{code}_{obs['dt'].strftime('%Y%m%d%H%M')}"
                                        if log_key not in self_ref.logged_incompatibilities:
                                            self_ref.logged_incompatibilities.add(log_key)
                                            
                                            reasons_list = analysis.get('reasons', [])
                                            r_str = ", ".join(reasons_list) if reasons_list else "Bilinmeyen Neden"
                                            self_ref.log_incompatibility(
                                                station_name=code,
                                                reason=r_str,
                                                metar_data=obs['bulten'],
                                                taf_data=analysis.get('ref_taf', 'TAF verisi yok')
                                            )
                    
                    map_incompatible_rows.extend(temp_error_rows)

                    if all_metars:
                        last_metar = all_metars[-1]
                        analysis = last_metar.get('analysis')
                        has_trend = re.search(r'\b(BECMG|TEMPO|NOSIG)\b', last_metar['bulten'])

                        if analysis:
                            durum = analysis['durum']
                            if "UYUMSUZ" in durum:
                                is_format = "F/UYUMSUZ" in "\n".join(analysis.get('reasons', [])) or "Format Hatası" in "\n".join(analysis.get('reasons', []))
                                if not has_trend and not is_format:
                                    map_color, map_msg = "#FF9800", "TREND YOK"
                                else:
                                    map_color = "#FF0000"
                                    map_msg = "F/UYUMSUZ" if is_format else "UYUMSUZ"
                                    incompatible_list.append(f"❌ {code}: {map_msg}")
                            elif "DİKKAT" in durum: map_color, map_msg = "#FFEA00", "DİKKAT"
                            elif "TAF YOK" in durum: map_color, map_msg = "#90A4AE", "TAF YOK"
                            else: map_color, map_msg = "#00FF00", "UYUMLU"
                            
                            detay_str = analysis.get('display_text', '') + "\n\n" + "\n".join(analysis.get('reasons', []))
                        else:
                            map_color, map_msg, detay_str = "#90A4AE", "ANALİZ YOK", "Analiz verisi bulunamadı."
                        
                        full_taf = analysis.get('full_taf_text', '') if analysis else ''
                        if not full_taf and analysis: full_taf = analysis.get('ref_taf', '')
                        source_val = last_metar['raw'][1] if 'raw' in last_metar and len(last_metar['raw']) > 1 else ''
                        map_detail = {'metar': last_metar['bulten'], 'taf': full_taf, 'detail': detay_str, 'date': last_metar['tarih_str'], 'metar_dt': last_metar['dt'], 'status_msg': map_msg, 'reasons': analysis.get('reasons', []) if analysis else [], 'source': source_val}

                    if st_points:
                        avg_score = sum(st_points) / len(st_points)
                        calculated_scores.append({'code': code, 'score': avg_score, 'count': len(st_points)})

                    if not map_win.winfo_exists(): return
                    map_win.after(0, lambda c=code, col=map_color, m=map_msg, d=map_detail: update_station_ui(c, col, m, d))
                    
                    t_str = last_metar['dt'].strftime("%H:%M") if 'dt' in last_metar and getattr(last_metar['dt'], 'year', 0) > 1900 else "-"
                    map_win.after(0, lambda c=code, s=map_msg, t=t_str: update_alarm_list(c, s, t))
                    
                except Exception as e: logging.error(f"Scan error {code}: {e}")
        
        map_win.after(0, lambda: finalize_scan(incompatible_list, map_incompatible_rows, calculated_scores))
    
    def update_station_ui(code, color, msg, detail_data=None):
        if not map_win.winfo_exists(): return
        
        if color:
            station_colors[code] = color
            
        if detail_data:
            map_results[code] = detail_data
    
    def finalize_scan(incompatible_list, map_incompatible_rows=None, calculated_scores=None):
        if not map_win.winfo_exists(): return
        
        if btn_start.winfo_exists(): btn_start.config(state="normal")
        if btn_stop.winfo_exists(): btn_stop.config(state="disabled")
        if lbl_map_status.winfo_exists(): lbl_map_status.config(text="Tarama Tamamlandı.", fg="#69F0AE")
        
        if incompatible_list:
            report = "UYUMSUZ RASATLAR TESPİT EDİLDİ:\n\n" + "\n".join(incompatible_list)
            gui_utils.show_auto_close_info(map_win, "Tarama Sonucu", report, 5000)
            
        if map_incompatible_rows:
            try:
                self_ref.add_to_monitor(map_incompatible_rows)
            except: pass
            
        if calculated_scores:
            self_ref.station_scores_list = calculated_scores
            
        # Tarama bittiğinde güncel filtrelerle haritayı yenile
        refresh_markers()
    btn_start.config(command=run_scan)

    # Otomatik Başlat (Pencere açıldıktan kısa süre sonra)
    map_win.after(500, run_scan)
    map_win.after(60000, map_auto_loop)

    # Mod seçimine göre butonları ayarla
    on_mode_change()
    # İlk açılışta siyah/gri marker'ların belirmesi için
    refresh_markers()
    
    # Modülün ana penceresini döndür (isteğe bağlı)
    return map_win