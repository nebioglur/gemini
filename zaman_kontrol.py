from datetime import datetime, timedelta

def taf_analiz_et(metar_saat_str, taf_ana_bitis, ara_taf_t1, ara_taf_t2, ara_taf_tipi="BECMG"):
    """
    Kullanıcının notlarındaki mantığa göre TREND periyodunu analiz eder.
    """
    # Saatleri objeye çevirelim (Örn: "1000" -> 10:00)
    fmt = "%H%M"
    metar_t = datetime.strptime(metar_saat_str, fmt)
    trend_sonu = metar_t + timedelta(hours=2)
    
    t1 = datetime.strptime(ara_taf_t1, fmt)
    t2 = datetime.strptime(ara_taf_t2, fmt)
    
    print(f"METAR Zamanı: {metar_saat_str}")
    print(f"2 Saatlik TREND Sonu: {trend_sonu.strftime(fmt)}")
    print(f"Ara TAF ({ara_taf_tipi}) Aralığı: {ara_taf_t1} - {ara_taf_t2}")
    print("-" * 30)

    # MANTIK KONTROLÜ
    if ara_taf_tipi == "TEMPO":
        # Not: Tempo'da T1 ve T2'nin ikisi de önemlidir.
        if t1 <= trend_sonu:
            return "SONUÇ: ARA TAF (TEMPO) rotasına girilmelidir."
        else:
            return "SONUÇ: ANA TAF rotasında kal."

    elif ara_taf_tipi == "BECMG":
        # 1. Durum: Trend sonu BECMG bitişini (T2) geçmişse kesin Ara TAF
        if trend_sonu >= t2:
            return "SONUÇ: ARA TAF (BECMG tamamlandı) kesinlikle kullanılmalı."
        
        # 2. Durum: Trend sonu T1'i geçmiş ama T2'ye ulaşmamışsa (Senin eklediğin inisiyatif kuralı)
        elif t1 < trend_sonu < t2:
            return "SONUÇ: İNİSİYATİF! BECMG başladı ama bitmedi. Hava şartına göre ARA veya ANA TAF seçilebilir."
        
        # 3. Durum: Henüz hiçbir kesişme yoksa
        else:
            return "SONUÇ: ANA TAF rotasında kal."

# ÖRNEK TEST (Notlarındaki Örnek 2'ye göre)
# METAR: 0850 (Trend sonu 1050)
# BECMG: 0900 / 1100 (T1: 09, T2: 11)
print(taf_analiz_et("0850", "1800", "0900", "1100", "BECMG"))