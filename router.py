import json
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer

# Servidor local de llama.cpp en la tablet
LOCAL_LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"

# Endpoint oficial de Ollama Cloud API
OLLAMA_CLOUD_URL = "https://api.ollama.com/api/generate"
OLLAMA_API_KEY = "45165a514f1342f0bc84e2d29f93c587.EZCBdevL-LOiljKcOMFJRzvc"

# Palabras clave que requieren el modelo potente de texto en la nube
COMPLEX_KEYWORDS = [
    "codigo", "programar", "python", "script", "math", "sql", 
    "explicar detalladamente", "resume", "traduce", "analiza", "algoritmo"
]

def is_complex_task(prompt: str) -> bool:
    """Detecta si la consulta requiere el modelo avanzado de texto en la nube."""
    return any(kw in prompt.lower() for kw in COMPLEX_KEYWORDS)

def get_first_youtube_video(query: str) -> str:
    """Busca el primer resultado en YouTube y añade el parámetro de reproducción automática."""
    try:
        search_url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            import re
            video_ids = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', response.text)
            if video_ids:
                first_video_id = video_ids[0]
                # Enlace directo con autoplay activado
                return f"https://www.youtube.com/watch?v={first_video_id}&autoplay=1"
        return f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
    except Exception:
        return f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"

def query_backend(prompt: str, image_base64: str = None) -> str:
    """Enruta inteligentemente entre modelos locales y en la nube según la tarea."""
    
    # 1. Tarea con Imagen -> Modelo gemma4:31b en la Nube
    if image_base64:
        headers = {
            "Authorization": f"Bearer {OLLAMA_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gemma4:31b",
            "prompt": prompt if prompt else "Analiza esta imagen detalladamente.",
            "images": [image_base64],
            "stream": False
        }
        try:
            r = requests.post(OLLAMA_CLOUD_URL, json=payload, headers=headers, timeout=120)
            if r.status_code == 200:
                return r.json().get("response", "Sin respuesta del modelo gemma4:31b.")
            return f"Error HTTP Nube (Gemma Imagen): {r.status_code} - {r.text}"
        except Exception as e:
            return f"Error Nube (Gemma Imagen): {str(e)}"

    # 2. Tarea Compleja de Texto / Código -> Modelo Pesado en la Nube
    elif is_complex_task(prompt):
        headers = {
            "Authorization": f"Bearer {OLLAMA_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-oss:120b",
            "prompt": prompt,
            "stream": False
        }
        try:
            r = requests.post(OLLAMA_CLOUD_URL, json=payload, headers=headers, timeout=60)
            if r.status_code == 200:
                return r.json().get("response", "Sin respuesta de la nube.")
            return f"Error HTTP Nube: {r.status_code}"
        except Exception as e:
            return f"Error Nube: {str(e)}"

    # 3. Tarea Cotidiana / Rápida -> Cerebro Local (llama.cpp)
    else:
        payload = {
            "model": "Llama-3.2-1B-Instruct-Q4_K_M",
            "messages": [
                {"role": "system", "content": "Responde de forma concisa y clara."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 128,
            "temperature": 0.2
        }
        try:
            r = requests.post(LOCAL_LLAMA_URL, json=payload, timeout=120)
            if r.status_code == 200:
                choices = r.json().get("choices", [])
                if choices:
                    return choices[0]["message"]["content"]
                return "Sin respuesta del modelo local."
            return f"Error HTTP Local: {r.status_code}"
        except Exception as e:
            return f"Error Local: {str(e)}"

def process_user_intent(prompt: str, image_base64: str = None) -> str:
    """Procesa intenciones del usuario (acciones especiales o enrutamiento de IA)."""
    text = prompt.strip()
    text_lower = text.lower()
    
    # Detección flexible de YouTube ante cualquier mención de la palabra
    if "youtube" in text_lower or "reproduce" in text_lower:
        import re
        query = re.sub(r'\b(busca|pon|en|youtube|reproduce|quiero|escuchar|musica|video|por|favor|de|la|el|los|las)\b', '', text_lower).strip()
        query = " ".join(query.split()) or text_lower.replace("youtube", "").strip()
        video_url = get_first_youtube_video(query if query else text_lower)
        return f"ACTION:YOUTUBE_PLAY:{video_url}"
        
    # Flujo de modelos híbridos
    return query_backend(text, image_base64)

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
                
                # Procesar la intención con texto e imagen
                reply = process_user_intent(prompt, image_base64)
                
                # Enviar respuesta exitosa
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response_json = json.dumps({"response": reply})
                self.wfile.write(response_json.encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Servidor router.py híbrido escuchando en el puerto {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()