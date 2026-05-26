from django.test import TestCase
from django.utils import timezone
from erbu_main.models import Student, DisabilityInfo
from django.urls import reverse
from django.contrib.auth import get_user_model
from erbu_main.models import Student, EducationProcess, EducationInstitution
from erbu_main.forms import StudentForm

class StudentModelTest(TestCase):
    def setUp(self):
        # Метод setUp выполняется ПЕРЕД каждым тестом. Создаем тестовые данные.
        self.student = Student.objects.create(
            first_name="Иван",
            last_name="Иванов",
            middle_name="Иванович",
            status="родительский",
            sex="муж",
            email="ivan@example.com",
            phone="89991112233",
            birthday=timezone.now().date()
        )

    def test_student_creation(self):
        """Проверяем, что объект студента успешно создался"""
        self.assertEqual(self.student.first_name, "Иван")
        self.assertEqual(self.student.last_name, "Иванов")
        # Проверяем строковое представление, если оно у вас настроено в __str__
        self.assertEqual(str(self.student), "Иванов Иван")

    def test_disability_info_relation(self):
        """Проверяем связь «Один к одному» с информацией об инвалидности"""
        disability = DisabilityInfo.objects.create(
            student=self.student,
            status_ovz="Да",
            disability_group="3 группа",
            nosology_type="Нарушения слуха"
        )
        # Проверяем, что через связь мы получаем верные данные
        self.assertEqual(self.student.disability_info.disability_group, "3 группа")


User = get_user_model()


class StudentAccessViewsTest(TestCase):
    def setUp(self):
        # 1. Создаем учебные заведения
        self.inst_1 = EducationInstitution.objects.create(name="Колледж №1")
        self.inst_2 = EducationInstitution.objects.create(name="Колледж №2")

        # 2. Создаем пользователей с разными ролями
        self.admin_user = User.objects.create_user(
            username="admin_user", password="password123", role="ADMIN"
        )
        self.teacher_user = User.objects.create_user(
            username="teacher_user", password="password123", role="TEACHER",
            education_institution=self.inst_1
        )

        # 3. Создаем студентов
        self.student_1 = Student.objects.create(
            first_name="Студент", last_name="Первый", sex="муж", birthday="2000-01-01"
        )
        self.student_2 = Student.objects.create(
            first_name="Студент", last_name="Второй", sex="жен", birthday="2000-05-05"
        )

        # 4. Привязываем студентов к разным колледжам
        EducationProcess.objects.create(
            student=self.student_1,
            education_institution=self.inst_1,
            course=1,  # Передаем обязательный курс (доступно от 1 до 4)
            form='очная'  # Также передаем форму обучения, так как она не null=True в моделях
        )

        EducationProcess.objects.create(
            student=self.student_2,
            education_institution=self.inst_2,
            course=2,  # Передаем обязательный курс
            form='очная'  # Передаем форму обучения
        )

class StudentFormTest(TestCase):
    def test_valid_student_form(self):
        """Форма должна быть валидной при правильных данных"""
        data = {
            'first_name': 'Петр',
            'last_name': 'Петров',
            'status': 'сирота',
            'sex': 'муж',
            'birthday': '2005-12-10',
        }
        form = StudentForm(data=data)
        self.assertTrue(form.is_valid())

    def test_invalid_student_form_empty_birthday(self):
        """Форма должна быть невалидной, если пропущена дата рождения"""
        data = {
            'first_name': 'Петр',
            'last_name': 'Петров',
            'status': 'сирота',
            'sex': 'муж',
            # 'birthday' отсутствует
        }
        form = StudentForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('birthday', form.errors)