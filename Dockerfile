FROM wlsdml1114/engui_genai-base_blackwell:1.1 as runtime

# 1. Системные зависимости (безопасный набор для OpenCV в headless-режиме)
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 libglvnd0 \
    libgdk-pixbuf2.0-0 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# 2. Клонируем ComfyUI ПЕРВЫМ делом
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI
WORKDIR /ComfyUI

# 3. Устанавливаем зависимости ComfyUI
RUN pip install -r requirements.txt

# 4. Устанавливаем ВСЕ дополнительные зависимости ОДНОЙ КОМАНДОЙ (после requirements.txt!)
RUN pip install -U pip && \
    pip install opencv-python-headless accelerate gguf imageio-ffmpeg einops transformers diffusers ftfy Pillow huggingface_hub[hf_transfer] runpod websocket-client requests

# 5. КРИТИЧЕСКАЯ ПРОВЕРКА: убедимся, что ftfy установлен ДО запуска ComfyUI
RUN python -c "import ftfy; import cv2; import accelerate; print('✅ Проверка зависимостей пройдена: ftfy, cv2, accelerate доступны')" || (echo '❌ КРИТИЧЕСКАЯ ОШИБКА: зависимости не установлены!' && exit 1)

# 6. Клонируем ТОЛЬКО необходимые ноды (минимизируем точки отказа)
RUN cd /ComfyUI/custom_nodes && \
    git clone https://github.com/Comfy-Org/ComfyUI-Manager.git && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git

# 7. Создаем структуру папок для моделей
RUN mkdir -p /ComfyUI/models/diffusion_models /ComfyUI/models/loras /ComfyUI/models/clip /ComfyUI/models/clip_vision /ComfyUI/models/vae

# 8. Скачиваем модели Wan2.2 (без лишних пробелов в командах!)
RUN wget -q https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors -O /ComfyUI/models/diffusion_models/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors && \
    wget -q https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-LOW_fp8_e4m3fn_scaled_KJ.safetensors -O /ComfyUI/models/diffusion_models/Wan2_2-I2V-A14B-LOW_fp8_e4m3fn_scaled_KJ.safetensors && \
    wget -q https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors -O /ComfyUI/models/clip_vision/clip_vision_h.safetensors && \
    wget -q https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors -O /ComfyUI/models/clip/umt5-xxl-enc-bf16.safetensors && \
    wget -q https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors -O /ComfyUI/models/vae/Wan2_1_VAE_bf16.safetensors && \
    wget -q https://huggingface.co/lightx2v/Wan2.2-Lightning/resolve/main/Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1/high_noise_model.safetensors -O /ComfyUI/models/loras/high_noise_model.safetensors && \
    wget -q https://huggingface.co/lightx2v/Wan2.2-Lightning/resolve/main/Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1/low_noise_model.safetensors -O /ComfyUI/models/loras/low_noise_model.safetensors

# 9. Cyberpunk LoRA (БЕЗ ПРОБЕЛОВ в URL!)
RUN curl -L -k "https://civitai.com/api/download/models/2553271?type=Model&format=SafeTensor" -o /ComfyUI/models/loras/cyberpunk_style.safetensors

# 10. Копируем ваши файлы
COPY . /ComfyUI/
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]