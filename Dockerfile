# 1. Используем стабильную базу от PyTorch (NVIDIA CUDA 12.4)
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

# Удаляем интерактивные запросы при установке
ENV DEBIAN_FRONTEND=noninteractive

# 2. Системные зависимости (включая git)
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 ffmpeg git wget curl libgomp1 ninja-build \
    && rm -rf /var/lib/apt/lists/*

# 3. Установка ComfyUI (Фиксируем стабильный коммит)
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI && \
    cd /ComfyUI && \
    git reset --hard 57164eb86716075f756627038e9323f95e505888

WORKDIR /ComfyUI

# 4. Установка Python-пакетов
# Сначала базовые требования Comfy, затем специфичные для видео
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install runpod websocket-client opencv-python-headless accelerate \
    transformers>=4.48.0 diffusers>=0.31.0 torchao sageattention \
    onnx onnxruntime-gpu imageio imageio-ffmpeg \
    flash-attn --no-build-isolation

# 5. Установка нод
RUN cd custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git

# Установка зависимостей нод (если есть)
RUN pip install -r custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt || true

# 6. Копирование файлов проекта
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY handler.py /ComfyUI/handler.py
COPY new_Wan22_api.json /ComfyUI/new_Wan22_api.json
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Создаем структуру папок для сетевого диска
RUN mkdir -p /ComfyUI/models/diffusion_models /ComfyUI/models/loras /ComfyUI/models/vae /ComfyUI/models/clip /ComfyUI/models/clip_vision

ENTRYPOINT ["/entrypoint.sh"]