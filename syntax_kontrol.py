# -*- coding: utf-8 -*-
import os
import py_compile
import sys
import traceback

def check_all_syntax():
    """
    Projedeki tüm Python dosyalarını sözdizimi (syntax) hatalarına karşı kontrol eder.
    """
    print("="*60)
    print("🐍 KARDELEN PROJESİ - TOPLU SÖZDİZİMİ KONTROL ARACI")
    print("="*60)

    # Scriptin bulunduğu dizini al ve çalışma dizini yap
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    print(f"📂 Kontrol Dizini: {base_dir}\n")

    # Kontrol edilecek dosyaların listesi (klasördeki tüm .py dosyaları)
    files_to_check = [f for f in os.listdir(base_dir) if f.endswith('.py')]
    
    error_found = False
    checked_count = 0

    for filename in sorted(files_to_check):
        if not os.path.exists(filename):
            continue
        
        checked_count += 1
        try:
            # doraise=True, hata durumunda exception fırlatmasını sağlar
            py_compile.compile(filename, doraise=True)
        except py_compile.PyCompileError as e:
            print(f"❌ HATA: {filename:<30}")
            if hasattr(e, 'exc_value') and e.exc_value:
                print(f"   -> Satır {getattr(e.exc_value, 'lineno', '?')}: {getattr(e.exc_value, 'msg', str(e)).strip()}")
            else:
                print(f"   -> {str(e.msg).strip()}")
            print("-" * 60)
            error_found = True
        except Exception as e:
            print(f"❌ BEKLENMEYEN HATA: {filename:<30}")
            print(f"   -> {e}")
            print("-" * 60)
            error_found = True

    print("\n" + "="*60)
    if error_found:
        print("⚠️ Kontrol tamamlandı. Yukarıda listelenen dosyalarda hatalar bulundu.")
    else:
        print(f"✅ Kontrol tamamlandı. {checked_count} dosya incelendi ve SÖZDİZİMİ HATASI BULUNAMADI.")
    print("="*60)

if __name__ == "__main__":
    check_all_syntax()
    input("\nÇıkmak için Enter tuşuna basın...")