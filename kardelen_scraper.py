"""
Kardelen web sitesinden veri çekme işlemlerini yürüten modül.
Siteye giriş yapma, form verilerini analiz etme ve raporları indirme işlerini yapar.
"""
import requests
from bs4 import BeautifulSoup
import re
import logging

# =============================================================================
# WEB VERİ ÇEKME SINIFI (SCRAPER)
# =============================================================================
class KardelenScraper:
    """
    Kardelen web sitesine bağlanan ve verileri indiren ana sınıf.
    Bu sınıf, siteye giriş yapar, tarihleri ayarlar ve raporları getirir.
    """
    def __init__(self, station_id="17244", proxies=None):
        self.station_id = station_id
        # Tüm istasyonlar için LogGoster.aspx kullanılıyor (Kopya dosyadan alınan mantık)
        self.base_url = f"http://kardelen.mgm.gov.tr/bultenler/GnkLog/LogGoster.aspx?ist={station_id}"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.base_url
        })
        
        if proxies:
            self.session.proxies.update(proxies)
            
        self.config = {
            "gun_sifir": False,
            "ay_map": {},
            "filtre_map": {}
        }
        self.station_buttons = {}

    def login(self, username, password):
        """
        Kardelen sistemine kullanıcı adı ve şifre ile giriş yapar.
        """
        login_url = "http://kardelen.mgm.gov.tr/Default.aspx"
        try:
            # 1. Sayfayı Getir (ViewState vb. için)
            r = self.session.get(login_url, timeout=10)
            if "Çıkış" in r.text or "LogGoster" in r.url:
                return True # Zaten giriş yapılmış

            soup = BeautifulSoup(r.text, "html.parser")
            
            # 2. Form Verilerini Hazırla
            payload = {}
            for inp in soup.find_all("input", type="hidden"):
                if inp.get("name"): payload[inp["name"]] = inp.get("value", "")
            
            # Kullanıcı Adı ve Şifre Alanlarını Bul (Genel Arama)
            user_inp = soup.find("input", {"name": lambda x: x and ("txtKullaniciAdi" in x or "UserName" in x or "User" in x)})
            pass_inp = soup.find("input", {"name": lambda x: x and ("txtSifre" in x or "Password" in x or "Pass" in x)})
            btn_inp = soup.find("input", {"type": "submit", "name": lambda x: x and ("btnGiris" in x or "Login" in x)})

            if user_inp and pass_inp:
                payload[user_inp["name"]] = username
                payload[pass_inp["name"]] = password
                if btn_inp:
                    payload[btn_inp["name"]] = btn_inp.get("value", "Giriş")
                
                # 3. Giriş İsteğini Gönder
                r_post = self.session.post(login_url, data=payload, timeout=15)
                
                # Başarı Kontrolü
                if "Çıkış" in r_post.text or len(r_post.history) > 0 or "LogGoster" in r_post.url:
                    return True
                else:
                    logging.warning("Giriş başarısız: Kullanıcı adı veya şifre hatalı olabilir.")
                    return False
            else:
                logging.warning("Giriş formu alanları tespit edilemedi.")
                return False

        except Exception as e:
            logging.error(f"Giriş işlemi sırasında hata: {e}")
            return False

    def set_station(self, station_id):
        """İstasyon ID'sini değiştirir ve URL'i günceller."""
        self.station_id = station_id
        self.base_url = f"http://kardelen.mgm.gov.tr/bultenler/GnkLog/LogGoster.aspx?ist={station_id}"
        
        self.session.headers.update({"Referer": self.base_url})

    def fetch_station_list(self):
        """
        http://kardelen.mgm.gov.tr/Bultenler/bltIstList.aspx adresinden
        tüm istasyon listesini (WMO ID ve İsim) çeker.
        """
        url = "http://kardelen.mgm.gov.tr/Bultenler/bltIstList.aspx"
        stations = {}
        try:
            r = self.session.get(url, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Tablo satırlarını gez
            for tr in soup.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) >= 2:
                    vals = [td.get_text(" ", strip=True) for td in tds]
                    wmo, name = None, None
                    
                    # 5 haneli sayısal değer WMO ID'dir
                    for v in vals:
                        if v.isdigit() and len(v) == 5: wmo = v
                        elif len(v) > 2 and not v.isdigit() and not name: name = v
                    
                    if wmo and name: stations[wmo] = name
                    
                    # İstasyon seçim butonunu (GÖSTER) bul ve kaydet
                    btn = tr.find("input", {"type": "submit"})
                    if btn and wmo:
                        self.station_buttons[wmo] = btn.get("name")
            return stations
        except Exception as e:
            logging.error(f"İstasyon listesi hatası: {e}")
            return {}

    def analyze_site(self):
        """Siteye ilk bağlantıyı yapar ve formdaki dinamik seçenekleri (Günler, Aylar, Filtreler) öğrenir."""
        try:
            r = self.session.get(self.base_url, timeout=5)
            soup = BeautifulSoup(r.text, "html.parser")

            # 1. Gün Analizi
            dd_gun = soup.find("select", {"name": lambda x: x and "ddBasGun" in x})
            if dd_gun:
                opt = dd_gun.find("option", value=True)
                self.config["gun_sifir"] = (opt and opt["value"].startswith("0") and len(opt["value"]) == 2)

            # 2. Ay Analizi
            dd_ay = soup.find("select", {"name": lambda x: x and "ddBasAy" in x})
            if dd_ay:
                self.config["ay_map"] = {opt.text.strip(): opt["value"] for opt in dd_ay.find_all("option")}

            # 3. Filtre Analizi
            dd_tur = soup.find("select", {"name": lambda x: x and "ddTur" in x})
            if dd_tur:
                self.config["filtre_map"] = {opt.text.strip(): opt["value"] for opt in dd_tur.find_all("option")}

            return True
        except Exception as e:
            logging.error(f"Site analizi bağlantı hatası: {e}")
            # Fallback ayarlar
            self.config["gun_sifir"] = False
            self.config["ay_map"] = {k: str(i) for i, k in enumerate(["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"], 1)}
            self.config["filtre_map"] = {"Tüm Bültenler": "500", "Metar": "1", "Taf": "2", "Sinoptik": "3"}
            return False

    def navigate_to_station(self, wmo_id):
        """
        İstasyon listesi sayfasındaki (bltIstList.aspx) 'GÖSTER' butonuna tıklayarak
        ilgili istasyonun log sayfasına (LogGoster.aspx) gider.
        """
        # Doğrudan URL parametresi ile erişim (Kullanıcı bildirimi üzerine optimize edildi)
        self.set_station(wmo_id)
        return True

    def fetch_logs(self, gun, ay_ismi, yil, filtre_id, gun_bit=None, ay_bit_ismi=None, yil_bit=None):
        """Belirtilen tarih ve filtre ayarlarına göre raporları siteden indirir."""
        try:
            r = self.session.get(self.base_url, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")

            # --- DİNAMİK FORM ANALİZİ ---
            # Sayfadaki input isimlerini (name) otomatik bulur.
            def find_name(keyword):
                el = soup.find(["select", "input"], {"name": lambda x: x and keyword in x})
                return el["name"] if el else None

            # 1. ViewState ve Hidden Field'ları topla
            payload = {}
            for inp in soup.find_all("input", type="hidden"):
                if inp.get("name"):
                    payload[inp["name"]] = inp.get("value", "")

            # 2. Input İsimlerini Tespit Et
            n_gun = find_name("ddBasGun") or find_name("ddGun")
            if not n_gun: n_gun = "ctl00$cBody$ddBasGun"
            
            n_ay = find_name("ddBasAy") or find_name("ddAy")
            if not n_ay: n_ay = "ctl00$cBody$ddBasAy"
            
            n_yil = find_name("ddBasYil") or find_name("ddYil")
            if not n_yil: n_yil = "ctl00$cBody$ddBasYil"
            
            n_gun_bit = find_name("ddBitGun")
            n_ay_bit = find_name("ddBitAy")
            n_yil_bit = find_name("ddBitYil")
            
            # GÜÇLENDİRİLMİŞ TESPİT: Eğer 'Bas' (Başlangıç) alanları varsa ama 'Bit' (Bitiş) bulunamadıysa,
            # isimleri tahmin et (ctl00$cBody$ddBasGun -> ctl00$cBody$ddBitGun)
            if n_gun and "Bas" in n_gun and not n_gun_bit:
                n_gun_bit = n_gun.replace("Bas", "Bit")
            if n_ay and "Bas" in n_ay and not n_ay_bit:
                n_ay_bit = n_ay.replace("Bas", "Bit")
            if n_yil and "Bas" in n_yil and not n_yil_bit:
                n_yil_bit = n_yil.replace("Bas", "Bit")

            if not n_gun_bit: n_gun_bit = "ctl00$cBody$ddBitGun"
            if not n_ay_bit: n_ay_bit = "ctl00$cBody$ddBitAy"
            if not n_yil_bit: n_yil_bit = "ctl00$cBody$ddBitYil"

            n_tur = find_name("ddTur") or find_name("ddBulten") or find_name("ddRaporTipi")
            n_ist = find_name("ddIst") # İstasyon seçimi varsa
            
            # Butonu bul (Goster, Yukle, Listele vb.)
            btn = soup.find("input", {"type": "submit", "name": lambda x: x and ("btn" in x or "Yukle" in x or "Goster" in x)})
            n_btn = btn["name"] if btn else "ctl00$cBody$btnYukle"
            btn_val = btn.get("value", "GÖSTER") if btn else "GÖSTER"

            # 3. Değerleri Hazırla
            # Gün formatı (01 mi 1 mi?) kontrolü
            gun_val = str(int(gun))
            if n_gun:
                gun_sel = soup.find("select", {"name": n_gun})
                if gun_sel and gun_sel.find("option", value="01"):
                    gun_val = str(int(gun)).zfill(2)
            
            gun_bit_val = str(int(gun_bit)).zfill(2) if gun_bit and len(gun_val)==2 else str(int(gun_bit)) if gun_bit else gun_val

            # Ay değerini bul (İsimden value'ya)
            ay_val = "1"
            if n_ay:
                ay_sel = soup.find("select", {"name": n_ay})
                if ay_sel:
                    # Türkçe karakter duyarlı büyük harf çevrimi
                    ay_upper = ay_ismi.replace("i", "İ").replace("ı", "I").upper()
                    opt = ay_sel.find("option", string=lambda t: t and ay_upper in t.replace("i", "İ").replace("ı", "I").upper())
                    if opt: 
                        ay_val = opt["value"]
                    elif ay_sel.find("option", value="01"): # İsimle bulamazsa ve 01 varsa
                        ay_val = "01"
            else:
                # Select bulunamazsa manuel haritalama dene
                tr_months = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"]
                try:
                    ay_upper = ay_ismi.replace("i", "İ").replace("ı", "I").upper()
                    idx = tr_months.index(ay_upper)
                    ay_val = str(idx + 1).zfill(2)
                except:
                    ay_val = "01"

            # Bitiş Ayı Değeri
            ay_bit_val = ay_val # Varsayılan: Başlangıç ayı ile aynı
            if ay_bit_ismi and n_ay_bit:
                ay_sel = soup.find("select", {"name": n_ay_bit}) or soup.find("select", {"name": n_ay})
                if ay_sel:
                    ay_bit_upper = ay_bit_ismi.replace("i", "İ").replace("ı", "I").upper()
                    opt = ay_sel.find("option", string=lambda t: t and ay_bit_upper in t.replace("i", "İ").replace("ı", "I").upper())
                    if opt: ay_bit_val = opt["value"]
            
            yil_bit_val = str(yil_bit) if yil_bit else str(yil)

            # Filtre (ddTur) Value Kontrolü (500 gönderildi ama sayfada yoksa)
            if n_tur and filtre_id == "500":
                tur_sel = soup.find("select", {"name": n_tur})
                if tur_sel:
                    if not tur_sel.find("option", value="500"):
                        # 500 yok, "Tüm" veya "Hepsi" ara
                        opt = tur_sel.find("option", string=lambda t: t and ("Tüm" in t or "Hepsi" in t or "All" in t))
                        if opt: filtre_id = opt["value"]

            # 4. Payload'ı Doldur
            if n_gun: payload[n_gun] = gun_val
            if n_ay: payload[n_ay] = ay_val
            if n_yil: payload[n_yil] = str(yil)
            if n_gun_bit: payload[n_gun_bit] = gun_bit_val
            if n_ay_bit: payload[n_ay_bit] = ay_bit_val
            if n_yil_bit: payload[n_yil_bit] = yil_bit_val
            if n_tur: payload[n_tur] = filtre_id
            
            # İstasyon ID'sini zorla (Default.aspx için kritik)
            if n_ist:
                # İstasyon ID'sini akıllı bul (Value vs Text eşleşmesi)
                val_to_use = self.station_id
                ist_sel = soup.find("select", {"name": n_ist})
                
                is_valid_option = False
                if ist_sel:
                    if not ist_sel.find("option", value=self.station_id):
                        # Value olarak yoksa text içinde ara (örn: "17060 - ISTANBUL")
                        opt = ist_sel.find("option", string=lambda t: t and self.station_id in t)
                        if opt: 
                            val_to_use = opt["value"]
                            is_valid_option = True
                        else:
                            # Hiçbiri yoksa, belki sadece ID ile başlıyordur
                            opt = ist_sel.find("option", string=lambda t: t and t.strip().startswith(self.station_id))
                            if opt: 
                                val_to_use = opt["value"]
                                is_valid_option = True
                    else:
                        is_valid_option = True

                # Sadece geçerli bir seçenekse gönder, yoksa URL/Session'a güven
                if is_valid_option:
                    payload[n_ist] = val_to_use
            elif "Default.aspx" in self.base_url:
                # Eğer input bulunamadıysa manuel ekle (Genel Bülten sayfası için)
                payload["ctl00$cBody$ddIst"] = self.station_id

            payload[n_btn] = btn_val
            payload["__EVENTTARGET"] = ""
            payload["__EVENTARGUMENT"] = ""

            r2 = self.session.post(self.base_url, data=payload, timeout=15)
            final_soup = BeautifulSoup(r2.text, "html.parser")
            
            # Tabloyu daha spesifik bulmaya çalış (grdLog genellikle veri tablosudur)
            target_table = final_soup.find("table", {"id": lambda x: x and ("grdLog" in x or "Grid" in x)})
            if target_table:
                rows = target_table.find_all("tr")
            else:
                rows = final_soup.find_all("tr")
                
            data = []

            for row in rows:
                cells = row.find_all("td")
                if not cells: continue
                vals = [c.get_text(" ", strip=True) for c in cells]

                turu = ""
                bulten = ""
                kull = "-"
                gond = "-"
                kayit = "-"
                rasat = "-"

                if len(vals) >= 6:
                    turu = vals[0]
                    bulten = " ".join(vals[-1].split())
                    try:
                        kull, gond, kayit, rasat = vals[1], vals[2], vals[3], vals[4]
                    except:
                        pass
                elif len(vals) >= 3:
                    # Yedek Mekanizma: Tablo yapısı farklıysa (örn. Default.aspx)
                    turu = vals[0]
                    bulten = " ".join(vals[-1].split())
                    # Tarih formatını (DD.MM.YYYY HH:MM) içeren sütunu bul
                    for v in vals[1:-1]:
                        if re.search(r'\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}', v):
                            rasat = v
                            kayit = v
                            break
                else:
                    continue

                turu_upper = turu.upper()
                bulten_upper = bulten.upper()
                
                is_valid = False
                valid_keywords = ["METAR", "TAF", "SPECI", "SYNOP", "SINOPTIK", "SİNOPTİK", "KLİMA", "KLIMA", "MAX", "MAKSİMUM", "HADİSE", "HADISE", "AMD", "COR", "AAA", "AAB", "AAC", "CCA", "CCB", "CCC", "SİLME", "SILME"]
                
                if any(k in turu_upper for k in valid_keywords):
                    is_valid = True
                elif "TAF" in bulten_upper[:30] or re.match(r'^(FC|FT)[A-Z0-9]{2}\b', bulten_upper):
                    if not turu: turu = "TAF"
                    is_valid = True
                elif "METAR" in bulten_upper[:30] or "SPECI" in bulten_upper[:30] or re.match(r'^(SA|SP)[A-Z0-9]{2}\b', bulten_upper):
                    if not turu: turu = "METAR"
                    is_valid = True
                elif "AAXX" in bulten_upper[:30] or re.match(r'^SM[A-Z0-9]{2}\b', bulten_upper):
                    if not turu: turu = "SİNOPTİK"
                    is_valid = True
                    
                if is_valid:
                    data.append((turu, kull, gond, kayit, rasat, bulten))
            
            if not data:
                # Sadece gerçekten hata varsa logla, "Kayıt bulunamadı" normal bir durumdur.
                if "Kayıt bulunamadı" not in r2.text and "No records" not in r2.text:
                    pass

            return data
        except requests.exceptions.Timeout:
            raise Exception("Sunucu yanıt vermedi (Zaman Aşımı). Lütfen internet bağlantınızı kontrol edin.")
        except requests.exceptions.ConnectionError:
            raise Exception("Sunucuya bağlanılamadı. İnternet bağlantınızı kontrol edin.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Beklenmeyen bağlantı hatası: {e}")
        except Exception as e:
            raise