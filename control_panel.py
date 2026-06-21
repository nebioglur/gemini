import tkinter as tk
from tkinter import ttk
from datetime import datetime, timezone

class ToolTip(object):
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 1
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                       background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                       font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

    def enter(self, event=None):
        self.id = self.widget.after(500, lambda: self.showtip(self.text))

    def leave(self, event=None):
        if self.id: self.widget.after_cancel(self.id)
        self.hidetip()

def create_tooltip(widget, text):
    toolTip = ToolTip(widget, text)
    widget.bind('<Enter>', toolTip.enter)
    widget.bind('<Leave>', toolTip.leave)

def create_control_panel(parent, callbacks, vars, station_data, config_data):
    """
    Kontrol panelini (Tarih, Filtre, İstasyon, Harita, Ayarlar, Listele, Geçmiş) oluşturur.
    Oluşturulan widget'ları bir sözlük olarak döndürür.
    """
    # Ana Panel (Toolbar Görünümü - Profesyonel Gri)
    panel = tk.Frame(parent, bg="#ECEFF1", pady=2, padx=2)
    panel.pack(fill="x")
    
    widgets = {}
    now = datetime.now(timezone.utc)
    mb_hist_filter = None # Placeholder for history filter button
    
    # Stil Ayarları
    style = ttk.Style()
    style.configure("CP.TCombobox", padding=2)

    # --- SOL TARA (VERİ SEÇİMİ) ---
    fr_left = tk.Frame(panel, bg="#ECEFF1")
    fr_left.pack(side="left", fill="y", padx=2)

    # 1. TARİH & BÜLTEN (Birleşik Grup)
    fr_data_select = tk.LabelFrame(fr_left, text="Veri Seçimi", font=("Segoe UI", 8, "bold"), bg="#ECEFF1", fg="#455A64", padx=2, pady=2)
    fr_data_select.pack(side="left", padx=2, fill="y")
    
    # Grid Layout
    fr_data_select.columnconfigure(0, weight=1)
    
    # Tarih Satırı
    f_date_row = tk.Frame(fr_data_select, bg="#ECEFF1")
    f_date_row.grid(row=0, column=0, sticky="ew", pady=(0, 2))
    
    cb_gun = ttk.Combobox(f_date_row, values=[str(i).zfill(2) for i in range(1,32)], width=3, style="CP.TCombobox")
    cb_gun.set(str(now.day).zfill(2))
    cb_gun.pack(side="left", padx=(0, 2))
    widgets['cb_gun'] = cb_gun
    
    # Bitiş günü gizli
    cb_gun_bit = ttk.Combobox(panel, values=[str(i).zfill(2) for i in range(1,32)], width=3)
    cb_gun_bit.set(str(now.day).zfill(2))
    widgets['cb_gun_bit'] = cb_gun_bit
    cb_gun.bind("<<ComboboxSelected>>", lambda e: cb_gun_bit.set(cb_gun.get()))
    
    cb_ay = ttk.Combobox(f_date_row, values=config_data.get('months', []), width=10, style="CP.TCombobox")
    cb_ay.pack(side="left", padx=2)
    widgets['cb_ay'] = cb_ay
    
    cb_yil = ttk.Combobox(f_date_row, values=[str(i) for i in range(2020, 2031)], width=5, style="CP.TCombobox")
    cb_yil.set(str(now.year))
    cb_yil.pack(side="left", padx=2)
    widgets['cb_yil'] = cb_yil

    # Bülten Tipi Satırı
    cb_filt = ttk.Combobox(fr_data_select, values=config_data.get('filters', []), width=18, style="CP.TCombobox", state="readonly")
    cb_filt.grid(row=1, column=0, sticky="ew")
    widgets['cb_filt'] = cb_filt

    # 2. İSTASYON SEÇİMİ
    fr_station = tk.LabelFrame(fr_left, text="İstasyon", font=("Segoe UI", 8, "bold"), bg="#ECEFF1", fg="#455A64", padx=2, pady=2)
    fr_station.pack(side="left", padx=2, fill="y")

    # Üst Satır: Combobox ve Yenile
    f_st_top = tk.Frame(fr_station, bg="#ECEFF1")
    f_st_top.pack(fill="x", pady=1)
    
    cb_ist = ttk.Combobox(f_st_top, values=station_data.get("TÜMÜ", []), width=20, style="CP.TCombobox")
    cb_ist.pack(side="left", padx=1)
    widgets['cb_ist'] = cb_ist
    
    # Varsayılan seçim
    default_st = next((s for s in station_data.get("TÜMÜ", []) if "17244" in s), "")
    cb_ist.set(default_st)
    
    btn_refresh = tk.Button(f_st_top, text="🔄", command=callbacks.get('update_station_list_ui'), 
                            bg="#CFD8DC", relief="flat", font=("Segoe UI", 8), width=3)
    btn_refresh.pack(side="left", padx=1)
    widgets['btn_refresh_ist'] = btn_refresh

    # Alt Satır: Manuel Giriş
    f_st_bot = tk.Frame(fr_station, bg="#ECEFF1")
    f_st_bot.pack(fill="x", pady=1)
    
    def validate_input(P):
        if P == "" or P.isalnum(): return True
        return False
    vcmd = (fr_station.register(validate_input), '%P')
    
    ent_manual_st = tk.Entry(f_st_bot, width=10, validate="key", validatecommand=vcmd, font=("Consolas", 9))
    ent_manual_st.pack(side="left", padx=1)
    widgets['ent_manual_st'] = ent_manual_st
    
    def on_manual_show(event=None):
        st_id = ent_manual_st.get()
        if st_id and callbacks.get('on_manual_station_search'):
            callbacks['on_manual_station_search'](st_id)

    ent_manual_st.bind("<Return>", on_manual_show)
    
    btn_manual_show = tk.Button(f_st_bot, text="ARA", command=on_manual_show, 
                                bg="#B0BEC5", relief="flat", font=("Segoe UI", 7, "bold"), width=6)
    btn_manual_show.pack(side="left", padx=1)
    widgets['btn_manual_show'] = btn_manual_show
    
    btn_list = tk.Button(f_st_bot, text="LİSTE", command=callbacks.get('open_station_table'), 
                         bg="#90A4AE", relief="flat", font=("Segoe UI", 7, "bold"), width=6)
    btn_list.pack(side="left", padx=1)
    widgets['btn_list'] = btn_list

    # Gizli comboboxlar (Kod uyumluluğu için)
    widgets['cb_meydan'] = ttk.Combobox(panel) 
    widgets['cb_sinoptik'] = ttk.Combobox(panel)

    # --- ORTA (AKSİYONLAR) ---
    fr_center = tk.Frame(panel, bg="#ECEFF1")
    fr_center.pack(side="left", fill="y", padx=2)
    
    # Büyük Göster Butonu
    btn_goster = tk.Button(fr_center, text="GÖSTER", command=callbacks.get('verileri_cek'), 
                           bg="#2E7D32", fg="white", font=("Segoe UI", 10, "bold"), 
                           width=12, height=2, relief="flat", cursor="hand2")
    btn_goster.pack(side="left", padx=2)
    widgets['btn_goster_btn'] = btn_goster
    
    # Diğer Aksiyonlar (Dikey)
    fr_actions = tk.Frame(fr_center, bg="#ECEFF1")
    fr_actions.pack(side="left", padx=2)
    
    btn_map = tk.Button(fr_actions, text="🗺️ HARİTA", command=callbacks.get('open_map_window'), 
                        bg="#0277BD", fg="white", font=("Segoe UI", 8, "bold"), width=11, relief="flat")
    btn_map.grid(row=0, column=0, padx=1, pady=1)

    btn_live_data = tk.Button(fr_actions, text="📡 CANLI VERİ", command=callbacks.get('open_web_radar'), 
                        bg="#F57C00", fg="white", font=("Segoe UI", 8, "bold"), width=11, relief="flat")
    btn_live_data.grid(row=1, column=0, padx=1, pady=1)

    btn_sinoptik = tk.Button(fr_actions, text="📊 SİNOPTİK", command=callbacks.get('open_sinoptik_rapor'), 
                             bg="#8E24AA", fg="white", font=("Segoe UI", 8, "bold"), width=11, relief="flat")
    btn_sinoptik.grid(row=0, column=1, rowspan=2, sticky="ns", padx=1, pady=1)
    widgets['btn_sinoptik'] = btn_sinoptik

    # --- SAĞ (GÖRÜNÜM VE GEÇMİŞ) ---
    fr_right = tk.Frame(panel, bg="#ECEFF1")
    fr_right.pack(side="right", fill="y", padx=2)

    # GÖRÜNÜM (YENİ)
    fr_view = tk.LabelFrame(fr_right, text="Görünüm", font=("Segoe UI", 8, "bold"), bg="#ECEFF1", fg="#455A64", padx=2, pady=2)
    fr_view.pack(side="left", fill="y", padx=2)
    
    chk_oto = tk.Checkbutton(fr_view, text="Oto", variable=vars['var_oto_yenile'], bg="#ECEFF1", font=("Segoe UI", 7))
    chk_oto.pack(side="left", padx=2)
    widgets['chk_oto'] = chk_oto

    tk.Checkbutton(fr_view, text="İpucu", variable=vars['var_tooltip_aktif'], bg="#ECEFF1", font=("Segoe UI", 7)).pack(side="left", padx=2)
    tk.Checkbutton(fr_view, text="Uyum", variable=vars['var_uyum_show'], command=callbacks.get('toggle_uyum_col'), bg="#ECEFF1", font=("Segoe UI", 7)).pack(side="left", padx=2)
    tk.Checkbutton(fr_view, text="Eski", variable=vars['var_show_old_versions'], command=callbacks.get('toggle_old_versions'), bg="#ECEFF1", font=("Segoe UI", 7)).pack(side="left", padx=2)
    tk.Checkbutton(fr_view, text="Harici", variable=vars['var_show_other_obs'], command=callbacks.get('toggle_other_obs'), bg="#ECEFF1", font=("Segoe UI", 7)).pack(side="left", padx=2)

    # 1. ANA FİLTRE VE İSTATİSTİK (Panelde Görünen Kısım)
    fr_main_stats = tk.LabelFrame(fr_right, text="İstatistik & Filtre", font=("Segoe UI", 8, "bold"), bg="#ECEFF1", fg="#455A64", padx=2, pady=2)
    fr_main_stats.pack(side="left", fill="y", padx=2)
    
    # Gizli Combobox (Logic uyumluluğu için)
    cb_trend_filtre = ttk.Combobox(fr_main_stats, values=["HEPSİ", "UYUMSUZ", "F/UYUMSUZ", "UYUMSUZ (RÜZGAR)", "UYUMSUZ (GÖRÜŞ)", "UYUMSUZ (HADİSE)", "UYUMSUZ (TAVAN)", "RE/GEÇMİŞ HATASI", "DİKKAT", "UYUMLU", "RASAT YOK", "GEÇ GELEN", "HARİCİ RASATLAR"], width=0, state="readonly")
    cb_trend_filtre.set("HEPSİ")
    widgets['cb_trend_filtre'] = cb_trend_filtre

    # --- TEK MENÜ BUTONU (FİLTRELEME) ---
    mb_filter = tk.Menubutton(fr_main_stats, text="HEPSİ", bg="#546E7A", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", width=15)

    def set_filter(val):
        cb_trend_filtre.set(val)
        mb_filter.config(text=val)
        
        # Buton rengini duruma göre güncelle
        bg_col = "#546E7A"
        if "UYUMSUZ" in val: bg_col = "#D32F2F"
        elif "DİKKAT" in val: bg_col = "#F57F17"
        elif "UYUMLU" in val: bg_col = "#388E3C"
        elif "RE/" in val: bg_col = "#4CAF50"
        elif "GEÇ GELEN" in val: bg_col = "#E91E63"
        elif "HARİCİ" in val: bg_col = "#607D8B"
        elif "RASAT YOK" in val: bg_col = "#5D4037"
        mb_filter.config(bg=bg_col)
        if callbacks.get('on_trend_filter_change'):
            callbacks['on_trend_filter_change'](None)

    menu_filter = tk.Menu(mb_filter, tearoff=0)
    mb_filter.config(menu=menu_filter)
    mb_filter.pack(fill="x", pady=2)
    widgets['menu_filter'] = menu_filter
    widgets['mb_filter'] = mb_filter

    # 1. HEPSİ
    menu_filter.add_command(label="TÜMÜNÜ GÖSTER", command=lambda: set_filter("HEPSİ"))
    menu_filter.add_separator()

    # 2. TREND UYUM
    menu_trend = tk.Menu(menu_filter, tearoff=0)
    widgets['menu_trend'] = menu_trend
    menu_filter.add_cascade(label="TREND UYUM DURUMU", menu=menu_trend)
    trend_opts = ["UYUMLU", "UYUMSUZ", "F/UYUMSUZ", "RE/GEÇMİŞ HATASI", "DİKKAT", "UYUMSUZ (RÜZGAR)", "UYUMSUZ (GÖRÜŞ)", "UYUMSUZ (HADİSE)", "UYUMSUZ (TAVAN)"]
    for opt in trend_opts:
        menu_trend.add_command(label=opt, command=lambda o=opt: set_filter(o))

    # 3. GEÇ GELEN
    menu_gec = tk.Menu(menu_filter, tearoff=0)
    widgets['menu_gec'] = menu_gec
    menu_filter.add_cascade(label="GEÇ GELEN RASATLAR", menu=menu_gec)
    menu_gec.add_command(label="HEPSİ", command=lambda: set_filter("GEÇ GELEN"))
    menu_gec.add_command(label="METAR", command=lambda: set_filter("GEÇ GELEN METAR"))
    menu_gec.add_command(label="TAF", command=lambda: set_filter("GEÇ GELEN TAF"))
    menu_gec.add_command(label="SİNOPTİK", command=lambda: set_filter("GEÇ GELEN SİNOPTİK"))

    # 4. RASAT YOK
    menu_filter.add_command(label="RASAT YOK", command=lambda: set_filter("RASAT YOK"))
    menu_filter.add_separator()
    # 5. HARİCİ RASATLAR
    menu_filter.add_command(label="HARİCİ RASATLAR", command=lambda: set_filter("HARİCİ RASATLAR"))
    
    # İstatistik Paneli (Renkli)
    fr_summary = tk.Frame(fr_main_stats, bg="#ECEFF1")
    fr_summary.pack(pady=1, fill="x")
    
    lbl_uyumsuz = tk.Label(fr_summary, text="❌ 0", font=("Segoe UI", 11, "bold"), fg="#D32F2F", bg="#ECEFF1", cursor="hand2")
    lbl_uyumsuz.pack(side="left", padx=2)
    lbl_uyumsuz.bind("<Button-1>", lambda e: set_filter("UYUMSUZ"))
    create_tooltip(lbl_uyumsuz, "UYUMSUZ: Limit dışı veya hatalı rasatlar")
    
    lbl_dikkat = tk.Label(fr_summary, text="⚠️ 0", font=("Segoe UI", 11, "bold"), fg="#F57F17", bg="#ECEFF1", cursor="hand2")
    lbl_dikkat.pack(side="left", padx=2)
    lbl_dikkat.bind("<Button-1>", lambda e: set_filter("DİKKAT"))
    create_tooltip(lbl_dikkat, "DİKKAT: Trend ile uyumlu veya sınırda olanlar")
    
    lbl_uyumlu = tk.Label(fr_summary, text="✅ 0", font=("Segoe UI", 11, "bold"), fg="#388E3C", bg="#ECEFF1", cursor="hand2")
    lbl_uyumlu.pack(side="left", padx=2)
    lbl_uyumlu.bind("<Button-1>", lambda e: set_filter("UYUMLU"))
    create_tooltip(lbl_uyumlu, "UYUMLU: Limit içi ve sorunsuz rasatlar")
    
    lbl_re = tk.Label(fr_summary, text="RE 0", font=("Segoe UI", 11, "bold"), fg="#4CAF50", bg="#ECEFF1", cursor="hand2")
    lbl_re.pack(side="left", padx=2)
    lbl_re.bind("<Button-1>", lambda e: set_filter("RE/GEÇMİŞ HATASI"))
    create_tooltip(lbl_re, "RE/GEÇMİŞ HATASI: Geçmiş hadise (RE) kuralı ihlalleri")
    
    lbl_rra = tk.Label(fr_summary, text="🕒 0", font=("Segoe UI", 11, "bold"), fg="#5D4037", bg="#ECEFF1", cursor="hand2")
    lbl_rra.pack(side="left", padx=2)
    lbl_rra.bind("<Button-1>", lambda e: set_filter("GEÇ GELEN"))
    create_tooltip(lbl_rra, "GEÇ GELEN: Zamanında gelmeyen veya düzeltme (RRA) içerenler")
    
    widgets['lbl_summary_uyumsuz'] = lbl_uyumsuz
    widgets['lbl_summary_dikkat'] = lbl_dikkat
    widgets['lbl_summary_uyumlu'] = lbl_uyumlu
    widgets['lbl_summary_re'] = lbl_re
    widgets['lbl_summary_rra'] = lbl_rra

    pop_win = tk.Toplevel(parent)
    pop_win.title("Geçmiş Analiz")
    pop_win.config(bg="#ECEFF1")
    pop_win.withdraw()

    def toggle_popup():
        if pop_win.state() == "withdrawn" or pop_win.state() == "iconic":
            vars['var_oto_yenile'].set(False)
            x = btn_popup.winfo_rootx() - 250
            y = btn_popup.winfo_rooty() + btn_popup.winfo_height() + 5
            pop_win.geometry(f"+{x}+{y}")
            pop_win.deiconify()
            pop_win.lift()
        else:
            pop_win.withdraw()
            
    pop_win.protocol("WM_DELETE_WINDOW", toggle_popup)

    btn_popup = tk.Button(fr_right, text="🕒 GEÇMİŞ ANALİZ", command=toggle_popup, bg="#546E7A", fg="white", font=("Segoe UI", 9, "bold"), width=18, relief="flat")
    btn_popup.pack(side="left", fill="y", padx=2, pady=2)

    # Geçmiş Analiz (Popup İçinde)
    fr_hist = tk.LabelFrame(pop_win, text="📊 GEÇMİŞ ANALİZ", font=("Segoe UI", 9, "bold"), bg="#ECEFF1", fg="#0D47A1", padx=5, pady=5)
    fr_hist.pack(fill="x", padx=5, pady=5)
    
    # --- YENİ: Geçmiş Analiz Filtresi ---
    f_h_filter = tk.Frame(fr_hist, bg="#ECEFF1")
    f_h_filter.pack(fill="x", pady=2)
    
    mb_hist_filter = tk.Menubutton(f_h_filter, text="TÜMÜNÜ GÖSTER", bg="#546E7A", fg="white", font=("Segoe UI", 8, "bold"), relief="flat", width=25)
    
    def set_hist_filter(val):
        cb_trend_filtre.set(val) # Use the same underlying variable
        
        display_text = val
        if val == "HEPSİ": display_text = "TÜMÜNÜ GÖSTER"
        
        mb_hist_filter.config(text=display_text)
        
        # Color coding for the history filter button
        bg_col = "#546E7A"
        if "UYUMSUZ" in val: bg_col = "#D32F2F"
        elif "DİKKAT" in val: bg_col = "#F57F17"
        elif "UYUMLU" in val: bg_col = "#388E3C"
        elif "RE/" in val: bg_col = "#4CAF50"
        elif "GEÇ GELEN" in val: bg_col = "#E91E63"
        elif "RASAT YOK" in val: bg_col = "#5D4037"
        elif "HARİCİ RASATLAR" in val: bg_col = "#607D8B"
        mb_hist_filter.config(bg=bg_col)

    menu_hist = tk.Menu(mb_hist_filter, tearoff=0)
    mb_hist_filter.config(menu=menu_hist)
    mb_hist_filter.pack(fill="x")
    widgets['menu_hist'] = menu_hist
    widgets['mb_hist_filter'] = mb_hist_filter
    # --- BİTTİ: Geçmiş Analiz Filtresi ---

    f_h_date = tk.Frame(fr_hist, bg="#ECEFF1")
    f_h_date.pack(fill="x", pady=(5, 2))
    
    hist_months = config_data.get('months', []) + ["TÜM YIL"]
    cb_ay_h = ttk.Combobox(f_h_date, values=hist_months, width=12, style="CP.TCombobox")
    cb_ay_h.pack(side="left", padx=1)
    widgets['cb_ay_history'] = cb_ay_h

    cb_yil_h = ttk.Combobox(f_h_date, values=[str(i) for i in range(2020, 2031)], width=7, style="CP.TCombobox")
    cb_yil_h.set(str(now.year))
    cb_yil_h.pack(side="left", padx=1)
    widgets['cb_yil_history'] = cb_yil_h
    
    f_h_btns = tk.Frame(fr_hist, bg="#ECEFF1")
    f_h_btns.pack(fill="x", pady=5)
    
    # Menü içeriğini ana menüden kopyala
    menu_hist.add_command(label="TÜMÜNÜ GÖSTER", command=lambda: set_hist_filter("HEPSİ"))
    menu_hist.add_separator()

    menu_hist_trend = tk.Menu(menu_hist, tearoff=0)
    widgets['menu_hist_trend'] = menu_hist_trend
    menu_hist.add_cascade(label="TREND UYUM DURUMU", menu=menu_hist_trend)
    for opt in trend_opts:
        menu_hist_trend.add_command(label=opt, command=lambda o=opt: set_hist_filter(o))

    menu_hist_gec = tk.Menu(menu_hist, tearoff=0)
    widgets['menu_hist_gec'] = menu_hist_gec
    menu_hist.add_cascade(label="GEÇ GELEN RASATLAR", menu=menu_hist_gec)
    menu_hist_gec.add_command(label="HEPSİ", command=lambda: set_hist_filter("GEÇ GELEN"))
    menu_hist_gec.add_command(label="METAR", command=lambda: set_hist_filter("GEÇ GELEN METAR"))
    menu_hist_gec.add_command(label="TAF", command=lambda: set_hist_filter("GEÇ GELEN TAF"))
    menu_hist_gec.add_command(label="SİNOPTİK", command=lambda: set_hist_filter("GEÇ GELEN SİNOPTİK"))

    menu_hist.add_command(label="RASAT YOK", command=lambda: set_hist_filter("RASAT YOK"))
    menu_hist.add_separator()
    menu_hist.add_command(label="HARİCİ RASATLAR", command=lambda: set_hist_filter("HARİCİ RASATLAR"))
    
    btn_trend = tk.Button(f_h_btns, text="ANALİZ ET", command=lambda: callbacks.get('trend_history')(initial_filter=cb_trend_filtre.get()), 
                          bg="#FF9800", fg="white", relief="flat", font=("Segoe UI", 8, "bold"))
    btn_trend.pack(side="left", padx=2, fill="x", expand=True)
    widgets['btn_trend_history'] = btn_trend
    
    btn_load_h = tk.Button(f_h_btns, text="DOSYADAN", command=callbacks.get('load_history_from_file'), 
                           bg="#4CAF50", fg="white", relief="flat", font=("Segoe UI", 8, "bold"), width=10)
    btn_load_h.pack(side="left", padx=2)
    
    btn_cancel = tk.Button(f_h_btns, text="İPTAL", command=callbacks.get('cancel_history'), 
                           bg="#D32F2F", fg="white", relief="flat", font=("Segoe UI", 8, "bold"), width=8)
    btn_cancel.pack(side="left", padx=2)
    widgets['btn_cancel_history'] = btn_cancel
    
    btn_excel_h = tk.Button(f_h_btns, text="EXCEL", command=callbacks.get('export_history_to_excel'), 
                            bg="#8D6E63", fg="white", relief="flat", font=("Segoe UI", 8, "bold"), width=8)
    btn_excel_h.pack(side="left", padx=2)

    # Oto Excel Checkbox
    var_auto_excel = vars.get('var_auto_excel', tk.BooleanVar())
    chk_auto_excel = tk.Checkbutton(fr_hist, text="Oto Excel", variable=var_auto_excel, bg="#ECEFF1", font=("Segoe UI", 7))
    chk_auto_excel.pack(side="left", padx=1)
    widgets['chk_auto_excel'] = chk_auto_excel
    
    # Dummy widget for compatibility
    widgets['cb_hist_filter'] = ttk.Combobox(panel)

    return widgets