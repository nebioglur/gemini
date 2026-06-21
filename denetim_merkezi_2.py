import pandas as pd
import math
import datetime
import concurrent.futures
import kurallar
import sys
import os
import re

# Ana dizindeki synop_decoder.py modülüne erişebilmek için yolu (path) ekliyoruz
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path: sys.path.insert(0, CURRENT_DIR)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from synop_decoder import SynopDecoder
except ImportError:
    SynopDecoder = None

def _get_val(s, key):
    """Merge sonrası oluşan _sin ekli sütunları ve orijinal sütunları güvenle okur."""
    sin_key = f"{key}_sin"
    if sin_key in s:
        val = s[sin_key]
        if pd.notna(val):
            return val
    if key in s:
        val = s[key]
        if pd.notna(val):
            return val
    return None

def _to_float(val):
    """Değeri güvenli bir şekilde float'a çevirir."""
    try: return float(val) if pd.notna(val) else None
    except (ValueError, TypeError): return None

def hata_analizi_yap(birlesik_df, df_metar):
    """
    Birleştirilmiş veri setini tarar ve hataları tespit eder.
    """
    hata_dict = kurallar.HATA_SOZLUGU

    # --- AY GEÇİŞİ (CROSS-MONTH) İÇİN ARŞİV ÖNBELLEĞİ ---
    _arsiv_cache = {}

    def get_arsiv_df(dt_target):
        y, m = dt_target.year, dt_target.month
        k = f"{y}_{m:02d}"
        if k in _arsiv_cache:
            return _arsiv_cache[k]
            
        arsiv_yolu = f"C:\\Users\\nebio\\Desktop\\check\\Arsiv\\{y}_{m:02d}"
        hedef_dosya = None
        if os.path.exists(arsiv_yolu):
            for f in os.listdir(arsiv_yolu):
                if f.startswith(f"DENETIM_{y}_{m:02d}") and f.endswith(".xlsx"):
                    hedef_dosya = os.path.join(arsiv_yolu, f)
                    break
                    
        if hedef_dosya:
            try:
                df_arsiv = pd.read_excel(hedef_dosya, sheet_name="Detaylı_Rapor")
                rename_dict = {
                    'Tarih': 'sayfa', 'Saat (GMT)': 'gmt',
                    'METAR - Saat': 'gmt_exact',
                    'METAR - Halihazır Hava (ww)': 'ww', 'METAR - Halihazır Hava 2 (ww2)': 'ww2', 'METAR - Halihazır Hava 3 (ww3)': 'ww3',
                    'SİNOPTİK - Halihazır Hava (ww)': 'ww_sin', 'SİNOPTİK - Geçmiş Hava 1 (W1)': 'w1_sin', 'SİNOPTİK - Geçmiş Hava 2 (W2)': 'w2_sin',
                    'SİNOPTİK - Yağış Miktarı (RRR)': 'rrr_sin', 'SİNOPTİK - Sıcaklık (T)': 't_sin', 'SİNOPTİK - İstasyon Basıncı (P)': 'p_sin',
                    'SİNOPTİK - Deniz Basıncı (P0)': 'p0_sin', 'METAR - Şifreli Mesaj': 'bulten', 'SİNOPTİK - Toplam Yağış': 'rrr_toplam'
                }
                for old_col, new_col in rename_dict.items():
                    col_matches = [c for c in df_arsiv.columns if c == old_col or str(c).upper() == old_col.upper()]
                    if col_matches: df_arsiv.rename(columns={col_matches[0]: new_col}, inplace=True)
                _arsiv_cache[k] = df_arsiv
                return df_arsiv
            except Exception: pass
        _arsiv_cache[k] = pd.DataFrame()
        return _arsiv_cache[k]

    # Dosyada tamamen eksik veya boş olan sütunları tespit et (Gereksiz "Eksik Grup" hatalarını önlemek için)
    dolu_sutunlar = set()
    for col in birlesik_df.columns:
        if birlesik_df[col].notna().any():
            dolu_sutunlar.add(col)

    def hata_ara(s):
        kodlar, aciklamalar = [], []
        gmt = s.get("gmt")

        veri_var = any(pd.notna(_get_val(s, key)) for key in ['t', 'td', 'p', 'p0', 'ir', 'rrr', 'n', 'vv', 'dd', 'ff', 'ww', 'w1', 'w2'])
        if not veri_var:
            rasatlar_str = str(_get_val(s, "RASATLAR")).strip() if pd.notna(_get_val(s, "RASATLAR")) else ""
            if rasatlar_str and rasatlar_str.lower() != "nan":
                veri_var = True

        if pd.isna(gmt) or not veri_var:
            if pd.notna(gmt):
                if gmt % 3 != 0:
                    return ("Ara Rasat", "", "Sadece METAR (Ara Rasat) bulunur, SİNOPTİK beklenmez.")
                else:
                    return ("Hata Yok", "", "")
            return ("Hata Yok", "", "")

        ir = _to_float(_get_val(s, "ir"))
        rrr = _to_float(_get_val(s, "rrr"))
        ix = _to_float(_get_val(s, "ix"))
        w1 = _to_float(_get_val(s, "w1"))
        w2 = _to_float(_get_val(s, "w2"))
        
        # EXCEL'DE KULLANICI W1 SÜTUNUNA (WW) W1 VE W2'Yİ BİTİŞİK GİRDİYSE AYIR (Örn: 82 -> W1=8, W2=2)
        if pd.notna(w1) and w1 > 9:
            try:
                w1_str = str(int(w1))
                if len(w1_str) == 2:
                    w1 = float(w1_str[0])
                    w2 = float(w1_str[1])
                    s['w1'] = w1
                    s['w2'] = w2
            except: pass
            
        tr = _to_float(_get_val(s, "tr"))
        
        t = _to_float(_get_val(s, "t"))
        td = _to_float(_get_val(s, "td"))
        tx = _to_float(_get_val(s, "tx"))
        tn = _to_float(_get_val(s, "tn"))
        tg = _to_float(_get_val(s, "tg"))
        n = _to_float(_get_val(s, "n"))
        nh = _to_float(_get_val(s, "nh"))
        cl = _to_float(_get_val(s, "cl"))
        cm = _to_float(_get_val(s, "cm"))
        ch = _to_float(_get_val(s, "ch"))
        dd = _to_float(_get_val(s, "dd"))
        ff = _to_float(_get_val(s, "ff"))
        vv = _to_float(_get_val(s, "vv"))
        a = _to_float(_get_val(s, "a"))
        ppp = _to_float(_get_val(s, "ppp"))
        p = _to_float(_get_val(s, "p"))
        p0 = _to_float(_get_val(s, "p0"))
        e = _to_float(_get_val(s, "e"))
        h = _to_float(_get_val(s, "h"))
        ww = _to_float(_get_val(s, "ww"))
        
        g924 = _get_val(s, "g924")
        g931 = _get_val(s, "g931")
        g932 = _get_val(s, "g932")
        g960 = _get_val(s, "g960")
        hadise_kayit = _get_val(s, "hadise_kayit")
        rasatlar = _get_val(s, "RASATLAR")
        gunes = _get_val(s, "gunes")
        buhar = _get_val(s, "buhar")
        rh = _to_float(_get_val(s, "rh"))
        
        # --- ŞİFRELİ MESAJ (RAW LINE) ÜZERİNDEN EKSİK DEĞERLERİ TAMAMLAMA ---
        # Kullanıcı veriyi excel'de ilgili hücreye girmemiş ancak raw string içinde (RASATLAR sütununda)
        # kodlamış olabilir. Validator öncesi, hata analizini yanıltmaması için verileri kurtar:
        if pd.notna(rasatlar) and ":" not in str(rasatlar) and len(str(rasatlar).strip()) >= 5 and SynopDecoder is not None:
            try:
                dec_tmp = SynopDecoder()
                s_data_tmp = dec_tmp.decode_line(str(rasatlar))
                if s_data_tmp:
                    def is_empty(v): return pd.isna(v) or str(v).strip() == ""
                    if is_empty(w1) and 'gecmis_hava1' in s_data_tmp: w1 = _to_float(s_data_tmp['gecmis_hava1'])
                    if is_empty(w2) and 'gecmis_hava2' in s_data_tmp: w2 = _to_float(s_data_tmp['gecmis_hava2'])
                    if is_empty(ww) and 'halihazir_hava' in s_data_tmp: ww = _to_float(s_data_tmp['halihazir_hava'])
                    if is_empty(tr) and 'yagis_suresi_kod' in s_data_tmp: tr = _to_float(s_data_tmp['yagis_suresi_kod'])
                    if is_empty(rrr) and 'yagis_miktari_kod' in s_data_tmp: rrr = _to_float(s_data_tmp['yagis_miktari_kod'])
                    if is_empty(ir) and 'ir' in s_data_tmp: ir = _to_float(s_data_tmp['ir'])
                    if is_empty(ix) and 'ix' in s_data_tmp: ix = _to_float(s_data_tmp['ix'])
                    
                    if is_empty(g960) and 'halihazir_hava_2' in s_data_tmp: g960 = s_data_tmp['halihazir_hava_2']; s['g960'] = g960
                    if is_empty(s.get('g910')) and 'hamle_hizi' in s_data_tmp: s['g910'] = s_data_tmp['hamle_hizi']
                    if is_empty(s.get('g911')) and 'max_ruzgar_hizi' in s_data_tmp: s['g911'] = s_data_tmp['max_ruzgar_hizi']
                    if is_empty(g924) and 'raw_groups' in s_data_tmp and 'deniz_durumu' in s_data_tmp['raw_groups']: g924 = s_data_tmp['raw_groups']['deniz_durumu']; s['g924'] = g924
                    if is_empty(g931) and 'kar_kalinligi_toplam' in s_data_tmp: g931 = s_data_tmp['kar_kalinligi_toplam']; s['g931'] = g931
                    if is_empty(g932) and 'kar_kalinligi_taze' in s_data_tmp: g932 = s_data_tmp['kar_kalinligi_taze']; s['g932'] = g932
            except: pass

        def is_yagis(w):
            try: return (20 <= int(w) <= 27) or (50 <= int(w) <= 99)
            except: return any(k in str(w).upper() for k in ["RA","SN","DZ","GR","GS","SG","PL","UP"])

        def get_dt_suan():
            t_str = s.get("sayfa")
            if pd.isna(t_str) or pd.isna(gmt): return None
            try:
                g, a, y = map(int, str(t_str).split('.'))
                return datetime.datetime(y, a, g, int(gmt))
            except: return None

        def get_metar_history(hours_back):
            dt_s = get_dt_suan()
            if not dt_s: return pd.DataFrame()
            t_str = s.get("sayfa")
            dt_b = dt_s - datetime.timedelta(hours=hours_back)
            p_str = dt_b.strftime('%d.%m.%Y')
            
            ay_degisti = dt_s.month != dt_b.month
            if ay_degisti:
                df_arsiv = get_arsiv_df(dt_b)
                if not df_arsiv.empty and "sayfa" in df_arsiv.columns and "gmt" in df_arsiv.columns:
                    m_prev = (df_arsiv["sayfa"] == p_str) & (df_arsiv["gmt"] >= dt_b.hour)
                    m_curr = (df_metar["sayfa"] == t_str) & (df_metar["gmt"] <= gmt)
                    res = pd.concat([df_arsiv[m_prev], df_metar[m_curr]], ignore_index=True)
                else:
                    res = pd.DataFrame()
            else:
                if dt_b.date() == dt_s.date():
                    res = df_metar[(df_metar["sayfa"] == t_str) & (df_metar["gmt"] >= dt_b.hour) & (df_metar["gmt"] <= gmt)]
                else:
                    m_prev = (df_metar["sayfa"] == p_str) & (df_metar["gmt"] >= dt_b.hour)
                    m_curr = (df_metar["sayfa"] == t_str) & (df_metar["gmt"] <= gmt)
                    res = pd.concat([df_metar[m_prev], df_metar[m_curr]])

            if not res.empty:
                valid_rows = []
                for _, r in res.iterrows():
                    sayfa = r.get("sayfa")
                    gmt_exact = r.get("gmt_exact")
                    actual_dt = None
                    if pd.notna(sayfa) and pd.notna(gmt_exact):
                        try:
                            g, a, y = map(int, str(sayfa).split('.'))
                            rounded_date = datetime.datetime(y, a, g)
                            gmt_exact_str = str(gmt_exact).replace('.0', '').zfill(4)
                            orig_h = int(gmt_exact_str[:2])
                            orig_m = int(gmt_exact_str[2:])
                            rounded_h = int(r.get("gmt", 0))
                            
                            if orig_h == 23 and rounded_h == 0:
                                actual_date = rounded_date - datetime.timedelta(days=1)
                            else:
                                actual_date = rounded_date
                                
                            actual_dt = actual_date.replace(hour=orig_h, minute=orig_m)
                        except:
                            pass
                    
                    def clear_boundary_re(row):
                        row = row.copy()
                        if pd.notna(row.get("bulten")):
                            row["bulten"] = re.sub(r'\bRE[A-Z]{2,}\b', '', str(row["bulten"]))
                            row["bulten"] = re.sub(r'\s+', ' ', row["bulten"]).strip()
                        for c_ww in ["ww", "ww2", "ww3"]:
                            if c_ww in row and pd.notna(row[c_ww]):
                                w_val = row[c_ww]
                                try:
                                    if 20 <= int(w_val) <= 29:
                                        row[c_ww] = float('nan')
                                except:
                                    if str(w_val).upper().startswith("RE"):
                                        row[c_ww] = float('nan')
                        return row

                    if actual_dt:
                        # DÜZELTME: Önceki periyoda ait (örn 18:00 rasadı için 11:50Z) METAR'ları dışla. Sadece dt_b'den BÜYÜK olanları al.
                        if actual_dt > dt_b and actual_dt <= dt_s:
                            valid_rows.append(r)
                    else:
                        r_gmt = r.get("gmt")
                        if pd.notna(r_gmt) and int(r_gmt) == dt_b.hour:
                            r = clear_boundary_re(r)
                            valid_rows.append(r)
                        
                return pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame()
            return res

        def get_sinoptik_prev(hours_back):
            dt_s = get_dt_suan()
            if not dt_s: return pd.DataFrame()
            dt_prev = dt_s - datetime.timedelta(hours=hours_back)
            p_str = dt_prev.strftime('%d.%m.%Y')
            sonuc = birlesik_df[(birlesik_df["sayfa"] == p_str) & (birlesik_df["gmt"] == dt_prev.hour)]
            if sonuc.empty and dt_s.month != dt_prev.month:
                df_arsiv = get_arsiv_df(dt_prev)
                if not df_arsiv.empty and "sayfa" in df_arsiv.columns and "gmt" in df_arsiv.columns:
                    sonuc = df_arsiv[(df_arsiv["sayfa"] == p_str) & (df_arsiv["gmt"] == dt_prev.hour)]
            return sonuc

        def vv_to_meters(vv_val):
            try:
                v = float(vv_val)
                if v <= 50: return v * 100
                elif 56 <= v <= 80: return (v - 50) * 1000
                elif 81 <= v <= 89: return 30000 + (v - 80) * 5000
                elif v == 90: return 0
                elif v == 91: return 50
                elif v == 92: return 200
                elif v == 93: return 500
                elif v == 94: return 1000
                elif v == 95: return 2000
                elif v == 96: return 4000
                elif v == 97: return 10000
                elif v == 98: return 20000
                elif v == 99: return 50000
            except: pass
            return -1

        def clean_trend(m):
            if pd.isna(m): return ""
            return re.split(r'\b(TEMPO|BECMG|NOSIG|RMK|PROB\d{2})\b', str(m).upper())[0].strip()

        def is_yagis(w):
            try: return (20 <= int(w) <= 27) or (50 <= int(w) <= 99)
            except: 
                cw = clean_trend(w)
                return bool(re.search(r'(?:^|\s)(RE|-|\+|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?(RA|SN|DZ|GR|GS|SG|PL|UP|SH)(?:\s|$)', cw))

        def is_sis(w):
            try: return 40 <= int(w) <= 49
            except: 
                cw = clean_trend(w)
                return bool(re.search(r'(?:^|\s)(RE|-|\+|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?(FG)(?:\s|$)', cw))

        def is_oraj(w):
            try: return int(w) in [17, 29] or (95 <= int(w) <= 99)
            except: 
                cw = clean_trend(w)
                return bool(re.search(r'(?:^|\s)(RE|-|\+|VC)?(TS)(RA|SN|DZ|GR|GS|SG|PL|UP|FG|BR|HZ|SA|DU)?(?:\s|$)', cw))

        def is_dolu(w):
            try: return int(w) in [87, 88, 89, 90, 93, 94, 96, 99]
            except: 
                cw = clean_trend(w)
                return bool(re.search(r'(?:^|\s)(RE|-|\+|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?(GR|GS)(?:\s|$)', cw))

        def is_tozkum_firtinasi(w):
            try: return 30 <= int(w) <= 35
            except: 
                cw = clean_trend(w)
                return bool(re.search(r'(?:^|\s)(RE|-|\+|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?(SS|DS)(?:\s|$)', cw))

        # h4: İr=1 olduğu halde yağış grubu kodlanmamış
        if ir == 1 and pd.isna(rrr):
            msg = hata_dict.get("h4", "İr=1 olduğu halde yağış grubu kodlanmamış")
            
            yagis_var_mi = False
            kanitlar = []

            # 1. Sinoptik Geçmiş Hava (W1, W2) Kontrolü (W1/W2=9 Orajdır, yağış zorunlu değildir)
            try:
                if (pd.notna(w1) and 5 <= int(w1) <= 8) or (pd.notna(w2) and 5 <= int(w2) <= 8):
                    yagis_var_mi = True
                    kanitlar.append("Sinoptik W1/W2")
            except: pass

            # 2. METAR Kontrolü (Son 6 saat)
            try:
                ww_col = "ww" if "ww" in df_metar.columns else None
                if ww_col:
                    lookback = 6 if gmt in [0, 12] else (12 if gmt == 18 else (24 if gmt == 6 else 3))
                    for w in get_metar_history(lookback)[ww_col]:
                        if is_yagis(w):
                            yagis_var_mi = True
                            kanitlar.append(f"METAR ww={w}")
                            break
            except Exception: pass

            if yagis_var_mi:
                msg += f" (TEYİTLİ: {', '.join(kanitlar)} var -> RRR girilmeli)"
                kodlar.append("h4 (TEYİTLİ)")
            else:
                msg += " (DİKKAT: Geçmişte yağış kaydı/METAR bulunamadı, İr=1 hatalı olabilir)"
                kodlar.append("h4 (DİKKAT)")
            aciklamalar.append(msg)
        
        # WMO Kuralları: Ana ve Ara Rasat İr/Yağış Grubu (6RRRtR) Katı Kontrolleri
        if gmt in [0, 6, 12, 18]:
            if pd.notna(ir) and ir != 1:
                kodlar.append("h7")
                aciklamalar.append(f"Ana sinoptik saatlerde (0000, 0600, 1200, 1800 GMT) 6. grup zorunlu olduğu için İr=1 olarak kodlanmalıdır (Girilen: İr={int(ir)}).")
            if pd.isna(rrr):
                kodlar.append("h383")
                aciklamalar.append("Ana sinoptik saatlerde (0000, 0600, 1200, 1800 GMT) yağış olsun veya olmasın 6RRRtR grubu mutlaka rapora dahil edilmelidir (Yağış yoksa RRR=000).")
        elif gmt in [3, 9, 15, 21]:
            if pd.notna(ir) and ir != 4:
                kodlar.append("h2")
                aciklamalar.append(f"Ara rasatlarda (03, 09, 15, 21 GMT) 6. grup koda dahil edilmediği için İr=4 olmalıdır (Girilen: İr={int(ir)}).")
            if pd.notna(rrr):
                kodlar.append("h6")
                aciklamalar.append("Ara rasatlarda (03, 09, 15, 21 GMT) 6RRRtR grubu koda dahil edilmez.")

        # h5: İr=3 olduğu halde yağış grubu kodlanmış
        if ir == 3 and pd.notna(rrr):
            kodlar.append("h5")
            aciklamalar.append(hata_dict.get("h5"))

        # h3: İr grubu hatalı
        if pd.notna(ir) and ir not in [0, 1, 2, 3, 4]:
            kodlar.append("h3")
            aciklamalar.append(hata_dict.get("h3"))

        # h8: İndikatör hatalı
        if (pd.notna(ir) and ir not in [0,1,2,3,4]) or (pd.notna(ix) and ix not in [1,2,3]):
            kodlar.append("h8")
            aciklamalar.append(hata_dict.get("h8"))
        
        # h17: h hatalı
        if pd.notna(h) and not (0 <= h <= 9):
            kodlar.append("h17")
            aciklamalar.append(hata_dict.get("h17"))

        # h22: Görüş kodu hatalı
        if pd.notna(vv):
            if not (0 <= vv <= 99):
                kodlar.append("h22")
                aciklamalar.append(hata_dict.get("h22"))
            elif 70 < vv < 90:
                kodlar.append("h22")
                aciklamalar.append("Maksimum görüş mesafesi 20 km (VV=70) olarak kodlanmalıdır. (71-89 arası kodlar kullanılmaz)")

        # h26: N=0 iken bulut grubu verilmiş
        if n == 0 and ((pd.notna(nh) and nh > 0) or (pd.notna(cl) and cl > 0) or (pd.notna(cm) and cm > 0) or (pd.notna(ch) and ch > 0)):
            kodlar.append("h26")
            aciklamalar.append(hata_dict.get("h26"))

        # h27: Bulut grubu yok ama N > 0
        if pd.isna(nh) and pd.isna(cl) and pd.isna(cm) and pd.isna(ch) and pd.notna(n) and n > 0 and n != 9:
            kodlar.append("h27")
            aciklamalar.append(hata_dict.get("h27"))

        # h36: Toplam kapalılık ölçülemedi (/) iken bulut katmanları (Nh, CL vb.) girilmiş
        if pd.isna(n) and (pd.notna(nh) or pd.notna(cl) or pd.notna(cm) or pd.notna(ch)):
            kodlar.append("h36")
            aciklamalar.append(hata_dict.get("h36", "Toplam kapalılık '/' (veya boş) olarak kodlanmış, ancak alt bulut grupları girilmiş."))

        # h30: h=/ (NaN) iken N!=9
        if pd.isna(h) and pd.notna(n) and n != 9:
            if (pd.notna(cl) and cl > 0) or (pd.notna(cm) and cm > 0):
                # İstisna: METAR'da ölçülemeyen bulut yüksekliği (///) varsa h30 tolere edilebilir.
                bulten_msg = s.get("bulten_metar") if pd.notna(s.get("bulten_metar")) else s.get("bulten")
                metar_h_bilinmiyor = False
                if pd.notna(bulten_msg):
                    ilk_bulut = re.search(r'\b(FEW|SCT|BKN|OVC|VV)(///|\d{3})', clean_trend(bulten_msg))
                    if ilk_bulut and ilk_bulut.group(2) == '///':
                        metar_h_bilinmiyor = True
                
                if not metar_h_bilinmiyor:
                    kodlar.append("h30")
                    aciklamalar.append(hata_dict.get("h30"))

        # h31: h var iken N=9
        if pd.notna(h) and n == 9:
            kodlar.append("h31")
            aciklamalar.append(hata_dict.get("h31"))
            
        # --- BULUT YÜKSEKLİĞİ (h) VE GÖRÜŞ (vv) MANTIK KONTROLLERİ ---
        if pd.notna(h):
            # h167: Alçak bulut (CL) varsa, tabanı çok yüksek olamaz (h=9 olamaz)
            if pd.notna(cl) and cl > 0:
                if h == 9:
                    if "h167" not in kodlar:
                        kodlar.append("h167")
                        aciklamalar.append(hata_dict.get("h167", "Alçak bulut (CL) varken bulut yüksekliği (h) 9 kodlanamaz."))

            # h168: Sadece Orta Bulut (CM) varsa, yükseklik çok düşük (0-300m) olamaz (h=0,1,2 olamaz)
            if (pd.isna(cl) or cl == 0) and pd.notna(cm) and cm > 0:
                if h < 3:
                    if "h168" not in kodlar:
                        kodlar.append("h168")
                        aciklamalar.append(hata_dict.get("h168", "Sadece Orta Bulut (CM) varken bulut yüksekliği (h) 0, 1, 2 kodlanamaz."))

            # h170: Sadece Yüksek Bulut (CH) varsa, yükseklik 9 (>= 2500m) olmalıdır
            if (pd.isna(cl) or cl == 0) and (pd.isna(cm) or cm == 0) and pd.notna(ch) and ch > 0:
                if h != 9:
                    if "h170" not in kodlar:
                        kodlar.append("h170")
                        aciklamalar.append(hata_dict.get("h170", "Sadece Yüksek Bulut (CH) varken bulut yüksekliği (h) 9 kodlanmalıdır."))

        # --- N=9 (GÖKYÜZÜ GÖRÜNMÜYOR) TAM KAPSAMLI KONTROLLERİ ---
        if pd.notna(n) and n == 9:
            # h32: N=9 iken Nh=9 kodlanmamış
            if pd.isna(nh) or nh != 9:
                kodlar.append("h32")
                aciklamalar.append(hata_dict.get("h32", "Gökyüzü görünmüyor (N=9) iken Alçak/Orta Bulut Kapalılığı (Nh) da 9 olmalıdır."))
            
            # h33: N=9 iken C=/ kodlanmamış (Bulut cinsleri boş olmalıdır)
            if pd.notna(cl) or pd.notna(cm) or pd.notna(ch):
                kodlar.append("h33")
                aciklamalar.append(hata_dict.get("h33", "N=9 iken bulut cinsleri (CL, CM, CH) değerlendirilemez, boş bırakılmalıdır."))
                
            # Dikine Görüş (h) ve Yatay Görüş (VV) Uyumsuzluğu
            if pd.notna(h):
                if h == 9:
                    kodlar.append("h311")
                    aciklamalar.append("Gökyüzü görünmüyor (N=9) iken dikine görüşü temsil eden 'h' değeri 9 (>2500m) olamaz.")
                elif pd.notna(vv) and vv < 10 and h >= 3:
                    if "h172" not in kodlar:
                        kodlar.append("h172")
                        aciklamalar.append(hata_dict.get("h172", "Dikine rüyet için verilen yükseklik çok fazla.") + f" (Yatay Görüş < 1km iken dikine görüş h={int(h)} verilmiş)")

            # Gökyüzü Görünmüyor İse Yatay Görüş Düşük Olmalı ve Kapatıcı Hadise (ww) Raporlanmalıdır
            gorus_dusuk_mu = pd.notna(vv) and vv < 50  # VV<50 kodu (5km altı)
            kapatici_hadise_var = False
            
            if pd.notna(ww):
                try:
                    w_int = int(ww)
                    if (40 <= w_int <= 49) or (70 <= w_int <= 79) or (30 <= w_int <= 39) or w_int in [4, 5, 8]:
                        kapatici_hadise_var = True
                except:
                    pass
                    
            if not gorus_dusuk_mu and pd.notna(vv):
                kodlar.append("h312")
                aciklamalar.append(f"Gökyüzü görünmüyor (N=9) olarak kodlanmış ancak yatay görüş mesafesi oldukça yüksek (VV={int(vv)}).")
                
            if not kapatici_hadise_var and (pd.isna(ww) or ww < 4):
                kodlar.append("h313")
                aciklamalar.append("N=9 (Gökyüzü görünmüyor) olarak kodlanmış ancak gökyüzünü kapatacak bir hadise (Sis, Yoğun Kar, Kum Fırtınası vb.) raporlanmamış.")
                
        # Ters Mantık: Nh=9 iken N!=9 olamaz
        if pd.notna(nh) and nh == 9 and (pd.isna(n) or n != 9):
            kodlar.append("h314")
            aciklamalar.append("Alçak/Orta Bulut kapalılığı görünmüyor (Nh=9) iken Toplam Bulut Kapalılığı (N) da 9 olmalıdır.")

        # h34 & h120: Toplam kapalılık ile bulut kapalılığı uyumsuz (Nh > N olamaz)
        if pd.notna(n) and pd.notna(nh) and n != 9 and nh != 9 and nh > n:
            if "h34" not in kodlar:
                kodlar.append("h34")
                aciklamalar.append(hata_dict.get("h34", "Toplam kapalılık (N) ile bulut kapalılığı (Nh) uyumsuz (Her zaman N >= Nh olmalıdır)."))
            if "h120" not in kodlar:
                kodlar.append("h120")
                aciklamalar.append(hata_dict.get("h120", "Alçak/Orta bulut toplam kapalığı (Nh), Toplam kapalılıktan (N) büyük olamaz."))

        # --- 8NhCLCMCH (1-3-5 KURALI VE BULUT GRUBU KONTROLLERİ) ---
        if pd.notna(n) and 0 < n < 9:
            # 1. Sadece Yüksek Bulut (CH) varsa, Alçak (CL) ve Orta (CM) yoksa Nh kesinlikle 0 olmalıdır.
            if pd.notna(ch) and ch > 0 and (pd.isna(cl) or cl == 0) and (pd.isna(cm) or cm == 0):
                if pd.notna(nh) and nh > 0:
                    kodlar.append("h154")
                    aciklamalar.append(hata_dict.get("h154", "1-3-5 Kuralı: Sadece CH bulutu varken Nh=0 olmalıdır."))

            # 2. Sadece tek katman Alçak Bulut (CL) varsa ve başka bulut yoksa Nh, toplam kapalılığa (N) eşit olmalıdır.
            if pd.notna(cl) and cl > 0 and (pd.isna(cm) or cm == 0) and (pd.isna(ch) or ch == 0):
                if pd.notna(nh) and nh != n:
                    kodlar.append("h154")
                    aciklamalar.append(hata_dict.get("h154", "1-3-5 Kuralı: Sadece CL bulutu varken Nh değeri, N (Toplam Kapalılık) ile eşit olmalıdır."))

            # 3. Nh = 0 iken CL veya CM raporlanmışsa (Mantık Hatası)
            if pd.notna(nh) and nh == 0:
                if pd.notna(cl) and cl > 0: kodlar.append("h135"); aciklamalar.append(hata_dict.get("h135"))
                elif pd.notna(cm) and cm > 0: kodlar.append("h139"); aciklamalar.append(hata_dict.get("h139"))

            # 4. Nh > 0 iken CL ve CM raporlanmamışsa (Bulut cinsi eksik)
            if pd.notna(nh) and nh > 0:
                if (pd.isna(cl) or cl == 0) and (pd.isna(cm) or cm == 0):
                    kodlar.append("h134"); aciklamalar.append(hata_dict.get("h134"))
                    
        # --- BULUT CİNSİ VE KAPALILIK UYUMSUZLUKLARI (h121 - h133) ---
        if pd.notna(n):
            # h121: Yüksek bulutlarda alçak bulut toplam kapalılığı 0 olur
            if pd.notna(ch) and ch > 0 and (pd.isna(cl) or cl == 0) and (pd.isna(cm) or cm == 0):
                if pd.notna(nh) and nh > 0:
                    if "h121" not in kodlar:
                        kodlar.append("h121")
                        aciklamalar.append(hata_dict.get("h121", "Yüksek bulutlarda alçak bulut toplam kapalılığı 0 olur."))

            # h125: Bulut cinsleri koda dahil edilmemiş
            if 0 < n < 9:
                if pd.isna(cl) and pd.isna(cm) and pd.isna(ch):
                    if "h125" not in kodlar:
                        kodlar.append("h125")
                        aciklamalar.append(hata_dict.get("h125", "Bulut cinsleri koda dahil edilmemiş."))

            # h128, h132: Cb Bulutu ve CL=3,9 Uyumsuzluğu (METAR Bülteni veya Hadise üzerinden)
            bulten_msg = ""
            bulten_col = "bulten" if "bulten" in df_metar.columns else None
            if bulten_col:
                try:
                    m_row = df_metar[(df_metar["sayfa"] == s.get("sayfa")) & (df_metar["gmt"] == gmt)]
                    if not m_row.empty:
                        bulten_msg = clean_trend(m_row[bulten_col].values[0])
                except: pass

            hadise_str = str(hadise_kayit).upper() if pd.notna(hadise_kayit) else ""
            cb_var = "CB" in bulten_msg or "CB" in hadise_str
            
            if pd.notna(cl):
                if cl in [3, 9] and not cb_var:
                    if "h128" not in kodlar:
                        kodlar.append("h128")
                        aciklamalar.append(hata_dict.get("h128", "CL=3 veya 9 verilmiş fakat Cb bulutu verilmemiş."))
                
                if cl not in [3, 9] and cb_var:
                    if "h132" not in kodlar:
                        kodlar.append("h132")
                        aciklamalar.append(hata_dict.get("h132", "Cb bulutu verilmiş fakat CL=9 veya 3 verilmemiş."))

        # --- YENİ EKLENEN BULUT (CL, CM, CH) UYUMSUZLUK KURALLARI ---
        if pd.notna(n) and n <= 8:
            # h155: Cu (CL=1 veya 2) havayı 8/8 kapatmaz. (Sadece Cu varken Nh=8 olamaz)
            if pd.notna(cl) and cl in [1, 2] and pd.notna(nh) and nh == 8:
                if (pd.isna(cm) or cm == 0) and (pd.isna(ch) or ch == 0):
                    kodlar.append("h155")
                    aciklamalar.append(hata_dict.get("h155", "Cu havayı 8/8 kapatmaz."))
            
            # h164: As veya Ns (CM=1 veya 2) gökyüzünü 6/8'den az kapatamaz. (N >= 6 olmalıdır)
            if pd.notna(cm) and cm in [1, 2] and n < 6:
                kodlar.append("h164")
                aciklamalar.append(hata_dict.get("h164", "As veya Ns gökyüzünü 6/8 den az kapatamaz."))

            # h151: CH=7 (Cs) kodlanmış ancak toplam kapalılık (N) 8/8 değil.
            if pd.notna(ch) and ch == 7 and n < 8:
                kodlar.append("h151")
                aciklamalar.append(hata_dict.get("h151", "Cs'nin cinsi 7 verilmiş fakat 8/8 kapatmamış."))
            
            # h152: Yalnızca Cs var ve gökyüzünü 8/8 kapatmış (N=8), fakat cinsi 7 verilmemiş (CH!=7)
            if pd.notna(ch) and ch in [5, 6, 8] and n == 8 and (pd.isna(cl) or cl == 0) and (pd.isna(cm) or cm == 0):
                kodlar.append("h152")
                aciklamalar.append(hata_dict.get("h152", "Cs 8/8 kapatmış fakat cinsi 7 verilmemiş."))

        # h37: dd kıstas dışı
        if pd.notna(dd) and not ((0 <= dd <= 36) or dd == 99):
            kodlar.append("h37")
            aciklamalar.append(hata_dict.get("h37"))
            
        # Rüzgar yönü değişken (99) ise rüzgar hızı hafif (<= 5) olmalıdır
        if pd.notna(dd) and dd == 99:
            if pd.notna(ff) and ff > 5:
                kodlar.append("h375")
                aciklamalar.append("WMO Kuralı: Rüzgar yönü değişken (dd=99) iken rüzgar hızı 5 knot'tan büyük olamaz.")

        # h38: dd=00 iken ff!=00
        if dd == 0 and pd.notna(ff) and ff > 0:
            kodlar.append("h38")
            aciklamalar.append(hata_dict.get("h38"))

        # h39: dd!=00 iken ff=00
        if pd.notna(dd) and dd != 0 and pd.notna(ff) and ff == 0:
            kodlar.append("h39")
            aciklamalar.append(hata_dict.get("h39"))

        # h43: ff=00 iken dd yön verilmiş
        if ff == 0 and pd.notna(dd) and dd > 0:
            kodlar.append("h43")
            aciklamalar.append(hata_dict.get("h43"))

        # h44: Rüzgar hızı limit dışı
        if pd.notna(ff) and ff > 100:
            kodlar.append("h44")
            aciklamalar.append(hata_dict.get("h44"))

        # h238: Hamle verilmesi için 10Kt ve daha fazla fark olmalı (910/911 Grubu)
        g910_val = s.get("g910")
        g911_val = s.get("g911")
        for g_val in [g910_val, g911_val]:
            if pd.notna(g_val) and pd.notna(ff):
                try:
                    g_str = str(int(g_val))
                    if len(g_str) == 5 and (g_str.startswith("910") or g_str.startswith("911")):
                        gust = int(g_str[-2:])
                    else:
                        gust = int(g_val)
                    
                    # KULLANICI İSTEĞİ: SİNOPTİK'te hamle için 10kt fark kuralı aranmaz (Bu METAR kuralıdır)
                    # if gust < ff + 10:
                    #     if "h238" not in kodlar:
                    #         kodlar.append("h238")
                    #         aciklamalar.append(hata_dict.get("h238") + f" (Ortalama Hız: {int(ff)} kt, Hamle: {gust} kt)")
                    
                    if gust > 100:
                        if "h239" not in kodlar:
                            kodlar.append("h239")
                            aciklamalar.append(hata_dict.get("h239", "Hamle için çok yüksek bir değer") + f" ({gust} kt)")
                except: pass

        # Sıcaklık Limitleri
        for val, code in [(t, "h48"), (td, "h53"), (tx, "h187"), (tn, "h193")]:
            if pd.notna(val) and (val < -50 or val > 60):
                kodlar.append(code)
                aciklamalar.append(hata_dict.get(code))
                
        # Sıcaklık 12 saatlik geçmiş kontrolü (h185, h191)
        if pd.notna(tx) or pd.notna(tn):
            try:
                gecmis_tler = []
                for h_delta in range(0, 13, 3): # 0, 3, 6, 9, 12 saat öncesi
                    hedef_row = get_sinoptik_prev(h_delta)
                    if not hedef_row.empty:
                        t_col = "t" if "t" in hedef_row.columns else "t_sin" if "t_sin" in hedef_row.columns else None
                        if t_col and pd.notna(hedef_row[t_col].values[0]):
                            gecmis_tler.append(float(hedef_row[t_col].values[0]))
                    
                    if gecmis_tler:
                        max_t_12h = max(gecmis_tler)
                        min_t_12h = min(gecmis_tler)
                        
                        if pd.notna(tx) and tx < max_t_12h:
                            if "h185" not in kodlar:
                                kodlar.append("h185")
                                aciklamalar.append(hata_dict.get("h185", "Maksimum sıcaklık son 12 saatteki sıcaklıktan düşük olamaz") + f" (Tx: {tx}°C, 12s Max T: {max_t_12h}°C)")
                                
                        if pd.notna(tn) and tn > min_t_12h:
                            if "h191" not in kodlar:
                                kodlar.append("h191")
                                aciklamalar.append(hata_dict.get("h191", "Minumum sıcaklık son 12 saatteki sıcaklıktan büyük olamaz") + f" (Tn: {tn}°C, 12s Min T: {min_t_12h}°C)")
            except Exception: pass

        # h52: İşba sıcaklığı (td), kuru termometre sıcaklığından (t) büyük olamaz
        if pd.notna(t) and pd.notna(td) and td > t:
            if "h52" not in kodlar:
                kodlar.append("h52")
                aciklamalar.append(hata_dict.get("h52", "İşba sıcaklığı kuru termometre sıcaklığından büyük olamaz"))
                
        # Toprak sıcaklığı (Tg) ile Minimum sıcaklık (Tn) Mantık Kontrolü
        if pd.notna(tg) and pd.notna(tn):
            if tg > tn:
                kodlar.append("h267")
                aciklamalar.append(hata_dict.get("h267", "Toprak minimum sıcaklığı (Tg), havadaki minimum sıcaklıktan (Tn) büyük olamaz (Tg <= Tn olmalıdır)."))

        # Basınç Limitleri
        for val, code in [(p, "h55"), (p0, "h58")]:
            if pd.notna(val) and (val < 800 or val > 1100):
                kodlar.append(code)
                aciklamalar.append(hata_dict.get(code))

        # Buharlaşma ve Güneşlenme Limitleri
        if gunes is not None:
            try:
                if float(str(gunes).replace(',', '.')) > 16.0:
                    kodlar.append("h220")
                    aciklamalar.append(hata_dict.get("h220", "Güneşlenme süresi çok fazla"))
            except: pass

        if buhar is not None:
            try:
                if float(str(buhar).replace(',', '.')) > 30.0:
                    kodlar.append("h214")
                    aciklamalar.append(hata_dict.get("h214", "Buharlaşma miktarı çok fazla"))
            except: pass

        # h61: Tandans karakteristiği 9 olamaz
        if a == 9:
            kodlar.append("h61")
            aciklamalar.append(hata_dict.get("h61"))

        # h63: Tandans karakteri 4 iken değişim 0 olur
        if a == 4 and pd.notna(ppp) and ppp != 0:
            kodlar.append("h63")
            aciklamalar.append(hata_dict.get("h63"))

        # h62: a!=0,4,5 iken ppp=0
        if pd.notna(a) and a not in [0, 4, 5] and pd.notna(ppp) and ppp == 0:
            kodlar.append("h62")
            aciklamalar.append(hata_dict.get("h62"))

        # h64: ppp çok fazla
        if pd.notna(ppp) and ppp > 20:
            kodlar.append("h64")
            aciklamalar.append(hata_dict.get("h64"))
            
        # h65 ve h66: Tandans (ppp) ve Karakteristik (a) 3 saat önceki basınçla uyum kontrolü
        p_current = p if pd.notna(p) else p0
        if pd.notna(p_current) and pd.notna(ppp) and pd.notna(a):
            try:
                prev_row = get_sinoptik_prev(3)
                if not prev_row.empty:
                        p_col = "p" if "p" in prev_row.columns else "p_sin" if "p_sin" in prev_row.columns else None
                        p0_col = "p0" if "p0" in prev_row.columns else "p0_sin" if "p0_sin" in prev_row.columns else None
                        
                        prev_p_val = None
                        if p_col and pd.notna(prev_row[p_col].values[0]): prev_p_val = prev_row[p_col].values[0]
                        elif p0_col and pd.notna(prev_row[p0_col].values[0]): prev_p_val = prev_row[p0_col].values[0]
                        
                        if pd.notna(prev_p_val):
                            diff = float(p_current) - float(prev_p_val)
                            
                            if abs(abs(diff) - float(ppp)) > 0.4:
                                kodlar.append("h65")
                                aciklamalar.append(hata_dict.get("h65", "Tandans değişimi 3 saat önceki basınçla uyumsuz") + f" (Fark: {abs(diff):.1f} hPa, ppp: {ppp} hPa)")
                            
                            a_int = int(a)
                            if a_int in [0, 1, 2, 3] and diff < -0.2:
                                kodlar.append("h66")
                                aciklamalar.append(hata_dict.get("h66", "Tandans değişimi tandans karakteri ile uyumsuz") + f" (a={a_int} [Artış/Aynı] ama basınç düştü)")
                            elif a_int in [5, 6, 7, 8] and diff > 0.2:
                                kodlar.append("h66")
                                aciklamalar.append(hata_dict.get("h66", "Tandans değişimi tandans karakteri ile uyumsuz") + f" (a={a_int} [Düşüş] ama basınç arttı)")
            except Exception: pass

        # h70: Yağış miktarı 000 kodlanmaz
        # h70 & h376: Yağış miktarı 000 kodlanmaz (Özel İstisna: 60001/60002)
        if pd.notna(rrr) and rrr == 0:
            if gmt in [0, 12]:
                if pd.notna(tr) and int(tr) != 1:
                    kodlar.append("h376")
                    aciklamalar.append(f"0000 ve 1200 GMT rasatlarında yağış yoksa 60001 kodlanmalıdır (Girilen: 6000{int(tr)}).")
                elif pd.isna(tr):
                    kodlar.append("h376")
                    aciklamalar.append("0000 ve 1200 GMT rasatlarında yağış yoksa 60001 kodlanmalıdır (tR eksik).")
            elif gmt in [6, 18]:
                if pd.notna(tr) and int(tr) != 2:
                    kodlar.append("h376")
                    aciklamalar.append(f"0600 ve 1800 GMT rasatlarında yağış yoksa 60002 kodlanmalıdır (Girilen: 6000{int(tr)}).")
                elif pd.isna(tr):
                    kodlar.append("h376")
                    aciklamalar.append("0600 ve 1800 GMT rasatlarında yağış yoksa 60002 kodlanmalıdır (tR eksik).")
            else:
                kodlar.append("h70")
                aciklamalar.append("Ara rasatlarda (03, 09, 15, 21Z) yağış miktarı 000 (rrr=0) kodlanmaz.")

        # h71: RRR çok fazla (990-999 arası değerler eser/ondalıklı miktar olduğu için hariç tutulur)
        if pd.notna(rrr) and rrr > 400 and not (990 <= rrr <= 999):
            kodlar.append("h71")
            aciklamalar.append(hata_dict.get("h71"))

        # h74: tR kontrolü
        if pd.notna(tr) and not (0 <= tr <= 9):
            kodlar.append("h74")
            aciklamalar.append(hata_dict.get("h74"))
        else:
            tr_val = int(tr) if pd.notna(tr) else None
            if gmt in [0, 12] and pd.notna(rrr):
                if tr_val != 1 and "h376" not in kodlar:
                    kodlar.append("h376")
                    aciklamalar.append(f"0000 ve 1200 GMT ana rasatlarında 6 saatlik yağış ölçümü için tR=1 olmalıdır. (Girilen: {tr_val if tr_val is not None else 'Eksik'})")
            elif gmt in [6, 18] and pd.notna(rrr):
                if tr_val != 2 and "h376" not in kodlar:
                    kodlar.append("h376")
                    aciklamalar.append(f"0600 ve 1800 GMT ana rasatlarında 12 saatlik yağış ölçümü için tR=2 olmalıdır. (Girilen: {tr_val if tr_val is not None else 'Eksik'})")

        # Ayın 1'i ve 00Z durumu (Bazı kontrollerde istisna)
        is_ayin_biri_00z = False
        if gmt in [0, 0.0]:
            tarih_str = str(s.get("sayfa", ""))
            if tarih_str.startswith("01.") or tarih_str.startswith("1."):
                is_ayin_biri_00z = True

        # h76: Hadise yok ama RRR var (Ana Sinoptikte RRR varsa geçmişte veya METAR'da yağış aranmalı)
        if pd.notna(rrr) and rrr > 0 and not is_ayin_biri_00z:
            yagis_kaniti = False
            
            # 1. Halihazır (ww) yağış mı?
            if pd.notna(ww) and ((20 <= ww <= 27) or ww == 29 or (50 <= ww <= 99)):
                yagis_kaniti = True
                
            # 2. Geçmiş Hava (W1, W2) yağış mı?
            if pd.notna(w1) and w1 >= 5: yagis_kaniti = True
            if pd.notna(w2) and w2 >= 5: yagis_kaniti = True
            
            # 3. METAR ve Geçmiş Sinoptik kontrolü
            if not yagis_kaniti:
                try:
                    lookback_h76 = 6 if gmt in [0, 6, 12, 18] else 3
                    metar_kesit_h76 = get_metar_history(lookback_h76)
                    ww_cols_h76 = [c for c in ["ww", "ww2", "ww3"] if c in df_metar.columns]
                    if ww_cols_h76:
                        if any(is_yagis(w) for c_ww in ww_cols_h76 for w in metar_kesit_h76[c_ww]):
                            yagis_kaniti = True
                            
                    bulten_col = "bulten" if "bulten" in df_metar.columns else None
                    if not yagis_kaniti and bulten_col and not metar_kesit_h76.empty:
                        if any(pd.notna(msg) and re.search(r'\b(\+|-|VC|RE)?(SH|FZ)?(RA|SN|DZ|GR|GS|SG|PL|UP)\b', clean_trend(msg)) for msg in metar_kesit_h76[bulten_col]):
                            yagis_kaniti = True
                            
                    if not yagis_kaniti and gmt in [0, 6, 12, 18]:
                        ara_sinoptik = get_sinoptik_prev(3)
                        if not ara_sinoptik.empty:
                            ara_rrr_col = "rrr" if "rrr" in ara_sinoptik.columns else "rrr_sin" if "rrr_sin" in ara_sinoptik.columns else None
                            if ara_rrr_col and pd.notna(ara_sinoptik[ara_rrr_col].values[0]):
                                if float(ara_sinoptik[ara_rrr_col].values[0]) > 0:
                                    yagis_kaniti = True
                            ara_ww = ara_sinoptik["ww"].values[0] if "ww" in ara_sinoptik.columns else (ara_sinoptik["ww_sin"].values[0] if "ww_sin" in ara_sinoptik.columns else None)
                            if pd.notna(ara_ww) and is_yagis(ara_ww):
                                yagis_kaniti = True
                except:
                    pass

            if not yagis_kaniti:
                if pd.notna(ww) and ww < 4:
                    kodlar.append("h76")
                    aciklamalar.append(hata_dict.get("h76") + " (Geçmiş METAR veya Ara Sinoptik'te de yağış bulunamadı.)")
                else:
                    kodlar.append("h315")
                    aciklamalar.append("Yağış miktarı (RRR) kodlanmış ancak Halihazır (ww) veya Geçmiş Hava (W1, W2) gruplarında yağış işlenmemiş, ayrıca geçmiş METAR/Sinoptik'lerde de yağış bulunamadı.")
                    
        # h72: 6 saat önce yağış olduğu halde bu saatte yağış miktarı verilmedi.
        if pd.isna(rrr) and gmt in [0, 6, 12, 18]:
            try:
                prev_row = get_sinoptik_prev(6)
                if not prev_row.empty:
                        p_ww = prev_row["ww"].values[0] if "ww" in prev_row.columns else None
                        p_w1 = prev_row["w1"].values[0] if "w1" in prev_row.columns else None
                        p_w2 = prev_row["w2"].values[0] if "w2" in prev_row.columns else None
                        
                        gecmis_yagis_var = False
                        if pd.notna(p_ww) and ((20 <= p_ww <= 27) or (50 <= p_ww <= 99)): gecmis_yagis_var = True
                        if pd.notna(p_w1) and 5 <= p_w1 <= 8: gecmis_yagis_var = True
                        if pd.notna(p_w2) and 5 <= p_w2 <= 8: gecmis_yagis_var = True
                        
                        if gecmis_yagis_var:
                            if "h72" not in kodlar:
                                kodlar.append("h72")
                                aciklamalar.append(hata_dict.get("h72", "6 saat önce yağış olduğu halde bu saatte yağış miktarı verilmedi."))
            except Exception: pass
            
        # h73: Hadise kaydında yağış olduğu halde bu saatte yağış miktarı verilmedi veya yağış verildiği halde Hadise kaydı yapılmadı.
        hadise_str = str(hadise_kayit).upper().replace(",", " ").replace(".", " ") if pd.notna(hadise_kayit) else ""
        hadise_str = " " + hadise_str + " " # Kelime sınırlarını belirlemek için boşluk ekle
        yagis_kelimeleri = [" YAĞ", " YAG", " KAR", " ÇİS", " CIS", " DOLU", " SAĞ", " SAG", " RA ", " SN ", " DZ ", " GR ", " GS ", " SG ", " PL "]
        hadise_yagis_var = any(k in hadise_str for k in yagis_kelimeleri)
        
        if pd.isna(rrr) and hadise_yagis_var:
            if "h73" not in kodlar:
                kodlar.append("h73")
                aciklamalar.append(hata_dict.get("h73", "Hadise kaydında yağış olduğu halde bu saatte yağış miktarı verilmedi veya yağış verildiği halde Hadise kaydı yapılmadı.") + " (Hadise var, RRR yok)")
        
        if pd.notna(rrr) and rrr > 0 and not hadise_yagis_var:
            if "h73" not in kodlar:
                kodlar.append("h73")
                aciklamalar.append(hata_dict.get("h73", "Hadise kaydında yağış olduğu halde bu saatte yağış miktarı verilmedi veya yağış verildiği halde Hadise kaydı yapılmadı.") + " (RRR var, Hadise yok/yetersiz)")

        # h230: Daha önceki rasatlarda yağış olduğu halde toplam yağış verilmedi
        if pd.isna(rrr) and gmt in [0, 6, 12, 18]:
            try:
                metar_kesit = get_metar_history(6)
                ww_cols = [c for c in ["ww", "ww2", "ww3"] if c in df_metar.columns]
                gecmiste_yagis_var = any(is_yagis(w) for c_ww in ww_cols for w in metar_kesit[c_ww])
                
                if gecmiste_yagis_var and not any("h4" in k for k in kodlar):
                    kodlar.append("h230")
                    aciklamalar.append(hata_dict.get("h230", "Daha önceki rasatlarda yağış olduğu halde toplam yağış (RRR) verilmedi."))
            except Exception: pass

        # Yağış (RRR) Değerlerini WMO Matematiksel Formattan Gerçek Milimetreye (mm) Çeviren Yardımcı
        def _rrr_to_mm(r_val):
            try:
                r_num = float(r_val)
                if r_num == 990: return 0.0
                if 991 <= r_num <= 999: return (r_num - 990) / 10.0
                return r_num
            except: return 0.0

        # YENİ: 12 Saatlik Yağış (06Z/18Z) vs 6 Saatlik Yağış (00Z/12Z) Çapraz Kontrolü
        if gmt in [6, 18] and pd.notna(rrr):
            try:
                prev_row_6h = get_sinoptik_prev(6)
                if not prev_row_6h.empty:
                    prev_rrr_col = "rrr" if "rrr" in prev_row_6h.columns else "rrr_sin" if "rrr_sin" in prev_row_6h.columns else None
                    if prev_rrr_col and pd.notna(prev_row_6h[prev_rrr_col].values[0]):
                        prev_rrr_raw = float(prev_row_6h[prev_rrr_col].values[0])
                        prev_rrr = _rrr_to_mm(prev_rrr_raw)
                        curr_rrr = _rrr_to_mm(rrr)
                        # 00Z ve 12Z'de ölçülen 6 saatlik toplam yağış, 06Z ve 18Z'de ölçülen 12 saatlik toplamdan büyük olamaz
                        if prev_rrr > curr_rrr and (prev_rrr - curr_rrr) > 0.1:  # 0.1 mm tolerans payı (Eser miktarlar için)
                            kodlar.append("h316")
                            _gmt_val = int(gmt)
                            _prev_gmt_val = _gmt_val - 6
                            aciklamalar.append(f"{_gmt_val:02d}00 GMT rasadındaki 12 saatlik toplam yağış ({curr_rrr} mm), periyot içindeki {_prev_gmt_val:02d}00 GMT rasadında ölçülen 6 saatlik miktardan ({prev_rrr} mm) küçük olamaz.")
            except Exception: pass

        # YENİ: 24 Saatlik Yağış Çapraz Kontrolü
        # 1. Excel'deki rrr_toplam sütunu (06Z'de ölçülen dünkü 06Z'den bugünkü 06Z'ye kadar olan 24 saatlik yağış)
        rrr_toplam = _get_val(s, "rrr_toplam")
        if gmt == 6 and pd.notna(rrr_toplam):
            try:
                rt_val = _rrr_to_mm(rrr_toplam)
                curr_rrr = _rrr_to_mm(rrr) if pd.notna(rrr) else 0.0
                
                past_rrrs = {}
                for h_back in [6, 12, 18]:
                    p_row = get_sinoptik_prev(h_back)
                    if not p_row.empty:
                        p_rrr_col = "rrr" if "rrr" in p_row.columns else "rrr_sin" if "rrr_sin" in p_row.columns else None
                        past_rrrs[h_back] = _rrr_to_mm(p_row[p_rrr_col].values[0]) if p_rrr_col and pd.notna(p_row[p_rrr_col].values[0]) else 0.0
                    else:
                        past_rrrs[h_back] = 0.0
                        
                sum_direct = curr_rrr + past_rrrs[6] + past_rrrs[12] + past_rrrs[18]
                sum_wmo = curr_rrr + past_rrrs[12]
                
                if sum_direct > 0 and abs(rt_val - sum_direct) > 0.1 and abs(rt_val - sum_wmo) > 0.1:
                    kodlar.append("h232")
                    aciklamalar.append(f"0600 GMT'deki 24 saatlik toplam yağış ({rt_val} mm), periyottaki geçmiş rasatların (6,12,18s) toplamıyla uyuşmuyor. (Geçmiş 4 Rasat Toplamı: {sum_direct:.1f} mm, WMO 12s+12s Toplamı: {sum_wmo:.1f} mm)")

                if curr_rrr > rt_val and (curr_rrr - rt_val) > 0.1:
                    kodlar.append("h317")
                    aciklamalar.append(f"0600 GMT rasadındaki 24 saatlik toplam yağış ({rt_val} mm), aynı rasatta ölçülen 12 saatlik miktardan ({curr_rrr} mm) küçük olamaz.")
                
                if past_rrrs[12] > rt_val and (past_rrrs[12] - rt_val) > 0.1:
                    if "h317" not in kodlar:
                        kodlar.append("h317")
                        aciklamalar.append(f"0600 GMT rasadındaki 24 saatlik toplam yağış ({rt_val} mm), periyot içindeki önceki 1800 GMT rasadında ölçülen 12 saatlik miktardan ({past_rrrs[12]} mm) küçük olamaz.")
            except Exception: pass
            
        # 2. tr=4 ile girilen 24 saatlik RRR grubu
        if pd.notna(rrr) and pd.notna(tr) and int(tr) == 4:
            try:
                curr_rrr_24 = _rrr_to_mm(rrr)
                
                past_rrrs = {}
                for h_back in [6, 12, 18, 24]:
                    p_row = get_sinoptik_prev(h_back)
                    if not p_row.empty:
                        p_rrr_col = "rrr" if "rrr" in p_row.columns else "rrr_sin" if "rrr_sin" in p_row.columns else None
                        if p_rrr_col and pd.notna(p_row[p_rrr_col].values[0]):
                            p_rrr_val = _rrr_to_mm(p_row[p_rrr_col].values[0])
                            if p_rrr_val > curr_rrr_24 and (p_rrr_val - curr_rrr_24) > 0.1:
                                kodlar.append("h317")
                                _p_gmt = (int(gmt) - h_back) % 24
                                aciklamalar.append(f"Rasadaki 24 saatlik toplam yağış (tR=4, {curr_rrr_24} mm), periyot içindeki {_p_gmt:02d}00 GMT rasadında ölçülen miktardan ({p_rrr_val} mm) küçük olamaz.")
                                break
                        past_rrrs[h_back] = _rrr_to_mm(p_row[p_rrr_col].values[0]) if p_rrr_col and pd.notna(p_row[p_rrr_col].values[0]) else 0.0
                    else:
                        past_rrrs[h_back] = 0.0
                        
                sum_direct = past_rrrs[6] + past_rrrs[12] + past_rrrs[18] + past_rrrs[24]
                sum_wmo = past_rrrs[12] + past_rrrs[24]
                
                if sum_direct > 0 and abs(curr_rrr_24 - sum_direct) > 0.1 and abs(curr_rrr_24 - sum_wmo) > 0.1:
                    kodlar.append("h232")
                    aciklamalar.append(f"Rasadaki 24 saatlik toplam yağış (tR=4, {curr_rrr_24} mm), geçmiş 4 ana rasadın (6,12,18,24s) yağışları toplamına eşit değil. (Direkt Toplam: {sum_direct:.1f} mm, WMO Toplamı: {sum_wmo:.1f} mm)")

                for h_back in [6, 12, 18]:
                    if past_rrrs[h_back] > curr_rrr_24 and (past_rrrs[h_back] - curr_rrr_24) > 0.1:
                        if "h317" not in kodlar:
                            kodlar.append("h317")
                            _p_gmt = (int(gmt) - h_back) % 24
                            aciklamalar.append(f"Rasadaki 24 saatlik toplam yağış (tR=4, {curr_rrr_24} mm), periyot içindeki {_p_gmt:02d}00 GMT rasadında ölçülen miktardan ({past_rrrs[h_back]} mm) küçük olamaz.")
                            break
            except Exception: pass

        # h78: Halihazır hava 00 olamaz
        if ww == 0:
            kodlar.append("h78")
            aciklamalar.append(hata_dict.get("h78"))

        # h79: Görüş 10 Km.den az iken hadise verilmemiş
        if pd.notna(vv) and vv < 60 and (pd.isna(ww) or ww < 4):
            kodlar.append("h79")
            aciklamalar.append(hata_dict.get("h79"))

        # h80 İPTAL EDİLDİ: WMO FM-12'ye göre ww=01-03 iken geçmişte yağış/hadise (W1>2) olması tamamen normaldir. (Örn: 70162)
        # if pd.notna(ww) and 1 <= ww <= 3 and pd.notna(w1) and w1 > 2:
        #     kodlar.append("h80")
        #     aciklamalar.append(hata_dict.get("h80"))

        # h378: ww=01, 02, 03 Bulut Gelişimi Çelişkisi Kontrolü
        if pd.notna(ww) and ww in [1, 2, 3] and pd.notna(n):
            prev_n = None
            dt_suan = get_dt_suan()
            if dt_suan:
                for h_back in [1, 2, 3]:
                    dt_prev = dt_suan - datetime.timedelta(hours=h_back)
                    prev_sayfa = dt_prev.strftime('%d.%m.%Y')
                    prev_gmt = float(dt_prev.hour)
                    
                    p_row = birlesik_df[(birlesik_df["sayfa"] == prev_sayfa) & (birlesik_df["gmt"] == prev_gmt)]
                    if p_row.empty and dt_suan.month != dt_prev.month:
                        df_arsiv = get_arsiv_df(dt_prev)
                        if not df_arsiv.empty and "sayfa" in df_arsiv.columns and "gmt" in df_arsiv.columns:
                            p_row = df_arsiv[(df_arsiv["sayfa"] == prev_sayfa) & (df_arsiv["gmt"] == prev_gmt)]
                            
                    if not p_row.empty:
                        for n_key in ["n_metar", "n_sin", "n", "T. Kp."]:
                            if n_key in p_row.columns:
                                val = p_row[n_key].values[0]
                                if pd.notna(val) and str(val).strip().lower() not in ["nan", "none", ""]:
                                    try: prev_n = float(val); break
                                    except: pass
                        if prev_n is not None: break
                            
            if prev_n is not None:
                if ww == 1 and n >= prev_n:
                    kodlar.append("h378")
                    aciklamalar.append(f"ww=01 (Bulutlar azalıyor) kodlanmış ancak önceki rasata göre bulutluluk azalmamış (Önceki N={int(prev_n)}, Güncel N={int(n)}).")
                elif ww == 2 and n != prev_n:
                    kodlar.append("h378")
                    aciklamalar.append(f"ww=02 (Değişiklik yok) kodlanmış ancak önceki rasata göre bulutluluk değişmiş (Önceki N={int(prev_n)}, Güncel N={int(n)}).")
                elif ww == 3 and n <= prev_n:
                    kodlar.append("h378")
                    aciklamalar.append(f"ww=03 (Bulutlar artıyor) kodlanmış ancak önceki rasata göre bulutluluk artmamış (Önceki N={int(prev_n)}, Güncel N={int(n)}).")

        # h81, h82, h84: Görüş ve Nem Kontrolleri
        if ww == 4 and ((pd.notna(vv) and vv >= 90) or (rh is not None and rh >= 70)):
            kodlar.append("h81")
            aciklamalar.append(hata_dict.get("h81"))
        if ww == 5 and ((pd.notna(vv) and vv >= 90) or (rh is not None and rh >= 70)):
            kodlar.append("h82")
            aciklamalar.append(hata_dict.get("h82"))
        if ww == 10 and ((pd.notna(vv) and (vv < 10 or vv >= 90)) or (rh is not None and rh < 70)):
            kodlar.append("h84")
            aciklamalar.append(hata_dict.get("h84"))

        # h86: ww=17 (Oraj) -> Cb olmalı
        if ww == 17 and pd.notna(cl) and cl not in [3, 9]:
            kodlar.append("h86")
            aciklamalar.append(hata_dict.get("h86"))
                    
        # --- 7wwW1W2 KAPSAMLI TUTARLILIK KONTROLLERİ ---
        if pd.notna(ww):
            # h83: 07, 08, 09 -> Fırtına yok, Görüş <= 8km (vv <= 58)
            if ww in [7, 8, 9] and pd.notna(vv) and vv > 58:
                kodlar.append("h83")
                aciklamalar.append(hata_dict.get("h83"))
            
            # h85: 11, 12 (Sığ sis) -> Yatay Görüş (VV) 1 km veya daha fazla OLMALIDIR (vv >= 10)
            if ww in [11, 12] and pd.notna(vv) and vv < 10:
                kodlar.append("h85")
                aciklamalar.append(hata_dict.get("h85", "11-12: Sığ sis (MIFG) hadiselerinde yatay görüş (VV) 1 km veya üzerinde olmalıdır. Görüş 1 km'den az ise ww=40-49 kullanılmalıdır."))
                
            # TOZ VE KUM FIRTINASI (ww=30-35)
            if 30 <= ww <= 35:
                if ww in [30, 31, 32]:
                    if pd.notna(ff) and not (28 <= ff <= 40): kodlar.append("h88"); aciklamalar.append(hata_dict.get("h88"))
                    if pd.notna(vv) and vv >= 10: kodlar.append("h89"); aciklamalar.append(hata_dict.get("h89"))
                else: # 33, 34, 35
                    if pd.notna(ff) and ff <= 40: kodlar.append("h90"); aciklamalar.append(hata_dict.get("h90"))
                    if pd.notna(vv) and vv >= 10: kodlar.append("h91"); aciklamalar.append(hata_dict.get("h91"))
                    
            # SÜRÜKLENEN KAR (ww=36-39) -> Görüş <= 8km olmalı
            if 36 <= ww <= 39 and pd.notna(vv) and vv > 58:
                kodlar.append("h92")
                aciklamalar.append(hata_dict.get("h92"))
                
            # 18: Squall (Grajlı Fırtına)
            if ww == 18 and pd.notna(ff) and ff < 22:
                kodlar.append("h268")
                aciklamalar.append(hata_dict.get("h268", "18: Squall (Fırtına) hadisesinde rüzgar hızı 22 kt veya daha fazla olmalıdır."))

            # Sona Eren Hadiseler (ww=20-29) için WMO Geçmiş Hava (W1, W2) Beklentisi Çapraz Kontrolü
            if pd.notna(ww) and 20 <= ww <= 29:
                w1_val = int(w1) if pd.notna(w1) else -1
                w2_val = int(w2) if pd.notna(w2) else -1
                
                # WMO FM-12 Kuralı: "ww ve W1W2 periyodun tam tanımını yapmalıdır."
                # ww=20-29 arası sona eren bir hadiseyi zaten açıkladığı için W1 ve W2'nin bunu
                # tekrar etmesi zorunlu değildir. W1/W2 hadise öncesindeki bulutluluk (0,1,2 vb.) olabilir.
                # Bu nedenle daha önce burada bulunan h361 (zorunlu W1/W2 eşleşmesi) kuralı iptal edilmiştir.

            # Sona Eren Hadiseler (ww=25, 26, 27, 28, 29) 1 Saatlik Geçmiş Kontrolü
            if ww in [25, 26, 27, 28, 29]:
                try:
                    metar_son_1_saat = get_metar_history(1)
                    bulundu = False
                    
                    bulten_col = "bulten" if "bulten" in df_metar.columns else None
                    ww_cols_1h = [c for c in ["ww", "ww2", "ww3"] if c in df_metar.columns]
                    
                    if ww == 28:
                        if pd.notna(vv) and vv < 10:
                            kodlar.append("h87")
                            aciklamalar.append("28 (Sona Eren Sis) hadisesinde rasat anında görüş 1 km'nin üzerinde (VV >= 10) olmalıdır.")
                        else:
                            if bulten_col and not metar_son_1_saat.empty:
                                for msg in metar_son_1_saat[bulten_col]:
                                    if pd.notna(msg) and re.search(r'\b(FG|FZFG)\b', clean_trend(msg)):
                                        bulundu = True; break
                            if not bulundu and ww_cols_1h and not metar_son_1_saat.empty:
                                for c_ww in ww_cols_1h:
                                    if bulundu: break
                                    for w in metar_son_1_saat[c_ww]:
                                        try:
                                            if 40 <= int(w) <= 49: bulundu = True; break
                                        except:
                                            if str(w).upper() in ["FG", "FZFG"]: bulundu = True; break
                            if not bulundu:
                                kodlar.append("h87")
                                aciklamalar.append("ww=28 (Sona Eren Sis) kodlanmış ancak son 1 saat içindeki METAR'larda Sis (FG/FZFG) raporlanmamış.")
                                
                    elif ww == 25:
                        if bulten_col and not metar_son_1_saat.empty:
                            for msg in metar_son_1_saat[bulten_col]:
                                if pd.notna(msg) and re.search(r'\b(SHRA)\b', clean_trend(msg)):
                                    bulundu = True; break
                        if not bulundu and ww_cols_1h and not metar_son_1_saat.empty:
                            for c_ww in ww_cols_1h:
                                if bulundu: break
                                for w in metar_son_1_saat[c_ww]:
                                    try:
                                        if int(w) in [80, 81, 82]: bulundu = True; break
                                    except:
                                        if str(w).upper() == "SHRA": bulundu = True; break
                        if not bulundu:
                            if "h269" not in kodlar:
                                kodlar.append("h269")
                                aciklamalar.append("ww=25 (Sona Eren Sağanak Yağmur) kodlanmış ancak son 1 saat içindeki METAR'larda Sağanak Yağmur (SHRA) raporlanmamış.")
                                
                    elif ww == 26:
                        if bulten_col and not metar_son_1_saat.empty:
                            for msg in metar_son_1_saat[bulten_col]:
                                if pd.notna(msg) and re.search(r'\b(SHSN|SHSG)\b', clean_trend(msg)):
                                    bulundu = True; break
                        if not bulundu and ww_cols_1h and not metar_son_1_saat.empty:
                            for c_ww in ww_cols_1h:
                                if bulundu: break
                                for w in metar_son_1_saat[c_ww]:
                                    try:
                                        if int(w) in [85, 86]: bulundu = True; break
                                    except:
                                        if str(w).upper() in ["SHSN", "SHSG"]: bulundu = True; break
                        if not bulundu:
                            if "h269" not in kodlar:
                                kodlar.append("h269")
                                aciklamalar.append("ww=26 (Sona Eren Kar Sağanağı) kodlanmış ancak son 1 saat içindeki METAR'larda Kar Sağanağı (SHSN/SHSG) raporlanmamış.")
                    
                    elif ww == 27:
                        if bulten_col and not metar_son_1_saat.empty:
                            for msg in metar_son_1_saat[bulten_col]:
                                if pd.notna(msg) and re.search(r'\b(GR|GS)\b', clean_trend(msg)):
                                    bulundu = True; break
                        if not bulundu and ww_cols_1h and not metar_son_1_saat.empty:
                            for c_ww in ww_cols_1h:
                                if bulundu: break
                                for w in metar_son_1_saat[c_ww]:
                                    try:
                                        if int(w) in [87, 88, 89, 90, 93, 94, 96, 99]: bulundu = True; break
                                    except:
                                        if str(w).upper() in ["GR", "GS"]: bulundu = True; break
                        if not bulundu:
                            if "h269" not in kodlar:
                                kodlar.append("h269")
                                aciklamalar.append("ww=27 (Sona Eren Dolu) kodlanmış ancak son 1 saat içindeki METAR'larda Dolu (GR/GS) raporlanmamış.")
                                
                    elif ww == 29:
                        if bulten_col and not metar_son_1_saat.empty:
                            for msg in metar_son_1_saat[bulten_col]:
                                if pd.notna(msg) and re.search(r'\bTS\b', clean_trend(msg)):
                                    bulundu = True; break
                        if not bulundu and ww_cols_1h and not metar_son_1_saat.empty:
                            for c_ww in ww_cols_1h:
                                if bulundu: break
                                for w in metar_son_1_saat[c_ww]:
                                    try:
                                        if int(w) in [17, 29, 95, 96, 97, 98, 99]: bulundu = True; break
                                    except:
                                        if "TS" in str(w).upper(): bulundu = True; break
                        if not bulundu:
                            if "h269" not in kodlar:
                                kodlar.append("h269")
                                aciklamalar.append("ww=29 (Sona Eren Oraj) kodlanmış ancak son 1 saat içindeki METAR'larda Oraj (TS) raporlanmamış.")
                except: pass
                
            # SİS KONTROLLERİ (ww=40-49)
            if 40 <= ww <= 49:
                if ww == 40 and pd.notna(vv) and not (10 <= vv < 50): kodlar.append("h93"); aciklamalar.append(hata_dict.get("h93"))
                if ww == 41 and pd.notna(vv) and vv >= 50: kodlar.append("h94"); aciklamalar.append(hata_dict.get("h94"))
                if 42 <= ww <= 49 and pd.notna(vv) and vv >= 10: kodlar.append("h95"); aciklamalar.append(hata_dict.get("h95"))
                if ww in [48, 49] and pd.notna(t) and t > 0: kodlar.append("h96"); aciklamalar.append(hata_dict.get("h96"))
                if ww in [43, 45, 47, 49] and pd.notna(n) and n != 9: kodlar.append("h97"); aciklamalar.append(hata_dict.get("h97"))
                if ww in [42, 44, 46, 48] and pd.notna(n) and n == 9: kodlar.append("h98"); aciklamalar.append(hata_dict.get("h98"))

            # YAĞIŞ (Sıcaklık, Bulut ve Görüş İlişkileri) (ww=50-99)
            if 50 <= ww <= 59 and pd.notna(cl) and cl not in [5, 6, 7]: kodlar.append("h100"); aciklamalar.append(hata_dict.get("h100", "50-59: Bu hadiselerde St veya Sc bulutu olmalıdır."))
            if ww in [56, 57] and pd.notna(t) and t > 5.4: kodlar.append("h101"); aciklamalar.append(hata_dict.get("h101"))
            if ww in [66, 67] and pd.notna(t) and t > 5.4: kodlar.append("h102"); aciklamalar.append(hata_dict.get("h102"))
            if ww in [68, 69] and pd.notna(t) and t > 8.5: kodlar.append("h103"); aciklamalar.append(hata_dict.get("h103"))
            if 70 <= ww <= 79 and pd.notna(t) and t > 6.5: kodlar.append("h104"); aciklamalar.append(hata_dict.get("h104"))
            if ww in [74, 75] and pd.notna(vv) and vv > 20: kodlar.append("h105"); aciklamalar.append(hata_dict.get("h105")) # vv>20 = 2km+
            
            # WMO Kural İyileştirmesi: Sağanak yağışlarda CM=8 (Ac Castellanus) tolere edilmelidir
            if 80 <= ww <= 94:
                if pd.notna(cl) and cl not in [1, 2, 3, 9] and not (pd.notna(cm) and cm == 8):
                    kodlar.append("h106"); aciklamalar.append(hata_dict.get("h106", "80-94: Bu hadiselerde Cu-Cb veya Ac Castellanus bulutu mutlaka olmalıdır."))
            
            if ww in [83, 84, 85, 86] and pd.notna(t) and t > 6.5: kodlar.append("h107"); aciklamalar.append(hata_dict.get("h107"))
            if ww in [87, 88] and pd.notna(t) and t > 8.5: kodlar.append("h108"); aciklamalar.append(hata_dict.get("h108"))
            if ww in [89, 90] and pd.notna(cl) and cl not in [3, 9]: kodlar.append("h109"); aciklamalar.append(hata_dict.get("h109"))
            if 95 <= ww <= 99 and pd.notna(cl) and cl not in [3, 9]: kodlar.append("h110"); aciklamalar.append(hata_dict.get("h110"))

            # --- YENİ ÇAPRAZ KONTROLLER (ww vs CL/CM/CH) ---
            
            # 1. Sürekli Yağış vs Konvektif Bulut Uyumsuzluğu
            if ww in [61, 63, 65, 71, 73, 75]:
                has_stratiform = False
                
                # 1. Standart CL/CM sütunlarından kontrol et
                if (pd.notna(cm) and cm in [1, 2]) or (pd.notna(cl) and cl in [5, 6, 7]):
                    has_stratiform = True
                    
                # 2. Bölüm 3'teki (333) ek bulut katmanlarını ve bg1..bg4 sütunlarını kontrol et
                if not has_stratiform:
                    cloud_sources = ["cl", "cm", "bg1", "bg2", "bg3", "bg4"]
                    raw_vals = [_get_val(s, k) for k in cloud_sources]
                    
                    # RASATLAR içindeki ham 8-gruplarını da dahil et (Örn: 83715, 87630)
                    rasat_str = str(rasatlar) if pd.notna(rasatlar) else ""
                    raw_vals.extend(re.findall(r'\b8\d{4}\b', rasat_str))
                    
                    for val in raw_vals:
                        if pd.isna(val) or str(val).strip() == "": continue
                        val_s = str(val).strip()
                        if val_s.endswith(".0"): val_s = val_s[:-2]
                        
                        if len(val_s) == 5 and val_s.startswith("8"):
                            try:
                                c_type = int(val_s[2])
                                # WMO Kod Tablosu 0500 (C): 1=As, 2=Ns, 5=Sc, 6=St, 7=St fra
                                if c_type in [1, 2, 5, 6, 7]:
                                    has_stratiform = True; break
                            except: pass

                if not has_stratiform:
                    kodlar.append("h318")
                    aciklamalar.append(f"Sürekli yağış (ww={int(ww)}) raporlanmış ancak havayı kapatan kalın tabakalı bulut (As/Ns veya kalın Sc/St) kodlanmamış.")

            # 2. Cb (Kümülonimbüs) Bulutu vs Kararlı Yağış Uyumsuzluğu
            if pd.notna(cl) and cl in [3, 9] and (pd.isna(cm) or cm == 0):
                if 60 <= ww <= 79:
                    kodlar.append("h319")
                    aciklamalar.append(f"Kümülonimbüs (Cb, CL={int(cl)}) bulutu sağanak karakterli yağış üretir, ancak halihazır hava sürekli/aralıklı yağış (ww={int(ww)}) olarak girilmiş. (Sağanak için ww=80-99 beklenir)")

            # 3. Virga veya Uzakta Yağış (ww=14, 15, 16) vs Bulutsuzluk
            if ww in [14, 15, 16]:
                if pd.notna(n) and n == 0:
                    kodlar.append("h320")
                    aciklamalar.append(f"Uzakta/ulaşmayan yağış (ww={int(ww)}) kodlanmış ancak gökyüzü bulutsuz (N=0) girilmiş.")

            # 4. Şimşek (ww=13) vs Cb/Ac Castellanus
            if ww == 13:
                has_cb_or_ac = (pd.notna(cl) and cl in [3, 9]) or (pd.notna(cm) and cm == 8)
                if not has_cb_or_ac:
                    kodlar.append("h321")
                    aciklamalar.append("Şimşek (ww=13) raporlanmış ancak Cb (CL=3,9) veya Ac Castellanus (CM=8) bulutu kodlanmamış.")
                    
                # h379: Şimşek (ww=13) raporlanıp Oraj çelişkisi/eksikliği
                m_bulten = _get_val(s, "bulten_metar")
                if not m_bulten: m_bulten = _get_val(s, "bulten")
                
                metar_ts_var = False
                if pd.notna(m_bulten) and "TS" in clean_trend(str(m_bulten)):
                    metar_ts_var = True
                    
                w1_is_9 = pd.notna(w1) and int(w1) == 9
                w2_is_9 = pd.notna(w2) and int(w2) == 9
                
                if metar_ts_var:
                    kodlar.append("h379")
                    aciklamalar.append("SİNOPTİK'te Şimşek (ww=13) kodlanmış ancak aynı saatteki METAR'da Oraj (TS) raporlanmış. Gök gürültüsü duyulduysa ww=13 kullanılamaz, Oraj kodları (17, 95-99) girilmelidir.")
                elif w1_is_9 or w2_is_9:
                    kodlar.append("h379")
                    aciklamalar.append("Geçmiş havada (W1 veya W2) Oraj (9) raporlanmışken, halihazır hava Şimşek (ww=13) kodlanamaz. Oraj sona erdiyse ww=29 (Sona Eren Oraj) kullanılmalıdır.")
                else:
                    # Gök gürültüsü unutulma ihtimaline karşı genel hatırlatma uyarısı
                    kodlar.append("h379 (DİKKAT)")
                    aciklamalar.append("Şimşek (ww=13) raporlanmış. Eğer istasyonda gök gürültüsü de duyulduysa ww=13 yerine Oraj (ww=17 veya 95-99) verilmelidir. Lütfen oraj olup olmadığını teyit ediniz.")

        # W1, W2 FORMAT VE MANTIK KONTROLÜ (Tek haneli rakam olmalılar)
        if pd.notna(w1) and not (0 <= w1 <= 9):
            kodlar.append("h117")
            aciklamalar.append(hata_dict.get("h117", "Geçmiş hava grubu 1 (W1) hatalı kodlanmış."))
            
        if pd.notna(w2):
            if not (0 <= w2 <= 9):
                kodlar.append("h117")
                aciklamalar.append(hata_dict.get("h117", "Geçmiş hava grubu 2 (W2) hatalı kodlanmış."))
                
            # Excel Mantık Hatası: W1 boş iken W2 girilmişse
            if pd.isna(w1):
                kodlar.append("h322")
                aciklamalar.append("Geçmiş hava 1 (W1) boş bırakılmış ancak Geçmiş hava 2 (W2) kodlanmış. W1 olmadan W2 değerlendirilemez.")

        # h111: Yağış var ama N=0
        if pd.notna(ww) and ww >= 50 and n == 0:
            kodlar.append("h111")
            aciklamalar.append(hata_dict.get("h111"))

        # h116: İkinci geçmiş hadise birinci geçmiş hadiseden büyük olamaz
        if pd.notna(w1) and pd.notna(w2) and w2 > w1:
            kodlar.append("h116")
            aciklamalar.append(hata_dict.get("h116"))

        # h118: ww<4 ve W1, W2 önemsiz ise 7 grubu kodlanmaz (ix=2 olmalı)
        if pd.notna(ww) and ww < 4:
            w1_val = w1 if pd.notna(w1) else 0
            w2_val = w2 if pd.notna(w2) else 0
            if w1_val < 3 and w2_val < 3 and (pd.notna(w1) or pd.notna(w2)):
                kodlar.append("h118")
                aciklamalar.append("Halihazır hava (ww < 4) ve geçmiş hava (W1, W2 < 3) önemsiz iken 7. grup koda dahil edilmemelidir (ix=2).")

        # h196: Yerin hali ve toprak sıcaklık grubu koda dahil edilmedi
        if gmt == 6 and pd.isna(e) and pd.isna(tg):
            # Kuralı iyileştir: Eğer 4E'sss grubu (kar durumu) raporlanmışsa, 3ETgTg grubu zorunlu değildir.
            # RASATLAR sütununda "333" sonrası "4" ile başlayan bir grup var mı diye kontrol et.
            has_4_group = False
            if pd.notna(rasatlar):
                rasat_str = str(rasatlar)
                if "333" in rasat_str:
                    section_333 = rasat_str.split("333", 1)[-1]
                    if "555" in section_333:
                        section_333 = section_333.split("555", 1)[0]
                    
                    # "4" ile başlayan 5 haneli bir grup ara
                    if re.search(r'\b4\d{4}\b', section_333):
                        has_4_group = True
            
            if not has_4_group:
                kodlar.append("h196")
                aciklamalar.append(hata_dict.get("h196"))

        # h197: t < 0 iken E=1,2 (ıslak) olmaz
        if pd.notna(t) and t < 0 and pd.notna(e) and e in [1, 2]:
            kodlar.append("h197")
            aciklamalar.append(hata_dict.get("h197"))

        # --- ÇAPRAZ KONTROL: SİNOPTİK VV vs METAR GÖRÜŞ ---
        vv_metar = s.get("vv_metar")
        bulten_msg = s.get("bulten_metar") if pd.notna(s.get("bulten_metar")) else s.get("bulten")
        if pd.notna(vv):
            try:
                s_vv = float(vv)
                is_cavok = pd.notna(bulten_msg) and "CAVOK" in clean_trend(bulten_msg)
                
                s_vis = vv_to_meters(s_vv)
                if s_vis != -1:
                    if is_cavok:
                        if s_vv < 60:
                            kodlar.append("h323")
                            aciklamalar.append(f"METAR CAVOK (Görüş >= 10km) iken, Sinoptik VV={int(s_vv)} ({int(s_vis)}m) olamaz.")
                        
                        if pd.notna(n) and n > 0:
                            if pd.notna(h) and h < 6:
                                kodlar.append("h324")
                                aciklamalar.append(f"METAR CAVOK iken Sinoptik'te 1500m (5000ft) altında bulut kodlanamaz (h={int(h)}).")
                            if pd.notna(cl) and cl in [2, 3, 9]:
                                kodlar.append("h325")
                                aciklamalar.append(f"METAR CAVOK iken Sinoptik'te Kümülonimbüs veya TCU (CL={int(cl)}) kodlanamaz.")
                    elif pd.notna(vv_metar):
                        m_vis = float(vv_metar)
                        # METAR Görüş >= 9999 (10km ve üstü) ise, SİNOPTİK VV >= 60 (10km ve üstü) olmalı
                        if m_vis >= 9999:
                            if s_vv < 60:
                                kodlar.append("h377")
                                aciklamalar.append(f"METAR Görüş 10km+ (>=10000m) iken, Sinoptik VV={int(s_vv)} ({int(s_vis)}m) olamaz.")
                        else:
                            # Gerçek mesafe karşılaştırması (Örn: Otomatik Sensör METAR=20000m ve SİNOPTİK=20000m)
                            tolerans = 1000 if m_vis <= 10000 else 2000
                            if abs(m_vis - s_vis) > tolerans:
                                kodlar.append("h377")
                                aciklamalar.append(f"Sinoptik VV={int(s_vv)} ({int(s_vis)}m) ile METAR Görüş ({int(m_vis)}m) uyumsuz.")
            except: pass

        # --- ÇAPRAZ KONTROL: METAR Geçmişi (Yağış, Sis, Kar, Hamle) vs SİNOPTİK ---
        try:
            if pd.notna(gmt):
                metar_kesit = get_metar_history(6 if gmt in [0, 6, 12, 18] else 3)
                ww_cols = [c for c in ["ww", "ww2", "ww3"] if c in df_metar.columns]
                bulten_col = "bulten" if "bulten" in df_metar.columns else None
                
                metarda_yagis_var = False
                metarda_sis_var = False
                metarda_oraj_gecmis_var = False
                metarda_tozkum_firtinasi_var = False

                if ww_cols:
                    metarda_yagis_var = any(is_yagis(w) for c_ww in ww_cols for w in metar_kesit[c_ww])
                    metarda_sis_var = any(is_sis(w) for c_ww in ww_cols for w in metar_kesit[c_ww])
                    metarda_oraj_gecmis_var = any(is_oraj(w) for c_ww in ww_cols for w in metar_kesit[c_ww])
                    metarda_tozkum_firtinasi_var = any(is_tozkum_firtinasi(w) for c_ww in ww_cols for w in metar_kesit[c_ww])
                    
                # BÜLTEN KONTROLÜ (Nihai Doğrulama)
                # Eğer bültende YOKSA, manuel girilen Excel sütunlarındaki hatalı girişleri yoksay!
                if bulten_col and not metar_kesit.empty:
                    metarda_yagis_var = any(is_yagis(msg) for msg in metar_kesit[bulten_col])
                    metarda_sis_var = any(is_sis(msg) for msg in metar_kesit[bulten_col])
                    metarda_oraj_gecmis_var = any(is_oraj(msg) for msg in metar_kesit[bulten_col])
                    metarda_tozkum_firtinasi_var = any(is_tozkum_firtinasi(msg) for msg in metar_kesit[bulten_col])

                if metarda_yagis_var:
                    if not ((pd.notna(w1) and int(w1) >= 5) or (pd.notna(w2) and int(w2) >= 5)):
                        # WMO Kuralı (Örn 11, 15): Yağış rasat anında devam ediyorsa (ww=yağış), W1/W2 yağış öncesini tanımlar.
                        if not is_yagis(ww):
                            kodlar.append("h326")
                            aciklamalar.append("METAR geçmişinde yağış raporlanmış, ancak Sinoptik geçmiş havada (W1/W2) yağış kodlanmamış (W1 ve W2 < 5).")

                if metarda_sis_var:
                    w1_val = int(w1) if pd.notna(w1) else -1
                    w2_val = int(w2) if pd.notna(w2) else -1
                    
                    if not (w1_val > 4 and w2_val > 4):
                        if w1_val != 4 and w2_val != 4:
                            if not is_sis(ww):
                                kodlar.append("h327")
                                aciklamalar.append("METAR geçmişinde Sis (FG) raporlanmış, ancak Sinoptik geçmiş havada (W1/W2) Sis (4) kodlanmamış.")

                # YENİ TERS KONTROL: Pus (BR) varken W1/W2 = 4 girilmesini engelle
                w1_val = int(w1) if pd.notna(w1) else -1
                w2_val = int(w2) if pd.notna(w2) else -1
                
                if w1_val == 4 or w2_val == 4:
                    if not metarda_sis_var:
                        metarda_pus_var = False
                        if bulten_col: metarda_pus_var = any("BR" in clean_trend(str(msg)).upper() for msg in metar_kesit[bulten_col])
                        elif ww_cols: metarda_pus_var = any("BR" in str(w).upper() for c_ww in ww_cols for w in metar_kesit[c_ww])
                        
                        if metarda_pus_var:
                            kodlar.append("h328")
                            aciklamalar.append("SİNOPTİK geçmiş havada (W1/W2) Sis (4) kodlanmış ancak METAR'da sadece Pus (BR) raporlanmış. Pus (BR) hadisesinin WMO formatında geçmiş hava kodu yoktur, 4 girilemez.")
                        else:
                            kodlar.append("h329")
                            aciklamalar.append("SİNOPTİK geçmiş havada (W1/W2) Sis (4) kodlanmış ancak periyottaki METAR'larda Sis (FG/FZFG) hadisesi bulunamadı.")

                # KUM/TOZ FIRTINASI (SS/DS) ve HZ/FU KONTROLLERİ
                if metarda_tozkum_firtinasi_var:
                    if w1_val != 3 and w2_val != 3:
                        kodlar.append("h330")
                        aciklamalar.append("METAR geçmişinde Kum/Toz Fırtınası (SS/DS) raporlanmış, ancak Sinoptik geçmiş havada (W1/W2) Fırtına (3) kodlanmamış.")

                if w1_val == 3 or w2_val == 3:
                    if not metarda_tozkum_firtinasi_var:
                        metarda_hz_fu_var = False
                        if bulten_col: metarda_hz_fu_var = any(re.search(r'\b(HZ|FU|SA|DU)\b', clean_trend(str(msg)).upper()) for msg in metar_kesit[bulten_col])
                        elif ww_cols: metarda_hz_fu_var = any(re.search(r'\b(HZ|FU|SA|DU)\b', str(w).upper()) for c_ww in ww_cols for w in metar_kesit[c_ww])
                        
                        if metarda_hz_fu_var:
                            kodlar.append("h331")
                            aciklamalar.append("SİNOPTİK geçmiş havada (W1/W2) Toz/Kum Fırtınası (3) kodlanmış ancak METAR'da sadece Toz Pusu/Duman vb. (HZ/FU/SA/DU) raporlanmış. Bu hadiselerin WMO formatında geçmiş hava kodu yoktur, 3 girilemez.")
                        else:
                            kodlar.append("h332")
                            aciklamalar.append("SİNOPTİK geçmiş havada (W1/W2) Kum/Toz Fırtınası (3) kodlanmış ancak periyottaki METAR'larda SS/DS hadisesi bulunamadı.")

                # ORAJ KONTROLÜ (Ayrı olarak - SİS bloku dışında)
                if metarda_oraj_gecmis_var:
                    w1_val = int(w1) if pd.notna(w1) else -1
                    w2_val = int(w2) if pd.notna(w2) else -1
                    
                    if w1_val != 9 and w2_val != 9:
                        if not is_oraj(ww):
                            kodlar.append("h333")
                            aciklamalar.append("METAR geçmişinde Oraj (TS) raporlanmış, ancak Sinoptik geçmiş havada (W1/W2) Oraj (9) kodlanmamış.")
                
                # RE (Recent Weather / Yakın Geçmiş Hadisesi) Kontrolü
                metarda_re_var = False
                re_hadiseler = []
                bulten_col = "bulten" if "bulten" in df_metar.columns else None
                if bulten_col and not metar_kesit.empty:
                    for msg in metar_kesit[bulten_col]:
                        if pd.notna(msg):
                            tokens = clean_trend(msg).split()
                            for t_tok in tokens:
                                if re.match(r'^RE[A-Z]{2,}', t_tok):
                                    metarda_re_var = True
                                    if t_tok not in re_hadiseler:
                                        re_hadiseler.append(t_tok)

                if metarda_re_var:
                    re_uyumlu = False
                    if pd.notna(ww) and 20 <= ww <= 29:
                        re_uyumlu = True
                    w1_val = int(w1) if pd.notna(w1) else -1
                    w2_val = int(w2) if pd.notna(w2) else -1
                    if w1_val >= 3 or w2_val >= 3:
                        re_uyumlu = True
                        
                    if not re_uyumlu:
                        kodlar.append("h334")
                        aciklamalar.append(f"METAR periyodunda Yakın Geçmiş Hadisesi ({', '.join(re_hadiseler)}) raporlanmış, ancak SİNOPTİK'te karşılığı yok (ww=20-29 veya ilgili W1/W2 kodlaması beklenir).")

                    # Yağış Miktarı (RRR) Kontrolü (TS bir yağış hadisesi olmadığından RRR grubunu zorunlu kılmaz)
                    re_yagis_iceriyor = any(re.search(r'RA|SN|DZ|GR|GS|SG|PL|SH|FZ', re_tok) for re_tok in re_hadiseler)
                    if re_yagis_iceriyor and pd.isna(rrr):
                        if gmt not in [3, 9, 15, 21]:
                            kodlar.append("h335")
                            aciklamalar.append(f"METAR'da yağışlı Yakın Geçmiş Hadisesi ({', '.join(re_hadiseler)}) raporlanmış. SİNOPTİK Yağış Miktarı (RRR) grubu boş bırakılamaz.")
                        
                    # Spesifik Geçmiş Hava (W1/W2) Kodlaması
                    # WMO Kuralı: Eğer Halihazır Hava (ww) zaten hadiseyi açıklıyorsa W1/W2 serbesttir.
                    ww_acikliyor_mu = False
                    if pd.notna(ww):
                        w_int = int(ww)
                        if (20 <= w_int <= 29) or (50 <= w_int <= 99) or w_int == 17:
                            ww_acikliyor_mu = True
                            
                    if not ww_acikliyor_mu:
                        re_ts_var = any("TS" in re_tok for re_tok in re_hadiseler)
                        re_sh_var = any("SH" in re_tok for re_tok in re_hadiseler)
                        re_sn_var = any("SN" in re_tok or "SG" in re_tok for re_tok in re_hadiseler)
                        re_fz_var = any("FZ" in re_tok for re_tok in re_hadiseler)
                        
                        if re_ts_var and (w1_val != 9 and w2_val != 9):
                            kodlar.append("h336")
                            aciklamalar.append(f"METAR'da Yakın Geçmişte Oraj ({', '.join([r for r in re_hadiseler if 'TS' in r])}) raporlanmış. SİNOPTİK Geçmiş Hava (W1 veya W2) kodlarından biri kesinlikle 9 olmalıdır.")
                            
                        if re_sh_var and (w1_val != 8 and w2_val != 8):
                            # Sağanak Kar (SHSN) durumunda W1=7 tolere edilebilir
                            if re_sn_var and (w1_val == 7 or w2_val == 7):
                                pass
                            else:
                                kodlar.append("h337")
                                aciklamalar.append(f"METAR'da Yakın Geçmişte Sağanak ({', '.join([r for r in re_hadiseler if 'SH' in r])}) raporlanmış. SİNOPTİK Geçmiş Hava (W1 veya W2) kodlarından biri 8 olmalıdır.")
                                
                        if re_sn_var and (w1_val != 7 and w2_val != 7) and not re_sh_var:
                            kodlar.append("h338")
                            aciklamalar.append(f"METAR'da Yakın Geçmişte Kar ({', '.join([r for r in re_hadiseler if 'SN' in r or 'SG' in r])}) raporlanmış. SİNOPTİK Geçmiş Hava (W1 veya W2) kodlarından biri 7 olmalıdır.")
                            
                        if re_fz_var and (w1_val not in [5, 6, 7] and w2_val not in [5, 6, 7]):
                            kodlar.append("h339")
                            aciklamalar.append(f"METAR'da Yakın Geçmişte Donduran Yağış ({', '.join([r for r in re_hadiseler if 'FZ' in r])}) raporlanmış. SİNOPTİK Geçmiş Hava (W1 veya W2) kodlarından biri 5, 6 veya 7 olmalıdır.")

                # 2. Rüzgar Hamlesi (Gust/G) Kontrolü (910/911 Grubu)
                
                if bulten_col:
                    for msg in metar_kesit[bulten_col]:
                        # Bültende 24015G25KT gibi rüzgar formatını Regex ile arar
                        if pd.notna(msg) and re.search(r'\b\d{3}\d{2,3}G\d{2,3}(KT|MPS)\b', clean_trend(msg)):
                            metarda_hamle_var = True
                            break
                            
                if not metarda_hamle_var:
                    for col in metar_kesit.columns:
                        if 'hamle' in str(col).lower():
                            if pd.to_numeric(metar_kesit[col], errors='coerce').max() > 0:
                                metarda_hamle_var = True
                                break

                if metarda_hamle_var:
                    g910_val = _get_val(s, "g910")
                    g911_val = _get_val(s, "g911")
                    if pd.isna(g910_val) and pd.isna(g911_val):
                        kodlar.append("h340")
                        aciklamalar.append("METAR geçmişinde rüzgar hamlesi (Gust/G) raporlanmış, ancak Sinoptikte 910/911 grubu kodlanmamış.")
                
                # 3.5 Dolu (GR) veya Küçük Dolu (GS) Kontrolü (960 Grubu)
                metarda_dolu_var = False
                if ww_cols: metarda_dolu_var = any(is_dolu(w) for c_ww in ww_cols for w in metar_kesit[c_ww])
                if bulten_col and not metar_kesit.empty:
                    metarda_dolu_var = any(pd.notna(msg) and re.search(r'\b(GR|GS)\b', clean_trend(msg)) for msg in metar_kesit[bulten_col])
                            
                if metarda_dolu_var and pd.isna(g960):
                    kodlar.append("h341")
                    aciklamalar.append("Gün içinde Dolu (GR) veya Küçük Dolu (GS) raporlanmış, ancak Sinoptikte 960 (Hadise/Kayıt) grubu kodlanmamış.")

                # 3.7 Yoğun Sis (FG, FZFG) Kontrolü (960 Grubu)
                metarda_yogun_sis_var = False
                if ww_cols:
                    for c_ww in ww_cols:
                        for w in metar_kesit[c_ww]:
                            try:
                                w_int = int(w)
                                if 42 <= w_int <= 49: metarda_yogun_sis_var = True; break
                            except:
                                w_str = str(w).upper().strip()
                                if w_str in ["FG", "FZFG"]: metarda_yogun_sis_var = True; break
                
                if bulten_col and not metar_kesit.empty:
                    metarda_yogun_sis_var = False # Manuel excel hücresini ez, sadece bülteni dikkate al
                    for msg in metar_kesit[bulten_col]:
                        if pd.notna(msg):
                            tokens = clean_trend(msg).split()
                            if "FG" in tokens or "FZFG" in tokens:
                                metarda_yogun_sis_var = True; break

                if metarda_yogun_sis_var and pd.isna(g960):
                    kodlar.append("h342")
                    aciklamalar.append("Gün içinde Yoğun Sis (FG/FZFG) raporlanmış, ancak Sinoptikte 960 (Hadise/Kayıt) grubu kodlanmamış.")

                # 3.8 Çoklu Hadise (Örn: Yağmur ve Pus) Kontrolü (h249)
                metarda_coklu_hadise_var = False
                if bulten_col and not metar_kesit.empty:
                    # Sadece o anki rasat saatine (gmt) bakıyoruz
                    metar_current = metar_kesit[metar_kesit["gmt"] == gmt]
                    for msg in metar_current[bulten_col]:
                        if pd.notna(msg):
                            tokens = clean_trend(msg).split()
                            yagis = False
                            pus_sis = False
                            for t_tok in tokens:
                                # Yağış hadiseleri
                                if re.match(r'^(\+|-|VC|RE)?(SH|TS|FZ)?(RA|SN|DZ|GR|GS|SG|PL)$', t_tok): yagis = True
                                # Görüş engelleyici hadiseler (Pus, Sis, Duman vb.)
                                if re.match(r'^(\+|-|VC|RE)?(MI|PR|BC|DR|BL|FZ)?(BR|FG|HZ|FU|DU|SA)$', t_tok): pus_sis = True
                            
                            if yagis and pus_sis:
                                metarda_coklu_hadise_var = True; break

                if metarda_coklu_hadise_var and pd.isna(g960):
                    if "h249" not in kodlar:
                        kodlar.append("h249")
                        aciklamalar.append(hata_dict.get("h249", "Hadise kaydında ikinci hadise olmasına rağmen 960. grubu koda dahil etmediniz.") + " (METAR: Hem yağış hem pus/sis vb. mevcut)")

                # --- 4. YERİN HALİ (E) VE KAR YÜKSEKLİĞİ (931) ÇAPRAZ KONTROLLERİ ---
                ss = None
                if pd.notna(g931):
                    try:
                        g_str = str(int(g931))
                        if len(g_str) == 5 and g_str.startswith("931"): ss = int(g_str[3:])
                        else: ss = int(g931)
                    except: pass
                
            # KULLANICI İSTEĞİ: 932 Grubu kullanılmıyor. 931 grubu doğrudan "Taze Kar" olarak değerlendirilir.
            ss_taze = ss
                
            # Mantık/931-Kar: Taze kar var ama yağış geçmişi yok
            if ss_taze is not None and ss_taze > 0:
                kar_yagisi_var = False
                try:
                    metar_kar_kesit = get_metar_history(6)
                    ww_cols_local = [c for c in ["ww", "ww2", "ww3"] if c in df_metar.columns]
                    if ww_cols_local:
                        for c_ww in ww_cols_local:
                            if kar_yagisi_var: break
                            for w in metar_kar_kesit[c_ww]:
                                try:
                                    if int(w) in [22, 26, 38, 39, 68, 69, 83, 84, 85, 86] or (70 <= int(w) <= 79): kar_yagisi_var = True; break
                                except:
                                    if any(kod in str(w).upper() for kod in ["SN", "SG", "PL"]): kar_yagisi_var = True; break
                                    
                    bulten_col = "bulten" if "bulten" in df_metar.columns else None
                    if bulten_col and not metar_kar_kesit.empty:
                            kar_yagisi_var = any(pd.notna(msg) and re.search(r'\b(\+|-|VC|RE)?(SH|FZ)?(SN|SG|PL)\b', clean_trend(msg)) for msg in metar_kar_kesit[bulten_col])
                        
                    if not kar_yagisi_var:
                        if (pd.notna(w1) and w1 == 7) or (pd.notna(w2) and w2 == 7): kar_yagisi_var = True
                        if pd.notna(ww):
                            try:
                                w_int = int(ww)
                                if w_int in [22, 26, 38, 39, 68, 69, 83, 84, 85, 86] or (70 <= w_int <= 79): kar_yagisi_var = True
                            except: pass
                except: pass
                
                if not kar_yagisi_var:
                    kodlar.append("h374")
                    aciklamalar.append(f"931 (Taze Kar) grubu girilmiş ({ss_taze} cm) ancak son 6 saatlik periyotta kar yağışı (SN/SG vb.) veya kar geçmiş havası (W1/W2=7) raporlanmamış.")

            # h242: Taze kar için yüksek bir değer
            if ss_taze is not None and ss_taze > 50:
                if ss_taze == 931 or ss_taze > 200:
                    kodlar.append("h346")
                    aciklamalar.append(f"Kar kalınlığı çok ekstrem bir değer olarak girilmiş ({ss_taze} cm). Sadece '931' yazılmış veya klavye hatası yapılmış olabilir.")
                elif "h242" not in kodlar and "h346" not in kodlar:
                    kodlar.append("h242")
                    aciklamalar.append(hata_dict.get("h242", "Taze kar için yüksek bir değer") + f" ({ss_taze} cm)")
                    
            # h205: Yerde kar var (E=5,6,7,8,9) iken 931 grubu verilmemiş
            if pd.notna(e) and 5 <= e <= 9 and pd.isna(g931):
                if "h205" not in kodlar:
                    kodlar.append("h205")
                    aciklamalar.append(hata_dict.get("h205", "Yerde kar var iken yerin hali ve toplam kar grubu verilmedi.") + f" (E={int(e)})")

            # h206: 931 verilmiş (ss>0) ama yerin hali kar/buz göstermiyor (E < 5)
            if ss is not None and ss > 0:
                if pd.notna(e) and e < 5:
                    if "h206" not in kodlar:
                        kodlar.append("h206")
                        aciklamalar.append(hata_dict.get("h206", "Yerde ölçülebilir kar veya buz örtüsü olmalıdır.") + f" (931{ss:02d} girilmiş ama E={int(e)})")
                        
            # h207 & h346: Toplam kar kalınlığı çok fazla (> 150 cm vb.)
            if ss is not None:
                if ss == 931 or ss > 400:
                    kodlar.append("h346")
                    aciklamalar.append(f"Kar kalınlığı çok ekstrem bir değer olarak girilmiş ({ss} cm). Sadece '931' yazılmış veya klavye hatası yapılmış olabilir.")
                elif ss > 150:
                    if "h207" not in kodlar:
                        kodlar.append("h207")
                        aciklamalar.append(hata_dict.get("h207", "Toplam kar kalınlığı çok fazla") + f" ({ss} cm)")

            # 4.1 Kar Yağışı METAR Çapraz Kontrolü (6 Saatlik Tarama, Ana Sinoptik Saatleri)
            if gmt in [0, 6, 12, 18] and pd.isna(g931):
                metar_kar_kesit = get_metar_history(6)
                kar_bulundu = False
                ww_cols_local = [c for c in ["ww", "ww2", "ww3"] if c in df_metar.columns]
                if ww_cols_local:
                    for c_ww in ww_cols_local:
                        if kar_bulundu: break
                        for w in metar_kar_kesit[c_ww]:
                            try:
                                if int(w) in [22, 26, 38, 39, 68, 69, 83, 84, 85, 86] or (70 <= int(w) <= 79): kar_bulundu = True; break
                            except:
                                if any(kod in str(w).upper() for kod in ["SN", "SG", "PL"]): kar_bulundu = True; break
                            
                # Bülten metninden de SN kontrolü
                if bulten_col and not metar_kar_kesit.empty:
                    if not kar_bulundu:
                        kar_bulundu = any(pd.notna(msg) and re.search(r'\b(\+|-|VC|RE)?(SH|FZ)?(SN|SG|PL)\b', clean_trend(msg)) for msg in metar_kar_kesit[bulten_col])
                            
                # SİNOPTİK Geçmiş Hava (W1/W2) kontrolü: Kar kodu 7 (SN/SG) ise 931 beklenir.
                if not kar_bulundu:
                    try:
                        if (pd.notna(w1) and int(w1) == 7) or (pd.notna(w2) and int(w2) == 7):
                            kar_bulundu = True
                    except: pass

                if kar_bulundu:
                    # Eğer sıcaklık yüksekse uyarı notu ekle
                    ek_not = ""
                    if pd.notna(t) and t > 3.0:
                        ek_not = f" (DİKKAT: Sıcaklık {t}°C, yağan kar erimiş olabilir ancak 931 grubu kontrol edilmeli.)"
                
                    if pd.isna(g931) and pd.isna(g932):
                        kodlar.append("h347")
                        _gmt_val = int(gmt) if pd.notna(gmt) else 0
                        aciklamalar.append(f"Son 6 saatte kar (SN vb.) raporlanmış, ancak ana ({_gmt_val:02d}00 GMT) rasadında 931 (Toplam) veya 932 (Taze) kar grubu girilmemiş.{ek_not} [KESİN ÇÖZÜM]")
                        
            # 3.9 Profesyonel Çapraz Kontroller (Dönüşüm, Donduran Yağış, Buz Taneleri vb.)
            if bulten_col and not metar_kesit.empty:
                metarda_yagmur = False
                metarda_kar = False
                metarda_donduran = False
                metarda_buz_taneleri = False
                metarda_toz_kum = False
                metarda_squall = False
                
                for msg in metar_kesit[bulten_col]:
                    if pd.notna(msg):
                        msg_upper = clean_trend(msg)
                        tokens = msg_upper.split()
                        
                        for t_tok in tokens:
                            # Yağmur ve Kar ayırımı (Karışık değil, bağımsız)
                            if re.match(r'^(\+|-|VC|RE)?(SH)?RA$', t_tok): metarda_yagmur = True
                            if re.match(r'^(\+|-|VC|RE)?(SH)?SN$', t_tok): metarda_kar = True
                            
                            # Donduran Yağış (FZRA, FZDZ)
                            if "FZRA" in t_tok or "FZDZ" in t_tok: metarda_donduran = True
                            # Buz Taneleri (PL) veya Kar Taneleri (SG)
                            if "PL" in t_tok or "SG" in t_tok: metarda_buz_taneleri = True
                            # Toz / Kum (DS, SS)
                            if "DS" in t_tok or "SS" in t_tok: metarda_toz_kum = True
                            # Squall (SQ)
                            if "SQ" in t_tok: metarda_squall = True

                # Yağmur <-> Kar Dönüşümü
                if metarda_yagmur and metarda_kar:
                    if pd.isna(g960) and (pd.isna(ww) or ww not in [68, 69]):
                        kodlar.append("h348")
                        aciklamalar.append("METAR geçmişinde Yağmurdan (RA) Kara (SN) veya tam tersi bir dönüşüm yaşanmış. ww=68/69 (Karla Karışık Yağmur) kodlamasını veya 960 grubunu kontrol ediniz.")

                # Donduran Yağış
                if metarda_donduran:
                    if pd.isna(g960) and (pd.isna(ww) or ww not in [56, 57, 66, 67]):
                        kodlar.append("h349")
                        aciklamalar.append("METAR geçmişinde Donduran Yağış (FZRA/FZDZ) raporlanmış. ww kodlaması (56,57,66,67) veya 960 grubunu kontrol ediniz.")
                        
                # Buz Taneleri / Kar Taneleri
                if metarda_buz_taneleri:
                    if pd.isna(g960) and (pd.isna(ww) or ww not in [77, 79]):
                        kodlar.append("h350")
                        aciklamalar.append("METAR geçmişinde Buz/Kar Taneleri (PL/SG) raporlanmış. ww kodlaması (77, 79) veya 960 grubunu kontrol ediniz.")
                        
                # Toz ve Kum Fırtınası
                if metarda_toz_kum:
                    if pd.isna(g960) and (pd.isna(ww) or not (30 <= ww <= 35)):
                        kodlar.append("h351")
                        aciklamalar.append("METAR geçmişinde Toz/Kum Fırtınası (DS/SS) raporlanmış. ww kodlaması (30-35) veya 960 grubunu kontrol ediniz.")
                        
                # Squall (Orajlı Fırtına)
                if metarda_squall:
                    if pd.isna(g960) and ww != 18:
                        kodlar.append("h352")
                        aciklamalar.append("METAR geçmişinde Orajalı Fırtına (SQ) raporlanmış. ww=18 kodlamasını veya 960 grubunu kontrol ediniz.")
                        
                # 3.12 ww=20-29 Sona Eren Hadiselerin Geçmiş METAR ile Doğrulanması
                if pd.notna(ww) and 20 <= ww <= 29 and ww_cols:
                    beklenen_gecmis = []
                    if ww == 20: beklenen_gecmis = [50, 51, 52, 53, 54, 55, 77, 78]
                    elif ww == 21: beklenen_gecmis = [58, 59, 60, 61, 62, 63, 64, 65, 91, 92]
                    elif ww == 22: beklenen_gecmis = [70, 71, 72, 73, 74, 75, 93, 94]
                    elif ww == 23: beklenen_gecmis = [68, 69, 76, 79]
                    elif ww == 24: beklenen_gecmis = [56, 57, 66, 67]
                    elif ww == 25: beklenen_gecmis = [80, 81, 82, 91, 92]
                    elif ww == 26: beklenen_gecmis = [83, 84, 85, 86, 93, 94]
                    elif ww == 27: beklenen_gecmis = [87, 88, 89, 90, 93, 94]
                    elif ww == 28: beklenen_gecmis = list(range(42, 50))
                    elif ww == 29: beklenen_gecmis = [17, 95, 96, 97, 98, 99]
                    
                    gecmiste_var_mi = False
                    for c_ww in ww_cols:
                        for w in metar_kesit[c_ww]:
                            try:
                                if int(w) in beklenen_gecmis:
                                    gecmiste_var_mi = True
                                    break
                            except: pass
                    
                    if not gecmiste_var_mi:
                        if "h269" not in kodlar:
                            kodlar.append("h269")
                            aciklamalar.append(hata_dict.get("h269") + f" (Beklenen ww: {beklenen_gecmis})")
                        
                # 3.10 ve 3.11 Rüzgar, Basınç Çapraz Kontrolleri İptal Edildi
                # (Rüzgar, Basınç, Sıcaklık otomatik çekildiği için eşleşen saatlerde uyumsuzluk aranmaz)
        except Exception: pass

        # --- ÇAPRAZ KONTROL: METAR Bulut Katmanları vs SİNOPTİK (CL, CM, CH, Nh) ---
        metar_bulutlar = []
        metar_has_vv = False
        for i in range(1, 5):
            cins = s.get(f"{i}. bulut cins_metar")
            kap = s.get(f"{i}. bulut kap_metar")
            if pd.notna(cins) and str(cins).strip() != "":
                metar_bulutlar.append({
                    "cins": str(cins).strip().upper(),
                    "kap": str(kap).strip().upper() if pd.notna(kap) else ""
                })
            # NEW: Check for VV in METAR cloud groups
            if str(cins).strip().upper().startswith("VV"):
                metar_has_vv = True

        # NEW: Also check the main METAR bulten for VV
        bulten_metar = s.get("bulten_metar")
        if pd.notna(bulten_metar) and "VV" in clean_trend(bulten_metar):
            metar_has_vv = True

        if metar_bulutlar:
            metar_alcak_var = any(b["cins"] in ["CB", "TCU", "CU", "SC", "ST"] for b in metar_bulutlar)
            metar_orta_var = any(b["cins"] in ["AC", "AS", "NS"] for b in metar_bulutlar)
            metar_yuksek_var = any(b["cins"] in ["CI", "CS", "CC"] for b in metar_bulutlar)
            metar_cb_tcu_var = any(b["cins"] in ["CB", "TCU"] for b in metar_bulutlar)

            # If METAR reports Vertical Visibility (VV), it means the sky is obscured.
            # In this case, individual cloud layers (low, middle, high) are not discernible.
            # So, for cross-checking with SYNOPTIC, we should not expect specific CL/CM/CH codes.
            # SYNOPTIC N=9 (sky obscured) and CL/CM/CH = '/' (not reported) would be consistent.
            if not metar_has_vv: # Only perform individual cloud layer checks if VV is NOT present in METAR
                # SYNOP bulut varlığını kontrol et (hem CL/CM/CH hem de 8'li gruplardan)
                synop_has_low_cloud = (pd.notna(cl) and cl > 0)
                synop_has_mid_cloud = (pd.notna(cm) and cm > 0)
                synop_has_high_cloud = (pd.notna(ch) and ch > 0)

                all_bg_raw_vals = [_get_val(s, "cl"), _get_val(s, "cm"), _get_val(s, "ch"), _get_val(s, "bg4")]
                for val in all_bg_raw_vals:
                    if pd.isna(val): continue
                    bg_str = str(val).strip()
                    if bg_str.endswith(".0"): bg_str = bg_str[:-2]
                    if len(bg_str) == 5 and bg_str.startswith("8"):
                        try:
                            c_code = int(bg_str[2])
                            if c_code in {0, 1, 2}: synop_has_high_cloud = True
                            if c_code in {3, 4, 5}: synop_has_mid_cloud = True
                            if c_code in {6, 7, 8, 9}: synop_has_low_cloud = True
                        except (ValueError, IndexError):
                            pass

                # 1. Alçak Bulut Uyumsuzluğu
                if metar_alcak_var and not synop_has_low_cloud:
                    kodlar.append("h353")
                    aciklamalar.append("METAR'da Alçak Bulut raporlanmış ancak SİNOPTİK'te Alçak Bulut (CL veya C kodu) kodlanmamış.")

                # 2. Orta Bulut Uyumsuzluğu
                if metar_orta_var and not synop_has_mid_cloud:
                    kodlar.append("h354")
                    aciklamalar.append("METAR'da Orta Bulut raporlanmış ancak SİNOPTİK'te Orta Bulut (CM veya C kodu) kodlanmamış.")

                # 3. Yüksek Bulut Uyumsuzluğu
                if metar_yuksek_var and not synop_has_high_cloud:
                    kodlar.append("h355")
                    aciklamalar.append("METAR'da Yüksek Bulut raporlanmış ancak SİNOPTİK'te Yüksek Bulut (CH veya C kodu) kodlanmamış.")

                # 4. CB / TCU Özel Kontrolü
                if metar_cb_tcu_var:
                    cb_tcu_in_synop = False
                    if pd.notna(cl) and cl in [2, 3, 9]:
                        cb_tcu_in_synop = True
                    else:
                        for val in all_bg_raw_vals:
                            if pd.isna(val): continue
                            bg_str = str(val).strip().split('.')[0]
                            if len(bg_str) == 5 and bg_str.startswith("8") and bg_str[2] == '9':
                                cb_tcu_in_synop = True; break
                    if not cb_tcu_in_synop:
                        kodlar.append("h356")
                        aciklamalar.append(f"METAR'da Kümülonimbüs (CB/TCU) mevcut, ancak SİNOPTİK'te CL kodu (2, 3, 9) veya C kodu (9) bulunamadı.")

                # 5. Nh (Alçak/Orta Bulut Kapalılığı) Mantık Kontrolü
                if pd.notna(nh) and nh == 0 and (metar_alcak_var or metar_orta_var):
                    kodlar.append("h357")
                    aciklamalar.append("METAR'da Alçak veya Orta bulut katmanı var ancak SİNOPTİK Nh (Alçak/Orta Kapalılık) 0 kodlanmış.")

        # --- EKSİK GRUP KONTROLLERİ ---
        # Eğer satırda herhangi bir veri varsa (veri_var=True) ama zorunlu gruplar yoksa hata ver
        if veri_var:
            def sutun_var(k): return f"{k}_sin" in dolu_sutunlar or k in dolu_sutunlar
            
            if pd.isna(t) and sutun_var('t'): kodlar.append("h252"); aciklamalar.append(f"{hata_dict.get('h252')} (Sıcaklık 't' okunamadı)")
            if pd.isna(td) and sutun_var('td'): kodlar.append("h253"); aciklamalar.append(f"{hata_dict.get('h253')} (İşba 'td' okunamadı)")
            if pd.isna(p) and sutun_var('p'): kodlar.append("h254"); aciklamalar.append(f"{hata_dict.get('h254')} (İst. Basıncı 'p' okunamadı)")
            if pd.isna(p0) and sutun_var('p0'): kodlar.append("h255"); aciklamalar.append(f"{hata_dict.get('h255')} (Deniz Basıncı 'p0' okunamadı)")
            if pd.isna(a) and sutun_var('a'): kodlar.append("h256"); aciklamalar.append(f"{hata_dict.get('h256')} (Basınç Karakteri 'a' okunamadı)")
            if pd.isna(n) and sutun_var('n'): kodlar.append("h257"); aciklamalar.append(f"{hata_dict.get('h257')} (Bulut 'n' okunamadı)")
            
            if gmt == 18 and pd.isna(tx) and sutun_var('tx'):
                kodlar.append("h258")
                aciklamalar.append(f"{hata_dict.get('h258')} (Maks. Sıcaklık 'tx' okunamadı)")
            if gmt == 6 and pd.isna(tn) and sutun_var('tn'):
                kodlar.append("h259")
                aciklamalar.append(f"{hata_dict.get('h259')} (Min. Sıcaklık 'tn' okunamadı)")
            if gmt == 6 and pd.isna(tg) and pd.isna(e) and sutun_var('tg'):
                kodlar.append("h260")
                aciklamalar.append(f"{hata_dict.get('h260')} (Toprak 'tg' okunamadı)")
        
        # h261 & Mantık/924: Dolu ve 924 Grubu Çapraz Kontrolü (Geçmiş saatleri kapsayacak şekilde)
        dolu_var_mi = False
        if pd.notna(ww) and ww in [87, 88, 89, 90, 93, 94, 96, 99]:
            dolu_var_mi = True
            
        gecmiste_dolu_var_mi = dolu_var_mi
        if not gecmiste_dolu_var_mi:
            # METAR veya geçmiş Sinoptik'te dolu var mı kontrol et (son 6 saat)
            try:
                lookback_dolu = 6 if gmt in [0, 6, 12, 18] else 3
                metar_kesit_dolu = get_metar_history(lookback_dolu)
                ww_cols_dolu = [c for c in ["ww", "ww2", "ww3"] if c in df_metar.columns]
                
                if ww_cols_dolu:
                    gecmiste_dolu_var_mi = any(is_dolu(w) for c_ww in ww_cols_dolu for w in metar_kesit_dolu[c_ww])
                
                bulten_col = "bulten" if "bulten" in df_metar.columns else None
                if bulten_col and not metar_kesit_dolu.empty:
                    gecmiste_dolu_var_mi = any(pd.notna(msg) and re.search(r'\b(GR|GS)\b', clean_trend(msg)) for msg in metar_kesit_dolu[bulten_col])
            except:
                pass
                
        if dolu_var_mi and pd.isna(g924):
            pass # Kullanıcı İsteği: 924 (Dolu Çapı) kaydı yapılmıyor dikkate alınmayacak
            # kodlar.append("h261")
            # aciklamalar.append(hata_dict.get("h261", "Dolu raporlandığı halde 924 grubu koda dahil edilmedi."))
            
        # YENİ EKLENEN: 924 (Dolu Çapı) Grubu Mantık ve Boyut Kontrolleri
        if pd.notna(g924):
            if not gecmiste_dolu_var_mi:
                if "h359" not in kodlar:
                    kodlar.append("h359")
                    aciklamalar.append("924 (Dolu Çapı) grubu girilmiş ancak Halihazır Hava (ww) veya periyottaki geçmiş METAR'larda dolu hadisesi bulunamadı.")
            
            try:
                g924_str = str(int(float(g924)))
                cap = int(g924_str[3:]) if len(g924_str) == 5 and g924_str.startswith("924") else int(float(g924))
                
                if cap > 50:
                    kodlar.append("h360")
                    aciklamalar.append(f"Dolu çapı çok ekstrem bir değer olarak girilmiş ({cap} mm). Lütfen değeri kontrol ediniz.")
            except:
                pass

        # h262: Hadise Kayıtlarında eksiklik
        if "hadise_kayit" in s and (pd.isna(hadise_kayit) or str(hadise_kayit).strip() == "") and pd.notna(ww) and ww >= 4:
            if sutun_var('hadise_kayit'):
                kodlar.append("h262")
                aciklamalar.append(hata_dict.get("h262"))
            
        # h266: Rasat metni kontrolü (Veri bütünlüğü teyidi)
        if pd.notna(gmt) and (pd.isna(rasatlar) or len(str(rasatlar).strip()) < 5):
            kodlar.append("h266")
            aciklamalar.append(hata_dict.get("h266"))
            
        # --- YENİ: PHP Validation Mantığı (SynopDecoder Entegrasyonu) ---
        # Eğer satırda ham bir rasat metni varsa, WMO FM-12 sözdizimine (syntax) uygunluğunu denetle
        if pd.notna(rasatlar) and len(str(rasatlar).strip()) >= 5:
            # Eğer veri bizim Excel okuyucu tarafından "COL:VAL" şeklinde üretildiyse (örn: IR:1 IX:2) es geç
            if ":" not in str(rasatlar) and SynopDecoder is not None:
                try:
                    decoder = SynopDecoder()
                    s_data = decoder.decode_line(str(rasatlar))
                    
                    if s_data:
                        # DECODER İLE SAĞLAMA (DECODER DOĞRUYSA EXCEL HATALARINI GÖRMEZDEN GEL)
                        if 'yagis_suresi_kod' in s_data:
                            dec_tr = s_data['yagis_suresi_kod']
                            if gmt in [0, 12] and dec_tr != 1:
                                if "h376" not in kodlar:
                                    kodlar.append("h376")
                                    aciklamalar.append(f"0000 ve 1200 GMT ana rasatlarında yağış ölçüm periyodu 6 saat (tR=1) olmalıdır. Şifrede 6RRR{dec_tr} girilmiş.")
                            elif gmt in [6, 18] and dec_tr != 2:
                                if "h376" not in kodlar:
                                    kodlar.append("h376")
                                    aciklamalar.append(f"0600 ve 1800 GMT ana rasatlarında yağış ölçüm periyodu 12 saat (tR=2) olmalıdır. Şifrede 6RRR{dec_tr} girilmiş.")

                        gormezden_gelinecekler = set()
                        if 'ruzgar_yon' in s_data:
                            m_dd = _to_float(_get_val(s, "dd_metar"))
                            if m_dd is not None:
                                # Decoder derece döner, METAR zaten derecedir. Fark 10 dereceden azsa Excel hatasını sil.
                                d_diff = min((s_data['ruzgar_yon'] - m_dd) % 360, (m_dd - s_data['ruzgar_yon']) % 360)
                                if d_diff <= 10:
                                    gormezden_gelinecekler.add("VAL_RUZGAR_YON")
                                    
                        if 'yagis_miktari_kod' in s_data:
                            gormezden_gelinecekler.update(["h4 (TEYİTLİ)", "h4 (DİKKAT)", "h4", "h70", "h71", "h72", "h73", "h230", "h315", "h383"])
                        if 'ruzgar_yon' in s_data and 'ruzgar_hiz' in s_data:
                            gormezden_gelinecekler.update(["h37", "h37/Mantık", "h38", "h39", "h43", "h44"])
                        if 'halihazir_hava' in s_data:
                            gormezden_gelinecekler.update(["h78", "h79", "h80", "h81", "h82", "h83", "h84", "h85", "h86", "h87", "h88", "h89", "h90", "h91", "h92", "h93", "h94", "h95", "h96", "h97", "h98", "h100", "h101", "h102", "h103", "h104", "h105", "h106", "h107", "h108", "h109", "h110", "h111", "h348", "h349", "h350", "h351", "h352"])
                        if 'gecmis_hava1' in s_data or 'gecmis_hava2' in s_data:
                            gormezden_gelinecekler.update(["h116", "h117", "h118", "h269", "h326", "h327", "h333", "h334", "h335", "h336", "h337", "h338", "h339"])
                            
                        if 'max_sicaklik' in s_data:
                            gormezden_gelinecekler.update(["h186", "h258"])
                        if 'min_sicaklik' in s_data:
                            gormezden_gelinecekler.update(["h192", "h259"])
                        if 'yer_sicakligi' in s_data or 'yerin_hali_E' in s_data:
                            gormezden_gelinecekler.update(["h196", "h260"])

                        if 'toplam_bulut' in s_data:
                            raw_n = s_data.get('toplam_bulut')
                            raw_nh = s_data.get('alcak_bulut_miktari')
                            c_errs = ["h26", "h27", "h30", "h31", "h32", "h33", "h36", "h121", "h125", "h128", "h132", "h134", "h135", "h139", "h151", "h152", "h154", "h155", "h164", "h167", "h168", "h170", "h314", "h311", "h312", "h313", "h162", "h163"]
                            
                            if raw_n is not None and raw_nh is not None and raw_n != 9 and raw_nh != 9 and raw_nh > raw_n:
                                pass # Şifrenin kendisinde de hata var, h120/h34 kalsın
                            else:
                                c_errs.extend(["h34", "h120"])
                                
                            gormezden_gelinecekler.update(c_errs)
                        
                        if gormezden_gelinecekler:
                            yeni_kodlar = []
                            yeni_aciklamalar = []
                            for k, a in zip(kodlar, aciklamalar):
                                if k not in gormezden_gelinecekler:
                                    yeni_kodlar.append(k)
                                    yeni_aciklamalar.append(a)
                            kodlar = yeni_kodlar
                            aciklamalar = yeni_aciklamalar

                    if not decoder.validate():
                        for err in decoder.get_errors():
                            kodlar.append("h362")
                            aciklamalar.append(f"Format Hatası: {err}")
                except: pass

        if kodlar:
            ek_metar_bilgisi = ""
            try:
                lb = 6 if gmt in [0, 6, 12, 18] else 3
                hist_df = get_metar_history(lb)
                bulten_col = "bulten" if "bulten" in df_metar.columns else None
                if bulten_col and not hist_df.empty:
                    m_list = []
                    for _, m_row in hist_df.iterrows():
                        if pd.notna(m_row[bulten_col]):
                            m_raw = str(m_row[bulten_col]).strip()
                            if m_raw.replace('"', '').replace("'", "").strip().lower() in ['nan', 'none', '<na>', '-', '']:
                                continue
                            z_match = re.search(r'\b\d{2}(\d{4}Z?)\b', m_raw)
                            m_saat = z_match.group(1) if z_match else (f"{int(m_row.get('gmt', 0)):02d}00Z")
                            m_list.append(f"[{m_saat}] {m_raw}")
                    if m_list:
                        m_list.reverse() # En yenisi üstte, en eskisi altta olacak şekilde sırala
                        ek_metar_bilgisi = "İLGİLİ METAR GEÇMİŞİ:\n" + "\n".join(m_list)
            except:
                pass
            return ("Hata Var", ", ".join(kodlar), " | ".join(aciklamalar), ek_metar_bilgisi)
        else:
            return ("Hata Yok", "", "", "")

    kayitlar = birlesik_df.to_dict('records')
    with concurrent.futures.ThreadPoolExecutor() as executor:
        sonuclar = list(executor.map(hata_ara, kayitlar))
    sonuc = pd.DataFrame(sonuclar, columns=["ANALİZ_SONUCU", "HATA_KODLARI", "HATA_ACIKLAMALARI", "EK_METAR_BILGISI"], index=birlesik_df.index)

    birlesik_df = pd.concat([birlesik_df, sonuc], axis=1)
    
    if "EK_METAR_BILGISI" in birlesik_df.columns:
        b_col = "bulten_metar" if "bulten_metar" in birlesik_df.columns else "bulten"
        if b_col in birlesik_df.columns:
            mask = birlesik_df["EK_METAR_BILGISI"].astype(str).str.strip() != ""
            
            def _clean_bulten(val):
                val_str = str(val).strip()
                if val_str.replace('"', '').replace("'", "").strip().lower() in ['nan', 'none', '<na>', '-', '']: return ""
                return val_str
                
            for idx in birlesik_df[mask].index:
                mevcut = _clean_bulten(birlesik_df.at[idx, b_col])
                ek = str(birlesik_df.at[idx, "EK_METAR_BILGISI"]).strip()
                
                if (not mevcut or len(mevcut) < 10) and "İLGİLİ METAR GEÇMİŞİ:" in ek:
                    lines = ek.split('\n')
                    if len(lines) > 1:
                        m_reg = re.match(r'^\[.*?\]\s*(.*)', lines[1])
                        if m_reg:
                            mevcut = m_reg.group(1)
                            
                if mevcut:
                    if ek not in mevcut:
                        birlesik_df.at[idx, b_col] = mevcut + "\n\n" + ek
                    else:
                        birlesik_df.at[idx, b_col] = mevcut
                else:
                    birlesik_df.at[idx, b_col] = ek
                
        birlesik_df.drop(columns=["EK_METAR_BILGISI"], inplace=True)
        
    return birlesik_df
