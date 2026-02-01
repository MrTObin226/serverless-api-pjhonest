import runpod
import os
import json
import requests
import time
import base64
import uuid

COMFY_URL = "http://127.0.0.1:8188"
WORKFLOW_FILE = "/ComfyUI/new_Wan22_api.json"
INPUT_DIR = "/ComfyUI/input"
OUTPUT_DIR = "/ComfyUI/output"


def wait_for_comfy():
    print("⏳ Ожидание запуска ComfyUI...")
    for _ in range(120):  # Увеличил до 120 сек, Wan грузится долго
        try:
            res = requests.get(f"{COMFY_URL}/object_info")
            if res.status_code == 200:
                print("✅ ComfyUI запущен!")
                return
        except:
            time.sleep(1)
    raise Exception("ComfyUI не запустился вовремя")


def save_base64_image(b64_string):
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    image_data = base64.b64decode(b64_string)

    filename = f"input_{uuid.uuid4()}.png"
    file_path = os.path.join(INPUT_DIR, filename)

    os.makedirs(INPUT_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(image_data)
    return filename


def handler(job):
    try:
        job_input = job['input']

        # 1. Обработка входящего фото
        b64_image = job_input.get("image_base64") or job_input.get("image")
        if not b64_image:
            return {"error": "Image is required (image_base64)"}

        image_filename = save_base64_image(b64_image)

        # 2. Загрузка воркфлоу
        with open(WORKFLOW_FILE, "r") as f:
            workflow = json.load(f)

        # 3. Динамическая настройка параметров
        # Узел 244: Загрузка изображения
        if "244" in workflow:
            workflow["244"]["inputs"]["image"] = image_filename

        # Узел 135: Промпт
        if "135" in workflow:
            workflow["135"]["inputs"]["positive_prompt"] = job_input.get("prompt", "cinematic motion, high quality")

        # Узел 220: Сид и шаги
        if "220" in workflow:
            seed = job_input.get("seed", int(time.time() * 1000) % 1000000000)
            workflow["220"]["inputs"]["seed"] = seed
            workflow["220"]["inputs"]["steps"] = job_input.get("steps", 15)

        # Узел 541: Длина видео (кадры)
        num_frames = job_input.get("frames", 81)  # Можно слать 49, 61 или 81
        if "541" in workflow:
            workflow["541"]["inputs"]["num_frames"] = num_frames

        # Узел 498: Контекст (должен совпадать с длиной видео)
        if "498" in workflow:
            workflow["498"]["inputs"]["context_frames"] = num_frames

        # 4. Отправка задачи в ComfyUI
        client_id = str(uuid.uuid4())
        payload = {"prompt": workflow, "client_id": client_id}
        res = requests.post(f"{COMFY_URL}/prompt", json=payload)

        if res.status_code != 200:
            return {"error": f"ComfyUI Error: {res.text}"}

        prompt_id = res.json().get('prompt_id')

        # 5. Ожидание результата
        start_time = time.time()
        timeout = job_input.get("timeout", 600)  # WanVideo требует времени

        while True:
            if time.time() - start_time > timeout:
                return {"error": "Generation timeout"}

            history_res = requests.get(f"{COMFY_URL}/history/{prompt_id}")
            if history_res.status_code == 200:
                history = history_res.json()
                if prompt_id in history:
                    # Ищем выходной файл в узле 131 (VHS_VideoCombine)
                    outputs = history[prompt_id].get('outputs', {})
                    video_info = outputs.get("131", {}).get("videos", [{}])[0]
                    video_filename = video_info.get("filename")

                    if video_filename:
                        video_path = os.path.join(OUTPUT_DIR, video_filename)

                        if os.path.exists(video_path):
                            with open(video_path, "rb") as f:
                                video_b64 = base64.b64encode(f.read()).decode('utf-8')

                            # Чистим за собой
                            os.remove(video_path)
                            os.remove(os.path.join(INPUT_DIR, image_filename))

                            return {"video_url": f"data:video/mp4;base64,{video_b64}", "seed": seed}

            time.sleep(2)

    except Exception as e:
        return {"error": str(e)}


# Запуск
wait_for_comfy()
runpod.serverless.start({"handler": handler})