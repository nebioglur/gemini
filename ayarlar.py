# -*- coding: utf-8 -*-

STATION = "LTAN"
WMO_ID = "17244"

# Türkiye Geneli İstasyon Listesi (Koordinatlı)
# A'dan Z'ye Sıralı (ICAO/WMO Koduna Göre)
TURKEY_STATIONS = {
    "17020": {"lat": 41.45, "lon": 31.79, "name": "ZONGULDAK", "type": "SİNOPTİK"},
    "17024": {"lat": 41.97, "lon": 33.76, "name": "İNEBOLU", "type": "SİNOPTİK"},
    "17045": {"lat": 41.18, "lon": 41.82, "name": "ARTVİN", "type": "SİNOPTİK"},
    "17050": {"lat": 41.67, "lon": 26.55, "name": "EDİRNE", "type": "SİNOPTİK"},
    "17052": {"lat": 41.73, "lon": 27.22, "name": "KIRKLARELİ", "type": "SİNOPTİK"},
    "17070": {"lat": 40.73, "lon": 31.60, "name": "BOLU", "type": "SİNOPTİK"},
    "17072": {"lat": 40.60, "lon": 33.61, "name": "ÇANKIRI", "type": "SİNOPTİK"},
    "17076": {"lat": 40.55, "lon": 34.95, "name": "ÇORUM", "type": "SİNOPTİK"},
    "17082": {"lat": 41.11, "lon": 42.70, "name": "ARDAHAN", "type": "SİNOPTİK"},
    "17084": {"lat": 40.91, "lon": 38.38, "name": "GİRESUN", "type": "SİNOPTİK"},
    "17086": {"lat": 40.46, "lon": 39.47, "name": "GÜMÜŞHANE", "type": "SİNOPTİK"},
    "17088": {"lat": 40.25, "lon": 40.22, "name": "BAYBURT", "type": "SİNOPTİK"},
    "17115": {"lat": 40.65, "lon": 29.27, "name": "YALOVA", "type": "SİNOPTİK"},
    "17120": {"lat": 40.14, "lon": 29.97, "name": "BİLECİK", "type": "SİNOPTİK"},
    "17130": {"lat": 39.84, "lon": 33.51, "name": "KIRIKKALE", "type": "SİNOPTİK"},
    "17135": {"lat": 39.82, "lon": 34.80, "name": "YOZGAT", "type": "SİNOPTİK"},
    "17155": {"lat": 39.41, "lon": 29.98, "name": "KÜTAHYA", "type": "SİNOPTİK"},
    "17160": {"lat": 39.14, "lon": 34.16, "name": "KIRŞEHİR", "type": "SİNOPTİK"},
    "17175": {"lat": 38.40, "lon": 42.10, "name": "BİTLİS", "type": "SİNOPTİK"},
    "17195": {"lat": 38.73, "lon": 35.48, "name": "KAYSERİ BÖLGE", "type": "SİNOPTİK"},
    "17203": {"lat": 39.10, "lon": 39.54, "name": "TUNCELİ", "type": "SİNOPTİK"},
    "17210": {"lat": 37.57, "lon": 43.73, "name": "HAKKARİ", "type": "SİNOPTİK"},
    "17246": {"lat": 38.36, "lon": 34.03, "name": "AKSARAY", "type": "SİNOPTİK"},
    "17248": {"lat": 37.96, "lon": 34.67, "name": "NİĞDE", "type": "SİNOPTİK"},
    "17265": {"lat": 36.71, "lon": 37.11, "name": "KİLİS", "type": "SİNOPTİK"},
    "17310": {"lat": 36.81, "lon": 34.64, "name": "MERSİN", "type": "SİNOPTİK"},
    "17320": {"lat": 37.17, "lon": 33.21, "name": "KARAMAN", "type": "SİNOPTİK"},
    "17360": {"lat": 37.07, "lon": 36.24, "name": "OSMANİYE", "type": "SİNOPTİK"},
    "17375": {"lat": 36.58, "lon": 36.17, "name": "İSKENDERUN", "type": "SİNOPTİK"},
    "LTAA": {"lat": 39.94, "lon": 32.68, "name": "ANKARA GÜVERCİNLİK", "type": "MEYDAN"}, # LTAA Etimesgut değil Güvercinlik/Etimesgut karışıklığı düzeltildi
    "LTAC": {"lat": 40.12, "lon": 32.99, "name": "ANKARA ESENBOĞA", "type": "MEYDAN"},
    "LTAD": {"lat": 39.93, "lon": 32.74, "name": "ANKARA ETİMESGUT", "type": "MEYDAN"},
    "LTAE": {"lat": 40.07, "lon": 32.57, "name": "ANKARA MÜRTED", "type": "MEYDAN"},
    "LTAF": {"lat": 36.98, "lon": 35.28, "name": "ADANA ŞAKİRPAŞA", "type": "MEYDAN"},
    "LTAG": {"lat": 37.00, "lon": 35.42, "name": "ADANA İNCİRLİK", "type": "MEYDAN"},
    "LTAH": {"lat": 38.72, "lon": 30.60, "name": "AFYON", "type": "MEYDAN"},
    "LTAI": {"lat": 36.90, "lon": 30.80, "name": "ANTALYA", "type": "MEYDAN"},
    "LTAJ": {"lat": 36.94, "lon": 37.47, "name": "GAZİANTEP", "type": "MEYDAN"},
    "LTAL": {"lat": 41.31, "lon": 33.79, "name": "KASTAMONU", "type": "MEYDAN"},
    "LTAN": {"lat": 37.97, "lon": 32.56, "name": "KONYA", "type": "MEYDAN"},
    "LTAP": {"lat": 40.82, "lon": 35.52, "name": "AMASYA MERZİFON", "type": "MEYDAN"},
    "LTAR": {"lat": 39.81, "lon": 36.90, "name": "SİVAS NURİ DEMİRAĞ", "type": "MEYDAN"},
    "LTAT": {"lat": 38.43, "lon": 38.09, "name": "MALATYA", "type": "MEYDAN"},
    "LTAU": {"lat": 38.77, "lon": 35.48, "name": "KAYSERİ ERKİLET", "type": "MEYDAN"},
    "LTAW": {"lat": 40.30, "lon": 36.37, "name": "TOKAT", "type": "MEYDAN"},
    "LTAY": {"lat": 37.78, "lon": 29.70, "name": "DENİZLİ ÇARDAK", "type": "MEYDAN"},
    "LTAZ": {"lat": 38.77, "lon": 34.53, "name": "NEVŞEHİR KAPADOKYA", "type": "MEYDAN"},
    "LTBA": {"lat": 40.97, "lon": 28.81, "name": "İSTANBUL ATATÜRK", "type": "MEYDAN"},
    "LTBD": {"lat": 37.81, "lon": 27.89, "name": "AYDIN ÇILDIR", "type": "MEYDAN"},
    "LTBF": {"lat": 39.61, "lon": 27.92, "name": "BALIKESİR", "type": "MEYDAN"},
    "LTBG": {"lat": 40.31, "lon": 27.97, "name": "BANDIRMA", "type": "MEYDAN"},
    "LTBH": {"lat": 40.13, "lon": 26.42, "name": "ÇANAKKALE", "type": "MEYDAN"},
    "LTBI": {"lat": 39.78, "lon": 30.58, "name": "ESKİŞEHİR", "type": "MEYDAN"},
    "LTBJ": {"lat": 38.29, "lon": 27.15, "name": "İZMİR ADNAN MENDERES", "type": "MEYDAN"},
    "LTBK": {"lat": 38.31, "lon": 27.16, "name": "GAZİEMİR", "type": "MEYDAN"},
    "LTBL": {"lat": 38.51, "lon": 27.01, "name": "ÇİĞLİ", "type": "MEYDAN"},
    "LTBO": {"lat": 38.68, "lon": 29.47, "name": "UŞAK", "type": "MEYDAN"},
    "LTBQ": {"lat": 40.73, "lon": 30.08, "name": "KOCAELİ CENGİZ TOPEL", "type": "MEYDAN"},
    "LTBR": {"lat": 40.25, "lon": 29.56, "name": "BURSA YENİŞEHİR", "type": "MEYDAN"},
    "LTBS": {"lat": 36.71, "lon": 28.79, "name": "MUĞLA DALAMAN", "type": "MEYDAN"},
    "LTBU": {"lat": 41.13, "lon": 27.91, "name": "TEKİRDAĞ ÇORLU", "type": "MEYDAN"},
    "LTBV": {"lat": 37.14, "lon": 27.68, "name": "BODRUM IMSIK", "type": "MEYDAN"},
    "LTBW": {"lat": 41.10, "lon": 28.15, "name": "HEZARFEN", "type": "MEYDAN"},
    "LTBX": {"lat": 40.98, "lon": 29.21, "name": "İSTANBUL SAMANDIRA", "type": "MEYDAN"},
    "LCEN": {"lat": 35.16, "lon": 33.50, "name": "LEFKOŞA / ERCAN", "type": "MEYDAN"},
    "LTBY": {"lat": 39.78, "lon": 30.52, "name": "ESKİŞEHİR HASAN POLATKAN", "type": "MEYDAN"},
    "LTBZ": {"lat": 39.11, "lon": 30.13, "name": "KÜTAHYA ZAFER", "type": "MEYDAN"},
    "LTCA": {"lat": 38.60, "lon": 39.28, "name": "ELAZIĞ", "type": "MEYDAN"},
    "LTCB": {"lat": 40.96, "lon": 38.08, "name": "ORDU GİRESUN", "type": "MEYDAN"},
    "LTCC": {"lat": 37.89, "lon": 40.20, "name": "DİYARBAKIR", "type": "MEYDAN"},
    "LTCD": {"lat": 39.70, "lon": 39.52, "name": "ERZİNCAN", "type": "MEYDAN"},
    "LTCE": {"lat": 39.95, "lon": 41.17, "name": "ERZURUM", "type": "MEYDAN"},
    "LTCF": {"lat": 40.56, "lon": 43.11, "name": "KARS HARAKANİ", "type": "MEYDAN"},
    "LTCG": {"lat": 40.99, "lon": 39.78, "name": "TRABZON", "type": "MEYDAN"},
    "LTCI": {"lat": 38.46, "lon": 43.33, "name": "VAN FERİT MELEN", "type": "MEYDAN"},
    "LTCJ": {"lat": 37.92, "lon": 41.11, "name": "BATMAN", "type": "MEYDAN"},
    "LTCK": {"lat": 38.74, "lon": 41.66, "name": "MUŞ SULTAN ALPARSLAN", "type": "MEYDAN"},
    "LTCL": {"lat": 37.97, "lon": 41.83, "name": "SİİRT", "type": "MEYDAN"},
    "LTCM": {"lat": 42.01, "lon": 35.06, "name": "SİNOP", "type": "MEYDAN"},
    "LTCN": {"lat": 37.53, "lon": 36.95, "name": "KAHRAMANMARAŞ", "type": "MEYDAN"},
    "LTCO": {"lat": 39.65, "lon": 43.02, "name": "AĞRI AHMED-İ HANİ", "type": "MEYDAN"},
    "LTCP": {"lat": 37.73, "lon": 38.46, "name": "ADIYAMAN", "type": "MEYDAN"},
    "LTCR": {"lat": 37.22, "lon": 40.63, "name": "MARDİN", "type": "MEYDAN"},
    "LTCS": {"lat": 37.45, "lon": 38.90, "name": "ŞANLIURFA GAP", "type": "MEYDAN"},
    "LTCT": {"lat": 39.97, "lon": 43.89, "name": "IĞDIR", "type": "MEYDAN"},
    "LTCU": {"lat": 38.86, "lon": 40.59, "name": "BİNGÖL", "type": "MEYDAN"},
    "LTCV": {"lat": 37.36, "lon": 42.05, "name": "ŞIRNAK ŞERAFETTİN ELÇİ", "type": "MEYDAN"},
    "LTCW": {"lat": 37.55, "lon": 44.23, "name": "HAKKARİ YÜKSEKOVA", "type": "MEYDAN"},
    "LTDA": {"lat": 36.36, "lon": 36.28, "name": "HATAY", "type": "MEYDAN"},
    "LTDB": {"lat": 36.89, "lon": 35.06, "name": "ÇUKUROVA ULUSLARARASI", "type": "MEYDAN"},
    "LTFB": {"lat": 37.95, "lon": 27.33, "name": "SELÇUK EFES", "type": "MEYDAN"},
    "LTFC": {"lat": 37.85, "lon": 30.36, "name": "ISPARTA SÜLEYMAN DEMİREL", "type": "MEYDAN"},
    "LTFD": {"lat": 39.55, "lon": 27.01, "name": "BALIKESİR KOCA SEYİT", "type": "MEYDAN"},
    "LTFE": {"lat": 37.25, "lon": 27.66, "name": "MUĞLA MİLAS-BODRUM", "type": "MEYDAN"},
    "LTFG": {"lat": 36.29, "lon": 32.30, "name": "GAZİPAŞA ALANYA", "type": "MEYDAN"},
    "LTFH": {"lat": 41.25, "lon": 36.55, "name": "SAMSUN ÇARŞAMBA", "type": "MEYDAN"},
    "LTFJ": {"lat": 40.89, "lon": 29.30, "name": "SABİHA GÖKÇEN", "type": "MEYDAN"},
    "LTFK": {"lat": 40.20, "lon": 25.88, "name": "GÖKÇEADA", "type": "MEYDAN"},
    "LTFM": {"lat": 41.26, "lon": 28.74, "name": "İSTANBUL HAVALİMANI", "type": "MEYDAN"},
    "LTFO": {"lat": 41.17, "lon": 40.83, "name": "RİZE ARTVİN", "type": "MEYDAN"},
    "LTFP": {"lat": 41.50, "lon": 32.08, "name": "ZONGULDAK ÇAYCUMA", "type": "MEYDAN"},
}

# Türkiye Sınırları (Detaylı Poligon - Base Map)
TURKEY_BORDER = [
    # Trakya (Bulgaristan - Yunanistan) - Gökçeada'yı kapsayacak şekilde genişletildi
    (26.04, 42.00), (26.35, 41.70), (26.60, 41.00), (26.10, 40.60), (25.60, 40.30),
    # Ege Kıyıları
    (26.00, 40.00), (25.90, 39.50), (26.30, 38.50), (27.00, 37.80), (27.20, 37.00),
    (27.30, 36.70), (28.00, 36.70),
    # Akdeniz
    (29.00, 36.20), (30.50, 36.10), (32.50, 36.00), (34.00, 36.10),
    (35.50, 36.60), (35.80, 36.00), (36.00, 35.80), (36.40, 35.80), (36.70, 36.20), # Hatay
    (36.50, 36.80),
    # Güneydoğu (Suriye - Irak)
    (38.00, 36.70), (40.00, 37.00), (42.00, 37.10), (42.36, 37.10),
    (43.00, 37.10), (44.30, 37.00), (44.80, 37.20),
    # Doğu (İran - Nahçıvan - Ermenistan)
    (44.80, 38.50), (44.50, 39.50), (44.80, 39.70), (44.60, 40.00), (43.50, 41.00),
    # Kuzeydoğu (Gürcistan)
    (42.50, 41.50),
    # Karadeniz
    (41.50, 41.50), (39.50, 41.10), (37.00, 41.40), (35.00, 42.10),
    (32.00, 41.90), (30.50, 41.30), (29.10, 41.30), (28.00, 41.60),
    # Trakya Dönüş
    (26.04, 42.00)
]

# Bölgesel Harita Koordinatları (Yaklaşık Sınırlar)
TURKEY_REGIONS = {
    "MARMARA": [
        (26.04, 42.00), (26.35, 41.70), (26.60, 41.00), (26.10, 40.60), (25.60, 40.30),
        (26.00, 40.00), (26.50, 39.50), (28.00, 39.50), (29.50, 40.00), (30.50, 40.50),
        (31.00, 41.00), (30.00, 41.50), (28.00, 41.60)
    ],
    "EGE": [
        (26.50, 39.50), (26.30, 38.50), (27.00, 37.80), (27.20, 37.00), (27.30, 36.70),
        (28.00, 36.70), (29.00, 37.00), (29.50, 38.00), (29.50, 39.00), (28.00, 39.50)
    ],
    "AKDENİZ": [
        (29.00, 37.00), (29.00, 36.20), (30.50, 36.10), (32.50, 36.00), (34.00, 36.10),
        (35.50, 36.60), (35.80, 36.00), (36.00, 35.80), (36.40, 35.80), (36.70, 36.20),
        (36.50, 36.80), (36.50, 37.50), (35.00, 37.80), (33.00, 37.50), (31.00, 37.50),
        (30.00, 37.20)
    ],
    "İÇ ANADOLU": [
        (30.50, 40.50), (29.50, 39.00), (29.50, 38.00), (30.00, 37.20), (31.00, 37.50),
        (33.00, 37.50), (35.00, 37.80), (36.50, 37.50), (37.00, 38.50), (37.00, 39.50),
        (36.00, 40.50), (34.00, 40.50), (32.00, 40.50)
    ],
    "KARADENİZ": [
        (31.00, 41.00), (32.00, 40.50), (34.00, 40.50), (36.00, 40.50), (38.00, 40.00),
        (40.00, 40.00), (41.50, 40.50), (42.50, 41.50), (41.50, 41.50), (39.50, 41.10),
        (37.00, 41.40), (35.00, 42.10), (32.00, 41.90), (30.50, 41.30), (29.10, 41.30),
        (28.00, 41.60), (30.00, 41.50)
    ],
    "DOĞU ANADOLU": [
        (38.00, 40.00), (37.00, 39.50), (37.00, 38.50), (38.00, 38.00), (39.00, 38.00),
        (40.00, 38.00), (41.00, 38.00), (42.00, 38.00), (43.00, 37.50), (44.30, 37.00),
        (44.80, 37.20), (44.80, 38.50), (44.50, 39.50), (44.80, 39.70), (44.60, 40.00),
        (43.50, 41.00), (42.50, 41.50), (41.50, 40.50), (40.00, 40.00)
    ],
    "GÜNEYDOĞU": [
        (36.50, 37.50), (36.50, 36.80), (38.00, 36.70), (40.00, 37.00), (42.00, 37.10),
        (42.36, 37.10), (43.00, 37.10), (43.00, 37.50), (42.00, 38.00), (41.00, 38.00),
        (40.00, 38.00), (39.00, 38.00), (38.00, 38.00), (37.00, 38.50)
    ]
}

# ICAO -> WMO Eşleşmesi (Kardelen ve Ogimet için)
ICAO_TO_WMO = {
    "17020": "17020", "17024": "17024", "17045": "17045", "17050": "17050",
    "17052": "17052", "17070": "17070", "17072": "17072", "17076": "17076",
    "17082": "17082", "17084": "17084", "17086": "17086", "17088": "17088",
    "17115": "17115", "17120": "17120", "17130": "17130", "17135": "17135",
    "17155": "17155", "17160": "17160", "17175": "17175", "17195": "17195",
    "17203": "17203", "17210": "17210", "17246": "17246", "17248": "17248",
    "17265": "17265", "17310": "17310", "17320": "17320", "17360": "17360",
    "17375": "17375",
    "LTAA": "17126", "LTAC": "17128", "LTAD": "17129", "LTAE": "17127",
    "LTAF": "17352", "LTAG": "17350", "LTAH": "17189", "LTAI": "17300",
    "LTAJ": "17260", "LTAL": "17783", "LTAN": "17244", "LTAP": "17082",
    "LTAR": "17091", "LTAT": "17200", "LTAU": "17195", "LTAW": "17087",
    "LTAY": "17257", "LTAZ": "17194", "LTBA": "17060", "LTBD": "17227",
    "LCEN": "17606",
    "LTBF": "17150", "LTBG": "17115", "LTBH": "17113", "LTBI": "17124",
    "LTBJ": "17219", "LTBK": "17821", "LTBL": "17218", "LTBO": "17185",
    "LTBQ": "17068", "LTBR": "17118", "LTBS": "17295", "LTBU": "17051",
    "LTBV": "17293", "LTBW": "17060", "LTBX": "17065", "LTBY": "17123",
    "LTBZ": "17154", "LTCA": "17202", "LTCB": "17616", "LTCC": "17280",
    "LTCD": "17092", "LTCE": "17096", "LTCF": "17098", "LTCG": "17038",
    "LTCI": "17170", "LTCJ": "17284", "LTCK": "17206", "LTCL": "17209",
    "LTCM": "17028", "LTCN": "17256", "LTCO": "17104", "LTCP": "17266",
    "LTCR": "17276", "LTCS": "17271", "LTCT": "17763", "LTCU": "17779",
    "LTCV": "17949", "LTCW": "17815", "LTDA": "17371", "LTDB": "17345",
    "LTFB": "17226", "LTFC": "17241", "LTFD": "17143", "LTFE": "17291",
    "LTFG": "17975", "LTFH": "17031", "LTFJ": "17063", "LTFK": "17109",
    "LTFM": "17058", "LTFO": "17044", "LTFP": "17023"
}