# -*- coding: utf-8 -*-
import os
import re
import json
import threading
import logging
from datetime import datetime, timezone
import tkinter as tk
from tkinter import messagebox

import config_manager
from log_processor import process_and_analyze_logs

class HistoryMixin:
    """
    Aylık geçmiş analiz raporlamaları, TXT dökümleri ve otomatik yedeklemeleri
    yöneten Mixin sınıfı. gui_app_3.py'nin yükünü azaltmak için tasarlanmıştır.
    """
    
    def _generate_monthly_report_file(self, grouped, yil, ay, initial_filter):
        try:
            # --- GECİKME ANALİZİ VE SIRALAMA HAZIRLIĞI ---
            all_items_for_report = []
            for group in grouped:
                if group['taf']: all_items_for_report.append(group['taf'])
                all_items_for_report.extend(group['observations'])
            
            def get_sort_key_report(item):
                dt = item.get('dt')
                if not dt or not isinstance(dt, datetime) or dt.year < 1900:
                    dt = datetime.max
                
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
                return (dt, reg, prio)

            all_items_for_report.sort(key=get_sort_key_report)

            first_reg_map_report = {}
            for item in all_items_for_report:
                typ = item['type'].upper()
                bulten = item.get('bulten', '').upper()
                is_special = any(k in typ for k in ["KLİMA", "KLIMA", "MAX", "MAKSİMUM", "MAKSIMUM", "HADİSE", "HADISE"])
                if not is_special and ("MAKSİMUM RÜZGAR" in bulten or "MAX RUZGAR" in bulten or "MAKSIMUM RUZGAR" in bulten):
                    is_special = True
                    
                if not is_special and item.get('dt'):
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
                    if k not in first_reg_map_report or (item.get('reg_dt', datetime.max) < first_reg_map_report[k].get('reg_dt', datetime.max)):
                        first_reg_map_report[k] = item

            latest_items_map = {}
            other_items = []
            
            for item in all_items_for_report:
                typ = item['type'].upper()
                bulten = item.get('bulten', '').upper()
                
                norm_type = None
                if any(x in typ for x in ["SİNOPTİK", "SYNOP", "SINOPTIK"]): norm_type = "SİNOPTİK"
                elif any(x in typ for x in ["METAR", "SPECI"]): norm_type = "METAR"
                elif "TAF" in typ: norm_type = "TAF"
                
                is_special = any(k in typ for k in ["KLİMA", "KLIMA", "MAX", "MAKSİMUM", "MAKSIMUM", "HADİSE", "HADISE"])
                if not is_special and ("MAKSİMUM RÜZGAR" in bulten or "MAX RUZGAR" in bulten or "MAKSIMUM RUZGAR" in bulten):
                    is_special = True

                if is_special:
                    other_items.append(item)
                elif norm_type and item.get('dt') and item['dt'].year > 1900:
                    group_dt = item['dt']
                    if norm_type == "TAF":
                        m_val = re.search(r'\b(\d{4}/\d{4})\b', item.get("bulten", ""))
                        if m_val: group_dt = m_val.group(1)
                        else:
                            m_wmo = re.search(r'\b[A-Z0-9]{4,6}\s+[A-Z]{4}\s+(\d{6})\b', item.get("bulten", ""))
                            if m_wmo: group_dt = m_wmo.group(1)

                    latest_items_map[(norm_type, group_dt)] = item
            
            main_report_items = list(latest_items_map.values())
            other_items.sort(key=get_sort_key_report)

            final_main_items = []
            write_other_items = True

            if "GEÇ GELEN" in initial_filter:
                filtered_items = []
                for item in all_items_for_report:
                    typ = item['type'].upper()
                    bulten = item.get('bulten', '').upper()
                    is_special = any(k in typ for k in ["KLİMA", "KLIMA", "MAX", "MAKSİMUM", "MAKSIMUM", "HADİSE", "HADISE"])
                    if not is_special and ("MAKSİMUM RÜZGAR" in bulten or "MAX RUZGAR" in bulten or "MAKSIMUM RUZGAR" in bulten):
                        is_special = True
                        
                    if not is_special and item.get('dt'):
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
                        first_item = first_reg_map_report.get(k)
                        
                        if first_item and hasattr(self, 'is_obs_late') and self.is_obs_late(first_item):
                            if "METAR" in initial_filter and not ("METAR" in typ or "SPECI" in typ): continue
                            if "TAF" in initial_filter and "TAF" not in typ: continue
                            if "SİNOPTİK" in initial_filter and not ("SİNOPTİK" in typ or "SYNOP" in typ or "SINOPTIK" in typ): continue
                            filtered_items.append(item)
                
                final_main_items = filtered_items
                write_other_items = False
            elif "HARİCİ RASATLAR" in initial_filter:
                final_main_items = []
                write_other_items = True
            elif "F/UYUMSUZ" in initial_filter:
                filtered_items = []
                for item in main_report_items:
                    anl = item.get('analysis')
                    if anl and "F/UYUMSUZ" in anl.get('durum', '').upper():
                        filtered_items.append(item)
                final_main_items = filtered_items
                write_other_items = False
            elif initial_filter == "RE/GEÇMİŞ HATASI":
                filtered_items = []
                for item in main_report_items:
                    anl = item.get('analysis')
                    if anl and ("RE/GECMIS" in anl.get('durum', '').upper() or "RE/GEÇMİŞ" in anl.get('durum', '').upper()):
                        filtered_items.append(item)
                final_main_items = filtered_items
                write_other_items = False
            elif "UYUMSUZ" in initial_filter:
                filtered_items = []
                for item in main_report_items:
                    anl = item.get('analysis')
                    if anl:
                        durum = anl.get('durum', '').upper()
                        if "UYUMSUZ" in durum and not ("RE/GECMIS" in durum or "RE/GEÇMİŞ" in durum or "F/UYUMSUZ" in durum):
                            if "(" in initial_filter:
                                reasons = " ".join(anl.get("reasons", [])).upper()
                                if "RÜZGAR" in initial_filter and ("RÜZGAR" in reasons or "WIND" in reasons): filtered_items.append(item)
                                elif "GÖRÜŞ" in initial_filter and ("GÖRÜŞ" in reasons or "VIS" in reasons): filtered_items.append(item)
                                elif "HADİSE" in initial_filter and ("HADİSE" in reasons or "WX" in reasons): filtered_items.append(item)
                                elif "TAVAN" in initial_filter and ("TAVAN" in reasons or "CIG" in reasons or "DİKEY" in reasons): filtered_items.append(item)
                            else:
                                filtered_items.append(item)
                final_main_items = filtered_items
                write_other_items = False
            elif initial_filter in ["DİKKAT", "UYUMLU", "RASAT YOK"]:
                filtered_items = []
                for item in main_report_items:
                    anl = item.get('analysis')
                    if anl:
                        durum = anl.get('durum', '').upper()
                        if initial_filter == "DİKKAT" and "DİKKAT" in durum: filtered_items.append(item)
                        elif initial_filter == "UYUMLU" and "UYUMLU" in durum: filtered_items.append(item)
                        elif initial_filter == "RASAT YOK" and "TAF YOK" in durum: filtered_items.append(item)
                final_main_items = filtered_items
                write_other_items = False
            else:
                final_main_items = main_report_items
            
            final_main_items.sort(key=get_sort_key_report)
            
            base_log_dir = config_manager.USER_DATA_DIR
            monthly_dir = os.path.join(base_log_dir, "Aylik_Kayitlar", yil)
            if not os.path.exists(monthly_dir): os.makedirs(monthly_dir)
            
            monthly_file = os.path.join(monthly_dir, f"{ay}.txt")
            
            # --- İSTATİSTİK ÖZETİ HESAPLAMA ---
            counts = {
                "HEPSİ": 0, "UYUMLU": 0, "UYUMSUZ": 0, "F/UYUMSUZ": 0, "DİKKAT": 0,
                "RE/GEÇMİŞ HATASI": 0, "GEÇ GELEN": 0, "RASAT YOK": 0,
                "HARİCİ RASATLAR": len(other_items)
            }
            for item in main_report_items:
                counts["HEPSİ"] += 1
                anl = item.get('analysis')
                if anl:
                    durum = anl.get('durum', '').upper()
                    if "RE/GECMIS" in durum or "RE/GEÇMİŞ" in durum: counts["RE/GEÇMİŞ HATASI"] += 1
                    elif "F/UYUMSUZ" in durum: counts["F/UYUMSUZ"] += 1
                    elif "UYUMSUZ" in durum: counts["UYUMSUZ"] += 1
                    elif "DİKKAT" in durum: counts["DİKKAT"] += 1
                    elif "UYUMLU" in durum: counts["UYUMLU"] += 1
                    elif "TAF YOK" in durum: counts["RASAT YOK"] += 1
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
                    first_item = first_reg_map_report.get(k)
                    if first_item and hasattr(self, 'is_obs_late') and self.is_obs_late(first_item):
                        counts["GEÇ GELEN"] += 1
            
            summary_text = (
                "====================================================================================================\n"
                f"📊 AYLIK İSTATİSTİK ÖZETİ\n"
                "====================================================================================================\n"
                f"   • TOPLAM BÜLTEN (HEPSİ)   : {counts['HEPSİ']}\n"
                f"   • ✅ UYUMLU                : {counts['UYUMLU']}\n"
                f"   • ⚠️ DİKKAT                : {counts['DİKKAT']}\n"
                f"   • ❌ UYUMSUZ               : {counts['UYUMSUZ']}\n"
                f"   • ❌ F/UYUMSUZ             : {counts['F/UYUMSUZ']}\n"
                f"   • 🕒 GEÇ GELEN             : {counts['GEÇ GELEN']}\n"
                f"   • ❗ RE/GEÇMİŞ HATASI      : {counts['RE/GEÇMİŞ HATASI']}\n"
                f"   • ⚪ RASAT YOK             : {counts['RASAT YOK']}\n"
                f"   • 🟣 HARİCİ RASATLAR       : {counts['HARİCİ RASATLAR']}\n"
                "====================================================================================================\n\n"
            )

            def write_report(file_path, target_items, include_other, filter_name):
                with open(file_path, "w", encoding="utf-8") as f:
                    baslik_ay = "YILLIK" if ay == "TÜM YIL" else "AYLIK"
                    f.write(f"KARDELEN {baslik_ay} ANALİZ RAPORU - {ay} {yil}\n")
                    f.write(f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
                    if filter_name != "HEPSİ":
                        f.write(f"FİLTRE: {filter_name}\n")
                    f.write("="*100 + "\n\n")
                    f.write(summary_text)
                    
                    for idx, obs in enumerate(target_items):
                        is_taf = "TAF" in obs['type'].upper()
                        anl = obs.get('analysis')
                        durum, reasons, ref_taf, res_txt = "BİLİNMİYOR", [], "-", "-"
                        if anl:
                            durum = anl.get('durum', 'BİLİNMİYOR').upper()
                            reasons = anl.get('reasons', [])
                            ref_taf = anl.get('ref_taf', '-')
                            
                            is_re_error = "RE/GECMIS" in durum or "RE/GEÇMİŞ" in durum
                            
                            if is_re_error: res_txt = "RE/GECMIS HATASI"
                            elif "F/UYUMSUZ" in durum: res_txt = "F/UYUMSUZ"
                            elif "UYUMSUZ" in durum: res_txt = "UYUMSUZ"
                            elif "DİKKAT" in durum: res_txt = "DIKKAT"
                            elif "UYUMLU" in durum: res_txt = "UYUMLU"
                            elif "TAF YOK" in durum: res_txt = "TAF_YOK"
                            elif "DÜZELTİLDİ" in durum: res_txt = "DUZELTILDI"
                        
                        is_late, delay_minutes = False, 0
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
                            if first_item_in_group and hasattr(self, 'is_obs_late') and self.is_obs_late(first_item_in_group):
                                is_late = True
                                if first_item_in_group.get('reg_dt') and first_item_in_group.get('dt'):
                                    delay_minutes = self.get_delay_minutes(first_item_in_group)
                        
                        next_obs_info = ""
                        if "UYUMSUZ" in res_txt:
                            for j in range(idx + 1, len(target_items)):
                                next_item = target_items[j]
                                curr_type = obs['type'].upper()
                                next_type = next_item['type'].upper()
                                if ("METAR" in curr_type or "SPECI" in curr_type) and ("METAR" in next_type or "SPECI" in next_type):
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
                        f.write("-" * 100 + "\n")
                        
                        status_prefix = f"[{res_txt}] " if res_txt not in ["-", "BİLİNMİYOR"] else ""
                        f.write(f"{status_prefix}KAYIT: {kayit_tar:<16} | RASAT: {obs['tarih_str']:<16} | {obs['type']:<5} | Kull: {kull}\n")
                        
                        status_line = f"DURUM: {res_txt}"
                        if is_late: status_line += f" [GECİKME: {delay_minutes} dk]"
                        f.write(f"{status_line}\n")
                        if next_obs_info: f.write(f"{next_obs_info}\n")
                        f.write(f"   BULTEN : {obs['bulten']}\n")
                        
                        if not is_taf and res_txt not in ["-", "TAF_YOK"]:
                            if ref_taf != "-":
                                clean_ref_taf = ref_taf.split('=')[0] + '=' if '=' in ref_taf else ref_taf
                                f.write(f"   ► REF TAF: {clean_ref_taf}\n")
                            if ("UYUMSUZ" in res_txt or "RE/GECMIS HATASI" in res_txt) and reasons:
                                for r in reasons: f.write(f"   NEDEN  : {r}\n")
                        
                        if "DUZELTILDI" in res_txt and reasons:
                            for r in reasons: f.write(f"   ℹ️ {r}\n")
                        f.write("\n")
                    
                    if include_other and other_items:
                        f.write("="*100 + "\n>>> HARİCİ RASATLAR (KLİMA, MAX RÜZGAR, HADİSE vb.)\n" + "="*100 + "\n\n")
                        for obs in other_items:
                            kull = obs['raw'][1] if len(obs['raw']) > 1 else "-"
                            kayit_tar = obs['raw'][3] if len(obs['raw']) > 3 else "-"
                            f.write(f"[{kayit_tar}] [{obs['tarih_str']}] (Kull: {kull}) [{obs['type']}]\n   BULTEN: {obs['bulten']}\n\n")

            # 1. Her zaman TAM veritabanını güncel tut
            write_report(monthly_file, main_report_items, True, "HEPSİ")
            
            # 2. Eğer filtre varsa ayrıca kaydet
            if initial_filter != "HEPSİ":
                safe_filter = initial_filter.replace("/", "_").replace(" ", "_")
                filtered_file = os.path.join(monthly_dir, f"{safe_filter}_{ay}.txt")
                write_report(filtered_file, final_main_items, write_other_items, initial_filter)
        except Exception as e:
            logging.error(f"Aylık dosya yazma hatası: {e}")

    def load_history_from_file(self):
        from tkinter import filedialog
        
        base_log_dir = config_manager.USER_DATA_DIR
        initial_dir = os.path.join(base_log_dir, "Aylik_Kayitlar")
        if not os.path.exists(initial_dir):
            initial_dir = base_log_dir
            
        raw_file = filedialog.askopenfilename(
            title="Geçmiş Analiz Verisi Seçin",
            initialdir=initial_dir,
            filetypes=[("Metin ve JSON Dosyaları", "*.txt;*.json"), ("JSON Ham Veri", "*_raw.json"), ("Aylık Rapor (TXT)", "*.txt"), ("Tüm Dosyalar", "*.*")]
        )
        
        if not raw_file:
            return # Kullanıcı iptal etti
            
        file_name = os.path.basename(raw_file)
        self.lbl_status.config(text=f"Dosyadan yükleniyor: {file_name}...")
        if 'btn_trend_history' in self.cp_widgets:
            self.cp_widgets['btn_trend_history'].config(state="disabled")
            
        def _worker():
            try:
                if raw_file.endswith('.json'):
                    with open(raw_file, 'r', encoding='utf-8') as f: 
                        logs = json.load(f)
                else:
                    logs = []
                    with open(raw_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    import re
                    
                    # 1. YENİ FORMAT (TÜR: METAR | KULL: ...)
                    pattern_new = r"TÜR:\s*(.*?)\s*\|\s*KULL:\s*(.*?)\s*\|\s*GÖND:\s*(.*?)\s*\|\s*KAYIT:\s*(.*?)\s*\|\s*RASAT:\s*([^\n]+)\nBÜLTEN:\s*([^\n]+)"
                    for m in re.finditer(pattern_new, content, re.IGNORECASE):
                        tip, kull, gond, kayit, rasat, bulten = m.groups()
                        logs.append([tip.strip(), kull.strip(), gond.strip(), kayit.strip(), rasat.strip(), bulten.strip()])
                        
                    # 2. YEDEK TXT FORMATI (NİSAN.txt formatı - TÜRÜ=... RASAT TAR...)
                    pattern_txt = r"TÜRÜ=(.*?)\tRASAT TAR\s+(.*?)\tKayıt Tar=(.*?)\tKULL=(.*?)\t+Bülten=\s*([^\n]+)"
                    for m in re.finditer(pattern_txt, content, re.IGNORECASE):
                        tur, rasat_tar_raw, kayit, kull, bulten = m.groups()
                        tip = tur.strip()
                        if not tip:
                            if "TAF" in bulten: tip = "TAF"
                            elif "SYNOP" in bulten or "SİNOPTİK" in bulten: tip = "SİNOPTİK"
                            else: tip = "METAR"
                        kayit = kayit.strip()
                        saat = kayit[-4:-2] + ":" + kayit[-2:] if len(kayit) >= 4 else "00:00"
                        tarih_sade = rasat_tar_raw.split()[0] if rasat_tar_raw else ""
                        rasat = f"{tarih_sade} {saat}Z"
                        logs.append([tip, kull.strip(), "-", kayit, rasat, bulten.strip()])
                        
                    # 3. EN ESKİ FORMAT (KAYIT: ... | RASAT: ...)
                    pattern1 = r'KAYIT:\s*([^|]+?)\s*\|\s*RASAT:\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*Kull:\s*([^\n]+)\n.*?BULTEN\s*:\s*([^\n]+)'
                    for m in re.finditer(pattern1, content, re.DOTALL | re.IGNORECASE):
                        kayit, rasat, tip, kull, bulten = m.group(1).strip(), m.group(2).strip(), m.group(3).strip(), m.group(4).strip(), m.group(5).strip()
                        gond = rasat.split()[1] if " " in rasat else "-"
                        logs.append([tip, kull, gond, kayit, rasat, bulten])
                    
                    # 4. HARİCİ RASATLAR (KLİMA, MAX vb.)
                    pattern2 = r'\[([^\]]+)\]\s*\[([^\]]+)\]\s*\(Kull:\s*([^)]+)\)\s*\[([^\]]+)\]\n\s*BULTEN:\s*([^\n]+)'
                    for m in re.finditer(pattern2, content, re.IGNORECASE):
                        kayit, rasat, kull, tip, bulten = m.group(1).strip(), m.group(2).strip(), m.group(3).strip(), m.group(4).strip(), m.group(5).strip()
                        gond = rasat.split()[1] if " " in rasat else "-"
                        logs.append([tip, kull, gond, kayit, rasat, bulten])
                        
                if logs:
                    grouped = process_and_analyze_logs(logs, getattr(self, 'robot', None))
                    
                    if hasattr(self, 'apply_dual_taf_analysis'):
                        self.apply_dual_taf_analysis(grouped)
                        
                    if hasattr(self, 'clean_invalid_re_rules'): self.clean_invalid_re_rules(grouped)
                    self.app_state["last_grouped_data"] = grouped
                    initial_filter = self.cp_widgets['cb_trend_filtre'].get()
                    
                    self.root.after(0, lambda: self.populate_tree(grouped, initial_filter))
                    self.root.after(0, lambda: self.lbl_status.config(text=f"Dosyadan yüklendi: {len(logs)} kayıt ({file_name})."))
                else:
                    self.root.after(0, lambda: self.lbl_status.config(text="Dosya boş."))
            except Exception as e:
                self.root.after(0, lambda e=e: messagebox.showerror("Hata", f"Dosya okuma hatası: {e}"))
            finally:
                if 'btn_trend_history' in self.cp_widgets:
                    self.root.after(0, lambda: self.cp_widgets['btn_trend_history'].config(state="normal"))
                    
        threading.Thread(target=_worker, daemon=True).start()

    def auto_daily_history_backup(self):
        """Her gün sonunda o günün verilerini aylık arşive otomatik ekler."""
        try:
            now_utc = datetime.now(timezone.utc)
            tr_months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
            ay = tr_months[now_utc.month - 1]
            yil = str(now_utc.year)
            
            base_log_dir = config_manager.USER_DATA_DIR
            monthly_dir = os.path.join(base_log_dir, "Aylik_Kayitlar", yil)
            os.makedirs(monthly_dir, exist_ok=True)
            raw_file = os.path.join(monthly_dir, f"{ay}_raw.json")
            
            gun = str(now_utc.day).zfill(2)
            logging.info("Gün sonu otomatik geçmiş analiz yedeği başlatılıyor...")
            
            if hasattr(self, 'scraper'):
                bugun_logs = self.scraper.fetch_logs(gun, ay, yil, "500")
                if not bugun_logs: return
                
                existing_logs = []
                if os.path.exists(raw_file):
                    try:
                        with open(raw_file, 'r', encoding='utf-8') as f: 
                            existing_logs = json.load(f)
                    except: pass
                
                all_logs = existing_logs + bugun_logs
                seen, unique_logs = set(), []
                for log in all_logs:
                    t_log = tuple(log)
                    if t_log not in seen:
                        seen.add(t_log)
                        unique_logs.append(log)
                        
                with open(raw_file, 'w', encoding='utf-8') as f: 
                    json.dump(unique_logs, f, ensure_ascii=False)
                
                grouped = process_and_analyze_logs(unique_logs, getattr(self, 'robot', None))
                if hasattr(self, 'apply_dual_taf_analysis'):
                    self.apply_dual_taf_analysis(grouped)
                    
                if hasattr(self, 'clean_invalid_re_rules'): self.clean_invalid_re_rules(grouped)
                self._generate_monthly_report_file(grouped, yil, ay, "HEPSİ")
                logging.info("Gün sonu geçmiş analiz yedeği başarıyla tamamlandı.")
        except Exception as e:
            logging.error(f"Otomatik gün sonu yedekleme hatası: {e}")