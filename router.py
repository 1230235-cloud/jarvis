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

def query_backend(prompt: str, image_base64: str = None) -> str:
    """Enruta inteligentemente entre modelos locales y en la nube según la tarea."""
    
    # 1. Tarea con Imagen -> Modelo de Visión en la Nube (Formato Multimodal)
    if image_base64:
        headers = {
            "Authorization": f"Bearer {OLLAMA_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "nemotron-3-ultra",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt if prompt else "Analiza esta imagen detalladamente."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                }
            ],
            "stream": False
        }
        try:
            r = requests.post("https://api.ollama.com/v1/chat/completions", json=payload, headers=headers, timeout=120)
            if r.status_code == 200:
                data = r.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0]["message"]["content"]
                return data.get("response", "Sin respuesta del modelo de visión.")
            return f"Error HTTP Nube (Imagen): {r.status_code} - {r.text}"
        except Exception as e:
            return f"Error Nube (Imagen): {str(e)}"

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
    
    # Comando YouTube opcional
    if "busca en youtube" in text_lower or "pon en youtube" in text_lower:
        query = text_lower.replace("busca en youtube", "").replace("pon en youtube", "").strip()
        return f"ACTION:YOUTUBE:{query}"
        
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