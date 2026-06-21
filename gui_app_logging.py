# -*- coding: utf-8 -*-
import logging
import os
import config_manager

class IncompatibilityLoggingMixin:
    """
    TAF-METAR uyumsuzluklarını ayrı bir dosyaya kaydetmek için
    gerekli fonksiyonları içeren bir mixin sınıfı.
    """
    def setup_incompatibility_logger(self):
        """Uyumsuz rasatlar için özel bir logger oluşturur ve ayarlar."""
        self.incompatibility_logger = logging.getLogger('IncompatibilityLogger')
        self.incompatibility_logger.setLevel(logging.INFO)
        
        # Log mesajlarının ana logger'a (root) gitmesini engelle
        self.incompatibility_logger.propagate = False
        
        # Eğer zaten bir handler varsa, tekrar eklemeyi önle (pencere tekrar açıldığında vb.)
        if self.incompatibility_logger.hasHandlers():
            return
            
        base_log_dir = config_manager.USER_DATA_DIR
        os.makedirs(base_log_dir, exist_ok=True)
        log_file = os.path.join(base_log_dir, "uyumsuz_rasatlar.txt")
        
        # Formatter: Sadece mesajı, tarihle birlikte temiz bir formatta yaz
        formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%d.%m.%Y %H:%M:%S')
        
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setFormatter(formatter)
        
        self.incompatibility_logger.addHandler(handler)
        logging.info(f"Uyumsuz rasat kayıt dosyası başlatıldı: {log_file}")

    def log_incompatibility(self, station_name, reason, metar_data, taf_data="N/A"):
        """Tespit edilen bir uyumsuzluğu özel log dosyasına kaydeder."""
        if not hasattr(self, 'incompatibility_logger'):
            self.setup_incompatibility_logger()
            
        log_message = f"İSTASYON: {station_name} | SEBEP: {reason} | METAR: {metar_data} | TAF: {taf_data}"
        self.incompatibility_logger.info(log_message)