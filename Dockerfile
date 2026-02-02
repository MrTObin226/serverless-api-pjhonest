# 1. База для RTX 4090 (PyTorch 2.5 + CUDA 12.4)
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

# Системные зависимости
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 ffmpeg git wget curl libgomp1 ninja-build \
    && rm -rf /var/lib/apt/lists/*

# 2. Клонируем ComfyUI и ОТКАТЫВАЕМСЯ на стабильный коммит (январь 2025)
# Это решает ошибку "'ModelPatcher' object is not iterable" и "load_model_gpu"
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI && \
    cd /ComfyUI && \
    git checkout 57164eb

WORKDIR /ComfyUI

# 3. Установка Python-пакетов
# Добавил 'onnx' и явный 'imageio-ffmpeg'
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install runpod websocket-client opencv-python-headless accelerate \
    transformers>=4.48.0 diffusers>=0.31.0 torchao sageattention \
    onnx onnxruntime-gpu imageio imageio-ffmpeg \
    flash-attn --no-build-isolation

# 4. Клонируем ноды
RUN cd custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git

# 5. Установка зависимостей нод
RUN pip install -r custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt || true

# 6. Копируем файлы проекта
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY handler.py /ComfyUI/handler.py
COPY new_Wan22_api.json /ComfyUI/new_Wan22_api.json
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Создаем структуру папок
RUN mkdir -p /ComfyUI/models/diffusion_models /ComfyUI/models/loras /ComfyUI/models/vae /ComfyUI/models/clip /ComfyUI/models/clip_vision

ENTRYPOINT ["/entrypoint.sh"]