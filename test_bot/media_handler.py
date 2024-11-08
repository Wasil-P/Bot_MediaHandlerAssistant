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

from crud import save_client_request, get_client_request, update_client_request, add_request_item, delete_request_items
from db import init_database
from send_email import send_email

load_dotenv()

ADMIN_CHAT_IDS = {
    "Филиал 1": os.getenv("ADMIN_ID_1"),
    "Филиал 2": os.getenv("ADMIN_ID_2"),
    "Филиал 3": os.getenv("ADMIN_ID_3"),
}

ADMIN_EMAIL = {
    "Филиал 1": os.getenv("ADMIN_EMAIL_1"),
    "Филиал 2": os.getenv("ADMIN_EMAIL_2"),
    "Филиал 3": os.getenv("ADMIN_EMAIL_3"),
}

ADMIN_CHAT_ID_MAIN = os.getenv("ADMIN_ID_MAIN") # ID галовного филиала

logging.basicConfig(level=logging.INFO)

# Инициализация хранилища и бота
storage = MemoryStorage()
bot = Bot(token=os.getenv("TOKEN_TG_TEST"))
dp = Dispatcher(storage=storage)  # Передаем storage как именованный аргумент


# Определение состояний
class Form(StatesGroup):
    choosing_action = State()
    choosing_branch = State()
    waiting_for_content = State()
    waiting_for_response = State()


# Шаг 1: Главное меню - команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    markup = InlineKeyboardBuilder()
    markup.add(
        InlineKeyboardButton(text="Направить обращение", callback_data="new_request"),
        InlineKeyboardButton(text="О боте", callback_data="about_bot")
    )
    await message.answer(
        "Добрый день! Чем я могу вам помочь? Выберите один из вариантов:",
        reply_markup=markup.as_markup()
    )


# Шаг 2: Обработка выбора в главном меню
@dp.callback_query(F.data == "new_request")
async def new_request(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()  # Останавливаем анимацию загрузки
    markup = InlineKeyboardBuilder()

    markup.row(
        InlineKeyboardButton(text="Филиал 1", callback_data="branch_Филиал 1"),
        InlineKeyboardButton(text="Филиал 2", callback_data="branch_Филиал 2")
    )
    markup.row(
        InlineKeyboardButton(text="Филиал 3", callback_data="branch_Филиал 3"),
        InlineKeyboardButton(text="Головной офис", callback_data="branch_Головной офис")
    )

    await callback_query.message.answer(
        "Пожалуйста, выберите, куда направить ваше обращение:\n"
        "1 - Филиал 1\n2 - Филиал 2\n3 - Филиал 3\n4 - Головной офис",
        reply_markup=markup.as_markup()
    )
    await state.set_state(Form.choosing_branch)  # указание состояния


@dp.callback_query(F.data == "about_bot")
async def about_bot(callback_query: types.CallbackQuery):
    await callback_query.answer()  # Останавливаем анимацию загрузки
    markup = InlineKeyboardBuilder()
    markup.add(InlineKeyboardButton(text="Направить обращение", callback_data="new_request"))
    await callback_query.message.answer(
        "Я — виртуальный помощник, созданный для направления ваших обращений в наши филиалы или Головной офис. "
        "Чем могу помочь вам сегодня?",
        reply_markup=markup.as_markup()
    )


# Шаг 3: Обработка выбора филиала или головного офиса
@dp.callback_query(F.data.startswith("branch_"))
async def select_branch(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()  # Останавливаем анимацию загрузки
    branch = callback_query.data.split("_")[1]
    logging.info(f"Функция select_branch. Филиал - {branch}")
    # Сохранение запроса клиента с филиалом
    user_id = callback_query.from_user.id
    request_id = save_client_request(user_id, branch=branch)

    # Сохраняем request_id и филиал в состоянии
    await state.update_data(selected_branch=branch, request_id=request_id)

    if branch == "Головной офис":
        await callback_query.message.answer(
            "Ваше обращение будет направлено в Головной офис. Вы можете отправить видео, фото или текст."
        )
    else:
        await callback_query.message.answer(
            "Ваше обращение будет направлено в выбранный филиал и дублировано в Головной офис. "
            "Вы можете отправить видео, фото или текст."
        )
    await state.set_state(Form.waiting_for_content)  # указание состояния


# Шаг 4: Получение содержимого обращения
@dp.message(lambda message: F.content_type.in_(
    [types.ContentType.TEXT, types.ContentType.PHOTO, types.ContentType.VIDEO])
                            and str(message.chat.id) != ADMIN_CHAT_ID_MAIN
                            and str(message.chat.id) not in ADMIN_CHAT_IDS.values())
async def get_content(message: types.Message, state: FSMContext):
    data = await state.get_data()
    branch = data.get("selected_branch")
    request_id = data.get("request_id")  # Получаем request_id
    logging.info(f"Функция get_content. Request ID: {request_id}")
    # Получение контента и типа содержимого
    # Получение контента и типа содержимого
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

    if content and content_type:
        add_request_item(request_id, content_type, content)  # Сохраняем контент как элемент запроса
        logging.info(f"Добавлен контент {content_type} к запросу {request_id}")

        # Получение всего контента, связанного с request_id
    request_data = get_client_request(request_id)
    content_items = "\n".join(
        f"{item['content_type']}: {item['content']}" for item in request_data.get("items", [])
    )

    # Подтверждение отправки
    markup = InlineKeyboardBuilder()
    markup.add(
        InlineKeyboardButton(text="Отправить", callback_data=f"confirm_send_{request_id}"),
        InlineKeyboardButton(text="Редактировать", callback_data=f"edit_message_{request_id}"),
        InlineKeyboardButton(text="Добавить", callback_data=f"add_content_{request_id}")
    )
    await message.answer(
        f"Просмотрите сообщение:\nОтправка: {content_items}\nФилиал: {branch}\nГотовы отправить или хотите отредактировать?",
        reply_markup=markup.as_markup()
    )
    logging.info(f"Состояния выбора меню")

# Шаг 5: Подтверждение отправки
@dp.callback_query(F.data.startswith("confirm_send_"))
async def confirm_send(callback_query: types.CallbackQuery):
    await callback_query.answer()  # Останавливаем анимацию загрузки
    request_id = callback_query.data.split("_")[2]
    logging.info(f"Функция confirm_send, request_id - {request_id}")
    request_data = get_client_request(request_id)
    user_id = request_data.get("user_id")
    branch = request_data.get("branch")
    branch_admin_id = ADMIN_CHAT_IDS.get(branch)
    branch_admin_email = ADMIN_EMAIL.get(branch)
    content_items = "\n".join(
        f"{item['content_type']}: {item['content']}" for item in request_data.get("items", [])
    )

    # Сообщение пользователю
    await callback_query.message.answer("Спасибо за ваше обращение! Мы свяжемся с вами в ближайшее время.")

    # Создание клавиатуры с кнопками
    markup = InlineKeyboardBuilder()
    callback_data_reply = f"reply-to-client_{user_id}_{request_id}"  # Создаем callback_data для кнопки "Ответить"

    markup.add(InlineKeyboardButton(text="Ответить", callback_data=callback_data_reply))

    # Текст для email
    send_subject = f"Новое обращение от клиента {user_id}"
    send_body_admin = f"Новое обращение от клиента {user_id}:\n {content_items}"
    send_body_head_office_duplicate = (f"Новое обращение в {branch}\nот клиента - {user_id}."
                                       f"\nСообщение: {content_items}")
    send_body_head_office = (f"Новое обращение {request_id}\nв головной офис\nот клиента - {user_id}."
                             f"\nСообщение: {content_items}")

    # # Отправка обращения администраторам филиала и головного офиса
    if branch_admin_id and branch_admin_email:
        logging.info(f"Функция confirm_send, id Филиала- {branch_admin_id}")
        await bot.send_message(branch_admin_id, send_body_admin,
                                                reply_markup=markup.as_markup()  # Добавляем клавиатуру к сообщению
                                                )
        await bot.send_message(ADMIN_CHAT_ID_MAIN, send_body_head_office_duplicate)
        # Отправка email
        send_email(send_subject, send_body_admin, branch_admin_email)
        send_email(send_subject, send_body_head_office_duplicate, os.getenv("HEAD_OFFICE_EMAIL"))

    else:
        logging.info(f"Функция confirm_send, id Головного филиала- {ADMIN_CHAT_ID_MAIN}")
        await bot.send_message(ADMIN_CHAT_ID_MAIN, send_body_head_office,
                                                    reply_markup=markup.as_markup())
        # Отправка email
        send_email(send_subject, send_body_head_office, os.getenv("HEAD_OFFICE_EMAIL"))



# Шаг 6: Редактирование сообщения
@dp.callback_query(F.data.startswith("edit_message_"))
async def edit_message(callback_query: types.CallbackQuery, state: FSMContext):
    request_id = callback_query.data.split("_")[2]
    await callback_query.answer()  # Останавливаем анимацию загрузки
    delete_request_items(request_id)  # функция для удаления записей из таблицы request_items
    await callback_query.message.answer("Введите новое сообщение для отправки.")
    await state.set_state(Form.waiting_for_content)  # указание состояния


# Шаг 7: Обработка добавления нового контента к запросу
@dp.callback_query(F.data.startswith("add_content_"))
async def add_more_content(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()  # Останавливаем анимацию загрузки
    request_id = callback_query.data.split("_")[2]

    # Сообщаем пользователю, что он может добавить еще одно сообщение, фото или видео
    await callback_query.message.answer(
        "Пожалуйста, отправьте дополнительный текст, фото или видео, которые вы хотите добавить к обращению."
    )

    # Сохраняем текущий request_id, чтобы знать, к какому запросу добавлять элементы
    await state.update_data(request_id=request_id)
    await state.set_state(Form.waiting_for_content)  # Возвращаемся к ожиданию контента


# Шаг 8: Ответ администратора клиенту
@dp.callback_query(F.data.startswith("reply-to-client_"))
async def reply_to_client(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()  # Останавливаем анимацию загрузки
    data = callback_query.data.split("_")
    user_id = data[1]  # ID обращения
    request_id = data[2]  # ID клиента
    logging.info(f"Функция!! reply_to_client: client_id - {user_id} request_id - {request_id}")

    # Запрашиваем новое сообщение у администратора
    await callback_query.message.answer("Введите ваше сообщение для клиента:")

    # Сохраняем идентификаторы, чтобы знать, к какому обращению относится новое сообщение
    await state.update_data(request_id=request_id, client_id=user_id)


# Шаг 9: Обработка ввода ответа администратора
@dp.message(lambda message: str(message.chat.id) in ADMIN_CHAT_IDS.values()
            or str(message.chat.id) == ADMIN_CHAT_ID_MAIN)
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

# Шаг 10: Подтверждение отправки сообщения клиенту
@dp.callback_query(F.data.startswith("send-to-client_"))
async def send_to_client(callback_query: types.CallbackQuery):
    await callback_query.answer()  # Останавливаем анимацию загрузки
    data = callback_query.data.split("_")
    client_id = data[1]  # ID клиента
    request_id = data[2]  # ID обращения
    logging.info(f"send_to_client_: client_id - {client_id} request_id - {request_id}")

    # Получаем данные обращения
    request_data = get_client_request(request_id)
    if not request_data:
        await callback_query.message.answer("Запрос не найден.")
        return

    branch = request_data.get("branch")
    admin_message = request_data.get("admin_response")
    send_subject = f"Новое обращение от клиента {client_id}"
    send_body_head_office_duplicate = (f"Ответ от администратора {branch}\nотправлен клиенту ID: {client_id}."
                                       f"\nID обращения: {request_id}"
                                        f"\nСообщение администратора: {admin_message}")
    if admin_message:
        # Отправляем ответ клиенту
        await bot.send_message(client_id, f"Ответ от администратора: {admin_message}")
        await callback_query.answer("Ответ отправлен клиенту.")
        await callback_query.message.answer("Ваш ответ отправлен клиенту.")

        # Дублирование в головной филиал
        await bot.send_message(ADMIN_CHAT_ID_MAIN, send_body_head_office_duplicate)
        send_email(send_subject, send_body_head_office_duplicate, os.getenv("HEAD_OFFICE_EMAIL"))

    else:
        logging.error("Ответ администратора не найден в запросе.")


# Шаг 11: Обработка редактирования ответа
@dp.callback_query(F.data.startswith("edit-response_"))
async def edit_response(callback_query: types.CallbackQuery):
    await callback_query.answer()  # Останавливаем анимацию загрузки
    client_id = callback_query.data.split("_")[1]

    # Информируем администратора о редактировании
    await callback_query.message.answer("Редактируйте сообщение и отправьте снова.")


# Основной запуск бота
if __name__ == "__main__":
    # Инициализация базы данных
    init_database()

    # Запуск бота
    dp.run_polling(bot)
