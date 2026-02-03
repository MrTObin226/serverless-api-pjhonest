#!/bin/bash
set -e
cd /ComfyUI

# Запуск в режиме нормальной VRAM (оптимально для 4090)
echo "Starting ComfyUI..."
python main.py \
  --listen \
  --extra-model-paths-config extra_model_paths.yaml \
  --reserve-vram 4096 \
  --disable-smart-memory &

# Ожидание готовности
echo "Waiting for ComfyUI to be ready..."
max_wait=120
wait_count=0
while [ $wait_count -lt $max_wait ]; do
    if curl -s http://127.0.0.1:8188/history > /dev/null 2>&1; then
        echo "✅ ComfyUI is ready!"
        break
    fi
    echo "⏳ Waiting... ($wait_count/$max_wait)"
    sleep 5
    wait_count=$((wait_count + 5))
done

if [ $wait_count -ge $max_wait ]; then
    echo "❌ Timeout: ComfyUI failed to start"
    exit 1
fi

# Запуск обработчика RunPod
echo "🚀 Starting handler..."
exec python handler.py