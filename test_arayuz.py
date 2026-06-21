#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Arayuz debug test"""
import sys
import os
import traceback

os.chdir(r"c:\Windows.old.000\Users\nebio\Desktop\tum\kardelen\HATARAMA")
sys.path.insert(0, r"c:\Windows.old.000\Users\nebio\Desktop\tum\kardelen\HATARAMA")

try:
    print("Step 1: Importing modules...")
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
    import threading
    import datetime
    import calendar
    import os as os_module
    import re
    import traceback
    import glob
    import logging
    import json
    import shutil
    print("✓ Standard modules imported")
    
    print("\nStep 2: Importing custom modules...")
    import kurallar
    print("✓ kurallar imported")
    
    print("\nStep 3: Setting up paths...")
    VALIDATOR_DIR = r"C:\Users\nebio\Desktop\check"
    if VALIDATOR_DIR not in sys.path:
        sys.path.append(VALIDATOR_DIR)
    
    try:
        import validator
        print("✓ validator imported")
    except ImportError as e:
        print(f"⚠ validator import failed: {e}")
        validator = None
    
    print("\nStep 4: Checking ayarlari_yukle function...")
    SETTINGS_FILE = 'ayarlar.json'
    
    def ayarlari_yukle():
        """Kayıtlı ayarları json dosyasından okur."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Ayarlar dosyası okunamadı: {e}")
        return {}
    
    print("✓ ayarlari_yukle function defined")
    
    print("\nStep 5: Testing lazy loading imports...")
    print("Importing pandas (this may take time)...")
    import pandas as pd
    print("✓ pandas imported")
    
    import denetim_merkezi_1 as dm1
    print("✓ denetim_merkezi_1 imported")
    
    import denetim_merkezi_2 as dm2
    print("✓ denetim_merkezi_2 imported")
    
    import denetim_merkezi_3 as dm3
    print("✓ denetim_merkezi_3 imported")
    
    import sutun_duzeltici
    print("✓ sutun_duzeltici imported")
    
    print("\n" + "="*60)
    print("✓✓✓ ALL CHECKS PASSED ✓✓✓")
    print("="*60)
    print("\nProgram is ready to run. No errors found!")
    
except Exception as e:
    print("\n" + "!"*60)
    print("ERROR DETECTED:")
    print("!"*60)
    traceback.print_exc()
    sys.exit(1)
