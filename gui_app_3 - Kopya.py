# -*- coding: utf-8 -*-
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import ttk, messagebox
import tkinter.font as tkfont
import threading
from datetime import datetime, timedelta, timezone
import re
import time
import textwrap
import calendar
import pandas as pd
import gui_analysis
import control_panel
import os
import file_ops
from kardelen_scraper import KardelenScraper
import logging
from log_processor import process_and_analyze_logs
from ayarlar import TURKEY_STATIONS, ICAO_TO_WMO
import gui_utils
import gui_station_selector
import config_manager
from synop_decoder import SynopDecoder # En üste ekleyin
class AnalysisMixin:
    def init_analysis_vars(self):
        self.analiz_detaylari = {}
        self.app_state = {
            "last_refresh": 0, "last_alarm": 0, "missing_data": False, "last_hourly_alarm": -1,
            "missing_items": [], "incompatible_exists": False, "last_grouped_data": None,
            "silence_end_time": 0, "last_alarm_metar": 0, "last_alarm_taf": 0, "last_alarm_synop": 0,
            "last_alarm_incompatible": 0, "seen_obs_keys": set(), "initial_load_complete": False,
            "last_special_alarm_min": -1, "last_rasat_zamani_alarm_hour": -1, "prev_incompatible_keys": set(),
            'penalty_counts': {}, 'previous_missing_items': set(),
            'last_penalty_alarm_ts': {}
        }
        self.app_state["last_max_lines"] = 1
        self.scraper = KardelenScraper(station_id="17244")
        self.station_data_store = {"MEYDAN": [], "SİNOPTİK": [], "TÜMÜ": []}
        self.load_stations()
        
        # UI Değişkenleri
        self.var_active_station_type = tk.StringVar(value="MEYDAN")
        
        # SettingsMixin ile entegrasyon (Değişkenleri eşle)
        if hasattr(self, 'settings_vars'):
            self.var_uyum_show = self.settings_vars.get('var_uyum_show', tk.BooleanVar(value=False))
            self.var_tooltip_aktif = self.settings_vars.get('var_tooltip_aktif', tk.BooleanVar(value=False))
        else:
            self.var_uyum_show = tk.BooleanVar(value=False)
            self.var_tooltip_aktif = tk.BooleanVar(value=False)
        self.var_auto_excel = tk.BooleanVar(value=False)
        self.var_show_old_versions = tk.BooleanVar(value=True)
        self.var_show_other_obs = tk.BooleanVar(value=False)
        self.history_cancel_event = threading.Event()
        self.ensure_monthly_log_exists()

    def load_stations(self):
        meydan_list = []
        sinoptik_list = []
        for code, info in TURKEY_STATIONS.items():
            wmo = ICAO_TO_WMO.get(code, "?")
            display_text = f"{code} - {info['name']} ({wmo})"
            if info.get('type') == "MEYDAN": meydan_list.append((code, display_text))
            else: sinoptik_list.append((code, display_text))
        
        meydan_list.sort(key=lambda x: x[0])
        sinoptik_list.sort(key=lambda x: x[0])
        
        self.station_data_store["MEYDAN"] = [x[1] for x in meydan_list]
        self.station_data_store["SİNOPTİK"] = [x[1] for x in sinoptik_list]
        self.station_data_store["TÜMÜ"] = self.station_data_store["MEYDAN"] + self.station_data_store["SİNOPTİK"]

    def setup_analysis_ui(self, parent):
        # Header
        self.header_frame, self.lbl_clock, self.lbl_timer, self.tree_frame, self.tree, self.lbl_title, self.lbl_upcoming = gui_analysis.setup_analysis_tab(parent)
        
        # Info Strip
        self.info_strip = tk.Frame(self.root, bg="#FFF9C4", height=25)
        self.info_strip.pack(fill="x", padx=10)
        self.lbl_status = tk.Label(self.info_strip, text="Hazır...", bg="#FFF9C4", fg="black", font=("Arial", 9))
        self.lbl_status.pack(side="left", padx=5)
        self.lbl_alarm_info = tk.Label(self.info_strip, text="", bg="#FFF9C4", fg="red", font=("Arial", 10, "bold"))
        self.lbl_alarm_info.pack(side="right", padx=10)
        self.btn_silence = tk.Button(self.info_strip, text="🔕 SUSTUR (10dk)", command=self.silence_alarm, bg="#CFD8DC", font=("Arial", 8, "bold"), relief="flat")
        self.btn_silence.pack(side="right", padx=2)
        self.pb_loading = ttk.Progressbar(self.info_strip, orient="horizontal", length=200, mode="indeterminate")

        # Control Panel
        cp_callbacks = {
            'update_station_list_ui': self.update_station_list_ui,
            'open_map_window': self.open_map_window,
            'open_web_radar': getattr(self, 'open_web_radar', lambda: None),
            'open_webview_map': getattr(self, 'open_webview_map', lambda: None),
            'start_web_server': getattr(self, 'start_web_server', lambda: None),
            'toggle_uyum_col': self.toggle_uyum_col,
            'toggle_old_versions': self.toggle_old_versions,
            'toggle_other_obs': self.toggle_other_obs,
            'trend_history': self.trend_history,
            'cancel_history': self.cancel_history,
            'verileri_cek': lambda: self.verileri_cek(),
            'export_to_excel': self.export_to_excel,
            'export_history_to_excel': self.export_history_to_excel,
            'save_detailed_log': self.save_detailed_log,
            'on_trend_filter_change': self.on_trend_filter_change,
            'on_meydan_selected': self.on_meydan_selected,
            'on_sinoptik_selected': self.on_sinoptik_selected,
            'on_manual_station_search': self.on_manual_station_search,
            'on_hist_filter_change': self.on_hist_filter_change,
            'view_log_file': getattr(self, 'view_log_file', None),
            'open_station_table': self.open_station_selector_window,
            'load_demo_data': self.load_demo_data,
            'load_history_from_file': getattr(self, 'load_history_from_file', lambda: None),
            'open_sinoptik_rapor': self.open_sinoptik_rapor
        }
        cp_vars = {
            'var_uyum_show': self.var_uyum_show,
            'var_tooltip_aktif': self.var_tooltip_aktif,
            'var_oto_yenile': self.settings_vars['var_oto_yenile'],
            'var_active_station_type': self.var_active_station_type,
            'var_auto_excel': self.var_auto_excel,
            'var_show_old_versions': self.var_show_old_versions,
            'var_show_other_obs': self.var_show_other_obs
        }
        
        # Varsayılan veriler (UI açılışında boş kalmaması için)
        default_months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        default_filters = ["Tüm Bültenler", "Metar", "Taf", "Sinoptik", "TREND UYUM"]

        self.cp_widgets = control_panel.create_control_panel(parent, cp_callbacks, cp_vars, self.station_data_store, {'months': default_months, 'filters': default_filters})
        
        # Son seçilen istasyonu yükle
        last_st = self.settings_vars['var_last_station'].get()
        if last_st:
            if last_st in self.station_data_store["TÜMÜ"]:
                self.cp_widgets['cb_ist'].set(last_st)
                wmo = "17244"
                if "(" in last_st: wmo = last_st.split("(")[-1].replace(")", "").strip()
                self.scraper.set_station(wmo)
            else:
                # Tam eşleşme yoksa kod ile bulmaya çalış (İsim değişikliği vb.)
                try:
                    code = last_st.split("-")[0].strip()
                    for st in self.station_data_store["TÜMÜ"]:
                        if st.startswith(code + " -"):
                            self.cp_widgets['cb_ist'].set(st)
                            wmo = st.split("(")[-1].replace(")", "").strip()
                            self.scraper.set_station(wmo)
                            break
                except: pass
        
        # Başlangıçta ayı ve filtreyi seç
        now_utc = datetime.now(timezone.utc)

        try: 
            self.cp_widgets['cb_gun'].set(str(now_utc.day).zfill(2))
            self.cp_widgets['cb_ay'].set(default_months[now_utc.month - 1])
            self.cp_widgets['cb_yil'].set(str(now_utc.year))
        except: pass
        
        try: self.cp_widgets['cb_ay_history'].set(default_months[now_utc.month - 1])
        except: pass
        try: self.cp_widgets['cb_filt'].current(0)
        except: pass

        # Başlangıçta başlığı ayarla
        if self.cp_widgets['cb_ist'].get():
            self.lbl_title.config(text=self.cp_widgets['cb_ist'].get())

        # Treeview Paketle
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Event Bindings
        self.tree.bind("<Double-1>", self.detay_goster)
        self.tree.bind("<Motion>", lambda e: self.on_tree_motion(e))
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.root.bind("<Control-a>", self.select_all_tree)
        self.root.bind("<Control-c>", self.copy_selection)
        self.root.bind("<Control-f>", self.open_main_search_dialog)
        self.cp_widgets['cb_ist'].bind("<<ComboboxSelected>>", lambda e: self.set_station_from_selection(self.cp_widgets['cb_ist'].get()))

        # Tarih değişimi olaylarını izle (Oto Yenileme Kontrolü)
        self.cp_widgets['cb_gun'].bind("<<ComboboxSelected>>", self.on_date_change)
        self.cp_widgets['cb_ay'].bind("<<ComboboxSelected>>", self.on_date_change)
        self.cp_widgets['cb_yil'].bind("<<ComboboxSelected>>", self.on_date_change)

        # OTO Butonu Değişimini İzle
        self.settings_vars['var_oto_yenile'].trace_add("write", self.on_oto_change)
        
        # Simülasyon Zamanı Değişimini İzle (YENİ)
        if 'var_test_time_offset' in self.settings_vars:
            self.settings_vars['var_test_time_offset'].trace_add("write", self.on_sim_time_change)

        # Site Analizi Başlat
        self.root.after(100, lambda: threading.Thread(target=self.baslat_site_analiz, daemon=True).start())
        
        # Tema ve Görünüm Ayarlarını Uygula (Başlangıçta Hataları Önlemek İçin)
        self.root.after(500, self.apply_interface_settings)
        

        # KULLANICI İSTEĞİ: OTO MODUNDA AÇILSIN
        self.settings_vars['var_oto_yenile'].set(True)
        
        # Başlangıç durumlarını uygula (OTO ve Uyum Sütunu)
        if self.settings_vars['var_oto_yenile'].get():
            self.on_oto_change()
            
        self.toggle_uyum_col()
        
        # Oto Excel Zamanlayıcısını Başlat
        self.root.after(60000, self.auto_excel_loop)
        
        # Saat Başı Güncelleme Zamanlayıcısını Başlat
        self.root.after(5000, self.periodic_update_check)

    def ensure_monthly_log_exists(self):
        """Ensures the log file for the current month exists, creating it if necessary."""
        try:
            now_utc = datetime.now(timezone.utc)
            tr_months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
            ay = tr_months[now_utc.month - 1]
            yil = str(now_utc.year)
            base_log_dir = config_manager.USER_DATA_DIR
            monthly_dir = os.path.join(base_log_dir, "Aylik_Kayitlar", yil)
            os.makedirs(monthly_dir, exist_ok=True)
            monthly_file = os.path.join(monthly_dir, f"{ay}.txt")
            if not os.path.exists(monthly_file):
                with open(monthly_file, "w", encoding="utf-8") as f:
                    f.write(f"KARDELEN AYLIK ANALİZ RAPORU - {ay} {yil}\n")
                    f.write(f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
                    f.write("="*100 + "\n\n")
                logging.info(f"Boş aylık log dosyası oluşturuldu: {monthly_file}")
        except Exception as e:
            logging.error(f"Aylık log dosyası oluşturma hatası: {e}")

    def on_date_change(self, event=None):
        """Tarih değiştiğinde yapılacak işlemler."""
        # OTO Yenileme mantığı on_oto_change ile yönetiliyor.
        pass

    def on_sim_time_change(self, *args):
        """Simülasyon zamanı değiştiğinde tarih seçimlerini güncelle."""
        try:
            offset = self.settings_vars['var_test_time_offset'].get()
            sim_now = datetime.now(timezone.utc) + timedelta(minutes=offset)
            
            # Tarih widget'larını güncelle
            self.cp_widgets['cb_gun'].set(str(sim_now.day).zfill(2))
            
            tr_months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
            self.cp_widgets['cb_ay'].set(tr_months[sim_now.month - 1])
            self.cp_widgets['cb_yil'].set(str(sim_now.year))
        except: pass

    def baslat_site_analiz(self):
        res = self.scraper.analyze_site()
        def ui_update():
            if not self.root.winfo_exists(): return
            
            # Scraper'dan gelen güncel listeleri yükle (Varsa)
            if self.scraper.config.get("ay_map"):
                aylar = list(self.scraper.config["ay_map"].keys())
                self.cp_widgets['cb_ay']['values'] = aylar
                self.cp_widgets['cb_ay_history']['values'] = aylar + ["TÜM YIL"]
                # Eğer seçim yoksa güncelle
                if not self.cp_widgets['cb_ay'].get():
                    try: self.cp_widgets['cb_ay'].set(aylar[datetime.now(timezone.utc).month - 1])
                    except: pass
                
                if not self.cp_widgets['cb_ay_history'].get():
                    try: self.cp_widgets['cb_ay_history'].set(aylar[datetime.now(timezone.utc).month - 1])
                    except: pass
            
            if self.scraper.config.get("filtre_map"):
                filtreler = list(self.scraper.config["filtre_map"].keys())
                if "TREND UYUM" not in filtreler: filtreler.append("TREND UYUM")
                if "GEÇ GELEN" not in filtreler: filtreler.append("GEÇ GELEN")
                self.cp_widgets['cb_filt']['values'] = filtreler

            if res:
                self.lbl_status.config(text="Site analizi tamamlandı. Hazır.")
                self.root.after(500, self.verileri_cek)
            else:
                self.lbl_status.config(text="Site analizi uyarısı. Veri çekiliyor...")
                # Analiz tam olmasa bile son istasyon varsa veriyi çek
                if self.cp_widgets['cb_ist'].get():
                    self.root.after(500, self.verileri_cek)
        try:
            self.root.after(0, ui_update)
        except RuntimeError:
            pass

    def apply_dual_taf_analysis(self, grouped_data):
        """
        METAR ile aynı saatte yayınlanan (ancak farklı grupta olan) TAF varsa,
        onunla da uyum kontrolü yapar. (Örn: METAR 10:50, TAF 10:40 ve TAF 07:40)
        """
        # --- İPTAL: TAF öncelik ve fallback mantığı log_processor.py içerisine 
        # (asıl motor ve zaman kıyaslamasına) taşındığı için devre dışı bırakılmıştır. ---
        return
        all_tafs = []
        for g in grouped_data:
            if g['taf'] and g['taf'].get('dt'):
                all_tafs.append(g['taf'])
        
        all_tafs.sort(key=lambda x: x['dt'])
        
        if not all_tafs: return

        for g in grouped_data:
            current_taf = g['taf']
            if not current_taf or not current_taf.get('dt'): continue
            
            for obs in g['observations']:
                if obs['type'] not in ['METAR']: continue
                
                m_dt = obs.get('dt')
                if not m_dt: continue
                
                candidate_tafs = []
                ct_dt = current_taf['dt']
                
                # KURAL: Sadece aynı saatte gelen TAF ve METAR için geçerli (Örn: 2240 TAF, 2250 METAR)
                if ct_dt.year == m_dt.year and ct_dt.month == m_dt.month and ct_dt.day == m_dt.day and ct_dt.hour == m_dt.hour:
                    
                    # "AAA TAF lar hariç" - Mevcut TAF bir düzeltme/amendment ise kural uygulanmaz.
                    current_bulten = current_taf.get('bulten', '').upper()
                    is_current_amd = any(x in current_bulten for x in ["AMD", "COR", "AAA", "AAB", "AAC", "CCA", "CCB", "CCC"])
                    
                    if not is_current_amd:
                        # Kendinden önceki TAF'ı bul (AAA/AMD hariç)
                        try:
                            idx = all_tafs.index(current_taf)
                            prev_taf = None
                            for i in range(idx - 1, -1, -1):
                                pt = all_tafs[i]
                                pt_bulten = pt.get("bulten", "").upper()
                                pt_is_amd = any(x in pt_bulten for x in ["AMD", "COR", "AAA", "AAB", "AAC", "CCA", "CCB", "CCC"])
                                if not pt_is_amd:
                                    prev_taf = pt
                                    break
                                    
                            if prev_taf and prev_taf not in candidate_tafs:
                                candidate_tafs.append(prev_taf)
                        except: pass

                for alt_taf in candidate_tafs:
                    trend_split = re.split(r'\b(NOSIG|BECMG|TEMPO)\b', obs['bulten'], 1)
                    metar_trend = "".join(trend_split[1:]) if len(trend_split) > 1 else ""
                    
                    alt_score, alt_status, alt_full_report = self.robot.analiz_et(alt_taf['bulten'], obs['bulten'], metar_trend, ref_date=m_dt)
                    
                    alt_reasons = []
                    for line in alt_full_report:
                        if "▪" in line:
                            r = line.split("▪")[1].strip()
                            if r not in alt_reasons:
                                alt_reasons.append(r)
                    if not alt_reasons and "UYUMLU" not in alt_status:
                        alt_reasons = ["Uyumsuz (Önceki TAF)"]
                    
                    current_anl = obs.get('analysis')
                    
                    if "UYUMSUZ" not in alt_status:
                        # Önceki TAF (örn 19:40) UYUMLU/DİKKAT -> Bunu referans al
                        alt_reasons.insert(0, f"[ANA KONTROL] Önceki TAF ({alt_taf['dt'].strftime('%H:%M')}) ile {alt_status}.")
                        obs['analysis'] = {"durum": alt_status, "reasons": alt_reasons, "full_report": alt_full_report, "ref_taf": alt_taf['bulten'], "alarm": "YESIL" if "UYUMLU" in alt_status else ("SARI" if "DİKKAT" in alt_status else "KIRMIZI")}
                    else:
                        # Önceki TAF (örn 19:40) UYUMSUZ -> Mevcut TAF (örn 22:40) durumuna bak
                        if current_anl:
                            if "UYUMSUZ" not in current_anl['durum']:
                                if not any("Önceki TAF" in r for r in current_anl['reasons']):
                                    current_anl['reasons'].insert(0, f"[EK KONTROL] Önceki TAF ({alt_taf['dt'].strftime('%H:%M')}) ile UYUMSUZ, Mevcut TAF ({ct_dt.strftime('%H:%M')}) ile {current_anl['durum']}.")
                            else:
                                if not any("Her iki TAF" in r for r in current_anl['reasons']):
                                    current_anl['reasons'].insert(0, f"[ANA KONTROL] Her iki TAF ({alt_taf['dt'].strftime('%H:%M')} ve {ct_dt.strftime('%H:%M')}) ile de UYUMSUZ.")

    def get_taf_from_local_logs(self, target_date):
        """Belirtilen tarihteki yerel loglardan 22:40 TAF verisini okur."""
        found_tafs = []
        bulten = None
        try:
            base_log_dir = config_manager.USER_DATA_DIR
            folder_name = target_date.strftime('%Y-%m-%d')
            log_file = os.path.join(base_log_dir, folder_name, "kardelen_gunluk_log.txt")
            
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "GELDİ" in line and "TAF" in line and ("22:40" in line or "2240" in line):                            
                            try:
                                log_ts_str = line.split(']')[0].strip('[')
                                log_dt = datetime.strptime(log_ts_str, '%d.%m.%Y %H:%M:%S')
                                if log_dt.date() != target_date.date():
                                    continue
                            except:
                                continue

                            parts = line.split("GELDİ:", 1)
                            if len(parts) > 1:
                                content = parts[1].strip()
                                tokens = content.split(maxsplit=2)
                                if len(tokens) >= 3:
                                    b = tokens[2]
                                    if b.startswith("TAF"):
                                        bulten = b
                                        break # Found it, exit loop

            if not bulten:
                tr_months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
                month_name = tr_months[target_date.month - 1]
                year_str = str(target_date.year)
                monthly_file = os.path.join(base_log_dir, "Aylik_Kayitlar", year_str, f"{month_name}.txt")
                if os.path.exists(monthly_file):
                    with open(monthly_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        target_date_str = target_date.strftime('%d.%m.%Y')
                        pattern = rf"RASAT:\s*{target_date_str}\s*22:40.*?BULTEN\s*:\s*(TAF\s+[^\n]+)"
                        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                        if match:
                            bulten = match.group(1).strip()

            if bulten:
                if not bulten.startswith("TAF"):
                    bulten = "TAF " + bulten
                rasat_str = f"{target_date.strftime('%d.%m.%Y')} 22:40"
                # YEREL_LOG etiketi, bu TAF'ın alarm ve uyarı/gecikme sistemlerinden muaf tutulmasını sağlar.
                found_tafs.append(("TAF", "YEREL_LOG", "-", "-", rasat_str, bulten))
        except Exception as e:
            logging.error(f"Yerel log okuma hatası: {e}")
        return found_tafs

    def get_synop_from_local_logs(self, target_date):
        """Belirtilen tarihteki yerel loglardan 00:00 SİNOPTİK verisini okur."""
        found_synops = []
        bulten = None
        try:
            base_log_dir = config_manager.USER_DATA_DIR
            
            # 00Z sinoptik, bir önceki günün log dosyasında olabilir (23:50 civarı)
            # veya tam 00:00'da yeni günün log dosyasında. İkisini de kontrol et.
            dates_to_check = [target_date, target_date + timedelta(days=1)]
            
            for check_date in dates_to_check:
                if bulten: break # Zaten bulunduysa döngüden çık
                folder_name = check_date.strftime('%Y-%m-%d')
                log_file = os.path.join(base_log_dir, folder_name, "kardelen_gunluk_log.txt")
                
                if os.path.exists(log_file):
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            # Sadece SİNOPTİK/SYNOP içeren "GELDİ" satırlarını işle
                            if "GELDİ" in line and ("SİNOPTİK" in line or "SYNOP" in line):
                                # Zaman kontrolü: 23:45-00:15 arası
                                if "23:4" in line or "23:5" in line or "00:0" in line or "00:1" in line:
                                    try:
                                        log_ts_str = line.split(']')[0].strip('[')
                                        log_dt = datetime.strptime(log_ts_str, '%d.%m.%Y %H:%M:%S')
                                        
                                        # Eğer log satırı, aradığımız günden çok farklıysa atla
                                        if abs((log_dt.date() - target_date).days) > 1:
                                            continue
                                    except:
                                        continue

                                    parts = line.split("GELDİ:", 1)
                                    if len(parts) > 1:
                                        content = parts[1].strip()
                                        tokens = content.split(maxsplit=2)
                                        if len(tokens) >= 3:
                                            b = tokens[2]
                                            # AAXX ile başlıyorsa bu bir sinoptik bültenidir
                                            if b.startswith("AAXX"):
                                                bulten = b
                                                break # İç döngüden çık (dosya okuma)
            
            if bulten:
                # Rasat tarihi olarak bir sonraki günün 00:00'ı kullanılır
                rasat_dt = target_date.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                rasat_str = rasat_dt.strftime("%d.%m.%Y %H:%MZ")
                found_synops.append(("SİNOPTİK", "YEREL_LOG", "-", "-", rasat_str, bulten))
        except Exception as e:
            logging.error(f"Yerel sinoptik log okuma hatası: {e}")
        return found_synops

    def get_metar_from_local_logs(self, target_date):
        """Belirtilen tarihteki yerel loglardan 23:xx METAR/SPECI verilerini okur."""
        found_metars = []
        try:
            base_log_dir = config_manager.USER_DATA_DIR
            dates_to_check = [target_date, target_date + timedelta(days=1)]
            for check_date in dates_to_check:
                folder_name = check_date.strftime('%Y-%m-%d')
                log_file = os.path.join(base_log_dir, folder_name, "kardelen_gunluk_log.txt")
                
                if os.path.exists(log_file):
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if "GELDİ" in line and ("METAR" in line or "SPECI" in line) and " 23:" in line:
                                try:
                                    log_ts_str = line.split(']')[0].strip('[')
                                    log_dt = datetime.strptime(log_ts_str, '%d.%m.%Y %H:%M:%S')
                                    
                                    if abs((log_dt.date() - target_date).days) > 1:
                                        continue
                                except:
                                    continue

                                parts = line.split("GELDİ:", 1)
                                if len(parts) > 1:
                                    content = parts[1].strip()
                                    tokens = content.split(maxsplit=2)
                                    if len(tokens) >= 3:
                                        turu = tokens[1]
                                        b = tokens[2]
                                        if b.startswith("METAR") or b.startswith("SPECI"):
                                            rasat_str = f"{target_date.strftime('%d.%m.%Y')} {tokens[0]}"
                                            found_metars.append((turu, "YEREL_LOG", "-", "-", rasat_str, b))
        except Exception as e:
            logging.error(f"Yerel metar log okuma hatası: {e}")
        return found_metars

    def verileri_cek(self, silent=False):
        g = self.cp_widgets['cb_gun'].get()
        a = self.cp_widgets['cb_ay'].get()
        y = self.cp_widgets['cb_yil'].get()
        f_ad = self.cp_widgets['cb_filt'].get()
        
        # --- FIX: Thread Çakışmasını Önle (Programın donmasını engeller) ---
        if self.app_state.get("is_refreshing", False):
            # Kullanıcı isteği: "tek tek istemiyorum" -> Uyarıyı sessize al
            # if not silent: messagebox.showwarning("İşlem Sürüyor", "Veri çekme işlemi şu an devam ediyor, lütfen bekleyin.")
            return
        self.app_state["is_refreshing"] = True
        # -------------------------------------------------------------------

        if f_ad == "TREND UYUM":
            self.app_state["is_refreshing"] = False # Thread başlamadığı için kilidi kaldır
            if not silent:
                self.trend_history(use_main_date=True)
            return

        if f_ad == "GEÇ GELEN":
            self.app_state["is_refreshing"] = False # Thread başlamadığı için kilidi kaldır
            if not silent:
                self.trend_history(use_main_date=True, initial_filter="GEÇ GELEN")
            return

        f_id = self.scraper.config["filtre_map"].get(f_ad, "500")
        
        if not silent:
            self.cp_widgets['btn_goster_btn'].config(state="disabled", text="Yükleniyor...")
            self.lbl_status.config(text=f"Veri çekiliyor... {g} {a} {y}")
            self.pb_loading.pack(side="left", padx=10)
            self.pb_loading.start(15)
        else:
            self.lbl_status.config(text=f"Oto. Yenileniyor... {g} {a} {y}")

        def islem():
            ham_veriler = []
            max_retries = 3 if silent else 1
            fetch_success = False
            
            try:
                for attempt in range(max_retries):
                    try:
                        self.scraper.navigate_to_station(self.scraper.station_id)

                        try:
                            # --- KARDELEN YEREL SAAT (UTC+3) KAYMASINI ÖNLEMEK İÇİN 2 GÜNLÜK ÇEKİM ---
                            tr_months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
                            m_idx = 1
                            for i, m_name in enumerate(tr_months):
                                if m_name.upper() == a.upper():
                                    m_idx = i + 1
                                    break
                            
                            target_dt = datetime(int(y), m_idx, int(g))
                            next_dt = target_dt + timedelta(days=1)
                            prev_dt = target_dt - timedelta(days=1)
                            
                            next_g = str(next_dt.day).zfill(2)
                            next_a = tr_months[next_dt.month - 1]
                            next_y = str(next_dt.year)
                            
                            prev_g = str(prev_dt.day).zfill(2)
                            prev_a = tr_months[prev_dt.month - 1]
                            prev_y = str(prev_dt.year)

                            # Kardelen'den Bugün ve Yarın'ı tek seferde çek (21:00 - 00:00 arası TSİ kaymasını tamamen kapsar)
                            ham_veriler = self.scraper.fetch_logs(g, a, y, f_id, gun_bit=next_g, ay_bit_ismi=next_a, yil_bit=next_y)
                                
                            # --- ÖNCEKİ GÜN 22:40 TAF ---
                            # 1. Önce yerel logları kontrol et
                            local_tafs = self.get_taf_from_local_logs(prev_dt)
                            if local_tafs:
                                ham_veriler.extend(local_tafs)
                                logging.info(f"Yerel loglardan önceki günün 22:40 TAF'ı eklendi: {len(local_tafs)} adet.")
                            else:
                                # 2. Yerelde yoksa web'den çek
                                taf_id = self.scraper.config.get("filtre_map", {}).get("Taf", "2")
                                if not taf_id: taf_id = "2"
                                
                                prev_tafs = self.scraper.fetch_logs(prev_g, prev_a, prev_y, taf_id)
                                if prev_tafs:
                                    ham_veriler.extend(prev_tafs)
                                    logging.info(f"Web'den önceki günün TAF'ları eklendi: {len(prev_tafs)} adet.")
                            
                            # --- ÖNCEKİ GÜN 00:00 SİNOPTİK ---
                            # 1. Önce yerel logları kontrol et
                            local_synops = self.get_synop_from_local_logs(prev_dt)
                            if local_synops:
                                ham_veriler.extend(local_synops)
                                logging.info(f"Yerel loglardan önceki günün 00:00 SİNOPTİK'i eklendi: {len(local_synops)} adet.")
                            else:
                                # 2. Yerelde yoksa web'den çek
                                try:
                                    synop_id = self.scraper.config.get("filtre_map", {}).get("Sinoptik", "3")
                                    if not synop_id: synop_id = "3"
                                    prev_synops = self.scraper.fetch_logs(prev_g, prev_a, prev_y, synop_id)
                                    if prev_synops:
                                        ham_veriler.extend(prev_synops)
                                        logging.info(f"Web'den önceki günün SİNOPTİK'leri eklendi: {len(prev_synops)} adet.")
                                except Exception as e: logging.warning(f"Önceki gün SİNOPTİK çekme hatası: {e}")
                        except Exception as e: logging.warning(f"Önceki gün TAF/SİNOPTİK çekme hatası: {e}")
                        
                        if ham_veriler: ham_veriler = list(set(tuple(x) for x in ham_veriler))
                        
                        # Başarılı olursa döngüden çık
                        fetch_success = True
                        
                        # Bağlantı başarılı olduğunda hata durumunu sıfırla
                        if self.app_state.get("connection_down", False):
                            self.app_state["connection_down"] = False
                            if self.settings_vars['var_anons_aktif'].get():
                                msg = "BAĞLANTI SAĞLANDI."
                                self.log_to_daily_file(f"SESLİ ANONS: {msg}", "ANONS")
                                # --- YENİ: TTS Motoru Hata Yakalama (EXE Uyumluluğu) ---
                                try:
                                    self.alarm_motoru.google_seslendir(
                                        msg, 
                                        hiz=self.settings_vars['var_konusma_hizi'].get(), 
                                        pitch=self.settings_vars['var_konusma_perdesi'].get(), 
                                        use_piper=self.settings_vars['var_piper_aktif'].get(), 
                                        use_edge=self.settings_vars['var_edge_aktif'].get(), 
                                        edge_voice=self.settings_vars['var_edge_voice'].get()
                                    )
                                except Exception as tts_err:
                                    if "EDGE TTS" in str(tts_err).upper():
                                        logging.warning(f"Edge TTS motoru kullanılamadı, yedek motora geçiliyor. Hata: {tts_err}")
                                        # Edge TTS olmadan (gTTS/Piper fallback) tekrar dene
                                        self.alarm_motoru.google_seslendir(msg, hiz=self.settings_vars['var_konusma_hizi'].get(), pitch=self.settings_vars['var_konusma_perdesi'].get(), use_piper=self.settings_vars['var_piper_aktif'].get(), use_edge=False)
                                    else:
                                        # Beklenmedik başka bir TTS hatası varsa logla
                                        logging.error(f"Beklenmedik TTS hatası: {tts_err}")
                                # --- BİTTİ ---
                        break

                    except Exception as e:
                        if attempt < max_retries - 1:
                            logging.warning(f"Oto yenileme hatası ({attempt+1}/{max_retries}), tekrar deneniyor: {e}")
                            time.sleep(3)
                            continue
                        
                        logging.error(f"Veri çekme hatası: {e}")
                        self.root.after(0, lambda: self.lbl_status.config(text="Hata!"))
                        err_msg = str(e)
                        
                        # Bağlantı hatası alarmı
                        if "Sunucu" in err_msg or "bağlanılamadı" in err_msg or "Timeout" in err_msg or "ConnectionError" in err_msg:
                            # Sadece ilk kesintide alarm tetikle (Sürekli tekrar etmemesi için)
                            if not self.app_state.get("connection_down", False):
                                self.app_state["connection_down"] = True
                                self.root.after(0, lambda msg=err_msg: self.trigger_connection_alarm(msg))
                        if not silent: self.root.after(0, lambda msg=err_msg: messagebox.showerror("Hata", msg))
                        ham_veriler = []
                
                # Sessiz modda veri çekilemediyse eski veriyi koru ve çık
                if silent and not fetch_success:
                    logging.warning("Oto yenileme başarısız (Bağlantı Hatası), eski veriler korunuyor.")
                    self.root.after(0, lambda: self.lbl_status.config(text="Yenileme Başarısız (Bağlantı)"))
                    
                    # --- FIX: Bağlantı hatasında bile alarm kontrolünü çalıştır ---
                    try:
                        # Eski verileri kullanarak kontrol et (Yeni veri olmadığı için eksik çıkacaktır)
                        current_data = self.app_state.get("last_grouped_data")
                        if current_data is None: current_data = [] # Veri yoksa boş liste gönder
                        self.root.after(0, lambda cd=current_data, g_v=g, a_v=a, y_v=y, s_v=silent: self.check_alarms(cd, g_v, a_v, y_v, s_v))
                    except Exception as alarm_err:
                        logging.error(f"Bağlantı hatası durumunda alarm kontrolü başarısız: {alarm_err}")
                    return
                
                if not ham_veriler and not silent:
                    logging.warning(f"Veri bulunamadı: {g} {a} {y} (Filtre: {f_ad})")
                    self.root.after(0, lambda: messagebox.showinfo("Bilgi", "Veri yok."))

                try:
                    raw_grouped_data = process_and_analyze_logs(ham_veriler, self.robot)
                    
                    # Sadece hedef UTC gününe ait olanları filtrele (Yerel saat kaymasıyla gelen fazlalıkları at)
                    # Ek Olarak: Gece yarısı 00:00 UTC geçişinde sahte alarm üretmemesi için
                    # bir önceki günün 22:00 ve sonrasına ait verilerini süreklilik adına listede tut.
                    grouped_data = []
                    target_date_obj = target_dt.date()
                    prev_date_obj = target_date_obj - timedelta(days=1)
                    
                    for group in raw_grouped_data:
                        filtered_obs = []
                        for obs in group['observations']:
                            if obs.get('dt'):
                                o_date = obs['dt'].date()
                                o_hour = obs['dt'].hour
                                if o_date == target_date_obj or (o_date == prev_date_obj and o_hour >= 22):
                                    filtered_obs.append(obs)
                        
                        taf_keep = group['taf']
                        if taf_keep and taf_keep.get('dt'):
                            t_date = taf_keep['dt'].date()
                            t_hour = taf_keep['dt'].hour
                            if not (t_date == target_date_obj or (t_date == prev_date_obj and t_hour >= 22)):
                                taf_keep = None
                                
                        if filtered_obs or taf_keep:
                            grouped_data.append({
                                'taf': taf_keep,
                                'observations': filtered_obs
                            })
                            
                    self.apply_dual_taf_analysis(grouped_data)
                    if hasattr(self, 'clean_invalid_re_rules'): self.clean_invalid_re_rules(grouped_data)
                    self.app_state["last_grouped_data"] = grouped_data

                    # --- YENİ: Uyumsuzlukları Dosyaya Logla ---
                    try:
                        station_full_name = self.cp_widgets['cb_ist'].get()
                        station_code = station_full_name.split(' ')[0] if station_full_name else "Bilinmiyor"
                        
                        for group in grouped_data:
                            for obs in group['observations']:
                                anl = obs.get('analysis')
                                if anl and "UYUMSUZ" in anl.get('durum', ''):
                                    # Son 24 saatteki uyumsuzlukları logla (eski verilerin tekrar loglanmasını 'logged_incompatibilities' seti önler)
                                    if obs.get('dt') and abs((datetime.now(timezone.utc).replace(tzinfo=None) - obs['dt']).total_seconds()) < 86400:
                                        # İstasyon kodunu doğrudan bülten içeriğinden ayıkla (TÜMÜ seçimi için gerekli)
                                        bulten = obs.get('bulten', 'METAR verisi yok')
                                        st_match = re.search(r'\b(LT[A-Z0-9]{2})\b', bulten)
                                        if st_match:
                                            st_code = st_match.group(1)
                                        else:
                                            station_full_name = self.cp_widgets['cb_ist'].get()
                                            st_code = station_full_name.split(' ')[0] if station_full_name else "Bilinmiyor"
                                            
                                        # Aynı rasatın defalarca loglanmasını engellemek için hafızada tut
                                        log_key = f"{st_code}_{obs['dt'].strftime('%Y%m%d%H%M')}"
                                        if log_key not in self.app_state.setdefault("logged_incompatibilities", set()):
                                            self.app_state["logged_incompatibilities"].add(log_key)
                                            
                                            reasons_list = anl.get('reasons', [])
                                            reason_str = ", ".join(reasons_list) if reasons_list else "Bilinmeyen Neden"
                                            
                                            clean_taf_data = anl.get('full_taf_text', anl.get('ref_taf', 'TAF verisi yok')).replace('\n', ' ')
                                            self.log_incompatibility(
                                                station_name=st_code,
                                                reason=reason_str,
                                                metar_data=bulten.replace('\n', ' '),
                                                taf_data=clean_taf_data
                                            )
                    except Exception as log_err:
                        logging.error(f"Uyumsuzluk loglama hatası: {log_err}")
                    
                    # Alarm ve Kontrol Mantığı (Kısaltılmış)
                    self.root.after(0, lambda gd=grouped_data, g_v=g, a_v=a, y_v=y, s_v=silent: self.check_alarms(gd, g_v, a_v, y_v, s_v))
                    
                    self.root.after(0, lambda: self.populate_tree(grouped_data, self.cp_widgets['cb_trend_filtre'].get()))
                    self.root.after(0, lambda: self.lbl_status.config(text=f"Toplam {len(ham_veriler)} kayıt."))
                    if ham_veriler:
                        logging.info(f"Veri başarıyla çekildi: {len(ham_veriler)} kayıt. ({g} {a} {y})")
                except Exception as e:
                    logging.error(f"Veri işleme/analiz hatası: {e}")
                    self.root.after(0, lambda: self.lbl_status.config(text="İşleme Hatası"))
                    if not silent:
                        self.root.after(0, lambda: messagebox.showerror("Hata", f"Veri işlenirken hata oluştu:\n{e}"))
                        err_msg_process = str(e)
                        self.root.after(0, lambda msg=err_msg_process: messagebox.showerror("Hata", f"Veri işlenirken hata oluştu:\n{msg}"))

                if not silent:
                    self.root.after(0, lambda: self.cp_widgets['btn_goster_btn'].config(state="normal", text="GÖSTER"))
                    self.root.after(0, self.pb_loading.pack_forget)
            finally:
                self.app_state["is_refreshing"] = False
            
        threading.Thread(target=islem).start()

    def is_obs_late(self, obs):
        """Bir rasatın geç gelip gelmediğini kontrol eder."""
        try:
            # --- YENİ: YEREL_LOG İstisnası ---
            # Yerel loglardan otomatik tamamlanan önceki gün verileri geç sayılmaz.
            if obs.get('raw') and len(obs['raw']) > 1 and obs['raw'][1] == "YEREL_LOG":
                return False
                
            typ = obs['type'].upper()
            
            # --- YENİ: Sadece ana rasat tiplerini denetle ---
            # Bu tipler (KLIMA, MAX RUZGAR, HADISE vb.) denetim dışıdır.
            if any(k in typ for k in ["KLİMA", "MAX", "HADİSE", "SİLME", "SILME"]):
                return False
            # Sadece METAR, TAF ve SİNOPTİK (AAXX) denetlenir.
            is_target_type = "METAR" in typ or "TAF" in typ or "SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ
            if not is_target_type:
                return False
            # --- BİTTİ ---

            # --- YENİ: Düzeltme/Amendment Kontrolü (Kullanıcı İsteği) ---
            bulten = obs.get('bulten', '').upper()
            if any(x in bulten for x in ["AMD", "COR", "AAA", "AAB", "AAC", "CCA", "CCB", "CCC"]):
                return False

            if obs['reg_dt'].year < 1900: return False
            
            # --- FIX: Kayıt Tarihi (reg_dt) ile Rasat Tarihi (dt) arasındaki farkı kontrol et ---
            diff_min = 0
            if obs.get('dt') and obs['dt'].year > 1900:
                diff_min = (obs['reg_dt'] - obs['dt']).total_seconds() / 60.0
                
                # Kayıt tarihi rasat tarihinden önceyse (negatif fark) geç kalma olarak değerlendirme
                if diff_min < 0: return False
            # ------------------------------------------------------------------------------------

            reg_min = obs['reg_dt'].minute
            
            if "METAR" in typ and "SPECI" not in typ:
                if diff_min > 65: return True # 1 saatten fazla gecikme (METAR için normalde 50dk fark olur)

                start_h = self.settings_vars['var_denetim_metar_start_hour'].get()
                period = self.settings_vars['var_denetim_metar_period'].get()
                if obs.get('dt') and (obs['dt'].hour - start_h) % period == 0:
                    s = self.settings_vars['var_denetim_metar_p1_start'].get()
                    e = self.settings_vars['var_denetim_metar_p1_end'].get()
                    in_window = (s <= reg_min <= e) if s <= e else (reg_min >= s or reg_min <= e)
                    return not in_window
            
            elif ("SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ) and "HADİSE" not in typ and "MAX" not in typ and "KLİMA" not in typ:
                if "MAKSİMUM" in typ or "MAKSIMUM" in typ: return False
                if "Maksimum Ruzgar" in obs.get('bulten', ''): return False
                if "HADİSE" in obs.get('bulten', '').upper() or "HADISE" in obs.get('bulten', '').upper(): return False
                if diff_min > 75: return True # Sinoptik için toleranslı üst limit

                # --- YENİ: Eğer Sinoptik olarak etiketlenmiş ama METAR saatindeyse (örn: 50. dk), METAR gibi denetle ---
                if obs.get('dt') and obs['dt'].minute >= 45:
                    # METAR gibi davran
                    metar_start_h = self.settings_vars['var_denetim_metar_start_hour'].get()
                    metar_period = self.settings_vars['var_denetim_metar_period'].get()
                    if (obs['dt'].hour - metar_start_h) % metar_period == 0:
                        s = self.settings_vars['var_denetim_metar_p1_start'].get()
                        e = self.settings_vars['var_denetim_metar_p1_end'].get()
                        in_window = (s <= reg_min <= e) if s <= e else (reg_min >= s or reg_min <= e)
                        return not in_window
                # --- BİTTİ ---

                start_h = self.settings_vars['var_denetim_synop_start_hour'].get()
                period = self.settings_vars['var_denetim_synop_period'].get()
                
                is_check_hour = (obs['dt'].hour - start_h) % period == 0
                if not is_check_hour and period == 3 and obs['dt'].hour in [0, 3, 6, 9, 12, 15, 18, 21]: is_check_hour = True

                if obs.get('dt') and is_check_hour:
                    s = self.settings_vars['var_denetim_synop_start'].get()
                    e = self.settings_vars['var_denetim_synop_end'].get()
                    in_window = (s <= reg_min <= e) if s <= e else (reg_min >= s or reg_min <= e)
                    return not in_window
            
            elif "TAF" in typ:
                if diff_min > 45: return True # TAF için toleranslı üst limit

                start_h = self.settings_vars['var_denetim_taf_start_hour'].get()
                period = self.settings_vars['var_denetim_taf_period'].get()
                
                # FIX: TAF'lar genelde periyot başından önceki saatte yayınlanır (Örn: 02:00 periyodu için 01:40)
                h = obs['dt'].hour
                is_check_hour = (h - start_h) % period == 0
                if not is_check_hour:
                    if ((h + 1) - start_h) % period == 0:
                        is_check_hour = True
                
                if obs.get('dt') and is_check_hour:
                    s = self.settings_vars['var_denetim_taf_start'].get()
                    e = self.settings_vars['var_denetim_taf_end'].get()
                    in_window = (s <= reg_min <= e) if s <= e else (reg_min >= s or reg_min <= e)
                    return not in_window
        except: pass
        return False

    def get_delay_minutes(self, item):
        """Rasatın on-time penceresinin bitişinden itibaren kaç dakika geciktiğini hesaplar."""
        if not item.get('reg_dt') or not item.get('dt'): return 0
        
        try:
            typ = item['type'].upper()
            if "METAR" in typ and "SPECI" not in typ:
                var_obj = self.settings_vars.get('var_denetim_metar_p1_end')
                end_min = int(var_obj.get()) if var_obj else 54
            elif "TAF" in typ:
                var_obj = self.settings_vars.get('var_denetim_taf_end')
                end_min = int(var_obj.get()) if var_obj else 59
            elif "SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ:
                var_obj = self.settings_vars.get('var_denetim_synop_end')
                end_min = int(var_obj.get()) if var_obj else 59
            else:
                # Diğer rasat türleri için gecikme hesaplanmaz.
                return 0
                
            expected_end_dt = item['dt'].replace(minute=end_min, second=0, microsecond=0)
            obs_min = item['dt'].minute
            
            # 59 olarak belirlenmişse, sınırı tam saat başı (00) olarak kabul et
            if end_min == 59:
                expected_end_dt += timedelta(minutes=1)

            # Saat başı geçişlerini yönet (örn: 07:50 rasatı için 06:54 bitişi)
            if obs_min < 15 and end_min > 45: expected_end_dt -= timedelta(hours=1)
            # Saat başı geçişlerini yönet (örn: 06:50 rasatı için 07:04 bitişi)
            elif obs_min > 45 and end_min < 15: expected_end_dt += timedelta(hours=1)
                
            delay = (item['reg_dt'] - expected_end_dt).total_seconds() / 60.0
            
            # Gecikme negatifse (yani zamanında gelmişse), gecikme 0'dır.
            if delay <= 0:
                return 0
            
            # Sonucu en yakın dakikaya yuvarla ve gecikme varsa en az 1 döndür.
            return max(1, int(round(delay)))
        except Exception as e:
            logging.error(f"get_delay_minutes hatası: {e}. Gecikme hesaplanamadı.")
            return 0

    def periodic_update_check(self):
        """Her dakika çalışır, belirli aralıklarla (örn: 30dk) güncelleme yapar."""
        try:
            # Simülasyon zamanı desteği (now değişkeni oto yenileme kapalı olsa da gün sonu kontrolü için gerekli)
            offset = 0
            if 'var_test_time_offset' in self.settings_vars:
                offset = self.settings_vars['var_test_time_offset'].get()
            now = datetime.now(timezone.utc) + timedelta(minutes=offset)

            if self.settings_vars['var_oto_yenile'].get():
                # Güncelleme sıklığı (Dakika cinsinden) - Burayı değiştirebilirsiniz
                update_interval = 10
                
                # Belirlenen aralıkta bir (xx:00, xx:10, xx:20...) çalıştır
                if now.minute % update_interval == 0:
                    last_run = self.app_state.get("last_auto_update_ts", "")
                    current_run = f"{now.day}_{now.hour}_{now.minute}"
                    
                    if current_run != last_run:
                        self.on_oto_change() # Tarihleri güncele
                        self.verileri_cek(silent=True)
                        self.app_state["last_auto_update_ts"] = current_run
                    
            # Gün sonu (23:55) otomatik geçmiş analiz yedeği
            if now.hour == 23 and now.minute >= 55:
                today_str = now.strftime("%Y-%m-%d")
                if self.app_state.get("last_daily_backup") != today_str:
                    self.app_state["last_daily_backup"] = today_str
                    threading.Thread(target=self.auto_daily_history_backup, daemon=True).start()
        except Exception as e: logging.error(f"Periyodik kontrol hatası: {e}")
        self.root.after(60000, self.periodic_update_check)

    def auto_excel_loop(self):
        """Otomatik Excel dışa aktarım döngüsü."""
        if self.var_auto_excel.get() and self.app_state.get("last_grouped_data"):
            try:
                data = []
                for child in self.tree.get_children():
                    vals = self.tree.item(child)["values"]
                    if vals: data.append(vals)
                
                if data:
                    # Basit bir DataFrame oluştur ve kaydet (Sessizce)
                    cols = ["KULL.", "GÖND.", "KAYIT TAR.", "RASAT TAR.", "BÜLTEN", "DURUM"]
                    # Treeview sütun sayısı ile eşleşmeyebilir, dinamik yapalım
                    df = pd.DataFrame(data)
                    
                    log_dir = os.path.join(os.path.expanduser("~"), "KardelenLogs", "AutoExports")
                    if not os.path.exists(log_dir): os.makedirs(log_dir)
                    
                    fname = f"Auto_Analiz_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
                    path = os.path.join(log_dir, fname)
                    df.to_excel(path, index=False, header=False)
            except Exception as e: logging.error(f"Oto Excel Hatası: {e}")
        self.root.after(600000, self.auto_excel_loop) # 10 dakikada bir

    def populate_tree(self, grouped_data, filter_val="HEPSİ"):
        for item in self.tree.get_children(): self.tree.delete(item)
        self.analiz_detaylari.clear()
        self.update_filter_menu_counts(grouped_data)
        
        # İstatistik sayacı (Filtrelenmiş veriler için)
        cnt = {"UYUMSUZ": 0, "DİKKAT": 0, "UYUMLU": 0, "RRA": 0}
        cnt = {"UYUMSUZ": 0, "DİKKAT": 0, "UYUMLU": 0, "RE": 0, "RRA": 0}

        if not grouped_data:
            try:
                self.cp_widgets['lbl_summary_uyumsuz'].config(text=f"❌ 0")
                self.cp_widgets['lbl_summary_dikkat'].config(text=f"⚠️ 0")
                self.cp_widgets['lbl_summary_uyumlu'].config(text=f"✅ 0")
                self.cp_widgets['lbl_summary_re'].config(text=f"RE 0")
                self.cp_widgets['lbl_summary_rra'].config(text=f"🕒 0")
            except: pass
            return
        
        try: wrap_width = int(max(400, self.root.winfo_screenwidth() - 600) / 7)
        except: wrap_width = 100
        

        shift_start_dt = None

        # --- VERİLERİ DÜZLEŞTİR VE SIRALA ---
        all_items = []
        for group in grouped_data:
            if group['taf']:
                all_items.append(group['taf'])
            all_items.extend(group['observations'])
            
        # YENİ SIRALAMA: Rasat Tarihine (dt) Göre (Kullanıcı İsteği)
        def get_sort_key(item):
            dt = item.get('dt')
            if not dt or not isinstance(dt, datetime) or dt.year < 1900:
                dt = datetime.max # Tarihsizleri sona at
            
            reg = datetime.min
            if item.get('reg_dt') and isinstance(item['reg_dt'], datetime):
                reg = item['reg_dt']
            elif item.get('dt') and isinstance(item['dt'], datetime):
                reg = item['dt']
            
            prio = 0
            b_upper = item.get("bulten", "").upper()
            if "CCC" in b_upper: prio = 6
            elif "CCB" in b_upper: prio = 5
            elif "CCA" in b_upper: prio = 4
            elif "AAC" in b_upper: prio = 3
            elif "AAB" in b_upper: prio = 2
            elif "AAA" in b_upper or "AMD" in b_upper or "COR" in b_upper: prio = 1
        
            
            # YENİ: dt'ye göre artan, reg'e göre azalan sırala (En yeni versiyonun önce işlenmesi için)
            reg_ts = -reg.timestamp() if reg != datetime.min else 0
            return (dt, reg_ts, -prio)
            
        all_items.sort(key=get_sort_key)
        
        # --- PERFORMANS İYİLEŞTİRMESİ: Ön İşleme Adımı ---
        # Sürüm ve ilk kayıt haritalarını tek bir döngüde oluşturarak
        # veri listesi üzerindeki geçiş sayısını azaltıyoruz.
        first_reg_map = {}
        version_groups = {}
        for item in all_items:
            if item.get('dt') and item['dt'].year > 1900:
                typ = item['type'].upper()
                norm_type = typ
                if "SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ: norm_type = "SİNOPTİK"
                elif "METAR" in typ or "SPECI" in typ: norm_type = "METAR"
                elif "TAF" in typ: norm_type = "TAF"
                
                group_dt = item['dt']
                if norm_type == "TAF":
                    m_val = re.search(r'\b(\d{4}/\d{4})\b', item.get("bulten", ""))
                    if m_val: group_dt = m_val.group(1)
                    else:
                        m_wmo = re.search(r'\b[A-Z0-9]{4,6}\s+[A-Z]{4}\s+(\d{6})\b', item.get("bulten", ""))
                        if m_wmo: group_dt = m_wmo.group(1)

                k = (norm_type, group_dt)
                
                # İlk kayıt haritasını doldur (En eski reg_dt'ye sahip olanı bul)
                if k not in first_reg_map or (item.get('reg_dt', datetime.max) < first_reg_map[k].get('reg_dt', datetime.max)):
                    first_reg_map[k] = item
                
                # Sürüm gruplarını doldur
                if k not in version_groups: version_groups[k] = []
                version_groups[k].append(item)
        
        # Takip edilen rasat zamanları (Tekrarları engellemek için)
        seen_obs_times = set()
        parent_iids = {} # YENİ: Grup ana satırlarını saklamak için

        max_lines = 1
        
        for i, item in enumerate(all_items):
            # --- YENİ GRUPLAMA MANTIĞI ---
            group_key = None
            parent_to_insert_under = ""
            is_parent_row = False

            # --- YENİ: Harici Rasat Tespiti (Gelişmiş) ---
            other_keywords = ["KLİMA", "KLIMA", "MAX", "HADİSE", "HADISE", "MAKSİMUM", "MAKSIMUM", "SİLME", "SILME"]
            is_other_obs = any(k in item['type'].upper() for k in other_keywords)
            if not is_other_obs:
                bulten_upper = item.get('bulten', '').upper()
                if "MAKSİMUM RÜZGAR" in bulten_upper or "MAX RUZGAR" in bulten_upper or "MAKSIMUM RUZGAR" in bulten_upper:
                    is_other_obs = True

            if not is_other_obs and item.get('dt') and item['dt'].year > 1900:
                typ = item['type'].upper()
                norm_type = typ
                if "SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ: norm_type = "SİNOPTİK"
                elif "METAR" in typ or "SPECI" in typ: norm_type = "METAR"
                elif "TAF" in typ: norm_type = "TAF"
                
                group_dt = item['dt']
                if norm_type == "TAF":
                    m_val = re.search(r'\b(\d{4}/\d{4})\b', item.get("bulten", ""))
                    if m_val: group_dt = m_val.group(1)
                    else:
                        m_wmo = re.search(r'\b[A-Z0-9]{4,6}\s+[A-Z]{4}\s+(\d{6})\b', item.get("bulten", ""))
                        if m_wmo: group_dt = m_wmo.group(1)

                group_key = (norm_type, group_dt)

                if group_key not in parent_iids:
                    is_parent_row = True
                else:
                    if not self.var_show_old_versions.get(): continue
                    parent_to_insert_under = parent_iids[group_key]
            else: is_parent_row = True

            # --- GECİKME KONTROLÜ (KIRMIZI SATIR) ---
            # Filtrelemeden önce hesaplanmalı ki ilk gelen kayıt (on-time olsa bile) görülsün ve sonrakiler kırmızı olmasın.
            is_delayed_red = False
            try:
                if item.get('dt') and item.get('reg_dt') and item['dt'].year > 1900 and item['reg_dt'].year > 1900:
                    typ = item['type'].upper()
                    norm_type = typ
                    if "SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ:
                        if "HADİSE" in typ or "HADISE" in typ or "HADİSE" in item.get('bulten', '').upper() or "HADISE" in item.get('bulten', '').upper():
                            norm_type = "SİNOPTİK HADİSE"
                        else:
                            norm_type = "SİNOPTİK"
                    elif "METAR" in typ or "SPECI" in typ: norm_type = "METAR"
                    elif "TAF" in typ: norm_type = "TAF"
                    
                    group_dt_red = item['dt']
                    if norm_type == "TAF":
                        m_val = re.search(r'\b(\d{4}/\d{4})\b', item.get("bulten", ""))
                        if m_val: group_dt_red = m_val.group(1)
                        else:
                            m_wmo = re.search(r'\b[A-Z0-9]{4,6}\s+[A-Z]{4}\s+(\d{6})\b', item.get("bulten", ""))
                            if m_wmo: group_dt_red = m_wmo.group(1)
                            
                    k = (norm_type, group_dt_red)
                    first_item_for_delay = first_reg_map.get(k, item)
                    
                    diff_min = (first_item_for_delay['reg_dt'] - first_item_for_delay['dt']).total_seconds() / 60.0
                    if diff_min < 0: diff_min = 0

                    var_metar = self.settings_vars.get('var_delay_limit_metar')
                    lim_metar = int(var_metar.get()) if var_metar else 5
                    var_synop = self.settings_vars.get('var_delay_limit_synop')
                    lim_synop = int(var_synop.get()) if var_synop else 10
                    var_taf = self.settings_vars.get('var_delay_limit_taf')
                    lim_taf = int(var_taf.get()) if var_taf else 20

                    if item == first_item_for_delay:
                        if "METAR" in typ and "SPECI" not in typ:
                            if diff_min > 5: is_delayed_red = True
                            if diff_min > lim_metar: is_delayed_red = True
                        elif "SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ:
                            if "HADİSE" not in typ and "HADISE" not in typ and "HADİSE" not in item.get('bulten', '').upper() and "HADISE" not in item.get('bulten', '').upper():
                                if diff_min > 10: is_delayed_red = True
                                if diff_min > lim_synop: is_delayed_red = True
                        elif "TAF" in typ:
                            if diff_min > lim_taf: is_delayed_red = True
            except: pass

            # --- GEÇ GELEN GRUP KONTROLÜ ---
            is_late_group = False
            first_group_item = None
            if item.get('dt'):
                # Normalize Type for Lookup
                typ = item['type'].upper()
                norm_type = typ
                if "SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ:
                    norm_type = "SİNOPTİK"
                elif "METAR" in typ or "SPECI" in typ: norm_type = "METAR"
                elif "TAF" in typ: norm_type = "TAF"

                group_dt = item['dt']
                if norm_type == "TAF":
                    m_val = re.search(r'\b(\d{4}/\d{4})\b', item.get("bulten", ""))
                    if m_val: group_dt = m_val.group(1)
                    else:
                        m_wmo = re.search(r'\b[A-Z0-9]{4,6}\s+[A-Z]{4}\s+(\d{6})\b', item.get("bulten", ""))
                        if m_wmo: group_dt = m_wmo.group(1)

                k = (norm_type, group_dt)
                first_group_item = first_reg_map.get(k)
                if first_group_item:
                    # Grubun ilk elemanı geç kaldıysa, bu grup geç kalmıştır.
                    is_late_group = self.is_obs_late(first_group_item)
            
            is_valid_group_item = not (item.get("analysis") and "DÜZELTİLDİ" in item.get("analysis").get("durum", "").upper())

            # --- FİLTRELEME ---
            show_item = False
            typ = item['type'].upper()
            
            if is_other_obs:
                if filter_val == "HARİCİ RASATLAR":
                    show_item = True
                elif filter_val == "HEPSİ" and self.var_show_other_obs.get():
                    show_item = True
                else:
                    continue
            
            elif filter_val == "HEPSİ": 
                show_item = True
            elif filter_val == "HARİCİ RASATLAR":
                # is_other_obs yukarıda işlendi, buraya düşenler harici değil
                continue
            elif filter_val == "GEÇ GELEN":
                if is_late_group and is_valid_group_item and is_parent_row:
                    show_item = True
            elif filter_val == "GEÇ GELEN METAR":
                if is_late_group and is_valid_group_item and ("METAR" in typ or "SPECI" in typ) and is_parent_row: show_item = True
            elif filter_val == "GEÇ GELEN TAF":
                if is_late_group and is_valid_group_item and "TAF" in typ and is_parent_row: show_item = True
            elif filter_val == "GEÇ GELEN SİNOPTİK":
                if is_late_group and is_valid_group_item and ("SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ) and is_parent_row: show_item = True
            elif filter_val == "TAF":
                if "TAF" in typ: show_item = True
            elif filter_val == "METAR":
                if "METAR" in typ or "SPECI" in typ: show_item = True
            elif filter_val == "SİNOPTİK":
                if "SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ: show_item = True
            elif filter_val == "RASAT":
                if "TAF" not in typ: show_item = True
            elif filter_val == "RE/GEÇMİŞ HATASI":
                anl = item.get("analysis")
                if anl and ("RE/GECMIS" in anl.get("durum", "").upper() or "RE/GEÇMİŞ" in anl.get("durum", "").upper()):
                    show_item = True
            elif filter_val == "F/UYUMSUZ":
                anl = item.get("analysis")
                if anl and "F/UYUMSUZ" in anl.get("durum", "").upper():
                    show_item = True
            elif filter_val == "UYUMSUZ":
                anl = item.get("analysis")
                if anl:
                    durum = anl.get("durum", "").upper()
                    if "UYUMSUZ" in durum and "F/UYUMSUZ" not in durum and "RE/GECMIS" not in durum and "RE/GEÇMİŞ" not in durum:
                        show_item = True
            else:
                anl = item.get("analysis")
                if anl:
                    durum = anl["durum"].upper()
                    if "UYUMSUZ (" in filter_val:
                        if "UYUMSUZ" in durum and "F/UYUMSUZ" not in durum and "RE/GECMIS" not in durum and "RE/GEÇMİŞ" not in durum:
                            reasons = " ".join(anl.get("reasons", [])).upper()
                            if "RÜZGAR" in filter_val and ("RÜZGAR" in reasons or "WIND" in reasons): show_item = True
                            elif "GÖRÜŞ" in filter_val and ("GÖRÜŞ" in reasons or "VIS" in reasons): show_item = True
                            elif "HADİSE" in filter_val and ("HADİSE" in reasons or "WX" in reasons): show_item = True
                            elif "TAVAN" in filter_val and ("TAVAN" in reasons or "CIG" in reasons or "DİKEY" in reasons): show_item = True
                    elif filter_val == "RASAT YOK" and "TAF YOK" in durum: show_item = True
                    elif filter_val in durum: show_item = True
            
            if not show_item: continue

            # --- İSTATİSTİK GÜNCELLEME (Filtrelenmiş Veri) ---
            if is_late_group and is_valid_group_item: cnt["RRA"] += 1
            
            anl_stat = item.get("analysis")
            if anl_stat:
                d_stat = anl_stat["durum"].upper()
                is_re_stat = "RE/GECMIS" in d_stat or "RE/GEÇMİŞ" in d_stat
                if is_re_stat: cnt["RE"] += 1
                elif "F/UYUMSUZ" in d_stat: pass
                elif "UYUMSUZ" in d_stat: cnt["UYUMSUZ"] += 1
                elif "DİKKAT" in d_stat: cnt["DİKKAT"] += 1
                elif "UYUMLU" in d_stat: cnt["UYUMLU"] += 1

            # --- GÖSTERİM ---
            vals = list(item["raw"])
            if item.get('dt') and isinstance(item['dt'], datetime) and item['dt'].year > 1900:
                vals[4] = item['dt'].strftime("%d.%m.%Y %H:%MZ")
            
            disp_bulten = item["bulten"]
            extra_lines = []
            if filter_val in ["UYUMLU", "UYUMSUZ", "DİKKAT"] or "UYUMSUZ (" in filter_val:
                anl = item.get("analysis")
                if anl and anl.get("ref_taf"):
                    ref_taf = anl.get('ref_taf', '')
                    clean_ref_taf = ref_taf.split('=')[0] + '=' if '=' in ref_taf else ref_taf
                    extra_lines = textwrap.wrap(f">>> REF TAF: {clean_ref_taf}", width=wrap_width)

            wrapped = textwrap.wrap(disp_bulten, width=wrap_width)
            if extra_lines:
                wrapped.extend(extra_lines)
            vals[5] = "\n".join(wrapped)
            if len(wrapped) > max_lines: max_lines = len(wrapped)
            
            tags = ['zebra1' if i%2==0 else 'zebra2']
            res_txt = "-"
            
            # Tür Bazlı Tag (Yeni)
            if "TAF" in item["type"]:
                tags.append('ROW_TAF')
                bulten_upper = item["bulten"].upper()
                if any(x in bulten_upper for x in ["COR", "AMD", "CCA", "CCB", "CCC", "AAA", "AAB", "AAC"]):
                    tags.append('COR_AMD')
            elif "METAR" in item["type"] or "SPECI" in item["type"]:
                tags.append('ROW_METAR')
            elif "SİNOPTİK" in item["type"] or "SYNOP" in item["type"] or "SINOPTIK" in item["type"]:
                tags.append('ROW_SYNOP')
            elif "SİLME" in item["type"] or "SILME" in item["type"]:
                tags.append('RASAT_SILME')
            
            if is_delayed_red: tags.append('DELAYED_RED')

            anl = item.get("analysis")
            
            # --- RENK ATAMASI (YEŞİL/SARI/MOR) ---
            if is_other_obs:
                tags.append('OTHER_OBS_COLOR')
                tags.append('ROW_OTHER') # Style override
                if "SİLME" in item["type"] or "SILME" in item["type"]:
                    tags.append('RASAT_SILME')
            elif item.get('dt') and item['dt'].year > 1900:
                if is_parent_row: tags.append('CURRENT_VERSION')
                else: tags.append('OLD_VERSION')
            else:
                tags.append('OTHER_DATA')

            if anl:
                durum = anl["durum"].upper()
                is_re_error = any("GEÇMİŞ HADİSE" in r.upper() for r in anl.get("reasons", []))
                
                if "SİLİNDİ" in durum or "SİLME" in durum:
                    res_txt = "🗑️ RASAT SİLME"
                    tags.append("RASAT_SILME")
                elif is_re_error:
                    res_txt = "❌ RE/Geçmiş H."
                    tags.append("RE_HATASI")
                elif "F/UYUMSUZ" in durum:
                    res_txt = "❌ F/UYUMSUZ"
                    tags.append("F_UYUMSUZ")
                elif "UYUMSUZ" in durum: 
                    res_txt = "❌ UYUMSUZ"
                    tags.append("UYUMSUZ")
                elif "DİKKAT" in durum:
                    res_txt = "⚠️ DİKKAT"
                    tags.append("DIKKAT")
                elif "UYUMLU" in durum:
                    res_txt = "✅ UYUMLU"
                    tags.append("UYUMLU")
                elif "DÜZELTİLDİ" in durum:
                    res_txt = "ℹ️ DÜZELTİLDİ"
                    tags.append("DUZELTILDI")
                elif "TAF YOK" in durum: res_txt = "TAF Yok"
            
            if is_late_group and is_valid_group_item: 
                tags.append('LATE_ARRIVAL')
                # Dakika farkını ekle (Periyot sonundan hesaplanan gerçek gecikme)
                target_item_for_delay = first_group_item if first_group_item else item
                if target_item_for_delay.get('reg_dt') and target_item_for_delay.get('dt'):
                    delay = self.get_delay_minutes(target_item_for_delay)
                    res_txt += f" ({delay} dk)"

            # TAG ÖNCELİK SIRALAMASI (Tkinter Treeview'da tags listesindeki SON tag en baskındır)
            priority_map = {
                'zebra1': 1, 'zebra2': 1,
                'ROW_OTHER': 2, 'ROW_SYNOP': 2, 'ROW_TAF': 2, 'ROW_METAR': 2,
                'OLD_VERSION': 3, 'CURRENT_VERSION': 3, 'OTHER_DATA': 3, 'OTHER_OBS_COLOR': 3,
                'UYUMLU': 4, 'DIKKAT': 4, 'TREND_YOK': 4,
                'DUZELTILDI': 5,
                'UYUMSUZ': 6, 'F_UYUMSUZ': 6,
                'UYUMSUZ': 6, 'F_UYUMSUZ': 6, 'RE_HATASI': 6, 'RASAT_SILME': 6,
                'LATE_ARRIVAL': 7, 'DELAYED_RED': 8,
                'COR_AMD': 9
            }
            tags.sort(key=lambda t: priority_map.get(t, 0))

            iid = self.tree.insert(parent_to_insert_under, "end", text=vals[0], values=tuple(vals[1:]) + (res_txt,), tags=tuple(tags))
            
            if is_parent_row and group_key:
                parent_iids[group_key] = iid
            
            if anl:
                self.analiz_detaylari[iid] = {
                    "metar": item["bulten"], "taf": anl["ref_taf"], "reasons": anl["reasons"],
                    "alarm": anl["alarm"], "durum": anl["durum"], "tarih": item["tarih_str"],
                    "full_taf": anl.get("full_taf_text", ""), "dt": item["dt"],
                    "detail_str": "\n".join(anl.get("full_report", [f"• {r}" for r in anl.get("reasons", [])]))
                }
        
        # İstatistikleri Güncelle
        try:
            self.cp_widgets['lbl_summary_uyumsuz'].config(text=f"❌ {cnt['UYUMSUZ']}")
            self.cp_widgets['lbl_summary_dikkat'].config(text=f"⚠️ {cnt['DİKKAT']}")
            self.cp_widgets['lbl_summary_uyumlu'].config(text=f"✅ {cnt['UYUMLU']}")
            self.cp_widgets['lbl_summary_re'].config(text=f"RE {cnt['RE']}")
            self.cp_widgets['lbl_summary_rra'].config(text=f"🕒 {cnt['RRA']}")
        except: pass

        self.app_state["last_max_lines"] = max_lines
        style = ttk.Style()
        
        # Ayarlardan değerleri al
        base_h = int(self.settings_vars.get('var_satir_yuksekligi', tk.IntVar(value=25)).get())
        font_sz = int(self.settings_vars.get('var_yazi_boyutu', tk.IntVar(value=10)).get())
        
        max_size = font_sz
        for t in ['metar', 'taf', 'synop', 'other', 'uyumsuz']:
            t_size = int(self.settings_vars.get(f'var_style_{t}_size', tk.IntVar(value=font_sz)).get())
            if t_size > max_size: max_size = t_size

        # Satır yüksekliğini içeriğe ve ayarlara göre hesapla
        line_h = max_size * 1.8
        new_height = max(base_h, int((max_lines * line_h) + (base_h * 0.2)))
        
        style.configure("Treeview", rowheight=new_height)
        self.adjust_column_widths()

    def update_filter_menu_counts(self, grouped_data):
        """Filtre menüsündeki sayıları günceller ve boş olanları pasif yapar."""
        if not grouped_data: return

        counts = {
            "HEPSİ": 0, "UYUMLU": 0, "UYUMSUZ": 0, "F/UYUMSUZ": 0, "DİKKAT": 0,
            "UYUMSUZ (RÜZGAR)": 0, "UYUMSUZ (GÖRÜŞ)": 0, "UYUMSUZ (HADİSE)": 0, "UYUMSUZ (TAVAN)": 0,
            "RE/GEÇMİŞ HATASI": 0,
            "GEÇ GELEN": 0, "GEÇ GELEN METAR": 0, "GEÇ GELEN TAF": 0, "GEÇ GELEN SİNOPTİK": 0, "RASAT YOK": 0,
            "HARİCİ RASATLAR": 0
        }

        all_items = []
        for group in grouped_data:
            if group['taf']: all_items.append(group['taf'])
            all_items.extend(group['observations'])
            
        # Geç gelen tespiti için sıralama ve ilk kayıt haritası
        def get_sort_key(item):
            reg = datetime.min
            if item.get('reg_dt') and isinstance(item['reg_dt'], datetime): reg = item['reg_dt']
            elif item.get('dt') and isinstance(item['dt'], datetime): reg = item['dt']
            
            prio = 0
            b_upper = item.get("bulten", "").upper()
            if "CCC" in b_upper: prio = 6
            elif "CCB" in b_upper: prio = 5
            elif "CCA" in b_upper: prio = 4
            elif "AAC" in b_upper: prio = 3
            elif "AAB" in b_upper: prio = 2
            elif "AAA" in b_upper or "AMD" in b_upper or "COR" in b_upper: prio = 1
            return (reg, prio)
        all_items.sort(key=get_sort_key)

        first_reg_map = {}
        for item in all_items:
            if item.get('dt'):
                # Normalize Type
                typ = item['type'].upper()
                norm_type = typ
                if "SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ:
                    norm_type = "SİNOPTİK"
                elif "METAR" in typ or "SPECI" in typ: norm_type = "METAR"
                elif "TAF" in typ: norm_type = "TAF"
                
                group_dt = item['dt']
                if norm_type == "TAF":
                    m_val = re.search(r'\b(\d{4}/\d{4})\b', item.get("bulten", ""))
                    if m_val: group_dt = m_val.group(1)
                    else:
                        m_wmo = re.search(r'\b[A-Z0-9]{4,6}\s+[A-Z]{4}\s+(\d{6})\b', item.get("bulten", ""))
                        if m_wmo: group_dt = m_wmo.group(1)

                k = (norm_type, group_dt)
                if k not in first_reg_map or (item.get('reg_dt', datetime.max) < first_reg_map[k].get('reg_dt', datetime.max)):
                    first_reg_map[k] = item

        for item in all_items:
            # --- YENİ: DÜZELTİLMİŞ KAYITLARI SAYMA ---
            # Gizlenen kayıtların filtre menüsündeki sayılara dahil edilmemesini sağlar.
            anl_check = item.get("analysis")
            if anl_check and "DÜZELTİLDİ" in anl_check.get("durum", "").upper():
                continue
            # -----------------------------------------

            other_keywords = ["KLİMA", "KLIMA", "MAX", "HADİSE", "HADISE", "MAKSİMUM", "MAKSIMUM", "SİLME", "SILME"]
            is_other_obs = any(k in item['type'].upper() for k in other_keywords)
            if not is_other_obs:
                bulten_upper = item.get('bulten', '').upper()
                if "MAKSİMUM RÜZGAR" in bulten_upper or "MAX RUZGAR" in bulten_upper or "MAKSIMUM RUZGAR" in bulten_upper:
                    is_other_obs = True
            
            counts["HEPSİ"] += 1
            if is_other_obs:
                counts["HARİCİ RASATLAR"] += 1
            
            anl = item.get("analysis")
            if anl:
                durum = anl["durum"].upper()
                is_re_error = "RE/GECMIS" in durum or "RE/GEÇMİŞ" in durum
                if is_re_error:
                    counts["RE/GEÇMİŞ HATASI"] += 1
                elif "F/UYUMSUZ" in durum:
                    counts["F/UYUMSUZ"] += 1
                elif "UYUMSUZ" in durum:
                    counts["UYUMSUZ"] += 1
                    reasons = " ".join(anl.get("reasons", [])).upper()
                    if "RÜZGAR" in reasons or "WIND" in reasons: counts["UYUMSUZ (RÜZGAR)"] += 1
                    if "GÖRÜŞ" in reasons or "VIS" in reasons: counts["UYUMSUZ (GÖRÜŞ)"] += 1
                    if "HADİSE" in reasons or "WX" in reasons: counts["UYUMSUZ (HADİSE)"] += 1
                    if "TAVAN" in reasons or "CIG" in reasons or "DİKEY" in reasons: counts["UYUMSUZ (TAVAN)"] += 1
                elif "DİKKAT" in durum: counts["DİKKAT"] += 1
                elif "UYUMLU" in durum: counts["UYUMLU"] += 1
                elif "TAF YOK" in durum: counts["RASAT YOK"] += 1

            if item.get('dt'):
                # Normalize Type
                typ = item['type'].upper()
                norm_type = typ
                if "SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ:
                    norm_type = "SİNOPTİK"
                elif "METAR" in typ or "SPECI" in typ: norm_type = "METAR"
                elif "TAF" in typ: norm_type = "TAF"

                group_dt = item['dt']
                if norm_type == "TAF":
                    m_val = re.search(r'\b(\d{4}/\d{4})\b', item.get("bulten", ""))
                    if m_val: group_dt = m_val.group(1)
                    else:
                        m_wmo = re.search(r'\b[A-Z0-9]{4,6}\s+[A-Z]{4}\s+(\d{6})\b', item.get("bulten", ""))
                        if m_wmo: group_dt = m_wmo.group(1)

                k = (norm_type, group_dt)
                first_item = first_reg_map.get(k)
                if first_item and self.is_obs_late(first_item):
                    if item == first_item:
                        counts["GEÇ GELEN"] += 1
                        
                        if "METAR" in typ or "SPECI" in typ: counts["GEÇ GELEN METAR"] += 1
                        elif "TAF" in typ: counts["GEÇ GELEN TAF"] += 1
                        elif ("SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ): counts["GEÇ GELEN SİNOPTİK"] += 1

        try:
            def set_entry(menu, idx, label, count):
                state = "normal" if count > 0 else "disabled"
                menu.entryconfigure(idx, label=f"{label} ({count})", state=state)
            
            # Ana Filtre Menüsü
            set_entry(self.cp_widgets['menu_filter'], 0, "TÜMÜNÜ GÖSTER", counts["HEPSİ"])
            set_entry(self.cp_widgets['menu_filter'], 4, "RASAT YOK", counts["RASAT YOK"])
            set_entry(self.cp_widgets['menu_filter'], 6, "HARİCİ RASATLAR", counts["HARİCİ RASATLAR"])
            
            # Geçmiş Filtre Menüsü (Varsa)
            if 'menu_hist' in self.cp_widgets:
                set_entry(self.cp_widgets['menu_hist'], 0, "TÜMÜNÜ GÖSTER", counts["HEPSİ"])

            for i, lbl in enumerate(["UYUMLU", "UYUMSUZ", "F/UYUMSUZ", "RE/GEÇMİŞ HATASI", "DİKKAT", "UYUMSUZ (RÜZGAR)", "UYUMSUZ (GÖRÜŞ)", "UYUMSUZ (HADİSE)", "UYUMSUZ (TAVAN)"]):
                set_entry(self.cp_widgets['menu_trend'], i, lbl, counts[lbl])
                if 'menu_hist_trend' in self.cp_widgets:
                    set_entry(self.cp_widgets['menu_hist_trend'], i, lbl, counts[lbl])
                
            for i, (lbl, key) in enumerate(zip(["HEPSİ", "METAR", "TAF", "SİNOPTİK"], ["GEÇ GELEN", "GEÇ GELEN METAR", "GEÇ GELEN TAF", "GEÇ GELEN SİNOPTİK"])):
                set_entry(self.cp_widgets['menu_gec'], i, lbl, counts[key])
                if 'menu_hist_gec' in self.cp_widgets:
                    set_entry(self.cp_widgets['menu_hist_gec'], i, lbl, counts[key])
            
            # Geçmiş Analiz Buton Metnini Güncelle (Sayı ile)
            if 'mb_hist_filter' in self.cp_widgets:
                current_val = self.cp_widgets['cb_trend_filtre'].get()
                count = counts.get(current_val, 0)
                
                display_text = current_val
                if current_val == "HEPSİ": display_text = "TÜMÜNÜ GÖSTER"
                
                self.cp_widgets['mb_hist_filter'].config(text=f"{display_text} ({count})")
        except Exception as e: logging.error(f"Menu update error: {e}")

    def open_sinoptik_rapor(self):
        import subprocess
        import sys
        import os
        from tkinter import messagebox
        
        if hasattr(self, 'cp_widgets') and 'btn_sinoptik' in self.cp_widgets:
            self.cp_widgets['btn_sinoptik'].config(state="disabled", text="BEKLEYİN...")
        if hasattr(self, 'lbl_status'):
            self.lbl_status.config(text="Lütfen bekleyin, dosyalar inceleniyor ve arayüz hazırlanıyor...", fg="#0277BD")
        self.root.update()
            
        try:
            kwargs = {}
            if sys.platform == "win32" and getattr(sys, 'frozen', False):
                kwargs["creationflags"] = 0x08000000

            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable, "--hatarama"], **kwargs)
            else:
                base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
                router_path = os.path.join(base_dir, "anakardelen (2).py")
                
                if os.path.exists(router_path):
                    subprocess.Popen([sys.executable, router_path, "--hatarama"], cwd=base_dir, **kwargs)
                else:
                    script_path = os.path.join(base_dir, "arayuz.py")
                    if os.path.exists(script_path):
                        subprocess.Popen([sys.executable, script_path], cwd=base_dir, **kwargs)
        except Exception as e:
            messagebox.showerror("Hata", f"Sinoptik Rapor aracı açılamadı:\n{e}")
        finally:
            if hasattr(self, 'cp_widgets') and 'btn_sinoptik' in self.cp_widgets:
                self.root.after(1500, lambda: self.cp_widgets['btn_sinoptik'].config(state="normal", text="📊 SİNOPTİK"))
            if hasattr(self, 'lbl_status'):
                self.root.after(1500, lambda: self.lbl_status.config(text="Hazır.", fg="black"))

    # --- YARDIMCI FONKSİYONLAR ---
    def adjust_column_widths(self):
        try:
            def get_int(var_name, default):
                try: 
                    var_obj = self.settings_vars.get(var_name)
                    return int(var_obj.get()) if var_obj else default
                except: return default
                
            sz = get_int('var_yazi_boyutu', 10)
            max_sz = sz
            for t in ['metar', 'taf', 'synop', 'other', 'uyumsuz']:
                t_sz = get_int(f'var_style_{t}_size', sz)
                if t_sz > max_sz: max_sz = t_sz

            weight = self.settings_vars.get('var_yazi_kalinligi', tk.StringVar(value="normal")).get()
            family = self.settings_vars.get('var_yazi_tipi', tk.StringVar(value="Arial")).get()
            font = tkfont.Font(family=family, size=max_sz, weight=weight)
            header_font = tkfont.Font(family=family, size=max_sz, weight="bold")
            
            # #0 (TÜRÜ) Sütunu
            max_w0 = header_font.measure("TÜRÜ") + 25
            for item in self.tree.get_children():
                w = font.measure(self.tree.item(item, "text")) + 25
                if w > max_w0: max_w0 = w
                for child in self.tree.get_children(item):
                    w_child = font.measure(self.tree.item(child, "text")) + 45
                    if w_child > max_w0: max_w0 = w_child
            self.tree.column("#0", width=max_w0, stretch=False)

            columns = self.tree["columns"]
            for col in columns:
                # KULL. ve GÖND. sütunları için daha az pay bırakalım (Kullanıcı isteği)
                padding = 10 if col in ["KULL.", "GÖND."] else 25
                max_w = header_font.measure(col) + padding
                
                for item in self.tree.get_children():
                    val = self.tree.set(item, col)
                    for line in str(val).split('\n'):
                        w = font.measure(line) + padding
                        if w > max_w: max_w = w
                    
                    for child in self.tree.get_children(item):
                        val = self.tree.set(child, col)
                        for line in str(val).split('\n'):
                            w = font.measure(line) + padding
                            if w > max_w: max_w = w
                
                if col == "BÜLTEN": self.tree.column(col, width=max_w, stretch=True)
                else: self.tree.column(col, width=max_w, stretch=False)
        except Exception as e: logging.error(f"Sütun ayar hatası: {e}")

    def select_all_tree(self, event=None):
        yellow_items = []
        def traverse(parent=""):
            for child in self.tree.get_children(parent):
                if "search_yellow" in self.tree.item(child, "tags"):
                    yellow_items.append(child)
                traverse(child)
        traverse()

        if yellow_items:
            self.tree.selection_remove(self.tree.selection())
            for item in yellow_items:
                self.tree.selection_add(item)
        else:
            for child in self.tree.get_children():
                self.tree.selection_add(child)
                for subchild in self.tree.get_children(child):
                    self.tree.selection_add(subchild)

    def copy_all_table(self):
        text = ""
        for child in self.tree.get_children():
            text += str(self.tree.item(child)["text"]) + "\t"
            vals = self.tree.item(child)["values"]
            if vals:
                text += "\t".join(map(str, vals)) + "\n"
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Kopyalandı", "Tüm tablo panoya kopyalandı.")

    def export_visible_to_excel(self, only_uyumsuz=False):
        import pandas as pd
        from tkinter import filedialog, messagebox
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")])
        if not file_path: return
        
        data = []
        for child in self.tree.get_children():
            text = self.tree.item(child)["text"]
            vals = self.tree.item(child)["values"]
            if vals:
                if only_uyumsuz:
                    durum_val = str(vals[5]).upper() if len(vals) > 5 else ""
                    if "UYUMSUZ" not in durum_val:
                        continue
                data.append([text] + list(vals))
        if data:
            cols = ["TÜRÜ", "KULL.", "GÖND.", "KAYIT TAR.", "RASAT TAR.", "BÜLTEN", "DURUM"]
            df = pd.DataFrame(data, columns=cols)
            df.to_excel(file_path, index=False)
            messagebox.showinfo("Başarılı", "Ekranda görünen kayıtlar Excel'e aktarıldı.")
            msg = "Sadece uyumsuz kayıtlar Excel'e aktarıldı." if only_uyumsuz else "Ekranda görünen kayıtlar Excel'e aktarıldı."
            messagebox.showinfo("Başarılı", msg)
        else:
            messagebox.showwarning("Uyarı", "Dışa aktarılacak uygun veri bulunamadı.")
            
    def export_visible_to_txt(self):
        from tkinter import filedialog, messagebox
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Metin Dosyası", "*.txt")])
        if not file_path: return
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for child in self.tree.get_children():
                    text = self.tree.item(child)["text"]
                    vals = self.tree.item(child)["values"]
                    if vals:
                        f.write(f"TÜR: {text} | KULL: {vals[0]} | GÖND: {vals[1]} | KAYIT: {vals[2]} | RASAT: {vals[3]}\n")
                        f.write(f"BÜLTEN: {vals[4]}\n")
                        f.write(f"DURUM: {vals[5]}\n")
                        f.write("-" * 80 + "\n")
            messagebox.showinfo("Başarılı", "Ekranda görünen kayıtlar TXT olarak kaydedildi.")
        except Exception as e:
            messagebox.showerror("Hata", f"Kaydetme hatası: {e}")

    def apply_interface_settings(self):
        """Ayarlar değiştiğinde arayüzü anlık günceller."""
        try:
            def get_int(var_name, default):
                try:
                    var_obj = self.settings_vars.get(var_name)
                    return int(var_obj.get()) if var_obj else default
                except: return default

            sz = get_int('var_yazi_boyutu', 10)
            weight = self.settings_vars.get('var_yazi_kalinligi', tk.StringVar(value="normal")).get()
            family = self.settings_vars.get('var_yazi_tipi', tk.StringVar(value="Arial")).get()
            base_h = get_int('var_satir_yuksekligi', 25)
            bg_col = self.settings_vars.get('var_tablo_arkaplan', tk.StringVar(value="#ffffff")).get()
            zebra2_col = self.settings_vars.get('var_tablo_zebra2', tk.StringVar(value="#eceff1")).get()
            sel_col = self.settings_vars.get('var_tablo_secili_renk', tk.StringVar(value="#1976D2")).get()
            
            style = ttk.Style()
            
            # Mevcut satır sayısına göre yüksekliği yeniden hesapla
            max_lines = self.app_state.get("last_max_lines", 1)
            line_h = sz * 1.8
            new_height = max(base_h, int((max_lines * line_h) + (base_h * 0.2)))
            
            style.configure("Treeview", font=(family, sz, weight), rowheight=new_height, background=bg_col, fieldbackground=bg_col)
            style.map("Treeview", background=[('selected', sel_col)], foreground=[('selected', 'white')])
            style.configure("Treeview.Heading", font=(family, sz, "bold"))
            
            max_size = sz

            # =========================================================================
            # TAG ÖNCELİK SIRALAMASI (Tkinter'da en son configure edilen en baskın olur)
            # Alt katmandan üst katmana doğru sıralanmalıdır!
            # =========================================================================

            # 1. EN ALT KATMAN: ZEBRA DESENLERİ
            try: self.tree.tag_configure('zebra1', background=bg_col)
            except: pass
            try: self.tree.tag_configure('zebra2', background=zebra2_col)
            except: pass
            
            # 2. SATIR TİPLERİ (KULLANICI AYARLARI - TEMEL RENKLER)
            for t, tag in [('other', 'ROW_OTHER'), ('synop', 'ROW_SYNOP'), ('taf', 'ROW_TAF'), ('metar', 'ROW_METAR')]:
                fg = self.settings_vars.get(f'var_style_{t}_fg', tk.StringVar(value="black")).get()
                bg = self.settings_vars.get(f'var_style_{t}_bg', tk.StringVar(value="")).get()
                t_family = self.settings_vars.get(f'var_style_{t}_family', tk.StringVar(value=family)).get()
                t_bold = self.settings_vars.get(f'var_style_{t}_bold', tk.BooleanVar(value=False)).get()
                t_size = get_int(f'var_style_{t}_size', sz)
                if t_size > max_size: max_size = t_size
                conf = {'font': (t_family, t_size, "bold" if t_bold else "normal")}
                if fg: conf['foreground'] = fg
                if bg: conf['background'] = bg
                try: self.tree.tag_configure(tag, **conf)
                except: pass
            
            # 3. VERSİYON DURUMLARI (ESKİ / GÜNCEL)
            try: self.tree.tag_configure('OLD_VERSION', background='#FFF9C4')
            except: pass
            try: self.tree.tag_configure('CURRENT_VERSION', background='#C8E6C9')
            except: pass
            try: self.tree.tag_configure('OTHER_DATA', background='#E1BEE7')
            except: pass
            try: self.tree.tag_configure('OTHER_OBS_COLOR', background='#80DEEA')
            except: pass
            try: self.tree.tag_configure('RASAT_SILME', background='#757575', foreground='white', font=(family, sz, "bold"))
            except: pass
            
            # KULLANICI AYARLARI (ESKİ / DÜZELTİLDİ) - 3'ün üzerine ezer
            for t, tag in [('eski', 'OLD_VERSION'), ('eski', 'DUZELTILDI')]:
                fg = self.settings_vars.get(f'var_style_{t}_fg', tk.StringVar(value="black")).get()
                bg = self.settings_vars.get(f'var_style_{t}_bg', tk.StringVar(value="")).get()
                t_family = self.settings_vars.get(f'var_style_{t}_family', tk.StringVar(value=family)).get()
                t_bold = self.settings_vars.get(f'var_style_{t}_bold', tk.BooleanVar(value=False)).get()
                t_size = get_int(f'var_style_{t}_size', sz)
                conf = {'font': (t_family, t_size, "bold" if t_bold else "normal")}
                if fg: conf['foreground'] = fg
                if bg: conf['background'] = bg
                try: self.tree.tag_configure(tag, **conf)
                except: pass

            # 4. ANALİZ SONUÇLARI (UYUMLU, DİKKAT)
            try: self.tree.tag_configure('UYUMLU', background='#69F0AE')
            except: pass
            try: self.tree.tag_configure('DIKKAT', background='#FF9800')
            except: pass
            try: self.tree.tag_configure('TREND_YOK')
            except: pass

            # 5. GECİKMELER VE KRİTİK HATALAR (EN ÜST KATMAN)
            # UYUMSUZ VE GEÇ KULLANICI AYARLARI
            for t, tag in [('uyumsuz', 'UYUMSUZ'), ('re_hatasi', 'RE_HATASI'), ('gec', 'LATE_ARRIVAL'), ('cor_amd', 'COR_AMD')]:
                fg = self.settings_vars.get(f'var_style_{t}_fg', tk.StringVar(value="black")).get()
                bg = self.settings_vars.get(f'var_style_{t}_bg', tk.StringVar(value="")).get()
                t_family = self.settings_vars.get(f'var_style_{t}_family', tk.StringVar(value=family)).get()
                t_bold = self.settings_vars.get(f'var_style_{t}_bold', tk.BooleanVar(value=False)).get()
                t_size = get_int(f'var_style_{t}_size', sz)
                conf = {'font': (t_family, t_size, "bold" if t_bold else "normal")}
                if fg: conf['foreground'] = fg
                if bg: conf['background'] = bg
                try: self.tree.tag_configure(tag, **conf)
                except: pass

            # Sabit Kritikler (Kullanıcı Ayarını da ezer)
            try: self.tree.tag_configure('F_UYUMSUZ', background='#FFEA00', foreground='black')
            except: pass
            try: self.tree.tag_configure('DELAYED_RED', background='#D32F2F', foreground='white')
            except: pass
            
            # Yeni maksimum satır boyutuna göre satır yüksekliğini ayarla
            line_h = max_size * 1.8
            new_height = max(base_h, int((max_lines * line_h) + (base_h * 0.2)))
            style.configure("Treeview", rowheight=new_height)
            
            self.adjust_column_widths()
        except Exception as e: logging.error(f"Arayüz güncelleme hatası: {e}")

    def detay_goster(self, event):
        sel = self.tree.selection()        
        if not sel: return
        detay = self.analiz_detaylari.get(sel[0])
        if detay:
            gui_utils.show_detail_window(self.root, "17244", detay['tarih'], detay['metar'], detay['full_taf'], detay['detail_str'], 0, detay['dt'], self.robot)

    def on_tree_motion(self, event):
        if self.var_tooltip_aktif.get():
            iid = self.tree.identify_row(event.y)
            if iid and iid in self.analiz_detaylari:
                text = self.analiz_detaylari[iid]['detail_str']
                self.tooltip_manager.show_tooltip(self.tree, event.x_root, event.y_root, text)
            else:
                self.tooltip_manager.hide_tooltip()

    def open_main_search_dialog(self, event=None):
        search_win = tk.Toplevel(self.root)
        search_win.title("Ana Tabloda Ara")
        search_win.geometry("380x140")
        search_win.transient(self.root)
        search_win.resizable(False, False)

        f_top = tk.Frame(search_win)
        f_top.pack(pady=10)

        tk.Label(f_top, text="Metin:").pack(side="left")
        entry_search = tk.Entry(f_top, width=25)
        entry_search.pack(side="left", padx=5)
        entry_search.focus_set()

        lbl_status = tk.Label(search_win, text="", fg="gray")
        lbl_status.pack()

        search_data = {"matches": [], "idx": -1}

        def clear_search_tags():
            for item in search_data["matches"]:
                try:
                    tags = list(self.tree.item(item, "tags"))
                    if "search_yellow" in tags:
                        tags.remove("search_yellow")
                        self.tree.item(item, tags=tags)
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
                
            self.tree.selection_remove(self.tree.selection())
            
            # Ağaçtaki yellow tag'i öncelikli kılmak için her aramada yenile
            self.tree.tag_configure("search_yellow", background="#FFEB3B", foreground="black")
            
            matches = []
            def traverse(parent=""):
                for child in self.tree.get_children(parent):
                    text = str(self.tree.item(child)["text"]).lower()
                    vals = [str(v).lower() for v in self.tree.item(child)["values"]]
                    if term in text or any(term in v for v in vals):
                        matches.append(child)
                        tags = list(self.tree.item(child, "tags"))
                        if "search_yellow" not in tags:
                            tags.append("search_yellow")
                            self.tree.item(child, tags=tags)
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
            self.tree.selection_set(item_id)
            self.tree.see(item_id)
            lbl_status.config(text=f"Sonuç: {search_data['idx']+1} / {len(search_data['matches'])}")

        entry_search.bind("<Return>", do_search)
        f_btns = tk.Frame(search_win)
        f_btns.pack(pady=5, fill="x")
        tk.Button(f_btns, text="ARA", command=do_search, width=10, bg="#B0BEC5").pack(side="left", padx=10, expand=True)
        tk.Button(f_btns, text="< ÖNCEKİ", command=lambda: navigate(-1), width=10).pack(side="left", padx=5, expand=True)
        tk.Button(f_btns, text="SONRAKİ >", command=lambda: navigate(1), width=10).pack(side="left", padx=10, expand=True)

    def show_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Tümünü Seç (Ctrl+A)", command=self.select_all_tree)
        menu.add_command(label="Seçili Satırları Kopyala (Ctrl+C)", command=self.copy_selection)
        menu.add_command(label="Tüm Tabloyu Kopyala", command=self.copy_all_table)
        menu.add_separator()
        menu.add_command(label="Tabloda Ara... (Ctrl+F)", command=self.open_main_search_dialog)
        menu.add_separator()
        
        def set_tree_filter(f_val):
            try:
                self.cp_widgets['cb_trend_filtre'].set(f_val)
                if 'mb_filter' in self.cp_widgets:
                    self.cp_widgets['mb_filter'].config(text=f_val if f_val != "HEPSİ" else "TÜMÜNÜ GÖSTER")
                if 'mb_hist_filter' in self.cp_widgets:
                    self.cp_widgets['mb_hist_filter'].config(text=f_val if f_val != "HEPSİ" else "TÜMÜNÜ GÖSTER")
            except: pass
            if self.app_state.get("last_grouped_data"):
                self.populate_tree(self.app_state["last_grouped_data"], f_val)

        filter_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Türe Göre Filtrele", menu=filter_menu)
        filter_menu.add_command(label="Tümünü Göster", command=lambda: set_tree_filter("HEPSİ"))
        filter_menu.add_command(label="Sadece METAR / SPECI", command=lambda: set_tree_filter("METAR"))
        filter_menu.add_command(label="Sadece TAF", command=lambda: set_tree_filter("TAF"))
        filter_menu.add_command(label="Sadece SİNOPTİK", command=lambda: set_tree_filter("SİNOPTİK"))
        menu.add_separator()
        
        if iid:
            if iid not in self.tree.selection():
                self.tree.selection_set(iid)
            
            # --- YENİ: BİRLEŞİK ÇÖZÜMLEME MENÜSÜ ---
            values = self.tree.item(iid, "values")
            bulten_metni = values[4] if len(values) > 4 else ""
            tur_metni = self.tree.item(iid, "text")
            full_text_for_check = (tur_metni + " " + bulten_metni).upper()
            
            decode_menu = tk.Menu(menu, tearoff=0)
            menu.add_cascade(label="🔍 Çözümle", menu=decode_menu)
            
            decode_menu.add_command(label="SİNOPTİK", command=lambda: self.show_decode_window("SİNOPTİK", bulten_metni))
            decode_menu.add_command(label="METAR", command=lambda: self.show_decode_window("METAR", bulten_metni))
            decode_menu.add_command(label="TAF", command=lambda: self.show_decode_window("TAF", bulten_metni))
            
            decode_menu.entryconfig("SİNOPTİK", state="normal" if any(x in full_text_for_check for x in ["SİNOPTİK", "SINOPTIK", "SYNOP", "AAXX", "SITT", "SM"]) else "disabled")
            decode_menu.entryconfig("METAR", state="normal" if any(x in full_text_for_check for x in ["METAR", "SPECI", "SATT", "SA", "SP"]) else "disabled")
            decode_menu.entryconfig("TAF", state="normal" if any(x in full_text_for_check for x in ["TAF", "FCTT", "FC", "FT"]) else "disabled")
            # -----------------------------------------
            menu.add_separator()
            
        # Ana Arayüz (Tüm Liste) Aktarımı
        menu.add_command(label="Tüm Listeyi Excel'e Aktar", command=self.export_to_excel)
        
        if iid:
            tags = self.tree.item(iid, "tags")
            if "LATE_ARRIVAL" in tags and hasattr(self, 'export_late_arrivals_excel'):
                menu.add_separator()
                export_menu = tk.Menu(menu, tearoff=0)
                menu.add_cascade(label="Geç Gelenleri Aktar", menu=export_menu)
                export_menu.add_command(label="Excel Olarak", command=self.export_late_arrivals_excel)
                export_menu.add_command(label="TXT Olarak", command=self.export_late_arrivals_txt)

            # Trend Uyum (Uyumsuz/Dikkat)
            if any(t in tags for t in ["UYUMSUZ", "DIKKAT", "F_UYUMSUZ"]):
                menu.add_separator()
                export_menu_trend = tk.Menu(menu, tearoff=0)
                menu.add_cascade(label="Uyumsuz/Dikkat Aktar", menu=export_menu_trend)
                export_menu_trend.add_command(label="Excel Olarak", command=lambda: self.export_trend_issues_excel(tags))
                export_menu_trend.add_command(label="TXT Olarak", command=lambda: self.export_trend_issues_txt(tags))
            
        menu.add_separator()
        export_visible_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Ekranda Görünenleri Aktar", menu=export_visible_menu)
        export_visible_menu.add_command(label="Excel Olarak", command=self.export_visible_to_excel)
        export_visible_menu.add_command(label="Tümü (Excel)", command=lambda: self.export_visible_to_excel(only_uyumsuz=False))
        export_visible_menu.add_command(label="Sadece Uyumsuzlar (Excel)", command=lambda: self.export_visible_to_excel(only_uyumsuz=True))
        export_visible_menu.add_command(label="TXT Olarak", command=self.export_visible_to_txt)

        menu.tk_popup(event.x_root, event.y_root)

    def export_trend_issues_excel(self, tags):
        """Uyumsuz/Dikkat kayıtlarını Excel'e aktarır"""
        from tkinter import filedialog
        import pandas as pd
        
        # Aktif ay ismini al
        month_name = datetime.now(timezone.utc).strftime('%B').title()
        if hasattr(self, 'tree_uncomp'):
            items = self.tree_uncomp.get_children()
            data = []
            for item in items:
                values = self.tree_uncomp.item(item, 'values')
                if values:
                    data.append(values)
            
            if data:
                df = pd.DataFrame(data)
                file_path = f"{month_name}_UYUMSUZ.xlsx"
                df.to_excel(file_path, index=False, sheet_name="Uyumsuz")
                messagebox.showinfo("Başarılı", f"Excel dosyası kaydedildi:\n{file_path}")
            else:
                messagebox.showwarning("Uyarı", "Dışa aktar için veri yok.")
    
    def export_trend_issues_txt(self, tags):
        """Uyumsuz/Dikkat kayıtlarını TXT'ye aktarır"""
        import pandas as pd
        
        month_name = datetime.now(timezone.utc).strftime('%B').title()
        if hasattr(self, 'tree_uncomp'):
            items = self.tree_uncomp.get_children()
            data = []
            for item in items:
                values = self.tree_uncomp.item(item, 'values')
                if values:
                    data.append(' | '.join(str(v) for v in values))
            
            if data:
                file_path = f"{month_name}_UYUMSUZ.txt"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(data))
                messagebox.showinfo("Başarılı", f"TXT dosyası kaydedildi:\n{file_path}")
            else:
                messagebox.showwarning("Uyarı", "Dışa aktar için veri yok.")

    def show_decode_window(self, report_type, raw_text):
        if not raw_text.strip(): return
        
        win = tk.Toplevel(self.root)
        win.title(f"🔍 {report_type} Çözümleyici")
        win.geometry("520x680")
        win.configure(bg="#F5F5F5")
        
        btn_frame = tk.Frame(win, bg="#F5F5F5")
        btn_frame.pack(side="bottom", fill="x", pady=5)
        
        btn_close = tk.Button(btn_frame, text="KAPAT", command=win.destroy, bg="#D32F2F", fg="white", font=("Segoe UI", 10, "bold"), width=15, relief="flat", cursor="hand2")
        btn_close.pack(pady=5)
        
        txt = tk.Text(win, padx=10, pady=10, font=("Consolas", 10), bg="#F5F5F5")
        txt.pack(fill="both", expand=True)
        
        detay = ""
        if report_type == "SİNOPTİK":
            try:
                # KULLANICI İSTEĞİ: PHP yerine Python tabanlı synop_decoder.py kullanılıyor.
                dec = SynopDecoder()
                
                # Ham bülten metnini temizle
                temiz_metin = re.sub(r'^(?:SİNOPTİK|SYNOP|SINOPTIK|KAYIT:.*?BULTEN\s*:|BULTEN\s*:|.*GELDİ:|.*YENİ RASAT)\s*', '', raw_text, flags=re.IGNORECASE|re.DOTALL).strip()
                
                # Çözümleme yap
                ham_cozum = dec.decode_line(temiz_metin)
                
                # Okunabilir metne çevir
                detay = dec.generate_human_readable(ham_cozum)
                
                if not detay or "Çözümlenecek veri bulunamadı" in detay:
                    detay = "SİNOPTİK bülteni çözümlenemedi veya format hatalı."
                    
            except Exception as e:
                detay = f"Çözümleme hatası: {e}"
        else:
            try:
                temiz_metin = re.sub(r'^(?:KAYIT:.*?BULTEN\s*:|BULTEN\s*:|.*GELDİ:|.*YENİ RASAT)\s*', '', raw_text, flags=re.IGNORECASE|re.DOTALL).strip()
                if report_type == "METAR":
                    m = re.search(r'(METAR|SPECI|SATT\d*|SA[A-Z0-9]{2}|SP[A-Z0-9]{2})', temiz_metin)
                    if m: temiz_metin = temiz_metin[m.start():]
                elif report_type == "TAF":
                    m = re.search(r'(TAF|FCTT\d*|FC[A-Z0-9]{2}|FT[A-Z0-9]{2})', temiz_metin)
                    if m: temiz_metin = temiz_metin[m.start():]
                
                body = self.robot._extract_body(temiz_metin)
                wind = self.robot._parse_wind(body)
                vis = self.robot._parse_visibility(body)
                
                # YENİ: Detaylı Bulut Çözümlemesi
                cloud_dict = {"FEW": "Az Bulutlu (1-2/8)", "SCT": "Parçalı Bulutlu (3-4/8)", "BKN": "Çok Bulutlu (5-7/8)", "OVC": "Kapalı (8/8)", "VV": "Dikey Görüş"}
                cloud_matches = re.findall(r'\b(FEW|SCT|BKN|OVC|VV)(\d{3})(CB|TCU|///)?\b', body)
                
                temp, dew = self.robot._parse_temp_dew(body) if report_type == "METAR" else (None, None)
                qnh = self.robot._parse_qnh(body) if report_type == "METAR" else None
                
                detay += f"• RÜZGAR:\n"
                if wind and wind != (0, 0):
                    yon, hiz = wind[:2]
                    gust = wind[2] if len(wind)>2 else 0
                    yon_str = "Değişken (VRB)" if yon == -1 else f"{yon}°"
                    detay += f"   - Yön  : {yon_str}\n   - Hız  : {hiz} KT\n"
                    if gust: detay += f"   - Hamle: {gust} KT (GUST)\n"
                else: detay += "   - Sakin (veya anlaşılamadı).\n"
                
                ws_matches = re.findall(r'\bWS\s+(R\d{2}[LCR]?|ALL\s+RWY)\b', body)
                if ws_matches:
                    detay += f"\n• RÜZGAR KESMESİ (WIND SHEAR):\n"
                    for ws in ws_matches:
                        rwy_str = "Tüm Pistler" if "ALL" in ws else f"Pist {ws}"
                        detay += f"   - {rwy_str} yüzeyinde Wind Shear (Rüzgar Kesmesi) uyarısı.\n"
                
                detay += f"\n• GÖRÜŞ MESAFESİ:\n"
                if vis == 10000: detay += "   - 10 km veya daha fazla (CAVOK/9999)\n"
                elif vis: detay += f"   - {vis} metre\n"
                else: detay += "   - Bulunamadı\n"
                
                rvr_raw_matches = re.findall(r'\bR\d{2}[LCR]?/[MP]?\d{4}(?:V[MP]?\d{4})?[UDPN]?\b', body)
                if rvr_raw_matches:
                    detay += f"\n• PİST GÖRÜŞ MESAFESİ (RVR):\n"
                    for rvr in rvr_raw_matches:
                        try:
                            rwy = re.search(r'R(\d{2}[LCR]?)', rvr).group(1)
                            vis_part = rvr.split('/')[1]
                            desc = f"   - Pist {rwy}: "
                            
                            if 'V' in vis_part:
                                parts = vis_part.split('V')
                                min_v = parts[0]
                                max_v = parts[1][:4] if len(parts)>1 else ""
                                trend = parts[1][4:] if len(parts[1])>4 else ""
                                
                                if min_v.startswith('M'): min_v = f"{min_v[1:]}m'den az"
                                elif min_v.startswith('P'): min_v = f"{min_v[1:]}m'den fazla"
                                else: min_v = f"{min_v}m"
                                
                                if max_v.startswith('M'): max_v = f"{max_v[1:]}m'den az"
                                elif max_v.startswith('P'): max_v = f"{max_v[1:]}m'den fazla"
                                else: max_v = f"{max_v}m"
                                
                                desc += f"{min_v} ile {max_v} arası değişken"
                            else:
                                v_val = vis_part[:4]
                                trend = vis_part[4:] if len(vis_part)>4 else ""
                                
                                if v_val.startswith('M'): desc += f"{v_val[1:]}m'den az"
                                elif v_val.startswith('P'): desc += f"{v_val[1:]}m'den fazla"
                                else: desc += f"{v_val}m"
                                
                            if 'U' in trend: desc += " (Artıyor)"
                            elif 'D' in trend: desc += " (Azalıyor)"
                            elif 'N' in trend: desc += " (Değişmiyor)"
                            elif 'P' in trend: desc += " (Değerlendirilemiyor)"
                            
                            detay += f"{desc}\n"
                        except:
                            detay += f"   - {rvr}\n"
                
                detay += f"\n• BULUTLAR / TAVAN:\n"
                cloud_matches = re.findall(r'\b(FEW|SCT|BKN|OVC|VV)(\d{3}|///)(CB|TCU|///)?\b', body)
                if cloud_matches:
                    for tip, yuk, ekstra in cloud_matches:
                        tur_tr = cloud_dict.get(tip, tip)
                        yuk_ft = int(yuk) * 100
                        eks_tr = " [Kümülonimbüs / Oraj Bulutu]" if ekstra == "CB" else (" [Kule Yapan Kümülüs]" if ekstra == "TCU" else "")
                        detay += f"   - {tur_tr}, {yuk_ft} ft{eks_tr}\n"
                        if yuk == '///':
                            yuk_str = "Bilinmeyen yükseklik"
                        else:
                            yuk_ft = int(yuk) * 100
                            yuk_str = f"{yuk_ft} ft"
                        
                        eks_tr = ""
                        if ekstra == "CB": eks_tr = " [Kümülonimbüs / Oraj Bulutu]"
                        elif ekstra == "TCU": eks_tr = " [Kule Yapan Kümülüs]"
                        elif ekstra == "///": eks_tr = " [Tespit Edilemiyor]"
                        
                        detay += f"   - {tur_tr}, {yuk_str}{eks_tr}\n"
                elif "CAVOK" in body or "SKC" in body or "NSC" in body or "CLR" in body:
                    detay += "   - Bulut tespit edilmedi (CAVOK/SKC/NSC)\n"
                else: detay += "   - Bulunamadı veya Gök Yüzü Görünmüyor\n"
                    
                detay += f"\n• HAVA HADİSESİ:\n"
                wx_tr_dict = {
                    "RA": "Yağmur", "SN": "Kar", "TS": "Oraj (Gök Gürültülü Fırtına)", 
                    "FG": "Sis", "BR": "Pus", "HZ": "Duman/Pus", "DZ": "Çisenti", 
                    "GR": "Dolu", "GS": "Küçük Dolu", "SG": "Kar Taneleri", "PL": "Buz Taneleri",
                    "FZ": "Donan", "SH": "Sağanak", "MI": "Sığ", "BC": "Parçalı", "PR": "Kısmi",
                    "BL": "Savrulan", "DR": "Sürüklenen", "SS": "Kum Fırtınası", "DS": "Toz Fırtınası",
                    "VA": "Volkanik Kül", "FU": "Duman", "DU": "Toz", "SA": "Kum", "UP": "Bilinmeyen Yağış", "VC": "Civarda"
                }
                wx_raw_matches = re.findall(r'\b(?:\-|\+|VC)?(?:TS|SH|FZ|BL|DR|MI|BC|PR|RA|DZ|SN|SG|PL|GR|GS|UP|FG|BR|HZ|FU|VA|DU|SA|SS|DS){1,3}\b', body)
                
                if wx_raw_matches:
                    for w_code in set(wx_raw_matches):
                        desc = w_code
                        prefix = ""
                        if w_code.startswith("+"): prefix = "Kuvvetli "; w_code = w_code[1:]
                        elif w_code.startswith("-"): prefix = "Hafif "; w_code = w_code[1:]
                        elif w_code.startswith("VC"): prefix = "Civarda "; w_code = w_code[2:]
                        
                        parts = [w_code[i:i+2] for i in range(0, len(w_code), 2)]
                        parts_tr = [wx_tr_dict.get(p, p) for p in parts]
                        detay += f"   - {prefix}{' '.join(parts_tr)} ({desc})\n"
                else: detay += "   - Önemli hadise yok (NSW Veya Bulunmadı)\n"
                
                recent_matches = re.findall(r'\bRE([A-Z]{2,})\b', body)
                if recent_matches:
                    detay += f"\n• GEÇMİŞ HAVA HADİSESİ (RECENT):\n"
                    for r_code in recent_matches:
                        parts = [r_code[i:i+2] for i in range(0, len(r_code), 2)]
                        parts_tr = [wx_tr_dict.get(p, p) for p in parts]
                        detay += f"   - Geçmişte: {' '.join(parts_tr)} (RE{r_code})\n"
                    
                if report_type == "METAR":
                    if temp is not None: detay += f"\n• SICAKLIK / İŞBA:\n   - Sıcaklık: {temp}°C\n   - Çiy Noktası: {dew}°C\n"
                    if qnh is not None: detay += f"\n• BASINÇ (QNH):\n   - {qnh} hPa\n"

                if report_type == "TAF":
                    trends = self.robot._parse_all_taf_trends(temiz_metin)
                    if trends:
                        detay += f"\n• TAF BEKLENTİLERİ (TRENDLER):\n"
                        for t in trends: 
                            detay += f"   ➤ {t['type']} {t['time'] if t['time'] else ''}\n"
                            if t['wind'] and t['wind'] != (0,0):
                                g_str = f" (Hamle: {t['wind'][2]})" if len(t['wind'])>2 and t['wind'][2] else ""
                                detay += f"      Rüzgar: {t['wind'][1]} KT{g_str}\n"
                            if t['vis']: detay += f"      Görüş: {'10+ km' if t['vis']==10000 else str(t['vis'])+'m'}\n"
                            
                            c_matches = re.findall(r'\b(FEW|SCT|BKN|OVC|VV)(\d{3})(CB|TCU)?\b', t.get('raw',''))
                            if c_matches:
                                c_str = ", ".join([f"{cloud_dict.get(c[0],c[0])} {int(c[1])*100}ft" for c in c_matches])
                                detay += f"      Bulut : {c_str}\n"
                            elif "CAVOK" in t.get('raw','') or "SKC" in t.get('raw',''):
                                detay += f"      Bulut : CAVOK/SKC\n"
                                
                            if t['wx']:
                                w_strs = [wx_tr_dict.get(w,w) for w in t['wx']]
                                detay += f"      Hadise: {', '.join(w_strs)}\n"
            except Exception as e:
                detay = f"Çözümleme hatası: {e}"
        
        txt.insert("1.0", f"SEÇİLEN METİN:\n{raw_text.strip()}\n\n" + "="*40 + "\n\nÇÖZÜMLENEN BİLGİLER:\n\n" + detay)
        
        # --- STİLLER VE RENKLENDİRME (TAGS) ---
        txt.tag_config("baslik", font=("Consolas", 11, "bold"), foreground="#0D47A1")
        txt.tag_config("kisim_baslik", font=("Consolas", 11, "bold"), foreground="#E65100", background="#FFF3E0")
        txt.tag_config("madde", font=("Consolas", 10, "bold"), foreground="#2E7D32")
        txt.tag_config("deger", font=("Consolas", 10, "bold"), foreground="#1565C0")
        txt.tag_config("ham_veri", foreground="#757575", font=("Consolas", 10, "italic"))
        
        # 1. Ana Başlıklar
        for kw in ["SEÇİLEN METİN:", "ÇÖZÜMLENEN BİLGİLER:", "• RÜZGAR:", "• GÖRÜŞ MESAFESİ:", "• BULUTLAR / TAVAN:", "• HAVA HADİSESİ:", "• SICAKLIK / İŞBA:", "• BASINÇ (QNH):", "• TAF BEKLENTİLERİ (TRENDLER):"]:
            start = "1.0"
            while True:
                pos = txt.search(kw, start, tk.END)
                if not pos: break
                txt.tag_add("baslik", pos, f"{pos}+{len(kw)}c")
                start = f"{pos}+{len(kw)}c"
                
        # 2. SİNOPTİK Kısım Başlıkları ve Ayıraçlar (Eski ve Yeni Format Desteği)
        for kw in ["KISIM 0", "KISIM 1", "KISIM 3", "KISIM 5", "==================================================", "🔹 BÖLÜM 0", "🔹 BÖLÜM 1", "🔹 BÖLÜM 2", "🔹 BÖLÜM 3", "🔹 BÖLÜM 4", "🔹 BÖLÜM 5"]:
            start = "1.0"
            while True:
                pos = txt.search(kw, start, tk.END)
                if not pos: break
                line_end = txt.index(f"{pos} lineend")
                txt.tag_add("kisim_baslik", pos, line_end)
                start = line_end
                
        # 3. Maddeler ve Değerler İçin Dinamik Boyama (Eski '• ' ve Yeni ' : ' formatı)
        start = "1.0"
        while True:
            pos_bullet = txt.search("• ", start, tk.END)
            pos_colon = txt.search(" : ", start, tk.END)
            
            if not pos_bullet and not pos_colon:
                break
                
            if pos_bullet and pos_colon:
                if txt.compare(pos_bullet, "<", pos_colon):
                    pos = pos_bullet
                    is_bullet = True
                else:
                    pos = pos_colon
                    is_bullet = False
            elif pos_bullet:
                pos = pos_bullet
                is_bullet = True
            else:
                pos = pos_colon
                is_bullet = False
            
            line_start = txt.index(f"{pos} linestart")
            line_end = txt.index(f"{pos} lineend")
            
            if is_bullet:
                colon_pos = txt.search(":", pos, line_end)
                if colon_pos:
                    txt.tag_add("madde", pos, f"{colon_pos}+1c")
                    line_text = txt.get(f"{colon_pos}+1c", line_end)
                    m = re.search(r'(\([^)]+\))\s*$', line_text)
                    if m:
                        paren_start_offset = m.start(1)
                        paren_pos = f"{colon_pos}+1c + {paren_start_offset}c"
                        txt.tag_add("deger", f"{colon_pos}+1c", paren_pos)
                        txt.tag_add("ham_veri", paren_pos, line_end)
                    else:
                        txt.tag_add("deger", f"{colon_pos}+1c", line_end)
            else:
                # Yeni format: "12470 : Açıklama"
                txt.tag_add("madde", line_start, pos)
                txt.tag_add("deger", f"{pos}+3c", line_end)
            
            start = line_end
            
        # 4. Yeni SİNOPTİK formatı için Alt Kırılımları (Örn: "01: Ayın 1. günü") renklendirme
        start = "1.0"
        while True:
            pos = txt.search(r'^\s*[0-9a-zA-Z/]+:', start, tk.END, regexp=True)
            if not pos: break
            
            line_end = txt.index(f"{pos} lineend")
            colon_pos = txt.search(":", pos, line_end)
            
            if colon_pos:
                if not txt.search(" : ", pos, line_end) and not txt.search("• ", pos, line_end):
                    txt.tag_add("ham_veri", pos, f"{colon_pos}+1c")
                    txt.tag_add("deger", f"{colon_pos}+1c", line_end)
                    
            start = line_end

        txt.config(state="disabled")

    def copy_selection(self, event=None):
        sel = self.tree.selection()
        if sel:
            text = "\n".join(["\t".join(map(str, self.tree.item(i)['values'])) for i in sel])
            self.root.clipboard_clear()
            self.root.clipboard_append(text)

    def set_station_from_selection(self, sel):
        self.settings_vars['var_oto_yenile'].set(False) # İstasyon değişirse OTO devre dışı
        wmo = "17244"
        if "(" in sel: wmo = sel.split("(")[-1].replace(")", "").strip()
        self.scraper.set_station(wmo)
        self.lbl_title.config(text=sel)
        self.settings_vars['var_last_station'].set(sel)
        self.verileri_cek()

    def on_meydan_selected(self, event):
        self.var_active_station_type.set("MEYDAN")
        self.set_station_from_selection(self.cp_widgets['cb_meydan'].get())

    def on_sinoptik_selected(self, event):
        self.var_active_station_type.set("SİNOPTİK")
        self.set_station_from_selection(self.cp_widgets['cb_sinoptik'].get())

    def on_manual_station_search(self, st_id):
        self.settings_vars['var_oto_yenile'].set(False) # İstasyon değişirse OTO devre dışı
        st_id = st_id.upper().strip()
        if st_id in ICAO_TO_WMO: st_id = ICAO_TO_WMO[st_id]
        self.scraper.set_station(st_id)
        
        display_text = st_id
        for name in self.station_data_store["TÜMÜ"]:
            if st_id in name:
                display_text = name
                break
        self.settings_vars['var_last_station'].set(display_text)
        self.lbl_title.config(text=display_text)
        self.verileri_cek()

    def update_station_list_ui(self):
        def _worker():
            web_stations = self.scraper.fetch_station_list()
            if web_stations:
                # Listeyi güncelle
                pass
        threading.Thread(target=_worker).start()

    def open_map_window(self):
        import turkey_map # Açılışı hızlandırmak için sadece harita açılırken yükle (Lazy Import)
        
        app_instance = self

        class MapContext:
            def __init__(self):
                self.incompatible_df = pd.DataFrame()
            def add_to_monitor(self, rows): pass
            def open_detail_window(self, event=None, external_tree=None, external_df=None): pass
            def log_incompatibility(self, station_name, reason, metar_data, taf_data="N/A"):
                if hasattr(app_instance, 'log_incompatibility'):
                    app_instance.log_incompatibility(station_name, reason, metar_data, taf_data)
        
        init_date = {"day": self.cp_widgets['cb_gun'].get(), "month": self.cp_widgets['cb_ay'].get(), "year": self.cp_widgets['cb_yil'].get()}
        turkey_map.open_turkey_map(self.root, MapContext(), self.robot, self.tooltip_manager, initial_type=self.var_active_station_type.get(), initial_date=init_date)

    def cancel_history(self):
        self.history_cancel_event.set()
        self.lbl_status.config(text="İptal ediliyor...", fg="#D32F2F")

    def trend_history(self, use_main_date=False, initial_filter="HEPSİ"):
        """Geçmiş verileri çeker, analiz eder ve tabloya yansıtır."""
        if use_main_date:
            ay = self.cp_widgets['cb_ay'].get()
            yil = self.cp_widgets['cb_yil'].get()
            btn_widget = self.cp_widgets['btn_goster_btn']
        else:
            ay = self.cp_widgets['cb_ay_history'].get()
            yil = self.cp_widgets['cb_yil_history'].get()
            btn_widget = self.cp_widgets['btn_trend_history']
        
        self.lbl_status.config(text=f"Geçmiş veriler aranıyor: {ay} {yil}...")
        btn_widget.config(state="disabled")
        self.history_cancel_event.clear()
        
        def _worker():
            try:
                all_logs = []
                aylar_listesi = [ay] if ay != "TÜM YIL" else ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
                
                for current_ay in aylar_listesi:
                    if not self.root.winfo_exists() or self.history_cancel_event.is_set():
                        break
                        
                    # Ayın son gününü hesapla
                    ay_map = self.scraper.config.get("ay_map", {})
                    if current_ay in ay_map: ay_num = int(ay_map[current_ay])
                    else:
                        tr_months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
                        ay_num = tr_months.index(current_ay) + 1 if current_ay in tr_months else 1
                    
                    yil_num = int(yil)
                    
                    # Gelecek ayları (henüz yaşanmamış) taramayı engelle
                    now_utc = datetime.now(timezone.utc)
                    if yil_num == now_utc.year and ay_num > now_utc.month:
                        continue
                        
                    _, last_day = calendar.monthrange(yil_num, ay_num)

                    # --- Önceki Ayın Son TAF'ını Çek (00:xx METAR'ları için) ---
                    try:
                        # Ayın ilk gününden bir önceki günün 22:40 TAF'ını çek
                        first_day_of_month = datetime(yil_num, ay_num, 1)
                        prev_dt = first_day_of_month - timedelta(days=1)
                        
                        tr_months_local = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
                        prev_g = str(prev_dt.day).zfill(2)
                        prev_a = tr_months_local[prev_dt.month - 1]
                        prev_y = str(prev_dt.year)
                        
                        taf_id = self.scraper.config.get("filtre_map", {}).get("Taf", "2")
                        if not taf_id: taf_id = "2"
                        
                        self.root.after(0, lambda p_g=prev_g, p_a=prev_a: self.lbl_status.config(text=f"Önceki ayın TAF'ı aranıyor... ({p_g} {p_a})"))
                        
                        prev_tafs_web = self.scraper.fetch_logs(prev_g, prev_a, prev_y, taf_id)
                        if prev_tafs_web:
                            target_tafs = [x for x in prev_tafs_web if "22:40" in x[4]]
                            if target_tafs: 
                                all_logs.extend(target_tafs)
                                logging.info(f"Geçmiş analiz için önceki ayın 22:40 TAF'ı web'den eklendi: {len(target_tafs)} adet.")
                    except Exception as e:
                        logging.warning(f"Geçmiş analiz için önceki ay TAF çekme hatası: {e}")

                    # --- PARALEL VERİ ÇEKME ---
                    with ThreadPoolExecutor(max_workers=8) as executor:
                        future_to_day = {
                            executor.submit(self.scraper.fetch_logs, str(day).zfill(2), current_ay, yil, "500"): day
                            for day in range(1, last_day + 1)
                        }

                        for i, future in enumerate(as_completed(future_to_day)):
                            if not self.root.winfo_exists() or self.history_cancel_event.is_set():
                                for f in future_to_day: f.cancel()
                                self.root.after(0, lambda: self.lbl_status.config(text="İşlem iptal edildi."))
                                return

                            day = future_to_day[future]
                            try:
                                part_logs = future.result()
                                if part_logs:
                                    all_logs.extend(part_logs)
                            except Exception as exc:
                                logging.warning(f"Geçmiş analizi için gün {day} çekilemedi: {exc}")

                            pct = int(((i + 1) / last_day) * 100)
                            if ay == "TÜM YIL":
                                self.root.after(0, lambda p=pct, d=day, c_a=current_ay: self.lbl_status.config(text=f"Yıllık tarama ({c_a}): %{p} (Gün {d}) indiriliyor..."))
                            else:
                                self.root.after(0, lambda p=pct, d=day: self.lbl_status.config(text=f"Geçmiş veri indiriliyor... %{p} (Gün {d})"))
                
                # Tekilleştirme
                seen = set()
                unique_logs = []
                for log in all_logs:
                    t_log = tuple(log)
                    if t_log not in seen:
                        seen.add(t_log)
                        unique_logs.append(log)
                
                logs = unique_logs
                
                if logs:
                    grouped = process_and_analyze_logs(logs, self.robot)
                    self.apply_dual_taf_analysis(grouped)
                    if hasattr(self, 'clean_invalid_re_rules'): self.clean_invalid_re_rules(grouped)
                    self.app_state["last_grouped_data"] = grouped
                    self.root.after(0, lambda: self.lbl_status.config(text=f"Geçmiş veri yüklendi: {len(logs)} kayıt."))
                    
                    # --- AYLIK KAYIT DOSYASINA YAZMA ---
                    try:
                        # --- GECİKME ANALİZİ VE SIRALAMA HAZIRLIĞI ---
                        all_items_for_report = []
                        for group in grouped:
                            if group['taf']: all_items_for_report.append(group['taf'])
                            all_items_for_report.extend(group['observations'])
                        
                        # GUI'deki gibi Rasat Tarihine göre sırala
                        def get_sort_key_report(item):
                            dt = item.get('dt')
                            if not dt or not isinstance(dt, datetime) or dt.year < 1900:
                                dt = datetime.max
                            
                            reg = datetime.min
                            if item.get('reg_dt') and isinstance(item['reg_dt'], datetime): reg = item['reg_dt']
                            elif item.get('dt') and isinstance(item['dt'], datetime): reg = item['dt']
                            
                            # Düzeltme önceliği (Aynı kayıt zamanında hangisi kazanır?)
                            # Normal < COR < CCA < CCB ... (Yüksek olan kazanır/üzerine yazar)
                            prio = 0
                            bulten = item.get("bulten", "").upper()
                            if "CCC" in bulten: prio = 6
                            elif "CCB" in bulten: prio = 5
                            elif "CCA" in bulten: prio = 4
                            elif "AAC" in bulten: prio = 3
                            elif "AAB" in bulten: prio = 2
                            elif "AAA" in bulten or "AMD" in bulten or "COR" in bulten: prio = 1
                            return (dt, reg, prio)

                        all_items_for_report.sort(key=get_sort_key_report)

                        # --- FIX: İlk kayıt haritasını filtrelemeden ÖNCE oluştur ---
                        # Böylece gecikme hesabı, düzeltilmiş (silinecek) olsa bile İLK gelen kayda göre yapılır.
                        first_reg_map_report = {}
                        for item in all_items_for_report:
                            if item.get('dt'):
                                typ = item['type'].upper()
                                norm_type = typ
                                if "SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ: norm_type = "SİNOPTİK"
                                elif "METAR" in typ or "SPECI" in typ: norm_type = "METAR"
                                elif "TAF" in typ: norm_type = "TAF"
                                
                                group_dt = item['dt']
                                if norm_type == "TAF":
                                    m_val = re.search(r'\b(\d{4}/\d{4})\b', item.get("bulten", ""))
                                    if m_val: group_dt = m_val.group(1)
                                    else:
                                        m_wmo = re.search(r'\b[A-Z0-9]{4,6}\s+[A-Z]{4}\s+(\d{6})\b', item.get("bulten", ""))
                                        if m_wmo: group_dt = m_wmo.group(1)

                                k = (norm_type, group_dt)
                                if k not in first_reg_map_report:
                                    first_reg_map_report[k] = item

                        # --- YENİ: Sadece en güncel versiyonları ve UYUMSUZ olanları filtrele ---
                        latest_items_map = {}
                        other_items = []
                        special_keywords = ["KLİMA", "KLIMA", "MAX", "MAKSİMUM", "HADİSE", "HADISE"]
                        
                        for item in all_items_for_report:
                            typ = item['type'].upper()
                            bulten = item.get('bulten', '').upper()
                            
                            # Tip Normalizasyonu
                            norm_type = None
                            if any(x in typ for x in ["SİNOPTİK", "SYNOP", "SINOPTIK"]): norm_type = "SİNOPTİK"
                            elif any(x in typ for x in ["METAR", "SPECI"]): norm_type = "METAR"
                            elif "TAF" in typ: norm_type = "TAF"
                            
                            # Özel Veri Kontrolü
                            is_special = any(k in typ or k in bulten for k in special_keywords)

                            # Gruplama Mantığı
                            if norm_type and item.get('dt') and item['dt'].year > 1900:
                                group_dt = item['dt']
                                if norm_type == "TAF":
                                    m_val = re.search(r'\b(\d{4}/\d{4})\b', item.get("bulten", ""))
                                    if m_val: group_dt = m_val.group(1)
                                    else:
                                        m_wmo = re.search(r'\b[A-Z0-9]{4,6}\s+[A-Z]{4}\s+(\d{6})\b', item.get("bulten", ""))
                                        if m_wmo: group_dt = m_wmo.group(1)

                                latest_items_map[(norm_type, group_dt)] = item
                            elif is_special:
                                other_items.append(item)
                        
                        # ANA LİSTE (METAR, TAF, SİNOPTİK - HEPSİ)
                        main_report_items = list(latest_items_map.values())
                        
                        # HARİCİ RASATLAR (KLİMA, MAX RÜZGAR vb.)
                        other_items.sort(key=get_sort_key_report)

                        # --- HAZIRLIK BİTTİ ---
                        
                        # --- FİLTRELEME (AYLIK KAYIT İÇİN) ---
                        # YENİ: Arayüzdeki filtre durumu ne olursa olsun, dosyanın yanlışlıkla 
                        # boş kalmasını engellemek için fiziksel TXT dosyasına HER ZAMAN tüm kayıtlar yazılır.
                        final_main_items = main_report_items
                        write_other_items = True
                        
                        final_main_items.sort(key=get_sort_key_report)
                        # --- FİLTRELEME BİTTİ ---
                        
                        base_log_dir = config_manager.USER_DATA_DIR
                        monthly_dir = os.path.join(base_log_dir, "Aylik_Kayitlar", yil)
                        if not os.path.exists(monthly_dir):
                            os.makedirs(monthly_dir)
                        
                        monthly_file = os.path.join(monthly_dir, f"{ay}.txt")

                        with open(monthly_file, "w", encoding="utf-8") as f:
                            f.write(f"KARDELEN AYLIK ANALİZ RAPORU - {ay} {yil}\n")
                            f.write(f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
                            f.write("="*100 + "\n\n")
                            
                            for idx, obs in enumerate(final_main_items):
                                is_taf = "TAF" in obs['type'].upper()
                                
                                anl = obs.get('analysis')
                                durum = "BİLİNMİYOR"
                                reasons = []
                                ref_taf = "-"
                                res_txt = "-"
                                if anl:
                                    durum = anl.get('durum', 'BİLİNMİYOR').upper()
                                    reasons = anl.get('reasons', [])
                                    ref_taf = anl.get('ref_taf', '-')
                                    
                                    is_re_error = any("GEÇMİŞ HADİSE" in r.upper() for r in reasons)
                                    
                                    if is_re_error: res_txt = "RE/GECMIS HATASI"
                                    elif "F/UYUMSUZ" in durum: res_txt = "F/UYUMSUZ"
                                    elif "UYUMSUZ" in durum: res_txt = "UYUMSUZ"
                                    elif "DİKKAT" in durum: res_txt = "DIKKAT"
                                    elif "UYUMLU" in durum: res_txt = "UYUMLU"
                                    elif "TAF YOK" in durum: res_txt = "TAF_YOK"
                                    elif "DÜZELTİLDİ" in durum: res_txt = "DUZELTILDI"
                                
                                # --- GECİKME KONTROLÜ ---
                                is_late = False
                                delay_minutes = 0
                                if obs.get('dt') and obs['dt'].year > 1900:
                                    typ = obs['type'].upper()
                                    norm_type_late = typ
                                    if "SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ: norm_type_late = "SİNOPTİK"
                                    elif "METAR" in typ or "SPECI" in typ: norm_type_late = "METAR"
                                    elif "TAF" in typ: norm_type_late = "TAF"
                                    
                                    group_dt_late = obs['dt']
                                    if norm_type_late == "TAF":
                                        m_val = re.search(r'\b(\d{4}/\d{4})\b', obs.get("bulten", ""))
                                        if m_val: group_dt_late = m_val.group(1)
                                        else:
                                            m_wmo = re.search(r'\b[A-Z0-9]{4,6}\s+[A-Z]{4}\s+(\d{6})\b', obs.get("bulten", ""))
                                            if m_wmo: group_dt_late = m_wmo.group(1)

                                    k_late = (norm_type_late, group_dt_late)
                                    first_item_in_group = first_reg_map_report.get(k_late)
                                    if first_item_in_group and self.is_obs_late(first_item_in_group):
                                        is_late = True
                                        # Gecikme süresini, gecikmeyi tetikleyen İLK kayda göre hesapla
                                        if first_item_in_group.get('reg_dt') and first_item_in_group.get('dt'):
                                            delay_minutes = self.get_delay_minutes(first_item_in_group)
                                
                                # --- SONRAKİ RASAT KONTROLÜ (UYUMSUZ İÇİN) ---
                                next_obs_info = ""
                                if "UYUMSUZ" in res_txt:
                                    for j in range(idx + 1, len(final_main_items)):
                                        next_item = final_main_items[j]
                                        curr_type = obs['type'].upper()
                                        next_type = next_item['type'].upper()
                                        
                                        is_curr_metar = "METAR" in curr_type or "SPECI" in curr_type
                                        is_next_metar = "METAR" in next_type or "SPECI" in next_type
                                        
                                        if is_curr_metar and is_next_metar:
                                            if obs.get('dt') and next_item.get('dt'):
                                                diff = (next_item['dt'] - obs['dt']).total_seconds() / 60
                                                if 0 < diff < 70:
                                                    next_time = next_item['dt'].strftime("%H:%M") if next_item['dt'].year > 1900 else "---"
                                                    next_st = "BILINMIYOR"
                                                    if next_item.get('analysis'):
                                                        nst = next_item['analysis'].get('durum', '').upper()
                                                        if "UYUMLU" in nst: next_st = "UYUMLU"
                                                        elif "DİKKAT" in nst: next_st = "DİKKAT"
                                                        elif "UYUMSUZ" in nst: next_st = "UYUMSUZ"
                                                    
                                                    next_obs_info = f"   >>> SONRAKİ RASAT: {next_time} {next_item['type']} ({next_st})"
                                            break
                                
                                kull = obs['raw'][1] if len(obs['raw']) > 1 else "-"
                                kayit_tar = obs['raw'][3] if len(obs['raw']) > 3 else "-"
                                
                                # YENİ FORMAT
                                f.write("-" * 100 + "\n")
                                f.write(f"KAYIT: {kayit_tar:<16} | RASAT: {obs['tarih_str']:<16} | {obs['type']:<5} | Kull: {kull}\n")
                                
                                status_line = f"DURUM: {res_txt}"
                                if is_late: status_line += f" [GECİKME: {delay_minutes} dk]"
                                f.write(f"{status_line}\n")
                                
                                if next_obs_info:
                                    f.write(f"{next_obs_info}\n")
                                
                                f.write(f"   BULTEN : {obs['bulten']}\n")
                                
                                # KULLANICI İSTEĞİ: Sinoptik çözümleme aylık kayıttan kaldırıldı, sağ tık menüsüne taşındı.

                                # Detaylı analiz istenmediği için sadece REF TAF yazıyoruz (varsa)
                                # Nedenleri (reasons) yazmıyoruz.
                                if not is_taf and res_txt not in ["-", "TAF_YOK"]:
                                    if ref_taf != "-":
                                        # YENİ: Bültenden sonra gelen istenmeyen verileri temizle
                                        clean_ref_taf = ref_taf.split('=')[0] + '=' if '=' in ref_taf else ref_taf
                                        f.write(f"   ► REF TAF: {clean_ref_taf}\n")
                                    
                                    if "UYUMSUZ" in res_txt and reasons:
                                        for r in reasons: f.write(f"   NEDEN  : {r}\n")
                                
                                # DÜZELTİLMİŞ İSE ESKİ/YENİ TAF FARKINI YAZ (TAF Tipi için de geçerli)
                                if "DUZELTILDI" in res_txt and reasons:
                                    for r in reasons: f.write(f"   ℹ️ {r}\n")

                                f.write("\n")
                            
                            # 2. HARİCİ RASATLAR (Varsa)
                            if write_other_items and other_items:
                                f.write("="*100 + "\n")
                                f.write(">>> HARİCİ RASATLAR (KLİMA, MAX RÜZGAR, HADİSE vb.)\n")
                                f.write("="*100 + "\n\n")
                                
                                for obs in other_items:
                                    kull = obs['raw'][1] if len(obs['raw']) > 1 else "-"
                                    kayit_tar = obs['raw'][3] if len(obs['raw']) > 3 else "-"
                                    
                                    f.write(f"[{kayit_tar}] [{obs['tarih_str']}] (Kull: {kull}) [{obs['type']}]\n")
                                    f.write(f"   BULTEN: {obs['bulten']}\n")
                                    f.write("\n")

                    except Exception as e:
                        logging.error(f"Aylık dosya yazma hatası: {e}")
                    
                    # Sonuç penceresini aç
                    def update_ui_after_history():
                        # Filtreyi sıfırla ve tabloyu doldur
                        self.cp_widgets['cb_trend_filtre'].set(initial_filter)
                        
                        bg_col = "#546E7A"
                        if "UYUMSUZ" in initial_filter: bg_col = "#D32F2F"
                        elif "DİKKAT" in initial_filter: bg_col = "#F57F17"
                        elif "UYUMLU" in initial_filter: bg_col = "#388E3C"
                        elif "GEÇ GELEN" in initial_filter: bg_col = "#E91E63"
                        elif "RASAT YOK" in initial_filter: bg_col = "#5D4037"
                        elif "HARİCİ RASATLAR" in initial_filter: bg_col = "#607D8B"

                        hist_disp_text = initial_filter if initial_filter != "HEPSİ" else "TÜMÜNÜ GÖSTER"

                        # Hem ana filtre butonunu hem de geçmiş filtre butonunu güncelle
                        if 'mb_filter' in self.cp_widgets: self.cp_widgets['mb_filter'].config(text=hist_disp_text, bg=bg_col)
                        if 'mb_hist_filter' in self.cp_widgets: self.cp_widgets['mb_hist_filter'].config(text=hist_disp_text, bg=bg_col)
                        self.populate_tree(grouped, initial_filter)
                        
                    self.root.after(0, update_ui_after_history)
                else:
                    self.root.after(0, lambda: self.lbl_status.config(text="Veri bulunamadı."))
                    self.root.after(0, lambda: messagebox.showwarning("Uyarı", "Bu tarih aralığında veri bulunamadı."))
            except Exception as e:
                self.root.after(0, lambda e=e: messagebox.showerror("Hata", f"Geçmiş veri hatası: {e}"))
            finally:
                self.root.after(0, lambda: btn_widget.config(state="normal"))
                
        threading.Thread(target=_worker).start()

    def load_demo_data(self):
        """Test amaçlı sahte veriler yükler."""
        self.lbl_status.config(text="Demo veriler hazırlanıyor...")
        
        # Sistem saati (Alarm kontrolü için gerekli - check_alarms içindeki tarih kontrolü)
        now_sys = datetime.now(timezone.utc)
        offset_min = self.settings_vars.get('var_test_time_offset', tk.IntVar(value=0)).get()
        now_sys = datetime.now(timezone.utc) + timedelta(minutes=offset_min)
        
        # Veri saati (Logların içeriği için - UTC+3 simülasyonu)
        # process_and_analyze_logs fonksiyonu gelen veriden 3 saat çıkarıyor.
        # Bu yüzden buraya UTC+3 veriyoruz ki sonuç UTC olsun ve now_utc ile eşleşsin.
        now_tr = datetime.now(timezone.utc) # + timedelta(hours=3) # İPTAL: Olduğu gibi al
        now_tr = now_sys # + timedelta(hours=3) # İPTAL: Olduğu gibi al
        now_tr = now_tr.replace(tzinfo=None, microsecond=0)
        
        # Tarih parametreleri (check_alarms için)
        tr_months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        g = str(now_sys.day).zfill(2)
        a = tr_months[now_sys.month - 1]
        y = str(now_sys.year)
        
        d_str = now_tr.strftime("%d.%m.%Y")
        day_str = now_tr.strftime("%d")
        
        # Dinamik saatler (Son 5 rasat)
        times = []
        # En son rasat saati: Şu anki saatin 50. dakikası eğer şu an >= 50 ise, yoksa bir önceki saatin 50. dakikası
        last_obs_time = now_tr.replace(minute=50, second=0)
        if now_tr.minute < 50:
            last_obs_time -= timedelta(hours=1)
            
        for i in range(4, -1, -1):
            t = last_obs_time - timedelta(hours=i)
            times.append(t)
            
        # TAF Saati (En eskiden 1 saat önce)
        taf_time = times[0] - timedelta(hours=1)
        taf_time_str = taf_time.strftime("%d%H%MZ")
        
        # Format: (TÜR, KULL, GOND, KAYIT, RASAT, BULTEN)
        logs = [
            ("TAF", "TEST", taf_time.strftime("%H:%M"), f"{d_str} {taf_time.strftime('%H:%M')}", f"{d_str} {taf_time.strftime('%H:%M')}", 
             f"TAF LTAN {taf_time_str} {day_str}09/{day_str}18 36012KT 9999 SCT030 BKN100 TEMPO {day_str}12/{day_str}15 3000 BR BKN012"),
             
            # times[0] -> En eski veri (4 saat önce).
            ("METAR", "TEST", times[0].strftime("%H:%M"), f"{d_str} {times[0].strftime('%H:%M')}", f"{d_str} {times[0].strftime('%H:%M')}", 
             f"METAR LTAN {times[0].strftime('%d%H%MZ')} 36012KT 0500 FG VV002 15/08 Q1015="), # UYUMSUZ (Görüş/Tavan Düşük)
             
            ("METAR", "TEST", times[1].strftime("%H:%M"), f"{d_str} {times[1].strftime('%H:%M')}", f"{d_str} {times[1].strftime('%H:%M')}", 
             f"METAR LTAN {times[1].strftime('%d%H%MZ')} 20015KT 9999 SCT030 16/08 Q1014="), # UYUMSUZ (Rüzgar)
             
            ("METAR", "TEST", times[2].strftime("%H:%M"), f"{d_str} {times[2].strftime('%H:%M')}", f"{d_str} {times[2].strftime('%H:%M')}", 
             f"METAR LTAN {times[2].strftime('%d%H%MZ')} 36012KT 4000 BR SCT030 14/10 Q1014="), # UYUMSUZ (Görüş)
             
            ("METAR", "TEST", times[3].strftime("%H:%M"), f"{d_str} {times[3].strftime('%H:%M')}", f"{d_str} {times[3].strftime('%H:%M')}", 
             f"METAR LTAN {times[3].strftime('%d%H%MZ')} 36012KT 3000 BR BKN012 13/10 Q1014="), # DİKKAT (TEMPO)
             
            # times[4] -> En son veri (Şu anki saat). Alarmı bu tetikleyecek.
            ("METAR", "TEST", times[4].strftime("%H:%M"), f"{d_str} {times[4].strftime('%H:%M')}", f"{d_str} {times[4].strftime('%H:%M')}", 
             f"METAR LTAN {times[4].strftime('%d%H%MZ')} 36012KT 0500 FG VV002 12/11 Q1014=") # UYUMSUZ (Limit Altı - Son Saat)
        ]
        
        grouped = process_and_analyze_logs(logs, self.robot)
        self.app_state["last_grouped_data"] = grouped
        
        # Alarmın çalması için zamanlayıcıyı sıfırla
        self.app_state["last_alarm_incompatible"] = 0
        
        # Alarm Kontrolünü Tetikle (ÖNEMLİ)
        self.check_alarms(grouped, g, a, y, silent=False)
        
        self.populate_tree(grouped, self.cp_widgets['cb_trend_filtre'].get())
        self.lbl_status.config(text="Demo veriler yüklendi (Simülasyon).")
        messagebox.showinfo("Demo Modu", "Sistem testi için sahte veriler yüklendi.\n\nSon veri (Şu anki saat) UYUMSUZ olarak ayarlandı ve alarm tetiklendi.")

    def export_to_excel(self):
        fname = f"Analiz_{self.cp_widgets['cb_ay'].get()}.xlsx"
        filter_val = self.cp_widgets['cb_trend_filtre'].get()
        use_reg_date = ("GEÇ GELEN" in filter_val)
        
        custom_summary = None
        if "GEÇ GELEN" in filter_val:
            cnt_metar = 0
            cnt_taf = 0
            cnt_synop = 0
            for child in self.tree.get_children():
                text = str(self.tree.item(child)["text"]).upper()
                if "METAR" in text or "SPECI" in text: cnt_metar += 1
                elif "TAF" in text: cnt_taf += 1
                elif "SİNOPTİK" in text or "SYNOP" in text: cnt_synop += 1
            custom_summary = f"ÖZET: METAR: {cnt_metar} | SİNOPTİK: {cnt_synop} | TAF: {cnt_taf}"

        file_ops.export_tree_to_excel(self.tree, self.analiz_detaylari, fname, use_reg_date=use_reg_date, custom_summary=custom_summary)

    def export_history_to_excel(self):
        """Geçmiş verileri Excel'e aktarır."""
        fname = f"Gecmis_Analiz_{self.cp_widgets['cb_ay_history'].get()}_{self.cp_widgets['cb_yil_history'].get()}.xlsx"
        filter_val = self.cp_widgets['cb_trend_filtre'].get()
        use_reg_date = ("GEÇ GELEN" in filter_val)
        
        custom_summary = None
        if "GEÇ GELEN" in filter_val:
            cnt_metar = 0
            cnt_taf = 0
            cnt_synop = 0
            for child in self.tree.get_children():
                text = str(self.tree.item(child)["text"]).upper()
                if "METAR" in text or "SPECI" in text: cnt_metar += 1
                elif "TAF" in text: cnt_taf += 1
                elif "SİNOPTİK" in text or "SYNOP" in text: cnt_synop += 1
            custom_summary = f"ÖZET: METAR: {cnt_metar} | SİNOPTİK: {cnt_synop} | TAF: {cnt_taf}"

        file_ops.export_tree_to_excel(self.tree, self.analiz_detaylari, fname, use_reg_date=use_reg_date, custom_summary=custom_summary)

    def save_detailed_log(self):
        file_ops.save_detailed_log_file(self.tree, self.analiz_detaylari)

    def on_trend_filter_change(self, event):
        if self.app_state["last_grouped_data"]:
            self.populate_tree(self.app_state["last_grouped_data"], self.cp_widgets['cb_trend_filtre'].get())

    def on_hist_filter_change(self, event):
        pass

    def open_station_selector_window(self):
        gui_station_selector.open_station_selector(self.root, self.cp_widgets, self.set_station_from_selection)

    def toggle_uyum_col(self):
        if self.var_uyum_show.get():
            self.tree["displaycolumns"] = "#all"
        else:
            self.tree["displaycolumns"] = tuple([c for c in ("KULL.", "GÖND.", "KAYIT TAR.", "RASAT TAR.", "BÜLTEN")])
        
        # Sütun genişliklerini güncelle (Bültenin yayılması için)
        self.root.after(50, self.adjust_column_widths)

    def toggle_old_versions(self):
        if self.app_state.get("last_grouped_data"):
            self.populate_tree(self.app_state["last_grouped_data"], self.cp_widgets['cb_trend_filtre'].get())

    def toggle_other_obs(self):
        if self.app_state.get("last_grouped_data"):
            self.populate_tree(self.app_state["last_grouped_data"], self.cp_widgets['cb_trend_filtre'].get())

    def silence_alarm(self):
        self.app_state["silence_end_time"] = time.time() + 600
        base_text = self.lbl_alarm_info.cget("text").split(" (")[0]
        self.lbl_alarm_info.config(text=f"{base_text} (Susturuldu - 10dk)")

    def on_oto_change(self, *args):
        """OTO butonu değiştiğinde çalışır."""
        active = self.settings_vars['var_oto_yenile'].get()
        widgets_to_lock = ['cb_gun', 'cb_ay', 'cb_yil', 'cb_filt']
        widgets_to_lock = ['cb_gun', 'cb_ay', 'cb_yil', 'cb_filt', 'cb_ist', 'btn_refresh_ist', 'ent_manual_st', 'btn_manual_show', 'btn_list']
        
        if active:
            # 1. Güncel Tarihe Gel
            now = datetime.now(timezone.utc)
            try:
                self.cp_widgets['cb_gun'].set(str(now.day).zfill(2))
                tr_months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
                self.cp_widgets['cb_ay'].set(tr_months[now.month - 1])
                self.cp_widgets['cb_yil'].set(str(now.year))
                
                # 2. Tüm Bültenleri Seç
                if "Tüm Bültenler" in self.cp_widgets['cb_filt']['values']:
                    self.cp_widgets['cb_filt'].set("Tüm Bültenler")
                else:
                    try: self.cp_widgets['cb_filt'].current(0)
                    except: pass
            except: pass
            
            # 3. Widgetları Kilitle
            for w in widgets_to_lock:
                try: self.cp_widgets[w].configure(state="disabled")
                except: pass
            
            self.stop_oto_blink()
        else:
            # Widgetları Aç
            for w in widgets_to_lock:
                try: 
                    if "btn_" in w or "ent_" in w or "cb_ist" in w:
                        self.cp_widgets[w].configure(state="normal")
                    else:
                        self.cp_widgets[w].configure(state="readonly")
                except: pass
            
            self.start_oto_blink()

    def start_oto_blink(self):
        self.oto_blink_active = True
        self._blink_oto()

    def stop_oto_blink(self):
        self.oto_blink_active = False
        try: self.cp_widgets['chk_oto'].configure(fg="black", bg="#ECEFF1")
        except: pass

    def _blink_oto(self):
        if not getattr(self, 'oto_blink_active', False): return
        if not self.root.winfo_exists(): return
        
        try:
            current_bg = self.cp_widgets['chk_oto'].cget("bg")
            # Kırmızı / Normal Yanıp Sönme
            new_bg = "#FF5252" if current_bg == "#ECEFF1" else "#ECEFF1"
            new_fg = "white" if new_bg == "#FF5252" else "black"
            
            self.cp_widgets['chk_oto'].configure(bg=new_bg, fg=new_fg)
            self.root.after(500, self._blink_oto)
        except: pass
 