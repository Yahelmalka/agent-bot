import os
import json
import asyncio
import pypdf
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
from agents import run_agent_system

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

AGENT_ICONS = {
    "Architect": "🏗️ *ארכיטקט*",
    "Builder": "💻 *בילדר*",
    "Debugger": "🐛 *דיבאגר*",
    "ExternalAgent": "🔌 *סוכן חיצוני*",
    "General": "💬 *עוזר כללי*",
}

STATE_FILE = "/data/user_state.json"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state():
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(USER_STATE, f, ensure_ascii=False)


USER_STATE = load_state()


def get_state(chat_id):
    state = USER_STATE.setdefault(
        str(chat_id),
        {"name": None, "history": [], "awaiting_name": True, "asked_name": False}
    )
    save_state()
    return state


def format_response(agent_name, text):
    icon = AGENT_ICONS.get(agent_name, "🤖 *תשובה*")
    return f"{icon}\n{'─' * 18}\n{text}"


async def keep_typing(context, chat_id):
    try:
        while True:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass


async def send_reply(context, chat_id, text):
    try:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    except Exception:
        await context.bot.send_message(chat_id=chat_id, text=text)


async def handle_name_step(context, chat_id, state, user_text=None):
    """מטפלת בשלב איסוף השם. מחזירה True אם הטיפול נעצר כאן (אין להמשיך הלאה)."""
    if not state["awaiting_name"]:
        return False

    if not state["asked_name"]:
        state["asked_name"] = True
        save_state()
        await context.bot.send_message(chat_id=chat_id, text="שלום! 👋 לפני שנתחיל — איך קוראים לך?")
        return True

    if user_text is None:
        await context.bot.send_message(chat_id=chat_id, text="רגע, לפני קבצים — איך קוראים לך קודם? 😊")
        return True

    state["name"] = user_text.strip()
    state["awaiting_name"] = False
    save_state()
    await context.bot.send_message(chat_id=chat_id, text=f"נעים להכיר, {state['name']}! 😊 במה אפשר לעזור?")
    return True


async def start_command(update, context):
    chat_id = update.message.chat_id
    USER_STATE[str(chat_id)] = {"name": None, "history": [], "awaiting_name": True, "asked_name": False}
    save_state()
    await handle_name_step(context, chat_id, USER_STATE[str(chat_id)])


async def help_command(update, context):
    help_text = (
        "*איך להשתמש בי:*\n\n"
        "פשוט כתבי הודעה, ואני אבין לבד לאיזה סוכן להעביר אותה.\n"
        "אפשר גם לשלוח קובץ PDF.\n\n"
        "/start — התחלה מחדש\n"
        "/help — ההודעה הזו"
    )
    await context.bot.send_message(chat_id=update.message.chat_id, text=help_text, parse_mode="Markdown")


async def handle_message(update, context):
    chat_id = update.message.chat_id
    user_text = update.message.text
    state = get_state(chat_id)

    if await handle_name_step(context, chat_id, state, user_text):
        return

    print(f"[{state['name']}] התקבל: {user_text}")

    typing_task = asyncio.create_task(keep_typing(context, chat_id))
    try:
        result_text, agent_name = await asyncio.to_thread(
            run_agent_system, user_text, state["history"], state["name"]
        )
    finally:
        typing_task.cancel()

    state["history"].append({"role": "user", "content": user_text})
    state["history"].append({"role": "assistant", "content": result_text})
    save_state()

    await send_reply(context, chat_id, format_response(agent_name, result_text))


async def handle_document(update, context):
    chat_id = update.message.chat_id
    state = get_state(chat_id)

    if await handle_name_step(context, chat_id, state):
        return

    document = update.message.document

    if not document.file_name.lower().endswith(".pdf"):
        await context.bot.send_message(chat_id=chat_id, text="כרגע אני יודעת לקרוא רק קבצי PDF 📄")
        return

    typing_task = asyncio.create_task(keep_typing(context, chat_id))
    try:
        file = await context.bot.get_file(document.file_id)
        temp_path = f"temp_{document.file_id}.pdf"
        await file.download_to_drive(temp_path)

        reader = pypdf.PdfReader(temp_path)
        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        os.remove(temp_path)

        caption = update.message.caption or "תעביר את הקובץ הזה לסוכן המתאים ועזור לי איתו"
        combined_text = f"{caption}\n\n--- תוכן הקובץ ---\n{extracted_text}"

        result_text, agent_name = await asyncio.to_thread(
            run_agent_system, combined_text, state["history"], state["name"]
        )
    finally:
        typing_task.cancel()

    state["history"].append({"role": "user", "content": f"[קובץ: {document.file_name}]"})
    state["history"].append({"role": "assistant", "content": result_text})
    save_state()

    await send_reply(context, chat_id, format_response(agent_name, result_text))


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start_command))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()