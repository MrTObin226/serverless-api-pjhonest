# Берем готовую основу с Python
FROM python:3.11-slim

# Устанавливаем библиотеку runpod
RUN pip install runpod

# Копируем наш скрипт внутрь коробки
COPY handler.py /handler.py

# Команда, которую выполнит RunPod при запуске
CMD [ "python", "-u", "/handler.py" ]