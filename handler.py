import runpod
import os
import base64
import torch
from io import BytesIO
from PIL import Image

# --- Инициализация (вне хендлера) ---
# Это загрузится один раз при старте воркера
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")


# Здесь должен быть твой код загрузки Wan 2.2
# model = load_my_wan_model("/models/wan2.2")

def handler(job):
    """
    Основной обработчик задач
    """
    job_input = job["input"]

    # Достаем данные, которые прислал бот
    prompt = job_input.get("prompt")
    image_b64 = job_input.get("image")  # Ожидаем base64

    if not image_b64:
        return {"error": "Image is required"}

    try:
        # Пример обработки:
        # 1. Декодируем фото
        # 2. Генерируем видео через Wan 2.2
        # 3. Сохраняем и отдаем ссылку

        return {
            "video_url": "https://storage.googleapis.com/your-bucket/output.mp4",
            "status": "SUCCESS"
        }
    except Exception as e:
        return {"error": str(e)}


# --- ОБЯЗАТЕЛЬНАЯ СТРОКА ---
# Без неё RunPod выдает ошибку, которую ты видишь
runpod.serverless.start({"handler": handler})