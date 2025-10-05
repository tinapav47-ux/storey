import os
import random
import asyncio
import aiohttp
import aiofiles
import shutil
from telegram import InputMediaPhoto, InputMediaVideo
from io import BytesIO
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


# --- Настройки бота ---
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Укажите токен бота через переменную окружения BOT_TOKEN")

WAITING_FOR_USERNAME = set()

# ---------------- Настройки ----------------
USER_AGENTS = [
    # --- Desktop Chrome ---
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.5790.171 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.5790.171 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36",

    # --- Desktop Firefox ---
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5; rv:116.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:116.0) Gecko/20100101 Firefox/116.0",

    # --- Desktop Edge ---
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36 Edg/116.0.1938.62",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36 Edg/116.0.1938.62",

    # --- Desktop Safari ---
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",

    # --- Desktop Opera ---
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36 OPR/102.0.4843.51",

    # --- Mobile Chrome (Android) ---
    "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.98 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.98 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.5790.171 Mobile Safari/537.36",

    # --- Mobile Safari (iOS) ---
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",

    # --- Mobile Firefox (Android) ---
    "Mozilla/5.0 (Android 13; Mobile; rv:116.0) Gecko/116.0 Firefox/116.0",
    "Mozilla/5.0 (Android 12; Mobile; rv:115.0) Gecko/115.0 Firefox/115.0",
]

BASE_SITE = "https://insta-stories.ru"
TIMEOUT_GOTO = 60000  # Увеличено до 60 секунд для загрузки страницы
TIMEOUT_WAIT_STORY = 30000  # Увеличено до 30 секунд для ожидания .story элементов

# --- Команда /view ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    WAITING_FOR_USERNAME.add(chat_id)
    await update.message.reply_text("Send Instagram username:")

# --- Обработка сообщений с username ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    username = update.message.text.strip()

    if chat_id not in WAITING_FOR_USERNAME:
        await update.message.reply_text("Press /view.")
        return

    await update.message.reply_text("Please wait.")

    WAITING_FOR_USERNAME.remove(chat_id)

    # Запускаем скачивание
    await fetch_and_save(username, chat_id, context)


def get_random_user_agent():
    return random.choice(USER_AGENTS)


def is_valid_http(url: str) -> bool:
    return bool(url) and (url.startswith("http://") or url.startswith("https://"))


# ---------- Скачивание файлов ----------
async def save_image_async(image_url: str, folder: str, index: int, session: aiohttp.ClientSession):
    try:
        headers = {"User-Agent": get_random_user_agent()}
        async with session.get(image_url, headers=headers, timeout=60) as resp:
            resp.raise_for_status()
            data = await resp.read()
        img = Image.open(BytesIO(data)).convert("RGB")
        file_path = os.path.join(folder, f"{index}.jpg")
        img.save(file_path, "JPEG")
        return file_path
    except Exception as e:
        print(f"[ERROR] Не удалось скачать картинку {image_url}: {e}")
        return None


async def save_video_async(video_url: str, folder: str, index: int, session: aiohttp.ClientSession):
    try:
        headers = {"User-Agent": get_random_user_agent()}
        file_path = os.path.join(folder, f"{index}.mp4")
        async with session.get(video_url, headers=headers, timeout=300) as resp:
            resp.raise_for_status()
            async with aiofiles.open(file_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(8192):
                    await f.write(chunk)
        return file_path
    except Exception as e:
        print(f"[ERROR] Не удалось скачать видео {video_url}: {e}")
        return None


# ---------- Парсинг страницы и сбор ссылок ----------
async def fetch_media_links(username: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    url = f"{BASE_SITE}/ru/{username}"
    user_agent = get_random_user_agent()
    found = []

    print(f"[INFO] Загружаю страницу: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=user_agent)

        try:
            await page.goto(url, timeout=TIMEOUT_GOTO)
        except Exception as e:
            print(f"[ERROR] Ошибка при загрузке страницы: {e}")
            await context.bot.send_message(chat_id=chat_id, text="Ошибка при загрузке страницы. Попробуйте позже.")
            await browser.close()
            return found

        # --- Проверка на текст в div.tab-content > p.text-center ---
        try:  # ждём появления хотя бы одного p.text-center внутри div.tab-content (макс. 5 секунд)
            text_el = await page.wait_for_selector("div.tab-content p.text-center", timeout=5000)
            print(f"[INFO] Проверка на текст в div.tab-content 1")
            if text_el:
                message = (await text_el.inner_text()).strip()
                print(f"[INFO] Проверка на текст в div.tab-content 2")
                if message:
                    print(f"[INFO] {message}")
                    await context.bot.send_message(chat_id=chat_id, text=message)
                    await browser.close()
                    return []  # Прерываем дальнейший парсинг
        except PlaywrightTimeoutError:
            # p.text-center не появился — продолжаем парсинг историй
            pass
        except Exception as e:
            print(f"[ERROR] Ошибка при проверке текста: {e}")
            await context.bot.send_message(chat_id=chat_id, text="Ошибка при проверке страницы. Попробуйте позже.")

        # --- Проверка сторис ---
        try:
            await page.wait_for_selector(".story", timeout=TIMEOUT_WAIT_STORY)
        except PlaywrightTimeoutError:
            print("[ERROR] Таймаут при загрузке страницы или отсутствуют .story элементы.")
            await context.bot.send_message(chat_id=chat_id, text="Таймаут или сторис не найдены. Попробуйте позже.")
            await browser.close()
            return found

        stories = await page.query_selector_all(".story")
        print(f"[INFO] Найдено сторисов: {len(stories)}")

        idx = 1
        for i, story in enumerate(stories, start=1):
            try:
                media_box = await story.query_selector(".mediaBox")
                if not media_box:
                    print(f"[SKIP] story #{i}: нет .mediaBox — пропущено.")
                    continue

                media_block = await media_box.query_selector(".media")

                # ----- Поиск видео нажатие кнопки -----
                if media_block:
                    btn = await media_block.query_selector('button[aria-label="Play video"]')
                    if btn:
                        try:
                            await btn.click(force=True)
                            await page.wait_for_timeout(10000)  # дать время DOM обновиться
                        except Exception as e:
                            print(f"[ERROR] story #{i}: не удалось кликнуть Play: {e}")
                            continue

                    # пробуем найти <source type="video/mp4">
                    source_el = await media_block.query_selector('source[type="video/mp4"]')
                    if not source_el:
                        source_el = await story.query_selector('source[type="video/mp4"]')
                    if not source_el:
                        try:
                            source_el = await page.wait_for_selector('source[type="video/mp4"]',
                                                                     timeout=30000, state="attached")  # Увеличено до 30 секунд
                        except PlaywrightTimeoutError:
                            source_el = None

                    if source_el:
                        src = await source_el.get_attribute("src")
                        type_attr = await source_el.get_attribute("type") or ""
                        if src and type_attr.strip().lower() == "video/mp4":
                            found.append({"type": "video", "url": src, "story_index": i, "order": idx})
                            print(f"[FOUND] (video) story #{i} -> {src}")
                            idx += 1
                            continue
                        else:
                            print(f"[SKIP] story #{i}: найден source, но некорректный (src={src}, type={type_attr})")
                            continue
                    else:
                        print(f"[SKIP] story #{i}: видео не найдено после Play.")
                        continue

                # ----- Картинка -----
                img_el = await media_box.query_selector("img")
                if img_el:
                    src = await img_el.get_attribute("src")
                    if src:
                        found.append({"type": "image", "url": src, "story_index": i, "order": idx})
                        print(f"[FOUND] (image) story #{i} -> {src}")
                        idx += 1
                        continue
                    else:
                        print(f"[SKIP] story #{i}: img без src.")
                        continue

                print(f"[SKIP] story #{i}: нет видео и нет картинки.")
            except Exception as e:
                print(f"[ERROR] Ошибка при обработке story #{i}: {e}")
                continue

        await browser.close()

    return found


def prepare_folder(folder: str):
    if not os.path.exists(folder):
        os.makedirs(folder)


# ---------- Главная логика ----------
async def fetch_and_save(username: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    media = await fetch_media_links(username, chat_id, context)
    if not media:
        print("[INFO] Медиа не найдено или произошла ошибка.")
        await context.bot.send_message(chat_id=chat_id, text="Медиа не найдено или произошла ошибка.")
        return

    folder = username
    # --- Очищаем или создаем папку только один раз ---
    prepare_folder(folder)

    saved_count = 0
    index = 1

    # Создаём один общий ClientSession для всех файлов
    async with aiohttp.ClientSession() as session:
        download_tasks = []

        for item in media:
            mtype = item.get("type")
            url = item.get("url")
            if not url or not is_valid_http(url):
                continue

            if mtype == "image":
                download_tasks.append(save_image_async(url, folder, index, session))
            elif mtype == "video":
                download_tasks.append(save_video_async(url, folder, index, session))
            index += 1

        # Параллельная загрузка всех файлов
        downloaded_files = await asyncio.gather(*download_tasks, return_exceptions=True)

    # Подсчёт реально скачанных файлов
    for f in downloaded_files:
        if isinstance(f, str):
            saved_count += 1

    print(f"[DONE] Скачано файлов: {saved_count}")

    # --- Отправка файлов пользователю ---
    await send_media_from_folder(chat_id, folder, context)


# --- Собираем файлы для отправки ---
async def send_media_from_folder(chat_id: int, folder: str, context):
    if not os.path.exists(folder):
        await context.bot.send_message(chat_id=chat_id, text="Папка с медиа не найдена.")
        return

    files = sorted(os.listdir(folder))

    # --- Отправка картинок альбомом ---
    photos = []
    for file_name in files:
        if file_name.endswith((".jpg", ".jpeg", ".png")):
            file_path = os.path.join(folder, file_name)
            photos.append(InputMediaPhoto(open(file_path, "rb")))

    # Telegram позволяет максимум 10 файлов в одном альбоме
    for i in range(0, len(photos), 10):
        await context.bot.send_media_group(chat_id=chat_id, media=photos[i:i + 10])

    # --- Отправка видео по отдельности ---
    for file_name in files:
        if file_name.endswith(".mp4"):
            file_path = os.path.join(folder, file_name)
            with open(file_path, "rb") as f:
                await context.bot.send_video(chat_id=chat_id, video=f)

    # --- После отправки всех файлов ---
    await context.bot.send_message(chat_id=chat_id, text="Done.")

    try:
        shutil.rmtree(folder)
        print(f"[INFO] Папка '{folder}' удалена после отправки файлов")
    except Exception as e:
        print(f"[ERROR] Не удалось удалить папку '{folder}': {e}")


# --- Запуск бота ---
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("view", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()


if __name__ == "__main__":
    main()
