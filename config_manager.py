# -*- coding: utf-8 -*-
try:
    import yaml
    HAS_YAML = True
except ImportError:
    import json
    HAS_YAML = False

import os
import sys
import logging
import shutil

# EXE çalışıyorsa exe'nin olduğu klasörü, değilse dosyanın olduğu klasörü al
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Öncelik: EXE'nin yanındaki dosya (Taşınabilir Mod)
CONFIG_FILE = os.path.join(APP_DIR, "kardelen_ayarlar.yaml")
CONFIG_FILE_OLD = os.path.join(APP_DIR, "kardelen_ayarlar.json")

# 2. Yedek: Kullanıcı Klasörü (Eğer EXE klasörüne yazma izni yoksa veya eski ayarlar oradaysa)
def _get_safe_user_dir():
    for p in [os.environ.get("USERPROFILE"), os.path.expanduser("~"), os.environ.get("PUBLIC")]:
        if p and os.path.exists(p):
            return p
    return APP_DIR

USER_DATA_DIR = os.path.join(_get_safe_user_dir(), "KardelenLogs")
USER_CONFIG_FILE = os.path.join(USER_DATA_DIR, "kardelen_ayarlar.yaml")
USER_CONFIG_FILE_OLD = os.path.join(USER_DATA_DIR, "kardelen_ayarlar.json")

def load_config():
    """Uygulama ayarlarını yükler."""
    # 1. ÖNCELİK: Kullanıcı Klasörü (Exe güncellense bile ayarların kaybolmaması için ana merkez burasıdır)
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                if HAS_YAML: return yaml.safe_load(f) or {}
                else: return json.load(f) or {}
        except Exception as e:
            logging.error(f"Bozuk ayar dosyası (USER_CONFIG). Yedekleniyor... Hata: {e}")
            try: shutil.copy(USER_CONFIG_FILE, USER_CONFIG_FILE + ".bozuk")
            except: pass
            
    # ESKİ SÜRÜMDEN GEÇİŞ (JSON -> YAML OTOMATİK DÖNÜŞÜM)
    elif os.path.exists(USER_CONFIG_FILE_OLD):
        try:
            with open(USER_CONFIG_FILE_OLD, 'r', encoding='utf-8') as f:
                old_config = json.load(f) or {}
            save_config(old_config) # Yeni formata (YAML) dönüştürüp kaydet
            return old_config
        except Exception as e:
            logging.error(f"Eski JSON ayar dosyası (USER_CONFIG) okunamadı. Hata: {e}")

    # 2. Yedek: EXE yanına bak (Taşınabilir mod veya ilk kurulum)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                if HAS_YAML: return yaml.safe_load(f) or {}
                else: return json.load(f) or {}
        except Exception as e:
            logging.error(f"Bozuk ayar dosyası (CONFIG_FILE). Yedekleniyor... Hata: {e}")
            try: shutil.copy(CONFIG_FILE, CONFIG_FILE + ".bozuk")
            except: pass
            
    elif os.path.exists(CONFIG_FILE_OLD):
        try:
            with open(CONFIG_FILE_OLD, 'r', encoding='utf-8') as f:
                old_config = json.load(f) or {}
            save_config(old_config) # Yeni formata (YAML) dönüştürüp kaydet
            return old_config
        except Exception as e:
            logging.error(f"Eski JSON ayar dosyası (CONFIG_FILE) okunamadı. Hata: {e}")

    # 3. Yoksa EXE içine gömülü ayarlara bak (Varsayılanlar)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundled_config = os.path.join(sys._MEIPASS, "kardelen_ayarlar.yaml")
        if os.path.exists(bundled_config):
            try:
                with open(bundled_config, 'r', encoding='utf-8') as f:
                    if HAS_YAML: return yaml.safe_load(f) or {}
                    else: return json.load(f) or {}
            except: pass
        
    return {}

def save_config(data):
    """Mevcut ayarları kaydeder."""
    try:
        # 1. ÖNCELİK: Kullanıcı Klasörüne yaz (Ayarların kalıcı olması için)
        if not os.path.exists(USER_DATA_DIR):
            os.makedirs(USER_DATA_DIR)
        with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
            if HAS_YAML:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            else:
                json.dump(data, f, indent=4, ensure_ascii=False)
    except: pass

    try:
        # 2. Opsiyonel: EXE yanına da yaz (Taşınabilir mod kullanımları için)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            if HAS_YAML:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            else:
                json.dump(data, f, indent=4, ensure_ascii=False)
    except: pass