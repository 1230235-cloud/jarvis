#!/data/data/com.termux/files/usr/bin/sh

# Matar procesos previos de forma exhaustiva
pkill -f llama-server 2>/dev/null
pkill -f router.py 2>/dev/null
fuser -k 8000/tcp 2>/dev/null
sleep 1

# Iniciar llama-server local (cerebro principal) con nohup
nohup /data/data/com.termux/files/home/llama.cpp/build/bin/llama-server -m /data/data/com.termux/files/home/llama.cpp/Llama-3.2-1B-Instruct-Q4_K_M.gguf --port 8080 -c 512 -t 4 > /dev/null 2>&1 &

sleep 3

# Iniciar router.py con nohup
nohup /data/data/com.termux/files/usr/bin/python /data/data/com.termux/files/home/llama.cpp/router.py > /dev/null 2>&1 &

echo "Sistema híbrido (Local + Nube) iniciado en segundo plano."
echo "Para verificar el estado ejecuta: ps aux | grep -E 'llama|router'"