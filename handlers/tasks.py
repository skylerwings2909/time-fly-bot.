import re
from datetime import datetime, timedelta
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import TaskForm
from keyboards import (
    generate_calendar_and_schedule,
    get_time_hours_keyboard,
    CalendarCallback,
    get_main_reply_keyboard
)
from database import add_task_to_db, get_user_tasks

router = Router()

def schedule_notifications(scheduler, bot, chat_id: int, task_id: int, run_time: datetime):
    from handlers.callbacks import send_reminder
    
    scheduler.add_job(
        send_reminder,
        'date',
        run_date=run_time,
        kwargs={'bot': bot, 'chat_id': chat_id, 'task_id': task_id, 'is_advance': False},
        id=f"job_{task_id}_main"
    )

    advance_time = run_time - timedelta(days=1)
    if advance_time > datetime.now():
        scheduler.add_job(
            send_reminder,
            'date',
            run_date=advance_time,
            kwargs={'bot': bot, 'chat_id': chat_id, 'task_id': task_id, 'is_advance': True},
            id=f"job_{task_id}_advance"
        )

@router.message(F.text == "➕ Добавить задачу")
@router.message(Command("add"))
async def start_add_task(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("📝 Напиши название задачи:")
    await state.set_state(TaskForm.waiting_for_title)

@router.message(TaskForm.waiting_for_title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    kb, schedule = generate_calendar_and_schedule(message.from_user.id)
    await message.answer(
        f"Отлично! Задача: **«{message.text}»**.\n"
        f"{schedule}\n"
        f"📅 **Выбери дату выполнения в календаре:**",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await state.set_state(TaskForm.waiting_for_date)

@router.callback_query(CalendarCallback.filter(), TaskForm.waiting_for_date)
async def process_calendar_selection(callback: types.CallbackQuery, callback_data: CalendarCallback, state: FSMContext):
    if callback_data.action in ["prev", "next"]:
        kb, schedule = generate_calendar_and_schedule(callback.from_user.id, callback_data.year, callback_data.month)
        await callback.message.edit_text(
            f"📅 **Календарь задач**\n{schedule}\nВыбери дату:",
            reply_markup=kb,
            parse_mode="Markdown"
        )
    elif callback_data.action == "day":
        selected_date = f"{callback_data.year}-{callback_data.month:02d}-{callback_data.day:02d}"
        await state.update_data(selected_date=selected_date)
        
        data = await state.get_data()
        
        if 'title' not in data:
            await callback.message.edit_text(
                f"📅 Выбрана дата: **{selected_date}**\n\n📝 Теперь введи название задачи для этой даты:",
                parse_mode="Markdown"
            )
            await state.set_state(TaskForm.waiting_for_title)
            return

        kb = get_time_hours_keyboard(selected_date)
        await callback.message.edit_text(
            f"📅 Выбрана дата: **{selected_date}**\n\n⏰ Выбери время напоминания или введи точное время вручную:",
            reply_markup=kb,
            parse_mode="Markdown"
        )
        await state.set_state(TaskForm.waiting_for_time)

@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: types.CallbackQuery):
    await callback.answer("Эта дата недоступна!", show_alert=False)

@router.callback_query(TaskForm.waiting_for_time, F.data.startswith("sethour:"))
async def process_time_selection(callback: types.CallbackQuery, state: FSMContext, scheduler, bot):
    hour_choice = callback.data.split(":")[1]
    data = await state.get_data()

    if hour_choice == "custom":
        await callback.message.edit_text(
            "✍️ **Введи точное время** в формате `ЧЧ:ММ` (например: `14:30` или `09:15`):",
            parse_mode="Markdown"
        )
        await state.set_state(TaskForm.waiting_for_custom_time)
        return

    title = data['title']
    chat_id = callback.message.chat.id

    if hour_choice == "quick_1min":
        run_time = datetime.now() + timedelta(minutes=1)
    else:
        if ":" not in hour_choice:
            hour_choice = f"{int(hour_choice):02d}:00"
        selected_date_str = data['selected_date']
        target_str = f"{selected_date_str} {hour_choice}"
        run_time = datetime.strptime(target_str, "%Y-%m-%d %H:%M")

    run_time_str = run_time.strftime("%Y-%m-%d %H:%M:%S")
    task_id = add_task_to_db(chat_id, title, run_time_str)

    schedule_notifications(scheduler, bot, chat_id, task_id, run_time)

    await callback.message.edit_text(
        f"🎯 Задача **«{title}»** запланирована!\n"
        f"🗓 Дедлайн: **{run_time.strftime('%d.%m.%Y в %H:%M')}**\n"
        f"🔔 Напоминания установлены: за 1 день и в момент сдачи!",
        parse_mode="Markdown"
    )
    await state.clear()

@router.message(TaskForm.waiting_for_custom_time)
async def process_custom_time(message: types.Message, state: FSMContext, scheduler, bot):
    time_text = message.text.strip()
    
    if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", time_text):
        await message.answer(
            "⚠️ **Некорректный формат времени!**\n"
            "Пожалуйста, введи время в формате `ЧЧ:ММ` (например: `14:30`, `09:05` или `18:00`).",
            parse_mode="Markdown"
        )
        return

    data = await state.get_data()
    selected_date_str = data['selected_date']
    title = data['title']
    chat_id = message.chat.id

    h, m = time_text.split(":")
    formatted_time = f"{int(h):02d}:{int(m):02d}"

    target_str = f"{selected_date_str} {formatted_time}"
    run_time = datetime.strptime(target_str, "%Y-%m-%d %H:%M")

    if run_time <= datetime.now():
        await message.answer(
            "⚠️ Это время на сегодня уже прошло! Введи время, которое ещё не наступило:",
            parse_mode="Markdown"
        )
        return

    run_time_str = run_time.strftime("%Y-%m-%d %H:%M:%S")
    task_id = add_task_to_db(chat_id, title, run_time_str)

    schedule_notifications(scheduler, bot, chat_id, task_id, run_time)

    await message.answer(
        f"🎯 Задача **«{title}»** запланирована!\n"
        f"🗓 Дедлайн: **{run_time.strftime('%d.%m.%Y в %H:%M')}**\n"
        f"🔔 Напоминания установлены: за 1 день и в момент сдачи!",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="Markdown"
    )
    await state.clear()

# --- НОВЫЕ ОБРАБОТЧИКИ ДЛЯ КАЛЕНДАРЯ И КНОПОК ---

@router.callback_query(CalendarCallback.filter(F.action == "weekday_filter"))
async def process_weekday_filter(callback: types.CallbackQuery, callback_data: CalendarCallback):
    weekdays_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    target_weekday = callback_data.weekday
    
    tasks = get_user_tasks(callback.from_user.id)
    matched = []
    
    for _, title, r_time in tasks:
        try:
            dt = datetime.strptime(r_time, "%Y-%m-%d %H:%M:%S")
            # Проверяем совпадение дня недели (не ограничиваемся текущим месяцем)
            if dt.weekday() == target_weekday:
                matched.append((dt, title))
        except ValueError:
            pass

    text = f"📌 **Все ваши задачи по дням недели — {weekdays_ru[target_weekday]}:**\n\n"
    if not matched:
        text += f"_У вас нет запланированных задач на этот день недели._"
    else:
        # Сортируем по дате от ближайших к далёким
        matched.sort(key=lambda x: x[0])
        for dt, title in matched:
            text += f"• **{dt.strftime('%d.%m.%Y')} в {dt.strftime('%H:%M')}** — {title}\n"

    await callback.answer()
    await callback.message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data == "show_completed_history")
async def show_completed_history_inline(callback: types.CallbackQuery):
    from database import get_user_score
    count = get_user_score(callback.from_user.id)
    await callback.answer()
    await callback.message.answer(
        f"📊 **История выполненных задач:**\n\n"
        f"Всего успешно завершено: **{count}** задач(и).\n"
        f"_Каждая выполненная задача повышает ваш ранг продуктивности!_",
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "show_all_tasks_inline")
async def show_all_tasks_inline_handler(callback: types.CallbackQuery):
    tasks = get_user_tasks(callback.from_user.id)
    if not tasks:
        await callback.answer("Список задач пуст", show_alert=True)
        return
    
    text = "📋 **Ваш полный список активных задач:**\n\n"
    for idx, (_, title, r_time) in enumerate(tasks, start=1):
        text += f"{idx}. **{title}** — 🗓 {r_time}\n"
        
    await callback.answer()
    await callback.message.answer(text, parse_mode="Markdown")