import subprocess
import time
import os

# 1. Matar procesos anteriores
os.system("pkill -f llama-server")
os.system("pkill -f 'python router.py'")
time.sleep(1)

# 2. Iniciar llama-server en segundo plano
llama_cmd = [
    "/data/data/com.termux/files/home/llama.cpp/build/bin/llama-server",
    "-m", "/data/data/com.termux/files/home/llama.cpp/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
    "--port", "8080",
    "-c", "512",
    "-t", "4"
]
subprocess.Popen(llama_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("llama-server iniciado.")

time.sleep(2)

# 3. Iniciar router.py en segundo plano
router_cmd = [
    "/data/data/com.termux/files/usr/bin/python",
    "/data/data/com.termux/files/home/llama.cpp/router.py"
]
subprocess.Popen(router_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("router.py iniciado.")