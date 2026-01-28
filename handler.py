import runpod
import os
import requests

# Твои настройки (передай их через Environment Variables в панели RunPod)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ARCHIVE_CHANNEL_ID = os.environ.get("ARCHIVE_CHANNEL_ID")


def handler(job):
    """
    Основная функция-обработчик
    """
    job_input = job['input']
    prompt = job_input.get('prompt', 'No prompt')

    # --- ТУТ БУДЕТ ГЕНЕРАЦИЯ ВИДЕО (Wan2.1) ---
    # Пока для теста создаем пустой файл или имитируем его
    temp_file_path = "/tmp/test_video.mp4"
    with open(temp_file_path, "w") as f:
        f.write("fake video data")

    # --- ОТПРАВКА В TELEGRAM (Хранилище без карт) ---
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"

    try:
        with open(temp_file_path, 'rb') as video_file:
            payload = {'chat_id': ARCHIVE_CHANNEL_ID}
            files = {'video': video_file}
            response = requests.post(url, data=payload, files=files).json()

        if response.get('ok'):
            # Возвращаем боту уникальный ID файла в системе Telegram
            file_id = response['result']['video']['file_id']
            return {"file_id": file_id, "status": "success"}
        else:
            return {"error": response.get("description"), "status": "error"}

    except Exception as e:
        return {"error": str(e), "status": "error"}


# ВАЖНО: Именно эту строчку ищет RunPod!
runpod.serverless.start({"handler": handler})