import os
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['KIVY_TEXT'] = 'sdl2'

import threading
import requests
import webbrowser
import base64
import time
import subprocess
import pyautogui
import speech_recognition as sr
import tkinter as tk
from tkinter import filedialog
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.clock import Clock

class JarvisUI(BoxLayout):
    def __init__(self, **kwargs):
        super(JarvisUI, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 8
        self.pending_image_path = None

        # Historial y modelo activo
        self.conversation_history = []
        self.active_model = "nemotron-3-ultra"
        self.is_offline = False

        # Configuración de Piper TTS y el modelo Claude (México - High)
        self.model_path = "voices/es_MX-claude-high.onnx"
        self.piper_bin = "./piper/piper"

        # 1. Barra superior: Selector de Conexión (Tailscale / LAN / Cloudflare)
        conn_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.07), spacing=5)
        conn_label = Label(text="URL Backend:", size_hint=(0.18, 1))
        self.url_input = TextInput(
            text="http://10.21.209.217:8000/ask",  # Default LAN IP
            multiline=False,
            size_hint=(0.42, 1)
        )
        self.btn_lan = Button(text="WiFi LAN", size_hint=(0.13, 1))
        self.btn_lan.bind(on_press=lambda x: setattr(self.url_input, 'text', "http://10.21.209.217:8000/ask"))
        
        self.btn_hotspot = Button(text="Hotspot", size_hint=(0.13, 1))
        self.btn_hotspot.bind(on_press=lambda x: setattr(self.url_input, 'text', "http://192.168.43.1:8000/ask"))
        
        self.btn_ngrok = Button(text="Ngrok", size_hint=(0.14, 1))
        self.btn_ngrok.bind(on_press=lambda x: setattr(self.url_input, 'text', "https://tu-dominio.ngrok-free.app/ask"))

        conn_layout.add_widget(conn_label)
        conn_layout.add_widget(self.url_input)
        conn_layout.add_widget(self.btn_lan)
        conn_layout.add_widget(self.btn_hotspot)
        conn_layout.add_widget(self.btn_ngrok)
        self.add_widget(conn_layout)

        # 2. Barra de Estado: Modo Offline y Selector de Imagen
        status_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.07), spacing=5)
        self.offline_btn = Button(
            text="🌐 Modo: Online (Nemotron 3 Ultra)", 
            background_color=(0.1, 0.6, 0.6, 1),
            size_hint=(0.45, 1)
        )
        self.offline_btn.bind(on_press=self.toggle_offline)

        self.img_status_label = Label(text="Sin imagen", size_hint=(0.35, 1))
        self.select_img_btn = Button(text="📂 Imagen", size_hint=(0.20, 1))
        self.select_img_btn.bind(on_press=self.open_file_dialog)

        status_layout.add_widget(self.offline_btn)
        status_layout.add_widget(self.img_status_label)
        status_layout.add_widget(self.select_img_btn)
        self.add_widget(status_layout)

        # 3. Área de historial de chat
        self.scroll = ScrollView(size_hint=(1, 0.71))
        self.chat_label = Label(
            text="[b]Nem:[/b] Hola, soy Nem. Sistema neuronal listo con voz Claude High. Modo activo: [b]Nemotron 3 Ultra[/b].\n",
            markup=True,
            size_hint_y=None,
            text_size=(self.width, None),
            valign='top'
        )
        self.chat_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1]))
        self.bind(width=lambda instance, value: setattr(self.chat_label, 'text_size', (value - 20, None)))
        self.scroll.add_widget(self.chat_label)
        self.add_widget(self.scroll)

        # 4. Controles de entrada (Mensaje + Botón Micrófono + Botón Enviar)
        input_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.15), spacing=10)
        self.user_input = TextInput(
            hint_text="Escribe o habla con Nem...",
            multiline=False,
            size_hint=(0.65, 1)
        )
        self.user_input.bind(on_text_validate=self.send_message)
        
        self.mic_btn = Button(
            text="🎤 Hablar",
            size_hint=(0.17, 1)
        )
        self.mic_btn.bind(on_press=self.start_listening_thread)

        self.send_btn = Button(
            text="Enviar",
            size_hint=(0.18, 1)
        )
        self.send_btn.bind(on_press=self.send_message)

        input_layout.add_widget(self.user_input)
        input_layout.add_widget(self.mic_btn)
        input_layout.add_widget(self.send_btn)
        self.add_widget(input_layout)

    def toggle_offline(self, instance):
        self.is_offline = not self.is_offline
        if self.is_offline:
            self.offline_btn.text = "📴 Modo: Offline (Llama Local)"
            self.offline_btn.background_color = (0.8, 0.4, 0.1, 1)
            self.append_chat("Nem", "Modo offline activado. Inferencia local mediante llama.cpp.")
            self.speak("Modo offline activado.", is_action=True)
        else:
            self.offline_btn.text = "🌐 Modo: Online (Nemotron 3 Ultra)"
            self.offline_btn.background_color = (0.1, 0.6, 0.6, 1)
            self.append_chat("Nem", "Modo online activado con Nemotron 3 Ultra.")
            self.speak("Modo online activado.", is_action=True)

    def speak(self, text, is_action=False):
        """Nem lee la respuesta por voz con Piper TTS."""
        def _run_speech():
            try:
                spoken_text = text
                if is_action or "def " in text or "```" in text or "{" in text or len(text) > 350:
                    spoken_text = "Listo, revisa el resultado en pantalla."

                output_wav = "output.wav"
                cmd = f"echo '{spoken_text}' | {self.piper_bin} --model {self.model_path} --output_file {output_wav}"
                os.system(cmd)

                if os.path.exists(output_wav):
                    os.system(f"aplay {output_wav} > /dev/null 2>&1 || ffplay -nodisp -autoexit {output_wav} > /dev/null 2>&1")
            except Exception as e:
                print(f"Error en Piper TTS: {e}")

        threading.Thread(target=_run_speech).start()

    def start_listening_thread(self, instance):
        self.mic_btn.disabled = True
        self.append_chat("Nem", "Escuchando...")
        self.speak("Te escucho", is_action=True)
        threading.Thread(target=self.listen_microphone).start()

    def listen_microphone(self):
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            text = recognizer.recognize_google(audio, language="es-ES")
            Clock.schedule_once(lambda dt: self._set_recognized_text(text))
        except sr.WaitTimeoutError:
            Clock.schedule_once(lambda dt: self._handle_mic_error("No se detectó voz a tiempo."))
        except sr.UnknownValueError:
            Clock.schedule_once(lambda dt: self._handle_mic_error("No pude entender lo que dijiste."))
        except Exception as e:
            Clock.schedule_once(lambda dt: self._handle_mic_error(f"Error de micrófono: {str(e)}"))

    def _set_recognized_text(self, text):
        self.user_input.text = text
        self.mic_btn.disabled = False
        self.append_chat("Tú (Voz)", text)
        self.send_message(None)

    def _handle_mic_error(self, error_msg):
        self.append_chat("Nem", error_msg)
        self.speak(error_msg, is_action=True)
        self.mic_btn.disabled = False

    def open_file_dialog(self, instance):
        try:
            root = tk.Tk()
            root.withdraw()
            file_path = filedialog.askopenfilename(
                title="Seleccionar imagen para análisis",
                filetypes=[("Archivos de Imagen", "*.png *.jpg *.jpeg *.webp *.bmp")]
            )
            root.destroy()
            if file_path:
                self.pending_image_path = file_path
                filename = file_path.split("/")[-1]
                self.img_status_label.text = f"Img: {filename}"
                self.append_chat("Nem", f"Imagen seleccionada: {filename}")
        except Exception as e:
            self.append_chat("Nem", f"Error al abrir explorador: {str(e)}")

    def append_chat(self, sender, text):
        new_text = f"{self.chat_label.text}\n[b]{sender}:[/b] {text}"
        self.chat_label.text = new_text

    def send_message(self, instance):
        prompt = self.user_input.text.strip()
        if not prompt and not self.pending_image_path:
            return

        text_lower = prompt.lower()
        if "gracias nem" in text_lower or text_lower == "gracias":
            self.conversation_history.clear()
            self.active_model = "nemotron-3-ultra"
            self.append_chat("Nem", "De nada, cierro el tema especializado. Vuelvo a Nemotron para tus consultas habituales.")
            self.speak("De nada, vuelvo a Nemotron.", is_action=True)
            self.user_input.text = ""
            return

        image_path = self.pending_image_path
        self.pending_image_path = None
        self.img_status_label.text = "Sin imagen"

        display_prompt = prompt if prompt else "[Imagen adjunta]"
        if image_path and prompt:
            display_prompt = f"{prompt} [Con imagen adjunta]"

        if instance:
            self.append_chat("Tú", display_prompt)

        self.user_input.text = ""
        self.send_btn.disabled = True

        if text_lower.startswith("busca en internet") or text_lower.startswith("busca en google"):
            query = text_lower.replace("busca en internet", "").replace("busca en google", "").strip()
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(url)
            reply_msg = f"Abriendo Google para buscar: {query}"
            self.append_chat("Nem", reply_msg)
            self.speak("Abriendo Google en pantalla.", is_action=True)
            self.send_btn.disabled = False
            return

        target_url = self.url_input.text.strip()
        image_b64 = None
        if image_path:
            try:
                with open(image_path, "rb") as img_file:
                    image_b64 = base64.b64encode(img_file.read()).decode('utf-8')
            except Exception as e:
                self.append_chat("Nem", f"Error al leer imagen: {str(e)}")
                self.send_btn.disabled = False
                return

        self.conversation_history.append({"role": "user", "content": prompt})
        threading.Thread(target=self._query_backend, args=(prompt, target_url, image_b64)).start()

    def _query_backend(self, prompt, target_url, image_b64):
        try:
            payload = {
                "prompt": prompt,
                "history": self.conversation_history,
                "active_model": self.active_model,
                "offline": self.is_offline
            }
            if image_b64:
                payload["image"] = image_b64

            response = requests.post(
                target_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            if response.status_code == 200:
                data = response.json()
                raw_text = data.get("response", str(data))
                new_model = data.get("active_model")
                if new_model and not self.is_offline:
                    self.active_model = new_model
                reply = raw_text.replace('\\n', '\n')
                self.conversation_history.append({"role": "assistant", "content": reply})
            else:
                reply = f"Error del servidor: HTTP {response.status_code}"
        except Exception as e:
            reply = f"Error de conexión: {str(e)}. (Activa el Modo Offline para usar la IA local)."

        Clock.schedule_once(lambda dt: self._update_response(reply))

    def _update_response(self, reply):
        is_action = False
        if reply.startswith("ACTION:YOUTUBE_PLAY:"):
            video_url = reply.replace("ACTION:YOUTUBE_PLAY:", "").strip()
            webbrowser.open(video_url)
            
            def auto_play_trigger():
                time.sleep(5.0)
                screen_width, screen_height = pyautogui.size()
                pyautogui.click(screen_width / 2, screen_height / 2)
                time.sleep(0.5)
                pyautogui.press('space')
                
            threading.Thread(target=auto_play_trigger).start()
            reply = "Reproduciendo video en YouTube."
            is_action = True

        elif reply.startswith("ACTION:LAUNCH_APP:"):
            app_name = reply.replace("ACTION:LAUNCH_APP:", "").strip()
            try:
                subprocess.Popen([app_name])
                reply = f"Abriendo {app_name}."
            except Exception as e:
                reply = f"No se pudo abrir {app_name}."
            is_action = True
            
        self.append_chat("Nem", reply)
        self.speak(reply, is_action=is_action)
        self.send_btn.disabled = False

class JarvisApp(App):
    def build(self):
        self.title = "Nem AI Client - Hybrid Online / Offline"
        return JarvisUI()

if __name__ == "__main__":
    JarvisApp().run()