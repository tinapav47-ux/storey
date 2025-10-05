# Базовый образ Python 3.12 slim
FROM python:3.12-slim

# Установка системных зависимостей для Playwright и Python
RUN apt-get update && apt-get install -y \
    curl wget git libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxcomposite1 libxrandr2 libxdamage1 libxfixes3 libgbm1 libpango-1.0-0 \
    libgtk-3-0 libasound2 libx11-xcb1 fonts-liberation libwoff1 \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование зависимостей и установка Python-библиотек
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir playwright && playwright install chromium

# Копирование исходного кода
COPY . .

# CMD с отключенной буферизацией, чтобы логи шли сразу в docker logs
CMD ["python", "-u", "botstoreybot.py"]
