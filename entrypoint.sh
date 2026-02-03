#!/bin/bash

echo "🚀 Starting RunPod Worker..."

# Пути к папкам ComfyUI
COMFY_MODELS="/ComfyUI/models"
VOLUME_MODELS="/runpod-volume/models"

# Функция для создания симлинков
link_models() {
    src=$1
    dest=$2
    mkdir -p "$dest"
    if [ -d "$src" ]; then
        echo "🔗 Linking $src -> $dest"
        ln -s "$src"/* "$dest"/ 2>/dev/null
    else
        echo "⚠️ Warning: Source directory $src not found!"
    fi
}

# 1. Линкуем модели с сетевого диска (твоя структура)
link_models "$VOLUME_MODELS/diffusion_models" "$COMFY_MODELS/diffusion_models"
link_models "$VOLUME_MODELS/clip_vision"      "$COMFY_MODELS/clip_vision"
link_models "$VOLUME_MODELS/clip"             "$COMFY_MODELS/text_encoders"
link_models "$VOLUME_MODELS/vae"              "$COMFY_MODELS/vae"
link_models "$VOLUME_MODELS/loras"            "$COMFY_MODELS/loras"

echo "✅ Models linked!"

# 2. Запускаем ComfyUI в фоне
echo "⏳ Starting ComfyUI..."
python /ComfyUI/main.py --listen 127.0.0.1 --port 8188 --disable-auto-launch --gpu-only &

# Ждем запуска
while ! curl -s http://127.0.0.1:8188/ > /dev/null; do
    sleep 2
done
echo "✅ ComfyUI is ready!"

# 3. Запускаем обработчик запросов
python -u handler.py