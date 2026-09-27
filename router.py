import os
import sys
import importlib
import json
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer

# Asegurar que el directorio de este script esté en sys.path para la carga de plugins
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Servidor local de llama.cpp en la tablet/máquina local
LOCAL_LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"
LOCAL_MODEL_NAME = "Llama-3.2-1B-Instruct-Q4_K_M"

# Endpoint oficial de Ollama Cloud API
OLLAMA_CLOUD_URL = "https://api.ollama.com/api/generate"
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "45165a514f1342f0bc84e2d29f93c587.EZCBdevL-LOiljKcOMFJRzvc")

# Modelos en la nube
PRIMARY_ONLINE_MODEL = "nemotron-3-ultra"   # IA Principal por defecto en modo online
SPECIALIZED_CODE_MODEL = "gpt-oss:120b"    # IA Especializada en código / investigación profunda
VISION_CLOUD_MODEL = "gemma4:31b"          # IA Especializada en análisis visual / fotos

# Palabras clave que provocan la redirección al modelo de código / análisis complejo
COMPLEX_KEYWORDS = [
    "codigo", "programar", "python", "script", "math", "sql", 
    "explicar detalladamente", "resume", "traduce", "analiza", "algoritmo",
    "investiga", "busca profunda", "deep research", "desarrolla", "arquitectura"
]

# Palabras clave para cerrar la sesión temática y regresar a Nemotron
CLOSE_SESSION_KEYWORDS = [
    "gracias nem", "gracias", "muchas gracias", "listo nem", 
    "cerrar tema", "terminar tema", "vuelve a nemotron", "nuevo tema"
]

def is_complex_task(prompt: str) -> bool:
    """Detecta si la consulta requiere la IA especializada en la nube."""
    return any(kw in prompt.lower() for kw in COMPLEX_KEYWORDS)

def is_close_session_command(prompt: str) -> bool:
    """Detecta si el usuario desea concluir la redirección temática."""
    p = prompt.strip().lower()
    return any(p == kw or p.startswith(kw) for kw in CLOSE_SESSION_KEYWORDS)

def is_offline_command(prompt: str) -> bool:
    """Detecta si el usuario pide explícitamente pasar a modo offline."""
    p = prompt.lower()
    return any(kw in p for kw in ["modo offline", "modo local", "desconectar internet", "sin conexion", "offline"])

def query_local_llama(prompt: str, history: list = None) -> tuple[str, str]:
    """Consulta al servidor local de llama.cpp."""
    messages = [{"role": "system", "content": "Eres Nem, asistente inteligente local. Responde de forma concisa, clara y precisa en español."}]
    if history:
        for item in history:
            messages.append({
                "role": item.get("role", "user"),
                "content": item.get("content", "")
            })
    else:
        messages.append({"role": "user", "content": prompt})

    payload = {
        "model": LOCAL_MODEL_NAME,
        "messages": messages,
        "max_tokens": 256,
        "temperature": 0.3
    }
    try:
        r = requests.post(LOCAL_LLAMA_URL, json=payload, timeout=90)
        if r.status_code == 200:
            choices = r.json().get("choices", [])
            if choices:
                return choices[0]["message"]["content"], LOCAL_MODEL_NAME
            return "Sin respuesta del modelo local.", LOCAL_MODEL_NAME
        return f"Error HTTP Local ({LOCAL_MODEL_NAME}): {r.status_code}", LOCAL_MODEL_NAME
    except Exception as e:
        return f"Error al conectar con llama-server local: {str(e)}", LOCAL_MODEL_NAME

def query_cloud_model(model: str, prompt: str, image_base64: str = None, history: list = None) -> str:
    """Consulta genérica a Ollama Cloud API."""
    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json"
    }

    full_prompt = prompt
    if history and len(history) > 1:
        formatted_history = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in history[:-1]])
        if formatted_history:
            full_prompt = f"Historial previo de la conversación:\n{formatted_history}\n\nNueva consulta:\n{prompt}"

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False
    }
    if image_base64:
        payload["images"] = [image_base64]

    r = requests.post(OLLAMA_CLOUD_URL, json=payload, headers=headers, timeout=120)
    if r.status_code == 200:
        return r.json().get("response", f"Sin respuesta del modelo {model}.")
    raise RuntimeError(f"HTTP {r.status_code} desde Ollama Cloud: {r.text}")

def query_backend(prompt: str, image_base64: str = None, history: list = None, 
                  active_model: str = None, force_offline: bool = False) -> dict:
    """
    Enrutador principal inteligente con soporte para:
    1. Modo Offline (Manual o automático por fallo de conexión).
    2. IA Principal: Nemotron 3 Ultra.
    3. Redirección contextual y persistencia por IA especializada (gpt-oss:120b para código/investigación).
    4. Cierre temático con 'gracias nem' para volver a Nemotron.
    """
    text = prompt.strip()

    # 1. Comprobar si el usuario solicita cerrar el tema especializado
    if is_close_session_command(text):
        return {
            "response": "De nada. He cerrado el tema especializado y reiniciado el contexto. Vuelvo a Nemotron para tus consultas habituales.",
            "active_model": PRIMARY_ONLINE_MODEL,
            "source": "system",
            "mode": "offline" if force_offline else "online",
            "session_closed": True
        }

    # 2. Comprobar modo offline forzado por flag o por comando
    if force_offline or is_offline_command(text):
        reply, used_model = query_local_llama(text, history)
        return {
            "response": reply,
            "active_model": used_model,
            "source": "local_offline",
            "mode": "offline",
            "session_closed": False
        }

    # 3. Tarea con Imagen -> Modelo de Visión en la Nube
    if image_base64:
        try:
            reply = query_cloud_model(VISION_CLOUD_MODEL, text or "Analiza esta imagen detalladamente.", image_base64, history)
            return {
                "response": reply,
                "active_model": VISION_CLOUD_MODEL,
                "source": "ollama_cloud_vision",
                "mode": "online",
                "session_closed": False
            }
        except Exception as e:
            # Fallback automático a modelo local si no hay internet
            local_reply, used_model = query_local_llama(text + " (Nota: la imagen no pudo enviarse por falta de conexión a la nube)", history)
            return {
                "response": f"[Sin conexión nube - Modo Offline activado]\n{local_reply}",
                "active_model": used_model,
                "source": "local_offline_fallback",
                "mode": "offline",
                "session_closed": False
            }

    # 4. Decisión de Modelo: ¿Mantener especialización activa o activar nueva redirección?
    # Si ya estábamos en el modelo especializado (gpt-oss:120b) o la consulta actual lo amerita:
    target_model = active_model
    if not target_model or target_model == PRIMARY_ONLINE_MODEL:
        if is_complex_task(text):
            target_model = SPECIALIZED_CODE_MODEL
        else:
            target_model = PRIMARY_ONLINE_MODEL
    else:
        # Se mantiene en el modelo especializado (por ejemplo gpt-oss:120b) hasta que diga 'gracias nem'
        pass

    # 5. Intentar consulta a la nube con el modelo seleccionado
    try:
        reply = query_cloud_model(target_model, text, None, history)
        return {
            "response": reply,
            "active_model": target_model,
            "source": f"ollama_cloud_{target_model}",
            "mode": "online",
            "session_closed": False
        }
    except Exception as e:
        # Fallback transparente al modelo local ante falta de internet o error en la nube
        print(f"[Aviso] Fallo en la nube ({target_model}): {e}. Conmutando automáticamente a Llama local...")
        local_reply, used_model = query_local_llama(text, history)
        return {
            "response": f"[Aviso: Sin conexión a la nube. Respuesta generada en modo offline]\n{local_reply}",
            "active_model": used_model,
            "source": "local_offline_fallback",
            "mode": "offline",
            "session_closed": False
        }

# --- CARGADOR DINÁMICO DE PLUGINS ---
loaded_plugins = []

def load_plugins():
    """Carga automáticamente todos los plugins ubicados en la carpeta plugins/."""
    global loaded_plugins
    loaded_plugins = []
    plugin_dir = os.path.join(CURRENT_DIR, "plugins")
    
    if not os.path.exists(plugin_dir):
        os.makedirs(plugin_dir)
        
    for filename in sorted(os.listdir(plugin_dir)):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            try:
                mod = importlib.import_module(f"plugins.{module_name}")
                if hasattr(mod, "can_handle") and hasattr(mod, "handle"):
                    loaded_plugins.append(mod)
                    print(f"[Plugin Cargado] -> {module_name}")
            except Exception as e:
                print(f"Error cargando plugin {module_name}: {e}")

def process_user_intent(prompt: str, image_base64: str = None, history: list = None, 
                        active_model: str = None, force_offline: bool = False) -> dict:
    """Busca si algún plugin maneja la intención; si no, delega en el enrutador IA."""
    text = prompt.strip()
    
    # 1. Evaluar si algún plugin registrado maneja esta petición
    for plugin in loaded_plugins:
        try:
            if plugin.can_handle(text):
                action_result = plugin.handle(text)
                return {
                    "response": action_result,
                    "active_model": active_model or PRIMARY_ONLINE_MODEL,
                    "source": "plugin",
                    "mode": "offline" if force_offline else "online",
                    "session_closed": False
                }
        except Exception as e:
            print(f"Error ejecutando plugin: {e}")
            
    # 2. Si ningún plugin aplica, usar el flujo híbrido de modelos
    return query_backend(text, image_base64, history, active_model, force_offline)

# --- SERVIDOR WEB INTEGRADO ---
class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/ask':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                prompt = data.get("prompt", "")
                image_base64 = data.get("image", None)
                history = data.get("history", None)
                
                # Soporte para modelo activo heredado y switch de modo offline
                active_model = data.get("active_model") or data.get("model_override")
                force_offline = bool(data.get("offline", False) or data.get("force_offline", False) or data.get("mode") == "offline")
                
                # Procesar intención mediante plugins o IA
                result_payload = process_user_intent(prompt, image_base64, history, active_model, force_offline)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result_payload).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e), "response": f"Error interno del servidor: {str(e)}"}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8000):
    load_plugins()
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print("=" * 60)
    print(f"  JARVIS Router Híbrido escuchando en el puerto {port}")
    print(f"  • IA Principal Online: {PRIMARY_ONLINE_MODEL}")
    print(f"  • IA Especializada:   {SPECIALIZED_CODE_MODEL}")
    print(f"  • IA Local Offline:    {LOCAL_MODEL_NAME}")
    print(f"  • Plugins activos:     {len(loaded_plugins)}")
    print("=" * 60)
    httpd.serve_forever()

if __name__ == "__main__":
    run()