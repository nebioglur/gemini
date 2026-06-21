import webview
import threading
from kardelen_scraper import KardelenScraper
from log_processor import process_and_analyze_logs
import TAF_METAR_TREND

class AnalizApi:
    def __init__(self):
        self.scraper = KardelenScraper()
        self.robot = TAF_METAR_TREND.HavacilikRobotModulu()
        self.scraper.analyze_site()

    def verileri_getir(self, day, month, year, filtre_id="500"):
        """HTML/JS tarafından çağrılacak metod"""
        try:
            logs = self.scraper.fetch_logs(day, month, year, filtre_id)
            if not logs:
                return {"status": "error", "message": "Kriterlere uygun veri bulunamadı."}
            
            # Verileri analiz et
            analiz_sonuclari = process_and_analyze_logs(logs, self.robot)
            
            # JavaScript'in anlayabilmesi için dict formatına dönüştürüyoruz
            js_data = []
            for group in analiz_sonuclari:
                g_dict = {"taf": group['taf'], "observations": []}
                for obs in group['observations']:
                    # Temel verileri alıp dict içine koyuyoruz
                    g_dict['observations'].append({
                        "turu": obs['type'],
                        "kayit_tar": obs['raw'][3] if len(obs['raw'])>3 else "-",
                        "bulten": obs['bulten'],
                        "durum": obs.get('analysis', {}).get('durum', '-')
                    })
                js_data.append(g_dict)
                
            return {"status": "success", "data": js_data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

HTML_KODU = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Kardelen Webview Analiz</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f4f9; padding: 20px; }
        button { padding: 10px; background: #2E7D32; color: white; border: none; cursor: pointer; }
        .result-box { margin-top: 20px; padding: 15px; background: white; border-radius: 5px; }
        .taf { color: #0D47A1; font-weight: bold; }
        .uyumsuz { color: red; font-weight: bold; }
        .uyumlu { color: green; font-weight: bold; }
    </style>
</head>
<body>
    <h2>✈️ Kardelen Analiz (Webview)</h2>
    Gün: <input type="text" id="day" value="15" size="3">
    Ay: <input type="text" id="month" value="MAYIS" size="10">
    Yıl: <input type="text" id="year" value="2026" size="5">
    <button onclick="analizBaslat()">GÖSTER</button>
    
    <div id="results" class="result-box">Sonuçlar burada görünecek...</div>

    <script>
        async function analizBaslat() {
            document.getElementById('results').innerHTML = "<i>Veriler çekiliyor ve analiz ediliyor... Lütfen bekleyin.</i>";
            
            let d = document.getElementById('day').value;
            let m = document.getElementById('month').value;
            let y = document.getElementById('year').value;
            
            // Python'daki verileri_getir fonksiyonunu çağırır
            let response = await pywebview.api.verileri_getir(d, m, y, "500");
            
            if (response.status === "error") {
                document.getElementById('results').innerHTML = "<b style='color:red'>" + response.message + "</b>";
                return;
            }
            
            let htmlOut = "<table border='1' width='100%' style='border-collapse: collapse;'>";
            htmlOut += "<tr style='background:#ddd'><th>TÜRÜ</th><th>KAYIT TAR.</th><th>BÜLTEN</th><th>DURUM</th></tr>";
            
            response.data.forEach(group => {
                if (group.taf) {
                    htmlOut += `<tr class="taf"><td>${group.taf.type}</td><td>-</td><td>${group.taf.bulten}</td><td>-</td></tr>`;
                }
                group.observations.forEach(obs => {
                    let durumClass = obs.durum.includes('UYUMSUZ') ? 'uyumsuz' : (obs.durum.includes('UYUMLU') ? 'uyumlu' : '');
                    htmlOut += `<tr>
                        <td>${obs.turu}</td>
                        <td>${obs.kayit_tar}</td>
                        <td style="font-family: monospace;">${obs.bulten}</td>
                        <td class="${durumClass}">${obs.durum}</td>
                    </tr>`;
                });
            });
            htmlOut += "</table>";
            document.getElementById('results').innerHTML = htmlOut;
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    api = AnalizApi()
    webview.create_window('Kardelen Analiz Arayüzü', html=HTML_KODU, js_api=api, width=1024, height=768)
    webview.start()
