# -*- coding: utf-8 -*-
"""
Kardelen Log Görüntüleyici Başlatıcı
Bu dosya artık sadece gui_app_1.py içindeki ana uygulamayı başlatır.
"""
from gui_app_1 import KardelenApp

def gui_baslat():
    app = KardelenApp()
    app.run()

if __name__ == "__main__":
    gui_baslat()
