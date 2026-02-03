#!/bin/bash

# 1. Создаем необходимые папки, если их еще нет на диске
mkdir -p /runpod-volume/ComfyUI/input
mkdir -p /runpod-volume/ComfyUI/output

# 2. Запуск ComfyUI в фоне
# Добавляем --lowvram для экономии памяти видеокарты 4090
# Указываем правильный путь к yaml (в корне проекта /workspace)
echo "🚀 Starting ComfyUI backend with Low VRAM mode..."
python3 /runpod-volume/ComfyUI/main.py --listen 0.0.0.0 --port 8188 --lowvram --extra-model-paths-config /workspace/extra_model_paths.yaml &
# 3. Запуск RunPod Handler
# Handler сам дождется готовности ComfyUI через функцию wait_for_comfyui
echo "🚀 Starting RunPod Handler..."
python3 -u /workspace/handler.py