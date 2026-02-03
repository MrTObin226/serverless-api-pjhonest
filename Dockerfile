FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

WORKDIR /workspace

# 1. Установка системных утилит
RUN apt-get update && apt-get install -y \
    python3-pip git wget ffmpeg libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Сначала копируем только requirements.txt для кэширования слоев
COPY requirements.txt .

# 3. Устанавливаем всё одним махом (включая torch нужной версии)
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
    pip3 install --no-cache-dir -r requirements.txt

# 4. Копируем остальной код (скрипты, json, yaml)
COPY . .

# 5. Права на запуск и старт
RUN chmod +x /workspace/entrypoint.sh
CMD ["/workspace/entrypoint.sh"]