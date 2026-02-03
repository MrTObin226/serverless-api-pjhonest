FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel
ENV DEBIAN_FRONTEND=noninteractive

# 1. Системные зависимости
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 ffmpeg git wget curl unzip libgomp1 ninja-build \
    && rm -rf /var/lib/apt/lists/*

# 2. Скачиваем СВЕЖИЙ master ComfyUI (чтобы не было ошибки Outdated)
RUN curl -L https://github.com/comfyanonymous/ComfyUI/archive/refs/heads/master.zip -o /comfy.zip && \
    unzip /comfy.zip && \
    mv ComfyUI-master /ComfyUI && \
    rm /comfy.zip

WORKDIR /ComfyUI

# 3. Python-зависимости (добавлен пакет 'av')
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir runpod websocket-client opencv-python-headless accelerate \
    transformers>=4.48.0 diffusers>=0.31.0 torchao sageattention \
    onnx onnxruntime-gpu imageio imageio-ffmpeg av \
    flash-attn --no-build-isolation

# 4. Клонируем ноды
RUN cd custom_nodes && \
    git clone --depth 1 https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone --depth 1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Manager.git

# 5. ЖЕСТКИЙ ФИКС ИМПОРТОВ (исправляет обе вариации имен функций)
RUN sed -i 's/apply_rope1/apply_rope/g' /ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper/wanvideo/modules/model.py && \
    sed -i 's/apply_rope_comfy1/apply_rope_comfy/g' /ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper/wanvideo/modules/model.py

# Установка зависимостей нод
RUN pip install --no-cache-dir -r custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt || true

# 6. Файлы проекта
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY handler.py /ComfyUI/handler.py
COPY new_Wan22_api.json /ComfyUI/new_Wan22_api.json
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh && mkdir -p /ComfyUI/input /ComfyUI/output
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["/entrypoint.sh"]