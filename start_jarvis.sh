#!/bin/bash

# Matar instancias previas
pkill -f llama-server 2>/dev/null
pkill -f "python router.py" 2>/dev/null

# Ejecutar llama-server en segundo plano y desvincular de la sesión
/data/data/com.termux/files/home/llama.cpp/build/bin/llama-server -m /data/data/com.termux/files/home/llama.cpp/Llama-3.2-1B-Instruct-Q4_K_M.gguf --port 8080 -c 512 -t 4 > /dev/null 2>&1 &
disown

# Esperar 2 segundos y lanzar Flask en segundo plano desvinculado
sleep 2
python /data/data/com.termux/files/home/llama.cpp/router.py > /dev/null 2>&1 &
disown

echo "Servicios desvinculados correctamente."