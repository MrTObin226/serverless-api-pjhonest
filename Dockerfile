FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel
ENV DEBIAN_FRONTEND=noninteractive

# 1. Системные зависимости + критически важные для CUDA оптимизации
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 ffmpeg git wget curl unzip libgomp1 ninja-build \
    build-essential libopenmpi-dev openmpi-bin \
    && rm -rf /var/lib/apt/lists/*

# 2. Оптимизации памяти ДО установки Python-пакетов (критично для A100)
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
ENV CUDA_CACHE_DISABLE=1
ENV TORCH_CUDNN_SDPA_ENABLED=1

# 3. Скачиваем ПОСЛЕДНЮЮ стабильную версию ComfyUI (без привязки к коммитам)
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI && \
    cd /ComfyUI && git pull

WORKDIR /ComfyUI

# 4. Установка зависимостей в правильном порядке (решает проблему совместимости)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    # Сначала фиксируем версию torch для совместимости с нодами
    pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124 && \
    # Базовые зависимости ComfyUI
    pip install --no-cache-dir -r requirements.txt && \
    # Дополнительные зависимости с ВЕРСИОННЫМИ ОГРАНИЧЕНИЯМИ для стабильности
    pip install --no-cache-dir \
        "runpod>=0.10.0" \
        "websocket-client>=1.8.0" \
        "opencv-python-headless>=4.10.0" \
        "accelerate>=0.34.0" \
        "transformers>=4.48.0,<4.49.0" \
        "diffusers>=0.31.0,<0.32.0" \
        "torchao>=0.7.0" \
        "sageattention>=1.2.0" \
        "onnx>=1.16.0" \
        "onnxruntime-gpu>=1.19.0" \
        "imageio>=2.34.0" \
        "imageio-ffmpeg>=0.5.1" \
        "av>=12.0.0" \
        "flash-attn>=2.6.0" --no-build-isolation

# 5. Клонируем ноды с ПОСЛЕДНИМИ ИСПРАВЛЕНИЯМИ (включая фикс apply_rope)
RUN cd custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git && \
    git clone https://github.com/city96/ComfyUI-GGUF.git

# 6. КРИТИЧЕСКИ ВАЖНО: обновляем ноды до версий с фиксом apply_rope
RUN cd custom_nodes/ComfyUI-WanVideoWrapper && \
    git pull && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e . && \
    # Принудительно обновляем зависимости для совместимости с новым API ComfyUI
    pip install --no-cache-dir "comfy-cli>=1.20.0"

RUN cd custom_nodes/ComfyUI-VideoHelperSuite && \
    git pull && \
    pip install --no-cache-dir -r requirements.txt

# 7. Файлы проекта
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY handler.py /ComfyUI/handler.py
COPY new_Wan22_api.json /ComfyUI/new_Wan22_api.json
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh && mkdir -p /ComfyUI/input /ComfyUI/output /ComfyUI/models
ENV PYTHONUNBUFFERED=1
ENV COMFYUI_NORMAL_VRAM=1

ENTRYPOINT ["/entrypoint.sh"]