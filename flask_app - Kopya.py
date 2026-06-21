import os
import sys
import logging
import subprocess
import ctypes
from flask import Flask, render_template, request, jsonify
from datetime import datetime

# Mevcut modülleri içe aktar
try:
    from kardelen_scraper import KardelenScraper
    from log_processor import process_and_analyze_logs
    import TAF_METAR_TREND
except ImportError as e:
    logging.critical(f"Modüller yüklenemedi. {e}")
    sys.exit(1)

# EXE olarak paketlendiğinde HTML şablonlarının yolunu doğru bulabilmesi için özel yapılandırma
if getattr(sys, 'frozen', False):
    template_dir = os.path.join(sys._MEIPASS, 'templates')
    app = Flask(__name__, template_folder=template_dir)
else:
    app = Flask(__name__)

# Global nesneler (Her istekte yeniden yaratmamak için)
scraper = KardelenScraper()
robot = TAF_METAR_TREND.HavacilikRobotModulu()

# Başlangıçta site analizi yap (Filtreleri ve ayları çekmek için)
logging.info("Site analizi yapılıyor, lütfen bekleyin...")
scraper.analyze_site()

def add_firewall_rule(port=5000):
    """Yönetici izinleri varsa Windows Güvenlik Duvarı'na otomatik izin kuralı ekler."""
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            rule_name = "Kardelen_Web_Sunucusu"
            # Kuralın sistemde zaten var olup olmadığını kontrol et
            check = subprocess.run(["netsh", "advfirewall", "firewall", "show", "rule", f"name={rule_name}"], capture_output=True, text=True, creationflags=0x08000000)
            if "No rules match" in check.stdout or "Hata" in check.stdout or "bulunamadı" in check.stdout.lower():
                # Kural yoksa güvenlik duvarı penceresi (popup) çıkmaması için önceden izin ekle
                subprocess.run(["netsh", "advfirewall", "firewall", "add", "rule", f"name={rule_name}", "dir=in", "action=allow", "protocol=TCP", f"localport={port}"], capture_output=True, creationflags=0x08000000)
                logging.info(f"Güvenlik duvarı izin kuralı ({port} portu için) sessizce eklendi.")
    except Exception as e:
        logging.warning(f"Güvenlik duvarı kuralı eklenemedi: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    # Varsayılan Tarih (Bugün)
    now = datetime.now()
    
    # Form Seçenekleri
    days = [str(i).zfill(2) for i in range(1, 32)]
    
    # Aylar (Scraper'dan gelmezse varsayılan)
    months = list(scraper.config.get("ay_map", {}).keys())
    if not months:
        months = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"]
    
    years = [str(i) for i in range(2023, 2031)]
    
    # Filtreler
    filters = list(scraper.config.get("filtre_map", {"Tüm Bültenler": "500"}).keys())

    # Seçili Değerler (Varsayılanlar)
    sel_day = str(now.day).zfill(2)
    sel_month = months[now.month - 1] if len(months) >= now.month else months[0]
    sel_year = str(now.year)
    sel_filter = filters[0] if filters else "Tüm Bültenler"
    
    results = []
    error = None

    if request.method == 'POST':
        # Formdan gelen verileri al
        sel_day = request.form.get('day')
        sel_month = request.form.get('month')
        sel_year = request.form.get('year')
        sel_filter = request.form.get('filter')
        
        # Filtre ID'sini bul
        f_id = scraper.config.get("filtre_map", {}).get(sel_filter, "500")
        
        try:
            # Verileri Çek
            logs = scraper.fetch_logs(sel_day, sel_month, sel_year, f_id)
            
            if logs:
                # Analiz Et
                results = process_and_analyze_logs(logs, robot)
            else:
                error = "Kriterlere uygun veri bulunamadı."
        except Exception as e:
            error = f"İşlem sırasında hata oluştu: {e}"

    return render_template('index.html', 
                           days=days, months=months, years=years, filters=filters,
                           sel_day=sel_day, sel_month=sel_month, sel_year=sel_year, sel_filter=sel_filter,
                           results=results, error=error)

@app.route('/api/command', methods=['POST'])
def api_command():
    """Web arayüzünden ana programa komut (Örn: Alarm susturma) gönderir."""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Geçersiz istek."}), 400
        
    action = data.get('action')
    if action == 'silence_alarm':
        try:
            # Ana programın (arayuz.py vb.) okuyabilmesi için bir sinyal dosyası oluştur
            flag_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarm_silence.flag")
            with open(flag_path, "w") as f:
                f.write("silenced")
            logging.info("Ağdan (Web arayüzü) 'Alarmı Sustur' sinyali alındı.")
            return jsonify({"status": "success", "message": "Alarm susturma komutu ana cihaza iletildi!"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
            
    return jsonify({"status": "error", "message": "Bilinmeyen komut."}), 400

if __name__ == '__main__':
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    print(f"Web sunucusu başlatıldı! Ağdaki diğer bilgisayarlardan erişmek için tarayıcıya şunu yazın: http://{local_ip}:5000")
    import webbrowser
    webbrowser.open("http://127.0.0.1:5000") # Ana bilgisayarda tarayıcıyı aç
    
    # Sunucu tam başlamadan saniyeler önce kuralı ekle ve Firewall uyarısını engelle
    add_firewall_rule(5000)
    
    # host='0.0.0.0' sayesinde LAN'daki (Ağdaki) diğer PC'ler IP adresiyle bağlanabilir.
    app.run(host='0.0.0.0', port=5000, debug=False)
