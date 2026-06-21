import pandas as pd
import sys
import os

# Ana dizini yola ekliyoruz ki denetim_merkezi_2.py'yi bulabilsin
sys.path.insert(0, r"c:\Windows.old.000\Users\nebio\Desktop\tum\kardelen\HATARAMA")

try:
    import denetim_merkezi_2_fixed as dm2
except ImportError:
    import denetim_merkezi_2 as dm2

def test_h317_senaryosu():
    print("=== 24 Saatlik Yağış (h317 ve h232) Test Senaryoları ===\n")
    
    birlesik_veri = [
        # -----------------------------------------------------------
        # SENARYO 1: Doğru Toplam (WMO 12h + 12h)
        # 18Z = 15.0 mm, 06Z = 10.0 mm -> rrr_toplam = 25.0 mm (Hata YOK)
        # -----------------------------------------------------------
        {"sayfa": "06.05.2024", "gmt": 6.0, "rrr_sin": 5.0, "tr_sin": 2.0},
        {"sayfa": "06.05.2024", "gmt": 12.0, "rrr_sin": 5.0, "tr_sin": 1.0},
        {"sayfa": "06.05.2024", "gmt": 18.0, "rrr_sin": 15.0, "tr_sin": 2.0}, # WMO T-12h
        {"sayfa": "07.05.2024", "gmt": 0.0, "rrr_sin": 0.0, "tr_sin": 1.0},
        {"sayfa": "07.05.2024", "gmt": 6.0, "rrr_sin": 10.0, "tr_sin": 2.0, "rrr_toplam_sin": 25.0, "Senaryo": "Senaryo 1: Doğru Toplam (15+10=25)"},
        
        # -----------------------------------------------------------
        # SENARYO 2: Hatalı (Toplam, Güncel 06Z'den Küçük)
        # 18Z = 15.0 mm, 06Z = 10.0 mm -> rrr_toplam = 5.0 mm (Hata h317, h232)
        # -----------------------------------------------------------
        {"sayfa": "08.05.2024", "gmt": 18.0, "rrr_sin": 15.0, "tr_sin": 2.0},
        {"sayfa": "09.05.2024", "gmt": 6.0, "rrr_sin": 10.0, "tr_sin": 2.0, "rrr_toplam_sin": 5.0, "Senaryo": "Senaryo 2: Hatalı (Toplam=5, 06Z=10)"},
        
        # -----------------------------------------------------------
        # SENARYO 3: Hatalı (Toplam, Dünkü 18Z'den Küçük)
        # 18Z = 20.0 mm, 06Z = 10.0 mm -> rrr_toplam = 15.0 mm (Hata h317, h232)
        # -----------------------------------------------------------
        {"sayfa": "10.05.2024", "gmt": 18.0, "rrr_sin": 20.0, "tr_sin": 2.0},
        {"sayfa": "11.05.2024", "gmt": 6.0, "rrr_sin": 10.0, "tr_sin": 2.0, "rrr_toplam_sin": 15.0, "Senaryo": "Senaryo 3: Hatalı (Toplam=15, 18Z=20)"},
        
        # -----------------------------------------------------------
        # SENARYO 4: Eser Miktar (990-999) Doğru Toplam
        # 18Z = 990 (0.0 mm), 06Z = 995 (0.5 mm) -> rrr_toplam = 995 (0.5 mm) (Hata YOK)
        # -----------------------------------------------------------
        {"sayfa": "12.05.2024", "gmt": 18.0, "rrr_sin": 990.0, "tr_sin": 2.0},
        {"sayfa": "13.05.2024", "gmt": 6.0, "rrr_sin": 995.0, "tr_sin": 2.0, "rrr_toplam_sin": 995.0, "Senaryo": "Senaryo 4: Eser Miktar (0.0 + 0.5 = 0.5)"},
        
        # -----------------------------------------------------------
        # SENARYO 5: tR=4 (24 Saatlik RRR Grubu) Doğru Toplam
        # Geçmiş: 6Z=5, 12Z=0, 18Z=15, 00Z=0 -> Güncel 6Z(tR=4) = 20.0 mm (Hata YOK)
        # -----------------------------------------------------------
        {"sayfa": "14.05.2024", "gmt": 6.0, "rrr_sin": 5.0, "tr_sin": 2.0},
        {"sayfa": "14.05.2024", "gmt": 12.0, "rrr_sin": 0.0, "tr_sin": 1.0},
        {"sayfa": "14.05.2024", "gmt": 18.0, "rrr_sin": 15.0, "tr_sin": 2.0},
        {"sayfa": "15.05.2024", "gmt": 0.0, "rrr_sin": 0.0, "tr_sin": 1.0},
        {"sayfa": "15.05.2024", "gmt": 6.0, "rrr_sin": 20.0, "tr_sin": 4.0, "Senaryo": "Senaryo 5: tR=4 Doğru (Geçmiş Toplam=20)"},
        
        # -----------------------------------------------------------
        # SENARYO 6: tR=4 (24 Saatlik RRR Grubu) Hatalı
        # Geçmiş: 6Z=5, 12Z=0, 18Z=15, 00Z=0 -> Güncel 6Z(tR=4) = 12.0 mm (Hata h317, h232)
        # -----------------------------------------------------------
        {"sayfa": "16.05.2024", "gmt": 6.0, "rrr_sin": 5.0, "tr_sin": 2.0},
        {"sayfa": "16.05.2024", "gmt": 12.0, "rrr_sin": 0.0, "tr_sin": 1.0},
        {"sayfa": "16.05.2024", "gmt": 18.0, "rrr_sin": 15.0, "tr_sin": 2.0},
        {"sayfa": "17.05.2024", "gmt": 0.0, "rrr_sin": 0.0, "tr_sin": 1.0},
        {"sayfa": "17.05.2024", "gmt": 6.0, "rrr_sin": 12.0, "tr_sin": 4.0, "Senaryo": "Senaryo 6: tR=4 Hatalı (Toplam=12, 18Z=15)"}
    ]
    
    df_birlesik = pd.DataFrame(birlesik_veri)
    # df_metar için sadece sayfa ve gmt içeren iskelet dataframe
    df_metar = pd.DataFrame([{"sayfa": r["sayfa"], "gmt": r["gmt"]} for r in birlesik_veri])
    
    sonuc_df = dm2.hata_analizi_yap(df_birlesik, df_metar)
    
    for idx, row in sonuc_df.dropna(subset=['Senaryo']).iterrows():
        print(f"[{row['sayfa']} {int(row['gmt']):02d}:00Z] {row['Senaryo']}")
        print(f"  Durum               : {row['ANALİZ_SONUCU']}")
        if pd.notna(row['HATA_KODLARI']) and str(row['HATA_KODLARI']).strip() != "":
            kodlar = str(row['HATA_KODLARI'])
            ilgili_kodlar = [k.strip() for k in kodlar.split(',') if k.strip() in ['h316', 'h317', 'h232']]
            ilgili_aciklamalar = [a.strip() for k, a in zip(kodlar.split(','), str(row['HATA_ACIKLAMALARI']).split('|')) if k.strip() in ['h316', 'h317', 'h232']]
            
            if ilgili_kodlar:
                print(f"  Hata Kodları        : {', '.join(ilgili_kodlar)}")
                for a in ilgili_aciklamalar:
                    print(f"  Açıklama            : {a}")
            else:
                print("  İlgili Hata Yok")
        else:
            print("  Hata Yok")
        print("-" * 75)

if __name__ == "__main__":
    test_h317_senaryosu()