import pandas as pd
import re

# Test verileri: Excel'inizden gelebilecek veya hatalı okunabilecek çeşitli saat (GMT) formatları
test_verileri = [
    "00:00", "00:00:00", "03:00", "06", "06.0", 6.0, 9, "1200Z", "1500", 
    "11064", "21Z", "23:50", "0050", "0950", "950", 
    "24:00", "01.04.2026 06:00", "belirsiz_metin", "", None, float('nan')
]

df_test = pd.DataFrame({"Orijinal_Excel_Verisi": test_verileri})

# arayuz.py içindeki 1. aşama temizlik
df_test["gmt_raw"] = df_test["Orijinal_Excel_Verisi"].astype(str).str.upper().str.replace('Z', '').str.strip()

# -----------------------------------------------------
# 1. SİNOPTİK SAAT DÖNÜŞÜM ALGORTİMASI
# -----------------------------------------------------
def fix_sinoptik_hour(x):
    v = str(x).strip()
    if not v or v == 'NAN' or v == 'NONE':
        return float('nan')

    match = re.match(r'^\d+', v)
    if match:
        ext = match.group(0)
        if len(ext) == 6: return float(ext[2:4]) # DDHHMM formatı
        elif len(ext) == 5: return float(ext[2:4]) # 11064 tarzı YYGGiw formatı
        elif len(ext) >= 3: return float(ext[:2]) # 0600 tarzı HHMM
        return float(ext)
    try:
        return float(v)
    except:
        return float('nan')

df_test["Sinoptik_Algilanan"] = df_test["gmt_raw"].apply(fix_sinoptik_hour)

# -----------------------------------------------------
# 2. METAR SAAT DÖNÜŞÜM ALGORTİMASI
# -----------------------------------------------------
def match_metar_time(val):
    val = str(val).strip()
    if val == 'NAN' or val == 'NONE': return float('nan')
    if val.endswith('.0'): val = val[:-2]
    h, m = 0, 0
    try:
        time_match = re.search(r'(\d{1,2}):(\d{2})', val)
        if time_match: h, m = int(time_match.group(1)), int(time_match.group(2))
        elif len(val) == 6 and val.isdigit(): h, m = int(val[2:4]), int(val[4:6])
        elif len(val) == 4 and val.isdigit(): h, m = int(val[:2]), int(val[2:])
        elif len(val) == 3 and val.isdigit(): h, m = int(val[:1]), int(val[1:]) 
        elif val.isdigit() and len(val) <= 2: h, m = int(val), 0
        else: return float('nan')
    except: return float('nan')

    total = h * 60 + m
    targets = list(range(25)) # 0-24
    target_mins = [t * 60 for t in targets]
    
    closest_idx = min(range(len(target_mins)), key=lambda i: abs(target_mins[i] - total))
    closest_h = targets[closest_idx]
    
    return float(0) if closest_h == 24 else float(closest_h)

df_test["Metar_Algilanan"] = df_test["gmt_raw"].apply(match_metar_time)

print("=" * 80)
print("SAAT (GMT) DÖNÜŞÜM TEST ARACI")
print("=" * 80)
print(df_test.to_string(index=False))
print("=" * 80)
print("\nNOT: Eğer Excel'inizdeki saat formatı tabloda 'NaN' (Geçersiz) üretiyorsa,")
print("program o saati tanıyamadığı için eşleştirme yapamaz ve 'Veri Yok' hatası verir.")