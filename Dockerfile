FROM wlsdml1114/engui_genai-base_blackwell:1.1

# 1. Системные зависимости
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 libglvnd0 ffmpeg curl wget git \
    && rm -rf /var/lib/apt/lists/*

# 2. ComfyUI и зависимости (делаем это ОДИН РАЗ)
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI
RUN pip install -r /ComfyUI/requirements.txt
RUN pip install runpod websocket-client opencv-python-headless accelerate transformers>=4.36.0 \
    diffusers>=0.24.0 ftfy Pillow einops safetensors imageio imageio-ffmpeg \
    gguf>=0.5.0 sentencepiece huggingface-hub

# 3. Ноды (тоже редко меняются)
RUN cd /ComfyUI/custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git

# 4. СОЗДАЕМ ПАПКИ МОДЕЛЕЙ (Заранее)
RUN mkdir -p /ComfyUI/models/diffusion_models /ComfyUI/models/loras /ComfyUI/models/clip_vision /ComfyUI/models/vae /ComfyUI/models/clip

# 5. СКАЧИВАЕМ МОДЕЛИ (Этот слой будет жить в кеше вечно, пока не изменишь ссылки)
RUN wget -q https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors -O /ComfyUI/models/diffusion_models/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors && \
    wget -q https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors -O /ComfyUI/models/clip_vision/clip_vision_h.safetensors && \
    wget -q https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors -O /ComfyUI/models/clip/umt5-xxl-enc-bf16.safetensors && \
    wget -q https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors -O /ComfyUI/models/vae/Wan2_1_VAE_bf16.safetensors

# 6. СКАЧИВАЕМ ЛОРУ (Используем твой рабочий метод с curl)
RUN curl -H "User-Agent: Mozilla/5.0" \
         -L "https://civitai.com/api/download/models/2553271?token=c056bf57d3819491f7ffd7bb814ea189" \
         -o /ComfyUI/models/loras/cyberpunk_style.safetensors -f

# -------------------------------------------------------------------------
# КРИТИЧЕСКИЙ МОМЕНТ: КОПИРУЕМ ТВОИ ФАЙЛЫ В САМОМ КОНЦЕ
# Теперь, если ты изменишь handler.py, Docker начнет сборку ТОЛЬКО ОТСЮДА!
# -------------------------------------------------------------------------
WORKDIR /ComfyUI
COPY extra_model_paths.yaml ./
COPY handler.py ./
COPY new_Wan22_api.json ./
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]