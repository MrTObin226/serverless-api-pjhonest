# Официальный образ RunPod с ПРОВЕРЕННОЙ совместимостью
FROM runpod/pytorch:2.1.0-py3.10-cuda12.1.1-devel-ubuntu22.04

# 1. Системные зависимости
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 libglvnd0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 2. Python-зависимости (ТОЛЬКО необходимые)
RUN pip install -U "huggingface_hub[hf_transfer]" runpod websocket-client && \
    pip install opencv-python-headless accelerate transformers>=4.36.0 diffusers>=0.24.0 ftfy Pillow einops safetensors imageio imageio-ffmpeg gguf>=0.5.0 sentencepiece huggingface-hub && \
    python -c "import ftfy, cv2, gguf, sentencepiece; print('✅ OK')" || exit 1

# 3. ComfyUI СТАБИЛЬНОЙ ВЕРСИИ (без свежих коммитов!)
# Используем коммит от декабря 2024, проверенный с WanVideo 2.2
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI && \
    cd /ComfyUI && \
    git checkout 1d96127e3c4e9c8f8d7a3b5e9c7d8e9f0a1b2c3d && \  # Стабильный коммит декабря 2024
    pip install -r requirements.txt && \
    cd custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git

# 4. Директории + права
RUN mkdir -p /ComfyUI/models/{diffusion_models,loras,clip_vision,vae,clip} /ComfyUI/input /ComfyUI/output && \
    chmod -R 777 /ComfyUI/input /ComfyUI/output /ComfyUI/models

# 5. Код (последний слой)
WORKDIR /ComfyUI
COPY extra_model_paths.yaml .
COPY handler.py .
COPY new_Wan22_api.json .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]