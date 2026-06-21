# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import json
import yaml
import time
import logging
from datetime import datetime, timezone, timedelta
import re
import gui_settings
import config_manager
import gui_utils

class SettingsMixin:
    def init_settings_vars(self):
        self.settings_vars = {}

        # Varsayılan Ayarlar (Merkezi Yönetim)
        self.default_values = {
            'var_anons_aktif': True, 'var_trend_alarm_aktif': True, 'var_metar_alarm_aktif': True,
            'var_sinoptik_alarm_aktif': True, 'var_taf_alarm_aktif': True, 'var_saat_basi_aktif': False,
            'var_piper_aktif': False,
            'var_edge_aktif': True,
            'var_edge_voice': "Ahmet (Erkek)",
            'var_piper_bin': "piper",
            'var_piper_model': "",
            'var_manuel_alarm_aktif': False, 'var_alarm_triggered': False, 'var_oto_yenile': True,
            'var_tebrik_aktif': True,
            'var_konusma_hizi': 150, 'var_konusma_perdesi': 0, 'var_oto_yenile_basla': 50, 'var_oto_yenile_bitis': 59,
            'var_tolerans_dk': 45, 
            'var_alarm_freq_metar':60, 'var_alarm_freq_taf': 300, 'var_alarm_freq_synop': 180, 'var_alarm_freq_incompatible': 60,
            # Tetikli Alarm Ayarları (Yeni Yapı)
            'var_metar_alarm_start_hour': "00:51", 'var_metar_alarm_period': 1, 'var_metar_alarm_trigger_min': 51,
            'var_metar_alarm_repeat': 4, 'var_synop_alarm_repeat': 3, 'var_taf_alarm_repeat': 3,
            'var_incompatible_alarm_repeat': 3,
            'var_synop_alarm_start_hour': "00:53", 'var_synop_alarm_period': 3, 'var_synop_alarm_trigger_min': 53,
            'var_taf_alarm_start_hour': "01:45", 'var_taf_alarm_period': 3, 'var_taf_alarm_trigger_min': 45,
            'var_klima_alarm_aktif': False, 'var_klima_alarm_start_hour': "06:53", 'var_klima_alarm_period': 24, 'var_klima_alarm_trigger_min': 53, 'var_alarm_freq_klima': 600,
            'var_max_ruzgar_alarm_aktif': False, 'var_max_ruzgar_alarm_start_hour': "06:53", 'var_max_ruzgar_alarm_period': 24, 'var_max_ruzgar_alarm_trigger_min': 53, 'var_alarm_freq_max_ruzgar': 600,
            'var_refresh_int_00_49': 60, 'var_refresh_int_50_59': 10,
            'var_rasat_zamani_aktif': False, 'var_rasat_zamani_start_min': 50, 'var_rasat_zamani_start_hour': 0, 'var_rasat_zamani_period': 1, 'var_alarm_freq_rasat_zamani': 0, 
            'var_ozel_ses_yolu': "",
            'var_manuel_saat': "00:00",
            'var_manuel_mesaj': "",
            'var_alarm_max_volume': True, 'var_eksik_veri_saat': 1,
            'var_tema_secimi': "Koyu Mod",
            'var_yazi_boyutu': 10,
            'var_yazi_kalinligi': "normal",
            'var_yazi_tipi': "Arial",
            'var_satir_yuksekligi': 25,
            'var_konsol_renk': "#263238",
            'var_tablo_arkaplan': "#ffffff",
            'var_tablo_zebra2': "#eceff1",
            'var_sutun_payi': 25,
            'var_tablo_secili_renk': "#1976D2",
            'var_filter_metar_start': 50, 'var_filter_metar_end': 54,
            'var_filter_synop_start': 50, 'var_filter_synop_end': 59,
            'var_filter_taf_start': 30, 'var_filter_taf_end': 59,
            # Denetim Ayarları (Yeni)
            'var_trend_min_sure': 15, 'var_trend_max_sure': 75,
            'var_trend_tl_min_sure': 15, 'var_trend_tl_max_sure': 90,
            'var_trend_zaman_aktif': True,
            'var_taf_esnek_mod': True,
            'var_kati_icao_kurallari': False,
            'var_denetim_metar_aktif': True,
            'var_denetim_metar_start_hour': 0, 'var_denetim_metar_period': 1,
            'var_denetim_metar_p1_start': 50, 'var_denetim_metar_p1_end': 54,
            'var_denetim_synop_aktif': True, 'var_denetim_synop_int': "3 Saat", 'var_denetim_synop_start_hour': 0, 'var_denetim_synop_period': 3, 'var_denetim_synop_start': 50, 'var_denetim_synop_end': 59,
            'var_denetim_taf_aktif': True, 'var_denetim_taf_int': "6 Saat", 'var_denetim_taf_start_hour': 2, 'var_denetim_taf_period': 3, 'var_denetim_taf_start': 30, 'var_denetim_taf_end': 59,
            # Görünüm Ayarları
            'var_uyum_show': False, 'var_tooltip_aktif': False,
            # Rasat Hatırlatıcıları (Personel Uyarı) - YENİ
            'var_remind_metar_aktif': True, 'var_remind_metar_start_h': "23:50", 'var_remind_metar_period': 1, 'var_remind_metar_min': 50, 'var_remind_metar_ontime': 5,
            'var_remind_synop_aktif': True, 'var_remind_synop_start_h': "23:50", 'var_remind_synop_period': 3, 'var_remind_synop_min': 50, 'var_remind_synop_ontime': 10,
            'var_remind_taf_aktif': True, 'var_remind_taf_start_h': "01:40", 'var_remind_taf_period': 3, 'var_remind_taf_min': 40, 'var_remind_taf_ontime': 30,
            # Gecikme Limitleri (Kırmızı Satır)
            'var_delay_limit_metar': 5, 'var_delay_limit_synop': 10, 'var_delay_limit_taf': 20,
            # Geç Gelen / Ceza Alarmı
            'var_denetim_gec_gelen_alarm_aktif': True,
            'var_ceza_tekrar_metar': 3, 'var_ceza_aralik_metar': 3,
            'var_ceza_tekrar_synop': 3, 'var_ceza_aralik_synop': 3,
            'var_ceza_tekrar_taf': 3, 'var_ceza_aralik_taf': 3,
            'var_baglanti_hata_tekrar': 2, 'var_baglanti_hata_aralik': 1,
            'var_test_time_offset': 0, # Dakika cinsinden zaman kaydırma (Simülasyon)
            'var_last_station': "", # Son seçilen istasyon
            # E-posta Ayarları
            'var_email_aktif': False, 'var_email_smtp': "smtp.gmail.com", 'var_email_port': 587,
            'var_email_gonderen': "", 'var_email_sifre': "", 'var_email_alici': "",
            # Rasat Stilleri (Özelleştirme)
            'var_style_metar_fg': "black", 'var_style_metar_bg': "#FFFFFF", 'var_style_metar_font_enable': False, 'var_style_metar_family': "Arial", 'var_style_metar_size': 10, 'var_style_metar_bold': False,
            'var_style_taf_fg': "#0D47A1", 'var_style_taf_bg': "#E3F2FD", 'var_style_taf_font_enable': False, 'var_style_taf_family': "Arial", 'var_style_taf_size': 10, 'var_style_taf_bold': True,
            'var_style_synop_fg': "black", 'var_style_synop_bg': "#F3E5F5", 'var_style_synop_font_enable': False, 'var_style_synop_family': "Arial", 'var_style_synop_size': 10, 'var_style_synop_bold': False,
            'var_style_other_fg': "black", 'var_style_other_bg': "#E0F2F1", 'var_style_other_font_enable': False, 'var_style_other_family': "Arial", 'var_style_other_size': 10, 'var_style_other_bold': False,
            'var_style_uyumsuz_fg': "white", 'var_style_uyumsuz_bg': "#D32F2F", 'var_style_uyumsuz_font_enable': False, 'var_style_uyumsuz_family': "Arial", 'var_style_uyumsuz_size': 10, 'var_style_uyumsuz_bold': True,
            'var_style_gec_fg': "black", 'var_style_gec_bg': "#F8BBD0", 'var_style_gec_font_enable': False, 'var_style_gec_family': "Arial", 'var_style_gec_size': 10, 'var_style_gec_bold': False,
            'var_style_eski_fg': "#78909C", 'var_style_eski_bg': "#ECEFF1", 'var_style_eski_font_enable': False, 'var_style_eski_family': "Arial", 'var_style_eski_size': 10, 'var_style_eski_bold': False,
            'var_style_re_hatasi_fg': "black", 'var_style_re_hatasi_bg': "#00E676", 'var_style_re_hatasi_font_enable': False, 'var_style_re_hatasi_family': "Arial", 'var_style_re_hatasi_size': 10, 'var_style_re_hatasi_bold': True,
            'var_style_cor_amd_fg': "white", 'var_style_cor_amd_bg': "#0D47A1", 'var_style_cor_amd_font_enable': False, 'var_style_cor_amd_family': "Arial", 'var_style_cor_amd_size': 10, 'var_style_cor_amd_bold': True
        }

        # Özel Alarmlar
        for i in range(5):
            self.settings_vars[f'var_sa_active_{i}'] = tk.BooleanVar(value=False)
            self.settings_vars[f'var_sa_freq_{i}'] = tk.StringVar(value="Her Gün")
            self.settings_vars[f'var_sa_date_{i}'] = tk.StringVar(value=datetime.now(timezone.utc).strftime("%d.%m.%Y"))
            self.settings_vars[f'var_sa_time_{i}'] = tk.StringVar(value="00:00")
            self.settings_vars[f'var_sa_msg_{i}'] = tk.StringVar(value="")
            self.settings_vars[f'var_sa_repeat_{i}'] = tk.IntVar(value=0)
            self.settings_vars[f'var_sa_count_{i}'] = tk.IntVar(value=0)
            
        # Personel Tebrik
        for i in range(20):
            self.settings_vars[f'var_kull_id_{i}'] = tk.StringVar(value="")
            self.settings_vars[f'var_kull_name_{i}'] = tk.StringVar(value="")

        # Varsayılan değerleri Tkinter değişkenlerine dönüştür
        for k, v in self.default_values.items():
            if isinstance(v, bool):
                self.settings_vars[k] = tk.BooleanVar(value=v)
            elif isinstance(v, int):
                self.settings_vars[k] = tk.IntVar(value=v)
            elif isinstance(v, float):
                self.settings_vars[k] = tk.DoubleVar(value=v)
            else:
                self.settings_vars[k] = tk.StringVar(value=str(v))


        # Ayarları Yükle
        gui_settings.load_settings(self.settings_vars)
        
        # Robot zaman kurallarını senkronize et
        try:
            if hasattr(self, 'robot'):
                self.robot.trend_min_sure = self.settings_vars['var_trend_min_sure'].get()
                self.robot.trend_max_sure = self.settings_vars['var_trend_max_sure'].get()
                self.robot.trend_tl_min_sure = self.settings_vars.get('var_trend_tl_min_sure', tk.IntVar(value=15)).get()
                self.robot.trend_tl_max_sure = self.settings_vars.get('var_trend_tl_max_sure', tk.IntVar(value=90)).get()
                self.robot.trend_zaman_aktif = self.settings_vars['var_trend_zaman_aktif'].get()
                self.robot.taf_esnek_mod_aktif = self.settings_vars['var_taf_esnek_mod'].get()
                self.robot.kati_icao_kurallari = self.settings_vars['var_kati_icao_kurallari'].get()
        except: pass
        
        # Kullanıcının özel alarm ve zaman ayarlarının üzerine yazılmasını engellemek için
        # zorunlu saat düzeltme (override) işlemi kaldırıldı.
        # Tüm ayarlar kullanıcının bıraktığı (veya varsayılan) gibi kalacak.

        self.last_saved_state = self.get_current_settings_state()

    def setup_settings_ui(self, parent):
        # Callback Fonksiyonları
        callbacks = {
            'ses_testi': lambda: self.alarm_motoru.google_seslendir("Ses sistemi testi. Bir, iki, üç.", hiz=150, pitch=0, use_piper=False, use_edge=True, edge_voice="Ahmet (Erkek)", use_openai=False),
            'test_speech_engine': lambda: self.alarm_motoru.google_seslendir(
                "Konuşma testi. Bir, iki, üç.", 
                hiz=self.settings_vars['var_konusma_hizi'].get(), 
                pitch=self.settings_vars['var_konusma_perdesi'].get(), 
                use_piper=self.settings_vars['var_piper_aktif'].get(), 
                piper_model=self.settings_vars['var_piper_model'].get(), 
                piper_bin=self.settings_vars['var_piper_bin'].get(), 
                use_edge=self.settings_vars['var_edge_aktif'].get(), 
                edge_voice=self.settings_vars['var_edge_voice'].get(), 
                use_openai=False
            ),
            'play_alarm_sound': self.play_alarm_sound,
            'rasat_yok_testi': self.rasat_yok_testi,
            'rasat_geldi_testi': self.rasat_geldi_testi,
            'alarm_simulation': self.alarm_simulation,
            'speak_text': lambda msg: self.alarm_motoru.google_seslendir(msg if msg else "Mesaj yok.", hiz=150, pitch=0, use_piper=False, use_edge=True, edge_voice="Ahmet (Erkek)", use_openai=False),
            'edge_test': self.edge_tts_test,
            'on_settings_change': self.on_settings_change_handler,
        }
        callbacks['show_alarm_history'] = self.show_alarm_history
        
        # Alt Butonlar (Toolbar Style)
        btn_frame = tk.Frame(parent, bg="#CFD8DC", pady=15)
        btn_frame.pack(side="bottom", fill="x")
        
        # Center container
        center_frame = tk.Frame(btn_frame, bg="#CFD8DC")
        center_frame.pack(anchor="center")

        def create_menubtn(parent, text, bg_color="#546E7A"):
            mb = tk.Menubutton(parent, text=text, font=("Segoe UI", 9, "bold"), 
                               bg=bg_color, fg="white", borderwidth=0,
                               activebackground=bg_color, activeforeground="white",
                               relief="flat", padx=20, pady=8, cursor="hand2")
            menu = tk.Menu(mb, tearoff=0, bg="white", fg="black", font=("Segoe UI", 9))
            mb.config(menu=menu)
            return mb, menu

        # 1. İŞLEMLER
        mb_actions, menu_actions = create_menubtn(center_frame, "İŞLEMLER")
        mb_actions.pack(side="left", padx=5)
        menu_actions.add_command(label="💾 VARSAYILAN YAP", command=self.save_settings_json)
        menu_actions.add_command(label="⚡ AYARLARI KAYDET (GEÇİCİ)", command=self.apply_temporary_settings)
        menu_actions.add_separator()
        menu_actions.add_command(label="📂 AYARLARI YEDEKLE", command=self.backup_settings)
        menu_actions.add_command(label="📥 YEDEKTEN YÜKLE", command=self.restore_settings)
        menu_actions.add_separator()
        menu_actions.add_command(label="🏭 FABRİKA AYARLARI", command=self.reset_to_defaults)

        # 2. MODLAR
        mb_modes, menu_modes = create_menubtn(center_frame, "MODLAR")
        mb_modes.pack(side="left", padx=5)
        menu_modes.add_command(label="🔊 SESLİ MOD", command=self.activate_audible_mode)
        menu_modes.add_command(label="🔕 SESSİZ MOD", command=self.activate_silent_mode)
        menu_modes.add_separator()
        menu_modes.add_command(label="☀️ AÇIK TEMA", command=lambda: self.settings_vars['var_tema_secimi'].set("Açık Mod"))
        menu_modes.add_command(label="🌙 KOYU TEMA", command=lambda: self.settings_vars['var_tema_secimi'].set("Koyu Mod"))

        # 3. TESTLER
        mb_test, menu_test = create_menubtn(center_frame, "TESTLER")
        mb_test.pack(side="left", padx=5)
        menu_test.add_command(label="🔊 SES TESTİ", command=callbacks['ses_testi'])
        menu_test.add_command(label="🔔 ALARM TESTİ", command=callbacks['play_alarm_sound'])
        menu_test.add_separator()
        menu_test.add_command(label="🚨 SİMÜLASYON PANELİ", command=callbacks['alarm_simulation'])

        # 4. LOGLAR
        mb_logs, menu_logs = create_menubtn(center_frame, "LOGLAR")
        mb_logs.pack(side="left", padx=5)
        menu_logs.add_command(label="📂 KLASÖR AÇ", command=self.open_log_folder)
        menu_logs.add_command(label="📝 GÖRÜNTÜLE", command=self.view_log_file)
        menu_logs.add_command(label="🔔 ALARM GEÇMİŞİ (24S)", command=self.show_alarm_history)

        # Ayarlar İçeriği
        self.lbl_settings_clock = gui_settings.setup_settings_tab(parent, self.settings_vars, callbacks)

    def play_alarm_sound(self):
        self.flash_visual_alert()
        path = self.settings_vars['var_ozel_ses_yolu'].get()
        if path and os.path.exists(path):
            self.alarm_motoru.cal_alarm_sesi(path)
            self.alarm_motoru.ozel_ses_cal(path)
        else:
            self.root.bell()

    def edge_tts_test(self):
        status, msg = self.alarm_motoru.check_edge_tts_status()
        if not status:
            messagebox.showerror("Edge TTS Hatası", msg)
        else:
            voice = self.settings_vars['var_edge_voice'].get()
            self.alarm_motoru.google_seslendir(f"Edge TTS sistemi kontrol ediliyor. Seçili ses: {voice}.", hiz=self.settings_vars['var_konusma_hizi'].get(), pitch=self.settings_vars['var_konusma_perdesi'].get(), use_edge=True, use_openai=False, edge_voice=voice)

    def open_log_folder(self):
        log_dir = config_manager.USER_DATA_DIR
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        os.startfile(log_dir)

    def view_log_file(self):
        try:
            self.notebook.select(self.tab_system_logs)
        except: pass

    def setup_system_logs_ui(self, log_win):
        base_log_dir = config_manager.USER_DATA_DIR
        now = datetime.now(timezone.utc)
        
        # --- NOTEBOOK (SEKMELER) ---
        nb = ttk.Notebook(log_win)
        nb.pack(fill="both", expand=True, padx=5, pady=5)
        
        # === TAB 1: GÜNLÜK SİSTEM LOGU ===
        tab_daily = ttk.Frame(nb)
        nb.add(tab_daily, text="Günlük Sistem Logu")
        
        toolbar = tk.Frame(tab_daily, bg="#ECEFF1", pady=5)
        toolbar.pack(side="top", fill="x")
        
        # Tarih Seçimi
        tk.Label(toolbar, text="Tarih:", bg="#ECEFF1", font=("Segoe UI", 9)).pack(side="left", padx=5)
        
        cb_day = ttk.Combobox(toolbar, values=[str(i).zfill(2) for i in range(1, 32)], width=3)
        cb_day.set(str(now.day).zfill(2))
        cb_day.pack(side="left", padx=2)
        
        months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        cb_month = ttk.Combobox(toolbar, values=months, width=10)
        cb_month.set(months[now.month - 1])
        cb_month.pack(side="left", padx=2)
        
        cb_year = ttk.Combobox(toolbar, values=[str(i) for i in range(2023, 2031)], width=5)
        cb_year.set(str(now.year))
        cb_year.pack(side="left", padx=2)
        
        frame_text = tk.Frame(tab_daily)
        frame_text.pack(fill="both", expand=True)
        sb = tk.Scrollbar(frame_text)
        sb.pack(side="right", fill="y")

        # Renkleri ayarlardan al
        konsol_bg = self.settings_vars.get('var_konsol_renk', tk.StringVar(value="#263238")).get()
        try:
            r, g, b = self.root.winfo_rgb(konsol_bg)
            # YIQ formülü ile parlaklık hesapla (0-65535 aralığı için)
            brightness = (r*299 + g*587 + b*114) / 1000
            konsol_fg = "#CFD8DC" if brightness < 32768000 else "#212121" # Eşik değeri ayarlandı
        except:
            konsol_fg = "#CFD8DC"

        txt_log = tk.Text(frame_text, font=("Consolas", 10), wrap="word", yscrollcommand=sb.set, bg=konsol_bg, fg=konsol_fg)
        txt_log.pack(side="left", fill="both", expand=True)
        sb.config(command=txt_log.yview)
        
        # Hata vurgusu için tag
        txt_log.tag_config("error_highlight", foreground="#FF5252", font=("Consolas", 10, "bold"))
        txt_log.tag_config("alarm_highlight", foreground="#FFD700", font=("Consolas", 10, "bold"))
        txt_log.tag_config("arrival_highlight", foreground="#69F0AE", font=("Consolas", 10, "bold"))
        txt_log.tag_config("missing_highlight", foreground="#FFAB91", font=("Consolas", 10, "bold"))
        txt_log.tag_config("anons_highlight", foreground="#00B0FF", font=("Consolas", 10, "bold"))
        txt_log.tag_config("tebrik_highlight", foreground="#00E676", font=("Consolas", 10, "bold"))
        txt_log.tag_config("dikkat_highlight", foreground="#FFD700", font=("Consolas", 10, "bold"))
        
        # YENİ: Günlük Log için satır bazlı blok renkleri
        txt_log.tag_config("metar_line", background="#004D40", foreground="#E0F7FA", font=("Consolas", 10, "bold"))
        txt_log.tag_config("taf_line", background="#311B92", foreground="#F3E5F5", font=("Consolas", 10, "bold"))
        txt_log.tag_config("synop_line", background="#E65100", foreground="#FFF3E0", font=("Consolas", 10, "bold"))
        txt_log.tag_config("speci_line", background="#b71c1c", foreground="#FBE9E7", font=("Consolas", 10, "bold"))

        var_filter_mode = tk.StringVar(value="Hepsi")
        
        # --- YARDIMCI FONKSİYONLAR (Çöp Kutusu & Yedekleme) ---
        def open_trash_folder():
            trash_dir = os.path.join(base_log_dir, "Cop_Kutusu")
            if not os.path.exists(trash_dir): os.makedirs(trash_dir)
            os.startfile(trash_dir)

        def empty_trash():
            trash_dir = os.path.join(base_log_dir, "Cop_Kutusu")
            if not os.path.exists(trash_dir) or not os.listdir(trash_dir):
                messagebox.showinfo("Bilgi", "Çöp kutusu zaten boş.", parent=log_win)
                return

            if messagebox.askyesno("Onay", "Çöp kutusundaki tüm dosyalar KALICI OLARAK silinecek.\nEmin misiniz?", parent=log_win):
                try:
                    count = 0
                    for filename in os.listdir(trash_dir):
                        file_path = os.path.join(trash_dir, filename)
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                                count += 1
                        except: pass
                    messagebox.showinfo("Başarılı", f"Çöp kutusu boşaltıldı ({count} dosya).", parent=log_win)
                except Exception as e:
                    messagebox.showerror("Hata", f"Hata: {e}")

        def backup_to_trash(filename, content):
            try:
                trash_dir = os.path.join(base_log_dir, "Cop_Kutusu")
                if not os.path.exists(trash_dir):
                    os.makedirs(trash_dir)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                basename = os.path.basename(filename)
                trash_filename = f"SILINEN_{timestamp}_{basename}"
                trash_path = os.path.join(trash_dir, trash_filename)
                
                with open(trash_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True
            except Exception as e:
                logging.error(f"Trash backup error: {e}")
                return False

        def get_daily_summary_text(target_file, target_date_str):
            counts = {"METAR": 0, "TAF": 0, "SİNOPTİK": 0, "SPECI": 0}
            missing_sets = {"METAR": set(), "TAF": set(), "SİNOPTİK": set()}
            late_counts = {"METAR": 0, "TAF": 0, "SİNOPTİK": 0}
            late_list = []
            error_counts = {}
            last_times = {"METAR": "-", "TAF": "-", "SİNOPTİK": "-", "SPECI": "-"}
            total_events = 0
            alarm_events = 0
            anons_events = 0
            tebrik_events = 0
            
            try:
                lim_metar = self.settings_vars.get('var_delay_limit_metar', tk.IntVar(value=5)).get()
                lim_synop = self.settings_vars.get('var_delay_limit_synop', tk.IntVar(value=10)).get()
                lim_taf = self.settings_vars.get('var_delay_limit_taf', tk.IntVar(value=20)).get()
            except: lim_metar, lim_synop, lim_taf = 5, 10, 20
            
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    for line in f:
                        upper_line = line.upper()
                        
                        if "ALARM" in upper_line and "EKSİK" in upper_line:
                            alarm_events += 1
                        
                        if "SESLİ ANONS" in upper_line:
                            anons_events += 1
                            if "TEBRİKLER" in upper_line or "TEBRIKLER" in upper_line:
                                tebrik_events += 1

                        if "GELDİ" in line or "YENİ RASAT" in line:
                            total_events += 1
                            try: time_part = line.split(",")[0].split(" ")[1]
                            except: time_part = "-"
                            try:
                                if "GELDİ:" in line: content_part = line.split("GELDİ:")[1].strip()
                                else: content_part = line.split("YENİ RASAT")[1].strip()
                                arr_tokens = content_part.split()
                                if len(arr_tokens) >= 2:
                                    arr_time = arr_tokens[0].replace(":", "")
                                    arr_type_raw = arr_tokens[1].upper()
                                    if "METAR" in arr_type_raw: missing_sets["METAR"].discard(f"{arr_time} METAR")
                                    elif "TAF" in arr_type_raw: missing_sets["TAF"].discard(f"{arr_time} TAF")
                                    elif "SİNOPTİK" in arr_type_raw or "SYNOP" in arr_type_raw: missing_sets["SİNOPTİK"].discard(f"{arr_time} SİNOPTİK")
                            except: pass

                            if "METAR" in upper_line: counts["METAR"] += upper_line.count("METAR"); last_times["METAR"] = time_part
                            if "TAF" in upper_line: counts["TAF"] += upper_line.count("TAF"); last_times["TAF"] = time_part
                            if "SİNOPTİK" in upper_line or "SYNOP" in upper_line or "SINOPTIK" in upper_line: counts["SİNOPTİK"] += upper_line.count("SİNOPTİK") + upper_line.count("SYNOP") + upper_line.count("SINOPTIK"); last_times["SİNOPTİK"] = time_part
                            if "SPECI" in upper_line: counts["SPECI"] += upper_line.count("SPECI"); last_times["SPECI"] = time_part
                            
                            try:
                                log_ts_str = line.split("]")[0].strip("[")
                                log_dt = datetime.strptime(log_ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                                msg_part = line.split("GELDİ:")[1].strip() if "GELDİ:" in line else line.split("YENİ RASAT")[1].strip()
                                obs_hm = msg_part.split(" ")[0]
                                oh, om = map(int, obs_hm.split(":"))
                                obs_dt = log_dt.replace(hour=oh, minute=om, second=0, microsecond=0)
                                if log_dt.hour < 5 and oh > 20: obs_dt -= timedelta(days=1)
                                elif log_dt.hour > 20 and oh < 5: obs_dt += timedelta(days=1)
                                diff = (log_dt - obs_dt).total_seconds() / 60.0
                                is_late = False
                                if "METAR" in upper_line and "SPECI" not in upper_line and diff > lim_metar: is_late = True
                                elif "TAF" in upper_line and diff > lim_taf: is_late = True
                                elif ("SİNOPTİK" in upper_line or "SYNOP" in upper_line or "SINOPTIK" in upper_line) and diff > lim_synop: is_late = True
                                if is_late:
                                    l_type = ""
                                    if "METAR" in upper_line: late_counts["METAR"] += 1; l_type = "METAR"
                                    elif "TAF" in upper_line: late_counts["TAF"] += 1; l_type = "TAF"
                                    elif "SİNOPTİK" in upper_line or "SYNOP" in upper_line or "SINOPTIK" in upper_line: late_counts["SİNOPTİK"] += 1; l_type = "SİNOPTİK"
                                    if l_type: late_list.append(f"{obs_hm} {l_type} (+{int(diff)}dk)")
                            except: pass
                        
                        if "EKSİK VERİ ALARMI" in line or "EKSİK:" in line:
                            try:
                                if "EKSİK VERİ ALARMI:" in line: missing_content = line.split("EKSİK VERİ ALARMI:")[1].strip()
                                elif "EKSİK:" in line: missing_content = line.split("EKSİK:")[1].strip()
                                else: missing_content = ""
                                if missing_content:
                                    for item in missing_content.split(','):
                                        parts = item.strip().split()
                                        if len(parts) >= 2:
                                            m_time, m_type = parts[0], parts[1].upper()
                                            if "METAR" in m_type: missing_sets["METAR"].add(f"{m_time} METAR")
                                            elif "TAF" in m_type: missing_sets["TAF"].add(f"{m_time} TAF")
                                            elif "SİNOPTİK" in m_type or "SYNOP" in m_type: missing_sets["SİNOPTİK"].add(f"{m_time} SİNOPTİK")
                            except: pass
                        
                        if "ERROR" in upper_line or "CRITICAL" in upper_line or "HATA" in upper_line:
                            err_type = "Genel"
                            if "VERİ ÇEKME" in upper_line or "FETCH" in upper_line or "CONNECTION" in upper_line or "BAĞLANTI" in upper_line: err_type = "Veri Çekme"
                            elif "ANALİZ" in upper_line: err_type = "Analiz"
                            elif "DOSYA" in upper_line or "FILE" in upper_line: err_type = "Dosya"
                            error_counts[err_type] = error_counts.get(err_type, 0) + 1
            except Exception: pass
            
            report = f"TARİH: {target_date_str}\nTOPLAM OLAY: {total_events}\n" + "-"*40 + "\n"
            report += f"{'TÜR':<12} {'ADET':<6} {'SON SAAT'}\n" + "-"*40 + "\n"
            report += f"{'METAR':<12} {counts['METAR']:<6} {last_times['METAR']}\n{'TAF':<12} {counts['TAF']:<6} {last_times['TAF']}\n{'SİNOPTİK':<12} {counts['SİNOPTİK']:<6} {last_times['SİNOPTİK']}\n{'SPECI':<12} {counts['SPECI']:<6} {last_times['SPECI']}\n" + "-"*40 + "\n"
            missing_str = ", ".join([f"{len(missing_sets[k])} {k}" for k in ["METAR", "TAF", "SİNOPTİK"] if missing_sets[k]]) or "Yok"
            late_str = ", ".join([f"{late_counts[k]} {k}" for k in ["METAR", "TAF", "SİNOPTİK"] if late_counts[k]]) or "Yok"
            report += f"RASAT: {total_events}\nTETİKLİ RASAT: {alarm_events}\nGEÇ GELEN RASAT: {late_str}\n"
            if late_list: report += "\nDETAYLI GEÇ GELENLER:\n" + "".join([f"  > {x}\n" for x in late_list])
            report += f"ANONS SAYISI: {anons_events} (Tebrik: {tebrik_events})\nHATA SAYISI: {', '.join([f'{v} {k}' for k, v in error_counts.items()]) or 'Yok'}\n"
            return report

        def load_content():
            try:
                d = cb_day.get()
                m_name = cb_month.get()
                y = cb_year.get()
                
                if m_name in months: m = months.index(m_name) + 1
                else: m = now.month
                
                target_date_str = f"{y}-{m:02d}-{d}"
                target_file = os.path.join(base_log_dir, target_date_str, "kardelen_gunluk_log.txt")
                
                txt_log.config(state="normal")
                txt_log.delete("1.0", tk.END)
                
                txt_log.tag_config("summary_border", foreground="#90A4AE", font=("Consolas", 10, "bold"))
                txt_log.tag_config("summary_title", foreground="#2196F3", font=("Consolas", 11, "bold"))

                if os.path.exists(target_file):
                    summary_text = get_daily_summary_text(target_file, target_date_str)
                    if summary_text:
                        txt_log.insert("end", "============================================================\n", "summary_border")
                        txt_log.insert("end", " 📊 GÜNLÜK İSTATİSTİK ÖZETİ\n", "summary_title")
                        txt_log.insert("end", "============================================================\n", "summary_border")
                        txt_log.insert("end", summary_text + "\n")
                        txt_log.insert("end", "============================================================\n\n", "summary_border")

                    with open(target_file, "r", encoding="utf-8") as f: lines = f.readlines()
                    
                    d_counts = {k: 0 for k in daily_labels.keys()}
                    def is_data_log(line):
                        upper_l = line.upper()
                        if "ALARM" in upper_l: return False
                        if "EKSİK" in upper_l: return False
                        if "SESLİ ANONS" in upper_l: return False
                        if "GELDİ:" in upper_l or "YENİ RASAT" in upper_l: return False
                        if "DİKKAT" in upper_l or "ŞARTA BAĞLI" in upper_l: return False
                        if "GEÇMİŞ HADİSE" in upper_l or "RE/GECMIS HATASI" in upper_l: return False
                        return True
                        
                    for l in lines:
                        upper_l = l.upper()
                        d_counts["HEPSİ"] += 1
                        if "ERROR" in upper_l or "CRITICAL" in upper_l: d_counts["HATALAR"] += 1
                        if "ALARM" in upper_l: d_counts["ALARMLAR"] += 1
                        if "GELDİ" in upper_l or "YENİ RASAT" in upper_l: d_counts["GELENLER"] += 1
                        if "EKSİK" in upper_l or "DİKKAT" in upper_l: d_counts["GELMEYENLER"] += 1
                        if "SESLİ ANONS" in upper_l: d_counts["ANONSLAR"] += 1
                        if is_data_log(l): d_counts["DATA"] += 1
                        if "GEÇMİŞ HADİSE" in upper_l or "RE/GECMIS HATASI" in upper_l: d_counts["RE_HATASI"] += 1
                        
                    new_values = []
                    current_raw = var_filter_mode.get().split(" (")[0]
                    if not current_raw: current_raw = "Hepsi"
                    
                    mode = "HEPSİ"
                    for val, lbl in daily_labels.items():
                        item_text = f"{lbl} ({d_counts[val]})"
                        new_values.append(item_text)
                        if lbl == current_raw:
                            mode = val
                            var_filter_mode.set(item_text)
                            
                    cb_daily_filter['values'] = new_values
                    filtered = []
                    if mode == "HEPSİ":
                        filtered = lines  # Tüm logları filtresiz göster
                    elif mode == "DATA":
                        for l in lines:
                            if is_data_log(l):
                                filtered.append(l)
                    elif mode == "HATALAR":
                        # HATALAR GRUPLANMIŞ GÖSTERİM
                        error_blocks = []
                        current_block = []
                        current_time = ""
                        for l in lines:
                            if "ERROR" in l or "CRITICAL" in l:
                                parts = l.split(" - ", 3)
                                time_part = parts[0].strip() if len(parts) >= 4 else ""
                                msg = parts[3].strip() if len(parts) >= 4 else l.strip()
                                
                                is_traceback_line = (
                                    msg.startswith("File ") or 
                                    msg.startswith("Traceback") or 
                                    "Error:" in msg or 
                                    msg.startswith("Exception")
                                )
                                
                                if current_block and is_traceback_line:
                                    current_block.append(msg)
                                else:
                                    if current_block:
                                        error_blocks.append(("\n  ".join(current_block), current_time))
                                    current_block = [msg]
                                    current_time = time_part
                            else:
                                if current_block:
                                    error_blocks.append(("\n  ".join(current_block), current_time))
                                    current_block = []
                                    current_time = ""
                        if current_block:
                            error_blocks.append(("\n  ".join(current_block), current_time))
                            
                        error_counts = {}
                        for block_msg, t_str in error_blocks:
                            if block_msg not in error_counts:
                                error_counts[block_msg] = []
                            if t_str:
                                error_counts[block_msg].append(t_str)
                        
                        if error_counts:
                            filtered.append("=== GÜNLÜK HATA ÖZETİ (GRUPLANMIŞ) ===\n\n")
                            for msg, times in sorted(error_counts.items(), key=lambda x: len(x[1]), reverse=True):
                                count = len(times)
                                clean_times = []
                                for t in times:
                                    try:
                                        # "2024-03-24 15:30:25,123" formatından "15:30:25" kısmını al
                                        time_only = t.split(" ")[1].split(",")[0]
                                        clean_times.append(time_only)
                                    except:
                                        clean_times.append(t)
                                
                                times_formatted = ", ".join(clean_times)
                                if len(clean_times) > 15:
                                    times_formatted = ", ".join(clean_times[:8]) + f" ... (+{len(clean_times)-15} daha) ... " + ", ".join(clean_times[-7:])
                                    
                                filtered.append(f"[{count} KEZ TEKRARLANDI]\n  ZAMANLAR: {times_formatted}\n  HATA: {msg}\n\n" + "-"*60 + "\n\n")
                        else:
                            filtered.append("Bu tarihte kaydedilmiş bir hata bulunmamaktadır.\n")
                    else:
                        for l in lines:
                            keep = False
                            if mode == "ALARMLAR" and "ALARM" in l: keep = True
                            elif mode == "GELENLER" and ("GELDİ" in l or "YENİ RASAT" in l): keep = True
                            elif mode == "GELMEYENLER" and ("EKSİK" in l or "DİKKAT" in l): keep = True
                            elif mode == "ANONSLAR" and ("SESLİ ANONS" in l): keep = True
                            elif mode == "RE_HATASI" and ("GEÇMİŞ HADİSE" in l.upper() or "RE/GECMIS HATASI" in l.upper()): keep = True
                            if keep: filtered.append(l)
                    
                    lines = filtered
                    txt_log.insert("end", "".join(lines))
                    
                    if mode == "HATALAR":
                        start = "1.0"
                        while True:
                            pos = txt_log.search("KEZ TEKRARLANDI]", start, stopindex=tk.END)
                            if not pos: break
                            line_idx = pos.split(".")[0]
                            txt_log.tag_add("error_highlight", f"{line_idx}.0", f"{line_idx}.end")
                            start = f"{line_idx}.end+1c"
                    else:
                        for kw in ["ERROR", "CRITICAL"]:
                            start = "1.0"
                            while True:
                                pos = txt_log.search(kw, start, stopindex=tk.END)
                                if not pos: break
                                line_idx = pos.split(".")[0]
                                txt_log.tag_add("error_highlight", f"{line_idx}.0", f"{line_idx}.end")
                                start = f"{line_idx}.end+1c"

                        start = "1.0"
                        while True:
                            pos = txt_log.search("ALARM", start, stopindex=tk.END)
                            if not pos: break
                            line_idx = pos.split(".")[0]
                            txt_log.tag_add("alarm_highlight", f"{line_idx}.0", f"{line_idx}.end")
                            start = f"{line_idx}.end+1c"
                        
                        # GELDİ / YENİ RASAT içeren satırları tipe göre blok boya
                        for kw in ["GELDİ", "YENİ RASAT"]:
                            start = "1.0"
                            while True:
                                pos = txt_log.search(kw, start, stopindex=tk.END)
                                if not pos: break
                                line_idx = pos.split(".")[0]
                                line_text = txt_log.get(f"{line_idx}.0", f"{line_idx}.end").upper()
                                
                                if "SPECI" in line_text: txt_log.tag_add("speci_line", f"{line_idx}.0", f"{line_idx}.end")
                                elif "METAR" in line_text: txt_log.tag_add("metar_line", f"{line_idx}.0", f"{line_idx}.end")
                                elif "TAF" in line_text: txt_log.tag_add("taf_line", f"{line_idx}.0", f"{line_idx}.end")
                                elif "SİNOPTİK" in line_text or "SYNOP" in line_text or "SINOPTIK" in line_text:
                                    txt_log.tag_add("synop_line", f"{line_idx}.0", f"{line_idx}.end")
                                else: txt_log.tag_add("arrival_highlight", f"{line_idx}.0", f"{line_idx}.end")
                                    
                                start = f"{line_idx}.end+1c"
                        
                        # EKSİK içeren satırları boya
                        start = "1.0"
                        while True:
                            pos = txt_log.search("EKSİK", start, stopindex=tk.END)
                            if not pos: break
                            line_idx = pos.split(".")[0]
                            txt_log.tag_add("missing_highlight", f"{line_idx}.0", f"{line_idx}.end")
                            start = f"{line_idx}.end+1c"
                            
                        # DİKKAT veya ŞARTA BAĞLI içeren satırları boya
                        for kw in ["DİKKAT", "ŞARTA BAĞLI"]:
                            start = "1.0"
                            while True:
                                pos = txt_log.search(kw, start, stopindex=tk.END)
                                if not pos: break
                                line_idx = pos.split(".")[0]
                                txt_log.tag_add("dikkat_highlight", f"{line_idx}.0", f"{line_idx}.end")
                                start = f"{line_idx}.end+1c"
                        
                        # SESLİ ANONS içeren satırları boya
                        start = "1.0"
                        while True:
                            pos = txt_log.search("SESLİ ANONS", start, stopindex=tk.END)
                            if not pos: break
                            line_idx = pos.split(".")[0]
                            txt_log.tag_add("anons_highlight", f"{line_idx}.0", f"{line_idx}.end")
                            start = f"{line_idx}.end+1c"
                        
                        # TEBRİKLER içeren satırları boya
                        start = "1.0"
                        while True:
                            pos = txt_log.search("Tebrikler", start, stopindex=tk.END, nocase=True)
                            if not pos: break
                            line_idx = pos.split(".")[0]
                            txt_log.tag_add("tebrik_highlight", f"{line_idx}.0", f"{line_idx}.end")
                            start = f"{line_idx}.end+1c"
                    
                    txt_log.see("end")
                else:
                    new_values = []
                    for val, lbl in daily_labels.items():
                        new_values.append(f"{lbl} (0)")
                    cb_daily_filter['values'] = new_values
                    var_filter_mode.set(new_values[0])
                    txt_log.insert("end", f"Bu tarih ({target_date_str}) için log dosyası bulunamadı.\n\n")
                    txt_log.insert("end", "Eğer bugün henüz veri çekilmediyse veya sistem kapalı kaldıysa dosya oluşmamış olabilir.\n")
                    txt_log.insert("end", "Eski verileri görmek için lütfen sol üstten önceki günleri/ayları seçerek 'GÖSTER' butonuna basınız.")
                
                txt_log.config(state="disabled")
            except Exception as e:
                messagebox.showerror("Hata", f"Log yüklenirken hata: {e}", parent=log_win)

        def delete_logs(mode="ALL"):
            try:
                d = cb_day.get()
                m_name = cb_month.get()
                y = cb_year.get()
                if m_name in months: m = months.index(m_name) + 1
                else: m = now.month
                target_date_str = f"{y}-{m:02d}-{d}"
                target_file = os.path.join(base_log_dir, target_date_str, "kardelen_gunluk_log.txt")

                if not os.path.exists(target_file):
                    messagebox.showwarning("Uyarı", "Dosya yok.")
                    return

                confirm_msg = f"{target_date_str} tarihli log dosyasında "
                if mode == "ALL": confirm_msg += "TÜM KAYITLAR silinecek."
                elif mode == "ALARMS": confirm_msg += "TÜM ALARMLAR silinecek."
                elif mode == "MISSING": confirm_msg += "SADECE TETİKLENENLER (EKSİK VERİ) silinecek."
                elif mode == "ANONS": confirm_msg += "SADECE ANONSLAR silinecek."
                elif mode == "DATA": confirm_msg += "SADECE SİSTEM/VERİ LOGLARI silinecek."
                
                if not messagebox.askyesno("Onay", f"{confirm_msg}\nEmin misiniz?", parent=log_win):
                    return

                if mode == "ALL":
                    # Tümünü silerken Çöp Kutusuna yedekle
                    try:
                        with open(target_file, "r", encoding="utf-8") as f: content = f.read()
                        if content: backup_to_trash(target_file, content)
                    except: pass
                    with open(target_file, "w", encoding="utf-8") as f: f.write("")
                else:
                    with open(target_file, "r", encoding="utf-8") as f: lines = f.readlines()
                    new_lines = []
                    
                    def is_data_log_del(line):
                        upper_l = line.upper()
                        if "ALARM" in upper_l: return False
                        if "EKSİK" in upper_l: return False
                        if "SESLİ ANONS" in upper_l: return False
                        if "GELDİ:" in upper_l or "YENİ RASAT" in upper_l: return False
                        if "DİKKAT" in upper_l or "ŞARTA BAĞLI" in upper_l: return False
                        if "GEÇMİŞ HADİSE" in upper_l or "RE/GECMIS HATASI" in upper_l: return False
                        return True

                    for l in lines:
                        upper_l = l.upper()
                        delete = False
                        if mode == "ALARMS" and "ALARM" in upper_l: delete = True
                        elif mode == "MISSING" and "EKSİK" in upper_l: delete = True
                        elif mode == "ANONS" and "SESLİ ANONS" in upper_l: delete = True
                        elif mode == "DATA" and is_data_log_del(l): delete = True
                        
                        if not delete:
                            new_lines.append(l)
                    
                    with open(target_file, "w", encoding="utf-8") as f: f.writelines(new_lines)
                
                load_content()
                messagebox.showinfo("Bilgi", "Silme işlemi tamamlandı.", parent=log_win)
            except Exception as e:
                messagebox.showerror("Hata", f"Silme hatası: {e}", parent=log_win)
        
        def open_search_dialog(event=None):
            # Aktif sekmeyi bul (0: Günlük, 1: Aylık)
            current_tab_id = nb.index(nb.select())
            target_text = txt_log if current_tab_id == 0 else txt_monthly
            
            search_win = tk.Toplevel(self.root)
            search_win.title("Ara")
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
            
            def do_search(event=None):
                term = entry_search.get()
                if not term: return
                
                target_text.tag_remove("search_highlight", "1.0", tk.END)
                target_text.tag_remove("search_current", "1.0", tk.END)
                
                matches = []
                start = "1.0"
                while True:
                    pos = target_text.search(term, start, stopindex=tk.END, nocase=True)
                    if not pos: break
                    end = f"{pos}+{len(term)}c"
                    target_text.tag_add("search_highlight", pos, end)
                    matches.append(pos)
                    start = end
                
                target_text.tag_config("search_highlight", background="#FFEB3B", foreground="black")
                target_text.tag_config("search_current", background="#FF9800", foreground="white")
                
                search_data["matches"] = matches
                search_data["idx"] = -1
                
                if matches:
                    lbl_status.config(text=f"{len(matches)} sonuç bulundu.")
                    navigate(1)
                else:
                    lbl_status.config(text="Sonuç yok.")

            def navigate(direction):
                if not search_data["matches"]: return
                
                target_text.tag_remove("search_current", "1.0", tk.END)
                
                if direction == 1: # İleri
                    search_data["idx"] = (search_data["idx"] + 1) % len(search_data["matches"])
                else: # Geri
                    search_data["idx"] = (search_data["idx"] - 1) % len(search_data["matches"])
                
                pos = search_data["matches"][search_data["idx"]]
                end = f"{pos}+{len(entry_search.get())}c"
                
                target_text.tag_add("search_current", pos, end)
                target_text.see(pos)
                lbl_status.config(text=f"Sonuç: {search_data['idx']+1} / {len(search_data['matches'])}")

            entry_search.bind("<Return>", do_search)
            
            f_btns = tk.Frame(search_win)
            f_btns.pack(pady=5, fill="x")
            
            tk.Button(f_btns, text="ARA", command=do_search, width=10, bg="#B0BEC5").pack(side="left", padx=10, expand=True)
            tk.Button(f_btns, text="< ÖNCEKİ", command=lambda: navigate(-1), width=10).pack(side="left", padx=5, expand=True)
            tk.Button(f_btns, text="SONRAKİ >", command=lambda: navigate(1), width=10).pack(side="left", padx=10, expand=True)

        log_win.bind("<Control-f>", open_search_dialog)

        # Sağ Tık Menüsü
        def copy_log_selection(event=None):
            if txt_log.tag_ranges("sel"):
                selected_text = txt_log.get(tk.SEL_FIRST, tk.SEL_LAST)
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)

        def delete_selected_log_lines(event=None):
            if not txt_log.tag_ranges("sel"):
                messagebox.showwarning("Uyarı", "Silmek için önce bir veya daha fazla satır seçin.", parent=log_win)
                return

            selected_text = txt_log.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            if not selected_text:
                return

            if not messagebox.askyesno("Onay", "Seçili satırlar log dosyasından kalıcı olarak silinecek.\nEmin misiniz?", parent=log_win):
                return
            
            try:
                # Get current file path
                d = cb_day.get()
                m_name = cb_month.get()
                y = cb_year.get()
                if m_name in months: m = months.index(m_name) + 1
                else: m = now.month
                target_date_str = f"{y}-{m:02d}-{d}"
                target_file = os.path.join(base_log_dir, target_date_str, "kardelen_gunluk_log.txt")

                if not os.path.exists(target_file):
                    messagebox.showerror("Hata", "Log dosyası bulunamadı.")
                    return

                with open(target_file, "r", encoding="utf-8") as f:
                    all_lines = f.readlines()

                lines_to_delete = {line.strip() for line in selected_text.split('\n')}
                new_lines = [line for line in all_lines if line.strip() not in lines_to_delete]

                with open(target_file, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)

                load_content()
                messagebox.showinfo("Bilgi", f"{len(all_lines) - len(new_lines)} satır silindi.")
            except Exception as e:
                messagebox.showerror("Hata", f"Silme işlemi sırasında hata oluştu: {e}")

        log_context_menu = tk.Menu(txt_log, tearoff=0)
        log_context_menu.add_command(label="Kopyala", command=copy_log_selection)
        log_context_menu.add_command(label="Seçili Satırları Sil", command=delete_selected_log_lines)

        decode_menu = tk.Menu(log_context_menu, tearoff=0)
        log_context_menu.add_separator()
        log_context_menu.add_cascade(label="🔍 Çözümle", menu=decode_menu)
        decode_menu.add_command(label="SİNOPTİK", command=lambda: self.show_decode_window("SİNOPTİK", txt_log.get(tk.SEL_FIRST, tk.SEL_LAST) if txt_log.tag_ranges("sel") else ""))
        decode_menu.add_command(label="METAR", command=lambda: self.show_decode_window("METAR", txt_log.get(tk.SEL_FIRST, tk.SEL_LAST) if txt_log.tag_ranges("sel") else ""))
        decode_menu.add_command(label="TAF", command=lambda: self.show_decode_window("TAF", txt_log.get(tk.SEL_FIRST, tk.SEL_LAST) if txt_log.tag_ranges("sel") else ""))

        def show_log_context_menu(event):
            decode_menu.entryconfig("SİNOPTİK", state="disabled")
            decode_menu.entryconfig("METAR", state="disabled")
            decode_menu.entryconfig("TAF", state="disabled")
            
            # Seçim yoksa, farenin altındaki satırı otomatik seç
            if not txt_log.tag_ranges("sel"):
                index = txt_log.index(f"@{event.x},{event.y}")
                txt_log.tag_add("sel", f"{index} linestart", f"{index} lineend")
                
            if txt_log.tag_ranges("sel"):
                sel_text = txt_log.get(tk.SEL_FIRST, tk.SEL_LAST).upper()
                if any(x in sel_text for x in ["SİNOPTİK", "SINOPTIK", "SYNOP", "AAXX", "SITT", "SM"]): decode_menu.entryconfig("SİNOPTİK", state="normal")
                if any(x in sel_text for x in ["METAR", "SPECI", "SATT", "SA", "SP"]): decode_menu.entryconfig("METAR", state="normal")
                if any(x in sel_text for x in ["TAF", "FCTT", "FC", "FT"]): decode_menu.entryconfig("TAF", state="normal")
            log_context_menu.tk_popup(event.x_root, event.y_root)

        txt_log.bind("<Button-3>", show_log_context_menu)
        txt_log.bind("<Control-c>", copy_log_selection)

        def show_arrival_summary():
            try:
                d = cb_day.get()
                m_name = cb_month.get()
                y = cb_year.get()
                
                if m_name in months: m = months.index(m_name) + 1
                else: m = now.month
                
                target_date_str = f"{y}-{m:02d}-{d}"
                target_file = os.path.join(base_log_dir, target_date_str, "kardelen_gunluk_log.txt")
                
                if not os.path.exists(target_file):
                    messagebox.showinfo("Bilgi", "Log dosyası bulunamadı.", parent=log_win)
                    return

                report = get_daily_summary_text(target_file, target_date_str)
                
                sum_win = tk.Toplevel(self.root)
                sum_win.title("Genel Özet")
                sum_win.geometry("420x350")
                
                txt_sum = tk.Text(sum_win, font=("Consolas", 10), bg="#ECEFF1", padx=10, pady=10)
                txt_sum.pack(fill="both", expand=True)
                txt_sum.insert("end", report)
                txt_sum.config(state="disabled")
                
                def copy_report():
                    self.root.clipboard_clear()
                    self.root.clipboard_append(report)
                    messagebox.showinfo("Bilgi", "Rapor panoya kopyalandı.", parent=sum_win)
                
                tk.Button(sum_win, text="📋 PANOYA KOPYALA", command=copy_report, bg="#4CAF50", fg="white", font=("Segoe UI", 9, "bold"), pady=5, relief="flat").pack(fill="x")
            except Exception as e:
                messagebox.showerror("Hata", f"Özet oluşturulurken hata: {e}", parent=log_win)

        tk.Button(toolbar, text="GÖSTER", command=load_content, bg="#2196F3", fg="white", font=("Segoe UI", 9, "bold"), relief="flat").pack(side="left", padx=5)
        
        daily_labels = {
            "HEPSİ": "Hepsi", "HATALAR": "Hatalar", "ALARMLAR": "Alarmlar", 
            "GELENLER": "Gelenler", "GELMEYENLER": "Tetiklenen", 
            "ANONSLAR": "Anonslar", "DATA": "Sistem/Veri", "RE_HATASI": "RE/Geçmiş Hatası"
        }
        tk.Label(toolbar, text="Filtre:", bg="#ECEFF1", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(10, 2))
        cb_daily_filter = ttk.Combobox(toolbar, textvariable=var_filter_mode, state="readonly", width=22)
        cb_daily_filter.pack(side="left", padx=2)
        cb_daily_filter.bind("<<ComboboxSelected>>", lambda e: load_content())
        
        mb_del = tk.Menubutton(toolbar, text="🗑️ SİL", bg="#D32F2F", fg="white", font=("Segoe UI", 9, "bold"), relief="flat")
        menu_del = tk.Menu(mb_del, tearoff=0)
        mb_del.config(menu=menu_del)
        menu_del.add_command(label="TÜMÜNÜ SİL", command=lambda: delete_logs("ALL"))
        menu_del.add_separator()
        menu_del.add_command(label="SADECE TETİKLENENLERİ SİL", command=lambda: delete_logs("MISSING"))
        menu_del.add_command(label="SADECE ANONSLARI SİL", command=lambda: delete_logs("ANONS"))
        menu_del.add_command(label="SADECE SİSTEM/VERİ SİL", command=lambda: delete_logs("DATA"))
        mb_del.pack(side="right", padx=5)
        
        tk.Button(toolbar, text="📊 GENEL ÖZET", command=show_arrival_summary, bg="#0288D1", fg="white", font=("Segoe UI", 9, "bold"), relief="flat").pack(side="right", padx=5)
        
        btn_trash = tk.Button(toolbar, text="♻️ ÇÖP KUTUSU", command=open_trash_folder, bg="#757575", fg="white", font=("Segoe UI", 9, "bold"), relief="flat")
        btn_trash.pack(side="right", padx=5)
        trash_menu = tk.Menu(btn_trash, tearoff=0)
        trash_menu.add_command(label="Çöp Kutusunu Boşalt", command=empty_trash)
        btn_trash.bind("<Button-3>", lambda e: trash_menu.tk_popup(e.x_root, e.y_root))

        # === TAB 2: AYLIK KAYITLAR ===
        tab_monthly = ttk.Frame(nb)
        nb.add(tab_monthly, text="Aylık Kayıtlar")
        
        toolbar_m = tk.Frame(tab_monthly, bg="#ECEFF1", pady=2)
        toolbar_m.pack(side="top", fill="x")
        
        toolbar_m_bottom = tk.Frame(tab_monthly, bg="#ECEFF1", pady=2)
        toolbar_m_bottom.pack(side="top", fill="x")

        tk.Label(toolbar_m, text="Dönem:", bg="#ECEFF1", font=("Segoe UI", 9)).pack(side="left", padx=5)
        
        hist_months_vals = months + ["TÜM YIL"]
        cb_month_m = ttk.Combobox(toolbar_m, values=hist_months_vals, width=15)
        cb_month_m.set(months[now.month - 1])
        cb_month_m.pack(side="left", padx=2)
        
        cb_year_m = ttk.Combobox(toolbar_m, values=[str(i) for i in range(2023, 2031)], width=5)
        cb_year_m.set(str(now.year))
        cb_year_m.pack(side="left", padx=2)
        
        frame_text_m = tk.Frame(tab_monthly)
        frame_text_m.pack(fill="both", expand=True)
        sb_m = tk.Scrollbar(frame_text_m)
        sb_m.pack(side="right", fill="y")
        txt_monthly = tk.Text(frame_text_m, font=("Consolas", 10), wrap="word", yscrollcommand=sb_m.set, bg=konsol_bg, fg=konsol_fg)
        txt_monthly.pack(side="left", fill="both", expand=True)
        sb_m.config(command=txt_monthly.yview)

        # Sağ Tık Menüsü (Aylık Kayıtlar)
        def copy_monthly_selection(event=None):
            if txt_monthly.tag_ranges("sel"):
                selected_text = txt_monthly.get(tk.SEL_FIRST, tk.SEL_LAST)
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)

        def delete_selected_monthly_lines(event=None):
            if not txt_monthly.tag_ranges("sel"):
                messagebox.showwarning("Uyarı", "Silmek için önce bir veya daha fazla kayıt seçin.")
                return

            selected_text = txt_monthly.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            if not selected_text:
                return

            if not messagebox.askyesno("Onay", "Seçili kayıt(lar) silinip Çöp Kutusuna taşınacak.\nEmin misiniz?"):
                return

            try:
                m_name = cb_month_m.get()
                y = cb_year_m.get()
                monthly_file = os.path.join(base_log_dir, "Aylik_Kayitlar", y, f"{m_name}.txt")

                if not os.path.exists(monthly_file):
                    messagebox.showerror("Hata", "Aylık log dosyası bulunamadı.")
                    return

                with open(monthly_file, "r", encoding="utf-8") as f:
                    content = f.read()

                blocks = re.split(r'(-{50,}\n)', content)
                new_content_parts = []
                deleted_blocks_content = []
                deleted_count = 0
                if blocks: new_content_parts.append(blocks[0])

                for i in range(1, len(blocks), 2):
                    separator, block_content = blocks[i], blocks[i+1]
                    if selected_text in block_content:
                        deleted_count += 1
                        deleted_blocks_content.append(block_content)
                        continue
                    else:
                        new_content_parts.extend([separator, block_content])

                if deleted_count > 0:
                    backup_to_trash(monthly_file, "".join(deleted_blocks_content))
                    with open(monthly_file, "w", encoding="utf-8") as f: f.write("".join(new_content_parts))
                    load_monthly_content()
                    messagebox.showinfo("Bilgi", f"{deleted_count} kayıt silindi ve Çöp Kutusuna taşındı.")
                else:
                    messagebox.showinfo("Bilgi", "Seçili metinle eşleşen bir kayıt bloğu bulunamadı.")
            except Exception as e:
                messagebox.showerror("Hata", f"Silme işlemi sırasında hata oluştu: {e}")

        monthly_context_menu = tk.Menu(txt_monthly, tearoff=0)
        monthly_context_menu.add_command(label="Kopyala", command=copy_monthly_selection)
        monthly_context_menu.add_command(label="Seçili Kaydı Sil", command=delete_selected_monthly_lines)

        decode_menu_m = tk.Menu(monthly_context_menu, tearoff=0)
        monthly_context_menu.add_separator()
        monthly_context_menu.add_cascade(label="🔍 Çözümle", menu=decode_menu_m)
        decode_menu_m.add_command(label="SİNOPTİK", command=lambda: self.show_decode_window("SİNOPTİK", txt_monthly.get(tk.SEL_FIRST, tk.SEL_LAST) if txt_monthly.tag_ranges("sel") else ""))
        decode_menu_m.add_command(label="METAR", command=lambda: self.show_decode_window("METAR", txt_monthly.get(tk.SEL_FIRST, tk.SEL_LAST) if txt_monthly.tag_ranges("sel") else ""))
        decode_menu_m.add_command(label="TAF", command=lambda: self.show_decode_window("TAF", txt_monthly.get(tk.SEL_FIRST, tk.SEL_LAST) if txt_monthly.tag_ranges("sel") else ""))

        def show_monthly_context_menu(event):
            decode_menu_m.entryconfig("SİNOPTİK", state="disabled")
            decode_menu_m.entryconfig("METAR", state="disabled")
            decode_menu_m.entryconfig("TAF", state="disabled")
            
            # Seçim yoksa, farenin altındaki satırı otomatik seç
            if not txt_monthly.tag_ranges("sel"):
                index = txt_monthly.index(f"@{event.x},{event.y}")
                txt_monthly.tag_add("sel", f"{index} linestart", f"{index} lineend")
                
            if txt_monthly.tag_ranges("sel"):
                sel_text = txt_monthly.get(tk.SEL_FIRST, tk.SEL_LAST).upper()
                if any(x in sel_text for x in ["SİNOPTİK", "SINOPTIK", "SYNOP", "AAXX", "SITT", "SM"]): decode_menu_m.entryconfig("SİNOPTİK", state="normal")
                if any(x in sel_text for x in ["METAR", "SPECI", "SATT", "SA", "SP"]): decode_menu_m.entryconfig("METAR", state="normal")
                if any(x in sel_text for x in ["TAF", "FCTT", "FC", "FT"]): decode_menu_m.entryconfig("TAF", state="normal")
            monthly_context_menu.tk_popup(event.x_root, event.y_root)

        txt_monthly.bind("<Button-3>", show_monthly_context_menu)

        # Renk Tagları (Aylık Kayıtlar İçin)
        txt_monthly.tag_config("header_highlight", foreground="#00B0FF", font=("Consolas", 11, "bold"))
        txt_monthly.tag_config("uyumsuz_highlight", foreground="#FF5252", font=("Consolas", 10, "bold"))
        txt_monthly.tag_config("f_uyumsuz_highlight", foreground="#E040FB", font=("Consolas", 10, "bold"))
        txt_monthly.tag_config("dikkat_highlight", foreground="#FFD740", font=("Consolas", 10, "bold"))
        txt_monthly.tag_config("uyumlu_highlight", foreground="#69F0AE", font=("Consolas", 10, "bold"))
        txt_monthly.tag_config("delay_highlight", foreground="#00E676", font=("Consolas", 10, "bold"))
        
        # YENİ: Satır bazlı blok renkleri (Okunabilirliği çok artırır)
        txt_monthly.tag_config("metar_line", background="#004D40", foreground="#E0F7FA", font=("Consolas", 10, "bold"))
        txt_monthly.tag_config("taf_line", background="#311B92", foreground="#F3E5F5", font=("Consolas", 10, "bold"))
        txt_monthly.tag_config("synop_line", background="#E65100", foreground="#FFF3E0", font=("Consolas", 10, "bold"))
        txt_monthly.tag_config("speci_line", background="#b71c1c", foreground="#FBE9E7", font=("Consolas", 10, "bold"))
        
        txt_monthly.tag_config("bulten_highlight", foreground="#ECEFF1", font=("Consolas", 10))
        txt_monthly.tag_config("ref_taf_highlight", foreground="#81D4FA", font=("Consolas", 10, "italic"))
        txt_monthly.tag_config("gecmis_hadise_highlight", foreground="#FF4081", font=("Consolas", 10, "bold"))

        var_monthly_filter = tk.StringVar(value="HEPSİ")

        def load_monthly_content(event=None):
            m_name = cb_month_m.get()
            y = cb_year_m.get()
            monthly_file = os.path.join(base_log_dir, "Aylik_Kayitlar", y, f"{m_name}.txt")
            
            txt_monthly.config(state="normal")
            txt_monthly.delete("1.0", tk.END)
            
            if not os.path.exists(monthly_file):
                for m in modes:
                    rb_monthly_dict[m].config(text=f"{m} (0)")
                txt_monthly.insert("end", f"Kayıt bulunamadı: {monthly_file}\n\nLütfen 'Veri Analiz' sekmesinden ilgili ay için 'GEÇMİŞ ANALİZ' işlemi yapınız.")
                txt_monthly.config(state="disabled")
                return

            try:
                with open(monthly_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                m_counts = {m: 0 for m in modes}
                parts_for_count = content.split("="*100 + "\n\n", 1)
                body_for_count = parts_for_count[1] if len(parts_for_count) > 1 else ""
                
                harici_match = re.search(r'(=*)\n>>> HARİCİ RASATLAR.*?\n(=*)\n\n(.*)', content, re.DOTALL)
                if harici_match:
                    harici_text = harici_match.group(3)
                    m_counts["HARİCİ RASATLAR"] = len(re.findall(r'^\[', harici_text, re.MULTILINE))
                
                taf_groups_for_count = re.split(r'(\n>>> .*?:.*)', body_for_count)
                
                def check_block_for_count(block_text, mode):
                    if not block_text.strip() or "KAYIT:" not in block_text: return False
                    if mode == "HEPSİ": return True
                    if mode == "UYUMLU": return "DURUM: UYUMLU" in block_text
                    if mode == "DİKKAT": return "DURUM: DIKKAT" in block_text or "DURUM: DİKKAT" in block_text
                    if mode == "UYUMSUZ": return "DURUM: UYUMSUZ" in block_text and "GEÇMİŞ HADİSE" not in block_text.upper()
                    if mode == "F/UYUMSUZ": return "DURUM: F/UYUMSUZ" in block_text and "GEÇMİŞ HADİSE" not in block_text.upper()
                    if mode == "GEÇ GELEN": return "[GECIKME:" in block_text or "[GECİKME:" in block_text
                    if mode == "RE/GEÇMİŞ HATASI": return "DURUM: RE/GECMIS HATASI" in block_text or "GEÇMİŞ HADİSE" in block_text.upper()
                    return False

                if taf_groups_for_count and taf_groups_for_count[0].strip():
                    for b in re.split(r'\n\n', taf_groups_for_count[0].strip()):
                        for m in modes:
                            if m != "HARİCİ RASATLAR" and check_block_for_count(b, m): m_counts[m] += 1
                                
                for i in range(1, len(taf_groups_for_count), 2):
                    if i+1 < len(taf_groups_for_count):
                        for b in re.split(r'\n\n', taf_groups_for_count[i+1].strip()):
                            for m in modes:
                                if m != "HARİCİ RASATLAR" and check_block_for_count(b, m): m_counts[m] += 1
                                    
                for m in modes:
                    rb_monthly_dict[m].config(text=f"{m} ({m_counts[m]})")
                
                filter_mode = var_monthly_filter.get()
                search_term = entry_search_m.get().strip().lower()
                
                if filter_mode == "HEPSİ" and not search_term:
                    output_content = content
                else:
                    parts = content.split("="*100 + "\n\n", 1)
                    if "📊 AYLIK İSTATİSTİK ÖZETİ" in content:
                        summary_idx = content.find("📊 AYLIK İSTATİSTİK ÖZETİ")
                        end_of_summary_border = content.find("====================================================================================================\n\n", summary_idx)
                        if end_of_summary_border != -1:
                            header_and_summary = content[:end_of_summary_border + 102]
                            body = content[end_of_summary_border + 102:]
                        else:
                            header_and_summary = parts[0] + "="*100 + "\n\n" if len(parts) > 1 else parts[0]
                            body = parts[1] if len(parts) > 1 else ""
                    else:
                        header_and_summary = parts[0] + "="*100 + "\n\n" if len(parts) > 1 else parts[0]
                        body = parts[1] if len(parts) > 1 else ""
                    
                    output_content = header_and_summary

                    if filter_mode == "HARİCİ RASATLAR":
                        match = re.search(r'(=*)\n>>> HARİCİ RASATLAR.*', content, re.DOTALL)
                        if match:
                            output_content += match.group(0)
                        else:
                            output_content += "Bu ay için harici rasat kaydı bulunamadı."
                    else:
                        taf_groups = re.split(r'(\n>>> .*?:.*)', body) # TAF GRUBU ve HARİCİ RASATLAR başlıklarını yakalar
                        
                        def check_block(block_text):
                            if not block_text.strip(): return False
                            radio_match = (filter_mode == "HEPSİ" or
                                        (filter_mode == "UYUMLU" and "DURUM: UYUMLU" in block_text) or
                                        (filter_mode == "DİKKAT" and ("DURUM: DIKKAT" in block_text or "DURUM: DİKKAT" in block_text)) or
                                        (filter_mode == "UYUMSUZ" and "DURUM: UYUMSUZ" in block_text and "GEÇMİŞ HADİSE" not in block_text.upper()) or
                                        (filter_mode == "F/UYUMSUZ" and "DURUM: F/UYUMSUZ" in block_text and "GEÇMİŞ HADİSE" not in block_text.upper()) or
                                        (filter_mode == "GEÇ GELEN" and ("[GECIKME:" in block_text or "[GECİKME:" in block_text)) or
                                        (filter_mode == "RE/GEÇMİŞ HATASI" and ("DURUM: RE/GECMIS HATASI" in block_text or "GEÇMİŞ HADİSE" in block_text.upper())))
                            if not radio_match: return False
                            search_match = (not search_term or search_term in block_text.lower())
                            return search_match

                        initial_content = taf_groups[0]
                        if initial_content.strip():
                            initial_blocks = re.split(r'\n\n', initial_content.strip())
                            matching_initial_blocks = [block for block in initial_blocks if check_block(block)]
                            if matching_initial_blocks:
                                output_content += "\n\n".join(matching_initial_blocks) + "\n"

                        for i in range(1, len(taf_groups), 2):
                            taf_header = taf_groups[i]
                            observations_text = taf_groups[i+1]
                            obs_blocks = re.split(r'\n\n', observations_text.strip())
                            matching_blocks = [block for block in obs_blocks if check_block(block)]
                            if matching_blocks:
                                output_content += taf_header
                                output_content += "\n" + "\n\n".join(matching_blocks) + "\n"
                
                txt_monthly.insert("end", output_content)

                # --- RENKLENDİRME (HIGHLIGHTING) ---
                def apply_tag(pattern, tag):
                    start = "1.0"
                    while True:
                        pos = txt_monthly.search(pattern, start, stopindex=tk.END, regexp=True)
                        if not pos: break
                        # Satır sonuna kadar boya
                        line_end = txt_monthly.index(f"{pos} lineend")
                        txt_monthly.tag_add(tag, pos, line_end)
                        start = f"{pos}+1c"

                def apply_tag_match(pattern, tag):
                    start = "1.0"
                    while True:
                        count_var = tk.IntVar()
                        pos = txt_monthly.search(pattern, start, stopindex=tk.END, regexp=True, count=count_var)
                        if not pos: break
                        end = f"{pos}+{count_var.get()}c"
                        txt_monthly.tag_add(tag, pos, end)
                        start = end

                # Başlıklar
                apply_tag(r'^>>> .*', "header_highlight")
                apply_tag(r'^KARDELEN AYLIK ANALİZ RAPORU.*', "header_highlight")
                
                # Durumlar
                apply_tag(r'DURUM: UYUMSUZ', "uyumsuz_highlight")
                apply_tag(r'DURUM: F/UYUMSUZ', "f_uyumsuz_highlight")
                apply_tag(r'DURUM: DİKKAT', "dikkat_highlight")
                apply_tag(r'DURUM: UYUMLU', "uyumlu_highlight")
                
                # Referans TAF Satırı
                apply_tag(r'^\s*(►\s*)?REF TAF:.*', "ref_taf_highlight")

                # Geçmiş Hadise
                apply_tag_match(r'GEÇMİŞ HADİSE', "gecmis_hadise_highlight")

                # YENİ: Ana Başlık Satırları (Blok Gösterimi)
                apply_tag(r'^KAYIT:.*\|\s*METAR\s*\|.*', "metar_line")
                apply_tag(r'^KAYIT:.*\|\s*TAF\s*\|.*', "taf_line")
                apply_tag(r'^KAYIT:.*\|\s*(SİNOPTİK|SYNOP|SINOPTIK)\s*\|.*', "synop_line")
                apply_tag(r'^KAYIT:.*\|\s*SPECI\s*\|.*', "speci_line")

                # YENİ: Bülten Satırları
                apply_tag(r'^\s*BULTEN\s*:.*', "bulten_highlight")

                # Özel Renklendirmeler (Gecikme)
                apply_tag_match(r'\[GEC[Iİ]KME:.*?\]', "delay_highlight")

                txt_monthly.tag_raise("delay_highlight")

                # Arama Vurgusu
                if search_term:
                    start_idx = "1.0"
                    while True:
                        pos = txt_monthly.search(search_term, start_idx, stopindex=tk.END, nocase=True)
                        if not pos: break
                        end_idx = f"{pos}+{len(search_term)}c"
                        txt_monthly.tag_add("search_highlight", pos, end_idx)
                        start_idx = end_idx
                    txt_monthly.tag_config("search_highlight", background="#FFEB3B", foreground="black")

            except Exception as e:
                txt_monthly.insert("end", f"Filtreleme hatası: {e}")
                
            txt_monthly.config(state="disabled")

        # Konsol renklerini anında (dinamik) değiştiren fonksiyon
        def update_console_colors(*args):
            try:
                bg = self.settings_vars['var_konsol_renk'].get()
                r, g, b = self.root.winfo_rgb(bg)
                brightness = (r*299 + g*587 + b*114) / 1000
                fg = "#CFD8DC" if brightness < 32768000 else "#212121"
                txt_log.config(bg=bg, fg=fg)
                txt_monthly.config(bg=bg, fg=fg)
            except Exception: pass
        
        if 'var_konsol_renk' in self.settings_vars:
            self.settings_vars['var_konsol_renk'].trace_add("write", update_console_colors)

        def get_monthly_summary_text(target_file, month_name, year):
            counts = {"METAR": 0, "TAF": 0, "SİNOPTİK": 0, "SPECI": 0, "HARİCİ": 0}
            late_counts = {"METAR": 0, "TAF": 0, "SİNOPTİK": 0}
            station_late_counts = {}
            total_events = 0
            
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                summary_match = re.search(r'(📊 AYLIK İSTATİSTİK ÖZETİ.*?)(?:\n={50,})', content, re.DOTALL)
                existing_summary = summary_match.group(1).strip() if summary_match else ""
                
                lines = content.split('\n')
                current_type = None
                is_late_current = False
                for line in lines:
                    if line.startswith("KAYIT:") and "| RASAT:" in line:
                        parts = line.split("|")
                        if len(parts) >= 3:
                            turu = parts[2].strip().upper()
                            if "METAR" in turu: counts["METAR"] += 1; current_type = "METAR"
                            elif "SPECI" in turu: counts["SPECI"] += 1; current_type = "SPECI"
                            elif "TAF" in turu: counts["TAF"] += 1; current_type = "TAF"
                            elif "SİNOPTİK" in turu or "SYNOP" in turu or "SINOPTIK" in turu: counts["SİNOPTİK"] += 1; current_type = "SİNOPTİK"
                            else: counts["HARİCİ"] += 1; current_type = "HARİCİ"
                            
                            total_events += 1
                            is_late_current = False
                    elif line.startswith("DURUM:") and "[GECİKME:" in line and current_type:
                        if current_type in late_counts:
                            late_counts[current_type] += 1
                            is_late_current = True
                    elif is_late_current and ("BULTEN :" in line or "BULTEN:" in line):
                        st = None
                        if current_type == "SİNOPTİK":
                            m = re.search(r'AAXX\s+\d{4}\s+(\d{5})', line)
                            if m: st = m.group(1)
                        else:
                            m = re.search(r'\b(LT[A-Z0-9]{2})\b', line)
                            if m: st = m.group(1)
                            
                        if not st: st = "Bilinmeyen"
                        
                        if st not in station_late_counts:
                            station_late_counts[st] = {"METAR": 0, "TAF": 0, "SİNOPTİK": 0}
                        if current_type in station_late_counts[st]:
                            station_late_counts[st][current_type] += 1
                        is_late_current = False
                            
                report = f"DÖNEM: {month_name} {year}\nTOPLAM RASAT: {total_events}\n" + "-"*40 + "\n"
                report += f"{'TÜR':<12} {'ADET':<10} {'GEÇ GELEN'}\n" + "-"*40 + "\n"
                report += f"{'METAR':<12} {counts['METAR']:<10} {late_counts['METAR']}\n"
                report += f"{'TAF':<12} {counts['TAF']:<10} {late_counts['TAF']}\n"
                report += f"{'SİNOPTİK':<12} {counts['SİNOPTİK']:<10} {late_counts['SİNOPTİK']}\n"
                report += f"{'SPECI':<12} {counts['SPECI']:<10} -\n"
                if counts["HARİCİ"] > 0: report += f"{'HARİCİ':<12} {counts['HARİCİ']:<10} -\n"
                report += "-"*40 + "\n\n"
                
                if any(late_counts.values()):
                    report += "GEÇ GELENLERİN İSTASYON BAZLI DAĞILIMI:\n" + "-"*40 + "\n"
                    sorted_stations = sorted(station_late_counts.items(), key=lambda x: sum(x[1].values()), reverse=True)
                    for st, sc in sorted_stations:
                        details = []
                        if sc['METAR'] > 0: details.append(f"{sc['METAR']} METAR")
                        if sc['TAF'] > 0: details.append(f"{sc['TAF']} TAF")
                        if sc['SİNOPTİK'] > 0: details.append(f"{sc['SİNOPTİK']} SİNOPTİK")
                        total_st_late = sum(sc.values())
                        report += f"📍 {st:<10} Toplam: {total_st_late:<4} ({', '.join(details)})\n"
                    report += "-"*40 + "\n\n"
                
                if existing_summary: report += existing_summary + "\n"
                return report
            except Exception as e:
                return f"Özet oluşturulurken hata: {e}"

        def show_monthly_summary():
            try:
                m_name = cb_month_m.get()
                y = cb_year_m.get()
                monthly_file = os.path.join(base_log_dir, "Aylik_Kayitlar", y, f"{m_name}.txt")
                if not os.path.exists(monthly_file):
                    messagebox.showinfo("Bilgi", "Aylık log dosyası bulunamadı.")
                    return
                report = get_monthly_summary_text(monthly_file, m_name, y)
                sum_win = tk.Toplevel(self.root)
                sum_win.title("Aylık Genel Özet")
                sum_win.geometry("450x550")
                txt_sum = tk.Text(sum_win, font=("Consolas", 10), bg="#ECEFF1", padx=10, pady=10)
                txt_sum.pack(fill="both", expand=True)
                txt_sum.insert("end", report)
                txt_sum.config(state="disabled")
                def copy_report():
                    self.root.clipboard_clear()
                    self.root.clipboard_append(report)
                    messagebox.showinfo("Bilgi", "Rapor panoya kopyalandı.", parent=sum_win)
                tk.Button(sum_win, text="📋 PANOYA KOPYALA", command=copy_report, bg="#4CAF50", fg="white", font=("Segoe UI", 9, "bold"), pady=5, relief="flat").pack(fill="x")
            except Exception as e:
                messagebox.showerror("Hata", f"Aylık özet oluşturulurken hata: {e}")

        def delete_monthly_logs_bulk():
            m_name = cb_month_m.get()
            y = cb_year_m.get()
            monthly_file = os.path.join(base_log_dir, "Aylik_Kayitlar", y, f"{m_name}.txt")
            
            if not os.path.exists(monthly_file):
                messagebox.showwarning("Uyarı", "Silinecek dosya bulunamadı.", parent=log_win)
                return
            
            if messagebox.askyesno("Onay", f"{m_name} {y} dönemine ait TÜM AYLIK KAYITLAR silinecek.\nDosya Çöp Kutusuna taşınacak.\nEmin misiniz?", parent=log_win):
                try:
                    with open(monthly_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    if backup_to_trash(monthly_file, content):
                        os.remove(monthly_file)
                        load_monthly_content()
                        messagebox.showinfo("Bilgi", "Aylık kayıt dosyası silindi ve Çöp Kutusuna taşındı.", parent=log_win)
                    else:
                        messagebox.showerror("Hata", "Yedekleme yapılamadığı için silme iptal edildi.", parent=log_win)
                except Exception as e:
                    messagebox.showerror("Hata", f"Silme hatası: {e}", parent=log_win)

        tk.Button(toolbar_m, text="GÖSTER", command=load_monthly_content, bg="#2196F3", fg="white", font=("Segoe UI", 9, "bold"), relief="flat").pack(side="left", padx=5)
        tk.Button(toolbar_m, text="🗑️ TÜMÜNÜ SİL", command=delete_monthly_logs_bulk, bg="#D32F2F", fg="white", font=("Segoe UI", 9, "bold"), relief="flat").pack(side="left", padx=5)
        
        tk.Button(toolbar_m, text="📊 GENEL ÖZET", command=show_monthly_summary, bg="#0288D1", fg="white", font=("Segoe UI", 9, "bold"), relief="flat").pack(side="right", padx=5)

        btn_trash_m = tk.Button(toolbar_m, text="♻️ ÇÖP KUTUSU", command=open_trash_folder, bg="#757575", fg="white", font=("Segoe UI", 9, "bold"), relief="flat")
        btn_trash_m.pack(side="left", padx=5)
        trash_menu_m = tk.Menu(btn_trash_m, tearoff=0)
        trash_menu_m.add_command(label="Çöp Kutusunu Boşalt", command=empty_trash)
        btn_trash_m.bind("<Button-3>", lambda e: trash_menu_m.tk_popup(e.x_root, e.y_root))
        
        # --- FİLTRELEME ---
        f_filter_m = tk.Frame(toolbar_m_bottom, bg="#ECEFF1")
        f_filter_m.pack(side="left", padx=(5, 2))
        tk.Label(f_filter_m, text="Filtre:", bg="#ECEFF1", font=("Segoe UI", 9, "bold")).pack(side="left")
        modes = ["HEPSİ", "UYUMLU", "DİKKAT", "UYUMSUZ", "F/UYUMSUZ", "GEÇ GELEN", "HARİCİ RASATLAR", "RE/GEÇMİŞ HATASI"]
        
        rb_monthly_dict = {}
        for mode in modes:
            rb = tk.Radiobutton(f_filter_m, text=mode, variable=var_monthly_filter, value=mode, command=load_monthly_content, bg="#ECEFF1", font=("Segoe UI", 9))
            rb.pack(side="left", padx=2)
            rb_monthly_dict[mode] = rb

        # --- ARAMA KUTUSU (FİLTRELEME) ---
        tk.Button(toolbar_m_bottom, text="🔍", command=load_monthly_content, bg="#B0BEC5", relief="flat", width=3).pack(side="right", padx=2)
        entry_search_m = tk.Entry(toolbar_m_bottom, width=20)
        entry_search_m.pack(side="right", padx=2)
        tk.Label(toolbar_m_bottom, text="Ara:", bg="#ECEFF1", font=("Segoe UI", 9, "bold")).pack(side="right", padx=2)
        
        entry_search_m.bind("<Return>", load_monthly_content)

        load_content()

    def show_alarm_history(self):
        """Son 24 saatteki alarmları gösteren pencere."""
        hist_win = tk.Toplevel(self.root)
        hist_win.title("Son 24 Saat Alarm Geçmişi")
        hist_win.geometry("800x500")
        
        txt = tk.Text(hist_win, font=("Consolas", 10), bg="#263238", fg="white", padx=10, pady=10)
        txt.pack(fill="both", expand=True)
        
        # Taglar
        txt.tag_config("EKSİK", foreground="#FF5252", font=("Consolas", 10, "bold"))
        txt.tag_config("UYUMSUZ", foreground="#FFD740", font=("Consolas", 10, "bold"))
        txt.tag_config("INFO", foreground="#B0BEC5")
        
        base_log_dir = config_manager.USER_DATA_DIR
        
        # Bugün ve Dün
        dates = [datetime.now(timezone.utc), datetime.now(timezone.utc) - timedelta(days=1)]
        found_alarms = []
        
        for d in dates:
            d_str = d.strftime('%Y-%m-%d')
            f_path = os.path.join(base_log_dir, d_str, "kardelen_gunluk_log.txt")
            if os.path.exists(f_path):
                with open(f_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "ALARM" in line or "EKSİK" in line or "UYUMSUZ" in line:
                            found_alarms.append(line.strip())
        
        # Sırala (Zaman damgası başta olduğu için string sort çalışır)
        found_alarms.sort()
        
        for line in found_alarms:
            tag = "INFO"
            if "EKSİK" in line: tag = "EKSİK"
            elif "UYUMSUZ" in line: tag = "UYUMSUZ"
            txt.insert("end", line + "\n", tag)
            
        txt.config(state="disabled")

    def flash_visual_alert(self):
        """Alarm çaldığında saati görsel olarak yanıp söndürür."""
        if not hasattr(self, 'lbl_settings_clock') or not self.lbl_settings_clock: return
        
        orig_fg = "#00E676" # Normal Yeşil
        alert_fg = "#FF5252" # Alarm Kırmızısı
        
        def _blink(count):
            if count <= 0 or not self.lbl_settings_clock.winfo_exists():
                try: self.lbl_settings_clock.config(fg=orig_fg)
                except: pass
                return
            
            try:
                current = self.lbl_settings_clock.cget("fg")
                new_col = alert_fg if str(current).upper() == orig_fg else orig_fg
                self.lbl_settings_clock.config(fg=new_col)
                self.root.after(200, lambda: _blink(count-1))
            except: pass
            
        _blink(20) # 4 saniye boyunca yanıp sön (Hızlandırıldı)

    def rasat_yok_testi(self):
        if self.settings_vars['var_anons_aktif'].get():
            self.alarm_motoru.google_seslendir("DİKKAT TEST. 19 40 TAF GELMEMİŞTİR.", hiz=150, pitch=0, use_piper=False, use_edge=True, edge_voice="Ahmet (Erkek)", use_openai=False)
        else:
            self.play_alarm_sound()

    def rasat_geldi_testi(self):
        if self.settings_vars['var_anons_aktif'].get():
            self.flash_visual_alert()
            self.alarm_motoru.google_seslendir("BEKLENEN VERİ SİSTEME DÜŞTÜ. TEST.", hiz=150, pitch=0, use_piper=False, use_edge=True, edge_voice="Ahmet (Erkek)", use_openai=False)
        else:
            self.play_alarm_sound()

    def alarm_simulation(self):
        # Simülasyon Seçim Penceresi
        sim_win = tk.Toplevel(self.root)
        sim_win.title("Simülasyon & Test")
        sim_win.geometry("350x450")
        
        # Zaman Kaydırma (Buraya taşındı)
        f_time = tk.LabelFrame(sim_win, text="Zaman Kaydırma (Dakika)", font=("Segoe UI", 9, "bold"), padx=5, pady=5)
        f_time.pack(fill="x", padx=10, pady=10)
        
        tk.Label(f_time, text="Offset:", font=("Segoe UI", 9)).pack(side="left")
        tk.Spinbox(f_time, from_=-525600, to=525600, textvariable=self.settings_vars['var_test_time_offset'], width=8, font=("Consolas", 10)).pack(side="left", padx=5)
        
        def reset_offset():
            self.settings_vars['var_test_time_offset'].set(0)
            self.root.bell()
        tk.Button(f_time, text="SIFIRLA", command=reset_offset, bg="#CFD8DC", font=("Segoe UI", 8, "bold"), relief="flat").pack(side="left", padx=5)
        
        tk.Label(sim_win, text="Eksik Veri Simülasyonu", font=("Segoe UI", 11, "bold")).pack(pady=(10, 5))
        
        # Gecikme Ayarı
        frame_delay = tk.Frame(sim_win)
        frame_delay.pack(pady=5)
        tk.Label(frame_delay, text="Gecikme (sn):").pack(side="left")
        var_delay = tk.IntVar(value=0)
        tk.Spinbox(frame_delay, from_=0, to=300, textvariable=var_delay, width=5).pack(side="left", padx=5)
        
        def start_sim(mode):
            items = []
            freq = self.settings_vars['var_alarm_freq_metar'].get() # Varsayılan frekans

            if mode == "METAR": items = ["TEST 1250 METAR"]
            elif mode == "TAF": 
                items = ["TEST 1240 TAF"]
                freq = self.settings_vars['var_alarm_freq_taf'].get()
            elif mode == "SINOPTIK": 
                items = ["TEST 1200 SİNOPTİK"]
                freq = self.settings_vars['var_alarm_freq_synop'].get()
            elif mode == "HEPSİ": items = ["TEST 1250 METAR", "TEST 1240 TAF", "TEST 1200 SİNOPTİK"]
            
            delay = var_delay.get()
            self.app_state["missing_items"] = items
            self.app_state["missing_data"] = True
            # Alarmın 'delay' saniye sonra çalması için zamanlayıcıyı ayarla
            self.app_state["last_alarm"] = time.time() + delay - freq
            sim_win.destroy()
            
            if delay > 0:
                # Geri Sayım Penceresi
                cd_win = tk.Toplevel(self.root)
                cd_win.overrideredirect(True)
                cd_win.attributes('-topmost', True)
                
                w, h = 300, 170
                x = (self.root.winfo_screenwidth() // 2) - (w // 2)
                y = (self.root.winfo_screenheight() // 2) - (h // 2)
                cd_win.geometry(f"{w}x{h}+{x}+{y}")
                cd_win.configure(bg="#263238", highlightbackground="#FF5722", highlightthickness=3)
                
                tk.Label(cd_win, text=f"SİMÜLASYON: {mode}", fg="#FF5722", bg="#263238", font=("Segoe UI", 12, "bold")).pack(pady=(15, 5))
                lbl_cd = tk.Label(cd_win, text=f"ALARM: {delay} sn", fg="white", bg="#263238", font=("Consolas", 20, "bold"))
                lbl_cd.pack(pady=5)
                
                def cancel_countdown():
                    self.app_state["missing_data"] = False
                    cd_win.destroy()
                    
                tk.Button(cd_win, text="İPTAL", command=cancel_countdown, bg="#D32F2F", fg="white", font=("Segoe UI", 9, "bold"), width=12, relief="flat").pack(pady=5)
                
                def _tick(rem):
                    if not self.root.winfo_exists() or not self.app_state.get("missing_data"): cd_win.destroy(); return
                    if rem <= 0: cd_win.destroy()
                    else:
                        lbl_cd.config(text=f"ALARM: {rem} sn")
                        cd_win.after(1000, _tick, rem-1)
                _tick(delay)
            else:
                messagebox.showinfo("Simülasyon", f"{mode} eksikliği simüle ediliyor.\nAlarm hemen çalacak.\nDurdurmak için 'GÖSTER' butonuna basınız.")

        tk.Button(sim_win, text="Sadece METAR", command=lambda: start_sim("METAR"), width=20, bg="#E0E0E0", relief="flat").pack(pady=5)
        tk.Button(sim_win, text="Sadece TAF", command=lambda: start_sim("TAF"), width=20, bg="#E0E0E0", relief="flat").pack(pady=5)
        tk.Button(sim_win, text="Sadece SİNOPTİK", command=lambda: start_sim("SINOPTIK"), width=20, bg="#E0E0E0", relief="flat").pack(pady=5)
        tk.Button(sim_win, text="HEPSİ", command=lambda: start_sim("HEPSİ"), width=20, bg="#B0BEC5", relief="flat").pack(pady=5)
        
        def sim_new_day():
            now = datetime.now(timezone.utc)
            target = now.replace(hour=0, minute=5, second=0, microsecond=0)
            # if target < now: target += timedelta(days=1) # İPTAL: Geleceğe atmasın
            diff = int((target - now).total_seconds() / 60)
            self.settings_vars['var_test_time_offset'].set(diff)
            sim_win.destroy()
            
            if hasattr(self, 'verileri_cek'):
                self.verileri_cek()

            messagebox.showinfo("Simülasyon", "Saat 00:05 Z (Bugün) yapıldı.\nSistem DÜNÜN 23:50 verisini arayacak.\n\nVeriler 'Veri Analiz' sekmesine yükleniyor.\nLütfen o sekmeyi kontrol ediniz.")

        tk.Button(sim_win, text="Yeni Gün (00:05Z) Testi", command=sim_new_day, width=20, bg="#B3E5FC", relief="flat").pack(pady=5)
        
        def sim_missing_new_day():
            now = datetime.now(timezone.utc)
            target = now.replace(hour=0, minute=5, second=0, microsecond=0)
            diff = int((target - now).total_seconds() / 60)
            self.settings_vars['var_test_time_offset'].set(diff)
            
            items = ["2350 METAR", "2240 TAF"]
            self.app_state["missing_items"] = items
            self.app_state["missing_data"] = True
            self.app_state["last_alarm"] = time.time() - 300 # Alarm hemen çalsın
            self.app_state["last_refresh"] = time.time() # Oto yenilemeyi ertele
            
            sim_win.destroy()
            messagebox.showinfo("Simülasyon", "Saat 00:05 Z yapıldı.\n23:50 METAR ve 22:40 TAF eksikliği simüle ediliyor.\n\nAlarm çalmalı.")

        tk.Button(sim_win, text="00:05Z Eksik Veri Testi", command=sim_missing_new_day, width=20, bg="#B0BEC5", relief="flat").pack(pady=5)
        
        def sim_ontime_warning():
            now = datetime.now(timezone.utc)
            # 51 geçeye ayarla
            target = now.replace(minute=51, second=0, microsecond=0)
            diff = int((target - now).total_seconds() / 60)
            self.settings_vars['var_test_time_offset'].set(diff)
            
            obs_h = target.hour
            items = [f"{obs_h:02d}50 METAR"]
            
            self.app_state["missing_items"] = items
            self.app_state["missing_data"] = True
            
            # Oto yenilemeyi kapat ki listeyi ezmesin
            self.settings_vars['var_oto_yenile'].set(False)
            
            sim_win.destroy()
            messagebox.showinfo("Simülasyon", f"Saat {target.strftime('%H:%M')} Z yapıldı.\nOto Yenileme durduruldu.\n\nOn-Time (İkaz) Alarmı ('DİKKAT {obs_h:02d}50 METAR GELMEDİ') çalmalı ve 51, 52, 53, 54 geçe tekrar etmelidir.")

        tk.Button(sim_win, text="51 Geçe İkaz (DİKKAT) Testi", command=sim_ontime_warning, width=25, bg="#FFCC80", relief="flat").pack(pady=5)

        def sim_missing_00z_synop():
            now = datetime.now(timezone.utc)
            # 01:05Z sets check for 00:00Z Synop
            target = now.replace(hour=1, minute=5, second=0, microsecond=0)
            diff = int((target - now).total_seconds() / 60)
            self.settings_vars['var_test_time_offset'].set(diff)
            
            items = ["0000 SİNOPTİK"]
            self.app_state["missing_items"] = items
            self.app_state["missing_data"] = True
            self.app_state["last_alarm"] = time.time() - 300
            self.app_state["last_refresh"] = time.time()
            
            sim_win.destroy()
            messagebox.showinfo("Simülasyon", "Saat 01:05 Z yapıldı.\n00:00 SİNOPTİK eksikliği simüle ediliyor.\n\nAlarm çalmalı.")

        tk.Button(sim_win, text="00Z Sinoptik Testi", command=sim_missing_00z_synop, width=20, bg="#B0BEC5", relief="flat").pack(pady=5)
        
    def set_standard_alarm_settings(self):
        if messagebox.askyesno("Standart Ayarlar", "Alarm ayarları fabrika standartlarına (varsayılan) döndürülecek.\nMevcut değişiklikleriniz kaybolabilir.\nEmin misiniz?"):
            alarm_keys = [
                'var_anons_aktif', 'var_trend_alarm_aktif', 'var_metar_alarm_aktif',
                'var_sinoptik_alarm_aktif', 'var_taf_alarm_aktif', 'var_tebrik_aktif',
                'var_alarm_freq_metar', 'var_alarm_freq_taf', 'var_alarm_freq_synop', 'var_alarm_freq_incompatible',
                'var_metar_start_min', 'var_synop_start_min', 'var_taf_start_min',
                'var_ozel_ses_yolu', 'var_alarm_max_volume',
                'var_saat_basi_aktif', 'var_rasat_zamani_aktif', 
                'var_rasat_zamani_start_min', 'var_alarm_freq_rasat_zamani'
            ]
            for k in alarm_keys:
                if k in self.default_values:
                    self.settings_vars[k].set(self.default_values[k])
            messagebox.showinfo("Bilgi", "Alarm ayarları standart değerlere sıfırlandı.")

    def activate_silent_mode(self):
        if messagebox.askyesno("Sessiz Mod", "Tüm sesli uyarılar ve alarmlar kapatılacak. Emin misiniz?"):
            self.settings_vars['var_anons_aktif'].set(False)
            self.settings_vars['var_trend_alarm_aktif'].set(False)
            self.settings_vars['var_metar_alarm_aktif'].set(False)
            self.settings_vars['var_sinoptik_alarm_aktif'].set(False)
            self.settings_vars['var_taf_alarm_aktif'].set(False)
            self.settings_vars['var_saat_basi_aktif'].set(False)
            self.settings_vars['var_manuel_alarm_aktif'].set(False)
            self.settings_vars['var_tebrik_aktif'].set(False)
            for i in range(5):
                self.settings_vars[f'var_sa_active_{i}'].set(False)
            messagebox.showinfo("Bilgi", "Sessiz mod etkinleştirildi.")

    def activate_audible_mode(self):
        if messagebox.askyesno("Sesli Mod", "Tüm sesli uyarılar ve alarmlar açılacak. Emin misiniz?"):
            self.settings_vars['var_anons_aktif'].set(True)
            self.settings_vars['var_trend_alarm_aktif'].set(True)
            self.settings_vars['var_metar_alarm_aktif'].set(True)
            self.settings_vars['var_sinoptik_alarm_aktif'].set(True)
            self.settings_vars['var_taf_alarm_aktif'].set(True)
            self.settings_vars['var_tebrik_aktif'].set(True)
            messagebox.showinfo("Bilgi", "Sesli mod etkinleştirildi.")

    def backup_settings(self):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON Dosyası", "*.json"), ("YAML Dosyası", "*.yaml"), ("Tüm Dosyalar", "*.*")]
            )
            if not file_path: return

            data = {k: v.get() for k, v in self.settings_vars.items()}
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.endswith(('.yaml', '.yml')):
                    yaml.dump(data, f, allow_unicode=True)
                else:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            
            messagebox.showinfo("Başarılı", "Ayarlar başarıyla yedeklendi.")
        except Exception as e:
            messagebox.showerror("Hata", f"Yedekleme hatası: {e}")

    def restore_settings(self):
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[("JSON Dosyası", "*.json"), ("YAML Dosyası", "*.yaml"), ("Tüm Dosyalar", "*.*")]
            )
            if not file_path: return

            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith(('.yaml', '.yml')):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            count = 0
            for k, v in data.items():
                if k in self.settings_vars:
                    try:
                        self.settings_vars[k].set(v)
                        count += 1
                    except: pass
            
            gui_settings.save_settings(self.settings_vars)
            self.last_saved_state = self.get_current_settings_state()
            messagebox.showinfo("Başarılı", f"{count} ayar yedekten yüklendi ve kaydedildi.")
        except Exception as e:
            messagebox.showerror("Hata", f"Yükleme hatası: {e}")

    def save_settings_json(self):
        try:
            gui_settings.save_settings(self.settings_vars)
            self.last_saved_state = self.get_current_settings_state()
            messagebox.showinfo("Bilgi", "Ayarlar varsayılan olarak kaydedildi.\n(Program açılışında bu ayarlar yüklenecek.)")
        except Exception as e:
            messagebox.showerror("Hata", f"Kaydetme hatası: {e}")

    def apply_temporary_settings(self):
        if hasattr(self, 'apply_interface_settings'):
            self.apply_interface_settings()
        messagebox.showinfo("Bilgi", "Ayarlar bu oturum için uygulandı.\n(Program kapanınca unutulur.)")

    def reset_to_defaults(self):
        if messagebox.askyesno("Sıfırlama Onayı", "TÜM ayarlar fabrika çıkış değerlerine sıfırlanacak.\nBu işlem geri alınamaz.\nEmin misiniz?"):
            # Merkezi varsayılanları kullan
            for k, v in self.default_values.items():
                if k in self.settings_vars: self.settings_vars[k].set(v)
            
            # Özel alarmları sıfırla
            for i in range(5):
                self.settings_vars[f'var_sa_active_{i}'].set(False)
                self.settings_vars[f'var_sa_msg_{i}'].set("")
                
            messagebox.showinfo("Bilgi", "Tüm ayarlar sıfırlandı.")

    def get_current_settings_state(self):
        return {k: v.get() for k, v in self.settings_vars.items()}

    def on_settings_change_handler(self):
        if hasattr(self, 'apply_interface_settings'):
            self.apply_interface_settings()
            
        try:
            if hasattr(self, 'robot'):
                self.robot.trend_min_sure = self.settings_vars['var_trend_min_sure'].get()
                self.robot.trend_max_sure = self.settings_vars['var_trend_max_sure'].get()
                self.robot.trend_tl_min_sure = self.settings_vars.get('var_trend_tl_min_sure', tk.IntVar(value=15)).get()
                self.robot.trend_tl_max_sure = self.settings_vars.get('var_trend_tl_max_sure', tk.IntVar(value=90)).get()
                self.robot.trend_zaman_aktif = self.settings_vars['var_trend_zaman_aktif'].get()
                self.robot.taf_esnek_mod_aktif = self.settings_vars.get('var_taf_esnek_mod', tk.BooleanVar(value=True)).get()
                self.robot.kati_icao_kurallari = self.settings_vars.get('var_kati_icao_kurallari', tk.BooleanVar(value=False)).get()
                self.robot.save_settings() # Değişikliği kalıcı olarak robota kaydet
        except Exception as e:
            # Hata durumunda programın çökmesini engelle, sadece logla
            logging.warning(f"Ayarlar robota kaydedilirken hata oluştu: {e}")