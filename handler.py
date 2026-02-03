import runpod
import requests
import time
import base64
import os
import json
import torch
import gc


def handler(event):
    job_id = event["id"]
    input_data = event.get("input", {})

    try:
        # Бот отправляет BASE64, а не URL!
        image_base64 = input_data.get("image_base64")
        prompt = input_data.get("prompt", "a person smiling naturally")
        steps = int(input_data.get("steps", 6))
        seed = input_data.get("seed", int(time.time()))

        if not image_base64:
            return {"error": "Требуется параметр image_base64"}

        # Сохраняем изображение в /workspace (не /runpod-volume!)
        input_path = f"/workspace/ComfyUI/input/input_{job_id}.jpg"
        try:
            if ',' in image_base64:
                image_base64 = image_base64.split(',')[1]
            img_data = base64.b64decode(image_base64)
            os.makedirs("/workspace/ComfyUI/input", exist_ok=True)
            with open(input_path, "wb") as f:
                f.write(img_data)
        except Exception as e:
            return {"error": f"Ошибка декодирования изображения: {str(e)}"}

        # Читаем ПРАВИЛЬНЫЙ файл workflow
        with open("/workspace/new_Wan22_api.json", "r") as f:
            workflow = json.load(f)

        output_prefix = f"wan2_{job_id}"

        # Настраиваем workflow
        for node in workflow.values():
            if node.get("class_type") == "LoadImage":
                node["inputs"]["image"] = f"input_{job_id}.jpg"

            if node.get("class_type") in ["CLIPTextEncode", "WanVideoTextEncode"]:
                node["inputs"]["text"] = prompt

            if node.get("class_type") == "WanVideoModelLoader":
                node["inputs"]["model"] = "wan2.2-rapid-mega-aio-v10.safetensors"
                node["inputs"]["vae"] = "wan2.2-rapid-mega-aio-v10.safetensors"

            if node.get("class_type") == "WanVideoSampler":
                node["inputs"]["steps"] = steps
                node["inputs"]["seed"] = seed
                node["inputs"]["frames"] = 64  # 8 секунд @ 8fps

            if node.get("class_type") in ["VHS_VideoCombine", "SaveVideo"]:
                node["inputs"]["filename_prefix"] = output_prefix

        # Отправка в ComfyUI
        try:
            resp = requests.post(
                "http://127.0.0.1:8188/prompt",
                json={"prompt": workflow},
                timeout=30
            )
            resp.raise_for_status()
            prompt_id = resp.json()["prompt_id"]
        except Exception as e:
            return {"error": f"Ошибка отправки в ComfyUI: {str(e)}"}

        # Ожидание завершения (макс 10 минут)
        print(f"🎬 Job {job_id}: генерация 64 кадров...")
        start_time = time.time()
        while time.time() - start_time < 600:
            try:
                history = requests.get("http://127.0.0.1:8188/history", timeout=10).json()
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    for node_output in outputs.values():
                        if "videos" in node_output:
                            video_info = node_output["videos"][0]
                            video_path = f"/workspace/ComfyUI/output/{video_info['filename']}"

                            if not os.path.exists(video_path):
                                return {"error": f"Видео не найдено: {video_path}"}

                            # Чтение в base64
                            with open(video_path, "rb") as f:
                                video_bytes = f.read()

                            # Очистка файлов
                            if os.path.exists(input_path):
                                os.remove(input_path)
                            if os.path.exists(video_path):
                                os.remove(video_path)

                            # 🔥 КРИТИЧНО: очистка памяти между запросами
                            torch.cuda.empty_cache()
                            gc.collect()

                            return {
                                "status": "success",
                                "video_base64": base64.b64encode(video_bytes).decode('utf-8'),
                                "seed": seed,
                                "frames": 64,
                                "fps": 8,
                                "duration_sec": 8
                            }
                    return {"error": "Видео не сгенерировано (проверьте ноды в workflow)"}
            except Exception as e:
                print(f"⚠️ Ошибка при опросе истории: {e}")

            time.sleep(5)

        return {"error": "Таймаут генерации (более 10 минут)"}

    except Exception as e:
        # Гарантированная очистка памяти при ЛЮБОЙ ошибке
        torch.cuda.empty_cache()
        gc.collect()
        return {"error": f"Критическая ошибка: {str(e)}"}


runpod.serverless.start({"handler": handler})