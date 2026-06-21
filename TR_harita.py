import geopandas as gpd
import matplotlib.pyplot as plt
import os
import math
import logging
import ssl

# SSL Sertifika hatalarını aşmak için (GitHub JSON indirmesi)
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

def generate_static_map(output_path="turkey_map_hd_v7.png"):
    """
    turkey_map.py için koordinatları sabitlenmiş altlık harita oluşturur.
    """
    try:
        # 🔹 Türkiye il sınırları (DİREK online – GitHub)
        turkey = gpd.read_file(
            "https://raw.githubusercontent.com/cihadturhan/tr-geojson/master/geo/tr-cities-utf8.json"
        )
        # 🔹 Ülke sınırı (iller birleştirilir)
        turkey_border = turkey.dissolve()
        
        # 🔹 Dünya Haritası (Kıbrıs ve çevre ülkeler için)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
            except AttributeError:
                # Geopandas 1.0+ için alternatif URL
                url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
                world = gpd.read_file(url)
                if 'NAME' in world.columns and 'name' not in world.columns:
                    world.rename(columns={'NAME': 'name'}, inplace=True)
                    
            cyprus = world[world.name == "Cyprus"]
            
    except Exception as e:
        logging.error(f"Harita verisi indirilemedi: {e}")
        return False

    # Koordinat sınırları (Genişletildi: Akdeniz, Karadeniz ve Kıbrıs dahil)
    min_lon, max_lon = 25.0, 45.0
    min_lat, max_lat = 34.0, 44.0
    
    # Gerçek coğrafi oran (Enleme göre boylamın daralması distorsiyonunu önlemek için)
    mean_lat = (min_lat + max_lat) / 2.0
    lat_ratio = math.cos(math.radians(mean_lat))
    
    aspect_ratio = ((max_lon - min_lon) * lat_ratio) / (max_lat - min_lat)
    h = 18
    w = h * aspect_ratio

    fig = plt.figure(figsize=(w, h), dpi=400)
    # Çerçevesiz tam ekran eksen (0,0'dan 1,1'e)
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.set_axis_off()
    fig.add_axes(ax)

    # 🔹 Deniz / Arka plan (Denizlerin belli olması için renk açıldı)
    ax.set_facecolor("#071425")
    
    # 🔹 Çevre Ülkeler (Kıbrıs dahil)
    if 'world' in locals():
        world.plot(ax=ax, color="#122236", edgecolor="#1b2a3d", linewidth=0.8)
        
    # 🔹 Kara Parçası ve İl Sınırları
    turkey.plot(ax=ax, color="#264161", edgecolor="#3c556e", linewidth=1.2)

    # 🔹 Ülke Dış Sınırı (3D / Glow Efekti için çoklu katman)
    # 1. Dış gölge (Vignette)
    turkey_border.plot(ax=ax, facecolor="none", edgecolor="#000000", linewidth=6.0, alpha=0.6)
    # 2. Orta kalın çerçeve
    turkey_border.plot(ax=ax, facecolor="none", edgecolor="#546e7a", linewidth=3.5)
    # 3. İnce parlak iç çerçeve
    turkey_border.plot(ax=ax, facecolor="none", edgecolor="#ffffff", linewidth=1.5)

    # 🔹 Kıbrıs Dış Sınırı (Aynı 3D Efekti)
    if 'cyprus' in locals() and not cyprus.empty:
        cyprus.plot(ax=ax, facecolor="none", edgecolor="#000000", linewidth=6.0, alpha=0.6)
        cyprus.plot(ax=ax, facecolor="none", edgecolor="#546e7a", linewidth=3.5)
        cyprus.plot(ax=ax, facecolor="none", edgecolor="#ffffff", linewidth=1.5)

    # 🔹 GERÇEK SINIRLAR İÇİN: Haritanın boylam eksenini, enleme göre sıkıştırır
    ax.set_aspect(1 / lat_ratio)

    # Sınırları EN SON sabitle (Plot işlemi limitleri değiştirebileceği için)
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)

    fig.savefig(output_path, facecolor="#071425", dpi=400)
    plt.close(fig)
    return True

if __name__ == "__main__":
    generate_static_map()
