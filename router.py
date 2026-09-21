import json
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer

LOCAL_LLAMA_URL = "http://127.0.0.1:8080/completion"
OLLAMA_CLOUD_URL = "https://api.ollama.com/api/generate"
OLLAMA_API_KEY = "45165a514f1342f0bc84e2d29f93c587.EZCBdevL-LOiljKcOMFJRzvc"

def is_heavy_task(prompt: str, has_image: bool) -> tuple[bool, str]:
    """Determina si la tarea debe ir a la nube o resolverse localmente."""
    if has_image:
        return True, "nemotron-3-ultra"
    
    p = prompt.lower()
    # Tareas pesadas o de código van a la nube
    if any(kw in p for kw in ["codigo", "programar", "python", "script", "sql", "algoritmo", "debug"]):
        return True, "gpt-oss:120b"
    elif any(kw in p for kw in ["analiza", "explica detalladamente", "razona", "matematicas"]):
        return True, "nemotron-3-ultra"
    
    # Todo lo demás se queda en el cerebro local (rápido y eficiente)
    return False, "local-1b"

def query_backend(prompt: str, image_base64: str = None) -> str:
    use_cloud, model_to_use = is_heavy_task(prompt, has_image=(image_base64 is not None))
    
    if not use_cloud:
        # Petición al modelo local (llama-server en puerto 8080)
        payload = {"prompt": prompt, "n_predict": 256}
        try:
            r = requests.post(LOCAL_LLAMA_URL, json=payload, timeout=30)
            if r.status_code == 200:
                return r.json().get("content", "Sin respuesta local.")
        except Exception:
            pass # Si falla el local, intentará respaldarse con la nube o reportar error
            
    # Petición a la nube si es tarea pesada
    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model_to_use, 
        "prompt": prompt if prompt else "Analiza esta imagen.", 
        "stream": False
    }
    if image_base64:
        payload["images"] = [image_base64]

    try:
        r = requests.post(OLLAMA_CLOUD_URL, json=payload, headers=headers, timeout=300)
        if r.status_code == 200:
            return r.json().get("response", "Sin respuesta.")
        return f"Error HTTP Nube ({model_to_use}): {r.status_code}"
    except Exception as e:
        return f"Error Nube: {str(e)}"

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/ask':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                prompt = data.get("prompt", "")
                image_base64 = data.get("image", None)
                
                reply = query_backend(prompt, image_base64)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"response": reply}).encode('utf-8'))
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