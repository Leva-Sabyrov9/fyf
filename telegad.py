import asyncio
import logging
import random
from datetime import datetime, time
from telebot.async_telebot import AsyncTeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pytz


BOT_TOKEN = '8350110594:AAG2NTwYI42RKPhWWORicT90efoEMRYqs4Q'
CHANNEL_ID = '-1002907497877'
ADMIN_ID = 582959560
# Добавим ID пользователя, которому будем отправлять юзернеймы
TARGET_USER_ID = 7474375848  # Можно установить конкретный ID или оставить None для отправки самому себе

bot = AsyncTeleBot(BOT_TOKEN)
scheduler = AsyncIOScheduler(timezone=pytz.timezone('Europe/Moscow'))
usernames = set()
awaiting_usernames = {}
awaiting_delete = {}
awaiting_target_user = {}  # Для установки ID целевого пользователя


def create_main_keyboard():
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        KeyboardButton('Добавить юзернеймы'),
        KeyboardButton('Показать список'),
        KeyboardButton('Запустить расписание'),
        KeyboardButton('Остановить расписание'),
        KeyboardButton('Опубликовать случайный'),
        KeyboardButton('Удалить юзернеймы'),
        KeyboardButton('Статус'),
        KeyboardButton('Помощь'),
        KeyboardButton('Настройка получателя')  # Новая кнопка
    )
    return keyboard


def create_delete_keyboard():
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        KeyboardButton('Удалить все'),
        KeyboardButton('Выбрать для удаления'),
        KeyboardButton('Назад')
    )
    return keyboard

def create_settings_keyboard():
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        KeyboardButton('Установить ID получателя'),
        KeyboardButton('Текущий получатель'),
        KeyboardButton('Отправить тестовое сообщение'),
        KeyboardButton('Назад')
    )
    return keyboard

@bot.message_handler(commands=['start'])
async def send_welcome(message):
    keyboard = create_main_keyboard()
    await bot.reply_to(message, "Привет! Я бот для публикации юзернеймов. Выбери действие:", reply_markup=keyboard)

@bot.message_handler(commands=['help'])
async def send_help(message):
    help_text = """
Доступные команды:
/add - добавить юзернеймы (через пробел)
/list - показать текущий список
/start_schedule - запустить расписание
/stop_schedule - остановить расписание
/publish_random - опубликовать случайный юзернейм
/delete - удалить юзернеймы
/status - показать статус
/get_chat_id - получить ID текущего чата
/set_target - установить ID получателя юзернеймов

Или используйте кнопки ниже для удобства!
"""
    keyboard = create_main_keyboard()
    await bot.reply_to(message, help_text, reply_markup=keyboard)

@bot.message_handler(func=lambda message: True)
async def handle_buttons(message):
    if message.from_user.id != ADMIN_ID:
        await bot.reply_to(message, "У вас нет прав для управления ботом")
        return
    
    if message.chat.id in awaiting_usernames:
        await process_usernames_input(message)
        return
    
    if message.chat.id in awaiting_delete:
        await process_delete_input(message)
        return
        
    if message.chat.id in awaiting_target_user:
        await process_target_user_input(message)
        return
    
    if message.text == 'Добавить юзернеймы':
        awaiting_usernames[message.chat.id] = True
        await bot.reply_to(message, "Введите юзернеймы через пробел:")
        
    elif message.text == 'Показать список':
        await show_usernames(message)
        
    elif message.text == 'Запустить расписание':
        await start_schedule(message)
        
    elif message.text == 'Остановить расписание':
        await stop_schedule(message)
        
    elif message.text == 'Опубликовать случайный':
        await publish_random(message)
        
    elif message.text == 'Удалить юзернеймы':
        keyboard = create_delete_keyboard()
        await bot.reply_to(message, "Выберите действие:", reply_markup=keyboard)
        
    elif message.text == 'Удалить все':
        await delete_all_usernames(message)
        
    elif message.text == 'Выбрать для удаления':
        awaiting_delete[message.chat.id] = True
        await bot.reply_to(message, "Введите юзернеймы для удаления через пробел:", reply_markup=create_main_keyboard())
        
    elif message.text == 'Настройка получателя':
        keyboard = create_settings_keyboard()
        await bot.reply_to(message, "Настройки получателя:", reply_markup=keyboard)
        
    elif message.text == 'Установить ID получателя':
        awaiting_target_user[message.chat.id] = True
        await bot.reply_to(message, "Введите ID пользователя, которому нужно отправлять юзернеймы:", reply_markup=create_main_keyboard())
        
    elif message.text == 'Текущий получатель':
        if TARGET_USER_ID:
            await bot.reply_to(message, f"Текущий получатель: {TARGET_USER_ID}")
        else:
            await bot.reply_to(message, "Получатель не установлен. Юзернеймы будут отправляться вам.")
            
    elif message.text == 'Отправить тестовое сообщение':
        if TARGET_USER_ID:
            try:
                await bot.send_message(TARGET_USER_ID, "Тестовое сообщение от бота")
                await bot.reply_to(message, "Тестовое сообщение отправлено!")
            except Exception as e:
                await bot.reply_to(message, f"Ошибка отправки: {e}")
        else:
            await bot.reply_to(message, "Сначала установите ID получателя")
        
    elif message.text == 'Назад':
        keyboard = create_main_keyboard()
        await bot.reply_to(message, "Главное меню:", reply_markup=keyboard)
        
    elif message.text == 'Статус':
        await send_status(message)
        
    elif message.text == 'Помощь':
        await send_help(message)
        
    else:
        pass


async def process_target_user_input(message):
    global TARGET_USER_ID
    
    if message.chat.id in awaiting_target_user:
        del awaiting_target_user[message.chat.id]
    
    try:
        TARGET_USER_ID = int(message.text)
        await bot.reply_to(message, f"ID получателя установлен: {TARGET_USER_ID}")
    except ValueError:
        await bot.reply_to(message, "Неверный формат ID. Введите числовой ID.")


async def process_usernames_input(message):
    if message.chat.id in awaiting_usernames:
        del awaiting_usernames[message.chat.id]
    
    args = message.text.split()
    if not args:
        await bot.reply_to(message, "Не указаны юзернеймы")
        return
    
    new_usernames = {f'@{u.strip().lstrip("@")}' for u in args}
    usernames.update(new_usernames)
    
    try:
        status_msg = await create_status_message()
        await bot.send_message(ADMIN_ID, f"✅ Добавлены новые юзернеймы: {', '.join(new_usernames)}\n\n{status_msg}")
    except Exception as e:
        print(f"Ошибка отправки статуса в личку: {e}")
    
    await bot.reply_to(message, f"✅ Добавлено {len(new_usernames)} юзернеймов: {', '.join(new_usernames)}")


async def process_delete_input(message):
    if message.chat.id in awaiting_delete:
        del awaiting_delete[message.chat.id]
    
    args = message.text.split()
    if not args:
        await bot.reply_to(message, "Не указаны юзернеймы для удаления")
        return
    
    to_delete = {f'@{u.strip().lstrip("@")}' for u in args}
    
    deleted = set()
    for username in to_delete:
        if username in usernames:
            usernames.remove(username)
            deleted.add(username)
    
    if deleted:
        try:
            status_msg = await create_status_message()
            await bot.send_message(ADMIN_ID, f"❌ Удалены юзернеймы: {', '.join(deleted)}\n\n{status_msg}")
        except Exception as e:
            print(f"Ошибка отправки статуса в личку: {e}")
        
        await bot.reply_to(message, f"✅ Удалено {len(deleted)} юзернеймов: {', '.join(deleted)}")
    else:
        await bot.reply_to(message, "❌ Не найдено юзернеймов для удаления")


async def delete_all_usernames(message):
    if not usernames:
        await bot.reply_to(message, "Список юзернеймов уже пуст")
        return
    
    count = len(usernames)
    usernames.clear()
    
    try:
        status_msg = await create_status_message()
        await bot.send_message(ADMIN_ID, f"❌ Удалены все юзернеймы ({count})\n\n{status_msg}")
    except Exception as e:
        print(f"Ошибка отправки статуса в личку: {e}")
    
    await bot.reply_to(message, f"✅ Удалены все юзернеймы ({count})", reply_markup=create_main_keyboard())


async def create_status_message():
    if not usernames:
        return "📊 Статус:\n• Юзернеймов: 0\n• Расписание: " + ("✅ Активно" if scheduler.get_job('username_poster') else "❌ Неактивно")
    
    schedule_status = "✅ Активно" if scheduler.get_job('username_poster') else "❌ Неактивно"
    
    target_info = f"\n• Получатель: {TARGET_USER_ID if TARGET_USER_ID else 'Не установлен'}"
    
    status_msg = f"📊 Статус:\n• Юзернеймов: {len(usernames)}\n• Расписание: {schedule_status}{target_info}\n\n📝 Список юзернеймов:\n"
    status_msg += "\n".join(f"{i+1}. {username}" for i, username in enumerate(usernames))
    
    return status_msg

async def send_status(message):
    status_msg = await create_status_message()
    await bot.reply_to(message, status_msg)

@bot.message_handler(commands=['get_chat_id'])
async def get_chat_id(message):
    chat_id = message.chat.id
    await bot.reply_to(message, f"ID этого чата: {chat_id}")

@bot.message_handler(commands=['set_target'])
async def set_target_user(message):
    if message.from_user.id != ADMIN_ID:
        await bot.reply_to(message, "У вас нет прав для этой команды")
        return
    
    args = message.text.split()[1:]
    if not args:
        await bot.reply_to(message, "Укажите ID пользователя после команды /set_target")
        return
    
    try:
        global TARGET_USER_ID
        TARGET_USER_ID = int(args[0])
        await bot.reply_to(message, f"ID получателя установлен: {TARGET_USER_ID}")
    except ValueError:
        await bot.reply_to(message, "Неверный формат ID. Введите числовой ID.")


@bot.message_handler(commands=['add'])
async def add_usernames(message):
    if message.from_user.id != ADMIN_ID:
        await bot.reply_to(message, "У вас нет прав для этой команды")
        return
    
    args = message.text.split()[1:]
    if not args:
        await bot.reply_to(message, "Укажите юзернеймы через пробел после команды /add")
        return
    
    new_usernames = {f'@{u.strip().lstrip("@")}' for u in args}
    usernames.update(new_usernames)
    
    try:
        status_msg = await create_status_message()
        await bot.send_message(ADMIN_ID, f"✅ Добавлены новые юзернеймы: {', '.join(new_usernames)}\n\n{status_msg}")
    except Exception as e:
        print(f"Ошибка отправки статуса в личку: {e}")
    
    await bot.reply_to(message, f"✅ Добавлено {len(new_usernames)} юзернеймов: {', '.join(new_usernames)}")

@bot.message_handler(commands=['delete'])
async def delete_usernames(message):
    if message.from_user.id != ADMIN_ID:
        await bot.reply_to(message, "У вас нет прав для этой команды")
        return
    
    args = message.text.split()[1:]
    if not args:
        await bot.reply_to(message, "Укажите юзернеймы для удаления через пробел после команды /delete")
        return
    
    to_delete = {f'@{u.strip().lstrip("@")}' for u in args}
    
    deleted = set()
    for username in to_delete:
        if username in usernames:
            usernames.remove(username)
            deleted.add(username)
    
    if deleted:
        try:
            status_msg = await create_status_message()
            await bot.send_message(ADMIN_ID, f"❌ Удалены юзернеймы: {', '.join(deleted)}\n\n{status_msg}")
        except Exception as e:
            print(f"Ошибка отправки статуса в личку: {e}")
        
        await bot.reply_to(message, f"✅ Удалено {len(deleted)} юзернеймов: {', '.join(deleted)}")
    else:
        await bot.reply_to(message, "❌ Не найдено юзернеймов для удаления")


@bot.message_handler(commands=['list'])
async def show_usernames(message):
    if not usernames:
        await bot.reply_to(message, "Список юзернеймов пуст")
        return
    
    message_text = "📋 Текущий список юзернеймов:\n" + "\n".join(
        f"{i+1}. {username}" for i, username in enumerate(usernames)
    )
    await bot.reply_to(message, message_text)


@bot.message_handler(commands=['status'])
async def status_command(message):
    await send_status(message)


def is_time_between(start_time, end_time):
    moscow_tz = pytz.timezone('Europe/Moscow')
    current_time = datetime.now(moscow_tz).time()
    return start_time <= current_time <= end_time


async def send_to_target_user(username):
    """Функция для отправки юзернейма целевому пользователю"""
    if not TARGET_USER_ID:
        # Если получатель не установлен, отправляем админу
        target_id = ADMIN_ID
    else:
        target_id = TARGET_USER_ID
    
    try:
        # Форматируем сообщение в нужном формате
        username_clean = username.lstrip('@')
        message_text = f"@{username_clean}\nT.me/{username_clean}"
        await bot.send_message(target_id, message_text)
        return True
    except Exception as e:
        print(f"Ошибка отправки целевому пользователю: {e}")
        return False


async def post_random_username():
    if not is_time_between(time(12, 0), time(19, 0)):
        print("Сейчас не время для публикации (12:00-19:00 МСК)")
        return
        
    if not usernames:
        print("Список юзернеймов пуст, нечего публиковать")
        return
    
    random_username = random.choice(list(usernames))
    message_text = f"🎲 Случайный юзернейм: {random_username}"
    
    try:
        await bot.send_message(CHANNEL_ID, message_text)
        print(f"Случайный юзернейм отправлен в группу {CHANNEL_ID} в {datetime.now()}")
        
        # Отправляем юзернейм целевому пользователю
        await send_to_target_user(random_username)
            
        return True
    except Exception as e:
        print(f"Ошибка отправки в группу: {e}")
        
        try:
            await bot.send_message(ADMIN_ID, f"Ошибка отправки в группу: {e}")
        except:
            print("Не удалось отправить сообщение об ошибке админу")
        return False


@bot.message_handler(commands=['start_schedule'])
async def start_schedule(message):
    if message.from_user.id != ADMIN_ID:
        await bot.reply_to(message, "У вас нет прав для этой команды")
        return
    
    scheduler.add_job(
        post_random_username,
        trigger=IntervalTrigger(minutes=20),
        id='username_poster'
    )
    
    try:
        status_msg = await create_status_message()
        await bot.send_message(ADMIN_ID, f"✅ Расписание запущено! Публикация каждые 20 минут с 12:00 до 19:00 по МСК\n\n{status_msg}")
    except Exception as e:
        print(f"Ошибка отправки статуса в личку: {e}")
    
    await bot.reply_to(message, "✅ Расписание запущено! Публикация случайного юзернейма каждые 20 минут с 12:00 до 19:00 по МСК")

@bot.message_handler(commands=['stop_schedule'])
async def stop_schedule(message):
    if message.from_user.id != ADMIN_ID:
        await bot.reply_to(message, "У вас нет прав для этой команды")
        return
    
    try:
        scheduler.remove_job('username_poster')
        
        try:
            status_msg = await create_status_message()
            await bot.send_message(ADMIN_ID, f"⏹ Расписание остановлено\n\n{status_msg}")
        except Exception as e:
            print(f"Ошибка отправки статуса в личку: {e}")
            
        await bot.reply_to(message, "⏹ Расписание остановлено")
    except:
        await bot.reply_to(message, "ℹ️ Расписание не было запущено")

@bot.message_handler(commands=['publish_random'])
async def publish_random(message):
    if message.from_user.id != ADMIN_ID:
        await bot.reply_to(message, "У вас нет прав для этой команды")
        return
    
    if not usernames:
        await bot.reply_to(message, "Список юзернеймов пуст")
        return
    
    random_username = random.choice(list(usernames))
    message_text = f"🎲 Случайный юзернейм: {random_username}"
    
    try:
        await bot.send_message(CHANNEL_ID, message_text)
        
        # Отправляем юзернейм целевому пользователю
        success = await send_to_target_user(random_username)
        
        if success:
            await bot.reply_to(message, f"✅ Случайный юзернейм опубликован и отправлен получателю: {random_username}")
        else:
            await bot.reply_to(message, f"✅ Случайный юзернейм опубликован, но не удалось отправить получателю: {random_username}")
            
    except Exception as e:
        await bot.reply_to(message, f"❌ Ошибка отправки в группу: {e}")

@bot.message_handler(func=lambda message: True)
async def echo_all(message):
    print(f"Получено сообщение: {message.text} от {message.from_user.id} в чате {message.chat.id}")

async def main():
    print("Бот запущен...")
    print(f"ID группы для публикации: {CHANNEL_ID}")
    try:
        scheduler.start()
        await bot.polling(non_stop=True)
    except Exception as e:
        print(f"Ошибка: {e}")
        await asyncio.sleep(5)
        await main()

if __name__ == '__main__':
    asyncio.run(main())