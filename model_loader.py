import os
from huggingface_hub import snapshot_download


def download_model():
    # Путь, куда будут сохранены веса внутри контейнера
    model_save_path = "/models/Wan2.1-T2V-14B"  # Или ваша версия 2.2

    print(f"🚀 Начинаю загрузку модели Wan в {model_save_path}...")

    snapshot_download(
        repo_id="Wan-AI/Wan2.1-T2V-14B",  # Замените на точный ID Wan 2.2, когда он будет в доступе
        local_dir=model_save_path,
        ignore_patterns=["*.msgpack", "*.h5", "*.bin"],  # Качаем только safetensors
        token=os.getenv("HF_TOKEN")  # Если репозиторий приватный
    )
    print("✅ Загрузка завершена!")


if __name__ == "__main__":
    download_model()