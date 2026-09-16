from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Configuración de Endpoints
LOCAL_LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"
OLLAMA_CLOUD_URL = "https://api.ollama.com/v1/chat/completions"
OLLAMA_API_KEY = "TU_API_KEY_AQUI"

def is_complex_task(prompt: str) -> bool:
    """Filtra palabras clave para determinar si la tarea va a la Nube."""
    keywords = ["codigo", "programar", "python", "script", "math", "sql", "explicar detalladamente"]
    return any(kw in prompt.lower() for kw in keywords)

@app.route('/ask', methods=['POST'])
def route_prompt():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "")
    force_cloud = data.get("force_cloud", False)

    # 1. Enrutamiento a la Nube (Ollama Cloud)
    if force_cloud or is_complex_task(prompt):
        headers = {
            "Authorization": f"Bearer {OLLAMA_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama3.3",
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            r = requests.post(OLLAMA_CLOUD_URL, json=payload, headers=headers, timeout=60)
            return jsonify({"source": "cloud", "response": r.json()})
        except Exception as e:
            return jsonify({"error": f"Error Nube: {str(e)}"}), 500

    # 2. Enrutamiento Local (Tablet)
    else:
        payload = {
            "model": "Llama-3.2-1B-Instruct-Q4_K_M",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 64
        }
        try:
            # Timeout extendido a 120s para evitar errores de conexión en la CPU de la tablet
            r = requests.post(LOCAL_LLAMA_URL, json=payload, timeout=120)
            return jsonify({"source": "local_tablet", "response": r.json()})
        except Exception as e:
            return jsonify({"error": f"Error Local: {str(e)}"}), 500

if __name__ == '__main__':
    # debug=True activa el autoreload automático al modificar el archivo
    app.run(host='0.0.0.0', port=8000, debug=True)