import openpyxl
from openpyxl.styles import Font, Alignment
from datetime import datetime, timedelta

from crud import fetch_requests_in_period


def report_generation(period):
    # Устанавливаем временной интервал для выборки данных
    today = datetime.now()
    if period == "day":
        start_date = today - timedelta(days=1)
    elif period == "week":
        start_date = today - timedelta(weeks=1)
    else:
        raise ValueError("Неверный период для генерации отчета")

    # Запрашиваем данные из базы данных
    data = fetch_requests_in_period(start_date, today)

    # Создание нового Excel-файла и активного листа
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Отчет"

    # Заголовки таблицы
    headers = ["ID обращения", "ID клиента", "Филиал", "Тип содержимого", "Содержимое", "Дата и время"]
    ws.append(headers)

    # Стили заголовков
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    # Заполняем Excel-файл данными из запроса
    for row in data:
        # Извлекаем данные и конвертируем datetime без временной зоны
        row = list(row)
        if isinstance(row[-1], datetime):
            row[-1] = row[-1].replace(tzinfo=None)  # Убираем временную зону
        ws.append(row)

    # Автоматическое изменение ширины столбцов
    for col in ws.columns:
        max_length = max(len(str(cell.value)) for cell in col if cell.value) + 2
        ws.column_dimensions[col[0].column_letter].width = max_length

    # Сохраняем файл и возвращаем путь к нему
    file_path = f"report_{period}_{today.strftime('%Y%m%d')}.xlsx"
    wb.save(file_path)
    return file_path
