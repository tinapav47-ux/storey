import os
import random
import asyncio
import aiohttp
import aiofiles
import shutil
from telegram import InputMediaPhoto, InputMediaVideo, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from io import BytesIO
from PIL import Image
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# --- Настройки бота ---
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Укажите токен бота через переменную окружения BOT_TOKEN")

WAITING_FOR_USERNAME = set()

# ---------------- Настройки ----------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/116.0.5845.97 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 Chrome/116.0.5845.97 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.5845.97 Safari/537.36",
]

BASE_SITE = "https://insta-stories.ru"
TIMEOUT_GOTO = 30000
TIMEOUT_WAIT_STORY = 10000

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
    await fetch_and_save(username, chat_id, context)

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def is_valid_http(url: str) -> bool:
    return bool(url) and (url.startswith("http://") or url.startswith("https://"))

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

async def fetch_media_links(username: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    url = f"{BASE_SITE}/ru/{username}"
    user_agent = get_random_user_agent()
    found = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=user_agent)

        try:
            await page.goto(url, timeout=TIMEOUT_GOTO)
        except Exception as e:
            print(f"[ERROR] Ошибка при загрузке страницы: {e}")
            await browser.close()
            return found

        try:
            await page.wait_for_selector(".story", timeout=TIMEOUT_WAIT_STORY)
        except PlaywrightTimeoutError:
            await browser.close()
            return found

        stories = await page.query_selector_all(".story")
        idx = 1
        for i, story in enumerate(stories, start=1):
            try:
                media_box = await story.query_selector(".mediaBox")
                if not media_box:
                    continue
                media_block = await media_box.query_selector(".media")

                # Видео
                if media_block:
                    btn = await media_block.query_selector('button[aria-label="Play video"]')
                    if btn:
                        try:
                            await btn.click(force=True)
                            await page.wait_for_timeout(10000)
                        except:
                            continue

                    source_el = await media_block.query_selector('source[type="video/mp4"]') or \
                                await story.query_selector('source[type="video/mp4"]')
                    if source_el:
                        src = await source_el.get_attribute("src")
                        if src:
                            found.append({"type": "video", "url": src, "story_index": i, "order": idx})
                            idx += 1
                            continue

                # Картинка
                img_el = await media_box.query_selector("img")
                if img_el:
                    src = await img_el.get_attribute("src")
                    if src:
                        found.append({"type": "image", "url": src, "story_index": i, "order": idx})
                        idx += 1
                        continue
            except Exception as e:
                print(f"[ERROR] story #{i}: {e}")
                continue

        await browser.close()
    return found

def prepare_folder(folder: str):
    if not os.path.exists(folder):
        os.makedirs(folder)

async def fetch_and_save(username: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    media = await fetch_media_links(username, chat_id, context)
    if not media:
        await context.bot.send_message(chat_id=chat_id, text="No stories found or error occurred.")
        return

    folder = username
    prepare_folder(folder)
    saved_count = 0
    index = 1

    async with aiohttp.ClientSession() as session:
        download_tasks = []
        for item in media:
            mtype, url = item["type"], item["url"]
            if mtype == "image":
                download_tasks.append(save_image_async(url, folder, index, session))
            elif mtype == "video":
                download_tasks.append(save_video_async(url, folder, index, session))
            index += 1
        downloaded_files = await asyncio.gather(*download_tasks, return_exceptions=True)

    for f in downloaded_files:
        if isinstance(f, str):
            saved_count += 1

    await send_media_from_folder(chat_id, folder, context)

async def send_media_from_folder(chat_id, folder, context):
    if not os.path.exists(folder):
        await context.bot.send_message(chat_id=chat_id, text="Folder not found.")
        return

    files = sorted(os.listdir(folder))
    photos = [InputMediaPhoto(open(os.path.join(folder, f), "rb")) for f in files if f.endswith((".jpg", ".jpeg", ".png"))]

    for i in range(0, len(photos), 10):
        await context.bot.send_media_group(chat_id=chat_id, media=photos[i:i + 10])

    for f in files:
        if f.endswith(".mp4"):
            with open(os.path.join(folder, f), "rb") as file:
                await context.bot.send_video(chat_id=chat_id, video=file)

    await context.bot.send_message(chat_id=chat_id, text="Done.")
    shutil.rmtree(folder, ignore_errors=True)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("view", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
