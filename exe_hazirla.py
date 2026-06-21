import os
# Pygame selamlama mesajını gizle
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

import shutil
import sys
import zipfile 
import py_compile
import importlib.util
import time
from datetime import datetime

def create_executable():
    print("="*60)
    print("KARDELEN PROJESİ - EXE OLUŞTURMA SİHRİBAZI (GELİŞMİŞ)")
    print("="*60)

    # Scriptin bulunduğu dizini al ve çalışma dizini yap
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    print(f"📂 Çalışma Dizini: {base_dir}")

    # 0. ADIM: Tehlikeli Dosya İsimlerini Otomatik Onar
    bad_files = ["import re.py", "import folium.py", "import requests.py", "import pandas.py"]
    for bf in bad_files:
        if os.path.exists(bf):
            print(f"\n⚠️ KRİTİK UYARI: '{bf}' adında Python içe aktarma sistemiyle çakışan dosya tespit edildi!")
            safe_name = bf.replace(".py", "_yedek.txt")
            try:
                if os.path.exists(safe_name): os.remove(safe_name)
                os.rename(bf, safe_name)
                print(f"   ✅ Dosya derlemeyi bozmaması için otomatik olarak '{safe_name}' adına çevrildi.")
            except Exception as e:
                print(f"   ❌ Dosya adı değiştirilemedi: {e}\n   Lütfen '{bf}' dosyasını manuel olarak silin.")
                return

    # 1. ADIM: Kütüphane Kontrolü
    print("\n🔍 Kütüphane kontrolü yapılıyor...")
    # Import adı : Pip paket adı
    required_modules = {
        'geopandas': 'geopandas', 'matplotlib': 'matplotlib', 'pandas': 'pandas',
        'requests': 'requests', 'PIL': 'Pillow', 'openpyxl': 'openpyxl',
        'pytz': 'pytz', 'dateutil': 'python-dateutil',
        'webview': 'pywebview', 'tkintermapview': 'tkintermapview', 'pygame': 'pygame',
        'pyttsx3': 'pyttsx3', 'gtts': 'gTTS', 'edge_tts': 'edge-tts',
        'yaml': 'pyyaml', 'folium': 'folium', 'comtypes': 'comtypes',
        'PyInstaller': 'pyinstaller',
        'bs4': 'beautifulsoup4',
        'flask': 'flask',
        'lxml': 'lxml',
        'html5lib': 'html5lib',
        'babel': 'Babel',
        'websockets': 'websockets',
        'pyproj': 'pyproj',
        'pycparser': 'pycparser',
        'webdriver_manager': 'webdriver-manager'
    }
    missing_modules = []
    pip_install_list = []
    for mod, pip_name in required_modules.items():
        if not importlib.util.find_spec(mod):
            missing_modules.append(mod)
            pip_install_list.append(pip_name)
    
    if missing_modules:
        print(f"⚠️ EKSİK KÜTÜPHANELER: {', '.join(missing_modules)}")
        print("📥 Eksik paketler otomatik olarak yükleniyor, lütfen bekleyin...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--disable-pip-version-check"] + pip_install_list)
            print("✅ Eksik kütüphaneler başarıyla yüklendi!")
            time.sleep(1) # Yükleme sonrası dosya sisteminin senkronize olması için kısa bir bekleme
        except subprocess.CalledProcessError:
            print(f"❌ Otomatik yükleme başarısız oldu. Lütfen manuel yükleyin:\n   pip install {' '.join(pip_install_list)}")
            input("Devam etmek için Enter'a basın...")
    else:
        print("✅ Kritik kütüphaneler yüklü.")

    # 2. ADIM: Çalışan eski process varsa kapat
    print("\n🧹 Sistem temizleniyor...")
    os.system("taskkill /f /im KardelenAnaliz.exe >nul 2>&1")
    time.sleep(2) # Dosyaların serbest kalması için bekle

    # RecursionError hatasını önlemek için limit artırımı (Geopandas vb. ağır kütüphaneler için)
    sys.setrecursionlimit(10000)

    # --- AYARLAR ---
    exe_name = "KardelenAnaliz"
    icon_name = "logo.ico" # İkon dosyanızın adı
    
    main_script = "anakardelen (2).py" 

    # Dosya varlık kontrolü
    if not os.path.exists(main_script):
        print(f"❌ HATA: Ana dosya '{main_script}' bulunamadı!")
        input("Çıkmak için Enter'a basın...")
        return

    # --- SÖZDİZİMİ (SYNTAX) KONTROLÜ ---
    print("\n🔍 Projedeki tüm Python dosyaları sözdizimi (Syntax) için taranıyor...")
    files_to_check = [f for f in os.listdir(base_dir) if f.endswith('.py')]
    latest_good_dir = os.path.join(base_dir, "Source_Backups", "Latest_Good_Code")
    
    syntax_error_found = False
    checked_count = 0
    
    for f in sorted(files_to_check):
        if os.path.exists(f):
            checked_count += 1
            try:
                py_compile.compile(f, doraise=True)
            except py_compile.PyCompileError as e:
                print(f"\n❌ HATA: {f} dosyasında YAZIM HATASI (Syntax Error) var!")
                if hasattr(e, 'exc_value') and e.exc_value:
                    print(f"   -> Satır {getattr(e.exc_value, 'lineno', '?')}: {getattr(e.exc_value, 'msg', str(e)).strip()}")
                else:
                    print(f"   -> {str(e.msg).strip()}")
                
                # OTOMATİK ONARIM / YEDEKTEN GERİ YÜKLEME
                backup_file = os.path.join(latest_good_dir, f)
                if os.path.exists(backup_file):
                    print(f"   🔄 '{f}' için son çalışan yedek bulundu. Otomatik onarılıyor...")
                    try:
                        shutil.copy2(backup_file, os.path.join(base_dir, f))
                        py_compile.compile(f, doraise=True) # Yedeği doğrula
                        print(f"   ✅ '{f}' başarıyla yedekten onarıldı!")
                        continue # Hata çözüldü, sonraki dosyaya geç
                    except Exception as restore_err:
                        print(f"   ⚠️ Yedek dosya da hatalı veya geri yüklenemedi: {restore_err}")
                else:
                    print("   ⚠️ Bu dosya için geri yüklenecek bir yedek bulunamadı.")
                
                syntax_error_found = True
            except Exception as e:
                print(f"\n❌ BEKLENMEYEN HATA: {f}\n   -> {e}")
                syntax_error_found = True

    if syntax_error_found:
        print("-" * 60)
        print("⚠️ HATA: Yukarıda listelenen dosyalarda sözdizimi hatası bulundu!")
        print("Lütfen hataları düzeltip derlemeyi yeniden başlatın.")
        input("\nÇıkmak için Enter'a basın...")
        return
    else:
        print(f"✅ Kontrol tamamlandı. {checked_count} dosya incelendi ve hata bulunamadı.")

    # Çıktı Klasörleri (Kesin Yollar)
    dist_path = os.path.join(base_dir, "dist")
    build_path = os.path.join(base_dir, "build")

    # Önceki derleme artıklarını temizle
    def safe_cleanup(path):
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
            except OSError:
                print(f"⚠️ '{os.path.basename(path)}' silinirken beklendi, tekrar deneniyor...")
                time.sleep(2)
                try: shutil.rmtree(path, ignore_errors=True)
                except: pass

    safe_cleanup(build_path)
    safe_cleanup(dist_path)

    if os.path.exists(f"{exe_name}.spec"): os.remove(f"{exe_name}.spec")
    if os.path.exists("version_info.txt"): os.remove("version_info.txt")

    # --- ÖNBELLEK (CACHE) VE TEMP TEMİZLİĞİ ---
    print("🧹 Önbellek (Cache) ve geçici dosyalar temizleniyor...")
    for root_dir, dirs, files in os.walk(base_dir):
        for d in list(dirs): # list() ile kopyasını alıyoruz ki iterasyon bozulmasın
            if d in ['__pycache__', '.pytest_cache', '.mypy_cache']:
                safe_cleanup(os.path.join(root_dir, d))
                dirs.remove(d) # İçine girmesini engellemek için listeden çıkar
        for f in files:
            if f.endswith(('.pyc', '.pyo', '.pyd', '.tmp')):
                try: os.remove(os.path.join(root_dir, f))
                except: pass
                
    # --- GEREKSİZ/BOZUK VERİ DOSYALARINI TEMİZLE ---
    print("🧹 Proje dizinindeki gereksiz/bozuk (.xls, .xlsx, .csv, .html) dosyaları temizleniyor...")
    for f in os.listdir(base_dir):
        if f.lower().endswith(('.xls', '.xlsx', '.csv', '.html', '.htm')) and not f.startswith('DENETIM'):
            try: 
                os.remove(os.path.join(base_dir, f))
                print(f"   🗑️ Silindi: {f}")
            except: pass

    # Versiyon Dosyası Oluşturma
    version_file = os.path.join(base_dir, "version_info.txt")
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(f"""
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(3, 0, 0, 0),
    prodvers=(3, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'041f04b0',
        [StringStruct(u'CompanyName', u'Ramazan NEBİOĞLU'),
        StringStruct(u'FileDescription', u'Kardelen Analiz - Konya Meydan'),
        StringStruct(u'FileVersion', u'3.0.0.0'),
        StringStruct(u'InternalName', u'{exe_name}'),
        StringStruct(u'LegalCopyright', u'Telif Hakkı (c) 2024 Ramazan NEBİOĞLU'),
        StringStruct(u'OriginalFilename', u'{exe_name}.exe'),
        StringStruct(u'ProductName', u'{exe_name}'),
        StringStruct(u'ProductVersion', u'3.0.0.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1055, 1200])])
  ]
)
""")

    # Harita dosyası kontrolü
    map_file = "turkey_map_hd_v7.png"
    if not os.path.exists(map_file):
        print(f"UYARI: '{map_file}' bulunamadı. Otomatik oluşturuluyor...")
        try:
            import TR_harita
            TR_harita.generate_static_map(map_file)
        except: pass
        
    # --- AYARLARI EŞİTLE (EXE İÇİNE GÜNCEL AYARLARI GÖMMEK İÇİN) ---
    print("\n⚙️ Mevcut ayarlarınız EXE içine gömülmek üzere senkronize ediliyor...")
    safe_user_dir = next((p for p in [os.environ.get("USERPROFILE"), os.path.expanduser("~"), os.environ.get("PUBLIC")] if p and os.path.exists(p)), base_dir)
    user_logs_dir = os.path.join(safe_user_dir, "KardelenLogs")
    
    # 1. Ana Ayarlar (Şarta bağlı alarmlar, arayüz vs.)
    user_config = os.path.join(user_logs_dir, "kardelen_ayarlar.yaml")
    local_config = os.path.join(base_dir, "kardelen_ayarlar.yaml")
    if os.path.exists(user_config):
        shutil.copy(user_config, local_config)
        print("   ✅ kardelen_ayarlar.yaml EXE'ye gömülmek üzere güncellendi.")

    # 2. Robot/Analiz Eşikleri (robot_config.json)
    user_robot = os.path.join(user_logs_dir, "robot_config.json")
    local_robot = os.path.join(base_dir, "robot_config.json")
    if os.path.exists(user_robot):
        shutil.copy(user_robot, local_robot)
        print("   ✅ robot_config.json EXE'ye gömülmek üzere güncellendi.")

    # Dahil edilecek veri dosyaları
    datas = [
        f'{os.path.join(base_dir, "turkey_map_hd_v7.png")};.',
        f'{os.path.join(base_dir, "kurallar.yaml")};.',
        f'{os.path.join(base_dir, "anakardelen_config.json")};.',
        f'{os.path.join(base_dir, "kardelen_ayarlar.yaml")};.',
        f'{os.path.join(base_dir, "robot_config.json")};.',
        f'{os.path.join(base_dir, "logo.png")};.',
        f'{os.path.join(base_dir, icon_name)};.',
        f'{os.path.join(base_dir, "icons")};icons',
        f'{os.path.join(base_dir, "flightradar.py")};.',
        f'{os.path.join(base_dir, "arayuz.py")};.',
        f'{os.path.join(base_dir, "webview_harita_analiz.py")};.',
        f'{os.path.join(base_dir, "flask_app.py")};.',
        f'{os.path.join(base_dir, "templates")};templates',
        f'{os.path.join(base_dir, "sinoptik_METAR_ROTA.py")};.'
    ]
    
    valid_datas = [d for d in datas if os.path.exists(d.split(';')[0])]

    # İkon dosyası
    icon_path = os.path.join(base_dir, icon_name)
    
    # Splash Görseli (Açılış Hızını Göstermek İçin)
    splash_image = os.path.join(base_dir, "logo.png")
    
    # PyInstaller Komutları
    args = [
        main_script,
        f'--name={exe_name}',
        f'--version-file={version_file}',
        f'--distpath={dist_path}', # KESİN YOL
        f'--workpath={build_path}', # KESİN YOL
        f'--specpath={base_dir}',   # KESİN YOL
        '--onedir',    # Klasör modunda derler. Defender şüphesini ciddi oranda düşürür.
        '--windowed',
        '--clean',
        '--noconfirm',
        # '--uac-admin', # Antivirüs şüphesini azaltmak için kaldırıldı (anakardelen.py zaten UAC istiyor)
        '--hidden-import=babel.numbers',
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=openpyxl',
        '--hidden-import=requests',
        '--hidden-import=pyproj',
        '--hidden-import=pandas',
        '--hidden-import=geopandas',
        '--hidden-import=lxml',
        '--hidden-import=html5lib',
        '--hidden-import=shapely',
        '--hidden-import=matplotlib',
        '--hidden-import=pyttsx3.drivers',
        '--hidden-import=pyttsx3.drivers.sapi5',
        '--hidden-import=pygame',
        '--hidden-import=gtts',
        '--hidden-import=edge_tts',
        '--hidden-import=asyncio',
        '--hidden-import=aiohttp',
        '--hidden-import=websockets',
        '--hidden-import=yaml',
        '--hidden-import=folium',
        '--hidden-import=branca',
        '--hidden-import=jinja2',
        '--hidden-import=webview',
        '--hidden-import=tkintermapview',
        '--hidden-import=comtypes',
        '--hidden-import=turkey_map',
        '--hidden-import=TR_harita',
        '--hidden-import=gui_app',
        '--hidden-import=gui_app_1',
        '--hidden-import=gui_app_2',
        '--hidden-import=gui_app_3',
        '--hidden-import=gui_app_logging',
        '--hidden-import=gui_app_logs_viewer',
        '--hidden-import=gui_app_map',
        '--hidden-import=gui_analysis',
        '--hidden-import=gui_analysis_alarms',
        '--hidden-import=gui_settings',
        '--hidden-import=gui_utils',
        '--hidden-import=gui_station_selector',
        '--hidden-import=turkey_map_subwindows',
        '--hidden-import=synop_decoder',
        '--hidden-import=decoder_lookups',
        '--hidden-import=weather_data_utils',
        '--hidden-import=rasat_alarm',
        '--hidden-import=control_panel',
        '--hidden-import=log_processor',
        '--hidden-import=kardelen_scraper',
        '--hidden-import=TAF_METAR_TREND',
        '--hidden-import=ayarlar',
        '--hidden-import=file_ops',
        '--hidden-import=surface_map',
        '--hidden-import=flightradar',
        '--hidden-import=arayuz',
        '--hidden-import=webview_harita_analiz',
        '--hidden-import=flask_app',
        '--hidden-import=flask',
        '--hidden-import=sinoptik_METAR_ROTA',
        '--hidden-import=webdriver_manager',
        '--log-level=INFO',
        '--collect-all=pyproj',
        '--collect-all=babel',
        '--collect-all=geopandas',
        '--collect-all=folium',
        '--collect-all=branca',
        '--collect-all=tkintermapview',
        *[f'--add-data={d}' for d in valid_datas],
    ]

    if os.path.exists(icon_path):
        args.append(f'--icon={icon_path}')
        
    if os.path.exists(splash_image):
        args.append(f'--splash={splash_image}')

    print("\n🚀 Derleme işlemi başlıyor (Bu işlem biraz sürebilir)...")
    
    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(args)
    except SystemExit as e:
        if e.code != 0:
            print(f"\n❌ PyInstaller HATA ile durdu! (Çıkış Kodu: {e.code})")
    except Exception as e:
        print(f"\n❌ BEKLENMEYEN HATA: {e}")

    # --- DOSYA KONTROLÜ ---
    exe_full_path = os.path.join(dist_path, exe_name, f"{exe_name}.exe")
    zip_full_path = os.path.join(dist_path, f"{exe_name}.zip")

    # Geçici dosyayı temizle (İPTAL: Artık main_build.py ana dosyamız)
    # if os.path.exists(main_script): os.remove(main_script)

    if os.path.exists(exe_full_path):
        print("\n" + "="*60)
        print("✅ İŞLEM BAŞARILI!")
        print(f"Derlenen klasör yolu: {os.path.join(dist_path, exe_name)}")
        print("="*60)

        try:
            with zipfile.ZipFile(zip_full_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                target_dir = os.path.join(dist_path, exe_name)
                for root_dir, dirs, files in os.walk(target_dir):
                    for file in files:
                        f_path = os.path.join(root_dir, file)
                        arcname = os.path.relpath(f_path, dist_path)
                        zipf.write(f_path, arcname=arcname)
            print(f"✅ ZIP dosyası hazır: {zip_full_path}")
        except Exception as e:
            print(f"⚠️ ZIP dosyası oluşturulamadı: {e}")

        # --- KAYNAK KOD (SOURCE) YEDEKLEMESİ ---
        print("\n📦 Kaynak kodlar yedekleniyor...")
        backup_dir = os.path.join(base_dir, "Source_Backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        source_zip_path = os.path.join(backup_dir, f"Kardelen_Source_Backup_{timestamp}.zip")
        latest_good_dir = os.path.join(backup_dir, "Latest_Good_Code")
        os.makedirs(latest_good_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(source_zip_path, 'w', zipfile.ZIP_DEFLATED) as szip:
                for item in os.listdir(base_dir):
                    if item.endswith(('.py', '.json', '.yaml', '.ico', '.png', '.txt')) and item != main_script:
                        file_path = os.path.join(base_dir, item)
                        szip.write(file_path, arcname=item)
                        shutil.copy2(file_path, os.path.join(latest_good_dir, item)) # Son çalışan hali düz klasöre de kaydet
                
                # İkonlar klasörünü yedekle
                icons_dir = os.path.join(base_dir, "icons")
                if os.path.exists(icons_dir):
                    for root_d, _, files in os.walk(icons_dir):
                        for f in files:
                            f_path = os.path.join(root_d, f)
                            szip.write(f_path, arcname=os.path.relpath(f_path, base_dir))
                            lg_path = os.path.join(latest_good_dir, os.path.relpath(f_path, base_dir))
                            os.makedirs(os.path.dirname(lg_path), exist_ok=True)
                            shutil.copy2(f_path, lg_path)
            print(f"✅ Kaynak kod yedeği oluşturuldu: {source_zip_path}")
        except Exception as e:
            print(f"⚠️ Kaynak kod yedekleme hatası: {e}")

        # --- DERLEME SONRASI TEMİZLİK ---
        print("\n🧹 Derleme logları ve geçici dosyalar temizleniyor...")
        safe_cleanup(build_path)
        if os.path.exists(f"{exe_name}.spec"): os.remove(f"{exe_name}.spec")
        if os.path.exists("version_info.txt"): os.remove("version_info.txt")
        for f in os.listdir(base_dir):
            if (f.startswith("warn-") and f.endswith(".txt")) or (f.startswith("xref-") and f.endswith(".html")):
                try: os.remove(os.path.join(base_dir, f))
                except: pass

        try:
            print(f"🚀 {exe_name}.exe başlatılıyor...")
            os.startfile(exe_full_path)
        except: pass
    else:
        print("\n" + "="*60)
        print("❌ KRİTİK HATA: Derleme bitti görünüyor ama dosya yok!")
        
        if os.path.exists(dist_path):
            print(f"📂 'dist' klasörü içeriği: {os.listdir(dist_path)}")
        else:
            print("📂 'dist' klasörü hiç oluşmamış!")
            
        if os.path.exists(build_path):
            print("ℹ️ 'build' klasörü MEVCUT. Bu, derlemenin başladığını ama tamamlanamadığını gösterir.")
            print("   Olası Sebep: Geopandas veya Matplotlib gibi kütüphaneler paketlenirken hata oluştu.")
        else:
            print("ℹ️ 'build' klasörü de YOK. PyInstaller hiç başlayamamış.")
            
        print("="*60)

    print("\n📦 Inno Setup ile kurulum (Setup) dosyası oluşturuluyor...")
    inno_compiler = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if not os.path.exists(inno_compiler):
        inno_compiler_64 = r"C:\Program Files\Inno Setup 6\ISCC.exe"
        if os.path.exists(inno_compiler_64): inno_compiler = inno_compiler_64
    iss_file = os.path.join(base_dir, "KardelenSetup.iss")
    
    if os.path.exists(inno_compiler) and os.path.exists(iss_file):
        try:
            subprocess.check_call([inno_compiler, iss_file])
            print(f"✅ Setup dosyası başarıyla oluşturuldu: {os.path.join(dist_path, 'Kardelen_Pro_Kurulum_v3.exe')}")
        except Exception as e:
            print(f"⚠️ Setup oluşturma hatası: {e}")
    else:
        print("⚠️ Inno Setup yüklü değil veya KardelenSetup.iss dosyası bulunamadı. Kurulum dosyası oluşturulmadı.")
    
    input("\nİşlem tamamlandı. Çıkmak için Enter tuşuna basın...")

if __name__ == "__main__":
    create_executable()
