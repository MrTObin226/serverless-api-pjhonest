# Вместо Blackwell-образа берем официальный стабильный PyTorch от RunPod
FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

# 1. Системные зависимости
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 libglvnd0 ffmpeg git wget curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Python-зависимости (без тяжелых моделей билд пролетит за секунды)
RUN pip install -U "huggingface_hub[hf_transfer]" runpod websocket-client opencv-python-headless accelerate transformers>=4.36.0 diffusers>=0.24.0 ftfy Pillow einops safetensors imageio imageio-ffmpeg gguf>=0.5.0 sentencepiece huggingface-hub

# 3. ComfyUI + ноды
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI && \
    cd /ComfyUI && pip install -r requirements.txt && \
    cd custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git

# 4. Создаем пустые папки (модели подцепятся из Volume)
RUN mkdir -p /ComfyUI/models/diffusion_models /ComfyUI/models/loras /ComfyUI/models/clip_vision /ComfyUI/models/vae /ComfyUI/models/clip /ComfyUI/input /ComfyUI/output

# 5. Копируем конфиги и код
WORKDIR /ComfyUI
COPY extra_model_paths.yaml .
COPY handler.py .
COPY new_Wan22_api.json .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]