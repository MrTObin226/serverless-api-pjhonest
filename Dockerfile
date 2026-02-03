# Используем официальный образ с уже настроенной CUDA и готовым PyTorch
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 1. Системные зависимости (Минимум для работы видео и сборки пакетов)
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 ffmpeg git wget curl unzip libgomp1 \
    build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 2. Оптимизации для A100 (SXM требует правильной аллокации памяти)
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
ENV TORCH_CUDNN_SDPA_ENABLED=1

# 3. Установка ComfyUI
RUN git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git /ComfyUI
WORKDIR /ComfyUI

# 4. Установка зависимостей (Ставим все сразу, чтобы избежать конфликтов при инсталляции нод)
# Мы НЕ используем 'pip install -e .', так как это часто ломает билд в Docker
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
    runpod websocket-client aiohttp requests \
    "av>=12.0.0" "decord>=0.6.0" einops \
    opencv-python-headless imageio imageio-ffmpeg \
    accelerate transformers>=4.48.0 diffusers>=0.31.0 \
    torchao sageattention xformers

# 5. Клонируем ноды
RUN cd custom_nodes && \
    git clone --depth 1 https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone --depth 1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Manager.git && \
    git clone --depth 1 https://github.com/city96/ComfyUI-GGUF.git

# 6. Установка специфичных требований нод (пропускаем установку через setup.py)
RUN pip install --no-cache-dir -r custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt || true
RUN pip install --no-cache-dir -r custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt || true

# 7. Файлы проекта
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY handler.py /ComfyUI/handler.py
COPY new_Wan22_api.json /ComfyUI/new_Wan22_api.json
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh && \
    mkdir -p /ComfyUI/input /ComfyUI/output /ComfyUI/models

ENTRYPOINT ["/entrypoint.sh"]