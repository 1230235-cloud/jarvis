import requests
import sys

JARVIS_URL = "http://10.21.209.217:8000/ask"

def chat():
    print("=" * 50)
    print("      JARVIS AI - CLIENTE DE TERMINAL")
    print("  Escribe tu mensaje o 'salir' para terminar.")
    print("  Escribe '/cloud <mensaje>' para forzar la nube.")
    print("=" * 50 + "\n")

    while True:
        try:
            user_input = input("\n\033[1;36mTú:\033[0m ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ["salir", "exit", "quit"]:
                print("\n\033[1;33mDesconectando de Jarvis...\033[0m")
                break

            force_cloud = False
            prompt = user_input

            # Comando para forzar el uso de Ollama Cloud
            if user_input.startswith("/cloud "):
                force_cloud = True
                prompt = user_input[7:].strip()

            payload = {"prompt": prompt, "force_cloud": force_cloud}

            print("\033[90mEnviando a Jarvis...\033[0m", end="\r")

            response = requests.post(JARVIS_URL, json=payload, timeout=90)
            
            if response.status_code == 200:
                data = response.json()
                source = data.get("source", "desconocido")
                
                # Extraer texto según la estructura de la respuesta
                res_obj = data.get("response", {})
                if "choices" in res_obj:
                    content = res_obj["choices"][0]["message"]["content"]
                elif "response" in res_obj:
                    content = res_obj["response"]
                else:
                    content = str(res_obj)

                # Formato visual según el origen de la inferencia
                if source == "local_tablet":
                    badge = "\033[1;32m[Tablet Local]\033[0m"
                else:
                    badge = "\033[1;35m[Ollama Cloud]\033[0m"

                print(f"\n\033[1;34mJarvis {badge}:\033[0m {content.strip()}")
            else:
                print(f"\n\033[1;31mError del Servidor [{response.status_code}]:\033[0m {response.text}")

        except KeyboardInterrupt:
            print("\n\n\033[1;33mSesión terminada.\033[0m")
            sys.exit(0)
        except Exception as e:
            print(f"\n\033[1;31mError de Conexión:\033[0m {e}")

if __name__ == "__main__":
    chat()