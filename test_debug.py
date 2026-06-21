#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import sys
import os

# Modülü içe aktar
sys.path.insert(0, r"c:\Windows.old.000\Users\nebio\Desktop\tum\kardelen\HATARAMA")
import denetim_merkezi_1 as dm1
import denetim_merkezi_2 as dm2

hedef_klasor = r"C:\Users\nebio\Desktop\check"

# Dosyaları bul
sin_dosyalari = [f for f in os.listdir(hedef_klasor) 
                 if os.path.isfile(os.path.join(hedef_klasor, f)) 
                 and ("SIN" in f.upper() or "SİN" in f.upper())
                 and f.lower().endswith(('.xls', '.xlsx'))]

metar_dosyalari = [f for f in os.listdir(hedef_klasor) 
                   if os.path.isfile(os.path.join(hedef_klasor, f)) 
                   and "METAR" in f.upper()
                   and f.lower().endswith(('.xls', '.xlsx'))]

print(f"SİN Dosyaları Bulundu: {sin_dosyalari}")
print(f"METAR Dosyaları Bulundu: {metar_dosyalari}")

if not sin_dosyalari or not metar_dosyalari:
    print("❌ Dosyalar bulunamadı!")
    sys.exit(1)

sin_yolu = os.path.join(hedef_klasor, sin_dosyalari[0])
metar_yolu = os.path.join(hedef_klasor, metar_dosyalari[0])

print(f"\n📖 SİN Dosyası: {sin_yolu}")
print(f"📖 METAR Dosyası: {metar_yolu}\n")

# VERİ OKU
print("="*60)
print("1. SİNOPTİK VERİSİ OKUNUYOR...")
print("="*60)
try:
    df_sin = dm1.dosya_oku_akilli(sin_yolu)
    print(f"✅ SİNOPTİK BAŞARILI")
    print(f"   Boyut: {df_sin.shape}")
    print(f"   Sütunlar: {df_sin.columns.tolist()}")
    print(f"   İlk Satır:\n{df_sin.iloc[0] if len(df_sin) > 0 else 'Veri yok'}")
    print(f"   NaN Sayıları:\n{df_sin.isna().sum()}")
except Exception as e:
    print(f"❌ SİNOPTİK HATASI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("2. METAR VERİSİ OKUNUYOR...")
print("="*60)
try:
    df_metar = dm1.dosya_oku_akilli(metar_yolu)
    print(f"✅ METAR BAŞARILI")
except Exception as e:
    print(f"❌ METAR HATASI: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("3. TARİH (AY/YIL) OTOMATİK TESPİT")
print("="*60)
yil, ay = 2026, 1
tarih_bulundu = False
for df in [df_metar, df_sin]:
    for col in df.columns:
        sample = df[col].astype(str).str.extract(r'\b\d{2}\.(\d{2})\.(\d{4})\b').dropna()
        if not sample.empty:
            ay = int(sample[0].mode()[0])
            yil = int(sample[1].mode()[0])
            tarih_bulundu = True
            break
    if tarih_bulundu: break
print(f"✅ Tespit Edilen Dönem: {ay:02d}/{yil}")

import calendar
_, son_gun = calendar.monthrange(yil, ay)
sablon_data = []
for d in range(1, son_gun + 1):
    t_str = pd.Timestamp(year=yil, month=ay, day=d).strftime('%d.%m.%Y')
    for h in range(24):
        sablon_data.append({"sayfa": t_str, "gmt": float(h)})
df_sablon = pd.DataFrame(sablon_data)

if 'sayfa' in df_sin.columns:
    df_sin['sayfa'] = df_sin['sayfa'].astype(str).apply(lambda s: dm1.tarih_olustur_helper(s, yil, ay, is_metar=False))
if 'gmt' in df_sin.columns:
    df_sin['gmt'] = pd.to_numeric(df_sin['gmt'], errors='coerce')

if 'sayfa' in df_metar.columns:
    df_metar['sayfa'] = df_metar['sayfa'].astype(str).apply(lambda s: dm1.tarih_olustur_helper(s, yil, ay, is_metar=True))
if 'gmt' in df_metar.columns:
    df_metar['gmt'] = pd.to_numeric(df_metar['gmt'], errors='coerce')

df_sin_merged = pd.merge(df_sablon, df_sin, on=["sayfa", "gmt"], how="left")
df_metar_tekil = df_metar.groupby(["sayfa", "gmt"], as_index=False).first()
df_birlesik = pd.merge(df_sin_merged, df_metar_tekil, on=["sayfa", "gmt"], how="left", suffixes=('_sin', '_metar'))

if '_raw_line_sin' in df_birlesik.columns:
    df_birlesik['RASATLAR'] = df_birlesik['_raw_line_sin'].fillna('')
elif '_raw_line' in df_birlesik.columns:
    df_birlesik['RASATLAR'] = df_birlesik['_raw_line'].fillna('')
else:
    df_birlesik['RASATLAR'] = ""
    
if 'bulten' in df_birlesik.columns:
    df_birlesik['METAR_MESAJI'] = df_birlesik['bulten'].fillna('')

print("\n" + "="*80)
print(f"4. EKSİKSİZ TAM LİSTE ({son_gun * 24} ADET SAATLİK KAYIT)")
print("="*80)
for idx, row in df_birlesik.iterrows():
    tarih = row['sayfa']
    saat = row['gmt']
    rasat = str(row['RASATLAR']).strip()
    metar = str(row.get('METAR_MESAJI', '')).strip()
    
    out = f"[{tarih} - {saat:02.0f}Z] "
    if (not rasat or rasat == "nan") and (not metar or metar == "nan"):
        out += "❌ VERİ YOK / NAN"
    else:
        if rasat and rasat != "nan": out += f"SİN: {rasat} "
        if metar and metar != "nan": out += f"MET: {metar}"
    print(out)
        
print("\n" + "="*80)
print("5. DİĞER HATALARIN TEK TEK İNCELENMESİ (dm2)")
print("="*80)
try:
    df_analiz = dm2.hata_analizi_yap(df_sin_merged, df_metar)
    hatali_rasatlar = df_analiz[~df_analiz['ANALİZ_SONUCU'].isin(["Hata Yok", "Ara Rasat", "Veri Yok"])]
    if not hatali_rasatlar.empty:
        for idx, row in hatali_rasatlar.iterrows():
            print(f"[{row['sayfa']} - {row['gmt']:02.0f}Z] KOD: {row['HATA_KODLARI']}")
            print(f"   -> {row['HATA_ACIKLAMALARI']}\n")
    else:
        print("✨ Başka hiçbir kural hatası bulunamadı.")
except Exception as e:
    print(f"❌ Hata Analizi Sırasında Hata: {e}")

print("\n" + "="*60)
print("✅ TEST TAMAMLANDI")
print("="*60)
