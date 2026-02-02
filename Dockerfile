# 1. Используем официальный образ NVIDIA с самым свежим стеком CUDA для RTX 50-й серии
FROM nvidia/cuda:12.8.0-devel-ubuntu22.04

# Устанавливаем системные зависимости и Python 3.11
RUN apt-get update && apt-get install -y \
    python3.11 python3.11-dev python3-pip \
    libgl1 libglib2.0-0 ffmpeg git wget curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Делаем Python 3.11 основным
RUN ln -sf /usr/bin/python3.11 /usr/bin/python

# 2. Устанавливаем PyTorch 2.6.0+, скомпилированный под CUDA 12.8
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# Клонируем ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI
WORKDIR /ComfyUI

# 3. Устанавливаем зависимости. Добавлены onnxruntime-gpu и sageattention для Wan 2.2
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install runpod websocket-client opencv-python-headless accelerate \
    transformers>=4.48.0 diffusers>=0.31.0 ftfy Pillow einops safetensors \
    sentencepiece imageio imageio-ffmpeg "huggingface_hub[hf_transfer]" \
    onnxruntime-gpu --extra-index-url https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/

# 4. Установка SageAttention (очень важно для скорости Wan 2.2 на Blackwell)
RUN pip install sageattention

# Клонируем ноды
RUN cd custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git

# Установка зависимостей нод (игнорируем ошибки, если что-то уже есть)
RUN pip install -r custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt || true

# 5. Настройка переменных окружения для RTX 5090 (sm_120)
ENV TORCH_CUDA_ARCH_LIST="9.0;10.0;12.0"
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Копируем файлы проекта
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY handler.py /ComfyUI/handler.py
COPY new_Wan22_api.json /ComfyUI/new_Wan22_api.json
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

# Создаем структуру папок
RUN mkdir -p /ComfyUI/models/diffusion_models /ComfyUI/models/loras /ComfyUI/models/clip_vision /ComfyUI/models/vae /ComfyUI/models/clip

# Запуск через наш скрипт
ENTRYPOINT ["/entrypoint.sh"]