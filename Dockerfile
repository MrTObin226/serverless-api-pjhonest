# Используем твой базовый образ
FROM wlsdml1114/engui_genai-base_blackwell:1.1

# 1. Системные зависимости + инструменты для скачивания (git, wget, curl)
# Добавлен git (чтобы не было ошибки в логах) и wget/curl для работы скрипта запуска
RUN apt-get update && apt-get install -y \
    git wget curl ffmpeg \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 libglvnd0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Ускоритель загрузки и основные библиотеки для RunPod
RUN pip install -U "huggingface_hub[hf_transfer]" && \
    pip install runpod websocket-client boto3 && \
    export HF_HUB_ENABLE_HF_TRANSFER=1

# 3. Установка ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI
WORKDIR /ComfyUI
RUN pip install -r requirements.txt

# 4. Зависимости для работы нейросетей и кастомных нод
RUN pip install opencv-python-headless accelerate transformers>=4.36.0 \
    diffusers>=0.24.0 ftfy Pillow einops safetensors imageio \
    imageio-ffmpeg gguf>=0.5.0 sentencepiece huggingface-hub

# 5. Установка кастомных нод для WanVideo
RUN cd /ComfyUI/custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git

# 6. Создание структуры папок (модели НЕ качаем здесь, чтобы билд не упал!)
RUN mkdir -p /ComfyUI/models/diffusion_models \
             /ComfyUI/models/loras \
             /ComfyUI/models/clip_vision \
             /ComfyUI/models/vae \
             /ComfyUI/models/clip \
             /ComfyUI/input \
             /ComfyUI/output

# 7. Копируем твои файлы конфигурации и скрипты
# Убедись, что эти файлы лежат в той же папке, что и Dockerfile
COPY extra_model_paths.yaml /ComfyUI/
COPY handler.py /ComfyUI/
COPY new_Wan22_api.json /ComfyUI/
COPY entrypoint.sh /entrypoint.sh

# 8. Права доступа
RUN chmod +x /entrypoint.sh && \
    chmod -R 777 /ComfyUI/output /ComfyUI/input /ComfyUI/models

# Запуск через скрипт, который скачает модели при старте контейнера
CMD ["/entrypoint.sh"]