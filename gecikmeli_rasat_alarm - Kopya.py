import threading
import os
import time
import re
import warnings
import subprocess
import asyncio
import tempfile

# Ses motoru kütüphaneleri
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    # Pygame import edilirken oluşan pkg_resources uyarısını gizle
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")
        import pygame
except ImportError:
    pygame = None

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

_tts_lock = threading.Lock()

class RasatAlarmSistemi:
    def __init__(self):
        if pygame and not pygame.mixer.get_init():
            pygame.mixer.init()

    def google_seslendir(self, mesaj, hiz=150, pitch=0, use_piper=False, piper_model=None, piper_bin="piper", use_edge=False, edge_voice=None, **kwargs):
        # Metin Düzenleme (Okunuş İyileştirme)
        # Örnek: 2350Z -> 23 50 Zulu (Yirmi üç, elli Zulu)
        mesaj = re.sub(r'\b(\d{2})(\d{2})Z\b', r'\1 \2', mesaj)
        # Örnek: 23:50 -> 23 50
        mesaj = re.sub(r'\b(\d{2}):(\d{2})\b', r'\1 \2', mesaj)
        # Örnek: 1940 TAF -> 19 40 TAF (Bitişik yazılan saatleri ayır)
        mesaj = re.sub(r'\b(\d{2})(\d{2})\s+(TAF|METAR|SİNOPTİK|SYNOP|SPECI)\b', r'\1 \2 \3', mesaj)
        
        # Saat okunuş düzeltmeleri (00 -> sıfır sıfır)
        mesaj = re.sub(r'\b00\b', 'sıfır sıfır', mesaj)
        
        # Kelime Bazlı Düzeltmeler (Telaffuz için)
        mesaj = mesaj.replace("SİNOPTİK", "Sinoptik")
        mesaj = mesaj.replace("SYNOP", "Sinoptik")
        mesaj = mesaj.replace("METAR", "Metar")
        mesaj = mesaj.replace("TAF", "Taf")
        mesaj = mesaj.replace("SPECI", "Speci")

        def run():
            with _tts_lock:
                unique_id = int(time.time() * 1000)
                temp_dir = tempfile.gettempdir()
                # 1. Öncelik: Edge TTS (Eğer aktifse)
                if use_edge and edge_tts:
                    try:
                        output_file = os.path.join(temp_dir, f"anons_edge_{unique_id}.mp3")

                        # Hız Ayarı (150 = Normal = +0%)
                        rate_val = int(hiz) - 150
                        rate_str = f"{rate_val:+d}%"
                        
                        # Perde Ayarı (0 = Normal = +0Hz)
                        pitch_val = int(pitch)
                        pitch_str = f"{pitch_val:+d}Hz"
                        
                        # Ses Haritalama (Kullanıcı dostu isimlerden ID'ye)
                        voice_map = {
                            "Ahmet (Erkek)": "tr-TR-AhmetNeural",
                            "Emel (Kadın)": "tr-TR-EmelNeural",
                            "Ahmet": "tr-TR-AhmetNeural",
                            "Emel": "tr-TR-EmelNeural"
                        }
                        voice = voice_map.get(edge_voice, "tr-TR-AhmetNeural")

                        async def _speak():
                            communicate = edge_tts.Communicate(mesaj, voice, rate=rate_str, pitch=pitch_str)
                            await communicate.save(output_file)
                        
                        asyncio.run(_speak())

                        if os.path.exists(output_file) and pygame:
                            pygame.mixer.music.load(output_file)
                            pygame.mixer.music.play()
                            while pygame.mixer.music.get_busy():
                                pygame.time.Clock().tick(10)
                            pygame.mixer.music.unload()
                            os.remove(output_file)
                            return
                    except Exception as e:
                        print(f"Edge TTS Hatası: {e}")
                        def show_err():
                            try:
                                import tkinter.messagebox
                                tkinter.messagebox.showwarning("Edge TTS Hatası", f"Edge TTS bağlantısı koptu.\nYedek ses motoruna geçiliyor.\n\nHata: {e}")
                            except: pass
                        threading.Thread(target=show_err, daemon=True).start()

                # 2. Öncelik: Piper TTS (Eğer aktifse)
                if use_piper and piper_model and os.path.exists(piper_model):
                    try:
                        wav_file = os.path.join(temp_dir, f"anons_temp_{unique_id}.wav")
                        # Piper komutu: echo "mesaj" | piper --model model.onnx --output_file output.wav
                        cmd = [piper_bin, "--model", piper_model, "--output_file", wav_file]
                        
                        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        proc.communicate(input=mesaj.encode('utf-8'))
                        
                        if os.path.exists(wav_file) and pygame:
                            pygame.mixer.music.load(wav_file)
                            pygame.mixer.music.play()
                            while pygame.mixer.music.get_busy():
                                pygame.time.Clock().tick(10)
                            pygame.mixer.music.unload()
                            os.remove(wav_file)
                            return
                    except Exception as e:
                        print(f"Piper Hatası: {e}")

                # 3. Öncelik: pyttsx3 (Offline, Hızlı, Windows Sesi)
                if pyttsx3:
                    try:
                        engine = pyttsx3.init()
                        # Türkçe sesi bulmaya çalış
                        voices = engine.getProperty('voices')
                        turkish_voice_id = None
                        for voice in voices:
                            if "turkish" in voice.name.lower() or "tr_tr" in voice.id.lower() or "tolga" in voice.name.lower():
                                turkish_voice_id = voice.id
                                break
                        
                        if turkish_voice_id:
                            engine.setProperty('voice', turkish_voice_id)
                            engine.setProperty('rate', hiz) # Konuşma hızı
                            engine.say(mesaj)
                            engine.runAndWait()
                            return
                        else:
                            # Türkçe ses yoksa bile varsayılan sistem sesiyle oku (gTTS yerine)
                            engine.setProperty('rate', hiz)
                            engine.say(mesaj)
                            engine.runAndWait()
                            return
                    except Exception as e:
                        print(f"pyttsx3 Hatası: {e}")

                # 4. Öncelik: gTTS (Online, Yavaş - Yedek)
                if gTTS and pygame:
                    try:
                        tts = gTTS(text=mesaj, lang='tr')
                        filename = os.path.join(temp_dir, f"anons_temp_{unique_id}.mp3")
                        tts.save(filename)
                        
                        pygame.mixer.music.load(filename)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            pygame.time.Clock().tick(10)
                        
                        # Dosyayı serbest bırak ve sil
                        try:
                            pygame.mixer.music.unload()
                            os.remove(filename)
                        except: pass
                    except Exception as e:
                        print(f"gTTS Hatası: {e}")
        
        threading.Thread(target=run, daemon=True).start()

    def ozel_ses_cal(self, dosya_yolu):
        if pygame and os.path.exists(dosya_yolu):
            def play():
                try:
                    pygame.mixer.music.load(dosya_yolu)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10)
                except: pass
            threading.Thread(target=play, daemon=True).start()