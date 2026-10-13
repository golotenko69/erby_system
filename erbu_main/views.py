import random
import string

import openpyxl
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from erbu_main.forms import (
    DisabilityForm, EducationEndedForm, EducationInstitutionForm, EducationProcessForm,
    EducationTargetForm, EmploymentForm, MseForm, ParentFormSet, PassportForm, PmpkForm, StudentForm,
)
from erbu_main.mixins import AdminRequiredMixin, TeacherRequiredMixin
from erbu_main.models import DisabilityInfo, EducationInstitution, EducationProcess, Student, StudentLog
from users.forms import CustomUserCreationForm

User = get_user_model()


def generate_random_string(length=8):
    """Случайная строка из букв и цифр (логины и пароли ответственных лиц)."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choice(alphabet) for _ in range(length))


def format_term(months):
    """Срок обучения в месяцах -> «1 г. 10 мес.» / «2 г.» / «10 мес.»."""
    if not months:
        return ''
    years, rest = divmod(months, 12)
    if years and rest:
        return f'{years} г. {rest} мес.'
    return f'{years} г.' if years else f'{rest} мес.'


def students_for_user(user):
    """Студенты, доступные пользователю: администратору — все, ответственному — своего заведения."""
    role = getattr(user, 'role', None)
    if role == 'ADMIN':
        return Student.objects.all()
    if role == 'TEACHER':
        return Student.objects.filter(
            education_process__education_institution=user.education_institution
        ).distinct()
    return Student.objects.none()


def mark_logs_read(request):
    """Фоновая функция для сброса счётчика уведомлений."""
    if request.method == 'POST' and request.user.is_authenticated and getattr(request.user, 'role', None) == 'ADMIN':
        StudentLog.objects.filter(is_read=False).update(is_read=True)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


def index_view(request):
    return render(request, 'erbu_main/index.html')


def contacts_view(request):
    return render(request, 'erbu_main/contacts.html')


class StudentsListView(TeacherRequiredMixin, ListView):
    model = Student
    template_name = 'erbu_main/students/students.html'
    context_object_name = 'students'
    paginate_by = 10

    def get_queryset(self):
        return students_for_user(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Выбор учебных заведений при экспорте доступен только администратору
        if getattr(self.request.user, 'role', None) == 'ADMIN':
            context['export_institutions'] = EducationInstitution.objects.order_by('name')
        return context


class StudentCreateView(TeacherRequiredMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'erbu_main/students/students_form.html'
    success_url = reverse_lazy('students')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context['passport_form'] = PassportForm(self.request.POST, prefix='passport')
            context['disability_form'] = DisabilityForm(self.request.POST, prefix='disability')
            context['mse_form'] = MseForm(self.request.POST, prefix='mse')
            context['pmpk_form'] = PmpkForm(self.request.POST, prefix='pmpk')
            context['parent_formset'] = ParentFormSet(self.request.POST, prefix='parent')
            context['edu_end_form'] = EducationEndedForm(self.request.POST, prefix='edu_end')
            context['edu_proc_form'] = EducationProcessForm(self.request.POST, user=self.request.user, prefix='edu_proc')
            context['edu_tar_form'] = EducationTargetForm(self.request.POST, prefix='edu_tar')
            context['employment_form'] = EmploymentForm(self.request.POST, prefix='employment')
        else:
            context['passport_form'] = PassportForm(prefix='passport')
            context['disability_form'] = DisabilityForm(prefix='disability')
            context['mse_form'] = MseForm(prefix='mse')
            context['pmpk_form'] = PmpkForm(prefix='pmpk')
            context['parent_formset'] = ParentFormSet(prefix='parent')
            context['edu_end_form'] = EducationEndedForm(prefix='edu_end')
            context['edu_proc_form'] = EducationProcessForm(user=self.request.user, prefix='edu_proc')
            context['edu_tar_form'] = EducationTargetForm(prefix='edu_tar')
            context['employment_form'] = EmploymentForm(prefix='employment')

        return context

    def form_valid(self, form):
        context = self.get_context_data()

        passport_form = context['passport_form']
        disability_form = context['disability_form']
        mse_form = context['mse_form']
        pmpk_form = context['pmpk_form']
        parent_formset = context['parent_formset']
        edu_end_form = context['edu_end_form']
        edu_proc_form = context['edu_proc_form']
        edu_tar_form = context['edu_tar_form']
        employment_form = context['employment_form']

        forms_valid = (
                form.is_valid() and passport_form.is_valid() and
                disability_form.is_valid() and mse_form.is_valid() and
                pmpk_form.is_valid() and parent_formset.is_valid() and
                edu_end_form.is_valid() and edu_proc_form.is_valid() and
                edu_tar_form.is_valid() and employment_form.is_valid()
        )

        if forms_valid:
            student = form.save()

            passport = passport_form.save(commit=False)
            passport.student = student
            passport.save()

            disability = disability_form.save(commit=False)
            disability.student = student
            disability.save()

            # Сохраняем МСЭ только если указана Инвалидность
            if disability_form.cleaned_data.get('has_disability') == 'Да':
                mse = mse_form.save(commit=False)
                mse.disability = disability
                mse.save()

            # Сохраняем ПМПК только если указан статус ОВЗ = Да
            if disability_form.cleaned_data.get('status_ovz') == 'Да':
                pmpk = pmpk_form.save(commit=False)
                pmpk.disability = disability
                pmpk.save()

            education_ended = edu_end_form.save(commit=False)
            education_ended.student = student
            education_ended.save()

            education_process = edu_proc_form.save(commit=False)
            education_process.student = student

            if self.request.user.role == 'TEACHER':
                education_process.education_institution = self.request.user.education_institution
            education_process.save()

            education_target = edu_tar_form.save(commit=False)
            education_target.student = student
            education_target.save()

            employment = employment_form.save(commit=False)
            employment.student = student
            employment.save()

            parent_formset.instance = student
            parent_formset.save()

            user_institution = getattr(self.request.user, 'education_institution', None)
            StudentLog.objects.create(
                action='CREATE',
                student_name=f"{student.last_name} {student.first_name} {student.middle_name or ''}".strip(),
                user=self.request.user,
                institution_name=user_institution.name if user_institution else "Администрация"
            )

            messages.success(self.request, f"Студент '{student.first_name} {student.last_name}' успешно создан!")
            return redirect('student_detail', student_id=student.pk)

        return self.render_to_response(self.get_context_data(form=form))

class StudentDeleteView(TeacherRequiredMixin, DeleteView):
    model = Student
    template_name = 'erbu_main/students/student_confirm_delete.html'
    success_url = reverse_lazy('students')
    pk_url_kwarg = 'student_id'

    def post(self, request, *args, **kwargs):
        obj = self.get_object()

        # ЛОГИРОВАНИЕ УДАЛЕНИЯ
        user_institution = getattr(self.request.user, 'education_institution', None)
        StudentLog.objects.create(
            action='DELETE',
            student_name=f"{obj.last_name} {obj.first_name} {obj.middle_name or ''}".strip(),
            user=self.request.user,
            institution_name=user_institution.name if user_institution else "Администрация"
        )

        messages.success(self.request, f"Студент '{obj.first_name} {obj.last_name}' успешно удален!")
        return super().delete(request, *args, **kwargs)

class StudentDetailView(TeacherRequiredMixin, DetailView):
    model = Student
    template_name = 'erbu_main/students/student_detail.html'
    context_object_name = 'student'
    pk_url_kwarg = 'student_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object

        # Паспорт
        context['passport'] = getattr(student, 'passport', None)

        # Инвалидность и связанные данные
        try:
            disability = student.disability_info
            context['disability'] = disability
            context['mse'] = getattr(disability, 'mse', None)
            context['pmpk'] = getattr(disability, 'pmpk', None)
        except DisabilityInfo.DoesNotExist:
            context['disability'] = None
            context['mse'] = None
            context['pmpk'] = None

        # Образование
        context['education_ended'] = getattr(student, 'education_ended', None)
        context['education_process'] = getattr(student, 'education_process', None)
        if context['education_process'] and context['education_process'].term:
            context['education_process'].term_display = format_term(context['education_process'].term)
        context['education_target'] = getattr(student, 'education_target', None)
        # Родители
        context['parents'] = student.parents.all()

        # Трудоустройство
        context['employment'] = getattr(student, 'employment', None)

        return context

    def get_queryset(self):
        user = self.request.user

        if user.role == 'ADMIN':
            return Student.objects.all()

        return Student.objects.filter(
            Q(education_process__education_institution=user.education_institution) |
            Q(pk=self.kwargs.get('student_id'))
        ).distinct()

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'


class EducationInstitutionListView(AdminRequiredMixin, ListView):
    """Список всех учебных заведений"""
    model = EducationInstitution
    template_name = 'erbu_main/educations/institution_list.html'
    context_object_name = 'institutions'
    paginate_by = 20

    def get_queryset(self):
        return EducationInstitution.objects.all().order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Передаем роль в контекст, чтобы делать проверки в шаблоне
        context['is_admin'] = getattr(user, 'role', None) == 'ADMIN'

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        for institution in context['institutions']:
            institution.teacher = User.objects.filter(
                education_institution=institution,
                role='TEACHER'
            ).first()

        for institution in context['institutions']:
            # Базовый запрос процессов обучения для этого учреждения
            edu_processes = EducationProcess.objects.filter(education_institution=institution)

            # 1. Общее количество уникальных студентов
            institution.student_count = edu_processes.values('student').distinct().count()

            # Данные, доступные только для администратора
            if context['is_admin']:
                # 2. Сколько студентов добавлено за сегодня
                institution.students_added_today = edu_processes.filter(
                    created_at__gte=today_start
                ).values('student').distinct().count()

                # 3. Последние добавленные студенты (например, последние 3) для вывода времени
                institution.recent_additions = edu_processes.select_related('student').order_by('-created_at')[:3]

        return context

class EducationInstitutionDetailView(AdminRequiredMixin, DetailView):
    """Детальная информация об учебном заведении"""
    model = EducationInstitution
    template_name = 'erbu_main/educations/institution_detail.html'
    context_object_name = 'institution'
    pk_url_kwarg = 'institution_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = self.object

        context['responsible_teacher'] = User.objects.filter(
            education_institution=institution,
            role='TEACHER'
        ).first()

        # Получаем всех студентов, обучающихся в этом учреждении
        education_processes = EducationProcess.objects.filter(
            education_institution=institution
        ).select_related('student').order_by('student__last_name', 'student__first_name')

        # Группируем по курсам
        students_by_course = {
            1: [], 2: [], 3: [], 4: []
        }

        for edu in education_processes:
            if edu.course in students_by_course:
                students_by_course[edu.course].append({
                    'student': edu.student,
                    'profession': edu.profession,
                    'form': edu.get_form_display(),
                    'grad_date': edu.grad_date
                })

        context['students_by_course'] = students_by_course
        context['total_students'] = education_processes.values('student').distinct().count()
        context['professions'] = education_processes.values_list('profession', flat=True).distinct()

        return context


class EducationInstitutionCreateView(AdminRequiredMixin, CreateView):
    """Создание нового учебного заведения и пользователя-учителя"""
    model = EducationInstitution
    form_class = EducationInstitutionForm
    template_name = 'erbu_main/educations/institution_form.html'
    success_url = reverse_lazy('institutions')

    def form_valid(self, form):
        # Сохраняем само учебное заведение
        response = super().form_valid(form)
        institution = self.object

        # Генерируем уникальный логин и пароль
        username = f"user_{generate_random_string(6).lower()}"
        password = generate_random_string(10)

        # Создаем связанного пользователя (учителя)
        User.objects.create_user(
            username=username,
            password=password,
            first_name=form.cleaned_data['teacher_first_name'],
            last_name=form.cleaned_data['teacher_last_name'],
            middle_name=form.cleaned_data.get('teacher_middle_name', ''),
            email=form.cleaned_data['teacher_email'],
            phone=form.cleaned_data['teacher_phone'],
            role='TEACHER',
            education_institution=institution,
            raw_password=password  # Сохраняем пароль, чтобы показать его админу
        )

        messages.success(
            self.request,
            f"Учреждение '{institution.name}' и ответственный успешно созданы!"
        )
        return response


class EducationInstitutionUpdateView(AdminRequiredMixin, UpdateView):
    """Редактирование учебного заведения"""
    model = EducationInstitution
    form_class = EducationInstitutionForm
    template_name = 'erbu_main/educations/institution_form.html'
    pk_url_kwarg = 'institution_id'

    def get_success_url(self):
        return reverse_lazy('institution_detail', kwargs={'institution_id': self.object.pk})

    def form_valid(self, form):
        messages.success(
            self.request,
            f"Учебное заведение '{form.instance.name}' успешно обновлено!"
        )
        return super().form_valid(form)


class EducationInstitutionDeleteView(AdminRequiredMixin, DeleteView):
    """Удаление учебного заведения с ограничением по студентам"""
    model = EducationInstitution
    template_name = 'erbu_main/educations/institution_confirm_delete.html'
    pk_url_kwarg = 'institution_id'
    success_url = reverse_lazy('institutions')
    context_object_name = 'institution'

    def dispatch(self, request, *args, **kwargs):
        """Проверяем наличие студентов до выполнения любого (GET/POST) запроса"""
        institution = self.get_object()
        students_count = EducationProcess.objects.filter(
            education_institution=institution
        ).values('student').distinct().count()

        # Если это POST-запрос (попытка удалить) и студенты есть — блокируем
        if request.method == 'POST' and students_count > 0:
            messages.error(
                request,
                f"Ошибка! Невозможно удалить учреждение '{institution.name}', так как в нём обучается {students_count} студентов."
            )
            return redirect('institution_detail', institution_id=institution.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Передаем количество студентов в контекст шаблона для динамического UI"""
        context = super().get_context_data(**kwargs)
        context['students_count'] = EducationProcess.objects.filter(
            education_institution=self.object
        ).values('student').distinct().count()
        return context

    def delete(self, request, *args, **kwargs):
        """Вызывается, если проверка в dispatch пройдена успешно и студентов нет"""
        institution = self.get_object()

        # Находим учителей этого заведения и деактивируем их, чтобы они не могли войти
        teachers = User.objects.filter(education_institution=institution, role='TEACHER')
        for teacher in teachers:
            teacher.is_active = False
            teacher.education_institution = None  # Стираем связь с удаленным учреждением
            teacher.save()

        messages.success(
            request,
            f"Учебное заведение '{institution.name}' успешно удалено. Связанные аккаунты сотрудников заблокированы."
        )
        return super().delete(request, *args, **kwargs)


class StudentFullEditView(UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'erbu_main/students/students_form.html'
    pk_url_kwarg = 'student_id'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if self.request.user.role == 'TEACHER':
            student_institution = None
            if hasattr(obj, 'education_process') and obj.education_process:
                student_institution = obj.education_process.education_institution

            if student_institution != self.request.user.education_institution:
                raise PermissionDenied("Нет доступа")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object if self.object.pk else None

        disability = getattr(student, 'disability_info', None)
        mse_instance = disability.mse if disability and hasattr(disability, 'mse') else None
        pmpk_instance = disability.pmpk if disability and hasattr(disability, 'pmpk') else None

        if self.request.POST:
            context['passport_form'] = PassportForm(self.request.POST, instance=getattr(student, 'passport', None),
                                                    prefix='passport')
            context['disability_form'] = DisabilityForm(self.request.POST, instance=disability, prefix='disability')
            context['mse_form'] = MseForm(self.request.POST, instance=mse_instance, prefix='mse')
            context['pmpk_form'] = PmpkForm(self.request.POST, instance=pmpk_instance, prefix='pmpk')
            context['parent_formset'] = ParentFormSet(self.request.POST, instance=student, prefix='parent')
            context['edu_end_form'] = EducationEndedForm(self.request.POST,
                                                         instance=getattr(student, 'education_ended', None),
                                                         prefix='edu_end')
            context['edu_proc_form'] = EducationProcessForm(self.request.POST,
                                                            instance=getattr(student, 'education_process', None),
                                                            user=self.request.user, prefix='edu_proc')
            context['edu_tar_form'] = EducationTargetForm(self.request.POST,
                                                          instance=getattr(student, 'education_target', None),
                                                          prefix='edu_tar')
            context['employment_form'] = EmploymentForm(self.request.POST,
                                                        instance=getattr(student, 'employment', None),
                                                        prefix='employment')
        else:
            context['passport_form'] = PassportForm(instance=getattr(student, 'passport', None), prefix='passport')
            context['disability_form'] = DisabilityForm(instance=disability, prefix='disability')
            context['mse_form'] = MseForm(instance=mse_instance, prefix='mse')
            context['pmpk_form'] = PmpkForm(instance=pmpk_instance, prefix='pmpk')
            context['parent_formset'] = ParentFormSet(instance=student, prefix='parent')
            context['edu_end_form'] = EducationEndedForm(instance=getattr(student, 'education_ended', None),
                                                         prefix='edu_end')
            context['edu_proc_form'] = EducationProcessForm(instance=getattr(student, 'education_process', None),
                                                            user=self.request.user, prefix='edu_proc')
            context['edu_tar_form'] = EducationTargetForm(instance=getattr(student, 'education_target', None),
                                                          prefix='edu_tar')
            context['employment_form'] = EmploymentForm(instance=getattr(student, 'employment', None),
                                                        prefix='employment')

        return context

    def form_valid(self, form):
        context = self.get_context_data()

        passport_form = context['passport_form']
        disability_form = context['disability_form']
        mse_form = context['mse_form']
        pmpk_form = context['pmpk_form']
        parent_formset = context['parent_formset']
        edu_end_form = context['edu_end_form']
        edu_proc_form = context['edu_proc_form']
        edu_tar_form = context['edu_tar_form']
        employment_form = context['employment_form']

        forms_valid = (
                form.is_valid() and passport_form.is_valid() and
                disability_form.is_valid() and mse_form.is_valid() and
                pmpk_form.is_valid() and parent_formset.is_valid() and
                edu_end_form.is_valid() and edu_proc_form.is_valid() and
                edu_tar_form.is_valid() and employment_form.is_valid()
        )

        if forms_valid:
            old_student = Student.objects.get(pk=self.object.pk)
            changes_list = []

            field_labels = {
                'status': 'Статус', 'phone': 'Телефон', 'email': 'Email',
                'education_type': 'Тип оконч. образования', 'education_document': 'Документ оконч. образования',
                'agreement': 'Целевой договор', 'abilimpiks': 'Участие в Абилимпикс',
                'employment_status': 'Трудоустроен', 'accounting_employment': 'Состоит в ЦЗН',
                'resume_status': 'Резюме создано'
            }

            def check_changes(form_obj, old_obj, fields):
                for field in fields:
                    if field in form_obj.cleaned_data:
                        new_val = form_obj.cleaned_data[field]
                        old_val = getattr(old_obj, field, None)

                        if hasattr(form_obj.fields[field], 'choices') and new_val:
                            new_val = dict(form_obj.fields[field].choices).get(new_val, new_val)
                        if old_obj and hasattr(old_obj, f'get_{field}_display'):
                            old_val = getattr(old_obj, f'get_{field}_display')()

                        if str(old_val) != str(new_val) and (old_val or new_val):
                            label = field_labels.get(field, field)
                            changes_list.append(f"• {label}: «{old_val or 'нет'}» ➔ «{new_val or 'нет'}»")

            check_changes(form, old_student, ['status', 'phone', 'email'])

            if hasattr(old_student, 'education_ended'):
                check_changes(edu_end_form, old_student.education_ended, ['education_type', 'education_document'])
            if hasattr(old_student, 'education_target'):
                check_changes(edu_tar_form, old_student.education_target, ['agreement', 'abilimpiks'])
            if hasattr(old_student, 'employment'):
                check_changes(employment_form, old_student.employment,
                              ['employment_status', 'accounting_employment', 'resume_status'])

            student = form.save()
            passport_form.save()

            disability = disability_form.save(commit=False)
            disability.student = student
            disability.save()

            # Обновление или удаление МСЭ
            if disability_form.cleaned_data.get('has_disability') == 'Да':
                mse = mse_form.save(commit=False)
                mse.disability = disability
                mse.save()
            else:
                if hasattr(disability, 'mse'):
                    disability.mse.delete()

            # Обновление или удаление ПМПК
            if disability_form.cleaned_data.get('status_ovz') == 'Да':
                pmpk = pmpk_form.save(commit=False)
                pmpk.disability = disability
                pmpk.save()
            else:
                if hasattr(disability, 'pmpk'):
                    disability.pmpk.delete()

            edu_end_form.save()
            edu_proc_form.save()
            edu_tar_form.save()
            employment_form.save()
            parent_formset.save()

            changes_text = "\n".join(changes_list) if changes_list else "Существенных изменений в ключевых полях нет."

            user_institution = getattr(self.request.user, 'education_institution', None)
            StudentLog.objects.create(
                action='UPDATE',
                student_name=f"{student.last_name} {student.first_name} {student.middle_name or ''}".strip(),
                user=self.request.user,
                institution_name=user_institution.name if user_institution else "Администрация",
                changes=changes_text
            )

            messages.success(self.request, "Студент успешно сохранен")
            return redirect('student_detail', student_id=student.pk)

        return self.render_to_response(self.get_context_data(form=form))

def _date(value):
    return value.strftime('%d.%m.%Y') if value else ''


def _base_row(student):
    return [
        student.student_id, student.last_name, student.first_name, student.middle_name,
        student.get_status_display(), student.get_sex_display(), student.email, student.phone,
        _date(student.birthday), student.snils, student.inn,
    ]


def _passport_row(student):
    p = getattr(student, 'passport', None)
    if not p:
        return [''] * 7
    return [p.series, p.number, p.issued, _date(p.date_issued), p.department_code, p.place_birth, p.place_resident]


def _disability_row(student):
    d = getattr(student, 'disability_info', None)
    if not d:
        return [''] * 11
    mse = getattr(d, 'mse', None)
    pmpk = getattr(d, 'pmpk', None)
    if d.disability_indefinite:
        removal, next_examination = 'Бессрочно', ''
    else:
        removal = _date(d.year_removal)
        next_examination = _date(mse.date_next_examination) if mse else ''
    return [
        d.get_status_ovz_display(), d.get_disability_group_display(), d.get_nosology_type_display(), removal,
        mse.series if mse else '', mse.number if mse else '',
        _date(mse.date_issued) if mse else '', next_examination,
        pmpk.number if pmpk else '', _date(pmpk.date_issued) if pmpk else '',
        pmpk.education_programm_pmpk if pmpk else '',
    ]


def _education_row(student):
    ee = getattr(student, 'education_ended', None)
    ep = getattr(student, 'education_process', None)
    et = getattr(student, 'education_target', None)
    return [
        ee.get_education_type_display() if ee else '', ee.name if ee else '',
        ee.get_education_document_display() if ee else '', ee.series if ee else '',
        _date(ee.date_issued) if ee else '',
        ep.education_institution.name if ep and ep.education_institution else '',
        ep.profession if ep else '', ep.course if ep else '', ep.get_form_display() if ep else '',
        format_term(ep.term) if ep else '', _date(ep.grad_date) if ep else '',
        et.name_organization if et else '', et.agreement if et else '', et.abilimpiks if et else '',
    ]


def _employment_row(student):
    em = getattr(student, 'employment', None)
    if not em:
        return [''] * 7
    return [
        em.get_employment_status_display(), em.place_job, em.position, _date(em.hiring_date),
        em.get_reason_not_employment_display(), em.get_accounting_employment_display(),
        em.get_resume_status_display(),
    ]


def _parents_row(student):
    parents = []
    for parent in student.parents.all():
        full_name = f"{parent.last_name or ''} {parent.first_name or ''} {parent.middle_name or ''}".strip()
        parents.append(f"{full_name} (Тел: {parent.phone or '-'}, Email: {parent.email or '-'})")
    return ['\n'.join(parents) if parents else 'Нет данных']


# Разделы отчёта в порядке вывода колонок: код -> (заголовки, функция строки)
EXPORT_SECTIONS = {
    'base': (
        ['ID', 'Фамилия', 'Имя', 'Отчество', 'Статус', 'Пол', 'Email', 'Телефон', 'Дата рождения', 'СНИЛС', 'ИНН'],
        _base_row,
    ),
    'passport': (
        ['Паспорт Серия', 'Паспорт Номер', 'Кем выдан', 'Дата выдачи', 'Код подр.', 'Место рождения',
         'Место жительства'],
        _passport_row,
    ),
    'disability': (
        ['Статус ОВЗ', 'Группа инвалидности', 'Нозология', 'Дата снятия', 'МСЭ Серия', 'МСЭ Номер',
         'МСЭ Дата выдачи', 'МСЭ Переосвидетельствование', 'ПМПК Номер', 'ПМПК Дата', 'Реком. программа'],
        _disability_row,
    ),
    'education': (
        ['Предыд. образование', 'Учреждение (предыд.)', 'Документ об образ.', 'Серия/Номер док.',
         'Дата выдачи док.', 'Текущее учреждение', 'Профессия', 'Курс', 'Форма обучения', 'Срок обучения',
         'Дата выпуска', 'Целевое образование', 'Договор', 'Абилимпикс'],
        _education_row,
    ),
    'employment': (
        ['Трудоустроен', 'Место работы', 'Должность', 'Дата приема', 'Причина нетрудоустр.', 'Состоит в ЦЗН',
         'Резюме создано'],
        _employment_row,
    ),
    'parents': (['Родители (ФИО, Телефон, Email)'], _parents_row),
}


class ExportStudentsExcelView(TeacherRequiredMixin, View):
    """Excel-отчёт по студентам.

    POST-параметры:
      sections     — дополнительные разделы отчёта (ключи EXPORT_SECTIONS), «base» включается всегда;
      institutions — id учебных заведений (только для администратора);
                     если не выбрано ни одного — выгружаются студенты всех заведений.
    Ответственное лицо всегда получает отчёт только по своему заведению.
    """

    def post(self, request, *args, **kwargs):
        requested = request.POST.getlist('sections')
        # «Основная информация» входит в отчёт всегда
        sections = [code for code in EXPORT_SECTIONS if code == 'base' or code in requested]

        queryset = students_for_user(request.user)
        if request.user.role == 'ADMIN':
            institution_ids = [int(pk) for pk in request.POST.getlist('institutions') if pk.isdigit()]
            if institution_ids:
                queryset = queryset.filter(education_process__education_institution__in=institution_ids)

        queryset = queryset.select_related(
            'passport', 'disability_info', 'disability_info__mse', 'disability_info__pmpk',
            'education_ended', 'education_process', 'education_process__education_institution',
            'education_target', 'employment',
        ).prefetch_related('parents').order_by(
            'education_process__education_institution__name', 'last_name', 'first_name'
        )

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Студенты'

        header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
        grey = Side(style='thin', color='D9D9D9')
        cell_border = Border(left=grey, right=grey, top=grey, bottom=grey)
        align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
        align_left = Alignment(horizontal='left', vertical='center', wrap_text=True)

        ws.append([header for code in sections for header in EXPORT_SECTIONS[code][0]])
        ws.row_dimensions[1].height = 28
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = align_center

        for row_num, student in enumerate(queryset, start=2):
            ws.append([value for code in sections for value in EXPORT_SECTIONS[code][1](student)])
            ws.row_dimensions[row_num].height = 22
            for cell in ws[row_num]:
                cell.border = cell_border
                cell.alignment = align_center if cell.column == 1 else align_left

        # Ширина колонок по содержимому
        for column in ws.columns:
            longest = max(len(str(cell.value or '')) for cell in column)
            ws.column_dimensions[get_column_letter(column[0].column)].width = max(longest + 3, 12)

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="students_report.xlsx"'
        wb.save(response)
        return response


class LogDetailJsonView(View):
    def get(self, request, log_id, *args, **kwargs):
        if not request.user.is_authenticated or getattr(request.user, 'role', None) != 'ADMIN':
            return JsonResponse({'error': 'Доступ запрещен'}, status=403)

        log_item = get_object_or_404(StudentLog, pk=log_id)

        data = {
            'action_display': log_item.get_action_display(),
            'student_name': log_item.student_name,
            'user': f"{log_item.user.last_name or ''} {log_item.user.first_name or ''}".strip() if log_item.user else "Система",
            'institution': log_item.institution_name or "Не указано",
            'date': log_item.created_at.strftime('%d.%m.%Y в %H:%M'),
            'changes': log_item.changes or "Нет подробных данных"
        }
        return JsonResponse(data)