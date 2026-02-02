# 1. База для RTX 4090
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

# Системные зависимости + ninja для быстрой сборки flash-attn
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 ffmpeg git wget curl libgomp1 ninja-build \
    && rm -rf /var/lib/apt/lists/*

# 2. Клонируем САМЫЙ СВЕЖИЙ ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI
WORKDIR /ComfyUI

# --- ИСПРАВЛЕНИЕ ОШИБКИ load_model_gpu ---
# Мы просто меняем старое имя функции на новое прямо в файле, который вызвал ошибку
RUN sed -i 's/load_model_gpu/load_models_gpu/g' /ComfyUI/comfy/clip_vision.py

# 3. Установка пакетов
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install runpod websocket-client opencv-python-headless accelerate \
    transformers>=4.48.0 diffusers>=0.31.0 torchao sageattention onnxruntime-gpu \
    flash-attn --no-build-isolation

# 4. Клонируем только нужные ноды для Wan 2.2 и LoRA
RUN cd custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git

# Установка зависимостей нод
RUN pip install -r custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt || true

# 5. Копируем конфиги и скрипты
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY handler.py /ComfyUI/handler.py
COPY new_Wan22_api.json /ComfyUI/new_Wan22_api.json
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 6. Создаем структуру папок (включая clip_vision для фото-в-видео)
RUN mkdir -p /ComfyUI/models/diffusion_models /ComfyUI/models/loras /ComfyUI/models/vae /ComfyUI/models/clip /ComfyUI/models/clip_vision

ENTRYPOINT ["/entrypoint.sh"]