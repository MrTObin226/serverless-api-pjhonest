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
    b64_image = job_input.get("image_base64") or job_input.get("image")
    if not b64_image:
        return {"error": "No image provided. Please send 'image_base64'."}

    image_filename = f"upload_{uuid.uuid4()}.jpg"
    save_base64_image(b64_image, image_filename)

    with open(WORKFLOW_FILE, "r") as f:
        workflow = json.load(f)

    prompt_text = job_input.get("prompt", "a cinematic video")
    steps = job_input.get("steps", 15)
    if "569" in workflow:
        workflow["569"]["inputs"]["value"] = steps
    if "244" in workflow:
        workflow["244"]["inputs"]["image"] = image_filename
    if "135" in workflow:
        workflow["135"]["inputs"]["positive_prompt"] = prompt_text
    if "220" in workflow:
        seed = job_input.get("seed", int(time.time() * 1000) % 1000000000)
        workflow["220"]["inputs"]["seed"] = seed

    client_id = str(uuid.uuid4())
    payload = {"prompt": workflow, "client_id": client_id}
    res = requests.post(f"{COMFY_URL}/prompt", json=payload)
    if res.status_code != 200:
        return {"error": f"ComfyUI Error: {res.text}"}
    prompt_id = res.json().get('prompt_id')

    # Таймаут 5 минут
    start_time = time.time()
    timeout = 300

    while True:
        if time.time() - start_time > timeout:
            return {"error": "Timeout: Video generation took too long"}

        history_res = requests.get(f"{COMFY_URL}/history/{prompt_id}")
        if history_res.status_code == 200:
            history = history_res.json()
            if prompt_id in history:
                outputs = history[prompt_id].get('outputs', {})
                for node_id, content in outputs.items():
                    if node_id == "131" and 'videos' in content and content['videos']:
                        video_filename = content['videos'][0]['filename']
                        # Правильный путь к output-директории
                        video_path = f"/ComfyUI/user/default/output/{video_filename}"

                        if os.path.exists(video_path):
                            with open(video_path, "rb") as f:
                                video_b64 = base64.b64encode(f.read()).decode('utf-8')
                                return {"video_url": f"data:video/mp4;base64,{video_b64}"}
                        else:
                            return {"error": f"Video file missing: {video_path}"}
        time.sleep(5)  # Оптимальный интервал опроса


wait_for_comfy()
runpod.serverless.start({"handler": handler})