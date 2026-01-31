FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

WORKDIR /

# Установка системных зависимостей
RUN apt-get update && apt-get install -y git wget ffmpeg libsm6 libxext6

# Копируем файлы
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код воркера
COPY handler.py .
COPY model_loader.py .

# Предварительная загрузка весов (чтобы не качать при каждом запуске)
RUN python model_loader.py

CMD [ "python", "-u", "/handler.py" ]