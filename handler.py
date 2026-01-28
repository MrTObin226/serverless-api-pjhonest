import runpod
import os
import requests
import torch
from diffusers import WanImageToVideoPipeline
import base64
from PIL import Image
import io

# Константы из настроек RunPod
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ARCHIVE_ID = os.environ.get("ARCHIVE_CHANNEL_ID")
MODEL_PATH = "/runpod-volume/wan21-i2v-480p"

pipe = None


def load_model():
    global pipe
    if pipe is None:
        pipe = WanImageToVideoPipeline.from_pretrained(MODEL_PATH, torch_dtype=torch.bfloat16)
        pipe.to("cuda")


def handler(job):
    load_model()
    job_input = job['input']

    # Декодируем фото от бота
    image_data = base64.b64decode(job_input['image_b64'])
    init_image = Image.open(io.BytesIO(image_data)).convert("RGB")

    # Генерация (480p для экономии)
    video_frames = pipe(job_input['prompt'], image=init_image, num_frames=81, target_shape=(480, 832)).frames[0]

    # Сохраняем временно
    video_path = f"/tmp/{job['id']}.mp4"
    # (Тут нужен код сохранения video_frames в mp4 через export_to_video)

    # Отправка в архив Telegram
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    with open(video_path, 'rb') as f:
        res = requests.post(url, data={'chat_id': ARCHIVE_ID}, files={'video': f}).json()

    if res.get('ok'):
        return {"file_id": res['result']['video']['file_id']}
    return {"error": "Upload failed"}


runpod.serverless.start({"handler": handler})