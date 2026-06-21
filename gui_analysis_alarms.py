# -*- coding: utf-8 -*-
import tkinter as tk
from datetime import datetime, timedelta, timezone
import time
import re
import ctypes
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import gui_utils

class AnalysisAlarmMixin:
    """
    Alarm kontrolleri ve saat döngüsü işlemlerini yöneten Mixin sınıfı.
    """
    def parse_time_str(self, time_val):
        """HH:MM veya HH formatındaki stringi (saat, dakika) olarak döndürür."""
        try:
            time_str = str(time_val).strip()
            if ":" in time_str:
                h, m = map(int, time_str.split(":"))
                return h, m
            elif len(time_str) == 4 and time_str.isdigit():
                return int(time_str[:2]), int(time_str[2:])
            else:
                return int(time_str), 0
        except: return 0, 0

    def is_taf_present_for_hour(self, target_hour):
        """Verilen saat için TAF verisinin gelip gelmediğini kontrol eder."""
        grouped_data = self.app_state.get("last_grouped_data")
        if not grouped_data: return False
        
        for group in grouped_data:
            t = group.get('taf')
            if t and t.get('dt'):
                if t['dt'].hour == target_hour:
                    return True
        return False

    def _check_special_alarms(self, now):
        """Özel tanımlı alarmları kontrol eder."""
        for i in range(5):
            try:
                if not self.settings_vars[f'var_sa_active_{i}'].get(): continue
                
                t_str = self.settings_vars[f'var_sa_time_{i}'].get()
                if not t_str or ":" not in t_str: continue
                
                h, m = map(int, t_str.split(':'))
                
                # Dinamik Tekrar Mantığı
                interval = 0
                count = 0
                try:
                    interval = int(self.settings_vars[f'var_sa_repeat_{i}'].get())
                    count = int(self.settings_vars[f'var_sa_count_{i}'].get())
                except: pass

                is_time_match = False
                if interval > 0 and count > 0:
                    start_min = h * 60 + m
                    curr_min = now.hour * 60 + now.minute
                    diff = curr_min - start_min
                    if diff >= 0 and diff % interval == 0 and (diff // interval) <= count:
                        is_time_match = True
                elif now.hour == h and now.minute == m:
                    is_time_match = True

                if not is_time_match: continue
                
                freq = self.settings_vars[f'var_sa_freq_{i}'].get()
                weekday = now.weekday() # 0=Pazartesi
                day = now.day
                
                trigger = False
                if freq == "Her Gün": trigger = True
                elif freq == "Hafta İçi Her Gün" and weekday < 5: trigger = True
                elif freq == "Hafta Sonu" and weekday >= 5: trigger = True
                elif freq == "Tek Seferlik":
                    d_str = self.settings_vars[f'var_sa_date_{i}'].get()
                    if now.strftime("%d.%m.%Y") == d_str: trigger = True
                elif freq == "Her Ayın 1'i" and day == 1: trigger = True
                elif freq == "Her Ayın 15'i" and day == 15: trigger = True
                else:
                    days_map = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
                    if freq in days_map and days_map.index(freq) == weekday: trigger = True
                
                if trigger:
                    msg = self.settings_vars[f'var_sa_msg_{i}'].get()
                    self._trigger_special_alarm(msg)
            except: pass

    def update_clock(self):
        """Sistem saatini günceller ve periyodik işlemleri tetikler."""
        try:
            # Simülasyon Zamanı
            offset_min = 0
            if hasattr(self, 'settings_vars'):
                offset_min = self.settings_vars.get('var_test_time_offset', tk.IntVar(value=0)).get()
            
            now = datetime.now(timezone.utc) + timedelta(minutes=offset_min)
            z_time = now.strftime("%H:%M:%S Z")
            
            if hasattr(self, 'lbl_clock') and self.lbl_clock:
                # Simülasyon Uyarısı (Saat Rengi Turuncu Olur)
                if offset_min != 0:
                    self.lbl_clock.config(fg="#FF9800", text=z_time + " (SİM)")
                else:
                    self.lbl_clock.config(fg="#FFFFFF", text=z_time)
            
            # Ayarlar sekmesindeki saati güncelle
            if hasattr(self, 'lbl_settings_clock') and self.lbl_settings_clock:
                try: self.lbl_settings_clock.config(text=z_time)
                except: pass

            # --- TARİH GÜNCELLEME (Gece Yarısı Geçişi) ---
            if hasattr(self, 'settings_vars') and self.settings_vars['var_oto_yenile'].get():
                try:
                    now_utc_date = datetime.now(timezone.utc) + timedelta(minutes=offset_min)
                    
                    current_gui_day = int(self.cp_widgets['cb_gun'].get())
                    if current_gui_day != now_utc_date.day:
                        self.cp_widgets['cb_gun'].set(str(now_utc_date.day).zfill(2))
                        months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
                        self.cp_widgets['cb_ay'].set(months[now_utc_date.month - 1])
                        self.cp_widgets['cb_yil'].set(str(now_utc_date.year))
                        self.app_state["last_refresh"] = 0
                except: pass

            # Alarm Metni Yanıp Sönme Efekti
            if hasattr(self, 'lbl_alarm_info'):
                txt = self.lbl_alarm_info.cget("text")
                if txt and ("EKSİK" in txt or "UYUMSUZ" in txt or "HATA" in txt or "DİKKAT" in txt or "GEÇ" in txt):
                    cur_bg = self.lbl_alarm_info.cget("bg")
                    
                    # Ceza Durumu (Daha agresif yanıp sönme: Kırmızı/Beyaz)
                    if "GEÇ" in txt or "CEZA" in txt or "EKSİK" in txt:
                        new_bg = "red" if cur_bg == "white" else "white"
                        new_fg = "white" if new_bg == "red" else "red"
                    else:
                        new_bg = "red" if cur_bg == "#FFF9C4" else "#FFF9C4"
                        new_fg = "white" if new_bg == "red" else "red"
                    self.lbl_alarm_info.config(bg=new_bg, fg=new_fg)
                else:
                    if self.lbl_alarm_info.cget("bg") != "#FFF9C4":
                        self.lbl_alarm_info.config(bg="#FFF9C4")
                    if txt and "GELDİ" in txt and self.lbl_alarm_info.cget("fg") != "#2E7D32":
                        self.lbl_alarm_info.config(fg="#2E7D32")
            
            # Oto Yenileme Mantığı
            if hasattr(self, 'settings_vars') and self.settings_vars['var_oto_yenile'].get():
                s = self.settings_vars['var_oto_yenile_basla'].get()
                e = self.settings_vars['var_oto_yenile_bitis'].get()
                in_range = (s <= now.minute <= e) if s <= e else (now.minute >= s or now.minute <= e)
                
                if in_range:
                    interval = self.settings_vars['var_refresh_int_50_59'].get()
                    if time.time() - self.app_state.get("last_refresh", 0) >= interval:
                        if hasattr(self, 'cp_widgets') and self.cp_widgets['btn_goster_btn']['state'] != 'disabled':
                            self.verileri_cek(silent=True)
                            self.app_state["last_refresh"] = time.time()
                    if hasattr(self, 'lbl_timer'):
                        rem = int(interval - (time.time() - self.app_state.get('last_refresh', 0)))
                        self.lbl_timer.config(text=f"Oto: {max(0, rem)}sn")
                else:
                    if hasattr(self, 'lbl_timer'): self.lbl_timer.config(text="Oto: Beklemede")
            elif hasattr(self, 'lbl_timer'):
                self.lbl_timer.config(text="Oto: KAPALI")

            # Saat Başı Alarmı
            if hasattr(self, 'settings_vars') and self.settings_vars['var_saat_basi_aktif'].get() and now.minute == 0 and self.app_state.get("last_hourly_alarm") != now.hour:
                if self.settings_vars['var_anons_aktif'].get():
                    msg = f"Saat {now.hour}."
                    self.log_to_daily_file(f"SESLİ ANONS: {msg}", "ANONS")
                    self.alarm_motoru.google_seslendir(msg, hiz=self.settings_vars['var_konusma_hizi'].get(), pitch=self.settings_vars['var_konusma_perdesi'].get(), use_piper=self.settings_vars['var_piper_aktif'].get(), use_edge=self.settings_vars['var_edge_aktif'].get(), edge_voice=self.settings_vars['var_edge_voice'].get())
                self.app_state["last_hourly_alarm"] = now.hour
            
            # Gelecek Alarm Göstergesi (Her 2 saniyede bir güncelle)
            if now.second % 2 == 0: self.update_upcoming_display(now)

            # ALARM TETİKLEME KONTROLLERİ
            self._handle_alarms(now)

        except Exception as e:
            logging.error(f"Clock Error: {e}") # Hata olsa bile saati durdurma
        
        # Döngüyü sürdür (Hata olsa bile)
        try:
            if self.root.winfo_exists():
                self.root.after(1000, self.update_clock)
        except: pass

    def update_upcoming_display(self, now):
        """Gelecek alarmı hesaplar ve ekranda gösterir."""
        if not hasattr(self, 'lbl_upcoming') or not self.lbl_upcoming: return
        
        upcoming_list = []
        
        # 3 saatlik pencerede ara
        for i in range(1, 181):
            future = now + timedelta(minutes=i)
            f_h = future.hour
            f_m = future.minute
            
            # METAR
            if self.settings_vars['var_remind_metar_aktif'].get():
                s, m_start = self.parse_time_str(self.settings_vars['var_remind_metar_start_h'].get())
                p = self.settings_vars['var_remind_metar_period'].get()
                m = m_start # Dakika başlangıç saatinden alınır
                if p > 0 and (f_h - s) % p == 0 and f_m == m:
                    upcoming_list.append(f"{f_h:02d}{f_m:02d}Z METAR")

            # SİNOPTİK
            if self.settings_vars['var_remind_synop_aktif'].get():
                s, m_start = self.parse_time_str(self.settings_vars['var_remind_synop_start_h'].get())
                p = self.settings_vars['var_remind_synop_period'].get()
                m = m_start
                # Standart Sinoptik (3 saatlik) için başlangıç saati 0 olmalı
                if p == 3 and s != 0: s = 0
                
                # Sinoptik saati hesapla (Hatırlatma dakikasına göre)
                target_h = (f_h + 1) % 24 if m > 45 else f_h
                
                if p > 0 and (target_h - s) % p == 0 and f_m == m:
                    upcoming_list.append(f"{target_h:02d}00Z SİNOPTİK")

            # TAF
            if self.settings_vars['var_remind_taf_aktif'].get():
                s, m = self.parse_time_str(self.settings_vars['var_remind_taf_start_h'].get())
                s = s % 24 # Saat 24 modunda olsun
                p = self.settings_vars['var_remind_taf_period'].get()
                if p > 0 and (f_h - s) % p == 0 and f_m == m:
                    upcoming_list.append(f"{f_h:02d}{f_m:02d}Z TAF")
            
            if len(upcoming_list) >= 2: break
        
        if upcoming_list:
            # Tekrarları temizle
            seen = set()
            unique_list = []
            for item in upcoming_list:
                if item not in seen:
                    unique_list.append(item)
                    seen.add(item)
            
            msg = " VE ".join(unique_list[:2]) + " OLACAK"
            self.lbl_upcoming.config(text=f"SIRADAKİ {msg}")
        else:
            self.lbl_upcoming.config(text="")

    def _trigger_special_alarm(self, msg):
        if msg and self.settings_vars['var_anons_aktif'].get():
            self.log_to_daily_file(f"SESLİ ANONS (ÖZEL): {msg}", "ANONS")
            self.alarm_motoru.google_seslendir(msg, hiz=self.settings_vars['var_konusma_hizi'].get(), pitch=self.settings_vars['var_konusma_perdesi'].get(), use_piper=self.settings_vars['var_piper_aktif'].get(), use_edge=self.settings_vars['var_edge_aktif'].get(), edge_voice=self.settings_vars['var_edge_voice'].get())
        else:
            self.play_alarm_sound()
        self.flash_visual_alert()

    def _is_within_ontime(self, item_str, now):
        """Bir eksik veri öğesinin şu an ON-TIME aralığında olup olmadığını kontrol eder.
           DENETİM AYARLARI sekmesindeki dakika aralıklarını kullanır.
        """
        try:
            parts = item_str.split()
            if len(parts) < 2: return False

            obs_h = 0
            obs_m = 0

            # YENİ: Gözlem saati ile mevcut saat arasında büyük fark varsa,
            # her zaman "gecikmiş" (delayed) kabul et. Bu, eski bir alarmın
            # tekrar "on-time" durumuna dönmesini engeller.
            try:
                time_str = parts[0] # "2100"
                if time_str.isdigit() and len(time_str) == 4:
                    obs_h = int(time_str[:2])
                    obs_m = int(time_str[2:])
                    # Saat farkını hesapla (24 saatlik döngüyü dikkate alarak)
                    hour_diff = (now.hour - obs_h + 24) % 24
                    # Eğer fark 2 saatten fazlaysa (ve 22 saatten azsa - ters döngü için)
                    # bu kesinlikle eski bir kayıttır ve "on-time" olamaz.
                    if hour_diff > 2 and hour_diff < 22:
                        return False
            except:
                pass # time_str parse edilemezse eski mantıkla devam et

            obs_type = parts[1]
            
            start_min = 0
            end_min = 0
            
            def get_val(var_name, default):
                var_obj = self.settings_vars.get(var_name)
                if not var_obj:
                    return default
                try:
                    val = var_obj.get()
                    # Değer boş bir string ise veya sayıya çevrilemiyorsa varsayılana dön
                    return int(val) if str(val).strip() else default
                except (ValueError, tk.TclError):
                    return default
                
            if "METAR" in obs_type:
                start_min = get_val('var_denetim_metar_p1_start', 50)
                end_min = get_val('var_denetim_metar_p1_end', 54)
            elif "SİNOPTİK" in obs_type or "SYNOP" in obs_type:
                start_min = get_val('var_denetim_synop_start', 50)
                end_min = get_val('var_denetim_synop_end', 59)
            elif "TAF" in obs_type:
                start_min = get_val('var_denetim_taf_start', 30)
                end_min = get_val('var_denetim_taf_end', 59)
            else:
                return True

            # Kesin DateTime penceresi oluştur (Saat sarmasını hatasız çözer)
            target = now.replace(hour=obs_h, minute=obs_m, second=0, microsecond=0)
            # Eğer now ile target arasında gün farkı varsa düzelt (gece yarısı geçişleri)
            if now.hour < 6 and obs_h > 18:
                target -= timedelta(days=1)
            elif now.hour > 18 and obs_h < 6:
                target += timedelta(days=1)
                
            start_dt = target.replace(minute=start_min)
            # Eğer start_min, hedefin dakikasından çok büyükse (örn hedef 00:00, start 50), bir önceki saattir
            if obs_m < 15 and start_min > 45:
                start_dt -= timedelta(hours=1)
            elif obs_m > 45 and start_min < 15:
                start_dt += timedelta(hours=1)
                
            end_dt = target.replace(minute=end_min)
            if obs_m < 15 and end_min > 45:
                end_dt -= timedelta(hours=1)
            elif obs_m > 45 and end_min < 15:
                end_dt += timedelta(hours=1)
                
            # Eğer start_dt, end_dt'den büyükse (Örn: 50'den 05'e kadar pencere), end_dt 1 saat ileridedir
            if start_dt > end_dt:
                end_dt += timedelta(hours=1)
                
            return start_dt <= now <= end_dt
        except Exception as e:
            logging.error(f"'_is_within_ontime' içinde hata: {e}", exc_info=True)
            return True

    def _handle_alarms(self, now):
        """Alarm tetikleme mantığını yönetir."""
        trigger_incompatible = False
        trigger_missing = False
        trigger_rasat_time = False
        warning_triggered_this_cycle = False
        rasat_time_msg = ""
        msgs = []

        # --- YENİ: Eksik veri listesi değiştiğinde sayaçları sıfırla ---
        all_missing = self.app_state.get("missing_items", [])
        current_missing_set = set(all_missing)
        previous_missing_set = self.app_state.get("previous_missing_items", set())

        if current_missing_set != previous_missing_set:
            # Liste değişti, uyarı ve ceza döngülerini sıfırdan başlat
            self.app_state["warning_alarm_counter"] = 0
            self.app_state["penalty_alarm_counter"] = 0
            self.app_state["penalty_alarm_counter_METAR"] = 0
            self.app_state["penalty_alarm_counter_SİNOPTİK"] = 0
            self.app_state["penalty_alarm_counter_TAF"] = 0
            self.app_state["last_alarm"] = 0
            self.app_state["last_penalty_alarm_time"] = 0
            self.app_state["last_penalty_alarm_time_METAR"] = 0
            self.app_state["last_penalty_alarm_time_SİNOPTİK"] = 0
            self.app_state["last_penalty_alarm_time_TAF"] = 0
            logging.info(f"Eksik veri listesi değişti. Sayaçlar sıfırlandı. Yeni liste: {current_missing_set}")

        self.app_state["previous_missing_items"] = current_missing_set
        # --- BİTTİ ---

        # 1. UYUMSUZLUK
        incomp_items = self.app_state.get("incompatible_items", [])
        re_error_items = self.app_state.get("re_error_items", [])
        if (incomp_items or re_error_items) and self.settings_vars['var_trend_alarm_aktif'].get():
            var_repeat = self.settings_vars.get('var_incompatible_alarm_repeat')
            repeat_limit = int(var_repeat.get()) if var_repeat else 3
            if self.app_state.get("incompatible_alarm_counter", 0) < repeat_limit:
                if time.time() - self.app_state.get("last_alarm_incompatible", 0) > self.settings_vars['var_alarm_freq_incompatible'].get():
                    trigger_incompatible = True
        

        # --- RASAT HAZIRLIK (REMINDERS) KONTROLÜ ---
        if self.app_state.get("last_special_alarm_min") != now.minute:
            if self.settings_vars['var_remind_metar_aktif'].get():
                s, m_s = self.parse_time_str(self.settings_vars['var_remind_metar_start_h'].get())
                p = self.settings_vars['var_remind_metar_period'].get()
                if p > 0 and (now.hour - s) % p == 0 and now.minute == m_s:
                    msgs.append(f"{now.hour:02d}{now.minute:02d} METAR YAPIN")
            
            if self.settings_vars['var_remind_synop_aktif'].get():
                s, m_s = self.parse_time_str(self.settings_vars['var_remind_synop_start_h'].get())
                p = self.settings_vars['var_remind_synop_period'].get()
                if p == 3 and s != 0: s = 0
                target_h = (now.hour + 1) % 24 if m_s > 45 else now.hour
                if p > 0 and (target_h - s) % p == 0 and now.minute == m_s:
                    msgs.append(f"{target_h:02d}00 SİNOPTİK YAPIN")

            if self.settings_vars['var_remind_taf_aktif'].get():
                s, m_s = self.parse_time_str(self.settings_vars['var_remind_taf_start_h'].get())
                p = self.settings_vars['var_remind_taf_period'].get()
                if p > 0 and (now.hour - s) % p == 0 and now.minute == m_s:
                    msgs.append(f"{now.hour:02d}{now.minute:02d} TAF YAPIN")

            # Özel Alarmları Kontrol Et
            self._check_special_alarms(now)

            if msgs:
                trigger_rasat_time = True
                if any("YAPIN" in m for m in msgs):
                    rasat_time_msg = " VE ".join(msgs)
                else:
                    rasat_time_msg = " VE ".join(msgs) + " ZAMANI"
            
            self.app_state["last_special_alarm_min"] = now.minute

        # --- ALARMLARI TETİKLE ---

        if trigger_incompatible:
            if time.time() > self.app_state.get("silence_end_time", 0):
                self.app_state["last_alarm_incompatible"] = time.time()
                self.app_state["incompatible_alarm_counter"] = self.app_state.get("incompatible_alarm_counter", 0) + 1
                
                if incomp_items:
                    self.log_alarm_event(f"UYUMSUZLUK: {', '.join(incomp_items)}")
                    self.log_to_daily_file(f"UYUMSUZLUK ALARMI: {', '.join(incomp_items)}", "ALARM")
                
                if re_error_items:
                    self.log_alarm_event(f"RE/GEÇMİŞ HATASI: {', '.join(re_error_items)}")
                    self.log_to_daily_file(f"RE/GECMIS HATASI ALARMI: {', '.join(re_error_items)}", "ALARM")
                
                all_items = re_error_items + incomp_items
                if re_error_items and not incomp_items:
                    voice_msg = f"DİKKAT. {re_error_items[0]} EKSİK VEYA HATALI GEÇMİŞ HADİSE."
                    display_msg = f"DİKKAT {re_error_items[0]} RE HATASI"
                else:
                    voice_msg = f"DİKKAT. {all_items[0]} UYUMSUZ."
                    display_msg = f"DİKKAT {all_items[0]} UYUMSUZ"

                if self.settings_vars['var_anons_aktif'].get():
                    if hasattr(self, 'lbl_alarm_info'):
                        self.lbl_alarm_info.config(text=display_msg, fg="red")
                    self.log_to_daily_file(f"SESLİ ANONS: {voice_msg}", "ANONS")
                    self.alarm_motoru.google_seslendir(voice_msg, hiz=self.settings_vars['var_konusma_hizi'].get(), pitch=self.settings_vars['var_konusma_perdesi'].get(), use_piper=self.settings_vars['var_piper_aktif'].get(), use_edge=self.settings_vars['var_edge_aktif'].get(), edge_voice=self.settings_vars['var_edge_voice'].get())
                else:
                    if hasattr(self, 'lbl_alarm_info'):
                        self.lbl_alarm_info.config(text=display_msg, fg="red")
                    self.play_alarm_sound()
                self.flash_visual_alert()

        # --- EKSİK VERİ YÖNETİMİ (ON-TIME ve DELAYED) ---
        all_missing = self.app_state.get("missing_items", [])
        ontime_items = [item for item in all_missing if self._is_within_ontime(item, now)]
        delayed_items = [item for item in all_missing if not self._is_within_ontime(item, now)]

        def get_val(var_name, default):
            var_obj = self.settings_vars.get(var_name)
            if not var_obj:
                return default
            try:
                val = var_obj.get()
                return int(val) if str(val).strip() else default
            except (ValueError, tk.TclError, TypeError):
                return default

        # 1. ON-TIME ALARMLARI (Standart)
        if ontime_items:
            
            # Tekrar Sayısı Kontrolü
            first_item = ontime_items[0]
            repeat_limit = 4 # Varsayılan
            freq = 60
            
            if "METAR" in first_item: 
                repeat_limit = get_val('var_metar_alarm_repeat', 4)
                freq = get_val('var_alarm_freq_metar', 60)
            elif "SİNOPTİK" in first_item:
                repeat_limit = get_val('var_synop_alarm_repeat', 4)
                freq = get_val('var_alarm_freq_synop', 60)
            elif "TAF" in first_item:
                repeat_limit = get_val('var_taf_alarm_repeat', 4)
                freq = get_val('var_alarm_freq_taf', 300)

            warning_count = self.app_state.get("warning_alarm_counter", 0)
            
            if warning_count < repeat_limit:
                if time.time() - self.app_state.get("last_alarm", 0) > freq and time.time() > self.app_state.get("silence_end_time", 0):
                    self.app_state["last_alarm"] = time.time()
                    self.app_state["warning_alarm_counter"] = warning_count + 1
                    warning_triggered_this_cycle = True
                    
                    self.log_alarm_event(f"EKSİK VERİ ({warning_count+1}/{repeat_limit}): {', '.join(ontime_items)}")
                    self.log_to_daily_file(f"EKSİK VERİ ALARMI: {', '.join(ontime_items)}", "ALARM")
                    
                    items_str = " VE ".join(ontime_items)
                    if hasattr(self, 'lbl_alarm_info'):
                        self.lbl_alarm_info.config(text=f"DİKKAT {items_str} GELMEDİ ({warning_count+1})", fg="red")

                    if self.settings_vars['var_anons_aktif'].get():
                        tts_msg = f"DİKKAT {items_str} GELMEDİ."
                        
                        if self.app_state.get("connection_down", False):
                            tts_msg = f"BAĞLANTI HATASI NEDENİYLE, {tts_msg}"

                        self.log_to_daily_file(f"SESLİ ANONS: {tts_msg}", "ANONS")
                        self.alarm_motoru.google_seslendir(tts_msg, hiz=self.settings_vars['var_konusma_hizi'].get(), pitch=self.settings_vars['var_konusma_perdesi'].get(), use_piper=self.settings_vars['var_piper_aktif'].get(), use_edge=self.settings_vars['var_edge_aktif'].get(), edge_voice=self.settings_vars['var_edge_voice'].get())
                    else: self.play_alarm_sound()
                    self.flash_visual_alert()
        
        # 2. DELAYED (CEZA) ALARMLARI
        var_obj = self.settings_vars.get('var_denetim_gec_gelen_alarm_aktif')
        ceza_aktif = var_obj.get() if var_obj else True
        
        if delayed_items and ceza_aktif:
            first_item = delayed_items[0]
            if "METAR" in first_item:
                p_interval = get_val('var_ceza_aralik_metar', 3) * 60
                p_max = get_val('var_ceza_tekrar_metar', 3)
                p_type = "METAR"
            elif "SİNOPTİK" in first_item or "SYNOP" in first_item:
                p_interval = get_val('var_ceza_aralik_synop', 3) * 60
                p_max = get_val('var_ceza_tekrar_synop', 3)
                p_type = "SİNOPTİK"
            else:
                p_interval = get_val('var_ceza_aralik_taf', 3) * 60
                p_max = get_val('var_ceza_tekrar_taf', 3)
                p_type = "TAF"
                
            p_count_key = f"penalty_alarm_counter_{p_type}"
            p_last_key = f"last_penalty_alarm_time_{p_type}"
            
            p_count = self.app_state.get(p_count_key, 0)
            p_last = self.app_state.get(p_last_key, 0)
            
            # İlk geçişte (On-Time bittiğinde) veya aralık dolduğunda çal
            time_ok = (p_count == 0 and time.time() - self.app_state.get("last_alarm", 0) > 10) or (p_count > 0 and time.time() - p_last > p_interval)
            
            if p_count < p_max and time_ok and time.time() > self.app_state.get("silence_end_time", 0):
                self.app_state[p_last_key] = time.time()
                self.app_state[p_count_key] = p_count + 1
                
                items_str = ", ".join(delayed_items)
                
                def cal_ceza_alarmi():
                    self.log_to_daily_file(f"GEÇ GELEN CEZA ALARMI ({p_count+1}/{p_max}): {items_str}", "ALARM")
                    tts_msg = f"{items_str} RASATI EKSİK VEYA GEÇ GÖNDERİLMİŞ LÜTFEN KONTROL EDİN"
                    
                    if hasattr(self, 'lbl_alarm_info'):
                        self.lbl_alarm_info.config(text=f"{tts_msg} ({p_count+1}/{p_max})", fg="red")
                    
                    if self.settings_vars['var_anons_aktif'].get():
                        final_msg = tts_msg
                        if self.app_state.get("connection_down", False):
                            final_msg = f"BAĞLANTI HATASI NEDENİYLE, {tts_msg}"

                        self.log_to_daily_file(f"SESLİ ANONS: {final_msg}", "ANONS")
                        self.alarm_motoru.google_seslendir(final_msg, hiz=self.settings_vars['var_konusma_hizi'].get(), pitch=self.settings_vars['var_konusma_perdesi'].get(), use_piper=self.settings_vars['var_piper_aktif'].get(), use_edge=self.settings_vars['var_edge_aktif'].get(), edge_voice=self.settings_vars['var_edge_voice'].get())
                    else: self.play_alarm_sound()
                    self.flash_visual_alert()

                cal_ceza_alarmi()
        
        if not all_missing:
            self.app_state["penalty_alarm_counter"] = 0
            self.app_state["penalty_alarm_counter_METAR"] = 0
            self.app_state["penalty_alarm_counter_SİNOPTİK"] = 0
            self.app_state["penalty_alarm_counter_TAF"] = 0
            self.app_state["warning_alarm_counter"] = 0

        if trigger_rasat_time:
            self.app_state["last_rasat_zamani_alarm_hour"] = now.hour
            if msgs:
                msg = f"LÜTFEN {rasat_time_msg}"
            else:
                msg = f"{now.hour:02d}{now.minute:02d} {rasat_time_msg}"
            if self.settings_vars['var_anons_aktif'].get():
                self.log_to_daily_file(f"SESLİ ANONS: {msg}", "ANONS")
                self.alarm_motoru.google_seslendir(msg, hiz=self.settings_vars['var_konusma_hizi'].get(), pitch=self.settings_vars['var_konusma_perdesi'].get(), use_piper=self.settings_vars['var_piper_aktif'].get(), use_edge=self.settings_vars['var_edge_aktif'].get(), edge_voice=self.settings_vars['var_edge_voice'].get())
            else: self.play_alarm_sound()

    def check_alarms(self, grouped_data, g, a, y, silent):
        if grouped_data is None: return

        # Bağlantı hatası durumunda da eksik veri kontrolü yap (Kullanıcı talebi)
        # if self.app_state.get("connection_down", False): return

        try:
            sel_d = int(g)
            sel_y = int(y)
            tr_months = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"]

            var_obj = self.settings_vars.get('var_test_time_offset')
            offset_min = int(var_obj.get()) if var_obj else 0
            now_utc = datetime.now(timezone.utc) + timedelta(minutes=offset_min)
            
            if a.upper() in tr_months: sel_m = tr_months.index(a.upper()) + 1
            else: sel_m = now_utc.month
            
            sel_date = datetime(sel_y, sel_m, sel_d).date()
            
            if abs((now_utc.date() - sel_date).days) > 1: return
        except: return

        missing_items = []
        
        # --- 1. EKSİK VERİ TESPİTİ ---
        
        # A. METAR Kontrolü
        if self.settings_vars['var_metar_alarm_aktif'].get():
            start_h, _ = self.parse_time_str(self.settings_vars['var_metar_alarm_start_hour'].get())
            trigger_min = self.settings_vars['var_metar_alarm_trigger_min'].get()
            period = self.settings_vars['var_metar_alarm_period'].get()
            
            shifted_time = now_utc - timedelta(minutes=trigger_min)
            shifted_h = shifted_time.hour
            normalized_h = (shifted_h - start_h) % 24
            cycle_idx = normalized_h // period
            check_h = (start_h + cycle_idx * period) % 24
            
            expected_dt = shifted_time - timedelta(hours=(shifted_h - check_h) % 24)
            expected_date = expected_dt.date()
            
            def get_val(var_name, default):
                var_obj = self.settings_vars.get(var_name)
                return int(var_obj.get()) if var_obj else default
                
            if check_h != -1:
                metar_min = get_val('var_denetim_metar_p1_start', 50)
                # Arama Penceresi: Başlangıç + Tolerans (Geciken veriyi de 'GELDİ' saymak için)
                search_window = get_val('var_tolerans_dk', 45)

                if expected_date == sel_date or expected_date == sel_date - timedelta(days=1):
                    found = False
                    for group in grouped_data:
                        for obs in group['observations']:
                            if obs['type'] in ['METAR', 'SPECI']:
                                # 1. ÖNCELİK: RASAT TARİHİ (DT) KONTROLÜ (Varlık Kontrolü)
                                if obs.get('dt') and obs['dt'].year > 1900:
                                    try:
                                        obs_utc = obs['dt']
                                        if obs_utc.date() == expected_date and obs_utc.hour == check_h and obs_utc.minute >= metar_min:
                                            found = True; break
                                    except: pass
                                
                                # 2. ÖNCELİK: KAYIT TARİHİ (REG_DT) KONTROLÜ (Yedek)
                                if obs.get('reg_dt') and obs['reg_dt'].year > 1900:
                                    try:
                                        reg_utc = obs['reg_dt']
                     
                                        # Ana Saat Kontrolü (Dakika aralığı)
                                        if reg_utc.date() == expected_date and reg_utc.hour == check_h:
                                            if metar_min <= reg_utc.minute <= (metar_min + search_window):
                                                found = True; break
                                        
                                        # Gecikme Toleransı (Süre bir sonraki saate sarkıyorsa)
                                        if (metar_min + search_window) >= 60:
                                            next_h = (check_h + 1) % 24
                                            next_date = expected_date
                                            if next_h == 0: next_date += timedelta(days=1)
                                            if reg_utc.date() == next_date and reg_utc.hour == next_h:
                                                if reg_utc.minute <= (metar_min + search_window) % 60:
                                                    found = True; break
                                    except: pass
                                
                                # 3. ÖNCELİK: ARAYÜZ GÖRÜNÜMÜ (STRING) KONTROLÜ
                                if obs.get('tarih_str'):
                                    # Boşluk zorunluluğu kaldırıldı (15:50Z gibi bitişik yazımlar için)
                                    if f"{check_h:02d}:50" in obs['tarih_str']:
                                        found = True; break
                        if found: break
                    
                    if not found:
                        should_alarm = True
                        if check_h == 23 and now_utc.hour == 0 and now_utc.minute < 20: should_alarm = False
                        
                        if should_alarm:
                            if self.check_log_for_arrival(check_h, 50, "METAR", expected_date): should_alarm = False
                        
                        if should_alarm: missing_items.append(f"{check_h:02d}50 METAR")

        # B. SİNOPTİK Kontrolü
        if self.settings_vars['var_sinoptik_alarm_aktif'].get():
            check_h = -1
            start_h, _ = self.parse_time_str(self.settings_vars['var_synop_alarm_start_hour'].get())
            trigger_min = self.settings_vars['var_synop_alarm_trigger_min'].get()
            period = self.settings_vars['var_synop_alarm_period'].get()
            # Standart Sinoptik (3 saatlik) için başlangıç saati 0 olmalı
            if period == 3 and start_h != 0: start_h = 0
            
            if trigger_min >= 45:
                shifted_time = now_utc + timedelta(minutes=(60 - trigger_min))
            else:
                shifted_time = now_utc - timedelta(minutes=trigger_min)
                
            shifted_h = shifted_time.hour
            normalized_h = (shifted_h - start_h) % 24
            cycle_idx = normalized_h // period
            check_h = (start_h + cycle_idx * period) % 24
            
            expected_dt = shifted_time - timedelta(hours=(shifted_h - check_h) % 24)
            expected_date = expected_dt.date()
            
            if check_h != -1:
                synop_min = get_val('var_denetim_synop_start', 50)
                search_window = get_val('var_tolerans_dk', 45)

                if expected_date == sel_date or expected_date == sel_date - timedelta(days=1):
                    found = False
                    for group in grouped_data:
                        for obs in group['observations']:
                            typ = obs['type'].upper()
                            if ("SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ) and "KLİMA" not in typ:
                                # 1. ÖNCELİK: RASAT TARİHİ (DT) KONTROLÜ
                                if obs.get('dt') and obs['dt'].year > 1900:
                                    obs_utc = obs['dt']
                                    if obs_utc.date() == expected_date and obs_utc.hour == check_h:
                                        found = True; break
                                    if check_h == 0 and obs_utc.date() == expected_date - timedelta(days=1) and obs_utc.hour >= 23:
                                        found = True; break
                                
                                # 2. ÖNCELİK: KAYIT TARİHİ (REG_DT) KONTROLÜ
                                if obs.get('reg_dt') and obs['reg_dt'].year > 1900:
                                    reg_utc = obs['reg_dt']
                                    
                                    # Ana Saat Kontrolü (Dakika aralığı)
                                    if reg_utc.date() == expected_date and reg_utc.hour == check_h:
                                        if synop_min <= reg_utc.minute <= (synop_min + search_window):
                                            found = True; break
                                    
                                    # Gecikme Toleransı (Süre bir sonraki saate sarkıyorsa)
                                    if (synop_min + search_window) >= 60:
                                        next_h = (check_h + 1) % 24
                                        next_date = expected_date
                                        if next_h == 0: next_date += timedelta(days=1)
                                        if reg_utc.date() == next_date and reg_utc.hour == next_h:
                                            if reg_utc.minute <= (synop_min + search_window) % 60:
                                                found = True; break

                                    # Erken Geliş Toleransı (-1 Saat) - Örn: 15:00 verisi 14:51'de gelirse
                                    prev_h = (check_h - 1) % 24
                                    prev_date = expected_date
                                    if check_h == 0: prev_date -= timedelta(days=1)
                                    if reg_utc.date() == prev_date and reg_utc.hour == prev_h and reg_utc.minute >= 40:
                                        found = True; break

                                    # 00Z Sinoptik Toleransı (Önceki gün 23:00+)
                                    if check_h == 0 and reg_utc.date() == expected_date - timedelta(days=1) and reg_utc.hour >= 23:
                                        found = True; break
                                
                                # 3. ÖNCELİK: ARAYÜZ GÖRÜNÜMÜ (STRING) KONTROLÜ (Kullanıcı Talebi)
                                # "1500 Sinoptik" alarmı için listede "15:00" saatli veri varsa kabul et.
                                if obs.get('tarih_str'):
                                    # Boşluk zorunluluğu kaldırıldı (15:00Z gibi bitişik yazımlar için)
                                    if f"{check_h:02d}:00" in obs['tarih_str'] or f"{check_h:02d}00" in obs['tarih_str']:
                                        found = True; break
                                    
                                    # 15:00Z Özel Kontrolü (Kullanıcı İsteği - Eksik Hatası İçin)
                                    if check_h == 15 and ("15:00" in obs['tarih_str'] or "1500Z" in obs['tarih_str'] or "1500" in obs['tarih_str']):
                                        found = True; break
                                        
                                    # 00:00 Sinoptik için 23:50 toleransı (Arayüzde dünkü kayıt varsa)
                                    if check_h == 0 and "23:" in obs['tarih_str']:
                                        found = True; break
                                
                                # 4. ÖNCELİK: BÜLTEN İÇERİĞİ KONTROLÜ (AAXX DDHH)
                                # Örn: 15:00 için AAXX ..15.
                                if obs.get('bulten'):
                                    # AAXX ddHH (dd: Gün, HH: Saat)
                                    try:
                                        if f"AAXX {expected_date.day:02d}{check_h:02d}" in obs['bulten']:
                                            found = True; break
                                    except: pass
                        if found: break
                    
                    if not found and self.check_log_for_arrival(check_h, 0, "SİNOPTİK", expected_date): found = True
                    if not found: missing_items.append(f"{check_h:02d}00 SİNOPTİK")

        # C. TAF Kontrolü
        if self.settings_vars['var_taf_alarm_aktif'].get():
            start_h, _ = self.parse_time_str(self.settings_vars['var_taf_alarm_start_hour'].get())
            trigger_min = self.settings_vars['var_taf_alarm_trigger_min'].get()
            period = self.settings_vars['var_taf_alarm_period'].get()
            
            shifted_time = now_utc - timedelta(minutes=trigger_min)
            shifted_h = shifted_time.hour
            normalized_h = (shifted_h - start_h) % 24
            cycle_idx = normalized_h // period
            check_h = (start_h + cycle_idx * period) % 24
            
            expected_dt = shifted_time - timedelta(hours=(shifted_h - check_h) % 24)
            expected_date = expected_dt.date()
            
            if check_h != -1:
                taf_min = get_val('var_denetim_taf_start', 30)
                search_window = get_val('var_tolerans_dk', 45)

                if expected_date == sel_date or expected_date == sel_date - timedelta(days=1):
                    found = False
                    for group in grouped_data:
                        # 1. ÖNCELİK: RASAT TARİHİ (DT) KONTROLÜ
                        t = group.get('taf')
                        if t and t.get('dt') and t['dt'].year > 1900:
                            obs_utc = t['dt']
                            if obs_utc.date() == expected_date and obs_utc.hour == check_h:
                                found = True; break
                        
                        # 2. ÖNCELİK: KAYIT TARİHİ (REG_DT) KONTROLÜ
                        t = group.get('taf')
                        if t and t.get('reg_dt') and t['reg_dt'].year > 1900:
                            reg_utc = t['reg_dt']
                            
                            # Ana Saat Kontrolü
                            if reg_utc.date() == expected_date and reg_utc.hour == check_h:
                                if taf_min <= reg_utc.minute <= (taf_min + search_window):
                                    found = True; break
                            
                            # TAF Gecikme Toleransı (Süre bir sonraki saate sarkıyorsa)
                            if (taf_min + search_window) >= 60:
                                next_h = (check_h + 1) % 24
                                next_date = expected_date
                                if next_h == 0: next_date += timedelta(days=1)
                                if reg_utc.date() == next_date and reg_utc.hour == next_h:
                                    if reg_utc.minute <= (taf_min + search_window) % 60:
                                        found = True; break
                            
                            # TAF Erken Geliş Toleransı (-1 Saat)
                            prev_h = (check_h - 1) % 24
                            prev_date = expected_date
                            if check_h == 0: prev_date -= timedelta(days=1)
                            if reg_utc.date() == prev_date and reg_utc.hour == prev_h and reg_utc.minute >= 25:
                                found = True; break
                        
                        # 3. ÖNCELİK: ARAYÜZ GÖRÜNÜMÜ (STRING) KONTROLÜ
                        t = group.get('taf')
                        if t and t.get('tarih_str'):
                            # Boşluk zorunluluğu kaldırıldı
                            if f"{check_h:02d}:40" in t['tarih_str']:
                                found = True; break
                        
                        for obs in group['observations']:
                            # 1. ÖNCELİK: RASAT TARİHİ (DT)
                            if "TAF" in obs['type'] and obs.get('dt'):
                                obs_utc = obs['dt']
                                if obs_utc.date() == expected_date and obs_utc.hour == check_h:
                                    found = True; break
                            
                            # 2. ÖNCELİK: KAYIT TARİHİ (REG_DT)
                            if "TAF" in obs['type'] and obs.get('reg_dt'):
                                reg_utc = obs['reg_dt']
                                
                                # Ana Saat Kontrolü
                                if reg_utc.date() == expected_date and reg_utc.hour == check_h:
                                    if taf_min <= reg_utc.minute <= (taf_min + search_window):
                                        found = True; break
                                
                                # TAF Gecikme Toleransı (Süre bir sonraki saate sarkıyorsa)
                                if (taf_min + search_window) >= 60:
                                    next_h = (check_h + 1) % 24
                                    next_date = expected_date
                                    if next_h == 0: next_date += timedelta(days=1)
                                    if reg_utc.date() == next_date and reg_utc.hour == next_h:
                                        if reg_utc.minute <= (taf_min + search_window) % 60:
                                            found = True; break
                                
                                # TAF Erken Geliş Toleransı (-1 Saat)
                                prev_h = (check_h - 1) % 24
                                prev_date = expected_date
                                if check_h == 0: prev_date -= timedelta(days=1)
                                if reg_utc.date() == prev_date and reg_utc.hour == prev_h and reg_utc.minute >= 25:
                                    found = True; break
                            
                            # 3. ÖNCELİK: ARAYÜZ GÖRÜNÜMÜ (STRING) KONTROLÜ
                            if "TAF" in obs['type'] and obs.get('tarih_str'):
                                # Boşluk zorunluluğu kaldırıldı
                                if f"{check_h:02d}:40" in obs['tarih_str']:
                                    found = True; break
                        if found: break
                    
                    if not found and self.check_log_for_arrival(check_h, 40, "TAF", expected_date): found = True
                    
                    # YENİ KURAL: Yeni güne geçildiğinde dünün verisini eksik listesinde arama
                    if expected_date < sel_date: found = True
                    if not found: missing_items.append(f"{check_h:02d}40 TAF")

        # D. KLİMA Kontrolü (GÜNLÜK KLİMA)
        if self.settings_vars['var_klima_alarm_aktif'].get():
            start_h, _ = self.parse_time_str(self.settings_vars['var_klima_alarm_start_hour'].get())
            trigger_min = self.settings_vars['var_klima_alarm_trigger_min'].get()
            period = self.settings_vars['var_klima_alarm_period'].get()
            
            if trigger_min >= 45:
                shifted_time = now_utc + timedelta(minutes=(60 - trigger_min))
            else:
                shifted_time = now_utc - timedelta(minutes=trigger_min)
                
            shifted_h = shifted_time.hour
            normalized_h = (shifted_h - start_h) % 24
            cycle_idx = normalized_h // period
            check_h = (start_h + cycle_idx * period) % 24
            
            expected_dt = shifted_time - timedelta(hours=(shifted_h - check_h) % 24)
            expected_date = expected_dt.date()
            
            if check_h != -1:
                
                found = False
                for group in grouped_data:
                    for obs in group['observations']:
                        typ = obs['type'].upper()
                        if "KLİMA" in typ or "KLIMA" in typ:
                            if obs.get('dt') and obs['dt'].year > 1900:
                                obs_utc = obs['dt']
                                if obs_utc.date() == expected_date and obs_utc.hour == check_h: found = True; break
                            elif f"{check_h:02d}:00" in obs.get('tarih_str', ''): found = True; break
                    if found: break
                
                if not found and self.check_log_for_arrival(check_h, 0, "KLİMA", expected_date): found = True
                if not found: missing_items.append(f"{check_h:02d}00 GÜNLÜK KLİMA")

        # E. MAX RÜZGAR Kontrolü
        if self.settings_vars['var_max_ruzgar_alarm_aktif'].get():
            start_h, _ = self.parse_time_str(self.settings_vars['var_max_ruzgar_alarm_start_hour'].get())
            trigger_min = self.settings_vars['var_max_ruzgar_alarm_trigger_min'].get()
            period = self.settings_vars['var_max_ruzgar_alarm_period'].get()
            
            if trigger_min >= 45:
                shifted_time = now_utc + timedelta(minutes=(60 - trigger_min))
            else:
                shifted_time = now_utc - timedelta(minutes=trigger_min)
                
            shifted_h = shifted_time.hour
            normalized_h = (shifted_h - start_h) % 24
            cycle_idx = normalized_h // period
            check_h = (start_h + cycle_idx * period) % 24
            
            expected_dt = shifted_time - timedelta(hours=(shifted_h - check_h) % 24)
            expected_date = expected_dt.date()
            
            if check_h != -1:
                
                found = False
                for group in grouped_data:
                    for obs in group['observations']:
                        typ = obs['type'].upper()
                        if "MAX" in typ or "MAKSİMUM" in typ or "MAKSIMUM" in typ:
                            if obs.get('dt') and obs['dt'].year > 1900:
                                obs_utc = obs['dt']
                                if obs_utc.date() == expected_date and obs_utc.hour == check_h: found = True; break
                            elif f"{check_h:02d}:00" in obs.get('tarih_str', ''): found = True; break
                    if found: break
                
                if not found and self.check_log_for_arrival(check_h, 0, "MAX", expected_date): found = True
                if expected_date < sel_date: found = True
                if not found: missing_items.append(f"{check_h:02d}00 MAX RÜZGAR")

        # --- 2. YENİ GELENLERİ BİLDİR ---
        current_keys = set()
        new_arrivals = []
        
        now_for_age = now_utc.replace(tzinfo=None)
        
        for group in grouped_data:
            if group['taf']:
                k = (group['taf']['type'], group['taf'].get('dt'), group['taf'].get('bulten'))
                current_keys.add(k)
                if k not in self.app_state.get("seen_obs_keys", set()):
                    is_old = False
                    if group['taf'].get('dt') and group['taf']['dt'].year > 1900:
                        age_mins = (now_for_age - group['taf']['dt']).total_seconds() / 60
                        if age_mins > 60: is_old = True # Eski verileri yeni gelmiş gibi anons etme
                    if not is_old: new_arrivals.append(group['taf'])
                    
            for obs in group['observations']:
                k = (obs['type'], obs.get('dt'), obs.get('bulten'))
                current_keys.add(k)
                if k not in self.app_state.get("seen_obs_keys", set()):
                    is_old = False
                    if obs.get('dt') and obs['dt'].year > 1900:
                        age_mins = (now_for_age - obs['dt']).total_seconds() / 60
                        if age_mins > 75: is_old = True
                    if not is_old: new_arrivals.append(obs)
        
        if not self.app_state.get("initial_load_complete"):
            self.app_state["seen_obs_keys"] = current_keys
            self.app_state["initial_load_complete"] = True
            new_arrivals = []
        else:
            self.app_state["seen_obs_keys"].update(current_keys)

        if new_arrivals:
            for item in new_arrivals:
                t_str = item['dt'].strftime('%H:%M') if item.get('dt') and item['dt'].year > 1900 else "---"
                self.log_to_daily_file(f"GELDİ: {t_str} {item['type']} {item.get('bulten', '')}", "INFO")

            disp_txt = ", ".join([f"{x['dt'].strftime('%H:%M') if x.get('dt') and x['dt'].year > 1900 else '---'} {x['type']}" for x in new_arrivals[:3]])
            if hasattr(self, 'lbl_alarm_info'): self.lbl_alarm_info.config(text=f"GELDİ: {disp_txt}", fg="#2E7D32")
            
            # Popup Bildirim
            if hasattr(self, 'root'):
                try:
                    last_item = new_arrivals[-1]
                    t_str_pop = last_item['dt'].strftime('%H:%M') if last_item.get('dt') and last_item['dt'].year > 1900 else "---"
                    popup_msg = f"{t_str_pop} {last_item['type']}"
                    if len(new_arrivals) > 1:
                        popup_msg += f" (+{len(new_arrivals)-1})"
                    if hasattr(gui_utils, 'show_bottom_right_popup'):
                        gui_utils.show_bottom_right_popup(self.root, "SİSTEME DÜŞTÜ", popup_msg)
                except: pass # Popup hatası olsa bile sesli anons çalışmaya devam etsin

            # Sesli Anons Hazırlığı
            relevant_item = None
            tebrik_name = None
            
            # 1. Tebrik Kontrolü (Kullanıcı ID Eşleşmesi)
            var_obj = self.settings_vars.get('var_tebrik_aktif')
            tebrik_aktif = var_obj.get() if var_obj else False
            if tebrik_aktif:
                for item in new_arrivals:
                    if 'raw' in item and len(item['raw']) > 1:
                        kull_id = str(item['raw'][1]).strip().upper()
                        for i in range(20):
                            saved_id = self.settings_vars.get(f'var_kull_id_{i}', tk.StringVar()).get().strip().upper()
                            if saved_id and saved_id == kull_id:
                                name = self.settings_vars.get(f'var_kull_name_{i}', tk.StringVar()).get()
                                if name:
                                    tebrik_name = name
                                    relevant_item = item
                                    break
                    if tebrik_name: break
            
            # 2. Eşleşme yoksa son gelen veriyi baz al
            if not relevant_item and new_arrivals:
                relevant_item = new_arrivals[-1]
            
            voice_msg = "YENİ RASAT GELDİ."
            
            if relevant_item:
                if relevant_item.get('dt') and relevant_item['dt'].year > 1900:
                    time_str = relevant_item['dt'].strftime('%H %M')
                else:
                    # Fallback: Bültenden saat bul
                    match = re.search(r'\b(\d{2})(\d{2})(\d{2})Z\b', relevant_item.get('bulten', ''))
                    if match:
                        time_str = f"{match.group(2)} {match.group(3)}"
                    else:
                        time_str = ""

                type_str = relevant_item['type']
                
                voice_msg = f"{time_str} {type_str} sisteme düştü."
                
                if tebrik_name:
                    voice_msg += f" Tebrikler {tebrik_name}."

            if self.settings_vars['var_anons_aktif'].get():
                self.log_to_daily_file(f"SESLİ ANONS: {voice_msg}", "ANONS")
                self.alarm_motoru.google_seslendir(voice_msg, hiz=self.settings_vars['var_konusma_hizi'].get(), pitch=self.settings_vars['var_konusma_perdesi'].get(), use_piper=self.settings_vars['var_piper_aktif'].get(), use_edge=self.settings_vars['var_edge_aktif'].get(), edge_voice=self.settings_vars['var_edge_voice'].get())
            else: self.play_alarm_sound()
            
            if hasattr(self, 'root'): self.root.after(5000, lambda: self.lbl_alarm_info.config(text="") if hasattr(self, 'lbl_alarm_info') else None)

        self.app_state["missing_items"] = missing_items
        self.app_state["missing_data"] = bool(missing_items)
        
        if missing_items and hasattr(self, 'lbl_alarm_info'):
            self.lbl_alarm_info.config(text="EKSİK: " + ", ".join(missing_items), fg="red")
        elif hasattr(self, 'lbl_alarm_info'):
            # Eğer eksik yoksa ve ekranda EKSİK yazıyorsa temizle
            if "EKSİK" in self.lbl_alarm_info.cget("text"):
                self.lbl_alarm_info.config(text="", bg="#FFF9C4")

        # --- 3. UYUMSUZLUK ALARMI ---
        if self.settings_vars['var_trend_alarm_aktif'].get():
            incompatible_items = []
            re_error_items = []
            current_incompatible_keys = set()
            for group in grouped_data:
                for obs in group['observations']:
                    if (now_utc.replace(tzinfo=None) - obs['dt']).total_seconds() < 3600:
                        anl = obs.get('analysis')
                        if anl and ("UYUMSUZ" in anl['durum'] or "RE/GECMIS" in anl['durum'] or "RE/GEÇMİŞ" in anl['durum']):
                            item_str = f"{obs['dt'].strftime('%H:%M')} {obs['type']}"
                            is_re = ("RE/GECMIS" in anl['durum'] or "RE/GEÇMİŞ" in anl['durum'] or any("GEÇMİŞ HADİSE" in r or "GECMIS" in r.upper() for r in anl.get('reasons', [])))
                            if is_re:
                                re_error_items.append(item_str)
                            else:
                                incompatible_items.append(item_str)
                            current_incompatible_keys.add((obs['tarih_str'], obs['type']))
            
            prev_keys = self.app_state.get("prev_incompatible_keys", set())
            if current_incompatible_keys - prev_keys:
                self.app_state["last_alarm_incompatible"] = 0 # Yeni uyumsuzluk varsa hemen çal
                self.app_state["incompatible_alarm_counter"] = 0
            self.app_state["prev_incompatible_keys"] = current_incompatible_keys
            self.app_state["incompatible_items"] = incompatible_items
            self.app_state["re_error_items"] = re_error_items
            
            if not current_incompatible_keys:
                self.app_state["incompatible_alarm_counter"] = 0

    def check_log_for_arrival(self, check_h, check_m, obs_type, expected_date):
        try:
            from datetime import time as dt_time
            expected_obs_dt = datetime.combine(expected_date, dt_time(check_h, check_m))
            
            # Log dosyalarını kontrol et (Önceki gün, Bugün, Sonraki gün)
            # Özellikle 00Z verileri önceki günün log dosyasına düşmüş olabilir.
            log_dates = [expected_date - timedelta(days=1), expected_date, expected_date + timedelta(days=1)]
            base_log_dir = os.path.join(os.path.expanduser("~"), "KardelenLogs")
            
            # Alternatif tip isimleri (SİNOPTİK/SYNOP)
            search_types = [obs_type]
            if "SİNOPTİK" in obs_type or "SYNOP" in obs_type:
                search_types = ["SİNOPTİK", "SYNOP", "SINOPTIK"]
            elif "KLİMA" in obs_type: search_types = ["KLİMA", "KLIMA"]
            elif "MAX" in obs_type: search_types = ["MAX", "MAKSİMUM", "MAKSIMUM"]

            for d in log_dates:
                folder_name = d.strftime('%Y-%m-%d')
                log_file = os.path.join(base_log_dir, folder_name, "kardelen_gunluk_log.txt")
                
                if os.path.exists(log_file):
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if "GELDİ" not in line and "MEVCUT" not in line and "YENİ RASAT" not in line:
                                continue

                            # YENİ: Log satırının saatini al ve dünün aynı saatindeki verisiyle karışmasını önle
                            log_dt = None
                            try:
                                log_ts_str = line.split(']')[0].strip('[')
                                log_dt = datetime.strptime(log_ts_str, '%d.%m.%Y %H:%M:%S')
                            except: pass
                                
                            if log_dt:
                                # Log zamanı ile beklenen rasat zamanı arasında 3 saatten fazla fark varsa 
                                # bu dünün veya yarının aynı saatteki farklı bir kaydıdır, atla.
                                if abs((log_dt - expected_obs_dt).total_seconds()) > 3 * 3600:
                                    continue

                            for t in search_types:
                                # Regex ile esnek zaman kontrolü (Dakika farklarını tolere et)
                                pattern = rf"(\d{{2}}):(\d{{2}})\s+{t}"
                                match = re.search(pattern, line)
                                if match:
                                    h = int(match.group(1))
                                    m = int(match.group(2))
                                    
                                    if h == check_h:
                                        if "METAR" in obs_type and (45 <= m <= 59 or abs(m - check_m) <= 9): return True
                                        elif "TAF" in obs_type and (30 <= m <= 50 or abs(m - check_m) <= 15): return True
                                        elif ("SİNOPTİK" in obs_type or "SYNOP" in obs_type) and (m <= 15 or abs(m - check_m) <= 15): return True
                                    elif check_h == 0 and h == 23:
                                        if ("SİNOPTİK" in obs_type or "SYNOP" in obs_type) and m >= 45: return True
                                        elif "TAF" in obs_type and m >= 30: return True

                                search_str = f"{check_h:02d}:{check_m:02d} {t}"
                                if search_str in line: return True
                                
            # YENİ EKLENTİ: Günlük loglarda bulunamadıysa son çare (sibop) olarak Aylık Kayıtlar (.txt) dosyasına bak
            tr_months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
            year_str = str(expected_date.year)
            month_name = tr_months[expected_date.month - 1]
            monthly_file = os.path.join(base_log_dir, "Aylik_Kayitlar", year_str, f"{month_name}.txt")
            
            if os.path.exists(monthly_file):
                target_date_str = expected_date.strftime('%d.%m.%Y')
                with open(monthly_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "RASAT:" in line and target_date_str in line:
                            for t in search_types:
                                if t in line:
                                    match = re.search(rf"RASAT:\s*{target_date_str}\s*(\d{{2}}):(\d{{2}})Z?", line)
                                    if match:
                                        h = int(match.group(1))
                                        m = int(match.group(2))
                                        if h == check_h:
                                            if "METAR" in obs_type and (45 <= m <= 59 or abs(m - check_m) <= 9): return True
                                            elif "TAF" in obs_type and (30 <= m <= 50 or abs(m - check_m) <= 15): return True
                                            elif ("SİNOPTİK" in obs_type or "SYNOP" in obs_type) and (m <= 15 or abs(m - check_m) <= 15): return True
                                        elif check_h == 0 and h == 23:
                                            if ("SİNOPTİK" in obs_type or "SYNOP" in obs_type) and m >= 45: return True
                                            elif "TAF" in obs_type and m >= 30: return True
        except: pass
        return False

    def log_alarm_event(self, message):
        try:
            log_dir = os.path.join(os.path.expanduser("~"), "KardelenLogs")
            if not os.path.exists(log_dir): os.makedirs(log_dir)
            
            offset_min = 0
            if hasattr(self, 'settings_vars'):
                var_obj = self.settings_vars.get('var_test_time_offset')
                if var_obj: offset_min = int(var_obj.get())
            now_utc = datetime.now(timezone.utc) + timedelta(minutes=offset_min)
            
            with open(os.path.join(log_dir, "Alarm_Kayitlari.txt"), "a", encoding="utf-8") as f:
                f.write(f"[{now_utc.strftime('%d.%m.%Y %H:%M:%S')}] {message}\n")
        except: pass

    def log_to_daily_file(self, message, type="INFO"):
        try:
            base_log_dir = os.path.join(os.path.expanduser("~"), "KardelenLogs")
            
            offset_min = 0
            if hasattr(self, 'settings_vars'):
                var_obj = self.settings_vars.get('var_test_time_offset')
                if var_obj: offset_min = int(var_obj.get())
                
            now_utc = datetime.now(timezone.utc) + timedelta(minutes=offset_min)
            
            # YENİ MANTIK: 00:00 ile 00:45 arasında gelen kayıtlar (23:50 METAR vb.) dünün klasörüne yazılır
            logical_date = now_utc - timedelta(minutes=45)
            today_folder = logical_date.strftime('%Y-%m-%d')
            
            log_dir = os.path.join(base_log_dir, today_folder)
            if not os.path.exists(log_dir): os.makedirs(log_dir)
            
            log_file = os.path.join(log_dir, "kardelen_gunluk_log.txt")
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{now_utc.strftime('%d.%m.%Y %H:%M:%S')}] [{type}] {message}\n")
        except: pass

    def trigger_connection_alarm(self, error_msg):
        if self.app_state.get("connection_alarm_active", False): return
        self.app_state["connection_alarm_active"] = True
        
        def _loop(count):
            if count <= 0:
                self.app_state["connection_alarm_active"] = False
                return
            if self.settings_vars['var_anons_aktif'].get():
                msg = "DİKKAT. SUNUCU YANIT VERMİYOR."
                self.log_to_daily_file(f"SESLİ ANONS: {msg}", "ANONS")
                self.alarm_motoru.google_seslendir(msg, hiz=150, use_edge=True)
            else: self.play_alarm_sound()
            self.flash_visual_alert()
            if hasattr(self, 'root'): self.root.after(60000, lambda: _loop(count - 1))
            
        _loop(2)
