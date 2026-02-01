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


def upload_to_catbox(file_path):
    """Загрузка файла на Catbox.moe для обхода лимитов RunPod API"""
    print(f"🚀 Загрузка {file_path} на Catbox...")
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f},
                timeout=30
            )
        if response.status_code == 200:
            url = response.text.strip()
            print(f"✅ Файл доступен по ссылке: {url}")
            return url
        else:
            print(f"❌ Ошибка Catbox: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Исключение при загрузке: {str(e)}")
        return None


def wait_for_comfy():
    print("⏳ Ожидание запуска ComfyUI...")
    for _ in range(120):
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
        b64_image = job_input.get("image_base64") or job_input.get("image")
        if not b64_image:
            return {"error": "Image is required"}

        image_filename = save_base64_image(b64_image)

        with open(WORKFLOW_FILE, "r") as f:
            workflow = json.load(f)

        # Настройка воркфлоу
        if "244" in workflow: workflow["244"]["inputs"]["image"] = image_filename
        if "135" in workflow: workflow["135"]["inputs"]["positive_prompt"] = job_input.get("prompt", "cinematic motion")

        seed = job_input.get("seed", int(time.time() * 1000) % 1000000000)
        if "220" in workflow:
            workflow["220"]["inputs"]["seed"] = seed
            workflow["220"]["inputs"]["steps"] = job_input.get("steps", 15)

        num_frames = job_input.get("frames", 81)
        if "541" in workflow: workflow["541"]["inputs"]["num_frames"] = num_frames
        if "498" in workflow: workflow["498"]["inputs"]["context_frames"] = num_frames

        # Отправка в Comfy
        res = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow, "client_id": str(uuid.uuid4())})
        if res.status_code != 200: return {"error": f"ComfyUI Error: {res.text}"}
        prompt_id = res.json().get('prompt_id')

        start_time = time.time()
        timeout = job_input.get("timeout", 900)  # Увеличили до 15 минут

        while True:
            if time.time() - start_time > timeout:
                return {"error": "Generation timeout"}

            history_res = requests.get(f"{COMFY_URL}/history/{prompt_id}")
            if history_res.status_code == 200:
                history = history_res.json()
                if prompt_id in history:
                    outputs = history[prompt_id].get('outputs', {})
                    video_info = outputs.get("131", {}).get("videos", [{}])[0]
                    video_filename = video_info.get("filename")

                    if video_filename:
                        video_path = os.path.join(OUTPUT_DIR, video_filename)
                        if os.path.exists(video_path):
                            # ГЛАВНОЕ ИЗМЕНЕНИЕ: Загружаем вместо кодирования в Base64
                            video_url = upload_to_catbox(video_path)

                            if not video_url:
                                return {"error": "Failed to upload video to cloud"}

                            # Чистим файлы
                            os.remove(video_path)
                            os.remove(os.path.join(INPUT_DIR, image_filename))

                            return {"video_url": video_url, "seed": seed, "status": "success"}

            time.sleep(5)  # Ждем чуть дольше между проверками

    except Exception as e:
        return {"error": str(e)}


wait_for_comfy()
runpod.serverless.start({"handler": handler})