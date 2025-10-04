# Story Downloader Telegram Bot  

Telegram-бот для **просмотра Instagram Stories**.  
>>Бот написан на языке **Python** и использовался для целей обучения и личного применения.  

---

## Возможности  
- Получение Instagram Stories по имени пользователя.  
- Скачивание фото и видео в оригинальном качестве.  
- Отправка медиа напрямую в Telegram (альбомом для фото, по одному — для видео).  
- Удаление временных файлов после отправки.  
- Работа через асинхронный стек (`asyncio`, `aiohttp`, `playwright`).  
- Поддержка **headless Chromium** для парсинга.  
- Использование **случайных User-Agent** для обхода блокировок.  

---

## Используемые технологии  

| Технология | Версия (в примере) | Описание | Ссылка |
|------------|-------------------|----------|--------|
| [Python](https://www.python.org/) | 3.12 | Язык программирования | [python.org](https://www.python.org/) |
| [python-telegram-bot](https://docs.python-telegram-bot.org/) | 20.x | Работа с Telegram Bot API | [PTB Docs](https://docs.python-telegram-bot.org/) |
| [Playwright](https://playwright.dev/python/) | 1.39+ | Управление браузером Chromium, парсинг контента | [playwright.dev](https://playwright.dev/python/) |
| [aiohttp](https://docs.aiohttp.org/) | 3.9+ | Асинхронные HTTP-запросы | [aiohttp Docs](https://docs.aiohttp.org/) |
| [aiofiles](https://pypi.org/project/aiofiles/) | 23.x | Асинхронная работа с файлами | [pypi aiofiles](https://pypi.org/project/aiofiles/) |
| [Pillow](https://pillow.readthedocs.io/) | 10.x | Обработка изображений | [Pillow Docs](https://pillow.readthedocs.io/) |
| [Docker](https://www.docker.com/) | latest | Контейнеризация приложения | [docker.com](https://www.docker.com/) |
| [Debian Slim](https://hub.docker.com/_/python) | python:3.12-slim | Базовый образ контейнера | [Docker Hub](https://hub.docker.com/_/python) |

---

##  Версии и совместимость
| Компонент        | Минимальная версия | Тестировалось на                |
| ---------------- | ------------------ | ------------------------------- |
| Python           | 3.10+              | 3.12                            |
| Playwright       | 1.39+              | 1.41                            |
| Telegram Bot API | v6+                | через `python-telegram-bot` v20 |
| Docker           | 20.x               | latest                          |
| ОС               | Linux/WSL/Docker   | Debian Slim                     |


---

## Структура проекта  
```
├── botstoreybot.py — основной код бота (Python)
├── requirements.txt — список зависимостей  
├── Dockerfile — сборка контейнера 
└── README.md — документация 
``` 

---

## Безопасность  

- Токен Telegram скрыт через переменную окружения (BOT_TOKEN).
- В коде нет прямого хранения ключей.
- Бот написан для личного использования и обучения, не для публичного развёртывания.

---

## Производительность и Go-версия

Бот изначально был написан на Python. Однако в процессе эксплуатации было замечено, что он:

1. Потребляет значительное количество ресурсов (CPU и RAM);
2. Сильно нагружает систему при большом количестве запросов.

В качестве эксперимента и проверки гипотезы о ресурсоёмкости различных языков программирования, бот был переписан на Go.
Это позволило протестировать:

1. Разницу в скорости работы;
2. Потребление памяти;
3. Удобство параллельных операций в разных языках;
4. Python-версия сохранена как базовый учебный пример.

