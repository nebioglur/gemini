import re
import pandas as pd
try:
    import decoder_lookups
except ImportError:
    decoder_lookups = None

class SynopDecoder:
    """
    WMO FM-12 SYNOP kodlarını çözen geliştirilmiş decoder.
    """
    
    def __init__(self):
        self.errors = [] # Çözümleme sırasındaki hataları biriktireceğimiz liste
    
    @staticmethod
    def decode_group_1(group):
        if '/' in group: return {}
        try:
            sign = -1 if group[1] == '1' else 1
            return {"sicaklik": sign * (int(group[2:]) / 10.0)}
        except: return {}

    @staticmethod
    def decode_group_2(group):
        if '/' in group: return {}
        try:
            if group[1] == '9': return {"bagil_nem": int(group[2:])}
            sign = -1 if group[1] == '1' else 1
            return {"isba": sign * (int(group[2:]) / 10.0)}
        except: return {}

    @staticmethod
    def decode_group_3(group):
        if '/' in group: return {}
        try:
            val = int(group[1:])
            return {"istasyon_basinci": (10000 + val)/10.0 if val < 1000 else val/10.0}
        except: return {}

    @staticmethod
    def decode_group_4(group):
        if '/' in group: return {}
        try:
            val_str = group[1:5]
            val = int(val_str)
            if val_str.startswith('8') and 8000 <= val < 9000:
                return {"jeopotansiyel_850": int("1" + val_str[1:])}
            elif val_str.startswith('7') and 7000 <= val < 8000:
                return {"jeopotansiyel_700": int("3" + val_str[1:])}
            else:
                return {"deniz_basinci": (10000 + val)/10.0 if val < 1000 else val/10.0}
        except: return {}

    @staticmethod
    def decode_group_5(group):
        if '/' in group: return {}
        try:
            return {"basinc_karakteri": int(group[1]), "basinc_degisimi": int(group[2:]) / 10.0}
        except: return {}

    @staticmethod
    def decode_group_6(group):
        if '/' in group: return {}
        try:
            return {"yagis_miktari_kod": int(group[1:4]), "yagis_suresi_kod": int(group[4])}
        except: return {}

    @staticmethod
    def decode_group_7(group):
        res = {}
        try:
            if group[1:3] != '//' and group[1:3].isdigit(): res["halihazir_hava"] = int(group[1:3])
            if group[3] != '/' and group[3].isdigit(): res["gecmis_hava1"] = int(group[3])
            if group[4] != '/' and group[4].isdigit(): res["gecmis_hava2"] = int(group[4])
        except: pass
        return res

    @staticmethod
    def decode_group_8(group):
        res = {}
        try:
            if group[1] != '/' and group[1].isdigit(): res["alcak_bulut_miktari"] = int(group[1])
            if group[2] != '/' and group[2].isdigit(): res["cl_bulut_tipi"] = int(group[2])
            if group[3] != '/' and group[3].isdigit(): res["cm_bulut_tipi"] = int(group[3])
            if group[4] != '/' and group[4].isdigit(): res["ch_bulut_tipi"] = int(group[4])
        except: pass
        return res

    @staticmethod
    def decode_group_0_section5(group):
        res = {}
        if '/' not in group:
            sign = -1 if group[1] == '1' else 1
            res["deniz_suyu_sicakligi"] = sign * (int(group[2:]) / 10.0)
        return res

    @staticmethod
    def get_ww_description(ww_code):
        ww_dict = {
            '00': 'Bulut gelişimi gözlenmedi',
            '01': 'Bulutlar dağılıyor',
            '02': 'Gökyüzü durumunda değişiklik yok',
            '03': 'Bulutlar artıyor',
            '04': 'Duman nedeniyle görüş düşük',
            '05': 'Kuru pus (Toz pusu)',
            '06': 'Havada asılı yaygın toz',
            '07': 'Rüzgarla kalkan toz/kum',
            '08': 'Toz/Kum şeytanı (Hortum)',
            '09': 'Toz/Kum fırtınası (Görüş mesafesinde)',
            '10': 'Pus (Görüş 1-5 km)',
            '11': 'Sığ sis (Yamalar halinde)',
            '12': 'Sığ sis (Sürekli az)',
            '13': 'Şimşek (Yağış yok)',
            '14': 'Ulaşmayan yağış (Virga)',
            '15': 'Uzakta yağış',
            '16': 'Yakında yağış',
            '17': 'Oraj (Gökgürültüsü), yağış yok',
            '18': 'Squall (Bora / Ani Fırtına)',
            '19': 'Huni bulutu (Tornado / Hortum)',
            '20': 'Sona eren çisenti',
            '21': 'Sona eren yağmur',
            '22': 'Sona eren kar',
            '23': 'Sona eren karla karışık yağmur',
            '24': 'Sona eren donduran yağış (Yağmur/Çisenti)',
            '25': 'Sona eren sağanak yağmur',
            '26': 'Sona eren kar sağanağı',
            '27': 'Sona eren dolu sağanağı',
            '28': 'Sona eren sis',
            '29': 'Sona eren oraj',
            '30': 'Hafif/Orta toz fırtınası (Azalan)',
            '31': 'Hafif/Orta toz fırtınası (Değişmeyen)',
            '32': 'Hafif/Orta toz fırtınası (Artan)',
            '33': 'Şiddetli toz fırtınası (Azalan)',
            '34': 'Şiddetli toz fırtınası (Değişmeyen)',
            '35': 'Şiddetli toz fırtınası (Artan)',
            '36': 'Hafif/Orta savrulan kar (Alçak)',
            '37': 'Şiddetli savrulan kar (Alçak)',
            '38': 'Hafif/Orta savrulan kar (Yüksek)',
            '39': 'Şiddetli savrulan kar (Yüksek)',
            '40': 'Uzakta sis',
            '41': 'Parçalı sis',
            '42': 'Sis (İncelen, gökyüzü görünür)',
            '43': 'Sis (İncelen, gökyüzü görünmez)',
            '44': 'Sis (Değişmeyen, gökyüzü görünür)',
            '45': 'Sis (Değişmeyen, gökyüzü görünmez)',
            '46': 'Sis (Kalınlaşan, gökyüzü görünür)',
            '47': 'Sis (Kalınlaşan, gökyüzü görünmez)',
            '48': 'Donduran sis (Gökyüzü görünür)',
            '49': 'Donduran sis (Gökyüzü görünmez)',
            '50': 'Hafif çisenti (Aralıklı)',
            '51': 'Hafif çisenti (Sürekli)',
            '52': 'Orta şiddette çisenti (Aralıklı)',
            '53': 'Orta şiddette çisenti (Sürekli)',
            '54': 'Kuvvetli çisenti (Aralıklı)',
            '55': 'Kuvvetli çisenti (Sürekli)',
            '56': 'Hafif donduran çisenti',
            '57': 'Kuvvetli donduran çisenti',
            '58': 'Hafif yağmur ve çisenti',
            '59': 'Orta/Kuvvetli yağmur ve çisenti',
            '60': 'Hafif yağmur (Aralıklı)',
            '61': 'Hafif yağmur (Sürekli)',
            '62': 'Orta şiddette yağmur (Aralıklı)',
            '63': 'Orta şiddette yağmur (Sürekli)',
            '64': 'Kuvvetli yağmur (Aralıklı)',
            '65': 'Kuvvetli yağmur (Sürekli)',
            '66': 'Hafif donduran yağmur',
            '67': 'Orta/Kuvvetli donduran yağmur',
            '68': 'Hafif karla karışık yağmur',
            '69': 'Orta/Kuvvetli karla karışık yağmur',
            '70': 'Hafif kar (Aralıklı)',
            '71': 'Hafif kar (Sürekli)',
            '72': 'Orta şiddette kar (Aralıklı)',
            '73': 'Orta şiddette kar (Sürekli)',
            '74': 'Kuvvetli kar (Aralıklı)',
            '75': 'Kuvvetli kar (Sürekli)',
            '76': 'Buz prizmaları (Buz iğneleri)',
            '77': 'Kar taneleri (Kardan grene)',
            '78': 'Yıldız şeklinde kar kristalleri',
            '79': 'Buz taneleri (Ice pellets)',
            '80': 'Hafif sağanak yağmur',
            '81': 'Orta/Kuvvetli sağanak yağmur',
            '82': 'Çok kuvvetli sağanak yağmur',
            '83': 'Hafif sağanak karla karışık yağmur',
            '84': 'Orta/Kuvvetli sağanak karla karışık yağmur',
            '85': 'Hafif sağanak kar',
            '86': 'Orta/Kuvvetli sağanak kar',
            '87': 'Hafif sağanak küçük dolu / Kar paleti',
            '88': 'Orta/Kuvvetli sağanak küçük dolu / Kar paleti',
            '89': 'Hafif sağanak dolu',
            '90': 'Orta/Kuvvetli sağanak dolu',
            '91': 'Önceki saatte oraj, şu an hafif yağmur',
            '92': 'Önceki saatte oraj, şu an kuvvetli yağmur',
            '93': 'Önceki saatte oraj, şu an hafif kar/dolu',
            '94': 'Önceki saatte oraj, şu an kuvvetli kar/dolu',
            '95': 'Hafif/Orta oraj (Yağmur veya Kar ile)',
            '96': 'Hafif/Orta oraj (Dolu ile)',
            '97': 'Şiddetli oraj (Yağmur veya Kar ile)',
            '98': 'Şiddetli oraj (Toz/Kum fırtınası ile)',
            '99': 'Şiddetli oraj (Dolu ile)'
        }
        return ww_dict.get(str(ww_code).zfill(2), f"Bilinmeyen Kod ({ww_code})")

    @staticmethod
    def get_w1w2_description(w_code):
        w_dict = {
            '0': 'Bulutluluk yarıdan az (Az Bulutlu)',
            '1': 'Bulutluluk yarıdan fazla (Parçalı Bulutlu)',
            '2': 'Bulutlu (Çok Bulutlu / Kapalı)',
            '3': 'Kum veya Toz fırtınası',
            '4': 'Sis veya Buz sisi',
            '5': 'Çisenti',
            '6': 'Yağmur',
            '7': 'Kar veya Karla karışık yağmur',
            '8': 'Sağanak yağış (Yağmur veya Kar sağanağı)',
            '9': 'Oraj (Gökgürültülü fırtına)',
            '/': 'Ölçülmedi / Bilinmiyor'
        }
        return w_dict.get(str(w_code), f"Bilinmeyen Kod ({w_code})")

    @staticmethod
    def get_cl_description(code):
        cl_dict = {
            '0': 'Alçak bulut yok',
            '1': 'Cumulus humilis veya fractus (Az gelişmiş Cu)',
            '2': 'Cumulus mediocris veya congestus (Orta/İyi gelişmiş Cu)',
            '3': 'Cumulonimbus calvus (Örsü olmayan Cb)',
            '4': 'Stratocumulus cumulogenitus (Cu kökenli Sc)',
            '5': 'Stratocumulus (Cu kökenli olmayan Sc)',
            '6': 'Stratus nebulosus veya fractus (İyi hava)',
            '7': 'Stratus/Cumulus fractus (Kötü havalarda pançak)',
            '8': 'Cumulus ve Stratocumulus (Farklı seviyelerde)',
            '9': 'Cumulonimbus capillatus (Örslü Cb)',
            '/': 'Ölçülmedi / Görünmüyor'
        }
        return cl_dict.get(str(code), f"Bilinmeyen Kod ({code})")

    @staticmethod
    def get_cm_description(code):
        cm_dict = {
            '0': 'Orta bulut yok',
            '1': 'Altostratus translucidus (Yarı saydam As)',
            '2': 'Altostratus opacus veya Nimbostratus (Opak As/Ns)',
            '3': 'Altocumulus translucidus (Tek katmanlı Ac)',
            '4': 'Altocumulus lenticularis (Merceksi Ac)',
            '5': 'Altocumulus translucidus (Şeritler halinde, kalınlaşan Ac)',
            '6': 'Altocumulus cumulogenitus (Cu/Cb kökenli Ac)',
            '7': 'Altocumulus opacus (Çok katmanlı, opak Ac)',
            '8': 'Altocumulus castellanus veya floccus (Kuleli/Yumak Ac)',
            '9': 'Altocumulus (Kaotik gökyüzü)',
            '/': 'Ölçülmedi / Görünmüyor'
        }
        return cm_dict.get(str(code), f"Bilinmeyen Kod ({code})")

    @staticmethod
    def get_ch_description(code):
        ch_dict = {
            '0': 'Yüksek bulut yok',
            '1': 'Cirrus fibratus veya uncinus (İpliksi/Çengelli Ci)',
            '2': 'Cirrus spissatus (Yoğun Ci)',
            '3': 'Cirrus spissatus (Cb kökenli Ci)',
            '4': 'Cirrus uncinus veya fibratus (Kalınlaşan Ci)',
            '5': 'Cirrostratus (Ufkun 45° altında Cs)',
            '6': 'Cirrostratus (Ufkun 45° üstünde Cs)',
            '7': 'Cirrostratus (Tüm gökyüzünü kaplayan Cs)',
            '8': 'Cirrostratus (Gök kubbeyi kısmen kaplayan Cs)',
            '9': 'Cirrocumulus (Cc)',
            '/': 'Ölçülmedi / Görünmüyor'
        }
        return ch_dict.get(str(code), f"Bilinmeyen Kod ({code})")

    @staticmethod
    def get_e_description(code):
        e_dict = {
            '0': 'Kuru yüzey (Çatlak veya belirgin toz/kum yok)',
            '1': 'Nemli yüzey (Su birikintisi yok)',
            '2': 'Islak yüzey (Su birikintileri var)',
            '3': 'Su basmış (Zemin sular altında)',
            '4': 'Donmuş toprak (Buz veya kar yok)',
            '5': 'Buzlanma veya kırağı (Kar örtüsü yok)',
            '6': 'Gevşek kuru toz veya kum (Zemini tamamen kaplamayan)',
            '7': 'İnce toz veya kum tabakası (Zemini kaplayan)',
            '8': 'Kalın toz veya kum tabakası (Zemini tamamen kaplayan)',
            '9': 'Aşırı kuru ve çatlak yüzey',
            '/': 'Ölçülmedi / Bilinmiyor'
        }
        return e_dict.get(str(code), f"Bilinmeyen Kod ({code})")

    @staticmethod
    def get_ep_description(code):
        ep_dict = {
            '0': 'Zemin büyük ölçüde buzla kaplı',
            '1': 'Islak veya eriyen kar (Zemini tamamen kaplamayan)',
            '2': 'Kuru kar (Zemini tamamen kaplamayan)',
            '3': 'Düzensiz veya yamalı ıslak kar örtüsü',
            '4': 'Eşit (Düzgün) ıslak veya eriyen kar örtüsü',
            '5': 'Düzensiz veya yamalı kuru kar örtüsü',
            '6': 'Eşit (Düzgün) kuru kar örtüsü',
            '7': 'Derin ve sürüklenmiş kar örtüsü (Düzensiz)',
            '8': 'Derin ve eşit kar örtüsü (Düzgün)',
            '9': 'Kuvvetli sürüklenen kar (Gökyüzü görünmeyebilir)',
            '/': 'Ölçülmedi / Bilinmiyor'
        }
        return ep_dict.get(str(code), f"Bilinmeyen Kod ({code})")

    @staticmethod
    def get_a_description(code):
        a_dict = {
            '0': 'Artıp sonra azalan (Basınç 3 saat öncekine göre daha yüksek veya aynı)',
            '1': 'Artıp sonra değişmeyen veya artışı yavaşlayan (Basınç 3 saat öncekine göre daha yüksek)',
            '2': 'Sürekli artan (Basınç 3 saat öncekine göre daha yüksek)',
            '3': 'Azalıp veya değişmeyip sonra artan (Basınç 3 saat öncekine göre daha yüksek)',
            '4': 'Değişmeyen (Basınç 3 saat önceki ile aynı)',
            '5': 'Azalıp sonra artan (Basınç 3 saat öncekine göre daha düşük veya aynı)',
            '6': 'Azalıp sonra değişmeyen veya düşüşü yavaşlayan (Basınç 3 saat öncekine göre daha düşük)',
            '7': 'Sürekli azalan (Basınç 3 saat öncekine göre daha düşük)',
            '8': 'Artıp veya değişmeyip sonra azalan (Basınç 3 saat öncekine göre daha düşük)',
            '/': 'Ölçülmedi / Bilinmiyor'
        }
        return a_dict.get(str(code), f"Bilinmeyen Kod ({code})")

    def decode_line(self, line):
        """Hatalara karşı korumalı sarmalayıcı (wrapper) fonksiyon."""
        self.errors = []
        try:
            return self._decode_line_internal(line)
        except Exception as e:
            import traceback
            self.errors.append(f"SİNOPTİK Şifresi çözümlenirken beklenmeyen (kritik) hata oluştu: {str(e)}")
            print(f"SynopDecoder Çöktü: {e}\n{traceback.format_exc()}")
            return {"ham_veri": str(line).strip() if line else "", "raw_groups": {}}

    def _decode_line_internal(self, line):
        """Tek bir SYNOP satırını parçalarına ayırır."""
        parts = str(line).replace('=', '').split()
        if not parts:
            self.errors.append("Rapor boş veya tanımsız.")
            return None

        data = {"ham_veri": line.strip(), "raw_groups": {}}
        
        # AAXX veya BBXX bul (Olası diğer SITT60 vb. başlıkları atlamak için)
        start_idx = -1
        for i, p in enumerate(parts):
            if p in ["AAXX", "BBXX"]:
                start_idx = i
                break
                
        if start_idx != -1:
            data["istasyon_tipi"] = "Kara İstasyonu (AAXX)" if parts[start_idx] == "AAXX" else "Deniz İstasyonu (BBXX)"
            idx = start_idx + 1
        else:
            idx = 0
            # AAXX yoksa bile SITT60 LTAN 300300 gibi olası başlıkları atla
            while idx < len(parts) and (not parts[idx].isdigit() or len(parts[idx]) == 6):
                idx += 1
        
        if idx < len(parts) and len(parts[idx]) == 5 and parts[idx].isdigit():
            # Türkiye WMO kodları 17XXX ile başlar. Tarih grubu (YYGGi) atlanmışsa istasyonu yakala
            is_station = False
            if parts[idx].startswith("17"):
                try:
                    hr = int(parts[idx][2:4])
                    if hr > 23:
                        is_station = True
                    elif idx + 1 < len(parts) and not parts[idx+1].startswith("17"):
                        is_station = True
                except:
                    pass
            if is_station:
                pass
            else:
                data["gun"] = parts[idx][:2]
                data["saat_gmt"] = parts[idx][2:4]
                data["ruzgar_indikatari_iw"] = parts[idx][4]
                idx += 1
            
        if idx < len(parts) and len(parts[idx]) == 5:
            data["istasyon_no"] = parts[idx]
            idx += 1
        else:
            self.errors.append("İstasyon indikatörü (IIiii) bulunamadı veya 5 haneli değil.")

        mode = "section1" # section1, 333, 555
        
        # Grup ayrıştırıcılarını bir sözlükte toplayarak kodu daha temiz hale getiriyoruz
        section1_decoders = {
            '1': (self.decode_group_1, 'sicaklik'),
            '2': (self.decode_group_2, 'isba'), # 'bagil_nem' de olabilir
            '3': (self.decode_group_3, 'istasyon_basinci'),
            '4': (self.decode_group_4, 'deniz_basinci'), # veya jeopotansiyel
            '5': (self.decode_group_5, 'basinc_degisimi'),
            '6': (self.decode_group_6, 'yagis_miktari'),
            '7': (self.decode_group_7, 'hadise'),
            '8': (self.decode_group_8, 'bulut_tipi'),
        }
        # Not: 'bagil_nem' gibi alternatif anahtarlar decode_group_2 içinde yönetiliyor.
        # Bu yüzden burada sadece birincil anahtar 'isba' belirtildi.

        for i in range(idx, len(parts)):
            grp = parts[i]
            if len(grp) != 5:
                if grp == "333": mode = "333"
                if grp == "555": mode = "555"
                continue

            indicator = grp[0]
            
            if mode == "section1":
                if i == idx: 
                    try:
                        if grp[0] != '/' and grp[0].isdigit(): data["ir"] = int(grp[0])
                        if grp[1] != '/' and grp[1].isdigit(): data["ix"] = int(grp[1])
                        if grp[2] != '/' and grp[2].isdigit(): data["bulut_yukseklik_kod"] = int(grp[2])
                        if grp[3:] != '//' and grp[3:].isdigit(): data["gorus_kod"] = int(grp[3:])
                    except: pass
                elif i == idx + 1:
                    try:
                        if grp[0] != '/' and grp[0].isdigit(): data["toplam_bulut"] = int(grp[0])
                        if grp[1:3] != '//' and grp[1:3].isdigit(): 
                            dd = int(grp[1:3])
                            data["ruzgar_yon"] = -1 if dd == 99 else dd * 10
                        if grp[3:] != '//' and grp[3:].isdigit(): 
                            data["ruzgar_hiz"] = int(grp[3:])
                    except: pass
                elif indicator == '0':
                    # High wind speed group 00fff
                    if grp.startswith("00") and data.get("ruzgar_hiz") == 99:
                        try: data["ruzgar_hiz"] = int(grp[2:])
                        except: pass
                
                # Yeniden düzenlenmiş (refactored) grup ayrıştırma
                elif indicator in section1_decoders:
                    decoder_func, raw_group_key = section1_decoders[indicator]
                    decoded = decoder_func(grp)
                    if decoded:
                        data.update(decoded)
                        # 'isba' ve 'bagil_nem' aynı gruptan (2) geldiği için özel kontrol
                        if 'bagil_nem' in decoded: data['raw_groups']['bagil_nem'] = grp
                        else: data['raw_groups'][raw_group_key] = grp

            elif mode == "333":
                try:
                    if indicator == '1' and '/' not in grp:
                        data["max_sicaklik"] = (-1 if grp[1] == '1' else 1) * (int(grp[2:]) / 10.0)
                        data['raw_groups']['max_sicaklik'] = grp
                    elif indicator == '2' and '/' not in grp:
                        data["min_sicaklik"] = (-1 if grp[1] == '1' else 1) * (int(grp[2:]) / 10.0)
                        data['raw_groups']['min_sicaklik'] = grp
                    elif indicator == '3':
                        if grp[1] != '/': data["yerin_hali_E"] = int(grp[1])
                        if grp[2] != '/':
                            data["yer_sicakligi"] = (-1 if grp[2] == '1' else 1) * (int(grp[3:]) / 10.0) if grp[3:] != '//' else None
                        data['raw_groups']['yer_sicakligi'] = grp
                    elif indicator == '4' and grp[1] != '/':
                        data["yerin_hali_E_prime"] = int(grp[1])
                        if grp[2:] != '///': data["kar_kalinligi_4"] = int(grp[2:])
                        data['raw_groups']['kar_kalinligi_4'] = grp
                    elif indicator == '5':
                        if grp.startswith("55") and grp[2:].isdigit() and not '/' in grp[2:]:
                            data["guneslenme_suresi"] = int(grp[2:]) / 10.0
                            data['raw_groups']['guneslenme_suresi'] = grp
                        elif grp[1:4].isdigit() and grp[4].isdigit() and not '/' in grp: # 5EEEiE
                            data["buharlasma_miktari"] = int(grp[1:4]) / 10.0
                            data["buharlasma_aleti"] = int(grp[4])
                            data['raw_groups']['buharlasma_miktari'] = grp
                        elif grp[1] != '/' and grp[1].isdigit(): # Fallback for 5Exxx
                            data["yerin_hali"] = int(grp[1])
                            data['raw_groups']['yerin_hali'] = grp
                    elif indicator == '6' and '/' not in grp:
                        data["yagis_miktari_kod_333"] = int(grp[1:4])
                        if len(grp) == 5 and grp[4].isdigit():
                            data["yagis_suresi_kod_333"] = int(grp[4])
                        data['raw_groups']['yagis_miktari_kod_333'] = grp
                    elif indicator == '7' and '/' not in grp:
                        if grp[1:].isdigit():
                            val = int(grp[1:])
                            if val == 9999:
                                data["yagis_miktari_24h"] = "Eser (İz)"
                            elif val == 9998:
                                data["yagis_miktari_24h"] = "Ölçülmedi"
                            else:
                                data["yagis_miktari_24h"] = f"{val / 10.0} mm"
                            data['raw_groups']['yagis_miktari_24h'] = grp
                    elif indicator == '8':
                        if "k3_bulutlar" not in data:
                            data["k3_bulutlar"] = []
                        data["k3_bulutlar"].append({
                            "ns": grp[1],
                            "c":  grp[2],
                            "hs": grp[3:],
                            "raw": grp
                        })
                    elif indicator == '9' and grp.startswith("910") and grp[3:].isdigit():
                        data["hamle_hizi"] = int(grp[3:])
                        data['raw_groups']['hamle_hizi'] = grp
                    elif indicator == '9' and grp.startswith("911") and grp[3:].isdigit():
                        data["max_ruzgar_hizi"] = int(grp[3:])
                        data['raw_groups']['max_ruzgar_hizi'] = grp
                    elif indicator == '9' and grp.startswith("924") and grp[3] != '/' and grp[4] != '/':
                        try:
                            data["deniz_durumu_S"] = int(grp[3])
                            data["denize_gorus_Vs"] = int(grp[4])
                            data['raw_groups']['deniz_durumu'] = grp
                        except: pass
                    elif indicator == '9' and grp.startswith("931") and grp[3:].isdigit():
                        data["kar_kalinligi_toplam"] = int(grp[3:])
                        data['raw_groups']['kar_kalinligi_toplam'] = grp
                    elif indicator == '9' and grp.startswith("932") and grp[3:].isdigit():
                        data["kar_kalinligi_taze"] = int(grp[3:])
                        data['raw_groups']['kar_kalinligi_taze'] = grp
                    elif indicator == '9' and grp.startswith("933") and grp[3:].isdigit():
                        data["karin_su_esdegeri"] = int(grp[3:])
                        data['raw_groups']['karin_su_esdegeri'] = grp
                    elif indicator == '9' and grp.startswith("909") and grp[3:].isdigit():
                        data["yagis_zamani_kod"] = grp[3:]
                        data['raw_groups']['yagis_zamani'] = grp
                    elif indicator == '9' and grp.startswith("94") and grp[3:5].isdigit():
                        data["derinlik_toprak_sicakligi_kod"] = grp[3:5]
                        data['raw_groups']['derinlik_toprak_sicakligi'] = grp
                    elif indicator == '9' and (grp.startswith("960") or grp.startswith("961")) and grp[3:5].isdigit():
                        if grp.startswith("960"):
                            data["halihazir_hava_2"] = int(grp[3:5])
                            data['raw_groups']['halihazir_hava_2'] = grp
                        else:
                            data["halihazir_hava_3"] = int(grp[3:5])
                            data['raw_groups']['halihazir_hava_3'] = grp
                except: pass
            
            elif mode == "555":
                try:
                    if indicator == '0':
                        decoded = self.decode_group_0_section5(grp)
                        if decoded:
                            data.update(decoded)
                            data['raw_groups']['deniz_suyu_sicakligi'] = grp
                    elif indicator == '1':
                        if '/' not in grp:
                            val = int(grp[1:])
                            # 1PPPP - Deniz seviyesine indirgenmiş basınç (QNH)
                            data["deniz_seviyesi_basinci_qnh"] = (10000 + val)/10.0 if val < 5000 else val/10.0
                            data['raw_groups']['deniz_seviyesi_basinci_qnh'] = grp
                    elif indicator == '2':
                        if '/' not in grp:
                            # 2RRRR - Günlük toplam yağış
                            data["gunluk_yagis"] = int(grp[1:5]) / 10.0
                            data['raw_groups']['gunluk_yagis'] = grp
                    elif indicator == '3':
                        if '/' not in grp:
                            # 3RRRR - Aylık toplam yağış
                            data["aylik_yagis"] = int(grp[1:5]) / 10.0
                            data['raw_groups']['aylik_yagis'] = grp
                    elif indicator == '4':
                        if '/' not in grp:
                            val = int(grp[1:])
                            # 4PPPP - İstasyon seviyesi basıncı (QFE)
                            data["istasyon_basinci_qfe"] = (10000 + val)/10.0 if val < 1000 else val/10.0
                            data['raw_groups']['istasyon_basinci_qfe'] = grp
                except: pass

        return data

    def generate_human_readable(self, data):
        """Hatalara karşı korumalı sarmalayıcı (wrapper) fonksiyon."""
        try:
            return self._generate_human_readable_internal(data)
        except Exception as e:
            import traceback
            print(f"SynopDecoder Rapor Oluşturma Hatası: {e}\n{traceback.format_exc()}")
            return f"Ham Veri: {data.get('ham_veri', '')}\n\n[SİSTEM HATASI] İnsan okuyabilir rapor oluşturulurken beklenmeyen bir hata meydana geldi:\n{e}"

    def _generate_human_readable_internal(self, data):
        """SYNOP verisini istenen yapılandırılmış ve detaylı formatta metne dönüştürür."""
        if not data or 'ham_veri' not in data:
            return "Çözümlenecek veri bulunamadı."
            
        raw_str = data['ham_veri'].strip()
        tokens = raw_str.replace('=', '').split()
        
        try:
            import decoder_lookups
        except ImportError:
            decoder_lookups = None
        
        res = [f"Ham Veri: {raw_str}\n"]
        
        mode = "HEADER"
        sec1_idx = 0
        cloud_layer_count = 1
        iw_unit = "Knot/ms"
        
        def get_vv_desc(vv):
            if vv == '//': return "Bilinmiyor."
            try:
                v = int(vv)
                if v == 0: return "< 0.1 km"
                if v <= 50: return f"{v / 10.0} km"
                if v <= 55: return "Belirtilmemiş"
                if v <= 80: return f"{v - 50} km"
                if v <= 88: return f"{30 + (v - 80) * 5} km"
                if v == 89: return "> 70 km"
                if v == 90: return "< 0.05 km"
                if v == 91: return "0.05 km"
                if v == 92: return "0.2 km"
                if v == 93: return "0.5 km"
                if v == 94: return "1 km"
                if v == 95: return "2 km"
                if v == 96: return "4 km"
                if v == 97: return "10 km"
                if v == 98: return "20 km"
                if v >= 99: return ">= 50 km"
            except: return "Bilinmiyor."
            return "Bilinmiyor."

        def get_h_desc(h):
            return {
                '0': "0 - 50 metre (0-150 ft) arası",
                '1': "50 - 100 metre (150-300 ft) arası",
                '2': "100 - 200 metre (300-600 ft) arası",
                '3': "200 - 300 metre (600-1000 ft) arası",
                '4': "300 - 600 metre (1000-2000 ft) arası",
                '5': "600 - 1000 metre (2000-3000 ft) arası",
                '6': "1000 - 1500 metre (3000-5000 ft) arası",
                '7': "1500 - 2000 metre (5000-6500 ft) arası",
                '8': "2000 - 2500 metre (6500-8000 ft) arası",
                '9': "> 2500 metre veya bulut yok",
                '/': "Bilinmiyor veya ölçülmedi"
            }.get(h, "Bilinmiyor")
            
        def get_hshs_desc(hs_str):
            if hs_str == '//': return "Bilinmiyor (//)"
            try:
                hs = int(hs_str)
                if hs == 0: return "< 100 ft"
                if hs <= 50: return f"{hs * 100} ft"
                if hs <= 55: return f"Kullanılmıyor ({hs})"
                if hs <= 80: return f"{(hs - 50) * 1000} ft"
                if hs <= 88: return f"Kullanılmıyor ({hs})"
                if hs == 89: return "> 30000 ft"
                if 90 <= hs <= 99:
                    ft_map = {90: "< 164 ft", 91: "164-328 ft", 92: "328-656 ft", 93: "656-984 ft", 94: "984-1968 ft", 95: "1968-3280 ft", 96: "3280-4921 ft", 97: "4921-6561 ft", 98: "6561-8202 ft", 99: ">= 8202 ft"}
                    return ft_map.get(hs, f"Kod {hs}")
            except: return f"Kod {hs_str}"
            return f"Kod {hs_str}"

        for tok in tokens:
            if tok == '=': continue
            
            if tok in ["AAXX", "BBXX"]:
                if not any("BÖLÜM 0" in r for r in res):
                    res.append("🔹 BÖLÜM 0: Başlık ve Tanımlamalar")
                ind_desc = "Kara" if tok == "AAXX" else "Deniz"
                res.append(f"{tok} : {ind_desc} istasyonundan yapılan yüzey (sinoptik) gözlemi indikatörü.")
                mode = "0"
                continue
            elif tok in ["CCA", "CCB", "CCC", "COR", "RTD"]:
                if not any("BÖLÜM 0" in r for r in res):
                    res.append("🔹 BÖLÜM 0: Başlık ve Tanımlamalar")
                res.append(f"{tok} : Düzeltilmiş (Correction) veya gecikmiş rapor indikatörü.")
                mode = "0"
                continue
            elif tok.startswith("222") and len(tok) == 5:
                res.append("🔹 BÖLÜM 2: Deniz Yüzeyi Verileri")
                res.append(f"{tok} : Bölüm 2 İndikatörü ve Gemi Yön/Hız Bilgisi.")
                mode = "2"
                continue
            elif tok == "333":
                res.append("🔹 BÖLÜM 3: İklimsel ve Özel Veriler")
                res.append("333 : Bölüm 3 İndikatörü (Klimatolojik ve Bölgesel Ek Veriler başlıyor).")
                mode = "3"
                continue
            elif tok == "444":
                res.append("🔹 BÖLÜM 4: Bulut ve Ek Veriler")
                res.append("444 : Bölüm 4 İndikatörü.")
                mode = "4"
                continue
            elif tok == "555":
                res.append("🔹 BÖLÜM 5: Ulusal Veriler")
                res.append("555 : Bölüm 5 İndikatörü (Sadece o ülkeye özgü şifrelemeler başlıyor).")
                mode = "5"
                continue
                
            if mode == "HEADER":
                if len(tok) == 6 and (tok.startswith('SM') or tok.startswith('SI') or tok.startswith('SN')):
                    if not any("BÖLÜM 0" in r for r in res):
                        res.append("🔹 BÖLÜM 0: Başlık ve Tanımlamalar")
                    t1 = "Ana Sinoptik Rapor" if tok.startswith('SM') else "Sinoptik Rapor"
                    res.append(f"{tok} : WMO Bülten Başlığı ({tok[:2]}: {t1}, {tok[2:4]}: Ülke Kodu).")
                    continue
                elif len(tok) == 4 and tok.isalpha():
                    res.append(f"{tok} : İstasyon ICAO Kodu.")
                    continue
                elif len(tok) == 6 and tok.isdigit():
                    res.append(f"{tok} : Rasat Zamanı (Ayın {int(tok[:2])}. günü, Saat {tok[2:4]}:{tok[4:]} UTC).")
                    continue
                elif len(tok) == 5 and tok.isdigit():
                    mode = "0"
            
            if mode == "0":
                if len(tok) == 5 and tok.isdigit():
                    is_station = False
                    if tok.startswith("17"):
                        try:
                            hr = int(tok[2:4])
                            if hr > 23:
                                is_station = True
                        except:
                            pass
                    
                    if not is_station and int(tok[:2]) <= 31 and int(tok[2:4]) <= 23:
                        if not any("BÖLÜM 0" in r for r in res):
                            res.append("🔹 BÖLÜM 0: Başlık ve Tanımlamalar")
                        res.append(f"{tok} : Tarih, Saat ve Rüzgar Birimi")
                        res.append(f"  {tok[:2]}: Ayın {int(tok[:2])}. günü")
                        res.append(f"  {tok[2:4]}: Saat {tok[2:4]}:00 UTC")
                        iw = tok[4]
                        if iw == '0': iw_desc = "m/s (Tahmini)"; iw_unit = "m/s"
                        elif iw == '1': iw_desc = "m/s (Ölçümle)"; iw_unit = "m/s"
                        elif iw == '3': iw_desc = "Knot (Tahmini)"; iw_unit = "Knot"
                        elif iw == '4': iw_desc = "Rüzgar ölçüm birimi Knot'tır (Ölçüm aletiyle yapılmış)"; iw_unit = "Knot"
                        else: iw_desc = f"Kod {iw}"
                        res.append(f"  {tok[4]}: {iw_desc}.")
                        mode = "0_STATION"
                    else:
                        if not any("BÖLÜM 0" in r for r in res):
                            res.append("🔹 BÖLÜM 0: Başlık ve Tanımlamalar")
                        res.append(f"{tok} : İstasyon WMO Numarası.")
                        res.append("🔹 BÖLÜM 1: Ana Sinoptik Veriler")
                        mode = "1"
                        sec1_idx = 0
                continue
            
            if mode == "0_STATION":
                if len(tok) == 5:
                    res.append(f"{tok} : İstasyon WMO Numarası.")
                    res.append("🔹 BÖLÜM 1: Ana Sinoptik Veriler")
                    mode = "1"
                    sec1_idx = 0
                continue
            
            if mode == "1":
                if len(tok) == 5:
                    if sec1_idx == 0:
                        res.append(f"{tok} : Yağış, İstasyon Tipi, Bulut Tabanı ve Görüş (1 iR ix h VV)")
                        ir_map = {'0': "Yağış grubu Bölüm 1 veya 3'te yer alıyor", '1': "Yağış grubu Bölüm 1 veya 3'te yer alıyor", '2': "Yağış grubu Bölüm 1 veya 3'te (Ölçülmedi/Yok)", '3': "Yağış yok (Grup atlandı)", '4': "Yağış ölçülmedi (Grup atlandı)"}
                        ix_map = {'1': "İnsanlı istasyon, hava hadisesi var", '2': "İnsanlı istasyon, halihazırda önemli hava hadisesi yok (7. Grup atlandı)", '3': "İnsanlı istasyon, gözlem yok", '4': "Otomatik istasyon, hava hadisesi var", '5': "Otomatik istasyon, hava hadisesi yok", '6': "Otomatik istasyon, gözlem yok", '7': "Otomatik istasyon, hava hadisesi var"}
                        res.append(f"  {tok[0]}: {ir_map.get(tok[0], 'Bilinmeyen iR')}.")
                        res.append(f"  {tok[1]}: {ix_map.get(tok[1], 'Bilinmeyen ix')}.")
                        res.append(f"  {tok[2]}: En alçak bulutun taban yüksekliği {get_h_desc(tok[2])}.")
                        res.append(f"  {tok[3:]}: Görüş mesafesi {get_vv_desc(tok[3:])}.")
                        sec1_idx = 1
                    elif sec1_idx == 1:
                        res.append(f"{tok} : Toplam Kapalılık ve Rüzgar (N dd ff)")
                        n_val = tok[0]
                        if n_val == '9': n_desc = "Gök görünmüyor"
                        elif n_val == '/': n_desc = "Ölçülmedi"
                        elif n_val == '0': n_desc = "Bulutsuz"
                        elif n_val == '8': n_desc = "Tamamen kapalı"
                        elif n_val == '7': n_desc = "7/8 (Neredeyse kapalı)"
                        else: n_desc = f"{n_val}/8 kapalı"
                        res.append(f"  {tok[0]}: Gökyüzü kapalılığı {n_desc}.")
                        
                        dd = tok[1:3]
                        if dd == '00': dd_desc = "Sakin"
                        elif dd == '99': dd_desc = "Değişken (VRB)"
                        elif dd == '//': dd_desc = "Bilinmiyor"
                        else: dd_desc = f"{int(dd)*10} derece"
                        res.append(f"  {tok[1:3]}: Rüzgar yönü {dd_desc}.")
                        
                        ff = tok[3:5]
                        res.append(f"  {tok[3:5]}: Rüzgar hızı {int(ff) if ff.isdigit() else ff} {iw_unit}.")
                        sec1_idx = 2
                    else:
                        ind = tok[0]
                        if ind == '0':
                            res.append(f"{tok} : Ekstra Rüzgar Hızı (00fff)")
                            res.append(f"  00: Yüksek rüzgar hızı indikatörü.")
                            res.append(f"  {tok[2:5]}: Rüzgar hızı {int(tok[2:5]) if tok[2:5].isdigit() else '///'} birim.")
                        elif ind == '1':
                            res.append(f"{tok} : Hava Sıcaklığı (1 sn TTT)")
                            res.append(f"  1: Sıcaklık grubu indikatörü.")
                            sign = "sıfırın üzerinde (+)" if tok[1] == '0' else "sıfırın altında (-)"
                            res.append(f"  {tok[1]}: Sıcaklık {sign}.")
                            temp_val = int(tok[2:5])/10.0 if tok[2:5].isdigit() else tok[2:5]
                            res.append(f"  {tok[2:5]}: Sıcaklık {temp_val} °C.")
                        elif ind == '2':
                            res.append(f"{tok} : İşba / Çiy Noktası Sıcaklığı (2 sn TdTdTd)")
                            res.append(f"  2: İşba grubu indikatörü.")
                            if tok[1] == '9':
                                res.append(f"  9: Bağıl nem indikatörü.")
                                res.append(f"  {tok[2:5]}: Bağıl nem %{int(tok[2:5]) if tok[2:5].isdigit() else tok[2:5]}.")
                            else:
                                sign = "sıfırın üzerinde (+)" if tok[1] == '0' else "sıfırın altında (-)"
                                res.append(f"  {tok[1]}: Sıcaklık {sign}.")
                                td_val = int(tok[2:5])/10.0 if tok[2:5].isdigit() else tok[2:5]
                                res.append(f"  {tok[2:5]}: İşba sıcaklığı {td_val} °C.")
                        elif ind == '3':
                            res.append(f"{tok} : İstasyon Seviyesi Basıncı - QFE (3 P0P0P0P0)")
                            res.append(f"  3: İstasyon basıncı indikatörü.")
                            if tok[1:].isdigit():
                                val = int(tok[1:])
                                p_val = (10000+val)/10.0 if val < 1000 else val/10.0
                                res.append(f"  {tok[1:5]}: İstasyon basıncı {p_val} hPa.")
                            else:
                                res.append(f"  {tok[1:5]}: İstasyon basıncı ölçülmedi (////).")
                        elif ind == '4':
                            res.append(f"{tok} : Deniz Seviyesi Basıncı veya Jeopotansiyel Yükseklik (4 PPPP / 4 a3hhh)")
                            res.append(f"  4: Basınç / Yükseklik indikatörü.")
                            if tok[1:].isdigit():
                                val_str = tok[1:5]
                                val = int(val_str)
                                # QNH (Deniz seviyesi basıncı) değerleri Dünya'da ekstrem durumlar hariç 920 ile 1090 hPa arasındadır.
                                # Eğer değer '8' veya '7' ile başlıyorsa ve MSLP olamayacak bir değerse bu a3hhh (Jeopotansiyel) grubudur.
                                if val_str.startswith('8') and 8000 <= val < 9000:
                                    res.append(f"  8: Standart izobarik yüzey (850 hPa indikatörü).")
                                    res.append(f"  {val_str[1:]}: 850 hPa seviyesinin yüksekliği 1{val_str[1:]} Geopotansiyel Metre.")
                                elif val_str.startswith('7') and 7000 <= val < 8000:
                                    res.append(f"  7: Standart izobarik yüzey (700 hPa indikatörü).")
                                    res.append(f"  {val_str[1:]}: 700 hPa seviyesinin yüksekliği 3{val_str[1:]} Geopotansiyel Metre.")
                                else:
                                    p_val = (10000 + val) / 10.0 if val < 1000 else val / 10.0
                                    res.append(f"  {val_str}: Deniz seviyesi basıncı {p_val} hPa.")
                            else:
                                res.append(f"  {tok[1:5]}: Veri ölçülmedi (////).")
                        elif ind == '5':
                            res.append(f"{tok} : 3 Saatlik Basınç Değişimi (5 a ppp)")
                            res.append(f"  5: Basınç eğilimi indikatörü.")
                            res.append(f"  {tok[1]}: Basınç karakteri: {self.get_a_description(tok[1])}.")
                            ppp_val = int(tok[2:5])/10.0 if tok[2:5].isdigit() else tok[2:5]
                            res.append(f"  {tok[2:5]}: Son 3 saatteki basınç değişimi {ppp_val} hPa.")
                        elif ind == '6':
                            res.append(f"{tok} : Yağış Miktarı (6 RRR tR)")
                            res.append(f"  6: Yağış grubu indikatörü.")
                            if tok[1:4] == '000': r_desc = "0 mm (Eser miktar / İz veya hiç yağış yok)"
                            elif tok[1:4] == '990': r_desc = "Eser miktar (İz)"
                            elif tok[1:4].isdigit() and int(tok[1:4]) > 990: r_desc = f"{(int(tok[1:4])-990)/10.0} mm"
                            elif tok[1:4].isdigit(): r_desc = f"{int(tok[1:4])} mm"
                            else: r_desc = "Ölçülmedi"
                            res.append(f"  {tok[1:4]}: Yağış miktarı {r_desc}.")
                            tr_map = {'1':'son 6 saat', '2':'son 12 saat', '3':'son 18 saat', '4':'son 24 saat'}
                            res.append(f"  {tok[4]}: Ölçüm periyodu {tr_map.get(tok[4], 'Bilinmiyor')}.")
                        elif ind == '7':
                            res.append(f"{tok} : Halihazır Hava ve Geçmiş Hava (7 ww W1 W2)")
                            res.append(f"  7: Hava hadisesi indikatörü.")
                            res.append(f"  {tok[1:3]}: Halihazır hava: {self.get_ww_description(tok[1:3])}.")
                            res.append(f"  {tok[3]}: Geçmiş hava 1: {self.get_w1w2_description(tok[3])}.")
                            res.append(f"  {tok[4]}: Geçmiş hava 2: {self.get_w1w2_description(tok[4])}.")
                        elif ind == '8':
                            res.append(f"{tok} : Bulut Tipleri (8 Nh CL CM CH)")
                            res.append(f"  8: Bulut detayları indikatörü.")
                            res.append(f"  {tok[1]}: Alçak/orta bulut kapalılığı {tok[1]}/8.")
                            res.append(f"  {tok[2]}: Alçak bulut (CL): {self.get_cl_description(tok[2])}.")
                            res.append(f"  {tok[3]}: Orta bulut (CM): {self.get_cm_description(tok[3])}.")
                            res.append(f"  {tok[4]}: Yüksek bulut (CH): {self.get_ch_description(tok[4])}.")
                        elif ind == '9':
                            res.append(f"{tok} : İstasyon Saati (9 GG gg)")
                            res.append(f"  9: Zaman indikatörü.")
                            res.append(f"  {tok[1:5]}: {tok[1:3]}:{tok[3:5]} UTC.")
            
            elif mode == "2":
                if len(tok) == 5:
                    ind = tok[0]
                    if ind == '0':
                        res.append(f"{tok} : Deniz Suyu Sıcaklığı (0 sn TwTwTw)")
                    elif ind == '1':
                        res.append(f"{tok} : Dalga Periyodu ve Yüksekliği (1 Pwa Pwa Hwa Hwa)")
                    elif ind == '2':
                        res.append(f"{tok} : Rüzgar Dalgaları (2 Pw Pw Hw Hw)")
                    elif ind == '3':
                        res.append(f"{tok} : Ölü Dalga Yönü (3 dw1 dw1 dw2 dw2)")
                    elif ind == '4':
                        res.append(f"{tok} : 1. Ölü Dalga Periyodu ve Yüksekliği (4 Pw1 Pw1 Hw1 Hw1)")
                    elif ind == '5':
                        res.append(f"{tok} : 2. Ölü Dalga Periyodu ve Yüksekliği (5 Pw2 Pw2 Hw2 Hw2)")
                    elif ind == '6':
                        res.append(f"{tok} : Gemi Buzlanması (6 Is Es Es Rs)")
                    elif ind == '7':
                        res.append(f"{tok} : Deniz Buzu Durumu (7 0 Is Es Es)")
                    else:
                        res.append(f"{tok} : Bölüm 2 Ek Veri Grubu")
            
            elif mode == "3":
                if len(tok) == 5:
                    ind = tok[0]
                    if ind == '1':
                        res.append(f"{tok} : Maksimum Sıcaklık (1 sn TxTxTx)")
                        res.append(f"  1: Maksimum sıcaklık indikatörü.")
                        sign = "sıfırın üzerinde (+)" if tok[1] == '0' else "sıfırın altında (-)"
                        res.append(f"  {tok[1]}: Sıcaklık {sign}.")
                        res.append(f"  {tok[2:5]}: Gündüz ölçülen maksimum sıcaklık {int(tok[2:5])/10.0 if tok[2:5].isdigit() else '///'} °C.")
                    elif ind == '2':
                        res.append(f"{tok} : Minimum Sıcaklık (2 sn TnTnTn)")
                        res.append(f"  2: Minimum sıcaklık indikatörü.")
                        sign = "sıfırın üzerinde (+)" if tok[1] == '0' else "sıfırın altında (-)"
                        res.append(f"  {tok[1]}: Sıcaklık {sign}.")
                        res.append(f"  {tok[2:5]}: Gece ölçülen minimum sıcaklık {int(tok[2:5])/10.0 if tok[2:5].isdigit() else '///'} °C.")
                    elif ind == '3':
                        res.append(f"{tok} : Toprak Durumu ve Sıcaklığı (3 E TgTg)")
                        res.append(f"  3: Toprak durumu indikatörü.")
                        res.append(f"  {tok[1]}: Yerin hali: {self.get_e_description(tok[1])}.")
                        if tok[2:5] == '///':
                            res.append(f"  {tok[2:5]}: Toprak sıcaklığı ölçülmemiş veya bildirilmiyor.")
                        else:
                            sign = "-" if tok[2] == '1' else "+"
                            res.append(f"  {tok[2:5]}: Toprak sıcaklığı {sign}{int(tok[3:5]) if tok[3:5].isdigit() else '//'} °C.")
                    elif ind == '4':
                        res.append(f"{tok} : Kar Durumu ve Kalınlığı (4 E' sss)")
                        res.append(f"  4: Kar/Buz durumu indikatörü.")
                        res.append(f"  {tok[1]}: Kar/Buz hali: {self.get_ep_description(tok[1])}.")
                        res.append(f"  {tok[2:5]}: Kar kalınlığı {int(tok[2:5]) if tok[2:5].isdigit() else '///'} cm.")
                    elif ind == '5':
                        if tok.startswith('55'):
                            res.append(f"{tok} : Güneşlenme Süresi (55 SSS)")
                            res.append(f"  55: Güneşlenme indikatörü.")
                            res.append(f"  {tok[2:5]}: Güneşlenme süresi {int(tok[2:5])/10.0 if tok[2:5].isdigit() else '///'} Saat.")
                        else:
                            res.append(f"{tok} : Günlük Buharlaşma (5 EEE iE)")
                            res.append(f"  5: Buharlaşma indikatörü.")
                            res.append(f"  {tok[1:4]}: Buharlaşma miktarı {int(tok[1:4])/10.0 if tok[1:4].isdigit() else '///'} mm.")
                            res.append(f"  {tok[4]}: Buharlaşma aleti tipi {tok[4]}.")
                    elif ind == '6':
                        res.append(f"{tok} : Yağış Miktarı Ek (6 RRR tR)")
                        res.append(f"  6: Yağış grubu indikatörü.")
                        res.append(f"  {tok[1:4]}: Yağış miktarı {tok[1:4]} mm.")
                        res.append(f"  {tok[4]}: Ölçüm periyodu {tok[4]}.")
                    elif ind == '7':
                        res.append(f"{tok} : 24 Saatlik Yağış (7 R24R24R24R24)")
                        res.append(f"  7: 24 Saatlik yağış indikatörü.")
                        res.append(f"  {tok[1:5]}: Yağış miktarı {int(tok[1:5])/10.0 if tok[1:5].isdigit() else '////'} mm.")
                    elif ind == '8':
                        res.append(f"{tok} : {cloud_layer_count}. Bulut Açılımı Katmanı (8 Ns C hshs)")
                        res.append(f"  8: Bulut katmanı indikatörü.")
                        res.append(f"  {tok[1]}: Miktar {tok[1]}/8.")
                        c_map = {'0':'Cirrus (Ci)','1':'Cirrocumulus (Cc)','2':'Cirrostratus (Cs)','3':'Altocumulus (Ac)','4':'Altostratus (As)','5':'Nimbostratus (Ns)','6':'Stratocumulus (Sc)','7':'Stratus (St)','8':'Cumulus (Cu)','9':'Cumulonimbus (Cb)'}
                        res.append(f"  {tok[2]}: Bulut tipi {c_map.get(tok[2], 'Bilinmiyor')}.")
                        res.append(f"  {tok[3:5]}: Bulut tabanı {get_hshs_desc(tok[3:5])} (Yükseklik kodu {tok[3:5]}).")
                        cloud_layer_count += 1
                    elif ind == '9':
                        if tok.startswith('910'):
                            res.append(f"{tok} : Rüzgar Hamlesi (9 10 ff)")
                            res.append(f"  910: Rüzgar hamlesi indikatörü.")
                            res.append(f"  {tok[3:5]}: Ölçülen hamle hızı {tok[3:5]} {iw_unit}.")
                        elif tok.startswith('911'):
                            res.append(f"{tok} : Özel Hadise / Maksimum Rüzgar Hamlesi (9 11 ff)")
                            res.append(f"  911: Maksimum rüzgar hamlesi (Gust) indikatörü.")
                            res.append(f"  {tok[3:5]}: Ölçülen hamle hızı {tok[3:5]} {iw_unit}.")
                        elif tok.startswith('931'):
                            res.append(f"{tok} : Toplam Kar Kalınlığı (9 31 ss)")
                            res.append(f"  931: Toplam kar kalınlığı indikatörü.")
                            res.append(f"  {tok[3:5]}: Toplam kar kalınlığı {int(tok[3:5]) if tok[3:5].isdigit() else tok[3:5]} cm.")
                        elif tok.startswith('932'):
                            res.append(f"{tok} : Taze Kar Kalınlığı (9 32 ss)")
                            res.append(f"  932: Taze kar kalınlığı indikatörü.")
                            res.append(f"  {tok[3:5]}: Taze kar kalınlığı {int(tok[3:5]) if tok[3:5].isdigit() else tok[3:5]} cm.")
                        elif tok.startswith('933'):
                            res.append(f"{tok} : Karın Su Eşdeğeri (9 33 RR)")
                            res.append(f"  933: Karın su eşdeğeri indikatörü.")
                            res.append(f"  {tok[3:5]}: Eşdeğer miktar {int(tok[3:5]) if tok[3:5].isdigit() else tok[3:5]} mm.")
                        elif tok.startswith('909'):
                            res.append(f"{tok} : Yağışın Başlama ve Bitme Zamanı (9 09 Rt dc)")
                            res.append(f"  909: Yağış zamanı indikatörü.")
                            res.append(f"  {tok[3]}: Başlama/Bitme zamanı (Rt kodu {tok[3]}).")
                            res.append(f"  {tok[4]}: Yağış süresi ve karakteri (dc kodu {tok[4]}).")
                        elif tok.startswith('94'):
                            res.append(f"{tok} : Derinlik Toprak Sıcaklığı (9 4 b tt)")
                            depth_map = {'1': '5 cm', '2': '10 cm', '3': '20 cm', '4': '50 cm', '5': '100 cm'}
                            depth = depth_map.get(tok[2], f"Kod {tok[2]}")
                            res.append(f"  94: Derinlik toprak sıcaklığı indikatörü.")
                            res.append(f"  {tok[2]}: Derinlik {depth}.")
                            if tok[3:5].isdigit():
                                tt = int(tok[3:5])
                                t_val = -(tt - 50) if tt >= 50 else tt
                                res.append(f"  {tok[3:5]}: Toprak sıcaklığı {t_val} °C.")
                            else:
                                res.append(f"  {tok[3:5]}: Toprak sıcaklığı ölçülemedi.")
                    elif tok.startswith('924'):
                        res.append(f"{tok} : Dolu Çapı / Deniz Durumu (9 24 xx)")
                        res.append(f"  924: Dolu çapı / deniz durumu indikatörü.")
                        res.append(f"  {tok[3:5]}: Çap {int(tok[3:5]) if tok[3:5].isdigit() else tok[3:5]} mm (veya Kod).")
                    elif tok.startswith('960') or tok.startswith('961'):
                        hadise_no = "İkinci" if tok.startswith('960') else "Üçüncü"
                        res.append(f"{tok} : {hadise_no} Hava Hadisesi (9 60/61 ww)")
                        res.append(f"  {tok[:3]}: {hadise_no} hava hadisesi indikatörü.")
                        res.append(f"  {tok[3:5]}: Hadise: {self.get_ww_description(tok[3:5])}.")
                    else:
                        res.append(f"{tok} : Özel Hadise Grubu (9 ...)")

            elif mode == "4":
                if len(tok) == 5:
                    res.append(f"{tok} : İstasyon Seviyesi Altındaki Bulutlar (N' C' H' H')")
                    res.append(f"  {tok[0]}: Bulut miktarı {tok[0]}/8.")
                    c_map = {'0':'Cirrus (Ci)','1':'Cirrocumulus (Cc)','2':'Cirrostratus (Cs)','3':'Altocumulus (Ac)','4':'Altostratus (As)','5':'Nimbostratus (Ns)','6':'Stratocumulus (Sc)','7':'Stratus (St)','8':'Cumulus (Cu)','9':'Cumulonimbus (Cb)'}
                    res.append(f"  {tok[1]}: Bulut tipi {c_map.get(tok[1], 'Bilinmiyor')}.")
                    res.append(f"  {tok[2:4]}: Bulut üst sınır yüksekliği (Kod {tok[2:4]}).")
                    res.append(f"  {tok[4]}: Bulut alt sınır yüksekliği / Karakteristik (Kod {tok[4]}).")

            elif mode == "5":
                if len(tok) == 5:
                    ind = tok[0]
                    if ind == '0':
                        res.append(f"{tok} : Deniz Suyu Sıcaklığı (0 sn TwTwTw)")
                        res.append(f"  0: Deniz suyu sıcaklık indikatörü.")
                        sign = "sıfırın üzerinde (+)" if tok[1] == '0' else "sıfırın altında (-)"
                        res.append(f"  {tok[1]}: Sıcaklık {sign}.")
                        res.append(f"  {tok[2:5]}: Deniz suyu sıcaklığı {int(tok[2:5])/10.0 if tok[2:5].isdigit() else '///'} °C.")
                    elif ind == '1':
                        res.append(f"{tok} : Deniz Seviyesi Basıncı - QNH (1 PPPP)")
                        res.append(f"  1: Türkiye için QNH (Altimetre) basıncı indikatörü.")
                        val = int(tok[1:]) if tok[1:].isdigit() else None
                        if val is not None:
                            qnh = (10000+val)/10.0 if val < 5000 else val/10.0
                            res.append(f"  {tok[1:5]}: QNH Basıncı {qnh} hPa.")
                        else:
                            res.append(f"  {tok[1:5]}: QNH Basıncı ölçülemedi.")
                    elif ind == '2':
                        res.append(f"{tok} : Günlük Toplam Yağış (2 RRRR)")
                        res.append(f"  2: Günlük yağış indikatörü.")
                        val = int(tok[1:5])/10.0 if tok[1:5].isdigit() else '////'
                        res.append(f"  {tok[1:5]}: Yağış miktarı {val} mm.")
                    elif ind == '3':
                        res.append(f"{tok} : Aylık Toplam Yağış (3 RRRR)")
                        res.append(f"  3: Aylık yağış indikatörü.")
                        val = int(tok[1:5])/10.0 if tok[1:5].isdigit() else '////'
                        res.append(f"  {tok[1:5]}: Yağış miktarı {val} mm.")
                    elif ind == '4':
                        res.append(f"{tok} : İstasyon Seviyesi Basıncı - QFE (4 PPPP)")
                        res.append(f"  4: İstasyon basıncı (QFE) indikatörü.")
                        val = int(tok[1:]) if tok[1:].isdigit() else None
                        if val is not None:
                            qfe = (10000+val)/10.0 if val < 1000 else val/10.0
                            res.append(f"  {tok[1:5]}: QFE Basıncı {qfe} hPa.")
                        else:
                            res.append(f"  {tok[1:5]}: QFE Basıncı ölçülemedi.")

        if raw_str.endswith('='):
            if res[-1] != "= : Raporun sonlandığını (bittiğini) gösteren işaret.":
                res.append("= : Raporun sonlandığını (bittiğini) gösteren işaret.")

        # Mevcut düz metin çıktısını şık bir ASCII Tablo (Grid) formatına dönüştür
        grid_res = [f"Ham Veri: {raw_str}\n"]
        grid_res.append("┌─────────┬────────────────────────────────────────┬─────────────────────────────────────────────────────┐")
        grid_res.append("│ GRUP    │ KATEGORİ / BAŞLIK                      │ ÇÖZÜMLENEN DEĞERLER VE DETAYLAR                     │")
        grid_res.append("├─────────┼────────────────────────────────────────┼─────────────────────────────────────────────────────┤")
        
        import textwrap
        def commit_row(grup, baslik, detaylar):
            if not grup and not baslik and not detaylar: return
            b_lines = textwrap.wrap(baslik, width=38) if baslik else [""]
            d_lines = []
            for d in detaylar: d_lines.extend(textwrap.wrap(d, width=51))
            if not d_lines: d_lines = ["-"]
            
            max_l = max(len(b_lines), len(d_lines))
            for i in range(max_l):
                g_str = f" {grup[:7]:<7}│" if i == 0 else "        │"
                b_str = f" {b_lines[i]:<38} │" if i < len(b_lines) else " " * 40 + "│"
                d_str = f" {d_lines[i]:<51} │" if i < len(d_lines) else " " * 53 + "│"
                grid_res.append(f"│{g_str}{b_str}{d_str}")
            grid_res.append("├─────────┼────────────────────────────────────────┼─────────────────────────────────────────────────────┤")

        c_grp, c_bas, c_det = "", "", []
        for line in res[1:]: 
            line_clean = line.strip()
            if not line_clean: continue
            if line_clean.startswith("🔹"):
                commit_row(c_grp, c_bas, c_det); c_grp, c_bas, c_det = "", "", []
                grid_res.append("├─────────┴────────────────────────────────────────┴─────────────────────────────────────────────────────┤")
                grid_res.append(f"│ {line_clean[:98]:<98} │")
                grid_res.append("├─────────┬────────────────────────────────────────┬─────────────────────────────────────────────────────┤")
            elif " : " in line_clean and not line.startswith("  "):
                commit_row(c_grp, c_bas, c_det)
                parts = line.split(" : ", 1)
                c_grp, c_bas, c_det = parts[0].strip(), parts[1].strip(), []
            elif line.startswith("  "): c_det.append(line.strip())
            elif line.startswith("= :"):
                commit_row(c_grp, c_bas, c_det); c_grp, c_bas, c_det = "", "", []
                commit_row("=", "Rapor Sonu İndikatörü", ["Raporun bittiğini gösteren işaret."])
        commit_row(c_grp, c_bas, c_det)
        grid_res[-1] = "└─────────┴────────────────────────────────────────┴─────────────────────────────────────────────────────┘"
        return "\n".join(grid_res)

    def validate(self):
        """Raporun WMO standartlarına uygunluğunu kontrol eder."""
        return len(self.errors) == 0
        
    def get_errors(self):
        """Bulunan format hatalarını döndürür."""
        return self.errors

# Kullanım Örneği:
# decoder = SynopDecoder()
# print(decoder.decode_line("AAXX 28121 17244 11658 82715 10125 20085 40125 52005 70222 85300 333 10185 20054"))