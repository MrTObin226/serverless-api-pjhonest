FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

WORKDIR /workspace

# 1. Установка системных утилит (нужны для сборки некоторых python-пакетов)
RUN apt-get update && apt-get install -y \
    python3-pip git wget ffmpeg libgl1-mesa-glx libglib2.0-0 \
    build-essential python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Обновляем pip
RUN pip3 install --no-cache-dir --upgrade pip

# 3. Установка PyTorch (самый тяжелый слой, лучше ставить отдельно)
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 4. Установка всех библиотек напрямую (без requirements.txt)
RUN pip3 install --no-cache-dir \
    runpod \
    requests \
    aiohttp \
    Pillow \
    sqlalchemy \
    alembic \
    pi-heif \
    websocket-client \
    transformers \
    diffusers \
    accelerate \
    safetensors \
    opencv-python \
    scipy \
    filelock \
    numpy

# 5. Теперь копируем твой код (скрипты и json-воркфлоу)
COPY . .

# 6. Права на запуск и старт
RUN chmod +x /workspace/entrypoint.sh

# Запуск через оболочку для корректной работы путей
CMD ["/bin/bash", "/workspace/entrypoint.sh"]