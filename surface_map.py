import matplotlib.pyplot as plt
import math
import pandas as pd
import numpy as np
import os
import matplotlib.colors as mcolors
import threading
import matplotlib.patheffects as path_effects
from METCAP import get_metar_data
import logging

def draw_surface_map():
    
    # Türkiye Koordinatları (turkey_map_hd_v7 ile uyumlu: 25.0-45.0E, 34.0-44.0N)
    min_lon, max_lon = 25.0, 45.0
    min_lat, max_lat = 34.0, 44.0
    extent = [min_lon, max_lon, min_lat, max_lat]

    # Harita Ayarları
    fig = plt.figure(figsize=(14, 8))
    ax = plt.axes()
    
    mean_lat = (min_lat + max_lat) / 2.0
    ax.set_aspect(1 / math.cos(math.radians(mean_lat)))
    ax.set_xlim([min_lon, max_lon])
    ax.set_ylim([min_lat, max_lat])

    # Arkaplan Resmi (turkey_map_hd_v7.png)
    bg_path = os.path.join(os.path.dirname(__file__), "turkey_map_hd_v7.png")
    
    if os.path.exists(bg_path):
        try:
            img = plt.imread(bg_path)
            ax.imshow(img, origin='upper', extent=extent)
        except Exception as e:
            logging.error(f"Resim yükleme hatası: {e}")
            # Resim yoksa varsayılan özellikler
            ax.set_facecolor('lightgray')
    else:
        logging.warning("Arkaplan resmi (turkey_map_hd_v7.png) bulunamadı.")
        ax.set_facecolor('lightgray')

    # Yükleniyor Yazısı
    loading_text = ax.text(0.5, 0.5, "Veriler İndiriliyor...\nLütfen Bekleyiniz...", 
                           transform=ax.transAxes, ha='center', va='center', 
                           fontsize=14, color='white', fontweight='bold',
                           bbox=dict(facecolor='black', alpha=0.7, edgecolor='white', boxstyle='round,pad=1'))

    data_holder = {"df": None}

    def fetch_data():
        try:
            logging.info("Veriler çekiliyor...")
            data_holder["df"] = get_metar_data(hours=6)
        except Exception as e:
            logging.error(f"Veri çekme hatası: {e}")
            data_holder["df"] = pd.DataFrame()

    def update_plot():
        loading_text.remove()
        df = data_holder["df"]
        
        if df is not None and not df.empty:
            # Türkiye Filtresi
            df = df[
                (df["lon"] >= min_lon) & (df["lon"] <= max_lon) &
                (df["lat"] >= min_lat) & (df["lat"] <= max_lat)
            ]

            if not df.empty:
                # 1. İZOBARLAR (Alçak ve Yüksek Basınç Çizgileri)
                pres_df = df.dropna(subset=["altim", "lat", "lon"]).copy()
                if not pres_df.empty and len(pres_df) > 3:
                    # API inHg değeri gönderiyorsa hPa (milibar) cinsine çevir
                    if pres_df["altim"].mean() < 200:
                        pres_df["altim"] = pres_df["altim"] * 33.8639
                        
                    p_min = int(pres_df["altim"].min())
                    p_max = int(pres_df["altim"].max())
                    start_level = p_min - (p_min % 4)
                    levels = np.arange(start_level, p_max + 5, 4)
                    
                    try:
                        cs = ax.tricontour(
                            pres_df["lon"], pres_df["lat"], pres_df["altim"],
                            levels=levels, colors="white", linewidths=1.0, zorder=4, alpha=0.6, linestyles="dashed"
                        )
                        ax.clabel(cs, inline=True, fontsize=10, fmt='%1.0f', colors="white")
                    except Exception as e:
                        logging.error(f"İzobar çizim hatası: {e}")

                # Sıcaklık Noktaları
                t_vals = df["temp"]
                # Renk skalası
                vmin, vmax = -10, 35
                norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=15, vmax=vmax)
                
                sc = ax.scatter(
                    df["lon"], df["lat"], c=t_vals, cmap="jet", s=50,
                    edgecolors="black", linewidths=0.5, zorder=5
                )
                plt.colorbar(sc, label="Sıcaklık (°C)", pad=0.02, shrink=0.8)

                # Rüzgar Barb'ları
                wind_df = df.dropna(subset=["wspd", "wdir"])
                if not wind_df.empty:
                    u = -wind_df["wspd"] * np.sin(np.deg2rad(wind_df["wdir"]))
                    v = -wind_df["wspd"] * np.cos(np.deg2rad(wind_df["wdir"]))
                    
                    ax.barbs(
                        wind_df["lon"], wind_df["lat"], u, v,
                        length=5, linewidth=0.5, color='black', zorder=6
                    )
                
                # Meteorolojik Hadiseler (Oraj, Kar, Yağmur, Sis vb.)
                if "wxString" in df.columns:
                    # TS (Oraj) - Kırmızı Artı
                    ts_df = df[df["wxString"].str.contains("TS", na=False)]
                    if not ts_df.empty:
                        ax.scatter(ts_df["lon"], ts_df["lat"], c='red', marker='P', s=45, edgecolors='black', linewidths=0.5, zorder=7)
                    
                    # SN (Kar) - Camgöbeği Yıldız
                    sn_df = df[df["wxString"].str.contains("SN", na=False) & ~df["wxString"].str.contains("TS", na=False)]
                    if not sn_df.empty:
                        ax.scatter(sn_df["lon"], sn_df["lat"], c='cyan', marker='*', s=55, edgecolors='blue', linewidths=0.3, zorder=7)
                    
                    # RA (Yağmur) - Mavi Nokta
                    ra_df = df[df["wxString"].str.contains("RA", na=False) & ~df["wxString"].str.contains("TS|SN", na=False)]
                    if not ra_df.empty:
                        ax.scatter(ra_df["lon"], ra_df["lat"], c='blue', marker='.', s=25, zorder=6)

                    # SH (Sağanak) - Ters Üçgen
                    sh_df = df[df["wxString"].str.contains("SH", na=False) & ~df["wxString"].str.contains("TS|SN|RA", na=False)]
                    if not sh_df.empty:
                        ax.scatter(sh_df["lon"], sh_df["lat"], c='green', marker='v', s=25, edgecolors='black', linewidths=0.3, zorder=6)

                    # Sis (FG) ve Pus (BR) - Gri Kare
                    fg_br_df = df[df["wxString"].str.contains("FG|BR", na=False) & ~df["wxString"].str.contains("TS|SN|RA|SH", na=False)]
                    if not fg_br_df.empty:
                        ax.scatter(fg_br_df["lon"], fg_br_df["lat"], c='gray', marker='s', s=15, alpha=0.8, edgecolors='black', linewidths=0.3, zorder=4)
        
                # 3. İSTASYON KODLARI (Katman olarak en üste)
                for _, row in df.iterrows():
                    if pd.notna(row['icaoId']) and pd.notna(row['lat']) and pd.notna(row['lon']):
                        ax.text(
                            row['lon'] + 0.05, row['lat'] + 0.05, str(row['icaoId']),
                            fontsize=8, color="#00E676", fontweight="bold",
                            path_effects=[path_effects.withStroke(linewidth=2, foreground="black")],
                            zorder=10
                        )
                        
        fig.canvas.draw()

    def check_thread():
        if not t.is_alive():
            timer.stop()
            update_plot()

    t = threading.Thread(target=fetch_data)
    t.start()

    timer = fig.canvas.new_timer(interval=100)
    timer.add_callback(check_thread)
    timer.start()

    plt.title("Türkiye Analiz Haritası (SHT Altlık)")
    plt.show()

if __name__ == "__main__":
    draw_surface_map()
