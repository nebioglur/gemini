# -*- coding: utf-8 -*-
import requests
import pandas as pd
import io
import re
import logging
from synop_decoder import SynopDecoder

def get_bulk_weather_data(hours=12):
    """METCAP.py mantığıyla toplu veri çeker (API + CSV Fallback)."""
    bbox = "25,34,46,43" # Türkiye Kapsamı
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    # 1. METAR ÇEKİMİ
    metar_list = []
    try:
        url = f"https://aviationweather.gov/api/data/metar?format=json&hours={hours}&bbox={bbox}"
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            metar_list = r.json()
    except Exception as e:
        logging.error(f"METAR API Hatası: {e}")

    # METAR Fallback (CSV)
    if not metar_list or len(metar_list) < 30:
        logging.warning("API verisi yetersiz, yedek kaynak (CSV Cache) devreye giriyor...")
        try:
            csv_url = "https://aviationweather.gov/data/cache/metars.cache.csv"
            r = requests.get(csv_url, headers=headers, timeout=30)
            if r.status_code == 200:
                csv_text = r.text
                skip_rows = 5
                # Başlık satırını dinamik olarak bul
                for i, line in enumerate(csv_text.splitlines()[:30]):
                    if "raw_text" in line and "station_id" in line:
                        skip_rows = i
                        break
                        
                df = pd.read_csv(io.StringIO(csv_text), skiprows=skip_rows)
                # Sütun adlarındaki gizli boşlukları temizle
                df.columns = [c.strip() for c in df.columns]
                
                if 'latitude' in df.columns and 'longitude' in df.columns:
                    # Türkiye Filtresi
                    df = df[(df['latitude'] >= 34) & (df['latitude'] <= 43) & (df['longitude'] >= 25) & (df['longitude'] <= 46)]
                    for _, row in df.iterrows():
                        metar_list.append({
                            'icaoId': row.get('station_id'),
                            'reportTime': row.get('observation_time'),
                            'rawOb': row.get('raw_text')
                        })
        except Exception as e:
            logging.error(f"METAR CSV Hatası: {e}")

    # 2. TAF ÇEKİMİ
    taf_list = []
    try:
        url = f"https://aviationweather.gov/api/data/taf?format=json&hours={hours}&bbox={bbox}"
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            taf_list = r.json()
    except Exception as e:
        logging.error(f"TAF API Hatası: {e}")
        
    # TAF Fallback (CSV)
    if not taf_list or len(taf_list) < 30:
        try:
            csv_url = "https://aviationweather.gov/data/cache/tafs.cache.csv"
            r = requests.get(csv_url, headers=headers, timeout=30)
            if r.status_code == 200:
                csv_text = r.text
                skip_rows = 5
                for i, line in enumerate(csv_text.splitlines()[:30]):
                    if "raw_text" in line and "station_id" in line:
                        skip_rows = i
                        break
                        
                df = pd.read_csv(io.StringIO(csv_text), skiprows=skip_rows)
                df.columns = [c.strip() for c in df.columns]
                
                if 'latitude' in df.columns and 'longitude' in df.columns:
                    df = df[(df['latitude'] >= 34) & (df['latitude'] <= 43) & (df['longitude'] >= 25) & (df['longitude'] <= 46)]
                    for _, row in df.iterrows():
                        taf_list.append({
                            'icaoId': row.get('station_id'),
                            'issueTime': row.get('issue_time'),
                            'rawTAF': row.get('raw_text')
                        })
        except: pass

    return metar_list, taf_list

def parse_synop_report(report_text):
    """Gelişmiş SİNOPTİK raporu ayrıştırıcı (SynopDecoder kullanarak)."""
    data = {'temp': None, 'pressure': None, 'weather_code': None, 'raw': report_text}
    try:
        decoder = SynopDecoder()
        decoded_data = decoder.decode_line(report_text)
        
        if decoded_data:
            # Harita sistemi (turkey_map.py) ile uyumluluğu korumak için ana değerleri ata
            if 'sicaklik' in decoded_data:
                data['temp'] = decoded_data['sicaklik']
            if 'deniz_basinci' in decoded_data:
                data['pressure'] = decoded_data['deniz_basinci']
            if 'halihazir_hava' in decoded_data:
                data['weather_code'] = decoded_data['halihazir_hava']
            
            # Geri kalan tüm detaylı veriyi de içine göm (ileride tooltip'lerde kullanmak için)
            data['parsed_details'] = decoded_data
    except:
        pass
    return data