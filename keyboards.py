import calendar
from datetime import datetime
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters.callback_data import CallbackData
from database import get_user_tasks

class CalendarCallback(CallbackData, prefix="cal"):
    action: str
    year: int
    month: int
    day: int

def get_main_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить задачу"), KeyboardButton(text="📅 Календарь")],
            [KeyboardButton(text="📋 Мои задачи"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )

class CalendarCallback(CallbackData, prefix="cal"):
    action: str
    year: int
    month: int
    day: int
    weekday: int = 0

def generate_calendar_and_schedule(user_id: int, year: int = None, month: int = None):
    now = datetime.now()
    if year is None: year = now.year
    if month is None: month = now.month

    tasks = get_user_tasks(user_id)
    task_dates = set()
    month_tasks = []

    for _, title, r_time in tasks:
        try:
            dt = datetime.strptime(r_time, "%Y-%m-%d %H:%M:%S")
            task_dates.add(dt.strftime("%Y-%m-%d"))
            if dt.year == year and dt.month == month:
                month_tasks.append((dt, title))
        except ValueError:
            pass

    inline_kb = []
    month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", 
                   "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    inline_kb.append([InlineKeyboardButton(text=f"{month_names[month-1]} {year}", callback_data="ignore")])
    
    # Делаем дни недели кликабельными для фильтрации по конкретному дню недели
    days_head = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    week_row = []
    for idx, day_name in enumerate(days_head):
        week_row.append(InlineKeyboardButton(
            text=day_name, 
            callback_data=CalendarCallback(action="weekday_filter", year=year, month=month, day=0, weekday=idx).pack()
        ))
    inline_kb.append(week_row)

    cal = calendar.monthcalendar(year, month)
    today = now.date()

    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                date_obj = datetime(year, month, day).date()
                date_str = f"{year}-{month:02d}-{day:02d}"
                
                btn_text = str(day)
                has_task = date_str in task_dates
                
                if has_task:
                    btn_text = f"📌{day}"
                
                # Если день прошлый и на него нет задач — делаем скрытым/пустым
                if date_obj < today and not has_task:
                    row.append(InlineKeyboardButton(text="·", callback_data="ignore"))
                else:
                    row.append(InlineKeyboardButton(
                        text=btn_text,
                        callback_data=CalendarCallback(action="day", year=year, month=month, day=day).pack()
                    ))
        inline_kb.append(row)

    # Навигация по месяцам
    prev_m = month - 1 if month > 1 else 12
    prev_y = year if month > 1 else year - 1
    next_m = month + 1 if month < 12 else 1
    next_y = year if month < 12 else year + 1

    prev_button = InlineKeyboardButton(text="◀️", callback_data=CalendarCallback(action="prev", year=prev_y, month=prev_m, day=1).pack()) \
        if (prev_y > now.year or (prev_y == now.year and prev_m >= now.month)) \
        else InlineKeyboardButton(text="⏹", callback_data="ignore")

    inline_kb.append([
        prev_button,
        InlineKeyboardButton(text="▶️", callback_data=CalendarCallback(action="next", year=next_y, month=next_m, day=1).pack())
    ])

    # Дополнительные кнопки под календарем
    inline_kb.append([
        InlineKeyboardButton(text="✅ Сделанные задачи", callback_data="show_completed_history"),
        InlineKeyboardButton(text="📋 Все задачи", callback_data="show_all_tasks_inline")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_kb)

    schedule_text = f"\n📅 **Расписание на {month_names[month-1]}:**\n"
    if not month_tasks:
        schedule_text += "_Задач на этот месяц пока нет._\n"
    else:
        weekdays_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        month_tasks.sort(key=lambda x: x[0])
        for dt, title in month_tasks:
            w_name = weekdays_ru[dt.weekday()]
            schedule_text += f"• **{w_name} ({dt.strftime('%d.%m')}) в {dt.strftime('%H:%M')}** — {title}\n"

    return keyboard, schedule_text

def get_time_hours_keyboard(selected_date_str: str):
    all_hours = [f"{h:02d}:00" for h in range(8, 23)]
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    valid_hours = []
    for h in all_hours:
        if selected_date_str == today_str:
            hour_num = int(h.split(":")[0])
            if hour_num > now.hour:
                valid_hours.append(h)
        else:
            valid_hours.append(h)

    buttons = []
    row = []
    for h in valid_hours:
        row.append(InlineKeyboardButton(text=f"⏰ {h}", callback_data=f"sethour:{h}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="✍️ Ввести точное время (например 14:30)", callback_data="sethour:custom")])
    buttons.append([InlineKeyboardButton(text="⚡ Через 1 минуту (тест)", callback_data="sethour:quick_1min")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_check_keyboard(task_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, готово!", callback_data=f"done:{task_id}")],
        [InlineKeyboardButton(text="⏳ Дай еще 15 минут", callback_data=f"more15:{task_id}")],
        [InlineKeyboardButton(text="📅 Запланировать продолжение", callback_data=f"replan:{task_id}")],
        [InlineKeyboardButton(text="❌ Оно мне не надо", callback_data=f"cancel:{task_id}")]
    ])