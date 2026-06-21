import os

# Hatalı dosyanın yolunu otomatik bulur
base_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(base_dir, "turkey_map.py")

if os.path.exists(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Dosyanın olması gereken son satırını buluyoruz
    # turkey_map.py normalde 'return map_win' ile biter.
    cutoff_index = -1
    for i, line in enumerate(lines):
        if line.strip() == "return map_win":
            cutoff_index = i
            # İlk bulduğumuz yerde kesiyoruz (Çünkü dosya başından itibaren doğru, sonrası tekrar)
            break
    
    if cutoff_index != -1:
        # Dosyayı bu satırdan sonra kesiyoruz
        new_content = lines[:cutoff_index + 1]
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_content)
            
        print(f"✅ Dosya onarıldı! Toplam {len(lines)} satırdan {len(new_content)} satıra düşürüldü.")
        print("Lütfen programı tekrar çalıştırın.")
    else:
        print("⚠️ Dosya içinde 'return map_win' satırı bulunamadı. Manuel kontrol gerekebilir.")
else:
    print(f"❌ Dosya bulunamadı: {file_path}")