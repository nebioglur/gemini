import pandas as pd
import math
import datetime
import kurallar
import sys
import os
import re

# Ana dizindeki synop_decoder.py modülüne erişebilmek için yolu (path) ekliyoruz
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from synop_decoder import SynopDecoder
except ImportError:
    SynopDecoder = None

def hata_analizi_yap(birlesik_df, df_metar):
    """
    Birleştirilmiş veri setini tarar ve hataları tespit eder.
    """
    hata_dict = kurallar.HATA_SOZLUGU

    # Dosyada tamamen eksik veya boş olan sütunları tespit et (Gereksiz "Eksik Grup" hatalarını önlemek için)
    dolu_sutunlar = set()
    for col in birlesik_df.columns:
        if birlesik_df[col].notna().any():
            dolu_sutunlar.add(col)

    def hata_ara(s):
        kodlar, aciklamalar = [], []

        # Merge işleminden kaynaklı _sin/_metar eklerini yönetmek için yardımcı fonksiyon
        def get_val(key):
            # SADECE SİNOPTİK (METAR'a fallback yapmayı engelliyoruz)
            # Böylece SİNOPTİK tarafında boş olan hücreler METAR ile doldurulup 
            # h37, h34 gibi sahte hatalar oluşturmaz.
            
            # 1. _sin ekiyle bul (merge sonrası SİNOPTİK verisi)
            sin_key = f"{key}_sin"
            if sin_key in s:
                val = s[sin_key]
                if pd.notna(val):
                    return val
                    
            # 2. Direkt olarak bul (merge öncesi veya isimsiz sütunlar)
            if key in s:
                val = s[key]
                if pd.notna(val):
                    return val
            
            return None

        def to_float(val):
            try: return float(val) if pd.notna(val) else None
            except: return None

        ir = to_float(get_val("ir"))
        rrr = to_float(get_val("rrr"))
        ix = to_float(get_val("ix"))
        ww = to_float(get_val("ww"))
        w1 = to_float(get_val("w1"))
        w2 = to_float(get_val("w2"))
        t = to_float(get_val("t"))
        td = to_float(get_val("td"))
        tx = to_float(get_val("tx"))
        tn = to_float(get_val("tn"))
        tg = to_float(get_val("tg"))
        n = to_float(get_val("n"))
        nh = to_float(get_val("nh"))
        cl = to_float(get_val("cl"))
        cm = to_float(get_val("cm"))
        ch = to_float(get_val("ch"))
        dd = to_float(get_val("dd"))
        ff = to_float(get_val("ff"))
        vv = to_float(get_val("vv"))
        a = to_float(get_val("a"))
        ppp = to_float(get_val("ppp"))
        p = to_float(get_val("p"))
        p0 = to_float(get_val("p0"))
        e = to_float(get_val("e"))
        h = to_float(get_val("h"))
        tr = to_float(get_val("tr"))
        gmt = s.get("gmt")
        g924 = get_val("g924")
        g931 = get_val("g931")
        g932 = get_val("g932")
        g960 = get_val("g960")
        hadise_kayit = get_val("hadise_kayit")
        rasatlar = get_val("RASATLAR")
        gunes = get_val("gunes")
        buhar = get_val("buhar")

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
            if dt_b.date() == dt_s.date():
                return df_metar[(df_metar["sayfa"] == t_str) & (df_metar["gmt"] > dt_b.hour) & (df_metar["gmt"] <= gmt)]
            else:
                p_str = dt_b.strftime('%d.%m.%Y')
                m_prev = (df_metar["sayfa"] == p_str) & (df_metar["gmt"] > dt_b.hour)
                m_curr = (df_metar["sayfa"] == t_str) & (df_metar["gmt"] <= gmt)
                return pd.concat([df_metar[m_prev], df_metar[m_curr]])
                
        def get_sinoptik_prev(hours_back):
            dt_s = get_dt_suan()
            if not dt_s: return pd.DataFrame()
            dt_prev = dt_s - datetime.timedelta(hours=hours_back)
            return birlesik_df[(birlesik_df["sayfa"] == dt_prev.strftime('%d.%m.%Y')) & (birlesik_df["gmt"] == dt_prev.hour)]

        def vv_to_meters(vv_val):
            try:
                v = float(vv_val)
                if v <= 50: return v * 100
                elif 56 <= v <= 80: return (v - 50) * 1000
                elif 81 <= v <= 89: return 30000 + (v - 80) * 5000
            except: pass
            return -1

        def is_yagis(w):
            try: return (20 <= int(w) <= 27) or (50 <= int(w) <= 99)
            except: 
                cw = clean_trend(w) if 'clean_trend' in locals() else str(w).upper()
                return bool(re.search(r'(?:^|\s)(RE|-|\+|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?(RA|SN|DZ|GR|GS|SG|PL|UP|SH)(?:\s|$)', cw))

        def is_sis(w):
            try: return 40 <= int(w) <= 49
            except: 
                cw = clean_trend(w) if 'clean_trend' in locals() else str(w).upper()
                return bool(re.search(r'(?:^|\s)(RE|-|\+|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?(FG)(?:\s|$)', cw))

        def is_oraj(w):
            try: return int(w) in [17, 29] or (95 <= int(w) <= 99)
            except: 
                cw = clean_trend(w) if 'clean_trend' in locals() else str(w).upper()
                return bool(re.search(r'(?:^|\s)(RE|-|\+|VC)?(TS)(RA|SN|DZ|GR|GS|SG|PL|UP|FG|BR|HZ|SA|DU)?(?:\s|$)', cw))

        def is_dolu(w):
            try: return int(w) in [87, 88, 89, 90, 93, 94, 96, 99]
            except: 
                cw = clean_trend(w) if 'clean_trend' in locals() else str(w).upper()
                return bool(re.search(r'(?:^|\s)(RE|-|\+|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?(GR|GS)(?:\s|$)', cw))

        def is_tozkum_firtinasi(w):
            try: return 30 <= int(w) <= 35
            except: 
                cw = clean_trend(w) if 'clean_trend' in locals() else str(w).upper()
                return bool(re.search(r'(?:^|\s)(RE|-|\+|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?(SS|DS)(?:\s|$)', cw))

        # (Kodun devamı...)

    kayitlar = birlesik_df.to_dict('records')
    sonuclar = [hata_ara(satir) for satir in kayitlar]
    sonuc = pd.DataFrame(sonuclar, columns=["ANALİZ_SONUCU", "HATA_KODLARI", "HATA_ACIKLAMALARI"], index=birlesik_df.index)

    return pd.concat([birlesik_df, sonuc], axis=1)
