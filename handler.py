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
import glob
import subprocess
import re

# Разрешение под 24GB VRAM: стабильная анимация без артефактов (>=5 сек)
WIDTH = 672
HEIGHT = 384
# 40 кадров @ 8 fps = 5 секунд (более стабильно, чем 48/64)
FRAMES = 40
FPS = 8
# Повышаем качество (дольше, но стабильнее и ближе к промпту)
STEPS_DEFAULT = 20
STEPS_MIN = 12
STEPS_MAX = 28
CFG_DEFAULT = 3.0
CFG_MIN = 2.2
CFG_MAX = 4.2
# LoRA включаем только при наличии слова "lora" в промпте
LORA_STRENGTH_DEFAULT = 0.2
LORA_STRENGTH_MIN = 0.15
LORA_STRENGTH_MAX = 0.6
# Стабильность движения
DEFAULT_DENOISE = 0.75
WORKFLOW_PATH = "/workspace/new_Wan22_api.json"
COMFY_URL = "http://127.0.0.1:8188"
TIMEOUT_GENERATION = 720  # 12 минут макс на одну задачу
POLL_INTERVAL = 5
MODELS_DIR = "/workspace/ComfyUI/models"
CHECKPOINTS_DIR = f"{MODELS_DIR}/checkpoints"
LORAS_DIR = f"{MODELS_DIR}/loras"
DIFFUSION_DIR = f"{MODELS_DIR}/diffusion_models"
TEXT_ENCODERS_DIR = f"{MODELS_DIR}/text_encoders"
CLIP_VISION_DIR = f"{MODELS_DIR}/clip_vision"
OUTPUT_DIR = "/workspace/ComfyUI/output"
MAX_VIDEO_MB = int(os.getenv("MAX_VIDEO_MB", "48"))  # лимит под Telegram
HANDLER_VERSION = "2026-02-04-03"


def handler(event):
    if event.get("input", {}).get("debug"):
        print(f"Handler version: {HANDLER_VERSION}")
    job_id = event.get("id", "unknown")
    input_data = event.get("input", {})

    try:
        image_base64 = input_data.get("image_base64")
        image_url = input_data.get("image_url")
        prompt = input_data.get("prompt", "a person smiling naturally")
        steps = int(input_data.get("steps", STEPS_DEFAULT))
        cfg = float(input_data.get("cfg", CFG_DEFAULT))
        lora_strength = float(input_data.get("lora_strength", LORA_STRENGTH_DEFAULT))
        denoise_strength = float(input_data.get("denoise_strength", DEFAULT_DENOISE))
        negative_prompt = input_data.get(
            "negative_prompt",
            "low quality, worst quality, jpeg artifacts, blurry, deformed, disfigured, "
            "extra limbs, extra fingers, glitch, color flash, blue screen, distorted face, "
            "camera shake, sudden motion, extreme blur, erratic motion, random movement",
        )
        seed = input_data.get("seed", int(time.time()))

        if not image_base64 and not image_url:
            return {"error": "Нужен image_base64 или image_url (data URI или публичный URL)"}

        # Уникальные пути под конкурентные запросы
        input_name = f"input_{job_id}.jpg"
        input_path = f"/workspace/ComfyUI/input/{input_name}"

        try:
            if image_base64:
                raw = image_base64
                if "," in raw:
                    raw = raw.split(",", 1)[1]
                img_data = base64.b64decode(raw)
            else:
                # image_url: поддержка data URI или публичного URL
                if image_url.startswith("data:"):
                    raw = image_url.split(",", 1)[1]
                    img_data = base64.b64decode(raw)
                else:
                    r = requests.get(image_url, timeout=30)
                    r.raise_for_status()
                    img_data = r.content
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

        # Имена моделей (можно переопределить через env)
        # Для качества лучше HIGH; можно переопределить через env
        MODEL_FILE = os.getenv("WAN_MODEL_FILE", "Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors")
        VAE_FILE = os.getenv("WAN_VAE_FILE", "Wan2_1_VAE_bf16.safetensors")
        T5_FILE = os.getenv("WAN_T5_FILE", "umt5-xxl-enc-bf16.safetensors")
        CLIP_VISION_FILE = os.getenv("WAN_CLIP_VISION_FILE", "clip_vision_h.safetensors")
        LORA_FILE = os.getenv("WAN_LORA_FILE", "cyberpunk_style.safetensors")

        # Включаем LoRA только по слову "lora" в промпте (регистронезависимо)
        enable_lora = bool(re.search(r"\blora\b", prompt, flags=re.IGNORECASE))
        if enable_lora:
            # Уберём служебное слово из текста, чтобы не портить качество
            prompt = re.sub(r"\blora\b", "", prompt, flags=re.IGNORECASE).strip()

        # Ограничиваем параметры, чтобы избежать OOM и артефактов
        steps = max(STEPS_MIN, min(STEPS_MAX, steps))
        cfg = max(CFG_MIN, min(CFG_MAX, cfg))
        lora_strength = max(LORA_STRENGTH_MIN, min(LORA_STRENGTH_MAX, lora_strength))
        denoise_strength = max(0.6, min(1.0, denoise_strength))

        # Быстрый preflight моделей
        model_path = os.path.join(DIFFUSION_DIR, MODEL_FILE)
        vae_path = os.path.join(MODELS_DIR, "vae", VAE_FILE)
        t5_path = os.path.join(TEXT_ENCODERS_DIR, T5_FILE)
        clip_path = os.path.join(CLIP_VISION_DIR, CLIP_VISION_FILE)
        lora_path = os.path.join(LORAS_DIR, LORA_FILE)

        missing = []
        if not os.path.exists(model_path):
            missing.append(f"diffusion_models/{MODEL_FILE}")
        if not os.path.exists(vae_path):
            missing.append(f"vae/{VAE_FILE}")
        if not os.path.exists(t5_path):
            missing.append(f"text_encoders/{T5_FILE}")
        if not os.path.exists(clip_path):
            missing.append(f"clip_vision/{CLIP_VISION_FILE}")
        if enable_lora and not os.path.exists(lora_path):
            missing.append(f"loras/{LORA_FILE}")

        if missing:
            return {
                "error": "Не найдены модели: "
                + ", ".join(missing)
                + ". Проверьте /runpod-volume/ComfyUI/models/..."
            }

        for node in workflow.values():
            if node.get("class_type") == "LoadImage":
                node["inputs"]["image"] = input_name
            elif node.get("class_type") in ["CLIPTextEncode"]:
                node["inputs"]["text"] = prompt
            elif node.get("class_type") == "WanVideoTextEncode":
                node["inputs"]["positive_prompt"] = prompt
                if "negative_prompt" in node["inputs"]:
                    node["inputs"]["negative_prompt"] = negative_prompt
            elif node.get("class_type") == "WanVideoModelLoader":
                node["inputs"]["model"] = MODEL_FILE
                # Используем валидный режим внимания (без зависимости от sageattention)
                if "attention_mode" in node["inputs"]:
                    node["inputs"]["attention_mode"] = "comfy"
            elif node.get("class_type") == "WanVideoVAELoader":
                node["inputs"]["model_name"] = VAE_FILE
            elif node.get("class_type") == "LoadWanVideoT5TextEncoder":
                node["inputs"]["model_name"] = T5_FILE
            elif node.get("class_type") == "CLIPVisionLoader":
                node["inputs"]["clip_name"] = CLIP_VISION_FILE
            elif node.get("class_type") == "WanVideoLoraSelectMulti":
                if enable_lora:
                    node["inputs"]["lora_0"] = LORA_FILE
                    node["inputs"]["strength_0"] = lora_strength
                else:
                    node["inputs"]["lora_0"] = "none"
                    node["inputs"]["strength_0"] = 0.0
            elif node.get("class_type") == "WanVideoSampler":
                node["inputs"]["steps"] = steps
                node["inputs"]["seed"] = seed
                if "cfg" in node["inputs"]:
                    node["inputs"]["cfg"] = cfg
                if "denoise_strength" in node["inputs"]:
                    node["inputs"]["denoise_strength"] = denoise_strength
                if "add_noise_to_samples" in node["inputs"]:
                    node["inputs"]["add_noise_to_samples"] = False
            elif node.get("class_type") == "WanVideoImageToVideoEncode":
                node["inputs"]["num_frames"] = FRAMES
                node["inputs"]["width"] = WIDTH
                node["inputs"]["height"] = HEIGHT
            elif node.get("class_type") == "ImageResizeKJv2":
                node["inputs"]["width"] = WIDTH
                node["inputs"]["height"] = HEIGHT
            elif node.get("class_type") == "WanVideoContextOptions":
                # Держим контекст ниже num_frames, чтобы избежать предупреждений
                # Более стабильные окна контекста + отключаем FreeNoise (уменьшает дрожание)
                node["inputs"]["context_frames"] = min(FRAMES - 1, 16) if FRAMES > 1 else 1
                if "context_overlap" in node["inputs"]:
                    node["inputs"]["context_overlap"] = min(node["inputs"].get("context_overlap", 4), 4)
                if "context_stride" in node["inputs"]:
                    node["inputs"]["context_stride"] = max(4, node["inputs"].get("context_stride", 4))
                if "freenoise" in node["inputs"]:
                    node["inputs"]["freenoise"] = False
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
                    # fallback: пробуем запросить конкретный prompt_id
                    try:
                        h2 = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=10)
                        if h2.status_code == 200:
                            history = {prompt_id: h2.json()}
                    except Exception:
                        pass
                if prompt_id not in history:
                    time.sleep(POLL_INTERVAL)
                    continue

                outputs = history[prompt_id].get("outputs", {})
                for node_output in outputs.values():
                    if "videos" not in node_output:
                        continue
                    video_info = node_output["videos"][0]
                    filename = video_info.get("filename")
                    if isinstance(filename, list):
                        filename = filename[0] if filename else None
                    subfolder = video_info.get("subfolder") or ""
                    fullpath = video_info.get("fullpath")

                    if fullpath and os.path.exists(fullpath):
                        video_path = fullpath
                    else:
                        if filename:
                            if subfolder:
                                video_path = f"/workspace/ComfyUI/output/{subfolder}/{filename}"
                            else:
                                video_path = f"/workspace/ComfyUI/output/{filename}"

                    if not video_path or not os.path.exists(video_path):
                        video_path = _find_latest_output(output_prefix)

                    if not video_path or not os.path.exists(video_path):
                        _cleanup(input_path, None)
                        return {"error": f"Видео не найдено: {filename or 'unknown'}"}

                    # Дождаться окончания записи файла
                    if not _wait_for_stable_file(video_path, timeout_sec=30):
                        _cleanup(input_path, None)
                        return {"error": "Видео не удалось прочитать (файл не стабилизировался)"}

                    # Если видео слишком большое — пересжимаем для Telegram
                    video_path = _maybe_reencode_for_telegram(video_path)

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
                        "duration_sec": FRAMES / FPS,
                    }
                # Если outputs есть, но видео пока не прописалось — ищем по префиксу
                fallback_video = _find_latest_output(output_prefix)
                if fallback_video and os.path.exists(fallback_video):
                    if not _wait_for_stable_file(fallback_video, timeout_sec=30):
                        time.sleep(POLL_INTERVAL)
                        continue
                    fallback_video = _maybe_reencode_for_telegram(fallback_video)
                    with open(fallback_video, "rb") as f:
                        video_bytes = f.read()
                    _cleanup(input_path, fallback_video)
                    torch.cuda.empty_cache()
                    gc.collect()
                    return {
                        "video_base64": base64.b64encode(video_bytes).decode("utf-8"),
                        "seed": seed,
                        "frames": FRAMES,
                        "fps": FPS,
                        "duration_sec": FRAMES / FPS,
                    }
                # продолжаем ждать до таймаута
                time.sleep(POLL_INTERVAL)
                continue
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


def _find_latest_output(prefix: str):
    patterns = [
        f"{OUTPUT_DIR}/**/{prefix}*.mp4",
        f"{OUTPUT_DIR}/**/{prefix}*.webm",
        f"{OUTPUT_DIR}/**/{prefix}*.mov",
    ]
    candidates = []
    for pat in patterns:
        candidates.extend(glob.glob(pat, recursive=True))
    if not candidates:
        return None
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def _wait_for_stable_file(path: str, timeout_sec: int = 30, stable_checks: int = 3):
    last_size = -1
    stable = 0
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            size = os.path.getsize(path)
        except OSError:
            size = -1
        if size > 0 and size == last_size:
            stable += 1
            if stable >= stable_checks:
                return True
        else:
            stable = 0
        last_size = size
        time.sleep(1)
    return False


def _maybe_reencode_for_telegram(path: str):
    try:
        size_mb = os.path.getsize(path) / (1024 * 1024)
    except OSError:
        return path
    if size_mb <= MAX_VIDEO_MB:
        return path

    out_path = path.rsplit(".", 1)[0] + "_tg.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        path,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "28",
        "-pix_fmt",
        "yuv420p",
        out_path,
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(out_path):
            return out_path
    except Exception:
        return path
    return path


runpod.serverless.start({"handler": handler})
