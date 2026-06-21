import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import re
import os

def excel_hucresi_coz(hucre_adi):
    """
    'C5', 'A1' gibi Excel hücre isimlerini Pandas'ın (satır_indeksi, sütun_indeksi) 
    formatına çevirir (Sıfır tabanlı).
    """
    eslesme = re.match(r"([A-Za-z]+)(\d+)", hucre_adi.strip())
    if not eslesme: 
        return None, None
        
    harf, sayi = eslesme.groups()
    
    # Sütun harfini indekse çevir (A=0, B=1, Z=25, vb.)
    sutun_idx = 0
    for karakter in harf.upper():
        sutun_idx = sutun_idx * 26 + (ord(karakter) - ord('A') + 1)
    sutun_idx -= 1
    
    # Satır numarasını indekse çevir (Excel'de 1. satır = 0. indeks)
    satir_idx = int(sayi) - 1
    
    return satir_idx, sutun_idx

def hucreleri_eslestir():
    root = tk.Tk()
    root.withdraw()

    # Dosya seçimi
    dosya_yolu = filedialog.askopenfilename(
        title="Verilerin Çekileceği Excel Dosyasını Seçin",
        filetypes=[("Excel Dosyaları", "*.xls *.xlsx")]
    )

    if not dosya_yolu:
        return

    # ================= AYARLAR =================
    # İki katmanlı (Ana Başlık ve Alt Başlık) olacak şekilde verilerin çekileceği hücreler.
    # LÜTFEN A1, A2 gibi geçici değerleri KENDİ EXCEL'İNİZDEKİ DOĞRU HÜCRE İSİMLERİYLE DEĞİŞTİRİN.
    # Çekilmesini istemediğiniz veya tablonuzda olmayan veriler için değeri boş ("") bırakabilirsiniz.
    hedef_hucreler = {
        ("TİP", "Tipi"): "A1",
        ("TİP", "GMT"): "A2",
        ("RÜZGAR", "Yön"): "A3",
        ("RÜZGAR", "Hız"): "A4",
        ("RÜZGAR", "Hamle"): "A5",
        ("RÜZGAR", "Salınım"): "A6",
        ("RÜYET", "Hakim"): "A7",
        ("RÜYET", "Min."): "A8",
        ("RÜYET", "Yön"): "A9",
        ("RÜYET", "Dikine"): "A10",
        ("HALİHAZIR HAVA", "1. Grup"): "A11",
        ("HALİHAZIR HAVA", "2. Grup"): "A12",
        ("HALİHAZIR HAVA", "3. Grup"): "A13",
        ("BULUT", "T. Kp."): "A14",
        ("1. BULUT", "Kap."): "A15",
        ("1. BULUT", "Cins"): "A16",
        ("1. BULUT", "Yük."): "A17",
        ("2. BULUT", "Kap."): "A18",
        ("2. BULUT", "Cins"): "A19",
        ("2. BULUT", "Yük."): "A20",
        ("3. BULUT", "Kap."): "A21",
        ("3. BULUT", "Cins"): "A22",
        ("3. BULUT", "Yük."): "A23",
        ("4. BULUT", "Kap."): "A24",
        ("4. BULUT", "Cins"): "A25",
        ("4. BULUT", "Yük."): "A26",
        ("SICAKLIK", "Kuru"): "A27",
        ("SICAKLIK", "Islak"): "A28",
        ("SICAKLIK", "İşba"): "A29",
        ("NM", "%"): "A30",
        ("BASINÇ", "QFE"): "A31",
        ("BASINÇ", "QNH"): "A32",
        ("BASINÇ", "inch"): "A33",
        ("WS", ""): "A34",
        ("P DRM", ""): "A35",
        ("Rstçı", ""): "A36",
        ("Maksimum Rüzgar", ""): "A37",
        ("Maksimum Rüzgar", "P. No"): "A38"
    }
    # ===========================================

    try:
        xls = pd.ExcelFile(dosya_yolu)
        eslesme_sonuclari = []

        for sayfa in xls.sheet_names:
            sayfa_str = str(sayfa).lower()
            is_valid = False
            gun_no = ""
            
            # Eski format: Sheet2, Sheet4...
            if "sheet" in sayfa_str or "sayfa" in sayfa_str:
                rakamlar = re.findall(r'\d+', sayfa_str)
                if rakamlar:
                    sayfa_no = int(rakamlar[0])
                    if sayfa_no % 2 == 0:
                        is_valid = True
                        gun_no = str(sayfa_no // 2)
            # Yeni format: A-01.12.2025 (Açık Veri)
            elif sayfa_str.startswith("a-"):
                is_valid = True
                match = re.search(r'\b(\d{2})\.\d{2}\.\d{4}\b', sayfa_str)
                if match:
                    gun_no = str(int(match.group(1)))
                else:
                    gun_no = "?"
            
            if is_valid:
                df = pd.read_excel(xls, sheet_name=sayfa, header=None)
                sayfa_verisi = {
                    ("SİSTEM BİLGİSİ", "Sayfa Adı"): sayfa,
                    ("SİSTEM BİLGİSİ", "Gün"): gun_no
                }
                
                for (ana_baslik, alt_baslik), hucre_adi in hedef_hucreler.items():
                    satir, sutun = excel_hucresi_coz(hucre_adi)
                    if satir is None or sutun is None:
                        sayfa_verisi[(ana_baslik, alt_baslik)] = ""
                    else:
                        try:
                            sayfa_verisi[(ana_baslik, alt_baslik)] = df.iloc[satir, sutun]
                        except (IndexError, TypeError):
                            sayfa_verisi[(ana_baslik, alt_baslik)] = "Bulunamadı"
                        
                eslesme_sonuclari.append(sayfa_verisi)

        if eslesme_sonuclari:
            sonuc_df = pd.DataFrame(eslesme_sonuclari)
            # Excel çıktısında 2 katmanlı başlık oluşturabilmek için format dönüşümü
            sonuc_df.columns = pd.MultiIndex.from_tuples(sonuc_df.columns)
            
            # Tabloyu konsolda göster
            print("\n" + "=" * 100)
            print("ÇİFT SAYILI SAYFALARDAN ÇEKİLEN VERİLER TABLOSU")
            print("-" * 100)
            print(sonuc_df.to_string())
            print("=" * 100 + "\n")

            masaustu = os.path.join(os.environ["USERPROFILE"], "Desktop")
            cikti_yolu = os.path.join(masaustu, "Cift_Sayfa_Hucre_Esleme_Sonucu.xlsx")
            
            sonuc_df.to_excel(cikti_yolu, index=False)
            messagebox.showinfo("Başarılı", f"Eşleştirme tamamlandı!\nDosya masaüstüne kaydedildi:\n{cikti_yolu}")
            os.startfile(cikti_yolu)
        else:
            messagebox.showwarning("Uyarı", "Dosyada çift numaralı sayfa (Örn: Sheet2) bulunamadı.")

    except Exception as e:
        messagebox.showerror("Hata", f"İşlem sırasında bir hata oluştu:\n{str(e)}")

if __name__ == "__main__":
    hucreleri_eslestir()