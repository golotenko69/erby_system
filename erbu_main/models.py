

# Create your models here.
from django.db import models




class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    first_name = models.CharField("Имя", max_length=100)
    middle_name = models.CharField("Отчество", max_length=100, blank=True, null=True)
    last_name = models.CharField("Фамилия", max_length=100, blank=True, null=True)

    STATUS_CHOICES = [
        ('родительский', 'Родительский'),
        ('сирота', 'Сирота'),
        ('оставшийся без попечения родителей', 'Оставшийся без попечения родителей'),
    ]
    status = models.CharField("Статус", max_length=100, choices=STATUS_CHOICES)

    sex = models.CharField("Пол", max_length=3, choices=[('жен', 'Жен'), ('муж', 'Муж')])
    email = models.EmailField("Email", max_length=100, blank=True, null=True)
    phone = models.CharField("Телефон", max_length=100, blank=True, null=True)
    birthday = models.DateField("Дата рождения")
    snils = models.CharField("СНИЛС", max_length=11, blank=True, null=True)
    inn = models.CharField("ИНН", max_length=12, blank=True, null=True)


    class Meta:
        verbose_name = "Студент"
        verbose_name_plural = "Студенты"

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


class Passport(models.Model):
    # OneToOne: У одного студента ровно один действующий паспорт в системе
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='passport'
    )
    series = models.CharField("Серия", max_length=4, blank=True, null=True)
    number = models.CharField("Номер", max_length=6, blank=True, null=True)
    issued = models.CharField("Кем выдан", max_length=100, blank=True, null=True)
    date_issued = models.DateField("Дата выдачи", blank=True, null=True)
    department_code = models.CharField("Код подразделения", max_length=10, blank=True, null=True)
    place_birth = models.CharField("Место рождения", max_length=100, blank=True, null=True)
    place_resident = models.CharField("Место жительства", max_length=100, blank=True, null=True)


class EducationEnded(models.Model):
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name='education_ended'
    )

    education_type = models.CharField(
        "Тип образования",
        max_length=49,
        choices=[
            ('общее', 'Общее'),
            ('среднее', 'Среднее')
        ]
    )

    name = models.CharField(
        "Название учреждения",
        max_length=100,
        blank=True,
        null=True
    )

    education_document = models.CharField(
        "Документ",
        max_length=100,
        choices=[
            ('свидетельство', 'Свидетельство'),
            ('аттестат', 'Аттестат')
        ]
    )

    series = models.CharField(
        "Серия/Номер",
        max_length=20,
        blank=True,
        null=True
    )

    date_issued = models.DateField(
        "Дата выдачи",
        blank=True,
        null=True
    )
class EducationInstitution(models.Model):
    name = models.CharField("Название", max_length=255)
    last_seen = models.DateTimeField("Последний раз в сети", blank=True, null=True)

    def __str__(self):
        return self.name

class EducationProcess(models.Model):
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name='education_process'
    )
    created_at = models.DateTimeField("Дата добавления в учреждение", auto_now_add=True)


    education_institution = models.ForeignKey(
        EducationInstitution,
        on_delete=models.CASCADE,
        related_name='students'
    )

    profession = models.CharField(
        "Профессия",
        max_length=100,
        blank=True,
        null=True
    )

    course = models.IntegerField(
        "Курс",
        choices=[(i, str(i)) for i in range(1, 5)]
    )

    form = models.CharField(
        "Форма обучения",
        max_length=20,
        choices=[
            ('очная', 'Очная'),
            ('заочная', 'Заочная'),
            ('очно/заочная', 'Очно/заочная')
        ]
    )

    term = models.IntegerField(
        "Срок обучения (мес)",
        blank=True,
        null=True
    )

    grad_date = models.DateField(
        "Год выпуска",
        blank=True,
        null=True
    )
class Parent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='parents')
    first_name = models.CharField("Имя", max_length=100, blank=True, null=True)
    middle_name = models.CharField("Отчество", max_length=100, blank=True, null=True)
    last_name = models.CharField("Фамилия", max_length=100, blank=True, null=True)
    phone = models.CharField("Телефон", max_length=20, blank=True, null=True)
    email = models.EmailField("Email", max_length=100, blank=True, null=True)


class DisabilityInfo(models.Model):
    DISABILITY_GROUP_CHOICES = [
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('ребенок-инвалид', 'Ребенок-инвалид'),
    ]

    NOSOLOGY_CHOICES = [
        ('интеллектуальные_опр_зпр_уо', 'Интеллектуальные нарушения (ОПР, ЗПР, УО)'),
        ('интеллектуальные_рас', 'Интеллектуальные нарушения (расстройство аутистического спектра)'),
        ('ода_мобильные', 'Нарушения ОДА (мобильные)'),
        ('ода_коляска', 'Нарушения ОДА (на кресле-коляске)'),
        ('зрение', 'Нарушение зрения'),
        ('слух', 'Нарушение слуха'),
        ('соматические', 'Соматические заболевания'),
        ('речь', 'Нарушение речи'),
    ]

    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True, related_name='disability_info')
    status_ovz = models.CharField("Статус ОВЗ", max_length=3, choices=[('Да', 'Да'), ('Нет', 'Нет')])

    # Изменено: добавлен выпадающий список choices
    disability_group = models.CharField(
        "Группа инвалидности",
        max_length=50,
        choices=DISABILITY_GROUP_CHOICES,
        blank=True,
        null=True
    )
    # Изменено: добавлен выпадающий список choices
    nosology_type = models.CharField(
        "Нозология",
        max_length=150,
        choices=NOSOLOGY_CHOICES,
        blank=True,
        null=True
    )
    year_removal = models.DateField("Дата снятия", blank=True, null=True)

class Mse(models.Model):
    disability = models.OneToOneField(
        DisabilityInfo,
        on_delete=models.CASCADE,
        related_name='mse'
    )
    series = models.CharField("Серия МСЭ", max_length=20, blank=True, null=True)
    number = models.CharField("Номер МСЭ", max_length=20, blank=True, null=True)
    date_issued = models.DateField("Дата выдачи", blank=True, null=True)
    date_next_examination = models.DateField("Дата переосвидетельствования", blank=True, null=True)

class Pmpk(models.Model):
    disability = models.OneToOneField(
        DisabilityInfo,
        on_delete=models.CASCADE,
        related_name='pmpk'
    )
    number = models.CharField("Номер заключения", max_length=50, blank=True, null=True)
    date_issued = models.DateField("Дата выдачи", blank=True, null=True)
    education_programm_pmpk = models.CharField("Рекомендованная программа", max_length=100, blank=True, null=True)


class EducationTarget(models.Model):
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name='education_target'
    )

    agreement = models.CharField(
        "Целевой договор",
        max_length=3,
        choices=[('Да', 'Да'), ('Нет', 'Нет')]
    )

    name_organization = models.CharField(
        "Организация",
        max_length=100,
        blank=True,
        null=True
    )

    abilimpiks = models.CharField(
        "Участие в Абилимпикс",
        max_length=3,
        choices=[('Да', 'Да'), ('Нет', 'Нет')]
    )


class Employment(models.Model):
    REASON_NOT_EMPLOYED_CHOICES = [
        ('служба_в_вс', 'Служба в вооруженных силах'),
        ('декрет_уход', 'Декретный отпуск или отпуск по уходу за ребенком'),
        ('обучение', 'Продолжил обучение'),
        ('здоровье', 'По состоянию здоровья'),
        ('иные', 'Иные причины'),
    ]

    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name='employment'
    )
    employment_status = models.CharField(
        "Трудоустроен",
        max_length=3,
        choices=[('Да', 'Да'), ('Нет', 'Нет')]
    )
    place_job = models.CharField("Место работы", max_length=150, blank=True, null=True)
    position = models.CharField("Должность", max_length=100, blank=True, null=True)
    hiring_date = models.DateField("Дата приема", blank=True, null=True)

    # Изменено: добавлен выпадающий список choices
    reason_not_employment = models.CharField(
        "Причина нетрудоустройства",
        max_length=200,
        choices=REASON_NOT_EMPLOYED_CHOICES,
        blank=True,
        null=True
    )

    accounting_employment = models.CharField("Состоит в ЦЗН", max_length=3, choices=[('Да', 'Да'), ('Нет', 'Нет')])
    resume_status = models.CharField("Резюме создано", max_length=3, choices=[('Да', 'Да'), ('Нет', 'Нет')])

class ResponsiblePerson(models.Model):
    first_name = models.CharField("Имя", max_length=100)
    middle_name = models.CharField("Отчество", max_length=100, blank=True, null=True)
    last_name = models.CharField("Фамилия", max_length=100, blank=True, null=True)
    position = models.CharField("Должность", max_length=100, blank=True, null=True)
    email = models.EmailField("Email", max_length=100, blank=True, null=True)
    phone = models.CharField("Телефон", max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = "Ответственное лицо"
        verbose_name_plural = "Ответственные лица"

    def __str__(self):
        return f"{self.last_name} ({self.position})"


class StudentLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Добавление'),
        ('UPDATE', 'Редактирование'),
        ('DELETE', 'Удаление'),
    ]

    action = models.CharField("Действие", max_length=10, choices=ACTION_CHOICES)
    student_name = models.CharField("ФИО Студента", max_length=300)
    user = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, verbose_name="Кто изменил")
    institution_name = models.CharField("Учреждение", max_length=255, blank=True, null=True)
    changes = models.TextField("Подробности изменений", blank=True, null=True)
    created_at = models.DateTimeField("Дата и время", auto_now_add=True)
    is_read = models.BooleanField("Прочитано", default=False)

    class Meta:
        verbose_name = "Лог изменений студента"
        verbose_name_plural = "Логи изменений студентов"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} - {self.student_name}"