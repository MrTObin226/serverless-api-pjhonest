import runpod
import os
import json
import requests
import time
import base64
import uuid
import glob
import shutil  # Добавлено для удаления папок

COMFY_URL = "http://127.0.0.1:8188"
WORKFLOW_FILE = "/ComfyUI/new_Wan22_api.json"
INPUT_DIR = "/ComfyUI/input"
OUTPUT_BASE = "/ComfyUI/output"


def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def upload_to_transfer_sh(file_path):
    log(f"🚀 Загрузка {file_path} на transfer.sh...")
    try:
        with open(file_path, 'rb') as f:
            response = requests.put(
                f"https://transfer.sh/{os.path.basename(file_path)}",
                data=f, timeout=60
            )
        if response.status_code == 200:
            return response.text.strip()
    except Exception as e:
        log(f"❌ Ошибка загрузки: {str(e)}")
    return None


def encode_file_to_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')


def wait_for_comfy():
    log("⏳ Ожидание запуска ComfyUI...")
    for _ in range(120):
        try:
            if requests.get(f"{COMFY_URL}/object_info").status_code == 200:
                log("✅ ComfyUI готов!")
                return
        except:
            time.sleep(1)
    raise Exception("ComfyUI не запустился")


def handler(job):
    # Создаем уникальные ID и пути СРАЗУ
    request_id = str(uuid.uuid4())
    job_output_dir = os.path.join(OUTPUT_BASE, request_id)
    input_filename = f"input_{request_id}.png"
    input_path = os.path.join(INPUT_DIR, input_filename)

    try:
        job_input = job['input']
        b64_image = job_input.get("image_base64") or job_input.get("image")
        if not b64_image: return {"error": "Image is required"}

        # 1. Подготовка папок и входного файла
        os.makedirs(INPUT_DIR, exist_ok=True)
        os.makedirs(job_output_dir, exist_ok=True)

        if "," in b64_image: b64_image = b64_image.split(",")[1]
        with open(input_path, "wb") as f:
            f.write(base64.b64decode(b64_image))

        # 2. Настройка Workflow
        with open(WORKFLOW_FILE, "r") as f:
            workflow = json.load(f)

        if "244" in workflow: workflow["244"]["inputs"]["image"] = input_filename
        if "135" in workflow: workflow["135"]["inputs"]["positive_prompt"] = job_input.get("prompt", "cinematic motion")

        seed = job_input.get("seed", int(time.time() * 1000) % 1000000000)
        if "220" in workflow: workflow["220"]["inputs"]["seed"] = seed

        # КЛЮЧЕВОЙ МОМЕНТ: VHS Combine сохранит файл ВНУТРЬ нашей уникальной папки
        if "131" in workflow:
            workflow["131"]["inputs"]["filename_prefix"] = f"{request_id}/Wan"

        # 3. Отправка
        res = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow, "client_id": request_id})
        prompt_id = res.json().get('prompt_id')
        log(f"📢 Задача {request_id} отправлена. Seed: {seed}")

        start_time = time.time()
        timeout = job_input.get("timeout", 900)

        while True:
            if time.time() - start_time > timeout:
                return {"error": "Generation timeout"}

            history_res = requests.get(f"{COMFY_URL}/history/{prompt_id}")
            if history_res.status_code == 200:
                history = history_res.json()
                if prompt_id in history:
                    log(f"✅ Готово. Ищем файл в {job_output_dir}...")

                    # Ищем ТОЛЬКО в нашей папке. Никаких get_latest_video!
                    candidates = glob.glob(os.path.join(job_output_dir, "*.mp4"))

                    if not candidates:
                        return {"error": "Video file not found in job directory"}

                    video_path = candidates[0]
                    log(f"🎬 Файл найден: {video_path}")

                    # 4. Загрузка/Кодирование
                    video_url = upload_to_transfer_sh(video_path)

                    response_payload = {"seed": seed, "status": "success"}
                    if video_url:
                        response_payload["video_url"] = video_url
                    else:
                        log("⚠️ Используем Base64 fallback")
                        response_payload["video_base64"] = encode_file_to_base64(video_path)

                    return response_payload

            time.sleep(3)

    except Exception as e:
        log(f"❌ Критическая ошибка: {str(e)}")
        return {"error": str(e)}

    finally:
        # ГАРАНТИРОВАННАЯ ЧИСТКА: Удаляем входной файл и ВСЮ папку вывода
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(job_output_dir): shutil.rmtree(job_output_dir)


wait_for_comfy()
runpod.serverless.start({"handler": handler})