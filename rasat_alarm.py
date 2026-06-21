import threading
import os
import time
import re
import winsound
import json
import asyncio
import uuid
import subprocess
import logging

# Ses motoru kütüphaneleri
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import pygame
except ImportError:
    pygame = None

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

try:
    from playsound import playsound
except ImportError:
    playsound = None

try:
    import requests
except ImportError:
    requests = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

class RasatAlarmSistemi:
    def __init__(self):
        if pygame and not pygame.mixer.get_init():
            try:
                pygame.mixer.pre_init(44100, -16, 2, 2048)
            except: pass
            pygame.mixer.init()
        self.speech_lock = threading.Lock()

    def check_edge_tts_status(self):
        if edge_tts is None:
            return False, "Edge TTS kütüphanesi (edge-tts) yüklü değil.\nLütfen 'pip install edge-tts' komutunu çalıştırın."
        return True, "Edge TTS kütüphanesi yüklü."

    def google_seslendir(self, mesaj, hiz=150, ses_seviyesi=0.7, use_openai=True, api_key=None, voice_model="alloy", edge_voice="Ahmet", **kwargs):
        # Metin Düzenleme (Okunuş İyileştirme)
        # Saat başı hatırlatması için düzeltme (Saat 14 00 -> Saat 14)
        mesaj = re.sub(r'\bSaat\s+(\d{1,2})[:\s]*00\b', r'Saat \1', mesaj, flags=re.IGNORECASE)

        # HHMM formatını ayır (0850 METAR -> 08 50 METAR)
        mesaj = re.sub(r'\b(\d{2})(\d{2})\s*(SİNOPTİK|SYNOP|METAR|TAF)', r'\1 \2 \3', mesaj, flags=re.IGNORECASE)

        # SİNOPTİK ve METAR için saat başı düzeltmesi (09 00 -> 09)
        mesaj = re.sub(r'\b(\d{2})[:\s]*00\s*(SİNOPTİK|SYNOP|METAR)', r'\1 \2', mesaj, flags=re.IGNORECASE)

        mesaj = re.sub(r'\b(\d{2})\s*(\d{2})\s*Z\b', r'\1 \2', mesaj)
        mesaj = re.sub(r'\b(\d{2}):(\d{2})\b', r'\1 \2', mesaj)
        # mesaj = re.sub(r'\b00\b', 'sıfır sıfır', mesaj)
        
        mesaj = mesaj.replace("SİNOPTİK", "Sinoptik")
        mesaj = mesaj.replace("SYNOP", "Sinoptik")
        mesaj = mesaj.replace("METAR", "Metar")
        mesaj = mesaj.replace("TAF", "Taf")
        mesaj = mesaj.replace("SPECI", "Speci")
        mesaj = mesaj.replace("SAAT", "Saat")
        mesaj = mesaj.replace("RASATI", "Rasatı")
        mesaj = mesaj.replace("RASATINDA", "Rasatında")
        mesaj = mesaj.replace("GELMEMİŞTİR", "Gelmemiştir")
        
        use_edge = kwargs.get('use_edge', False)
        pitch = kwargs.get('pitch', 0)
        use_piper = kwargs.get('use_piper', False)
        piper_model = kwargs.get('piper_model', None)
        piper_bin = kwargs.get('piper_bin', "piper")

        def run():
            with self.speech_lock:
                spoken = False
                unique_id = uuid.uuid4().hex[:8]

                # 1. Öncelik: Edge TTS (Ahmet/Emel)
                if not spoken and use_edge and edge_tts:
                    try:
                        # Hız ayarı: 150 -> +0%, 225 -> +50%, 75 -> -50%
                        rate_percent = int((hiz - 150) / 1.5)
                        rate_str = f"{rate_percent:+d}%"
                        
                        # Perde Ayarı
                        pitch_val = int(pitch)
                        pitch_str = f"{pitch_val:+d}Hz"

                        # Ses Haritalama
                        voice_map = {
                            "Ahmet (Erkek)": "tr-TR-AhmetNeural",
                            "Emel (Kadın)": "tr-TR-EmelNeural",
                            "Ahmet": "tr-TR-AhmetNeural",
                            "Emel": "tr-TR-EmelNeural"
                        }
                        final_voice = voice_map.get(edge_voice, "tr-TR-AhmetNeural")

                        output_file = f"anons_edge_{unique_id}.mp3"
                        async def _speak():
                            communicate = edge_tts.Communicate(mesaj, final_voice, rate=rate_str, pitch=pitch_str)
                            await communicate.save(output_file)
                        
                        asyncio.run(_speak())

                        if os.path.exists(output_file) and pygame:
                            pygame.mixer.music.load(output_file)
                            pygame.mixer.music.set_volume(float(ses_seviyesi))
                            pygame.mixer.music.play()
                            while pygame.mixer.music.get_busy():
                                pygame.time.Clock().tick(10)
                            
                            try:
                                pygame.mixer.music.unload()
                                os.remove(output_file)
                            except: pass
                            spoken = True
                    except Exception as e:
                        logging.error(f"Edge TTS Hatası: {e}")
                        def show_err():
                            try:
                                import tkinter.messagebox
                                tkinter.messagebox.showwarning("Edge TTS Hatası", f"Edge TTS bağlantısı koptu.\nYedek ses motoruna geçiliyor.\n\nHata: {e}")
                            except: pass
                        threading.Thread(target=show_err, daemon=True).start()

                # 2. Öncelik: Piper TTS (Yerel)
                if not spoken and use_piper and piper_model and os.path.exists(piper_model):
                    try:
                        wav_file = f"anons_piper_{unique_id}.wav"
                        # Piper komutu
                        cmd = [piper_bin, "--model", piper_model, "--output_file", wav_file]
                        
                        kwargs = {}
                        if sys.platform == "win32":
                            kwargs["creationflags"] = 0x08000000  # subprocess.CREATE_NO_WINDOW
                        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
                        proc.communicate(input=mesaj.encode('utf-8'))
                        
                        if os.path.exists(wav_file) and pygame:
                            pygame.mixer.music.load(wav_file)
                            pygame.mixer.music.set_volume(float(ses_seviyesi))
                            pygame.mixer.music.play()
                            while pygame.mixer.music.get_busy():
                                pygame.time.Clock().tick(10)
                            
                            try:
                                pygame.mixer.music.unload()
                                os.remove(wav_file)
                            except: pass
                            spoken = True
                    except Exception as e:
                        logging.error(f"Piper Hatası: {e}")

                # 3. Öncelik: gTTS (Google Anons)
                if not spoken and gTTS and pygame:
                    try:
                        tts = gTTS(text=mesaj, lang='tr')
                        filename = f"anons_gtts_{unique_id}.mp3"
                        tts.save(filename)
                        
                        pygame.mixer.music.load(filename)
                        pygame.mixer.music.set_volume(float(ses_seviyesi))
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            pygame.time.Clock().tick(10)
                        
                        try:
                            pygame.mixer.music.unload()
                            os.remove(filename)
                        except: pass
                        spoken = True
                    except Exception as e:
                        logging.error(f"gTTS Hatası: {e}")

                # 4. Öncelik: OpenAI (Eğer seçiliyse)
                if not spoken and use_openai and requests:
                    try:
                        final_api_key = api_key or os.environ.get("OPENAI_API_KEY")
                        if final_api_key:
                            url = "https://api.openai.com/v1/audio/speech"
                            headers = {"Authorization": f"Bearer {final_api_key}", "Content-Type": "application/json"}
                            openai_speed = min(max(hiz / 150.0, 0.25), 4.0)
                            payload = {"model": "tts-1", "input": mesaj, "voice": voice_model, "speed": openai_speed}
                            
                            response = requests.post(url, headers=headers, json=payload, timeout=10)
                            if response.status_code == 200:
                                filename = f"anons_openai_{unique_id}.mp3"
                                with open(filename, "wb") as f: f.write(response.content)
                                
                                pygame.mixer.music.load(filename)
                                pygame.mixer.music.set_volume(float(ses_seviyesi))
                                pygame.mixer.music.play()
                                while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
                                
                                try:
                                    pygame.mixer.music.unload()
                                    os.remove(filename)
                                except: pass
                                spoken = True
                    except Exception as e:
                        logging.error(f"OpenAI TTS Hatası: {e}")

                # 5. Öncelik: pyttsx3 (Sistem Sesi - Fallback)
                if not spoken and pyttsx3:
                    try:
                        try:
                            import comtypes
                            comtypes.CoInitialize()
                        except: pass

                        engine = pyttsx3.init()
                        voices = engine.getProperty('voices')
                        turkish_voice_id = None
                        
                        for voice in voices:
                            if "tolga" in voice.name.lower():
                                turkish_voice_id = voice.id
                                break
                        if not turkish_voice_id:
                            for voice in voices:
                                if "turkish" in voice.name.lower() or "tr_tr" in voice.id.lower():
                                    turkish_voice_id = voice.id
                                    break
                        
                        if turkish_voice_id:
                            engine.setProperty('voice', turkish_voice_id)
                        else:
                            # Türkçe ses bulunamazsa logla ve varsayılan ile devam et
                            logging.warning("Sistemde Türkçe (Tolga) ses paketi bulunamadı. Varsayılan ses kullanılacak.")
                        engine.setProperty('rate', hiz)
                        engine.setProperty('volume', ses_seviyesi)
                        engine.say(mesaj)
                        engine.runAndWait()
                        spoken = True
                    except Exception as e:
                        logging.error(f"pyttsx3 Hatası: {e}")
            
                # 6. Fallback: Hiçbiri çalışmadıysa beep sesi
                if not spoken:
                    self.guvenli_ses_cal()

        threading.Thread(target=run, daemon=True).start()

    def test_openai_api(self, api_key):
        """Tests if the provided OpenAI API key is valid."""
        if not requests:
            return False, "Requests kütüphanesi yüklü değil."
        if not api_key or not api_key.strip():
            return False, "Lütfen bir API anahtarı girin."

        url = "https://api.openai.com/v1/models"
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return True, "API Anahtarı geçerli ve bağlantı başarılı!"
            elif response.status_code == 401:
                return False, "Geçersiz API Anahtarı. Lütfen kontrol edin."
            else:
                # Hata mesajını JSON'dan okumaya çalış
                error_detail = response.json().get("error", {}).get("message", "")
                return False, f"Hata: {response.status_code}. {error_detail}"
        except requests.exceptions.RequestException as e:
            return False, f"Bağlantı hatası: {e}"

    def guvenli_ses_cal(self):
        """Sistem beep sesi (Yedek alarm)."""
        # YENİ: Beep yerine daha modern ve güvenilir bir sistem sesi çalıyoruz.
        # Bu, tüm ses motorları başarısız olduğunda bile bir ses duyulmasını garanti eder.
        try:
            # 'SystemAsterisk' Windows'ta genellikle bulunan bir sestir.
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
        except Exception as e:
            logging.error(f"Güvenli ses çalınamadı (winsound): {e}")
            # En son çare olarak eski usul beep
            try: winsound.Beep(1000, 500) # 1000 Hz, 0.5 saniye
            except: pass

    def cal_alarm_sesi(self, dosya_yolu=None):
        """
        Belirtilen ses dosyasını çalar. Dosya yoksa veya hata olursa sistem zili çalar.
        """
        def run():
            success = False
            if dosya_yolu and os.path.exists(dosya_yolu):
                # 1. playsound dene
                if playsound:
                    try:
                        playsound(dosya_yolu)
                        success = True
                    except: pass
                
                # 2. pygame dene
                if not success and pygame:
                    try:
                        pygame.mixer.music.load(dosya_yolu)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            pygame.time.Clock().tick(10)
                        success = True
                    except: pass

            if not success:
                self.guvenli_ses_cal()

        threading.Thread(target=run, daemon=True).start()