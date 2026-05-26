from django.db import models
from django.contrib.auth.models import AbstractUser

from erbu_main.models import EducationInstitution


# Create your models here.

class CustomUser(AbstractUser):

    class Role(models.TextChoices):
        TEACHER = 'TEACHER', 'Ответственное лицо'
        ADMIN = 'ADMIN', 'Администратор'

    role = models.CharField(max_length=50, choices=Role.choices)

    education_institution = models.ForeignKey(
        'erbu_main.EducationInstitution',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Учебное заведение"
    )

    # Новые поля для данных ответственного лица
    middle_name = models.CharField('Отчество', max_length=150, blank=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)
    # Поле для отображения сгенерированного пароля администратору

    raw_password = models.CharField('Сгенерированный пароль', max_length=128, blank=True)
