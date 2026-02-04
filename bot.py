import base64
import os
import asyncio
import sqlite3
import warnings
import logging
import aiohttp
import random
import time
from datetime import datetime
from io import BytesIO
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from urllib3.exceptions import NotOpenSSLWarning

# --- Настройка логов ---
logging.basicConfig(level=logging.INFO)
warnings.filterwarnings("ignore", category=NotOpenSSLWarning)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_KEY = os.getenv("ETERNAL_API_KEY")

# --- Константы ---
WELCOME_PHOTO_ID = "AgACAgEAAxkBAANfaXT3bSDtzl0IG_LyTnKUAps5WNQAApALaxuC16lHGHgvWG2DiKoBAAMCAAN4AAM4BA"
EXAMPLE_PHOTO_ID = "AgACAgEAAxkBAANdaXT3CuG-6zG7CReOFph-NvtLYhUAAo8LaxuC16lHuqKVYVTmHZsBAAMCAAN5AAM4BA"

RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
ENDPOINT_ID = os.getenv("ENDPOINT_ID")

COST_EDIT = 2
COST_ANIMATE = 4

# Словари примеров (file_id нужно обновить на актуальные в вашем боте)
EXAMPLES_MEDIA = {
    "edit_1": {"type": "photo", "file_id": EXAMPLE_PHOTO_ID, "caption": "Пример редактирования №1: Улыбка"},
    "edit_2": {"type": "photo", "file_id": EXAMPLE_PHOTO_ID, "caption": "Пример редактирования №2: Киберпанк"},
    "anim_1": {"type": "video", "file_id": EXAMPLE_PHOTO_ID, "caption": "Пример анимации №1: Подмигивание"},
    "anim_2": {"type": "video", "file_id": EXAMPLE_PHOTO_ID, "caption": "Пример анимации №2: Приветствие"}
}

URL_PHOTO = "https://open.eternalai.org/creative-ai/image"
URL_VIDEO = "https://open.eternalai.org/creative-ai/video"
URL_POLL = "https://open.eternalai.org/creative-ai/poll-result/"

# --- СТРОКИ И ПРЕСЕТЫ ---
STRINGS = {
    "ru": {
        "start": "🌟 **Добро пожаловать в HonestEyes AI!**\n\nЗдесь ты можешь редактировать фотографии и оживлять их.\n⚠️ По всем техническим вопросам писать админу.\n\n🪙 Твой баланс: {coins} монет",
        "btn_create": "📸 Обработать", "btn_profile": "👤 Профиль", "btn_lang": "🌐 Язык",
        "btn_shop": "🛒 Магазин", "btn_bonus": "🎁 Бонус", "btn_ex": "👀 Примеры", "ex_edit_cat": "🖼 Редактирование",
        "ex_anim_cat": "🎬 Оживление",
        "no_coins": "⚠️ Нужно {need} 🪙", "bonus_ok": "✅ +1 монета!", "bonus_fail": "⏳ Вы уже получили бонус сегодня!",
        "back": "⬅️ Назад", "send_photo": "📸 Отправьте фотографию:",
        "action_title": "Выберите действие:", "edit_btn": "🖼 Редактировать", "anim_btn": "🎬 Оживить",
        "presets_title": "Выберите эффект:", "btn_custom": "✍️ Свой запрос",
        "enter_custom": "📝 Введите описание (англ):", "wait": "⏳ ИИ работает... (1-2 мин)", "error_api": "❌ Ошибка ИИ:"
    },
    "en": {
        "start": "🌟 **HonestEyes AI**\n\nHello, {name}!\n🪙 Balance: {coins} coins",
        "btn_create": "📸 Create", "btn_profile": "👤 Profile", "btn_lang": "🌐 Language",
        "btn_shop": "🛒 Shop", "btn_bonus": "🎁 Bonus", "btn_ex": "👀 Examples", "ex_edit_cat": "🖼 Editing",
        "ex_anim_cat": "🎬 Animation",
        "no_coins": "⚠️ Need {need} 🪙", "bonus_ok": "✅ +1 coin!", "bonus_fail": "⏳ Tomorrow!",
        "back": "⬅️ Back", "send_photo": "📸 Send a photo:",
        "action_title": "Choose action:", "edit_btn": "🖼 Edit", "anim_btn": "🎬 Animate",
        "presets_title": "Choose effect:", "btn_custom": "✍️ Custom Prompt",
        "enter_custom": "📝 Enter prompt:", "wait": "⏳ AI working... (up to 2 min)", "error_api": "❌ AI Error:"
    }
}

PRESETS = {
    "edit": {
        "en": {"Smile": "Make the person smile", "Younger": "Make the person look younger",
               "Cyberpunk": "Cyberpunk style"},
        "ru": {"Улыбка": "Make the person smile", "Моложе": "Make the person look younger",
               "Киберпанк": "Cyberpunk style"}
    },
    "animate": {
        "en": {"Wink": "Human winking", "Hello": "Human waving hand"},
        "ru": {"Подмигнуть": "Human winking", "Привет": "Human waving hand"}
    }
}

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class States(StatesGroup):
    awaiting_photo = State()
    awaiting_custom_prompt = State()


# --- Database ---
def init_db():
    with sqlite3.connect("database.db") as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, real_name TEXT, 
            coins INTEGER DEFAULT 10, joined_date TEXT, lang TEXT, last_bonus TEXT)""")


def get_user(user_id):
    with sqlite3.connect("database.db") as conn:
        res = conn.execute("SELECT coins, lang, last_bonus, real_name FROM users WHERE user_id = ?",
                           (user_id,)).fetchone()
        return res if res else (10, "ru", None, "User")


def update_user(user_id, **kwargs):
    with sqlite3.connect("database.db") as conn:
        for k, v in kwargs.items():
            conn.execute(f"UPDATE users SET {k} = ? WHERE user_id = ?", (v, user_id))


def get_string(uid, key):
    u = get_user(uid)
    return STRINGS.get(u[1], STRINGS["en"]).get(key, key)


def get_main_ikb(uid):
    s = lambda k: get_string(uid, k)
    builder = InlineKeyboardBuilder()
    builder.button(text=s("btn_create"), callback_data="ui_create")
    builder.button(text=s("btn_profile"), callback_data="ui_profile")
    builder.button(text=s("btn_ex"), callback_data="ui_examples")
    builder.button(text=s("btn_bonus"), callback_data="ui_bonus")
    builder.button(text=s("btn_lang"), callback_data="open_lang")
    builder.adjust(1, 2)
    return builder.as_markup()


# --- Handlers ---
@dp.message(Command("start"))
async def cmd_start(m: types.Message, state: FSMContext):
    await state.clear()
    with sqlite3.connect("database.db") as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, real_name, joined_date, coins, lang) VALUES (?,?,?,?,?,?)",
            (m.from_user.id, m.from_user.username, m.from_user.first_name, datetime.now().strftime("%d.%m.%Y"), 10,
             "ru"))
    u = get_user(m.from_user.id)
    await m.answer_photo(WELCOME_PHOTO_ID, caption=get_string(m.from_user.id, "start").format(coins=u[0]),
                         reply_markup=get_main_ikb(m.from_user.id), parse_mode="Markdown")


@dp.callback_query(F.data == "ui_create")
async def ui_create(c: types.CallbackQuery, state: FSMContext):
    await c.message.delete()
    await c.message.answer(get_string(c.from_user.id, "send_photo"),
                           reply_markup=InlineKeyboardBuilder().button(text=get_string(c.from_user.id, "back"),
                                                                       callback_data="back_to_main").as_markup())
    await state.set_state(States.awaiting_photo)


@dp.callback_query(F.data == "ui_profile")
async def ui_profile(c: types.CallbackQuery):
    u = get_user(c.from_user.id)
    text = f"👤 **{u[3]}**\n🆔 ID: `{c.from_user.id}`\n🪙 Баланс: {u[0]} монет\n🌐 Язык: {u[1].upper()}\n"
    builder = InlineKeyboardBuilder()
    builder.button(text=get_string(c.from_user.id, "back"), callback_data="back_to_main")
    await c.message.edit_caption(caption=text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@dp.callback_query(F.data == "ui_examples")
async def ui_examples_hub(c: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_string(c.from_user.id, "ex_edit_cat"), callback_data="ex_cat_edit")
    builder.button(text=get_string(c.from_user.id, "ex_anim_cat"), callback_data="ex_cat_anim")
    builder.button(text=get_string(c.from_user.id, "back"), callback_data="back_to_main")
    builder.adjust(1)
    await c.message.delete()
    await c.message.answer_photo(EXAMPLE_PHOTO_ID, caption="👀 Выберите категорию примеров:",
                                 reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith("ex_cat_"))
async def ui_examples_category(c: types.CallbackQuery):
    category = c.data.replace("ex_cat_", "")
    builder = InlineKeyboardBuilder()
    if category == "edit":
        builder.button(text="✨ Пример: Улыбка", callback_data="view_ex_edit_1")
        builder.button(text="✨ Пример: Киберпанк", callback_data="view_ex_edit_2")
    else:
        builder.button(text="✨ Пример: Подмигивание", callback_data="view_ex_anim_1")
        builder.button(text="✨ Пример: Привет", callback_data="view_ex_anim_2")
    builder.button(text=get_string(c.from_user.id, "back"), callback_data="ui_examples")
    builder.adjust(1)
    await c.message.delete()
    await c.message.answer_photo(EXAMPLE_PHOTO_ID, caption=f"📂 Выберите пример:", reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith("view_ex_"))
async def ui_view_example(c: types.CallbackQuery):
    ex_id = c.data.replace("view_ex_", "")
    back_cat = "ex_cat_edit" if "edit" in ex_id else "ex_cat_anim"
    data = EXAMPLES_MEDIA.get(ex_id)
    if not data: return await c.answer("Пример скоро будет добавлен!", show_alert=True)
    builder = InlineKeyboardBuilder()
    builder.button(text=get_string(c.from_user.id, "back"), callback_data=back_cat)
    await c.message.delete()
    try:
        if data["type"] == "video":
            await c.message.answer_video(data["file_id"], caption=data["caption"], reply_markup=builder.as_markup())
        else:
            await c.message.answer_photo(data["file_id"], caption=data["caption"], reply_markup=builder.as_markup())
    except:
        await c.message.answer("⚠️ Медиа не найдено.", reply_markup=builder.as_markup())


@dp.callback_query(F.data == "ui_bonus")
async def ui_bonus(c: types.CallbackQuery):
    user_id = c.from_user.id
    u = get_user(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    if u[2] == today:
        await c.answer(get_string(user_id, "bonus_fail"), show_alert=True)
    else:
        update_user(user_id, coins=u[0] + 1, last_bonus=today)
        await c.answer(get_string(user_id, "bonus_ok"), show_alert=True)
        u = get_user(user_id)
        await c.message.edit_caption(caption=get_string(user_id, "start").format(name=u[3], coins=u[0]),
                                     reply_markup=get_main_ikb(user_id), parse_mode="Markdown")


@dp.message(States.awaiting_photo, F.photo)
async def photo_handler(m: types.Message, state: FSMContext):
    await state.update_data(photo_id=m.photo[-1].file_id)
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{get_string(m.from_user.id, 'edit_btn')} ({COST_EDIT} 🪙)", callback_data="action_edit")
    builder.button(text=f"{get_string(m.from_user.id, 'anim_btn')} ({COST_ANIMATE} 🪙)", callback_data="action_animate")
    builder.button(text=get_string(m.from_user.id, "back"), callback_data="back_to_main")
    builder.adjust(1)
    await m.answer_photo(m.photo[-1].file_id, caption=get_string(m.from_user.id, "action_title"),
                         reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith("action_"))
async def show_presets(c: types.CallbackQuery, state: FSMContext):
    action = c.data.replace("action_", "")
    u = get_user(c.from_user.id)
    cost = COST_EDIT if action == "edit" else COST_ANIMATE
    if u[0] < cost: return await c.answer(get_string(c.from_user.id, "no_coins").format(need=cost), show_alert=True)
    await state.update_data(action=action, cost=cost)
    presets = PRESETS.get(action, {}).get(u[1], PRESETS.get(action, {}).get("en", {}))
    builder = InlineKeyboardBuilder()
    for label, _ in presets.items():
        builder.button(text=f"✨ {label}", callback_data=f"do_preset_{label[:10]}")
    builder.button(text=get_string(c.from_user.id, "btn_custom"), callback_data="do_custom")
    builder.button(text=get_string(c.from_user.id, "back"), callback_data="back_to_main")
    builder.adjust(2)
    await c.message.edit_caption(caption=get_string(c.from_user.id, "presets_title"), reply_markup=builder.as_markup())


@dp.callback_query(F.data == "do_custom")
async def do_custom(c: types.CallbackQuery, state: FSMContext):
    await c.message.edit_caption(caption=get_string(c.from_user.id, "enter_custom"))
    await state.set_state(States.awaiting_custom_prompt)


@dp.callback_query(F.data.startswith("do_preset_"))
async def handle_preset(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    u = get_user(c.from_user.id)
    presets = PRESETS.get(data['action'], {}).get(u[1], PRESETS.get(data['action'], {}).get("en", {}))
    label_part = c.data.replace("do_preset_", "")
    prompt = next((v for k, v in presets.items() if k[:10] == label_part), "Enhanced")
    await generate_content(c.message, state, prompt, c.from_user.id)


@dp.message(States.awaiting_custom_prompt)
async def handle_custom_prompt(m: types.Message, state: FSMContext):
    await generate_content(m, state, m.text, m.from_user.id)


# Таймауты и лимиты для RunPod (не блокируют других пользователей)
RUNPOD_TIMEOUT = aiohttp.ClientTimeout(total=900, connect=60)
MAX_WAIT_SEC = 900  # 15 минут на задачу (генерация до ~12 мин)
POLL_INTERVAL_SEC = 12


async def generate_content(message: types.Message, state: FSMContext, prompt_text: str, user_id: int):
    data = await state.get_data()
    u = get_user(user_id)
    cost = data.get("cost", 4)
    wait_msg = await bot.send_message(
        user_id,
        "⏳ Нейросеть Wan2.2 запущена. Рендер 8 сек видео — около 5–10 мин. Ожидайте.",
    )

    async with aiohttp.ClientSession(timeout=RUNPOD_TIMEOUT) as session:
        try:
            file_obj = BytesIO()
            tg_file = await bot.get_file(data["photo_id"])
            await bot.download_file(tg_file.file_path, destination=file_obj)
            raw_base64 = base64.b64encode(file_obj.getvalue()).decode("utf-8")
            image_data = f"data:image/jpeg;base64,{raw_base64}"

            url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/run"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {RUNPOD_API_KEY}",
            }
            # Улучшаем промпт для лучшего качества и соответствия
            enhanced_prompt = _enhance_prompt(prompt_text)
            
            payload = {
                "input": {
                    "image_base64": image_data,
                    "prompt": enhanced_prompt,
                    "seed": random.randint(1, 1000000000),
                    "steps": 18,  # Оптимальное качество без OOM
                    "cfg": 4.5,   # Сильное следование промпту
                }
            }

            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    await wait_msg.edit_text(f"❌ RunPod API: {resp.status}. {err_text[:200]}")
                    return
                result = await resp.json()

            job_id = result.get("id")
            if not job_id:
                await wait_msg.edit_text("❌ Не удалось получить ID задачи.")
                return

            await wait_msg.edit_text(f"⏳ Задание в очереди. ID: `{job_id}`. Ожидайте…")

            poll_url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{job_id}"
            start_time = time.time()
            last_msg_update = 0

            while time.time() - start_time < MAX_WAIT_SEC:
                await asyncio.sleep(POLL_INTERVAL_SEC)

                async with session.get(poll_url, headers=headers) as resp:
                    if resp.status != 200:
                        continue
                    status_data = await resp.json()

                status = status_data.get("status")

                if status == "COMPLETED":
                    output = status_data.get("output") or {}
                    if isinstance(output, dict) and output.get("error"):
                        await wait_msg.edit_text(f"❌ Ошибка нейросети: {output['error']}")
                        return

                    video_url = output.get("video_url") if isinstance(output, dict) else None
                    video_base64 = output.get("video_base64") if isinstance(output, dict) else None
                    seed = output.get("seed", "n/a") if isinstance(output, dict) else "n/a"

                    try:
                        if video_url:
                            await bot.send_video(
                                user_id,
                                video=video_url,
                                caption=f"✨ Видео готово!\n🎲 Seed: {seed}",
                            )
                        elif video_base64:
                            video_bytes = base64.b64decode(video_base64)
                            video_file = BufferedInputFile(
                                video_bytes,
                                filename=f"wan2_{job_id}.mp4",
                            )
                            await bot.send_video(
                                user_id,
                                video=video_file,
                                caption=f"✨ Видео готово!\n🎲 Seed: {seed}",
                            )
                        else:
                            await wait_msg.edit_text("❌ Нейросеть не вернула видео.")
                            return

                        new_balance = u[0] - cost
                        update_user(user_id, coins=new_balance)
                        await bot.send_message(
                            user_id,
                            f"🪙 Списано {cost} монет. Остаток: {new_balance}",
                        )
                        await wait_msg.delete()
                        return
                    except Exception as e:
                        logging.exception("Отправка видео в Telegram")
                        await wait_msg.edit_text(f"❌ Ошибка отправки видео: {str(e)}")
                        return

                if status in ("FAILED", "CANCELLED"):
                    err = (status_data.get("output") or {}).get("error", status)
                    await wait_msg.edit_text(f"❌ Задача прервана: {err}")
                    return

                elapsed = int(time.time() - start_time)
                if elapsed - last_msg_update >= 60:
                    last_msg_update = elapsed
                    try:
                        await wait_msg.edit_text(
                            f"⏳ Генерация… прошло {elapsed // 60} мин. Job: `{job_id}`",
                        )
                    except Exception:
                        pass

            await wait_msg.edit_text("❌ Время ожидания истекло (15 мин).")

        except asyncio.TimeoutError:
            await wait_msg.edit_text("❌ Таймаут соединения с RunPod.")
        except Exception as e:
            logging.exception("generate_content")
            await wait_msg.edit_text(f"❌ Ошибка: {str(e)}")
        finally:
            await state.clear()
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    u = get_user(c.from_user.id)
    await c.message.delete()
    await c.message.answer_photo(WELCOME_PHOTO_ID, caption=get_string(c.from_user.id, "start").format(coins=u[0]),
                                 reply_markup=get_main_ikb(c.from_user.id), parse_mode="Markdown")


@dp.callback_query(F.data == "open_lang")
async def open_lang(c: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇸 EN", callback_data="set_lang_en")
    builder.button(text="🇷🇺 RU", callback_data="set_lang_ru")
    builder.adjust(2)
    await c.message.edit_caption(caption="🌐 Change language:", reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith("set_lang_"))
async def set_lang(c: types.CallbackQuery):
    lang = c.data.replace("set_lang_", "")
    update_user(c.from_user.id, lang=lang)
    u = get_user(c.from_user.id)
    await c.message.delete()
    await c.message.answer_photo(WELCOME_PHOTO_ID,
                                 caption=get_string(c.from_user.id, "start").format(name=u[3], coins=u[0]),
                                 reply_markup=get_main_ikb(c.from_user.id), parse_mode="Markdown")


def _enhance_prompt(prompt: str) -> str:
    """Улучшает промпт для лучшего качества генерации."""
    prompt = prompt.strip()
    if not prompt:
        return "high quality, detailed, smooth motion, natural movement"
    
    # Добавляем качественные дескрипторы, если их нет
    quality_terms = [
        "high quality", "detailed", "smooth motion", "natural movement",
        "realistic", "sharp focus", "professional", "cinematic"
    ]
    
    prompt_lower = prompt.lower()
    has_quality = any(term in prompt_lower for term in quality_terms)
    
    if not has_quality:
        prompt = f"{prompt}, high quality, detailed, smooth motion, natural movement"
    
    return prompt


async def main():
    init_db()
    print("🚀 Бот запущен (Режим Multipart Upload)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())