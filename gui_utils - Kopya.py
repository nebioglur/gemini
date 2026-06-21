import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import sys
import os
import re
from datetime import datetime, timedelta
import config_manager

def get_resource_path(relative_path):
    """PyInstaller ile oluşturulan EXE ve geliştirme ortamı için kaynak yolu çözücü."""
    try:
        # PyInstaller geçici klasörü (sys._MEIPASS)
        base_path = sys._MEIPASS
    except Exception:
        # Normal çalışma
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class ToolTipManager:
    """Tooltip pencerelerini yöneten sınıf."""
    def __init__(self):
        self.tooltip_window = None
        self.last_tooltip_item = None

    def show_tooltip(self, parent, x, y, text, text_color="#eceff1"):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except: pass
            self.tooltip_window = None

        self.tooltip_window = tk.Toplevel(parent)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.withdraw()
        
        bg_color = "#263238"
        fg_color = text_color
        
        if "UYUMSUZ" in text or "KRİTİK" in text or "YANLIŞ" in text:
            border_color = "#FF5252" # Kırmızı
        elif "DİKKAT" in text:
            border_color = "#FFD700" # Sarı
        elif "UYUMLU" in text:
            border_color = "#69F0AE" # Yeşil
        else:
            border_color = "#80cbc4" # Varsayılan

        frame = tk.Frame(self.tooltip_window, bg=bg_color, highlightbackground=border_color, highlightthickness=2)
        frame.pack(fill="both", expand=True)

        lines = text.split('\n')
        w = min(max([len(line) for line in lines] + [40]), 90) + 2
        h = len(lines) + 2
        
        txt_widget = tk.Text(frame, width=w, height=h, bg=bg_color, fg=fg_color, font=("Consolas", 10), relief="flat", wrap="word")
        txt_widget.pack(padx=10, pady=8)

        txt_widget.tag_config("green", foreground="#00E676")
        txt_widget.tag_config("red", foreground="#FF5252")
        txt_widget.tag_config("yellow", foreground="#FFD700")
        txt_widget.tag_config("gold", foreground="#FFD700")
        txt_widget.tag_config("default", foreground=fg_color)

        for line in lines:
            tag = "default"
            if "✅" in line or "UYUMLU" in line: tag = "green"
            elif "❌" in line or "UYUMSUZ" in line: tag = "red"
            elif "⚠️" in line or "DİKKAT" in line: tag = "yellow"
            elif "💡 TAVSİYE" in line: tag = "gold"
            txt_widget.insert("end", line + "\n", tag)

        txt_widget.config(state="disabled")

        self.tooltip_window.update_idletasks()
        width = self.tooltip_window.winfo_reqwidth()
        height = self.tooltip_window.winfo_reqheight()

        pos_x = x + 15
        pos_y = y + 10
        if pos_x + width > self.tooltip_window.winfo_screenwidth(): pos_x = x - width - 15
        if pos_y + height > self.tooltip_window.winfo_screenheight(): pos_y = y - height - 10
        if pos_x < 0: pos_x = 0
        if pos_y < 0: pos_y = 0

        self.tooltip_window.wm_geometry(f"+{pos_x}+{pos_y}")
        self.tooltip_window.deiconify()

    def hide_tooltip(self):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except: pass
            self.tooltip_window = None
        self.last_tooltip_item = None

def show_auto_close_info(parent, title, message, duration=5000):
    """Belirtilen süre sonunda otomatik kapanan, çerçevesiz bilgi penceresi."""
    try:
        top = tk.Toplevel(parent)
        top.overrideredirect(True)  # Pencere kenarlıklarını kaldır
        top.configure(bg="#263238")
        
        frame = tk.Frame(top, bg="#263238", highlightbackground="#00E676", highlightthickness=2)
        frame.pack(fill="both", expand=True)
        
        tk.Label(frame, text=title, bg="#263238", fg="#00E676", font=("Segoe UI", 11, "bold")).pack(pady=(15, 5))
        tk.Label(frame, text=message, bg="#263238", fg="white", font=("Segoe UI", 10)).pack(pady=5, padx=20)
        
        top.update_idletasks()
        w = top.winfo_reqwidth()
        h = top.winfo_reqheight()
        
        try:
            # Parent pencerenin ortasına konumlandır
            x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (w // 2)
            y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (h // 2)
        except:
            x = (top.winfo_screenwidth() // 2) - (w // 2)
            y = (top.winfo_screenheight() // 2) - (h // 2)
            
        top.geometry(f"{w}x{h}+{x}+{y}")
        
        def safe_destroy():
            try: top.destroy()
            except: pass
            
        top.after(duration, safe_destroy)
    except: pass

def show_detail_window(parent, station, date, metar_text, taf_text, analysis_detail, fm_start_idx, metar_dt, robot_instance):
    """Detaylı analiz penceresini açar ve renklendirmeleri yapar."""
    
    # Varsayılan Renkler
    DEFAULT_COLORS = {
        "detail_bg": "#2b2b2b",
        "detail_fg": "white",
        "detail_txt_bg": "#1e1e1e",
        "detail_header_col": "#aaaaaa",
        "detail_metar_col": "#4FC3F7",
        "detail_taf_col": "#78909C",
        "detail_success_col": "#69F0AE",
        "detail_error_col": "#FF5252",
        "detail_warning_col": "#FFD700"
    }

    # Renk Ayarlarını Yükle
    cfg = config_manager.load_config()
    
    # Mevcut renkleri belirle (Config yoksa varsayılanı kullan)
    current_colors = {}
    for k, v in DEFAULT_COLORS.items():
        current_colors[k] = cfg.get(k, v)

    bg_col = current_colors["detail_bg"]
    fg_col = current_colors["detail_fg"]
    txt_bg_col = current_colors["detail_txt_bg"]

    top = tk.Toplevel(parent)
    top.title(f"Detaylı Analiz: {date}")
    top.geometry("1000x700")
    top.configure(bg=bg_col)
    
    # Başlık
    lbl_header = tk.Label(top, text=f"İSTASYON: {station} | TARİH: {date}", 
                          bg=bg_col, fg=fg_col, font=("Calibri", 14, "bold"))
    lbl_header.pack(pady=10)

    # Butonlar
    btn_frame = tk.Frame(top, bg=bg_col)
    btn_frame.pack(fill="x", padx=10)

    # Ana İçerik Alanı
    main_frame = tk.Frame(top, bg=bg_col)
    main_frame.pack(fill="both", expand=True, padx=10, pady=5)

    sb = tk.Scrollbar(main_frame)
    txt_display = tk.Text(main_frame, font=("Calibri", 12), wrap="word", 
                          bg=txt_bg_col, fg=fg_col, insertbackground=fg_col,
                          yscrollcommand=sb.set)

    sb.pack(side="right", fill="y")
    txt_display.pack(side="left", fill="both", expand=True)
    sb.config(command=txt_display.yview)

    def copy_content():
        try:
            content = txt_display.get("1.0", tk.END)
            parent.clipboard_clear()
            parent.clipboard_append(content)
            show_auto_close_info(top, "BİLGİ", "İçerik panoya kopyalandı.", 2000)
        except: pass

    tk.Button(btn_frame, text="📋 Metni Kopyala", command=copy_content, 
              bg="#90A4AE", fg="black", font=("Segoe UI", 9, "bold")).pack(side="right")

    # --- RENK AYARLARI BUTONU VE FONKSİYONU ---
    def open_color_settings():
        col_win = tk.Toplevel(top)
        col_win.title("Renk Ayarları")
        
        # Pencereyi Ortala
        w, h = 360, 650
        top.update_idletasks()
        x = top.winfo_x() + (top.winfo_width() // 2) - (w // 2)
        y = top.winfo_y() + (top.winfo_height() // 2) - (h // 2)
        col_win.geometry(f"{w}x{h}+{x}+{y}")
        
        # Mevcut arka plan rengini al
        current_bg = cfg.get("detail_bg", DEFAULT_COLORS["detail_bg"])
        col_win.configure(bg=current_bg)
        
        def update_col_win_widgets(bg_c):
            """Renk ayarları penceresindeki etiketlerin arka planını günceller."""
            col_win.configure(bg=bg_c)
            for widget in col_win.winfo_children():
                if isinstance(widget, (tk.Label, tk.Frame)):
                    try: widget.configure(bg=bg_c)
                    except: pass
        
        def pick_color(key, title, tag_name=None, widget_type=None):
            """Renk seçiciyi açar ve ilgili ayarı günceller."""
            current_val = cfg.get(key, DEFAULT_COLORS[key])
            c = colorchooser.askcolor(title=title, initialcolor=current_val)[1]
            
            if c:
                cfg[key] = c
                config_manager.save_config(cfg)
                
                # Anlık Arayüz Güncellemesi
                if key == "detail_bg":
                    top.configure(bg=c)
                    lbl_header.configure(bg=c)
                    btn_frame.configure(bg=c)
                    main_frame.configure(bg=c)
                    update_col_win_widgets(c)
                elif key == "detail_txt_bg":
                    txt_display.configure(bg=c)
                elif key == "detail_fg":
                    lbl_header.configure(fg=c)
                    txt_display.configure(fg=c)
                    txt_display.tag_config("default", foreground=c)
                
                # Tag Güncellemeleri
                if tag_name:
                    if isinstance(tag_name, list):
                        for t in tag_name: txt_display.tag_config(t, foreground=c)
                    else:
                        txt_display.tag_config(tag_name, foreground=c)

        # Buton Oluşturucu
        def create_btn(txt, key, tag=None, w_type=None):
            tk.Button(col_win, text=txt, width=30, bg="#CFD8DC", 
                      command=lambda: pick_color(key, txt, tag, w_type)).pack(pady=5)

        tk.Label(col_win, text="GENEL GÖRÜNÜM", bg=current_bg, fg="white", font=("Segoe UI", 9, "bold")).pack(pady=(10,5))
        create_btn("Pencere Arka Planı", "detail_bg")
        create_btn("Metin Kutusu Arka Planı", "detail_txt_bg")
        create_btn("Genel Yazı Rengi", "detail_fg")
        
        tk.Label(col_win, text="METİN RENKLERİ", bg=current_bg, fg="white", font=("Segoe UI", 9, "bold")).pack(pady=(10,5))
        create_btn("Başlıklar (Header)", "detail_header_col", ["header", "section_header"])
        create_btn("METAR Metni", "detail_metar_col", "metar")
        create_btn("TAF Metni", "detail_taf_col", "taf")
        create_btn("Başarılı / Uyumlu (Yeşil)", "detail_success_col", "green")
        create_btn("Hata / Uyumsuz (Kırmızı)", "detail_error_col", ["red", "comp_red"])
        create_btn("Uyarı / Dikkat (Sarı)", "detail_warning_col", ["yellow", "limit_msg"])

        def apply_theme_colors(target_colors):
            """Verilen renk temasını uygular."""
            for k, v in target_colors.items():
                cfg[k] = v
            config_manager.save_config(cfg)
            
            # Arayüzü Güncelle
            bg = target_colors["detail_bg"]
            fg = target_colors["detail_fg"]
            txt_bg = target_colors["detail_txt_bg"]
            
            top.configure(bg=bg)
            lbl_header.configure(bg=bg, fg=fg)
            btn_frame.configure(bg=bg)
            main_frame.configure(bg=bg)
            txt_display.configure(bg=txt_bg, fg=fg)
            
            update_col_win_widgets(bg)
            
            # Tagları Güncelle
            tag_map = { 
                "header": "detail_header_col", "section_header": "detail_header_col", 
                "metar": "detail_metar_col", "taf": "detail_taf_col", 
                "green": "detail_success_col", "red": "detail_error_col", 
                "comp_red": "detail_error_col", "yellow": "detail_warning_col", 
                "limit_msg": "detail_warning_col", "default": "detail_fg" 
            }
            for tag, key in tag_map.items():
                txt_display.tag_config(tag, foreground=target_colors[key])

        tk.Label(col_win, text="HAZIR TEMALAR (RENK UYUMU)", bg=current_bg, fg="white", font=("Segoe UI", 9, "bold")).pack(pady=(15,5))
        
        f_themes = tk.Frame(col_win, bg=current_bg)
        f_themes.pack()
        
        tk.Button(f_themes, text="🌙 KOYU TEMA", command=lambda: apply_theme_colors(DEFAULT_COLORS), bg="#455A64", fg="white", width=15).pack(side="left", padx=5)
        
        LIGHT_COLORS = {
            "detail_bg": "#f0f0f0", "detail_fg": "black", "detail_txt_bg": "#ffffff",
            "detail_header_col": "#555555", "detail_metar_col": "#0277BD", "detail_taf_col": "#455A64",
            "detail_success_col": "#2E7D32", "detail_error_col": "#D32F2F", "detail_warning_col": "#F57F17"
        }
        tk.Button(f_themes, text="☀️ AÇIK TEMA", command=lambda: apply_theme_colors(LIGHT_COLORS), bg="#E0E0E0", fg="black", width=15).pack(side="left", padx=5)

        tk.Button(col_win, text="♻️ VARSAYILANLARA DÖN", command=lambda: apply_theme_colors(DEFAULT_COLORS), bg="#FF5252", fg="white", font=("Segoe UI", 9, "bold"), width=30).pack(pady=20)

    tk.Button(btn_frame, text="🎨 Renk Ayarları", command=open_color_settings, 
              bg="#607D8B", fg="white", font=("Segoe UI", 9, "bold")).pack(side="right", padx=5)

    # Tag configurations
    txt_display.tag_config("header", foreground=current_colors["detail_header_col"], font=("Calibri", 11, "bold"))
    txt_display.tag_config("metar", foreground=current_colors["detail_metar_col"], font=("Calibri", 14, "bold"))
    txt_display.tag_config("taf", foreground=current_colors["detail_taf_col"], font=("Calibri", 14, "bold"))
    txt_display.tag_config("green", foreground=current_colors["detail_success_col"])
    txt_display.tag_config("red", foreground=current_colors["detail_error_col"])
    txt_display.tag_config("yellow", foreground=current_colors["detail_warning_col"])
    txt_display.tag_config("default", foreground=fg_col)
    txt_display.tag_config("highlight", background="#FFEB3B", foreground="black")
    txt_display.tag_config("threshold", foreground="#00E676", background="white", font=("Calibri", 12, "bold"))
    txt_display.tag_config("limit_msg", foreground=current_colors["detail_warning_col"], font=("Calibri", 12, "bold"))
    txt_display.tag_config("threshold_orange", background="#FF9800", foreground="black", font=("Calibri", 12, "bold"))
    txt_display.tag_config("comp_red", foreground=current_colors["detail_error_col"], font=("Calibri", 12, "bold"))
    txt_display.tag_config("section_header", foreground=current_colors["detail_header_col"], font=("Calibri", 14, "bold"))
    txt_display.tag_config("gold", foreground="#FFD700", font=("Calibri", 12, "bold"))
    txt_display.tag_config("active_period", foreground="#4FC3F7", font=("Calibri", 14, "bold"))
    txt_display.tag_config("tag_becmg", foreground="#66BB6A", font=("Calibri", 14, "bold"))
    txt_display.tag_config("tag_tempo", foreground="#66BB6A", font=("Calibri", 14, "bold"))
    txt_display.tag_config("tag_fm", foreground="#AB47BC", font=("Calibri", 14, "bold"))

    if metar_text:
        txt_display.insert("end", "METAR / SPECI:\n", "header")
        txt_display.insert("end", f"{metar_text}\n\n", "metar")

    txt_display.insert("end", "REFERANS TAF:\n", "header")
    # YENİ: Bültenden sonra gelen istenmeyen verileri temizle
    clean_taf_text = taf_text.split('=')[0] + '=' if taf_text and '=' in taf_text else taf_text
    taf_display_text = clean_taf_text if clean_taf_text else "Uygun TAF bulunamadı."
    taf_start_mark = txt_display.index("insert")
    txt_display.insert("end", f"{taf_display_text}\n\n", "taf")

    if taf_text:
        try:
            # Highlight active period
            relevant_text = clean_taf_text[fm_start_idx:]
            token_pattern = re.compile(r'(BECMG|PROB\d{2}\s+TEMPO|TEMPO|PROB\d{2}|FM\d{6})')
            matches = list(token_pattern.finditer(relevant_text))

            first_trend_start = matches[0].start() if matches else len(relevant_text)
            
            # Ana gövdeyi (ilk trende kadar) işaretle
            s_pos = f"{taf_start_mark}+{fm_start_idx}c"
            e_pos = f"{taf_start_mark}+{fm_start_idx + first_trend_start}c"
            txt_display.tag_add("active_period", s_pos, e_pos)

            # METAR zaman kodunu metinden çek (En güvenli yöntem)
            m_match = re.search(r'\b\d{6}Z\b', metar_text)
            if m_match:
                m_code = m_match.group(0)
            else:
                m_code = metar_dt.strftime("%d%H%MZ") if metar_dt and getattr(metar_dt, 'year', 0) > 1900 else "000000Z"
            
            for i, m in enumerate(matches):
                trend_type = m.group(1)
                t_start = m.start()
                t_end = matches[i+1].start() if i+1 < len(matches) else len(relevant_text)
                chunk = relevant_text[t_start:t_end]

                is_active = False
                if trend_type.startswith("FM"):
                    res = robot_instance._is_trend_active(trend_type[2:], m_code, trend_type, ref_date=metar_dt)
                    is_active = res[0] if isinstance(res, tuple) else res
                else:
                    time_match = re.search(r'\b(\d{4}/\d{4})\b', chunk)
                    if time_match:
                        res = robot_instance._is_trend_active(time_match.group(1), m_code, trend_type, ref_date=metar_dt)
                        is_active = res[0] if isinstance(res, tuple) else res

                if is_active:
                    txt_display.tag_add("active_period", f"{taf_start_mark}+{fm_start_idx + t_start}c", f"{taf_start_mark}+{fm_start_idx + t_end}c")
        except Exception as e: print(f"Highlight error: {e}")

    txt_display.insert("end", "-"*60 + "\n", "header")
    txt_display.insert("end", "ANALİZ DETAYI:\n", "header")

    for line in analysis_detail.split('\n'):
        tag = "default"
        if line.strip().startswith(("1.", "2.", "3.", "4.", "• 1.", "• 2.", "• 3.", "• 4.")): tag = "section_header"
        elif "FORMAT HATASI" in line: tag = "comp_red"
        elif "KURALLAR" in line: tag = "section_header"
        elif "✅" in line or "UYUMLU" in line: tag = "green"
        elif "❌" in line or "UYUMSUZ" in line: tag = "red"
        elif "⚠️" in line or "DİKKAT" in line: tag = "yellow"
        elif "💡 TAVSİYE" in line: tag = "gold"
        
        # YENİ: GEÇMİŞ HADİSE KURALI için özel ayrıştırma
        if "[GEÇMİŞ HADİSE KURALI]" in line:
            core_message = line.split("[GEÇMİŞ HADİSE KURALI]")[1].strip()
            
            prev_obs_text = ""
            if "[Önceki Rasat:" in core_message:
                parts = core_message.split("[Önceki Rasat:")
                core_message = parts[0].strip()
                prev_obs_text = parts[1].replace("]", "").strip()

            txt_display.insert("end", "• ", tag)
            txt_display.insert("end", "GEÇMİŞ HADİSE (RE) HATASI:\n", "comp_red")
            txt_display.insert("end", f"     - Açıklama: {core_message}\n", "default")
            
            if prev_obs_text:
                txt_display.insert("end", f"     - Önceki Bülten:\n", "default")
                txt_display.insert("end", f"       {prev_obs_text}\n", "metar")
        else:
            txt_display.insert("end", f"{line}\n", tag)

    # --- ÖZEL RENKLENDİRMELER (Regex ile sonradan uygula) ---
    
    # 1. "Görüş/Tavan değişimi limit dışı" -> SARI KALIN
    for pattern in [r'Görüş değişimi limit dışı', r'Tavan değişimi limit dışı', r'Rüzgar .*? farkı']:
        start = "1.0"
        while True:
            count = tk.IntVar()
            pos = txt_display.search(pattern, start, stopindex=tk.END, regexp=True, count=count)
            if not pos: break
            txt_display.tag_add("limit_msg", pos, f"{pos}+{count.get()}c")
            start = f"{pos}+{count.get()}c"

    # 2. [Eşik:...] -> TURUNCU HIGHLIGHT
    start = "1.0"
    while True:
        count = tk.IntVar()
        pos = txt_display.search(r'\[Eşik:.*?\]', start, stopindex=tk.END, regexp=True, count=count)
        if not pos: break
        txt_display.tag_add("threshold_orange", pos, f"{pos}+{count.get()}c")
        start = f"{pos}+{count.get()}c"

    # 3. (TAF:... vs METAR:...) -> KALIN KIRMIZI BÜYÜK
    start = "1.0"
    while True:
        count = tk.IntVar()
        pos = txt_display.search(r'\(TAF:.*? vs METAR:.*?\)', start, stopindex=tk.END, regexp=True, count=count)
        if not pos: break
        txt_display.tag_add("comp_red", pos, f"{pos}+{count.get()}c")
        start = f"{pos}+{count.get()}c"

    # 4. [İyileşme:...] -> YEŞİL KALIN
    start = "1.0"
    while True:
        count = tk.IntVar()
        pos = txt_display.search(r'\[İyileşme:.*?\]', start, stopindex=tk.END, regexp=True, count=count)
        if not pos: break
        txt_display.tag_add("improvement", pos, f"{pos}+{count.get()}c")
        start = f"{pos}+{count.get()}c"

    # BECMG, TEMPO ve FM Gruplarını Renklendir
    for kw, tag in [("BECMG", "tag_becmg"), ("TEMPO", "tag_tempo"), ("PROB30", "tag_tempo"), ("PROB40", "tag_tempo")]:
        start = "1.0"
        while True:
            pos = txt_display.search(kw, start, stopindex=tk.END)
            if not pos: break
            end = f"{pos}+{len(kw)}c"
            txt_display.tag_add(tag, pos, end)
            start = end
    
    start = "1.0"
    while True:
        count = tk.IntVar()
        pos = txt_display.search(r'FM\d{6}', start, stopindex=tk.END, regexp=True, count=count)
        if not pos: break
        end = f"{pos}+{count.get()}c"
        txt_display.tag_add("tag_fm", pos, end)
        start = end

    txt_display.tag_raise("active_period")
    txt_display.tag_raise("tag_becmg")
    txt_display.tag_raise("tag_tempo")
    txt_display.tag_raise("tag_fm")

    txt_display.config(state="disabled")

def show_bottom_right_popup(parent, title, message, duration=5000):
    """Sağ alt köşede otomatik kapanan bildirim penceresi gösterir."""
    try:
        top = tk.Toplevel(parent)
        top.overrideredirect(True)
        top.attributes('-topmost', True)
        top.configure(bg="#263238", highlightbackground="#00E676", highlightthickness=1)
        
        # Sol şerit (Görsellik)
        canvas = tk.Canvas(top, width=6, bg="#00E676", highlightthickness=0)
        canvas.pack(side="left", fill="y")
        
        content_frame = tk.Frame(top, bg="#263238", padx=15, pady=10)
        content_frame.pack(side="left", fill="both", expand=True)
        
        tk.Label(content_frame, text=title, bg="#263238", fg="#00E676", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(content_frame, text=message, bg="#263238", fg="white", font=("Segoe UI", 12, "bold"), justify="left").pack(anchor="w", pady=(2, 0))
        
        top.update_idletasks()
        w = top.winfo_reqwidth()
        h = top.winfo_reqheight()
        
        sw = top.winfo_screenwidth()
        sh = top.winfo_screenheight()
        
        x = sw - w - 20
        y = sh - h - 60
        
        top.geometry(f"{w}x{h}+{x}+{y}")
        
        # Fade-in
        top.attributes('-alpha', 0.0)
        def fade_in(alpha):
            if alpha < 0.95:
                alpha += 0.1
                top.attributes('-alpha', alpha)
                top.after(30, lambda: fade_in(alpha))
            else:
                top.attributes('-alpha', 0.95)
        fade_in(0)

        def close_popup(e=None):
            try: top.destroy()
            except: pass

        top.after(duration, close_popup)
        
        top.bind("<Button-1>", close_popup)
        content_frame.bind("<Button-1>", close_popup)
        for child in content_frame.winfo_children():
            child.bind("<Button-1>", close_popup)
            
    except: pass