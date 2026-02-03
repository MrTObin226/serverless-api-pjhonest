"""
RunPod Serverless handler: фото -> 8 сек видео (Wan2.2).
Оптимизировано под RTX 4090 24GB: разрешение и шаги подобраны против OOM.
"""
import runpod
import requests
import time
import base64
import os
import json
import torch
import gc

# Разрешение под 24GB VRAM: плавное 8 сек без OOM (64 кадра @ 8 fps)
WIDTH = 672
HEIGHT = 384
FRAMES = 64
FPS = 8
STEPS_DEFAULT = 6
WORKFLOW_PATH = "/workspace/new_Wan22_api.json"
COMFY_URL = "http://127.0.0.1:8188"
TIMEOUT_GENERATION = 720  # 12 минут макс на одну задачу
POLL_INTERVAL = 5


def handler(event):
    job_id = event.get("id", "unknown")
    input_data = event.get("input", {})

    try:
        image_base64 = input_data.get("image_base64")
        prompt = input_data.get("prompt", "a person smiling naturally")
        steps = int(input_data.get("steps", STEPS_DEFAULT))
        seed = input_data.get("seed", int(time.time()))

        if not image_base64:
            return {"error": "Требуется параметр image_base64"}

        # Уникальные пути под конкурентные запросы
        input_name = f"input_{job_id}.jpg"
        input_path = f"/workspace/ComfyUI/input/{input_name}"

        try:
            raw = image_base64
            if "," in raw:
                raw = raw.split(",", 1)[1]
            img_data = base64.b64decode(raw)
            os.makedirs("/workspace/ComfyUI/input", exist_ok=True)
            with open(input_path, "wb") as f:
                f.write(img_data)
        except Exception as e:
            return {"error": f"Ошибка декодирования изображения: {str(e)}"}

        if not os.path.exists(WORKFLOW_PATH):
            return {"error": f"Workflow не найден: {WORKFLOW_PATH}"}

        with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        output_prefix = f"wan2_{job_id}"

        # Имена моделей на volume: checkpoints + VAE из одного файла, LoRA всегда cyberpunk_style
        MODEL_FILE = "wan2.2-rapid-mega-aio-v10.safetensors"
        LORA_FILE = "cyberpunk_style.safetensors"

        for node in workflow.values():
            if node.get("class_type") == "LoadImage":
                node["inputs"]["image"] = input_name
            elif node.get("class_type") in ["CLIPTextEncode", "WanVideoTextEncode"]:
                node["inputs"]["text"] = prompt
            elif node.get("class_type") == "WanVideoModelLoader":
                node["inputs"]["model"] = MODEL_FILE
                node["inputs"]["vae"] = MODEL_FILE
            elif node.get("class_type") == "WanVideoLoraSelectMulti":
                node["inputs"]["lora_0"] = LORA_FILE
                node["inputs"]["strength_0"] = 1.0
            elif node.get("class_type") == "WanVideoSampler":
                node["inputs"]["steps"] = steps
                node["inputs"]["seed"] = seed
                node["inputs"]["frames"] = FRAMES
                node["inputs"]["fps"] = FPS
                node["inputs"]["width"] = WIDTH
                node["inputs"]["height"] = HEIGHT
            elif node.get("class_type") in ["VHS_VideoCombine", "SaveVideo"]:
                node["inputs"]["filename_prefix"] = output_prefix
                if "frame_rate" in node["inputs"]:
                    node["inputs"]["frame_rate"] = FPS

        try:
            resp = requests.post(
                f"{COMFY_URL}/prompt",
                json={"prompt": workflow},
                timeout=30,
            )
            resp.raise_for_status()
            prompt_id = resp.json()["prompt_id"]
        except requests.exceptions.RequestException as e:
            _cleanup(input_path, None)
            return {"error": f"Ошибка отправки в ComfyUI: {str(e)}"}

        start_time = time.time()
        video_path = None

        while time.time() - start_time < TIMEOUT_GENERATION:
            try:
                history = requests.get(f"{COMFY_URL}/history", timeout=10).json()
                if prompt_id not in history:
                    time.sleep(POLL_INTERVAL)
                    continue

                outputs = history[prompt_id].get("outputs", {})
                for node_output in outputs.values():
                    if "videos" not in node_output:
                        continue
                    video_info = node_output["videos"][0]
                    filename = video_info.get("filename") or video_info.get("subfolder", "")
                    if isinstance(filename, list):
                        filename = filename[0] if filename else ""
                    subfolder = video_info.get("subfolder", "")
                    if subfolder:
                        video_path = f"/workspace/ComfyUI/output/{subfolder}/{filename}"
                    else:
                        video_path = f"/workspace/ComfyUI/output/{filename}"

                    if not os.path.exists(video_path):
                        video_path = f"/workspace/ComfyUI/output/{filename}"
                    if not os.path.exists(video_path):
                        _cleanup(input_path, None)
                        return {"error": f"Видео не найдено: {filename}"}

                    with open(video_path, "rb") as f:
                        video_bytes = f.read()

                    _cleanup(input_path, video_path)
                    torch.cuda.empty_cache()
                    gc.collect()

                    return {
                        "video_base64": base64.b64encode(video_bytes).decode("utf-8"),
                        "seed": seed,
                        "frames": FRAMES,
                        "fps": FPS,
                        "duration_sec": FRAMES // FPS,
                    }
                return {"error": "В выводе workflow нет видео"}
            except Exception as e:
                print(f"⚠️ Job {job_id} опрос истории: {e}")
            time.sleep(POLL_INTERVAL)

        _cleanup(input_path, video_path)
        return {"error": f"Таймаут генерации ({TIMEOUT_GENERATION // 60} мин)"}

    except Exception as e:
        torch.cuda.empty_cache()
        gc.collect()
        return {"error": f"Критическая ошибка: {str(e)}"}


def _cleanup(input_path, video_path):
    for p in (input_path, video_path):
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


runpod.serverless.start({"handler": handler})
