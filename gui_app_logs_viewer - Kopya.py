# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, scrolledtext
import os
import logging
from datetime import datetime
import re
import pandas as pd
from tkinter import filedialog, messagebox
import config_manager

class LogViewerMixin:
    """
    'uyumsuz_rasatlar.txt' dosyasını arayüzde göstermek için
    gerekli olan sekme ve bileşenleri yöneten mixin sınıfı.
    """
    def setup_log_viewer_ui(self, parent_tab):
        """Uyumsuzluk kayıtlarını gösteren sekmenin arayüzünü oluşturur."""
        self.log_viewer_frame = ttk.Frame(parent_tab)
        self.log_viewer_frame.pack(fill="both", expand=True)

        # Üst Frame (Butonlar için)
        top_frame = ttk.Frame(self.log_viewer_frame)
        top_frame.pack(fill="x", padx=5, pady=5)

        refresh_button = ttk.Button(top_frame, text="🔄 Kayıtları Yenile", command=self.load_incompatibility_log)
        refresh_button.pack(side="left")

        # --- Filtre Arayüzü Eklentisi ---
        ttk.Label(top_frame, text="Tarih Filtresi:").pack(side="left", padx=(15, 5))
        self.date_filter_combo = ttk.Combobox(top_frame, values=["Tümü", "Bugün"], state="readonly", width=10)
        self.date_filter_combo.set("Tümü")
        self.date_filter_combo.pack(side="left", padx=5)
        self.date_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.load_incompatibility_log())

        # --- İstasyon Filtresi ---
        ttk.Label(top_frame, text="İstasyon:").pack(side="left", padx=(15, 5))
        self.station_filter_combo = ttk.Combobox(top_frame, values=["Tümü"], state="readonly", width=10)
        self.station_filter_combo.set("Tümü")
        self.station_filter_combo.pack(side="left", padx=5)
        self.station_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.load_incompatibility_log())

        # --- Arama Arayüzü Eklentisi ---
        ttk.Label(top_frame, text="Ara:").pack(side="left", padx=(15, 5))
        self.search_entry = ttk.Entry(top_frame, width=30)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", self.search_logs) # Enter tuşu ile arama desteği
        
        search_button = ttk.Button(top_frame, text="🔍 Bul", command=self.search_logs)
        search_button.pack(side="left")

        # Arama sonuç sayısını gösterecek etiket
        self.search_result_label = ttk.Label(top_frame, text="", font=("Arial", 9, "bold"))
        self.search_result_label.pack(side="left", padx=10)

        # Çift tıklama ipucu
        instruction_label = ttk.Label(self.log_viewer_frame, text="💡 İpucu: İlgili istasyona haritada odaklanmak için log satırına çift tıklayın.", font=("Arial", 9, "italic"), foreground="#0288D1")
        instruction_label.pack(fill="x", padx=5, pady=2)

        # Log içeriğini gösterecek Text widget
        self.log_text_widget = scrolledtext.ScrolledText(
            self.log_viewer_frame,
            wrap=tk.WORD,
            state="disabled",  # Başlangıçta yazmaya kapalı
            font=("Consolas", 10),
            bg="#263238", fg="#ECEFF1"
        )
        self.log_text_widget.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # Log dosyasının tam yolu
        base_log_dir = config_manager.USER_DATA_DIR
        self.incompatibility_log_path = os.path.join(base_log_dir, "uyumsuz_rasatlar.txt")

        # Bulunan kelimeleri vurgulamak için stil tanımı
        self.log_text_widget.tag_config("search_match", background="yellow", foreground="black")
        self.log_text_widget.tag_config("date", foreground="#B0BEC5", font=("Consolas", 10))
        self.log_text_widget.tag_config("station", foreground="#00E676", font=("Consolas", 11, "bold"))
        self.log_text_widget.tag_config("reason_lbl", foreground="#FF5252", font=("Consolas", 10, "bold"))
        self.log_text_widget.tag_config("reason_val", foreground="#FFCDD2", font=("Consolas", 10, "italic"))
        self.log_text_widget.tag_config("metar_lbl", foreground="#4FC3F7", font=("Consolas", 10, "bold"))
        self.log_text_widget.tag_config("taf_lbl", foreground="#BA68C8", font=("Consolas", 10, "bold"))
        self.log_text_widget.tag_config("data_val", foreground="#FFFFFF", font=("Consolas", 10))
        self.log_text_widget.tag_config("summary_title", foreground="#FFCA28", font=("Consolas", 12, "bold"))
        self.log_text_widget.tag_config("summary_text", foreground="#FFF59D", font=("Consolas", 11))

        # Çift Tıklama Olayı
        self.log_text_widget.bind("<Double-1>", self.on_log_double_click)
        
        # --- Sağ Tık Menüsü ---
        self.log_context_menu = tk.Menu(self.log_text_widget, tearoff=0)
        self.log_context_menu.add_command(label="Tümünü Seç", command=self.select_all_logs)
        self.log_context_menu.add_command(label="Seçili Metni Kopyala", command=self.copy_log_selection)
        self.log_context_menu.add_separator()
        self.log_context_menu.add_command(label="Excel'e Aktar (Ekranda Görünenleri)", command=self.export_logs_to_excel)
        self.log_context_menu.add_command(label="TXT Olarak Aktar", command=self.export_logs_to_txt)
        self.log_context_menu.add_separator()
        self.log_context_menu.add_command(label="🗑️ Tüm Kayıtları Temizle", command=self.clear_incompatibility_logs)
        
        self.log_text_widget.bind("<Button-3>", lambda e: self.log_context_menu.tk_popup(e.x_root, e.y_root))

    def select_all_logs(self):
        self.log_text_widget.tag_add(tk.SEL, "1.0", tk.END)
        self.log_text_widget.mark_set(tk.INSERT, "1.0")
        self.log_text_widget.see(tk.INSERT)
        return 'break'

    def export_logs_to_txt(self):
        if not getattr(self, 'current_display_logs', None):
            messagebox.showwarning("Uyarı", "Dışa aktarılacak veri bulunmuyor.")
            return
        try:
            file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Metin Dosyası", "*.txt")], title="TXT Olarak Kaydet")
            if not file_path: return
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.log_text_widget.get("1.0", tk.END))
            messagebox.showinfo("Başarılı", "Kayıtlar başarıyla TXT'ye aktarıldı.")
        except Exception as e:
            messagebox.showerror("Hata", f"TXT'ye aktarılırken hata oluştu: {e}")

    def clear_incompatibility_logs(self):
        if messagebox.askyesno("Onay", "Tüm uyumsuzluk kayıtları kalıcı olarak SİLİNECEK.\nEmin misiniz?"):
            try:
                with open(self.incompatibility_log_path, "w", encoding="utf-8") as f:
                    f.write("")
                self.load_incompatibility_log()
                messagebox.showinfo("Başarılı", "Kayıtlar başarıyla temizlendi.")
            except Exception as e:
                messagebox.showerror("Hata", f"Kayıtlar silinirken hata oluştu: {e}")

    def on_log_double_click(self, event):
        """Log satırına çift tıklandığında içindeki istasyon kodunu bulur ve haritaya odaklar."""
        try:
            index = self.log_text_widget.index(f"@{event.x},{event.y}")
            line = self.log_text_widget.get(f"{index} linestart", f"{index} lineend")
            
            import re
            match = re.search(r'İSTASYON:\s*([A-Z0-9]{4,5})', line)
            if match:
                station_code = match.group(1)
                if hasattr(self, 'focus_station_on_map'):
                    self.focus_station_on_map(station_code)
        except Exception as e:
            logging.error(f"Log çift tıklama hatası: {e}")

    def export_logs_to_excel(self):
        if not hasattr(self, 'current_display_logs') or not self.current_display_logs:
            messagebox.showwarning("Uyarı", "Dışa aktarılacak veri bulunmuyor.")
            return
            
        try:
            file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Dosyası", "*.xlsx")], title="Excel Olarak Kaydet")
            if not file_path: return
            
            data = []
            for log in self.current_display_logs:
                if log[1] is not None:
                    dt_str, station, reason, metar, taf, _ = log
                    data.append([dt_str, station, reason, metar, taf])
            
            if not data:
                messagebox.showwarning("Uyarı", "Geçerli formatta veri bulunamadı.")
                return
                
            df = pd.DataFrame(data, columns=["Tarih", "İstasyon", "Sebep", "METAR", "TAF"])
            df.to_excel(file_path, index=False)
            messagebox.showinfo("Başarılı", "Kayıtlar başarıyla Excel'e aktarıldı.")
        except Exception as e:
            messagebox.showerror("Hata", f"Excel'e aktarılırken hata oluştu: {e}")

    def copy_log_selection(self):
        try:
            selected_text = self.log_text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.log_text_widget.clipboard_clear()
            self.log_text_widget.clipboard_append(selected_text)
        except tk.TclError:
            pass # Seçili alan yoksa sessizce geç

    def load_incompatibility_log(self):
        """'uyumsuz_rasatlar.txt' dosyasını okur ve Text widget'ına yükler."""
        self.log_text_widget.config(state="normal")
        self.log_text_widget.delete("1.0", tk.END)
        
        # Seçili filtreyi kontrol et
        filter_val = getattr(self, 'date_filter_combo', None)
        is_today_only = filter_val and filter_val.get() == "Bugün"
        today_str = datetime.now().strftime('%Y-%m-%d') if is_today_only else None

        station_val = getattr(self, 'station_filter_combo', None)
        selected_station = station_val.get() if station_val else "Tümü"

        try:
            if os.path.exists(self.incompatibility_log_path):
                with open(self.incompatibility_log_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Filtreye göre satırları ayıkla
                date_filtered_lines = [line for line in lines if not is_today_only or line.startswith(today_str)]
                
                if is_today_only and not date_filtered_lines:
                    self.log_text_widget.insert(tk.END, f"{today_str} tarihi için uyumsuz rasat kaydı bulunmuyor.\n", "data_val")
                elif not date_filtered_lines:
                    self.log_text_widget.insert(tk.END, "Uyumsuz rasat kayıt dosyası boş veya bulunamadı.\n", "data_val")
                else:
                    pattern = re.compile(r'^(.+?)\s+-\s+İSTASYON:\s*(.*?)\s+\|\s*SEBEP:\s*(.*?)\s+\|\s*METAR:\s*(.*?)\s+\|\s*TAF:\s*(.*)$')
                    
                    parsed_logs = []
                    station_counts = {}
                    
                    # Önce tüm veriyi ayrıştır ve istasyon istatistiklerini topla
                    for line in date_filtered_lines:
                        match = pattern.match(line.strip())
                        if match:
                            dt_str, station, reason, metar, taf = match.groups()
                            station = station.strip()
                            parsed_logs.append((dt_str, station, reason, metar, taf, line))
                            station_counts[station] = station_counts.get(station, 0) + 1
                        else:
                            parsed_logs.append((None, None, None, None, None, line.strip()))

                    # İstasyon filtresi listesini dinamik olarak güncelle
                    if station_val:
                        current_sel = station_val.get()
                        stations_list = ["Tümü"] + sorted(list(station_counts.keys()))
                        station_val['values'] = stations_list
                        if current_sel not in stations_list:
                            station_val.set("Tümü")
                            selected_station = "Tümü"

                    # İstasyon filtresini uygula
                    display_logs = []
                    for log in parsed_logs:
                        if log[1] is not None:
                            if selected_station != "Tümü" and log[1] != selected_station:
                                continue
                        else:
                            if selected_station != "Tümü":
                                continue
                        display_logs.append(log)

                    if not display_logs:
                        self.log_text_widget.insert(tk.END, f"Seçili istasyon ({selected_station}) için kayıt bulunmuyor.\n", "data_val")
                        return
                        
                    self.current_display_logs = display_logs

                    cnt_ruzgar = 0
                    cnt_gorus = 0
                    cnt_bulut = 0
                    cnt_hadise = 0
                    cnt_format = 0
                    total_errors = len(display_logs)

                    for log in display_logs:
                        upper_line = log[5].upper()
                        if "RÜZGAR" in upper_line or "WIND" in upper_line: cnt_ruzgar += 1
                        if "GÖRÜŞ" in upper_line or "VIS" in upper_line: cnt_gorus += 1
                        if "TAVAN" in upper_line or "DİKEY" in upper_line or "CIG" in upper_line or "BULUT" in upper_line: cnt_bulut += 1
                        if "HADİSE" in upper_line or "WX" in upper_line: cnt_hadise += 1
                        if "FORMAT" in upper_line or "ZAMAN" in upper_line or "F/UYUMSUZ" in upper_line: cnt_format += 1
                    
                    summary = f"📊 UYUMSUZLUK ÖZETİ (Toplam {total_errors} Kayıt)\n"
                    self.log_text_widget.insert(tk.END, summary, "summary_title")
                    self.log_text_widget.insert(tk.END, "="*60 + "\n", "summary_text")
                    self.log_text_widget.insert(tk.END, f"💨 Rüzgar Kaynaklı     : {cnt_ruzgar}\n", "summary_text")
                    self.log_text_widget.insert(tk.END, f"👁️ Görüş Kaynaklı      : {cnt_gorus}\n", "summary_text")
                    self.log_text_widget.insert(tk.END, f"☁️ Bulut/Tavan Kaynaklı: {cnt_bulut}\n", "summary_text")
                    self.log_text_widget.insert(tk.END, f"⛈️ Hadise Kaynaklı     : {cnt_hadise}\n", "summary_text")
                    self.log_text_widget.insert(tk.END, f"❌ Format/Zaman Hatası : {cnt_format}\n", "summary_text")

                    # En çok hata yapan istasyonlar sıralaması (Tümü seçiliyse göster)
                    if selected_station == "Tümü" and station_counts:
                        self.log_text_widget.insert(tk.END, "="*60 + "\n", "summary_text")
                        self.log_text_widget.insert(tk.END, f"🏆 EN ÇOK HATA YAPAN İSTASYONLAR (Tümü):\n", "summary_title")
                        top_stations = sorted(station_counts.items(), key=lambda x: x[1], reverse=True)
                        for st, count in top_stations:
                            self.log_text_widget.insert(tk.END, f"   📍 {st}: {count} Hata\n", "summary_text")
                            
                    self.log_text_widget.insert(tk.END, "="*60 + "\n\n", "summary_text")
                    
                    for log in display_logs:
                        if log[1] is not None:
                            dt_str, station, reason, metar, taf, _ = log
                            self.log_text_widget.insert(tk.END, f"[{dt_str}] ", "date")
                            self.log_text_widget.insert(tk.END, f"İSTASYON: {station}\n", "station")
                            self.log_text_widget.insert(tk.END, f"   SEBEP: ", "reason_lbl")
                            self.log_text_widget.insert(tk.END, f"{reason}\n", "reason_val")
                            self.log_text_widget.insert(tk.END, f"   METAR: ", "metar_lbl")
                            self.log_text_widget.insert(tk.END, f"{metar}\n", "data_val")
                            self.log_text_widget.insert(tk.END, f"   TAF  : ", "taf_lbl")
                            self.log_text_widget.insert(tk.END, f"{taf}\n", "data_val")
                            self.log_text_widget.insert(tk.END, "-"*80 + "\n", "date")
                        else:
                            self.log_text_widget.insert(tk.END, log[5] + "\n", "data_val")
            else:
                self.log_text_widget.insert(tk.END, "Uyumsuz rasat kayıt dosyası henüz oluşturulmamış veya bulunamadı.\n", "data_val")
        except Exception as e:
            error_message = f"Log dosyası okunurken bir hata oluştu:\n\n{e}"
            self.log_text_widget.insert(tk.END, error_message)
            logging.error(error_message)
        finally:
            self.log_text_widget.config(state="disabled")
            self.log_text_widget.see(tk.END) # Her yenilemede en sona git
            if hasattr(self, 'search_entry'):
                self.search_entry.delete(0, tk.END) # Yenilemede arama kutusunu temizle
            if hasattr(self, 'search_result_label'):
                self.search_result_label.config(text="") # Yenilemede sonuç sayacını temizle

    def search_logs(self, event=None):
        """Log metninde arama yapar, sonuçları vurgular ve toplam sayıyı gösterir."""
        search_term = self.search_entry.get().strip()
        
        # Önceki vurguları temizle
        self.log_text_widget.tag_remove("search_match", "1.0", tk.END)
        self.search_result_label.config(text="")
        
        if not search_term:
            return

        start_pos = "1.0"
        first_match_pos = None
        match_count = 0

        while True:
            # Metin içinde ara (büyük/küçük harf duyarsız: nocase=True)
            start_pos = self.log_text_widget.search(search_term, start_pos, stopindex=tk.END, nocase=True)
            
            if not start_pos:
                break # Başka eşleşme bulunamadı
                
            match_count += 1
            # Bulunan kelimenin bitiş indeksini hesapla
            end_pos = f"{start_pos}+{len(search_term)}c"
            self.log_text_widget.tag_add("search_match", start_pos, end_pos)
            
            if not first_match_pos:
                first_match_pos = start_pos
                self.log_text_widget.see(first_match_pos) # İlk sonuca otomatik kaydır
                
            start_pos = end_pos
            
        if match_count > 0:
            self.search_result_label.config(text=f"{match_count} sonuç bulundu", foreground="green")
        else:
            self.search_result_label.config(text="Sonuç bulunamadı", foreground="red")