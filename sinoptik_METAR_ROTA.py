# -*- coding: utf-8 -*-
import re
import sys
import os
from datetime import timedelta

# Proje içi bağımlılıklar
from synop_decoder import SynopDecoder

# HATARAMA klasöründeki kurallar.py dosyasını dinamik olarak yükle
current_dir = os.path.dirname(os.path.abspath(__file__))
hatarama_dir = os.path.join(current_dir, "HATARAMA")
if hatarama_dir not in sys.path:
    sys.path.insert(0, hatarama_dir)

try:
    import kurallar
    HATA_DICT = kurallar.HATA_SOZLUGU
except ImportError:
    HATA_DICT = {}

class SinoptikRobotModulu:
    def __init__(self):
        self.decoder = SynopDecoder()
        self.hata_sozlugu = HATA_DICT

    def analiz_et(self, synop_raw, metar_raw, ref_date=None, all_metars=None):
        """
        SİNOPTİK ve METAR bültenlerini karşılaştırır ve SİNOPTİK iç tutarlılık denetimi yapar.
        """
        errors = []
        durum = "UYUMLU"
        skor = 100

        # 1. SİNOPTİK VERİSİNİ ÇÖZÜMLE
        synop_data = self.decoder.decode_line(synop_raw)
        if not synop_data:
            return 0, "F/UYUMSUZ", ["SİNOPTİK bülteni çözümlenemedi veya format hatalı."]

        # Format hatalarını al
        if not self.decoder.validate():
            for err in self.decoder.get_errors():
                errors.append(f"Format: {err}")

        # Değişkenleri güvenli şekilde al
        s_t = synop_data.get("sicaklik")
        s_td = synop_data.get("isba")
        s_p = synop_data.get("istasyon_basinci")
        s_p0 = synop_data.get("deniz_basinci")
        s_dd = synop_data.get("ruzgar_yon")
        s_ff = synop_data.get("ruzgar_hiz")
        s_ww = synop_data.get("halihazir_hava")
        s_ir = synop_data.get("ir")
        s_ix = synop_data.get("ix")
        s_rrr = synop_data.get("yagis_miktari_kod")
        s_n = synop_data.get("toplam_bulut")
        s_w1 = synop_data.get("gecmis_hava1")
        s_w2 = synop_data.get("gecmis_hava2")
        s_vv = synop_data.get("gorus_kod")
        s_cl = synop_data.get("cl_bulut_tipi")

        # =========================================================
        # 2. İÇ TUTARLILIK DENETİMİ (kurallar.py tabanlı)
        # =========================================================
        
        # Yağış İndikatörü (ir) Kontrolü
        if s_ir == 1 and s_rrr is None:
            errors.append(self.hata_sozlugu.get("h4", "İr=1 olduğu halde yağış grubu (RRR) verilmemiş."))
        if s_ir == 3 and s_rrr is not None:
            errors.append(self.hata_sozlugu.get("h5", "İr=3 (yağış yok) olduğu halde yağış grubu kodlanmış."))
        
        # İstasyon Tipi İndikatörü (ix) Kontrolü
        if s_ix == 1 and s_ww is None:
            errors.append(self.hata_sozlugu.get("h11", "İx=1 (hadise var) iken 7. grup (ww) verilmemiş."))
        if s_ix == 2 and s_ww is not None:
            errors.append(self.hata_sozlugu.get("h12", "İx=2 (hadise yok) iken 7. grup (ww) verilmiş."))

        # Halihazır Hava ve Bulut Tutarlılığı
        if s_ww is not None and s_ww >= 50 and s_n == 0:
            errors.append(self.hata_sozlugu.get("h111", "Yağış hadisesi verildiği halde toplam kapalılık 0."))
        
        if s_ww == 0:
            errors.append(self.hata_sozlugu.get("h78", "Halihazır hava 00 olamaz."))

        # Eksik Grup Kontrolleri
        if s_t is None: errors.append(self.hata_sozlugu.get("h252", "Sıcaklık (T) grubu koda dahil edilmedi."))
        if s_td is None: errors.append(self.hata_sozlugu.get("h253", "İşba (Td) grubu koda dahil edilmedi."))
        if s_p0 is None: errors.append(self.hata_sozlugu.get("h255", "Deniz seviyesi basıncı (QNH/P0) koda dahil edilmedi."))
        if s_n is None: errors.append(self.hata_sozlugu.get("h257", "Bulut grubu (N) koda dahil edilmedi."))

        # =========================================================
        # 3. METAR İLE ÇAPRAZ DENETİM (CROSS-CHECK)
        # =========================================================
        if metar_raw and metar_raw != "-":
            m_t, m_td, m_qnh, m_dd, m_ff = None, None, None, None, None
            
            # METAR Sıcaklık/İşba (Örn: 15/08, M02/M05)
            m_temp_match = re.search(r'\b(M?\d{2})/(M?\d{2})?\b', metar_raw)
            if m_temp_match:
                t_str = m_temp_match.group(1)
                d_str = m_temp_match.group(2)
                m_t = -int(t_str[1:]) if t_str.startswith('M') else int(t_str)
                if d_str:
                    m_td = -int(d_str[1:]) if d_str.startswith('M') else int(d_str)

            # METAR QNH (Örn: Q1015)
            m_qnh_match = re.search(r'\bQ(\d{4})\b', metar_raw)
            if m_qnh_match:
                m_qnh = int(m_qnh_match.group(1))

            # METAR Rüzgar (Örn: 36015G25KT, VRB02KT)
            m_wind_match = re.search(r'\b(\d{3}|VRB)(\d{2,3})(?:G\d{2,3})?KT\b', metar_raw)
            if m_wind_match:
                m_dd = -1 if m_wind_match.group(1) == "VRB" else int(m_wind_match.group(1))
                m_ff = int(m_wind_match.group(2))

            # --- KIYASLAMALAR ---
            # 1. Sıcaklık Kıyaslaması (Max 1.5°C tolerans)
            if s_t is not None and m_t is not None and abs(s_t - m_t) > 1.5:
                errors.append(f"Sıcaklık Farkı: SİNOPTİK ({s_t}°C) vs METAR ({m_t}°C) uyumsuz.")

            # 2. İşba Kıyaslaması (Max 1.5°C tolerans)
            if s_td is not None and m_td is not None and abs(s_td - m_td) > 1.5:
                errors.append(f"İşba Farkı: SİNOPTİK ({s_td}°C) vs METAR ({m_td}°C) uyumsuz.")

            # 3. Basınç Kıyaslaması (QNH vs Deniz Seviyesi Basıncı - Max 1.5 hPa tolerans)
            if s_p0 is not None and m_qnh is not None and abs(s_p0 - m_qnh) > 1.5:
                errors.append(f"Basınç Farkı: SİNOPTİK P0 ({s_p0}hPa) vs METAR QNH ({m_qnh}hPa) uyumsuz.")

            # 4. Rüzgar Kıyaslaması (Yön max 50°, Hız max 6KT tolerans)
            if s_ff is not None and m_ff is not None and abs(s_ff - m_ff) > 6:
                errors.append(f"Rüzgar Hızı Farkı: SİNOPTİK ({s_ff}KT/ms) vs METAR ({m_ff}KT) uyumsuz.")
                
            if s_dd is not None and m_dd is not None and m_dd != -1 and s_dd != -1:
                yon_farki = abs(s_dd - m_dd)
                if yon_farki > 180: yon_farki = 360 - yon_farki
                if yon_farki >= 50 and (s_ff >= 5 or m_ff >= 5):
                    errors.append(f"Rüzgar Yönü Farkı: SİNOPTİK ({s_dd}°) vs METAR ({m_dd}°) uyumsuz.")

            # 5. Hadise (Weather) Kıyaslaması
            has_metar_rain = bool(re.search(r'\b(RA|SN|DZ|SH|GR|GS|PL|SG)\b', metar_raw))
            has_metar_fog = bool(re.search(r'\b(FG|BR|HZ)\b', metar_raw))
            has_metar_ts = bool(re.search(r'\b(TS)\b', metar_raw))
            
            if s_ww is not None:
                # METAR'da var, SİNOPTİK 7. Grupta YOK
                if has_metar_rain and s_ww < 50 and s_ww not in [20, 21, 22, 23, 24, 25, 26, 27, 29]:
                    errors.append(f"7. Grup Çelişkisi: METAR'da Yağış var, ancak SİNOPTİK ww={s_ww} (Yağışsız).")
                if has_metar_fog and not (40 <= s_ww <= 49 or s_ww in [4, 5, 10, 11, 12, 28]):
                    errors.append(f"7. Grup Çelişkisi: METAR'da Sis/Pus var, ancak SİNOPTİK ww={s_ww}.")
                if has_metar_ts and not (s_ww == 17 or s_ww == 29 or 91 <= s_ww <= 99):
                    errors.append(f"7. Grup Çelişkisi: METAR'da Oraj (TS) var, ancak SİNOPTİK ww={s_ww}.")
                    
                # SİNOPTİK 7. Grupta VAR, METAR'da YOK (İki yönlü kontrol)
                if s_ww >= 50 and not has_metar_rain and not has_metar_ts:
                    errors.append(f"7. Grup Çelişkisi: SİNOPTİK ww={s_ww} (Yağışlı) kodlanmış, ancak METAR'da Yağış raporlanmamış.")
                if (40 <= s_ww <= 49) and not has_metar_fog:
                    errors.append(f"7. Grup Çelişkisi: SİNOPTİK ww={s_ww} (Sisli) kodlanmış, ancak METAR'da Sis/Pus raporlanmamış.")

            # =========================================================
            # GEÇMİŞ HAVA (W1, W2) İÇİN GEÇMİŞ METAR (SON 3/6 SAAT) DENETİMİ
            # =========================================================
            if all_metars and ref_date and s_w1 is not None and s_w2 is not None:
                # The past weather period is typically 6 hours for main stations, 3 for others.
                # We'll check the last 6 hours of METARs for a robust check.
                past_metars = []
                for m in all_metars:
                    # Check METARs from the 6 hours preceding the SYNOP time
                    if m.get('dt') and (ref_date - timedelta(hours=6, minutes=10)) <= m['dt'] < ref_date:
                        past_metars.append(m)
                
                if past_metars:
                    phenomena_codes = set()
                    
                    # Cloud cover flags
                    had_less_than_half_cover = False
                    had_more_than_half_cover = False

                    # Determine all W codes (0-9) that occurred in the past period
                    for m in past_metars:
                        m_raw = m.get('bulten', '')
                        
                        # Check for weather phenomena (codes 3-9)
                        if re.search(r'\b(TS)\b', m_raw): phenomena_codes.add(9)
                        if re.search(r'\b(SH)\b', m_raw): phenomena_codes.add(8)
                        if re.search(r'\b(SN|SG|PL)\b', m_raw): phenomena_codes.add(7)
                        # Add RA (6) or DZ (5) only if not part of a shower or thunderstorm
                        if not re.search(r'\b(TS|SH)\b', m_raw):
                            if re.search(r'\b(RA)\b', m_raw): phenomena_codes.add(6)
                            if re.search(r'\b(DZ)\b', m_raw): phenomena_codes.add(5)
                        if re.search(r'\b(FG|BR|HZ)\b', m_raw): phenomena_codes.add(4)
                        if re.search(r'\b(DS|SS|BLSN)\b', m_raw): phenomena_codes.add(3)

                        # Check for cloud cover (codes 0-2)
                        if re.search(r'\b(BKN|OVC)\b', m_raw):
                            had_more_than_half_cover = True
                        elif re.search(r'\b(FEW|SCT|SKC|CLR|NSC)\b', m_raw):
                            had_less_than_half_cover = True
                        else: # If no cloud groups are mentioned, it's often clear
                            had_less_than_half_cover = True
                    
                    cloud_codes = set()
                    if had_more_than_half_cover and had_less_than_half_cover: cloud_codes.add(1)
                    elif had_more_than_half_cover: cloud_codes.add(2)
                    elif had_less_than_half_cover: cloud_codes.add(0)

                    expected_w1, expected_w2 = None, None

                    if len(phenomena_codes) >= 2:
                        sorted_phenomena = sorted(list(phenomena_codes), reverse=True)
                        expected_w1 = sorted_phenomena[0]
                        expected_w2 = sorted_phenomena[1]
                    elif len(phenomena_codes) == 1:
                        expected_w1 = list(phenomena_codes)[0]
                        expected_w2 = expected_w1 # If only one type of phenomenon, W2=W1
                    else: # No phenomena, only clouds
                        if cloud_codes:
                            sorted_clouds = sorted(list(cloud_codes), reverse=True)
                            expected_w1 = sorted_clouds[0]
                            expected_w2 = sorted_clouds[1] if len(sorted_clouds) > 1 else expected_w1

                    # Compare with reported W1, W2
                    if expected_w1 is not None and s_w1 != expected_w1:
                        errors.append(f"Geçmiş Hava (W1) Çelişkisi: METAR'lara göre W1={expected_w1} beklenirken, SİNOPTİK W1={s_w1} olarak kodlanmış.")
                    if expected_w2 is not None and s_w2 != expected_w2:
                         errors.append(f"Geçmiş Hava (W2) Çelişkisi: METAR'lara göre W2={expected_w2} beklenirken, SİNOPTİK W2={s_w2} olarak kodlanmış.")

        # =========================================================
        # NİHAİ DEĞERLENDİRME
        # =========================================================
        formatted_errors = []
        formatted_errors.append("============================================================")
        formatted_errors.append(" 🔹 SİNOPTİK & METAR ÇAPRAZ DENETİM")
        formatted_errors.append("============================================================")

        if not errors:
            durum = "UYUMLU"
            skor = 100
            formatted_errors.append(" ✅ SİNOPTİK verisi iç kurallarla ve METAR ile TAM UYUMLU.")
        else:
            # Eğer hatalar arasında "Farkı" veya "Uyumsuz" kelimesi geçiyorsa (Çapraz Kontrol) UYUMSUZ
            if any("Farkı" in e or "Uyumsuz" in e for e in errors):
                durum = "UYUMSUZ"
            else:
                durum = "F/UYUMSUZ"
            skor = 0
            for err in errors:
                formatted_errors.append(f" ❌ {err}")

        return skor, durum, formatted_errors