import json
import os
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import requests

try:
    from config import TELEGRAM_BOT_TOKEN
except ImportError:
    TELEGRAM_BOT_TOKEN = None
    print("⚠️ Файл config.py не найден. Уведомления в Telegram отключены.")

DATA_FILE = "deadlines.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"user_name": "", "telegram_id": "", "deadlines": []}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        if isinstance(raw_data, list):
            # Старый формат — только список дедлайнов
            return {
                "user_name": "",
                "telegram_id": "",
                "deadlines": raw_data
            }
        elif isinstance(raw_data, dict):
            # Новый формат
            return {
                "user_name": raw_data.get("user_name", ""),
                "telegram_id": raw_data.get("telegram_id", ""),
                "deadlines": raw_data.get("deadlines", [])
            }
        else:
            return {"user_name": "", "telegram_id": "", "deadlines": []}
    except (json.JSONDecodeError, IOError, ValueError):
        return {"user_name": "", "telegram_id": "", "deadlines": []}


def save_data(data):
    """Сохраняет данные в JSON"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def send_telegram_message(chat_id, text):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        print("❌ Не отправлено: отсутствует токен или chat_id")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, data={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        })
        if response.status_code == 200:
            print(f"✅ Уведомление отправлено в чат {chat_id}")
            return True
        else:
            print(f"❌ Ошибка Telegram API ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"💥 Ошибка при отправке: {e}")
        return False



def check_and_notify(deadlines, telegram_id):
    today = datetime.today().date()
    notified = False
    for item in deadlines:
        if item.get("notified_7") and item.get("notified_1"):
            continue
        try:
            due_date = datetime.strptime(item["due_date"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue

        days_left = (due_date - today).days
        msg = None

        if days_left == 7 and not item.get("notified_7"):
            msg = f"🔔 Напоминание: через 7 дней дедлайн!\n\n📚 {item['subject']}\n📝 {item['task']}\n📅 {item['due_date']}"
            item["notified_7"] = True
            notified = True
        elif days_left == 1 and not item.get("notified_1"):
            msg = f"⚠️ ВНИМАНИЕ: завтра дедлайн!\n\n📚 {item['subject']}\n📝 {item['task']}\n📅 {item['due_date']}"
            item["notified_1"] = True
            notified = True

        if msg and telegram_id:
            send_telegram_message(telegram_id, msg)
    return notified


def ask_for_profile():
    root = tk.Tk()
    root.withdraw()  # скрыть окно

    name = simpledialog.askstring("Профиль", "Как тебя зовут?", parent=root)
    if not name:
        name = "Студент"

    telegram_help = (
        "Введи свой Telegram ID:\n"
        "1. Напиши /start боту @my_study_planner_bot\n"
        "2. Вставь сюда число (например: 123456789)\n\n"
        "Если оставить пустым — уведомлений не будет."
    )
    telegram_id = simpledialog.askstring("Telegram", telegram_help, parent=root)
    root.destroy()

    return name.strip(), (telegram_id.strip() if telegram_id else "")


def mark_as_done(deadlines, index, listbox, user_name, telegram_id):
    if 0 <= index < len(deadlines):
        deadlines[index]["done"] = True
        save_data({"user_name": user_name, "telegram_id": telegram_id, "deadlines": deadlines})
        refresh_list(listbox, deadlines, user_name)
        messagebox.showinfo("Отлично!", "Дедлайн отмечен как выполненный ✅")


def refresh_list(listbox, deadlines, user_name):
    listbox.delete(0, tk.END)
    today = datetime.today().date()
    for i, item in enumerate(deadlines):
        try:
            due = datetime.strptime(item["due_date"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue

        days_left = (due - today).days

        if item.get("done"):
            prefix = "✅"
            color = "green"
        elif days_left < 0:
            prefix = "❌"
            color = "red"
        elif days_left == 0:
            prefix = "🔥"
            color = "darkred"
        elif days_left <= 7:
            prefix = "⚠️"
            color = "orange"
        else:
            prefix = "📅"
            color = "black"

        line = f"{prefix} {item['due_date']} | {item['subject']} — {item['task']}"
        listbox.insert(tk.END, line)
        listbox.itemconfig(i, {'fg': color})


def create_main_window(user_name, telegram_id, deadlines):
    root = tk.Tk()
    root.title("🎓 Планировщик учёбы")
    root.geometry("680x640")

    # Приветствие
    status = "🔔 Уведомления включены!" if telegram_id else "🔕 Уведомления отключены"
    greeting = f"Привет, {user_name}! 👋\n{status}"
    ttk.Label(root, text=greeting, font=("Arial", 12, "bold"), foreground="blue", justify="center").pack(pady=5)

    # Форма добавления
    frame_input = ttk.Frame(root, padding="10")
    frame_input.pack(fill=tk.X)

    ttk.Label(frame_input, text="Предмет:").grid(row=0, column=0, sticky=tk.W)
    entry_subject = ttk.Entry(frame_input, width=30)
    entry_subject.grid(row=0, column=1, padx=5, pady=2)

    ttk.Label(frame_input, text="Задание:").grid(row=1, column=0, sticky=tk.W)
    entry_task = ttk.Entry(frame_input, width=30)
    entry_task.grid(row=1, column=1, padx=5, pady=2)

    ttk.Label(frame_input, text="Дата (ГГГГ-ММ-ДД):").grid(row=2, column=0, sticky=tk.W)
    entry_date = ttk.Entry(frame_input, width=30)
    entry_date.grid(row=2, column=1, padx=5, pady=2)

    def on_add():
        subj = entry_subject.get().strip()
        task = entry_task.get().strip()
        date_str = entry_date.get().strip()
        if not subj or not task or not date_str:
            messagebox.showerror("Ошибка", "Заполни все поля!")
            return
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Ошибка", "Дата в формате ГГГГ-ММ-ДД")
            return

        new_deadline = {
            "subject": subj,
            "task": task,
            "due_date": date_str,
            "done": False,
            "notified_7": False,
            "notified_1": False
        }
        deadlines.append(new_deadline)
        save_data({"user_name": user_name, "telegram_id": telegram_id, "deadlines": deadlines})
        refresh_list(listbox, deadlines, user_name)
        entry_subject.delete(0, tk.END)
        entry_task.delete(0, tk.END)
        entry_date.delete(0, tk.END)
        messagebox.showinfo("Успех", "Дедлайн добавлен!")

    ttk.Button(frame_input, text="Добавить", command=on_add).grid(row=3, column=1, pady=10)

    ttk.Label(root, text="Все дедлайны:", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=(10, 0))
    listbox = tk.Listbox(root, height=20, width=95)
    listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

    def on_done():
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выбери дедлайн в списке")
            return
        idx = selection[0]
        mark_as_done(deadlines, idx, listbox, user_name, telegram_id)

    ttk.Button(root, text="Отметить как выполненное ✅", command=on_done).pack(pady=5)

    refresh_list(listbox, deadlines, user_name)

    def background_check():
        if check_and_notify(deadlines, telegram_id):
            save_data({"user_name": user_name, "telegram_id": telegram_id, "deadlines": deadlines})

    threading.Thread(target=background_check, daemon=True).start()

    root.mainloop()


def main():
    data = load_data()
    user_name = data.get("user_name", "").strip()
    telegram_id = data.get("telegram_id", "").strip()
    deadlines = data.get("deadlines", [])

    if not user_name:
        user_name, telegram_id = ask_for_profile()
        save_data({"user_name": user_name, "telegram_id": telegram_id, "deadlines": deadlines})

    create_main_window(user_name, telegram_id, deadlines)


if __name__ == "__main__":
    main()