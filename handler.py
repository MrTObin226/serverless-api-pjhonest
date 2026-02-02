import runpod
import os
import json
import requests
import time
import base64
import uuid
import glob
import shutil

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
    request_id = str(uuid.uuid4())
    job_output_dir = os.path.join(OUTPUT_BASE, request_id)
    input_filename = f"input_{request_id}.png"
    input_path = os.path.join(INPUT_DIR, input_filename)

    try:
        job_input = job['input']
        b64_image = job_input.get("image_base64") or job_input.get("image")
        if not b64_image: return {"error": "Image is required"}

        os.makedirs(INPUT_DIR, exist_ok=True)
        os.makedirs(job_output_dir, exist_ok=True)

        if "," in b64_image: b64_image = b64_image.split(",")[1]
        with open(input_path, "wb") as f:
            f.write(base64.b64decode(b64_image))

        with open(WORKFLOW_FILE, "r") as f:
            workflow = json.load(f)

        # --- НАСТРОЙКА WORKFLOW ---
        # 1. Входное изображение
        if "244" in workflow:
            workflow["244"]["inputs"]["image"] = input_filename

        # 2. Промпт пользователя
        user_prompt = job_input.get("prompt", "cinematic motion")
        if "135" in workflow:
            workflow["135"]["inputs"]["positive_prompt"] = user_prompt

        # 3. Seed
        seed = job_input.get("seed", int(time.time() * 1000) % 1000000000)
        if "220" in workflow:
            workflow["220"]["inputs"]["seed"] = seed

        # 4. Логика Киберпанк LoRA
        # Если в промпте есть слово "cyberpunk" (регистронезависимо), включаем LoRA на 100%
        is_cyberpunk = "cyberpunk" in user_prompt.lower()
        if "280" in workflow:  # Узел LoRA Киберпанк
            workflow["280"]["inputs"]["strength"] = 0.8 if is_cyberpunk else 0.0
            log(f"🔧 Cyberpunk Mode: {'ON' if is_cyberpunk else 'OFF'}")

        # 5. Путь сохранения
        if "131" in workflow:
            workflow["131"]["inputs"]["filename_prefix"] = f"{request_id}/Wan"

        # --- ОТПРАВКА ЗАДАЧИ ---
        res = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow, "client_id": request_id})
        if res.status_code != 200:
            return {"error": f"ComfyUI Error: {res.text}"}

        prompt_id = res.json().get('prompt_id')
        log(f"📢 Задача {request_id} отправлена. Seed: {seed}")

        start_time = time.time()
        timeout = job_input.get("timeout", 900)  # 15 минут таймаут

        while True:
            if time.time() - start_time > timeout:
                return {"error": "Generation timeout"}

            history_res = requests.get(f"{COMFY_URL}/history/{prompt_id}")
            if history_res.status_code == 200:
                history = history_res.json()
                if prompt_id in history:
                    # Проверяем, была ли ошибка при генерации
                    run_data = history[prompt_id]
                    if not run_data.get('status', {}).get('completed', False):
                        # Пытаемся найти сообщение об ошибке в ответе
                        return {"error": "Generation failed inside ComfyUI"}

                    log(f"✅ Готово. Ищем файл в {job_output_dir}...")
                    candidates = glob.glob(os.path.join(job_output_dir, "*.mp4"))

                    if not candidates:
                        # Иногда файловая система тормозит, даем второй шанс
                        time.sleep(2)
                        candidates = glob.glob(os.path.join(job_output_dir, "*.mp4"))
                        if not candidates:
                            return {"error": "Video file not found created"}

                    video_path = candidates[0]
                    log(f"🎬 Файл найден: {video_path}")

                    video_url = upload_to_transfer_sh(video_path)
                    response = {"seed": seed, "status": "success"}

                    if video_url:
                        response["video_url"] = video_url
                    else:
                        response["video_base64"] = encode_file_to_base64(video_path)

                    return response

            time.sleep(3)

    except Exception as e:
        log(f"❌ Критическая ошибка: {str(e)}")
        return {"error": str(e)}

    finally:
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(job_output_dir): shutil.rmtree(job_output_dir)


wait_for_comfy()
runpod.serverless.start({"handler": handler})