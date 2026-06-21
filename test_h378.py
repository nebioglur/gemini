import pandas as pd
import sys
import os

# Ana dizini yola ekliyoruz ki denetim_merkezi_2.py'yi bulabilsin
sys.path.insert(0, r"c:\Windows.old.000\Users\nebio\Desktop\tum\HATARAMA")
import denetim_merkezi_2 as dm2

def test_h378_senaryosu():
    print("=== ww=03 ve N azalması (h378) Test Senaryosu ===\n")
    
    test_tarih = "15.05.2024"
    
    # 1. Önceki Rasat (Saat 09:00 GMT)
    # N = 6/8
    # ww = 02 (Değişiklik yok)
    
    # 2. Güncel Rasat (Saat 12:00 GMT)
    # N = 3/8 (Önceki rasata göre AZALMIŞ: 6 -> 3)
    # ww = 03 (Bulutlar artıyor kodlanmış) -> ÇELİŞKİ VAR (h378 fırlatılmalı!)
    
    birlesik_veri = [
        {
            "sayfa": test_tarih, "gmt": 9.0, "n_sin": 6.0, "ww_sin": 2.0, 
            "t_sin": 15.0, "p_sin": 1012.0, "RASATLAR": "SIMULE EDILMIS 09Z RASADI"
        },
        {
            "sayfa": test_tarih, "gmt": 12.0, "n_sin": 3.0, "ww_sin": 3.0, 
            "t_sin": 16.0, "p_sin": 1011.0, "RASATLAR": "SIMULE EDILMIS 12Z RASADI"
        }
    ]
    
    df_birlesik = pd.DataFrame(birlesik_veri)
    df_metar = pd.DataFrame([{"sayfa": test_tarih, "gmt": 9.0}, {"sayfa": test_tarih, "gmt": 12.0}])
    
    # Hata analizini çalıştır
    sonuc_df = dm2.hata_analizi_yap(df_birlesik, df_metar)
    
    # Sonuçları ekrana yazdır
    for idx, row in sonuc_df.iterrows():
        saat = int(row['gmt'])
        print(f"Saat: {saat:02d}:00 GMT")
        print(f"  N (Bulut Kapalılığı): {int(row['n_sin'])}/8")
        print(f"  ww (Halihazır Hava) : {int(row['ww_sin']):02d}")
        print(f"  Durum               : {row['ANALİZ_SONUCU']}")
        if pd.notna(row['HATA_KODLARI']) and str(row['HATA_KODLARI']).strip() != "":
            print(f"  Hata Kodları        : {row['HATA_KODLARI']}")
            print(f"  Açıklama            : {row['HATA_ACIKLAMALARI']}")
        print("-" * 65)

if __name__ == "__main__":
    test_h378_senaryosu()