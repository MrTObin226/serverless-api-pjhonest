FROM wlsdml1114/engui_genai-base_blackwell:1.1

# 1. Только необходимый минимум для работы видео
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 ffmpeg && rm -rf /var/lib/apt/lists/*

# 2. Установка ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI
WORKDIR /ComfyUI
RUN pip install -r requirements.txt

# 3. Установка ТОЛЬКО необходимых библиотек для Wan2.2
# ftfy - обязателен для их токенайзера
RUN pip install -U pip && \
    pip install opencv-python-headless accelerate transformers diffusers ftfy Pillow runpod websocket-client requests

# 4. Установка ТОЛЬКО одной нужной ноды
RUN cd /ComfyUI/custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git

# 5. Скачиваем ТОЛЬКО необходимые модели (Экономим ~20ГБ места)
RUN mkdir -p /ComfyUI/models/diffusion_models /ComfyUI/models/loras /ComfyUI/models/clip /ComfyUI/models/clip_vision /ComfyUI/models/vae

# Оставляем только HIGH версию, если нужна максимальная детализация
RUN wget -q https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors -O /ComfyUI/models/diffusion_models/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors && \
    wget -q https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors -O /ComfyUI/models/clip_vision/clip_vision_h.safetensors && \
    wget -q https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors -O /ComfyUI/models/clip/umt5-xxl-enc-bf16.safetensors && \
    wget -q https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors -O /ComfyUI/models/vae/Wan2_1_VAE_bf16.safetensors

# Твои LoRA
RUN wget -q https://huggingface.co/lightx2v/Wan2.2-Lightning/resolve/main/Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1/high_noise_model.safetensors -O /ComfyUI/models/loras/high_noise_model.safetensors
RUN curl -L "https://civitai.com/api/download/models/2553271?type=Model&format=SafeTensor" -o /ComfyUI/models/loras/cyberpunk_style.safetensors

# 6. Копируем только файлы управления
COPY handler.py /ComfyUI/handler.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]