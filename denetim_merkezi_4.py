import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
import datetime
import calendar
import pandas as pd
import os

# Modülleri içe aktar
import denetim_merkezi_1 as dm1
import denetim_merkezi_2 as dm2
import denetim_merkezi_3 as dm3

def aylik_rapor_olustur():
    try:
        messagebox.showinfo("1. Adım", "SİNOPTİK dosyasını seç")
        sin_yolu = filedialog.askopenfilename(filetypes=[("Veri Dosyaları", "*.xls *.xlsx *.txt"), ("Excel", "*.xls *.xlsx"), ("Metin", "*.txt")])
        if not sin_yolu: return

        messagebox.showinfo("2. Adım", "METAR dosyasını seç")
        metar_yolu = filedialog.askopenfilename(filetypes=[("Veri Dosyaları", "*.xls *.xlsx *.txt"), ("Excel", "*.xls *.xlsx")])
        if not metar_yolu: return

        simdi = datetime.datetime.now()
        varsayilan_ay = simdi.month - 1 if simdi.month > 1 else 12
        varsayilan_yil = simdi.year if simdi.month > 1 else simdi.year - 1

        yil = simpledialog.askinteger("Yıl", "Rapor Yılı:", initialvalue=varsayilan_yil, minvalue=2000, maxvalue=2030)
        if not yil: return
        ay = simpledialog.askinteger("Ay", "Rapor Ayı:", initialvalue=varsayilan_ay, minvalue=1, maxvalue=12)
        if not ay: return
    except Exception as e:
        messagebox.showerror("Hata", str(e))
        return

    btn_run.config(state=tk.DISABLED, text="İşleniyor... Lütfen Bekleyin")

    def islem_yurut():
        try:
            # 1. Veri Okuma
            df_sin = dm1.dosya_oku_akilli(sin_yolu)
            df_metar = dm1.dosya_oku_akilli(metar_yolu)

            # Okuma Raporu
            okuma_raporu = ""
            try:
                if not df_sin.empty and "sayfa" in df_sin.columns:
                    sheets = sorted(df_sin["sayfa"].unique().astype(str), key=lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else 0)
                    mapped = []
                    for s in sheets:
                        t = dm1.tarih_olustur_helper(s, yil, ay)
                        if t: mapped.append(f"[{s}] -> {t}")
                    okuma_raporu = "SİNOPTİK SAYFA - TARİH EŞLEŞMELERİ:\n" + "-"*40 + "\n" + ("\n".join(mapped) if mapped else "⚠️ Eşleşme yok")
            except: pass

            # GMT Kontrolü (Sütun İsimlendirme - Temizlikten Önce Yapılmalı)
            if "gmt" not in df_sin.columns:
                # Akıllı GMT Sütunu Bulma
                gmt_col_found = None
                for col in df_sin.columns:
                    try:
                        vals = df_sin[col].dropna().unique()
                        target_hours = {0, 3, 6, 9, 12, 15, 18, 21, '00', '03', '06', '09', '12', '15', '18', '21'}
                        match_count = sum(1 for v in vals if v in target_hours)
                        
                        # Sayısal Aralık Kontrolü (0-23 arası mı?) - İstasyon No (17xxx) karışmasını önler
                        is_valid_range = False
                        try:
                            nums = pd.to_numeric(vals, errors='coerce')
                            nums = nums[~pd.isna(nums)]
                            if len(nums) > 0 and nums.min() >= 0 and nums.max() <= 23:
                                is_valid_range = True
                        except: pass

                        if match_count >= 2 or (is_valid_range and len(vals) >= 2):
                            gmt_col_found = col; break
                    except: pass
                
                if gmt_col_found: 
                    df_sin.rename(columns={gmt_col_found: "gmt"}, inplace=True)
                else:
                    # Fallback: Bilinen sütunları atla, ilk uygun sütunu GMT yap
                    known_cols = ['istasyon_no', 'sayfa', 'tarih', 'personel', 'rasatci']
                    for col in df_sin.columns:
                        if str(col).lower() not in known_cols:
                            df_sin.rename(columns={col: "gmt"}, inplace=True)
                            break
            if "gmt" not in df_metar.columns:
                if len(df_metar.columns) > 0: df_metar.rename(columns={df_metar.columns[0]: "gmt"}, inplace=True)

            # GÜVENLİK: Eksik sütunlardan kaynaklanan KeyError: 'sayfa' çökmelerini önlemek için
            if "sayfa" not in df_sin.columns: df_sin["sayfa"] = "1"
            if "gmt" not in df_sin.columns: df_sin["gmt"] = 0.0
            if "sayfa" not in df_metar.columns: df_metar["sayfa"] = "1"
            if "gmt" not in df_metar.columns: df_metar["gmt"] = 0.0

            # Veri Temizliği ve Hazırlığı
            for i, df in enumerate([df_sin, df_metar]):
                is_metar = (i == 1) # 1. indeks METAR
                
                # Önce Tarih Formatını Düzenle (Tarih kaydırma için gerekli)
                df["sayfa"] = df["sayfa"].astype(str)
                df["sayfa"] = df["sayfa"].apply(lambda x: dm1.tarih_olustur_helper(x, yil, ay))
                df.dropna(subset=["sayfa"], inplace=True)

                if "gmt" in df.columns:
                    # Saat Temizliği ve Ayrıştırma
                    df["gmt_raw"] = df["gmt"].astype(str).str.upper().str.replace('Z', '').str.strip()
                    
                    if is_metar:
                        # METAR için en yakın Sinoptik saatini bul (0050 -> 00, 2350 -> 00 ertesi gün)
                        def match_time(row):
                            val = row["gmt_raw"]
                            date_val = row["sayfa"]
                            h, m = 0, 0
                            try:
                                if ":" in val: parts = val.split(":"); h, m = int(parts[0]), int(parts[1])
                                elif len(val) == 4 and val.isdigit(): h, m = int(val[:2]), int(val[2:])
                                elif val.isdigit(): h = int(val)
                                else: return None, None
                            except: return None, None

                            total = h * 60 + m
                            targets = [0, 3, 6, 9, 12, 15, 18, 21, 24] # 24 = Ertesi gün 00
                            target_mins = [t * 60 for t in targets]
                            
                            closest_idx = min(range(len(target_mins)), key=lambda i: abs(target_mins[i] - total))
                            closest_h = targets[closest_idx]
                            
                            if closest_h == 24:
                                closest_h = 0
                                try:
                                    dt = pd.to_datetime(date_val, format="%d.%m.%Y") + datetime.timedelta(days=1)
                                    date_val = dt.strftime("%d.%m.%Y")
                                except: pass
                            
                            return closest_h, date_val

                        res = df.apply(match_time, axis=1, result_type='expand')
                        df["gmt"] = res[0]
                        df["sayfa"] = res[1]
                    else:
                        # Sinoptik
                        df["gmt"] = df["gmt_raw"].str.split(':').str[0]
                        df["gmt"] = pd.to_numeric(df["gmt"], errors="coerce")

                    df.dropna(subset=["gmt"], inplace=True)
                
                numeric_cols = ['ir', 'ix', 'rrr', 'ww', 'w1', 'w2', 't', 'td', 'n', 'nh', 'cl', 'cm', 'ch', 'dd', 'ff', 'vv', 'a', 'ppp', 'tx', 'tn', 'tg', 'p', 'p0', 'e', 'h', 'tr', 'g924', 'g910', 'g911', 'g931', 'g932', 'g960']
                for col in numeric_cols:
                    if col in df.columns:
                        # ayrılmış ondalık sayıları noktaya (.) çevir (Örn: 3,5 -> 3.5)
                        if df[col].dtype == 'object':
                            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                        df[col] = pd.to_numeric(df[col], errors="coerce")

            if df_sin.empty:
                raise ValueError("Sinoptik verileri işlendikten sonra boş kaldı! Tarih veya Saat sütunları okunamamış olabilir.\nLütfen Excel sayfa isimlerinin (1, 2, 3...) veya tarih formatının doğru olduğundan emin olun.")

            # Rasatlar Sütunu
            if not df_sin.empty:
                def raw_rasat_olustur(row):
                    if '_raw_line' in row and pd.notna(row['_raw_line']):
                        return str(row['_raw_line'])
                        
                    parts = []
                    
                    def to_int_str(val, length=1):
                        if pd.isna(val) or str(val).strip() == "": return "/" * length
                        try:
                            return str(int(float(val))).zfill(length)
                        except: return "/" * length

                    ir = to_int_str(row.get('ir'), 1)
                    ix = to_int_str(row.get('ix'), 1)
                    h = to_int_str(row.get('h'), 1)
                    vv = to_int_str(row.get('vv'), 2)
                    parts.append(f"{ir}{ix}{h}{vv}")
                    
                    n = to_int_str(row.get('n'), 1)
                    dd = to_int_str(row.get('dd'), 2)
                    ff = to_int_str(row.get('ff'), 2)
                    parts.append(f"{n}{dd}{ff}")
                    
                    t = row.get('t')
                    if pd.notna(t) and str(t).strip() != "":
                        try:
                            t_val = float(t)
                            sn = "1" if t_val < 0 else "0"
                            t_str = str(int(round(abs(t_val) * 10))).zfill(3)
                            parts.append(f"1{sn}{t_str}")
                        except: pass
                        
                    td = row.get('td')
                    if pd.notna(td) and str(td).strip() != "":
                        try:
                            td_val = float(td)
                            sn = "1" if td_val < 0 else "0"
                            td_str = str(int(round(abs(td_val) * 10))).zfill(3)
                            parts.append(f"2{sn}{td_str}")
                        except: pass
                        
                    p = row.get('p')
                    if pd.notna(p) and str(p).strip() != "":
                        try:
                            p_val = float(p)
                            p_str = str(int(round(p_val * 10)))[-4:]
                            parts.append(f"3{p_str}")
                        except: pass
                        
                    p0 = row.get('p0')
                    if pd.notna(p0) and str(p0).strip() != "":
                        try:
                            p0_val = float(p0)
                            p0_str = str(int(round(p0_val * 10)))[-4:]
                            parts.append(f"4{p0_str}")
                        except: pass
                        
                    a = row.get('a')
                    ppp = row.get('ppp')
                    if pd.notna(a) and str(a).strip() != "" and pd.notna(ppp) and str(ppp).strip() != "":
                        try:
                            a_str = str(int(float(a)))
                            ppp_str = str(int(round(float(ppp) * 10))).zfill(3)
                            parts.append(f"5{a_str}{ppp_str}")
                        except: pass
                        
                    rrr = row.get('rrr')
                    tr = row.get('tr')
                    if pd.notna(rrr) and str(rrr).strip() != "" and pd.notna(tr) and str(tr).strip() != "":
                        try:
                            rrr_str = str(int(float(rrr))).zfill(3)
                            tr_str = str(int(float(tr)))
                            parts.append(f"6{rrr_str}{tr_str}")
                        except: pass
                        
                    ww = to_int_str(row.get('ww'), 2)
                    w1 = to_int_str(row.get('w1'), 1)
                    w2 = to_int_str(row.get('w2'), 1)
                    if ww != "//" or w1 != "/" or w2 != "/":
                        parts.append(f"7{ww}{w1}{w2}")
                        
                    nh = to_int_str(row.get('nh'), 1)
                    cl = to_int_str(row.get('cl'), 1)
                    cm = to_int_str(row.get('cm'), 1)
                    ch = to_int_str(row.get('ch'), 1)
                    if nh != "/" or cl != "/" or cm != "/" or ch != "/":
                        parts.append(f"8{nh}{cl}{cm}{ch}")
                        
                    sec333 = []
                    tx = row.get('tx')
                    if pd.notna(tx) and str(tx).strip() != "":
                        try:
                            tx_val = float(tx)
                            sn = "1" if tx_val < 0 else "0"
                            tx_str = str(int(round(abs(tx_val) * 10))).zfill(3)
                            sec333.append(f"1{sn}{tx_str}")
                        except: pass
                        
                    tn = row.get('tn')
                    if pd.notna(tn) and str(tn).strip() != "":
                        try:
                            tn_val = float(tn)
                            sn = "1" if tn_val < 0 else "0"
                            tn_str = str(int(round(abs(tn_val) * 10))).zfill(3)
                            sec333.append(f"2{sn}{tn_str}")
                        except: pass
                        
                    tg = row.get('tg')
                    e = row.get('e')
                    if pd.notna(tg) and str(tg).strip() != "" and pd.notna(e) and str(e).strip() != "":
                        try:
                            e_str = str(int(float(e)))
                            tg_val = float(tg)
                            sn = "1" if tg_val < 0 else "0"
                            tg_str = str(int(round(abs(tg_val)))).zfill(2)
                            sec333.append(f"3{e_str}{sn}{tg_str}")
                        except: pass
                        
                    g910 = row.get('g910')
                    if pd.notna(g910) and str(g910).strip() != "":
                        try:
                            g910_str = str(int(float(g910)))
                            if len(g910_str) == 5 and g910_str.startswith("910"): sec333.append(g910_str)
                            else: sec333.append(f"910{g910_str.zfill(2)}")
                        except: pass
                        
                    g911 = row.get('g911')
                    if pd.notna(g911) and str(g911).strip() != "":
                        try:
                            g911_str = str(int(float(g911)))
                            if len(g911_str) == 5 and g911_str.startswith("911"): sec333.append(g911_str)
                            else: sec333.append(f"911{g911_str.zfill(2)}")
                        except: pass
                        
                    g931 = row.get('g931')
                    if pd.notna(g931) and str(g931).strip() != "":
                        try:
                            g931_str = str(int(float(g931)))
                            if len(g931_str) == 5 and g931_str.startswith("931"): sec333.append(g931_str)
                            else: sec333.append(f"931{g931_str.zfill(2)}")
                        except: pass
                        
                    g932 = row.get('g932')
                    if pd.notna(g932) and str(g932).strip() != "":
                        try:
                            g932_str = str(int(float(g932)))
                            if len(g932_str) == 5 and g932_str.startswith("932"): sec333.append(g932_str)
                            else: sec333.append(f"932{g932_str.zfill(2)}")
                        except: pass
                    
                    g960 = row.get('g960')
                    if pd.notna(g960) and str(g960).strip() != "":
                        try:
                            g960_str = str(int(float(g960)))
                            if len(g960_str) == 5 and g960_str.startswith("960"): sec333.append(g960_str)
                            else: sec333.append(f"960{g960_str.zfill(2)}")
                        except: pass

                    if sec333:
                        parts.append("333")
                        parts.extend(sec333)

                    return " ".join(parts)
                df_sin["RASATLAR"] = df_sin.apply(raw_rasat_olustur, axis=1)

            # Şablon ve Birleştirme
            _, son_gun = calendar.monthrange(yil, ay)
            sablon_data = []
            for d in range(1, son_gun + 1):
                t_str = pd.Timestamp(year=yil, month=ay, day=d).strftime('%d.%m.%Y')
                for h in [0, 3, 6, 9, 12, 15, 18, 21]:
                    sablon_data.append({"sayfa": t_str, "gmt": h})
            df_sablon = pd.DataFrame(sablon_data)

            df_sin = df_sin.drop_duplicates(subset=["sayfa", "gmt"])
            df_sin = pd.merge(df_sablon, df_sin, on=["sayfa", "gmt"], how="left")
            df_metar_tekil = df_metar.drop_duplicates(subset=["sayfa", "gmt"], keep="last")

            def _zaman_don(dframe):
                return pd.to_datetime(
                    dframe["sayfa"].astype(str).str.strip() + " " +
                    dframe["gmt"].fillna(0).astype(int).astype(str).str.zfill(2) + ":00",
                    format="%d.%m.%Y %H:%M",
                    errors="coerce"
                )

            df_sin["dt"] = _zaman_don(df_sin)
            df_metar_tekil["dt"] = _zaman_don(df_metar_tekil)
            df_sin.sort_values("dt", inplace=True)
            df_metar_tekil.sort_values("dt", inplace=True)

            birlesik = pd.merge_asof(
                df_sin,
                df_metar_tekil,
                on="dt",
                direction="nearest",
                tolerance=pd.Timedelta(hours=3),
                suffixes=("_sin", "_metar")
            )
            birlesik.drop(columns=[c for c in ["sayfa_metar", "gmt_metar"] if c in birlesik.columns], inplace=True, errors="ignore")
            birlesik.drop(columns=["dt"], inplace=True, errors="ignore")

            # 2. Hata Analizi
            birlesik = dm2.hata_analizi_yap(birlesik, df_metar)

            # Sütun İsimlendirme ve Sıralama
            col_map = {
                'sayfa': 'Tarih', 'gmt': 'Saat (GMT)', 'ir': 'İndikatör (ir)', 'ix': 'İndikatör (ix)',
                'h': 'Bulut Yük. (h)', 'vv': 'Görüş (VV)', 'n': 'Toplam Bulut (N)',
                'dd': 'Rüzgar Yönü (dd)', 'ff': 'Rüzgar Hızı (ff)', 't': 'Sıcaklık (T)',
                'td': 'İşba (Td)', 'p0': 'Deniz Basıncı (P0)', 'p': 'İstasyon Basıncı (P)',
                'a': 'Basınç Karakteri (a)', 'ppp': 'Basınç Değişimi (ppp)',
                'ww': 'Halihazır Hava (ww)', 'WW': 'Geçmiş Hava 1 (W1)', 'w2': 'Geçmiş Hava 2 (W2)',
                'nh': 'Alçak/Orta Bulut (Nh)', 'cl': 'Alçak Bulut (CL)', 'cm': 'Orta Bulut (CM)',
                'ch': 'Yüksek Bulut (CH)', 'tx': 'Maks. Sıcaklık (Tx)', 'tn': 'Min. Sıcaklık (Tn)',
                'tg': 'Toprak Sıcaklığı (Tg)', 'e': 'Yerin Hali (E)', 'rrr': 'Yağış Miktarı (RRR)',
                'tr': 'Yağış Süresi (tR)', 'g910': '910 Grubu (Hamle)', 'g911': '911 Grubu (Hamle)',
                'g931': '931 Grubu (Kar)', 'g932': '932 Grubu (Taze Kar)', 'g960': '960 Grubu (Hadise)', 'ANALİZ_SONUCU': 'DURUM',
                'buhar': 'Buharlaşma', 'rad_tipi': 'Radyasyon Tipi', 'radyasyon': 'Radyasyon Miktarı',
                'gunes': 'Güneşlenme Süresi', 'deniz_suyu': 'Deniz Suyu Sıc.', 'rrr_toplam': 'Toplam Yağış',
                'buh_alet_tipi': 'Buhar Aleti Tipi', 'e_kar': 'Yerin Hali (Kar)',
                'HATA_KODLARI': 'HATA KODU', 'HATA_ACIKLAMALARI': 'AÇIKLAMA',
                'RASATLAR': 'RASATLAR', 'g924': '924 Grubu', 'hadise_kayit': 'Hadise Kayıtları',
                'personel': 'Personel'
            }
            new_columns = {}
            for c in birlesik.columns:
                base = c.replace('_sin', '').replace('_metar', '')
                suffix = '_sin' if '_sin' in c else ('_metar' if '_metar' in c else '')
                if base in col_map:
                    new_name = col_map[base]
                    if suffix == '_sin': new_name = f"SİNOPTİK - {new_name}"
                    elif suffix == '_metar': new_name = f"METAR - {new_name}"
                    new_columns[c] = new_name
                else: new_columns[c] = c.upper()
            birlesik.rename(columns=new_columns, inplace=True)

            # Aynı isme sahip sütunlar oluşursa (Örn: iki tane PERSONEL) Pandas'ın çökmesini engellemek için tekilleştir
            if any(birlesik.columns.duplicated()):
                cols = pd.Series(birlesik.columns)
                for dup in cols[cols.duplicated()].unique():
                    dup_indices = cols[cols == dup].index.tolist()
                    for idx_num, idx in enumerate(dup_indices):
                        if idx_num != 0:
                            cols[idx] = f"{dup}_{idx_num}"
                birlesik.columns = cols
            birlesik.columns = cols.tolist()

            # Önemli sütunları başa al (RASATLAR'ı görünür yap)
            oncelikli = ['Tarih', 'Saat (GMT)', 'DURUM', 'HATA KODU', 'RASATLAR', 'AÇIKLAMA']
            mevcut_oncelikli = [c for c in oncelikli if c in birlesik.columns]
            # UNNAMED sütunlarını nihai Excel raporundan gizle (Zaten RASATLAR sütununa eklendiler)
            digerleri = [c for c in birlesik.columns if c not in mevcut_oncelikli and "UNNAMED" not in str(c).upper()]
            birlesik = birlesik[mevcut_oncelikli + digerleri]

            # KONSOL ÇIKTISI: Sadece Hatalı Rasatları Yazdır
            print("\n" + "="*60)
            print(f"HATALI RASATLAR LİSTESİ ({ay}/{yil})")
            print(f"{'TARİH':<15} {'SAAT':<10} {'HATA KODU'}")
            print("-" * 60)
            if "DURUM" in birlesik.columns:
                durum_ser = birlesik["DURUM"].fillna("").astype(str).str.strip()
                hatali_kayitlar = birlesik[~durum_ser.isin(["Hata Yok", "Ara Rasat"])]
                hata_kodu_ser = birlesik["HATA KODU"].fillna("").astype(str).str.strip() if "HATA KODU" in birlesik.columns else pd.Series([""] * len(birlesik), index=birlesik.index)
                aciklama_ser = birlesik["AÇIKLAMA"].fillna("").astype(str).str.strip() if "AÇIKLAMA" in birlesik.columns else pd.Series([""] * len(birlesik), index=birlesik.index)
                ekstra = birlesik[(durum_ser == "") & ((hata_kodu_ser != "") | (aciklama_ser != ""))]
                if not ekstra.empty:
                    hatali_kayitlar = pd.concat([hatali_kayitlar, ekstra]).drop_duplicates()
            else:
                hata_kodu_ser = birlesik["HATA KODU"].fillna("").astype(str).str.strip() if "HATA KODU" in birlesik.columns else pd.Series([""] * len(birlesik), index=birlesik.index)
                aciklama_ser = birlesik["AÇIKLAMA"].fillna("").astype(str).str.strip() if "AÇIKLAMA" in birlesik.columns else pd.Series([""] * len(birlesik), index=birlesik.index)
                hatali_kayitlar = birlesik[(hata_kodu_ser != "") | (aciklama_ser != "")]
            if not hatali_kayitlar.empty:
                for _, row in hatali_kayitlar.iterrows():
                    kod = str(row.get('HATA KODU', ''))
                    if not kod and row.get('DURUM') == 'Veri Yok': kod = "Veri Yok"
                    print(f"{str(row.get('Tarih', '')): <15} {str(row.get('Saat (GMT)', '')): <10} {kod}")
            else:
                print("Hata bulunamadı.")
            print("="*60 + "\n")

            # 3. Rapor Kaydetme
            cikti_yolu = dm3.raporu_excel_olarak_kaydet(birlesik, yil, ay, okuma_raporu)
            
            messagebox.showinfo("Başarılı", f"İşlem Tamamlandı!\nDosya: {cikti_yolu}")
            try: os.startfile(cikti_yolu)
            except: pass
        except Exception as e:
            messagebox.showerror("Hata", f"Bir hata oluştu:\n{e}")
        finally:
            btn_run.config(state=tk.NORMAL, text="RAPOR OLUŞTUR")

    threading.Thread(target=islem_yurut).start()

root = tk.Tk()
root.title("Meteoroloji Denetim")
root.geometry("300x150")
btn_run = tk.Button(root, text="RAPOR OLUŞTUR", command=aylik_rapor_olustur, font=("Arial", 12, "bold"), bg="green", fg="white")
btn_run.pack(expand=True, fill="both", padx=20, pady=20)
root.mainloop()