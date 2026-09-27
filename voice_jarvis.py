import os
import sys
import subprocess
import requests
import pyttsx3
import speech_recognition as sr

# URL de conexión (puede pasarse como primer argumento en consola)
JARVIS_URL = sys.argv[1] if len(sys.argv) > 1 else "http://100.64.0.1:8000/ask"
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
    print(f"\n\033[1;34mNem:\033[0m {text}")
    engine.say(text)
    engine.runAndWait()

def listen(duration=5) -> str:
    recognizer = sr.Recognizer()
    try:
        print("\n\033[90m[MIC] Escuchando (habla ahora)... \033[0m")
        RAW_AUDIO = "/tmp/jarvis_raw.wav"
        cmd = f"sh -c 'pw-record --target {TARGET_MIC} {RAW_AUDIO} & PID=$!; sleep {duration}; kill $PID; ffmpeg -y -i {RAW_AUDIO} -ac 1 -ar 16000 {TEMP_AUDIO} > /dev/null 2>&1'"
        subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

        if not os.path.exists(TEMP_AUDIO):
            return ""

        with sr.AudioFile(TEMP_AUDIO) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="es-ES")
            print(f"\033[1;36mTú dijiste:\033[0m {text}")
            return text

    except sr.UnknownValueError:
        return ""
    except Exception as e:
        print(f"\033[1;31m[ERROR MIC]:\033[0m {e}")
        return ""
    finally:
        for path in [TEMP_AUDIO, "/tmp/jarvis_raw.wav"]:
            if os.path.exists(path):
                os.remove(path)

def voice_chat():
    speak("Sistemas Nem listos con Nemotron 3 Ultra y modo offline. Te escucho.")
    conversation_history = []
    active_model = "nemotron-3-ultra"
    is_offline = False

    while True:
        try:
            prompt = listen()
            if not prompt:
                continue

            prompt_lower = prompt.lower()
            if any(kw in prompt_lower for kw in ["salir", "apagar", "adiós", "terminar"]):
                speak("Hasta luego.")
                break

            if "modo offline" in prompt_lower:
                is_offline = True
                speak("Modo offline activado. Usando inferencia local.")
                continue
            elif "modo online" in prompt_lower:
                is_offline = False
                active_model = "nemotron-3-ultra"
                speak("Modo online activado con Nemotron.")
                continue

            conversation_history.append({"role": "user", "content": prompt})

            payload = {
                "prompt": prompt,
                "history": conversation_history,
                "active_model": active_model,
                "offline": is_offline
            }

            print("\033[90mConsultando backend...\033[0m")
            response = requests.post(JARVIS_URL, json=payload, timeout=90)
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("response", "Sin respuesta.")
                new_model = data.get("active_model")
                session_closed = data.get("session_closed", False)

                if session_closed:
                    conversation_history.clear()
                    active_model = "nemotron-3-ultra"
                elif new_model and not is_offline:
                    active_model = new_model

                conversation_history.append({"role": "assistant", "content": content})
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