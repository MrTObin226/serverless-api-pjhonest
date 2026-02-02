#!/bin/bash

# Останавливаем скрипт при любой ошибке
set -e

# Переходим в папку ComfyUI (важно для путей)
cd /ComfyUI

# 1. Запуск ComfyUI в фоне с указанием конфига моделей
echo "Starting ComfyUI..."
python main.py --listen --extra-model-paths-config extra_model_paths.yaml &

# 2. Ожидание готовности (твой цикл — отличный)
echo "Waiting for ComfyUI to be ready..."
max_wait=120
wait_count=0
while [ $wait_count -lt $max_wait ]; do
    if curl -s http://127.0.0.1:8188/history > /dev/null 2>&1; then
        echo "ComfyUI is ready!"
        break
    fi
    echo "Waiting for ComfyUI... ($wait_count/$max_wait)"
    sleep 5
    wait_count=$((wait_count + 5))
done

if [ $wait_count -ge $max_wait ]; then
    echo "Error: ComfyUI failed to start within $max_wait seconds"
    exit 1
fi

# 3. Запуск обработчика
echo "Starting the handler..."
# Используем exec, чтобы handler стал основным процессом (PID 1)
exec python handler.py