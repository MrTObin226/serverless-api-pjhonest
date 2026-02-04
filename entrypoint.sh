#!/bin/bash
set -euo pipefail

# Оптимизации CUDA для RTX 4090 (24GB) — меньше OOM, быстрее аллокации
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:128
export XFORMERS_FORCE_DISABLE_TRITON=1
export CUDA_VISIBLE_DEVICES=0

# Симлинки на модели из RunPod Network Volume (у тебя всё в /runpod-volume/ComfyUI/models/)
echo "🔗 Создание симлинков на модели..."
VOLUME_MODELS="/runpod-volume/ComfyUI/models"
for sub in checkpoints clip vae loras diffusion_models text_encoders clip_vision; do
    src="${VOLUME_MODELS}/${sub}"
    dst="/workspace/ComfyUI/models/${sub}"
    mkdir -p "$dst"
    if [ -d "$src" ]; then
        for f in "$src"/*; do
            # Не линкуем пустые/битые файлы
            if [ -f "$f" ] && [ -s "$f" ]; then
                ln -sf "$f" "$dst/"
            fi
        done
    fi
done
mkdir -p /workspace/ComfyUI/input /workspace/ComfyUI/output

# Запуск ComfyUI в фоне
echo "🚀 Запуск ComfyUI..."
cd /workspace/ComfyUI
python3 main.py --dont-print-server --port 8188 --listen 0.0.0.0 &
COMFY_PID=$!

# Ожидание готовности API
echo "⏳ Ожидание готовности ComfyUI (до 90 сек)..."
for i in $(seq 1 90); do
    if curl -sf http://127.0.0.1:8188/history > /dev/null 2>&1; then
        echo "✅ ComfyUI готов (PID: $COMFY_PID)"
        break
    fi
    sleep 1
    if [ "$i" -eq 90 ]; then
        echo "❌ ComfyUI не запустился за 90 секунд"
        exit 1
    fi
done
# Запуск RunPod serverless worker (handler.py вызывает runpod.serverless.start)
cd /workspace
echo "🔌 Запуск RunPod handler (cwd=/workspace)..."
exec python3 /workspace/handler.py
