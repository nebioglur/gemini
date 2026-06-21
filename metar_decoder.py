import re

class MetarDecoder:
    """
    Havacılık METAR ve SPECI mesajlarını çözen ve 
    insan okumasına uygun hale getiren decoder.
    """
    def __init__(self):
        self.errors = []

    def decode_line(self, line):
        self.errors = []
        if not line or len(str(line).strip()) < 10:
            self.errors.append("Geçersiz veya çok kısa METAR şifresi.")
            return None
            
        data = {"ham_veri": str(line).strip()}
        parts = data["ham_veri"].split()
        
        idx = 0
        # 1. Rapor Tipi
        if parts[idx] in ["METAR", "SPECI"]:
            data["tip"] = parts[idx]
            idx += 1
            
        # 2. İstasyon Kodu (ICAO)
        if idx < len(parts) and len(parts[idx]) == 4 and parts[idx].isalpha():
            data["istasyon"] = parts[idx]
            idx += 1
            
        # 3. Tarih ve Saat Grubu
        if idx < len(parts) and re.match(r'^\d{6}Z$', parts[idx]):
            data["gun"] = parts[idx][:2]
            data["saat_gmt"] = parts[idx][2:4]
            data["dakika"] = parts[idx][4:6]
            idx += 1
            
        # Diğer tüm grupları tespit et
        clouds = []
        weather = []
        recent_weather = []
        for i in range(idx, len(parts)):
            p = parts[i]
            if p == "AUTO":
                data["otomatik"] = True
            elif p == "CAVOK":
                data["cavok"] = True
            elif re.match(r'^\d{3}\d{2,3}(G\d{2,3})?(KT|MPS|KMH)$', p) or p.startswith("VRB"):
                data["ruzgar"] = p
            elif re.match(r'^\d{4}$', p) or re.match(r'^\d{4}NDV$', p):
                data["gorus"] = p
            elif re.match(r'^M?\d{2}/M?\d{2}$', p) or re.match(r'^M?\d{2}/$', p):
                data["sicaklik_isba"] = p
            elif re.match(r'^Q\d{4}$', p) or re.match(r'^A\d{4}$', p):
                data["basinc"] = p
            elif re.match(r'^(FEW|SCT|BKN|OVC|VV|NSC|NCD)(\d{3}|///)?(CB|TCU|///)?$', p):
                clouds.append(p)
            elif re.match(r'^R\d{2}[LCR]?/.*', p):
                pass # RVR (Runway Visual Range) grubu şimdilik atlanıyor
            elif re.match(r'^(RE)?(\+|-|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?(DZ|RA|SN|SG|IC|PE|GR|GS|UP)?(BR|FG|FU|VA|DU|SA|HZ)?(PO|SQ|FC|SS|DS)?$', p):
                # Hava hadiseleri (Çakışmaları önlemek için istisnaları filtrele)
                if p not in ["NOSIG", "BECMG", "TEMPO", "RMK", "AUTO", "CAVOK"]: 
                    if p.startswith("RE"):
                        recent_weather.append(p)
                    else:
                        weather.append(p)
            elif p in ["NOSIG", "BECMG", "TEMPO", "RMK", "PROB30", "PROB40"]:
                data["trend_rmk"] = " ".join(parts[i:])
                break
                
        if clouds: data["bulutlar"] = clouds
        if weather: data["halihazir_hava"] = weather
        if recent_weather: data["gecmis_hava"] = recent_weather
            
        return data

    def translate_wx(self, code):
        if not code: return ""
        trans = []
        c = code
        if c.startswith('RE'): trans.append("Yakın Zamanda/Geçmiş"); c = c[2:]
        elif c.startswith('VC'): trans.append("Civarında"); c = c[2:]
        
        if c.startswith('+'): trans.append("Kuvvetli"); c = c[1:]
        elif c.startswith('-'): trans.append("Hafif"); c = c[1:]
        
        dict_w = {
            "MI": "Sığ", "PR": "Kısmi", "BC": "Parçalı", "DR": "Alçaktan Savrulan", "BL": "Yüksekten Savrulan",
            "SH": "Sağanak", "TS": "Orajlı", "FZ": "Donduran",
            "DZ": "Çisenti", "RA": "Yağmur", "SN": "Kar", "SG": "Kar Taneleri", "IC": "Buz İğneleri",
            "PE": "Buz Taneleri", "GR": "Dolu", "GS": "Küçük Dolu", "UP": "Bilinmeyen Yağış",
            "BR": "Pus", "FG": "Sis", "FU": "Duman", "VA": "Volkanik Kül", "DU": "Toz", "SA": "Kum", "HZ": "Toz Pusu",
            "PO": "Toz/Kum Şeytanı", "SQ": "Bora (Squall)", "FC": "Hortum", "SS": "Kum Fırtınası", "DS": "Toz Fırtınası"
        }
        chunks = [c[i:i+2] for i in range(0, len(c), 2)]
        for chunk in chunks:
            trans.append(dict_w.get(chunk, chunk))
        
        return f"{code} ({' '.join(trans)})"

    def generate_human_readable(self, data):
        if not data or 'ham_veri' not in data:
            return "Çözümlenecek veri bulunamadı."
            
        res = [f"Ham Veri: {data['ham_veri']}\n"]
        res.append("┌───────────────────────────┬────────────────────────────────────────────────────────────┐")
        res.append("│ METEOROLOJİK PARAMETRE    │ ÇÖZÜMLENEN BİLGİ VE DETAYLAR                               │")
        res.append("├───────────────────────────┼────────────────────────────────────────────────────────────┤")
        
        import textwrap
        def add_grid_row(baslik, deger):
            d_lines = textwrap.wrap(deger, width=58) if deger else ["-"]
            for i, line in enumerate(d_lines):
                b_str = f" {baslik:<25} │" if i == 0 else " " * 27 + "│"
                res.append(f"│{b_str} {line:<58} │")
            res.append("├───────────────────────────┼────────────────────────────────────────────────────────────┤")
        
        if "tip" in data: add_grid_row("Rapor Tipi", data['tip'])
        if "istasyon" in data: add_grid_row("İstasyon (ICAO)", data['istasyon'])
        if "gun" in data: add_grid_row("Tarih ve Saat", f"Ayın {data['gun']}. günü, Saat {data['saat_gmt']}:{data['dakika']} UTC")
        if "otomatik" in data: add_grid_row("Gözlem Tipi", "Otomatik İstasyon (AUTO)")
        
        if "ruzgar" in data:
            r = data["ruzgar"]
            if r.startswith("VRB"): add_grid_row("Yüzey Rüzgarı", f"Değişken yönlü, hızı {r[3:]}")
            else: add_grid_row("Yüzey Rüzgarı", f"{r[:3]} dereceden {r[3:]}")
        
        if "cavok" in data:
            add_grid_row("Görüş / Bulutluluk", "CAVOK (Görüş >= 10km, önemli bulut veya hadise yok)")
        else:
            if "gorus" in data:
                v = data["gorus"].replace("NDV", "")
                add_grid_row("Hakim Görüş", f"{'10 km veya daha fazla' if v == '9999' else f'{int(v)} metre'}")
                
            if "halihazir_hava" in data:
                tr_hava = [self.translate_wx(w) for w in data['halihazir_hava']]
                add_grid_row("Halihazır Hava Hadisesi", ", ".join(tr_hava))
                
            if "gecmis_hava" in data:
                tr_gec = [self.translate_wx(w) for w in data['gecmis_hava']]
                add_grid_row("Geçmiş Hava Hadisesi", ", ".join(tr_gec))
                
            if "bulutlar" in data:
                for i, b in enumerate(data["bulutlar"]):
                    if b in ["NSC", "NCD"]: add_grid_row("Bulut Durumu", f"Önemli bulut yok ({b})")
                    elif b.startswith("VV"): add_grid_row("Dikine Görüş (VV)", f"{int(b[2:5])*100 if b[2:5].isdigit() else 'Bilinmiyor'} feet")
                    else:
                        amt_tr = {"FEW":"Az (1-2/8)", "SCT":"Parçalı (3-4/8)", "BKN":"Çok Bulutlu (5-7/8)", "OVC":"Kapalı (8/8)"}.get(b[:3], b[:3])
                        hgt = f"{int(b[3:6]) * 100} ft" if len(b)>=6 and b[3:6].isdigit() else "Bilinmiyor"
                        tip = f" ({b[6:]})" if len(b)>6 and b[6:] != "///" else ""
                        add_grid_row(f"Bulut Katmanı {i+1}", f"{amt_tr}, Tabanı {hgt}{tip}")
                        
        if "sicaklik_isba" in data:
            t, td = (data["sicaklik_isba"].split('/') + [""])[:2]
            add_grid_row("Sıcaklık / Çiy Noktası", f"{t.replace('M', '-')} °C / {td.replace('M', '-')} °C")
        if "basinc" in data:
            basinc_str = f"{data['basinc'][1:]} hPa" if data["basinc"].startswith('Q') else f"{data['basinc'][1:3]}.{data['basinc'][3:]} inHg"
            add_grid_row("Deniz Seviyesi Basıncı", basinc_str)
        if "trend_rmk" in data: 
            add_grid_row("Trend ve RMK Notları", data['trend_rmk'])
            
        res[-1] = "└───────────────────────────┴────────────────────────────────────────────────────────────┘"
        return "\n".join(res)