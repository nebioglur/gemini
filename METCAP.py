import warnings
warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import geopandas as gpd
import math
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import io
import tkinter as tk
import matplotlib.colors as mcolors
from tkinter import messagebox
import webbrowser
import logging

def get_metar_data(hours=6):
    # Veri kaybını önlemek için Avrupa'yı iki parça halinde çekiyoruz (Batı ve Doğu)
    regions = [
        "-50,15,20,80", # Batı Avrupa (Genişletildi)
        "10,15,70,80"   # Doğu Avrupa ve Ortadoğu (Genişletildi)
    ]
    
    all_data = []
    for bbox in regions:
        url = f"https://aviationweather.gov/api/data/metar?format=json&hours={hours}&bbox={bbox}"
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            chunk = r.json()
            if isinstance(chunk, list):
                all_data.extend(chunk)
        except Exception as e:
            logging.error(f"Bölge verisi alınamadı ({bbox}): {e}")

    df = pd.DataFrame(all_data)
    
    # ---------------------------
    # YEDEK KAYNAK (CSV CACHE)
    # ---------------------------
    # Eşik 1000 yapıldı. Sadece Türkiye geldiyse Avrupa eksik demektir -> Yedeği kullan.
    if df.empty or len(df) < 1000:
        logging.warning(f"API verisi yetersiz ({len(df)} istasyon), yedek kaynak (CSV Cache) devreye giriyor...")
        try:
            csv_url = "https://aviationweather.gov/data/cache/metars.cache.csv"
            headers = {'User-Agent': 'Mozilla/5.0'}
            r_csv = requests.get(csv_url, headers=headers, timeout=60)
            
            if r_csv.status_code == 200:
                # Header satırını dinamik bul (raw_text ile başlayan satır)
                csv_text = r_csv.text
                skip_rows = 5 # Varsayılan
                for i, line in enumerate(csv_text.splitlines()[:30]):
                    if "raw_text" in line and "station_id" in line:
                        skip_rows = i
                        break

                df_csv = pd.read_csv(io.StringIO(csv_text), skiprows=skip_rows)
                # Sütun isimlerindeki boşlukları temizle
                df_csv.columns = [c.strip() for c in df_csv.columns]
                
                # Sütunları bizim formatımıza çevir
                rename_map = {
                    "station_id": "icaoId", "latitude": "lat", "longitude": "lon",
                    "temp_c": "temp", "dewpoint_c": "dewpt", "wind_speed_kt": "wspd",
                    "wind_dir_degrees": "wdir", "visibility_statute_mi": "visibility",
                    "altim_in_hg": "altim", "observation_time": "reportTime",
                    "wx_string": "wxString",
                    "raw_text": "rawOb"
                }
                df_csv = df_csv.rename(columns=rename_map)
                
                # Sütun kontrolü (KeyError önlemek için)
                if "lon" in df_csv.columns and "lat" in df_csv.columns:
                    # Avrupa ve çevresini filtrele
                    df_csv = df_csv[
                        (df_csv["lon"] >= -50) & (df_csv["lon"] <= 70) &
                        (df_csv["lat"] >= 15) & (df_csv["lat"] <= 80)
                    ]
                    
                    df = df_csv.copy()
                    logging.info(f"Yedek kaynaktan {len(df)} istasyon verisi çekildi.")
                else:
                    logging.error(f"Yedek kaynak sütun hatası. Mevcut sütunlar: {list(df_csv.columns)}")
        except Exception as e:
            logging.error(f"Yedek kaynak hatası: {e}")
            
    if df.empty: return pd.DataFrame()

    # Harita için lat/lon gerekli, ayrıca eksik sütun kontrolü
    cols = ['icaoId', 'lat', 'lon', 'temp', 'dewpt', 'wspd', 'wdir', 'visibility', 'reportTime', 'altim', 'wxString', 'rawOb']
    
    df = df.copy() # SettingWithCopyWarning önlemi
    
    for c in cols:
        if c not in df.columns:
            df[c] = None
            
    df = df[cols].copy()
    # Sayısal dönüşüm
    for c in ['lat', 'lon', 'temp', 'dewpt', 'wspd', 'wdir', 'visibility', 'altim']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
        
    # En güncel veriyi tut
    if "reportTime" in df.columns:
        df = df.sort_values("reportTime")
        df = df.drop_duplicates(subset="icaoId", keep="last")
        
    df = df.dropna(subset=['icaoId', 'lat', 'lon'])

    return df

def run_metcap_map():
    # ---------------------------
    # HARİTA AYARLARI
    # ---------------------------
    fig = plt.figure(figsize=(14, 9))
    try:
        manager = plt.get_current_fig_manager()
        manager.window.state('zoomed')
    except: pass
    
    ax = plt.axes()
    
    # Alan seçimi (Batı Avrupa'yı da kapsayacak şekilde)
    min_lon, max_lon = -40, 60
    min_lat, max_lat = 20, 75
    ax.set_xlim([min_lon, max_lon])
    ax.set_ylim([min_lat, max_lat])
    
    mean_lat = (min_lat + max_lat) / 2.0
    ax.set_aspect(1 / math.cos(math.radians(mean_lat)))
    ax.set_facecolor('#9e9e9e') # Ocean

    # Geopandas ile Dünya Haritası Çizimi (Cartopy iptal edildi)
    try:
        try:
            world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
        except AttributeError:
            url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
            world = gpd.read_file(url)
        world.plot(ax=ax, color='#e0e0e0', edgecolor='#424242', linewidth=0.6)
    except Exception as e:
        logging.error(f"Geopandas dünya haritası yükleme hatası: {e}")

    # Türkiye İl Sınırları
    try:
        turkey = gpd.read_file("https://raw.githubusercontent.com/cihadturhan/tr-geojson/master/geo/tr-cities-utf8.json")
        turkey.plot(ax=ax, facecolor='none', edgecolor='#546E7A', linewidth=0.5, linestyle=':')
    except Exception as e:
        logging.error(f"İl sınırları eklenirken hata: {e}")

    plt.title("Avrupa & Türkiye – Analiz Haritası", fontsize=14)

    # ---------------------------
    # VERİLERİ ÇEK VE HARİTAYA İŞLE
    # ---------------------------
    df = get_metar_data(hours=6)
    sc = None

    if not df.empty:
        # 1. İZOBARLAR (Basınç)
        pres_df = df.dropna(subset=["altim", "lat", "lon"]).copy()
        if not pres_df.empty and len(pres_df) > 3:
            if pres_df["altim"].mean() < 200:
                pres_df["altim"] = pres_df["altim"] * 33.8639
                
            p_min = int(pres_df["altim"].min())
            p_max = int(pres_df["altim"].max())
            start_level = p_min - (p_min % 4)
            levels = np.arange(start_level, p_max + 5, 4)
            
            try:
                cs = ax.tricontour(
                    pres_df["lon"], pres_df["lat"], pres_df["altim"],
                    levels=levels, colors="#37474F", linewidths=0.8, zorder=4, alpha=0.8
                )
                ax.clabel(cs, inline=True, fontsize=8, fmt='%1.0f', colors="#37474F")
            except Exception as e:
                logging.error(f"İzobar hatası: {e}")

        # 2. SICAKLIK (Renkli Noktalar)
        t_vals = df["temp"]
        vmin, vmax = t_vals.min(), t_vals.max()
        if pd.isna(vmin): vmin, vmax = -10, 30
        if vmin >= 0: vmin = -0.1
        if vmax <= 0: vmax = 0.1
        norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)

        sc = ax.scatter(
            df["lon"], df["lat"], c=t_vals, cmap="seismic", norm=norm, s=25,
            edgecolors="black", linewidths=0.3, zorder=5, picker=5
        )
        plt.colorbar(sc, pad=0.02, label="Sıcaklık (°C)")
        wind_df = df.dropna(subset=["wspd", "wdir"])
        if not wind_df.empty:
            u = -wind_df["wspd"] * np.sin(np.deg2rad(wind_df["wdir"]))
            v = -wind_df["wspd"] * np.cos(np.deg2rad(wind_df["wdir"]))
            ax.barbs(wind_df["lon"], wind_df["lat"], u, v, length=5, linewidth=0.6, zorder=6)

        # FIRTINA UYARISI (>25kt)
        storm_df = df[df["wspd"] > 25]
        if not storm_df.empty:
            ax.scatter(storm_df["lon"], storm_df["lat"], c='yellow', marker='^', s=60, edgecolors='red', linewidths=1.5, zorder=8)

        # 4. YAĞIŞ VE HADİSELER (RA, SN, TS)
        if "wxString" in df.columns:
            ts_df = df[df["wxString"].str.contains("TS", na=False)]
            if not ts_df.empty: ax.scatter(ts_df["lon"], ts_df["lat"], c='red', marker='P', s=45, edgecolors='black', linewidths=0.5, zorder=7)
            
            sn_df = df[df["wxString"].str.contains("SN", na=False) & ~df["wxString"].str.contains("TS", na=False)]
            if not sn_df.empty: ax.scatter(sn_df["lon"], sn_df["lat"], c='cyan', marker='*', s=55, edgecolors='blue', linewidths=0.3, zorder=7)
            
            ra_df = df[df["wxString"].str.contains("RA", na=False) & ~df["wxString"].str.contains("TS|SN", na=False)]
            if not ra_df.empty: ax.scatter(ra_df["lon"], ra_df["lat"], c='blue', marker='.', s=25, zorder=6)

            sh_df = df[df["wxString"].str.contains("SH", na=False) & ~df["wxString"].str.contains("TS|SN|RA", na=False)]
            if not sh_df.empty: ax.scatter(sh_df["lon"], sh_df["lat"], c='green', marker='v', s=25, edgecolors='black', linewidths=0.3, zorder=6)

            fg_br_df = df[df["wxString"].str.contains("FG|BR", na=False) & ~df["wxString"].str.contains("TS|SN|RA|SH", na=False)]
            if not fg_br_df.empty: ax.scatter(fg_br_df["lon"], fg_br_df["lat"], c='gray', marker='s', s=15, alpha=0.8, edgecolors='black', linewidths=0.3, zorder=4)

        update_time = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
        plt.figtext(0.02, 0.02, f"Güncelleme: {update_time}", ha="left", fontsize=9, bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
    else:
        logging.warning("Veri alınamadı veya boş döndü.")

    # ---------------------------
    # ÇİFT TIKLAMA İLE ZOOM
    # ---------------------------
    def on_click(event):
        if event.inaxes:
            ax = event.inaxes
            if event.button == 3 and sc is not None:
                cont, ind = sc.contains(event)
                if cont:
                    try:
                        idx = ind["ind"][0]
                        row = df.iloc[idx]
                        icao = row['icaoId']
                        url = f"https://rucsoundings.noaa.gov/gwt/?data_source=GFS&latest=latest&airport={icao}&n_hrs=1"
                        webbrowser.open(url)
                        return
                    except: pass

            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            width = xlim[1] - xlim[0]
            height = ylim[1] - ylim[0]
            factor = None
            
            if event.button == 1 and event.dblclick: factor = 0.5
            elif event.button == 3: factor = 2.0
                
            if factor:
                ax.set_xlim([event.xdata - width * factor / 2, event.xdata + width * factor / 2])
                ax.set_ylim([event.ydata - height * factor / 2, event.ydata + height * factor / 2])
                ax.figure.canvas.draw()

    # ---------------------------
    # TIKLAMA İLE DETAY PENCERESİ
    # ---------------------------
    def on_pick(event):
        if event.artist != sc: return
        ind = event.ind[0]
        try:
            row = df.iloc[ind]
            msg = (f"İstasyon: {row['icaoId']}\nZaman: {row['reportTime']}\n---------------------------\n"
                   f"Sıcaklık: {row['temp']} °C\nÇiy Noktası: {row['dewpt']} °C\n"
                   f"Rüzgar: {row['wdir']}° @ {row['wspd']} kt\nGörüş: {row['visibility']}\n"
                   f"Basınç: {row['altim']}\nHadise: {row.get('wxString', '-')}")
            messagebox.showinfo(f"METAR Detayı - {row['icaoId']}", msg)
        except Exception as e: logging.error(f"Hata: {e}")

    fig.canvas.mpl_connect('pick_event', on_pick)
    fig.canvas.mpl_connect('button_press_event', on_click)
    plt.show()

if __name__ == "__main__":
    run_metcap_map()
