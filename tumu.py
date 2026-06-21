import time
import datetime
import calendar
import threading
import traceback
import tkinter as tk
import re
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont
import pandas as pd
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')

class KardelenUltraScraper:
    def __init__(self, station_id="17244"):
        self.station_id = station_id
        self.url = f"http://kardelen.mgm.gov.tr/bultenler/Metar/MetarDefter.aspx?ist={station_id}"
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def fetch(self, start_date, end_date, progress_callback=None):
        results = []
        total_days = (end_date - start_date).days + 1
        
        wait = WebDriverWait(self.driver, 15)
        try:
            for i in range(total_days):
                current_date = start_date + datetime.timedelta(days=i)
                
                if progress_callback:
                    progress_callback(i + 1, total_days, current_date.strftime("%d.%m.%Y"))
                    
                try:
                    self.driver.get(self.url)
                    wait.until(EC.presence_of_element_located((By.ID, 'cBody_ddBasGun')))
                    
                    js_script = f"""
                        document.getElementById('cBody_ddBasGun').value = '{current_date.day}';
                        document.getElementById('cBody_ddBasAy').value = '{current_date.month}';
                        document.getElementById('cBody_ddBasYil').value = '{current_date.year}';
                        
                        document.getElementById('cBody_ddBitisGun').value = '{current_date.day}';
                        document.getElementById('cBody_ddbitisAy').value = '{current_date.month}';
                        document.getElementById('cBody_ddbitisYil').value = '{current_date.year}';
                        
                        var rd_tumu = document.getElementById('cBody_rdList_0');
                        if(rd_tumu) rd_tumu.click();
                        
                        var ddtur = document.getElementById('cBody_ddTur');
                        if(ddtur) ddtur.value = '500';
                        
                        var yukle_btn = document.getElementById('cBody_btnYukle');
                        if(yukle_btn) yukle_btn.click();
                    """
                    self.driver.execute_script(js_script)
                    
                    time.sleep(1.5)
                    wait.until(EC.presence_of_element_located((By.XPATH, "//table//tr[position()>4]")))
                    
                    # Sayfa kaynağını tek seferde al ve BeautifulSoup ile çok daha hızlı parçala
                    soup = BeautifulSoup(self.driver.page_source, "html.parser")
                    rows = soup.select("table tr")

                    gunluk_kayit = 0

                    for row in rows[4:]:
                        cols = row.find_all(["td", "th"], recursive=False)
                        texts = [c.get_text(separator=" ", strip=True) for c in cols]

                        if len(texts) < 4: continue

                        row_lower = " ".join(texts).lower()
                        if any(x in row_lower for x in ["dokuman", "map", "tarih", "saat", "kullanıcı", "tip", "rasat"]):
                            continue

                        # Bülten her zaman tablonun son sütunundadır. Spesifik kelime aramak ("LT", "METAR" vb.)
                        # standart dışı girilmiş bazı rasatların atlanmasına ve verinin eksik gelmesine yol açar.
                        bulten = " ".join(texts[-1].split())
                        if len(bulten) < 10:
                            bulten = max(texts, key=len) # Eğer tabloda kayma varsa en uzun metni yedek olarak al
                        if len(bulten) < 10: continue

                        # Tablo sütunlarını kaymalara karşı esnek eşleştir
                        if len(texts) >= 6:
                            turu, kull, gond, kayit, gmt = texts[0], texts[1], texts[2], texts[3], texts[4]
                        elif len(texts) == 5:
                            turu, kull, gond, kayit, gmt = texts[0], texts[1], "-", texts[2], texts[3]
                        else:
                            turu, kull, gond, kayit, gmt = texts[0], texts[3], "-", texts[2], texts[1]

                        if turu.upper() == 'M': turu = "METAR"
                        elif turu.upper() == 'S': turu = "SPECI"
                        elif turu.upper() == 'T': turu = "TAF"
                        elif turu.upper() == 'V': turu = "SİNOPTİK"

                        gmt_clean = gmt.replace(":", "").replace("Z", "").strip()
                        gmt_format = f"{gmt_clean[:2]}:{gmt_clean[2:4]}Z" if len(gmt_clean) >= 4 else f"{gmt}Z"
                        rasat = f"{current_date.strftime('%d.%m.%Y')} {gmt_format}"

                        results.append([turu, kull, gond, kayit, rasat, bulten])
                        gunluk_kayit += 1

                    if len(rows) > 4 and gunluk_kayit == 0:
                        print(f"[{current_date.strftime('%d.%m.%Y')}] Eksik Veri Nedeni: Tabloda {len(rows) - 4} satır var ancak geçerli bir rasat bülteni ayıklanamadı.")
                    elif gunluk_kayit > 0:
                        logging.info(f"[{current_date.strftime('%d.%m.%Y')}] Tablodan {gunluk_kayit} adet geçerli rasat bülteni eksiksiz ayıklandı.")

                except Exception as e:
                    logging.error(f"[{current_date.strftime('%d.%m.%Y')}] Veri çekme hatası:\n{traceback.format_exc()}")
                    continue
        finally:
            self.driver.quit()

        return results

# ================= GUI ARAYÜZÜ =================
def run_gui():

    def update_status(current, total, date_str):
        # GUI güncellemelerini ana iş parçacığında (thread-safe) yapmak için root.after kullanılır
        def _update():
            progress["value"] = (current / total) * 100
            lbl_status.config(text=f"Taranıyor... {date_str} ({current}/{total})")
        root.after(0, _update)

    def _fetch_worker(start_date, end_date):
        btn.config(state="disabled", text="Yükleniyor...")
        btn_gecmis.config(state="disabled", text="Yükleniyor...")
        try:
            total_days = (end_date - start_date).days + 1
            # RAM/CPU'nun boğulup "Timeout" kaynaklı eksik veri yaratmasını önlemek için max 6 pencere
            max_workers = min(6, total_days) 
            if max_workers < 1: max_workers = 1
            
            chunk_size = (total_days // max_workers) or 1
            chunks = []
            for i in range(max_workers):
                c_start = start_date + datetime.timedelta(days=i * chunk_size)
                c_end = end_date if i == max_workers - 1 else c_start + datetime.timedelta(days=chunk_size - 1)
                if c_start <= end_date:
                    chunks.append((c_start, c_end))
                    
            result = []
            completed_days = [0]
            
            def safe_progress(c, t, d_str):
                completed_days[0] += 1
                current = completed_days[0]
                def _update():
                    progress["value"] = (current / total_days) * 100
                    lbl_status.config(text=f"Taranıyor... {d_str} ({current}/{total_days})")
                root.after(0, _update)
                
            def fetch_chunk(c_start, c_end):
                # Eksik veri çakışmasını engellemek için HER thread kendi Chrome penceresini açar
                local_scraper = KardelenUltraScraper(ist.get())
                return local_scraper.fetch(c_start, c_end, progress_callback=safe_progress)
                
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(fetch_chunk, cs, ce) for cs, ce in chunks]
                for future in as_completed(futures):
                    res_chunk = future.result()
                    if res_chunk:
                        result.extend(res_chunk)
                        
            # Parçalar farklı sürelerde biteceği için tabloya karışık girmesini engelle, tarihe göre sırala
            def sort_key(x):
                try:
                    # Rasat Tarihi formatı: "18.04.2026 13:50Z"
                    date_part = x[4][:10]
                    time_part = x[4][11:].replace("Z", "").strip()
                    if ":" in time_part:
                        return datetime.datetime.strptime(f"{date_part} {time_part}", "%d.%m.%Y %H:%M")
                    
                    # Saat kısmı eksikse/bozuksa (örn: "-") Kayıt Tarihine (x[3]) başvur
                    return datetime.datetime.strptime(x[3].strip(), "%d.%m.%Y %H:%M")
                except Exception:
                    try: return datetime.datetime.strptime(x[4][:10], "%d.%m.%Y")
                    except Exception: return datetime.datetime.min
                    
            result.sort(key=sort_key, reverse=False)

            tree.delete(*tree.get_children())

            for r in result:
                tree.insert("", tk.END, values=r)
                
            # Sütunları tabloya gelen veri boyutuna göre (DOĞRU FONT İLE) otomatik genişlet
            font = tkfont.Font(family="Arial", size=10)
            header_font = tkfont.Font(family="Arial", size=10, weight="bold")
            
            for i, col in enumerate(tree["columns"]):
                max_width = header_font.measure(col) + 30  # Başlık genişliği + boşluk
                
                # Hız ve performans için Treeview yerine bellekteki result listesini okuyoruz
                for r in result:
                    width = font.measure(str(r[i])) + 30
                    if width > max_width:
                        max_width = width
                        
                if max_width > 800: max_width = 800  # Ekranı taşırmamak için maksimum sınır
                is_stretch = True if col == "Bülten" else False
                min_w = 100 if is_stretch else max_width # Pencere küçülünce sabit sütunların ezilmesini önler
                tree.column(col, width=max_width, minwidth=min_w, stretch=is_stretch)

            if not result:
                messagebox.showinfo("Bilgi", "İlgili tarihlerde veri bulunamadı.")
            else:
                logging.info(f"[GENEL SONUÇ] Toplam {len(result)} kayıt başarıyla arayüze aktarıldı.")
                messagebox.showinfo("Başarılı", f"İşlem tamamlandı!\nToplam {len(result)} kayıt ultra hızla yüklendi.")

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Hata", str(e))

        finally:
            btn.config(state="normal", text="Yükle")
            btn_gecmis.config(state="normal", text="Göster")
            progress["value"] = 0
            lbl_status.config(text="Durum: İşlem Tamamlandı veya Durduruldu")

    def start_range_fetch():
        try:
            start_date = datetime.date(int(by.get()), int(bm.get()), int(bd.get()))
            end_date = datetime.date(int(ey.get()), int(em.get()), int(ed.get()))
        except (ValueError, IndexError):
            messagebox.showerror("Hata", "Tarih aralığı hatalı.")
            return
        threading.Thread(target=_fetch_worker, args=(start_date, end_date), daemon=True).start()

    def start_monthly_fetch():
        try:
            secim = cb_ay_gecmis.get().split()
            if len(secim) != 2:
                raise ValueError
            ay_str = secim[0]
            yil_str = secim[1]
            
            aylar = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                     "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
            ay_num = aylar.index(ay_str) + 1
            yil_num = int(yil_str)
            
            _, son_gun = calendar.monthrange(yil_num, ay_num)
            
            start_date = datetime.date(yil_num, ay_num, 1)
            end_date = datetime.date(yil_num, ay_num, son_gun)
        except (ValueError, IndexError):
            messagebox.showerror("Hata", "Geçersiz ay veya yıl.")
            return
        threading.Thread(target=_fetch_worker, args=(start_date, end_date), daemon=True).start()

    def export_excel():
        rows = [tree.item(i)["values"] for i in tree.get_children()]
        if not rows:
            return

        df = pd.DataFrame(rows, columns=["Türü", "Kullanıcı", "Gönd. Z.", "Kayıt Tarihi", "Rasat Tarihi", "Bülten"])
        file = filedialog.asksaveasfilename(defaultextension=".xlsx")

        if file:
            df.to_excel(file, index=False)
            messagebox.showinfo("Başarılı", "Excel başarıyla kaydedildi")

    def export_txt():
        rows = [tree.item(i)["values"] for i in tree.get_children()]
        if not rows:
            return

        file = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Dosyası", "*.txt")])
        if file:
            try:
                with open(file, "w", encoding="utf-8") as f:
                    for values in rows:
                        turu = str(values[0]).strip()
                        kull = str(values[1]).strip()
                        gond = str(values[2]).strip()
                        kayit = str(values[3]).strip()
                        rasat = str(values[4]).strip()
                        bulten = str(values[5]).strip()
                        
                        f.write(f"TÜRÜ: {turu:<8} | KULL: {kull:<8} | KAYIT TAR: {kayit:<16} | RASAT TAR: {rasat:<17} | BÜLTEN: {bulten}\n")
                messagebox.showinfo("Başarılı", "TXT dosyası belirtilen formatta başarıyla kaydedildi.")
            except Exception as e:
                messagebox.showerror("Hata", f"TXT dosyası kaydedilirken hata oluştu:\n{e}")

    root = tk.Tk()
    root.title("Kardelen METAR Ultra Scraper PRO")
    root.geometry("1200x600")

    frame_top = tk.Frame(root, pady=10)
    frame_top.pack(side=tk.TOP, fill=tk.X, padx=10)

    # --- İstasyon ve Excel ---
    frame_ist = tk.Frame(frame_top)
    frame_ist.pack(side=tk.LEFT, padx=10)
    
    tk.Label(frame_ist, text="İstasyon:").pack(anchor="w")
    ist = tk.Entry(frame_ist, width=10)
    ist.insert(0, "17244")
    ist.pack(anchor="w", pady=2)
    
    tk.Button(frame_ist, text="Excel'e Aktar", command=export_excel).pack(anchor="w", pady=5)

    now = datetime.datetime.now()

    # --- Geçmiş Aylar Bölümü ---
    frame_gecmis = tk.LabelFrame(frame_top, text="Aylık Toplu Veri", padx=10, pady=10)
    frame_gecmis.pack(side=tk.LEFT, padx=15, fill=tk.Y)
    
    aylar = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
             "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
    
    dinamik_aylar = []
    for i in range(60):  # Son 5 yıl (60 ay) listelenir. İsterseniz bu sayıyı değiştirebilirsiniz.
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        dinamik_aylar.append(f"{aylar[m-1]} {y}")
    
    cb_ay_gecmis = ttk.Combobox(frame_gecmis, values=dinamik_aylar, width=15, state="readonly")
    if dinamik_aylar:
        cb_ay_gecmis.set(dinamik_aylar[0])
    cb_ay_gecmis.grid(row=0, column=0, padx=2)

    btn_gecmis = tk.Button(frame_gecmis, text="Göster", command=start_monthly_fetch, bg="#007bff", fg="white", font=("Arial", 9, "bold"))
    btn_gecmis.grid(row=0, column=1, padx=15)

    # --- Güncel Veri Bölümü ---
    frame_guncel = tk.LabelFrame(frame_top, text="Tarih Aralığı Seçimi", padx=10, pady=5)
    frame_guncel.pack(side=tk.LEFT, padx=15, fill=tk.Y)

    tk.Label(frame_guncel, text="Başlangıç:").grid(row=0, column=0, sticky='e', pady=2)
    bd = tk.Entry(frame_guncel, width=3); bd.insert(0, now.strftime("%d"))
    bm = tk.Entry(frame_guncel, width=3); bm.insert(0, now.strftime("%m"))
    by = tk.Entry(frame_guncel, width=5); by.insert(0, now.strftime("%Y"))
    bd.grid(row=0, column=1, padx=1); bm.grid(row=0, column=2, padx=1); by.grid(row=0, column=3, padx=1)

    tk.Label(frame_guncel, text="Bitiş:").grid(row=1, column=0, sticky='e', pady=2)
    ed = tk.Entry(frame_guncel, width=3); ed.insert(0, now.strftime("%d"))
    em = tk.Entry(frame_guncel, width=3); em.insert(0, now.strftime("%m"))
    ey = tk.Entry(frame_guncel, width=5); ey.insert(0, now.strftime("%Y"))
    ed.grid(row=1, column=1, padx=1); em.grid(row=1, column=2, padx=1); ey.grid(row=1, column=3, padx=1)

    btn = tk.Button(frame_guncel, text="Aralığı Yükle", command=start_range_fetch, bg="green", fg="white", font=("Arial", 9, "bold"))
    btn.grid(row=0, column=4, rowspan=2, padx=15)

    # --- İlerleme Çubuğu (Progress Bar) Bölümü ---
    frame_status = tk.Frame(root)
    frame_status.pack(fill=tk.X, padx=25, pady=5)
    
    lbl_status = tk.Label(frame_status, text="Durum: Bekliyor", font=("Arial", 9, "bold"), fg="#555555")
    lbl_status.pack(side=tk.LEFT)
    
    progress = ttk.Progressbar(frame_status, orient="horizontal", mode="determinate")
    progress.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)

    # Tablo Yazı Tipi Stili (Ölçümlerin doğru yapılması için sabitliyoruz)
    style = ttk.Style()
    style.configure("Treeview", font=("Arial", 10), rowheight=25)
    style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

    cols = ("Türü", "Kullanıcı", "Gönd. Z.", "Kayıt Tarihi", "Rasat Tarihi", "Bülten")

    tree_frame = tk.Frame(root)
    tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

    tree = ttk.Treeview(tree_frame, columns=cols, show="headings")

    yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    yscroll.pack(side="right", fill="y")
    
    xscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    xscroll.pack(side="bottom", fill="x")
    
    tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

    for c in cols:
        if c == "Bülten":
            tree.heading(c, text=c, anchor="w")
            tree.column(c, width=500, anchor="w", stretch=True)
        elif c in ["Kayıt Tarihi", "Rasat Tarihi"]:
            tree.heading(c, text=c, anchor="center")
            tree.column(c, width=130, anchor="center", stretch=False)
        else:
            tree.heading(c, text=c, anchor="center")
            tree.column(c, width=80, anchor="center", stretch=False)

    tree.pack(side="left", fill="both", expand=True)

    # ================= SAĞ TIK (CONTEXT) MENÜSÜ =================
    right_click_menu = tk.Menu(root, tearoff=0)

    def copy_selection():
        selected_items = tree.selection()
        if not selected_items: return
        
        clipboard_text = ""
        for item in selected_items:
            values = tree.item(item)["values"]
            clipboard_text += "\t".join(str(v) for v in values) + "\n"
            
        root.clipboard_clear()
        root.clipboard_append(clipboard_text.strip())

    def select_all():
        for item in tree.get_children():
            tree.selection_add(item)

    def deselect_all():
        for item in tree.selection():
            tree.selection_remove(item)

    right_click_menu.add_command(label="📋 Kopyala", command=copy_selection)
    right_click_menu.add_command(label="✅ Hepsini Seç", command=select_all)
    right_click_menu.add_command(label="❌ Seçimi Kaldır", command=deselect_all)
    right_click_menu.add_separator()
    right_click_menu.add_command(label="📊 Excel'e Aktar", command=export_excel)
    right_click_menu.add_command(label="📝 TXT'ye Aktar", command=export_txt)

    def show_right_click_menu(event):
        # Eğer sağ tıklanan satır seçili değilse, sadece onu seç
        item = tree.identify_row(event.y)
        if item and item not in tree.selection():
            tree.selection_set(item)
            
        try:
            right_click_menu.tk_popup(event.x_root, event.y_root)
        finally:
            right_click_menu.grab_release()

    tree.bind("<Button-3>", show_right_click_menu)

    def auto_export_loop():
        last_monthly_run_day = None
        last_daily_run_hour = None
        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            current_day_str = now.strftime("%Y-%m-%d")
            
            # --- AYLIK YEDEK: Her gün gece 00:00 Z - 00:05 Z arası ---
            if now.hour == 0 and now.minute < 5:
                if last_monthly_run_day != current_day_str:
                    try:
                        start_d = datetime.date(now.year, now.month, 1)
                        end_d = now.date()
                        
                        auto_scraper = KardelenUltraScraper(ist.get())
                        results = auto_scraper.fetch(start_d, end_d)
                        
                        if results:
                            aylar = ["OCAK","ŞUBAT","MART","NİSAN","MAYIS","HAZİRAN","TEMMUZ","AĞUSTOS","EYLÜL","EKİM","KASIM","ARALIK"]
                            ay_isim = aylar[now.month - 1]
                            yil = str(now.year)
                            
                            base_dir = os.path.join(os.path.expanduser("~"), "KardelenLogs", "Aylik_Kayitlar", yil, "DEFTER_KAYD")
                            os.makedirs(base_dir, exist_ok=True)
                            file_path = os.path.join(base_dir, f"{ay_isim}.txt")
                            
                            # Pandas DataFrame üzerinden doğrudan Text (Tab Separated) olarak kaydetme
                            df = pd.DataFrame(results, columns=["TÜR", "KULL", "GÖND", "KAYIT", "RASAT", "BÜLTEN"])
                            df.to_csv(file_path, sep='\t', index=False, encoding='utf-8')

                            print(f"[OTO YEDEK] Aylık defter güncellendi: {file_path}")
                        last_monthly_run_day = current_day_str
                    except Exception as e:
                        print(f"[OTO YEDEK HATA (AYLIK)] {e}")

            # --- GÜNLÜK YEDEK: Her saat 47 geçe o günün verisini çeker ---
            if now.minute == 47:
                run_id = f"{current_day_str}_{now.hour}"
                if last_daily_run_hour != run_id:
                    try:
                        target_d = now.date()
                        auto_scraper = KardelenUltraScraper(ist.get())
                        results = auto_scraper.fetch(target_d, target_d)
                        
                        if results:
                            date_str = target_d.strftime("%d.%m.%Y")
                            folder_date = target_d.strftime("%Y-%m-%d")
                            
                            base_dir = os.path.join(os.path.expanduser("~"), "KardelenLogs", folder_date, "DEFTER_KAYD")
                            os.makedirs(base_dir, exist_ok=True)
                            file_path = os.path.join(base_dir, f"{date_str}.txt")
                            
                            # Pandas DataFrame üzerinden doğrudan Text (Tab Separated) olarak kaydetme
                            df = pd.DataFrame(results, columns=["TÜR", "KULL", "GÖND", "KAYIT", "RASAT", "BÜLTEN"])
                            df.to_csv(file_path, sep='\t', index=False, encoding='utf-8')

                            print(f"[OTO YEDEK] Günlük defter güncellendi: {file_path}")
                        last_daily_run_hour = run_id
                    except Exception as e:
                        print(f"[OTO YEDEK HATA (GÜNLÜK)] {e}")

            time.sleep(30)

    threading.Thread(target=auto_export_loop, daemon=True).start()

    root.mainloop()

if __name__ == "__main__":
    run_gui()