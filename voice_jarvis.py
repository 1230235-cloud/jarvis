import os
import sys
import subprocess
import requests
import pyttsx3
import speech_recognition as sr

JARVIS_URL = "http://10.21.209.217:8000/ask"
TEMP_AUDIO = "/tmp/jarvis_input.wav"
TARGET_MIC = "alsa_input.pci-0000_00_1f.3.analog-stereo"

# Inicializar motor TTS (Texto a Voz)
engine = pyttsx3.init()
engine.setProperty('rate', 170)

voices = engine.getProperty('voices')
for voice in voices:
    if "spanish" in voice.name.lower() or "es" in voice.id.lower():
        engine.setProperty('voice', voice.id)
        break

def speak(text: str):
    print(f"\n\033[1;34mJarvis:\033[0m {text}")
    engine.say(text)
    engine.runAndWait()

def listen(duration=5) -> str:
    recognizer = sr.Recognizer()
    try:
        print("\n\033[90m[MIC] Escuchando (grabando 5s con PipeWire)... habla ahora\033[0m")
        
        # Grabación con pw-record y conversión limpia a PCM WAV mediante ffmpeg
        RAW_AUDIO = "/tmp/jarvis_raw.wav"
        cmd = f"sh -c 'pw-record --target {TARGET_MIC} {RAW_AUDIO} & PID=$!; sleep {duration}; kill $PID; ffmpeg -y -i {RAW_AUDIO} -ac 1 -ar 16000 {TEMP_AUDIO} > /dev/null 2>&1'"
        subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        
        print("\033[93m[MIC] Grabación finalizada. Procesando voz...\033[0m")

        if not os.path.exists(TEMP_AUDIO):
            print("\033[1;31m[ERROR MIC]: No se generó el archivo de audio.\033[0m")
            return ""

        # Enviar audio a Google STT
        with sr.AudioFile(TEMP_AUDIO) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="es-ES")
            print(f"\033[1;36mTú dijiste:\033[0m {text}")
            return text

    except sr.UnknownValueError:
        print("\033[1;31m[MIC] No se entendieron palabras claras.\033[0m")
        return ""
    except sr.RequestError as e:
        print(f"\033[1;31m[MIC] Error en la API STT: {e}\033[0m")
        return ""
    except Exception as e:
        print(f"\033[1;31m[ERROR MIC]: {e}\033[0m")
        return ""
    finally:
        for path in [TEMP_AUDIO, "/tmp/jarvis_raw.wav"]:
            if os.path.exists(path):
                os.remove(path)

def voice_chat():
    speak("Sistemas listos. Te escucho.")
    while True:
        try:
            prompt = listen()
            if not prompt:
                continue

            if any(kw in prompt.lower() for kw in ["salir", "apagar", "adiós", "terminar"]):
                speak("Hasta luego.")
                break

            print("\033[90mConsultando backend de Jarvis...\033[0m")
            response = requests.post(JARVIS_URL, json={"prompt": prompt}, timeout=90)
            
            if response.status_code == 200:
                data = response.json()
                res_obj = data.get("response", {})
                
                if "choices" in res_obj:
                    content = res_obj["choices"][0]["message"]["content"]
                elif "response" in res_obj:
                    content = res_obj["response"]
                else:
                    content = str(res_obj)

                speak(content.strip())
            else:
                speak("Hubo un error al procesar tu solicitud.")

        except KeyboardInterrupt:
            speak("Sesión de voz finalizada.")
            sys.exit(0)
        except Exception as e:
            print(f"\033[1;31mError general:\033[0m {e}")

if __name__ == "__main__":
    voice_chat()