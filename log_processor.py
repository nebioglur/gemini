import re
from datetime import datetime, timedelta
import logging

def extract_station_code(text):
    """Metin içinden istasyon kodunu (ICAO) çıkarır. (Zaman grubuyla bitişik olanı arar)"""
    # Örn: LTAN 121200Z -> LTAN
    match = re.search(r'\b([A-Z]{4})\s+\d{6}Z?', text)
    if match:
        return match.group(1)
    return None

def _resolve_dt_helper(day, hour, minute, ref_date):
    """DDHHMM formatındaki zamanı referans tarihe göre en yakın datetime objesine çevirir."""
    candidates = []
    # Check previous, current, and next month to handle month/year boundaries
    for month_offset in [-1, 0, 1]:
        try:
            year, month = ref_date.year, ref_date.month + month_offset
            if month < 1:
                month += 12
                year -= 1
            elif month > 12:
                month -= 12
                year += 1
            
            # Create the date, will raise ValueError if day is invalid for month
            dt = datetime(year, month, day, hour, minute)
            candidates.append(dt)
        except ValueError:
            continue
    if not candidates: return None
    return min(candidates, key=lambda x: abs(x - ref_date))

def parse_taf_periods(taf_text, issue_time):
    clean_taf = " ".join(taf_text.split())
    periods = []
    change_regex = r'(FM\d{6}|(?:BECMG|PROB\d{2}\s+TEMPO|TEMPO|PROB\d{2})\s+\d{4}/\d{4})'
    changes = list(re.finditer(change_regex, clean_taf))

    # Yardımcı: Bir noktadan sonraki ilk FM grubuna kadar olan metni al
    def get_wx_until_next_fm(start_idx):
        fm_iter = re.finditer(r'FM\d{6}', clean_taf)
        end_idx = len(clean_taf)
        for m in fm_iter:
            if m.start() > start_idx:
                end_idx = m.start()
                break
        return clean_taf[start_idx:end_idx].strip()

    # BASE Periyodu: Baştan ilk FM'e kadar (TEMPO/BECMG dahil)
    base_wx = get_wx_until_next_fm(0)

    # Varsayılan bitiş zamanı (TAF geçerliliği kadar, örn: 30 saat)
    default_end = issue_time + timedelta(hours=30)

    periods.append({
        'type': 'BASE',
        'start': issue_time,
        'end': default_end,
        'wx': base_wx,
        'header': 'ANA'
    })

    for i, m in enumerate(changes):
        match_text = m.group(1)
        group_type = 'FM' if match_text.startswith('FM') else match_text.split()[0]
        start_idx = m.end()
        
        if group_type in ['FM', 'BECMG']:
            # Kalıcı değişiklikler: Sonraki FM'e kadar her şeyi al (Trendler dahil)
            full_wx = get_wx_until_next_fm(m.start())
        else:
            # TEMPO/PROB: Sadece kendi bloğu (Sonraki değişime kadar)
            end_idx = changes[i+1].start() if i+1 < len(changes) else len(clean_taf)
            wx_text = clean_taf[start_idx:end_idx].strip()
            full_wx = f"{match_text} {wx_text}"

        p_start = None
        p_end = default_end

        try:
            if group_type == 'FM':
                ts = match_text[2:]
                day, hour, minute = int(ts[0:2]), int(ts[2:4]), int(ts[4:6])
                p_start = issue_time.replace(day=day, hour=hour, minute=minute, second=0, microsecond=0)
                # Ay geçiş kontrolü
                if day < issue_time.day and (issue_time.day - day) > 15:
                    p_start = p_start.replace(month=issue_time.month + 1 if issue_time.month < 12 else 1, year=issue_time.year if issue_time.month < 12 else issue_time.year + 1)
                elif day > issue_time.day and (day - issue_time.day) > 15:
                    p_start = p_start.replace(month=issue_time.month - 1 if issue_time.month > 1 else 12, year=issue_time.year if issue_time.month > 1 else issue_time.year - 1)
            else:
                time_range = match_text.split()[-1]
                parts = time_range.split('/')
                s_part, e_part = parts[0], parts[1]
                
                def resolve(ddhh):
                    d, h = int(ddhh[:2]), int(ddhh[2:])
                    dt = issue_time.replace(day=d, hour=h, minute=0, second=0, microsecond=0)
                    if d < issue_time.day and (issue_time.day - d) > 15:
                        dt = dt.replace(month=issue_time.month + 1 if issue_time.month < 12 else 1, year=issue_time.year if issue_time.month < 12 else issue_time.year + 1)
                    elif d > issue_time.day and (d - issue_time.day) > 15:
                        dt = dt.replace(month=issue_time.month - 1 if issue_time.month > 1 else 12, year=issue_time.year if issue_time.month > 1 else issue_time.year - 1)
                    return dt

                dt_s = resolve(s_part)
                dt_e = resolve(e_part)

                if group_type == 'BECMG':
                    # BECMG için son saat (değişimin tamamlandığı an) başlangıç kabul edilir
                    p_start = dt_e
                    p_end = default_end
                elif group_type in ['TEMPO']:
                    p_start = dt_s
                    p_end = dt_e

            periods.append({
                'type': group_type,
                'start': p_start,
                'end': p_end,
                'wx': full_wx,
                'header': match_text
            })
        except:
            continue

    # start değeri None olan (okunamayan) gruplar için varsayılan olarak en küçük zamanı ata
    periods.sort(key=lambda x: x['start'] if x['start'] is not None else datetime.min)
    return periods

def _find_active_taf_period(periods, obs_dt):
    """
    Finds the last permanent (BASE, FM, BECMG) and active temporary (TEMPO) TAF periods
    to determine the reference weather text for the UI.
    """
    last_permanent = periods[0]  # Default to BASE
    active_tempo = None

    for p in periods:
        # Permanent changes that happened before or at the observation time
        if p['type'] in ['BASE', 'FM', 'BECMG']:
            if p['start'] <= obs_dt:
                last_permanent = p
        # Temporary changes active during the observation time
        elif p['type'] in ['TEMPO']:
            # Note: The end time of a TEMPO is the end of the temporary condition.
            if p['start'] <= obs_dt <= p['end']:
                active_tempo = p
    
    # The reference for the UI is the TEMPO if active, otherwise the last permanent state.
    active_period = active_tempo if active_tempo else last_permanent
    ref_wx_text = active_period['wx']
    ref_header = active_period.get('header', 'ANA')
    
    return ref_wx_text, ref_header

def _extract_short_reasons(full_report, durum):
    """
    Extracts a list of short, human-readable reasons from the full analysis report.
    """
    short_reasons = []
    for line in full_report:
        if "▪" in line:
            reason = line.split("▪")[1].strip()
            if reason not in short_reasons:
                short_reasons.append(reason)
    
    # If no specific reasons found but the status is not compatible, add a generic reason.
    if not short_reasons and "UYUMLU" not in durum:
        report_text = "\n".join(full_report)
        if "NOSIG" in report_text:
            short_reasons.append("NOSIG Çelişkisi")
        elif "F/UYUMSUZ" in report_text:
            short_reasons.append("Format Hatası")
        elif "UYUMSUZ" in durum:
            short_reasons.append("Limit Dışı")
            
    return short_reasons

def _handle_nosig_analysis(metar_trend_part, full_report, durum, reasons):
    """
    Analyzes the full report for NOSIG-related warnings and updates the status and reasons.
    This function relies on the detailed report from the core analysis engine.
    """
    if "NOSIG" not in metar_trend_part:
        return durum, reasons

    report_text = "\n".join(full_report).upper()
    
    # Check for explicit NOSIG conflicts identified by the analysis engine
    # Example: "NOSIG ÇELİŞKİSİ: TAF'TA AKTİF DEĞİŞİMLER VAR: ..."
    if "NOSIG ÇELİŞKİSİ" in report_text or "ÇELİŞKİ: METAR 'NOSIG'" in report_text:
        # Find the specific conflict reason from the report
        nosig_reason = next((line.strip() for line in full_report if "NOSIG" in line and ("ÇELİŞKİ" in line or "UYARISI" in line)), None)
        
        # The core engine already provides a good explanation. Let's use it.
        if nosig_reason:
            # Clean up the reason for display (remove the bullet point and icons)
            clean_reason = re.sub(r'^\s*▪\s*|\s*ℹ️\s*|\s*❌\s*', '', nosig_reason).strip()
            if clean_reason not in reasons:
                reasons.append(f"⚠️ {clean_reason}")
        else: # Fallback if parsing fails
            reasons.append("⚠️ NOSIG UYARISI: TAF'ta beklenen değişim ile METAR'daki NOSIG çelişiyor.")

        if "UYUMLU" in durum:
            durum = "DİKKAT (NOSIG)"
        return durum, reasons

    # If no conflicts are found, add the appropriate informational message
    if "UYUMSUZ" in durum:
        reasons.append("❌ NOSIG UYARISI: TAF ile uyumsuz olan mevcut durumun (Hadise vb.) 2 saat daha devam edeceği (NOSIG) belirtilmiş.")
    elif "DİKKAT" in durum:
        reasons.append("⚠️ NOSIG: Dikkat çeken / TAF sınırlarında olan mevcut durumun 2 saat daha devam edeceği (NOSIG) belirtilmiş.")
    else:  # UYUMLU
        reasons.append("✅ NOSIG: TAF rotasıyla uyumlu (2 saat içinde değişim yok).")
        
    return durum, reasons

def _determine_alarm_status(durum):
    """
    Determines the alarm color and display text based on the analysis status.
    """
    if "DİKKAT" in durum or "Trend" in durum:
        return "SARI", "⚠️ DİKKAT"
    elif "UYUMSUZ" in durum:
        return "KIRMIZI", "❌ UYUMSUZ"
    
    return "YESIL", "✅ UYUMLU"

def analyze_single_obs(taf_item, obs, robot_instance):
    """Tek bir METAR/TAF çifti için analiz yapar."""
    try:
        # 1. TAF periyotlarını ve aktif olanı bul (UI referansı için)
        periods = parse_taf_periods(taf_item["bulten"], taf_item["dt"])
        ref_taf_wx, ref_period_header = _find_active_taf_period(periods, obs['dt'])

        # 2. METAR trendini ayıkla
        metar_trend_part = ""
        trend_match = re.search(r'\b(BECMG|TEMPO|NOSIG|TREND)\b', obs["bulten"])
        if trend_match:
            metar_trend_part = obs["bulten"][trend_match.start():].strip()

        # 3. Ana analiz motorunu çağır
        t_valid_match = re.search(r'\b\d{4}/\d{4}\b', taf_item["bulten"])
        taf_validity_str = t_valid_match.group(0) if t_valid_match else "0000/0000"

        _, durum, full_report = robot_instance.analiz_et(
            taf_raw=taf_item["bulten"],
            metar_raw=obs["bulten"],
            trend_raw=metar_trend_part,
            taf_zaman=taf_validity_str,
            ref_date=obs["dt"]
        )
        
        # 4. Sonuçları işle ve zenginleştir
        reasons = _extract_short_reasons(full_report, durum)
        durum, reasons = _handle_nosig_analysis(metar_trend_part, full_report, durum, reasons)
        alarm, display_text = _determine_alarm_status(durum)

        # 5. Sonuç sözlüğünü oluştur ve döndür
        return {
            "durum": durum, 
            "reasons": reasons, 
            "full_report": full_report, 
            "alarm": alarm, 
            "ref_taf": ref_taf_wx, 
            "display_text": display_text, 
            "ref_period": ref_period_header, 
            "full_taf_text": taf_item["bulten"]
        }

    except Exception as e:
        logging.error(f"analyze_single_obs içinde beklenmedik hata: {e}", exc_info=True)
        return {
            "durum": "HATA", 
            "reasons": [str(e)], 
            "full_report": [str(e)], 
            "alarm": "KIRMIZI", 
            "ref_taf": taf_item.get("bulten", "TAF Bulteni Yok"), 
            "display_text": "❌ HATA", 
            "ref_period": "-", 
            "full_taf_text": taf_item.get("bulten", "TAF Bulteni Yok")
        }

def process_and_analyze_logs(ham_veriler, robot_instance):
    islenmis_liste = []

    for v in ham_veriler:
        v_list = list(v)
        rasat_str = v_list[4]
        kayit_str = v_list[3]
        bulten = v_list[5]
        
        # --- TÜR NORMALİZASYONU EN BAŞTA YAPILMALI ---
        turu = v_list[0].strip().upper()
        bulten_up = bulten.upper()
        
        is_amd = any(x in turu for x in ["AMD", "COR", "AAA", "AAB", "AAC", "CCA", "CCB", "CCC"])
        is_metar = any(x in turu for x in ["METAR", "SPECI", "SA", "SP"]) or any(x in bulten_up[:30] for x in ["METAR", "SPECI"])
        if is_amd and "TAF" not in turu and not is_metar:
            turu = "TAF " + turu
            
        if not turu:
            if "TAF" in bulten_up[:30] or re.match(r'^(FC|FT)[A-Z0-9]{2}\b', bulten_up): turu = "TAF"
            elif "METAR" in bulten_up[:30] or "SPECI" in bulten_up[:30] or re.match(r'^(SA|SP)[A-Z0-9]{2}\b', bulten_up): turu = "METAR"
            elif "AAXX" in bulten_up[:30] or re.match(r'^SM[A-Z0-9]{2}\b', bulten_up): turu = "SİNOPTİK"
            
        if "SİLME" in turu or "SILME" in turu:
            turu = "RASAT SİLME"

        v_list[0] = turu
        # ---------------------------------------------

        dt = datetime.min
        reg_dt = datetime.min
        formatted_rasat = rasat_str

        # Tarih formatları
        date_formats = [
            "%d.%m.%Y %H:%M",
            "%d.%m.%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%y%m%d%H%M"
        ]

        try:
            # 1. Tüm zaman stringlerini önce naive datetime'a çevir
            dt_raw = datetime.min
            for fmt in date_formats:
                try: dt_raw = datetime.strptime(rasat_str.strip(), fmt); break
                except: pass

            reg_dt_raw = datetime.min
            for fmt in date_formats:
                try: reg_dt_raw = datetime.strptime(kayit_str.strip(), fmt); break
                except: pass
            
            if reg_dt_raw == datetime.min:
                reg_dt_raw = datetime.now()
            
            # 2. Bültenden UTC zamanını ayrıştır (ground truth)
            bulten_dt_utc = None
            
            # FIX: Referans olarak Kayıt Tarihi yerine Rasat Tarihi (dt_raw) kullan.
            # Böylece geç girilen (re-upload) verilerde tarih kayması (bir sonraki aya atlama) önlenir.
            ref_for_calc = dt_raw if dt_raw != datetime.min else reg_dt_raw
            
            if "METAR" in turu or "TAF" in turu or "SPECI" in turu:
                match = re.search(r'\b(\d{2})(\d{2})(\d{2})Z\b', bulten)
                if match:
                    day, hour, minute = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    bulten_dt_utc = _resolve_dt_helper(day, hour, minute, ref_for_calc)

            elif "SİNOPTİK" in turu or "SYNOP" in turu or "SINOPTIK" in turu:
                match = re.search(r'AAXX\s+(\d{2})(\d{2})\d', bulten)
                if match:
                    day, hour = int(match.group(1)), int(match.group(2))
                    bulten_dt_utc = _resolve_dt_helper(day, hour, 0, ref_for_calc)

            # 3. Zamanları belirle
            if bulten_dt_utc:
                dt = bulten_dt_utc
                if abs((dt_raw - bulten_dt_utc).total_seconds()) < 60 * 30:
                    reg_dt = reg_dt_raw
                else:
                    reg_dt = reg_dt_raw - timedelta(hours=3)
            else:
                if dt_raw != datetime.min:
                    dt = dt_raw - timedelta(hours=3)
                reg_dt = reg_dt_raw - timedelta(hours=3)

            # --- RASAT SİLME İÇİN KAYIT TARİHİ BAZ ALINMALI ---
            if turu == "RASAT SİLME":
                dt = reg_dt

        except Exception:
            # Herhangi bir parse hatasında eski yönteme dön
            is_utc = rasat_str.strip().upper().endswith('Z')
            clean_rasat = rasat_str.strip().upper().removesuffix('Z').strip()
            
            # Kayıt tarihi
            reg_dt = datetime.min
            try: reg_dt = datetime.strptime(kayit_str.strip(), "%d.%m.%Y %H:%M");
            except: pass
            if reg_dt != datetime.min and not is_utc:
                reg_dt = reg_dt - timedelta(hours=3)

            # Rasat tarihi
            dt = datetime.min
            try: dt = datetime.strptime(clean_rasat, "%d.%m.%Y %H:%M")
            except: pass
            if dt != datetime.min and not is_utc:
                dt = dt - timedelta(hours=3)

        # Kayıt tarihi için formatları dene (yedek)
        formats = [
            "%d.%m.%Y %H:%M",
            "%d.%m.%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%y%m%d%H%M"
            "%y%m%d%H%MZ"
        ]
        if reg_dt == datetime.min:
            clean_kayit = kayit_str.strip().upper().removesuffix('Z').strip()
            for fmt in formats:
                try: reg_dt = datetime.strptime(kayit_str.strip(), fmt); break
                except: pass
            
            if reg_dt == datetime.min:
                for fmt in formats:
                    try: reg_dt = datetime.strptime(clean_kayit, fmt); break
                    except: pass

        # --- 0000 UTC SİNOPTİK DÜZELTMESİ ---
        # Eğer 00 UTC rasatı, önceki günün son saatlerinde (20-23 UTC) etiketlendiyse düzelt.
        # GENEL KURAL: Sinoptik saatleri 00, 03, 06... şeklindedir. 23:xx saati standart dışıdır ve 00Z'yi ifade eder.
        if ("SİNOPTİK" in v_list[0].upper() or "SINOPTIK" in v_list[0].upper()) and dt.hour == 23:
            next_day = dt + timedelta(days=1)
            dt = dt.replace(year=next_day.year, month=next_day.month, day=next_day.day, hour=0, minute=0, second=0)
            # v_list[4] (Görünen Tarih) güncellenmiyor, orijinal kalıyor ki kullanıcı ne zaman geldiğini görsün.

        if ("SİNOPTİK" in v_list[0].upper() or "SINOPTIK" in v_list[0].upper()) and dt.hour in [20, 21, 22, 23]:
            parts = v_list[5].split()
            # İlk 5 gruba bak (AAXX YYGGiw ...)
            for p in parts[:5]:
                # YY00i formatı (Günün tarihi + 00 saat)
                if len(p) == 5 and p.isdigit() and p[2:4] == "00":
                    try:
                        yy = int(p[:2])
                        next_day = dt + timedelta(days=1)
                        if yy == next_day.day:
                            logging.info(f"SİNOPTİK DÜZELTME: {dt.strftime('%d.%m %H:%M')} -> 00:00 UTC ({p})")
                            dt = dt.replace(year=next_day.year, month=next_day.month, day=next_day.day, hour=0, minute=0, second=0)
                            break
                    except: pass

        item = {
            "raw": v_list,
            "dt": dt,
            "reg_dt": reg_dt,
            "tarih_str": formatted_rasat,
            "type": turu,
            "bulten": v_list[5],
            "analysis": None
        }
        islenmis_liste.append(item)

    # --- CORRECTION HANDLING (CCA/CCB/CCC) ---
    # Aynı 'RASAT TAR' ve 'TÜR' olanları grupla
    obs_map = {}
    for item in islenmis_liste:
        itype = item["type"]
        if "METAR" in itype or "SPECI" in itype or "TAF" in itype:
            group_dt = item["dt"]
            if "TAF" in itype:
                # Aynı geçerlilik periyodundaki (DDHH/DDHH) TAF'ları grupla ki AMD/COR düzeltmeleri eskisini ezebilsin
                m_val = re.search(r'\b(\d{4}/\d{4})\b', item.get("bulten", ""))
                if m_val: 
                    group_dt = m_val.group(1)
                else:
                    m_wmo = re.search(r'\b[A-Z0-9]{4,6}\s+[A-Z]{4}\s+(\d{6})\b', item.get("bulten", ""))
                    if m_wmo: group_dt = m_wmo.group(1)
                    
            norm_type = "TAF" if "TAF" in itype else ("SPECI" if "SPECI" in itype else "METAR")
            key = (group_dt, norm_type)
            if key not in obs_map: obs_map[key] = []
            obs_map[key].append(item)
    
    for key, items in obs_map.items():
        if len(items) > 1:
            # Düzeltme seviyesini belirle (COR/AMD/AAA=1, CCA/AAB=2, vb...)
            def get_corr_level(txt):
                t = txt.upper()
                if "CCC" in t: return 6
                if "CCB" in t: return 5
                if "CCA" in t: return 4
                if "AAC" in t: return 3
                if "AAB" in t: return 2
                if "AAA" in t or "AMD" in t or "COR" in t: return 1
                return 0
            
            # AAA/AMD her zaman normal TAF'ı ezecek şekilde önce düzeltme seviyesine bakılır
            items.sort(key=lambda x: (get_corr_level(x["bulten"]), x["reg_dt"]), reverse=True)
            
            # Diğerlerini 'DÜZELTME VAR' olarak işaretle
            valid_item = items[0]
            for superseded in items[1:]:
                yeni_bulten = valid_item["bulten"]
                superseded["valid_taf_ref"] = valid_item
                superseded["analysis"] = {
                    "durum": "DÜZELTİLDİ",
                    "reasons": [
                        f"BU TAF İPTAL EDİLDİ / DÜZELTİLDİ.",
                        f"ESKİ: {superseded['bulten']}",
                        f"YENİ: {yeni_bulten}"
                    ],
                    "full_report": [f"BU TAF İPTAL EDİLDİ / DÜZELTİLDİ.\nESKİ: {superseded['bulten']}\nYENİ: {yeni_bulten}"],
                    "alarm": "MAVI",
                    "ref_taf": yeni_bulten,
                    "display_text": "DÜZELTİLDİ",
                    "ref_period": "-",
                    "full_taf_text": yeni_bulten
                }

    # Sıralama Anahtarı: METAR/TAF/SİNOPTİK -> Rasat Tarihi (dt), Diğerleri -> Kayıt Tarihi (reg_dt)
    def sort_key(x):
        if any(t in x["type"] for t in ["METAR", "TAF", "SPECI", "SİNOPTİK", "SYNOP", "SINOPTIK"]):
            return (x["dt"], x["reg_dt"])
        return (x["reg_dt"], x["reg_dt"])

    islenmis_liste.sort(key=sort_key)

    # --- GEÇMİŞ HADİSE (RE) DENETİMİ ---
    # Ardışık METAR/SPECI rasatları arasında kesilen hadiselerin (RE) girilip girilmediğini kontrol eder.
    station_obs = {}
    for item in islenmis_liste:
        if "METAR" in item["type"] or "SPECI" in item["type"]:
            st_code = extract_station_code(item["bulten"])
            if st_code:
                if st_code not in station_obs:
                    station_obs[st_code] = []
                station_obs[st_code].append(item)
                
    for st_code, obs_list in station_obs.items():
        # Rasat tarihine (dt) ve sonra kayıt tarihine göre sırala
        obs_list.sort(key=lambda x: (x["dt"], x["reg_dt"]))
        
        valid_obs_list = []
        for obs in obs_list:
            anl = obs.get("analysis") or {}
            if "DÜZELTİLDİ" not in anl.get("durum", ""):
                valid_obs_list.append(obs)
                
        for i in range(1, len(valid_obs_list)):
            prev_obs = valid_obs_list[i-1]
            curr_obs = valid_obs_list[i]
            
            # Sadece 1 saatten kısa süre geçmişse bu kuralı işlet (Örn: 30 dk veya 60 dk periyotlar)
            diff_minutes = (curr_obs["dt"] - prev_obs["dt"]).total_seconds() / 60.0
            if diff_minutes > 65 or diff_minutes <= 0:
                continue
                
            prev_active, prev_re, prev_vc = robot_instance.extract_active_and_recent_weather(prev_obs["bulten"])
            curr_active, curr_re, curr_vc = robot_instance.extract_active_and_recent_weather(curr_obs["bulten"])
            
            re_errors = []
            
            # Kural 1: Önceki SPECI'de RE varsa, sonraki ilk METAR'da RE olmalı (Eğer o hadise yeniden başlamamışsa)
            if "SPECI" in prev_obs["type"] and "METAR" in curr_obs["type"]:
                for wx in prev_re:
                    # YENİ MANTIK: Hadiselerin köklerini ayır (Örn: RESHRA -> SH, RA) ve ortak kök var mı diye bak
                    wx_roots = set(re.findall(r'(TS|SH|FZ|MI|BC|PR|DR|BL|RA|SN|DZ|GR|GS|SG|PL|UP|FG|BR|HZ|SA|DU|SS|DS|PO|SQ|FC)', wx))
                    
                    is_covered = False
                    for current_re_item in curr_re:
                        curr_re_roots = set(re.findall(r'(TS|SH|FZ|MI|BC|PR|DR|BL|RA|SN|DZ|GR|GS|SG|PL|UP|FG|BR|HZ|SA|DU|SS|DS|PO|SQ|FC)', current_re_item))
                        if wx_roots & curr_re_roots: # Ortak kök varsa (Örn: İkisinde de RA varsa) örtüşüyor demektir
                            is_covered = True
                            break
                    
                    if not is_covered:
                        # Eğer o hadise tekrar başlamadıysa ve civar (VC) olarak devam etmiyorsa RE verilmesi zorunludur.
                        for a_wx in curr_active | curr_vc:
                            a_roots = set(re.findall(r'(TS|SH|FZ|MI|BC|PR|DR|BL|RA|SN|DZ|GR|GS|SG|PL|UP|FG|BR|HZ|SA|DU|SS|DS|PO|SQ|FC)', a_wx))
                            if wx_roots & a_roots:
                                is_covered = True
                                break
                        
                        if not is_covered:
                            prev_t_str = prev_obs['dt'].strftime('%H:%M') + "Z" if prev_obs.get('dt') and prev_obs['dt'].year > 1900 else ""
                            re_errors.append(f"ZORUNLU KURAL: Önceki SPECI ({prev_t_str}) rasatında bulunan 'RE{wx}' bilgisi, takip eden ilk METAR rasatında da MUHAKKAK verilmelidir. [Önceki Rasat: {prev_obs['bulten']}]")
                            
            # Kural 2: Önceki rasatta aktif hadise var, şu anki rasatta kesilmişse RE olmalı
            for wx in prev_active:
                koken = re.sub(r'^[\-\+VC]+', '', wx)
                
                # Görüş engelleyiciler (MIFG, BCFG, FZFG dahil) ve sürüklenen/kalkan toz/kum/kar için RE aranmaz.
                if any(obsc in koken for obsc in ["FG", "BR", "HZ", "FU", "DU", "SA", "PO"]):
                    continue
                if koken in ["DRSN", "DRDU", "DRSA", "BLDU", "BLSA"]:
                    continue

                wx_roots = set(re.findall(r'(TS|SH|FZ|MI|BC|PR|DR|BL|RA|SN|DZ|GR|GS|SG|PL|UP|FG|BR|HZ|SA|DU|SS|DS|PO|SQ|FC)', wx))
                
                # Önceki hadisenin şiddetini hesapla (+ = 3, Normal = 2, - = 1, VC = 0)
                prev_intensity = 3 if wx.startswith('+') else (1 if wx.startswith('-') else (0 if wx.startswith('VC') else 2))

                is_active_now = False
                intensity_decreased = False
                
                for a_wx in curr_active | curr_vc:
                    a_roots = set(re.findall(r'(TS|SH|FZ|MI|BC|PR|DR|BL|RA|SN|DZ|GR|GS|SG|PL|UP|FG|BR|HZ|SA|DU|SS|DS|PO|SQ|FC)', a_wx))
                    if wx_roots & a_roots: # Ortak kök bulundu (Örn: TSRA)
                        curr_intensity = 3 if a_wx.startswith('+') else (1 if a_wx.startswith('-') else (0 if a_wx.startswith('VC') else 2))
                        # Eğer güncel hadise öncekinden daha hafif DEĞİLSE (aynıysa veya arttıysa) geçmiş hadiseye gerek yoktur
                        if curr_intensity >= prev_intensity:
                            is_active_now = True
                            break
                        else:
                            intensity_decreased = True

                if not is_active_now:
                    re_found = False
                    for r_wx in curr_re:
                        r_roots = set(re.findall(r'(TS|SH|FZ|MI|BC|PR|DR|BL|RA|SN|DZ|GR|GS|SG|PL|UP|FG|BR|HZ|SA|DU|SS|DS|PO|SQ|FC)', r_wx))
                        if wx_roots & r_roots:
                            re_found = True
                            break

                    if not re_found:
                        prev_t_str = prev_obs['dt'].strftime('%H:%M') + "Z" if prev_obs.get('dt') and prev_obs['dt'].year > 1900 else ""
                        if intensity_decreased:
                            re_errors.append(f"Önceki rasattaki ({prev_t_str}) '{wx}' hadisesinin şiddeti hafiflemiş, bu nedenle RE{koken} (Geçmiş Hadise) kodu girilmelidir. [Önceki Rasat: {prev_obs['bulten']}]")
                        else:
                            re_errors.append(f"Önceki rasattaki ({prev_t_str}) '{wx}' hadisesi tamamen kesilmiş, ancak RE{koken} (Geçmiş Hadise) kodu girilmemiş. [Önceki Rasat: {prev_obs['bulten']}]")
            
            if re_errors:
                # Hataları geçici bir listeye al (Ana analiz döngüsünde sonuçların üzerine eklenecek)
                curr_obs["re_errors"] = re_errors

    # --- YENİ GRUPLAMA MANTIĞI (İSTASYON BAZLI EŞLEŞTİRME) ---
    # TAF ve METAR'ları istasyon kodlarına göre eşleştirir.
    # Böylece LTAI tarafından yazılan LTBS TAF'ı, LTAI METAR'ı ile karışmaz.
    
    groups = []
    active_taf_groups = {} # { 'LTAN': group_dict, ... }
    
    # Başlangıçta TAF'sız (Yetim) rasatlar için grup
    orphan_group = {"taf": None, "observations": []}
    groups.append(orphan_group)

    for item in islenmis_liste:
        st_code = extract_station_code(item["bulten"])
        
        
        if "TAF" in item["type"]:
            new_group = {"taf": item, "observations": []}
            groups.append(new_group)
            if st_code:
                active_taf_groups[st_code] = new_group
        
        elif "METAR" in item["type"] or "SPECI" in item["type"]:
            # Düzeltme ile elenenleri de gruba ekle (görünsünler)
            target_group = orphan_group
            if st_code and st_code in active_taf_groups:
                target_group = active_taf_groups[st_code]
            
            target_group["observations"].append(item)
            
        else:
            # Sinoptik vb.
            orphan_group["observations"].append(item)

    if not orphan_group["observations"]:
        groups.remove(orphan_group)

    # --- ANALİZ ---
    for group in groups:
        current_taf_item = group['taf']
        
        for obs in group['observations']:
            # Önceden analiz edilmişse (Sadece DÜZELTİLDİ / İptal durumu vb. için) atla
            if obs.get("analysis") and "DÜZELTİLDİ" in obs["analysis"].get("durum", ""): 
                continue
            
            if obs["type"] == "RASAT SİLME":
                obs["analysis"] = {
                    "durum": "RASAT SİLİNDİ",
                    "reasons": ["Bu kayıt sistemden silinmiş bir rasatı ifade eder."],
                    "full_report": ["Bu kayıt sistemden silinmiş bir rasatı ifade eder."],
                    "alarm": "YESIL",
                    "ref_taf": "-",
                    "display_text": "🗑️ RASAT SİLME",
                    "ref_period": "-",
                    "full_taf_text": "-"
                }
                continue

            if not ("METAR" in obs["type"] or "SPECI" in obs["type"]):
                obs["analysis"] = {
                    "durum": "-",
                    "reasons": [],
                    "full_report": [],
                    "alarm": "YESIL",
                    "ref_taf": "-",
                    "display_text": "-"
                }
                continue
            
            # --- TAF EŞLEŞTİRME İYİLEŞTİRMESİ ---
            # Eğer bulunduğumuz grupta TAF yoksa (Yetim), geçmiş gruplardan uygun TAF ara.
            active_taf = current_taf_item
            
            if not active_taf:
                obs_st = extract_station_code(obs["bulten"])
                if obs_st:
                    # Tüm grupları tersten tara (En yeni TAF'tan eskiye)
                    for g in reversed(groups):
                        t = g['taf']
                        if t and t['dt'] <= obs['dt']:
                            t_st = extract_station_code(t["bulten"])
                            if t_st == obs_st:
                                active_taf = t
                                break

            if not active_taf:
                obs["analysis"] = {
                    "durum": "TAF YOK",
                    "reasons": ["Referans TAF bulunamadı."],
                    "full_report": ["Referans TAF bulunamadı."],
                    "alarm": "YESIL",
                    "ref_taf": "-",
                    "display_text": "TAF YOK",
                    "ref_period": "-",
                    "full_taf_text": "TAF BULUNAMADI"
                }
                
                # TAF yoksa bile METAR için Geçmiş Hadise (RE) hatası varsa göster
                if obs.get("re_errors"):
                    obs["analysis"]["durum"] = "RE/GECMIS HATASI"
                    obs["analysis"]["display_text"] = "❌ RE/Geçmiş H."
                    obs["analysis"]["alarm"] = "KIRMIZI"
                    for err in obs["re_errors"]:
                        obs["analysis"]["reasons"].append(f"⚠️ [GEÇMİŞ HADİSE KURALI] {err}")
                continue

            # TAF'ın aktif, güncel versiyonunu (Düzeltme varsa AMD vb.) kullan
            actual_taf_to_evaluate = active_taf
            if actual_taf_to_evaluate.get("valid_taf_ref"):
                actual_taf_to_evaluate = actual_taf_to_evaluate["valid_taf_ref"]

            # --- GEÇERLİLİK (VALIDITY) KONTROLÜ VE ASIL TAF SEÇİMİ ---
            primary_taf = actual_taf_to_evaluate
            secondary_taf = None
            
            obs_st = extract_station_code(obs["bulten"])
            prev_taf_candidate = None
            
            if obs_st:
                curr_idx = groups.index(group)
                for i in range(curr_idx - 1, -1, -1):
                    g = groups[i]
                    if g['taf']:
                        t_st = extract_station_code(g['taf']["bulten"])
                        if t_st == obs_st:
                            prev_taf_candidate = g['taf']
                            if prev_taf_candidate.get("valid_taf_ref"):
                                prev_taf_candidate = prev_taf_candidate["valid_taf_ref"]
                            break

            # TAF geçerlilik başlangıcını kontrol et
            t_valid_match = re.search(r'\b(\d{2})(\d{2})/\d{2}\d{2}\b', primary_taf["bulten"])
            if t_valid_match and prev_taf_candidate:
                v_day, v_hour = int(t_valid_match.group(1)), int(t_valid_match.group(2))
                v_dt = _resolve_dt_helper(v_day, v_hour, 0, primary_taf['dt'])
                # Kullanıcı İsteği: Yeni TAF yayınlandıktan sonra (örn: 13:40), yeni periyodun 
                # başlangıcına (15:00) kadar olan tüm METAR (14:50 dahil) ve SPECI'ler Çift TAF kontrolüne girer.
                if v_dt and obs['dt'] <= v_dt:
                    secondary_taf = primary_taf
                    primary_taf = prev_taf_candidate

            # 1. Asıl TAF ile Analiz
            analysis = analyze_single_obs(primary_taf, obs, robot_instance)
            
            # --- YENİ KURAL: GEÇİŞ PERİYODU KONTROLÜ (90 DAKİKA) ---
            # METAR ile yeni TAF arasında 90 dakikaya kadar fark varsa (Örn: 13:40 TAF -> 14:50 METAR = 70dk), esnek moda sok.
            time_diff_mins = (obs['dt'] - actual_taf_to_evaluate['dt']).total_seconds() / 60.0
            is_transition_period = (0 <= time_diff_mins <= 90)

            def get_status_score(status_str):
                s = status_str.upper()
                if "UYUMLU" in s: return 2
                if "DİKKAT" in s: return 1
                return 0

            # 2. İkinci Seçenek (Fallback) TAF ile Analiz (Esnek Mod Aktifse)
            is_esnek_mod_active = getattr(robot_instance, 'taf_esnek_mod_aktif', True)
            if is_esnek_mod_active and (("UYUMSUZ" in analysis["durum"] and obs["type"] != "SPECI") or is_transition_period):
                if secondary_taf:
                    # Yeni periyot TAF'ı ile (2. Seçenek) şansımızı deneyelim
                    sec_analysis = analyze_single_obs(secondary_taf, obs, robot_instance)
                    
                    s_main = get_status_score(analysis["durum"])
                    s_sec = get_status_score(sec_analysis["durum"])
                    
                    combined_full_report = []
                    combined_full_report.append("============================================================")
                    combined_full_report.append(" 🔄 GEÇİŞ PERİYODU ÇİFT TAF ANALİZİ (ESNEK KONTROL)")
                    combined_full_report.append("============================================================")
                    combined_full_report.append(f"► 1. SEÇENEK (Mevcut Geçerli TAF): {primary_taf['tarih_str']}")
                    combined_full_report.extend(analysis["full_report"])
                    combined_full_report.append("")
                    combined_full_report.append(f"► 2. SEÇENEK (Yeni Yayınlanan TAF): {secondary_taf['tarih_str']}")
                    combined_full_report.extend(sec_analysis["full_report"])

                    if s_sec >= s_main:
                        analysis = sec_analysis
                        if s_main == 0 and s_sec == 0:
                            analysis["reasons"].insert(0, f"ℹ️ GEÇİŞ RASATI: Her iki TAF ile de UYUMSUZ (Yeni TAF baz alındı).")
                        else:
                            analysis["reasons"].insert(0, f"ℹ️ GEÇİŞ RASATI: Yeni yayınlanan TAF ({secondary_taf['tarih_str']}) daha uyumlu (Esnek Kontrol).")
                        
                        clean_curr = primary_taf.get('bulten', '').split('=')[0].strip() + '='
                        analysis["ref_taf"] = f"(Yeni TAF) {analysis['ref_taf']}\n\n[Geçerli Eski TAF]\n{clean_curr}"
                        analysis["full_report"] = combined_full_report
                    else:
                        analysis["reasons"].insert(0, f"ℹ️ GEÇİŞ RASATI: Eski TAF daha uyumlu (Esnek Kontrol). Eski TAF baz alındı.")
                        clean_sec = secondary_taf.get('bulten', '').split('=')[0].strip() + '='
                        analysis["ref_taf"] = f"(Mevcut TAF) {analysis['ref_taf']}\n\n[Yeni Yayınlanan TAF]\n{clean_sec}"
                        analysis["full_report"] = combined_full_report
                elif prev_taf_candidate:
                    # Normal Fallback (Secondary yer değiştirmemişse, önceki TAF'a standart bakış)
                    # Toleransı 6 saate çıkardık (Örn: 19:40 ile 22:50 arası ~3 saat)
                    if 0 <= (obs['dt'] - prev_taf_candidate['dt']).total_seconds() <= 6 * 3600:
                        prev_analysis = analyze_single_obs(prev_taf_candidate, obs, robot_instance)
                        
                        s_main = get_status_score(analysis["durum"])
                        s_prev = get_status_score(prev_analysis["durum"])
                        
                        combined_full_report = []
                        combined_full_report.append("============================================================")
                        combined_full_report.append(" 🔄 GEÇİŞ PERİYODU ÇİFT TAF ANALİZİ (ESNEK KONTROL)")
                        combined_full_report.append("============================================================")
                        combined_full_report.append(f"► 1. SEÇENEK (Mevcut TAF): {actual_taf_to_evaluate['tarih_str']}")
                        combined_full_report.extend(analysis["full_report"])
                        combined_full_report.append("")
                        combined_full_report.append(f"► 2. SEÇENEK (Önceki TAF): {prev_taf_candidate['tarih_str']}")
                        combined_full_report.extend(prev_analysis["full_report"])

                        if s_prev > s_main:
                            analysis = prev_analysis
                            analysis["reasons"].insert(0, f"ℹ️ Mevcut TAF ile uyumsuz, önceki TAF ({prev_taf_candidate['tarih_str']}) ile daha uyumlu. Önceki TAF baz alındı.")
                            clean_curr = actual_taf_to_evaluate.get('bulten', '').split('=')[0].strip() + '='
                            analysis["ref_taf"] = f"(Önceki TAF) {analysis['ref_taf']}\n\n[Mevcut TAF]\n{clean_curr}"
                            analysis["full_report"] = combined_full_report
                        elif is_transition_period or s_main == 0:
                            if s_main == 0 and s_prev == 0:
                                analysis["reasons"].insert(0, f"ℹ️ Her iki TAF ile de UYUMSUZ.")
                            clean_prev = prev_taf_candidate.get('bulten', '').split('=')[0].strip() + '='
                            analysis["ref_taf"] = f"(Mevcut TAF) {analysis['ref_taf']}\n\n[Önceki TAF]\n{clean_prev}"
                            analysis["full_report"] = combined_full_report
            
            # --- GEÇMİŞ HADİSE (RE) UYARILARINI ANA ANALİZE EKLE ---
            if obs.get("re_errors"):
                analysis["durum"] = "RE/GECMIS HATASI"
                analysis["display_text"] = "❌ RE/Geçmiş H."
                analysis["alarm"] = "KIRMIZI"
                
                analysis["full_report"].append("")
                analysis["full_report"].append("============================================================")
                analysis["full_report"].append(" ❌ GEÇMİŞ HADİSE (RE) KURAL İHLALİ")
                analysis["full_report"].append("============================================================")
                
                for err in obs["re_errors"]:
                    analysis["reasons"].append(f"⚠️ [GEÇMİŞ HADİSE KURALI] {err}")
                    analysis["full_report"].append(f"⚠️ [GEÇMİŞ HADİSE KURALI] {err}")

            obs["analysis"] = analysis

    # --- GRUPLAMA VE SIRALAMA ---
    # Grupları TAF tarihine (veya ilk rasat tarihine) göre sırala
    def group_sort_key(g):
        if g['taf']: 
            return (g['taf']['dt'], g['taf']['reg_dt'])
        elif g['observations']: 
            first = g['observations'][0]
            return (first['dt'], first['reg_dt'])
        return (datetime.min, datetime.min)

    groups.sort(key=group_sort_key)
    

    return groups
