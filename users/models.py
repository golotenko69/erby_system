from django.db import models
from django.contrib.auth.models import AbstractUser

from erbu_main.models import EducationInstitution


# Create your models here.

class CustomUser(AbstractUser):

    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Студент'
        TEACHER = 'TEACHER', 'Преподаватель'
        ADMIN = 'ADMIN', 'Администратор'

    role = models.CharField(max_length=50, choices=Role.choices)

    education_institution = models.ForeignKey(
        'erbu_main.EducationInstitution',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Учебное заведение"
    )
