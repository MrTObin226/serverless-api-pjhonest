# 1. База - стабильный образ PyTorch с поддержкой CUDA 12.4
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

# Убираем интерактивные вопросы
ENV DEBIAN_FRONTEND=noninteractive

# 2. Системные зависимости (включая git и unzip)
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 ffmpeg git wget curl unzip libgomp1 ninja-build \
    && rm -rf /var/lib/apt/lists/*

# 3. Скачиваем ComfyUI как АРХИВ (обход ошибки 128)
# Берем коммит 57164eb (Январь 2025) - он проверен с WanVideo
RUN wget https://github.com/comfyanonymous/ComfyUI/archive/2ff3104f70767a897e5468a0fe632fbd5a432b40.zip -O /comfy.zip && \
    unzip /comfy.zip && \
    mv /ComfyUI-2ff3104f70767a897e5468a0fe632fbd5a432b40 /ComfyUI && \
    rm /comfy.zip

WORKDIR /ComfyUI

# 4. Установка Python-пакетов (в один слой, чтобы pip не терялся)
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install runpod websocket-client opencv-python-headless accelerate \
    transformers>=4.48.0 diffusers>=0.31.0 torchao sageattention \
    onnx onnxruntime-gpu imageio imageio-ffmpeg \
    flash-attn --no-build-isolation

# 5. Клонируем только нужные ноды (с --depth 1 для скорости)
RUN cd custom_nodes && \
    git clone --depth 1 https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone --depth 1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Manager.git

# Установка зависимостей для нод
RUN pip install -r custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt || true

# 6. Копируем ТВОИ файлы проекта (они должны лежать в корне твоего репозитория)
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY handler.py /ComfyUI/handler.py
COPY new_Wan22_api.json /ComfyUI/new_Wan22_api.json
COPY entrypoint.sh /entrypoint.sh

# Права и папки
RUN chmod +x /entrypoint.sh && \
    mkdir -p /ComfyUI/input /ComfyUI/output

# На RTX 4090 (Blackwell/Lovelace) эти переменные ускоряют работу
ENV PYTHONUNBUFFERED=1
ENV CUDA_DEVICE_ORDER=PCI_BUS_ID

ENTRYPOINT ["/entrypoint.sh"]