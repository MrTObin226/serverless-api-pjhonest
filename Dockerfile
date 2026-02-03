FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

WORKDIR /workspace

# 1. Установка системных утилит
RUN apt-get update && apt-get install -y \
    python3-pip git wget ffmpeg libgl1-mesa-glx libglib2.0-0 \
    build-essential python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Обновляем pip и ставим Torch
RUN pip3 install --no-cache-dir --upgrade pip
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 3. Установка базовых библиотек (чтобы не зависеть от requirements.txt)
RUN pip3 install --no-cache-dir runpod requests aiohttp Pillow sqlalchemy alembic pi-heif websocket-client einops tqdm pyyaml

# 4. Клонируем ComfyUI и Custom Nodes ВНУТРЬ ОБРАЗА для установки их зависимостей
# Мы делаем это в /workspace/temp_install
WORKDIR /workspace/temp_install
RUN git clone https://github.com/comfyanonymous/ComfyUI.git . && \
    pip3 install --no-cache-dir -r requirements.txt

WORKDIR /workspace/temp_install/custom_nodes

# Список ваших расширений с установкой их требований
RUN git clone https://github.com/Comfy-Org/ComfyUI-Manager.git && \
    pip3 install --no-cache-dir -r ComfyUI-Manager/requirements.txt

RUN git clone https://github.com/city96/ComfyUI-GGUF && \
    pip3 install --no-cache-dir -r ComfyUI-GGUF/requirements.txt

RUN git clone https://github.com/kijai/ComfyUI-KJNodes && \
    pip3 install --no-cache-dir -r ComfyUI-KJNodes/requirements.txt

RUN git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite && \
    pip3 install --no-cache-dir -r ComfyUI-VideoHelperSuite/requirements.txt

RUN git clone https://github.com/kael558/ComfyUI-GGUF-FantasyTalking && \
    pip3 install --no-cache-dir -r ComfyUI-GGUF-FantasyTalking/requirements.txt

RUN git clone https://github.com/orssorbit/ComfyUI-wanBlockswap

RUN git clone https://github.com/kijai/ComfyUI-WanVideoWrapper && \
    pip3 install --no-cache-dir -r ComfyUI-WanVideoWrapper/requirements.txt

# Узлы от eddyhhlure1Eddy (здесь живет comfy_aimdo)
RUN git clone https://github.com/eddyhhlure1Eddy/IntelligentVRAMNode && \
    git clone https://github.com/eddyhhlure1Eddy/auto_wan2.2animate_freamtowindow_server && \
    git clone https://github.com/eddyhhlure1Eddy/ComfyUI-AdaptiveWindowSize

# 5. Возвращаемся в рабочую директорию и копируем ваши скрипты
WORKDIR /workspace
COPY . .

# Удаляем временную папку, зависимости уже в системе
RUN rm -rf /workspace/temp_install

RUN chmod +x /workspace/entrypoint.sh
CMD ["/bin/bash", "/workspace/entrypoint.sh"]