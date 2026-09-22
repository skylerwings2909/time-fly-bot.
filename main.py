import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TOKEN
from database import init_db, get_all_uncompleted_tasks
from handlers import common, tasks, callbacks
from handlers.callbacks import send_reminder

logging.basicConfig(level=logging.INFO)

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота / Главное меню"),
        BotCommand(command="add", description="Добавить новую задачу"),
        BotCommand(command="calendar", description="Открыть календарь"),
        BotCommand(command="list", description="Активные задачи"),
        BotCommand(command="stats", description="Моя статистика"),
        BotCommand(command="help", description="Инструкция")
    ]
    await bot.set_my_commands(commands)

async def restore_scheduled_jobs(scheduler: AsyncIOScheduler, bot: Bot):
    """Восстанавливает планирование всех задач из базы данных при перезапуске бота"""
    tasks_list = get_all_uncompleted_tasks()
    now = datetime.now()
    restored_count = 0

    for task_id, user_id, title, run_time_str in tasks_list:
        try:
            run_time = datetime.strptime(run_time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

        if run_time > now:
            # Восстанавливаем основное напоминание
            scheduler.add_job(
                send_reminder,
                'date',
                run_date=run_time,
                kwargs={'bot': bot, 'chat_id': user_id, 'task_id': task_id, 'is_advance': False},
                id=f"job_{task_id}_main",
                replace_existing=True
            )

            # Восстанавливаем предварительное напоминание (за 24 часа)
            advance_time = run_time - timedelta(days=1)
            if advance_time > now:
                scheduler.add_job(
                    send_reminder,
                    'date',
                    run_date=advance_time,
                    kwargs={'bot': bot, 'chat_id': user_id, 'task_id': task_id, 'is_advance': True},
                    id=f"job_{task_id}_advance",
                    replace_existing=True
                )
            restored_count += 1
        else:
            # Если время задачи прошло во время простоя бота — сразу отправляем уведомление
            asyncio.create_task(send_reminder(bot, chat_id=user_id, task_id=task_id, is_advance=False))

    logging.info(f"🔄 Успешно восстановлено задач в планировщике: {restored_count}")

async def main():
    init_db()

    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    scheduler = AsyncIOScheduler()

    # Передаем зависимости (scheduler, bot) прямо в handlers
    dp.workflow_data.update({
        "scheduler": scheduler,
        "bot": bot
    })

    # Подключаем роутеры
    dp.include_router(common.router)
    dp.include_router(tasks.router)
    dp.include_router(callbacks.router)

    await set_bot_commands(bot)

    # Запускаем планировщик и восстанавливаем задачи
    scheduler.start()
    await restore_scheduled_jobs(scheduler, bot)

    # Сбрасываем накопленные обновления и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Мини-сервер, чтобы Render не отключал Web Service
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# Запускаем мини-сервер в отдельном потоке перед стартом бота
threading.Thread(target=run_web_server, daemon=True).start()