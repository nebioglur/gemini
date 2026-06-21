import re
from datetime import datetime, timedelta, timezone
import json
import os
import logging

# =============================================================================
# HAVACILIK ROBOT MODÜLÜ (ANALİZ MOTORU)
# =============================================================================
class HavacilikRobotModulu:
    """
    TAF ve METAR raporlarını ayrıştıran ve ICAO kurallarına göre
    uyumluluk analizi yapan ana sınıf.

    TAF/METAR ANALİZ MANTIĞI (ICAO & ANNEX 3)
    -----------------------------------------
    Bu modül, ICAO standartlarına ve havacılık meteorolojisi kurallarına dayanarak
    TAF (Tahmin) ile METAR (Gerçekleşen) raporlarını karşılaştırır.

    ÇALIŞMA MANTIĞI:
    1. Tanımlamalar ve Eşik Değerler (__init__):
       - Görüş (Visibility): 150m, 350m, 600m, 800m, 1500m, 3000m, 5000m.
       - Tavan (Ceiling): 100, 200, 500, 1000, 1500 feet.
       - Kritik Hadiseler: TS, FZ, FG, SN, GR vb.

    2. Veri Ayrıştırma (Parsing):
       - Rüzgar, Görüş, Bulut/Tavan ve Hadiseler metinden ayrıştırılır.

    3. Karşılaştırma Mantığı (_compare_values):
       - Rüzgar: Hız farkı >= 10 KT veya Yön farkı >= 60 derece (hız >= 10KT ise).
       - Görüş ve Tavan: Eşik değerlerden biri geçildiyse (Örn: 5000m -> 3000m).
       - Hadise: Kritik hadise var/yok durumu değiştiyse.

    4. Ana Analiz Akışı (analiz_et):
       a. Ana Karşılaştırma: TAF ana kısmı vs METAR.
       b. TAF Trend Kontrolü: Uyumsuzsa, BECMG/TEMPO gruplarına bakılır.
       c. METAR Trend Kontrolü: Hala uyumsuzsa, METAR sonundaki NOSIG/BECMG/TEMPO'ya bakılır.
       d. Uyumsuzluk: Hiçbiri uymuyorsa "UYUMSUZ" döner.
    """
    def __init__(self):
        self.esikler_ruyet = [150, 350, 600, 800, 1500, 3000, 5000]
        self.esikler_tavan = [100, 200, 500, 1000, 1500]
        self.esikler_vv = [100, 200, 500, 1000]
        self.kritik_hadiseler = {
            'TS': r'(?:\b|(?<=VC))TS', 
            'FZ': r'\bFZ', 
            'FG': r'(?:\b|(?<=VC)|(?<=MI)|(?<=BC)|(?<=PR)|(?<=FZ))FG\b', 
            'SQ': r'\bSQ\b', 
            'FC': r'\bFC\b', 
            'SS': r'(?:\b|(?<=VC))SS\b', 
            'DS': r'(?:\b|(?<=VC))DS\b', 
            'BLSN': r'\bBLSN\b', 
            'DRSN': r'\bDRSN\b', 
            'BLDU': r'\bBLDU\b', 
            'DRDU': r'\bDRDU\b', 
            'BLSA': r'\bBLSA\b', 
            'DRSA': r'\bDRSA\b', 
            'RA': r'(?:\b|(?<=SH)|(?<=TS)|(?<=FZ)|(?<=VC))RA\b', 
            'SN': r'(?:\b|(?<=SH)|(?<=TS)|(?<=FZ)|(?<=VC))SN\b', 
            'GR': r'(?:\b|(?<=SH)|(?<=TS)|(?<=VC))GR\b'
        }
        
        logging.info("--- KRİTİK DEĞERLEME KISTASLARI ---")
        logging.info(f"Görüş Eşikleri (m): {self.esikler_ruyet}")
        logging.info(f"Tavan Eşikleri (ft): {self.esikler_tavan}")
        logging.info(f"Dikey Görüş Eşikleri (ft): {self.esikler_vv}")
        logging.info(f"Kritik Hadiseler (Regex): {self.kritik_hadiseler}")
        logging.info("-----------------------------------")
        
        # Kullanıcı İsteği: Konsola (Terminal) Kıstas Çeşit ve Limitlerini Yazdır
        print("\n" + "="*60)
        print("🌍 TREND KISTAS ÇEŞİTLERİ VE LİMİTLERİ (ICAO ANNEX 3)")
        print("="*60)
        print(f"👁️  Görüş Eşikleri (m)       : {self.esikler_ruyet}")
        print(f"☁️  Tavan Eşikleri (ft)      : {self.esikler_tavan}")
        print(f"📏 Dikey Görüş Eşikleri (ft): {self.esikler_vv}")
        print(f"⛈️  Kritik Hadiseler         : {', '.join(self.kritik_hadiseler.keys())}")
        print("="*60 + "\n")

        base_log_dir = os.path.join(os.path.expanduser("~"), "KardelenLogs")
        self.config_file = os.path.join(base_log_dir, "robot_config.json")
        self.trend_min_sure = 15
        self.trend_max_sure = 75
        self.trend_tl_min_sure = 15
        self.trend_tl_max_sure = 90
        self.trend_zaman_aktif = True
        self.kati_icao_kurallari = False
        self.load_settings()

    def load_settings(self):
        """Ayarları dosyadan yükler."""
        loaded = False
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.trend_min_sure = data.get("trend_min_sure", 15)
                    self.trend_max_sure = data.get("trend_max_sure", 75)
                    self.trend_zaman_aktif = data.get("trend_zaman_aktif", True)
                    self.esikler_ruyet = data.get("esikler_ruyet", self.esikler_ruyet)
                    self.esikler_tavan = data.get("esikler_tavan", self.esikler_tavan)
                    self.esikler_vv = data.get("esikler_vv", self.esikler_vv)
                    self.kati_icao_kurallari = data.get("kati_icao_kurallari", False)
                    self.trend_tl_min_sure = data.get("trend_tl_min_sure", 15)
                    self.trend_tl_max_sure = data.get("trend_tl_max_sure", 90)
                    loaded = True
            except: pass
            
        # Eğer kullanıcı klasöründe yoksa (yeni bilgisayar/kurulum), EXE içine gömülü olanı kullan
        if not loaded:
            import sys
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                bundled_config = os.path.join(sys._MEIPASS, "robot_config.json")
                if os.path.exists(bundled_config):
                    try:
                        with open(bundled_config, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            self.trend_min_sure = data.get("trend_min_sure", 15)
                            self.trend_max_sure = data.get("trend_max_sure", 75)
                            self.trend_zaman_aktif = data.get("trend_zaman_aktif", True)
                            self.esikler_ruyet = data.get("esikler_ruyet", self.esikler_ruyet)
                            self.esikler_tavan = data.get("esikler_tavan", self.esikler_tavan)
                            self.esikler_vv = data.get("esikler_vv", self.esikler_vv)
                            self.kati_icao_kurallari = data.get("kati_icao_kurallari", False)
                            self.trend_tl_min_sure = data.get("trend_tl_min_sure", 15)
                            self.trend_tl_max_sure = data.get("trend_tl_max_sure", 90)
                    except: pass

    def save_settings(self):
        """Ayarları dosyaya kaydeder."""
        data = {
            "trend_min_sure": self.trend_min_sure,
            "trend_max_sure": self.trend_max_sure,
            "trend_zaman_aktif": self.trend_zaman_aktif,
            "esikler_ruyet": self.esikler_ruyet,
            "esikler_tavan": self.esikler_tavan,
            "esikler_vv": self.esikler_vv,
            "kati_icao_kurallari": self.kati_icao_kurallari,
            "trend_tl_min_sure": self.trend_tl_min_sure,
            "trend_tl_max_sure": self.trend_tl_max_sure
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except: pass

    def _resolve_dt(self, day, hour, minute, ref_date):
        """DDHHMM formatındaki zamanı referans tarihe göre datetime objesine çevirir."""
        candidates = []
        for offset in [-1, 0, 1]:
            y, m = ref_date.year, ref_date.month + offset
            if m < 1: m += 12; y -= 1
            elif m > 12: m -= 12; y += 1
            try:
                base = datetime(y, m, 1)
                dt = base + timedelta(days=day-1, hours=hour, minutes=minute)
                candidates.append(dt)
            except: continue
        if not candidates: return None
        return min(candidates, key=lambda x: abs(x - ref_date))

    def _resolve_hhmm(self, hh, mm, ref_date):
        """HHMM formatındaki saati referans tarihe en yakın olacak şekilde çözer."""
        candidates = []
        for day_offset in [-1, 0, 1]:
            try:
                base = ref_date + timedelta(days=day_offset)
                dt = base.replace(hour=hh, minute=mm, second=0, microsecond=0)
                candidates.append(dt)
            except: continue
        if not candidates: return ref_date
        return min(candidates, key=lambda x: abs(x - ref_date))

    def zaman_uygun_mu(self, taf_header, metar_time_code, ref_date=None):
        """
        TAF geçerlilik aralığı ile METAR saatini kıyaslar.
        UTC zaman dilimi ve gün geçişlerini (ay sonu dahil) dikkate alır.
        """
        try:
            # TAF: DDHH/DDHH
            t_match = re.search(r'(\d{2})(\d{2})/(\d{2})(\d{2})', taf_header)
            if not t_match: return False
            
            ts_d, ts_h = int(t_match.group(1)), int(t_match.group(2))
            te_d, te_h = int(t_match.group(3)), int(t_match.group(4))
            
            # METAR: DDHHMMZ
            m_match = re.search(r'(\d{2})(\d{2})(\d{2})Z', metar_time_code)
            if not m_match: return False
            
            m_d, m_h, m_m = int(m_match.group(1)), int(m_match.group(2)), int(m_match.group(3))
            
            now = ref_date if ref_date else datetime.now(timezone.utc).replace(tzinfo=None)
            
            def safe_dt(y, m, d, h, minute=0):
                # Ayın 1'inden başlayıp gün ekleyerek tarih oluştur (Ay sonu taşmalarını önler)
                base = datetime(y, m, 1)
                return base + timedelta(days=d-1, hours=h, minutes=minute)

            # TAF Başlangıç (En yakın tarih tahmini)
            candidates = []
            for offset in [-1, 0, 1]:
                y, m = now.year, now.month + offset
                if m < 1: m += 12; y -= 1
                elif m > 12: m -= 12; y += 1
                try:
                    candidates.append(safe_dt(y, m, ts_d, ts_h))
                except: continue
            
            if not candidates: return False
            t_start = min(candidates, key=lambda x: abs(x - now))
            
            # TAF Bitiş
            y_end, m_end = t_start.year, t_start.month
            if te_d < ts_d: # Gün devri (Ay sonu)
                m_end += 1
                if m_end > 12: m_end = 1; y_end += 1
            
            t_end = safe_dt(y_end, m_end, te_d, te_h)
            
            # METAR (TAF aralığına giren aday)
            m_candidates = []
            for offset in [-1, 0, 1]:
                y, m = t_start.year, t_start.month + offset
                if m < 1: m += 12; y -= 1
                elif m > 12: m -= 12; y += 1
                try:
                    m_candidates.append(safe_dt(y, m, m_d, m_h, m_m))
                except: continue
                
            # 30 dakika tolerans (öncesinde) - TAF'lar genelde 40 geçe yayınlanır, 50 geçe METAR gelir
            t_start_tol = t_start - timedelta(minutes=30)
            for m_dt in m_candidates:
                if t_start_tol <= m_dt <= t_end:
                    return True
                    
            return False
        except Exception:
            return False

    def _is_trend_active(self, trend_header, metar_time_code, trend_type, ref_date=None, buffer_minutes=130):
   
        """
        TREND (BECMG, TEMPO, PROB) periyodunun METAR zamanına göre aktif olup olmadığını kontrol eder.
        UTC zaman dilimi ve gün geçişlerini (ay sonu dahil) dikkate alır.
        """
        try:
            m_match = re.search(r'(\d{2})(\d{2})(\d{2})Z', metar_time_code)
            if not m_match: return True, "Kesin"
            
            m_d, m_h, m_m = int(m_match.group(1)), int(m_match.group(2)), int(m_match.group(3))
            now = ref_date if ref_date else datetime.now(timezone.utc).replace(tzinfo=None)
            metar_dt = self._resolve_dt(m_d, m_h, m_m, now)
            window_end = metar_dt + timedelta(minutes=buffer_minutes)

            if trend_type.startswith('FM'):
                if len(trend_header) == 6:
                    fd, fh, fm = int(trend_header[0:2]), int(trend_header[2:4]), int(trend_header[4:6])
                    fm_dt = self._resolve_dt(fd, fh, fm, now)
                    if fm_dt > window_end:
                        return False, "Pasif"
                    return True, "Kesin"
                return True, "Kesin"

            # Trend Header: DDHH/DDHH (Örn: 1606/1608)
            t_match = re.search(r'(\d{2})(\d{2})\s*/\s*(\d{2})(\d{2})', trend_header)
            if not t_match: return True, "Kesin"

            ts_d, ts_h = int(t_match.group(1)), int(t_match.group(2)) # T1
            te_d, te_h = int(t_match.group(3)), int(t_match.group(4)) # T2
            
            t_start = self._resolve_dt(ts_d, ts_h, 0, now) # T1 objesi
            t_end = self._resolve_dt(te_d, te_h, 0, now)   # T2 objesi
            
            # Kontrol Penceresi (METAR + Buffer)

            # 1. Trend Başlangıcı Pencere İçinde mi? (Gelecek kontrolü)
            # Trend, pencere bitmeden başlamalıdır.
            if t_start > window_end:
                return False, "Pasif"

            # 2. Trend Bitişi METAR'dan önce mi? (Geçmiş kontrolü)
            if t_end < metar_dt:
                if 'BECMG' in trend_type:
                    # BECMG: Sürekli yeni bir duruma geçişi ifade eder. Geri başa dönüş yok.
                    # Bu yüzden bitiş saati geçse bile etkisi devam eder (Kalıcı).
                    return True, "Aktif (Tamamlandı)"
                else:
                    # TEMPO: Süreksiz, geçici durum. Periyot sonu başlangıca döner.
                    return False, "Pasif"
            
            return True, "Kesin"
        except:
            return True, "Kesin"

    def _get_trend_times(self, trend_header, ref_date):
        """Trend başlığından (DDHH/DDHH) başlangıç ve bitiş zamanlarını hesaplar."""
        try:
            t_match = re.search(r'(\d{2})(\d{2})/(\d{2})(\d{2})', trend_header)
            if not t_match: return None, None
            
            ts_d, ts_h = int(t_match.group(1)), int(t_match.group(2))
            te_d, te_h = int(t_match.group(3)), int(t_match.group(4))
            
            now = ref_date
            
            def safe_dt(y, m, d, h, minute=0):
                base = datetime(y, m, 1)
                return base + timedelta(days=d-1, hours=h, minutes=minute)

            # Trend Başlangıç
            candidates = []
            for offset in [-1, 0, 1]:
                y, m = now.year, now.month + offset
                if m < 1: m += 12; y -= 1
                elif m > 12: m -= 12; y += 1
                try:
                    candidates.append(safe_dt(y, m, ts_d, ts_h))
                except: continue
            
            if not candidates: return None, None
            t_start = min(candidates, key=lambda x: abs(x - now))
            
            # Trend Bitiş
            y_end, m_end = t_start.year, t_start.month
            if te_d < ts_d: 
                m_end += 1
                if m_end > 12: m_end = 1; y_end += 1
            
            t_end = safe_dt(y_end, m_end, te_d, te_h)
            return t_start, t_end
        except:
            return None, None

    def check_threshold(self, v1, v2, thresholds):
        """İki değer arasında (örn. Görüş) limit geçişi olup olmadığını kontrol eder."""
        low, high = min(v1, v2), max(v1, v2)
        for t in thresholds:
            if low < t <= high: return True
        return False

    def _parse_wind(self, code):
        """Metin içinden rüzgar yönü, hızı ve hamlesini (gust) ayıklar."""
        # Önce Gust ve KT içeren tam formatı dene
        match = re.search(r'\b(\d{3}|VRB)(\d{2,3})(?:G(\d{2,3}))?KT\b', code)
        if match:
            yon = -1 if match.group(1) == "VRB" else int(match.group(1))
            hiz = int(match.group(2))
            gust = int(match.group(3)) if match.group(3) else 0
            return yon, hiz, gust
            
        # Fallback: Eski basit format (Gust yok varsayılır)
        match = re.search(r'\b(\d{3}|VRB)(\d{2,3})KT\b', code)
        if match:
            yon = -1 if match.group(1) == "VRB" else int(match.group(1))
            hiz = int(match.group(2))
            return yon, hiz, 0
            
        return None

    def _parse_ceiling(self, code):
        """Metin içinden bulut tavanını (Ceiling) veya Dikey Görüşü (VV) ayıklar."""
        if any(x in code for x in ['CAVOK', 'SKC', 'NSC', 'CLR']):
            return 9999, False
        
        vv = re.search(r'VV(\d{3})', code)
        if vv: return int(vv.group(1)) * 100, True
        
        clouds = re.findall(r'(BKN|OVC)(\d{3})', code)
        if clouds:
            return min([int(c[1]) * 100 for c in clouds]), False
            
        # EĞER FEW/SCT VARSA AMA BKN/OVC YOKSA, TAVAN YOK (9999) KABUL ET.
        # Bu, trend grubunda bulut değişimi olduğunda (örn: VV002 -> SCT010) persistence'ı kırar.
        if re.search(r'(FEW|SCT)(\d{3})', code):
            return 9999, False

        return None

    def _parse_cloud_layers(self, code):
        """Tüm bulut katmanlarını (Tip, Yükseklik) listesi olarak döner."""
        layers = []
        matches = re.findall(r'\b(FEW|SCT|BKN|OVC|VV)(\d{3})\b', code)
        for m in matches:
            layers.append((m[0], int(m[1])*100))
        return layers

    def _parse_temp_dew(self, code):
        """Metin içinden Sıcaklık/İşba ayıklar. Örn: 15/08, M01/M03"""
        match = re.search(r'\b(M?\d{2})/(M?\d{2})?\b', code)
        if match:
            temp_str = match.group(1)
            dew_str = match.group(2)
            
            temp = -int(temp_str[1:]) if temp_str.startswith('M') else int(temp_str)
            dew = None
            if dew_str:
                dew = -int(dew_str[1:]) if dew_str.startswith('M') else int(dew_str)
            
            return temp, dew
        return None, None

    def _parse_qnh(self, code):
        """Metin içinden QNH basınç değerini ayıklar. Örn: Q1013"""
        match = re.search(r'\bQ(\d{4})\b', code)
        if match:
            return int(match.group(1))
        return None

    def _parse_visibility(self, code):
        """Metin içinden görüş mesafesini (Visibility) ayıklar."""
        if 'CAVOK' in code:
            return 10000
            
        # 4 haneli sayıları bul (Zaman ve QNH kodlarını hariç tut)
        for m in re.finditer(r'\b(\d{4})\b', code):
            val = int(m.group(1))
            start = m.start()
            
            # Öncesindeki metni kontrol et (TL, AT, FM, Q)
            context = code[max(0, start-5):start].upper()
            if re.search(r'(TL|AT|FM|Q)\s*$', context):
                continue
                
            return val
            
        return None

    def _parse_weather(self, code, ignore_light=True):
        """Metin içindeki kritik hava hadiselerini (Weather) ayıklar."""
        if 'NSW' in code:
            return set()
            
        # RE (Recent) kodlarını temizle (Örn: RESHRA, RERA)
        code_clean = re.sub(r'\bRE[A-Z]+\b', '', code)

        # VC (Vicinity - Meydan Civarı) kodlarını temizle (Örn: VCTS, VCSH). VC içeren hadiseler trend uyumunda değerlendirilmez.
        code_clean = re.sub(r'\bVC[A-Z]+\b', '', code_clean)

        if ignore_light:
            # Hafif yağmur/sağanak/çisenti/kar (-RA, -SHRA, -DZ, -SHDZ, -SN, -SHSN, -SG) trend uyumunda kritik sayılmaz.
            code_clean = re.sub(r'(?<![A-Z])-(?:SH)?(?:RA|DZ|SN|SG)\b', '', code_clean)
            if not getattr(self, 'kati_icao_kurallari', False):
                # ESNEK MOD (Varsayılan): Orta şiddetli sağanak (SHRA) da kritik sayılmasın.
                code_clean = re.sub(r'\bSHRA\b', '', code_clean)

        search_text = code_clean
        found = set()
        for label, pattern in self.kritik_hadiseler.items():
            if re.search(pattern, search_text):
                found.add(label)
        
        return found if found else None

    def _parse_weather_full(self, code):
        """
        Parses all weather phenomena from a code string, including intensity.
        Returns a set of weather codes like {'-SHRA', 'TSRA', 'FG'}.
        """
        if not code:
            return set()
        
        # This regex finds weather codes with optional intensity (+, -) and proximity (VC) prefixes.
        pattern = r'\b(?:\-|\+|VC)?(?:TS|SH|FZ|BL|DR|MI|BC|PR|RA|DZ|SN|SG|PL|GR|GS|UP|FG|BR|HZ|FU|VA|DU|SA|SS|DS){1,3}\b'
        
        # Exclude RE codes from this search for active weather
        code_no_re = re.sub(r'\bRE[A-Z]+\b', '', code)
        
        matches = re.findall(pattern, code_no_re)
        
        return set(matches)

    def extract_active_and_recent_weather(self, code):
        """Metin içindeki aktif hadiseleri, geçmiş (RE) hadiseleri ve civar (VC) hadiselerini set olarak döner."""
        # Trend ve RMK gruplarını keserek sadece ana gövdedeki aktif hadiseleri bul.
        # Çünkü trenddeki 'NSW' veya hadiseler aktif durumu etkilememeli.
        main_part = code
        for token in ['BECMG', 'TEMPO', 'NOSIG', 'RMK']:
            if token in main_part:
                main_part = main_part.split(token)[0]

        # Use the new full parser for active weather
        all_wx = self._parse_weather_full(main_part)

        # VC (Civar) hadiseler
        vc_wx = {wx for wx in all_wx if wx.startswith('VC')}
        # Aktif hadiselerden VC olanları çıkar
        active_wx = all_wx - vc_wx
        
        # RE (Geçmiş) hadiseler (Ana gövdede aranır)
        recent_wx = {match for match in re.findall(r'\bRE([A-Z]+)\b', main_part)}
            
        return active_wx, recent_wx, vc_wx

    def _extract_body(self, text):
        """Rapor metnini rüzgar grubundan itibaren alır (Başlıkları ve zamanı atlar)."""
        # Rüzgar deseni: 3 hane yön (veya VRB) + 2/3 hane hız + (opsiyonel G + hamle) + KT
        match = re.search(r'\b(\d{3}|VRB)\d{2,3}(?:G\d{2,3})?KT\b', text)
        if match:
            return text[match.start():]
        return text

    def _compare_values(self, t_vals, m_vals):
        """TAF/Trend değerleri ile METAR değerlerini karşılaştırır ve hataları listeler."""
        t_wind, t_vis, t_cig, t_wx = t_vals
        m_wind, m_vis, m_cig, m_wx = m_vals
        errors = []

        # Rüzgar
        t_yon, t_hiz, _ = t_wind # Gust (Hamle) kontrolü devre dışı
        m_yon, m_hiz, _ = m_wind # Gust (Hamle) kontrolü devre dışı
        
        if abs(t_hiz - m_hiz) >= 10:
            errors.append("Rüzgar Hızı (Fark >= 10KT)")
        
        # Rüzgar Yönü: Her iki taraf da variable (-1) değilse karşılaştır
        # Variable rüzgarla yöne bakılmaz (ICAO kural)
        if t_yon != -1 and m_yon != -1:
            yon_f = abs(t_yon - m_yon)
            if yon_f > 180: yon_f = 360 - yon_f
            # Yön farkı kontrolü: >=60° SADECE hız >= 10KT durumlarda söz konusu
            if yon_f >= 60 and (t_hiz >= 10 or m_hiz >= 10):
                errors.append("Rüzgar Yönü (Fark >= 60°)")
        # Eğer sadece biri variable ise, yön farklılığı görmezden gel (ICAO = normal)
        elif (t_yon == -1) != (m_yon == -1):
            pass  # Variable durumda yön tutarsızlığı error olmaz

        # Görüş
        low_v = min(t_vis, m_vis)
        high_v = max(t_vis, m_vis)
        crossed_ths = []
        for th in self.esikler_ruyet:
            if low_v < th <= high_v:
                crossed_ths.append(str(th))
        if crossed_ths:
            th_str = ",".join(crossed_ths)
            errors.append(f"Görüş {th_str} m kıstası")

        # Tavan
        t_c_h, t_is_vv = t_cig
        m_c_h, m_is_vv = m_cig
        low = min(t_c_h, m_c_h)
        high = max(t_c_h, m_c_h)
        crossed_ths = []
        for th in self.esikler_tavan:
            if low < th <= high:
                crossed_ths.append(str(th))
        if crossed_ths:
            label = "Dikey Görüş" if (t_is_vv or m_is_vv) else "Tavan"
            th_str = ",".join(crossed_ths)
            errors.append(f"{label} {th_str} ft kıstası")
        
        # Hadise (Weather)
        # None ise (belirtilmemişse) boş küme kabul etme, karşılaştırma yapma (persist durumu dışarıda yönetilir)
        # Ancak burada t_wx ve m_wx kesinleşmiş setler olarak gelir.
        set_t = t_wx if t_wx is not None else set()
        set_m = m_wx if m_wx is not None else set()
        
        # Farklılık var mı? (Sadece kritik hadiseler listesindekiler için)
        diff = set_t.symmetric_difference(set_m)
        if diff:
            errors.append("Hava Hadisesi")
                
        return errors

    def _parse_all_taf_trends(self, text):
        """TAF metni içindeki tüm BECMG, TEMPO ve PROB gruplarını ayıklar."""
        trends = []
        clean_taf = " ".join(text.split())
        change_regex = r'(FM\d{6}|(?:BECMG|PROB\d{2}\s+TEMPO|TEMPO|PROB\d{2})\s+\d{4}/\d{4})'
        changes = list(re.finditer(change_regex, clean_taf))

        def get_wx_until_next_fm(start_idx):
            fm_iter = re.finditer(r'FM\d{6}', clean_taf)
            end_idx = len(clean_taf)
            for m in fm_iter:
                if m.start() > start_idx:
                    end_idx = m.start()
                    break
            return clean_taf[start_idx:end_idx].strip()

        for i, m in enumerate(changes):
            match_text = m.group(1)
            group_type = 'FM' if match_text.startswith('FM') else match_text.split()[0]
            start_idx = m.end()

            if group_type in ['FM', 'BECMG']:
                full_wx = get_wx_until_next_fm(m.start())
            else:
                end_idx = changes[i+1].start() if i+1 < len(changes) else len(clean_taf)
                wx_text = clean_taf[start_idx:end_idx].strip()
                full_wx = f"{match_text} {wx_text}"

            time_str = match_text[2:] if group_type == 'FM' else match_text.split()[-1]
            
            w = self._parse_wind(full_wx)
            v = self._parse_visibility(full_wx)
            c = self._parse_ceiling(full_wx)
            wx = self._parse_weather(full_wx)

            trends.append({
                'type': group_type,
                'time': time_str,
                'raw': full_wx,
                'wind': w,
                'vis': v,
                'cig': c,
                'wx': wx
            })
        return trends
        
    def _generate_recommendation(self, error_str, expected_vals, metar_dt=None, target_dt=None, trend_raw=""):
        """Uyumsuzluk kalemine göre beklenen (TAF) değeri TAVSİYE olarak döndürür."""
        if not expected_vals or len(expected_vals) < 4: return ""
        t_wind, t_vis, t_cig, t_wx = expected_vals
        
        prefix = "💡 TAVSİYE:"
        is_nosig = 'NOSIG' in trend_raw
        
        trend_prefix = ""
        if is_nosig:
            if target_dt and metar_dt:
                diff_min = (target_dt - metar_dt).total_seconds() / 60.0
                if 15 < diff_min <= 75:
                    trend_prefix = f"BECMG TL{target_dt.strftime('%H%M')} "
                else:
                    trend_prefix = "BECMG "
            else:
                trend_prefix = "BECMG "
        
        if "Rüzgar" in error_str and t_wind:
            t_yon, t_hiz, t_gust = t_wind
            y_str = "VRB" if t_yon == -1 else f"{t_yon:03d}"
            g_str = f"G{t_gust:02d}" if t_gust else ""
            w_str = f"{y_str}{t_hiz:02d}{g_str}KT"
            if is_nosig: return f"{prefix} İyileşme/Dönüş için '{trend_prefix}{w_str}' kullanılmalıydı."
            return f"{prefix} Rüzgar {w_str} bekleniyordu."
        elif "Görüş" in error_str and t_vis is not None:
            vis_str = f"{t_vis}" if t_vis != 10000 else "9999"
            if is_nosig: return f"{prefix} İyileşme/Dönüş için '{trend_prefix}{vis_str}' kullanılmalıydı."
            v_desc = f"{t_vis} m" if t_vis != 10000 else "10 km veya üzeri (CAVOK)"
            return f"{prefix} Görüş {v_desc} bekleniyordu."
        elif ("Tavan" in error_str or "Dikey Görüş" in error_str) and t_cig is not None:
            if t_cig == (9999, False):
                c_str = "NSC"
            elif t_cig[1]:
                c_str = f"VV{t_cig[0]//100:03d}"
            else:
                c_str = f"BKN{t_cig[0]//100:03d}"
            if is_nosig: return f"{prefix} İyileşme/Dönüş için '{trend_prefix}{c_str}' kullanılmalıydı."
            c_desc = "NSC/CAVOK (Limit altı bulut beklenmiyor)" if t_cig == (9999, False) else f"{c_str} (veya OVC)"
            return f"{prefix} Tavan/VV {c_desc} bekleniyordu."
        elif "Hadise" in error_str:
            wx_str = " ".join(t_wx) if t_wx else "NSW"
            if is_nosig: return f"{prefix} İyileşme/Dönüş için '{trend_prefix}{wx_str}' kullanılmalıydı."
            wx_desc = ", ".join(t_wx) if t_wx else "NSW (Önemli hadise beklenmiyor)"
            return f"{prefix} Hadise '{wx_desc}' bekleniyordu."
        return ""

    def _fmt_vals(self, vals):
        """Rapor için değerleri formatlar."""
        w, v, c, wx = vals
        v_str = f"{v}m" if v is not None else "Yok"
        c_str = (f"VV{c[0]//100:03d}" if c[1] else f"CIG{c[0]:03d}") if c != (9999, False) else "NSC"
        wx_str = ",".join(sorted(wx)) if wx else "NSW"
        return f"Vis:{v_str} CIG:{c_str} Wx:{wx_str}"

    def _fmt_comparison(self, t_vals, m_vals, t_label="TAF", m_label="METAR"):
        """TAF ve METAR değerlerini karşılaştırmalı formatlar."""
        _, t_v, t_c, t_wx = t_vals
        _, m_v, m_c, m_wx = m_vals
        
        # Değerleri formatla
        tv_str = f"{t_v}m" if t_v is not None else "Yok"
        mv_str = f"{m_v}m" if m_v is not None else "Yok"
        tc_str = (f"VV{t_c[0]//100:03d}" if t_c[1] else f"CIG{t_c[0]:03d}") if t_c != (9999, False) else "NSC"
        mc_str = (f"VV{m_c[0]//100:03d}" if m_c[1] else f"CIG{m_c[0]:03d}") if m_c != (9999, False) else "NSC"
        twx_str = ",".join(sorted(t_wx)) if t_wx else "NSW"
        mwx_str = ",".join(sorted(m_wx)) if m_wx else "NSW"
        
        return f"{t_label}: Vis:{tv_str} CIG:{tc_str} Wx:{twx_str} vs {m_label}: Vis:{mv_str} CIG:{mc_str} Wx:{mwx_str}"

    def _clean_wx_by_vis(self, vis, wx_set):
        """Görüş mesafesi yüksekse (5000m+) sis/pus vb. hadiseleri temizler."""
        if vis is not None and vis > 5000 and wx_set:
            new_wx = wx_set.copy()
            # Görüş kısıtlayıcı hadiseler
            for bad in ['BR', 'HZ', 'FG', 'FU', 'VA', 'DU', 'SA']:
                new_wx.discard(bad)
            
            # FZFG durumu: FG gitti, FZ kaldıysa ve yağış yoksa FZ'yi de sil
            if 'FZ' in new_wx:
                precips = {'RA', 'DZ', 'SN', 'SG', 'PL', 'GR', 'GS'}
                if not new_wx.intersection(precips):
                    new_wx.discard('FZ')
            return new_wx
        return wx_set

    def _find_applicable_tafs(self, metar_time_code, taf_list):
        """
        METAR saatine göre geçerli TAF'ları bulur (TÜM SAATLER UTC).
        
        KURAL (Kullanıcı İsteği): 
        - 05:50 METAR -> Yalnızca 04:40 TAF ile kıyaslanır.
        - 04:50 METAR -> Hem 04:40 TAF hem de 01:40 TAF ile kıyaslanır.
        (Yani METAR yayın zamanı, son TAF'ın yayın zamanından sonraki 60 dakika içindeyse geçiş periyodu kabul edilir ve 2 TAF'a da bakılır).
        """
        try:
            # METAR saatini çöz (DDHHMMZ) - UTC
            m_match = re.search(r'(\d{2})(\d{2})(\d{2})Z', metar_time_code)
            if not m_match: return []
            m_d, m_h, m_m = int(m_match.group(1)), int(m_match.group(2)), int(m_match.group(3))
            
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            metar_dt = self._resolve_dt(m_d, m_h, m_m, now)
            if not metar_dt: return []
            
            parsed_tafs = []
            
            for taf_raw, taf_validity in taf_list:
                # TAF'ın yayın saatini bul
                taf_hour_match = re.search(r'(?:TAF|FC|FCTT70|SATT70)\s+(?:\w+\s+)?(\d{2})(\d{2})(\d{2})Z', taf_raw)
                if not taf_hour_match:
                    taf_hour_match = re.search(r'(\d{2})(\d{2})(\d{2})Z', taf_raw)
                
                if taf_hour_match:
                    t_d = int(taf_hour_match.group(1))
                    t_h = int(taf_hour_match.group(2))
                    t_m = int(taf_hour_match.group(3))
                    taf_pub_dt = self._resolve_dt(t_d, t_h, t_m, metar_dt)
                else:
                    continue
                    
                if not taf_pub_dt: continue
                
                # Gelecekte yayınlanmış bir TAF ile geçmişteki METAR'ı kıyaslayamayız
                if taf_pub_dt > metar_dt:
                    continue
                    
                parsed_tafs.append({
                    'raw': taf_raw,
                    'validity': taf_validity,
                    'pub_dt': taf_pub_dt
                })
            
            if not parsed_tafs: return []
            
            # TAF'ları yayın zamanına göre en yeniden en eskiye doğru sırala
            parsed_tafs.sort(key=lambda x: x['pub_dt'], reverse=True)
            
            newest_taf = parsed_tafs[0]
            result = [(newest_taf['raw'], newest_taf['validity'])]
            
            # METAR ile en yeni TAF'ın yayın saati arasındaki fark (dakika)
            diff_minutes = (metar_dt - newest_taf['pub_dt']).total_seconds() / 60.0
            
            # Geçiş periyodu: TAF yayınlandıktan sonraki ilk 60 dakika (Örn: 04:40 TAF -> 04:50 METAR)
            # Bu durumda bir önceki TAF da geçerliliğini korur ve değerlendirilir.
            # Ancak, en yeni TAF bir AMD veya COR ise geçiş periyodu iptal edilir, sadece güncel TAF'a bakılır.
            is_amendment = any(x in newest_taf['raw'].upper() for x in ['AMD', 'COR', 'AAA', 'AAB', 'AAC'])
            if diff_minutes <= 60.0 and len(parsed_tafs) > 1 and not is_amendment:
                second_newest = parsed_tafs[1]
                result.append((second_newest['raw'], second_newest['validity']))
            
            return result
        except Exception as e:
            logging.error(f"TAF arama hatası: {e}")
            return []

    def analiz_et_multi(self, taf_list, metar_raw, trend_raw, ref_date=None):
        """
        Birden fazla TAF'ı METAR'a göre değerlendir (KURAL: aynı saatte 2 TAF, diğerlerde 1 TAF).
        Her TAF için ayrı değerlendirme raporu oluştur.
        
        KURAL:
        - METAR ve TAF aynı UTC saatte → 2 TAF ile karşılaştır (aynı saat + başka saat)
        - METAR ve TAF başka saatlarda → tek TAF ile karşılaştır
        
        Args:
            taf_list: [(taf_raw, taf_validity_period), ...] listesi
            metar_raw: METAR verisi (UTC)
            trend_raw: METAR trend verisi (varsa)
            ref_date: Referans tarihi
        
        Returns:
            (score, status, [lines]) - birleştirilmiş rapor
        """
        if not taf_list:
            return 0, "VERİ BULUNAMADI", ["Hiçbir TAF verilmedi."]
        
        # METAR zamanını bul (UTC)
        metar_time_match = re.search(r'\b(\d{2})(\d{2})(\d{2})Z\b', metar_raw)
        if not metar_time_match:
            return 0, "VERİ BULUNAMADI", ["METAR saat kodu bulunamadı."]
        
        # Geçerli TAF'ları filtrele ve sırala (KURAL: aynı saatte 2 TAF, diğerlerde 1 TAF)
        applicable_tafs = self._find_applicable_tafs(metar_time_match.group(0), taf_list)
        if not applicable_tafs:
            # Fallback: ilk TAF'ı kullan
            applicable_tafs = [taf_list[0]]
        
        # Ana rapor líneleri
        all_report_lines = []
        all_report_lines.append("=" * 70)
        all_report_lines.append("📊 ÇOK TAF ANALİZİ (METAR: {} UTC)".format(metar_time_match.group(0)))
        all_report_lines.append("=" * 70)
        
        # Kural açıklaması
        if len(applicable_tafs) == 2:
            all_report_lines.append("✓ KURAL: Geçiş Periyodu (04:50 vb.) → 2 TAF ile karşılaştırılacak")
        else:
            all_report_lines.append("✓ KURAL: Standart Periyot (05:50 vb.) → Tek TAF ile karşılaştırılacak")
        
        all_report_lines.append(f"Değerlendirilen TAF sayısı: {len(applicable_tafs)}")
        all_report_lines.append("")
        
        # Sonuçları sakla
        best_score = 0
        best_status = "UYUMSUZ"
        consolidated_lines = []
        
        # Her TAF için analiz
        for i, (taf_raw, taf_zaman) in enumerate(applicable_tafs, 1):
            all_report_lines.append("=" * 70)
            all_report_lines.append(f"🔍 Referans TAF {i}: {taf_zaman}")
            all_report_lines.append("=" * 70)
            
            # TAF'ı analiz et
            score, status, report_lines = self.analiz_et(
                taf_raw, metar_raw, trend_raw, 
                taf_zaman=taf_zaman, 
                ref_date=ref_date
            )
            
            # Raporu ekle
            all_report_lines.extend(report_lines)
            all_report_lines.append("")
            
            # En iyi sonucu takip et
            if score > best_score:
                best_score = score
                best_status = status
                consolidated_lines = report_lines
        
        # Özet ekle
        all_report_lines.insert(5, "→ En İyi Sonuç: {} ({})".format(best_status, best_score))
        all_report_lines.insert(6, "")
        
        return best_score, best_status, all_report_lines

    def analiz_et(self, taf_raw, metar_raw, trend_raw, taf_zaman="0412/0512", ref_date=None):
        """Modülün ana denetleme fonksiyonu. TAF ve METAR'ı karşılaştırır."""
        
        # Sonuç Değişkenlerini Başlat (Hata önleme)
        res1 = False
        res2 = False
        res3 = False
        res4 = False
        critical_format_error = False
        valid_trend_evals = 0
        format_error_evals = 0
        format_error_reports = []

        if ref_date is None: ref_date = datetime.now(timezone.utc).replace(tzinfo=None)

        if not taf_raw or not metar_raw:
            return 0, "VERİ BULUNAMADI", ["TAF veya METAR verisi eksik."]

        # Dummy taf_zaman düzeltmesi
        if taf_zaman == "0412/0512" or not taf_zaman:
            tz_match = re.search(r'\b(\d{4}/\d{4})\b', taf_raw)
            if tz_match:
                taf_zaman = tz_match.group(1)

        # Başlıkları temizle (Rüzgar grubundan başlat)
        taf_body = self._extract_body(taf_raw)
        metar_body = self._extract_body(metar_raw)
        
        # TAF Ana kısmını izole et (Trendlerden arındır)
        taf_main_part = re.split(r'\b(BECMG|PROB\d{2}\s+TEMPO|TEMPO|PROB\d{2}|FM\d{6})\b', taf_body)[0].strip()

        # METAR Ana kısmını izole et (Trend ve RMK'dan arındır)
        metar_main_part = metar_body
        for token in ['BECMG', 'TEMPO', 'NOSIG', 'RMK']:
            if token in metar_main_part:
                metar_main_part = metar_main_part.split(token)[0].strip()

        # 1. ZAMAN KONTROLÜ
        metar_dt = None
        t_end_taf = None
        metar_time_match = re.search(r'\b(\d{2})(\d{2})(\d{2})Z\b', metar_raw)
        if not metar_time_match:
            return 0, "VERİ BULUNAMADI", ["METAR saat kodu bulunamadı."]
            
        if taf_zaman and not self.zaman_uygun_mu(taf_zaman, metar_time_match.group(0), ref_date):
            return 0, "TAF YOK", ["METAR saati TAF geçerlilik aralığı dışında."]

        try:
            m_d = int(metar_time_match.group(1))
            m_h = int(metar_time_match.group(2))
            m_m = int(metar_time_match.group(3))
            metar_dt = self._resolve_dt(m_d, m_h, m_m, ref_date)
            
            if taf_zaman:
                _, t_end_taf = self._get_trend_times(taf_zaman, metar_dt)
        except: pass

        m_wind = self._parse_wind(metar_main_part)
        if m_wind is None:
            return 0, "VERİ BULUNAMADI", ["METAR rüzgar verisi okunamadı."]
        m_vis = self._parse_visibility(metar_main_part)
        m_cig = self._parse_ceiling(metar_main_part)
        if m_cig is None: m_cig = (9999, False)
        m_wx = self._parse_weather(metar_main_part)
        metar_vals = (m_wind, m_vis, m_cig, m_wx)

        t_wind = self._parse_wind(taf_main_part)
        if t_wind is None:
            return 0, "VERİ BULUNAMADI", ["TAF rüzgar verisi okunamadı."]
        t_vis = self._parse_visibility(taf_main_part) 
        t_cig = self._parse_ceiling(taf_main_part)
        if t_cig is None: t_cig = (9999, False)
        t_wx = self._parse_weather(taf_main_part)
        taf_vals = (t_wind, t_vis, t_cig, t_wx)
        
        taf_trends = self._parse_all_taf_trends(taf_raw)
        
        # METAR Trend Değerlerini Hazırla
        metar_trend_vals = None
        metar_trend_parts = []
        if trend_raw:
            trend_content = re.split(r'\bRMK\b', trend_raw)[0].strip()
            w = self._parse_wind(trend_content)
            mt_wind = w if w is not None else m_wind
            v = self._parse_visibility(trend_content)
            mt_vis = v if v is not None else m_vis
            c = self._parse_ceiling(trend_content)
            mt_cig = c if c is not None else m_cig
            wx = self._parse_weather(trend_content)
            
            is_becoming_or_tempo = 'BECMG' in trend_raw or 'TEMPO' in trend_raw
            all_wx_codes = [
                'TS', 'SH', 'FZ', 'BL', 'DR', 'MI', 'BC', 'PR', 'RA', 'DZ', 'SN', 'SG', 
                'PL', 'GR', 'GS', 'UP', 'FG', 'BR', 'HZ', 'FU', 'VA', 'DU', 'SA', 'SS', 'DS'
            ]
            wx_pattern = r'\b(?:\-|\+|VC)?(?:' + '|'.join(all_wx_codes) + r'){1,3}\b|NSW'
            mentions_any_weather = re.search(wx_pattern, trend_content)

            if is_becoming_or_tempo and mentions_any_weather:
                mt_wx = wx if wx is not None else set()
            else:
                mt_wx = wx.copy() if wx is not None else (m_wx.copy() if m_wx else set())
            
            mt_wx = self._clean_wx_by_vis(mt_vis, mt_wx)
            if mt_vis is not None and mt_vis > 5000 and mt_cig[1]:
                mt_cig = (9999, False)
            
            metar_trend_vals = (mt_wind, mt_vis, mt_cig, mt_wx)
            
            # METAR Trendlerini Ayrıştır (Çoklu trend durumunda doğru eşleştirme için)
            # Örn: "BECMG TL2000 ... TEMPO TL2100 ..." -> [{'type':'BECMG', 'content':'...'}, {'type':'TEMPO', 'content':'...'}]
            tokens = re.split(r'\b(BECMG|TEMPO|NOSIG)\b', trend_content)
            i = 1
            while i < len(tokens):
                t_type = tokens[i]
                t_content = tokens[i+1] if i+1 < len(tokens) else ""
                metar_trend_parts.append({'type': t_type, 'content': t_content})
                i += 2

        # --- DETAYLI ANALİZ ---
        report_lines = []
        nosig_conflicts = []
        
        ana_hadise_bust = False
        trend_hadise_bust = False
        trend_bust_var = False
        active_trends_found = False

        # Gösterim için metinleri hazırla
        taf_header = taf_raw[:taf_raw.find(taf_body)] if taf_body in taf_raw else ""
        taf_ana_display = (taf_header + taf_main_part).strip().replace('\n', ' ')
        metar_ana_display = (metar_raw.replace(trend_raw, "") if trend_raw else metar_raw).strip().replace('\n', ' ')
        metar_trend_display = trend_raw.strip().replace('\n', ' ') if trend_raw else "YOK"

        # METAR Trend Zaman Detaylarını Ekle (FM/TL/AT)
        if trend_raw:
            time_details = []
            for m in re.finditer(r'\b(FM|TL|AT)(\d{4})\b', trend_raw):
                t_type, t_val = m.group(1), m.group(2)
                label = "Başlangıç" if t_type == 'FM' else "Bitiş" if t_type == 'TL' else "Saat"
                time_details.append(f"[{label}: {t_val[:2]}:{t_val[2:]}Z]")
            if time_details:
                metar_trend_display += " " + " ".join(time_details)

        # 1. TAF ANA - METAR ANA
        report_lines.append("============================================================")
        report_lines.append(" 🔹 TAF ANA GÖVDE ANALİZİ")
        report_lines.append("============================================================")
        errors_1 = self._compare_values(taf_vals, metar_vals)
        
        better_info_1 = ""
        if errors_1:
            errors_1, better_info_1 = self._check_better_conditions(errors_1, taf_vals, metar_vals)
            
        report_lines.append(" [1] METAR ANA GÖVDE İLE KIYASLAMA")
        report_lines.append(f"  ├─ TAF Beklentisi : {taf_ana_display}")
        report_lines.append(f"  ├─ METAR Durumu   : {metar_ana_display}")
        if not errors_1:
            report_lines.append(f"  └─ Sonuç          : ✅ UYUMLU{better_info_1}")
            res1 = True
        else:
            report_lines.append(f"  └─ Sonuç          : ❌ UYUMSUZ")
            for e in errors_1: 
                report_lines.append(f"       ▪ {e}")
                rec = self._generate_recommendation(e, taf_vals)
                if rec: report_lines.append(f"         {rec}")
        report_lines.append("")

        # 3. TAF ANA - METAR TREND (Varsa)
        if metar_trend_vals:
            errors_3 = self._compare_values(taf_vals, metar_trend_vals)
            
            better_info_3 = ""
            if errors_3:
                errors_3, better_info_3 = self._check_better_conditions(errors_3, taf_vals, metar_trend_vals)
                
            report_lines.append(" [2] METAR TREND İLE KIYASLAMA")
            report_lines.append(f"  ├─ TAF Beklentisi : {taf_ana_display}")
            report_lines.append(f"  ├─ METAR Trendi   : {metar_trend_display}")
            if not errors_3:
                report_lines.append(f"  └─ Sonuç          : ✅ UYUMLU{better_info_3}")
                res3 = True
            else:
                report_lines.append(f"  └─ Sonuç          : ❌ UYUMSUZ")
                for e in errors_3: 
                    report_lines.append(f"       ▪ {e}")
                    rec = self._generate_recommendation(e, taf_vals, metar_dt=metar_dt, target_dt=t_end_taf, trend_raw=trend_raw)
                    if rec: report_lines.append(f"         {rec}")
                    if "Hadise" in e:
                        ana_hadise_bust = True
            report_lines.append("")

        # 2 & 4. TAF TRENDLERİ
        if taf_trends:
            report_lines.append("============================================================")
            report_lines.append(" 🔹 TAF TRENDLERİ ANALİZİ")
            report_lines.append("============================================================")
            for i, tr in enumerate(taf_trends, 1):
                # Zaman kontrolü
                is_active = True
                if tr['time'] and metar_time_match:
                    res = self._is_trend_active(tr['time'], metar_time_match.group(0), tr['type'], ref_date, buffer_minutes=130)
                    is_active = res[0] if isinstance(res, tuple) else res
                
                if not is_active: continue
                
                # TAF trendinin başlama zamanını bul (RE kuralı ve METAR Trend eşleşmeleri için)
                t_start, t_end = None, None
                if tr['time'] and metar_dt:
                    t_start, t_end = self._get_trend_times(tr['time'], metar_dt)
                elif tr['type'].startswith('FM') and metar_dt:
                    try: t_start = self._resolve_dt(int(tr['type'][2:4]), int(tr['type'][4:6]), int(tr['type'][6:8]), metar_dt)
                    except: pass

                # Trend değerlerini kullan, yoksa ana değerleri (Persistence/Süreklilik)
                if tr['type'].startswith('FM'):
                    # ICAO Kuralı: FM grupları kendinden öncekileri sıfırlar. 
                    # Belirtilmeyen hadise bitmiş (NSW) veya hava temiz kabul edilir.
                    # Belirtilmeyen visibility = NSC (9999 feet, açık gökyüzü)
                    eff_wind = tr['wind'] if tr['wind'] is not None else t_wind
                    eff_vis = tr['vis'] if tr['vis'] is not None else 9999  # NSC: No Significant Cloud
                    eff_cig = tr['cig'] if tr['cig'] is not None else (9999, False)
                    eff_wx = tr['wx'] if tr['wx'] is not None else set()  # NSW: No Significant Weather
                else:
                    # BECMG / TEMPO gruplarında belirtilmeyen değerler ana TAF'tan aynen devam eder.
                    eff_wind = tr['wind'] if tr['wind'] is not None else t_wind
                    eff_vis = tr['vis'] if tr['vis'] is not None else t_vis
                    eff_cig = tr['cig'] if tr['cig'] is not None else t_cig
                    eff_wx = tr['wx'] if tr['wx'] is not None else t_wx

                eff_wx = self._clean_wx_by_vis(eff_vis, eff_wx)
                
                # Görüş > 5000m ise VV (Dikey Görüş) fiziksel olarak barınamaz, temizle.
                # VV (Vertical Visibility) sadece kısıtlı görüş (FG, VV alt limit) durumunda kullanılır
                if eff_vis is not None and eff_vis >= 9000 and eff_cig[1]: # eff_cig[1] -> is_vv
                    # Açık hava (>5000m) VV değerini desteklemez
                    eff_cig = (9999, False)
                
                tr_vals = (eff_wind, eff_vis, eff_cig, eff_wx)
                
                # A. TAF TREND vs METAR ANA
                tr_errors_ana = self._compare_values(tr_vals, metar_vals)

                # <<< YENİ KURAL (AKILLANDIRILMIŞ): GEÇMİŞ HADİSE (RE) KONTROLÜ >>>
                # Eğer METAR'da bir hadise 'RE' (Recent) olarak raporlanıyorsa,
                # ve aynı hadise artık 'aktif' değilse (ya da METAR trendinde beklenmiyorsa), bu TAF trendi 'tamamlanmış' kabul edilir.
                active_wx, recent_wx, _ = self.extract_active_and_recent_weather(metar_main_part)
                trend_wx_full = self._parse_weather_full(tr['raw'])
                metar_trend_wx_full = self._parse_weather_full(trend_raw) if trend_raw else set()
                get_root = lambda wx_codes: {re.sub(r'^[\-\+]', '', code) for code in wx_codes}
                trend_wx_roots = get_root(trend_wx_full)
                active_wx_roots = get_root(active_wx | metar_trend_wx_full)
                
                is_related = False
                for twx in trend_wx_roots:
                    for awx in active_wx_roots:
                        if twx in awx or awx in twx:
                            is_related = True
                            break
                    if is_related: break
                
                is_before_trend_start = bool(t_start and metar_dt and metar_dt < t_start)
                
                is_re_skipped = False
                if not trend_wx_roots.isdisjoint(recent_wx) and not is_related and not is_before_trend_start:
                    # Sadece hava hadisesi dışında ICAO limitlerini aşan bir fark (Rüzgar vb.) yoksa pasif kabul et
                    non_wx_errors = [e for e in tr_errors_ana if "Hadise" not in e]
                    if not non_wx_errors:
                        is_re_skipped = True
                
                if is_re_skipped:
                    report_lines.append(f" ⏳ ARA TAF {i} ({tr['type']} {tr['time']})")
                    report_lines.append(f"  └─ ℹ️ DURUM: TAF Trend hadisesi ({', '.join(trend_wx_roots)}) METAR'da 'RE' olarak raporlandı ve artık aktif/beklenen değil. Trend pasif kabul edildi.\n")
                    continue # Bu trendi atla ve bir sonrakine geç
                # <<< BİTTİ >>>

                active_trends_found = True
                report_lines.append(f" ⏳ ARA TAF {i} ({tr['type']} {tr['time']})")

                # --- HATA DÜZELTME: Bozuk kod bloğu onarıldı ---
                better_info_ana = ""
                if tr_errors_ana:
                    tr_errors_ana, better_info_ana = self._check_better_conditions(tr_errors_ana, tr_vals, metar_vals, base_vals=taf_vals)

                report_lines.append("  [A] METAR ANA GÖVDE İLE KIYASLAMA")
                report_lines.append(f"   ├─ TAF Trendi  : {tr['raw']}")
                report_lines.append(f"   ├─ METAR Durumu: {metar_ana_display}")
                if not tr_errors_ana:
                    report_lines.append(f"   └─ Sonuç       : ✅ UYUMLU{better_info_ana}")
                    
                    # NOSIG ve Rüzgar Farkı Açıklaması
                    if trend_raw and 'NOSIG' in trend_raw and tr_vals[0] and metar_vals[0]:
                        t_yon, t_hiz, _ = tr_vals[0]
                        m_yon, m_hiz, _ = metar_vals[0]
                        if t_hiz != m_hiz and abs(t_hiz - m_hiz) < 10:
                            report_lines.append(f"        ℹ️ BİLGİ: TAF Trend rüzgarı ({t_hiz}KT) ile METAR rüzgarı ({m_hiz}KT) farkı <10KT olduğu için NOSIG ile çelişmez.")
                    
                    res2 = True
                else:
                    report_lines.append(f"   └─ Sonuç       : ❌ UYUMSUZ")
                    for e in tr_errors_ana: 
                        report_lines.append(f"        ▪ {e}")
                        rec = self._generate_recommendation(e, tr_vals)
                        if rec: report_lines.append(f"          {rec}")
                        if "Rüzgar" in e and trend_raw and 'NOSIG' in trend_raw:
                            report_lines.append(f"        ℹ️ ÇELİŞKİ: METAR 'NOSIG' (değişim yok) veriyor ancak TAF Trendi rüzgarda limit dışı (>=10KT) değişim bekliyor.")
                report_lines.append("")

                # B. TAF TREND vs METAR TREND (Varsa)
                if metar_trend_vals:
                    # METAR Trend Zaman Kontrolü
                    skip_metar_trend_check = False
                    
                    trend_format_error = None
                    
                    # --- YENİ KURAL: KISMEN VEYA TAM GERÇEKLEŞME VE AKILLI HEDEF SEÇİMİ ---
                    # TAF'ta TEMPO varsa; METAR Ana'da gerçekleşen parametrelerin
                    # METAR Trend'inde BECMG ile TAF Ana'ya dönmesi, gerçekleşmeyenlerin ise
                    # TEMPO ile beklenmesi kuralını denetler.
                    gerceklesenler = []
                    beklenenler = []
                    if 'TEMPO' in tr['type'] and trend_raw:
                        smart_target = list(tr_vals)
                        
                        # 1. Rüzgar Gerçekleşmiş mi? (METAR Ana ile TAF Trend uyumlu mu?)
                        # YENİ MANTIK: Gerçekleşmiş sayılması için Ana TAF'tan KOPMUŞ, TEMPO'ya OTURMUŞ olması şart.
                        ana_err = any("Rüzgar" in e for e in self._compare_values((taf_vals[0], t_vis, t_cig, t_wx), metar_vals))
                        tmp_err = any("Rüzgar" in e for e in self._compare_values((tr_vals[0], t_vis, t_cig, t_wx), metar_vals))
                        if ana_err and not tmp_err:
                             smart_target[0] = taf_vals[0]
                             gerceklesenler.append("Rüzgar")
                        elif tr_vals[0] != taf_vals[0]:
                             beklenenler.append("Rüzgar")
                             
                        # 2. Görüş Gerçekleşmiş mi?
                        ana_err = any("Görüş" in e for e in self._compare_values((t_wind, taf_vals[1], t_cig, t_wx), metar_vals))
                        tmp_err = any("Görüş" in e for e in self._compare_values((t_wind, tr_vals[1], t_cig, t_wx), metar_vals))
                        if ana_err and not tmp_err:
                             smart_target[1] = taf_vals[1]
                             gerceklesenler.append("Görüş")
                        elif tr_vals[1] != taf_vals[1]:
                             beklenenler.append("Görüş")
                             
                        # 3. Tavan Gerçekleşmiş mi?
                        ana_err = any("Tavan" in e or "Dikey" in e for e in self._compare_values((t_wind, t_vis, taf_vals[2], t_wx), metar_vals))
                        tmp_err = any("Tavan" in e or "Dikey" in e for e in self._compare_values((t_wind, t_vis, tr_vals[2], t_wx), metar_vals))
                        if ana_err and not tmp_err:
                             smart_target[2] = taf_vals[2]
                             gerceklesenler.append("Tavan/VV")
                        elif tr_vals[2] != taf_vals[2]:
                             beklenenler.append("Tavan/VV")
                             
                        # 4. Hadise Gerçekleşmiş mi?
                        ana_err = any("Hadise" in e for e in self._compare_values((t_wind, t_vis, t_cig, taf_vals[3]), metar_vals))
                        tmp_err = any("Hadise" in e for e in self._compare_values((t_wind, t_vis, t_cig, tr_vals[3]), metar_vals))
                        if ana_err and not tmp_err:
                             smart_target[3] = taf_vals[3]
                             gerceklesenler.append("Hadise")
                        elif tr_vals[3] != taf_vals[3] and tr_vals[3]:
                             beklenenler.append("Hadise")
                             
                        target_vals_for_comparison = tuple(smart_target)
                        
                        if gerceklesenler or beklenenler:
                            report_lines.append(f"   ℹ️ Kısmi/Tam Gerçekleşme (Süreksiz Durum) Analizi:")
                            if gerceklesenler:
                                report_lines.append(f"      + Gerçekleşen (BECMG ile Ana TAF'a iyileşme/dönüş beklenir): {', '.join(gerceklesenler)}")
                            if beklenenler:
                                report_lines.append(f"      - Henüz Gerçekleşmeyen (TEMPO ile beklenir): {', '.join(beklenenler)}")
                                
                        # EĞER GERÇEKLEŞEN BİR ŞEY VARSA VE NOSIG KULLANILMIŞSA
                        if gerceklesenler and 'NOSIG' in trend_raw:
                            is_tolerated = False
                            if not getattr(self, 'kati_icao_kurallari', False):
                                # KULLANICI İSTEĞİ (Esnek Mod): TEMPO'nun bitmesine 1 saat civarı kaldıysa NOSIG tolere edilebilir.
                                if t_end and metar_dt:
                                    kalan_sure_dk = (t_end - metar_dt).total_seconds() / 60.0
                                    if 0 <= kalan_sure_dk <= 75: # 1 Saat + 15dk METAR yayın saati toleransı
                                        is_tolerated = True
                                        report_lines.append(f"   ℹ️ TOLERANS: TEMPO'nun bitmesine yakın ({int(kalan_sure_dk)} dk) olduğu için NOSIG kullanımı tolere edildi.")
                                        
                            if not is_tolerated:
                                nosig_conflicts.append(f"TEMPO ile beklenen durum gerçekleşti, Ana TAF'a iyileşme (BECMG) beklenirken NOSIG verildi.")
                    else:
                        target_vals_for_comparison = tr_vals
                    
                    # Aday METAR trend parçalarını belirle
                    candidates = [{'type': 'ALL', 'content': trend_content}] # Varsayılan: Hepsi
                    if 'TEMPO' in tr['type']:
                        if gerceklesenler:
                            # Gerçekleşen varsa iyileşme/dönüş için BECMG aranır
                            matches = [p for p in metar_trend_parts if p['type'] == 'BECMG']
                            if matches: 
                                candidates = matches
                            elif 'NOSIG' not in trend_raw:
                                trend_format_error = "Format Hatası (F/UYUMSUZ): Süreksiz (TEMPO) durum gerçekleştiği için, Ana TAF'a dönüş/iyileşme METAR Trend'inde BECMG ile verilmelidir."
                                candidates = [] # Döngüye girmesin, hata direkt yansısın
                        else:
                            # Henüz gerçekleşmediyse TEMPO aranır
                            matches = [p for p in metar_trend_parts if p['type'] == 'TEMPO']
                            if matches: candidates = matches
                    elif 'BECMG' in tr['type']:
                        matches = [p for p in metar_trend_parts if p['type'] == 'BECMG']
                        if matches: candidates = matches

                    # Her bir aday parça için doğrulama yap (Eğer biri bile uyarsa kabul et)
                    # Çoklu trend durumunda tüm parslar kontrol edilir ve en iyisi seçilir
                    valid_candidate_found = False
                    last_check_error = None
                    best_match_score = float('inf')  # En az hata sayısı
                    best_match_errors = None
                    best_format_warning = None
                    
                    for cand in candidates:
                        search_text = cand['content']
                        cand_type = cand['type']
                        if cand_type == 'ALL':
                            if 'TEMPO' in trend_raw: cand_type = 'TEMPO'
                            elif 'BECMG' in trend_raw: cand_type = 'BECMG'
                            else: cand_type = 'UNKNOWN'
                            
                        current_error = None
                        format_warning_for_this_cand = None
                        skip_metar_trend_check = False
                        
                        # METAR Trend içindeki FM ve TL zamanlarını çöz
                        mt_fm_dt = None
                        mt_tl_dt = None

                        # FMHHMM
                        fm_match = re.search(r'\bFM(\d{4})\b', search_text)
                        if fm_match and metar_dt:
                            _h, _m = int(fm_match.group(1)[:2]), int(fm_match.group(1)[2:])
                            mt_fm_dt = self._resolve_hhmm(_h, _m, metar_dt)

                        # TLHHMM
                        tl_match = re.search(r'\bTL(\d{4})\b', search_text)
                        if tl_match and metar_dt:
                            _h, _m = int(tl_match.group(1)[:2]), int(tl_match.group(1)[2:])
                            mt_tl_dt = self._resolve_hhmm(_h, _m, metar_dt)

                        # --- KULLANICI MANTIĞI: TEMPO (Başlangıç) ve BECMG (Bitiş) Zaman Kontrolleri ---
                        # Aday METAR trend parçasını değerlendir
                        candidate_metar_trend_vals = metar_trend_vals  # Varsayılan
                        
                        # Aday parçadan trend değerleri çıkart (Zaman belirtisi kaldırıldıktan sonra)
                        search_text_clean = re.sub(r'\b(FM|TL|AT)\d{4}\b', '', search_text).strip()
                        c_wind = self._parse_wind(search_text_clean) or metar_trend_vals[0]
                        c_vis = self._parse_visibility(search_text_clean) or metar_trend_vals[1]
                        c_cig = self._parse_ceiling(search_text_clean) or metar_trend_vals[2]
                        c_wx = self._parse_weather(search_text_clean) or metar_trend_vals[3]
                        candidate_metar_trend_vals = (c_wind, c_vis, c_cig, c_wx)
                        
                        # NOSIG varsa veya kurallar kapalıysa format kontrolü yapma
                        if 'NOSIG' not in trend_raw and self.trend_zaman_aktif:
                            # KESİN KURAL: FM veya TL zamanı METAR'dan en az 15 dakika sonra olmalıdır.
                            if mt_fm_dt and metar_dt:
                                fm_diff = (mt_fm_dt - metar_dt).total_seconds() / 60.0
                                if fm_diff < 0:
                                    current_error = f"Format Hatası (F/UYUMSUZ): FM zamanı ({mt_fm_dt.strftime('%H%M')}) geçmişe (METAR saatinden önceye) ait olamaz."
                                elif fm_diff < self.trend_min_sure:
                                    current_error = f"Format Hatası (F/UYUMSUZ): FM zamanı ({mt_fm_dt.strftime('%H%M')}) METAR saatinden en az {self.trend_min_sure} dk sonrasına verilmelidir."
                                    
                            if not current_error and mt_tl_dt and metar_dt:
                                tl_diff = (mt_tl_dt - metar_dt).total_seconds() / 60.0
                                if tl_diff < 0:
                                    current_error = f"Format Hatası (F/UYUMSUZ): TL zamanı ({mt_tl_dt.strftime('%H%M')}) geçmişe (METAR saatinden önceye) ait olamaz."
                                elif tl_diff < self.trend_min_sure:
                                    current_error = f"Format Hatası (F/UYUMSUZ): TL zamanı ({mt_tl_dt.strftime('%H%M')}) METAR saatinden en az {self.trend_min_sure} dk sonrasına verilmelidir."

                                # TEMPO: Başlangıç saatine (t_start) göre kontrol (Yalnızca TAF'ta TEMPO bekleniyorsa)
                                if not current_error and cand_type == 'TEMPO' and 'TEMPO' in tr['type'] and t_start and metar_dt:
                                    # TL Zaman Kontrolü (Varsa TAF Bitiş ile uyumlu olmalı)
                                    if mt_tl_dt and t_end:
                                        if abs((mt_tl_dt - t_end).total_seconds()) > 1800:
                                            skip_metar_trend_check = True

                                    if not current_error and not skip_metar_trend_check:
                                        diff_min = (t_start - metar_dt).total_seconds() / 60.0
                                        
                                        # 15-75 dk önce: FM zorunlu (Örn: TEMPO FM0400)
                                        if self.trend_min_sure < diff_min <= self.trend_max_sure:
                                            if not mt_fm_dt:
                                                if getattr(self, 'kati_icao_kurallari', False):
                                                    current_error = f"Format Hatası (F/UYUMSUZ): {self.trend_min_sure}-{self.trend_max_sure} dk kala FM kullanımı ZORUNLUDUR."
                                                else:
                                                    format_warning_for_this_cand = f"Format Toleransı (DİKKAT): {self.trend_min_sure}-{self.trend_max_sure} dk kala FM kullanılmalıydı."
                                            elif abs((mt_fm_dt - t_start).total_seconds()) > 1800:
                                                current_error = f"Zaman Uyumsuzluğu (F/UYUMSUZ): METAR FM{mt_fm_dt.strftime('%H%M')} != TAF Başlangıç {t_start.strftime('%H%M')}"
                                        
                                        # 0-15 dk önce: FM KULLANILMAMALI
                                        elif 0 <= diff_min <= self.trend_min_sure:
                                            if mt_fm_dt: current_error = f"Format Hatası (F/UYUMSUZ): 0-{self.trend_min_sure} dk kala FM kullanılmamalı."
                                            
                            # BECMG: Bitiş saatine (t_end) veya İyileşme saatine göre kontrol
                            elif not current_error and cand_type == 'BECMG' and metar_dt:
                                target_dt = t_end
                                if 'TEMPO' in tr['type'] and t_start and metar_dt < t_start:
                                    target_dt = t_start
                                    
                                if target_dt:
                                    # FM Zaman Kontrolü (Sadece TAF'ta BECMG varsa aranır)
                                    if mt_fm_dt and t_start and 'BECMG' in tr['type']:
                                        if abs((mt_fm_dt - t_start).total_seconds()) > 1800:
                                            current_error = f"Zaman Uyumsuzluğu (F/UYUMSUZ): METAR FM{mt_fm_dt.strftime('%H%M')} != TAF Başlangıç {t_start.strftime('%H%M')}"

                                    if not current_error:
                                        diff_min = (target_dt - metar_dt).total_seconds() / 60.0
                                        
                                        # 15-90 dk önce: TL zorunlu (Örn: BECMG TL0700)
                                        if self.trend_tl_min_sure < diff_min <= self.trend_tl_max_sure:
                                            if not mt_tl_dt:
                                                if getattr(self, 'kati_icao_kurallari', False):
                                                    current_error = f"Format Hatası (F/UYUMSUZ): {self.trend_tl_min_sure}-{self.trend_tl_max_sure} dk kala TL kullanımı ZORUNLUDUR."
                                                else:
                                                    format_warning_for_this_cand = f"Format Toleransı (DİKKAT): {self.trend_tl_min_sure}-{self.trend_tl_max_sure} dk kala TL kullanılmalıydı."
                                            elif abs((mt_tl_dt - target_dt).total_seconds()) > 1800:
                                                current_error = f"Zaman Uyumsuzluğu (F/UYUMSUZ): METAR TL{mt_tl_dt.strftime('%H%M')} != Beklenen Dönüş/Bitiş {target_dt.strftime('%H%M')}"
                                        
                                        # 0-15 dk önce: TL KULLANILMAMALI (Sadece BECMG yazılır)
                                        elif 0 <= diff_min <= self.trend_tl_min_sure:
                                            if mt_tl_dt: current_error = f"Format Hatası (F/UYUMSUZ): 0-{self.trend_tl_min_sure} dk kala TL kullanılmamalı."

                        # Genel Güvenlik: FM/TL varsa ve TAF ile çok alakasızsa (>60dk) her durumda ele
                        if t_start and mt_fm_dt and abs((mt_fm_dt - t_start).total_seconds()) > 3600: skip_metar_trend_check = True
                        if t_end and mt_tl_dt and abs((mt_tl_dt - t_end).total_seconds()) > 3600:
                            # KULLANICI İSTEĞİ: METAR TL zamanı, TAF Başlangıç zamanı ile örtüşüyorsa (Geçiş anı) kontrol et.
                            if t_start and abs((mt_tl_dt - t_start).total_seconds()) <= 3600:
                                pass
                            else:
                                skip_metar_trend_check = True
                        
                        if not current_error:
                            valid_candidate_found = True
                            best_format_warning = format_warning_for_this_cand
                            break # Geçerli bir trend parçası bulundu, döngüden çık
                        else:
                            last_check_error = current_error

                    if not trend_format_error:
                        if valid_candidate_found:
                            trend_format_error = None
                        else:
                            trend_format_error = last_check_error
                    
                    if not skip_metar_trend_check:
                        valid_trend_evals += 1
                        if trend_format_error:
                            tr_errors_trend = [trend_format_error]
                            critical_format_error = True
                            format_error_evals += 1
                            format_error_reports.append(trend_format_error)
                        else:
                            tr_errors_trend = self._compare_values(target_vals_for_comparison, metar_trend_vals)
                            if best_format_warning:
                                tr_errors_trend.append(best_format_warning)
                        
                        better_info_trend = ""
                        if tr_errors_trend:
                             tr_errors_trend, better_info_trend = self._check_better_conditions(tr_errors_trend, target_vals_for_comparison, metar_trend_vals, base_vals=taf_vals)

                        report_lines.append(f"   B. vs METAR TREND:")
                        report_lines.append(f"      🔹 TAF TREND: {tr['raw']}")
                        report_lines.append(f"      🔹 METAR TREND: {metar_trend_display}")
                        if not tr_errors_trend:
                            report_lines.append(f"      ✅ UYUMLU{better_info_trend}")
                            
                            # --- YENİ EKLENTİ: NOSIG ve Rüzgar Farkı Açıklaması ---
                            if trend_raw and 'NOSIG' in trend_raw and target_vals_for_comparison[0] and metar_trend_vals[0]:
                                t_yon, t_hiz, _ = target_vals_for_comparison[0]
                                m_yon, m_hiz, _ = metar_trend_vals[0]
                                if t_hiz != m_hiz and abs(t_hiz - m_hiz) < 10:
                                    report_lines.append(f"      ℹ️ BİLGİ: TAF Trend rüzgarı ({t_hiz}KT) ile METAR rüzgarı ({m_hiz}KT) farkı <10KT olduğu için NOSIG ile çelişmez.")
                            # --- BİTTİ ---
                            
                            res4 = True
                        else:
                            for e in tr_errors_trend: 
                                if "Format Toleransı" in e:
                                    report_lines.append(f"      ⚠️ {e}")
                                else:
                                    report_lines.append(f"      ❌ {e}")
                                    rec = self._generate_recommendation(e, target_vals_for_comparison, metar_dt=metar_dt, target_dt=t_end or t_end_taf, trend_raw=trend_raw)
                                    if rec: report_lines.append(f"         {rec}")
                                if "Rüzgar" in e and trend_raw and 'NOSIG' in trend_raw:
                                    report_lines.append(f"      ℹ️ ÇELİŞKİ: METAR 'NOSIG' (değişim yok) veriyor ancak TAF Trendi rüzgarda limit dışı (>=10KT) değişim bekliyor.")
                                if "Hadise" in e:
                                    # YENİ KURAL: TAF trendinin başlama saati, NOSIG'in 2 saatlik etki alanının dışındaysa BUST sayma
                                    is_overlapping_nosig = True
                                    if 'NOSIG' in trend_raw and t_start and metar_dt:
                                        nosig_end = metar_dt + timedelta(hours=2)
                                        # Eğer TAF trendi NOSIG'in süresi dolduktan sonra başlıyorsa çelişki yoktur.
                                        if t_start >= nosig_end:
                                            is_overlapping_nosig = False
                                            
                                    if is_overlapping_nosig:
                                        trend_hadise_bust = True
                    else:
                        report_lines.append(f"   └─ Sonuç       : ⏭️ ZAMAN UYUMSUZ (ATLANDI)")
                    report_lines.append("")
            
            if not active_trends_found:
                report_lines.append("  ℹ️ Aktif TAF Trendi Yok (Zaman Uyumsuz)\n")
        else:
            report_lines.append("  ℹ️ TAF Trendi Yok\n")

        # --- SONUÇ DEĞERLENDİRMESİ ---
        # METAR (Gözlem) Kısmı: Ana TAF veya TAF Trendi ile uyumlu mu?
        metar_ok = res1 or res2
        
        # TREND (Tahmin) Kısmı: Eğer METAR Trendi varsa, Ana TAF veya TAF Trendi ile uyumlu mu?
        # Eğer METAR Trendi yoksa, bu kısım değerlendirme dışıdır.
        trend_ok = False
        if metar_trend_vals:
            trend_ok = res3 or res4

        # GENEL DEĞERLENDİRME MANTIĞI
        # 1. Hiçbir uyum yoksa -> UYUMSUZ
        # 2. En az biri uyumluysa -> DİKKAT (En az)
        # 3. Hepsi uyumluysa -> UYUMLU (veya DİKKAT - Trend durumuna göre)

        has_trend = (metar_trend_vals is not None)
        
        # Eğer değerlendirilen tüm TAF trendleri format hatası verdiyse ve mükemmel uyum (res3/res4) yoksa:
        if valid_trend_evals > 0 and format_error_evals == valid_trend_evals and not (res3 or res4):
            critical_format_error = True

        if critical_format_error:
            # KULLANICI TALEBİ: F/UYUMSUZ varsa detaylı analizde hatayı ve kuralları açıkla.
            detailed_error_report = []
            detailed_error_report.append("============================================================")
            detailed_error_report.append(" ❌ KRİTİK FORMAT HATASI (F/UYUMSUZ)")
            detailed_error_report.append("============================================================")
            detailed_error_report.append("METAR Trend grubu zaman belirteçleri (FM/TL), TAF periyoduyla uyumlu değil.")
            detailed_error_report.append("-" * 60)
            
            # Hataları bul ve ekle
            found_errors = []
            seen_errors = set()
            for line in report_lines:
                if "F/UYUMSUZ" in line:
                    clean_line = line.strip()
                    if clean_line not in seen_errors:
                        found_errors.append(clean_line)
                        seen_errors.add(clean_line)
            for err in format_error_reports:
                if err not in seen_errors:
                    detailed_error_report.append(f"• {err}")
                    seen_errors.add(err)
            
            for err in found_errors:
                detailed_error_report.append(f"• {err}")
            
            detailed_error_report.append("-" * 60)
            detailed_error_report.append("KURALLAR VE AÇIKLAMA:")
            detailed_error_report.append("1. TEMPO/BECMG Başlangıcı (FM):")
            detailed_error_report.append(f"   - {self.trend_min_sure}-{self.trend_max_sure} dk kala: FM kullanımı ZORUNLUDUR.")
            detailed_error_report.append(f"   - 0-{self.trend_min_sure} dk kala: FM kullanımı YASAKTIR (Direkt trend yazılır).")
            detailed_error_report.append("2. BECMG Bitişi (TL):")
            detailed_error_report.append(f"   - {self.trend_min_sure}-{self.trend_max_sure} dk kala: TL kullanımı ZORUNLUDUR.")
            detailed_error_report.append(f"   - 0-{self.trend_min_sure} dk kala: TL kullanımı YASAKTIR.")
            
            return 0, "F/UYUMSUZ", detailed_error_report

        # --- KESİN UYUMSUZLUK KURALI: NOSIG vs TAF TREND ÇELİŞKİSİ ---
        if has_trend and "NOSIG" in trend_raw:
            if nosig_conflicts:
                unique_conflicts = list(dict.fromkeys(nosig_conflicts))
                report_lines.append("============================================================")
                report_lines.append(" ❌ KESİN UYUMSUZLUK")
                report_lines.append(f" ❌ NOSIG ÇELİŞKİSİ: TAF'ta aktif değişimler var: {', '.join(unique_conflicts)}")
                
                # YENİ: Otomatik Tavsiye Bildirimi
                if taf_vals:
                    suggestion_prefix = "BECMG "
                    if t_end_taf and metar_dt:
                        diff_min = (t_end_taf - metar_dt).total_seconds() / 60.0
                        if 15 < diff_min <= 75:
                            suggestion_prefix = f"BECMG TL{t_end_taf.strftime('%H%M')} "
                            
                    t_wind, t_vis, t_cig, t_wx = taf_vals
                    parts = []
                    if t_wind and t_wind[0] is not None:
                        t_yon, t_hiz, t_gust = t_wind
                        y_str = "VRB" if t_yon == -1 else f"{t_yon:03d}"
                        g_str = f"G{t_gust:02d}" if t_gust else ""
                        parts.append(f"{y_str}{t_hiz:02d}{g_str}KT")
                    if t_vis is not None:
                        parts.append(f"{t_vis}" if t_vis != 10000 else "9999")
                    if t_wx is not None:
                        parts.append(" ".join(t_wx) if t_wx else "NSW")
                    if t_cig is not None:
                        if t_cig == (9999, False): parts.append("NSC")
                        elif t_cig[1]: parts.append(f"VV{t_cig[0]//100:03d}")
                        else: parts.append(f"BKN{t_cig[0]//100:03d}")
                        
                    w_str = " ".join(parts)
                    report_lines.append(f" 💡 TAVSİYE: NOSIG yerine Ana TAF'a dönüşü belirten '{suggestion_prefix}{w_str}' kullanılmalıydı.")

                report_lines.append("============================================================")
                return 0, "UYUMSUZ", report_lines
            elif not active_trends_found and ana_hadise_bust:
                report_lines.append("============================================================")
                report_lines.append(" ❌ KESİN UYUMSUZLUK")
                report_lines.append(" ❌ NOSIG ÇELİŞKİSİ: TAF Ana gövdede kritik hadise beklentisi")
                report_lines.append("    varken METAR NOSIG (değişim yok) veriyor.")
                
                # YENİ: Hadise Çelişkisi İçin Tavsiye
                suggestion_prefix = "BECMG "
                if t_end_taf and metar_dt:
                    diff_min = (t_end_taf - metar_dt).total_seconds() / 60.0
                    if 15 < diff_min <= 75:
                        suggestion_prefix = f"BECMG TL{t_end_taf.strftime('%H%M')} "
                report_lines.append(f" 💡 TAVSİYE: NOSIG yerine beklenen hadisenin (veya NSW'nin) durumu '{suggestion_prefix}...' ile belirtilmeliydi.")
                report_lines.append("============================================================")
                return 0, "UYUMSUZ", report_lines
        at_least_one_ok = metar_ok or (trend_ok if has_trend else False)

        # Kullanıcı Mantığı:
        # 1. En az bir uyum varsa UYUMSUZ değildir.
        # 2. METAR Trendi varsa ve TAF ile uyumlu değilse -> DİKKAT (Beklenmeyen durumölüş)
        # 3. METAR Trendi varsa ve TAF ile uyumluysa (res3 veya res4 True) -> UYUMLU
        # 4. METAR Trendi NOSIG ise (veya yoksa) ve Ana METAR uyumluysa -> UYUMLU
        
        # Ana METAR Gözlem Uyumsuz ise başlangıçta UYUMSUZ döndür
        if not res1:
            # En az bir trend uyumlu mu?
            if res2:  # TAF Trendi ANA METAR ile uyumlu
                return 100, "UYUMLU", report_lines
            # METAR Trend'den uyum var mı?
            if has_trend and (res3 or res4):
                return 100, "UYUMLU", report_lines
            # Hiçbir uyum yok
            return 0, "UYUMSUZ", report_lines
        
        # Ana METAR Gözlem uyumlu (res1=True)
        if has_trend and ("BECMG" in trend_raw or "TEMPO" in trend_raw):
            # METAR Trend Tahmin'i de kontrol et
            if not (res3 or res4):
                # METAR Trendi TAF ile uyumlu değil
                return 50, "DİKKAT", report_lines
            else:
                # METAR Trendi de TAF ile uyumlu
                return 100, "UYUMLU", report_lines
        else:
            # METAR Trendi yoksa veya 'NOSIG' / RMK içinde
            return 100, "UYUMLU", report_lines

    def _check_better_conditions(self, errors, t_vals, m_vals, base_vals=None):
        """
        METAR şartlarının TAF'tan daha iyi olup olmadığını kontrol eder.
        İyileşme durumlarını daha detaylı açıklar.
        """
        t_wind, t_vis, t_cig, t_wx = t_vals
        m_wind, m_vis, m_cig, m_wx = m_vals

        new_errors = errors.copy()
        infos = []

        # 1. Ana TAF'tan Kopuşta Kritik Hadise Kuralı (Base Yoksa)
        if any("Hadise" in e for e in errors) and base_vals is None:
            return errors, ""

        # --- DALGALANMA VE GEÇİŞ KONTROLÜ (TEMPO veya Devam Eden BECMG için) ---
        if base_vals:
            b_wind, b_vis, b_cig, b_wx = base_vals

            # Görüş Hatası Dalgalanması
            vis_err_list = [e for e in new_errors if "Görüş" in e]
            if vis_err_list and t_vis is not None and b_vis is not None and m_vis is not None:
                min_v, max_v = min(b_vis, t_vis), max(b_vis, t_vis)
                if min_v <= m_vis <= max_v:
                    for e in vis_err_list: new_errors.remove(e)
                    infos.append(f"Görüş Dalgalanma Aralığında ({min_v}m - {max_v}m)")
                elif m_vis > max_v:
                    for e in vis_err_list: new_errors.remove(e)
                    infos.append(f"Görüş İyileşmesi (Beklenen: <{max_v}m, Gelen: {m_vis}m)")

            # Tavan Hatası Dalgalanması
            cig_err_list = [e for e in new_errors if "Tavan" in e or "Dikey" in e]
            if cig_err_list and t_cig[0] is not None and b_cig[0] is not None and m_cig[0] is not None:
                min_c, max_c = min(b_cig[0], t_cig[0]), max(b_cig[0], t_cig[0])
                if min_c <= m_cig[0] <= max_c:
                    for e in cig_err_list: new_errors.remove(e)
                    infos.append(f"Tavan Dalgalanma Aralığında ({min_c}ft - {max_c}ft)")
                elif m_cig[0] > max_c:
                    for e in cig_err_list: new_errors.remove(e)
                    infos.append(f"Tavan İyileşmesi (Beklenen: <{max_c}ft, Gelen: {m_cig[0]}ft)")

            # Rüzgar Hatası Dalgalanması
            wind_err_list = [e for e in new_errors if "Rüzgar" in e]
            if wind_err_list and t_wind[1] is not None and b_wind[1] is not None and m_wind[1] is not None:
                min_w, max_w = min(b_wind[1], t_wind[1]), max(b_wind[1], t_wind[1])
                if min_w <= m_wind[1] <= max_w:
                    for e in wind_err_list: new_errors.remove(e)
                    infos.append(f"Rüzgar Hızı Dalgalanma Aralığında ({min_w}KT - {max_w}KT)")
                    
            # Hadise Hatası Dalgalanması
            hadise_err_list = [e for e in new_errors if "Hadise" in e]
            if hadise_err_list:
                # Eğer METAR'daki hadise, ana TAF'taki ile aynıysa, bu "henüz gerçekleşmemiş" demektir.
                diff_with_base = (b_wx or set()).symmetric_difference(m_wx or set())
                if not diff_with_base:
                    for e in hadise_err_list: new_errors.remove(e)
                    infos.append("Hadise Henüz Gerçekleşmedi (Ana TAF Devam)")
                elif t_wx and not m_wx:
                    for e in hadise_err_list: new_errors.remove(e)
                    infos.append(f"Hadise İyileşmesi (Beklenen: {', '.join(t_wx)}, Gelen: Yok)")

        # --- DOĞRUDAN İYİLEŞME KONTROLÜ (Ana TAF vs METAR) ---
        else:
            # Görüş İyileşmesi
            vis_err_list = [e for e in new_errors if "Görüş" in e]
            if vis_err_list and m_vis is not None and t_vis is not None:
                # Sadece limit aşımı varsa ve METAR daha iyiyse hatayı kaldır.
                if m_vis > t_vis:
                    for e in vis_err_list: new_errors.remove(e)
                    infos.append(f"Görüş İyileşmesi (Beklenen: {t_vis}m, Gelen: {m_vis}m)")

            # Tavan İyileşmesi
            cig_err_list = [e for e in new_errors if "Tavan" in e or "Dikey" in e]
            if cig_err_list and m_cig[0] is not None and t_cig[0] is not None:
                if m_cig[0] > t_cig[0]:
                    for e in cig_err_list: new_errors.remove(e)
                    infos.append(f"Tavan İyileşmesi (Beklenen: {t_cig[0]}ft, Gelen: {m_cig[0]}ft)")
            
            # Hadise İyileşmesi
            hadise_err_list = [e for e in new_errors if "Hadise" in e]
            if hadise_err_list and t_wx and not m_wx:
                for e in hadise_err_list: new_errors.remove(e)
                infos.append(f"Hadise İyileşmesi (Beklenen: {', '.join(t_wx)}, Gelen: Yok)")

        info_str = f" [Açıklama: {', '.join(infos)}]" if infos else ""
        return new_errors, info_str


# --- MODÜL KULLANIMI ---
if __name__ == "__main__":
    robot = HavacilikRobotModulu()
    
    print("--- ZAMAN KONTROL TESTLERİ (BECMG/TEMPO) ---")
    test_cases = [
        ("1012/1014", "101300Z", "TEMPO", datetime(2024,10,10,13,0), True),  # İçinde
        ("1012/1014", "101100Z", "TEMPO", datetime(2024,10,10,11,0), False), # Önce
        ("1012/1014", "101500Z", "TEMPO", datetime(2024,10,10,15,0), False), # Sonra
        ("3123/0101", "312330Z", "TEMPO", datetime(2023,12,31,23,30), True), # Yılbaşı gecesi
        ("3123/0101", "010030Z", "TEMPO", datetime(2024,1,1,0,30), True),    # Yeni yıl sabahı
    ]
    
    for t_head, m_time, t_type, ref, exp in test_cases:
        res = robot._is_trend_active(t_head, m_time, t_type, ref_date=ref)
        status = "[+] GECTI" if res[0] == exp else f"[-] KALDI (Beklenen: {exp})"
        print(f"{status} | {t_type} {t_head} vs {m_time} -> Sonuç: {res[0]} ({res[1]})")

    print("\n--- TAM ANALİZ TESTİ ---")
    skor, durum, neden = robot.analiz_et(
        "TAF 0412/0512 20010KT", 
        "METAR 041330Z 20022KT", 
        "BECMG 20010KT",
        ref_date=datetime(2024,10,4,13,30)
    )
    print(f"Robot Skoru: %{skor} | Durum: {durum}")

    print("\n--- GEÇMİŞ HADİSE (RE) - RESHRA vs RA TESTİ ---")
    test_metar = "METAR LTAN 231250Z 17022KT 9999 FEW027CB SCT035 BKN090 07/04 Q1008 RESHRA NOSIG"
    
    aktif_wx, gecmis_wx, vc_wx = robot.extract_active_and_recent_weather(test_metar)
    print(f"Test Metni: {test_metar}")
    print(f"Bulunan Aktif Hadiseler: {aktif_wx}")
    print(f"Bulunan Geçmiş (RE) Hadiseler: {gecmis_wx}")
    print(f"Bulunan Civar (VC) Hadiseler: {vc_wx}")
    print(f"Sonuç: RESHRA ayrıştırıldığında kök hadise olarak 'RA' başarıyla set edildi mi?: {'RA' in gecmis_wx}")