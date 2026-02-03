#!/bin/bash
set -e

# Исправляем ошибку comfy_aimdo в cuda_malloc.py
if [ -f "/workspace/ComfyUI/cuda_malloc.py" ]; then
    echo "🔧 Исправление cuda_malloc.py..."
    sed -i 's/^import comfy_aimdo/# import comfy_aimdo (disabled)/' /workspace/ComfyUI/cuda_malloc.py 2>/dev/null || true
    sed -i 's/^from comfy_aimdo/# from comfy_aimdo (disabled)/' /workspace/ComfyUI/cuda_malloc.py 2>/dev/null || true
    echo "✅ cuda_malloc.py исправлен"
fi

# Создаём симлинки на модели из сетевого тома
echo "🔗 Создание симлинков на модели..."
mkdir -p /workspace/ComfyUI/models/checkpoints \
         /workspace/ComfyUI/models/clip \
         /workspace/ComfyUI/models/vae \
         /workspace/ComfyUI/models/loras \
         /workspace/ComfyUI/input \
         /workspace/ComfyUI/output

ln -sf /runpod-volume/models/checkpoints/* /workspace/ComfyUI/models/checkpoints/ 2>/dev/null || true
ln -sf /runpod-volume/models/clip/* /workspace/ComfyUI/models/clip/ 2>/dev/null || true
ln -sf /runpod-volume/models/vae/* /workspace/ComfyUI/models/vae/ 2>/dev/null || true
ln -sf /runpod-volume/models/loras/* /workspace/ComfyUI/models/loras/ 2>/dev/null || true

# Оптимизации CUDA для RTX 4090
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export XFORMERS_FORCE_DISABLE_TRITON=1
export CUDA_VISIBLE_DEVICES=0

# Запуск ComfyUI (БЕЗ --disable-all-custom-nodes!)
echo "🚀 Запуск ComfyUI..."
cd /workspace/ComfyUI
python main.py --dont-print-server --port 8188 --listen 0.0.0.0 2>&1 | grep -v "comfy_aimdo" &
COMFY_PID=$!

# Ожидание готовности API
echo "⏳ Ожидание готовности ComfyUI (до 60 сек)..."
for i in {1..60}; do
    if curl -s http://127.0.0.1:8188/history > /dev/null 2>&1; then
        echo "✅ ComfyUI готов к работе (PID: $COMFY_PID)"
        break
    fi
    sleep 1
    if [ $i -eq 60 ]; then
        echo "❌ ComfyUI не запустился за 60 секунд"
        exit 1
    fi
done

# Запуск хендлера RunPod
echo "🔌 Запуск RunPod handler..."
exec python -m runpod.endpoint.run