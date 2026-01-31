import runpod
import os
import json
import requests
import time
import base64
import uuid
from io import BytesIO

COMFY_URL = "http://127.0.0.1:8188"
WORKFLOW_FILE = "new_Wan22_api.json"


def wait_for_comfy():
    print("⏳ Ожидание запуска ComfyUI...")
    for _ in range(60):
        try:
            requests.get(COMFY_URL)
            print("✅ ComfyUI запущен!")
            return
        except:
            time.sleep(1)
    raise Exception("ComfyUI не запустился за 60 секунд")


def save_base64_image(b64_string, filename):
    # Убираем префикс data:image/..., если он есть
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]

    image_data = base64.b64decode(b64_string)
    input_dir = "/ComfyUI/input"
    os.makedirs(input_dir, exist_ok=True)
    file_path = os.path.join(input_dir, filename)

    with open(file_path, "wb") as f:
        f.write(image_data)
    return filename


def handler(job):
    job_input = job['input']

    # 1. Обработка изображения
    # Бот пришлет "image_base64", но мы поддержим и просто "image" на всякий случай
    b64_image = job_input.get("image_base64") or job_input.get("image")

    if not b64_image:
        return {"error": "No image provided. Please send 'image_base64'."}

    image_filename = f"upload_{uuid.uuid4()}.jpg"
    save_base64_image(b64_image, image_filename)

    # 2. Загрузка Workflow
    with open(WORKFLOW_FILE, "r") as f:
        workflow = json.load(f)

    # 3. Подстановка параметров
    prompt_text = job_input.get("prompt", "a cinematic video")
    steps = job_input.get("steps", 15)
    # Подстановка шагов в ноду 569
    if "569" in workflow:
        workflow["569"]["inputs"]["value"] = steps
    # Ищем ноды и меняем значения (ID взяты из твоего new_Wan22_api.json)
    if "244" in workflow:  # LoadImage
        workflow["244"]["inputs"]["image"] = image_filename

    if "135" in workflow:  # TextEncode
        workflow["135"]["inputs"]["positive_prompt"] = prompt_text

    if "220" in workflow:  # Sampler
        # Генерация случайного сида, если не передан
        seed = job_input.get("seed", int(time.time() * 1000) % 1000000000)
        workflow["220"]["inputs"]["seed"] = seed

    # 4. Отправка в ComfyUI
    client_id = str(uuid.uuid4())
    payload = {"prompt": workflow, "client_id": client_id}

    res = requests.post(f"{COMFY_URL}/prompt", json=payload)
    if res.status_code != 200:
        return {"error": f"ComfyUI Error: {res.text}"}

    prompt_id = res.json().get('prompt_id')

    # 5. Ожидание результата
    while True:
        history_res = requests.get(f"{COMFY_URL}/history/{prompt_id}")
        if history_res.status_code == 200:
            history = history_res.json()
            if prompt_id in history:
                outputs = history[prompt_id].get('outputs', {})
                # Ищем видео (VHS_VideoCombine обычно node 131)
                for node_id, content in outputs.items():
                    # ЗАМЕНИТЕ цикл поиска на этот:
                    for node_id, content in outputs.items():
                        # Ищем именно ноду видео-комбайнера (131)
                        if node_id == "131" and 'videos' in content and content['videos']:
                            video_filename = content['videos'][0]['filename']
                            video_path = f"/ComfyUI/output/{video_filename}"

                            if os.path.exists(video_path):
                                with open(video_path, "rb") as f:
                                    video_b64 = base64.b64encode(f.read()).decode('utf-8')
                                    return {"video_url": f"data:video/mp4;base64,{video_b64}"}

                        # Fallback для крайних случаев (не основной путь!)
                        elif 'gifs' in content and content['gifs']:
                            # ... обработка GIF (не нужно для вашего случая)
                            pass

                        # Кодируем видео в base64 для возврата
                        with open(video_path, "rb") as f:
                            video_b64 = base64.b64encode(f.read()).decode('utf-8')
                            # Возвращаем с правильным префиксом для телеграма/веба
                            return {"video_url": f"data:video/mp4;base64,{video_b64}"}
        time.sleep(1)



wait_for_comfy()
runpod.serverless.start({"handler": handler})