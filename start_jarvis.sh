#!/bin/bash

# Terminar instancias anteriores si existen
pkill -f llama-server 2>/dev/null
pkill -f "python router.py" 2>/dev/null

# Lanzar llama-server en segundo plano con nohup
nohup /data/data/com.termux/files/home/llama.cpp/build/bin/llama-server -m /data/data/com.termux/files/home/llama.cpp/Llama-3.2-1B-Instruct-Q4_K_M.gguf --port 8080 -c 512 -t 4 > /dev/null 2>&1 &

# Esperar 2 segundos y lanzar Flask en segundo plano
sleep 2
nohup python /data/data/com.termux/files/home/llama.cpp/router.py > /dev/null 2>&1 &

echo "Servicios de Jarvis iniciados correctamente en segundo plano."