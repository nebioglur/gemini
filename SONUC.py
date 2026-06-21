import pandas as pd
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import calendar

def rasat_duzenleyici():
    root = tk.Tk()
    root.withdraw()

    # 1. Dosya Seçimleri
    messagebox.showinfo("Adım 1", "Lütfen SİNOPTİK dosyasını seçin")
    sin_yolu = filedialog.askopenfilename(filetypes=[("Excel", "*.xls *.xlsx")])
    
    messagebox.showinfo("Adım 2", "Lütfen METAR dosyasını seçin")
    metar_yolu = filedialog.askopenfilename(filetypes=[("Excel", "*.xls *.xlsx")])

    if not sin_yolu or not metar_yolu:
        return

    def veri_oku_ve_temizle(yolu, etiket):
        # Tüm sayfaları oku
        xls = pd.ExcelFile(yolu)
        df_list = []
        for sheet in xls.sheet_names:
            # Başlığı otomatik bulmak için header=None ile oku
            temp_df = pd.read_excel(yolu, sheet_name=sheet)
            
            # Sütun isimlerini standartlaştır (Küçük harf ve boşluksuz)
            temp_df.columns = [str(c).strip().lower() for c in temp_df.columns]
            
            # Tarih ve Saat (GMT) sütunlarını bulmaya çalış
            # Sizin dosyalarınızda 'gmt' ve 'sayfa' (tarih) sütunları kritik
            df_list.append(temp_df)
        
        full_df = pd.concat(df_list, ignore_index=True)
        return full_df

    try:
        df_sin = veri_oku_ve_temizle(sin_yolu, "SINOPTIK")
        df_metar = veri_oku_ve_temizle(metar_yolu, "METAR")

        # Zaman Damgası Oluşturma (Sıralama için en güvenli yol)
        # 'sayfa' sütununu tarih, 'gmt' sütununu saat olarak kullanıyoruz
        for df in [df_sin, df_metar]:
            if 'sayfa' in df.columns and 'gmt' in df.columns:
                df['zaman_objesi'] = pd.to_datetime(
                    df['sayfa'].astype(str) + ' ' + df['gmt'].astype(str).str.split('.').str[0] + ':00',
                    errors='coerce'
                )

        # 2. Master Tablo Oluştur (Tüm ayı kapsayan boş iskelet)
        # Örnek olarak Ocak 2026 üzerinden
        tarihler = pd.date_range(start="2026-01-01", end="2026-01-31 21:00", freq='3H')
        df_master = pd.DataFrame({'zaman_objesi': tarihler})

        # 3. Verileri Yan Yana Birleştir (Merge)
        # Verileri 'melt' yapmıyoruz, sütun olarak yan yana ekliyoruz
        final = pd.merge(df_master, df_sin, on='zaman_objesi', how='left')
        final = pd.merge(final, df_metar, on='zaman_objesi', how='left', suffixes=('_SIN', '_METAR'))

        # 4. Temizlik ve Sıralama
        final['Tarih'] = final['zaman_objesi'].dt.strftime('%d.%m.%Y')
        final['Saat'] = final['zaman_objesi'].dt.hour
        final = final.sort_values(by='zaman_objesi')

        # Gereksiz sütunları at
        cols_to_keep = ['Tarih', 'Saat'] + [c for c in final.columns if '_SIN' in c or '_METAR' in c or 'rasatlar' in c.lower()]
        final = final[cols_to_keep]

        # Masaüstüne Kaydet
        masaustu = os.path.join(os.environ["USERPROFILE"], "Desktop")
        cikti_yolu = os.path.join(masaustu, "RASAT_SIRALI_LISTE.xlsx")
        final.to_excel(cikti_yolu, index=False)
        
        messagebox.showinfo("Başarılı", f"Dosya Masaüstüne Kaydedildi:\n{cikti_yolu}")
        os.startfile(cikti_yolu)

    except Exception as e:
        messagebox.showerror("Hata", f"İşlem sırasında hata oluştu: {e}")

if __name__ == "__main__":
    rasat_duzenleyici()