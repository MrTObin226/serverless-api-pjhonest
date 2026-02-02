# Стабильная база
FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

# Добавили libgomp1 и очистку кэша
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 ffmpeg git wget curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Клонируем ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI
WORKDIR /ComfyUI

# Расширенный список pip-пакетов для Wan 2.2
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install runpod websocket-client opencv-python-headless accelerate \
    transformers>=4.36.0 diffusers>=0.24.0 ftfy Pillow einops safetensors \
    sentencepiece imageio imageio-ffmpeg "huggingface_hub[hf_transfer]"

# Клонируем ноды
RUN cd custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git

# Установка зависимостей нод
RUN pip install -r custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt || true

# Копируем конфиги ПРЯМО в /ComfyUI
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY handler.py /ComfyUI/handler.py
COPY new_Wan22_api.json /ComfyUI/new_Wan22_api.json
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

# Важно: ComfyUI иногда ищет модели в папке models, создадим их на всякий случай
RUN mkdir -p /ComfyUI/models/diffusion_models /ComfyUI/models/loras /ComfyUI/models/clip_vision /ComfyUI/models/vae /ComfyUI/models/clip

CMD ["/entrypoint.sh"]