import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import kurallar

def aylik_rapor_olustur():
    # 1. DOSYA SEÇİMLERİ
    messagebox.showinfo("Adım 1", "Lütfen SİNOPTİK (SinTum.xls) dosyasını seçin.")
    sin_yolu = filedialog.askopenfilename(filetypes=[("Excel", "*.xls *.xlsx *.xlsm")])
    if not sin_yolu: return

    messagebox.showinfo("Adım 2", "Lütfen METAR (MetarTum.xls) dosyasını seçin.")
    metar_yolu = filedialog.askopenfilename(filetypes=[("Excel", "*.xls *.xlsx *.xlsm")])
    if not metar_yolu: return

    try:
        # 2. TÜM SAYFALARI (SHEET2 - SHEET62) DÖNGÜYLE OKUMA
        # .xls dosyalarını da desteklemek için engine parametresini kaldırıyoruz (Pandas otomatik algılar)
        sin_excel = pd.ExcelFile(sin_yolu)
        metar_excel = pd.ExcelFile(metar_yolu)

        sin_gunler = []
        metar_gunler = []
        
        # Dosyadaki gerçek sayfa isimlerini kullanarak döngü kuruyoruz
        for sayfa_adi in sin_excel.sheet_names:
            # Sinoptik oku (Header 4. satırda)
            try:
                s = pd.read_excel(sin_excel, sheet_name=sayfa_adi, header=3)
                if s.empty: continue
                s['Sayfa'] = sayfa_adi
                sin_gunler.append(s)
            except: pass

            # Metar oku (Header 5. satırda)
            if sayfa_adi in metar_excel.sheet_names:
                try:
                    m = pd.read_excel(metar_excel, sheet_name=sayfa_adi, header=4)
                    m['Sayfa'] = sayfa_adi
                    metar_gunler.append(m)
                except: pass

        # Verileri Birleştir
        if not sin_gunler:
            raise ValueError("Sinoptik dosyasından veri okunamadı! Sayfa isimleri veya format uyumsuz olabilir.")
            
       
        df_sin_all = df_sin_all.loc[:, [c for c in df_sin_all.columns if not str(c).startswith('Unnamed')]]
        df_metar_all = df_metar_all.loc[:, [c for c in df_metar_all.columns if not str(c).startswith('Unnamed')]]

        # Gereksiz boş sütunları temizle
        df_sin_all = df_sin_all.loc[:, ~df_sin_all.columns.str.contains('^Unnamed')]
        df_metar_all = df_metar_all.loc[:, ~df_metar_all.columns.str.contains('^Unnamed')]

        # Sütun isimlerini küçük harfe çevir (Standartlaştırma)
        df_sin_all.columns = df_sin_all.columns.str.strip().str.lower()
        df_metar_all.columns = df_metar_all.columns.str.strip().str.lower()

        # GMT Standardizasyonu (Eşleşme problemini çözmek için)
        # Veri tiplerini sayıya çeviriyoruz ki "03" ile 3 eşleşebilsin
        if 'gmt' in df_sin_all.columns: df_sin_all['gmt'] = pd.to_numeric(df_sin_all['gmt'], errors='coerce')
        if 'gmt' in df_metar_all.columns: df_metar_all['gmt'] = pd.to_numeric(df_metar_all['gmt'], errors='coerce')

        # Diğer kritik sütunları da sayısal veriye çevir (Mantıksal kıyaslama için şart)
        numeric_cols = ['n', 'dd', 'ff', 'vv', 't', 'td', 'p', 'p0', 'a', 'ppp', 'ir', 'ix', 'rrr', 'tr', 'ww', 'w1', 'w2', 'nh', 'cl', 'cm', 'ch', 'h']
        for col in numeric_cols:
            if col in df_sin_all.columns: df_sin_all[col] = pd.to_numeric(df_sin_all[col], errors='coerce')

        # 3. KURALLARI YÜKLE (Sayfa4)
        hata_dict = kurallar.HATA_SOZLUGU

        # 4. ANALİZ VE ÇAPRAZ KONTROL (GMT BAZLI)
        # Not: GMT ve Sayfa (Gün) üzerinden eşleştirme yapılır
        # Tüm Sinoptik verilerini (eşleşmese bile) korumak için LEFT JOIN kullanıyoruz
        
        # Metar verisi boşsa veya sütunlar eksikse merge hatasını önle
        if 'sayfa' not in df_metar_all.columns or 'gmt' not in df_metar_all.columns:
             df_metar_all = pd.DataFrame(columns=['sayfa', 'gmt'])

        # Sütunlar küçük harfe çevrildiği için anahtarlar: 'sayfa', 'gmt'
        birlesik = pd.merge(df_sin_all, df_metar_all, on=['sayfa', 'gmt'], how='left', suffixes=('_sin', '_metar'))

        if birlesik.empty:
            messagebox.showwarning("Uyarı", "Veriler eşleştirilemedi veya boş! Lütfen dosya formatlarını ve GMT sütunlarını kontrol edin.")
            return

        def hata_ara(satir):
            try:
                bulgular = []
                kodlar = []
                aciklamalar = []
                
                # 1. MEVCUT HATA KODLARINI KONTROL ET
                # Sinoptik dosyasından gelen 'hata no' sütunu varsa değerlendir
                hata_no = satir.get('hata no')
                if pd.notna(hata_no):
                    aciklama = hata_dict.get(hata_no, "Tanımsız Hata Kodu")
                    bulgular.append(f"[Kod {hata_no}]: {aciklama}")
                    kodlar.append(str(hata_no))
                    aciklamalar.append(aciklama)

                # 2. MANUEL KONTROLLER (TÜM GRUPLAR)
                
                # --- A. YAĞIŞ GRUBU (iR, RRR) ---
                ir = satir.get('ir')
                ix = satir.get('ix')
                rrr = satir.get('rrr')
                ww = satir.get('ww')

                if ir == 1 and pd.isna(rrr):
                    msg = hata_dict.get('h4', 'Yağış Grubu Eksik')
                    bulgular.append(f"h4: {msg}")
                    kodlar.append('h4')
                    aciklamalar.append(msg)
                elif ir == 3 and pd.notna(rrr) and rrr != 0:
                    msg = hata_dict.get('h5', 'Yağış Yok (iR=3) ama RRR girilmiş')
                    bulgular.append(f"h5: {msg}")
                    kodlar.append('h5')
                    aciklamalar.append(msg)
                
                # iX ve ww Kontrolü
                if ix == 1 and pd.isna(ww):
                    msg = hata_dict.get('h11', 'iX=1 ama ww yok')
                    bulgular.append(f"h11: {msg}")
                    kodlar.append('h11')
                    aciklamalar.append(msg)
                elif ix == 2 and pd.notna(ww):
                    msg = hata_dict.get('h12', 'iX=2 ama ww var')
                    bulgular.append(f"h12: {msg}")
                    kodlar.append('h12')
                    aciklamalar.append(msg)

                # --- B. RÜZGAR GRUBU (dd, ff) ---
                dd = satir.get('dd')
                ff_sin = satir.get('ff_sin', satir.get('ff'))
                if dd == 0 and pd.notna(ff_sin) and ff_sin > 0:
                    msg = hata_dict.get('h38', 'Yön 00 iken Hız > 0')
                    bulgular.append(f"h38: {msg}")
                    kodlar.append('h38')
                    aciklamalar.append(msg)
                if pd.notna(dd) and dd > 0 and pd.notna(ff_sin) and ff_sin == 0:
                    msg = hata_dict.get('h43', 'Hız 00 iken Yön verilmiş')
                    bulgular.append(f"h43: {msg}")
                    kodlar.append('h43')
                    aciklamalar.append(msg)

                # --- C. GÖRÜŞ ve HADİSE (VV, ww) ---
                vv = satir.get('vv')
                # VV < 90 (yaklaşık 10km altı) iken ww olmalı
                if pd.notna(vv) and vv < 90 and (pd.isna(ww) or ww == 0):
                     msg = hata_dict.get('h79', 'Görüş düşük ama hadise yok')
                     bulgular.append(f"h79: {msg}")
                     kodlar.append('h79')
                     aciklamalar.append(msg)

                # --- D. BULUTLAR (N, Nh, CL, CM, CH) ---
                n = satir.get('n')
                nh = satir.get('nh')
                cl = satir.get('cl')
                cm = satir.get('cm')
                ch = satir.get('ch')

                if n == 0 and ((pd.notna(cl) and cl > 0) or (pd.notna(cm) and cm > 0) or (pd.notna(ch) and ch > 0)):
                    msg = hata_dict.get('h26', 'N=0 iken bulut var')
                    bulgular.append(f"h26: {msg}")
                    kodlar.append('h26')
                    aciklamalar.append(msg)
                
                if pd.notna(nh) and pd.notna(n) and nh > n:
                    msg = hata_dict.get('h120', 'Nh > N olamaz')
                    bulgular.append(f"h120: {msg}")
                    kodlar.append('h120')
                    aciklamalar.append(msg)
                
                if pd.notna(n) and n == 9 and pd.notna(cl) and cl == 0: # N=9 (görünmüyor) ise CL=0 olamaz
                    msg = hata_dict.get('h33', 'N=9 iken CL=/ olmalı')
                    bulgular.append(f"h33: {msg}")
                    kodlar.append('h33')
                    aciklamalar.append(msg)

                # --- E. SICAKLIK (T, Td) ---
                t = satir.get('t')
                td = satir.get('td')
                if pd.notna(t) and pd.notna(td) and td > t:
                    msg = hata_dict.get('h52', 'İşba (Td) > Sıcaklık (T)')
                    bulgular.append(f"h52: {msg}")
                    kodlar.append('h52')
                    aciklamalar.append(msg)

                # --- F. BASINÇ VE TANDANS (a, ppp) ---
                a = satir.get('a')
                ppp = satir.get('ppp')
                if a == 4 and pd.notna(ppp) and ppp != 0:
                    msg = hata_dict.get('h63', 'a=4 (sabit) iken ppp=0 olmalı')
                    bulgular.append(f"h63: {msg}")
                    kodlar.append('h63')
                    aciklamalar.append(msg)
                if a == 9:
                    msg = hata_dict.get('h61', 'Tandans a=9 olamaz')
                    bulgular.append(f"h61: {msg}")
                    kodlar.append('h61')
                    aciklamalar.append(msg)

                # --- G. GEÇMİŞ HAVA (W1, W2) ---
                w1 = satir.get('w1')
                w2 = satir.get('w2')
                if pd.notna(w1) and pd.notna(w2) and w2 > w1:
                    msg = hata_dict.get('h116', 'W2 > W1 olamaz (W1 en büyük kod olmalı)')
                    bulgular.append(f"h116: {msg}")
                    kodlar.append('h116')
                    aciklamalar.append(msg)

                # --- F. METAR KARŞILAŞTIRMASI ---
                ff_metar = satir.get('hız_metar', satir.get('hız'))
                if pd.notna(ff_sin) and pd.notna(ff_metar) and abs(ff_sin - ff_metar) > 5:
                    msg = "METAR ve SİNOPTİK Rüzgar Hızı Uyumsuz!"
                    bulgular.append(msg)
                    aciklamalar.append(msg)

                sonuc_mesaj = " | ".join(bulgular) if bulgular else "Hata Yok"
                sonuc_kodlar = ", ".join(kodlar)
                sonuc_aciklamalar = " | ".join(aciklamalar)
                return [sonuc_mesaj, sonuc_kodlar, sonuc_aciklamalar]
            except Exception as e:
                return [f"Satır İşlenirken Hata: {str(e)}", "İŞLEM HATASI", ""]

        # apply yerine liste üreteci kullanarak işlemi daha güvenli hale getiriyoruz
        # Bu yöntem "1-d array" veya boyut hatalarını kesin olarak çözer
        kayitlar = birlesik.to_dict('records')
        sonuclar = [hata_ara(satir) for satir in kayitlar]
        
        uygulama_sonucu = pd.DataFrame(sonuclar, index=birlesik.index, columns=['ANALİZ_SONUCU', 'HATA_KODLARI', 'HATA_ACIKLAMALARI'])
        birlesik = pd.concat([birlesik, uygulama_sonucu], axis=1)

        # Çıktıyı Düzenle (Sıralama ve Sütun Düzeni)
        if 'sayfa' in birlesik.columns and 'gmt' in birlesik.columns:
            birlesik = birlesik.sort_values(by=['sayfa', 'gmt'])
            
        # Önemli sütunları başa al
        oncelikli_sutunlar = ['sayfa', 'gmt', 'istasyon no', 'HATA_KODLARI', 'HATA_ACIKLAMALARI', 'ANALİZ_SONUCU']
        diger_sutunlar = [c for c in birlesik.columns if c not in oncelikli_sutunlar]
        birlesik = birlesik[[c for c in oncelikli_sutunlar if c in birlesik.columns] + diger_sutunlar]

        # 5. KAYDET VE AÇ
        masaustu = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
        final_yol = os.path.join(masaustu, "ARALIK_2025_TAM_DENETIM.xlsx")
        
        # Dosya açık mı kontrol et (PermissionError önlemi)
        if os.path.exists(final_yol):
            try:
                with open(final_yol, 'a'): pass
            except PermissionError:
                raise PermissionError(f"Excel dosyası şu an açık: {final_yol}\nLütfen dosyayı kapatıp tekrar deneyin.")
        
        # Özet Tablo (Hangi istasyonda kaç hata var?)
        # İstasyon sütununu bulmaya çalış (yoksa 'Sayfa' bazlı grupla)
        istasyon_col = next((c for c in birlesik.columns if 'ist' in c), 'sayfa')
        hata_ozeti = birlesik[birlesik['ANALİZ_SONUCU'] != "Hata Yok"].groupby(istasyon_col).size().reset_index(name='Hata Sayısı')

        # Genel İstatistikler (Raporun başına eklenecek)
        toplam_gun = birlesik['sayfa'].nunique()
        hata_df = birlesik[birlesik['ANALİZ_SONUCU'] != "Hata Yok"]
        toplam_hata = len(hata_df)

        if not hata_df.empty:
            en_cok_hata_gun = hata_df['sayfa'].value_counts().idxmax()
            en_cok_hata_sayisi = hata_df['sayfa'].value_counts().max()
            en_cok_hata_str = f"{en_cok_hata_gun} ({en_cok_hata_sayisi} Hata)"
        else:
            en_cok_hata_str = "Hata Yok"

        genel_bilgi = pd.DataFrame([{'Taranan Gün Sayısı': toplam_gun, 'Toplam Bulunan Hata': toplam_hata, 'En Çok Hata Yapılan Gün': en_cok_hata_str}])

        # Excel'e Çoklu Sayfa Olarak Kaydet
        with pd.ExcelWriter(final_yol, engine='openpyxl') as writer:
            # 1. Detaylı Rapor
            # Tüm sütunları rapora dahil ediyoruz
            birlesik.to_excel(writer, sheet_name='Detaylı_Rapor', index=False)
            
            # 2. Özet Tablo
            genel_bilgi.to_excel(writer, sheet_name='Hata_Ozeti', index=False, startrow=0)
            hata_ozeti.to_excel(writer, sheet_name='Hata_Ozeti', index=False, startrow=4)
        
        messagebox.showinfo("Başarılı", f"31 Günlük veri tarandı!\nDosya: ARALIK_2025_TAM_DENETIM.xlsx")
        os.startfile(final_yol)

    except Exception as e:
        messagebox.showerror("Hata", f"İşlem sırasında hata oluştu: {str(e)}")

# Pencereyi Başlat
root = tk.Tk()
root.title("31 Günlük Meteoroloji Denetçisi")
root.geometry("350x150")
tk.Button(root, text="Tüm Ayı Birleştir ve Denetle", command=aylik_rapor_olustur, bg="darkgreen", fg="white", pady=20).pack(expand=True)
root.mainloop()