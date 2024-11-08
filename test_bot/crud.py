import random
import logging
from psycopg2 import sql


from db import get_database_connection

# Функция для генерации уникального пятизначного request_id
def generate_unique_request_id():
    conn = get_database_connection()
    cursor = conn.cursor()
    unique_id = None

    # Генерация уникального числа
    while True:
        potential_id = random.randint(100000, 999999)  # Генерация случайного числа
        cursor.execute("SELECT 1 FROM requests WHERE request_id = %s", (potential_id,))
        if not cursor.fetchone():  # Если не найдено совпадений, число уникально
            unique_id = potential_id
            break

    cursor.close()
    conn.close()
    return unique_id

# Функция для сохранения обращения клиента
def save_client_request(user_id, branch=None):
    conn = get_database_connection()
    cursor = conn.cursor()
    request_id = generate_unique_request_id()  # Генерируем уникальный request_id

    try:
        # Вставка данных в таблицу requests
        cursor.execute(
            "INSERT INTO requests (request_id, user_id, branch) VALUES (%s, %s, %s)",
            (request_id, user_id, branch)
        )
        conn.commit()
        logging.info(f"Запрос успешно сохранен с request_id: {request_id}")
    except Exception as e:
        logging.error(f"Ошибка при сохранении обращения клиента: {e}")
        conn.rollback()
        request_id = None
    finally:
        cursor.close()
        conn.close()

    return request_id

# Функция для добавления элементов (текста, фото, видео) к запросу
def add_request_item(request_id, content_type, content):
    conn = get_database_connection()
    cursor = conn.cursor()

    # Проверка, что content_type соответствует одному из допустимых значений
    if content_type not in ['text', 'photo', 'video', 'voice']:
        logging.error(f"Некорректный тип контента: {content_type}")
        return

    try:
        # Вставка элемента в таблицу request_items
        cursor.execute(
            "INSERT INTO request_items (request_id, content_type, content) VALUES (%s, %s, %s)",
            (request_id, content_type, content)
        )
        conn.commit()
        logging.info(f"Элемент '{content_type}' успешно добавлен к запросу с ID {request_id}")
    except Exception as e:
        logging.error(f"Ошибка при добавлении элемента к запросу с ID {request_id}: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

# Функция для получения данных обращения по request_id
def get_client_request(request_id):
    conn = get_database_connection()
    cursor = conn.cursor()

    try:
        # Получение информации о запросе
        cursor.execute("SELECT * FROM requests WHERE request_id = %s", (request_id,))
        request = cursor.fetchone()

        # Получение всех элементов запроса
        cursor.execute("SELECT content_type, content FROM request_items WHERE request_id = %s", (request_id,))
        items = cursor.fetchall()

        if request:
            return {
                "request_id": request[0],
                "user_id": request[1],
                "branch": request[2],
                "timestamp": request[3],
                "admin_response": request[4],
                "items": [{"content_type": item[0], "content": item[1]} for item in items]
            }
        else:
            return None
    except Exception as e:
        logging.error(f"Ошибка при получении данных запроса с ID {request_id}: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

# Функция для обновления обращения клиента
def update_client_request(request_id, **fields):
    conn = get_database_connection()
    cursor = conn.cursor()

    try:
        # Проверяем, существует ли запрос с указанным request_id
        cursor.execute("SELECT COUNT(1) FROM requests WHERE request_id = %s", (request_id,))
        exists = cursor.fetchone()[0]

        if not exists:
            logging.error(f"Запрос с ID {request_id} не найден в базе данных.")
            return False

        # Обновление основного запроса
        set_clause = ', '.join(f"{field} = %s" for field in fields.keys())
        values = list(fields.values()) + [request_id]

        cursor.execute(
            sql.SQL("UPDATE requests SET " + set_clause + " WHERE request_id = %s"),
            values
        )
        conn.commit()
        logging.info(f"Запрос с ID {request_id} успешно обновлен: {fields}")
    except Exception as e:
        logging.error(f"Ошибка при обновлении запроса с ID {request_id}: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

    return True

def delete_request_items(request_id):
    conn = get_database_connection()
    cursor = conn.cursor()
    # Здесь выполняется SQL-запрос на удаление записей из таблицы request_items
    cursor.execute('''
        DELETE FROM request_items
        WHERE request_id = %s;
    ''', (request_id,))
    conn.commit()