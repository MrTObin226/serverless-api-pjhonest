#!/bin/bash

# Останавливать скрипт при любой ошибке
set -e

echo "🚀 Проверка наличия моделей перед запуском..."

# Функция для скачивания, если файла нет
download_if_missing() {
    local url=$1
    local dest=$2
    if [ ! -f "$dest" ]; then
        echo "📥 Скачивание: $(basename "$dest")..."
        wget -q "$url" -O "$dest"
    else
        echo "✅ Пройдено: $(basename "$dest") уже на месте."
    fi
}

# 1. Скачивание основной модели Wan2.2 (14B FP8)
download_if_missing \
    "https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors" \
    "/ComfyUI/models/diffusion_models/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors"

# 2. Скачивание T5 Encoder (Text-to-Video)
download_if_missing \
    "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors" \
    "/ComfyUI/models/clip/umt5-xxl-enc-bf16.safetensors"

# 3. Скачивание VAE
download_if_missing \
    "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors" \
    "/ComfyUI/models/vae/Wan2_1_VAE_bf16.safetensors"

# 4. Скачивание CLIP Vision (для I2V)
download_if_missing \
    "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors" \
    "/ComfyUI/models/clip_vision/clip_vision_h.safetensors"

# 5. Скачивание Lightning LoRA (для скорости)
download_if_missing \
    "https://huggingface.co/lightx2v/Wan2.2-Lightning/resolve/main/Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1/high_noise_model.safetensors" \
    "/ComfyUI/models/loras/high_noise_model.safetensors"

# 6. Скачивание Cyberpunk LoRA (используем curl с твоим токеном)
DEST_CYBER="/ComfyUI/models/loras/cyberpunk_style.safetensors"
if [ ! -f "$DEST_CYBER" ]; then
    echo "📥 Скачивание Cyberpunk LoRA..."
    curl -H "User-Agent: Mozilla/5.0" -L "https://civitai.com/api/download/models/2553271?token=c056bf57d3819491f7ffd7bb814ea189" -o "$DEST_CYBER"
fi

echo "✨ Все модели готовы. Запуск ComfyUI..."

# Запуск ComfyUI в фоне
python /ComfyUI/main.py --listen --port 8188 &

# Ожидание готовности API
echo "Waiting for ComfyUI API..."
max_wait=120
wait_count=0
while [ $wait_count -lt $max_wait ]; do
    if curl -s http://127.0.0.1:8188/ > /dev/null 2>&1; then
        echo "✅ ComfyUI is ready!"
        break
    fi
    echo "⌛ Ожидание ComfyUI... ($wait_count/$max_wait)"
    sleep 2
    wait_count=$((wait_count + 2))
done

if [ $wait_count -ge $max_wait ]; then
    echo "❌ Ошибка: ComfyUI не запустился!"
    exit 1
fi

# Запуск обработчика RunPod (основной процесс)
echo "🚀 Запуск обработчика handler.py..."
exec python handler.py