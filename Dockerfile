FROM python:3.12-slim
LABEL authors="Андрей"

ENV PYTHONUNBUFFERED=1

# Устанавливаем системные зависимости и драйвер Microsoft ODBC для MSSQL (современный метод)
RUN apt-get update && apt-get install -y gnupg2 curl apt-transport-https unixodbc-dev g++ \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем и устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта в контейнер
COPY . .
RUN python manage.py collectstatic --noinpu

# Открываем порт 8000 (на нем будет слушать Gunicorn)
EXPOSE 8000

CMD ["gunicorn", "django_erbu.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]