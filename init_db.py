import os
import django

# Настраиваем окружение Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_erbu.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Настройки для учетной записи администратора
username = 'admin'
email = 'admin@example.com'
password = 'admin123'  # Обязательно замените на свой надёжный пароль

if not User.objects.filter(username=username).exists():
    print(f"Создаю суперпользователя {username} с ролью ADMIN...")

    # Создаем объект суперпользователя, сразу передавая кастомное поле role
    User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        role='ADMIN'  # Устанавливаем роль ADMIN напрямую
    )

    print("Суперпользователь успешно создан и роль ADMIN присвоена!")
else:
    # На случай пересборки контейнера: если админ есть, но роль слетела, принудительно обновляем её
    user = User.objects.get(username=username)
    if getattr(user, 'role', None) != 'ADMIN':
        user.role = 'ADMIN'
        user.save()
        print(f"Пользователь {username} уже существовал, роль принудительно обновлена до ADMIN.")
    else:
        print(f"Пользователь {username} уже существует и имеет роль ADMIN.")