import runpod
import time


def handler(job):
    # Данные, которые прислал бот
    job_input = job['input']
    prompt = job_input.get('prompt', 'No prompt')
    image_url = job_input.get('image_url', '')

    print(f"Начинаю генерацию для: {prompt}")

    # Имитируем работу нейросети (ждем 10 секунд)
    time.sleep(10)

    # В реальной жизни тут будет ссылка на готовое видео в S3
    return {
        "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
        "message": f"Видео по запросу '{prompt}' готово!"
    }


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})