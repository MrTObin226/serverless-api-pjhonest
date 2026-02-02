# Стабильная база, которую "понимают" все GPU на RunPod
FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

# Мы сами ставим всё системное, чтобы не зависеть от авторов образа
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 ffmpeg git wget curl \
    && rm -rf /var/lib/apt/lists/*

# Клонируем в корень, чтобы пути были короткими и понятными
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI
WORKDIR /ComfyUI

# Ставим зависимости (pip сам разберется с версиями)
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install runpod websocket-client opencv-python-headless accelerate transformers diffusers ftfy Pillow einops safetensors

# Копируем ТВОИ файлы (убедись, что они лежат в той же папке, где Dockerfile)
COPY extra_model_paths.yaml .
COPY handler.py .
COPY new_Wan22_api.json .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]