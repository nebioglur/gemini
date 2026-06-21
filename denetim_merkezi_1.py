import sys
import subprocess
def ensure_lxml():
    try:
        import lxml
        import html5lib
    except ImportError:
        try:
            print("HTML Ayrıştırma motorları (lxml) eksik. Otomatik yükleniyor...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "lxml", "html5lib"])
        except Exception:
            pass
ensure_lxml()

import pandas as pd
import os
import re
import calendar
import logging
import traceback
import zipfile

# --- BAD CRC-32 (BOZUK EXCEL) BYPASS HACK ---
try:
    if hasattr(zipfile, 'ZipExtFile') and hasattr(zipfile.ZipExtFile, '_update_crc'):
        if not getattr(zipfile.ZipExtFile, '_crc_patched', False):
            _orig_update_crc = zipfile.ZipExtFile._update_crc
            def _patched_update_crc(self, newdata):
                self._expected_crc = None  # Zorla CRC kontrolünü kapat (BadZipFile hatasını önler)
                return _orig_update_crc(self, newdata)
            zipfile.ZipExtFile._update_crc = _patched_update_crc
            zipfile.ZipExtFile._crc_patched = True
except Exception:
    pass
# --------------------------------------------

# =========================================================
# BELLEK ÖNBELLEĞİ (CACHE) YÖNETİMİ
# =========================================================
_DOSYA_CACHE = {}


# =========================================================
# METAR PARSER (Raw Line Extraction)
# =========================================================

def parse_metar_line(line):
    parts = str(line).split()
    if not parts:
        return None

    data = {}
    gmt_found = False
    
    for p in parts:
        p = p.strip()
        if re.fullmatch(r'\d{6}Z', p): data['gmt'] = int(p[2:4]); gmt_found = True; break
        elif re.fullmatch(r'\d{4}Z', p): data['gmt'] = int(p[:2]); gmt_found = True; break
        elif re.fullmatch(r'\d{2}:\d{2}Z?', p): data['gmt'] = int(p.split(':')[0]); gmt_found = True; break

    if gmt_found:
        return data
    return None

# =========================================================
# SÜTUN NORMALİZASYONU
# =========================================================

def sutun_adi_normalize_et(col):

    c_raw = str(col).strip()
    
    # --- DOĞRUDAN EŞLEŞTİRME ---
    # Excel dosyanızdaki birebir sütun adlarını hiçbir işleme sokmadan doğrudan kodlara çevirir
    dogrudan_eslesmeler = {
        'GMT': 'gmt', 'iR': 'ir', 'iX': 'ix', 'h': 'h', 'VV': 'vv', 'N': 'n', 
        'dd': 'dd', 'ff': 'ff', '910': 'g910', '911': 'g911', 'T': 't', 'Td': 'td', 
        'Rh': 'rh', '3Po': 'p', '4P': 'p0', 'a': 'a', 'ppp': 'ppp', 'RRR': 'rrr', 
        'ww': 'ww', 'WW': 'w1', '960': 'g960', 'Bulut': 'nh', 'Bg1': 'cl', 
        'Bg2': 'cm', 'Bg3': 'ch', 'Bg4': 'bg4', '924': 'g924', '931': 'g931', 
        'Rasatçı': 'personel', 'Rasatci': 'personel',
        'mesaj_tipi': 'mesaj_tipi', 'salinim': 'salinim', 'min_gorus': 'min_gorus',
        'yon_gorus': 'yon_gorus', 'dikine_gorus': 'dikine_gorus', 'ww2': 'ww2', 'ww3': 'ww3',
        '1. bulut kap': '1. bulut kap', '1. bulut cins': '1. bulut cins', '1. bulut yuk': '1. bulut yuk',
        '2. bulut kap': '2. bulut kap', '2. bulut cins': '2. bulut cins', '2. bulut yuk': '2. bulut yuk',
        '3. bulut kap': '3. bulut kap', '3. bulut cins': '3. bulut cins', '3. bulut yuk': '3. bulut yuk',
        '4. bulut kap': '4. bulut kap', '4. bulut cins': '4. bulut cins', '4. bulut yuk': '4. bulut yuk',
        'tw': 'tw', 'inch': 'inch', 'ws': 'ws', 't': 't', 'td': 'td', 'p': 'p', 'p0': 'p0', 
        'n': 'n', 'vv': 'vv', 'rh': 'rh', 'gmt': 'gmt', 'dd': 'dd', 'ff': 'ff'
    }
    
    if c_raw in dogrudan_eslesmeler:
        return dogrudan_eslesmeler[c_raw]

    c = str(col).strip().lower()

    c = c.replace("\n", " ")
    c = re.sub(r"\s+", " ", c)
    c = c.replace("i̇", "i").replace("ı", "i")

    # Sembolleri boşlukla değiştirerek birim içeren kodların (Örn: "T (C)", "P hPa") daha rahat yakalanmasını sağlar
    c_clean = c.replace("(", " ").replace(")", " ").replace(".", " ").replace("/", " ").strip()
    c_clean = re.sub(r"\s+", " ", c_clean)

    # -----------------------------------------------------
    # TARİH / SAAT
    # -----------------------------------------------------

    if c in ['istasyon', 'ist', 'ist_no', 'ist no', 'station']:
        return 'istasyon_no'

    if 'tarih' in c or 'date' in c or 'gün' in c or 'gun' in c:
        return 'tarih'

    if 'gmt' in c or 'utc' in c:
        return 'gmt'

    if c in ['zaman', 'time', 'hour']:
        return 'gmt'

    if 'saat' in c and not any(
        x in c for x in ['güneş', 'sun', 'yağış', 'yagis', 'süresi', 'suresi']
    ):
        return 'gmt'

    # -----------------------------------------------------
    # RÜZGAR
    # -----------------------------------------------------

    if 'maksimum rüzgar' in c or 'max rüzgar' in c or c == '910':
        return 'g910'

    if 'hamle' in c or 'gust' in c or c == '911':
        return 'g911'
        
    if '924' in c: return 'g924'
    if '931' in c: return 'g931'
    if '932' in c: return 'g932'
    if '960' in c or '961' in c: return 'g960'
    if c == 'bg4': return 'bg4'

    if 'hız' in c or 'hiz' in c or 'speed' in c or c_clean == 'ff' or c_clean.startswith('ff '):
        return 'ff'

    if ('yön' in c or 'yon' in c or 'dir' in c or c_clean == 'dd' or c_clean.startswith('dd ')) and not any(k in c for k in ['rüyet', 'ruyet', 'görüş', 'gorus']):
        return 'dd'

    # -----------------------------------------------------
    # SICAKLIK
    # -----------------------------------------------------

    if 'toprak' in c or 'grass' in c or c_clean == 'tg' or c_clean.startswith('tg '):
        return 'tg'

    if c_clean == 'tx' or c_clean.startswith('tx ') or ('maks' in c and 'rüzgar' not in c):
        return 'tx'

    if c_clean == 'tn' or c_clean.startswith('tn ') or ('min' in c):
        return 'tn'

    if 'şba' in c or 'sba' in c or 'dew' in c or c_clean == 'td' or c_clean.startswith('td '):
        return 'td'
        
    if 'ıslak' in c or 'islak' in c or c_clean == 'tw' or c_clean.startswith('tw '):
        return 'tw'

    if (
        c_clean == 't'
        or c_clean.startswith('t ')
        or c_clean.endswith(' t')
        or 'kuru' in c
        or 'dry' in c
        or 'temp' in c
        or 'sıcaklık' in c
        or 'sicaklik' in c
    ) and not any(x in c for x in ['kp', 'kap', 'sür', 'sur']):
        return 't'

    if '%' in c or 'nem' in c or c_clean == 'rh' or c_clean.startswith('rh '):
        return 'rh'

    # -----------------------------------------------------
    # BASINÇ
    # -----------------------------------------------------

    if (
        '4p' in c
        or 'deniz' in c
        or 'msl' in c
        or c_clean == 'p0'
        or c_clean.startswith('p0 ')
        or 'qff' in c
        or 'qnh' in c
    ):
        return 'p0'

    if (
        '3po' in c
        or 'aktüel' in c
        or 'aktuel' in c
        or 'istasyon basıncı' in c
        or 'stn' in c
        or 'qfe' in c
        or c_clean == 'p'
        or c_clean.startswith('p ')
        or 'basınç' in c
        or 'basinc' in c
    ) and not ('4p' in c or 'deniz' in c or 'msl' in c or 'p0' in c):
        return 'p'

    if 'değişim' in c or 'degisim' in c or c_clean == 'ppp' or c_clean.startswith('ppp '):
        return 'ppp'

    if c_clean == 'a' or c_clean.startswith('a ') or 'karakteristik' in c:
        return 'a'

    # -----------------------------------------------------
    # METAR BULUT KATMANLARI
    # -----------------------------------------------------
    c_metar_cloud = c_clean.replace("ü", "u").replace("ö", "o")
    for i in range(1, 5):
        if f"{i} bulut kap" in c_metar_cloud: return f"{i}. bulut kap"
        if f"{i} bulut cins" in c_metar_cloud: return f"{i}. bulut cins"
        if f"{i} bulut yuk" in c_metar_cloud: return f"{i}. bulut yuk"

    # -----------------------------------------------------
    # BULUT
    # -----------------------------------------------------

    if c_clean == 'bulut' or c_clean.startswith('bulut ') or 'alçak' in c or 'alcak' in c or c_clean == 'nh' or c_clean.startswith('nh '):
        return 'nh'

    if 'kapalılık' in c or 'total' in c or c_clean == 'n' or c_clean.startswith('n ') or 't. kp' in c:
        return 'n'

    if c == 'kap.' or c == 'kap':
        return 'kap_katman'

    if c_clean == 'cl' or c_clean.startswith('cl ') or c == 'bg1':
        return 'cl'

    if c_clean == 'cm' or c_clean.startswith('cm ') or c == 'bg2':
        return 'cm'

    if c_clean == 'ch' or c_clean.startswith('ch ') or c == 'bg3':
        return 'ch'

    if 'yükseklik' in c or 'yukseklik' in c or c_clean == 'h' or c_clean.startswith('h ') or 'dikine' in c:
        return 'h'

    # -----------------------------------------------------
    # GÖRÜŞ
    # -----------------------------------------------------

    if c_clean == 'vv' or c_clean.startswith('vv ') or 'görüş' in c or 'gorus' in c or 'hakim' in c:
        return 'vv'

    # -----------------------------------------------------
    # YAĞIŞ
    # -----------------------------------------------------

    if 'yağış' in c or 'yagis' in c or c_clean == 'rrr' or c_clean.startswith('rrr '):
        return 'rrr'

    if 'süresi' in c or 'suresi' in c or c_clean == 'tr' or c_clean.startswith('tr '):
        return 'tr'

    # -----------------------------------------------------
    # HADİSE
    # -----------------------------------------------------

    if str(col).strip() == 'WW': return 'w1' # Büyük harf WW -> w1 (Geçmiş Hava)
    if '2. grup' in c: return 'ww2'
    if '3. grup' in c: return 'ww3'
    if 'halihazır' in c or 'hali' in c or 'present' in c or c == 'ww' or '1. grup' in c: return 'ww'
    if 'geçmiş1' in c or 'gecmis1' in c or c == 'w1': return 'w1'
    if 'geçmiş2' in c or 'gecmis2' in c or c == 'w2': return 'w2'
    if 'geçmiş' in c or 'gecmis' in c: return 'w1'

    if (
        'bülten' in c_clean
        or 'bulten' in c_clean
        or c_clean == 'metar'
        or c_clean == 'speci'
        or ('mesaj' in c_clean and 'tipi' not in c_clean)
        or 'şifre' in c_clean
        or 'sifre' in c_clean
        or c_clean in ['rasat', 'rasatlar', 'ham veri']
    ):
        return 'bulten'

    return c

# =========================================================
# BAŞLIK BULMA
# =========================================================

def header_bul(df):

    exact_keywords = {'t', 'td', 'p', 'p0', 'ir', 'ix', 'h', 'n', 'dd', 'ff', 'a', 'ppp', 'rrr', 'vv'}
    
    safe_keywords = {
        'gmt', 'utc', 'saat', 'istasyon', 'station',
        'sıcaklık', 'sicaklik', 'rüzgar', 'ruzgar', 'basınç', 'basinc',
        'yağış', 'yagis', 'görüş', 'gorus', 'qfe', 'qnh',
        'dikine', 'hakim', '1. grup', '2. grup', '3. grup', 'rstçı', 'kap', 'cins', 'bulut', 'rasatçı', 'rasatci', 'rasatlar', 'rasat',
        '910', '911', '924', '931', '932', '960', 'bg1', 'bg2', 'bg3', 'bg4',
        'kuru', 'işba', 'isba', 'hız', 'hiz', 'yön', 'yon', 'salınım', 'salinim',
        'tipi', 'mesaj', 'bülten'
    }
    
    # Kullanıcının Excel dosyasındaki tam sütun başlıkları (En yüksek puanı vermek için)
    kullanici_basliklari = {'gmt', 'ir', 'ix', 'h', 'vv', 'n', 'dd', 'ff', '910', '911', 't', 'td', 'rh', '3po', '4p', 'a', 'ppp', 'rrr', 'ww', '960', 'bulut', 'bg1', 'bg2', 'bg3', 'bg4', '924', '931', 'rasatçı', 'rasatlar', 'rasat'}

    best_row = None
    best_score = 0

    max_rows = min(40, len(df))

    for i in range(max_rows):

        row = df.iloc[i].fillna('').astype(str)

        score = 0

        for val in row:

            c = val.strip().lower()

            if not c:
                continue

            if 'unnamed' in c:
                continue

            if c in kullanici_basliklari:
                score += 5 # Orijinal dosya başlıkları ise rekor puan
                
            elif c in exact_keywords or c in safe_keywords:
                score += 3

            elif any(k in c for k in safe_keywords):
                score += 2

            elif re.fullmatch(r'[a-z]{1,4}', c):
                score += 1

        if score > best_score:
            best_score = score
            best_row = i

    if best_score >= 4:
        return best_row

    return None


# =========================================================
# MULTI HEADER OLUŞTUR
# =========================================================

def multi_header_olustur(df, h):

    row_h = df.iloc[h].copy().astype(str).replace(r'^\s*$', pd.NA, regex=True).replace(to_replace=r'(?i)^unnamed.*', value=pd.NA, regex=True).replace('nan', pd.NA)
    
    h_below = h + 1
    # Altındaki tamamen boş satırları atla (METAR'daki boş satır atlamaları)
    while h_below < len(df):
        r_temp = df.iloc[h_below].copy().astype(str).replace(r'^\s*$', pd.NA, regex=True).replace(to_replace=r'(?i)^unnamed.*', value=pd.NA, regex=True).replace('nan', pd.NA).dropna()
        if len(r_temp) > 0:
            break
        h_below += 1

    if h_below < len(df):
        row_below = df.iloc[h_below].copy().astype(str).replace(r'^\s*$', pd.NA, regex=True).replace(to_replace=r'(?i)^unnamed.*', value=pd.NA, regex=True).replace('nan', pd.NA)
    else:
        row_below = pd.Series([pd.NA]*len(df.columns))

    def is_mostly_numeric(r):
        vals = [str(v).strip().replace(',', '.').replace('-', '') for v in r.dropna().astype(str) if str(v).strip()]
        if not vals: return False
        nums = [v for v in vals if v.replace('.','',1).isdigit()]
        return (len(nums) / len(vals)) > 0.25

    if h_below < len(df) and not is_mostly_numeric(row_below):
        # h üst başlık, h_below alt başlık (arada boşluk varsa otomatik atlanmış haliyle gelir)
        row1 = row_h
        row2 = row_below
        data_start = h_below + 1
    else:
        # h alt başlık veya tek satır başlık olabilir. Üstündeki ebeveyn başlığı ara
        parent_h = -1
        max_valid = 1 # Araya sızan 3-4 kelimelik hayalet satırları atlamak için en çok kelimeye sahip asıl başlığı ara
        for i in range(h - 1, max(-1, h - 5), -1):
            r = df.iloc[i].copy().astype(str).replace(r'^\s*$', pd.NA, regex=True).replace(to_replace=r'(?i)^unnamed.*', value=pd.NA, regex=True).replace('nan', pd.NA)
            valid_vals = [v for v in r.dropna() if len(str(v).strip()) > 1]
            if len(valid_vals) > max_valid:
                max_valid = len(valid_vals)
                parent_h = i
        
        if parent_h != -1:
            row1 = df.iloc[parent_h].copy().astype(str).replace(r'^\s*$', pd.NA, regex=True).replace(to_replace=r'(?i)^unnamed.*', value=pd.NA, regex=True).replace('nan', pd.NA)
            row2 = row_h
            data_start = h_below
        else:
            row1 = pd.Series([pd.NA]*len(df.columns))
            row2 = row_h
            data_start = h_below

    # Boş hücreleri bir önceki başlık ile doldur (Merged cell ffill)
    row1 = row1.ffill().fillna('').astype(str)
    row2 = row2.ffill().fillna('').astype(str)

    cols = []
    for idx, (a, b) in enumerate(zip(row1, row2)):
        p1 = '' if 'unnamed' in a.lower() or a.lower() in ['nan', '<na>'] else a
        p2 = '' if 'unnamed' in b.lower() or b.lower() in ['nan', '<na>'] else b
        birlesik_ad = f"{p1} {p2}".strip()
        cols.append(birlesik_ad if birlesik_ad else f"Veri_{idx+1}")

    data = df.iloc[data_start:].copy()
    data.columns = cols
    
    # Sadece tamamen boş olan satır ve sütunları temizle, verisi olan hiçbir sütunu silme
    data = data.dropna(how='all').reset_index(drop=True)
    
    # Sadece hem isimsiz (Veri_...) hem de tamamen boş olan hayalet sütunları sil.
    # İsimli (Başlığı olan) ama boş olan meteorolojik sütunları SİLME!
    hayalet_sutunlar = [c for c in data.columns if str(c).startswith("Veri_") and data[c].isna().all()]
    data = data.drop(columns=hayalet_sutunlar)

    return data


# =========================================================
# SYNOP PARSER
# =========================================================

def _is_valid_ddhhm(token):
    if len(token) != 5 or not token.isdigit():
        return False

    day = int(token[0:2])
    hour = int(token[2:4])
    unit = int(token[4])

    return 1 <= day <= 31 and 0 <= hour <= 23 and 0 <= unit <= 4


def parse_synop_line(line):

    parts = str(line).split()

    if not parts:
        return None

    clean_parts = []
    for p in parts:
        if p.upper() in ['AAXX', 'BBXX', 'CCA', 'CCB', 'COR']:
            clean_parts.append(p.upper())
            continue
        clean_parts.append(p)

    if len(clean_parts) < 2:
        return None

    data = {}

    # AAXX/BBXX kodundan sonra gelen tarih/saat/ölçüm birimi ve istasyon
    # numarası gruplarını tespit edelim.
    idx = 0
    if 'AAXX' in clean_parts:
        idx = clean_parts.index('AAXX') + 1
    elif 'BBXX' in clean_parts:
        idx = clean_parts.index('BBXX') + 1
    elif 'CCA' in clean_parts:
        idx = clean_parts.index('CCA') + 1
    elif 'CCB' in clean_parts:
        idx = clean_parts.index('CCB') + 1
    elif 'COR' in clean_parts:
        idx = clean_parts.index('COR') + 1

    if idx < len(clean_parts):
        first = clean_parts[idx]
        second = clean_parts[idx + 1] if idx + 1 < len(clean_parts) else None

        if _is_valid_ddhhm(first):
            data['gmt'] = int(first[2:4])
            data['day'] = int(first[0:2])
            data['wind_unit'] = int(first[4])
            idx += 1

            if second and len(second) == 5 and second.isdigit():
                data['istasyon_no'] = second
                idx += 1

        elif second and _is_valid_ddhhm(second) and len(first) == 5 and first.isdigit():
            data['istasyon_no'] = first
            data['gmt'] = int(second[2:4])
            data['day'] = int(second[0:2])
            data['wind_unit'] = int(second[4])
            idx += 2

        elif len(first) == 5 and first.isdigit():
            data['istasyon_no'] = first
            idx += 1

    mode = 'main'

    for grp in clean_parts[idx:]:

        if grp == '333':
            mode = '333'
            continue

        if grp == '555':
            mode = '555'
            continue

        if '=' in grp:
            break

        if len(grp) != 5:
            continue

        safe = grp.replace('/', '0')

        if not safe.isdigit():
            continue

        ind = safe[0]
        val = safe[1:]

        # -------------------------------------------------
        # ANA BÖLÜM
        # -------------------------------------------------

        if mode == 'main':

            if 'ir' not in data:

                data['ir'] = int(safe[0])
                data['ix'] = int(safe[1])
                data['h'] = int(safe[2])
                data['vv'] = int(safe[3:])

                continue

            if 'n' not in data:

                data['n'] = int(safe[0])
                data['dd'] = int(safe[1:3])
                data['ff'] = int(safe[3:])

                continue

            if ind == '1':

                sign = -1 if val[0] == '1' else 1
                data['t'] = sign * int(val[1:]) / 10

            elif ind == '2':

                sign = -1 if val[0] == '1' else 1
                data['td'] = sign * int(val[1:]) / 10

            elif ind == '3':

                pressure = int(val) / 10

                if pressure < 500:
                    pressure += 1000
                else:
                    pressure += 900

                data['p'] = pressure

            elif ind == '4':

                pressure = int(val) / 10

                if pressure < 500:
                    pressure += 1000
                else:
                    pressure += 900

                data['p0'] = pressure

            elif ind == '5':

                data['a'] = int(val[0])
                data['ppp'] = int(val[1:]) / 10

            elif ind == '6':

                data['rrr'] = int(val[:3])
                data['tr'] = int(val[3])

            elif ind == '7':

                data['ww'] = int(val[:2])
                data['w1'] = int(val[2])
                data['w2'] = int(val[3])

            elif ind == '8':

                data['nh'] = int(val[0])
                data['cl'] = int(val[1])
                data['cm'] = int(val[2])
                data['ch'] = int(val[3])

        elif mode == '333':

            if ind == '8':
                data.setdefault('cloud_layers', []).append({
                    'nh': int(val[0]),
                    'c': int(val[1]),
                    'hshs': int(val[2:])
                })
            elif ind == '9' and val.startswith('11'):
                try:
                    data['g911'] = int(val[2:])
                except ValueError:
                    pass

        elif mode == '555':

            if ind == '1':
                pressure = int(val) / 10
                if pressure < 500:
                    pressure += 1000
                else:
                    pressure += 900
                data['qnh'] = pressure

    return data


# =========================================================
# TARİH OLUŞTURMA HELPER
# =========================================================

def tarih_olustur_helper(val, yil, ay, is_metar=False):
    try:
        val_str = str(val).lower().strip()
        
        import re
        # İçinde açıkça tarih formatı varsa onu yakala ve standartlaştır (örn: "01-04-2026", "2026/04/01")
        match = re.search(r'\b(\d{2})[\./-](\d{2})[\./-](\d{4})\b', val_str)
        if match:
            val_str = f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
            
        match_rev = re.search(r'\b(\d{4})[\./-](\d{2})[\./-](\d{2})\b', val_str)
        if match_rev:
            val_str = f"{match_rev.group(3)}.{match_rev.group(2)}.{match_rev.group(1)}"
            
        # Sadece rakamdan ibaretse (örn: "1", "01", "15") bunu doğrudan GÜN olarak alalım
        # Yoksa pd.to_datetime("1") komutu 2001 yılına atayabiliyor.
        if val_str.isdigit():
            gun = int(val_str)
            _, son_gun = calendar.monthrange(yil, ay)
            if 1 <= gun <= son_gun:
                return pd.Timestamp(year=yil, month=ay, day=gun).strftime('%d.%m.%Y')

        try:
            dt = pd.to_datetime(val_str, errors='raise', dayfirst=True)
            return dt.strftime('%d.%m.%Y')
        except:
            pass

        import re
        rakamlar = re.findall(r'\d+', val_str)
        if not rakamlar:
            return None
        gun = int(rakamlar[0])

        # Hem SİNOPTİK hem METAR için verilerin (Sheet2, 4, 6...) formatında olduğu kuralı
        if "sheet" in val_str or "sayfa" in val_str or val_str.isdigit():
            if gun >= 2 and gun % 2 == 0:
                gun = gun // 2
            elif gun >= 3 and gun % 2 != 0:
                return None # Tek sayılı sayfalar (Sheet3, Sheet5 vb.) kapalı rasatlar olduğundan yoksayılır
            else:
                return None

        _, son_gun = calendar.monthrange(yil, ay)
        if 1 <= gun <= son_gun:
            return pd.Timestamp(year=yil, month=ay, day=gun).strftime('%d.%m.%Y')
        
        return None
    except:
        return None

# =========================================================
# ANA DOSYA OKUMA
# =========================================================

def dosya_oku_akilli(dosya_yolu):
    global _DOSYA_CACHE
    try:
        # Dosyanın son değiştirilme tarihini al (Dosya güncellenirse eski cache iptal olur)
        mtime = os.path.getmtime(dosya_yolu)
        cache_key = (dosya_yolu, mtime)
        if cache_key in _DOSYA_CACHE:
            logging.info(f"⚡ '{os.path.basename(dosya_yolu)}' bellekten (Cache) süper hızlı yüklendi.")
            return _DOSYA_CACHE[cache_key].copy()
    except Exception:
        pass

    tum = []
    ekstra_veriler = {}

    try:

        excel = pd.ExcelFile(dosya_yolu)

        for sayfa in excel.sheet_names:

            if 'document map' in sayfa.lower():
                logging.warning(f"Uyarı: '{sayfa}' isimli gizli/meta sayfa atlandı.")
                continue

            # Tek sayılı sayfaları (kapalı rasat) oku, özel hücreleri çıkar ve sonraki sayfaya geç
            sayfa_str = str(sayfa).lower()
            is_odd_sheet = False
            cift_sayfa_adi = None
            
            if "sheet" in sayfa_str or "sayfa" in sayfa_str:
                rakamlar = re.findall(r'\d+', sayfa_str)
                if rakamlar:
                    sayfa_no = int(rakamlar[0])
                    if sayfa_no % 2 != 0:
                        if len(excel.sheet_names) <= 1:
                            is_odd_sheet = False
                        else:
                            is_odd_sheet = True
                        if sayfa_no != 1:
                            # Örn: Sheet3 verisini Sheet2'ye bağla
                            cift_sayfa_adi = sayfa_str.replace(str(sayfa_no), str(sayfa_no - 1))
            elif sayfa_str.startswith("k-"):
                is_odd_sheet = True
                cift_sayfa_adi = sayfa_str.replace("k-", "a-")
            elif re.search(r'(_1|\(1\))$', sayfa_str):
                # Aynı tarihe sahip olduğu için _1 veya (1) eklenen kapalı rasat sayfaları
                is_odd_sheet = True
                cift_sayfa_adi = re.sub(r'(_1|\(1\))$', '', sayfa_str).strip()

            if is_odd_sheet:
                # KONTROL: Bu sayfa tek numaralı ama aslında ana verileri içeriyor olabilir! (Örn: Tek sayfalı METAR dosyası)
                ham_kontrol = pd.read_excel(excel, sheet_name=sayfa, header=None, dtype=str)
                h_idx = header_bul(ham_kontrol)
                if h_idx is not None:
                    row_values = ham_kontrol.iloc[h_idx].astype(str).str.lower().values
                    match_count = 0
                    for val in row_values:
                        v_clean = str(val).strip()
                        if v_clean in ["t", "p", "n", "ff", "dd", "h", "a"] or any(k in v_clean for k in ["gmt", "saat", "ww", "halihazır", "present", "istasyon", "rüzgar", "yön", "hız", "basınç", "yağış", "rrr", "bulut", "görüş", "vv", "bülten", "metar", "tipi"]):
                            match_count += 1
                    if match_count >= 5:
                        is_odd_sheet = False  # Bu bir kapalı rasat değil, açık veri sayfasıdır!
                        
                if is_odd_sheet:
                    for i in range(min(10, len(ham_kontrol))):
                        v_a = str(ham_kontrol.iloc[i, 0]).strip().upper() if len(ham_kontrol.columns) > 0 else ""
                        if v_a in ['TİPİ', 'TIPI', 'METAR', 'GM', 'GMT'] or 'METAR' in v_a or 'GMT' in v_a:
                            # Sadece sütunları dolu olanları say
                            dolu_sutun_sayisi = ham_kontrol.iloc[i].dropna().astype(str).str.strip().ne("").sum()
                            if dolu_sutun_sayisi > 4:
                                is_odd_sheet = False
                            break
                            
            if is_odd_sheet:
                if cift_sayfa_adi:
                    try:
                        df_odd = pd.read_excel(excel, sheet_name=sayfa, header=None)
                        
                        orig_cift_sayfa = None
                        for s in excel.sheet_names:
                            if str(s).lower() == cift_sayfa_adi:
                                orig_cift_sayfa = s
                                break
                        if orig_cift_sayfa is None: orig_cift_sayfa = cift_sayfa_adi

                        # --- METAR TEK SAYILI (Ham Rasat) KESİN KONUM ARAMA ---
                        # KULLANICI İSTEĞİ: C2'de 'RASAT' başlığı, C3'ten itibaren şifreler, B sütununda Saatler
                        gmt_col_idx = 1     # B sütunu (Saat)
                        rasat_col_idx = 2   # C sütunu (Kapalı Rasat)
                        rasat_row_start = 2 # C3 satırı (0-tabanlı indeks ile 2)
                        
                        # Ufak bir satır kayma payına karşı 'RASAT' başlığını arıyoruz
                        header_found = False
                        for r_idx in range(min(10, len(df_odd))):
                            for c_idx in range(len(df_odd.columns)):
                                val = str(df_odd.iloc[r_idx, c_idx]).strip().upper()
                                if val in ['RASAT', 'RASATLAR', 'BÜLTEN', 'BULTEN', 'MESAJ', 'ŞİFRE', 'SIFRE', 'METAR']:
                                    rasat_col_idx = c_idx
                                    rasat_row_start = r_idx + 1
                                    if c_idx > 0: gmt_col_idx = c_idx - 1 # Saat genelde hemen solundadır
                                    header_found = True
                                    break
                            if header_found: break
                        
                        if gmt_col_idx != -1 and rasat_col_idx != -1:
                            metar_raw_rows = []
                            for r in range(rasat_row_start, len(df_odd)):
                                gmt_val = df_odd.iloc[r, gmt_col_idx]
                                rasat_val = df_odd.iloc[r, rasat_col_idx]
                                
                                gmt_str = str(gmt_val).strip() if pd.notna(gmt_val) else ""
                                rasat_str = str(rasat_val).strip() if pd.notna(rasat_val) else ""
                                
                                # Eğer GMT hücresi boşsa veya sadece 'NaN' yazıyorsa, saati METAR'ın şifresi içinden çek
                                if (not gmt_str or gmt_str.lower() == 'nan' or not re.search(r'\d', gmt_str)) and len(rasat_str) > 15:
                                    if re.search(r'\b\d{6}Z\b', rasat_str):
                                        z_match = re.search(r'\b\d{2}(\d{4})Z\b', rasat_str)
                                        if z_match:
                                            gmt_str = z_match.group(1)

                                if gmt_str and rasat_str and len(rasat_str) > 10 and gmt_str.lower() != 'nan':
                                    tip_val = df_odd.iloc[r, 0] if len(df_odd.columns) > 0 else ""
                                    tip_str = str(tip_val).strip() if pd.notna(tip_val) else ""
                                    metar_raw_rows.append({'mesaj_tipi': tip_str, 'gmt': gmt_str, 'bulten': rasat_str, '_raw_line': rasat_str, 'sayfa': orig_cift_sayfa})
                                            
                            if metar_raw_rows:
                                tum.append(pd.DataFrame(metar_raw_rows))
                                logging.info(f"Bilgi: '{sayfa}' METAR ham rasat sayfası başarıyla okundu.")

                        # --- SİNOPTİK TEK SAYILI (Ekstra Veriler & Rasatlar) ---
                        extracted = {h: {} for h in range(24)}
                        
                        def safe_get(r, c):
                            if r < len(df_odd) and c < len(df_odd.columns):
                                val = df_odd.iloc[r, c]
                                if pd.notna(val) and str(val).strip() != "":
                                    return str(val).strip()
                            return None

                        # 18 GMT (Maksimum Sıcaklık) -> F18 -> (17, 5)
                        v_tx = safe_get(17, 5)
                        if v_tx: extracted[18]['tx'] = v_tx

                        # 06 GMT -> Minumum vb.
                        map_06 = {
                            (17, 14): 'tn',            # O18: Minumum
                            (22, 14): 'top_ustu_min',  # O23: Top. Ustu Min.
                            (25, 14): 'rrr_toplam',    # O26: Top. Yağış
                            (14, 19): 'e',             # T15: Yerin Hali
                            (17, 19): 'e_kar',         # T18: YerinHali(Kar)
                            (22, 19): 'g931',          # T23: Kar Kalınlığı
                            (25, 19): 'g932',          # T26: Taze Kar
                            (14, 23): 'buhar',         # X15: Buharlaşma
                            (17, 23): 'buh_alet_tipi', # X18: Buh. Alet Tipi
                            (22, 23): 'gunes',         # X23: Güneşlenme
                            (14, 27): 'rad_tipi',      # AB15: Rad. Tipi
                            (17, 27): 'radyasyon',     # AB18: Radyasyon
                            (22, 27): 'deniz_suyu'     # AB23: Dnz Suyu Sıc
                        }
                        for (r, c), col_name in map_06.items():
                            val = safe_get(r, c)
                            if val: extracted[6][col_name] = val
                            
                        # Rasatlar (Ham Synop Kodları) - KULLANICI İSTEĞİNE GÖRE KESİN KONUM (D5-D12)
                        rasat_col = 3 # D sütunu (0:A, 1:B, 2:C, 3:D)
                        rasat_row_start = 4 # D5 satırı (0-tabanlı indeks 4)
                        
                        # Kaymalara karşı "RASATLAR" başlığını garantiye alalım
                        found_header = False
                        for r_idx in range(min(20, len(df_odd))):
                            for c_idx in range(len(df_odd.columns)):
                                val = safe_get(r_idx, c_idx)
                                if val:
                                    val_upper = str(val).strip().upper()
                                    if 'RASATLAR' in val_upper or 'ŞİFRELİ' in val_upper or 'SIFRELI' in val_upper:
                                        rasat_col = c_idx
                                        rasat_row_start = r_idx + 1
                                        found_header = True
                                        break
                            if found_header:
                                break
                                
                        # 00, 03, 06, 09, 12, 15, 18, 21 GMT için sırayla alt alta 8 satır oku (Örn: D5-D12)
                        sin_gmt_saatleri = [0, 3, 6, 9, 12, 15, 18, 21]
                        for i, g_hour in enumerate(sin_gmt_saatleri):
                            r = rasat_row_start + i
                            val = safe_get(r, rasat_col)
                            if val and len(str(val).strip()) > 10:
                                extracted[g_hour]['_raw_line'] = str(val).strip()

                        if orig_cift_sayfa and any(extracted.values()):
                            ekstra_veriler[orig_cift_sayfa] = extracted
                    except: pass
                logging.info(f"Bilgi: '{sayfa}' kapalı rasat (tek numaralı) sayfa olarak işlendi ve ana tablodan atlandı.")
                continue

            ham = pd.read_excel(
                excel,
                sheet_name=sayfa,
                header=None,
                dtype=str
            )

            # --- SİNOPTİK VE METAR ÇİFT SAYFALAR İÇİN SABİT OKUMA (Nokta Atışı) ---
            sayfa_str_low = str(sayfa).lower()
            # Açık rasat sayfası ise
            header_row = -1
            sablon_tipi = None
            for i in range(min(20, len(ham))):
                v_a = str(ham.iloc[i, 0]).strip().upper() if len(ham.columns) > 0 else ""
                v_b = str(ham.iloc[i, 1]).strip().upper() if len(ham.columns) > 1 else ""
                if v_a in ['GM', 'GMT']:
                    header_row = i
                    sablon_tipi = 'SINOPTİK'
                    break
                elif v_a in ['TİPİ', 'TIPI'] or v_b == 'GMT' or v_a == 'METAR':
                    header_row = i
                    sablon_tipi = 'METAR'
                    break

            if sablon_tipi == 'SINOPTİK':
                    # DİNAMİK SİNOPTİK OKUMA (Sütun Kaymalarına Karşı Kesin Çözüm)
                    data_start_row = header_row + 1
                    if header_row + 1 < len(ham):
                        alt_val = str(ham.iloc[header_row + 1, 0]).strip()
                        if not alt_val.isdigit() and alt_val.lower() != 'nan':
                            data_start_row = header_row + 2
                            
                    sabit_kolonlar = {}
                    for c_idx in range(len(ham.columns)):
                        c_val1 = str(ham.iloc[header_row, c_idx]).strip().lower()
                        c_val2 = str(ham.iloc[header_row + 1, c_idx]).strip().lower() if header_row + 1 < len(ham) else ""
                        
                        if c_val2 and c_val2 != 'nan' and not any(char.isdigit() for char in c_val2):
                            birlesik_isim = f"{c_val1} {c_val2}"
                        else:
                            birlesik_isim = c_val1
                            
                        norm_ad = sutun_adi_normalize_et(birlesik_isim)
                        
                        bilinen_isimler = {
                            'gmt', 'ir', 'ix', 'h', 'vv', 'n', 'dd', 'ff', 't', 'td', 'rh', 'p', 'p0', 
                            'a', 'ppp', 'rrr', 'tr', 'ww', 'w1', 'w2', 'nh', 'cl', 'cm', 'ch', 'tx', 
                            'tn', 'tg', 'e', 'bg4', 'g910', 'g911', 'g924', 'g931', 'g932', 'g960', 'bulten',
                            'personel'
                        }
                        
                        if norm_ad in bilinen_isimler or (norm_ad and norm_ad != birlesik_isim):
                            sabit_kolonlar[c_idx] = norm_ad
                        elif "şifre" in birlesik_isim or "mesaj" in birlesik_isim or "bülten" in birlesik_isim or "rasat" in birlesik_isim or "ham" in birlesik_isim:
                            sabit_kolonlar[c_idx] = '_raw_line'
                        else:
                            # Başlığı boş veya farklı isimlendirilmiş sütunların içeriğine bakarak tahmin et
                            is_raw, is_960 = False, False
                            for r_i in range(data_start_row, min(data_start_row + 20, len(ham))):
                                val = str(ham.iloc[r_i, c_idx]).strip().upper()
                                if len(val) > 20 and ("=" in val or val.startswith("AAXX") or val.startswith("CCA") or " 17" in val):
                                    is_raw = True; break
                                if len(val) >= 3 and (val.startswith("960") or val.startswith("961")):
                                    is_960 = True; break
                            
                            if is_raw and '_raw_line' not in sabit_kolonlar.values(): sabit_kolonlar[c_idx] = '_raw_line'
                            elif is_960 and 'g960' not in sabit_kolonlar.values(): sabit_kolonlar[c_idx] = 'g960'
                            elif c_idx == 22 and 'g960' not in sabit_kolonlar.values(): sabit_kolonlar[c_idx] = 'g960'
                            elif c_idx == 19 and 'rrr' not in sabit_kolonlar.values(): sabit_kolonlar[c_idx] = 'rrr'
                            elif c_idx == 30 and 'g931' not in sabit_kolonlar.values(): sabit_kolonlar[c_idx] = 'g931'
                            elif c_idx == 32 and 'personel' not in sabit_kolonlar.values(): sabit_kolonlar[c_idx] = 'personel'
                            
                    # KULLANICI İSTEĞİ: SİNOPTİK Sheet2,4,6... Sabit Koordinat Garantisi (T, W, AE, AG)
                    garanti_sutunlar = {
                        0: 'gmt', 1: 'ir', 2: 'ix', 3: 'h', 4: 'vv', 5: 'n', 6: 'dd', 7: 'ff',
                        10: 'g910', 11: 'g911', 12: 't', 13: 'td', 14: 'rh', 15: 'p', 16: 'p0', 
                        17: 'a', 18: 'ppp', 19: 'rrr', 20: 'ww', 21: 'w1', 22: 'g960', 23: 'nh', 
                        24: 'cl', 25: 'cm', 26: 'ch', 27: 'bg4', 29: 'g924', 30: 'g931', 32: 'personel'
                    }
                    if len(ham.columns) >= 33:
                        for g_idx, g_col in garanti_sutunlar.items():
                            if g_col not in sabit_kolonlar.values():
                                sabit_kolonlar[g_idx] = g_col
                    
                    mevcut_idx = [k for k in sabit_kolonlar.keys() if k < len(ham.columns)]
                    
                    df = ham.iloc[data_start_row : header_row + 15, mevcut_idx].copy()
                    df.columns = [sabit_kolonlar[k] for k in mevcut_idx]
                    
                    df['sayfa'] = sayfa
                    if 'gmt' in df.columns:
                        df.dropna(subset=['gmt'], inplace=True)
                    else:
                        df.dropna(how='all', inplace=True)
                    
                    if any(df.columns.duplicated()):
                        cols = pd.Series(df.columns).fillna('Unnamed_NaN')
                        for dup in cols[cols.duplicated()].unique():
                            dup_indices = cols[cols == dup].index.tolist()
                            for idx_num, idx in enumerate(dup_indices):
                                if idx_num != 0:
                                    cols[idx] = f"{dup}_{idx_num}"
                        df.columns = cols
                    
                    print(f"\nSAYFA: {sayfa}")
                    print("SİNOPTİK DİNAMİK ŞABLONLA OKUNDU (Sütun Kaymalarına Karşı Korumalı)")
                    sutun_detay_log = ", ".join([f"[{k}]:{v}" for k, v in sabit_kolonlar.items()])
                    logging.info(f"'{sayfa}' sayfası SİNOPTİK dinamik hücre eşleştirmesi ile okundu. Eşleşen Sütunlar -> {sutun_detay_log}")
                    
                    tum.append(df)
                    continue

            elif sablon_tipi == 'METAR':
                    # DİNAMİK METAR OKUMA (Sütun Kaymalarına Karşı Kesin Çözüm)
                    sabit_kolonlar = {}
                    for c_idx in range(len(ham.columns)):
                        c_val1 = str(ham.iloc[header_row, c_idx]).strip().lower()
                        c_val2 = str(ham.iloc[header_row + 1, c_idx]).strip().lower() if header_row + 1 < len(ham) else ""
                        
                        if c_val2 and c_val2 != 'nan' and not any(char.isdigit() for char in c_val2):
                            birlesik_isim = f"{c_val1} {c_val2}"
                        else:
                            birlesik_isim = c_val1
                            
                        norm_ad = sutun_adi_normalize_et(birlesik_isim)
                        
                        bilinen_isimler = {
                            'gmt', 'ir', 'ix', 'h', 'vv', 'n', 'dd', 'ff', 't', 'td', 'rh', 'p', 'p0', 
                            'a', 'ppp', 'rrr', 'tr', 'ww', 'w1', 'w2', 'nh', 'cl', 'cm', 'ch', 'tx', 
                            'tn', 'tg', 'e', 'bg4', 'g910', 'g911', 'g924', 'g931', 'g932', 'g960', 'bulten',
                            'mesaj_tipi', 'salinim', 'min_gorus', 'yon_gorus', 'dikine_gorus', 'ww2', 'ww3',
                            '1. bulut kap', '1. bulut cins', '1. bulut yuk', '2. bulut kap', '2. bulut cins', '2. bulut yuk',
                            '3. bulut kap', '3. bulut cins', '3. bulut yuk', '4. bulut kap', '4. bulut cins', '4. bulut yuk',
                            'tw', 'inch', 'ws', 'personel'
                        }
                        
                        if norm_ad in bilinen_isimler or (norm_ad and norm_ad != birlesik_isim):
                            sabit_kolonlar[c_idx] = norm_ad
                        elif "şifre" in birlesik_isim or "mesaj" in birlesik_isim or "bülten" in birlesik_isim:
                            sabit_kolonlar[c_idx] = 'bulten'
                    
                    mevcut_idx = [k for k in sabit_kolonlar.keys() if k < len(ham.columns)]
                    
                    data_start_row = header_row + 1
                    if header_row + 1 < len(ham):
                        alt_val = str(ham.iloc[header_row + 1, 0]).strip()
                        if not alt_val.isdigit() and alt_val.lower() != 'nan':
                            data_start_row = header_row + 2
                            
                    df = ham.iloc[data_start_row :, mevcut_idx].copy()
                    df.columns = [sabit_kolonlar[k] for k in mevcut_idx]
                    
                    df['sayfa'] = sayfa
                    # METAR için saatin boş olduğu veya veri bulunmayan ekstra not satırlarını temizle
                    if 'gmt' in df.columns:
                        df.dropna(subset=['gmt'], inplace=True)
                    
                    if any(df.columns.duplicated()):
                        cols = pd.Series(df.columns).fillna('Unnamed_NaN')
                        for dup in cols[cols.duplicated()].unique():
                            dup_indices = cols[cols == dup].index.tolist()
                            for idx_num, idx in enumerate(dup_indices):
                                if idx_num != 0:
                                    cols[idx] = f"{dup}_{idx_num}"
                        df.columns = cols
                    
                    print(f"\nSAYFA: {sayfa}")
                    print("METAR SABİT ŞABLONLA OKUNDU (5. Satır Başlık, 6. Satırdan Sonrası Veri)")
                    sutun_detay_log = ", ".join([f"[{k}]:{v}" for k, v in sabit_kolonlar.items()])
                    logging.info(f"'{sayfa}' sayfası METAR dinamik hücre eşleştirmesi ile okundu. Eşleşen Sütunlar -> {sutun_detay_log}")
                    
                    tum.append(df)
                    continue

            h = header_bul(ham)

            print(f"\nSAYFA: {sayfa}")
            print("HEADER:", h)

            if h is not None and h + 1 < len(ham):

                df = multi_header_olustur(ham, h)

            elif h is not None:

                df = ham.iloc[h + 1:].copy()
                df.columns = ham.iloc[h]

            else:

                text_lines = ham.fillna('').agg(' '.join, axis=1)

                parsed_rows = []

                for line in text_lines:

                    parsed = parse_synop_line(line)
                    if not parsed:
                        parsed = parse_metar_line(line)

                    if parsed:
                        parsed['_raw_line'] = line.strip()
                        parsed_rows.append(parsed)

                if parsed_rows:

                    df = pd.DataFrame(parsed_rows)

                else:
                    logging.warning(f"Uyarı: '{sayfa}' sayfasında geçerli bir veri veya tablo yapısı bulunamadı, atlandı.")
                    continue

            df['sayfa'] = sayfa

            # KESİN ÇÖZÜM (REINDEXING HATASI İÇİN): Sütun isimlerini tekilleştir
            if any(df.columns.duplicated()):
                cols = pd.Series(df.columns).fillna('Unnamed_NaN')
                for dup in cols[cols.duplicated()].unique():
                    dup_indices = cols[cols == dup].index.tolist()
                    for idx_num, idx in enumerate(dup_indices):
                        if idx_num != 0:
                            cols[idx] = f"{dup}_{idx_num}"
                df.columns = cols

            tum.append(df)

    except Exception as e:

        print("OKUMA HATASI:", e)
        logging.error(f"'{os.path.basename(dosya_yolu)}' okunurken kritik bir hata oluştu:", exc_info=True)
        
        # --- HTML FALLBACK (Eğer dosya aslen HTML olarak dışa aktarılmışsa) ---
        try:
            tablolar = pd.read_html(dosya_yolu, flavor='lxml')
            for i, ham in enumerate(tablolar):
                h = header_bul(ham)
                if h is None:
                    if len(ham) > 5: h = 3
                    else: continue
                
                df = ham.iloc[h + 1:].copy()
                df.columns = ham.iloc[h]
                df['sayfa'] = f"HTML_Sayfa_{i+1}"
                
                if any(df.columns.duplicated()):
                    cols = pd.Series(df.columns).fillna('Unnamed_NaN')
                    for dup in cols[cols.duplicated()].unique():
                        dup_indices = cols[cols == dup].index.tolist()
                        for idx_num, idx in enumerate(dup_indices):
                            if idx_num != 0: cols[idx] = f"{dup}_{idx_num}"
                    df.columns = cols
                    
                tum.append(df)
            if tum:
                logging.info(f"'{os.path.basename(dosya_yolu)}' dosyası HTML formatında başarıyla okundu.")
        except Exception as html_e:
            try:
                from bs4 import BeautifulSoup, SoupStrainer
                # 1 ve 2. Optimizasyon: Sadece table etiketlerini lxml motoruyla çok hızlı oku
                sadece_tablolar = SoupStrainer('table')
                with open(dosya_yolu, 'r', encoding='utf-8', errors='replace') as f:
                    try:
                        hizli_soup = BeautifulSoup(f, 'lxml', parse_only=sadece_tablolar)
                    except getattr(BeautifulSoup, 'FeatureNotFound', Exception):
                        f.seek(0)
                        try:
                            # lxml yoksa varsayılan html.parser
                            hizli_soup = BeautifulSoup(f, 'html.parser', parse_only=sadece_tablolar)
                        except Exception:
                            # Tüm motorlar çökerse tarayıcı standartlarındaki en dayanıklı html5lib motoruna geç
                            f.seek(0)
                            hizli_soup = BeautifulSoup(f, 'html5lib', parse_only=sadece_tablolar)
                
                # Sütun kaymalarını önlemek için <br> etiketlerini boşlukla değiştir
                for br in hizli_soup.find_all("br"):
                    br.replace_with(" ")
                # Gizli HTML elementlerini ağaçtan tamamen sil (Pandas'ın görmemesi için)
                for hidden in hizli_soup.find_all(style=lambda value: value and 'display:none' in value.replace(' ', '')):
                    hidden.decompose()
                
                html_str = str(hizli_soup)
                if not html_str.strip():
                    raise ValueError("HTML tablosu bulunamadı.")
                import io
                # parse_only ile ayıklanan temiz HTML'i lxml ile en hızlı şekilde dataframe'e dönüştür
                tablolar = pd.read_html(io.StringIO(html_str), flavor='lxml')
                for i, ham in enumerate(tablolar):
                    h = header_bul(ham)
                    if h is None:
                        if len(ham) > 5: h = 3
                        else: continue
                    
                    df = ham.iloc[h + 1:].copy()
                    df.columns = ham.iloc[h]
                    df['sayfa'] = f"HTML_Sayfa_{i+1}"
                    
                    if any(df.columns.duplicated()):
                        cols = pd.Series(df.columns).fillna('Unnamed_NaN')
                        for dup in cols[cols.duplicated()].unique():
                            dup_indices = cols[cols == dup].index.tolist()
                            for idx_num, idx in enumerate(dup_indices):
                                if idx_num != 0: cols[idx] = f"{dup}_{idx_num}"
                        df.columns = cols
                        
                    tum.append(df)
                if tum:
                    logging.info(f"'{os.path.basename(dosya_yolu)}' dosyası HTML(bs4) formatında başarıyla okundu.")
            except Exception as html_bs4_e:
                try:
                    df_csv = pd.read_csv(dosya_yolu, sep='\t')
                    if len(df_csv.columns) < 3:
                        df_csv = pd.read_csv(dosya_yolu, sep=None, engine='python')
                    
                    h = header_bul(df_csv)
                    if h is None:
                        if len(df_csv) > 5: h = 3
                        else: h = 0
                    
                    df = df_csv.iloc[h + 1:].copy()
                    df.columns = df_csv.iloc[h]
                    df['sayfa'] = "CSV_Sayfa_1"
                    
                    if any(df.columns.duplicated()):
                        cols = pd.Series(df.columns).fillna('Unnamed_NaN')
                        for dup in cols[cols.duplicated()].unique():
                            dup_indices = cols[cols == dup].index.tolist()
                            for idx_num, idx in enumerate(dup_indices):
                                if idx_num != 0: cols[idx] = f"{dup}_{idx_num}"
                        df.columns = cols
                        
                    tum.append(df)
                    if tum:
                        logging.info(f"'{os.path.basename(dosya_yolu)}' dosyası CSV formatında başarıyla okundu.")
                except Exception as csv_e:
                    logging.warning("HTML/CSV standart okuma başarısız. Agresif (RAW TEXT) kurtarma deneniyor...")
                    try:
                        with open(dosya_yolu, 'r', encoding='utf-8', errors='ignore') as f:
                            raw_lines = f.readlines()
                        salvaged_data = []
                        for line in raw_lines:
                            if not line.strip(): continue
                            parts = re.split(r'\t|;|\||,| {2,}', line.strip())
                            salvaged_data.append(parts)
                        if len(salvaged_data) > 0:
                            df = pd.DataFrame(salvaged_data)
                            h = header_bul(df)
                            if h is None:
                                h = 3 if len(df) > 5 else 0
                            df_final = df.iloc[h + 1:].copy()
                            df_final.columns = df.iloc[h]
                            df_final['sayfa'] = "RAW_Sayfa_1"
                            if any(df_final.columns.duplicated()):
                                cols = pd.Series(df_final.columns).fillna('Unnamed_NaN')
                                for dup in cols[cols.duplicated()].unique():
                                    dup_indices = cols[cols == dup].index.tolist()
                                    for idx_num, idx in enumerate(dup_indices):
                                        if idx_num != 0: cols[idx] = f"{dup}_{idx_num}"
                                df_final.columns = cols
                            tum.append(df_final)
                            logging.info(f"'{os.path.basename(dosya_yolu)}' dosyası AGRESİF RAW TEXT formatında başarıyla okundu.")
                        else:
                            raise ValueError("Anlamlı metin verisi bulunamadı.")
                    except Exception as agg_e:
                        logging.error(f"'{os.path.basename(dosya_yolu)}' HTML, CSV ve RAW olarak okunamadı: HTML={html_e}, CSV={csv_e}, RAW={agg_e}")

    if not tum:
        raise ValueError(f"Hiç veri okunamadı. Dosya bozuk veya desteklenmeyen formatta olabilir: {os.path.basename(dosya_yolu)}")

    # -----------------------------------------------------
    # CONCAT
    # -----------------------------------------------------

    df_all = pd.concat(tum, ignore_index=True)

    # -----------------------------------------------------
    # KOLON NORMALİZASYONU
    # -----------------------------------------------------

    yeni_kolonlar = []

    for idx, c in enumerate(df_all.columns):
        norm_c = sutun_adi_normalize_et(c)
        # Sadece rakamlardan oluşan veya anlamsız (nan) başlıkları veri kaybını önlemek için isimlendir
        if str(norm_c).strip().isdigit() or str(norm_c).strip().lower() in ['nan', 'none', '']:
            norm_c = f'Bilinmeyen_Veri_{idx+1}'
        yeni_kolonlar.append(norm_c)

    df_all.columns = yeni_kolonlar

    # Sadece hem Bilinmeyen_Veri_ adını alan hem de tamamen boş olan hayalet sütunları sil.
    # İsimli (Başlığı olan) meteorolojik sütunları tamamen boş olsa bile SİLME!
    hayalet_sutunlar = [c for c in df_all.columns if str(c).startswith("Bilinmeyen_Veri_") and df_all[c].isna().all()]
    df_all = df_all.drop(columns=hayalet_sutunlar)

    # -----------------------------------------------------
    # EKSTRA VERİLERİ (KAPALI RASAT) ANA TABLOYA AKTAR
    # -----------------------------------------------------
    if ekstra_veriler:
        def safe_gmt_extract(x):
            v = str(x).strip().upper().replace('Z', '')
            if not v or v == 'NAN': return float('nan')
            try:
                if ':' in v:
                    h = int(v.split(':')[0])
                    m = int(v.split(':')[1]) if len(v.split(':')) > 1 else 0
                    if m >= 40: h += 1
                    if h == 24: h = 0
                    return float(h)
                elif len(v) >= 3 and v.isdigit():
                    h = int(v[:-2])
                    m = int(v[-2:])
                    if m >= 40: h += 1
                    if h == 24: h = 0
                    return float(h)
                else:
                    return float(v)
            except:
                return float('nan')

        def exact_gmt_extract(x):
            v = str(x).strip().upper().replace('Z', '')
            if not v or v == 'NAN': return ""
            try:
                if ':' in v:
                    h = int(v.split(':')[0])
                    m = int(v.split(':')[1]) if len(v.split(':')) > 1 else 0
                    return f"{h:02d}{m:02d}"
                elif len(v) >= 3 and v.isdigit():
                    h = int(v[:-2])
                    m = int(v[-2:])
                    return f"{h:02d}{m:02d}"
                else:
                    return f"{int(float(v)):02d}00"
            except:
                return ""
                
        gmt_num = df_all['gmt'].apply(safe_gmt_extract)
        gmt_exact = df_all['gmt'].apply(exact_gmt_extract)
        
        for cift_sayfa, ekstra_gmt_dict in ekstra_veriler.items():
                
            for g_hour, data_dict in ekstra_gmt_dict.items():
                if not data_dict: continue
                    
                if isinstance(g_hour, str):
                    mask_gmt = (df_all['sayfa'] == cift_sayfa) & (gmt_exact == g_hour)
                else:
                    mask_gmt = (df_all['sayfa'] == cift_sayfa) & (gmt_num == g_hour)
                    
                for k, v in data_dict.items():
                    if k not in df_all.columns:
                        df_all[k] = ""
                    if mask_gmt.any():
                        df_all.loc[mask_gmt, k] = str(v).strip()

    # -----------------------------------------------------
    # DUPLICATE MERGE
    # -----------------------------------------------------

    if any(df_all.columns.duplicated()):

        temiz = pd.DataFrame(index=df_all.index)

        for col in df_all.columns.unique():

            alt = df_all.loc[:, df_all.columns == col].copy()

            if alt.shape[1] > 1:
                alt.columns = range(alt.shape[1])
                temiz[col] = alt.bfill(axis=1).iloc[:, 0]
            else:
                temiz[col] = alt.iloc[:, 0]

        df_all = temiz

    # GÜVENLİK: Eğer sayfa sütunu kaybolduysa çökmemesi için ekle
    if "sayfa" not in df_all.columns:
        df_all["sayfa"] = "1"

    print("\nSON KOLONLAR:")
    print(df_all.columns.tolist())

    print("\nİLK 5 SATIR")
    # Konsol kilitlenmesini önlemek için sadece ilk 15 sütunu yazdır
    print(df_all.iloc[:5, :15])

    # Başarıyla okunan veriyi belleğe kaydet
    try:
        mtime = os.path.getmtime(dosya_yolu)
        _DOSYA_CACHE[(dosya_yolu, mtime)] = df_all.copy()
    except Exception:
        pass
    return df_all
