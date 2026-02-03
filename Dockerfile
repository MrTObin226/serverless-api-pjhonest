FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel
ENV DEBIAN_FRONTEND=noninteractive

# 1. Системные зависимости + критичные для видео-кодеков
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 ffmpeg git wget curl unzip libgomp1 ninja-build \
    build-essential cmake libx264-dev libx265-dev libvpx-dev libvorbis-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Оптимизации памяти для A100 (решает фрагментацию)
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:512
ENV CUDA_CACHE_DISABLE=1
ENV TORCH_CUDNN_SDPA_ENABLED=1

# 3. Сначала клонируем НОДЫ (чтобы установить их зависимости ДО ComfyUI)
RUN mkdir -p /ComfyUI/custom_nodes && cd /ComfyUI/custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git && \
    git clone https://github.com/city96/ComfyUI-GGUF.git

# 4. Устанавливаем КРИТИЧНЫЕ зависимости нод ДО установки ComfyUI (особенно 'av')
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir "av>=12.0.0" "decord>=0.6.0" "einops>=0.7.0" && \
    cd /ComfyUI/custom_nodes/ComfyUI-WanVideoWrapper && \
    pip install --no-cache-dir -e . && \
    cd /ComfyUI/custom_nodes/ComfyUI-VideoHelperSuite && \
    pip install --no-cache-dir -e .

# 5. Теперь клонируем СВЕЖИЙ ComfyUI (master содержит apply_rope1)
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI && \
    cd /ComfyUI && git pull

WORKDIR /ComfyUI

# 6. Устанавливаем зависимости ComfyUI (уже после установки нод)
RUN pip install --no-cache-dir -r requirements.txt

# 7. Дополнительные зависимости с ВЕРСИОННЫМИ ОГРАНИЧЕНИЯМИ для совместимости
RUN pip install --no-cache-dir \
    "runpod>=0.10.0" \
    "websocket-client>=1.8.0" \
    "opencv-python-headless>=4.10.0" \
    "accelerate>=0.34.0" \
    "transformers>=4.48.0,<4.49.0" \
    "diffusers>=0.31.0,<0.32.0" \
    "torchao>=0.7.0,<0.8.0" \
    "onnx>=1.16.0" \
    "onnxruntime-gpu>=1.19.0" \
    "imageio>=2.34.0" \
    "imageio-ffmpeg>=0.5.1"

# 8. Файлы проекта
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY handler.py /ComfyUI/handler.py
COPY new_Wan22_api.json /ComfyUI/new_Wan22_api.json
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh && mkdir -p /ComfyUI/input /ComfyUI/output /ComfyUI/models
ENV PYTHONUNBUFFERED=1
ENV COMFYUI_NORMAL_VRAM=1

ENTRYPOINT ["/entrypoint.sh"]