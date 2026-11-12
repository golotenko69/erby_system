import secrets
import string

from django.contrib.auth import get_user_model

_ALPHABET = string.ascii_letters + string.digits


def generate_random_string(length=8):
    """Криптостойкая случайная строка из букв и цифр (логины и пароли ответственных лиц)."""
    return ''.join(secrets.choice(_ALPHABET) for _ in range(length))


def generate_unique_username(prefix='user_', length=6):
    """Логин вида user_xxxxxx, гарантированно не занятый другим пользователем."""
    User = get_user_model()
    while True:
        username = f"{prefix}{generate_random_string(length).lower()}"
        if not User.objects.filter(username=username).exists():
            return username


def format_term(months):
    """Срок обучения в месяцах -> «1 г. 10 мес.» / «2 г.» / «10 мес.»."""
    if not months:
        return ''
    years, rest = divmod(months, 12)
    if years and rest:
        return f'{years} г. {rest} мес.'
    return f'{years} г.' if years else f'{rest} мес.'
