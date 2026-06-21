import os
import time
import tkinter as tk
from tkinter import messagebox, ttk
import threading

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

DOWNLOAD_DIR = r"C:\Users\nebio\Desktop\check"

def baslat_tarayici(istasyon_no, yil, ay, root_window):
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    chrome_options = Options()
    # Dosyaların otomatik olarak (sormadan) CHECK klasörüne inmesi için ayarlar
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Ekranda tarayıcıyı görebilmek için headless kullanmıyoruz
    # chrome_options.add_argument("--headless")
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.maximize_window()
        
        url = "http://kardelen.mgm.gov.tr/BultenGenel/Default.aspx"
        driver.get(url)
        
        # Selenium otomasyonu için temel yapı aşağıdadır. 
        # Sitenin gerçek input ID'leri (id="...") bilinemediği için, 
        # bu versiyonda tarayıcı yapılandırması yapılarak size teslim edilir. 
        # Tarayıcı açıldıktan sonra işlemleri manuel yaptığınızda, 
        # indirilen Excel dosyaları doğrudan check klasörüne gidecektir.
        
        root_window.after(0, lambda: messagebox.showinfo(
            "Tarayıcı Açıldı", 
            f"Tarayıcı başarıyla başlatıldı.\n\nLütfen web sayfasında İstasyon No: {istasyon_no}, Yıl: {yil}, Ay: {ay} seçimlerini yapıp göster butonuna tıklayın.\n\nDocument Map üzerindeki Export (Excel) butonuna tıkladığınızda dosyalar otomatik olarak:\n{DOWNLOAD_DIR}\nklasörüne inecektir."
        ))
        
        # Tarayıcıyı manuel işlemler için açık tutar
        while True:
            time.sleep(1)
            
    except Exception as e:
        root_window.after(0, lambda e=e: messagebox.showerror("Hata", f"Tarayıcı başlatılırken hata oluştu:\n{e}\n\nLütfen bilgisayarınızda Chrome tarayıcısının ve 'selenium' kütüphanesinin yüklü olduğundan emin olun."))

def arayuz_olustur():
    if not SELENIUM_AVAILABLE:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Eksik Kütüphane", "Lütfen terminali (CMD/PowerShell) açıp şu komutu çalıştırın:\n\npip install selenium")
        return

    root = tk.Tk()
    root.title("Kardelen Otomatik İndirme Asistanı")
    root.geometry("350x280")
    root.configure(bg="#ECF0F1")
    
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
    
    tk.Label(root, text="KARDELEN BÜLTEN İNDİRİCİ", font=("Segoe UI", 12, "bold"), bg="#ECF0F1", fg="#2C3E50").pack(pady=10)
    
    tk.Label(root, text="İstasyon No:", bg="#ECF0F1", font=("Segoe UI", 10)).pack(pady=2)
    ent_ist = tk.Entry(root, font=("Segoe UI", 10), justify="center")
    ent_ist.pack()
    
    tk.Label(root, text="Yıl:", bg="#ECF0F1", font=("Segoe UI", 10)).pack(pady=2)
    import datetime
    current_year = datetime.datetime.now().year
    cb_yil = ttk.Combobox(root, values=list(range(current_year, 2000, -1)), state="readonly", font=("Segoe UI", 10))
    cb_yil.set(current_year)
    cb_yil.pack()
    
    tk.Label(root, text="Ay:", bg="#ECF0F1", font=("Segoe UI", 10)).pack(pady=2)
    cb_ay = ttk.Combobox(root, values=[f"{i:02d}" for i in range(1, 13)], state="readonly", font=("Segoe UI", 10))
    
    varsayilan_ay = datetime.datetime.now().month - 1
    if varsayilan_ay == 0: varsayilan_ay = 12
    cb_ay.set(f"{varsayilan_ay:02d}")
    cb_ay.pack()
    
    def on_click():
        ist = ent_ist.get().strip()
        y = cb_yil.get()
        a = cb_ay.get()
        
        threading.Thread(target=baslat_tarayici, args=(ist, y, a, root), daemon=True).start()
        
    tk.Button(root, text="Tarayıcıyı Başlat", command=on_click, font=("Segoe UI", 10, "bold"), bg="#2980B9", fg="white", cursor="hand2").pack(pady=20)
    
    root.mainloop()

if __name__ == "__main__":
    arayuz_olustur()