import pandas as pd
import sys
import os

# Ana dizini yola ekliyoruz ki denetim_merkezi_2.py'yi bulabilsin
sys.path.insert(0, r"c:\Windows.old.000\Users\nebio\Desktop\tum\HATARAMA")
import denetim_merkezi_2 as dm2

def test_h379_senaryosu():
    print("=== Şimşek (ww=13) ve Oraj (h379) Test Senaryosu ===\n")
    
    test_tarih = "16.05.2024"
    
    birlesik_veri = [
        {
            # Senaryo 1: METAR'da TSRA (Oraj) var, SİNOPTİK'te Şimşek (ww=13)
            "sayfa": test_tarih, "gmt": 6.0, "ww_sin": 13.0, "cl_sin": 3.0, "w1_sin": 2.0, "w2_sin": 2.0,
            "t_sin": 15.0, "p_sin": 1012.0, "bulten_metar": "METAR LTAN 160600Z 12010KT 9999 TSRA FEW030CB 15/10 Q1012="
        },
        {
            # Senaryo 2: Geçmiş havada W1=9 (Oraj) var, SİNOPTİK'te Şimşek (ww=13)
            "sayfa": test_tarih, "gmt": 9.0, "ww_sin": 13.0, "cl_sin": 9.0, "w1_sin": 9.0, "w2_sin": 2.0,
            "t_sin": 16.0, "p_sin": 1011.0, "bulten_metar": "METAR LTAN 160900Z 12010KT 9999 FEW030CB 16/10 Q1011="
        },
        {
            # Senaryo 3: Sadece ww=13 var (Oraj unutuldu mu? diye DİKKAT uyarısı fırlatmalı)
            "sayfa": test_tarih, "gmt": 12.0, "ww_sin": 13.0, "cl_sin": 3.0, "w1_sin": 2.0, "w2_sin": 2.0,
            "t_sin": 17.0, "p_sin": 1010.0, "bulten_metar": "METAR LTAN 161200Z 12010KT 9999 FEW030CB 17/10 Q1010="
        }
    ]
    
    df_birlesik = pd.DataFrame(birlesik_veri)
    df_metar = pd.DataFrame([
        {"sayfa": test_tarih, "gmt": 6.0, "bulten": birlesik_veri[0]["bulten_metar"]},
        {"sayfa": test_tarih, "gmt": 9.0, "bulten": birlesik_veri[1]["bulten_metar"]},
        {"sayfa": test_tarih, "gmt": 12.0, "bulten": birlesik_veri[2]["bulten_metar"]}
    ])
    
    sonuc_df = dm2.hata_analizi_yap(df_birlesik, df_metar)
    
    for idx, row in sonuc_df.iterrows():
        saat = int(row['gmt'])
        print(f"Saat: {saat:02d}:00 GMT")
        print(f"  Durum               : {row['ANALİZ_SONUCU']}")
        if pd.notna(row['HATA_KODLARI']) and str(row['HATA_KODLARI']).strip() != "":
            print(f"  Hata Kodları        : {row['HATA_KODLARI']}")
            print(f"  Açıklama            : {row['HATA_ACIKLAMALARI']}")
        print("-" * 65)

if __name__ == "__main__":
    test_h379_senaryosu()