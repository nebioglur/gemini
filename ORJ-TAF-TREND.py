import re
from datetime import datetime, timedelta

class HavacilikRobotModulu:
    def __init__(self):
        self.esikler_ruyet = [150, 350, 600, 800, 1500, 3000, 5000]
        self.esikler_tavan = [100, 200, 500, 1000, 1500]
        self.esikler_vv = [100, 200, 500, 1000]
        self.kritik_hadiseler = [r'TS', r'FZ', r'SQ', r'FC', r'FG', r'SS', r'DS', r'(?<!-)RA', r'(?<!-)SN', r'GR']

    def zaman_uygun_mu(self, taf_header, metar_time_code):
        """
        TAF geçerlilik aralığı ile METAR saatini kıyaslar.
        Örnek taf_header: '0412/0512' (4. gün 12:00 ile 5. gün 12:00 arası)
        Örnek metar_time_code: '041330Z' (4. gün 13:30)
        """
        try:
            # TAF Aralığını Ayrıştır
            match = re.search(r'(\d{2})(\d{2})/(\d{2})(\d{2})', taf_header)
            if not match: return False
            
            bas_gun, bas_saat = int(match.group(1)), int(match.group(2))
            bit_gun, bit_saat = int(match.group(3)), int(match.group(4))
            
            # METAR Saatini Ayrıştır
            metar_gun = int(metar_time_code[:2])
            metar_saat = int(metar_time_code[2:4])
            
            # Basit Günlük/Saatlik Kontrol (Aynı gün içindeyse)
            if metar_gun == bas_gun:
                return metar_saat >= bas_saat
            elif metar_gun == bit_gun:
                return metar_saat < bit_saat
            return False
        except:
            return False

    def check_threshold(self, v1, v2, thresholds):
        """İki değer arasında eşik geçişi olup olmadığını kontrol eder."""
        low, high = min(v1, v2), max(v1, v2)
        for t in thresholds:
            if low < t <= high: return True
        return False

    def _parse_wind(self, code):
        """Rüzgar yönü ve hızını ayıklar."""
        match = re.search(r'(\d{3}|VRB)(\d{2,3})', code)
        if not match: return 0, 0
        yon = 0 if match.group(1) == "VRB" else int(match.group(1))
        hiz = int(match.group(2))
        return yon, hiz

    def _parse_ceiling(self, code):
        """Bulut tavanını (Ceiling) veya Dikey Görüşü (VV) ayıklar."""
        if any(x in code for x in ['CAVOK', 'SKC', 'NSC', 'CLR']):
            return 9999, False
        vv = re.search(r'VV(\d{3})', code)
        if vv: return int(vv.group(1)) * 100, True
        clouds = re.findall(r'(BKN|OVC)(\d{3})', code)
        if clouds:
            return min([int(c[1]) * 100 for c in clouds]), False
        return 9999, False

    def _parse_visibility(self, code):
        """Görüş mesafesini (Visibility) ayıklar."""
        if 'CAVOK' in code: return 10000
        match = re.search(r'\b(\d{4})\b', code)
        if match: return int(match.group(1))
        return 10000

    def _parse_cloud_layers(self, code):
        """Bulut katmanlarını (Tip, Yükseklik) listesi olarak döner."""
        layers = []
        matches = re.findall(r'\b(FEW|SCT|BKN|OVC|VV)(\d{3})\b', code)
        for m in matches:
            layers.append((m[0], int(m[1])*100))
        return layers

    def analiz_et(self, taf_raw, metar_raw, trend_raw, taf_zaman="0412/0512"):
        """Modülün ana denetleme fonksiyonu."""
        
        # 1. ZAMAN KONTROLÜ
        metar_zaman_kodu = metar_raw.split(' ')[1] # Genelde 2. sırada olur (Örn: 041330Z)
        if not self.zaman_uygun_mu(taf_zaman, metar_zaman_kodu):
            return -1, "HATA: METAR saati TAF geçerlilik aralığı dışında.", []

        errors = []
        
        # 2. RÜZGAR DENETİMİ
        t_yon, t_hiz = self._parse_wind(taf_raw)
        m_yon, m_hiz = self._parse_wind(metar_raw)
        
        # Rüzgar hızı farkı 10 KT ve üstü ayrı limit
        if abs(t_hiz - m_hiz) >= 10:
            errors.append("Rüzgar hızı farkı >= 10KT")
            
        # 60 derece fark ve hız eşiği
        yon_f = abs(t_yon - m_yon)
        if yon_f > 180: yon_f = 360 - yon_f
        if yon_f >= 60 and (t_hiz >= 10 or m_hiz >= 10):
            errors.append("Rüzgar yön farkı >= 60 derece (Hız >= 10KT iken)")

        # --- GÖRÜŞ (RÜYET) DENETİMİ ---
        t_vis = self._parse_visibility(taf_raw)
        m_vis = self._parse_visibility(metar_raw)
        if self.check_threshold(t_vis, m_vis, self.esikler_ruyet):
            errors.append(f"Görüş değişimi limit dışı (TAF:{t_vis}m vs METAR:{m_vis}m)")

        # --- BULUT VE DİKİNE RÜYET (VV) ---
        t_cig, t_is_vv = self._parse_ceiling(taf_raw)
        m_cig, m_is_vv = self._parse_ceiling(metar_raw)
        thresholds = self.esikler_vv if (t_is_vv or m_is_vv) else self.esikler_tavan
        if self.check_threshold(t_cig, m_cig, thresholds):
            errors.append(f"Tavan/VV değişimi limit dışı (TAF:{t_cig} vs METAR:{m_cig})")

        # --- KAPALILIK SEGMENTİ ---
        t_layers = self._parse_cloud_layers(taf_raw)
        m_layers = self._parse_cloud_layers(metar_raw)
        def has_bkn_ovc_below_1500(layers):
            for c_type, h in layers:
                if h < 1500 and c_type in ['BKN', 'OVC', 'VV']: return True
            return False
        if has_bkn_ovc_below_1500(t_layers) != has_bkn_ovc_below_1500(m_layers):
            errors.append("1500ft altında kapalılık değişimi (SCT<->BKN)")

        # 3. NİHAİ PUANLAMA
        if not errors:
            return 100, "UYUMLU", []
        
        # TREND TAF Rotasına sokuyorsa %50 DİKKAT
        if any(x in trend_raw for x in ["BECMG", "TEMPO", "FM"]):
            return 50, "DİKKAT (Trend TAF Rotasına Giriyor)", errors
            
        return 0, "UYUMSUZ", errors

# --- MODÜL KULLANIMI ---
if __name__ == "__main__":
    robot = HavacilikRobotModulu()
    # Örnek: TAF 4. gün 12:00-05:00 arası geçerli. METAR 4. gün 13:30.
    skor, durum, neden = robot.analiz_et(
        "TAF 0412/0512 20010KT", 
        "METAR 041330Z 20022KT", 
        "BECMG 20010KT"
    )
    print(f"Robot Skoru: %{skor} | Durum: {durum}")