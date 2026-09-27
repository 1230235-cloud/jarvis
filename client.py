import requests
import sys

# URL por defecto (puede especificarse como argumento: python client.py http://100.x.y.z:8000/ask)
DEFAULT_URL = "http://100.64.0.1:8000/ask"
if len(sys.argv) > 1:
    JARVIS_URL = sys.argv[1]
else:
    JARVIS_URL = DEFAULT_URL

def chat():
    print("=" * 60)
    print("       JARVIS / NEM AI - CLIENTE DE CONSOLA")
    print(f"  Conectado a: {JARVIS_URL}")
    print("  Comandos especiales:")
    print("    /offline        -> Forzar Modo Offline (IA local llama.cpp)")
    print("    /online         -> Volver a Modo Online (Nemotron 3 Ultra)")
    print("    gracias nem     -> Cerrar tema especializado y volver a Nemotron")
    print("    salir / exit    -> Terminar la sesión")
    print("=" * 60 + "\n")

    history = []
    active_model = "nemotron-3-ultra"
    is_offline = False

    while True:
        try:
            mode_badge = "\033[1;33m[OFFLINE]\033[0m" if is_offline else f"\033[1;36m[{active_model}]\033[0m"
            user_input = input(f"\n{mode_badge} \033[1;32mTú:\033[0m ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ["salir", "exit", "quit"]:
                print("\n\033[1;33mDesconectando de Nem...\033[0m")
                break

            if user_input.lower() == "/offline":
                is_offline = True
                print("\033[1;33mModo Offline activado (usando Llama local).\033[0m")
                continue
            elif user_input.lower() == "/online":
                is_offline = False
                active_model = "nemotron-3-ultra"
                print("\033[1;32mModo Online activado (usando Nemotron 3 Ultra).\033[0m")
                continue

            # Preparar payload enriquecido
            history.append({"role": "user", "content": user_input})
            payload = {
                "prompt": user_input,
                "history": history,
                "active_model": active_model,
                "offline": is_offline
            }

            print("\033[90mConsultando a Nem...\033[0m", end="\r")

            try:
                response = requests.post(JARVIS_URL, json=payload, timeout=90)
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("response", "")
                    new_model = data.get("active_model", active_model)
                    source = data.get("source", "desconocido")
                    session_closed = data.get("session_closed", False)

                    if session_closed:
                        history.clear()
                        active_model = "nemotron-3-ultra"
                    elif new_model and not is_offline:
                        active_model = new_model

                    history.append({"role": "assistant", "content": content})

                    badge_color = "\033[1;35m" if "cloud" in source else "\033[1;33m"
                    print(f"\n\033[1;34mNem {badge_color}[{source} | {active_model}]:\033[0m {content.strip()}")
                else:
                    print(f"\n\033[1;31mError del Servidor [{response.status_code}]:\033[0m {response.text}")
            except requests.exceptions.RequestException as e:
                print(f"\n\033[1;31mError de conexión:\033[0m {e}")
                print("\033[90mSugerencia: Revisa la URL del backend o usa '/offline' para la IA local.\033[0m")

        except KeyboardInterrupt:
            print("\n\n\033[1;33mSesión terminada.\033[0m")
            sys.exit(0)

if __name__ == "__main__":
    chat()