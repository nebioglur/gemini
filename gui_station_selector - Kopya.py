# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
import os
from PIL import Image, ImageTk
from ayarlar import TURKEY_STATIONS, ICAO_TO_WMO
import gui_utils

def open_station_selector(parent, cp_widgets, callback_set_station):
    win = tk.Toplevel(parent)
    win.title("İstasyon Listesi ve Konum Önizleme")
    win.geometry("950x600")
    
    # PanedWindow ile İkiye Böl (Liste | Harita)
    paned = tk.PanedWindow(win, orient=tk.HORIZONTAL, sashwidth=4, bg="#ECEFF1")
    paned.pack(fill="both", expand=True, padx=5, pady=5)
    
    frame_left = tk.Frame(paned)
    frame_right = tk.Frame(paned, bg="#263238") # Harita arka planı koyu
    
    paned.add(frame_left, minsize=450)
    paned.add(frame_right, minsize=400)
    
    # Arama
    f_search = tk.Frame(frame_left, pady=5, padx=5)
    f_search.pack(fill="x")
    tk.Label(f_search, text="Ara:").pack(side="left")
    var_search = tk.StringVar()
    entry = tk.Entry(f_search, textvariable=var_search)
    entry.pack(side="left", fill="x", expand=True, padx=5)
    entry.focus_set()
    
    # Tablo
    cols = ("KOD", "İSİM", "TİP")
    tree = ttk.Treeview(frame_left, columns=cols, show="headings")
    tree.heading("KOD", text="KOD")
    tree.heading("İSİM", text="İSİM")
    tree.heading("TİP", text="TİP")
    tree.column("KOD", width=80)
    tree.column("İSİM", width=250)
    tree.column("TİP", width=100)
    
    sb = ttk.Scrollbar(frame_left, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    tree.pack(fill="both", expand=True, padx=5, pady=5)

    # --- SAĞ TARA: HARİTA ÖNİZLEME ---
    lbl_preview_title = tk.Label(frame_right, text="KONUM ÖNİZLEME", bg="#263238", fg="#B0BEC5", font=("Segoe UI", 10, "bold"))
    lbl_preview_title.pack(pady=(10, 5))
    
    canvas = tk.Canvas(frame_right, bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Harita Görselini Hazırla
    map_img_orig = None
    try:
        map_path = gui_utils.get_resource_path("turkey_map_hd_v7.png")
        
        if not os.path.exists(map_path):
            try:
                import TR_harita
                TR_harita.generate_static_map(map_path)
            except: pass
        
        if os.path.exists(map_path):
            map_img_orig = Image.open(map_path)
    except: pass

    # Harita önbelleği (Performans için)
    map_cache = {"img": None, "w": 0, "h": 0, "params": {}}

    def confirm_selection(code):
        code = str(code)
        name = "?"
        if code in TURKEY_STATIONS:
            name = TURKEY_STATIONS[code]['name']
        
        wmo = ICAO_TO_WMO.get(code, "?")
        display_text = f"{code} - {name} ({wmo})"
        
        cp_widgets['cb_ist'].set(display_text)
        callback_set_station(display_text)
        win.destroy()

    def update_map_preview(station_code=None):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10 or h < 10: return
        
        # Harita Sınırları (TR_harita.py ile uyumlu)
        MIN_LON, MAX_LON = 25.0, 45.0
        MIN_LAT, MAX_LAT = 34.0, 44.0
        
        if map_img_orig:
            # Önbellek kontrolü ve yeniden boyutlandırma
            if map_cache["w"] != w or map_cache["h"] != h or map_cache["img"] is None:
                img_w, img_h = map_img_orig.size
                ratio = min(w/img_w, h/img_h)
                new_w, new_h = int(img_w * ratio), int(img_h * ratio)
                
                resized = map_img_orig.resize((new_w, new_h), Image.LANCZOS)
                map_cache["img"] = ImageTk.PhotoImage(resized)
                map_cache["w"] = w
                map_cache["h"] = h
                map_cache["params"] = {
                    "new_w": new_w, "new_h": new_h,
                    "off_x": (w - new_w) // 2,
                    "off_y": (h - new_h) // 2
                }
            
            photo = map_cache["img"]
            p = map_cache["params"]
            canvas.create_image(p["off_x"], p["off_y"], image=photo, anchor="nw")
            
            # İstasyon İşaretle
            if station_code: station_code = str(station_code)
            
            for code, info in TURKEY_STATIONS.items():
                lon, lat = info['lon'], info['lat']
                
                # Piksel Hesapla
                rel_x = (lon - MIN_LON) / (MAX_LON - MIN_LON)
                rel_y = (MAX_LAT - lat) / (MAX_LAT - MIN_LAT)
                
                px = p["off_x"] + (rel_x * p["new_w"])
                py = p["off_y"] + (rel_y * p["new_h"])
                
                is_selected = (code == station_code)
                
                # Marker
                r = 6 if is_selected else 3
                fill_col = "#00E676" if is_selected else "#90A4AE"
                outline_col = "white" if is_selected else "#546E7A"
                
                item_id = canvas.create_oval(px-r, py-r, px+r, py+r, fill=fill_col, outline=outline_col, width=1 if not is_selected else 2)
                
                # Tıklama ile seçim
                canvas.tag_bind(item_id, "<Button-1>", lambda e, c=code: confirm_selection(c))
                canvas.tag_bind(item_id, "<Enter>", lambda e, c=code, n=info['name']: [lbl_preview_title.config(text=f"{c} - {n}", fg="#00E676"), canvas.config(cursor="hand2")])
                canvas.tag_bind(item_id, "<Leave>", lambda e: [lbl_preview_title.config(text=f"{station_code} - {TURKEY_STATIONS[station_code]['name']}" if station_code and station_code in TURKEY_STATIONS else "KONUM ÖNİZLEME", fg="#00E676" if station_code else "#B0BEC5"), canvas.config(cursor="")])

                if is_selected:
                    canvas.create_text(px, py-r-12, text=code, fill="#00E676", font=("Segoe UI", 10, "bold"))
                    lbl_preview_title.config(text=f"{code} - {info['name']}", fg="#00E676")
            
            if not station_code:
                lbl_preview_title.config(text="KONUM ÖNİZLEME", fg="#B0BEC5")
        else:
            canvas.create_text(w//2, h//2, text="Harita görseli bulunamadı.", fill="white")

    # Canvas boyut değişimi
    canvas.bind("<Configure>", lambda e: update_map_preview(
        str(tree.item(tree.selection()[0])['values'][0]) if tree.selection() else None
    ))
    
    # Veri Hazırlama
    data = []
    for code, info in TURKEY_STATIONS.items():
        data.append((code, info['name'], info.get('type', 'MEYDAN')))
    data.sort(key=lambda x: x[0])
    
    def populate(filter_txt=""):
        for item in tree.get_children(): tree.delete(item)
        ft = filter_txt.upper()
        for code, name, typ in data:
            if ft in code or ft in name:
                tree.insert("", "end", values=(code, name, typ))
    
    populate()
    var_search.trace("w", lambda *args: populate(var_search.get()))
    
    def on_tree_select(event):
        sel = tree.selection()
        if sel:
            code = str(tree.item(sel[0])['values'][0])
            update_map_preview(code)
    
    tree.bind("<<TreeviewSelect>>", on_tree_select)
    
    # Fare ile gezinirken ve kaydırırken harita güncelleme
    last_hover_code = [None]
    def check_row_under_mouse(y):
        try:
            row_id = tree.identify_row(y)
            if row_id:
                vals = tree.item(row_id)['values']
                if vals:
                    code = str(vals[0])
                    if code != last_hover_code[0]:
                        last_hover_code[0] = code
                        update_map_preview(code)
        except: pass

    tree.bind("<Motion>", lambda e: check_row_under_mouse(e.y))
    # Kaydırma sonrası güncelleme için kısa bir gecikme (liste kaydıktan sonra kontrol et)
    tree.bind("<MouseWheel>", lambda e: tree.after(20, lambda: check_row_under_mouse(e.y)))
    tree.bind("<Button-4>", lambda e: tree.after(20, lambda: check_row_under_mouse(e.y)))
    tree.bind("<Button-5>", lambda e: tree.after(20, lambda: check_row_under_mouse(e.y)))

    def select_station(event=None):
        sel = tree.selection()
        if not sel: return
        vals = tree.item(sel[0])['values']
        confirm_selection(vals[0])
        
    tree.bind("<Double-1>", select_station)
    tree.bind("<Return>", select_station)
    tk.Button(frame_left, text="SEÇ VE KAPAT", command=select_station, bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"), relief="flat").pack(pady=10)