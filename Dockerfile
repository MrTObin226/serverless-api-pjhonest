FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

WORKDIR /workspace

# Установка системных утилит
RUN apt-get update && apt-get install -y \
    python3-pip git wget ffmpeg libgl1-mesa-glx libglib2.0-0

# Копируем конфиги и скрипты
COPY . .

# Установка библиотек для RunPod и работы с API
RUN pip3 install --no-cache-dir runpod requests

# Важно: устанавливаем зависимости самого ComfyUI (на всякий случай)
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Запуск обработчика
RUN chmod +x /workspace/entrypoint.sh
CMD ["/workspace/entrypoint.sh"]