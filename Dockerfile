# Используем базовый образ PyTorch с CUDA 12.1
FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /

# Установка системных пакетов
RUN apt-get update && apt-get install -y \
    git \
    wget \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Клонируем ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git

# Устанавливаем зависимости ComfyUI + RunPod
RUN pip install --no-cache-dir -r ComfyUI/requirements.txt
RUN pip install --no-cache-dir runpod requests

# --- Установка Custom Nodes ---
WORKDIR /ComfyUI/custom_nodes

# 1. WanVideo Wrapper (Kijai) - Самая оптимизированная нода для Wan
RUN git clone https://github.com/kijai/ComfyUI-WanVideo-Wrapper.git
RUN pip install --no-cache-dir -r ComfyUI-WanVideo-Wrapper/requirements.txt

# 2. Video Helper Suite (Для сборки видео)
RUN git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
RUN pip install --no-cache-dir -r ComfyUI-VideoHelperSuite/requirements.txt

WORKDIR /

# Копируем файлы проекта
COPY handler.py .
COPY workflow_api.json .
COPY entrypoint.sh .

# Права на запуск
RUN chmod +x entrypoint.sh

# Запуск
CMD ["./entrypoint.sh"]