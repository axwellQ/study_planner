import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Токен из config.py
try:
    from config import TELEGRAM_BOT_TOKEN
except ImportError:
    raise Exception("Создай config.py с TELEGRAM_BOT_TOKEN!")

DATA_FILE = "deadlines.json"


def load_all_users():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = (
        "👋 Привет! Я — твой Study Planner Bot.\n\n"
        f"Твой ID: <code>{chat_id}</code>\n"
        "Введи его в приложение Study Planner.\n\n"
        "Команды:\n"
        "/tasks — показать мои дедлайны"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    all_users = load_all_users()

    if chat_id not in all_users:
        await update.message.reply_text("❌ Сначала добавь дедлайны в приложение.")
        return

    deadlines = all_users[chat_id].get("deadlines", [])
    if not deadlines:
        await update.message.reply_text("📭 Нет дедлайнов.")
        return

    today = datetime.today().date()
    text = "📚 Твои дедлайны:\n\n"

    for item in deadlines:
        try:
            due = datetime.strptime(item["due_date"], "%Y-%m-%d").date()
        except:
            continue

        days_left = (due - today).days
        status = "✅" if item.get("done") else ("❌" if days_left < 0 else "⏳")
        text += f"{status} {item['due_date']} | {item['subject']} — {item['task']}\n"

    if len(text) > 4000:
        text = text[:4000] + "\n... (сокращено)"
    await update.message.reply_text(text)


def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tasks", tasks))
    print("✅ Бот запущен. Напиши ему /start или /tasks")
    app.run_polling()


if __name__ == "__main__":
    main()