#!/sh
# Собираем статику (теперь это сработает, так как контейнер запущен и видит SECRET_KEY)
python manage.py collectstatic --noinput

# Применяем миграции для SQLite
python manage.py migrate --noinput

# Создаем суперпользователя с ролью ADMIN
python init_db.py

# Запускаем сервер
exec gunicorn django_erbu.wsgi:application --bind 0.0.0.0:8000 --workers 3