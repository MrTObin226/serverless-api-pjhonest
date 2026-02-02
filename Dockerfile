FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 ffmpeg git wget curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI
WORKDIR /ComfyUI

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install runpod websocket-client opencv-python-headless accelerate \
    transformers>=4.48.0 diffusers>=0.31.0 torchao sageattention onnxruntime-gpu

RUN cd custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git

RUN pip install -r custom_nodes/ComfyUI-WanVideoWrapper/requirements.txt || true

COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY handler.py /ComfyUI/handler.py
COPY new_Wan22_api.json /ComfyUI/new_Wan22_api.json
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /ComfyUI/models/diffusion_models /ComfyUI/models/loras /ComfyUI/models/vae /ComfyUI/models/clip

ENTRYPOINT ["/entrypoint.sh"]