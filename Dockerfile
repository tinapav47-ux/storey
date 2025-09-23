FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    curl wget git libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxcomposite1 libxrandr2 libxdamage1 libxfixes3 libgbm1 libpango1.0-0 \
    libgtk-3-0 libasound2 libx11-xcb1 fonts-liberation libwoff1 \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir playwright && playwright install chromium

COPY . .

CMD ["python", "botstoreybot.py"]
