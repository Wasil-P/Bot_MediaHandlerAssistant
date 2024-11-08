import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Функция для отправки email
def send_email(subject, body, to_email):
    from_email = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    # Настройка MIME
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Отправка письма через SMTP
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(from_email, email_password)
            server.sendmail(from_email, to_email, msg.as_string())
        logging.info("Письмо успешно отправлено!")
    except Exception as e:
        logging.info(f"Ошибка при отправке письма: {e}")