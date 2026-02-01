FROM wlsdml1114/engui_genai-base_blackwell:1.1

# 1. Системные зависимости (минимум для работы с видео)
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 libglvnd0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 2. Ускоритель загрузки моделей
RUN pip install -U "huggingface_hub[hf_transfer]" && \
    pip install runpod websocket-client && \
    export HF_HUB_ENABLE_HF_TRANSFER=1

# 3. ComfyUI (БЕЗ ПРОБЕЛОВ после .git!)
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI
WORKDIR /ComfyUI
RUN pip install -r requirements.txt

# 4. ВСЕ ЗАВИСИМОСТИ ОДНОЙ КОМАНДОЙ (без конфликтов!)
RUN pip install opencv-python-headless accelerate transformers>=4.36.0 diffusers>=0.24.0 ftfy Pillow einops safetensors imageio imageio-ffmpeg gguf>=0.5.0 sentencepiece huggingface-hub

# 5. КРИТИЧЕСКАЯ ПРОВЕРКА (падает НА ЭТАПЕ СБОРКИ!)
RUN python -c "import ftfy, cv2, gguf, sentencepiece; print('✅ Зависимости установлены')" || (echo '❌ ОШИБКА' && exit 1)

# 6. ТОЛЬКО 2 РАБОЧИЕ НОДЫ (БЕЗ ПРОБЕЛОВ!)
RUN cd /ComfyUI/custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git

# 7. Модели (БЕЗ ПРОБЕЛОВ перед -O! ПРАВИЛЬНЫЕ ПУТИ!)
RUN mkdir -p /ComfyUI/models/diffusion_models /ComfyUI/models/loras /ComfyUI/models/clip_vision /ComfyUI/models/vae /ComfyUI/models/clip

RUN wget -q https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors -O /ComfyUI/models/diffusion_models/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors && \
    wget -q https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors -O /ComfyUI/models/clip_vision/clip_vision_h.safetensors && \
    wget -q https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors -O /ComfyUI/models/clip/umt5-xxl-enc-bf16.safetensors && \
    wget -q https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors -O /ComfyUI/models/vae/Wan2_1_VAE_bf16.safetensors && \
    wget -q https://huggingface.co/lightx2v/Wan2.2-Lightning/resolve/main/Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1/high_noise_model.safetensors -O /ComfyUI/models/loras/high_noise_model.safetensors

# 7. Исправленное скачивание Лоры (используем curl с User-Agent и токеном)
RUN curl -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
         -L "https://civitai.com/api/download/models/2553271?token=c056bf57d3819491f7ffd7bb814ea189" \
         -o /ComfyUI/models/loras/cyberpunk_style.safetensors -f || \
    (echo "❌ Ошибка скачивания! Проверьте токен или доступность модели" && exit 1)
# 8. Файлы
COPY extra_model_paths.yaml /ComfyUI/
COPY handler.py new_Wan22_api.json /ComfyUI/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
