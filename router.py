import json
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer

OLLAMA_CLOUD_URL = "https://api.ollama.com/api/generate"
OLLAMA_API_KEY = "45165a514f1342f0bc84e2d29f93c587.EZCBdevL-LOiljKcOMFJRzvc"

def select_cloud_model(prompt: str, has_image: bool = False) -> str:
    """Usa un modelo ágil y ligero para mantener respuestas rápidas y evitar timeouts."""
    if has_image:
        return "llama3.2-vision"  # O el modelo visual ligero que prefieras
    
    # Modelo ágil y general que responde al instante
    return "llama3.2"

def query_cloud_backend(prompt: str, image_base64: str = None) -> str:
    model_to_use = select_cloud_model(prompt, has_image=(image_base64 is not None))
    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"}
    
    payload = {
        "model": model_to_use, 
        "prompt": prompt if prompt else "Analiza esta imagen.", 
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 256  # Limita un poco la longitud para garantizar velocidad
        }
    }
    
    if image_base64:
        payload["images"] = [image_base64]

    try:
        r = requests.post(OLLAMA_CLOUD_URL, json=payload, headers=headers, timeout=60)
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
                
                reply = query_cloud_backend(prompt, image_base64)
                
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
    print(f"Servidor router.py en la tablet escuchando en el puerto {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()