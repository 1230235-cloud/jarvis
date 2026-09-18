import json
import re
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer

LOCAL_LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"
OLLAMA_CLOUD_URL = "https://api.ollama.com/api/generate"
OLLAMA_API_KEY = "45165a514f1342f0bc84e2d29f93c587.EZCBdevL-LOiljKcOMFJRzvc"

def query_backend(prompt: str) -> str:
    payload = {
        "model": "Llama-3.2-1B-Instruct-Q4_K_M",
        "messages": [{"role": "system", "content": "Responde conciso."}, {"role": "user", "content": prompt}],
        "max_tokens": 128, "temperature": 0.2
    }
    try:
        r = requests.post(LOCAL_LLAMA_URL, json=payload, timeout=120)
        if r.status_code == 200:
            choices = r.json().get("choices", [])
            if choices: return choices[0]["message"]["content"]
            return "Sin respuesta local."
        return f"Error Local HTTP: {r.status_code}"
    except Exception as e:
        return f"Error Local: {str(e)}"

def process_user_intent(prompt: str) -> str:
    text = prompt.strip().lower()
    
    # 1. Comando YouTube
    if "youtube" in text:
        query = re.sub(r'\b(busca|pon|en|youtube|reproduce|quiero|escuchar|musica|video|por|favor|de)\b', '', text).strip()
        query = " ".join(query.split()) or "musica"
        return f"ACTION:YOUTUBE:{query}"
        
    # 2. Comando Búsqueda Web local en la PC (Firefox / Chrome)
    elif "busca en internet" in text or "busca en google" in text or "investiga" in text or "busca" in text:
        clean_query = text.replace("busca en internet", "").replace("busca en google", "").replace("investiga", "").replace("busca", "").strip()
        if not clean_query:
            clean_query = text
        return f"ACTION:WEB:{clean_query}"
        
    # 3. Flujo Normal de IA
    return query_backend(prompt)

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/ask':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                prompt = data.get("prompt", "")
                reply = process_user_intent(prompt)
                
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
    print(f"Servidor router.py escuchando en el puerto {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()