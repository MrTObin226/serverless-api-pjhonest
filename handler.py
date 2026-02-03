import runpod
import json
import base64
import time
import os
import requests
import random

# Настройки ComfyUI
COMFY_URL = "http://127.0.0.1:8188"
INPUT_DIR = "/ComfyUI/input"
OUTPUT_DIR = "/ComfyUI/output"


def check_server():
    try:
        requests.get(COMFY_URL, timeout=1)
        return True
    except:
        return False


def clear_dirs():
    """Очистка папок перед генерацией"""
    for d in [INPUT_DIR, OUTPUT_DIR]:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f != ".gitkeep":
                    try:
                        os.remove(os.path.join(d, f))
                    except:
                        pass


def handler(job):
    job_input = job["input"]

    # 1. Разбираем входные данные
    image_base64 = job_input.get("image_base64")
    prompt = job_input.get("prompt", "cinematic video")
    use_cyberpunk = job_input.get("use_cyberpunk", False)  # Флаг от бота
    seed = job_input.get("seed", random.randint(1, 999999999))

    if not image_base64:
        return {"error": "No image provided"}

    # 2. Очистка и сохранение картинки
    clear_dirs()
    image_name = f"input_{job['id']}.png"
    with open(os.path.join(INPUT_DIR, image_name), "wb") as f:
        f.write(base64.b64decode(image_base64.split(",")[-1]))

    # 3. Загрузка Workflow
    with open("new_Wan22_api.json", "r") as f:
        workflow = json.load(f)

    # 4. Модификация Workflow
    # Узел 3: Картинка
    workflow["3"]["inputs"]["image"] = image_name

    # Узел 6: Промпт (Позитивный)
    # Если киберпанк, добавляем триггерные слова
    full_prompt = prompt
    if use_cyberpunk:
        full_prompt = f"cyberpunk style, neon lights, high tech, {prompt}"

    workflow["6"]["inputs"]["prompt"] = full_prompt

    # Узел 4: LoRA (Cyberpunk)
    # Если use_cyberpunk=True, ставим силу 1.0, иначе 0.0 (отключаем)
    lora_strength = 1.0 if use_cyberpunk else 0.0
    workflow["4"]["inputs"]["strength_model"] = lora_strength
    # Важно: имя файла должно совпадать с тем, что ты скачал wget-ом
    workflow["4"]["inputs"]["lora_name"] = "cyberpunk_style.safetensors"

    # Узел 8: Сид и Шаги
    workflow["8"]["inputs"]["seed"] = seed
    # Для обычного Wan (не Lightning) нужно больше шагов, 20-30 оптимально.
    # Если ты используешь Lightning лору (она у тебя скачана как high_noise_model), то шагов нужно 4-8.
    # Но так как ты просил Cyberpunk Lora, она не Lightning.
    # Поэтому ставим универсальные 25 шагов.
    workflow["8"]["inputs"]["steps"] = 25

    # 5. Отправка в ComfyUI
    try:
        resp = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow}).json()
        prompt_id = resp["prompt_id"]
    except Exception as e:
        return {"error": f"ComfyUI Error: {e}"}

    # 6. Ожидание результата
    start = time.time()
    while time.time() - start < 600:  # 10 минут таймаут
        try:
            history = requests.get(f"{COMFY_URL}/history/{prompt_id}").json()
            if prompt_id in history:
                # Нашли результат
                outputs = history[prompt_id]["outputs"]
                # Узел 10 - VHS_VideoCombine
                if "10" in outputs:
                    filename = outputs["10"]["gifs"][0]["filename"]

                    # Читаем видео и кодируем в base64
                    with open(os.path.join(OUTPUT_DIR, filename), "rb") as f:
                        video_b64 = base64.b64encode(f.read()).decode()

                    return {
                        "status": "COMPLETED",
                        "video_base64": video_b64,
                        "seed": seed
                    }
        except:
            pass
        time.sleep(2)

    return {"error": "Timeout", "status": "FAILED"}


runpod.serverless.start({"handler": handler})