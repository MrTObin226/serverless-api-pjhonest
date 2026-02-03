# Образ для RunPod Serverless: фото -> видео (Wan2.2), RTX 4090
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

WORKDIR /workspace

# 1. Системные зависимости
RUN apt-get update && apt-get install -y \
    python3-pip python3-dev git wget ffmpeg \
    libgl1-mesa-glx libglib2.0-0 build-essential libssl-dev libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Pip и зависимости RunPod
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir runpod requests Pillow websocket-client numpy

# 3. ComfyUI и его зависимости (могут поставить старый torch — перезатрём ниже)
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /workspace/ComfyUI && \
    pip3 install --no-cache-dir -r /workspace/ComfyUI/requirements.txt

# 4. PyTorch 2.4+ с CUDA 12.1 (обязательно после ComfyUI: torch.uint64 и поддержка)
RUN pip3 install --no-cache-dir --force-reinstall \
    torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 \
    --index-url https://download.pytorch.org/whl/cu121

# 5. Кастомные ноды для Wan2.2 и видео
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    pip3 install --no-cache-dir -r ComfyUI-WanVideoWrapper/requirements.txt && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    pip3 install --no-cache-dir -r ComfyUI-VideoHelperSuite/requirements.txt

# 6. Копируем только нужные файлы (handler, workflow, entrypoint, config)
COPY handler.py /workspace/handler.py
COPY new_Wan22_api.json /workspace/new_Wan22_api.json
COPY entrypoint.sh /workspace/entrypoint.sh
COPY extra_model_paths.yaml /workspace/ComfyUI/extra_model_paths.yaml

# 7. Папки и права
RUN mkdir -p /workspace/ComfyUI/input /workspace/ComfyUI/output \
    /workspace/ComfyUI/models/checkpoints \
    /workspace/ComfyUI/models/clip \
    /workspace/ComfyUI/models/vae \
    /workspace/ComfyUI/models/loras \
    && chmod +x /workspace/entrypoint.sh

# RunPod монтирует том с моделями в /runpod-volume
# Симлинки создаются в entrypoint при старте
ENTRYPOINT ["/workspace/entrypoint.sh"]
