import json
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer

# Configuración de Modelos
LOCAL_LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"
OLLAMA_CLOUD_URL = "https://api.ollama.com/api/generate"
OLLAMA_API_KEY = "45165a514f1342f0bc84e2d29f93c587.EZCBdevL-LOiljKcOMFJRzvc"

COMPLEX_KEYWORDS = [
    "codigo", "programar", "python", "script", "math", "sql", 
    "explicar detalladamente", "resume", "traduce", "analiza", "algoritmo"
]

def is_complex_task(prompt: str) -> bool:
    return any(kw in prompt.lower() for kw in COMPLEX_KEYWORDS)

def search_web(query: str) -> str:
    """Búsqueda web ligera usando Wikipedia (no requiere librerías extra)."""
    url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&utf8=&format=json"
    try:
        res = requests.get(url, timeout=5).json()
        results = res.get("query", {}).get("search", [])
        if not results:
            return "No se encontraron resultados en internet."
        import re
        snippet = re.sub(r'<[^>]+>', '', results[0]['snippet'])
        return f"{results[0]['title']}: {snippet}"
    except Exception as e:
        return f"Error en búsqueda: {str(e)}"

def query_backend(prompt: str, force_cloud: bool = False) -> str:
    if force_cloud or is_complex_task(prompt):
        headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": "gemma4:31b", "prompt": prompt, "stream": False}
        try:
            r = requests.post(OLLAMA_CLOUD_URL, json=payload, headers=headers, timeout=60)
            if r.status_code == 200:
                return r.json().get("response", "Sin respuesta.")
            return f"Error HTTP Nube: {r.status_code}"
        except Exception as e:
            return f"Error Nube: {str(e)}"
    else:
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
    if "busca en youtube" in text or "pon en youtube" in text:
        query = text.replace("busca en youtube", "").replace("pon en youtube", "").strip()
        return f"ACTION:YOUTUBE:{query}"
        
    # 2. Comando Búsqueda Web
    elif "busca en internet" in text or "busca en google" in text or "investiga" in text:
        clean_query = text.replace("busca en internet", "").replace("busca en google", "").replace("investiga", "").strip()
        web_results = search_web(clean_query)
        augmented_prompt = f"El usuario consulta: '{clean_query}'.\nInformación: {web_results}\nResponde la consulta con esta información:"
        return query_backend(augmented_prompt, force_cloud=True)
        
    # 3. Flujo Normal
    return query_backend(prompt)

# --- SERVIDOR WEB INTEGRADO ---
class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/ask':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                prompt = data.get("prompt", "")
                
                # Procesar la intención del usuario
                reply = process_user_intent(prompt)
                
                # Enviar respuesta exitosa a Kivy
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
    print(f"Servidor router.py escuchando en el puerto {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()