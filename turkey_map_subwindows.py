# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import file_ops

def open_history_window(parent, self_ref):
    hist_win = tk.Toplevel(parent)
    hist_win.title("Geçmiş Hatalar (Tüm Kayıtlar - Uyumsuzluklar, Dikkat ve Trend Yok)")
    hist_win.geometry("1200x700")
    hist_win.state('zoomed')
    hist_win.configure(bg="#2b2b2b")

    # Başlık
    tk.Label(hist_win, text="TESPİT EDİLEN TÜM UYUMSUZ, DİKKAT VE TREND EKSİKLİKLERİ", bg="#2b2b2b", fg="#FF5252", font=("Segoe UI", 14, "bold")).pack(pady=10)

    # Kontrol Paneli (Filtre ve Excel)
    ctrl_frame = tk.Frame(hist_win, bg="#2b2b2b")
    ctrl_frame.pack(fill="x", padx=10, pady=5)

    tk.Label(ctrl_frame, text="Filtre:", bg="#2b2b2b", fg="white", font=("Segoe UI", 10)).pack(side="left", padx=5)
    cb_hist_filter = ttk.Combobox(ctrl_frame, values=["HEPSİ", "❌ UYUMSUZ", "❌ F/UYUMSUZ", "⚠️ DİKKAT", "🔸 TREND YOK"], state="readonly", width=15)
    cb_hist_filter.current(0)
    cb_hist_filter.pack(side="left", padx=5)

    def export_history_excel():
        df = getattr(self_ref, 'incompatible_df', None)
        if df is None or df.empty:
            messagebox.showwarning("Uyarı", "Dışa aktarılacak veri yok.", parent=hist_win)
            return
        file_ops.export_map_history_excel(df, hist_win, cb_hist_filter.get())

    btn_excel = tk.Button(ctrl_frame, text="EXCEL'E AKTAR", command=export_history_excel, bg="#4CAF50", fg="white", font=("Segoe UI", 9, "bold"), relief="flat")
    btn_excel.pack(side="right", padx=10)

    # Treeview Frame
    tree_frame = tk.Frame(hist_win, bg="#2b2b2b")
    tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Ana Arayüz ile Aynı Sütun Yapısı
    cols = ("İstasyon", "Türü", "KULL.", "GÖND.", "KAYIT TAR.", "RASAT TAR.", "BÜLTEN", "TREND UYUM")
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
    
    tree.heading("İstasyon", text="İSTASYON")
    tree.heading("Türü", text="TÜRÜ")
    tree.heading("KULL.", text="KULL.")
    tree.heading("GÖND.", text="GÖND.")
    tree.heading("KAYIT TAR.", text="KAYIT TAR.")
    tree.heading("RASAT TAR.", text="RASAT TAR.")
    tree.heading("BÜLTEN", text="BÜLTEN")
    tree.heading("TREND UYUM", text="TREND UYUM")
    
    tree.column("İstasyon", width=70, anchor="center")
    tree.column("Türü", width=70, anchor="center")
    tree.column("KULL.", width=60, anchor="center")
    tree.column("GÖND.", width=60, anchor="center")
    tree.column("KAYIT TAR.", width=110, anchor="center")
    tree.column("RASAT TAR.", width=110, anchor="center")
    tree.column("BÜLTEN", width=500, anchor="w")
    tree.column("TREND UYUM", width=120, anchor="center")

    sb_y = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    sb_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
    
    sb_y.pack(side="right", fill="y")
    sb_x.pack(side="bottom", fill="x")
    tree.pack(fill="both", expand=True)

    # Zebra ve Durum Renkleri
    tree.tag_configure('zebra1', background='#f9f9f9')
    tree.tag_configure('zebra2', background='#e3f2fd')
    tree.tag_configure('UYUMSUZ', background='#FF1744', foreground='white')
    tree.tag_configure('F_UYUMSUZ', background='#FFEA00', foreground='black')
    tree.tag_configure('DIKKAT', background='#FFEB3B', foreground='black')
    tree.tag_configure('TREND_YOK', background='#FF9800', foreground='black')

    def refresh_history_tree(event=None):
        for item in tree.get_children():
            tree.delete(item)
            
        df = getattr(self_ref, 'incompatible_df', None)
        if df is not None and not df.empty:
            # Tüm veriyi göster (Süre kısıtlaması yok)
            df_filtered = df.sort_values(by='_dt', ascending=False)
            
            filter_val = cb_hist_filter.get()
            if filter_val == "❌ UYUMSUZ":
                df_filtered = df_filtered[df_filtered["_uyum"].astype(str).str.contains("UYUMSUZ", na=False)]
            elif filter_val == "❌ F/UYUMSUZ":
                df_filtered = df_filtered[df_filtered["_uyum"].astype(str).str.contains("F/UYUMSUZ", na=False)]
            elif filter_val == "⚠️ DİKKAT":
                df_filtered = df_filtered[df_filtered["_uyum"].astype(str).str.contains("DİKKAT", na=False)]
            elif filter_val == "🔸 TREND YOK":
                df_filtered = df_filtered[df_filtered["_uyum"].astype(str).str.contains("TREND YOK", na=False)]

            for i, (_, row) in enumerate(df_filtered.iterrows()):
                bulten_text = str(row.get("Bülten", "") or "")
                
                vals = (
                    row.get("İstasyon"),
                    row.get("Türü", "METAR"),
                    row.get("KULL.", "-"),
                    row.get("GÖND.", "-"),
                    row.get("KAYIT TAR.", "-"),
                    row.get("date"), # RASAT TAR.
                    bulten_text,
                    row.get("_uyum", "")
                )
                
                tags = []
                # Zebra Deseni
                if i % 2 == 0: tags.append('zebra1')
                else: tags.append('zebra2')
                
                if "F/UYUMSUZ" in row.get("_uyum", ""): tags.append("F_UYUMSUZ")
                elif "UYUMSUZ" in row.get("_uyum", ""): tags.append("UYUMSUZ")
                elif "DİKKAT" in row.get("_uyum", ""): tags.append("DIKKAT")
                elif "TREND YOK" in row.get("_uyum", ""): tags.append("TREND_YOK")
                tree.insert("", "end", values=vals, tags=tuple(tags))

    cb_hist_filter.bind("<<ComboboxSelected>>", refresh_history_tree)
    refresh_history_tree()

    tree.bind("<Double-1>", lambda e: self_ref.open_detail_window(event=e, external_tree=tree, external_df=getattr(self_ref, 'incompatible_df', None)))

def open_score_window(parent, self_ref):
    score_win = tk.Toplevel(parent)
    score_win.title("TAF Skor Tablosu (Son 48 Saat)")
    score_win.geometry("600x800")
    score_win.configure(bg="#2b2b2b")

    tk.Label(score_win, text="İSTASYON TAF SKORLARI", bg="#2b2b2b", fg="#00E676", font=("Segoe UI", 14, "bold")).pack(pady=10)
    tk.Label(score_win, text="(Son 48 saatlik ortalama puan)", bg="#2b2b2b", fg="#B0BEC5", font=("Segoe UI", 10)).pack(pady=0)

    def show_score_info():
        info_text = (
            "TAF SKOR HESAPLAMA YÖNTEMİ:\n\n"
            "1. KAPSAM:\n"
            "   • Sadece TREND (NOSIG, BECMG, TEMPO) içeren rasatlar puanlamaya dahil edilir.\n"
            "   • Trend içermeyen rasatlar hesaplamaya katılmaz.\n\n"
            "2. PUANLAMA:\n"
            "   • ✅ UYUMLU: 100 Puan\n"
            "   • ⚠️ DİKKAT: 50 Puan\n"
            "   • ❌ UYUMSUZ: 0 Puan\n\n"
            "3. CEZA KURALI:\n"
            "   • Ardışık 3 kez 'DİKKAT' durumu oluşursa, 3. rasat 0 puan alır.\n"
            "   • 'UYUMSUZ' durumu ardışık sayacı sıfırlar.\n\n"
            "4. SIRALAMA:\n"
            "   • Puanlar büyükten küçüğe sıralanır.\n"
            "   • Eşitlik durumunda daha fazla rasat yapan istasyon üstte yer alır."
        )
        messagebox.showinfo("Puanlama Mantığı", info_text, parent=score_win)

    def export_score_excel():
        scores = getattr(self_ref, 'station_scores_list', [])
        if not scores:
            messagebox.showwarning("Uyarı", "Dışa aktarılacak veri yok.", parent=score_win)
            return
        file_ops.export_map_scores_excel(scores, score_win)

    tk.Button(score_win, text="NASIL HESAPLANIR?", command=show_score_info, bg="#546E7A", fg="white", font=("Segoe UI", 9, "bold"), relief="flat").pack(pady=5)
    tk.Button(score_win, text="EXCEL'E AKTAR", command=export_score_excel, bg="#4CAF50", fg="white", font=("Segoe UI", 9, "bold"), relief="flat").pack(pady=5)

    # Treeview
    cols = ("Rank", "İstasyon", "Puan", "Rasat Sayısı")
    tree_score = ttk.Treeview(score_win, columns=cols, show="headings")
    tree_score.heading("Rank", text="#")
    tree_score.heading("İstasyon", text="İstasyon")
    tree_score.heading("Puan", text="Puan")
    tree_score.heading("Rasat Sayısı", text="Rasat Sayısı")
    
    tree_score.column("Rank", width=50, anchor="center")
    tree_score.column("İstasyon", width=100, anchor="center")
    tree_score.column("Puan", width=100, anchor="center")
    tree_score.column("Rasat Sayısı", width=100, anchor="center")
    
    tree_score.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Verileri Doldur
    scores = getattr(self_ref, 'station_scores_list', [])
    # Sırala (Puan azalan, Eşitlikte Rasat Sayısı azalan)
    scores.sort(key=lambda x: (x['score'], x['count']), reverse=True)
    
    # Zebra deseni
    tree_score.tag_configure('oddrow', background='#37474f')
    
    for i, s in enumerate(scores, 1):
        tag_color = "high" if s['score'] >= 90 else "med" if s['score'] >= 70 else "low"
        row_tags = [tag_color]
        if i % 2 == 0: row_tags.append('oddrow')
        tree_score.insert("", "end", values=(i, s['code'], f"{s['score']:.1f}", s['count']), tags=tuple(row_tags))
        
    tree_score.tag_configure('high', foreground='#00E676')
    tree_score.tag_configure('med', foreground='#FFEB3B')
    tree_score.tag_configure('low', foreground='#FF5252')

def open_settings_window(parent, robot):
    set_win = tk.Toplevel(parent)
    set_win.title("Analiz ve Alarm Ayarları")
    set_win.geometry("500x350")
    set_win.configure(bg="#2b2b2b")
    
    # Stil Ayarları (Notebook için)
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TNotebook", background="#2b2b2b", borderwidth=0)
    style.configure("TNotebook.Tab", background="#37474f", foreground="white", padding=[10, 5])
    style.map("TNotebook.Tab", background=[("selected", "#00E676")], foreground=[("selected", "black")])

    nb = ttk.Notebook(set_win)
    nb.pack(fill="both", expand=True, padx=10, pady=10)

    # --- TAB 1: ZAMAN KURALLARI ---
    tab_time = tk.Frame(nb, bg="#2b2b2b")
    nb.add(tab_time, text="Zaman Kuralları")
    
    tk.Label(tab_time, text="TREND GEÇERLİLİK SÜRELERİ (Dakika)", bg="#2b2b2b", fg="#00E676", font=("Segoe UI", 10, "bold")).pack(pady=10)
    
    # Sayısal doğrulama fonksiyonu
    def validate_numeric(P):
        if P == "" or P.isdigit():
            return True
        return False
    vcmd = (set_win.register(validate_numeric), '%P')

    # İki sütunlu yapı için ana çerçeve (Grid ile düzenli dağılım)
    main_frame = tk.Frame(tab_time, bg="#2b2b2b")
    main_frame.pack(pady=15, padx=20, fill="x")
    
    # Sütun 1: Alt Limit
    tk.Label(main_frame, text="Alt Limit (Dk):", bg="#2b2b2b", fg="white", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=10, pady=(0, 5))
    e_min = tk.Entry(main_frame, width=10, validate="key", validatecommand=vcmd, font=("Consolas", 11), bg="#37474f", fg="white", insertbackground="white")
    e_min.insert(0, str(robot.trend_min_sure))
    e_min.grid(row=1, column=0, sticky="ew", padx=10)
    tk.Label(main_frame, text="(Varsayılan: 45)", bg="#2b2b2b", fg="#78909C", font=("Segoe UI", 8)).grid(row=2, column=0, sticky="w", padx=10, pady=(2, 0))
    
    # Sütun 2: Üst Limit
    tk.Label(main_frame, text="Üst Limit (Dk):", bg="#2b2b2b", fg="white", font=("Segoe UI", 10)).grid(row=0, column=1, sticky="w", padx=10, pady=(0, 5))
    e_max = tk.Entry(main_frame, width=10, validate="key", validatecommand=vcmd, font=("Consolas", 11), bg="#37474f", fg="white", insertbackground="white")
    e_max.insert(0, str(robot.trend_max_sure))
    e_max.grid(row=1, column=1, sticky="ew", padx=10)
    tk.Label(main_frame, text="(Varsayılan: 90)", bg="#2b2b2b", fg="#78909C", font=("Segoe UI", 8)).grid(row=2, column=1, sticky="w", padx=10, pady=(2, 0))
    
    main_frame.columnconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=1)

    # --- TAB 2: LİMİTLER (EŞİKLER) ---
    tab_limit = tk.Frame(nb, bg="#2b2b2b")
    nb.add(tab_limit, text="Limitler (Eşikler)")

    tk.Label(tab_limit, text="UYUMSUZLUK EŞİK DEĞERLERİ", bg="#2b2b2b", fg="#00E676", font=("Segoe UI", 10, "bold")).pack(pady=10)
    
    fr_lim = tk.Frame(tab_limit, bg="#2b2b2b")
    fr_lim.pack(fill="x", padx=20)

    def create_limit_row(parent, label, val_list, r):
        tk.Label(parent, text=label, bg="#2b2b2b", fg="white", font=("Segoe UI", 9)).grid(row=r, column=0, sticky="w", pady=5)
        e = tk.Entry(parent, bg="#37474f", fg="white", insertbackground="white", font=("Consolas", 10))
        e.insert(0, ",".join(map(str, val_list)))
        e.grid(row=r, column=1, sticky="ew", padx=10, pady=5)
        return e

    e_vis = create_limit_row(fr_lim, "Görüş (m):", robot.esikler_ruyet, 0)
    e_ceil = create_limit_row(fr_lim, "Tavan (ft):", robot.esikler_tavan, 1)
    e_vv = create_limit_row(fr_lim, "Dikey Görüş (ft):", robot.esikler_vv, 2)
    
    fr_lim.columnconfigure(1, weight=1)
    tk.Label(tab_limit, text="* Değerleri virgül ile ayırarak girin (Örn: 150,350,600).", bg="#2b2b2b", fg="#78909C", font=("Segoe UI", 8)).pack(pady=5)
    
    # --- TAB 3: SES VE ALARM (YENİ) ---
    tab_sound = tk.Frame(nb, bg="#2b2b2b")
    nb.add(tab_sound, text="Ses ve Alarm")
    
    tk.Label(tab_sound, text="SESLİ UYARI YAPILANDIRMASI", bg="#2b2b2b", fg="#00E676", font=("Segoe UI", 10, "bold")).pack(pady=10)
    
    # Örnek Kontroller (İşlevsellik için backend bağlantısı gerekebilir)
    var_ses_aktif = tk.BooleanVar(value=True)
    tk.Checkbutton(tab_sound, text="Sesli Okuma Aktif", variable=var_ses_aktif, bg="#2b2b2b", fg="white", selectcolor="#2b2b2b", activebackground="#2b2b2b", activeforeground="white", font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=5)
    
    tk.Checkbutton(tab_sound, text="Sadece 'UYUMSUZ' Durumunda Alarm Çal", bg="#2b2b2b", fg="white", selectcolor="#2b2b2b", activebackground="#2b2b2b", activeforeground="white", font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=5)
    
    def save_settings():
        try:
            # Zaman Ayarları
            mn = int(e_min.get())
            mx = int(e_max.get())
            if mn >= mx:
                messagebox.showerror("Hata", "Alt limit üst limitten küçük olmalıdır.", parent=set_win)
                return
            
            # Limit Ayarları
            try:
                vis_list = [int(x.strip()) for x in e_vis.get().split(',') if x.strip()]
                ceil_list = [int(x.strip()) for x in e_ceil.get().split(',') if x.strip()]
                vv_list = [int(x.strip()) for x in e_vv.get().split(',') if x.strip()]
                
                vis_list.sort()
                ceil_list.sort()
                vv_list.sort()
            except ValueError:
                messagebox.showerror("Hata", "Limit değerleri sadece sayı ve virgül içermelidir.", parent=set_win)
                return

            robot.trend_min_sure = mn
            robot.trend_max_sure = mx
            robot.esikler_ruyet = vis_list
            robot.esikler_tavan = ceil_list
            robot.esikler_vv = vv_list
            
            robot.save_settings()
            messagebox.showinfo("Başarılı", "Ayarlar güncellendi ve kaydedildi.", parent=set_win)
            set_win.destroy()
        except ValueError:
            messagebox.showerror("Hata", "Lütfen geçerli sayı girin.", parent=set_win)
    
    def reset_defaults():
        e_min.delete(0, tk.END)
        e_min.insert(0, "45")
        e_max.delete(0, tk.END)
        e_max.insert(0, "90")
        e_vis.delete(0, tk.END)
        e_vis.insert(0, "150,350,600,800,1500,3000,5000")
        e_ceil.delete(0, tk.END)
        e_ceil.insert(0, "100,200,500,1000,1500")
        e_vv.delete(0, tk.END)
        e_vv.insert(0, "100,200,500,1000")

    btn_frame = tk.Frame(set_win, bg="#2b2b2b")
    btn_frame.pack(pady=10, fill="x", side="bottom")
    
    tk.Button(btn_frame, text="KAYDET", command=save_settings, bg="#4CAF50", fg="white", font=("Segoe UI", 9, "bold"), width=15, relief="flat").pack(side="left", padx=20, pady=10)
    tk.Button(btn_frame, text="VARSAYILAN", command=reset_defaults, bg="#FF9800", fg="#0D47A1", font=("Segoe UI", 9, "bold"), width=15, relief="flat").pack(side="right", padx=20, pady=10)