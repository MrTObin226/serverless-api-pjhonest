import runpod
import os
import base64
import requests
import time
import json
import uuid
import shutil


def wait_for_comfyui():
    print("⏳ Ожидание запуска ComfyUI...")
    while True:
        try:
            response = requests.get("http://127.0.0.1:8188/history")
            if response.status_code == 200:
                break
        except:
            time.sleep(2)


def handler(event):
    wait_for_comfyui()
    input_data = event["input"]
    job_id = event["id"]  # Уникальный ID запроса от RunPod
    prompt_text = input_data.get("prompt", "cyberpunk style, futuristic")
    image_url = input_data.get("image_url")

    with open("/workspace/new_Wan22_api.json", "r") as f:
        workflow = json.load(f)

    # 1. Индивидуальное имя файла для каждого пользователя
    input_filename = f"input_{job_id}.jpg"

    if image_url:
        try:
            img_data = requests.get(image_url, timeout=15).content
            input_path = f"/runpod-volume/ComfyUI/input/{input_filename}"
            with open(input_path, "wb") as f:
                f.write(img_data)

            for node in workflow.values():
                if node.get("class_type") == "LoadImage":
                    node["inputs"]["image"] = input_filename
        except Exception as e:
            print(f"❌ Ошибка загрузки фото: {e}")

    # 2. Настройка уникального префикса для выхода
    # Чтобы видео называлось 'output_ID_запроса_00001.mp4'
    output_prefix = f"output_{job_id}"
    for node in workflow.values():
        if node.get("class_type") in ["CLIPTextEncode", "WanVideoTextEncode"]:
            node["inputs"]["text"] = prompt_text

        # Меняем имя модели на скачанную тобой MEGA v10
        if node.get("class_type") == "WanVideoModelLoader":
            node["inputs"]["model"] = "wan2.2-rapid-mega-aio-v10.safetensors"

        # Настройка ноды сохранения (важно для поиска видео!)
        if node.get("class_type") in ["SaveVideo", "VideoCombine", "VHS_VideoCombine"]:
            node["inputs"]["filename_prefix"] = output_prefix

    # 3. Отправка
    try:
        req = requests.post("http://127.0.0.1:8188/prompt", json={"prompt": workflow})
        prompt_id = req.json()["prompt_id"]
    except Exception as e:
        return {"status": "error", "message": str(e)}

    # 4. Ожидание и точный возврат файла
    print(f"🚀 Задача {job_id} в работе...")
    while True:
        history = requests.get("http://127.0.0.1:8188/history").json()
        if prompt_id in history:
            # Ищем файл в истории по нашему уникальному префиксу
            video_filename = None
            for node_output in history[prompt_id]['outputs'].values():
                if 'videos' in node_output:
                    video_filename = node_output['videos'][0]['filename']

            if video_filename:
                # В Serverless RunPod видео нужно либо отправить в S3,
                # либо вернуть как Base64 (если оно маленькое), либо дать путь.
                # Для Telegram бота лучше вернуть путь или имя файла.
                video_path = f"/runpod-volume/ComfyUI/output/{video_filename}"
                with open(video_path, "rb") as video_file:
                    encoded_string = base64.b64encode(video_file.read()).decode('utf-8')

                return {
                    "status": "completed",
                    "video_base64": encoded_string,  # Бот получит само видео прямо в ответе
                    "filename": video_filename
                }
            break
        time.sleep(5)


runpod.serverless.start({"handler": handler})