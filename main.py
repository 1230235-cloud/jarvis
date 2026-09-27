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
        self.spacing = 10
        self.pending_image_path = None

        # Variables para mantener el historial y el modelo activo de la sesión
        self.conversation_history = []
        self.active_model = None

        # Configuración de Piper TTS y el modelo Claude (México - High)
        self.model_path = "voices/es_MX-claude-high.onnx"
        self.piper_bin = "./piper/piper"

        # Campo superior para la URL del túnel de Cloudflare
        url_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.08), spacing=5)
        url_label = Label(text="Túnel URL:", size_hint=(0.2, 1))
        self.url_input = TextInput(
            text="https://deutsch-quote-dubai-signed.trycloudflare.com/ask",
            multiline=False,
            size_hint=(0.8, 1)
        )
        url_layout.add_widget(url_label)
        url_layout.add_widget(self.url_input)
        self.add_widget(url_layout)

        # Fila para seleccionar imagen mediante explorador de archivos
        img_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.08), spacing=5)
        self.img_status_label = Label(text="Ninguna imagen seleccionada", size_hint=(0.7, 1))
        self.select_img_btn = Button(text="📂 Seleccionar Imagen", size_hint=(0.3, 1))
        self.select_img_btn.bind(on_press=self.open_file_dialog)
        img_layout.add_widget(self.img_status_label)
        img_layout.add_widget(self.select_img_btn)
        self.add_widget(img_layout)

        # Área de historial de chat
        self.scroll = ScrollView(size_hint=(1, 0.69))
        self.chat_label = Label(
            text="[b]Nem:[/b] Hola, soy Nem. Sistema neuronal listo con voz Claude High...\n",
            markup=True,
            size_hint_y=None,
            text_size=(self.width, None),
            valign='top'
        )
        self.chat_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1]))
        self.bind(width=lambda instance, value: setattr(self.chat_label, 'text_size', (value - 20, None)))
        self.scroll.add_widget(self.chat_label)
        self.add_widget(self.scroll)

        # Controles de entrada (Mensaje + Botón Micrófono + Botón Enviar)
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

    def speak(self, text, is_action=False):
        """
        Nem lee todo lo que conteste la IA por voz, excepto si detecta código
        o bloques largos (>350 caracteres), usando una confirmación rápida.
        """
        def _run_speech():
            try:
                spoken_text = text
                if is_action or "def " in text or "```" in text or "{" in text or len(text) > 350:
                    spoken_text = "Listo, revisa el resultado en pantalla."

                output_wav = "output.wav"
                
                # Ejecutar el binario local de Piper con el modelo descargado
                cmd = f"echo '{spoken_text}' | {self.piper_bin} --model {self.model_path} --output_file {output_wav}"
                os.system(cmd)

                # Reproducir el audio resultante en Linux
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
                self.img_status_label.text = f"Imagen: {filename}"
                self.append_chat("Nem", f"Imagen cargada temporalmente: {filename}")
        except Exception as e:
            self.append_chat("Nem", f"Error al abrir el explorador: {str(e)}")

    def append_chat(self, sender, text):
        new_text = f"{self.chat_label.text}\n[b]{sender}:[/b] {text}"
        self.chat_label.text = new_text

    def send_message(self, instance):
        prompt = self.user_input.text.strip()
        if not prompt and not self.pending_image_path:
            return

        # Detección de comando de cierre "Gracias Nem"
        text_lower = prompt.lower()
        if "gracias nem" in text_lower or text_lower == "gracias":
            self.conversation_history.clear()
            self.active_model = None
            self.append_chat("Nem", "De nada, cierro el tema actual. Quedo atenta a tu siguiente consulta.")
            self.speak("De nada, quedo atenta.", is_action=True)
            self.user_input.text = ""
            return

        # Detección automática de investigaciones profundas
        if self.active_model is None and (text_lower.startswith("investiga") or text_lower.startswith("busca profunda")):
            self.active_model = "deep_research"

        image_path = self.pending_image_path
        self.pending_image_path = None
        self.img_status_label.text = "Ninguna imagen seleccionada"

        display_prompt = prompt if prompt else "[Imagen adjunta]"
        if image_path and prompt:
            display_prompt = f"{prompt} [Con imagen adjunta]"

        if instance:
            self.append_chat("Tú", display_prompt)

        self.user_input.text = ""
        self.send_btn.disabled = True

        if text_lower.startswith("busca") or text_lower.startswith("investiga"):
            query = text_lower.replace("busca en internet", "").replace("busca en google", "").replace("investiga", "").replace("busca", "").strip()
            url = f"[https://www.google.com/search?q=](https://www.google.com/search?q=){query.replace(' ', '+')}"
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
                self.append_chat("Nem", f"Error al leer la imagen: {str(e)}")
                self.send_btn.disabled = False
                return

        # Guardar prompt en la memoria
        self.conversation_history.append({"role": "user", "content": prompt})

        threading.Thread(target=self._query_backend, args=(prompt, target_url, image_b64)).start()

    def _query_backend(self, prompt, target_url, image_b64):
        try:
            # Payload enriquecido pasando historial y model_override
            payload = {
                "prompt": prompt,
                "history": self.conversation_history,
                "model_override": self.active_model
            }
            if image_b64:
                payload["image"] = image_b64

            response = requests.post(
                target_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=300
            )
            if response.status_code == 200:
                data = response.json()
                raw_text = data.get("response", str(data))
                reply = raw_text.replace('\\n', '\n')
                # Guardar respuesta en el historial
                self.conversation_history.append({"role": "assistant", "content": reply})
            else:
                reply = f"Error del servidor: HTTP {response.status_code}"
        except Exception as e:
            reply = f"Error de conexión: {str(e)}"

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
        self.title = "Nem AI Client - Claude High Voice"
        return JarvisUI()

if __name__ == "__main__":
    JarvisApp().run()