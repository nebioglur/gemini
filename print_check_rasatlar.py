#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import pandas as pd

ROOT = r"c:\Windows.old.000\Users\nebio\Desktop\tum\kardelen\HATARAMA"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import denetim_merkezi_1 as dm1

CHECK_DIR = r"C:\Users\nebio\Desktop\check"

SİN_PATTERNS = ["SIN", "SİN"]
METAR_PATTERN = "METAR"


def find_files():
    files = [f for f in os.listdir(CHECK_DIR) if os.path.isfile(os.path.join(CHECK_DIR, f))]
    sin_files = [f for f in files if any(pat in f.upper() for pat in SİN_PATTERNS) and f.lower().endswith((".xls", ".xlsx"))]
    metar_files = [f for f in files if METAR_PATTERN in f.upper() and f.lower().endswith((".xls", ".xlsx"))]
    return sorted(sin_files), sorted(metar_files)


def print_rasatlar(file_path, label):
    print("\n" + "=" * 80)
    print(f"{label}: {file_path}")
    print("=" * 80)

    try:
        df = dm1.dosya_oku_akilli(file_path)
    except Exception as e:
        print(f"❌ Okuma hatası: {e}")
        return

    if df is None or df.empty:
        print("⚠️ Veri bulunamadı.")
        return

    raw_column = None
    for candidate in ["bulten", "bulten_metar", "_raw_line", "RASATLAR", "SİNOPTİK - Şifreli Mesaj", "METAR - Şifreli Mesaj"]:
        if candidate in df.columns:
            raw_column = candidate
            break

    if raw_column is None:
        print("⚠️ Şifreli rasat için uygun bir sütun bulunamadı.")
        print("Mevcut sütunlar:", df.columns.tolist())
        return

    if "sayfa" not in df.columns:
        print("⚠️ 'sayfa' sütunu bulunamadı.")
    if "gmt" not in df.columns:
        print("⚠️ 'gmt' sütunu bulunamadı.")

    printed = 0
    for _, row in df.iterrows():
        raw_value = str(row.get(raw_column, "")).strip()
        if not raw_value or raw_value.lower() == "nan":
            continue

        tarih = row.get("sayfa")
        saat = row.get("gmt")

        if pd.isna(tarih) or pd.isna(saat):
            continue

        try:
            saat_val = int(float(saat))
        except Exception:
            try:
                saat_val = int(str(saat).replace('Z', '').split(':')[0])
            except Exception:
                saat_val = None

        if saat_val is None:
            saat_str = str(saat)
        else:
            saat_str = f"{saat_val:02d}Z"

        print(f"[{tarih} - {saat_str}] {raw_value}")
        printed += 1

    if printed == 0:
        print("⚠️ Şifreli rasat verisi bulunamadı.")


if __name__ == "__main__":
    sin_files, metar_files = find_files()

    if not sin_files and not metar_files:
        print(f"{CHECK_DIR} içinde SİN veya METAR .xls/.xlsx dosyası bulunamadı.")
        sys.exit(1)

    if sin_files:
        for sin_file in sin_files:
            print_rasatlar(os.path.join(CHECK_DIR, sin_file), "SİNOPTİK")

    if metar_files:
        for metar_file in metar_files:
            print_rasatlar(os.path.join(CHECK_DIR, metar_file), "METAR")

    print("\n✅ Tamamlandı.")
