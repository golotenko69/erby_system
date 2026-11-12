import io

import openpyxl
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from erbu_main.forms import StudentForm
from erbu_main.models import DisabilityInfo, EducationInstitution, EducationProcess, Student, StudentLog

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
            disability_group="3",
            nosology_type="слух"
        )
        # Проверяем, что через связь мы получаем верные данные
        self.assertEqual(self.student.disability_info.disability_group, "3")


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

    def test_export_of_institution_without_students_redirects_with_message(self):
        empty = EducationInstitution.objects.create(name="Колледж №3")
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('student_export_excel'), {'institutions': [empty.pk]}, secure=True)
        self.assertRedirects(response, reverse('students'), fetch_redirect_response=False)

    def test_base_section_is_always_exported(self):
        header, _ = self.export_rows(self.admin_user, sections=["passport"])
        self.assertEqual(header[0], "ID")
        self.assertIn("Паспорт Серия", header)


class StudentFormTest(TestCase):
    def test_valid_student_form(self):
        """Форма должна быть валидной при правильных данных"""
        data = {
            'first_name': 'Петр',
            'middle_name': 'Петрович',
            'last_name': 'Петров',
            'status': 'сирота',
            'sex': 'муж',
            'birthday': '2005-12-10',
            'email': 'petr@example.com',
            'phone': '+79991234567',
            'snils': '12345678901',
            'inn': '123456789012',
        }
        form = StudentForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['snils'], '123-456-789 01')

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

class AccessControlTest(TestCase):
    """Ответственное лицо не должно иметь доступа к студентам чужого учреждения и к функциям администратора."""

    def setUp(self):
        self.inst_1 = EducationInstitution.objects.create(name="Колледж №1")
        self.inst_2 = EducationInstitution.objects.create(name="Колледж №2")
        self.admin_user = User.objects.create_user(username="admin", password="pass", role="ADMIN")
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", role="TEACHER", education_institution=self.inst_1
        )
        self.own = Student.objects.create(first_name="Свой", last_name="Свой", sex="муж", birthday="2000-01-01")
        self.foreign = Student.objects.create(first_name="Чужой", last_name="Чужой", sex="жен", birthday="2000-01-01")
        EducationProcess.objects.create(student=self.own, education_institution=self.inst_1, course=1, form='очная')
        EducationProcess.objects.create(student=self.foreign, education_institution=self.inst_2, course=1, form='очная')
        self.client.force_login(self.teacher)

    def get(self, name, **kwargs):
        return self.client.get(reverse(name, kwargs=kwargs), secure=True)

    def test_teacher_sees_own_student(self):
        self.assertEqual(self.get('student_detail', student_id=self.own.pk).status_code, 200)

    def test_teacher_cannot_view_foreign_student(self):
        self.assertEqual(self.get('student_detail', student_id=self.foreign.pk).status_code, 404)

    def test_teacher_cannot_edit_foreign_student(self):
        self.assertEqual(self.get('student_edit', student_id=self.foreign.pk).status_code, 404)

    def test_teacher_cannot_delete_foreign_student(self):
        response = self.client.post(reverse('student_delete', kwargs={'student_id': self.foreign.pk}), secure=True)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Student.objects.filter(pk=self.foreign.pk).exists())

    def test_teacher_can_delete_own_student_and_it_is_logged(self):
        response = self.client.post(reverse('student_delete', kwargs={'student_id': self.own.pk}), secure=True)
        self.assertRedirects(response, reverse('students'), fetch_redirect_response=False)
        self.assertFalse(Student.objects.filter(pk=self.own.pk).exists())
        self.assertTrue(StudentLog.objects.filter(action='DELETE', student_name__contains='Свой').exists())

    def test_teacher_cannot_create_users_via_signup(self):
        response = self.client.post(reverse('signup'), {
            'username': 'hacker', 'password1': 'Sup3r-Secret-42', 'password2': 'Sup3r-Secret-42', 'role': 'ADMIN',
        }, secure=True)
        self.assertNotEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='hacker').exists())

    def test_teacher_cannot_open_institutions(self):
        self.assertNotEqual(self.get('institutions').status_code, 200)

    def test_anonymous_is_redirected_to_login_with_next(self):
        self.client.logout()
        response = self.get('students')
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
        self.assertIn('next=', response.url)


class InstitutionAdminTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(username="admin", password="pass", role="ADMIN")
        self.client.force_login(self.admin_user)

    def test_create_institution_creates_teacher_without_plaintext_password(self):
        response = self.client.post(reverse('institution_add'), {
            'name': 'Новый колледж', 'teacher_last_name': 'Иванов', 'teacher_first_name': 'Иван',
            'teacher_middle_name': '', 'teacher_phone': '+79991234567', 'teacher_email': 'i@example.com',
        }, secure=True, follow=True)
        self.assertEqual(response.status_code, 200)
        teacher = User.objects.get(role='TEACHER')
        self.assertEqual(teacher.education_institution.name, 'Новый колледж')
        self.assertFalse(hasattr(teacher, 'raw_password'))
        # Пароль показан администратору один раз в сообщении и действительно подходит
        message = str(list(response.context['messages'])[0])
        password = message.split('пароль: ')[1].split('.')[0]
        self.assertTrue(teacher.check_password(password))

    def test_reset_teacher_password(self):
        institution = EducationInstitution.objects.create(name="Колледж")
        teacher = User.objects.create_user(
            username="t", password="old", role="TEACHER", education_institution=institution
        )
        self.client.post(reverse('institution_reset_password', kwargs={'institution_id': institution.pk}), secure=True)
        teacher.refresh_from_db()
        self.assertFalse(teacher.check_password('old'))

    def test_delete_empty_institution_blocks_teacher(self):
        institution = EducationInstitution.objects.create(name="Пустой")
        teacher = User.objects.create_user(
            username="t", password="p", role="TEACHER", education_institution=institution
        )
        self.client.post(reverse('institution_delete', kwargs={'institution_id': institution.pk}), secure=True)
        self.assertFalse(EducationInstitution.objects.filter(pk=institution.pk).exists())
        teacher.refresh_from_db()
        self.assertFalse(teacher.is_active)

    def test_institution_with_students_is_not_deleted(self):
        institution = EducationInstitution.objects.create(name="С людьми")
        student = Student.objects.create(first_name="А", last_name="Б", sex="муж", birthday="2000-01-01")
        EducationProcess.objects.create(student=student, education_institution=institution, course=1, form='очная')
        self.client.post(reverse('institution_delete', kwargs={'institution_id': institution.pk}), secure=True)
        self.assertTrue(EducationInstitution.objects.filter(pk=institution.pk).exists())


class StudentCreateEditFlowTest(TestCase):
    """Полный цикл: создание студента со всеми разделами и последующее редактирование."""

    def setUp(self):
        self.institution = EducationInstitution.objects.create(name="Колледж")
        self.other = EducationInstitution.objects.create(name="Чужой колледж")
        self.teacher = User.objects.create_user(
            username="teacher", password="pass", role="TEACHER", education_institution=self.institution
        )
        self.client.force_login(self.teacher)

    def form_data(self, **overrides):
        data = {
            'first_name': 'Петр', 'middle_name': 'Петрович', 'last_name': 'Петров', 'status': 'сирота',
            'sex': 'муж', 'birthday': '2005-12-10', 'email': 'petr@example.com', 'phone': '+79991234567',
            'snils': '12345678901', 'inn': '123456789012',
            'passport-series': '1234', 'passport-number': '567890', 'passport-issued': 'УФМС',
            'passport-date_issued': '2020-01-01', 'passport-department_code': '123-456',
            'passport-place_birth': 'Чита', 'passport-place_resident': 'Чита',
            'disability-has_disability': 'Да', 'disability-disability_group': '3',
            'disability-nosology_type': 'слух', 'disability-disability_indefinite': 'on',
            'disability-status_ovz': 'Нет',
            'mse-series': 'МСЭ', 'mse-number': '1', 'mse-date_issued': '2021-01-01',
            'edu_end-education_type': 'общее', 'edu_end-name': 'Школа №1',
            'edu_end-education_document': 'аттестат', 'edu_end-series': '123', 'edu_end-date_issued': '2021-06-01',
            # Пытаемся подставить чужое учреждение — оно должно быть отклонено/заменено
            'edu_proc-education_institution': str(self.institution.pk), 'edu_proc-profession': 'Повар',
            'edu_proc-course': '1', 'edu_proc-form': 'очная', 'edu_proc-term': '1 г. 10 мес.',
            'edu_proc-grad_date': '2026-06-30',
            'edu_tar-agreement': 'Нет', 'edu_tar-name_organization': '-', 'edu_tar-abilimpiks': 'Нет',
            'employment-employment_status': 'Нет', 'employment-reason_not_employment': 'иные',
            'employment-accounting_employment': 'Нет', 'employment-resume_status': 'Нет',
            'parent-TOTAL_FORMS': '1', 'parent-INITIAL_FORMS': '0',
            'parent-MIN_NUM_FORMS': '0', 'parent-MAX_NUM_FORMS': '1000',
            'parent-0-first_name': 'Иван', 'parent-0-middle_name': 'Иванович', 'parent-0-last_name': 'Петров',
            'parent-0-phone': '89991234567', 'parent-0-email': 'father@example.com',
        }
        data.update(overrides)
        return data

    def test_create_then_edit(self):
        response = self.client.post(reverse('student_add'), self.form_data(), secure=True)
        self.assertEqual(response.status_code, 302, getattr(response, 'context', None) and [
            (k, v.errors) for k, v in response.context.flatten().items() if hasattr(v, 'errors') and v.errors
        ])
        student = Student.objects.get(last_name='Петров')
        self.assertEqual(student.education_process.education_institution, self.institution)
        self.assertEqual(student.education_process.term, 22)
        self.assertTrue(hasattr(student.disability_info, 'mse'))
        self.assertEqual(student.parents.count(), 1)
        self.assertTrue(StudentLog.objects.filter(action='CREATE').exists())

        # Чужое учреждение подставить нельзя
        response = self.client.post(
            reverse('student_add'),
            self.form_data(**{'edu_proc-education_institution': str(self.other.pk), 'snils': '11111111111'}),
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(EducationProcess.objects.filter(education_institution=self.other).exists())

        # Редактирование: снимаем инвалидность (МСЭ удаляется), меняем телефон (попадает в журнал)
        parent = student.parents.get()
        data = self.form_data(**{
            'phone': '+79990000000', 'disability-has_disability': 'Нет',
            'parent-INITIAL_FORMS': '1', 'parent-0-id': str(parent.pk), 'parent-0-student': str(student.pk),
        })
        response = self.client.post(reverse('student_edit', kwargs={'student_id': student.pk}), data, secure=True)
        self.assertEqual(response.status_code, 302)
        student.refresh_from_db()
        self.assertEqual(student.phone, '+79990000000')
        self.assertFalse(hasattr(student.disability_info, 'mse'))
        log = StudentLog.objects.get(action='UPDATE')
        self.assertIn('Телефон', log.changes)

    def test_edit_student_without_related_records(self):
        """Студент без паспорта и прочих разделов (например, заведён через админку) редактируется без ошибок."""
        student = Student.objects.create(first_name="Петр", last_name="Петров", sex="муж", birthday="2005-12-10")
        EducationProcess.objects.create(student=student, education_institution=self.institution, course=1, form='очная')
        response = self.client.post(
            reverse('student_edit', kwargs={'student_id': student.pk}), self.form_data(), secure=True
        )
        self.assertEqual(response.status_code, 302)
        student.refresh_from_db()
        self.assertEqual(student.passport.series, '1234')
        self.assertEqual(student.employment.reason_not_employment, 'иные')
