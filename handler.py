import runpod
import torch
import os
import base64
from diffusers import WanImageToVideoPipeline
from PIL import Image
import io

# Путь к нашей "флешке" внутри RunPod
MODEL_PATH = "/runpod-volume/wan21-i2v-480p"

pipe = None

def load_models():
    global pipe
    # Используем bfloat16 для экономии памяти и FP8 для скорости
    pipe = WanImageToVideoPipeline.from_pretrained(MODEL_PATH, torch_dtype=torch.bfloat16)
    pipe.to("cuda")
    # Включаем TeaCache для 2х ускорения
    # pipe.enable_teacache(threshold=0.1)

def handler(job):
    job_input = job['input']
    prompt = job_input.get('prompt')
    image_b64 = job_input.get('image')
    lora_name = job_input.get('lora') # Если нужно дополнение

    # Декодируем фото
    image_data = base64.b64decode(image_b64)
    init_image = Image.open(io.BytesIO(image_data)).convert("RGB")

    # Если есть LoRA
    if lora_name:
        pipe.load_lora_weights(f"/runpod-volume/loras/{lora_name}")

    # Генерация (ставим 480p для экономии денег)
    video_frames = pipe(
        prompt,
        image=init_image,
        num_frames=81,
        target_shape=(480, 832) # Экономное разрешение
    ).frames[0]

    # Сохраняем видео (здесь нужно добавить загрузку в S3, как обсуждали ранее)
    # Для теста вернем имитацию ссылки
    return {"video_url": "https://your-s3-storage.com/output_video.mp4"}

if __name__ == "__main__":
    load_models()
    runpod.serverless.start({"handler": handler})