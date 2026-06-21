import pandas as pd
import re
from saat_eslestirme import SaatEslestirici, otomat_veriler_eslestirilebilir_mi
import sys
try:
    from synop_decoder import SynopDecoder
except ImportError:
    SynopDecoder = None
try:
    from metar_decoder import MetarDecoder
except ImportError:
    MetarDecoder = None

class WeatherLogValidator:
    def __init__(self, sin_row, met_row, metar_gmt=None, sinoptik_gmt=None):
        """
        sin_row ve met_row: Pandas DataFrame'den dictionary'e çevrilmiş satır verileri.
        metar_gmt: METAR gözleminin GMT saati (saat eşleştirme için)
        sinoptik_gmt: SİNOPTİK gözleminin GMT saati (saat eşleştirme için)
        """
        self.sin = sin_row
        self.met = met_row
        
        # Eğer METAR bülteninin içine denetim_merkezi tarafından geçmiş metarlar eklenmişse 
        # (Örn: İLGİLİ METAR GEÇMİŞİ:), bu kısımları analizden önce temizle. Aksi halde 
        # eski saatteki hadiseler güncel saatteki hatalara (h371 vb.) neden olur.
        if 'Bulten' in self.met and pd.notna(self.met['Bulten']):
            original_bulten = str(self.met['Bulten'])
            # Orijinal bülteni sakla (özet/temizlenmiş halini veri akışında kullanıyoruz,
            # fakat gerektiğinde METAR geçmişini kontrol etmek için orijinali koruyoruz)
            self.met['_raw_bulten'] = original_bulten
            # Daha güvenli temizlik: Büyük/küçük harf veya İ/I farkından etkilenmemesi için Regex kullanıyoruz
            parts = re.split(r'İLG[İI]L[İI] METAR GEÇM[İI]Ş[İI]:?\s*|ILGILI METAR GECMISI:?\s*', original_bulten, flags=re.IGNORECASE)
            b_str = parts[0].strip()
            
            # Geçmiş listesi varsa, ana METAR şifresini RUTİN METAR (50/00) ve yakınlık prensibine göre bul
            if len(parts) > 1:
                history_text = parts[1].strip()
                b_str_found = None
                
                # Tüm geçmiş mesajları ayıkla: Örn: [0444Z] LTAN ... 
                messages = re.findall(r'\[(\d{4})Z\]\s*([^\[]+)', history_text)
                
                if messages:
                    # 1. Yöntem: METAR saatine göre en yakın ve RUTİN olanı bul
                    if metar_gmt is not None and str(metar_gmt).strip().lower() not in ['nan', 'none']:
                        try:
                            # metar_gmt'yi dakikaya çevir
                            metar_gmt_str = str(metar_gmt).strip().replace('.0', '')
                            if len(metar_gmt_str) == 4 and metar_gmt_str.isdigit():
                                target_mins = int(metar_gmt_str[:2]) * 60 + int(metar_gmt_str[2:])
                            else:
                                target_h = int(float(metar_gmt))
                                target_mins = target_h * 60
                                
                            best_msg = None
                            min_diff = float('inf')
                            
                            for m_time, m_text in messages:
                                m_h = int(m_time[:2])
                                m_m = int(m_time[2:])
                                m_mins = m_h * 60 + m_m
                                
                                diff = abs(target_mins - m_mins)
                                if diff > 12 * 60: diff = 24 * 60 - diff
                                
                                # SPECI mesajlarını (dakikası 50, 00 veya 20 olmayanları) cezalandır, rutin METAR'ı seç
                                is_routine = m_m in [50, 0, 20]
                                penalty = 0 if is_routine else 15
                                
                                if diff + penalty < min_diff:
                                    min_diff = diff + penalty
                                    best_msg = m_text.strip()
                                    
                            if best_msg:
                                b_str_found = best_msg
                        except:
                            pass
                            
                    # 2. Yöntem: Eğer saatten bulunamadıysa ilk rutin METAR'ı (50 veya 00 ile biten) seç
                    if not b_str_found:
                        for m_time, m_text in messages:
                            if m_time.endswith('50') or m_time.endswith('00'):
                                b_str_found = m_text.strip()
                                break
                                
                    # 3. Yöntem: Hiçbiri olmadıysa en üsttekini (ilk mesajı) al
                    if not b_str_found:
                        b_str_found = messages[0][1].strip()
                
                if b_str_found:
                    b_str = b_str_found
                elif not b_str or b_str.replace('"', '').replace("'", "").strip().lower() in ['nan', 'none', '<na>', '-', ''] or len(b_str) < 10:
                    m_reg = re.search(r'\[.*?\]\s*([^\[]+)', history_text)
                    if m_reg:
                        b_str = m_reg.group(1).strip()
                    
            self.met['Bulten'] = b_str

            # Eğer METAR saati verilmemişse, orijinal bülten içindeki [HHMMZ] etiketlerini
            # alıp sinoptik saati ile eşleştirerek uygun bir METAR saati bulunup bulunmadığını kontrol et.
            try:
                if (metar_gmt is None or pd.isna(metar_gmt)) and sinoptik_gmt is not None:
                    # Tüm [0750Z] tarzı zamanları bul
                    matches = re.findall(r'\[(\d{4})Z\]', original_bulten)
                    if matches:
                        alt_gmtler = []
                        for m in matches:
                            try:
                                alt_gmtler.append(int(m))
                            except: 
                                pass
                        if alt_gmtler:
                            en_yakin, fark, aciklama = self.eslestirici.en_yakin_eslesmeyi_bul(self.sinoptik_gmt, alt_gmtler, otomat_veri_mi=True)
                            if en_yakin is not None:
                                # Bulduğumuz eşleşmeyi yerel `metar_gmt` değişkenine ata;
                                # daha sonra __init__ sonunda attribute olarak atanacak.
                                try:
                                    metar_gmt = int(en_yakin)
                                except:
                                    metar_gmt = en_yakin
            except Exception:
                pass
                
        self.errors = []
        self.metar_gmt = metar_gmt
        self.sinoptik_gmt = sinoptik_gmt
        self.eslestirici = SaatEslestirici(tolerans_dakika=15)
        
    def _vv_to_meters(self, vv_val):
        try:
            s_vv = float(vv_val)
            if s_vv <= 50: return s_vv * 100
            elif 56 <= s_vv <= 80: return (s_vv - 50) * 1000
            elif 81 <= s_vv <= 89: return 30000 + (s_vv - 80) * 5000
            elif s_vv == 90: return 0
            elif s_vv == 91: return 50
            elif s_vv == 92: return 200
            elif s_vv == 93: return 500
            elif s_vv == 94: return 1000
            elif s_vv == 95: return 2000
            elif s_vv == 96: return 4000
            elif s_vv == 97: return 10000
            elif s_vv == 98: return 20000
            elif s_vv == 99: return 50000
        except: pass
        return -1

    def _get_combined_hadise(self):
        hadise = self.met.get('Hadise', '')
        bulten = self.met.get('Bulten', '')
        h_str = "" if pd.isna(hadise) else str(hadise)
        b_str = "" if pd.isna(bulten) else str(bulten)
        
        # Eğer Bülten (raw METAR) geçerli bir mesaj içeriyorsa, Excel'deki manuel 'Hadise' 
        # sütunundaki kopyalama hatalarından (eski saatteki SHRA'nın hücrede kalması vb.) etkilenmemek için 
        # sadece bülteni kullanıyoruz. Bu sayede h371 gibi sahte hatalar kesin olarak engellenir.
        if b_str and len(b_str) > 10 and ("=" in b_str or "KT" in b_str):
            return b_str.upper()
            
        return (h_str + " " + b_str).upper()
        
    def _has_active_wx_match(self, pattern):
        hadise = self._get_combined_hadise()
        # Birden fazla mesaj (Örn: METAR ve SPECI) birleştirilmiş olabilir. '=' ile ayırıp her birini kendi içinde temizle.
        mesajlar = hadise.split('=')
        for mesaj in mesajlar:
            if not mesaj.strip(): continue
            # Trend gruplarından sonrasını at (TEMPO, BECMG, RMK vb. sonrası tahmin/açıklamadır)
            mesaj_clean = re.split(r'\b(TEMPO|BECMG|NOSIG|RMK|PROB\d{2})\b', mesaj)[0].strip()
            for t in mesaj_clean.split():
                # RE (Geçmiş) ve VC (Civarı) hadiseleri aktif hava durumu (ww) sayılmaz!
                if t.startswith("RE") or t.startswith("VC"): continue
                if t in ["AUTO", "CAVOK"]: continue
                if re.search(pattern, t):
                    return True
        return False

    def check_temperature(self):
        """
        METAR ve SİNOPTİK sıcaklıklarını karşılaştırır.
        Otomatik çekilen veriler olduğu için, saatler eşleşmedikçe hata vermez.
        """
        t_sin = self.sin.get('T')
        t_met = self.met.get('Kuru')
        
        if pd.notna(t_sin) and pd.notna(t_met):
            # Saat eşleştirmesi: Eğer GMT saatleri verilmişse kontrol et
            if self.metar_gmt is not None and self.sinoptik_gmt is not None:
                saatler_eslesir, msg, fark_dakika = self.eslestirici.saatler_esilestirilebilir_mi(
                    self.metar_gmt, self.sinoptik_gmt, otomat_veri_mi=True
                )
                if not saatler_eslesir:
                    # Saatler eşleşmiyor, otomatik veri için hata vermiyoruz
                    return
                # Saatler eşleşiyor, hata kontrolü yap
                if abs(t_sin - t_met) > 1.2:
                    self.errors.append({
                        "kod": "h270", 
                        "mesaj": f"Sıcaklık Uyumsuzluğu (SAATLER EŞLEŞTİ): Sinoptik(T)={t_sin}°C, Metar(Kuru)={t_met}°C ({fark_dakika}dk fark)"
                    })
            else:
                # Saat bilgisi yoksa eski kuralı uygula
                if abs(t_sin - t_met) > 1.2:
                    self.errors.append({"kod": "h270", "mesaj": f"Sıcaklık Uyumsuzluğu: Sinoptik(T)={t_sin}, Metar(Kuru)={t_met}"})

    def check_dewpoint(self):
        """
        METAR ve SİNOPTİK işba (çiğlenme) sıcaklıklarını karşılaştırır.
        Otomatik çekilen veriler olduğu için, saatler eşleşmedikçe hata vermez.
        """
        td_sin = self.sin.get('Td')
        td_met = self.met.get('İşba')
        
        if pd.notna(td_sin) and pd.notna(td_met):
            # Saat eşleştirmesi
            if self.metar_gmt is not None and self.sinoptik_gmt is not None:
                saatler_eslesir, msg, fark_dakika = self.eslestirici.saatler_esilestirilebilir_mi(
                    self.metar_gmt, self.sinoptik_gmt, otomat_veri_mi=True
                )
                if not saatler_eslesir:
                    return
                if abs(td_sin - td_met) > 1.2:
                    self.errors.append({
                        "kod": "h271", 
                        "mesaj": f"İşba Uyumsuzluğu (SAATLER EŞLEŞTİ): Sinoptik(Td)={td_sin}°C, Metar(İşba)={td_met}°C ({fark_dakika}dk fark)"
                    })
            else:
                if abs(td_sin - td_met) > 1.2:
                    self.errors.append({"kod": "h271", "mesaj": f"İşba Uyumsuzluğu: Sinoptik(Td)={td_sin}, Metar(İşba)={td_met}"})
                
    def check_humidity(self):
        """Nem yüzdesini karşılaştırır. Otomatik veriler için saat eşleştirmesi yapılır."""
        rh_sin = self.sin.get('Rh')
        rh_met = self.met.get('%')
        
        if pd.notna(rh_sin) and pd.notna(rh_met):
            if self.metar_gmt is not None and self.sinoptik_gmt is not None:
                saatler_eslesir, msg, fark_dakika = self.eslestirici.saatler_esilestirilebilir_mi(
                    self.metar_gmt, self.sinoptik_gmt, otomat_veri_mi=True
                )
                if not saatler_eslesir:
                    return
                if abs(rh_sin - rh_met) > 10:  # %10 tolerans
                    self.errors.append({
                        "kod": "h272", 
                        "mesaj": f"Nem Uyumsuzluğu (SAATLER EŞLEŞTİ): Sinoptik(Rh)={rh_sin}%, Metar(%)={rh_met}% ({fark_dakika}dk fark)"
                    })
            else:
                if abs(rh_sin - rh_met) > 10:
                    self.errors.append({"kod": "h272", "mesaj": f"Nem Uyumsuzluğu: Sinoptik(Rh)=%{rh_sin}, Metar(%)={rh_met}"})

    def check_pressure(self):
        """METAR ve SİNOPTİK basınç eşleştirmesi kullanıcı isteğiyle iptal edildi. Sadece QFE<=QNH mantık denetimi uygulanır."""
        pass
                
    def check_pressure_reduction(self):
        """Basınç indirgeme tutarlılığı kullanıcı isteğiyle muaf tutuldu."""
        pass

    def check_wind_speed(self):
        """Rüzgar hızını karşılaştırır. Kullanıcı beyanına göre SİNOPTİK verileri (ff) zaten Knot cinsindendir."""
        ff_sin = self.sin.get('ff')
        sknt_met = self.met.get('Hız')
        
        if pd.notna(ff_sin) and pd.notna(sknt_met):
            # Saat eşleştirmesi
            if self.metar_gmt is not None and self.sinoptik_gmt is not None:
                saatler_eslesir, msg, fark_dakika = self.eslestirici.saatler_esilestirilebilir_mi(
                    self.metar_gmt, self.sinoptik_gmt, otomat_veri_mi=True
                )
                if not saatler_eslesir:
                    return  # Saatler eşleşmediyse kontrol yapma
            
            # İkisi de knot kabul ediliyor, doğrudan tolerans ile kıyasla (5 Knot)
            if abs(ff_sin - sknt_met) > 5.0:
                self.errors.append({"kod": "h273", "mesaj": f"Rüzgar Hızı Uyumsuz: Sinoptik(ff)={ff_sin} kt, Metar(Hız)={sknt_met} kt"})
                
    def check_wind_unit(self):
        """Excel verisi zaten Knot olduğundan m/s-Knot karışma riski uyarısı (eşitlik kontrolü) iptal edildi."""
        pass

    def check_wind_dir(self):
        """Rüzgar yönünü karşılaştırır. Otomatik çekilen veri olduğu için saat eşleştirmesi yapılır."""
        dd_sin = self.sin.get('dd')
        dir_met = self.met.get('Yön')
        sknt_met = self.met.get('Hız')
        istasyon_no = str(self.sin.get('istasyon_no', '')).strip()
        
        # Otomatik verilerde dd derece olarak girilmiş olabilir
        if pd.notna(dd_sin) and dd_sin > 36 and dd_sin <= 360 and dd_sin != 99:
            dd_sin = round(dd_sin / 10)
        
        # --- İSTASYONA ÖZEL TOLERANS AYARI ---
        # Varsayılan rüzgar yönü toleransı (Derece):
        tolerans = 10 
        
        ozel_toleranslar = {
            "17060": 20,  # Örnek: 17060 istasyonu için tolerans 20 derece
            "17624": 30   # Örnek: 17624 istasyonu için tolerans 30 derece
        }
        if istasyon_no in ozel_toleranslar:
            tolerans = ozel_toleranslar[istasyon_no]
        
        # METAR'da 3 knot ve altı rüzgarlarda yön VRB (Değişken) kabul edilir.
        if pd.notna(sknt_met) and sknt_met <= 3:
            return
        
        # VRB (değişken rüzgar) kontrolü - yön belirsiz ise kontrol yapma
        if dir_met is not None:
            dir_str = str(dir_met).strip().upper()
            if 'VRB' in dir_str or 'VAR' in dir_str:
                return  # Değişken rüzgar, yön kontrolü yapılmaz
        
        if pd.notna(dd_sin) and pd.notna(dir_met) and dd_sin != 99:
            # Saat eşleştirmesi
            if self.metar_gmt is not None and self.sinoptik_gmt is not None:
                saatler_eslesir, msg, fark_dakika = self.eslestirici.saatler_esilestirilebilir_mi(
                    self.metar_gmt, self.sinoptik_gmt, otomat_veri_mi=True
                )
                if not saatler_eslesir:
                    return  # Saatler eşleşmediyse kontrol yapma
            
            # dd=00 özel durumu: sakin rüzgar (dd=00) ise, dir_met=0 olabilir
            # Ama dd!=00 ise yön kontrolü yap
            if dd_sin != 0:
                try:
                    dir_met_num = float(dir_met) if dir_met is not None else None
                    if dir_met_num is not None and dir_met_num >= 0:  # Geçerli derece
                        dd_deg = dd_sin * 10
                        diff = min((dd_deg - dir_met_num) % 360, (dir_met_num - dd_deg) % 360)
                
                        # AMBİGÜİTE DÜZELTMESİ: Eğer dd_sin <= 36 ise hem kod (x10) hem de derece olarak kontrol et
                        if diff > tolerans and dd_sin <= 36:
                            diff_alt = min((dd_sin - dir_met_num) % 360, (dir_met_num - dd_sin) % 360)
                            if diff_alt <= tolerans:
                                diff = diff_alt
                                dd_deg = dd_sin  # Derece olarak kabul et

                        if diff > 30:
                            self.errors.append({"kod": "h274", "mesaj": f"Rüzgar Yönü Uyumsuz: Sinoptik(dd)={dd_deg}°, Metar(Yön)={dir_met_num}°"})
                        elif diff > tolerans:
                            self.errors.append({"kod": "h274", "mesaj": f"Rüzgar Yönü Uyumsuz: Sinoptik(dd)={dd_deg}°, Metar(Yön)={dir_met_num}° (Tol: {tolerans}°)"})
                except (ValueError, TypeError):
                    pass  # dir_met sayısal değil ise kontrol yapma

    def check_calm_wind(self):
        ff_sin = self.sin.get('ff')
        dd_sin = self.sin.get('dd')
        if ff_sin == 0 and pd.notna(dd_sin) and dd_sin > 0:
            self.errors.append({"kod": "h275", "mesaj": f"Sakin Rüzgar Çelişkisi: Rüzgar hızı 0 iken, yön {dd_sin} girilmiş."})
            
    def check_wind_gust(self):
        ff_sin = self.sin.get('ff')
        g910 = self.sin.get('910')
        g911 = self.sin.get('911')
        
        if pd.notna(ff_sin) and pd.notna(g910) and g910 < ff_sin:
            self.errors.append({"kod": "h276", "mesaj": f"910 Grubu Hatası: Anlık hamle ({g910}), normal rüzgar hızından ({ff_sin}) küçük olamaz."})
            
        if pd.notna(g910) and pd.notna(g911):
            if g911 < g910:
                self.errors.append({"kod": "h277", "mesaj": f"911 Grubu Hatası: Maksimum hamle ({g911}), anlık hamleden ({g910}) küçük olamaz."})
        elif pd.notna(ff_sin) and pd.notna(g911) and g911 < ff_sin:
            self.errors.append({"kod": "h277", "mesaj": f"911 Grubu Hatası: Maksimum hamle ({g911}), normal rüzgar hızından ({ff_sin}) küçük olamaz."})

    def check_clouds(self):
        n_sin = self.sin.get('N')
        tkp_met = self.met.get('T. Kp.')
        if pd.notna(n_sin) and pd.notna(tkp_met):
            n_val = int(n_sin)
            m_val = int(tkp_met)
            
            if n_val == 9 and m_val in [8, 9]:
                pass  # N=9 (Gökyüzü görünmüyor) METAR'da OVC(8) veya VV(9) ile tolere edilebilir
            elif m_val == 9 and n_val in [8, 9]:
                pass
            elif abs(n_val - m_val) > 1:
                self.errors.append({"kod": "h278", "mesaj": f"Toplam Bulut Kapalılığı Uyumsuz: Sin(N)={n_val}, Metar(T. Kp)={m_val} (Tol: ±1 okta)"})
            elif n_val != m_val:
                self.errors.append({"kod": "h278", "mesaj": f"Toplam Bulut Kapalılığı Uyumsuz: Sin(N)={n_val}, Metar(T. Kp)={m_val}"})

    def check_cloud_base_crosscheck(self):
        h_sin = self.sin.get('h')
        bulten = str(self.met.get('Bulten', '')).upper()
        
        # METAR bulut gruplarını bul (Örn: SCT///, BKN015CB)
        cloud_groups = re.findall(r'\b(FEW|SCT|BKN|OVC|VV)(///|\d{3})(CB|TCU|///)?\b', bulten)
        if cloud_groups and len(cloud_groups) > 0:
            lowest_cloud_height = cloud_groups[0][1]
            
            # METAR'da en alt bulut yüksekliği ölçülemiyorsa (///) ve SİNOPTİK'te bir değer girilmişse
            if lowest_cloud_height == "///" and pd.notna(h_sin):
                self.errors.append({
                    "kod": "h279", 
                    "mesaj": f"METAR'da en alt bulutun yüksekliği ölçülemiyor (///) olarak raporlanmış, ancak SİNOPTİK'te bulut yüksekliği (h={int(h_sin)}) girilmiş."
                })

    def check_clouds_detail(self):
        # Bulut Cinsleri (WMO Kodlarına Göre Sinoptik Eşleşmeleri)
        for i in range(1, 5):
            bg_sin = self.sin.get(f'Bg{i}')
            cins_met = self.met.get(f'{i}. BULUT Cins')
            
            if pd.notna(bg_sin) and pd.notna(cins_met) and str(bg_sin).strip() != "" and str(cins_met).strip() != "":
                bg_str = str(bg_sin).strip()
                
                # Excel'deki uzun 8-grubu metni (örn: 82715.0) Bg sütununa yanlışlıkla girilmişse düzelt
                if len(bg_str) > 1:
                    if bg_str.endswith(".0"): bg_str = bg_str[:-2]
                    if len(bg_str) == 5 and bg_str.startswith("8"):
                        bg_str = bg_str[2] # 8 Ns C hshs -> C (cins) 2. indekstir
                    else:
                        continue # Tanınmayan uzun bir değerse çapraz kontrolü atla
                        
                cins_str = str(cins_met).strip().upper()
                
                if 'CB' in cins_str and bg_str not in ['3', '9']:
                    self.errors.append({"kod": "h280", "mesaj": f"Bulut Cinsi Uyumsuzluğu ({i}. Katman): Metar'da CB var, Sinoptik Bg{i}={bg_str} (3 veya 9 beklenir)"})
                elif 'TCU' in cins_str and bg_str != '2':
                    self.errors.append({"kod": "h280", "mesaj": f"Bulut Cinsi Uyumsuzluğu ({i}. Katman): Metar'da TCU var, Sinoptik Bg{i}={bg_str} (2 beklenir)"})
                elif 'ST' in cins_str and bg_str not in ['6', '7']:
                    self.errors.append({"kod": "h280", "mesaj": f"Bulut Cinsi Uyumsuzluğu ({i}. Katman): Metar'da St var, Sinoptik Bg{i}={bg_str} (CL/C kodu 6 veya 7 beklenir)"})
                elif 'SC' in cins_str and bg_str not in ['4', '5', '6', '8']:
                    self.errors.append({"kod": "h280", "mesaj": f"Bulut Cinsi Uyumsuzluğu ({i}. Katman): Metar'da Sc var, Sinoptik Bg{i}={bg_str} (CL/C kodu 4, 5, 6 veya 8 beklenir)"})
                elif 'CU' in cins_str and 'TCU' not in cins_str and bg_str not in ['1', '2', '8']:
                    self.errors.append({"kod": "h280", "mesaj": f"Bulut Cinsi Uyumsuzluğu ({i}. Katman): Metar'da Cu var, Sinoptik Bg{i}={bg_str} (CL/C kodu 1, 2 veya 8 beklenir)"})
                elif 'AS' in cins_str and bg_str not in ['1', '2', '4']:
                    self.errors.append({"kod": "h280", "mesaj": f"Bulut Cinsi Uyumsuzluğu ({i}. Katman): Metar'da As var, Sinoptik Bg{i}={bg_str} (CM/C kodu 1, 2 veya 4 beklenir)"})
                elif 'AC' in cins_str and bg_str not in ['3', '4', '5', '6', '7', '8', '9']:
                    self.errors.append({"kod": "h280", "mesaj": f"Bulut Cinsi Uyumsuzluğu ({i}. Katman): Metar'da Ac var, Sinoptik Bg{i}={bg_str} (CM/C kodu 3-9 arası beklenir)"})
                elif 'NS' in cins_str and bg_str not in ['2', '5']:
                    self.errors.append({"kod": "h280", "mesaj": f"Bulut Cinsi Uyumsuzluğu ({i}. Katman): Metar'da Ns var, Sinoptik Bg{i}={bg_str} (CM/C kodu 2 veya 5 beklenir)"})
                elif 'CI' in cins_str and bg_str not in ['0', '1', '2', '3', '4']:
                    self.errors.append({"kod": "h280", "mesaj": f"Bulut Cinsi Uyumsuzluğu ({i}. Katman): Metar'da Ci var, Sinoptik Bg{i}={bg_str} (CH/C kodu 0, 1, 2, 3 veya 4 beklenir)"})
                elif 'CS' in cins_str and bg_str not in ['2', '5', '6', '7', '8']:
                    self.errors.append({"kod": "h280", "mesaj": f"Bulut Cinsi Uyumsuzluğu ({i}. Katman): Metar'da Cs var, Sinoptik Bg{i}={bg_str} (CH/C kodu 2, 5, 6, 7 veya 8 beklenir)"})
                elif 'CC' in cins_str and bg_str not in ['1', '9']:
                    self.errors.append({"kod": "h280", "mesaj": f"Bulut Cinsi Uyumsuzluğu ({i}. Katman): Metar'da Cc var, Sinoptik Bg{i}={bg_str} (CH/C kodu 1 veya 9 beklenir)"})

    def check_visibility_and_fog(self):
        vv_sin = self.sin.get('VV')
        ww_sin = self.sin.get('ww')
        vis_met = self.met.get('Hakim')
        hadise_met = self._get_combined_hadise()
        # TREND GRUPLARINI TEMİZLE (Birden fazla mesaj olabilir, '=' ile ayır)
        hadise_met_clean = ""
        for mesaj in hadise_met.split('='):
            if mesaj.strip():
                mesaj_clean = re.split(r'\b(TEMPO|BECMG|NOSIG|RMK|PROB\d{2})\b', mesaj)[0].strip()
                hadise_met_clean += " " + mesaj_clean

        # Sinoptik Sis / Görüş Kontrolü
        if pd.notna(vv_sin):
            if vv_sin < 60 and (pd.isna(ww_sin) or ww_sin < 4):
                self.errors.append({"kod": "h281", "mesaj": f"Sinoptik: Görüş 10 km'nin altında (VV={int(vv_sin)}) ancak görüşü kısıtlayan belirgin bir hadise (ww) girilmemiş."})
            if pd.notna(ww_sin) and 40 <= ww_sin <= 49 and vv_sin >= 10:
                self.errors.append({"kod": "h282", "mesaj": f"Sinoptik: Sis hadisesi (ww={int(ww_sin)}) kodlanmış ancak görüş 1 km veya üzerinde (VV={int(vv_sin)}). Sis için görüş < 1 km olmalıdır."})

        # METAR Sis / Görüş Kontrolü
        if pd.notna(vis_met):
            # Parçalı sisler (BCFG vb.) görüşü tamamen 1km altına düşürmeyebilir, bu yüzden sadece tam sisleri (FG) arıyoruz.
            tam_sis_var = False
            for token in hadise_met_clean.split():
                if token in ["FG", "FZFG", "+FG", "-FG"]:
                    tam_sis_var = True
                    break
            
            if tam_sis_var and vis_met >= 1000:
                self.errors.append({"kod": "h282", "mesaj": f"METAR: Tam Sis (FG) raporlanmış ancak görüş 1000m veya üzerinde (Hakim={int(vis_met)}m). Tam sis için Hakim Görüş < 1000m olmalıdır."})
            
            if vis_met < 1000:
                kisitlayici_kodlar = ["FG", "BR", "HZ", "RA", "SN", "DZ", "GR", "GS", "SG", "PL", "SA", "DU", "FU", "VA", "SQ", "PO", "FC", "SS", "DS"]
                
                hadise_var = False
                for token in hadise_met_clean.split():
                    token_clean = re.sub(r'^(RE|\+|-|VC)*', '', token)
                    if any(kod in token_clean for kod in kisitlayici_kodlar):
                        hadise_var = True
                        break
                        
                if not hadise_var and "CAVOK" not in hadise_met_clean:
                    self.errors.append({"kod": "h281", "mesaj": f"METAR: Görüş 1 km'nin altında ({int(vis_met)}m) ancak görüşü kısıtlayan belirgin bir hadise (FG, SN, RA vb.) raporlanmamış."})

        # Çapraz Kontrol (METAR < 1000m vs Sinoptik VV < 10)
        is_cavok = "CAVOK" in hadise_met_clean
        if pd.notna(vv_sin):
            s_vv = float(vv_sin)
            s_vis = self._vv_to_meters(s_vv)
            if s_vis != -1:
                if is_cavok:
                    if s_vv < 60:
                        self.errors.append({"kod": "h283", "mesaj": f"Çapraz Görüş Çelişkisi: METAR CAVOK (Görüş >= 10km) iken, Sinoptik VV={int(s_vv)} ({int(s_vis)}m) girilmiş."})
                    
                    n_sin = self.sin.get('N')
                    h_sin = self.sin.get('h')
                    cl_sin = self.sin.get('Bg1')
                    if pd.notna(n_sin) and n_sin > 0:
                        if pd.notna(h_sin) and h_sin < 6:
                            self.errors.append({"kod": "h284", "mesaj": f"Çapraz Bulut Çelişkisi: METAR CAVOK iken Sinoptik'te 1500m (5000ft) altında bulut girilmiş (h={int(h_sin)})."})
                        if pd.notna(cl_sin) and cl_sin in [2, 3, 9]:
                            self.errors.append({"kod": "h285", "mesaj": f"Çapraz Bulut Çelişkisi: METAR CAVOK iken Sinoptik'te Kümülonimbüs veya TCU (CL={int(cl_sin)}) girilmiş."})
                elif pd.notna(vis_met):
                    m_vis = float(vis_met)
                    if m_vis >= 9999:
                        if s_vv < 60:
                            self.errors.append({"kod": "h283", "mesaj": f"Çapraz Görüş Çelişkisi: METAR 10km+ (>=10000m) iken, Sinoptik VV={int(s_vv)} ({int(s_vis)}m) girilmiş."})
                    else:
                        tolerans = 1000 if m_vis <= 10000 else 2000
                        if abs(m_vis - s_vis) > tolerans:
                            self.errors.append({"kod": "h283", "mesaj": f"Çapraz Görüş Çelişkisi: Sinoptik VV={int(s_vv)} ({int(s_vis)}m), METAR={int(m_vis)}m."})

    def check_thunderstorm_and_hail(self):
        ww_list = []
        ww_sin = self.sin.get('ww')
        if pd.notna(ww_sin):
            try: ww_list.append(int(ww_sin))
            except ValueError: pass
            
        g960 = self.sin.get('960')
        if pd.notna(g960):
            try:
                g960_str = str(int(float(g960)))
                if len(g960_str) == 5 and g960_str.startswith('960'): ww_list.append(int(g960_str[3:]))
                elif len(g960_str) <= 2: ww_list.append(int(g960_str))
            except: pass
            
        if not ww_list:
            return
                
        has_ts = self._has_active_wx_match(r'TS')
        has_hail = self._has_active_wx_match(r'GR|GS')
        
        def check_codes(codes):
            return any(w in codes for w in ww_list)
        
        # 1. Sinoptik'te 91-99 arası (Oraj) verilmişse METAR'da TS olmalıdır (90 geçmiş saatte orajı ifade eder)
        if check_codes(list(range(91, 100))) and not has_ts:
            bad_w = next(w for w in ww_list if 91 <= w <= 99)
            self.errors.append({"kod": "h286", "mesaj": f"Sinoptik'te {bad_w} (Oraj) kodlanmış ancak METAR'da Oraj (TS) raporlanmamış."})
            
        # 2. Dolusuz Oraj (95, 97) ama METAR'da Dolu (GR/GS) var
        if check_codes([95, 97]) and has_hail:
            bad_w = next(w for w in ww_list if w in [95, 97])
            self.errors.append({"kod": "h287", "mesaj": f"Sinoptik'te {bad_w} (Dolusuz Oraj) kodlanmış ancak METAR'da Dolu (GR/GS) raporlanmış."})
            
        # 3. Dolulu Oraj (96, 99) ama METAR'da Dolu yok
        if check_codes([96, 99]) and not has_hail:
            bad_w = next(w for w in ww_list if w in [96, 99])
            self.errors.append({"kod": "h288", "mesaj": f"Sinoptik'te {bad_w} (Dolulu Oraj) kodlanmış ancak METAR'da Dolu (GR/GS) raporlanmamış."})

        # 4. METAR'da hem TS hem Dolu varsa, Sinoptik kod buna uygun (Örn: 90, 93, 94, 96, 99) olmalıdır
        if has_ts and has_hail:
            if not check_codes([90, 93, 94, 96, 99]):
                self.errors.append({"kod": "h289", "mesaj": f"METAR'da Oraj ve Dolu (TS + GR/GS) var, ancak Sinoptik {ww_list} kodu uyumsuz (90, 93, 94, 96 veya 99 beklenir)."})
                    
    def check_hail_size(self):
        ww_list = []
        ww_sin = self.sin.get('ww')
        if pd.notna(ww_sin):
            try: ww_list.append(int(ww_sin))
            except ValueError: pass
            
        g960 = self.sin.get('960')
        if pd.notna(g960):
            try:
                g960_str = str(int(float(g960)))
                if len(g960_str) == 5 and g960_str.startswith('960'): ww_list.append(int(g960_str[3:]))
                elif len(g960_str) <= 2: ww_list.append(int(g960_str))
            except: pass
            
        g924 = self.sin.get('924')
        
        has_hail_met = self._has_active_wx_match(r'GR|GS')
        has_hail_sin = any(w in [87, 88, 89, 90, 93, 94, 96, 99] for w in ww_list)
                
        if (has_hail_met or has_hail_sin) and pd.isna(g924):
            self.errors.append({"kod": "h290", "mesaj": "Dolu (GR/GS veya ww kodu) raporlanmış ancak dolu çapı/miktarı (924 grubu) girilmemiş."})
        elif not (has_hail_met or has_hail_sin) and pd.notna(g924):
            self.errors.append({"kod": "h290", "mesaj": "Dolu raporlanmamasına rağmen 924 (Dolu Çapı) grubu girilmiş."})

    def check_specific_weather_phenomena(self):
        vis_met = self.met.get('Hakim')
        
        ww_list = []
        ww_sin = self.sin.get('ww')
        if pd.notna(ww_sin) and str(ww_sin).strip() != "":
            try: ww_list.append(int(float(str(ww_sin).strip())))
            except Exception: pass
            
        g960 = self.sin.get('960')
        if pd.notna(g960) and str(g960).strip() != "":
            try:
                g960_str = str(int(float(str(g960).strip())))
                if len(g960_str) == 5 and g960_str.startswith('960'): ww_list.append(int(g960_str[3:]))
                elif len(g960_str) == 5 and g960_str.startswith('961'): ww_list.append(int(g960_str[3:]))
                elif len(g960_str) <= 2: ww_list.append(int(g960_str))
            except Exception: pass
            
        # --- YENİ: RAW SİNOPTİK İÇİNDEN DİREKT WW VE 960 GRUBU ÇIKARMA ---
        raw_sinoptik = str(self.sin.get('RASATLAR', ''))
        if raw_sinoptik:
            m_ww = re.search(r'\b7(\d{2})\d{2}\b', raw_sinoptik)
            if m_ww and int(m_ww.group(1)) not in ww_list:
                ww_list.append(int(m_ww.group(1)))
                
            for match in re.finditer(r'\b96[01](\d{2})\b', raw_sinoptik):
                code = int(match.group(1))
                if code not in ww_list:
                    ww_list.append(code)
                
        if not ww_list:
            return
                
        has_fz = self._has_active_wx_match(r'FZ(RA|DZ)')
        has_sn = self._has_active_wx_match(r'(?<!BL)(?<!DR)(SN|SG)')
        has_br = self._has_active_wx_match(r'BR')
        has_fu_va = self._has_active_wx_match(r'FU|VA')
        has_hz = self._has_active_wx_match(r'HZ')
        has_ss_ds = self._has_active_wx_match(r'SS|DS')
        has_po = self._has_active_wx_match(r'PO')
        has_sh = self._has_active_wx_match(r'SH')
        has_blsn_drsn = self._has_active_wx_match(r'(BL|DR)SN')
        has_ts = self._has_active_wx_match(r'TS')
        has_fzfg = self._has_active_wx_match(r'FZFG')
        has_fg = self._has_active_wx_match(r'(?<!FZ)FG')
        
        def check_codes(codes):
            return any(w in codes for w in ww_list)
            
        fz_codes = [56, 57, 66, 67]
        if has_fz:
            has_higher_priority = any(w >= 80 for w in ww_list) # Sağanak/Oraj öncelikli olabilir
            if not check_codes(fz_codes) and not has_higher_priority:
                try: ww_msg = f"ww={int(float(ww_sin))}"
                except: ww_msg = f"{ww_list}"
                self.errors.append({"kod": "h364", "mesaj": f"METAR'da Donduran Yağış/Çisenti (FZRA/FZDZ) var, ancak Sinoptik {ww_msg} uyumsuz (56, 57, 66, 67 veya daha büyük öncelikli hadise beklenir)."})
        elif check_codes(fz_codes) and not has_fz:
            bad_w = next(w for w in ww_list if w in fz_codes)
            self.errors.append({"kod": "h364", "mesaj": f"Sinoptik'te {bad_w} (Donduran Yağış/Çisenti) kodlanmış ancak METAR'da FZRA/FZDZ raporlanmamış."})
            
        kar_kodlari = list(range(70, 80)) + [68, 69, 83, 84, 85, 86]
        if has_sn:
            has_higher_priority = any(w >= 90 for w in ww_list)
            if not check_codes(kar_kodlari) and not has_higher_priority:
                try: ww_msg = f"ww={int(float(ww_sin))}"
                except: ww_msg = f"{ww_list}"
                self.errors.append({"kod": "h365", "mesaj": f"METAR'da Kar (SN) raporlanmış, ancak Sinoptik {ww_msg} uyumsuz (70-79, 83-86, 68-69 veya daha büyük öncelikli hadise beklenir)."})
        elif check_codes([70, 71, 72, 73, 74, 75, 85, 86]) and not has_sn:
            bad_w = next(w for w in ww_list if w in [70, 71, 72, 73, 74, 75, 85, 86])
            self.errors.append({"kod": "h365", "mesaj": f"Sinoptik'te {bad_w} (Kar Yağışı) kodlanmış ancak METAR'da Kar (SN) raporlanmamış."})
            
        if has_br:
            # WMO Kuralları: Kod numarası 10'dan büyük olan herhangi bir hadise Pus'tan (10) daha yüksek önceliklidir.
            # Örn: ww=61 (Yağmur) varsa 10 (Pus) girmese bile doğru kabul edilir.
            has_higher_priority = any(w > 10 for w in ww_list)
            if not check_codes([10]) and not has_higher_priority:
                # YENİ İSTİSNA: METAR'da BR olsa dahi görüş 5000 metreden iyi ise Sinoptik'te 10 zorunlu değildir.
                if pd.isna(vis_met) or float(vis_met) <= 5000:
                    try: ww_msg = f"ww={int(float(ww_sin))}"
                    except: ww_msg = f"{ww_list}"
                    self.errors.append({"kod": "h366", "mesaj": f"METAR'da Pus (BR) var (Görüş <= 5000m), ancak Sinoptik {ww_msg} uyumsuz (10 veya daha büyük öncelikli hadise beklenir). [KESİN ÇÖZÜM]"})
        elif check_codes([10]) and not has_br:
            if pd.isna(vis_met) or vis_met <= 5000:
                self.errors.append({"kod": "h366", "mesaj": f"Sinoptik'te 10 (Pus) kodlanmış ancak METAR'da Pus (BR) raporlanmamış (Görüş <= 5000m iken beklenir)."})
            
        if has_fu_va:
            # Duman/Kül (04). 4'ten büyük tüm hadiseler daha yüksek önceliklidir.
            has_higher_priority = any(w > 4 for w in ww_list)
            if not check_codes([4]) and not has_higher_priority:
                try: ww_msg = f"ww={int(float(ww_sin))}"
                except: ww_msg = f"{ww_list}"
                self.errors.append({"kod": "h367", "mesaj": f"METAR'da Duman/Volkanik Kül (FU/VA) var, ancak Sinoptik {ww_msg} uyumsuz (04 veya daha büyük öncelikli hadise beklenir)."})
        elif check_codes([4]) and not has_fu_va:
            if pd.isna(vis_met) or vis_met <= 5000:
                self.errors.append({"kod": "h367", "mesaj": f"Sinoptik'te 04 (Duman/Volkanik Kül) kodlanmış ancak METAR'da FU veya VA raporlanmamış (Görüş <= 5000m iken beklenir)."})
            
        if has_hz:
            # Toz Pusu (05). 5'ten büyük tüm hadiseler daha yüksek önceliklidir.
            has_higher_priority = any(w > 5 for w in ww_list)
            if not check_codes([5]) and not has_higher_priority:
                try: ww_msg = f"ww={int(float(ww_sin))}"
                except: ww_msg = f"{ww_list}"
                self.errors.append({"kod": "h368", "mesaj": f"METAR'da Toz Pusu (HZ) var, ancak Sinoptik {ww_msg} uyumsuz (05 veya daha büyük öncelikli hadise beklenir)."})
        elif check_codes([5]) and not has_hz:
            if pd.isna(vis_met) or vis_met <= 5000:
                self.errors.append({"kod": "h368", "mesaj": f"Sinoptik'te 05 (Toz Pusu) kodlanmış ancak METAR'da Toz Pusu (HZ) raporlanmamış (Görüş <= 5000m iken beklenir)."})

        ss_ds_codes = list(range(30, 36))
        if has_ss_ds:
            has_higher_priority = any(w > 35 for w in ww_list)
            if not check_codes(ss_ds_codes) and not has_higher_priority:
                try: ww_msg = f"ww={int(float(ww_sin))}"
                except: ww_msg = f"{ww_list}"
                self.errors.append({"kod": "h369", "mesaj": f"METAR'da Kum/Toz Fırtınası (SS/DS) var, ancak Sinoptik {ww_msg} uyumsuz (30-35 veya daha büyük öncelikli hadise beklenir)."})
        elif check_codes(ss_ds_codes) and not has_ss_ds:
            bad_w = next(w for w in ww_list if w in ss_ds_codes)
            self.errors.append({"kod": "h369", "mesaj": f"Sinoptik'te {bad_w} (Kum/Toz Fırtınası) kodlanmış ancak METAR'da SS/DS raporlanmamış."})
            
        if has_po:
            has_higher_priority = any(w > 8 for w in ww_list)
            if not check_codes([8]) and not has_higher_priority:
                try: ww_msg = f"ww={int(float(ww_sin))}"
                except: ww_msg = f"{ww_list}"
                self.errors.append({"kod": "h370", "mesaj": f"METAR'da Toz Şeytanı (PO) var, ancak Sinoptik {ww_msg} uyumsuz (08 veya daha büyük öncelikli hadise beklenir)."})
        elif check_codes([8]) and not has_po:
            self.errors.append({"kod": "h370", "mesaj": f"Sinoptik'te 08 (Toz Şeytanı) kodlanmış ancak METAR'da Toz Şeytanı (PO) raporlanmamış."})

        sh_codes = list(range(80, 91))
        if has_sh:
            has_higher_priority = any(w > 90 for w in ww_list) # TS (Oraj) sağanaktan üstündür
            if not check_codes(sh_codes) and not has_higher_priority:
                try: ww_msg = f"ww={int(float(ww_sin))}"
                except: ww_msg = f"{ww_list}"
                self.errors.append({"kod": "h371", "mesaj": f"METAR'da Sağanak Yağış (SH..) var, ancak Sinoptik {ww_msg} uyumsuz (80-90 arası veya daha büyük öncelikli hadise beklenir)."})
        elif check_codes(sh_codes) and not (has_sh or has_ts):
            bad_w = next(w for w in ww_list if w in sh_codes)
            self.errors.append({"kod": "h371", "mesaj": f"Sinoptik'te {bad_w} (Sağanak Yağış) kodlanmış ancak METAR'da Sağanak (SH) raporlanmamış."})

        blsn_codes = list(range(36, 40))
        if has_blsn_drsn:
            has_higher_priority = any(w > 39 for w in ww_list)
            if not check_codes(blsn_codes) and not has_higher_priority:
                try: ww_msg = f"ww={int(float(ww_sin))}"
                except: ww_msg = f"{ww_list}"
                self.errors.append({"kod": "h372", "mesaj": f"METAR'da Sürüklenen/Savrulan Kar (BLSN/DRSN) var, ancak Sinoptik {ww_msg} uyumsuz (36-39 arası veya daha büyük öncelikli hadise beklenir)."})
        elif check_codes(blsn_codes) and not has_blsn_drsn:
            bad_w = next(w for w in ww_list if w in blsn_codes)
            self.errors.append({"kod": "h372", "mesaj": f"Sinoptik'te {bad_w} (Sürüklenen/Savrulan Kar) kodlanmış ancak METAR'da BLSN veya DRSN raporlanmamış."})
            
        if has_blsn_drsn or check_codes(blsn_codes):
            ff_sin = self.sin.get('ff')
            if ff_sin is not None and ff_sin < 3:
                bad_w = next((w for w in ww_list if w in blsn_codes), ww_list[0] if ww_list else "")
                self.errors.append({"kod": "VAL_MANTIK_BLSN", "mesaj": f"Kar Savrulması (BLSN/DRSN veya ww/960={bad_w}) raporlanmış ancak rüzgar hızı çok düşük (Sinoptik ff={ff_sin} m/s). Savrulma için genelde >=3 m/s rüzgar beklenir."})

        if has_fzfg:
            has_higher_priority = any(w > 49 for w in ww_list)
            if not check_codes([48, 49]) and not has_higher_priority:
                try: ww_msg = f"ww={int(float(ww_sin))}"
                except: ww_msg = f"{ww_list}"
                self.errors.append({"kod": "h380", "mesaj": f"METAR'da Donduran Sis (FZFG) var, ancak Sinoptik {ww_msg} uyumsuz (48 veya 49 beklenir)."})
        elif check_codes([48, 49]) and not has_fzfg:
            bad_w = next(w for w in ww_list if w in [48, 49])
            self.errors.append({"kod": "h380", "mesaj": f"Sinoptik'te {bad_w} (Donduran Sis) kodlanmış ancak METAR'da FZFG raporlanmamış."})

        fg_codes = list(range(40, 48))
        if has_fg:
            has_higher_priority = any(w > 49 for w in ww_list)
            if not check_codes(fg_codes + [28]) and not has_higher_priority:
                try: ww_msg = f"ww={int(float(ww_sin))}"
                except: ww_msg = f"{ww_list}"
                self.errors.append({"kod": "h381", "mesaj": f"METAR'da Sis (FG) var, ancak Sinoptik {ww_msg} uyumsuz (40-47 veya 28 beklenir)."})
            
        # WMO Öncelik Kontrolü (Priority Inversion Check)
        ww_sin_val = self.sin.get('ww')
        if pd.notna(ww_sin_val):
            try:
                main_ww = int(ww_sin_val)
                if len(ww_list) > 1:
                    for ek_ww in ww_list:
                        if ek_ww == main_ww: continue
                        
                        # KURAL İSTİSNASI: 17 hadisesi 20-49 arası hadiselerden üstündür!
                        if (20 <= main_ww <= 49) and ek_ww == 17:
                            self.errors.append({"kod": "h382", "mesaj": f"WMO Öncelik Hatası: 17 (Yağışsız Oraj) hadisesinin 20-49 arası hadiselere göre önceliği vardır. Ana halihazır hava (ww) 17 olmalı, {main_ww} hadisesi 960 grubuna yazılmalıdır."})
                            continue

                        # Aktif yağış/hadise (50-99) her zaman sona eren hadiseden (20-29) önceliklidir
                        if (20 <= main_ww <= 29) and (50 <= ek_ww <= 99):
                            self.errors.append({"kod": "h382", "mesaj": f"WMO Öncelik Hatası: Ana halihazır hava (ww) olarak sona eren hadise ({main_ww}) girilmiş, ancak 960 grubuna aktif hadise ({ek_ww}) yazılmış. Aktif hadiselerin önceliği daha yüksektir, ana ww grubuna {ek_ww} yazılmalıdır."})
                        # Pus (10), duman vb. (04-09) ile aktif yağış (50-99) çelişkisi
                        elif (main_ww <= 19) and (50 <= ek_ww <= 99):
                            if main_ww == 17: continue # 17 bu durumdan muaftır
                            self.errors.append({"kod": "h382", "mesaj": f"WMO Öncelik Hatası: Ana halihazır hava (ww={main_ww}), 960 grubundaki aktif hadiseden ({ek_ww}) daha düşük öncelikli. Ana ww grubuna {ek_ww} yazılmalıdır."})
            except: pass

    def check_windshear(self):
        hadise_met = self._get_combined_hadise()
        ws_met = str(self.met.get('WS', '')).upper()
        
        # '\bWS\b' ile 'WSW' gibi yön kısaltmalarının yanlışlıkla eşleşmesi engellenir
        has_ws = bool(re.search(r'\bWS\b', hadise_met)) or bool(re.search(r'\bWS\b', ws_met)) or (ws_met not in ["", "NAN", "NONE", "NAT"] and "WS" in ws_met)
        
        sknt_met = self.met.get('Hız')
        g910 = self.sin.get('910')
        
        if has_ws:
            hiz_yetersiz = False
            if sknt_met is not None and sknt_met < 10:
                if pd.isna(g910) or (pd.notna(g910) and g910 < 10):
                    hiz_yetersiz = True
            
            if hiz_yetersiz:
                self.errors.append({"kod": "h301", "mesaj": f"METAR'da Windshear (WS) raporlanmış ancak yüzey rüzgar hızı çok düşük (Hız={sknt_met} kt). WS için genellikle kuvvetli rüzgar veya hamle (>10 kt) beklenir."})

    def check_sky_obscured_logic(self):
        n_sin = self.sin.get('N')
        vv_sin = self.sin.get('VV')
        vis_met = self.met.get('Hakim')
        
        ww_list = []
        ww_sin = self.sin.get('ww')
        if pd.notna(ww_sin):
            try: ww_list.append(int(ww_sin))
            except ValueError: pass
            
        g960 = self.sin.get('960')
        if pd.notna(g960):
            try:
                g960_str = str(int(float(g960)))
                if len(g960_str) == 5 and g960_str.startswith('960'): ww_list.append(int(g960_str[3:]))
                elif len(g960_str) <= 2: ww_list.append(int(g960_str))
            except: pass
        
        if pd.notna(n_sin) and n_sin == 9:
            gorus_dusuk = False
            if pd.notna(vv_sin) and vv_sin < 10:
                gorus_dusuk = True
            elif pd.notna(vis_met) and vis_met < 1000:
                gorus_dusuk = True
                
            kapatici_hadise_var = self._has_active_wx_match(r'FG|SN|SS|DS|BLSN|VA|FU|SA|DU')
            
            for ww in ww_list:
                if (40 <= ww <= 49) or (70 <= ww <= 79) or (30 <= ww <= 39) or ww in [4, 5, 8, 28]:
                    kapatici_hadise_var = True
                    break
            
            if not gorus_dusuk:
                self.errors.append({"kod": "h302", "mesaj": f"Gökyüzü görünmez (N=9) kodlanmış ancak görüş 1 km veya daha yüksek. (Sinoptik VV={vv_sin}, METAR={vis_met}m)"})
            elif not kapatici_hadise_var:
                self.errors.append({"kod": "h302", "mesaj": f"Gökyüzü görünmez (N=9) kodlanmış ancak gökyüzünü tamamen kapatacak bir hadise (Sis, Yoğun Kar vb.) raporlanmamış."})

    def check_temp_dewpoint_spread(self):
        pass # Kullanıcı isteğiyle iptal edildi: Spread hatasında hadise kodlamak zorunda değil

    def check_freezing_temp_logic(self):
        t_met = self.met.get('Kuru')
        has_fz = self._has_active_wx_match(r'FZ')
        if has_fz and pd.notna(t_met):
            if t_met > 2.0:
                self.errors.append({"kod": "h304", "mesaj": f"METAR'da Donduran Hadise (FZ..) raporlanmış ancak hava sıcaklığı dondurucu şartlar için çok yüksek (T={t_met}°C)."})

    def check_snow_temp_logic(self):
        """
        METAR'da kar (SN/SG) raporlandığında hava sıcaklığının mantıksal limitler (T <= 4.0) içinde olup olmadığını kontrol eder.
        """
        t_met = self.met.get('Kuru')
        t_sin = self.sin.get('T')
        
        has_sn = self._has_active_wx_match(r'(?<!BL)(?<!DR)(SN|SG|PL)')
        if has_sn:
            temp = t_met if pd.notna(t_met) else t_sin
            if pd.notna(temp) and temp > 4.0:
                self.errors.append({"kod": "h305", "mesaj": f"METAR'da Kar Yağışı (SN/SG vb.) raporlanmış ancak hava sıcaklığı kar için şüpheli derecede yüksek (T={temp}°C)."})

    def check_station_elevation_logic(self):
        qfe_met = self.met.get('QFE')
        qnh_met = self.met.get('QNH')
        
        if pd.notna(qfe_met) and pd.notna(qnh_met):
            diff = qnh_met - qfe_met
            if diff < -2:
                self.errors.append({"kod": "h306", "mesaj": f"QFE ({qfe_met}) değeri QNH ({qnh_met}) değerinden büyük. İstasyon deniz seviyesinin altında değilse, basınç değerleri ters yazılmış olabilir."})
            elif diff > 350:
                # Barometrik formülle kaba rakım hesabı
                h_tahmin = 44330 * (1 - (qfe_met / qnh_met)**0.1903)
                if h_tahmin > 3200:
                    self.errors.append({"kod": "h306", "mesaj": f"QNH-QFE indirgeme farkı anormal yüksek ({diff:.1f} hPa). Tahmini rakım ~{int(h_tahmin)}m hesaplandı. Değerleri kontrol ediniz."})

    def check_decoder_consistency(self):
        """
        Ham (şifreli) SİNOPTİK ve METAR mesajlarını decoder'lar ile çözerek
        Excel'den okunan/girilen hücre verileriyle sağlama (crosscheck) yapar.
        """
        rasat_sin = self.sin.get('RASATLAR', '')
        bulten_met = self.met.get('Bulten', '')

        sin_wind_ok = False
        met_wind_ok = False
        sin_temp_ok = False
        met_temp_ok = False
        sin_dew_ok = False
        met_dew_ok = False
        sin_press_ok = False
        met_press_ok = False
        sin_cloud_ok = False
        met_cloud_ok = False
        sin_vis_ok = False
        met_vis_ok = False
        sin_ww_ok = False
        sin_w1w2_ok = False

        # SİNOPTİK SAĞLAMASI
        if SynopDecoder is not None and pd.notna(rasat_sin) and len(str(rasat_sin).strip()) > 10:
            if ":" not in str(rasat_sin): # Manuel birleştirme değil, gerçek raw format ise
                s_decoder = SynopDecoder()
                s_data = s_decoder.decode_line(str(rasat_sin))
                if s_data:
                    # Sıcaklık Sağlaması
                    s_t = self.sin.get('T')
                    dec_t = s_data.get('sicaklik')
                    if pd.notna(s_t) and dec_t is not None:
                        sin_temp_ok = True
                        if pd.notna(s_t) and abs(float(s_t) - float(dec_t)) > 0.1:
                            self.errors.append({"kod": "h307", "mesaj": f"Şifreli SİNOPTİK mesajı ile Excel verisi çelişiyor! Şifreye göre Sıcaklık={dec_t}°C, Excel'de T={s_t}°C."})
                            
                    # İşba (Çiy Noktası) Sağlaması
                    s_td = self.sin.get('Td')
                    dec_td = s_data.get('isba')
                    if dec_td is not None:
                        sin_dew_ok = True
                        if pd.notna(s_td) and abs(float(s_td) - float(dec_td)) > 0.1:
                            self.errors.append({"kod": "h307", "mesaj": f"Şifreli SİNOPTİK mesajı ile Excel verisi çelişiyor! Şifreye göre İşba={dec_td}°C, Excel'de Td={s_td}°C."})
                    
                    # İstasyon Basıncı (QFE) Sağlaması
                    s_p = self.sin.get('4P') # self.sin['4P'] dictte istasyon basıncı (p_sin) olarak taşınır
                    dec_p = s_data.get('istasyon_basinci_qfe') or s_data.get('istasyon_basinci')
                    if dec_p is not None:
                        sin_press_ok = True
                        if pd.notna(s_p) and abs(float(s_p) - float(dec_p)) > 0.1:
                            self.errors.append({"kod": "h307", "mesaj": f"Şifreli SİNOPTİK mesajı ile Excel verisi çelişiyor! Şifreye göre İst.Basıncı={dec_p} hPa, Excel'de İst.Basıncı={s_p} hPa."})
                            
                    # Deniz Seviyesi Basıncı (QNH) Sağlaması
                    s_p0 = self.sin.get('3Po') # self.sin['3Po'] dictte deniz seviyesi basıncı (p0_sin) olarak taşınır
                    dec_p0 = s_data.get('deniz_seviyesi_basinci_qnh') or s_data.get('deniz_basinci')
                    if dec_p0 is not None:
                        sin_press_ok = True
                        if pd.notna(s_p0) and abs(float(s_p0) - float(dec_p0)) > 0.1:
                            self.errors.append({"kod": "h307", "mesaj": f"Şifreli SİNOPTİK mesajı ile Excel verisi çelişiyor! Şifreye göre Dnz.Basıncı={dec_p0} hPa, Excel'de Dnz.Basıncı={s_p0} hPa."})
                            
                    # Rüzgar Sağlaması (Crosscheck)
                    s_ff = self.sin.get('ff')
                    s_dd = self.sin.get('dd')
                    dec_ff = s_data.get('ruzgar_hiz')
                    if dec_ff is not None:
                        sin_wind_ok = True
                    elif pd.notna(s_ff) or pd.notna(s_dd):
                        self.errors.append({"kod": "h307", "mesaj": "Excel'de Rüzgar (dd/ff) girilmiş ancak şifreli SİNOPTİK mesajında rüzgar grubu hatalı veya eksik."})
                        
                    if 'toplam_bulut' in s_data: sin_cloud_ok = True
                    if 'gorus_kod' in s_data: sin_vis_ok = True
                    if 'halihazir_hava' in s_data: 
                        sin_ww_ok = True
                        s_ww = self.sin.get('ww')
                        dec_ww = s_data.get('halihazir_hava')
                        if pd.notna(s_ww) and str(s_ww).strip() != '' and float(s_ww) != float(dec_ww):
                            self.errors.append({"kod": "h307", "mesaj": f"Şifreli SİNOPTİK mesajı ile Excel verisi çelişiyor! Şifreye göre ww={dec_ww}, Excel'de ww={s_ww}."})
                            
                    s_w1 = self.sin.get('w1')
                    s_w2 = self.sin.get('w2')
                    
                    # Kullanıcı W1 sütununa (Excel'de WW) W1 ve W2'yi birleşik girdiyse (Örn: 82), bunları ayır
                    if pd.notna(s_w1) and str(s_w1).strip() != '':
                        try:
                            w1_val = int(float(s_w1))
                            if w1_val > 9:
                                w1_str = str(w1_val)
                                if len(w1_str) == 2:
                                    s_w1 = float(w1_str[0])
                                    s_w2 = float(w1_str[1])
                                    self.sin['w1'] = s_w1
                                    self.sin['w2'] = s_w2
                        except: pass

                    if 'gecmis_hava1' in s_data:
                        sin_w1w2_ok = True
                        dec_w1 = s_data.get('gecmis_hava1')
                        if pd.notna(s_w1) and str(s_w1).strip() != '' and float(s_w1) != float(dec_w1):
                            self.errors.append({"kod": "h307", "mesaj": f"Şifreli SİNOPTİK mesajı ile Excel verisi çelişiyor! Şifreye göre W1={dec_w1}, Excel'de W1={s_w1}."})
                            
                    if 'gecmis_hava2' in s_data:
                        sin_w1w2_ok = True
                        dec_w2 = s_data.get('gecmis_hava2')
                        if pd.notna(s_w2) and str(s_w2).strip() != '' and float(s_w2) != float(dec_w2):
                            self.errors.append({"kod": "h307", "mesaj": f"Şifreli SİNOPTİK mesajı ile Excel verisi çelişiyor! Şifreye göre W2={dec_w2}, Excel'de W2={s_w2}."})

                    # YENİ EKLENEN KONTROLLER
                    # Toplam Bulut (N)
                    s_n = self.sin.get('N')
                    dec_n = s_data.get('toplam_bulut')
                    if dec_n is not None:
                        sin_cloud_ok = True
                        if pd.notna(s_n) and float(s_n) != float(dec_n):
                            self.errors.append({"kod": "h307", "mesaj": f"Şifreli SİNOPTİK mesajı ile Excel verisi çelişiyor! Şifreye göre N={dec_n}, Excel'de N={s_n}."})

                    # Bulut Cinsleri (CL, CM, CH) ve Nh
                    s_nh = self.sin.get('Nh', self.sin.get('nh_sin', self.sin.get('N')))
                    s_cl = self.sin.get('cl_sin', self.sin.get('Bg1'))
                    s_cm = self.sin.get('cm_sin', self.sin.get('Bg2'))
                    s_ch = self.sin.get('ch_sin', self.sin.get('Bg3'))
                    
                    # Kullanıcı 'Nh' veya 'Bulut' sütununa "85520" gibi tam 8-grubunu girmiş olabilir.
                    # Eğer s_nh 5 haneli ve 8 ile başlıyorsa, değerleri oradan ayıkla:
                    def extract_8_group(val):
                        if pd.isna(val): return None
                        v_str = str(val).strip()
                        if v_str.endswith('.0'): v_str = v_str[:-2]
                        if len(v_str) == 5 and v_str.startswith('8') and v_str.isdigit():
                            return v_str
                        return None

                    group_8 = None
                    for val in [s_nh, s_cl, s_cm, s_ch]:
                        group_8 = extract_8_group(val)
                        if group_8: break
                        
                    if not group_8:
                        rasat_str = str(self.sin.get('RASATLAR', ''))
                        main_section = rasat_str.split('333')[0]
                        match = re.search(r'\b8([0-9/]{4})\b', main_section)
                        if match:
                            group_8 = match.group(0)

                    if group_8:
                        s_nh = group_8[1] if group_8[1] != '/' else None
                        s_cl = group_8[2] if group_8[2] != '/' else None
                        s_cm = group_8[3] if group_8[3] != '/' else None
                        s_ch = group_8[4] if group_8[4] != '/' else None

                    dec_nh = s_data.get('alcak_bulut_miktari')
                    dec_cl = s_data.get('cl_bulut_tipi')
                    dec_cm = s_data.get('cm_bulut_tipi')
                    dec_ch = s_data.get('ch_bulut_tipi')

                    def is_valid_single_digit(val):
                        if pd.isna(val) or val is None: return False
                        v_str = str(val).strip()
                        if v_str.endswith('.0'): v_str = v_str[:-2]
                        return len(v_str) == 1 and v_str.isdigit()

                    if dec_nh is not None and is_valid_single_digit(s_nh) and float(s_nh) != float(dec_nh):
                        self.errors.append({"kod": "h307", "mesaj": f"Şifreli SİNOPTİK mesajı ile Excel verisi çelişiyor! Şifreye göre Nh={dec_nh}, Excel'de Nh={s_nh}."})
                    if dec_cl is not None and is_valid_single_digit(s_cl) and float(s_cl) != float(dec_cl):
                        self.errors.append({"kod": "h307", "mesaj": f"Şifreli SİNOPTİK mesajı ile Excel verisi çelişiyor! Şifreye göre CL={dec_cl}, Excel'de CL={s_cl}."})
                    if dec_cm is not None and is_valid_single_digit(s_cm) and float(s_cm) != float(dec_cm):
                        self.errors.append({"kod": "h307", "mesaj": f"Şifreli SİNOPTİK mesajı ile Excel verisi çelişiyor! Şifreye göre CM={dec_cm}, Excel'de CM={s_cm}."})
                    if dec_ch is not None and is_valid_single_digit(s_ch) and float(s_ch) != float(dec_ch):
                        self.errors.append({"kod": "h307", "mesaj": f"Şifreli SİNOPTİK mesajı ile Excel verisi çelişiyor! Şifreye göre CH={dec_ch}, Excel'de CH={s_ch}."})

                    # Yağış (RRR)
                    s_rrr = self.sin.get('rrr_sin')
                    dec_rrr = s_data.get('yagis_miktari_kod')
                    if dec_rrr is not None:
                        if pd.notna(s_rrr) and float(s_rrr) != float(dec_rrr):
                             self.errors.append({"kod": "h307", "mesaj": f"Şifreli SİNOPTİK mesajı ile Excel verisi çelişiyor! Şifreye göre RRR={dec_rrr}, Excel'de RRR={s_rrr}."})


        # METAR SAĞLAMASI
        if MetarDecoder is not None and pd.notna(bulten_met) and len(str(bulten_met).strip()) > 10:
            m_decoder = MetarDecoder()
            m_data = m_decoder.decode_line(str(bulten_met))
            if m_data:
                # Sıcaklık ve İşba Sağlaması
                if 'sicaklik_isba' in m_data:
                    parts = m_data['sicaklik_isba'].split('/')
                    m_t = self.met.get('Kuru')
                    m_td = self.met.get('İşba')
                    
                    dec_t_str = parts[0].replace('M', '-')
                    try:
                        dec_t = float(dec_t_str)
                        met_temp_ok = True
                        if pd.notna(m_t) and abs(float(m_t) - dec_t) >= 1.0:
                            self.errors.append({"kod": "h308", "mesaj": f"Şifreli METAR mesajı ile Excel verisi çelişiyor! Şifreye göre T={dec_t}°C, Excel'de Kuru={m_t}°C."})
                    except: pass
                    
                    if len(parts) > 1 and parts[1]:
                        dec_td_str = parts[1].replace('M', '-')
                        try:
                            dec_td = float(dec_td_str)
                            met_dew_ok = True
                            if pd.notna(m_td) and abs(float(m_td) - dec_td) >= 1.0:
                                self.errors.append({"kod": "h308", "mesaj": f"Şifreli METAR mesajı ile Excel verisi çelişiyor! Şifreye göre İşba={dec_td}°C, Excel'de İşba={m_td}°C."})
                        except: pass
                
                m_qnh = self.met.get('QNH')
                if 'basinc' in m_data and m_data['basinc'].startswith('Q'):
                    met_press_ok = True
                    try:
                        dec_qnh = float(m_data['basinc'][1:])
                        if pd.notna(m_qnh):
                            excel_val = float(m_qnh)
                            # Excel'deki QNH (Örn: 1021.0) ile şifredeki QNH (1020) arasındaki fark 1.5 hPa'dan küçükse tolere et.
                            if abs(excel_val - dec_qnh) >= 1.5:
                                self.errors.append({"kod": "h308", "mesaj": f"Şifreli METAR mesajı ile Excel verisi çelişiyor! Şifreye göre QNH={int(dec_qnh)} hPa, Excel'de QNH={m_qnh} hPa."})
                    except: pass
                    
                # Rüzgar Sağlaması (Crosscheck)
                m_ff = self.met.get('Hız')
                m_dd = self.met.get('Yön')
                dec_ruzgar = m_data.get('ruzgar')
                if dec_ruzgar is not None:
                    met_wind_ok = True
                elif pd.notna(m_ff) or pd.notna(m_dd):
                    self.errors.append({"kod": "h308", "mesaj": "Excel'de Rüzgar (Yön/Hız) girilmiş ancak şifreli METAR mesajında rüzgar grubu hatalı veya eksik."})

                # Bulut ve Görüş
                if 'cavok' in m_data:
                    met_cloud_ok = True
                    met_vis_ok = True
                else:
                    if 'bulutlar' in m_data: met_cloud_ok = True
                    if 'gorus' in m_data: met_vis_ok = True

        # DEKODERDE HATA YOKSA EXCEL'DEKİ ÇAPRAZ DENETİM (EXCEL VS EXCEL) HATALARINI GÖRMEZDEN GEL
        if sin_wind_ok and met_wind_ok:
            wind_codes = ["h273", "h274", "h275"]
            self.errors = [e for e in self.errors if e['kod'] not in wind_codes]
            
        if sin_temp_ok and met_temp_ok:
            temp_codes = ["h270", "h304"]
            self.errors = [e for e in self.errors if e['kod'] not in temp_codes]
            
        if sin_dew_ok and met_dew_ok:
            dew_codes = ["h271"]
            self.errors = [e for e in self.errors if e['kod'] not in dew_codes]
            
        if (sin_temp_ok and met_temp_ok) and (sin_dew_ok and met_dew_ok):
            self.errors = [e for e in self.errors if e['kod'] != "h272"]
            
        if sin_press_ok and met_press_ok:
            press_codes = ["h306"]
            self.errors = [e for e in self.errors if e['kod'] not in press_codes]
            
        if sin_cloud_ok and met_cloud_ok:
            cloud_codes = ["h278", "h280", "h284", "h285"]
            self.errors = [e for e in self.errors if e['kod'] not in cloud_codes]
            
        if sin_vis_ok and met_vis_ok:
            vis_codes = ["h283", "h282", "h281"]
            self.errors = [e for e in self.errors if e['kod'] not in vis_codes]
            
        if sin_ww_ok:
            ww_codes = [
                "h281", "h282", "h286", "h287", "h288", "h289", "h290", 
                "h291", "h292", "h293", "h294", "h295", "h296", "h297", 
                "h298", "h299", "h300", "h302", "h301"
            ]
            self.errors = [e for e in self.errors if e['kod'] not in ww_codes]

    def run_all_checks(self):
        # Saat eşleştirme kontrolü:
        # METAR ve SİNOPTİK saatleri arasında belirgin bir fark varsa (örn: > 15 dakika),
        # iki rasat birbiriyle uyumlu değildir ve çapraz kıyaslama yapılmamalıdır.
        saatler_uyumlu = True
        if self.metar_gmt is not None and self.sinoptik_gmt is not None:
            saatler_uyumlu, _, _ = self.eslestirici.saatler_esilestirilebilir_mi(
                self.metar_gmt, self.sinoptik_gmt, otomat_veri_mi=True
            )

        if saatler_uyumlu:
            self.check_temperature()
            self.check_dewpoint()
            self.check_humidity()
            self.check_pressure()
            self.check_pressure_reduction()
            self.check_wind_speed()
            self.check_wind_unit()
            self.check_wind_dir()
            self.check_calm_wind()
            self.check_wind_gust()
            self.check_clouds()
            self.check_clouds_detail()
            self.check_cloud_base_crosscheck()
            self.check_visibility_and_fog()
            self.check_thunderstorm_and_hail()
            self.check_hail_size()
            self.check_specific_weather_phenomena()
            self.check_windshear()
            self.check_sky_obscured_logic()
            self.check_temp_dewpoint_spread()
            self.check_freezing_temp_logic()
            self.check_snow_temp_logic()
            self.check_station_elevation_logic()

        # Şifreli Raw Mesaj ile Hücre/Sütun Sağlaması (Crosscheck)
        self.check_decoder_consistency()

        # --- GÜVENLİK FİLTRESİ: İptal Edilen Kuralları Temizle ---
        self.errors = [e for e in self.errors if e.get('kod') != "VAL_MANTIK_SPREAD"]

        return self.errors

if __name__ == "__main__":
    # Örnek Pandas DataFrame simülasyonu
    sinoptik_data = pd.DataFrame([
        {'GMT': 12, 'T': 20.5, 'Td': 15.0, 'Rh': 70, 'ff': 10, 'dd': 27, '4P': 1005.1, '3Po': 1012.0, 'N': 4}
    ])
    
    metar_data = pd.DataFrame([
        {'GMT': 12, 'Kuru': 20.6, 'İşba': 14.8, '%': 69, 'Hız': 20, 'Yön': 270, 'QFE': 1005.2, 'QNH': 1012.1, 'T. Kp.': 4}
    ])

    # DataFrame'leri Satır Bazlı Birleştirip (GMT üzerinden) Doğrulamaya Gönderme
    merged_data = pd.merge(sinoptik_data, metar_data, on='GMT', suffixes=('_sin', '_met'))

    print("==== ÇAPRAZ KONTROL SONUÇLARI ====")
    for index, row in merged_data.iterrows():
        # Dictionary olarak çıkarıyoruz
        sin_dict = {
            'T': row.get('T'), 'Td': row.get('Td'), 'Rh': row.get('Rh'),
            'ff': row.get('ff'), 'dd': row.get('dd'), 
            '4P': row.get('4P'), '3Po': row.get('3Po'), 'N': row.get('N'),
            'RASATLAR': row.get('RASATLAR', '')
        }
        met_dict = {
            'Kuru': row.get('Kuru'), 'İşba': row.get('İşba'), '%': row.get('%'),
            'Hız': row.get('Hız'), 'Yön': row.get('Yön'), 
            'QFE': row.get('QFE'), 'QNH': row.get('QNH'), 'T. Kp.': row.get('T. Kp.')
        }

        validator = WeatherLogValidator(
            sin_dict, 
            met_dict,
            metar_gmt=row.get('GMT'),  # METAR GMT saati
            sinoptik_gmt=row.get('GMT')  # SİNOPTİK GMT saati
        )
        hatalar = validator.run_all_checks()
        
        print(f"Saat: {row['GMT']}Z")
        if hatalar:
            for hata in hatalar: print(f" - [{hata['kod']}] {hata['mesaj']}")
        else:
            print(" - Hata Bulunmadı. Eşleşme Başarılı.")