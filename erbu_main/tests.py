import io

import openpyxl
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from erbu_main.forms import StudentForm
from erbu_main.models import DisabilityInfo, EducationInstitution, EducationProcess, Student

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

    def export_rows(self, user, **data):
        """Выполняет экспорт от имени user и возвращает (шапка, фамилии студентов из отчёта)."""
        self.client.force_login(user)
        response = self.client.post(reverse('student_export_excel'), data, secure=True)
        self.assertEqual(response.status_code, 200)
        sheet = openpyxl.load_workbook(io.BytesIO(response.content)).active
        rows = list(sheet.iter_rows(values_only=True))
        return rows[0], [row[1] for row in rows[1:]]

    def test_admin_export_without_filter_contains_all_institutions(self):
        _, last_names = self.export_rows(self.admin_user)
        self.assertEqual(last_names, ["Первый", "Второй"])

    def test_admin_export_filtered_by_one_institution(self):
        _, last_names = self.export_rows(self.admin_user, institutions=[self.inst_2.pk])
        self.assertEqual(last_names, ["Второй"])

    def test_admin_export_filtered_by_several_institutions(self):
        _, last_names = self.export_rows(self.admin_user, institutions=[self.inst_1.pk, self.inst_2.pk])
        self.assertEqual(sorted(last_names), ["Второй", "Первый"])

    def test_admin_export_ignores_invalid_institution_id(self):
        _, last_names = self.export_rows(self.admin_user, institutions=["abc"])
        self.assertEqual(len(last_names), 2)

    def test_teacher_export_is_limited_to_own_institution(self):
        # Ответственное лицо не может выгрузить чужое заведение, подставив его id
        _, last_names = self.export_rows(self.teacher_user, institutions=[self.inst_2.pk])
        self.assertEqual(last_names, ["Первый"])

    def test_base_section_is_always_exported(self):
        header, _ = self.export_rows(self.admin_user, sections=["passport"])
        self.assertEqual(header[0], "ID")
        self.assertIn("Паспорт Серия", header)


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