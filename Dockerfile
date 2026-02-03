FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

WORKDIR /workspace

# 1. Системные зависимости
RUN apt-get update && apt-get install -y \
    python3-pip git wget ffmpeg libgl1-mesa-glx libglib2.0-0 \
    build-essential libssl-dev libffi-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. PyTorch 2.1 + CUDA 12.1
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 \
    --index-url https://download.pytorch.org/whl/cu121

# 3. Базовые зависимости
RUN pip3 install --no-cache-dir \
    runpod==1.5.2 \
    requests aiohttp Pillow websocket-client \
    einops tqdm pyyaml safetensors opencv-python-headless \
    xformers==0.0.23.post1

# 4. Чистый ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git && \
    cd ComfyUI && \
    pip3 install --no-cache-dir -r requirements.txt

# 5. Только нужные кастомные ноды
WORKDIR /workspace/ComfyUI/custom_nodes

RUN git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    pip3 install --no-cache-dir -r ComfyUI-WanVideoWrapper/requirements.txt

RUN git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    pip3 install --no-cache-dir -r ComfyUI-VideoHelperSuite/requirements.txt

RUN git clone https://github.com/city96/ComfyUI-GGUF.git && \
    pip3 install --no-cache-dir -r ComfyUI-GGUF/requirements.txt

# 6. Копируем ваши файлы
WORKDIR /workspace
COPY . .

# 7. Создаём папки и права
RUN mkdir -p /workspace/ComfyUI/input /workspace/ComfyUI/output && \
    chmod +x /workspace/entrypoint.sh

# 8. Копируем конфиг
COPY config.yaml /workspace/ComfyUI/config.yaml

ENTRYPOINT ["/workspace/entrypoint.sh"]