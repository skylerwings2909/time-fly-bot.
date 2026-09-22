import logging
from datetime import datetime, timedelta
from aiogram import Router, F, types
from database import get_task_by_id, delete_task_from_db, increment_user_score
from keyboards import get_check_keyboard

router = Router()

async def send_reminder(bot, chat_id: int, task_id: int, is_advance: bool = False):
    title = get_task_by_id(task_id)
    try:
        if is_advance:
            await bot.send_message(
                chat_id=chat_id,
                text=f"📢 **Напоминание (Завтра дедлайн!)**\n"
                     f"Завтра необходимо завершить задачу: **«{title}»**! ⏳",
                parse_mode="Markdown"
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=f"🔔 **Время истекло! (Дедлайн)**\nКак дела с задачей: **«{title}»**?",
                reply_markup=get_check_keyboard(task_id),
                parse_mode="Markdown"
            )
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения: {e}")

@router.callback_query(F.data.startswith("done:"))
async def task_done(callback: types.CallbackQuery, scheduler):
    task_id = int(callback.data.split(":")[1])
    title = get_task_by_id(task_id)
    
    for j_type in ["main", "advance"]:
        job_id = f"job_{task_id}_{j_type}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

    delete_task_from_db(task_id)
    count = increment_user_score(callback.from_user.id)
    
    ach = "Новичок 🌱"
    if count >= 5: ach = "Повелитель времени ⏳🔥"
    if count >= 10: ach = "Мастер продуктивности 🏆👑"

    await callback.message.edit_text(
        f"🎉 **Отлично! Задача «{title}» выполнена!**\n\n"
        f"🏆 **Твой ранг:** {ach}\n"
        f"📊 Всего завершено задач: **{count}**",
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("more15:"))
async def task_more(callback: types.CallbackQuery, scheduler, bot):
    task_id = int(callback.data.split(":")[1])
    title = get_task_by_id(task_id)
    
    run_time = datetime.now() + timedelta(minutes=15)
    scheduler.add_job(
        send_reminder,
        'date',
        run_date=run_time,
        kwargs={'bot': bot, 'chat_id': callback.message.chat.id, 'task_id': task_id, 'is_advance': False},
        id=f"job_{task_id}_main"
    )
    await callback.message.edit_text(f"⏳ Добавлено еще **15 минут** на **«{title}»**.", parse_mode="Markdown")

@router.callback_query(F.data.startswith("replan:"))
async def task_replan(callback: types.CallbackQuery, scheduler, bot):
    task_id = int(callback.data.split(":")[1])
    title = get_task_by_id(task_id)
    
    run_time = datetime.now() + timedelta(hours=2)
    scheduler.add_job(
        send_reminder,
        'date',
        run_date=run_time,
        kwargs={'bot': bot, 'chat_id': callback.message.chat.id, 'task_id': task_id, 'is_advance': False},
        id=f"job_{task_id}_main"
    )
    await callback.message.edit_text(f"📅 Задача **«{title}»** отложена на 2 часа.", parse_mode="Markdown")

@router.callback_query(F.data.startswith("cancel:"))
async def task_cancel(callback: types.CallbackQuery, scheduler):
    task_id = int(callback.data.split(":")[1])
    title = get_task_by_id(task_id)
    
    for j_type in ["main", "advance"]:
        job_id = f"job_{task_id}_{j_type}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

    delete_task_from_db(task_id)
    await callback.message.edit_text(f"❌ Задача **«{title}»** отменена и удалена.", parse_mode="Markdown")