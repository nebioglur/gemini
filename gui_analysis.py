import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

def setup_analysis_tab(parent):
    """
    Analiz sekmesinin iskeletini (Header, Treeview) oluşturur.
    Geriye oluşturulan widget'ları döndürür.
    """
    
    # Header Frame (Dashboard Style)
    header_frame = tk.Frame(parent, bg="#263238", height=50)
    header_frame.pack(fill="x", padx=0, pady=0)
    header_frame.pack_propagate(False) # Sabit yükseklik
    
    # Sol: Başlık
    f_title = tk.Frame(header_frame, bg="#263238")
    f_title.pack(side="left", padx=15)
    lbl_title = tk.Label(f_title, text="PRO KARDELEN", bg="#263238", fg="#00E676", font=("Segoe UI", 14, "bold"))
    lbl_title.pack(anchor="w")

    
    tk.Label(f_title, text="Havacılık Meteorolojisi Analiz Sistemi", bg="#263238", fg="#B0BEC5", font=("Segoe UI", 9)).pack(anchor="w")

    # Sağ: Saat ve Timer
    f_clock = tk.Frame(header_frame, bg="#263238")
    f_clock.pack(side="right", padx=15)
    
    lbl_upcoming = tk.Label(f_clock, text="", bg="#263238", fg="#FFD700", font=("Segoe UI", 9, "bold"))
    lbl_upcoming.pack(side="left", padx=15)
    
    lbl_clock = tk.Label(f_clock, text="00:00:00 Z", bg="#263238", fg="#FFFFFF", font=("Consolas", 18, "bold"))
    lbl_clock.pack(side="right")
    
    lbl_timer = tk.Label(f_clock, text="", bg="#263238", fg="#00E676", font=("Consolas", 11))
    lbl_timer.pack(side="right", padx=10)

    # Treeview Frame (Tablo Alanı)
    # Not: pack() işlemi ana dosyada Control Panel'den sonra yapılacak
    tree_frame = tk.Frame(parent)
    
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Treeview", font=("Segoe UI", 10), rowheight=30, background="#ffffff", fieldbackground="#ffffff")
    style.map("Treeview", background=[('selected', '#1976D2')], foreground=[('selected', 'white')])
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#37474F", foreground="white", relief="flat")

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

    # Tag (Renk) Tanımlamaları
    tree.tag_configure('zebra1', background='#ffffff')
    tree.tag_configure('zebra2', background='#f5f5f5')
    tree.tag_configure('UYUMSUZ', background='#D32F2F', foreground='white', font=("Segoe UI", 10, "bold"))
    tree.tag_configure('DIKKAT', background='#FFA000')
    tree.tag_configure('UYUMLU', background='#43A047')
    tree.tag_configure('taf_row', background='#E3F2FD', foreground='#0D47A1', font=("Segoe UI", 10, "bold"))
    tree.tag_configure('TREND_YOK', background='#FFE0B2')
    tree.tag_configure('F_UYUMSUZ', background='#FFEA00', foreground='black', font=("Segoe UI", 10, "bold"))
    tree.tag_configure('RE_HATASI', background='#00E676', foreground='black', font=("Segoe UI", 10, "bold"))
    tree.tag_configure('LATE_ARRIVAL', background='#FFCC80', foreground='black', font=("Segoe UI", 10, "bold"))

    return header_frame, lbl_clock, lbl_timer, tree_frame, tree, lbl_title, lbl_upcoming