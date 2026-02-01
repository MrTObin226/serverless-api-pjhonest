FROM wlsdml1114/engui_genai-base_blackwell:1.1

# 1. Системные зависимости
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 libglvnd0 ffmpeg \
    curl build-essential python3-dev wget git \
    && rm -rf /var/lib/apt/lists/*

# 2. Установка критических библиотек ПЕРВЫМ делом
RUN python -m pip install --upgrade pip
RUN python -m pip install --no-cache-dir gguf pandas sentencepiece
# Пытаемся поставить sageattn, если не выйдет - идем дальше
RUN python -m pip install --no-cache-dir sageattn || echo "SageAttn install failed, skipping..."

# 3. ComfyUI и остальные зависимости
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI
WORKDIR /ComfyUI
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir opencv-python-headless accelerate transformers diffusers ftfy Pillow einops imageio-ffmpeg

# 4. Кастомные ноды
RUN cd /ComfyUI/custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git

# 5. Модели (Исправлены пути!)
RUN mkdir -p /ComfyUI/models/diffusion_models /ComfyUI/models/loras /ComfyUI/models/clip_vision /ComfyUI/models/vae /ComfyUI/models/text_encoders

RUN wget -q https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors -O /ComfyUI/models/diffusion_models/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors && \
    wget -q https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors -O /ComfyUI/models/clip_vision/clip_vision_h.safetensors && \
    wget -q https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors -O /ComfyUI/models/text_encoders/umt5-xxl-enc-bf16.safetensors && \
    wget -q https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors -O /ComfyUI/models/vae/Wan2_1_VAE_bf16.safetensors && \
    wget -q https://huggingface.co/lightx2v/Wan2.2-Lightning/resolve/main/Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1/high_noise_model.safetensors -O /ComfyUI/models/loras/high_noise_model.safetensors

# 6. LoRA стиля
RUN curl -L "https://civitai.com/api/download/models/2553271?type=Model&format=SafeTensor" -o /ComfyUI/models/loras/cyberpunk_style.safetensors

# 7. Конфиги
COPY extra_model_paths.yaml /ComfyUI/
COPY handler.py new_Wan22_api.json /ComfyUI/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]