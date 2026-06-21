# =============================================================================
# KARDELEN LOG GÖRÜNTÜLEYİCİ VE ANALİZ ARACI
# Bu dosya, Kardelen web sitesinden hava durumu verilerini çeker,
# TAF ve METAR raporlarını eşleştirir ve uyumluluk analizi yapar.
# =============================================================================
import pandas as pd
import json
import os
import sys
import time
import subprocess
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox
import threading
from datetime import datetime, timedelta, timezone
import re
import calendar
import turkey_map
import TAF_METAR_TREND
from tkinter import filedialog
from kardelen_scraper import KardelenScraper
from log_processor import process_and_analyze_logs


# =============================================================================
# AYARLAR VE YAPILANDIRMA
# =============================================================================

# >>> YAML KURAL ENTEGRASYONU <<<
YAML_KURALLAR = None
try:
    import yaml
    base_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_path = os.path.join(base_dir, "kurallar.yaml")
    if os.path.exists(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            YAML_KURALLAR = yaml.safe_load(f)
        print("✅ Kurallar YAML dosyasından yüklendi.")
except ImportError:
    print("⚠️ PyYAML yüklü değil. Limit kontrolleri yapılamayacak.")
except Exception as e:
    print(f"⚠️ YAML yükleme hatası: {e}")

# Analiz Detaylarını Saklayacağımız Hafıza (Row ID -> Reasons List)
ANALIZ_DETAYLARI = {}

# Tooltip Kontrol Değişkenleri (Global)
tooltip_window = None
last_tooltip_item = None
ALARM_SOUND_PATH = None
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anakardelen_config.json")

def load_config():
    """Uygulama ayarlarını (örn. alarm sesi yolu) kayıtlı dosyadan yükler."""
    global ALARM_SOUND_PATH
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                ALARM_SOUND_PATH = data.get("alarm_sound_path")
        except: pass

def save_config():
    """Mevcut ayarları dosyaya kaydeder."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({"alarm_sound_path": ALARM_SOUND_PATH}, f)
    except: pass

# Başlangıçta ayarları yükle
load_config()

robot = TAF_METAR_TREND.HavacilikRobotModulu()

# =============================================================================
# TOOLTIP VE GÖRSELLEŞTİRME FONKSİYONLARI
# Bu bölüm, ekrandaki renklendirmeleri ve fare ile üzerine gelince çıkan
# bilgi kutucuklarını (tooltip) yönetir.
# =============================================================================
def apply_regex_highlights(text_widget, line_idx, text_content, reasons):
    """Metin içindeki kritik hava durumu bilgilerini (Rüzgar, Görüş vb.) renklendirir."""
    tags = {
            "hl_wind": {"bg": "#FFCCBC", "keywords": ["Rüzgar", "Wind", "Yön", "Hız", "Gust", "VRB"]},
            "hl_vis":  {"bg": "#B3E5FC", "keywords": ["Rüyet", "Görüş", "Vis", "Sis", "Pus", "CAVOK"]},
            "hl_cloud": {"bg": "#C8E6C9", "keywords": ["Bulut", "Tavan", "Cloud", "OVC", "BKN", "NSC", "SKC", "CLR"]},
            "hl_wx":   {"bg": "#E1BEE7", "keywords": ["Hadise", "Yağış", "Weather", "RA", "SN", "TS", "SH", "DZ", "FG", "BR", "HZ"]}
    }
    regexes = {
            "hl_wind": r'\b(?:VRB|[0-3]\d{2})\d{2,3}(?:G\d{2,3})?KT\b',
            "hl_vis": r'(?<!/)\b\d{4}\b(?!/)|CAVOK',
            "hl_cloud": r'\b(?:FEW|SCT|BKN|OVC|VV)\d{3}(?:CB|TCU)?\b|NSC|SKC|CLR',
            "hl_wx": r'\b(?:\-|\+|VC)?(?:TS|SH|FZ|BL|DR|MI|BC|PR|RA|DZ|SN|SG|PL|GR|GS|UP|FG|BR|HZ|FU|VA|DU|SA|SS|DS){1,3}\b'
    }

    for tag, props in tags.items():
        text_widget.tag_config(tag, background=props["bg"], foreground="black")
        reasons_text = " ".join(reasons).lower()
        if any(k.lower() in reasons_text for k in props["keywords"]):
            for match in re.finditer(regexes[tag], text_content):
                ws = f"{line_idx}.{match.start()}"
                we = f"{line_idx}.{match.end()}"
                text_widget.tag_add(tag, ws, we)

def show_tooltip(x, y, content_data, text_color="#263238"):
    """Fare imlecinin olduğu yerde detaylı bilgi penceresi (tooltip) gösterir."""
    global tooltip_window

    # Varsa eskisini kapat
    if tooltip_window:
        tooltip_window.destroy()

    tooltip_window = tk.Toplevel()
    tooltip_window.wm_overrideredirect(True) # Çerçevesiz pencere
    tooltip_window.withdraw() # Önce gizle, hesaplama yapıp göstereceğiz

    bg_color = "#eceff1"

    # İçerik Tipi Kontrolü (Dict ise zengin içerik, str ise düz metin)
    if isinstance(content_data, dict):
        metar = content_data.get("metar", "")
        taf = content_data.get("taf", "")
        reasons = content_data.get("reasons", [])
        alarm = content_data.get("alarm", "YESIL")

        border_color = "#FF5252" if alarm in ["KIRMIZI", "HATA"] else ("#FFA726" if alarm == "SARI" else "#66BB6A")

        frame = tk.Frame(tooltip_window, bg=bg_color, highlightbackground=border_color, highlightthickness=2)
        frame.pack(fill="both", expand=True)

        # Zengin Metin Kutusu
        txt = tk.Text(frame, width=90, height=12, bg=bg_color, font=("Consolas", 9), relief="flat", wrap="word")
        txt.pack(padx=5, pady=5)

        # METAR Satırı
        line1 = metar
        txt.insert("end", line1 + "\n")
        apply_regex_highlights(txt, 1, line1, reasons)

        # TAF Satırı
        line2 = taf
        txt.insert("end", line2 + "\n")
        apply_regex_highlights(txt, 2, line2, reasons)

        txt.insert("end", "-"*90 + "\n")

        # Sebepler
        for r in reasons:
            txt.insert("end", f"• {r}\n")

        txt.config(state="disabled")
    else:
        # Eski usul düz metin (Fallback)
        text = str(content_data)
        border_color = "#FF5252" if "Hata" in text or "KRİTİK" in text else "#80cbc4"
        frame = tk.Frame(tooltip_window, bg=bg_color, highlightbackground=border_color, highlightthickness=2)
        frame.pack(fill="both", expand=True)

        label = tk.Label(frame, text=text, justify=tk.LEFT, background=bg_color, foreground=text_color, font=("Consolas", 10), padx=10, pady=8)
        label.pack()

        # Pencerenin boyutlarını hesaplaması için zorla güncelle
        tooltip_window.update_idletasks()

        # --- AKILLI KONUMLANDIRMA ---
        req_width = tooltip_window.winfo_reqwidth()
        req_height = tooltip_window.winfo_reqheight()
        screen_width = tooltip_window.winfo_screenwidth()
        screen_height = tooltip_window.winfo_screenheight()

        # Varsayılan konum (Farenin sağ altı)
        pos_x = x + 15
        pos_y = y + 10

        # Sağ kenara taşıyor mu? -> Sola al
        if pos_x + req_width > screen_width:
            pos_x = x - req_width - 15

        # Alt kenara taşıyor mu? -> Üste al
        if pos_y + req_height > screen_height:
            pos_y = y - req_height - 10

        # Sol veya üst kenardan taşmayı engelle (Negatif koordinat olmasın)
        pos_x = max(0, pos_x)
        pos_y = max(0, pos_y)

        # Yeni konumu uygula ve göster
        tooltip_window.wm_geometry(f"+{pos_x}+{pos_y}")
        tooltip_window.deiconify()

def hide_tooltip(event=None):
    """Ekranda açık olan tooltip penceresini kapatır."""
    global tooltip_window, last_tooltip_item
    if tooltip_window:
        tooltip_window.destroy()
        tooltip_window = None
    if event:
        last_tooltip_item = None

class ToolTip:
    """Butonlar ve etiketler için basit ipucu (tooltip) sınıfı."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)
    def show_tip(self, event=None):
        if self.tip_window or not self.text: return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("Arial", 8)).pack(ipadx=1)
    def hide_tip(self, event=None):
        if self.tip_window: self.tip_window.destroy(); self.tip_window = None
def on_tree_motion(event, tree, check_var=None):
    """Tablo üzerinde fare gezdirildiğinde satır detaylarını gösterir."""
    global last_tooltip_item

    # Eğer kontrol değişkeni (Uyum Sütunu tiki) varsa ve kapalıysa tooltip gösterme
    if check_var is not None and not check_var.get():
        hide_tooltip(event=True)
        return

    item_id = tree.identify_row(event.y)

    if item_id == last_tooltip_item:
        return

    last_tooltip_item = item_id
    hide_tooltip() # Öncekini gizle

    if item_id and item_id in ANALIZ_DETAYLARI:
        detay = ANALIZ_DETAYLARI[item_id]

        # Tooltip oluşturulacak metin var mı?
        reasons = detay.get("reasons", [])
        if reasons:
            # Zengin veri paketi hazırla
            data = {
                "metar": detay["metar"],
                "taf": detay["taf"],
                "reasons": reasons,
                "alarm": detay.get("alarm", "YESIL")
            }
            show_tooltip(event.x_root, event.y_root, data)

# =============================================================================
# ARAYÜZ (GUI) OLUŞTURMA VE BAŞLATMA
# Bu kısım, kullanıcının gördüğü pencereyi, butonları ve tabloyu oluşturur.
# =============================================================================
def gui_baslat():
    """Ana grafik arayüzünü (Pencere, Tablo, Butonlar) oluşturur ve başlatır."""
    root = tk.Tk()
    root.title("Kardelen Log Görüntüleyici (17244 KONYA) - ICAO Denetim Modu")
    root.geometry("1450x750")

    # Scraper instance
    scraper = KardelenScraper()

    # --- STİL VE ZEBRA DESENİ ---
    style = ttk.Style()
    style.theme_use('clam')

    # Zebra desen için iki farklı satır rengi
    style.configure("Treeview", 
        font=("Arial", 11), 
        rowheight=42,  # Satır yüksekliği artırıldı (iki satır metin için)
        background="#f9f9f9", 
        fieldbackground="#f9f9f9"
    )
    style.map("Treeview", background=[('selected', '#b3e5fc')])

    style.configure("Treeview.Heading", font=("Arial", 11, "bold"), background="#263238", foreground="white")

    # 3. TABLO
    tree_frame = tk.Frame(root)
    tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

    cols = ("KULL.", "GÖND.", "KAYIT TAR.", "RASAT TAR.", "BÜLTEN", "TREND UYUM")
    tree = ttk.Treeview(tree_frame, columns=cols, show="tree headings", selectmode="extended")

    ysb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    ysb.pack(side="right", fill="y")
    xsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    xsb.pack(side="bottom", fill="x")
    tree.configure(yscroll=ysb.set, xscroll=xsb.set)
    tree.pack(side="left", fill="both", expand=True)

    tree.heading("#0", text="TÜRÜ")
    for col in cols: tree.heading(col, text=col)

    tree.column("#0", width=180, anchor="w")
    tree.column("KULL.", width=70, anchor="center")
    tree.column("GÖND.", width=80, anchor="center")
    tree.column("KAYIT TAR.", width=130, anchor="center")
    tree.column("RASAT TAR.", width=130, anchor="center")
    tree.column("BÜLTEN", width=600, anchor="w")      
    tree.column("TREND UYUM", width=130, anchor="center")   

    # --- EKSİK TANIMLAMALAR (Header ve Control Panel) ---
    # Header Frame (Saat ve Başlık)
    header_frame = tk.Frame(root, bg="#2E7D32", height=40)
    header_frame.pack(fill="x", padx=5, pady=5, before=tree_frame)
    
    tk.Label(header_frame, text="KARDELEN LOG ANALİZÖRÜ", bg="#2E7D32", fg="white", font=("Arial", 12, "bold")).pack(side="left", padx=10)
    lbl_clock = tk.Label(header_frame, text="00:00:00 Z", bg="#2E7D32", fg="white", font=("Consolas", 14, "bold"))
    lbl_clock.pack(side="right", padx=10)

    # Control Panel (Tarih ve Filtreler)
    control_panel = tk.Frame(root)
    control_panel.pack(fill="x", padx=5, pady=5, before=tree_frame)

    frame_tarih = tk.LabelFrame(control_panel, text=" 📅 Tarih ", font=("Arial", 9, "bold"), fg="#333", padx=5, pady=5)
    frame_tarih.pack(side="left", padx=5, fill="y")
    now = datetime.now()
    cb_gun = ttk.Combobox(frame_tarih, values=[str(i).zfill(2) for i in range(1,32)], width=3)
    cb_gun.set(str(now.day).zfill(2))
    cb_gun.pack(side="left", padx=2)
    
    cb_ay = ttk.Combobox(frame_tarih, values=[], width=10)
    cb_ay.pack(side="left", padx=2)
    
    cb_yil = ttk.Combobox(frame_tarih, values=[str(i) for i in range(2023, 2030)], width=5)
    cb_yil.set(str(now.year))
    cb_yil.pack(side="left", padx=2)

    frame_filtre = tk.LabelFrame(control_panel, text=" 🔍 Filtre ", font=("Arial", 9, "bold"), fg="#333", padx=5, pady=5)
    frame_filtre.pack(side="left", padx=5, fill="y")
    cb_filt = ttk.Combobox(frame_filtre, values=[], width=15)
    cb_filt.pack(side="left", padx=5)

    # Alarm Değişkenleri (update_clock fonksiyonu için gerekli)
    var_alarm_active = tk.BooleanVar(value=False)
    var_alarm_time = tk.StringVar(value="00:00")
    var_alarm_triggered = tk.BooleanVar(value=False)

    # --- TAG TANIMLARI (BURAYA TAŞIYIN) ---
    tree.tag_configure('zebra1', background='#f9f9f9')
    tree.tag_configure('zebra2', background='#e3f2fd')
    tree.tag_configure('UYUMSUZ', background='#D32F2F', foreground='white')
    tree.tag_configure('DIKKAT', background='#FBC02D', foreground='black')
    tree.tag_configure('UYUMLU', background='#388E3C', foreground='white')
    tree.tag_configure('UYUMSUZ', background='#D32F2F', foreground='white')
    tree.tag_configure('DIKKAT', background='#FBC02D', foreground='black')
    tree.tag_configure('UYUMLU', background='#388E3C', foreground='white')
    tree.tag_configure('yellow_row', background='#FFFDE7')
    tree.tag_configure('white_row', background='white')
    tree.tag_configure('TS_ROW', background='#E1BEE7', foreground='black')
    tree.tag_configure('SN_ROW', background='#B3E5FC', foreground='black')
    tree.tag_configure('FG_ROW', background='#CFD8DC', foreground='black')

    # --- ZEBRA DESENLİ SATIR EKLEME ---
    def zebra_insert(parent, index, **kw):
        """Zebra desenli satır ekler."""
        children = tree.get_children(parent)
        tag = 'zebra1' if len(children) % 2 == 0 else 'zebra2'
        tags = kw.get('tags', ())
        kw['tags'] = tags + (tag,)
        return tree.insert(parent, index, **kw)

    # ...veri ekleme kısmında tree.insert yerine zebra_insert kullanın...
    # Örnek:
    # zebra_insert("", "end", text="...", values=(...), tags=(satir_tag,))

    # --- ÇOK SATIRLI METİN GÖSTERME ---
    # Treeview hücresinde iki satır metin göstermek için, metinleri '\n' ile ayırabilirsiniz:
    # Örnek:
    # zebra_insert("", "end", text="TÜRÜ", values=("KULL.\nEk Bilgi", "GÖND.\nEk Bilgi", ...))

    # --- EKSİK TANIMLAMALAR (Header ve Control Panel) ---
    # Header Frame (Saat ve Başlık)
    header_frame = tk.Frame(root, bg="#2E7D32", height=40)
    header_frame.pack(fill="x", padx=5, pady=5, before=tree_frame)
    
    tk.Label(header_frame, text="KARDELEN LOG ANALİZÖRÜ", bg="#2E7D32", fg="white", font=("Arial", 12, "bold")).pack(side="left", padx=10)
    lbl_clock = tk.Label(header_frame, text="00:00:00 Z", bg="#2E7D32", fg="white", font=("Consolas", 14, "bold"))
    lbl_clock.pack(side="right", padx=10)

    # Control Panel (Tarih ve Filtreler)
    control_panel = tk.Frame(root)
    control_panel.pack(fill="x", padx=5, pady=5, before=tree_frame)

    frame_tarih = tk.LabelFrame(control_panel, text=" 📅 Tarih ", font=("Arial", 9, "bold"), fg="#333", padx=5, pady=5)
    frame_tarih.pack(side="left", padx=5, fill="y")
    now = datetime.now()
    cb_gun = ttk.Combobox(frame_tarih, values=[str(i).zfill(2) for i in range(1,32)], width=3)
    cb_gun.set(str(now.day).zfill(2))
    cb_gun.pack(side="left", padx=2)
    
    cb_ay = ttk.Combobox(frame_tarih, values=[], width=10)
    cb_ay.pack(side="left", padx=2)
    
    cb_yil = ttk.Combobox(frame_tarih, values=[str(i) for i in range(2023, 2030)], width=5)
    cb_yil.set(str(now.year))
    cb_yil.pack(side="left", padx=2)

    frame_filtre = tk.LabelFrame(control_panel, text=" 🔍 Filtre ", font=("Arial", 9, "bold"), fg="#333", padx=5, pady=5)
    frame_filtre.pack(side="left", padx=5, fill="y")
    cb_filt = ttk.Combobox(frame_filtre, values=[], width=15)
    cb_filt.pack(side="left", padx=5)

    # Alarm Değişkenleri (update_clock fonksiyonu için gerekli)
    var_alarm_active = tk.BooleanVar(value=False)
    var_alarm_time = tk.StringVar(value="00:00")
    var_alarm_triggered = tk.BooleanVar(value=False)

    # --- GÖRÜNÜM AYARLARI ---
    frame_ayarlar = tk.LabelFrame(control_panel, text=" ⚙️ Görünüm ", font=("Arial", 9, "bold"), fg="#333", padx=5, pady=5)
    frame_ayarlar.pack(side="left", padx=5, fill="y")

    var_uyum_show = tk.BooleanVar(value=True)
    def toggle_uyum_col():
        """Tablodaki 'Uyum' sütununu gizler veya gösterir."""
        if var_uyum_show.get():
            tree["displaycolumns"] = "#all"
        else:
            display = [c for c in cols if c != "TREND UYUM"]
            tree["displaycolumns"] = tuple(display)

    cb_uyum = tk.Checkbutton(frame_ayarlar, text="Uyum Sütunu", variable=var_uyum_show, command=toggle_uyum_col)
    cb_uyum.pack(side="left", padx=5)

    # OTO YENİLEME (51-00 arası)
    var_oto_yenile = tk.BooleanVar(value=False)
    cb_oto = tk.Checkbutton(frame_ayarlar, text="Oto Yenile (51-00)", variable=var_oto_yenile)
    cb_oto.pack(side="left", padx=5)

    # --- GEÇMİŞ (HISTORY) PANELİ ---
    frame_history = tk.LabelFrame(control_panel, text="  Geçmiş ", font=("Arial", 9, "bold"), fg="#333", padx=5, pady=5)
    frame_history.pack(side="left", padx=5, fill="y")

    cb_ay_history = ttk.Combobox(frame_history, values=[], width=10)
    cb_ay_history.pack(side="left", padx=2)

    cb_yil_history = ttk.Combobox(frame_history, values=[str(i) for i in range(2010, 2031)], width=5)
    cb_yil_history.set(str(now.year))
    cb_yil_history.pack(side="left", padx=2)

    def populate_tree(grouped_data):
        """Verileri tabloya yazar (Hem canlı hem geçmiş veri için ortak fonksiyon)."""
        for item in tree.get_children(): tree.delete(item)
        ANALIZ_DETAYLARI.clear()

        for group in grouped_data:
            taf_item = group['taf']
            obs_list = group['observations']
            
            if taf_item:
                raw_t = list(taf_item["raw"])
                raw_t[5] = taf_item["bulten"]
                taf_iid = tree.insert("", "end", text=raw_t[0], values=tuple(raw_t[1:]) + ("-",), tags=('yellow_row',), open=True)
            else:
                taf_iid = ""
                
            for item in obs_list:
                analysis = item.get("analysis")
                uyum_sonucu = "-"
                satir_tag = 'white_row'
                
                if analysis:
                    durum = analysis["durum"]
                    if "UYUMSUZ" in durum:
                        uyum_sonucu = "❌ UYUMSUZ"
                        satir_tag = "UYUMSUZ"
                    elif "DIKKAT" in durum:
                        uyum_sonucu = "⚠️ DIKKAT"
                        satir_tag = "DIKKAT"
                    elif "UYUMLU" in durum:
                        uyum_sonucu = "✅ UYUMLU"
                        satir_tag = "UYUMLU"
                    elif "TAF YOK" in durum:
                        uyum_sonucu = "TAF Yok"
                    elif "LİMİT DIŞI" in durum:
                        uyum_sonucu = "-"
                    else:
                        uyum_sonucu = f"❓ {durum}"
                
                raw_l = list(item["raw"])
                raw_l[5] = item["bulten"]
                iid = tree.insert(taf_iid, "end", text=raw_l[0], values=tuple(raw_l[1:]) + (uyum_sonucu,), tags=(satir_tag,))
                
                if analysis:
                    ANALIZ_DETAYLARI[iid] = {
                        "metar": item["bulten"],
                        "taf": analysis["ref_taf"],
                        "reasons": analysis["reasons"],
                        "alarm": analysis["alarm"],
                        "durum": analysis["durum"],
                        "tarih": item["tarih_str"]
                    }
            
            tree.insert("", "end", text="", values=("", "", "", "", "", ""), tags=('white_row',))
        
        tree.after(100, adjust_column_widths)

    def trend_history():
        """Geçmiş verileri çeker ve analiz eder."""
        ay_secili = cb_ay_history.get()
        yil_secili = cb_yil_history.get()
        g = "01"
        a = ay_secili
        y = yil_secili
        
        # Ayın son gününü bul
        try:
            ay_num = list(scraper.config["ay_map"].keys()).index(a) + 1
            yil_num = int(y)
            _, last_day = calendar.monthrange(yil_num, ay_num)
            g_bit = str(last_day)
        except: 
            g_bit = "31"
            
        f_id = "500" # Tüm bültenler

        btn_trend_history.config(state="disabled", text="Yükleniyor...")
        lbl_status.config(text=f"Geçmiş veriler yükleniyor: {g}-{g_bit} {a} {y}")
        root.config(cursor="watch")
        pb_loading.pack(side="left", padx=10, pady=2)
        pb_loading.start(15)

        def islem():
            try:
                try: 
                    ham_veriler = scraper.fetch_logs(g, a, y, f_id, gun_bit=g_bit)
                except: 
                    ham_veriler = []

                if not ham_veriler:
                    root.after(0, lambda: lbl_status.config(text="Geçmiş veri bulunamadı."))
                    root.after(0, lambda: messagebox.showinfo("Bilgi", "Kriterlere uygun geçmiş veri yok."))
                    return

                grouped_data = process_and_analyze_logs(ham_veriler, robot)
                
                # UI Güncelleme
                root.after(0, lambda: populate_tree(grouped_data))
                root.after(0, lambda: lbl_status.config(text=f"Toplam {len(ham_veriler)} geçmiş kayıt bulundu."))
            except Exception as e:
                root.after(0, lambda: lbl_status.config(text="Hata oluştu."))
                root.after(0, lambda e=e: messagebox.showerror("Hata", f"Geçmiş analizi sırasında hata oluştu:\n{e}"))
            finally:
                def finalize_ui():
                    root.config(cursor="")
                    pb_loading.stop()
                    pb_loading.pack_forget()
                    btn_trend_history.config(state="normal", text="TREND")
                root.after(0, finalize_ui)

        threading.Thread(target=islem).start()

    btn_trend_history = tk.Button(frame_history, text="TREND", command=trend_history, width=8, height=1, bg="#E0E0E0")
    btn_trend_history.pack(pady=2)

    # Listele (Buton)
    frame_listele = tk.LabelFrame(control_panel, text=" 📋 Listele ", font=("Arial", 9, "bold"), fg="#333", padx=10, pady=5)
    frame_listele.pack(side="left", padx=5, fill="y")

    btn_goster_btn = tk.Button(frame_listele, text="GÖSTER", command=lambda: verileri_cek(), width=10, height=1, bg="#E0E0E0")
    btn_goster_btn.pack(pady=2)

    # --- EXCEL DIŞA AKTAR ---
    def export_to_excel():
        """Tablodaki verileri Excel (.xlsx) dosyası olarak kaydeder."""
        try:
            file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")])
            if not file_path: return

            data = []
            base_cols = ["TÜRÜ", "KULL.", "GÖND.", "KAYIT TAR.", "RASAT TAR.", "BÜLTEN", "TREND UYUM"]
            max_reasons = 0
            
            def traverse(parent=""):
                nonlocal max_reasons
                for child in tree.get_children(parent):
                    text = tree.item(child)["text"]
                    vals = tree.item(child)["values"]
                    
                    reasons = []
                    if child in ANALIZ_DETAYLARI:
                        reasons = ANALIZ_DETAYLARI[child].get("reasons", [])
                    
                    if len(reasons) > max_reasons:
                        max_reasons = len(reasons)

                    if vals: 
                        row = [text] + list(vals)
                        row.append(reasons)
                        data.append(row)
                    traverse(child)
            traverse()
            
            final_data = []
            reason_cols = [f"NEDEN {i+1}" for i in range(max_reasons)]
            all_cols = base_cols + reason_cols
            
            for row in data:
                base_vals = row[:-1]
                reasons_list = row[-1]
                padded = reasons_list + [""] * (max_reasons - len(reasons_list))
                final_data.append(base_vals + padded)
            
            df = pd.DataFrame(final_data, columns=all_cols)
            df.to_excel(file_path, index=False)
            messagebox.showinfo("Başarılı", "Veriler Excel'e aktarıldı.")
        except Exception as e:
            messagebox.showerror("Hata", f"Excel'e aktarım hatası: {e}")

    def save_detailed_log():
        """Analiz sonuçlarını detaylı bir metin dosyasına kaydeder."""
        if not ANALIZ_DETAYLARI:
            messagebox.showwarning("Uyarı", "Kaydedilecek analiz verisi yok.")
            return
            
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Metin Dosyası", "*.txt"), ("Log Dosyası", "*.log")],
                title="Detaylı Log Kaydet"
            )
            if not file_path: return
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"KARDELEN DETAYLI ANALİZ RAPORU\n")
                f.write(f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
                f.write("="*80 + "\n\n")
                
                for item_id in tree.get_children():
                    # Grup başlıklarını (TAF satırları) işle
                    if item_id not in ANALIZ_DETAYLARI:
                        vals = tree.item(item_id)['values']
                        text = tree.item(item_id)['text']
                        if "TAF" in text:
                             f.write(f"\n>>> TAF GRUBU: {text} (Yayın: {vals[2]})\n")
                             f.write("-" * 50 + "\n")
                        continue

                    detay = ANALIZ_DETAYLARI[item_id]
                    durum = "BİLİNMİYOR"
                    if detay['alarm'] == "YESIL": durum = "UYUMLU"
                    elif detay['alarm'] == "SARI": durum = "DIKKAT"
                    elif detay['alarm'] == "KIRMIZI": durum = "UYUMSUZ"

                    f.write(f"[{detay['tarih']}] {detay['metar']}\n")
                    f.write(f"   DURUM: {durum}\n")
                    f.write(f"   REF TAF: {detay['taf']}\n")
                    if detay['reasons']:
                        f.write("   NEDENLER:\n")
                        for r in detay['reasons']: f.write(f"     - {r}\n")
                    f.write("\n")
            
            messagebox.showinfo("Başarılı", f"Log dosyası kaydedildi:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"Log kaydetme hatası: {e}")

    # Excel Butonu
    btn_excel = tk.Button(frame_listele, text="Excel'e Aktar", command=export_to_excel, width=10, height=1, bg="#E0E0E0")
    btn_excel.pack(pady=2)
    
    # Log Butonu
    btn_log = tk.Button(frame_listele, text="Log Kaydet (.txt)", command=save_detailed_log, width=12, height=1, bg="#E0E0E0")
    btn_log.pack(pady=2)

    # Göster (Süs)
    frame_goster = tk.LabelFrame(control_panel, text=" 👁️ Göster ", font=("Arial", 9, "bold"), fg="#333", padx=10, pady=5)
    frame_goster.pack(side="left", padx=5, fill="y")
    btn_analiz = tk.Button(frame_goster, text="Log Analiz Sayfası", state="disabled", width=15, font=("Arial", 9))
    btn_analiz.pack()

    # --- TÜRKİYE HARİTASI BUTONU ---
    def open_map_window():
        class ToolTipAdapter:
            def show_tooltip(self, parent, x, y, text, color):
                show_tooltip(x, y, text, color)
            def hide_tooltip(self):
                hide_tooltip()
        
        class MapContext:
            def __init__(self):
                self.incompatible_df = pd.DataFrame(columns=["date", "Türü", "İstasyon", "Bülten", "_uyum", "_detay", "_ref_taf", "_dt"])
                self.station_scores_list = []
            def add_to_monitor(self, rows): pass
            def open_detail_window(self, event=None, external_tree=None, external_df=None): pass

        turkey_map.open_turkey_map(root, MapContext(), robot, ToolTipAdapter())

    btn_map = tk.Button(frame_goster, text="Türkiye Haritası", command=open_map_window, width=15, font=("Arial", 9), bg="#BBDEFB")
    btn_map.pack(pady=2)

    # Bilgi Çubuğu
    info_strip = tk.Frame(root, bg="#FFF9C4", height=25)
    info_strip.pack(fill="x", padx=10)
    lbl_status = tk.Label(info_strip, text="Hazır - Site analizi bekleniyor...", bg="#FFF9C4", fg="black", font=("Arial", 9))
    lbl_status.pack(side="left", padx=5)
    pb_loading = ttk.Progressbar(info_strip, orient="horizontal", length=200, mode="indeterminate")

    # 3. TABLO
    tree_frame = tk.Frame(root)
    tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

    cols = ("KULL.", "GÖND.", "KAYIT TAR.", "RASAT TAR.", "BÜLTEN", "TREND UYUM")
    tree = ttk.Treeview(tree_frame, columns=cols, show="tree headings", selectmode="extended")

    ysb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    ysb.pack(side="right", fill="y")
    xsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    xsb.pack(side="bottom", fill="x")
    tree.configure(yscroll=ysb.set, xscroll=xsb.set)
    tree.pack(side="left", fill="both", expand=True)

    tree.heading("#0", text="TÜRÜ")
    for col in cols: tree.heading(col, text=col)

    tree.column("#0", width=180, anchor="w")
    tree.column("KULL.", width=70, anchor="center")
    tree.column("GÖND.", width=80, anchor="center")
    tree.column("KAYIT TAR.", width=130, anchor="center")
    tree.column("RASAT TAR.", width=130, anchor="center")
    tree.column("BÜLTEN", width=600, anchor="w")      
    tree.column("TREND UYUM", width=130, anchor="center")   

    # --- TAG TANIMLARI (BURAYA TAŞIYIN) ---
    tree.tag_configure('zebra1', background='#f9f9f9')
    tree.tag_configure('zebra2', background='#e3f2fd')
    tree.tag_configure('UYUMSUZ', background='#D32F2F', foreground='white')
    tree.tag_configure('DIKKAT', background='#FBC02D', foreground='black')
    tree.tag_configure('UYUMLU', background='#388E3C', foreground='white')
    tree.tag_configure('yellow_row', background='#FFFDE7')
    tree.tag_configure('white_row', background='white')
    tree.tag_configure('TS_ROW', background='#E1BEE7', foreground='black')
    tree.tag_configure('SN_ROW', background='#B3E5FC', foreground='black')
    tree.tag_configure('FG_ROW', background='#CFD8DC', foreground='black')

    # --- ZEBRA DESENLİ SATIR EKLEME ---
    def zebra_insert(parent, index, **kw):
        """Zebra desenli satır ekler."""
        children = tree.get_children(parent)
        tag = 'zebra1' if len(children) % 2 == 0 else 'zebra2'
        tags = kw.get('tags', ())
        kw['tags'] = tags + (tag,)
        return tree.insert(parent, index, **kw)

    # ...veri ekleme kısmında tree.insert yerine zebra_insert kullanın...
    # Örnek:
    # zebra_insert("", "end", text="...", values=(...), tags=(satir_tag,))

    # --- ÇOK SATIRLI METİN GÖSTERME ---
    # Treeview hücresinde iki satır metin göstermek için, metinleri '\n' ile ayırabilirsiniz:
    # Örnek:
    # zebra_insert("", "end", text="TÜRÜ", values=("KULL.\nEk Bilgi", "GÖND.\nEk Bilgi", ...))

    # --- EKSİK TANIMLAMALAR (Header ve Control Panel) ---
    # Header Frame (Saat ve Başlık)
    header_frame = tk.Frame(root, bg="#2E7D32", height=40)
    header_frame.pack(fill="x", padx=5, pady=5, before=tree_frame)
    
    tk.Label(header_frame, text="KARDELEN LOG ANALİZÖRÜ", bg="#2E7D32", fg="white", font=("Arial", 12, "bold")).pack(side="left", padx=10)
    lbl_clock = tk.Label(header_frame, text="00:00:00 Z", bg="#2E7D32", fg="white", font=("Consolas", 14, "bold"))
    lbl_clock.pack(side="right", padx=10)

    # Control Panel (Tarih ve Filtreler)
    control_panel = tk.Frame(root)
    control_panel.pack(fill="x", padx=5, pady=5, before=tree_frame)

    frame_tarih = tk.LabelFrame(control_panel, text=" 📅 Tarih ", font=("Arial", 9, "bold"), fg="#333", padx=5, pady=5)
    frame_tarih.pack(side="left", padx=5, fill="y")
    now = datetime.now()
    cb_gun = ttk.Combobox(frame_tarih, values=[str(i).zfill(2) for i in range(1,32)], width=3)
    cb_gun.set(str(now.day).zfill(2))
    cb_gun.pack(side="left", padx=2)
    
    cb_ay = ttk.Combobox(frame_tarih, values=[], width=10)
    cb_ay.pack(side="left", padx=2)
    
    cb_yil = ttk.Combobox(frame_tarih, values=[str(i) for i in range(2023, 2030)], width=5)
    cb_yil.set(str(now.year))
    cb_yil.pack(side="left", padx=2)

    frame_filtre = tk.LabelFrame(control_panel, text=" 🔍 Filtre ", font=("Arial", 9, "bold"), fg="#333", padx=5, pady=5)
    frame_filtre.pack(side="left", padx=5, fill="y")
    cb_filt = ttk.Combobox(frame_filtre, values=[], width=15)
    cb_filt.pack(side="left", padx=5)

    # Alarm Değişkenleri (update_clock fonksiyonu için gerekli)
    var_alarm_active = tk.BooleanVar(value=False)
    var_alarm_time = tk.StringVar(value="00:00")
    var_alarm_triggered = tk.BooleanVar(value=False)

    # --- GÖRÜNÜM AYARLARI ---
    frame_ayarlar = tk.LabelFrame(control_panel, text=" ⚙️ Görünüm ", font=("Arial", 9, "bold"), fg="#333", padx=5, pady=5)
    frame_ayarlar.pack(side="left", padx=5, fill="y")

    var_uyum_show = tk.BooleanVar(value=True)
    def toggle_uyum_col():
        """Tablodaki 'Uyum' sütununu gizler veya gösterir."""
        if var_uyum_show.get():
            tree["displaycolumns"] = "#all"
        else:
            display = [c for c in cols if c != "TREND UYUM"]
            tree["displaycolumns"] = tuple(display)

    cb_uyum = tk.Checkbutton(frame_ayarlar, text="Uyum Sütunu", variable=var_uyum_show, command=toggle_uyum_col)
    cb_uyum.pack(side="left", padx=5)

    # OTO YENİLEME (51-00 arası)
    var_oto_yenile = tk.BooleanVar(value=False)
    cb_oto = tk.Checkbutton(frame_ayarlar, text="Oto Yenile (51-00)", variable=var_oto_yenile)
    cb_oto.pack(side="left", padx=5)

    # Listele (Buton)
    frame_listele = tk.LabelFrame(control_panel, text=" 📋 Listele ", font=("Arial", 9, "bold"), fg="#333", padx=10, pady=5)
    frame_listele.pack(side="left", padx=5, fill="y")

    btn_goster_btn = tk.Button(frame_listele, text="GÖSTER", command=lambda: verileri_cek(), width=10, height=1, bg="#E0E0E0")
    btn_goster_btn.pack(pady=2)

    # --- EXCEL DIŞA AKTAR ---
    def export_to_excel():
        """Tablodaki verileri Excel (.xlsx) dosyası olarak kaydeder."""
        try:
            file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")])
            if not file_path: return

            data = []
            base_cols = ["TÜRÜ", "KULL.", "GÖND.", "KAYIT TAR.", "RASAT TAR.", "BÜLTEN", "TREND UYUM"]
            max_reasons = 0
            
            def traverse(parent=""):
                nonlocal max_reasons
                for child in tree.get_children(parent):
                    text = tree.item(child)["text"]
                    vals = tree.item(child)["values"]
                    
                    reasons = []
                    if child in ANALIZ_DETAYLARI:
                        reasons = ANALIZ_DETAYLARI[child].get("reasons", [])
                    
                    if len(reasons) > max_reasons:
                        max_reasons = len(reasons)

                    if vals: 
                        row = [text] + list(vals)
                        row.append(reasons)
                        data.append(row)
                    traverse(child)
            traverse()
            
            final_data = []
            reason_cols = [f"NEDEN {i+1}" for i in range(max_reasons)]
            all_cols = base_cols + reason_cols
            
            for row in data:
                base_vals = row[:-1]
                reasons_list = row[-1]
                padded = reasons_list + [""] * (max_reasons - len(reasons_list))
                final_data.append(base_vals + padded)
            
            df = pd.DataFrame(final_data, columns=all_cols)
            df.to_excel(file_path, index=False)
            messagebox.showinfo("Başarılı", "Veriler Excel'e aktarıldı.")
        except Exception as e:
            messagebox.showerror("Hata", f"Excel'e aktarım hatası: {e}")

    def save_detailed_log():
        """Analiz sonuçlarını detaylı bir metin dosyasına kaydeder."""
        if not ANALIZ_DETAYLARI:
            messagebox.showwarning("Uyarı", "Kaydedilecek analiz verisi yok.")
            return
            
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Metin Dosyası", "*.txt"), ("Log Dosyası", "*.log")],
                title="Detaylı Log Kaydet"
            )
            if not file_path: return
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"KARDELEN DETAYLI ANALİZ RAPORU\n")
                f.write(f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
                f.write("="*80 + "\n\n")
                
                for item_id in tree.get_children():
                    # Grup başlıklarını (TAF satırları) işle
                    if item_id not in ANALIZ_DETAYLARI:
                        vals = tree.item(item_id)['values']
                        text = tree.item(item_id)['text']
                        if "TAF" in text:
                             f.write(f"\n>>> TAF GRUBU: {text} (Yayın: {vals[2]})\n")
                             f.write("-" * 50 + "\n")
                        continue

                    detay = ANALIZ_DETAYLARI[item_id]
                    durum = "BİLİNMİYOR"
                    if detay['alarm'] == "YESIL": durum = "UYUMLU"
                    elif detay['alarm'] == "SARI": durum = "DIKKAT"
                    elif detay['alarm'] == "KIRMIZI": durum = "UYUMSUZ"

                    f.write(f"[{detay['tarih']}] {detay['metar']}\n")
                    f.write(f"   DURUM: {durum}\n")
                    f.write(f"   REF TAF: {detay['taf']}\n")
                    if detay['reasons']:
                        f.write("   NEDENLER:\n")
                        for r in detay['reasons']: f.write(f"     - {r}\n")
                    f.write("\n")
            
            messagebox.showinfo("Başarılı", f"Log dosyası kaydedildi:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"Log kaydetme hatası: {e}")

    # Excel Butonu
    btn_excel = tk.Button(frame_listele, text="Excel'e Aktar", command=export_to_excel, width=10, height=1, bg="#E0E0E0")
    btn_excel.pack(pady=2)
    
    # Log Butonu
    btn_log = tk.Button(frame_listele, text="Log Kaydet (.txt)", command=save_detailed_log, width=12, height=1, bg="#E0E0E0")
    btn_log.pack(pady=2)

    # Göster (Süs)
    frame_goster = tk.LabelFrame(control_panel, text=" 👁️ Göster ", font=("Arial", 9, "bold"), fg="#333", padx=10, pady=5)
    frame_goster.pack(side="left", padx=5, fill="y")
    btn_analiz = tk.Button(frame_goster, text="Log Analiz Sayfası", state="disabled", width=15, font=("Arial", 9))
    btn_analiz.pack()

    # Bilgi Çubuğu
    info_strip = tk.Frame(root, bg="#FFF9C4", height=25)
    info_strip.pack(fill="x", padx=10)
    lbl_status = tk.Label(info_strip, text="Hazır - Site analizi bekleniyor...", bg="#FFF9C4", fg="black", font=("Arial", 9))
    lbl_status.pack(side="left", padx=5)

    # 3. TABLO
    tree_frame = tk.Frame(root)
    tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

    cols = ("KULL.", "GÖND.", "KAYIT TAR.", "RASAT TAR.", "BÜLTEN", "TREND UYUM")
    tree = ttk.Treeview(tree_frame, columns=cols, show="tree headings", selectmode="extended")

    ysb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    ysb.pack(side="right", fill="y")
    xsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    xsb.pack(side="bottom", fill="x")
    tree.configure(yscroll=ysb.set, xscroll=xsb.set)
    tree.pack(side="left", fill="both", expand=True)

    tree.heading("#0", text="TÜRÜ")
    for col in cols: tree.heading(col, text=col)

    tree.column("#0", width=180, anchor="w")
    tree.column("KULL.", width=70, anchor="center")
    tree.column("GÖND.", width=80, anchor="center")
    tree.column("KAYIT TAR.", width=130, anchor="center")
    tree.column("RASAT TAR.", width=130, anchor="center")
    tree.column("BÜLTEN", width=600, anchor="w")      
    tree.column("TREND UYUM", width=130, anchor="center")   

    # --- TAG TANIMLARI (BURAYA TAŞIYIN) ---
    tree.tag_configure('zebra1', background='#f9f9f9')
    tree.tag_configure('zebra2', background='#e3f2fd')
    tree.tag_configure('UYUMSUZ', background='#D32F2F', foreground='white')
    tree.tag_configure('DIKKAT', background='#FBC02D', foreground='black')
    tree.tag_configure('UYUMLU', background='#388E3C', foreground='white')
    tree.tag_configure('yellow_row', background='#FFFDE7')
    tree.tag_configure('white_row', background='white')
    tree.tag_configure('TS_ROW', background='#E1BEE7', foreground='black')
    tree.tag_configure('SN_ROW', background='#B3E5FC', foreground='black')
    tree.tag_configure('FG_ROW', background='#CFD8DC', foreground='black')

    def adjust_column_widths():
        """Tablo sütun genişliklerini içeriğe göre otomatik olarak ayarlar."""
        try:
            font = tkfont.Font(family="Arial", size=10)
            header_font = tkfont.Font(family="Arial", size=10, weight="bold")

            for col in cols:
                max_width = header_font.measure(col) + 25

                children = tree.get_children()
                # Performans için maksimum 100 satırı kontrol et
                for i, item in enumerate(children):
                    if i > 100: break 
                    val = tree.set(item, col)
                    w = font.measure(str(val)) + 20
                    if w > max_width:
                        max_width = w

                if col == "BÜLTEN":
                    max_width = min(max_width, 900)
                    max_width = max(max_width, 400)

                tree.column(col, width=max_width)
        except Exception as e:
            print(f"Sütun ayar hatası: {e}")

    # --- EVENT BINDING (MOUSE HAREKETLERİ - TOOLTIP İÇİN) ---
    tree.bind("<Motion>", lambda event: on_tree_motion(event, tree, var_uyum_show))
    tree.bind("<Leave>", hide_tooltip)

    # ================= KOPYALAMA FONKSİYONLARI =================
    def copy_selection(event=None):
        """Seçili satırları kopyalar."""
        selected_items = tree.selection()
        if not selected_items:
            return

        copy_text = ""
        for item_id in selected_items:
            text = tree.item(item_id, 'text')
            vals = tree.item(item_id, 'values')
            copy_text += text + "\t" + "\t".join(map(str, vals)) + "\n"

        root.clipboard_clear()
        root.clipboard_append(copy_text)
        messagebox.showinfo("Kopyalandı", f"{len(selected_items)} satır panoya kopyalandı.")

    def copy_all_table():
        """Tablodaki tüm verileri kopyalar."""
        def traverse(parent=""):
            res = ""
            for child in tree.get_children(parent):
                text = tree.item(child)["text"]
                vals = tree.item(child)["values"]
                res += text + "\t" + "\t".join(map(str, vals)) + "\n"
                res += traverse(child)
            return res

        copy_text = "TÜRÜ\t" + "\t".join(cols) + "\n" + traverse()

        root.clipboard_clear()
        root.clipboard_append(copy_text)
        messagebox.showinfo("Kopyalandı", "Tüm tablo panoya kopyalandı.")

    def select_all_tree(event=None):
        """Tüm satırları (veya varsa sadece sarı vurguluları) seçer."""
        yellow_items = []
        def traverse(parent=""):
            for child in tree.get_children(parent):
                if "search_yellow" in tree.item(child, "tags"):
                    yellow_items.append(child)
                traverse(child)
        traverse()

        if yellow_items:
            tree.selection_remove(tree.selection())
            for item in yellow_items:
                tree.selection_add(item)
        else:
            for item in tree.get_children():
                tree.selection_add(item)
                for child in tree.get_children(item):
                    tree.selection_add(child)
        return 'break'

    def open_main_search_dialog(event=None):
        """Ana tabloda arama yapmak için pencere açar."""
        search_win = tk.Toplevel(root)
        search_win.title("Tabloda Ara")
        search_win.geometry("380x140")
        search_win.transient(root)
        search_win.resizable(False, False)

        f_top = tk.Frame(search_win)
        f_top.pack(pady=10)

        tk.Label(f_top, text="Aranacak Metin:").pack(side="left")
        entry_search = tk.Entry(f_top, width=25)
        entry_search.pack(side="left", padx=5)
        entry_search.focus_set()

        lbl_status = tk.Label(search_win, text="", fg="gray")
        lbl_status.pack()

        search_data = {"matches": [], "idx": -1}

        def clear_search_tags():
            for item in search_data["matches"]:
                try:
                    tags = list(tree.item(item, "tags"))
                    if "search_yellow" in tags:
                        tags.remove("search_yellow")
                        tree.item(item, tags=tags)
                except: pass

        def on_close():
            clear_search_tags()
            search_win.destroy()

        search_win.protocol("WM_DELETE_WINDOW", on_close)

        def do_search(event=None):
            term = entry_search.get().lower()
            clear_search_tags()
            search_data["matches"] = []
            
            if not term:
                lbl_status.config(text="")
                return
                
            tree.selection_remove(tree.selection())
            
            # Ağaçtaki yellow tag'i tanımla
            tree.tag_configure("search_yellow", background="#FFEB3B", foreground="black")
            
            matches = []
            def traverse(parent=""):
                for child in tree.get_children(parent):
                    text = str(tree.item(child)["text"]).lower()
                    vals = [str(v).lower() for v in tree.item(child)["values"]]
                    if term in text or any(term in v for v in vals):
                        matches.append(child)
                        tags = list(tree.item(child, "tags"))
                        if "search_yellow" not in tags:
                            tags.append("search_yellow")
                            tree.item(child, tags=tags)
                    traverse(child)
            traverse()
            search_data["matches"] = matches
            search_data["idx"] = -1
            if matches:
                lbl_status.config(text=f"{len(matches)} sonuç bulundu.")
                navigate(1)
            else:
                lbl_status.config(text="Sonuç bulunamadı.")

        def navigate(direction):
            if not search_data["matches"]: return
            if direction == 1:
                search_data["idx"] = (search_data["idx"] + 1) % len(search_data["matches"])
            else:
                search_data["idx"] = (search_data["idx"] - 1) % len(search_data["matches"])
            item_id = search_data["matches"][search_data["idx"]]
            tree.selection_set(item_id)
            tree.see(item_id)
            lbl_status.config(text=f"Sonuç: {search_data['idx']+1} / {len(search_data['matches'])}")

        entry_search.bind("<Return>", do_search)
        f_btns = tk.Frame(search_win)
        f_btns.pack(pady=5, fill="x")
        tk.Button(f_btns, text="ARA", command=do_search, width=10, bg="#B0BEC5").pack(side="left", padx=10, expand=True)
        tk.Button(f_btns, text="< ÖNCEKİ", command=lambda: navigate(-1), width=10).pack(side="left", padx=5, expand=True)
        tk.Button(f_btns, text="SONRAKİ >", command=lambda: navigate(1), width=10).pack(side="left", padx=10, expand=True)

    # Sağ Tık Menüsü
    context_menu = tk.Menu(root, tearoff=0)
    context_menu.add_command(label="Seçileni Kopyala (Ctrl+C)", command=copy_selection)
    context_menu.add_command(label="Tümünü Seç (Ctrl+A)", command=select_all_tree)
    context_menu.add_separator()
    context_menu.add_command(label="Tüm Tabloyu Kopyala", command=copy_all_table)
    context_menu.add_separator()
    context_menu.add_command(label="Tabloda Ara... (Ctrl+F)", command=open_main_search_dialog)
    context_menu.add_separator()

    def expand_all():
        """Tablodaki tüm grupları açar."""
        for item in tree.get_children():
            tree.item(item, open=True)

    def collapse_all():
        """Tablodaki tüm grupları kapatır."""
        for item in tree.get_children():
            tree.item(item, open=False)

    context_menu.add_command(label="Tümünü Genişlet", command=expand_all)
    context_menu.add_command(label="Tümünü Daralt", command=collapse_all)

    def show_context_menu(event):
        """Tablo üzerinde sağ tıklandığında menüyü açar."""
        row_id = tree.identify_row(event.y)
        if row_id:
            if row_id not in tree.selection():
                tree.selection_set(row_id)
            context_menu.tk_popup(event.x_root, event.y_root)

    tree.bind("<Button-3>", show_context_menu)
    root.bind("<Control-c>", copy_selection)
    root.bind("<Control-a>", select_all_tree)
    root.bind("<Control-f>", open_main_search_dialog)
    # ==========================================================

    # --- DENETLEME MEKANİZMASI (POP-UP DETAY) ---
    def detay_goster(event):
        """Çift tıklanan satırın detaylı analiz raporunu yeni pencerede açar."""
        selected_item = tree.selection()
        if not selected_item: return

        item_id = selected_item[0]
        detay = ANALIZ_DETAYLARI.get(item_id)

        if not detay: return

        # Popup Pencere Oluştur
        popup = tk.Toplevel(root)
        popup.title("ICAO Denetim Raporu")
        popup.geometry("650x450")
        popup.configure(bg="#f0f0f0")

        header_text = "Analiz Detayı"
        text_color = "black"

        # ICAO.py'den gelen alarm durumuna göre başlık ve renk
        if detay['alarm'] == "SARI":
            header_text = "⚠️ DIKKAT: TREND İLE UYUM SAĞLANDI (veya Fiziksel Uyarı)"
            text_color = "#2E7D32" # Koyu Yeşil
        elif detay['alarm'] == "KIRMIZI":
            header_text = "❌ UYUMSUZLUK TESPİTİ"
            text_color = "#D32F2F" # Kırmızı
        elif detay['alarm'] == "YESIL":
            header_text = "✅ TAM UYUMLU"
            text_color = "#2E7D32" # Yeşil

        tk.Label(popup, text=header_text, font=("Arial", 12, "bold"), fg=text_color, bg="#f0f0f0").pack(pady=10)

        text_area = tk.Text(popup, wrap="word", font=("Consolas", 11), padx=10, pady=10, fg=text_color)
        text_area.pack(fill="both", expand=True, padx=10, pady=5)

        # Satır satır ekleme ve boyama
        text_area.insert("end", f"METAR TARİHİ: {detay['tarih']}\n")
        text_area.insert("end", f"{'-'*60}\n")

        metar_str = f"METAR: {detay['metar']}"
        text_area.insert("end", metar_str + "\n")
        line_metar = int(text_area.index("insert").split('.')[0]) - 1
        apply_regex_highlights(text_area, line_metar, metar_str, detay['reasons'])

        text_area.insert("end", "\n")

        taf_str = f"REFERANS TAF: {detay['taf']}"
        text_area.insert("end", taf_str + "\n")
        line_taf = int(text_area.index("insert").split('.')[0]) - 1
        apply_regex_highlights(text_area, line_taf, taf_str, detay['reasons'])

        text_area.insert("end", f"\n{'-'*60}\nANALİZ SONUCU:\n")

        durum = detay.get('durum', '')
        reasons = detay.get('reasons', [])

        if "UYUMSUZ" in durum:
            text_area.insert("end", "1- UYUMSUZLUK NEDENİ:\n")
            for r in reasons: text_area.insert("end", f"• {r}\n")
            text_area.insert("end", "\n2- TREND KONTROLÜ:\n• Trend ile de uyum sağlanamadı veya Trend yok.\n")
            text_area.insert("end", "\n3- SONUÇ:\n• ❌ UYUMSUZ\n")
            
        elif "DIKKAT" in durum:
            text_area.insert("end", "1- UYUMSUZLUK NEDENİ (Ana METAR):\n")
            for r in reasons: text_area.insert("end", f"• {r}\n")
            text_area.insert("end", "\n2- TREND KONTROLÜ:\n• ✅ METAR Trendi TAF limitlerine giriyor.\n")
            text_area.insert("end", "\n3- SONUÇ:\n• ⚠️ DIKKAT (Trend ile uyumlu)\n")
            
        elif "UYUMLU" in durum:
            text_area.insert("end", "1- UYUM DURUMU:\n• TAF limitleri dahilinde.\n")
            if "Trend" in durum: text_area.insert("end", " (TAF Trendi ile)\n")
            text_area.insert("end", "\n3- SONUÇ:\n• ✅ UYUMLU\n")
            
        else:
            if reasons:
                for r in reasons: text_area.insert("end", f"• {r}\n")
            else:
                text_area.insert("end", "• Limit içi veya tam uyumlu.")

        text_area.config(state="disabled")

    tree.bind("<Double-1>", detay_goster)

    def flash_visual_alert(count=10):
        """Alarm çaldığında başlık çubuğunu yanıp söndürür (Görsel Uyarı)."""
        if count > 0:
            current_bg = header_frame.cget("bg")
            # Kırmızı (#ef5350) ile Orijinal Yeşil (#66BB6A) arasında geçiş
            new_bg = "#ef5350" if current_bg == "#66BB6A" else "#66BB6A"
            header_frame.config(bg=new_bg)
            root.after(400, lambda: flash_visual_alert(count - 1))
        else:
            header_frame.config(bg="#66BB6A")

    def play_alarm_sound():
        """Seçili alarm sesini çalar."""
        root.after(0, flash_visual_alert) # Görsel uyarıyı başlat

        if ALARM_SOUND_PATH and os.path.exists(ALARM_SOUND_PATH):
            try:
                from playsound import playsound
                # GUI'yi dondurmamak için sesi ayrı bir thread'de çal
                threading.Thread(target=lambda: playsound(ALARM_SOUND_PATH), daemon=True).start()
            except ImportError:
                print("⚠️ 'playsound' kütüphanesi yüklü değil. Alarm sesi çalınamıyor.")
                root.bell() # Yedek olarak sistem zilini çal
            except Exception as e:
                print(f"Ses çalma hatası: {e}")
                root.bell()
        else:
            root.bell() # Varsayılan sistem zilini çal

    # Uygulama Durumu (Otomatik işlemler için)
    app_state = {
        "last_refresh": 0,
        "last_alarm": 0,
        "missing_data": False
    }

    def verileri_cek():
        """'GÖSTER' butonuna basıldığında çalışır. Verileri çeker, analiz eder ve tabloya yazar."""

        g, a, y = cb_gun.get(), cb_ay.get(), cb_yil.get()
        f_ad = cb_filt.get()
        f_id = scraper.config["filtre_map"].get(f_ad, "500")

        btn_goster_btn.config(state="disabled", text="Yükleniyor...")
        lbl_status.config(text=f"Veri çekiliyor... {g} {a} {y} | Filtre: {f_ad}")
        root.config(cursor="watch")
        pb_loading.pack(side="left", padx=10, pady=2)
        pb_loading.start(15)

        def islem():
            try:
                # 2. Web Sitesinden Verileri İndir
                ham_veriler = scraper.fetch_logs(g, a, y, f_id)

                if not ham_veriler:
                    root.after(0, lambda: lbl_status.config(text="Veri bulunamadı."))
                    root.after(0, lambda: messagebox.showinfo("Bilgi", "Kriterlere uygun veri yok."))
                    return

                # 3. Verileri Analiz Et (Beyin Kısmı)
                grouped_data = process_and_analyze_logs(ham_veriler, robot)

                # 4. Sonuçları Tabloya Yaz (Ortak Fonksiyon)
                root.after(0, lambda: populate_tree(grouped_data))

                # 5. Ekstra Kontroller (Zamanlama Hatası Var mı?)
                # Her türün en son gelen kaydını bul
                son_veriler = {}
                for group in grouped_data:
                    if group['taf']:
                        t = group['taf']
                        if t["type"] not in son_veriler or t["dt"] > son_veriler[t["type"]]["dt"]:
                            son_veriler[t["type"]] = t
                    for obs in group['observations']:
                        if obs["type"] not in son_veriler or obs["dt"] > son_veriler[obs["type"]]["dt"]:
                            son_veriler[obs["type"]] = obs
                
                alarm_tetikle = False
                hatali_bultenler = []
                for typ, item in son_veriler.items():
                    try:
                        kayit_str = item["raw"][3] # Kayıt Tarihi Sütunu
                        k_dt = datetime.strptime(kayit_str.strip(), "%d.%m.%Y %H:%M")
                        if k_dt.minute != 55:
                            msg = f"{typ} -> Kayıt: {k_dt.strftime('%H:%M')}"
                            hatali_bultenler.append(msg)
                            alarm_tetikle = True
                    except: pass
                
                if alarm_tetikle:
                    hata_txt = "Aşağıdaki rasatların kayıt saati :55 geçe değil:\n\n" + "\n".join(hatali_bultenler)
                    root.after(0, lambda: messagebox.showwarning("ZAMANLAMA UYARISI", hata_txt))
                    try:
                        alarm_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarm_kardelen.py")
                        if os.path.exists(alarm_script):
                            kwargs = {
                                "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL
                            }
                            if sys.platform == "win32":
                                kwargs["creationflags"] = 0x08000000
                            subprocess.Popen([sys.executable, alarm_script], **kwargs)
                    except Exception as e:
                        print(f"Alarm tetikleme hatası: {e}")
                # -------------------------------------------------

                # 6. Eksik Veri Kontrolü (Saat başı METAR gelmiş mi?)
                now_utc = datetime.now(timezone.utc)
                if now_utc.minute >= 55:
                    metar_var = False
                    # Tüm gözlemleri düzleştirip kontrol et
                    all_obs = [obs for g in grouped_data for obs in g['observations']]
                    for item in all_obs:
                        if item["type"] in ["METAR", "SPECI"]:
                            # METAR saati şu anki saat ile eşleşiyor mu?
                            # item["dt"] naive datetime (Kardelen'den gelen). UTC kabul ediyoruz.
                            if (item["dt"].year == now_utc.year and 
                                item["dt"].month == now_utc.month and 
                                item["dt"].day == now_utc.day and 
                                item["dt"].hour == now_utc.hour):
                                metar_var = True
                                break
                    
                    app_state["missing_data"] = not metar_var
                else:
                    app_state["missing_data"] = False

                root.after(0, lambda: lbl_status.config(text=f"Toplam {len(ham_veriler)} kayıt bulundu ve analiz edildi."))
            except Exception as e:
                root.after(0, lambda: lbl_status.config(text="Hata oluştu."))
                root.after(0, lambda e=e: messagebox.showerror("Hata", f"İşlem sırasında bir hata oluştu:\n{e}"))
            finally:
                def finalize_ui():
                    root.config(cursor="")
                    pb_loading.stop()
                    pb_loading.pack_forget()
                    btn_goster_btn.config(state="normal", text="GÖSTER")
                root.after(0, finalize_ui)

        threading.Thread(target=islem).start()

    def baslat():
        """Program açılışında siteye bağlanır, ayarları ve filtreleri otomatik yükler."""
        res = scraper.analyze_site()
        if res and scraper.config["ay_map"]:
            aylar = list(scraper.config["ay_map"].keys())
            cb_ay['values'] = aylar
            try: cb_ay.set(aylar[datetime.now().month - 1])
            except: cb_ay.current(0)
            
            filtreler = list(scraper.config["filtre_map"].keys())
            cb_filt['values'] = filtreler
            
            for i, f in enumerate(filtreler):
                if "Tüm" in f or "500" in scraper.config["filtre_map"][f]:
                    cb_filt.current(i)
                    break
            
            # Geçmiş combobox'ı da güncelle
            cb_ay_history['values'] = aylar
            try: cb_ay_history.set(aylar[datetime.now().month - 1])
            except: pass
            else:
                if filtreler: cb_filt.current(0)
                
            lbl_status.config(text="Site analizi tamamlandı. Hazır.")
        else:
            cb_ay['values'] = ["Ocak", "Şubat", "Mart"]
            cb_filt['values'] = ["Tüm Bültenler"]
            lbl_status.config(text="Site analizi başarısız. Manuel mod.")
            
    threading.Thread(target=baslat).start()

    # --- SAAT VE ALARM DÖNGÜSÜ ---
    def update_clock():
        """Her saniye çalışarak saati günceller, alarmları ve otomatik yenilemeyi kontrol eder."""
        now_utc = datetime.now(timezone.utc)
        lbl_clock.config(text=now_utc.strftime("%H:%M:%S Z"))
        
        if var_alarm_active.get():
            current_hm = now_utc.strftime("%H:%M")
            if current_hm == var_alarm_time.get():
                if not var_alarm_triggered.get():
                    var_alarm_triggered.set(True)
                    play_alarm_sound()
                    root.lift()
                    root.attributes('-topmost', True)
                    messagebox.showwarning("RASAT ALARMI", f"Saat {current_hm} UTC oldu!\nRasat zamanı.")
                    root.attributes('-topmost', False)
            else:
                var_alarm_triggered.set(False)
        
        # --- OTO YENİLEME (51-00 arası her dk) ---
        if var_oto_yenile.get():
            if 51 <= now_utc.minute <= 59:
                if time.time() - app_state["last_refresh"] > 60:
                    # Eğer işlem yapmıyorsa (Buton aktifse) yenile
                    if btn_goster_btn['state'] != 'disabled':
                        verileri_cek()
                        app_state["last_refresh"] = time.time()
        
        # --- EKSİK RASAT ALARMI (Her 2 dk) ---
        if app_state["missing_data"]:
            if time.time() - app_state["last_alarm"] > 120: # 2 dakika (120 sn)
                play_alarm_sound()
                app_state["last_alarm"] = time.time()
        
        root.after(1000, update_clock)
    
    update_clock()

    root.mainloop()

if __name__ == "__main__":
    gui_baslat()