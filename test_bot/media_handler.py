import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton
from dotenv import load_dotenv
from aiogram.utils.keyboard import InlineKeyboardBuilder
from crud import save_client_request, get_client_request, update_client_request

load_dotenv()
ADMIN_CHAT_ID = os.getenv("ADMIN_ID")  # ID администратора
logging.basicConfig(level=logging.INFO)

# Инициализация хранилища и бота
storage = MemoryStorage()
bot = Bot(token=os.getenv("TOKEN_TG_TEST"))
dp = Dispatcher(storage=storage)  # Передаем storage как именованный аргумент


# Определение состояний
class Form(StatesGroup):
    waiting_for_response = State()


# Шаг 1:  Обработка команды /start
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Добро пожаловать! Отправьте ваше сообщение, фото или видео.")


# Шаг 2:  Обработка получения текста, фото или видео от клиента
@dp.message(
    lambda message: F.content_type.in_(
        [types.ContentType.TEXT, types.ContentType.PHOTO, types.ContentType.VIDEO])
        and str(message.chat.id) != ADMIN_CHAT_ID)
async def get_content(message: types.Message):
    user_id = message.from_user.id
    content = None
    content_type = None

    if message.text:
        content = message.text
        content_type = "text"
    elif message.photo:
        content = message.photo[-1].file_id
        content_type = "photo"
    elif message.video:
        content = message.video.file_id
        content_type = "video"

    # Сохранение обращения клиента и получение request_id
    request_id = save_client_request(user_id, content_type, content)

    # Выбор филиала
    branches = ["Филиал 1", "Филиал 2", "Филиал 3"]
    markup = InlineKeyboardBuilder()
    for branch in branches:
        markup.add(types.InlineKeyboardButton(
            text=branch, callback_data=f"branch_{branch}_{request_id}"))
    await message.answer("Выберите филиал:", reply_markup=markup.as_markup())


# Шаг 3: Выбор филиала
@dp.callback_query(F.data.startswith("branch_"))
async def select_branch(callback_query: types.CallbackQuery):
    data = callback_query.data.split("_")
    branch = data[1]
    request_id = data[2]  # Извлекаем ID обращения из callback_data

    user_id = callback_query.from_user.id
    update_client_request(request_id, branch=branch)  # Обновляем филиал в обращении

    # Получаем данные обращения
    request_data = get_client_request(request_id)
    content = request_data.get("content") or request_data.get("photo_id") or request_data.get("video_id")

    # Подтверждение или редактирование
    markup = InlineKeyboardBuilder()
    markup.add(types.InlineKeyboardButton(
        text="Отправить администратору", callback_data=f"confirm_send_{request_id}"))
    markup.add(types.InlineKeyboardButton(
        text="Редактировать", callback_data=f"edit_message_{request_id}"))

    await callback_query.message.answer(
        f"Просмотрите сообщение:\n "
        f"Отправка: {content}\n "
        f"Филиал: {branch}\n "
        f"Готовы отправить или хотите отредактировать?",
        reply_markup=markup.as_markup()
    )


# Шаг 4: Подтверждение отправки
@dp.callback_query(F.data.startswith("confirm_send_"))
async def confirm_send(callback_query: types.CallbackQuery):
    request_id = callback_query.data.split("_")[2]
    user_id = callback_query.from_user.id

    # Получаем данные обращения
    request_data = get_client_request(request_id)
    content = request_data.get("content") or request_data.get("photo_id") or request_data.get("video_id")
    branch = request_data.get("branch")

    await callback_query.message.answer("Ваше сообщение отправлено администратору. Ожидайте")

    # Создание клавиатуры с кнопками
    markup = InlineKeyboardBuilder()
    logging.info(f"confirm_send: client_id - {user_id} request_id - {request_id}")
    callback_data_reply = f"reply-to-client_{user_id}_{request_id}"  # Создаем callback_data для кнопки "Ответить"

    markup.add(InlineKeyboardButton(text="Ответить", callback_data=callback_data_reply))

    # Отправка сообщения администратору
    await bot.send_message(
        ADMIN_CHAT_ID,
        f"Новое сообщение от клиента.\nФилиал: {branch}\n"
        f"Контент: {content}\n\nПожалуйста, ответьте на это сообщение."
        f"\nID клиента: {user_id}\nID обращения: {request_id}",
        reply_markup=markup.as_markup()  # Добавляем клавиатуру к сообщению
    )

    logging.info(f"Администратору выслано сообщение от клиента (ID обращения: {request_id}).")


# Шаг 5: Обработка редактирования сообщения
@dp.callback_query(F.data.startswith("edit_message_"))
async def edit_message(callback_query: types.CallbackQuery):
    request_id = callback_query.data.split("_")[2]
    user_id = callback_query.from_user.id

    # Запрашиваем новое сообщение у пользователя
    await callback_query.message.answer("Введите новое сообщение:")

    # Сохраняем идентификатор запроса, чтобы знать, к какому обращению относится новое сообщение
    await dp.current_state(user=callback_query.from_user.id).update_data(request_id=request_id)
    logging.info(f"Администратору выслано сообщение после редактирования")


# Шаг 6: Ответ администратора клиенту
@dp.callback_query(F.data.startswith("reply-to-client_"))
async def reply_to_client(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data.split("_")
    user_id = data[1]  # ID обращения
    request_id = data[2]  # ID клиента
    logging.info(f"reply_to_client: client_id - {user_id} request_id - {request_id}")

    # Запрашиваем новое сообщение у администратора
    await callback_query.message.answer("Введите ваше сообщение для клиента:")

    # Сохраняем идентификаторы, чтобы знать, к какому обращению относится новое сообщение
    await state.update_data(request_id=request_id, client_id=user_id)


# Шаг 7: Обработка ввода ответа администратора
@dp.message(lambda message: str(message.chat.id) == ADMIN_CHAT_ID)
async def admin_response(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    request_id = user_data.get("request_id")
    client_id = user_data.get("client_id")
    logging.info(f"admin_response: client_id - {client_id} request_id - {request_id}")
    if request_id and client_id:
        # Сохраняем ответ администратора
        admin_message = message.text
        update_client_request(request_id, admin_response=admin_message)
        # Предпросмотр сообщения
        markup = InlineKeyboardBuilder()
        markup.add(
            InlineKeyboardButton(text="Отправить",
                                 callback_data=f"send-to-client_{client_id}_{request_id}"),
            InlineKeyboardButton(text="Редактировать",
                                 callback_data=f"edit-response_{client_id}_{request_id}"))

        await message.answer(
            f"Предпросмотр сообщения:\n{admin_message}",
            reply_markup=markup.as_markup()
        )
    else:
        await message.answer("Не удалось определить ID обращения или клиента.")

# Шаг 8: Подтверждение отправки сообщения клиенту
@dp.callback_query(F.data.startswith("send-to-client_"))
async def send_to_client(callback_query: types.CallbackQuery):
    data = callback_query.data.split("_")
    client_id = data[1]  # ID клиента
    request_id = data[2]  # ID обращения
    logging.info(f"send_to_client_: client_id - {client_id} request_id - {request_id}")

    # Получаем данные обращения
    request_data = get_client_request(request_id)
    if not request_data:
        await callback_query.message.answer("Запрос не найден.")
        return

    admin_message = request_data.get("admin_response")
    if admin_message:
        # Отправляем ответ клиенту
        await bot.send_message(client_id, f"Ответ от администратора: {admin_message}")
        await callback_query.answer("Ответ отправлен клиенту.")
        await callback_query.message.answer("Ваш ответ отправлен клиенту.")
    else:
        logging.error("Ответ администратора не найден в запросе.")


# Шаг 9: Обработка редактирования ответа
@dp.callback_query(F.data.startswith("edit-response_"))
async def edit_response(callback_query: types.CallbackQuery):
    client_id = callback_query.data.split("_")[1]

    # Информируем администратора о редактировании
    await callback_query.message.answer("Редактируйте сообщение и отправьте снова.")


# Основной запуск бота
if __name__ == "__main__":
    dp.run_polling(bot)
