from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from keyboards import get_main_reply_keyboard, generate_calendar_and_schedule
from database import get_user_tasks, get_user_score
from states import TaskForm
from datetime import datetime

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! ⏱️✨\n"
        "Я твой персональный трекер задач с поддержкой календаря и двойных напоминаний.\n\n"
        "Используй кнопки внизу экрана для быстрой работы 👇",
        reply_markup=get_main_reply_keyboard()
    )

@router.message(F.text == "ℹ️ Помощь")
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "💡 **Как пользоваться ботом:**\n\n"
        "1. Нажми **«➕ Добавить задачу»** или **«📅 Календарь»**.\n"
        "2. Выбери дату и время (из списка или напиши вручную, напр. 14:30).\n"
        "3. Бот пришлет **2 напоминания**:\n"
        "   — 📢 **За 1 день до дедлайна** (предварительное)\n"
        "   — 🔔 **В точное время сдачи** (основное)\n"
        "4. В **«📅 Календарь»** дни с запланированными задачами подсвечиваются иконкой 📌, а ниже виден список дел!",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="Markdown"
    )

@router.message(F.text == "📅 Календарь")
@router.message(Command("calendar"))
async def open_calendar_directly(message: types.Message, state: FSMContext):
    await state.clear()
    kb, schedule = generate_calendar_and_schedule(message.from_user.id)
    await message.answer(
        f"📅 **Календарь задач**\n"
        f"📌 — дни с запланированными делами\n"
        f"{schedule}\n"
        f"Выбери дату для добавления новой задачи:",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await state.set_state(TaskForm.waiting_for_date)

@router.message(F.text == "📋 Мои задачи")
@router.message(Command("list"))
async def show_user_tasks(message: types.Message):
    tasks = get_user_tasks(message.from_user.id)
    if not tasks:
        await message.answer("📋 **У вас пока нет активных задач.**", parse_mode="Markdown")
        return

    text = "📋 **Ваши активные задачи:**\n\n"
    for idx, (t_id, title, r_time) in enumerate(tasks, start=1):
        try:
            dt = datetime.strptime(r_time, "%Y-%m-%d %H:%M:%S")
            time_str = dt.strftime("%d.%m.%Y в %H:%M")
        except ValueError:
            time_str = r_time
        text += f"{idx}. **{title}** — 🗓 {time_str}\n"

    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "📊 Статистика")
@router.message(Command("stats"))
async def show_stats(message: types.Message):
    count = get_user_score(message.from_user.id)
    ach = "Новичок 🌱"
    if count >= 5: ach = "Повелитель времени ⏳🔥"
    if count >= 10: ach = "Мастер продуктивности 🏆👑"

    await message.answer(
        f"📊 **Ваша статистика:**\n\n"
        f"✅ Выполнено задач: **{count}**\n"
        f"🏆 Ваш ранг: **{ach}**",
        parse_mode="Markdown"
    )