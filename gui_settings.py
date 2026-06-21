import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font, colorchooser
import config_manager
from datetime import datetime, timezone, timedelta

class ToolTip(object):
    def __init__(self, widget, text_provider):
        self.widget = widget
        self.text_provider = text_provider
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                       background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                       font=("Segoe UI", "9", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

    def enter(self, event=None):
        text = self.text_provider()
        self.schedule(text)

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self, text):
        self.unschedule()
        self.id = self.widget.after(500, lambda: self.showtip(text))

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

def create_tooltip(widget, text_provider):
    toolTip = ToolTip(widget, text_provider)
    widget.bind('<Enter>', toolTip.enter)
    widget.bind('<Leave>', toolTip.leave)

def load_settings(vars_dict):
    """Config dosyasından ayarları yükler ve değişkenlere atar."""
    config = config_manager.load_config()
    if not config: return

    # Hatalı/Uyumsuz veri tiplerinin tüm ayar yüklemesini durdurmasını engelleyen güvenli sözlük
    class SafeDict(dict):
        def __getitem__(self, key):
            real_var = super().get(key)
            class SafeVar:
                def set(self, val):
                    if real_var is not None:
                        try: real_var.set(val)
                        except Exception as e: print(f"Ayar yükleme uyumsuzluğu atlandı ({key} <- {val}): {e}")
            return SafeVar()
            
    vars_dict = SafeDict(vars_dict)

    try:
        if 'oto_yenile_basla' in config: vars_dict['var_oto_yenile_basla'].set(config['oto_yenile_basla'])
        if 'oto_yenile_bitis' in config: vars_dict['var_oto_yenile_bitis'].set(config['oto_yenile_bitis'])
        if 'tolerans_dk' in config: vars_dict['var_tolerans_dk'].set(config['tolerans_dk'])
        if 'anons_aktif' in config: vars_dict['var_anons_aktif'].set(config['anons_aktif'])
        if 'trend_alarm_aktif' in config: vars_dict['var_trend_alarm_aktif'].set(config['trend_alarm_aktif'])
        if 'metar_alarm_aktif' in config: vars_dict['var_metar_alarm_aktif'].set(config['metar_alarm_aktif'])
        if 'sinoptik_alarm_aktif' in config: vars_dict['var_sinoptik_alarm_aktif'].set(config['sinoptik_alarm_aktif'])
        if 'taf_alarm_aktif' in config: vars_dict['var_taf_alarm_aktif'].set(config['taf_alarm_aktif'])
        if 'saat_basi_aktif' in config: vars_dict['var_saat_basi_aktif'].set(config['saat_basi_aktif'])
        if 'rasat_zamani_aktif' in config: vars_dict['var_rasat_zamani_aktif'].set(config['rasat_zamani_aktif'])
        if 'rasat_zamani_start_min' in config: vars_dict['var_rasat_zamani_start_min'].set(config['rasat_zamani_start_min'])
        if 'rasat_zamani_start_hour' in config: vars_dict['var_rasat_zamani_start_hour'].set(config['rasat_zamani_start_hour'])
        if 'rasat_zamani_period' in config: vars_dict['var_rasat_zamani_period'].set(config['rasat_zamani_period'])
        if 'alarm_freq_rasat_zamani' in config: vars_dict['var_alarm_freq_rasat_zamani'].set(config['alarm_freq_rasat_zamani'])
        if 'alarm_sound_path' in config: vars_dict['var_ozel_ses_yolu'].set(config['alarm_sound_path'])
        if 'alarm_freq_metar' in config: vars_dict['var_alarm_freq_metar'].set(config['alarm_freq_metar'])
        if 'alarm_freq_taf' in config: vars_dict['var_alarm_freq_taf'].set(config['alarm_freq_taf'])
        if 'alarm_freq_synop' in config: vars_dict['var_alarm_freq_synop'].set(config['alarm_freq_synop'])
        if 'alarm_freq_incompatible' in config: vars_dict['var_alarm_freq_incompatible'].set(config['alarm_freq_incompatible'])
        if 'trend_min_sure' in config: vars_dict['var_trend_min_sure'].set(config['trend_min_sure'])
        if 'trend_max_sure' in config: vars_dict['var_trend_max_sure'].set(config['trend_max_sure'])
        if 'trend_tl_min_sure' in config: vars_dict['var_trend_tl_min_sure'].set(config['trend_tl_min_sure'])
        if 'trend_tl_max_sure' in config: vars_dict['var_trend_tl_max_sure'].set(config['trend_tl_max_sure'])
        if 'trend_zaman_aktif' in config: vars_dict['var_trend_zaman_aktif'].set(config['trend_zaman_aktif'])
        if 'taf_esnek_mod_aktif' in config: vars_dict['var_taf_esnek_mod'].set(config['taf_esnek_mod_aktif'])
        if 'kati_icao_kurallari' in config: vars_dict['var_kati_icao_kurallari'].set(config['kati_icao_kurallari'])
        
        # Tetikli Alarm Ayarları
        if 'metar_alarm_start_hour' in config: vars_dict['var_metar_alarm_start_hour'].set(config['metar_alarm_start_hour'])
        if 'metar_alarm_period' in config: vars_dict['var_metar_alarm_period'].set(config['metar_alarm_period'])
        if 'metar_alarm_trigger_min' in config: vars_dict['var_metar_alarm_trigger_min'].set(config['metar_alarm_trigger_min'])
        if 'synop_alarm_start_hour' in config: vars_dict['var_synop_alarm_start_hour'].set(config['synop_alarm_start_hour'])
        if 'synop_alarm_period' in config: vars_dict['var_synop_alarm_period'].set(config['synop_alarm_period'])
        if 'synop_alarm_trigger_min' in config: vars_dict['var_synop_alarm_trigger_min'].set(config['synop_alarm_trigger_min'])
        if 'metar_alarm_repeat' in config: vars_dict['var_metar_alarm_repeat'].set(config['metar_alarm_repeat'])
        if 'synop_alarm_repeat' in config: vars_dict['var_synop_alarm_repeat'].set(config['synop_alarm_repeat'])
        if 'taf_alarm_repeat' in config: vars_dict['var_taf_alarm_repeat'].set(config['taf_alarm_repeat'])
        if 'incompatible_alarm_repeat' in config: vars_dict['var_incompatible_alarm_repeat'].set(config['incompatible_alarm_repeat'])
        if 'taf_alarm_start_hour' in config: vars_dict['var_taf_alarm_start_hour'].set(config['taf_alarm_start_hour'])
        if 'taf_alarm_period' in config: vars_dict['var_taf_alarm_period'].set(config['taf_alarm_period'])
        if 'taf_alarm_trigger_min' in config: vars_dict['var_taf_alarm_trigger_min'].set(config['taf_alarm_trigger_min'])
        
        # Rasat Hatırlatıcıları Yükle
        for k in ['metar', 'synop', 'taf']:
            if f'remind_{k}_aktif' in config: vars_dict[f'var_remind_{k}_aktif'].set(config[f'remind_{k}_aktif'])
            if f'remind_{k}_start_h' in config: vars_dict[f'var_remind_{k}_start_h'].set(config[f'remind_{k}_start_h'])
            if f'remind_{k}_period' in config: vars_dict[f'var_remind_{k}_period'].set(config[f'remind_{k}_period'])
            if f'remind_{k}_min' in config: vars_dict[f'var_remind_{k}_min'].set(config[f'remind_{k}_min'])
            if f'remind_{k}_ontime' in config: vars_dict[f'var_remind_{k}_ontime'].set(config[f'remind_{k}_ontime'])

        for k in ['klima', 'max_ruzgar']:
            for suffix in ['aktif', 'start_hour', 'period', 'trigger_min']:
                key = f'var_{k}_alarm_{suffix}'
                if key[4:] in config: vars_dict[key].set(config[key[4:]])
            if f'alarm_freq_{k}' in config: vars_dict[f'var_alarm_freq_{k}'].set(config[f'alarm_freq_{k}'])

        if 'refresh_int_00_49' in config: vars_dict['var_refresh_int_00_49'].set(config['refresh_int_00_49'])
        if 'refresh_int_50_59' in config: vars_dict['var_refresh_int_50_59'].set(config['refresh_int_50_59'])
        if 'tebrik_aktif' in config: vars_dict['var_tebrik_aktif'].set(config['tebrik_aktif'])
        if 'konusma_hizi' in config: vars_dict['var_konusma_hizi'].set(config['konusma_hizi'])
        if 'konusma_perdesi' in config: vars_dict['var_konusma_perdesi'].set(config['konusma_perdesi'])
        if 'piper_aktif' in config: vars_dict['var_piper_aktif'].set(config['piper_aktif'])
        if 'edge_aktif' in config: vars_dict['var_edge_aktif'].set(config['edge_aktif'])
        if 'edge_voice' in config: vars_dict['var_edge_voice'].set(config['edge_voice'])
        if 'piper_bin' in config: vars_dict['var_piper_bin'].set(config['piper_bin'])
        if 'piper_model' in config: vars_dict['var_piper_model'].set(config['piper_model'])
        if 'alarm_max_volume' in config: vars_dict['var_alarm_max_volume'].set(config['alarm_max_volume'])
        if 'eksik_veri_saat' in config: vars_dict['var_eksik_veri_saat'].set(config['eksik_veri_saat'])
        if 'tema_secimi' in config: vars_dict['var_tema_secimi'].set(config['tema_secimi'])
        if 'yazi_boyutu' in config: vars_dict['var_yazi_boyutu'].set(config['yazi_boyutu'])
        if 'yazi_kalinligi' in config: vars_dict['var_yazi_kalinligi'].set(config['yazi_kalinligi'])
        if 'yazi_tipi' in config: vars_dict['var_yazi_tipi'].set(config['yazi_tipi'])
        if 'satir_yuksekligi' in config: vars_dict['var_satir_yuksekligi'].set(config['satir_yuksekligi'])
        if 'konsol_renk' in config: vars_dict['var_konsol_renk'].set(config['konsol_renk'])
        if 'tablo_arkaplan' in config: vars_dict['var_tablo_arkaplan'].set(config['tablo_arkaplan'])
        if 'tablo_zebra2' in config: vars_dict['var_tablo_zebra2'].set(config['tablo_zebra2'])
        if 'sutun_payi' in config: vars_dict['var_sutun_payi'].set(config['sutun_payi'])
        if 'tablo_secili_renk' in config: vars_dict['var_tablo_secili_renk'].set(config['tablo_secili_renk'])
        if 'filter_metar_start' in config: vars_dict['var_filter_metar_start'].set(config['filter_metar_start'])
        if 'filter_metar_end' in config: vars_dict['var_filter_metar_end'].set(config['filter_metar_end'])
        if 'filter_synop_start' in config: vars_dict['var_filter_synop_start'].set(config['filter_synop_start'])
        if 'filter_synop_end' in config: vars_dict['var_filter_synop_end'].set(config['filter_synop_end'])
        if 'filter_taf_start' in config: vars_dict['var_filter_taf_start'].set(config['filter_taf_start'])
        if 'filter_taf_end' in config: vars_dict['var_filter_taf_end'].set(config['filter_taf_end'])
        
        # Denetim Ayarları Yükle
        if 'denetim_metar_aktif' in config: vars_dict['var_denetim_metar_aktif'].set(config['denetim_metar_aktif'])
        if 'denetim_metar_p1_start' in config: vars_dict['var_denetim_metar_p1_start'].set(config['denetim_metar_p1_start'])
        if 'denetim_metar_p1_end' in config: vars_dict['var_denetim_metar_p1_end'].set(config['denetim_metar_p1_end'])
        if 'denetim_metar_start_hour' in config: vars_dict['var_denetim_metar_start_hour'].set(config['denetim_metar_start_hour'])
        if 'denetim_metar_period' in config: vars_dict['var_denetim_metar_period'].set(config['denetim_metar_period'])
        if 'denetim_synop_aktif' in config: vars_dict['var_denetim_synop_aktif'].set(config['denetim_synop_aktif'])
        if 'denetim_synop_int' in config: vars_dict['var_denetim_synop_int'].set(config['denetim_synop_int'])
        if 'denetim_synop_start_hour' in config: vars_dict['var_denetim_synop_start_hour'].set(config['denetim_synop_start_hour'])
        if 'denetim_synop_period' in config: vars_dict['var_denetim_synop_period'].set(config['denetim_synop_period'])
        if 'denetim_synop_start' in config: vars_dict['var_denetim_synop_start'].set(config['denetim_synop_start'])
        if 'denetim_synop_end' in config: vars_dict['var_denetim_synop_end'].set(config['denetim_synop_end'])
        if 'denetim_taf_aktif' in config: vars_dict['var_denetim_taf_aktif'].set(config['denetim_taf_aktif'])
        if 'denetim_taf_int' in config: vars_dict['var_denetim_taf_int'].set(config['denetim_taf_int'])
        if 'denetim_taf_start_hour' in config: vars_dict['var_denetim_taf_start_hour'].set(config['denetim_taf_start_hour'])
        if 'denetim_taf_period' in config: vars_dict['var_denetim_taf_period'].set(config['denetim_taf_period'])
        if 'denetim_taf_start' in config: vars_dict['var_denetim_taf_start'].set(config['denetim_taf_start'])
        if 'denetim_taf_end' in config: vars_dict['var_denetim_taf_end'].set(config['denetim_taf_end'])
        if 'denetim_gec_gelen_alarm_aktif' in config: vars_dict['var_denetim_gec_gelen_alarm_aktif'].set(config['denetim_gec_gelen_alarm_aktif'])
        if 'denetim_ceza_tekrar' in config: vars_dict['var_denetim_ceza_tekrar'].set(config['denetim_ceza_tekrar'])
        if 'denetim_ceza_aralik' in config: vars_dict['var_denetim_ceza_aralik'].set(config['denetim_ceza_aralik'])
        if 'delay_limit_metar' in config: vars_dict['var_delay_limit_metar'].set(config['delay_limit_metar'])
        if 'delay_limit_synop' in config: vars_dict['var_delay_limit_synop'].set(config['delay_limit_synop'])
        if 'delay_limit_taf' in config: vars_dict['var_delay_limit_taf'].set(config['delay_limit_taf'])
        if 'baglanti_hata_tekrar' in config: vars_dict['var_baglanti_hata_tekrar'].set(config['baglanti_hata_tekrar'])
        if 'baglanti_hata_aralik' in config: vars_dict['var_baglanti_hata_aralik'].set(config['baglanti_hata_aralik'])
        if 'uyum_show' in config: vars_dict['var_uyum_show'].set(config['uyum_show'])
        if 'tooltip_aktif' in config: vars_dict['var_tooltip_aktif'].set(config['tooltip_aktif'])
        if 'last_station' in config: vars_dict['var_last_station'].set(config['last_station'])
        if 'email_aktif' in config: vars_dict['var_email_aktif'].set(config['email_aktif'])
        if 'email_smtp' in config: vars_dict['var_email_smtp'].set(config['email_smtp'])
        if 'email_port' in config: vars_dict['var_email_port'].set(config['email_port'])
        if 'email_gonderen' in config: vars_dict['var_email_gonderen'].set(config['email_gonderen'])
        if 'email_sifre' in config: vars_dict['var_email_sifre'].set(config['email_sifre'])
        if 'email_alici' in config: vars_dict['var_email_alici'].set(config['email_alici'])
        
        # Rasat Stilleri
        for t in ['metar', 'taf', 'synop', 'other', 'uyumsuz', 'gec', 'eski', 're_hatasi']:
            if f'style_{t}_fg' in config: vars_dict[f'var_style_{t}_fg'].set(config[f'style_{t}_fg'])
            if f'style_{t}_bg' in config: vars_dict[f'var_style_{t}_bg'].set(config[f'style_{t}_bg'])
            if f'style_{t}_family' in config: vars_dict[f'var_style_{t}_family'].set(config[f'style_{t}_family'])
            if f'style_{t}_size' in config: vars_dict[f'var_style_{t}_size'].set(config[f'style_{t}_size'])
            if f'style_{t}_bold' in config: vars_dict[f'var_style_{t}_bold'].set(config[f'style_{t}_bold'])
        
        # Özel Alarmları Yükle
        for i in range(5):
            if f'special_alarm_{i}_active' in config: vars_dict[f'var_sa_active_{i}'].set(config[f'special_alarm_{i}_active'])
            if f'special_alarm_{i}_freq' in config: vars_dict[f'var_sa_freq_{i}'].set(config[f'special_alarm_{i}_freq'])
            if f'special_alarm_{i}_date' in config: vars_dict[f'var_sa_date_{i}'].set(config[f'special_alarm_{i}_date'])
            if f'special_alarm_{i}_time' in config: vars_dict[f'var_sa_time_{i}'].set(config[f'special_alarm_{i}_time'])
            if f'special_alarm_{i}_msg' in config: vars_dict[f'var_sa_msg_{i}'].set(config[f'special_alarm_{i}_msg'])
            if f'special_alarm_{i}_repeat' in config: vars_dict[f'var_sa_repeat_{i}'].set(config[f'special_alarm_{i}_repeat'])
            if f'special_alarm_{i}_count' in config: vars_dict[f'var_sa_count_{i}'].set(config[f'special_alarm_{i}_count'])
        
        for i in range(20):
            if f'kull_id_{i}' in config: vars_dict[f'var_kull_id_{i}'].set(config[f'kull_id_{i}'])
            if f'kull_name_{i}' in config: vars_dict[f'var_kull_name_{i}'].set(config[f'kull_name_{i}'])
    except Exception as e:
        print(f"Ayarlar yüklenirken hata: {e}")

def save_settings(vars_dict):
    """Değişkenlerdeki ayarları config dosyasına kaydeder."""
    def get_safe(key, default=0):
        try:
            return vars_dict[key].get()
        except:
            return default

    data = {
        "oto_yenile_basla": get_safe('var_oto_yenile_basla'),
        "oto_yenile_bitis": get_safe('var_oto_yenile_bitis'),
        "tolerans_dk": get_safe('var_tolerans_dk'),
        "anons_aktif": vars_dict['var_anons_aktif'].get(),
        "trend_alarm_aktif": vars_dict['var_trend_alarm_aktif'].get(),
        "metar_alarm_aktif": vars_dict['var_metar_alarm_aktif'].get(),
        "sinoptik_alarm_aktif": vars_dict['var_sinoptik_alarm_aktif'].get(),
        "taf_alarm_aktif": vars_dict['var_taf_alarm_aktif'].get(),
        "saat_basi_aktif": vars_dict['var_saat_basi_aktif'].get(),
        "rasat_zamani_aktif": vars_dict['var_rasat_zamani_aktif'].get(),
        "rasat_zamani_start_min": get_safe('var_rasat_zamani_start_min', 50),
        "rasat_zamani_start_hour": get_safe('var_rasat_zamani_start_hour', 0),
        "rasat_zamani_period": get_safe('var_rasat_zamani_period', 1),
        "alarm_freq_rasat_zamani": get_safe('var_alarm_freq_rasat_zamani', 0),
        "alarm_sound_path": vars_dict['var_ozel_ses_yolu'].get(),
        "alarm_freq_metar": get_safe('var_alarm_freq_metar'),
        "alarm_freq_taf": get_safe('var_alarm_freq_taf'),
        "alarm_freq_synop": get_safe('var_alarm_freq_synop'),
        "alarm_freq_incompatible": get_safe('var_alarm_freq_incompatible'),
        "trend_min_sure": get_safe('var_trend_min_sure', 15),
        "trend_max_sure": get_safe('var_trend_max_sure', 75),
        "trend_tl_min_sure": get_safe('var_trend_tl_min_sure', 15),
        "trend_tl_max_sure": get_safe('var_trend_tl_max_sure', 90),
        "trend_zaman_aktif": get_safe('var_trend_zaman_aktif', True),
        "taf_esnek_mod_aktif": get_safe('var_taf_esnek_mod', True),
        "kati_icao_kurallari": get_safe('var_kati_icao_kurallari', False),
        
        "metar_alarm_start_hour": get_safe('var_metar_alarm_start_hour'),
        "metar_alarm_period": get_safe('var_metar_alarm_period'),
        "metar_alarm_trigger_min": get_safe('var_metar_alarm_trigger_min'),
        "synop_alarm_start_hour": get_safe('var_synop_alarm_start_hour'),
        "synop_alarm_period": get_safe('var_synop_alarm_period'),
        "synop_alarm_trigger_min": get_safe('var_synop_alarm_trigger_min'),
        "metar_alarm_repeat": get_safe('var_metar_alarm_repeat', 4),
        "synop_alarm_repeat": get_safe('var_synop_alarm_repeat', 4),
        "taf_alarm_repeat": get_safe('var_taf_alarm_repeat', 4),
        "incompatible_alarm_repeat": get_safe('var_incompatible_alarm_repeat', 3),
        "taf_alarm_start_hour": get_safe('var_taf_alarm_start_hour'),
        "taf_alarm_period": get_safe('var_taf_alarm_period'),
        "taf_alarm_trigger_min": get_safe('var_taf_alarm_trigger_min'),
        
        "remind_metar_aktif": vars_dict['var_remind_metar_aktif'].get(), "remind_metar_start_h": get_safe('var_remind_metar_start_h'), "remind_metar_period": get_safe('var_remind_metar_period'), "remind_metar_min": get_safe('var_remind_metar_min'), "remind_metar_ontime": get_safe('var_remind_metar_ontime'),
        "remind_synop_aktif": vars_dict['var_remind_synop_aktif'].get(), "remind_synop_start_h": get_safe('var_remind_synop_start_h'), "remind_synop_period": get_safe('var_remind_synop_period'), "remind_synop_min": get_safe('var_remind_synop_min'), "remind_synop_ontime": get_safe('var_remind_synop_ontime'),
        "remind_taf_aktif": vars_dict['var_remind_taf_aktif'].get(), "remind_taf_start_h": get_safe('var_remind_taf_start_h'), "remind_taf_period": get_safe('var_remind_taf_period'), "remind_taf_min": get_safe('var_remind_taf_min'), "remind_taf_ontime": get_safe('var_remind_taf_ontime'),

        "klima_alarm_aktif": vars_dict['var_klima_alarm_aktif'].get(), "klima_alarm_start_hour": get_safe('var_klima_alarm_start_hour'), "klima_alarm_period": get_safe('var_klima_alarm_period'), "klima_alarm_trigger_min": get_safe('var_klima_alarm_trigger_min'), "alarm_freq_klima": get_safe('var_alarm_freq_klima'),
        "max_ruzgar_alarm_aktif": vars_dict['var_max_ruzgar_alarm_aktif'].get(), "max_ruzgar_alarm_start_hour": get_safe('var_max_ruzgar_alarm_start_hour'), "max_ruzgar_alarm_period": get_safe('var_max_ruzgar_alarm_period'), "max_ruzgar_alarm_trigger_min": get_safe('var_max_ruzgar_alarm_trigger_min'), "alarm_freq_max_ruzgar": get_safe('var_alarm_freq_max_ruzgar'),

        "refresh_int_00_49": get_safe('var_refresh_int_00_49'),
        "refresh_int_50_59": get_safe('var_refresh_int_50_59'),
        "tebrik_aktif": vars_dict['var_tebrik_aktif'].get(),
        "konusma_hizi": get_safe('var_konusma_hizi', 150),
        "konusma_perdesi": get_safe('var_konusma_perdesi', 0),
        "piper_aktif": vars_dict['var_piper_aktif'].get(),
        "edge_aktif": vars_dict['var_edge_aktif'].get(),
        "edge_voice": vars_dict['var_edge_voice'].get(),
        "piper_bin": vars_dict['var_piper_bin'].get(),
        "piper_model": vars_dict['var_piper_model'].get(),
        "alarm_max_volume": vars_dict['var_alarm_max_volume'].get(),
        "eksik_veri_saat": get_safe('var_eksik_veri_saat', 1),
        "tema_secimi": vars_dict['var_tema_secimi'].get(),
        "yazi_boyutu": get_safe('var_yazi_boyutu', 10),
        "yazi_kalinligi": vars_dict['var_yazi_kalinligi'].get(),
        "yazi_tipi": vars_dict['var_yazi_tipi'].get(),
        "satir_yuksekligi": get_safe('var_satir_yuksekligi', 25),
        "konsol_renk": vars_dict['var_konsol_renk'].get(),
        "tablo_arkaplan": vars_dict['var_tablo_arkaplan'].get(),
        "tablo_zebra2": vars_dict['var_tablo_zebra2'].get(),
        "sutun_payi": get_safe('var_sutun_payi', 25),
        "tablo_secili_renk": vars_dict['var_tablo_secili_renk'].get(),
        "filter_metar_start": get_safe('var_filter_metar_start', 50),
        "filter_metar_end": get_safe('var_filter_metar_end', 54),
        "filter_synop_start": get_safe('var_filter_synop_start', 50),
        "filter_synop_end": get_safe('var_filter_synop_end', 59),
        "filter_taf_start": get_safe('var_filter_taf_start', 30),
        "filter_taf_end": get_safe('var_filter_taf_end', 59),
        "denetim_metar_aktif": vars_dict['var_denetim_metar_aktif'].get(),
        "denetim_metar_p1_start": get_safe('var_denetim_metar_p1_start', 50),
        "denetim_metar_start_hour": get_safe('var_denetim_metar_start_hour', 0),
        "denetim_metar_period": get_safe('var_denetim_metar_period', 1),
        "denetim_synop_aktif": vars_dict['var_denetim_synop_aktif'].get(),
        "denetim_synop_int": vars_dict['var_denetim_synop_int'].get(),
        "denetim_synop_start_hour": get_safe('var_denetim_synop_start_hour', 0),
        "denetim_synop_period": get_safe('var_denetim_synop_period', 3),
        "denetim_synop_start": get_safe('var_denetim_synop_start', 50),
        "denetim_synop_end": get_safe('var_denetim_synop_end', 0),
        "denetim_taf_aktif": vars_dict['var_denetim_taf_aktif'].get(),
        "denetim_taf_int": vars_dict['var_denetim_taf_int'].get(),
        "denetim_taf_start_hour": get_safe('var_denetim_taf_start_hour', 1),
        "denetim_taf_period": get_safe('var_denetim_taf_period', 3),
        "denetim_taf_start": get_safe('var_denetim_taf_start', 35),
        "denetim_taf_end": get_safe('var_denetim_taf_end', 0),
        "denetim_gec_gelen_alarm_aktif": vars_dict['var_denetim_gec_gelen_alarm_aktif'].get(),
        "denetim_ceza_tekrar": get_safe('var_denetim_ceza_tekrar', 3),
        "denetim_ceza_aralik": get_safe('var_denetim_ceza_aralik', 3),
        "delay_limit_metar": get_safe('var_delay_limit_metar', 5),
        "delay_limit_synop": get_safe('var_delay_limit_synop', 10),
        "delay_limit_taf": get_safe('var_delay_limit_taf', 20),
        "baglanti_hata_tekrar": get_safe('var_baglanti_hata_tekrar', 2),
        "baglanti_hata_aralik": get_safe('var_baglanti_hata_aralik', 1),
        "uyum_show": vars_dict['var_uyum_show'].get(),
        "tooltip_aktif": vars_dict['var_tooltip_aktif'].get(),
        "last_station": vars_dict['var_last_station'].get(),
        "email_aktif": vars_dict['var_email_aktif'].get(),
        "email_smtp": vars_dict['var_email_smtp'].get(),
        "email_port": get_safe('var_email_port', 587),
        "email_gonderen": vars_dict['var_email_gonderen'].get(),
        "email_sifre": vars_dict['var_email_sifre'].get(),
        "email_alici": vars_dict['var_email_alici'].get()
    }
    
    # Rasat Stilleri
    for t in ['metar', 'taf', 'synop', 'other', 'uyumsuz', 'gec', 'eski', 're_hatasi', 'cor_amd']:
        fg_def = "white" if t in ["uyumsuz", "re_hatasi", "cor_amd"] else ("#78909C" if t == "eski" else "black")
        bg_def = "#D32F2F" if t in ["uyumsuz"] else ("#0D47A1" if t == "cor_amd" else ("#E040FB" if t == "re_hatasi" else ("#F8BBD0" if t == "gec" else ("#ECEFF1" if t == "eski" else ("#FFFFFF" if t == "metar" else "")))))
        bold_def = True if t in ["uyumsuz", "re_hatasi", "cor_amd"] else False
        data[f'style_{t}_fg'] = get_safe(f'var_style_{t}_fg', fg_def)
        data[f'style_{t}_bg'] = get_safe(f'var_style_{t}_bg', bg_def)
        data[f'style_{t}_family'] = get_safe(f'var_style_{t}_family', "Arial")
        data[f'style_{t}_size'] = get_safe(f'var_style_{t}_size', 10)
        data[f'style_{t}_bold'] = get_safe(f'var_style_{t}_bold', bold_def)
    
    # Özel Alarmları Kaydet
    for i in range(5):
        data[f'special_alarm_{i}_active'] = vars_dict[f'var_sa_active_{i}'].get()
        data[f'special_alarm_{i}_freq'] = vars_dict[f'var_sa_freq_{i}'].get()
        data[f'special_alarm_{i}_date'] = vars_dict[f'var_sa_date_{i}'].get()
        data[f'special_alarm_{i}_time'] = vars_dict[f'var_sa_time_{i}'].get()
        data[f'special_alarm_{i}_msg'] = vars_dict[f'var_sa_msg_{i}'].get()
        data[f'special_alarm_{i}_repeat'] = get_safe(f'var_sa_repeat_{i}')
        data[f'special_alarm_{i}_count'] = get_safe(f'var_sa_count_{i}')
        
    for i in range(20):
        data[f'kull_id_{i}'] = vars_dict[f'var_kull_id_{i}'].get()
        data[f'kull_name_{i}'] = vars_dict[f'var_kull_name_{i}'].get()
        
    config_manager.save_config(data)

def setup_settings_tab(parent, vars, callbacks):
    """
    Ayarlar sekmesinin içeriğini oluşturur.
    """
    
    refresh_info_window_callback = None

    # --- İÇ FONKSİYONLAR ---
    def enable_mouse_wheel(widget):
        """Spinbox için fare tekerleği desteği."""
        def _on_mouse_wheel(event):
            if event.delta > 0: widget.event_generate("<<Increment>>")
            else: widget.event_generate("<<Decrement>>")
            return "break"
        widget.bind("<MouseWheel>", _on_mouse_wheel)
        widget.bind("<Button-4>", lambda e: widget.event_generate("<<Increment>>"))
        widget.bind("<Button-5>", lambda e: widget.event_generate("<<Decrement>>"))

    def ses_sec_butonu():
        yol = filedialog.askopenfilename(filetypes=[("Ses", "*.mp3 *.wav")])
        if yol:
            vars['var_ozel_ses_yolu'].set(yol)
            # Trace sayesinde otomatik kaydedilecek

    def reset_defaults():
        if messagebox.askyesno("Varsayılanlara Dön", "Ayarlar varsayılan değerlere (50-59 dk, 45 dk tolerans) dönecek. Emin misiniz?"):
            vars['var_oto_yenile_basla'].set(50)
            vars['var_oto_yenile_bitis'].set(59)
            vars['var_tolerans_dk'].set(45)
            # Trace sayesinde otomatik kaydedilecek

    # --- OTO KAYIT İÇİN İZLEME (TRACE) ---
    def on_change(*args):
        # save_settings(vars) # Oto kayıt devre dışı (Manuel kayıt için)
        if 'on_settings_change' in callbacks:
            callbacks['on_settings_change']()
        
        if refresh_info_window_callback:
            refresh_info_window_callback()

    # TEMA DEĞİŞİKLİĞİ MANTIĞI (MODLAR MENÜSÜ İÇİN)
    def on_theme_change(*args):
        try:
            t = vars['var_tema_secimi'].get()
            if t == "Açık Mod":
                vars['var_konsol_renk'].set("#F5F5F5")
                vars['var_tablo_arkaplan'].set("#FFFFFF")
                vars['var_tablo_zebra2'].set("#F5F5F5")
                vars['var_tablo_secili_renk'].set("#2196F3")
                vars['var_style_metar_bg'].set("#FFFFFF")
                vars['var_style_metar_fg'].set("black")
            elif t == "Koyu Mod":
                vars['var_konsol_renk'].set("#263238")
                vars['var_tablo_arkaplan'].set("#37474F")
                vars['var_tablo_zebra2'].set("#263238")
                vars['var_tablo_secili_renk'].set("#1976D2")
                vars['var_style_metar_bg'].set("#455A64")
                vars['var_style_metar_fg'].set("black")
        except: pass

    vars['var_tema_secimi'].trace_add("write", on_theme_change)

    # GENEL YAZI TİPİ/BOYUTU DEĞİŞTİĞİNDE ALT STİLLERİ DE OTOMATİK GÜNCELLE
    def sync_general_fonts(*args):
        try:
            sz = vars['var_yazi_boyutu'].get()
            fam = vars['var_yazi_tipi'].get()
            for t in ['metar', 'taf', 'synop', 'other']:
                vars[f'var_style_{t}_size'].set(sz)
                vars[f'var_style_{t}_family'].set(fam)
        except: pass

    vars['var_yazi_boyutu'].trace_add("write", sync_general_fonts)
    vars['var_yazi_tipi'].trace_add("write", sync_general_fonts)

    trace_vars = ['var_oto_yenile_basla', 'var_oto_yenile_bitis', 'var_tolerans_dk', 'var_ozel_ses_yolu', 
                  'var_alarm_freq_metar', 'var_alarm_freq_taf', 'var_alarm_freq_synop', 'var_alarm_freq_incompatible', 
                  'var_metar_alarm_trigger_min', 'var_synop_alarm_trigger_min', 'var_taf_alarm_trigger_min', 'var_refresh_int_00_49', 
                  'var_metar_alarm_aktif', 'var_sinoptik_alarm_aktif', 'var_taf_alarm_aktif', 'var_trend_alarm_aktif',
                  'var_klima_alarm_aktif', 'var_max_ruzgar_alarm_aktif',
                  'var_metar_alarm_start_hour', 'var_metar_alarm_period', 'var_synop_alarm_start_hour', 'var_synop_alarm_period', 
                  'var_taf_alarm_start_hour', 'var_taf_alarm_period', 'var_klima_alarm_start_hour', 'var_klima_alarm_period', 'var_klima_alarm_trigger_min', 'var_alarm_freq_klima',
                  'var_max_ruzgar_alarm_start_hour', 'var_max_ruzgar_alarm_period', 'var_max_ruzgar_alarm_trigger_min', 'var_alarm_freq_max_ruzgar',
                  'var_refresh_int_50_59', 'var_tebrik_aktif', 'var_konusma_hizi', 'var_konusma_perdesi', 'var_saat_basi_aktif', 'var_anons_aktif', 'var_piper_aktif', 'var_edge_aktif', 'var_edge_voice', 'var_piper_bin', 'var_piper_model', 'var_alarm_max_volume', 'var_eksik_veri_saat',
                  'var_metar_alarm_repeat', 'var_synop_alarm_repeat', 'var_taf_alarm_repeat',
                  'var_incompatible_alarm_repeat',
                  'var_yazi_kalinligi', 'var_yazi_tipi',
                  'var_tema_secimi', 'var_yazi_boyutu', 'var_satir_yuksekligi', 'var_konsol_renk', 'var_tablo_arkaplan',
                  'var_tablo_zebra2', 'var_sutun_payi', 'var_tablo_secili_renk', 'var_filter_metar_start', 'var_filter_metar_end', 
                  'var_filter_synop_start', 'var_filter_synop_end', 'var_filter_taf_start', 'var_filter_taf_end',
                  'var_trend_min_sure', 'var_trend_max_sure', 'var_trend_tl_min_sure', 'var_trend_tl_max_sure', 'var_trend_zaman_aktif',
                  'var_denetim_metar_aktif', 'var_denetim_metar_p1_start', 'var_denetim_metar_p1_end',
                  'var_denetim_metar_start_hour', 'var_denetim_metar_period',
                  'var_denetim_synop_aktif', 'var_denetim_synop_int', 'var_denetim_synop_start', 'var_denetim_synop_end', 'var_denetim_synop_start_hour', 'var_denetim_synop_period',
                  'var_denetim_taf_aktif', 'var_denetim_taf_int', 'var_denetim_taf_start', 'var_denetim_taf_end', 'var_denetim_taf_start_hour', 'var_denetim_taf_period',
                  'var_taf_esnek_mod', 'var_kati_icao_kurallari',
                  'var_delay_limit_metar', 'var_delay_limit_synop', 'var_delay_limit_taf', 'var_denetim_gec_gelen_alarm_aktif', 'var_denetim_ceza_tekrar', 'var_denetim_ceza_aralik',
                  'var_baglanti_hata_tekrar', 'var_baglanti_hata_aralik',
                  'var_remind_metar_aktif', 'var_remind_metar_start_h', 'var_remind_metar_period', 'var_remind_metar_min', 'var_remind_metar_ontime',
                  'var_remind_synop_aktif', 'var_remind_synop_start_h', 'var_remind_synop_period', 'var_remind_synop_min', 'var_remind_synop_ontime',
                  'var_remind_taf_aktif', 'var_remind_taf_start_h', 'var_remind_taf_period', 'var_remind_taf_min', 'var_remind_taf_ontime',
                  'var_uyum_show', 'var_tooltip_aktif', 'var_last_station',
                  'var_email_aktif', 'var_email_smtp', 'var_email_port', 'var_email_gonderen', 'var_email_sifre', 'var_email_alici']
    
    for t in ['metar', 'taf', 'synop', 'other', 'uyumsuz', 'gec', 'eski', 're_hatasi', 'cor_amd']:
        trace_vars.extend([f'var_style_{t}_fg', f'var_style_{t}_bg', f'var_style_{t}_family', f'var_style_{t}_size', f'var_style_{t}_bold'])

    for i in range(5):
        trace_vars.extend([f'var_sa_active_{i}', f'var_sa_freq_{i}', f'var_sa_date_{i}', f'var_sa_time_{i}', f'var_sa_msg_{i}', f'var_sa_repeat_{i}', f'var_sa_count_{i}'])

    for i in range(20):
        trace_vars.extend([f'var_kull_id_{i}', f'var_kull_name_{i}'])

    for v in trace_vars:
        if v in vars:
            vars[v].trace_add("write", on_change)

    # --- HEADER: UTC SAAT (ZULU) ---
    # Professional Dashboard Look
    f_header = tk.Frame(parent, bg="#263238", height=70)
    f_header.pack(side="top", fill="x")
    f_header.pack_propagate(False)
    
    # Clock Container
    f_clock_frame = tk.Frame(f_header, bg="#263238")
    f_clock_frame.place(relx=0.5, rely=0.5, anchor="center")
    
    tk.Label(f_clock_frame, text="SİSTEM SAATİ (UTC)", font=("Segoe UI", 8, "bold"), bg="#263238", fg="#B0BEC5").pack()
    
    # Dijital (LCD) Font Kontrolü
    clock_font = ("Consolas", 28, "bold")
    try:
        if "DS-Digital" in font.families():
            clock_font = ("DS-Digital", 42, "bold")
    except: pass
    
    # Clock Digits Container (Overlay için)
    f_digits = tk.Frame(f_clock_frame, bg="#263238")
    f_digits.pack()
    
    # Ghost Label (Arka plan gölgesi - Silik 88:88:88)
    tk.Label(f_digits, text="88:88:88 Z", font=clock_font, bg="#263238", fg="#1B5E20").grid(row=0, column=0)
    
    lbl_clock = tk.Label(f_digits, text="--:--:-- Z", font=clock_font, bg="#263238", fg="#00E676")
    lbl_clock.grid(row=0, column=0)

    # --- TABS (NOTEBOOK) & SCROLLABLE HELPER ---
    style = ttk.Style()
    style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[15, 5])
    
    # --- MODERN BUTTON STYLES ---
    style.configure("Modern.TButton", 
                    font=("Segoe UI", 9, "bold"), 
                    background="#546E7A", 
                    foreground="white", 
                    borderwidth=0, 
                    focuscolor="none", 
                    padding=6)
    style.map("Modern.TButton", 
              background=[('active', '#455A64'), ('pressed', '#37474F'), ('disabled', '#B0BEC5')],
              foreground=[('disabled', '#ECEFF1')])

    style.configure("Small.TButton", font=("Segoe UI", 8), background="#78909C", foreground="white", borderwidth=0, focuscolor="none", padding=2)
    style.map("Small.TButton", background=[('active', '#607D8B'), ('pressed', '#546E7A')])
    # ----------------------------

    notebook = ttk.Notebook(parent)
    notebook.pack(fill="both", expand=True, padx=5, pady=5)

    def create_scrollable_tab(tab_name):
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text=tab_name)
        
        canvas = tk.Canvas(tab_frame)
        scrollbar = ttk.Scrollbar(tab_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def _on_mousewheel(event): canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        scrollable_frame.bind('<Enter>', lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        scrollable_frame.bind('<Leave>', lambda e: canvas.unbind_all("<MouseWheel>"))
        
        return scrollable_frame

    # Tab 1: ALARM VE SAAT
    tab_alarm_saat = create_scrollable_tab(" ⏰ ALARM VE SAAT ")
    
    # Tab 2: İSTASYON AYARLARI
    tab_istasyon = create_scrollable_tab(" 🛠️ İSTASYON AYARLARI ")

    # Tab 3: ARAYÜZ & GÖRÜNÜM
    tab_arayuz = create_scrollable_tab(" 🎨 ARAYÜZ & GÖRÜNÜM ")

    # Tab 4: DENETİM AYARLARI
    tab_denetim = create_scrollable_tab(" 📋 DENETİM AYARLARI ")

    # ================= TAB 2: İSTASYON AYARLARI İÇERİĞİ =================
    
    # --- SES AYARLARI (Tab 2) ---
    f_ses = ttk.LabelFrame(tab_istasyon, text=" Ses ve Anons Ayarları ", padding=10)
    f_ses.pack(fill="x", pady=(0, 10))

    ttk.Checkbutton(f_ses, text="Google Sesli Anonsları Etkinleştir", variable=vars['var_anons_aktif']).pack(anchor="w", pady=5)
    f_edge_row = ttk.Frame(f_ses)
    f_edge_row.pack(fill="x", pady=5)
    ttk.Checkbutton(f_edge_row, text="Edge TTS Kullan (Online - 1. Öncelik)", variable=vars['var_edge_aktif']).pack(side="left")
    ttk.Label(f_edge_row, text="Ses:").pack(side="left", padx=(10, 2))
    cb_edge_voice = ttk.Combobox(f_edge_row, textvariable=vars['var_edge_voice'], values=["Ahmet (Erkek)", "Emel (Kadın)"], width=15, state="readonly")
    cb_edge_voice.pack(side="left", padx=2)
    ttk.Button(f_edge_row, text="Test Et", command=callbacks.get('edge_test'), width=8, style="Modern.TButton").pack(side="left", padx=10)
    ttk.Checkbutton(f_ses, text="Piper TTS Kullan (Yerel - 2. Öncelik)", variable=vars['var_piper_aktif']).pack(anchor="w", pady=5)
    
    # Ses Durum Bilgisi (Yeni)
    lbl_voice_status = ttk.Label(f_ses, text="", font=("Segoe UI", 8, "italic"), foreground="#546E7A")
    lbl_voice_status.pack(anchor="w", padx=25, pady=(0, 5))

    def update_voice_status(*args):
        if not vars['var_anons_aktif'].get(): lbl_voice_status.config(text="Durum: Sesli anonslar KAPALI.")
        elif vars['var_edge_aktif'].get(): lbl_voice_status.config(text="Durum: Aktif -> Edge TTS. Yedek: Piper/Sistem.")
        elif vars['var_piper_aktif'].get(): lbl_voice_status.config(text="Durum: Aktif -> Piper TTS. Yedek: Sistem.")
        else: lbl_voice_status.config(text="Durum: Aktif -> Sistem Sesi (Windows/Google).")
    
    vars['var_anons_aktif'].trace_add("write", update_voice_status)
    vars['var_piper_aktif'].trace_add("write", update_voice_status)
    update_voice_status() # İlk açılışta durumu yaz

    f_api = ttk.Frame(f_ses)
    f_api.pack(fill="x", pady=(0, 5), padx=20)
    
    ttk.Label(f_api, text="Piper Exe:").pack(side="left")
    ttk.Entry(f_api, textvariable=vars['var_piper_bin'], width=15).pack(side="left", padx=5)
    
    ttk.Label(f_api, text="Model (.onnx):").pack(side="left", padx=(10, 5))
    ttk.Entry(f_api, textvariable=vars['var_piper_model'], width=25).pack(side="left", padx=5)
    
    def select_piper_model():
        f = filedialog.askopenfilename(filetypes=[("ONNX Model", "*.onnx")])
        if f: vars['var_piper_model'].set(f)
        
    ttk.Button(f_api, text="📂", width=3, command=select_piper_model, style="Small.TButton").pack(side="left")

    ttk.Checkbutton(f_ses, text="Alarm Çalarken Sesi Maksimum Yap", variable=vars['var_alarm_max_volume']).pack(anchor="w", pady=5)

    f_hiz = ttk.Frame(f_ses)
    f_hiz.pack(fill="x", pady=5)
    ttk.Label(f_hiz, text="Konuşma Hızı:").pack(side="left")
    ttk.Button(f_hiz, text="↺", width=3, command=lambda: vars['var_konusma_hizi'].set(150), style="Small.TButton").pack(side="right", padx=2)
    ttk.Label(f_hiz, textvariable=vars['var_konusma_hizi'], width=4).pack(side="right")
    ttk.Scale(f_hiz, from_=100, to=250, variable=vars['var_konusma_hizi'], orient="horizontal").pack(side="left", fill="x", expand=True, padx=10)

    f_perde = ttk.Frame(f_ses)
    f_perde.pack(fill="x", pady=5)
    ttk.Label(f_perde, text="Ses Perdesi (Hz):").pack(side="left")
    ttk.Button(f_perde, text="↺", width=3, command=lambda: vars['var_konusma_perdesi'].set(0), style="Small.TButton").pack(side="right", padx=2)
    ttk.Label(f_perde, textvariable=vars['var_konusma_perdesi'], width=4).pack(side="right")
    ttk.Scale(f_perde, from_=-50, to=50, variable=vars['var_konusma_perdesi'], orient="horizontal").pack(side="left", fill="x", expand=True, padx=10)

    f_file = ttk.Frame(f_ses)
    f_file.pack(fill="x", pady=5)
    ttk.Button(f_file, text="📂 Özel Alarm Sesi Seç", command=ses_sec_butonu, style="Modern.TButton").pack(side="left")
    ttk.Label(f_file, textvariable=vars['var_ozel_ses_yolu'], foreground="blue").pack(side="left", padx=5, fill="x", expand=True)

    # --- TEST PANELİ (Tab 2) ---
    f_test = ttk.LabelFrame(tab_istasyon, text=" Sistem Testleri ", padding=10)
    f_test.pack(fill="x", pady=(0, 10))
    
    test_btns = [
        ("🔊 Ses Testi", callbacks.get('ses_testi')),
        ("🗣️ Konuşma Testi", callbacks.get('test_speech_engine')),
        ("🔔 Alarm Sesi", callbacks.get('play_alarm_sound')),
        ("⚠️ Rasat Yok", callbacks.get('rasat_yok_testi')),
        ("✅ Rasat Geldi", callbacks.get('rasat_geldi_testi')),
        ("🚨 Simülasyon", callbacks.get('alarm_simulation')),
    ]
    
    for i, (txt, cmd) in enumerate(test_btns):
        r, c = divmod(i, 2)
        ttk.Button(f_test, text=txt, command=cmd, style="Modern.TButton").grid(row=r, column=c, sticky="ew", padx=2, pady=2)
    f_test.columnconfigure(0, weight=1)
    f_test.columnconfigure(1, weight=1)

    # ================= TAB 1: ALARM VE SAAT İÇERİĞİ =================

    # --- OTO YENİLEME (Tab 1) ---
    f_oto_yenile_ayar = ttk.LabelFrame(tab_alarm_saat, text=" Otomatik Yenileme Aralığı (Dakika) ", padding=10)
    f_oto_yenile_ayar.pack(fill="x", pady=(0, 10))
    
    f_oto_grid = ttk.Frame(f_oto_yenile_ayar)
    f_oto_grid.pack(fill="x")
    
    ttk.Label(f_oto_grid, text="Aktif Aralık (dk):").grid(row=0, column=0, sticky="w", pady=5)
    
    f_range = ttk.Frame(f_oto_grid)
    f_range.grid(row=0, column=1, sticky="w")
    sb_start = ttk.Spinbox(f_range, from_=0, to=59, textvariable=vars['var_oto_yenile_basla'], width=3)
    sb_start.pack(side="left")
    enable_mouse_wheel(sb_start)
    ttk.Label(f_range, text="-").pack(side="left")
    sb_end = ttk.Spinbox(f_range, from_=0, to=59, textvariable=vars['var_oto_yenile_bitis'], width=3)
    sb_end.pack(side="left")
    enable_mouse_wheel(sb_end)
    
    ttk.Label(f_oto_grid, text="Normal Hız (sn):").grid(row=1, column=0, sticky="w", pady=5)
    sb_r1 = ttk.Spinbox(f_oto_grid, from_=5, to=600, textvariable=vars.get('var_refresh_int_00_49'), width=5)
    sb_r1.grid(row=1, column=1, sticky="w")
    enable_mouse_wheel(sb_r1)
    
    ttk.Label(f_oto_grid, text="Yoğun Hız (sn):").grid(row=2, column=0, sticky="w", pady=5)
    sb_r2 = ttk.Spinbox(f_oto_grid, from_=5, to=600, textvariable=vars.get('var_refresh_int_50_59'), width=5)
    sb_r2.grid(row=2, column=1, sticky="w")
    enable_mouse_wheel(sb_r2)

    # Durum LED'i
    f_led = ttk.Frame(f_oto_yenile_ayar)
    f_led.pack(fill="x", pady=5)
    ttk.Label(f_led, text="Durum:").pack(side="left")
    cv_led = tk.Canvas(f_led, width=16, height=16, highlightthickness=0)
    cv_led.pack(side="left", padx=5)
    led_id = cv_led.create_oval(2, 2, 14, 14, fill="#B0BEC5", outline="#78909C")
    lbl_countdown = ttk.Label(f_led, text="", font=("Segoe UI", 8, "bold"))
    lbl_countdown.pack(side="left", padx=5)

    def update_led():
        if not cv_led.winfo_exists(): return
        try:
            now_min = datetime.now(timezone.utc).minute
            s = vars['var_oto_yenile_basla'].get()
            e = vars['var_oto_yenile_bitis'].get()
            active = (s <= now_min <= e) if s <= e else ((now_min >= s) or (now_min <= e))
            if active:
                col, txt, fg = "#00E676", "AKTİF", "#2E7D32"
            else:
                col, txt, fg = "#B0BEC5", "BEKLEMEDE", "#EF6C00"
            cv_led.itemconfig(led_id, fill=col)
            lbl_countdown.config(text=txt, foreground=fg)
        except: pass
        cv_led.after(1000, update_led)
    update_led()
    
    ttk.Button(f_oto_yenile_ayar, text="Varsayılanlara Dön", command=reset_defaults, style="Modern.TButton").pack(anchor="e", pady=5)

    # --- TETİKLİ ALARM İLE VERİ KONTROLÜ (Tab 1) ---
    f_per = ttk.LabelFrame(tab_alarm_saat, text=" ŞARTA BAĞLI RASAT İKAZ ALARMI ", padding=10)
    f_per.pack(fill="x", pady=(0, 10))
    
    ttk.Label(f_per, text="(Rasat periyotunda belirtilen eşik değerlerde gelmeyen rasatlar tespit ettiğinde çalar)\nÖrn: 1. ikaz metarda 53 geçe, sonra her 60 sn veri gelip gelmediğine göre 2. ikaz çalar.", font=("Segoe UI", 8), foreground="#546E7A").pack(anchor="w", pady=(0, 10))
    
    f_grid = ttk.Frame(f_per)
    f_grid.pack(fill="x")
    f_grid.columnconfigure(0, weight=1)

    ttk.Label(f_grid, text="Tip", font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w", pady=(0,5))
    ttk.Label(f_grid, text="Başlangıç (Saat:Dk)", font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="", pady=(0,5))
    ttk.Label(f_grid, text="Periyot(Sa)", font=("Segoe UI", 8, "bold")).grid(row=0, column=2, sticky="", pady=(0,5))
    ttk.Label(f_grid, text="Tetik(Dk)", font=("Segoe UI", 8, "bold")).grid(row=0, column=3, sticky="", pady=(0,5))
    ttk.Label(f_grid, text="Sıklık(Sn)", font=("Segoe UI", 8, "bold")).grid(row=0, column=4, sticky="", pady=(0,5))
    ttk.Label(f_grid, text="Tekrar", font=("Segoe UI", 8, "bold")).grid(row=0, column=5, sticky="", pady=(0,5))
    ttk.Label(f_grid, text="Limit(Bit.)", font=("Segoe UI", 8, "bold")).grid(row=0, column=6, sticky="e", pady=(0,5))

    row_idx = 1
    def add_alarm_item(label, var_active, var_start_h, var_period, var_trigger, var_freq, var_repeat=None, var_limit_end=None):
        nonlocal row_idx
        ttk.Checkbutton(f_grid, text=label, variable=var_active).grid(row=row_idx, column=0, sticky="w", pady=3)
        
        # Başlangıç Saati
        ent_sh = ttk.Entry(f_grid, textvariable=var_start_h, width=6)
        ent_sh.grid(row=row_idx, column=1, padx=2)
        
        # Periyot
        sb_p = ttk.Spinbox(f_grid, from_=1, to=24, textvariable=var_period, width=3)
        sb_p.grid(row=row_idx, column=2, padx=2)
        enable_mouse_wheel(sb_p)
        
        # Tetik Dakikası
        sb_t = ttk.Spinbox(f_grid, from_=0, to=59, textvariable=var_trigger, width=3)
        sb_t.grid(row=row_idx, column=3, padx=2)
        enable_mouse_wheel(sb_t)
        
        # Sıklık
        sb_f = ttk.Spinbox(f_grid, from_=5, to=3600, textvariable=var_freq, width=5)
        sb_f.grid(row=row_idx, column=4, sticky="", padx=2)
        enable_mouse_wheel(sb_f)
        
        # Tekrar (Yeni)
        if var_repeat:
            sb_r = ttk.Spinbox(f_grid, from_=1, to=20, textvariable=var_repeat, width=3)
            sb_r.grid(row=row_idx, column=5, sticky="", padx=2)
            enable_mouse_wheel(sb_r)
        
        # Limit Bitiş (Ceza Başlangıcı belirler)
        if var_limit_end:
            sb_l = ttk.Spinbox(f_grid, from_=0, to=59, textvariable=var_limit_end, width=3)
            sb_l.grid(row=row_idx, column=6, sticky="e", padx=2)
            enable_mouse_wheel(sb_l)
        
        row_idx += 1

    add_alarm_item("METAR", vars['var_metar_alarm_aktif'], vars['var_metar_alarm_start_hour'], vars['var_metar_alarm_period'], vars['var_metar_alarm_trigger_min'], vars['var_alarm_freq_metar'], vars['var_metar_alarm_repeat'], vars['var_denetim_metar_p1_end'])
    add_alarm_item("SİNOPTİK", vars['var_sinoptik_alarm_aktif'], vars['var_synop_alarm_start_hour'], vars['var_synop_alarm_period'], vars['var_synop_alarm_trigger_min'], vars['var_alarm_freq_synop'], vars['var_synop_alarm_repeat'], vars['var_denetim_synop_end'])
    add_alarm_item("TAF", vars['var_taf_alarm_aktif'], vars['var_taf_alarm_start_hour'], vars['var_taf_alarm_period'], vars['var_taf_alarm_trigger_min'], vars['var_alarm_freq_taf'], vars['var_taf_alarm_repeat'], vars['var_denetim_taf_end'])
    add_alarm_item("GÜNLÜK KLİMA", vars['var_klima_alarm_aktif'], vars['var_klima_alarm_start_hour'], vars['var_klima_alarm_period'], vars['var_klima_alarm_trigger_min'], vars['var_alarm_freq_klima'])
    add_alarm_item("MAX RÜZGAR", vars['var_max_ruzgar_alarm_aktif'], vars['var_max_ruzgar_alarm_start_hour'], vars['var_max_ruzgar_alarm_period'], vars['var_max_ruzgar_alarm_trigger_min'], vars['var_alarm_freq_max_ruzgar'])
    
    # Uyumsuzluk ve Rasat Zamanı (Eski usul devam)
    ttk.Separator(f_grid, orient="horizontal").grid(row=row_idx, column=0, columnspan=5, sticky="ew", pady=5)
    row_idx += 1
    
    ttk.Checkbutton(f_grid, text="Uyumsuzluk", variable=vars['var_trend_alarm_aktif']).grid(row=row_idx, column=0, sticky="w")
    sb_inc = ttk.Spinbox(f_grid, from_=5, to=3600, textvariable=vars['var_alarm_freq_incompatible'], width=5)
    sb_inc.grid(row=row_idx, column=4, sticky="", padx=2)
    enable_mouse_wheel(sb_inc)
    sb_inc_rep = ttk.Spinbox(f_grid, from_=1, to=20, textvariable=vars['var_incompatible_alarm_repeat'], width=3)
    sb_inc_rep.grid(row=row_idx, column=5, sticky="", padx=2)
    enable_mouse_wheel(sb_inc_rep)
    row_idx += 1

    # --- RASAT ZAMANI HATIRLATICILARI (YENİ BÖLÜM) ---
    f_remind = ttk.LabelFrame(tab_alarm_saat, text=" Rasat Zamanı Hatırlatıcıları (Personel Uyarı) ", padding=10)
    f_remind.pack(fill="x", pady=(0, 10))
    
    f_rem_grid = ttk.Frame(f_remind)
    f_rem_grid.pack(fill="x")
    f_rem_grid.columnconfigure(0, weight=1)

    ttk.Label(f_rem_grid, text="Tip", font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w", pady=(0,5))
    ttk.Label(f_rem_grid, text="Başlangıç (Saat:Dk)", font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="", pady=(0,5))
    ttk.Label(f_rem_grid, text="Periyot(Sa)", font=("Segoe UI", 8, "bold")).grid(row=0, column=2, sticky="", pady=(0,5))
    ttk.Label(f_rem_grid, text="On Time(Dk)", font=("Segoe UI", 8, "bold")).grid(row=0, column=3, sticky="", pady=(0,5))

    rem_row_idx = 1
    def add_remind_item(label, var_active, var_start_h, var_period, var_min, var_ontime):
        nonlocal rem_row_idx
        ttk.Checkbutton(f_rem_grid, text=label, variable=var_active).grid(row=rem_row_idx, column=0, sticky="w", pady=3)
        ent_sh = ttk.Entry(f_rem_grid, textvariable=var_start_h, width=6)
        ent_sh.grid(row=rem_row_idx, column=1, padx=2)
        sb_p = ttk.Spinbox(f_rem_grid, from_=1, to=24, textvariable=var_period, width=3)
        sb_p.grid(row=rem_row_idx, column=2, padx=2)
        enable_mouse_wheel(sb_p)
        sb_ot = ttk.Spinbox(f_rem_grid, from_=1, to=120, textvariable=var_ontime, width=3)
        sb_ot.grid(row=rem_row_idx, column=3, padx=2)
        enable_mouse_wheel(sb_ot)
        rem_row_idx += 1

    add_remind_item("METAR HAZIRLIK", vars['var_remind_metar_aktif'], vars['var_remind_metar_start_h'], vars['var_remind_metar_period'], vars['var_remind_metar_min'], vars['var_remind_metar_ontime'])
    add_remind_item("SİNOPTİK HAZIRLIK", vars['var_remind_synop_aktif'], vars['var_remind_synop_start_h'], vars['var_remind_synop_period'], vars['var_remind_synop_min'], vars['var_remind_synop_ontime'])
    add_remind_item("TAF HAZIRLIK", vars['var_remind_taf_aktif'], vars['var_remind_taf_start_h'], vars['var_remind_taf_period'], vars['var_remind_taf_min'], vars['var_remind_taf_ontime'])

    # --- DİĞER AYARLAR (Tab 1) ---
    f_other = ttk.LabelFrame(tab_alarm_saat, text=" Diğer Ayarlar ", padding=10)
    f_other.pack(fill="x", pady=(0, 10))
    
    ttk.Checkbutton(f_other, text="Saat Başı Hatırlatıcı (:00)", variable=vars['var_saat_basi_aktif']).pack(anchor="w", pady=5)
    
    f_tol = ttk.Frame(f_other)
    f_tol.pack(fill="x", pady=5)
    ttk.Label(f_tol, text="Eksik Veri Tol. (dk):").pack(side="left")
    sb_tol = ttk.Spinbox(f_tol, from_=0, to=120, textvariable=vars['var_tolerans_dk'], width=5)
    sb_tol.pack(side="left", padx=5)
    enable_mouse_wheel(sb_tol)

    # --- BAĞLANTI HATASI UYARISI (Tab 1) ---
    f_conn = ttk.LabelFrame(tab_alarm_saat, text=" Bağlantı Hatası Uyarısı ", padding=10)
    f_conn.pack(fill="x", pady=(0, 10))
    
    ttk.Label(f_conn, text="Tekrar Sayısı:").pack(side="left")
    sb_conn_rep = ttk.Spinbox(f_conn, from_=1, to=10, textvariable=vars['var_baglanti_hata_tekrar'], width=3)
    sb_conn_rep.pack(side="left", padx=5)
    enable_mouse_wheel(sb_conn_rep)
    
    ttk.Label(f_conn, text="Aralık (dk):").pack(side="left", padx=(10, 0))
    sb_conn_int = ttk.Spinbox(f_conn, from_=1, to=60, textvariable=vars['var_baglanti_hata_aralik'], width=3)
    sb_conn_int.pack(side="left", padx=5)
    enable_mouse_wheel(sb_conn_int)

    # --- E-POSTA AYARLARI (Tab 1) ---
    f_email = ttk.LabelFrame(tab_alarm_saat, text=" E-posta Bildirim Ayarları ", padding=10)
    f_email.pack(fill="x", pady=(0, 10))
    
    ttk.Checkbutton(f_email, text="Eksik Veri Durumunda E-posta Gönder", variable=vars['var_email_aktif']).grid(row=0, column=0, columnspan=2, sticky="w", pady=5)
    
    ttk.Label(f_email, text="SMTP Sunucu:").grid(row=1, column=0, sticky="w")
    ttk.Entry(f_email, textvariable=vars['var_email_smtp'], width=20).grid(row=1, column=1, sticky="w", padx=5)
    
    ttk.Label(f_email, text="Port:").grid(row=1, column=2, sticky="w")
    ttk.Entry(f_email, textvariable=vars['var_email_port'], width=5).grid(row=1, column=3, sticky="w", padx=5)
    
    ttk.Label(f_email, text="Gönderen Email:").grid(row=2, column=0, sticky="w")
    ttk.Entry(f_email, textvariable=vars['var_email_gonderen'], width=30).grid(row=2, column=1, columnspan=3, sticky="w", padx=5)
    
    ttk.Label(f_email, text="Şifre (App Pw):").grid(row=3, column=0, sticky="w")
    ttk.Entry(f_email, textvariable=vars['var_email_sifre'], width=30, show="*").grid(row=3, column=1, columnspan=3, sticky="w", padx=5)
    
    ttk.Label(f_email, text="Alıcı Email (Virgülle ayırın):").grid(row=4, column=0, sticky="w")
    ttk.Entry(f_email, textvariable=vars['var_email_alici'], width=30).grid(row=4, column=1, columnspan=3, sticky="w", padx=5)

    # --- MANUEL ALARM (Tab 1) ---
    f_man = ttk.LabelFrame(tab_alarm_saat, text=" Manuel Alarm Kur ", padding=10)
    f_man.pack(fill="x", pady=(0, 10))
    
    f_man_inner = ttk.Frame(f_man)
    f_man_inner.pack(fill="x")
    ttk.Entry(f_man_inner, textvariable=vars['var_manuel_saat'], width=6, font=("Consolas", 10)).pack(side="left", padx=2)
    ttk.Entry(f_man_inner, textvariable=vars['var_manuel_mesaj'], width=20).pack(side="left", padx=2)
    ttk.Button(f_man_inner, text="KUR", command=lambda: vars['var_manuel_alarm_aktif'].set(True), width=5, style="Modern.TButton").pack(side="left", padx=2)
    ttk.Button(f_man_inner, text="SİL", command=lambda: vars['var_manuel_alarm_aktif'].set(False), width=5, style="Modern.TButton").pack(side="left", padx=2)

    # --- BİLGİ BUTONU (Tab 1) ---
    def show_alarm_schedule():
        info_win = tk.Toplevel(parent)
        info_win.title("Alarm Zamanlama ve Detay Bilgisi")
        info_win.geometry("700x600")
        
        txt = tk.Text(info_win, font=("Consolas", 10), padx=10, pady=10, bg="#ECEFF1")
        txt.pack(fill="both", expand=True)
        
        txt.tag_config("header", font=("Segoe UI", 11, "bold"), foreground="#2E7D32", background="#C8E6C9")
        txt.tag_config("bold", font=("Consolas", 10, "bold"))
        txt.tag_config("active", foreground="#2E7D32", font=("Consolas", 10, "bold"))
        txt.tag_config("passive", foreground="#B0BEC5")
        
        def refresh_content():
            txt.config(state="normal")
            txt.delete("1.0", "end")
            
            def add_section(title):
                txt.insert("end", f"\n {title} \n", "header")
                txt.insert("end", "-"*70 + "\n")

            # 1. RASAT HATIRLATICI ALARMLAR (DÜZENLİ)
            add_section("1. RASAT HATIRLATICI ALARMLAR (DÜZENLİ)")
            txt.insert("end", "Bu alarmlar şarta bağlı değildir. Belirlenen saatte personeli uyarır.\n\n")
            
            reminders = [
                ("METAR HAZIRLIK", 'var_remind_metar_aktif', 'var_remind_metar_start_h', 'var_remind_metar_period', 'var_remind_metar_min'),
                ("SİNOPTİK HAZIRLIK", 'var_remind_synop_aktif', 'var_remind_synop_start_h', 'var_remind_synop_period', 'var_remind_synop_min'),
                ("TAF HAZIRLIK", 'var_remind_taf_aktif', 'var_remind_taf_start_h', 'var_remind_taf_period', 'var_remind_taf_min')
            ]

            for name, v_act, v_start, v_period, v_min in reminders:
                active = vars[v_act].get()
                status_tag = "active" if active else "passive"
                status_text = "AKTİF" if active else "PASİF"
                
                txt.insert("end", f"{name:<20}: ", "bold")
                txt.insert("end", f"{status_text}\n", status_tag)
                
                if active:
                    start_h = vars[v_start].get()
                    period = vars[v_period].get()
                    minute = vars[v_min].get()
                    txt.insert("end", f"   • Zaman     : {start_h} itibarıyla her {period} saatte bir, {minute} geçe.\n")
                    txt.insert("end", f"   • Anons     : 'LÜTFEN [SAAT] [TÜR] YAPIN' (Örn: LÜTFEN 13 50 METAR YAPIN)\n")
                txt.insert("end", "\n")

            # 2. TETİKLİ ALARMLAR (EKSİK VERİ KONTROLÜ)
            add_section("2. ŞARTA BAĞLI RASAT İKAZ ALARMI")
            txt.insert("end", "Rasat periyotunda belirtilen eşik değerlerde gelmeyen rasatlar tespit ettiğinde çalar.\n")
            txt.insert("end", "Örn: 1. ikaz metarda 53 geçe, sonra her 60 sn veri gelip gelmediğine göre 2. ikaz çalar.\n\n")
            
            triggered_alarms = [
                ("Eksik METAR", 'var_metar_alarm_aktif', 'var_metar_alarm_start_hour', 'var_metar_alarm_trigger_min', 'var_alarm_freq_metar', 'var_metar_alarm_period', 'var_metar_alarm_repeat', 'var_denetim_metar_p1_end'),
                ("Eksik TAF", 'var_taf_alarm_aktif', 'var_taf_alarm_start_hour', 'var_taf_alarm_trigger_min', 'var_alarm_freq_taf', 'var_taf_alarm_period', 'var_taf_alarm_repeat', 'var_denetim_taf_end'),
                ("Eksik SİNOPTİK", 'var_sinoptik_alarm_aktif', 'var_sinoptik_alarm_start_hour', 'var_synop_alarm_trigger_min', 'var_alarm_freq_synop', 'var_synop_alarm_period', 'var_synop_alarm_repeat', 'var_denetim_synop_end'),
            ]
            
            ceza_aktif = vars.get('var_denetim_gec_gelen_alarm_aktif', tk.BooleanVar(value=True)).get()
            def get_c_val(key):
                return vars.get(key, tk.IntVar(value=3)).get()

            for name, v_act, v_start, v_trig, v_freq, v_period, v_repeat, v_end_min in triggered_alarms:
                # Check if var exists to prevent error if key missing
                if v_start not in vars: continue 

                active = vars[v_act].get()
                status_tag = "active" if active else "passive"
                status_text = "AKTİF" if active else "PASİF"
                
                txt.insert("end", f"{name:<20}: ", "bold")
                txt.insert("end", f"{status_text}\n", status_tag)
                
                if active:
                    start_h = vars[v_start].get()
                    trig_min = vars[v_trig].get()
                    freq = vars[v_freq].get()
                    period = vars[v_period].get()
                    repeat = vars[v_repeat].get()
                    end_min = vars[v_end_min].get() if v_end_min in vars else 0
                    ceza_start = (end_min + 1) % 60
                    
                    desc = f"{start_h} itibarıyla her {period} saatte bir, {trig_min} geçe kontrol edilir."
                    if "METAR" in name:
                        desc += f"\n      -> Örn: 09:{trig_min} itibarıyla 09:50 METAR'ı gelmemişse alarm çalar."
                        anons_orn = "DİKKAT 0950 METAR GELMEDİ"
                        ceza_orn = "0950 METAR EKSİK VEYA GEÇ GÖNDERİLMİŞ KONTROL EDİN"
                    elif "SİNOPTİK" in name:
                        desc += f"\n      -> Örn: 09:{trig_min} itibarıyla 09:00 SİNOPTİK gelmemişse alarm çalar."
                        anons_orn = "DİKKAT 0900 SİNOPTİK GELMEDİ"
                        ceza_orn = "0900 SİNOPTİK EKSİK VEYA GEÇ GÖNDERİLMİŞ KONTROL EDİN"
                    elif "TAF" in name:
                        desc += f"\n      -> Örn: 01:{trig_min} itibarıyla 01:40 TAF gelmemişse alarm çalar."
                        anons_orn = "DİKKAT 0140 TAF GELMEDİ"
                        ceza_orn = "0140 TAF EKSİK VEYA GEÇ GÖNDERİLMİŞ KONTROL EDİN"
                    
                    txt.insert("end", f"   • Tetikleme : {desc}\n")
                    txt.insert("end", f"   • Sıklık    : {freq} saniyede bir tekrar eder.\n")
                    txt.insert("end", f"   • Tekrar    : {repeat} kez tekrarlanır (Cezadan önce).\n")
                    txt.insert("end", f"   • Anons     : '{anons_orn}'\n")
                    
                    if ceza_aktif:
                        if "METAR" in name:
                            c_aralik = get_c_val('var_ceza_aralik_metar')
                            c_tekrar = get_c_val('var_ceza_tekrar_metar')
                        elif "SİNOPTİK" in name:
                            c_aralik = get_c_val('var_ceza_aralik_synop')
                            c_tekrar = get_c_val('var_ceza_tekrar_synop')
                        else:
                            c_aralik = get_c_val('var_ceza_aralik_taf')
                            c_tekrar = get_c_val('var_ceza_tekrar_taf')
                            
                        txt.insert("end", f"   • Ceza      : {ceza_start:02d} geçe itibarıyla.\n")
                        txt.insert("end", f"                 Sıklık: {c_aralik} dk, {c_tekrar} kez tekrar eder.\n")
                        txt.insert("end", f"                 Bilgi : Ceza tekrar sayısı ekranda (x/{c_tekrar}) şeklinde gösterilir.\n")
                        txt.insert("end", f"                 Anons : '{ceza_orn}' (Ceza)\n")
                        txt.insert("end", f"                 Log   : '[ALARM] GEÇ GELEN CEZA ALARMI (1/{c_tekrar}): ...'\n")
                    else:
                        txt.insert("end", f"   • Ceza      : PASİF (Denetim ayarlarından açılabilir)\n")
                txt.insert("end", "\n")

            # 3. ŞARTA BAĞLI BİLGİ ANONSU
            add_section("3. ŞARTA BAĞLI BİLGİ ANONSU")
            txt.insert("end", "Sisteme yeni bir veri düştüğünde sesli olarak bildirir.\n")
            txt.insert("end", "Örn: '1350 TAF SİSTEME DÜŞTÜ'\n\n")
            
            anons_active = vars['var_anons_aktif'].get()
            status_tag = "active" if anons_active else "passive"
            status_text = "AKTİF" if anons_active else "PASİF"
            
            txt.insert("end", f"{'VERİ ANONSU':<20}: ", "bold")
            txt.insert("end", f"{status_text}\n", status_tag)
            if anons_active:
                txt.insert("end", "   • Çalışma   : Yeni METAR, TAF veya SİNOPTİK geldiğinde otomatik okunur.\n")
                txt.insert("end", "   • Anons     : '[SAAT] [TÜR] SİSTEME DÜŞTÜ'\n")
            txt.insert("end", "\n")

            # 4. 3. ALARMA BAĞLI PERSONEL TEBRİK
            add_section("4. 3. ALARMA BAĞLI PERSONEL TEBRİK")
            txt.insert("end", "Yeni veri geldiğinde (3. Alarm), gönderen personeli ismiyle tebrik eder.\n")
            
            tebrik_active = vars['var_tebrik_aktif'].get()
            status_tag = "active" if tebrik_active else "passive"
            status_text = "AKTİF" if tebrik_active else "PASİF"
            
            txt.insert("end", f"{'PERSONEL TEBRİK':<20}: ", "bold")
            txt.insert("end", f"{status_text}\n", status_tag)
            if tebrik_active:
                txt.insert("end", "   • Çalışma   : Gelen verinin KULL ID'si listede varsa ismi okur.\n")
                txt.insert("end", "   • Bağımlılık: 3. Alarm (Bilgi Anonsu) ile birlikte çalışır.\n")
                txt.insert("end", "   • Anons     : '... TEBRİKLER [İSİM]'\n")
            txt.insert("end", "\n")

            # 2. DİĞER ALARMLAR
            add_section("DİĞER UYARILAR")
            
            # Trend Uyum
            act_trend = vars['var_trend_alarm_aktif'].get()
            txt.insert("end", f"{'UYUMSUZLUK':<15}: ", "bold")
            txt.insert("end", f"{'AKTİF' if act_trend else 'PASİF'}\n", "active" if act_trend else "passive")
            if act_trend:
                desc = "Her yeni rasat geldiğinde TAF ile karşılaştırılır.\n      -> Limit dışı fark (Rüzgar, Görüş, Tavan) varsa alarm çalar."
                txt.insert("end", f"   • Çalışma   : {desc}\n")
                txt.insert("end", f"   • Sıklık    : {vars['var_alarm_freq_incompatible'].get()} saniyede bir (Uyumsuzluk sürdükçe)\n")
                rep_val = vars.get('var_incompatible_alarm_repeat', tk.IntVar(value=3)).get()
                txt.insert("end", f"   • Tekrar    : {rep_val} kez tekrarlanır.\n")
                txt.insert("end", "   • Anons     : 'DİKKAT. [SAAT] [TÜR] UYUMSUZ.'\n")
                txt.insert("end", "\n")
                
            # Saat Başı
            act_hourly = vars['var_saat_basi_aktif'].get()
            txt.insert("end", f"{'SAAT BAŞI':<10}: ", "bold")
            txt.insert("end", f"{'SAAT BAŞI':<15}: ", "bold")
            txt.insert("end", f"{'AKTİF' if act_hourly else 'PASİF'}\n", "active" if act_hourly else "passive")
            if act_hourly:
                txt.insert("end", "   • Tetikleme : Her saat başı (XX:00)\n")
                txt.insert("end", "   • Anons     : 'SAAT [XX]'\n")
                txt.insert("end", "\n")

            # 3. ÖZEL ALARMLAR
            add_section("ÖZEL DİNAMİK ALARMLAR")
            has_special = False
            for i in range(5):
                if vars[f'var_sa_active_{i}'].get():
                    has_special = True
                    time_val = vars[f'var_sa_time_{i}'].get()
                    freq_val = vars[f'var_sa_freq_{i}'].get()
                    msg_val = vars[f'var_sa_msg_{i}'].get()
                    rep_val = vars[f'var_sa_repeat_{i}'].get()
                    
                    txt.insert("end", f"ALARM {i+1}:\n", "bold")
                    txt.insert("end", f"   • Zaman     : {time_val} UTC\n")
                    txt.insert("end", f"   • Periyot   : {freq_val}\n")
                    if rep_val > 0:
                        txt.insert("end", f"   • Tekrar    : {rep_val} dakikada bir\n")
                    else:
                        txt.insert("end", f"   • Tekrar    : Yok (Tek seferlik)\n")
                    txt.insert("end", f"   • Mesaj     : {msg_val}\n")
                    txt.insert("end", f"   • Anons     : '{msg_val}' (Girilen metin okunur)\n")
            
            if not has_special:
                txt.insert("end", "Aktif özel alarm bulunmamaktadır.\n")

            # 4. SES AYARLARI
            add_section("SES VE ÇALMA BİLGİSİ")
            if vars['var_anons_aktif'].get():
                txt.insert("end", "• Mod: GOOGLE SESLİ ANONS (TTS)\n", "bold")
                txt.insert("end", f"• Hız: {vars['var_konusma_hizi'].get()}\n")
                txt.insert("end", "• Süre: Mesaj uzunluğuna göre değişir.\n")
            else:
                txt.insert("end", "• Mod: ALARM SESİ DOSYASI\n", "bold")
                path = vars['var_ozel_ses_yolu'].get()
                txt.insert("end", f"• Dosya: {path if path else 'Varsayılan Sistem Sesi'}\n")
                txt.insert("end", "• Süre: Dosya uzunluğu kadar.\n")

            # 5. 24 SAATLİK ALARM AKIŞI (YOLCULUK)
            add_section("24 SAATLİK ALARM AKIŞI (YOLCULUK)")
            
            now_utc = datetime.now(timezone.utc)
            txt.insert("end", f"Şu anki zaman (UTC): {now_utc.strftime('%H:%M')}\n")
            txt.insert("end", "Sanki bir yolculuktasınız... İşte duraklar:\n\n")
            
            found_future = False
            next_stop_found = False
            
            def parse_t(val):
                try:
                    if ":" in str(val): return map(int, str(val).split(":"))
                    return int(val), 0
                except: return 0, 0

            # 24 saat = 1440 dakika
            for i in range(1, 1441):
                future = now_utc + timedelta(minutes=i)
                f_h = future.hour
                f_m = future.minute
                
                events = []
                
                # METAR
                if vars['var_remind_metar_aktif'].get():
                    s, m_s = parse_t(vars['var_remind_metar_start_h'].get())
                    p = vars['var_remind_metar_period'].get()
                    if p > 0 and (f_h - s) % p == 0 and f_m == m_s:
                        events.append("METAR HAZIRLIK")

                # SİNOPTİK
                if vars['var_remind_synop_aktif'].get():
                    s, m_s = parse_t(vars['var_remind_synop_start_h'].get())
                    p = vars['var_remind_synop_period'].get()
                    if p > 0 and (f_h - s) % p == 0 and f_m == m_s:
                        events.append("SİNOPTİK HAZIRLIK")

                # TAF
                if vars['var_remind_taf_aktif'].get():
                    s, m_s = parse_t(vars['var_remind_taf_start_h'].get())
                    p = vars['var_remind_taf_period'].get()
                    if p > 0 and (f_h - s) % p == 0 and f_m == m_s:
                        events.append("TAF HAZIRLIK")
                
                # Saat Başı
                if vars['var_saat_basi_aktif'].get() and f_m == 0:
                    events.append("SAAT BAŞI")
                
                # Özel Alarmlar
                for k in range(5):
                    if vars[f'var_sa_active_{k}'].get():
                        t_str = vars[f'var_sa_time_{k}'].get()
                        try:
                            th, tm = map(int, t_str.split(':'))
                            if f_h == th and f_m == tm:
                                events.append(f"ÖZEL ALARM {k+1}")
                        except: pass

                if events:
                    found_future = True
                    time_str = future.strftime('%H:%M')
                    
                    if not next_stop_found:
                        txt.insert("end", f"🚌 SONRAKİ DURAK: {time_str} UTC\n", "header")
                        txt.insert("end", f"   -> {', '.join(events)}\n\n", "active")
                        txt.insert("end", "--- Diğer Duraklar ---\n")
                        next_stop_found = True
                    else:
                        txt.insert("end", f"{time_str} UTC -> {', '.join(events)}\n")
            
            if not found_future:
                txt.insert("end", "Önümüzdeki 24 saat içinde planlanmış alarm bulunmamaktadır.\n")
                
            txt.config(state="disabled")

        nonlocal refresh_info_window_callback
        refresh_info_window_callback = refresh_content

        # Clear callback when window closes
        def on_close():
            nonlocal refresh_info_window_callback
            refresh_info_window_callback = None
            info_win.destroy()
        
        info_win.protocol("WM_DELETE_WINDOW", on_close)

        # Initial population
        refresh_content()

    ttk.Button(tab_alarm_saat, text="ℹ️ ALARM ZAMANLAMA BİLGİSİ", command=show_alarm_schedule, style="Modern.TButton").pack(fill="x", pady=10)

    # --- ÖZEL DİNAMİK ALARMLAR (Tab 1) ---
    f_special = ttk.LabelFrame(tab_alarm_saat, text=" Özel Dinamik Alarmlar ", padding=10)
    f_special.pack(fill="x", pady=(0, 10))
    
    # Başlıklar
    ttk.Label(f_special, text="Aktif", font=("Segoe UI", 8, "bold")).grid(row=0, column=0, padx=5)
    ttk.Label(f_special, text="Periyot", font=("Segoe UI", 8, "bold")).grid(row=0, column=1, padx=5)
    ttk.Label(f_special, text="Tarih (Ops)", font=("Segoe UI", 8, "bold")).grid(row=0, column=2, padx=5)
    ttk.Label(f_special, text="Saat (UTC)", font=("Segoe UI", 8, "bold")).grid(row=0, column=3, padx=5)
    ttk.Label(f_special, text="Sıklık (dk)", font=("Segoe UI", 8, "bold")).grid(row=0, column=4, padx=5)
    ttk.Label(f_special, text="Tekrar", font=("Segoe UI", 8, "bold")).grid(row=0, column=5, padx=5)
    
    freq_values = ["Her Gün", "Hafta İçi Her Gün", "Hafta Sonu", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar", "Tek Seferlik", "Her Ayın 1'i", "Her Ayın 15'i"]
    
    def get_special_alarm_tip(idx):
        if not vars[f'var_sa_active_{idx}'].get(): return "Alarm pasif."
        t_str = vars[f'var_sa_time_{idx}'].get()
        freq = vars[f'var_sa_freq_{idx}'].get()
        try:
            now = datetime.now(timezone.utc)
            target_h, target_m = map(int, t_str.split(':'))
            target = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
            
            days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
            
            if freq == "Her Gün":
                if target <= now: target += timedelta(days=1)
            elif freq == "Hafta İçi Her Gün":
                if target <= now or target.weekday() >= 5:
                    target += timedelta(days=1)
                    while target.weekday() >= 5:
                        target += timedelta(days=1)
            elif freq == "Hafta Sonu":
                if target <= now or target.weekday() < 5:
                    target += timedelta(days=1)
                    while target.weekday() < 5:
                        target += timedelta(days=1)
            elif freq == "Tek Seferlik":
                d_str = vars[f'var_sa_date_{idx}'].get()
                target = datetime.strptime(f"{d_str} {t_str}", "%d.%m.%Y %H:%M").replace(tzinfo=timezone.utc)
                if target <= now: return "Süre geçti (Tek Seferlik)"
            elif freq in days:
                current_day_idx = now.weekday()
                target_day_idx = days.index(freq)
                days_ahead = (target_day_idx - current_day_idx + 7) % 7
                if days_ahead == 0 and target <= now: days_ahead = 7
                target += timedelta(days=days_ahead)
            elif freq == "Her Ayın 1'i":
                target = now.replace(day=1, hour=target_h, minute=target_m, second=0, microsecond=0)
                if target <= now:
                    if target.month == 12:
                        target = target.replace(year=target.year + 1, month=1)
                    else:
                        target = target.replace(month=target.month + 1)
            elif freq == "Her Ayın 15'i":
                target = now.replace(day=15, hour=target_h, minute=target_m, second=0, microsecond=0)
                if target <= now:
                    if target.month == 12:
                        target = target.replace(year=target.year + 1, month=1)
                    else:
                        target = target.replace(month=target.month + 1)
            
            diff = target - now
            total_seconds = int(diff.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return f"Sıradaki: {target.strftime('%d.%m %H:%M')} UTC\nKalan: {hours}sa {minutes}dk"
        except: return "Zaman hesaplanamadı."

    for i in range(5):
        r = i + 1
        chk = ttk.Checkbutton(f_special, variable=vars[f'var_sa_active_{i}'])
        chk.grid(row=r, column=0, padx=5, pady=2)
        create_tooltip(chk, lambda i=i: get_special_alarm_tip(i))
        
        ttk.Combobox(f_special, textvariable=vars[f'var_sa_freq_{i}'], values=freq_values, width=12, state="readonly").grid(row=r, column=1, padx=5, pady=2)
        ttk.Entry(f_special, textvariable=vars[f'var_sa_date_{i}'], width=12).grid(row=r, column=2, padx=5, pady=2)
        ent_time = ttk.Entry(f_special, textvariable=vars[f'var_sa_time_{i}'], width=8)
        ent_time.grid(row=r, column=3, padx=5, pady=2)
        create_tooltip(ent_time, lambda i=i: get_special_alarm_tip(i))
        
        sb_rep = ttk.Spinbox(f_special, from_=0, to=1440, textvariable=vars[f'var_sa_repeat_{i}'], width=5)
        sb_rep.grid(row=r, column=4, padx=5, pady=2)
        enable_mouse_wheel(sb_rep)
        
        sb_cnt = ttk.Spinbox(f_special, from_=0, to=10, textvariable=vars[f'var_sa_count_{i}'], width=3)
        sb_cnt.grid(row=r, column=5, padx=5, pady=2)
        enable_mouse_wheel(sb_cnt)
        
        ttk.Entry(f_special, textvariable=vars[f'var_sa_msg_{i}'], width=40).grid(row=r, column=6, padx=5, pady=2, sticky="w")
        
        ttk.Button(f_special, text="Test", width=5, command=lambda idx=i: callbacks.get('speak_text', lambda m: None)(vars[f'var_sa_msg_{idx}'].get()), style="Small.TButton").grid(row=r, column=7, padx=5, pady=2)

    # --- PERSONEL TEBRİK SİSTEMİ (Tab 2) ---
    f_kull = ttk.LabelFrame(tab_istasyon, text=" Personel Tebrik Sistemi (KULL ID) ", padding=10)
    f_kull.pack(fill="x", pady=(0, 10))
    
    ttk.Checkbutton(f_kull, text="Personel Tebrik Seslendirmesini Etkinleştir", variable=vars['var_tebrik_aktif']).grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=5)
    
    def test_personel_tebrik():
        for i in range(20):
            nm = vars[f'var_kull_name_{i}'].get()
            if nm:
                callbacks.get('speak_text', lambda m: None)(f"Rasat sisteme düştü. Tebrikler {nm}.")
                return
        messagebox.showinfo("Bilgi", "Test için listede en az bir isim olmalıdır.")

    ttk.Button(f_kull, text="🔊 Örnek Test", command=test_personel_tebrik, style="Modern.TButton").grid(row=0, column=2, columnspan=2, sticky="e", padx=5)

    ttk.Label(f_kull, text="KULL ID (Örn: 20038)", font=("Segoe UI", 8, "bold")).grid(row=1, column=0, padx=5)
    ttk.Label(f_kull, text="İsim Soyisim (Okunacak)", font=("Segoe UI", 8, "bold")).grid(row=1, column=1, padx=5)
    ttk.Label(f_kull, text="KULL ID", font=("Segoe UI", 8, "bold")).grid(row=1, column=2, padx=5)
    ttk.Label(f_kull, text="İsim Soyisim", font=("Segoe UI", 8, "bold")).grid(row=1, column=3, padx=5)
    
    for i in range(20):
        r = (i % 10) + 2
        c_offset = 0 if i < 10 else 2
        ttk.Entry(f_kull, textvariable=vars[f'var_kull_id_{i}'], width=15).grid(row=r, column=0+c_offset, padx=5, pady=2)
        ttk.Entry(f_kull, textvariable=vars[f'var_kull_name_{i}'], width=30).grid(row=r, column=1+c_offset, padx=5, pady=2)

    # ================= TAB 3: ARAYÜZ & GÖRÜNÜM İÇERİĞİ =================

    # --- TEMA AYARLARI ---
    f_tema = ttk.LabelFrame(tab_arayuz, text=" Görünüm ve Tema ", padding=10)
    f_tema.pack(fill="x", pady=(0, 10))
    
    ttk.Label(f_tema, text="Uygulama Teması:").pack(side="left", padx=5)
    ttk.Combobox(f_tema, textvariable=vars['var_tema_secimi'], values=["Koyu Mod", "Açık Mod", "Sistem"], state="readonly", width=15).pack(side="left", padx=5)
    
    # --- METİN VE TABLO ---
    f_font = ttk.LabelFrame(tab_arayuz, text=" Metin ve Tablo Ayarları ", padding=10)
    f_font.pack(fill="x", pady=(0, 10))
    
    ttk.Label(f_font, text="Genel Yazı Boyutu:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    sb_font = ttk.Spinbox(f_font, from_=8, to=16, textvariable=vars['var_yazi_boyutu'], width=5)
    sb_font.grid(row=0, column=1, sticky="w", padx=5)
    enable_mouse_wheel(sb_font)

    ttk.Label(f_font, text="Yazı Kalınlığı:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
    ttk.Combobox(f_font, textvariable=vars['var_yazi_kalinligi'], values=["normal", "bold"], state="readonly", width=8).grid(row=0, column=3, sticky="w", padx=5)
    
    ttk.Label(f_font, text="Yazı Tipi:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    font_families = sorted([f for f in font.families() if not f.startswith('@')])
    cb_family = ttk.Combobox(f_font, textvariable=vars['var_yazi_tipi'], values=font_families, state="readonly", width=25)
    cb_family.grid(row=1, column=1, columnspan=3, sticky="w", padx=5)
    
    ttk.Label(f_font, text="Tablo Satır Yüksekliği:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    sb_row = ttk.Spinbox(f_font, from_=20, to=50, textvariable=vars['var_satir_yuksekligi'], width=5)
    sb_row.grid(row=2, column=1, sticky="w", padx=5)
    enable_mouse_wheel(sb_row)
    
    ttk.Label(f_font, text="Sütun Genişlik Payı:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
    sb_pad = ttk.Spinbox(f_font, from_=5, to=100, textvariable=vars['var_sutun_payi'], width=5)
    sb_pad.grid(row=3, column=1, sticky="w", padx=5)
    enable_mouse_wheel(sb_pad)
    
    ttk.Label(f_font, text="Tablo Arka Planı:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
    ttk.Entry(f_font, textvariable=vars['var_tablo_arkaplan'], width=10).grid(row=4, column=1, sticky="w", padx=5)

    # Önizleme 1
    lbl_prev_bg = tk.Label(f_font, width=4, bg=vars['var_tablo_arkaplan'].get(), relief="solid", borderwidth=1)
    lbl_prev_bg.grid(row=4, column=3, padx=5)
    vars['var_tablo_arkaplan'].trace_add("write", lambda *a: lbl_prev_bg.config(bg=vars['var_tablo_arkaplan'].get()) if vars['var_tablo_arkaplan'].get() else None)
    
    def pick_table_bg():
        c = colorchooser.askcolor(initialcolor=vars['var_tablo_arkaplan'].get(), title="Tablo Arka Plan Rengi")[1]
        if c: vars['var_tablo_arkaplan'].set(c)
        
    ttk.Button(f_font, text="🎨 Seç", command=pick_table_bg, width=6, style="Modern.TButton").grid(row=4, column=2, sticky="w", padx=2)
    
    ttk.Label(f_font, text="Tablo İkincil Renk (Zebra):").grid(row=5, column=0, sticky="w", padx=5, pady=5)
    ttk.Entry(f_font, textvariable=vars['var_tablo_zebra2'], width=10).grid(row=5, column=1, sticky="w", padx=5)

    # Önizleme 2
    lbl_prev_zebra = tk.Label(f_font, width=4, bg=vars['var_tablo_zebra2'].get(), relief="solid", borderwidth=1)
    lbl_prev_zebra.grid(row=5, column=3, padx=5)
    vars['var_tablo_zebra2'].trace_add("write", lambda *a: lbl_prev_zebra.config(bg=vars['var_tablo_zebra2'].get()) if vars['var_tablo_zebra2'].get() else None)
    
    def pick_zebra2_bg():
        c = colorchooser.askcolor(initialcolor=vars['var_tablo_zebra2'].get(), title="Tablo İkincil Renk")[1]
        if c: vars['var_tablo_zebra2'].set(c)
        
    ttk.Button(f_font, text="🎨 Seç", command=pick_zebra2_bg, width=6, style="Modern.TButton").grid(row=5, column=2, sticky="w", padx=2)
    
    ttk.Label(f_font, text="Seçili Satır Rengi:").grid(row=6, column=0, sticky="w", padx=5, pady=5)
    ttk.Entry(f_font, textvariable=vars['var_tablo_secili_renk'], width=10).grid(row=6, column=1, sticky="w", padx=5)

    # Önizleme 3
    lbl_prev_sel = tk.Label(f_font, width=4, bg=vars['var_tablo_secili_renk'].get(), relief="solid", borderwidth=1)
    lbl_prev_sel.grid(row=6, column=3, padx=5)
    vars['var_tablo_secili_renk'].trace_add("write", lambda *a: lbl_prev_sel.config(bg=vars['var_tablo_secili_renk'].get()) if vars['var_tablo_secili_renk'].get() else None)
    
    def pick_select_bg():
        c = colorchooser.askcolor(initialcolor=vars['var_tablo_secili_renk'].get(), title="Seçili Satır Rengi")[1]
        if c: vars['var_tablo_secili_renk'].set(c)
        
    ttk.Button(f_font, text="🎨 Seç", command=pick_select_bg, width=6, style="Modern.TButton").grid(row=6, column=2, sticky="w", padx=2)
    
    # --- TÜR BAZLI STİL AYARLARI ---
    f_styles = ttk.LabelFrame(tab_arayuz, text=" Satır Stilleri (METAR / TAF / SİNOPTİK / ESKİ / UYUMSUZ vb.) ", padding=10)
    f_styles.pack(fill="x", pady=(0, 10))

    ttk.Label(f_styles, text="Türü", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=5, pady=2)
    ttk.Label(f_styles, text="Yazı Rengi", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, padx=5, pady=2)
    ttk.Label(f_styles, text="Arka Plan", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, padx=5, pady=2)
    ttk.Label(f_styles, text="Yazı Tipi", font=("Segoe UI", 9, "bold")).grid(row=0, column=3, padx=5, pady=2)
    ttk.Label(f_styles, text="Boyut", font=("Segoe UI", 9, "bold")).grid(row=0, column=4, padx=5, pady=2)
    ttk.Label(f_styles, text="Kalın", font=("Segoe UI", 9, "bold")).grid(row=0, column=5, padx=5, pady=2)

    def pick_color(var, title):
        c = colorchooser.askcolor(initialcolor=var.get() if var.get() else "#FFFFFF", title=title)[1]
        if c: var.set(c)

    for i, (t_key, t_name) in enumerate([('metar', 'METAR'), ('taf', 'TAF'), ('synop', 'SİNOPTİK'), ('other', 'HARİCİ'), ('eski', 'ESKİ/DÜZELTİLEN'), ('uyumsuz', 'UYUMSUZ'), ('re_hatasi', 'RE/GEÇMİŞ HATA'), ('gec', 'GEÇ GELEN'), ('cor_amd', 'AMD/COR TAF')]):
        r = i + 1
        ttk.Label(f_styles, text=t_name).grid(row=r, column=0, sticky="w", padx=5, pady=2)
        
        # FG
        f_fg = ttk.Frame(f_styles)
        f_fg.grid(row=r, column=1, padx=5, pady=2)
        lbl_fg = tk.Label(f_fg, width=2, bg=vars[f'var_style_{t_key}_fg'].get() or "#FFFFFF", relief="solid", borderwidth=1)
        lbl_fg.pack(side="left")
        ttk.Button(f_fg, text="🎨", width=2, command=lambda v=vars[f'var_style_{t_key}_fg'], n=t_name: pick_color(v, f"{n} Yazı Rengi"), style="Small.TButton").pack(side="left", padx=2)
        ttk.Button(f_fg, text="X", width=2, command=lambda v=vars[f'var_style_{t_key}_fg']: v.set(""), style="Small.TButton").pack(side="left", padx=2)
        vars[f'var_style_{t_key}_fg'].trace_add("write", lambda *a, v=vars[f'var_style_{t_key}_fg'], l=lbl_fg: l.config(bg=v.get() if v.get() else "#FFFFFF"))
        
        # BG
        f_bg = ttk.Frame(f_styles)
        f_bg.grid(row=r, column=2, padx=5, pady=2)
        lbl_bg = tk.Label(f_bg, width=2, bg=vars[f'var_style_{t_key}_bg'].get() or "#FFFFFF", relief="solid", borderwidth=1)
        lbl_bg.pack(side="left")
        ttk.Button(f_bg, text="🎨", width=2, command=lambda v=vars[f'var_style_{t_key}_bg'], n=t_name: pick_color(v, f"{n} Arka Plan Rengi"), style="Small.TButton").pack(side="left", padx=2)
        ttk.Button(f_bg, text="X", width=2, command=lambda v=vars[f'var_style_{t_key}_bg']: v.set(""), style="Small.TButton").pack(side="left", padx=2)
        vars[f'var_style_{t_key}_bg'].trace_add("write", lambda *a, v=vars[f'var_style_{t_key}_bg'], l=lbl_bg: l.config(bg=v.get() if v.get() else "#FFFFFF"))

        # Font
        ttk.Combobox(f_styles, textvariable=vars[f'var_style_{t_key}_family'], values=font_families, state="readonly", width=15).grid(row=r, column=3, padx=5, pady=2)
        # Boyut
        sb_size = ttk.Spinbox(f_styles, from_=6, to=30, textvariable=vars[f'var_style_{t_key}_size'], width=4)
        sb_size.grid(row=r, column=4, padx=5, pady=2)
        enable_mouse_wheel(sb_size)
        # Bold
        ttk.Checkbutton(f_styles, variable=vars[f'var_style_{t_key}_bold']).grid(row=r, column=5, padx=5, pady=2)

    # --- KONSOL / LOG ---
    f_konsol = ttk.LabelFrame(tab_arayuz, text=" Konsol ve Log Yapısı ", padding=10)
    f_konsol.pack(fill="x", pady=(0, 10))
    
    ttk.Label(f_konsol, text="Konsol Arka Planı:").pack(side="left", padx=5)
    ttk.Entry(f_konsol, textvariable=vars['var_konsol_renk'], width=10).pack(side="left", padx=5)
    
    # Önizleme 5
    lbl_prev_cons = tk.Label(f_konsol, width=4, bg=vars['var_konsol_renk'].get(), relief="solid", borderwidth=1)
    lbl_prev_cons.pack(side="left", padx=5)
    vars['var_konsol_renk'].trace_add("write", lambda *a: lbl_prev_cons.config(bg=vars['var_konsol_renk'].get()) if vars['var_konsol_renk'].get() else None)

    def pick_console_bg():
        c = colorchooser.askcolor(initialcolor=vars['var_konsol_renk'].get(), title="Konsol Arka Plan Rengi")[1]
        if c: vars['var_konsol_renk'].set(c)

    ttk.Button(f_konsol, text="🎨", command=pick_console_bg, width=3, style="Small.TButton").pack(side="left", padx=2)

    def reset_colors():
        if messagebox.askyesno("Renkleri Sıfırla", "Renk ayarları varsayılan değerlere (Fabrika) dönecek. Emin misiniz?"):
            vars['var_konsol_renk'].set("#263238")
            vars['var_tablo_arkaplan'].set("#ffffff")
            vars['var_tablo_zebra2'].set("#eceff1")
            vars['var_tablo_secili_renk'].set("#1976D2")
            
    ttk.Button(f_konsol, text="🎨 Renkleri Sıfırla", command=reset_colors, style="Modern.TButton").pack(side="right", padx=5)

    # ================= TAB 4: DENETİM AYARLARI İÇERİĞİ =================
    
    # --- GENEL DENETİM AYARLARI ---
    f_genel_denetim = ttk.LabelFrame(tab_denetim, text=" Genel Denetim Ayarları ", padding=10)
    f_genel_denetim.pack(fill="x", pady=(0, 10))
    
    f_gd_inner = ttk.Frame(f_genel_denetim)
    f_gd_inner.pack(fill="x")
    
    ttk.Label(f_gd_inner, text="Geriye Dönük Eksik Veri Kontrolü (Saat):").pack(side="left")
    sb_eksik_saat = ttk.Spinbox(f_gd_inner, from_=1, to=24, textvariable=vars['var_eksik_veri_saat'], width=5)
    sb_eksik_saat.pack(side="left", padx=5)
    enable_mouse_wheel(sb_eksik_saat)

    # --- TREND ZAMAN KURALLARI (FM/TL) ---
    f_den_trend = ttk.LabelFrame(tab_denetim, text=" TREND Zaman Kuralları (FM/TL) ", padding=10)
    f_den_trend.pack(fill="x", pady=(0, 10))
    create_tooltip(f_den_trend, lambda: "BECMG/TEMPO başlangıç (FM) ve bitiş (TL) saatleri için zorunluluk sürelerini belirler.")
    
    ttk.Checkbutton(f_den_trend, text="TREND Zaman Kurallarını (FM/TL) Etkinleştir", variable=vars['var_trend_zaman_aktif']).pack(anchor="w", pady=(0, 5), padx=5)
    
    chk_kati = ttk.Checkbutton(f_den_trend, text="Katı ICAO Kurallarını Uygula (SHRA ve NOSIG Toleransını Kapat)", variable=vars['var_kati_icao_kurallari'])
    chk_kati.pack(anchor="w", pady=(0, 5), padx=5)
    create_tooltip(chk_kati, lambda: "Aktif olduğunda; NOSIG için olan 75dk toleransı ve SHRA gibi bazı hadiselerin yoksayılması İPTAL edilir.\nTamamen katı ICAO Annex 3 kuralları uygulanır.")

    f_fm_grid = ttk.Frame(f_den_trend)
    f_fm_grid.pack(fill="x", pady=2)
    ttk.Label(f_fm_grid, text="FM Başlangıç Alt Limit (Dk):", width=25).pack(side="left")
    sb_tr_min = ttk.Spinbox(f_fm_grid, from_=0, to=120, textvariable=vars.get('var_trend_min_sure', tk.IntVar(value=15)), width=4)
    sb_tr_min.pack(side="left", padx=5)
    enable_mouse_wheel(sb_tr_min)
    create_tooltip(sb_tr_min, lambda: "Bu sürenin altındayken FM kullanılamaz (Direkt yazılır).\nVarsayılan: 15")
    
    ttk.Label(f_fm_grid, text="FM Üst Limit (Dk):").pack(side="left", padx=(15, 0))
    sb_tr_max = ttk.Spinbox(f_fm_grid, from_=0, to=300, textvariable=vars.get('var_trend_max_sure', tk.IntVar(value=75)), width=4)
    sb_tr_max.pack(side="left", padx=5)
    enable_mouse_wheel(sb_tr_max)
    create_tooltip(sb_tr_max, lambda: "Bu süreye kadar FM kullanımı zorunludur.\nVarsayılan: 75")

    f_tl_grid = ttk.Frame(f_den_trend)
    f_tl_grid.pack(fill="x", pady=2)
    ttk.Label(f_tl_grid, text="TL Bitiş Alt Limit (Dk):", width=25).pack(side="left")
    sb_tl_min = ttk.Spinbox(f_tl_grid, from_=0, to=120, textvariable=vars.get('var_trend_tl_min_sure', tk.IntVar(value=15)), width=4)
    sb_tl_min.pack(side="left", padx=5)
    enable_mouse_wheel(sb_tl_min)
    create_tooltip(sb_tl_min, lambda: "Bu sürenin altındayken TL kullanılamaz (Direkt yazılır).\nVarsayılan: 15")

    ttk.Label(f_tl_grid, text="TL Üst Limit (Dk):").pack(side="left", padx=(15, 0))
    sb_tl_max = ttk.Spinbox(f_tl_grid, from_=0, to=300, textvariable=vars.get('var_trend_tl_max_sure', tk.IntVar(value=90)), width=4)
    sb_tl_max.pack(side="left", padx=5)
    enable_mouse_wheel(sb_tl_max)
    create_tooltip(sb_tl_max, lambda: "Bu süreye kadar TL kullanımı zorunludur.\nVarsayılan: 90")

    # --- METAR DENETİMİ ---
    f_den_metar = ttk.LabelFrame(tab_denetim, text=" METAR Denetimi (Geç Gelen Rasat) ", padding=10)
    f_den_metar.pack(fill="x", pady=(0, 10))
    create_tooltip(f_den_metar, lambda: "METAR'ların 'zamanında' gelip gelmediğini denetler.\n'Geç Gelen' filtresi bu ayarlara göre çalışır.")
    
    ttk.Checkbutton(f_den_metar, text="METAR Denetimini Etkinleştir", variable=vars['var_denetim_metar_aktif']).pack(anchor="w", pady=5)
    
    f_mp1 = ttk.Frame(f_den_metar)
    f_mp1.pack(fill="x", pady=2)
    lbl_metar_start = ttk.Label(f_mp1, text="Başlangıç Saati:")
    lbl_metar_start.pack(side="left")
    create_tooltip(lbl_metar_start, lambda: "METAR denetiminin hangi saatte başlayacağını belirtir.\nÖrn: 0 -> Her saat başı kontrol edilir.")
    ttk.Spinbox(f_mp1, from_=0, to=23, textvariable=vars['var_denetim_metar_start_hour'], width=3).pack(side="left", padx=5)
    lbl_metar_period = ttk.Label(f_mp1, text="Periyot (Saat):")
    lbl_metar_period.pack(side="left")
    create_tooltip(lbl_metar_period, lambda: "METAR denetiminin kaç saatte bir yapılacağını belirtir.\nÖrn: 1 -> Her saat kontrol edilir.")
    ttk.Spinbox(f_mp1, from_=1, to=24, textvariable=vars['var_denetim_metar_period'], width=3).pack(side="left", padx=5)
    
    f_mp2 = ttk.Frame(f_den_metar)
    f_mp2.pack(fill="x", pady=2)
    lbl_metar_ontime = ttk.Label(f_mp2, text="Zaman Aralığı (On Time):", width=20)
    lbl_metar_ontime.pack(side="left")
    create_tooltip(lbl_metar_ontime, lambda: "Bir METAR'ın 'zamanında' sayılması için kayıt saatinin (UTC)\nhangi dakikalar arasında olması gerektiğini belirtir.\nÖrn: 50-54 -> Rasat, saat XX:50 ile XX:54 arasında gelmelidir.")
    ttk.Label(f_mp2, text="Dakika Aralığı:").pack(side="left")
    ttk.Spinbox(f_mp2, from_=0, to=59, textvariable=vars['var_denetim_metar_p1_start'], width=3).pack(side="left", padx=5)
    ttk.Label(f_mp2, text="-").pack(side="left")
    ttk.Spinbox(f_mp2, from_=0, to=59, textvariable=vars['var_denetim_metar_p1_end'], width=3).pack(side="left", padx=5)

    # --- SİNOPTİK DENETİMİ ---
    f_den_synop = ttk.LabelFrame(tab_denetim, text=" SİNOPTİK Denetimi ", padding=10)
    f_den_synop.pack(fill="x", pady=(0, 10))
    create_tooltip(f_den_synop, lambda: "SİNOPTİK rasatlarının 'zamanında' gelip gelmediğini denetler.\n'Geç Gelen' filtresi bu ayarlara göre çalışır.")
    
    ttk.Checkbutton(f_den_synop, text="SİNOPTİK Denetimini Etkinleştir", variable=vars['var_denetim_synop_aktif']).pack(anchor="w", pady=5)
    f_syn = ttk.Frame(f_den_synop)
    f_syn.pack(fill="x")
    ttk.Label(f_syn, text="Başlangıç Saati:").pack(side="left")
    ttk.Spinbox(f_syn, from_=0, to=23, textvariable=vars['var_denetim_synop_start_hour'], width=3).pack(side="left", padx=5)
    ttk.Label(f_syn, text="Periyot (Saat):").pack(side="left")
    ttk.Spinbox(f_syn, from_=1, to=24, textvariable=vars['var_denetim_synop_period'], width=3).pack(side="left", padx=5)
    lbl_synop_zaman = ttk.Label(f_syn, text="Zaman Aralığı (On Time):", width=20)
    lbl_synop_zaman.pack(side="left", padx=(10, 5))
    create_tooltip(lbl_synop_zaman, lambda: "Bir SİNOPTİK'in 'zamanında' sayılması için kayıt saatinin (UTC)\nhangi dakikalar arasında olması gerektiğini belirtir.\nÖrn: 50-0 -> Rasat, saat XX:50 ile bir sonraki saatin XX:00'ı arasında gelmelidir.")
    ttk.Spinbox(f_syn, from_=0, to=59, textvariable=vars['var_denetim_synop_start'], width=3).pack(side="left")
    ttk.Label(f_syn, text="-").pack(side="left")
    ttk.Spinbox(f_syn, from_=0, to=59, textvariable=vars['var_denetim_synop_end'], width=3).pack(side="left")

    # --- TAF DENETİMİ ---
    f_den_taf = ttk.LabelFrame(tab_denetim, text=" TAF Denetimi ", padding=10)
    f_den_taf.pack(fill="x", pady=(0, 10))
    create_tooltip(f_den_taf, lambda: "TAF'ların 'zamanında' gelip gelmediğini denetler.\n'Geç Gelen' filtresi bu ayarlara göre çalışır.")
    
    ttk.Checkbutton(f_den_taf, text="TAF Denetimini Etkinleştir", variable=vars['var_denetim_taf_aktif']).pack(anchor="w", pady=5)
    
    chk_esnek = ttk.Checkbutton(f_den_taf, text="Geçiş Saatlerinde Esnek Çift TAF Modu (04:50, 10:50 vb.)", variable=vars.get('var_taf_esnek_mod'))
    chk_esnek.pack(anchor="w", pady=(0, 5))
    create_tooltip(chk_esnek, lambda: "Aktif olduğunda geçiş saatlerinde yeni ve eski TAF'ı aynı anda değerlendirerek en uyumlu olanı seçer.\nKapalıyken sadece ICAO kurallarına göre asıl geçerli olan TAF dikkate alınır.")

    f_taf = ttk.Frame(f_den_taf)
    f_taf.pack(fill="x")
    ttk.Label(f_taf, text="Başlangıç Saati:").pack(side="left")
    ttk.Spinbox(f_taf, from_=0, to=23, textvariable=vars['var_denetim_taf_start_hour'], width=3).pack(side="left", padx=5)
    ttk.Label(f_taf, text="Periyot (Saat):").pack(side="left")
    ttk.Spinbox(f_taf, from_=1, to=24, textvariable=vars['var_denetim_taf_period'], width=3).pack(side="left", padx=5)
    lbl_taf_zaman = ttk.Label(f_taf, text="Zaman Aralığı (On Time):", width=20)
    lbl_taf_zaman.pack(side="left", padx=(10, 5))
    create_tooltip(lbl_taf_zaman, lambda: "Bir TAF'ın 'zamanında' sayılması için kayıt saatinin (UTC)\nhangi dakikalar arasında olması gerektiğini belirtir.\nÖrn: 30-0 -> Rasat, saat XX:30 ile bir sonraki saatin XX:00'ı arasında gelmelidir.")
    ttk.Spinbox(f_taf, from_=0, to=59, textvariable=vars['var_denetim_taf_start'], width=3).pack(side="left")
    ttk.Label(f_taf, text="-").pack(side="left")
    ttk.Spinbox(f_taf, from_=0, to=59, textvariable=vars['var_denetim_taf_end'], width=3).pack(side="left")

    # --- GECİKME LİMİTLERİ (KIRMIZI SATIR VE ALARM TOLERANSI) ---
    f_delay = ttk.LabelFrame(tab_denetim, text=" Gecikme Limitleri (Kırmızı Satır ve Alarm Toleransı) ", padding=10)
    f_delay.pack(fill="x", pady=(0, 10))
    create_tooltip(f_delay, lambda: "Rasatın geliş süresi (Kayıt Saati - Rasat Saati) bu limiti aşarsa,\nana tablodaki satır kırmızı ile işaretlenir.\nBu ayar aynı zamanda 'Eksik Veri Alarmı' için tolerans süresi olarak kullanılır.")
    
    f_d_grid = ttk.Frame(f_delay)
    f_d_grid.pack(fill="x")
    
    ttk.Label(f_d_grid, text="METAR (dk):").pack(side="left")
    ttk.Spinbox(f_d_grid, from_=0, to=60, textvariable=vars['var_delay_limit_metar'], width=3).pack(side="left", padx=5)
    
    ttk.Label(f_d_grid, text="SİNOPTİK (dk):").pack(side="left", padx=(10, 0))
    ttk.Spinbox(f_d_grid, from_=0, to=60, textvariable=vars['var_delay_limit_synop'], width=3).pack(side="left", padx=5)
    
    ttk.Label(f_d_grid, text="TAF (dk):").pack(side="left", padx=(10, 0))
    ttk.Spinbox(f_d_grid, from_=0, to=60, textvariable=vars['var_delay_limit_taf'], width=3).pack(side="left", padx=5)

    # --- GECİKMELİ RASAT CEZA ALARMI ---
    f_ceza = ttk.LabelFrame(tab_denetim, text=" Geç Gelen / Eksik Veri Ceza Alarmı ", padding=10)
    f_ceza.pack(fill="x", pady=(0, 10))
    create_tooltip(f_ceza, lambda: "On-Time aralığı dışında kalan veya hiç gelmeyen rasatlar için\nbelirtilen aralıklarla tekrar eden alarm sistemidir.")
    
    ttk.Checkbutton(f_ceza, text="Ceza Alarmını Etkinleştir", variable=vars['var_denetim_gec_gelen_alarm_aktif']).pack(anchor="w", pady=5)
    
    f_ceza_grid = ttk.Frame(f_ceza)
    f_ceza_grid.pack(fill="x", pady=5)
    
    ttk.Label(f_ceza_grid, text="TÜR", font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ttk.Label(f_ceza_grid, text="Tekrar Sayısı", font=("Segoe UI", 8, "bold")).grid(row=0, column=1, padx=5, pady=2)
    ttk.Label(f_ceza_grid, text="Aralık (dk)", font=("Segoe UI", 8, "bold")).grid(row=0, column=2, padx=5, pady=2)
    
    ttk.Label(f_ceza_grid, text="METAR:").grid(row=1, column=0, sticky="w", padx=5)
    sb_ct_m = ttk.Spinbox(f_ceza_grid, from_=1, to=20, textvariable=vars['var_ceza_tekrar_metar'], width=4)
    sb_ct_m.grid(row=1, column=1, padx=5, pady=2)
    enable_mouse_wheel(sb_ct_m)
    sb_ca_m = ttk.Spinbox(f_ceza_grid, from_=1, to=60, textvariable=vars['var_ceza_aralik_metar'], width=4)
    sb_ca_m.grid(row=1, column=2, padx=5, pady=2)
    enable_mouse_wheel(sb_ca_m)
    
    ttk.Label(f_ceza_grid, text="SİNOPTİK:").grid(row=2, column=0, sticky="w", padx=5)
    sb_ct_s = ttk.Spinbox(f_ceza_grid, from_=1, to=20, textvariable=vars['var_ceza_tekrar_synop'], width=4)
    sb_ct_s.grid(row=2, column=1, padx=5, pady=2)
    enable_mouse_wheel(sb_ct_s)
    sb_ca_s = ttk.Spinbox(f_ceza_grid, from_=1, to=60, textvariable=vars['var_ceza_aralik_synop'], width=4)
    sb_ca_s.grid(row=2, column=2, padx=5, pady=2)
    enable_mouse_wheel(sb_ca_s)
    
    ttk.Label(f_ceza_grid, text="TAF:").grid(row=3, column=0, sticky="w", padx=5)
    sb_ct_t = ttk.Spinbox(f_ceza_grid, from_=1, to=20, textvariable=vars['var_ceza_tekrar_taf'], width=4)
    sb_ct_t.grid(row=3, column=1, padx=5, pady=2)
    enable_mouse_wheel(sb_ct_t)
    sb_ca_t = ttk.Spinbox(f_ceza_grid, from_=1, to=60, textvariable=vars['var_ceza_aralik_taf'], width=4)
    sb_ca_t.grid(row=3, column=2, padx=5, pady=2)
    enable_mouse_wheel(sb_ca_t)

    return lbl_clock
   
   
   