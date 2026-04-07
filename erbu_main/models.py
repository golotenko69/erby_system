from django.db import models

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

    # Связь с ответственными лицами (один куратор на многих студентов и наоборот)
    responsible_persons = models.ManyToManyField(
        'ResponsiblePerson',
        related_name='students',
        verbose_name="Ответственные лица"
    )

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
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='education_history')
    education_type = models.CharField("Тип образования", max_length=49,
                                      choices=[('общее', 'Общее'), ('среднее', 'Среднее')])
    name = models.CharField("Название учреждения", max_length=100, blank=True, null=True)
    education_document = models.CharField("Документ", max_length=100,
                                          choices=[('свидетельство', 'Свидетельство'), ('аттестат', 'Аттестат')])
    series = models.CharField("Серия/Номер", max_length=20, blank=True, null=True)
    date_issued = models.DateField("Дата выдачи", blank=True, null=True)


class EducationProcess(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='current_education')
    education_institution = models.CharField("ВУЗ/Колледж", max_length=100, blank=True, null=True)
    profession = models.CharField("Профессия", max_length=100, blank=True, null=True)
    course = models.IntegerField("Курс", choices=[(i, str(i)) for i in range(1, 5)])
    form = models.CharField("Форма обучения", max_length=20,
                            choices=[('очная', 'Очная'), ('заочная', 'Заочная'), ('очно/заочная', 'Очно/заочная')])
    term = models.IntegerField("Срок обучения (мес)", blank=True, null=True)
    grad_date = models.DateField("Дата выпуска", blank=True, null=True)


class Parent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='parents')
    first_name = models.CharField("Имя", max_length=100, blank=True, null=True)
    middle_name = models.CharField("Отчество", max_length=100, blank=True, null=True)
    last_name = models.CharField("Фамилия", max_length=100, blank=True, null=True)
    phone = models.CharField("Телефон", max_length=20, blank=True, null=True)
    email = models.EmailField("Email", max_length=100, blank=True, null=True)


class Mse(models.Model):
    series = models.CharField("Серия МСЭ", max_length=20, blank=True, null=True)
    number = models.CharField("Номер МСЭ", max_length=20, blank=True, null=True)
    date_issued = models.DateField("Дата выдачи", blank=True, null=True)
    date_next_examination = models.DateField("Дата переосвидетельствования", blank=True, null=True)


class Pmpk(models.Model):
    number = models.CharField("Номер заключения", max_length=50, blank=True, null=True)
    date_issued = models.DateField("Дата выдачи", blank=True, null=True)
    education_programm_pmpk = models.CharField("Рекомендованная программа", max_length=100, blank=True, null=True)


class DisabilityInfo(models.Model):
    # OneToOne: Актуальная информация об инвалидности
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True, related_name='disability_info')
    status_ovz = models.CharField("Статус ОВЗ", max_length=3, choices=[('Да', 'Да'), ('Нет', 'Нет')])
    pmpk = models.ForeignKey(Pmpk, on_delete=models.SET_NULL, null=True, blank=True)
    mse = models.ForeignKey(Mse, on_delete=models.SET_NULL, null=True, blank=True)
    disability_group = models.CharField("Группа инвалидности", max_length=50, blank=True, null=True)

    NOSOLOGY_CHOICES = [
        ('аутизм', 'Аутизм'), ('ментальные нарушения (ЗПР)', 'ЗПР'),
        ('нарушения опорно-двигательного аппарата (мобильные)', 'НОДА (мобильные)'),
        ('потеря зрения', 'Потеря зрения'), ('потеря слуха', 'Потеря слуха'),
        ('соматические заболевания', 'Соматические заболевания'), ('нарушения речи', 'Нарушения речи')
    ]
    nosology_type = models.CharField("Нозология", max_length=100, choices=NOSOLOGY_CHOICES)
    year_removal = models.DateField("Дата снятия", blank=True, null=True)


class EducationTarget(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='targets')
    agreement = models.CharField("Целевой договор", max_length=3, choices=[('Да', 'Да'), ('Нет', 'Нет')])
    name_organization = models.CharField("Организация", max_length=100, blank=True, null=True)
    abilimpiks = models.CharField("Участие в Абилимпикс", max_length=3, choices=[('Да', 'Да'), ('Нет', 'Нет')])


class Employment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='employment')
    employment_status = models.CharField("Трудоустроен", max_length=3, choices=[('Да', 'Да'), ('Нет', 'Нет')])
    place_job = models.CharField("Место работы", max_length=150, blank=True, null=True)
    position = models.CharField("Должность", max_length=100, blank=True, null=True)
    hiring_date = models.DateField("Дата приема", blank=True, null=True)
    reason_not_employment = models.CharField("Причина нетрудоустройства", max_length=200, blank=True, null=True)
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