FROM python:3.12-slim
LABEL authors="Андрей"

ENV PYTHONUNBUFFERED=1

# Устанавливаем минимальные системные зависимости для сборки некоторых Python-пакетов (если применимо)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем и устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта в контейнер (в одну строку, без разрывов)
COPY . .

# Открываем порт 8000
EXPOSE 8000

CMD ["gunicorn", "django_erbu.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]