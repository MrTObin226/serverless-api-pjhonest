#!/bin/bash
set -e
cd /ComfyUI

# Запуск БЕЗ --lowvram, но с резервированием памяти для системных нужд
echo "Starting ComfyUI (NORMAL_VRAM mode)..."
python main.py \
  --listen \
  --extra-model-paths-config extra_model_paths.yaml \
  --reserve-vram 4096 \  # Резервируем 4 ГБ для системных операций
  --disable-smart-memory \  # Отключаем "умное" управление памятью (ломает WanVideo)
  &

# Ожидание готовности (как у вас — отлично работает)
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

[ $wait_count -ge $max_wait ] && { echo "❌ Timeout"; exit 1; }

# Запуск обработчика
echo "🚀 Starting handler..."
exec python handler.py