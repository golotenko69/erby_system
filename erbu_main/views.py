import openpyxl
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from erbu_main.forms import (
    DisabilityForm, EducationEndedForm, EducationInstitutionForm, EducationProcessForm,
    EducationTargetForm, EmploymentForm, MseForm, ParentFormSet, PassportForm, PmpkForm, StudentForm,
)
from erbu_main.mixins import AdminRequiredMixin, TeacherRequiredMixin
from erbu_main.models import EducationInstitution, EducationProcess, Student, StudentLog
from erbu_main.utils import format_term, generate_random_string, generate_unique_username
from users.forms import CustomUserCreationForm

User = get_user_model()


def students_for_user(user):
    """Студенты, доступные пользователю: администратору — все, ответственному — своего заведения."""
    role = getattr(user, 'role', None)
    if role == 'ADMIN':
        return Student.objects.all()
    if role == 'TEACHER' and user.education_institution_id:
        return Student.objects.filter(
            education_process__education_institution_id=user.education_institution_id
        )
    return Student.objects.none()


def log_student_action(user, action, student, changes=None):
    """Запись в журнал изменений студентов (уведомления администратора)."""
    institution = getattr(user, 'education_institution', None)
    StudentLog.objects.create(
        action=action,
        student_name=f"{student.last_name or ''} {student.first_name} {student.middle_name or ''}".strip(),
        user=user,
        institution_name=institution.name if institution else "Администрация",
        changes=changes,
    )


@require_POST
def mark_logs_read(request):
    """Фоновая функция для сброса счётчика уведомлений."""
    if getattr(request.user, 'role', None) != 'ADMIN':
        return JsonResponse({'status': 'error'}, status=403)
    StudentLog.objects.filter(is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})


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
        return (
            students_for_user(self.request.user)
            .select_related('disability_info')
            .order_by('last_name', 'first_name', 'pk')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Выбор учебных заведений при экспорте доступен только администратору
        if getattr(self.request.user, 'role', None) == 'ADMIN':
            context['export_institutions'] = EducationInstitution.objects.order_by('name')
        return context


class StudentFormsMixin:
    """Общая логика создания/редактирования студента со всеми вложенными формами."""

    FORM_CLASSES = {
        'passport_form': (PassportForm, 'passport'),
        'disability_form': (DisabilityForm, 'disability'),
        'mse_form': (MseForm, 'mse'),
        'pmpk_form': (PmpkForm, 'pmpk'),
        'edu_end_form': (EducationEndedForm, 'edu_end'),
        'edu_proc_form': (EducationProcessForm, 'edu_proc'),
        'edu_tar_form': (EducationTargetForm, 'edu_tar'),
        'employment_form': (EmploymentForm, 'employment'),
    }

    def get_related_instances(self, student):
        """Существующие связанные объекты студента (None — если их ещё нет)."""
        if student is None or student.pk is None:
            return {}
        disability = getattr(student, 'disability_info', None)
        return {
            'passport_form': getattr(student, 'passport', None),
            'disability_form': disability,
            'mse_form': getattr(disability, 'mse', None) if disability else None,
            'pmpk_form': getattr(disability, 'pmpk', None) if disability else None,
            'edu_end_form': getattr(student, 'education_ended', None),
            'edu_proc_form': getattr(student, 'education_process', None),
            'edu_tar_form': getattr(student, 'education_target', None),
            'employment_form': getattr(student, 'employment', None),
        }

    def build_related_forms(self, student=None):
        data = self.request.POST if self.request.method == 'POST' else None
        instances = self.get_related_instances(student)
        forms = {}
        for name, (form_class, prefix) in self.FORM_CLASSES.items():
            kwargs = {'prefix': prefix, 'instance': instances.get(name)}
            if form_class is EducationProcessForm:
                kwargs['user'] = self.request.user
            forms[name] = form_class(data, **kwargs)
        forms['parent_formset'] = ParentFormSet(
            data, instance=student if student is not None else Student(), prefix='parent'
        )
        return forms

    def get_context_data(self, **kwargs):
        related_forms = kwargs.pop('related_forms', None)
        context = super().get_context_data(**kwargs)
        if related_forms is None:
            related_forms = self.build_related_forms(getattr(self, 'object', None))
        context.update(related_forms)
        return context

    @staticmethod
    def all_valid(form, related_forms):
        # Валидируем все формы (без короткого замыкания), чтобы показать все ошибки сразу
        results = [form.is_valid()] + [f.is_valid() for f in related_forms.values()]
        return all(results)

    def save_related(self, student, forms):
        """Сохраняет все связанные с студентом объекты."""
        for name in ('passport_form', 'edu_end_form', 'edu_tar_form', 'employment_form'):
            obj = forms[name].save(commit=False)
            obj.student = student
            obj.save()

        education_process = forms['edu_proc_form'].save(commit=False)
        education_process.student = student
        if self.request.user.role == 'TEACHER':
            # Ответственное лицо может добавлять студентов только в своё учреждение
            education_process.education_institution = self.request.user.education_institution
        education_process.save()

        disability_form = forms['disability_form']
        disability = disability_form.save(commit=False)
        disability.student = student
        disability.save()

        # МСЭ хранится только при наличии инвалидности, ПМПК — только при статусе ОВЗ
        for form_name, flag_field, related in (
            ('mse_form', 'has_disability', 'mse'),
            ('pmpk_form', 'status_ovz', 'pmpk'),
        ):
            if disability_form.cleaned_data.get(flag_field) == 'Да':
                obj = forms[form_name].save(commit=False)
                obj.disability = disability
                obj.save()
            elif forms[form_name].instance.pk:
                forms[form_name].instance.delete()

        parent_formset = forms['parent_formset']
        parent_formset.instance = student
        parent_formset.save()


class StudentCreateView(TeacherRequiredMixin, StudentFormsMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'erbu_main/students/students_form.html'

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        related_forms = self.build_related_forms()

        if not self.all_valid(form, related_forms):
            return self.render_to_response(self.get_context_data(form=form, related_forms=related_forms))

        with transaction.atomic():
            student = form.save()
            self.save_related(student, related_forms)
            log_student_action(request.user, 'CREATE', student)

        messages.success(request, f"Студент '{student.first_name} {student.last_name}' успешно создан!")
        return redirect('student_detail', student_id=student.pk)


class StudentDeleteView(TeacherRequiredMixin, DeleteView):
    model = Student
    template_name = 'erbu_main/students/student_confirm_delete.html'
    success_url = reverse_lazy('students')
    pk_url_kwarg = 'student_id'

    def get_queryset(self):
        # Ответственное лицо может удалять только студентов своего учреждения
        return students_for_user(self.request.user)

    def form_valid(self, form):
        student = self.object
        with transaction.atomic():
            log_student_action(self.request.user, 'DELETE', student)
            response = super().form_valid(form)
        messages.success(self.request, f"Студент '{student.first_name} {student.last_name}' успешно удален!")
        return response


class StudentDetailView(TeacherRequiredMixin, DetailView):
    model = Student
    template_name = 'erbu_main/students/student_detail.html'
    context_object_name = 'student'
    pk_url_kwarg = 'student_id'

    def get_queryset(self):
        # Ответственное лицо видит только студентов своего учреждения
        return students_for_user(self.request.user).select_related(
            'passport', 'disability_info', 'disability_info__mse', 'disability_info__pmpk',
            'education_ended', 'education_process', 'education_process__education_institution',
            'education_target', 'employment',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object

        disability = getattr(student, 'disability_info', None)
        context['passport'] = getattr(student, 'passport', None)
        context['disability'] = disability
        context['mse'] = getattr(disability, 'mse', None) if disability else None
        context['pmpk'] = getattr(disability, 'pmpk', None) if disability else None

        education_process = getattr(student, 'education_process', None)
        if education_process and education_process.term:
            education_process.term_display = format_term(education_process.term)
        context['education_ended'] = getattr(student, 'education_ended', None)
        context['education_process'] = education_process
        context['education_target'] = getattr(student, 'education_target', None)
        context['parents'] = student.parents.all()
        context['employment'] = getattr(student, 'employment', None)
        return context


class SignUpView(AdminRequiredMixin, CreateView):
    """Создание учётной записи. Доступно только администратору:
    форма позволяет выбрать роль, в том числе «Администратор»."""
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('index')
    template_name = 'registration/signup.html'


class EducationInstitutionListView(AdminRequiredMixin, ListView):
    """Список всех учебных заведений"""
    model = EducationInstitution
    template_name = 'erbu_main/educations/institution_list.html'
    context_object_name = 'institutions'
    paginate_by = 20

    def get_queryset(self):
        today_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        return EducationInstitution.objects.annotate(
            student_count=Count('students__student', distinct=True),
            students_added_today=Count(
                'students__student', filter=Q(students__created_at__gte=today_start), distinct=True
            ),
        ).order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = True  # представление доступно только администратору

        institutions = list(context['institutions'])
        teachers = {}
        for teacher in User.objects.filter(
            education_institution__in=institutions, role='TEACHER'
        ).order_by('pk'):
            teachers.setdefault(teacher.education_institution_id, teacher)

        for institution in institutions:
            institution.teacher = teachers.get(institution.pk)
            # Последние добавленные студенты для вывода времени
            institution.recent_additions = (
                EducationProcess.objects.filter(education_institution=institution)
                .select_related('student').order_by('-created_at')[:3]
            )
        context['institutions'] = institutions
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
        ).order_by('pk').first()

        # Получаем всех студентов, обучающихся в этом учреждении
        education_processes = EducationProcess.objects.filter(
            education_institution=institution
        ).select_related('student').order_by('student__last_name', 'student__first_name')

        # Группируем по курсам
        students_by_course = {1: [], 2: [], 3: [], 4: []}
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
        context['professions'] = (
            education_processes.exclude(profession__isnull=True).exclude(profession='')
            .order_by('profession').values_list('profession', flat=True).distinct()
        )
        return context


class EducationInstitutionCreateView(AdminRequiredMixin, CreateView):
    """Создание нового учебного заведения и пользователя-учителя"""
    model = EducationInstitution
    form_class = EducationInstitutionForm
    template_name = 'erbu_main/educations/institution_form.html'

    def get_success_url(self):
        return reverse_lazy('institution_detail', kwargs={'institution_id': self.object.pk})

    def form_valid(self, form):
        username = generate_unique_username()
        password = generate_random_string(12)

        with transaction.atomic():
            response = super().form_valid(form)
            User.objects.create_user(
                username=username,
                password=password,
                first_name=form.cleaned_data['teacher_first_name'],
                last_name=form.cleaned_data['teacher_last_name'],
                middle_name=form.cleaned_data.get('teacher_middle_name', ''),
                email=form.cleaned_data['teacher_email'],
                phone=form.cleaned_data['teacher_phone'],
                role='TEACHER',
                education_institution=self.object,
            )

        # Пароль не хранится в открытом виде — показываем его администратору один раз
        messages.success(
            self.request,
            f"Учреждение '{self.object.name}' и ответственный успешно созданы. "
            f"Логин: {username}, пароль: {password}. Сохраните пароль — повторно он показан не будет."
        )
        return response


class ResetTeacherPasswordView(AdminRequiredMixin, View):
    """Генерирует новый пароль ответственного лица и показывает его администратору один раз."""

    def post(self, request, institution_id):
        institution = get_object_or_404(EducationInstitution, pk=institution_id)
        teacher = User.objects.filter(
            education_institution=institution, role='TEACHER'
        ).order_by('pk').first()
        if teacher is None:
            messages.error(request, "У учреждения нет ответственного лица.")
            return redirect('institution_detail', institution_id=institution.pk)

        password = generate_random_string(12)
        teacher.set_password(password)
        teacher.save(update_fields=['password'])
        messages.success(
            request,
            f"Новый пароль для {teacher.username}: {password}. Сохраните его — повторно он показан не будет."
        )
        return redirect('institution_detail', institution_id=institution.pk)


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

    def students_count(self):
        return EducationProcess.objects.filter(
            education_institution=self.object
        ).values('student').distinct().count()

    def get_context_data(self, **kwargs):
        """Передаем количество студентов в контекст шаблона для динамического UI"""
        context = super().get_context_data(**kwargs)
        context['students_count'] = self.students_count()
        return context

    def form_valid(self, form):
        institution = self.object
        students_count = self.students_count()
        if students_count > 0:
            messages.error(
                self.request,
                f"Ошибка! Невозможно удалить учреждение '{institution.name}', "
                f"так как в нём обучается студентов: {students_count}."
            )
            return redirect('institution_detail', institution_id=institution.pk)

        with transaction.atomic():
            # Блокируем учётные записи сотрудников, чтобы они не могли войти
            User.objects.filter(education_institution=institution, role='TEACHER').update(
                is_active=False, education_institution=None
            )
            response = super().form_valid(form)

        messages.success(
            self.request,
            f"Учебное заведение '{institution.name}' успешно удалено. Связанные аккаунты сотрудников заблокированы."
        )
        return response


class StudentFullEditView(TeacherRequiredMixin, StudentFormsMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'erbu_main/students/students_form.html'
    pk_url_kwarg = 'student_id'

    FIELD_LABELS = {
        'status': 'Статус', 'phone': 'Телефон', 'email': 'Email',
        'education_type': 'Тип оконч. образования', 'education_document': 'Документ оконч. образования',
        'agreement': 'Целевой договор', 'abilimpiks': 'Участие в Абилимпикс',
        'employment_status': 'Трудоустроен', 'accounting_employment': 'Состоит в ЦЗН',
        'resume_status': 'Резюме создано'
    }

    def get_queryset(self):
        # Ответственное лицо может редактировать только студентов своего учреждения
        return students_for_user(self.request.user)

    def collect_changes(self, form, related_forms):
        """Описание изменений ключевых полей для журнала (сравниваем с данными из БД)."""
        old_student = Student.objects.get(pk=self.object.pk)
        old_related = self.get_related_instances(old_student)
        changes = []

        def check(form_obj, old_obj, fields):
            if old_obj is None:
                return
            for field in fields:
                if field not in form_obj.cleaned_data:
                    continue
                new_val = form_obj.cleaned_data[field]
                old_val = getattr(old_obj, field, None)
                choices = getattr(form_obj.fields[field], 'choices', None)
                if choices and new_val:
                    new_val = dict(choices).get(new_val, new_val)
                if hasattr(old_obj, f'get_{field}_display'):
                    old_val = getattr(old_obj, f'get_{field}_display')()
                if str(old_val or '') != str(new_val or ''):
                    label = self.FIELD_LABELS.get(field, field)
                    changes.append(f"• {label}: «{old_val or 'нет'}» ➔ «{new_val or 'нет'}»")

        check(form, old_student, ['status', 'phone', 'email'])
        check(related_forms['edu_end_form'], old_related.get('edu_end_form'), ['education_type', 'education_document'])
        check(related_forms['edu_tar_form'], old_related.get('edu_tar_form'), ['agreement', 'abilimpiks'])
        check(related_forms['employment_form'], old_related.get('employment_form'),
              ['employment_status', 'accounting_employment', 'resume_status'])
        return changes

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        related_forms = self.build_related_forms(self.object)

        if not self.all_valid(form, related_forms):
            return self.render_to_response(self.get_context_data(form=form, related_forms=related_forms))

        changes = self.collect_changes(form, related_forms)
        with transaction.atomic():
            student = form.save()
            self.save_related(student, related_forms)
            log_student_action(
                request.user, 'UPDATE', student,
                changes="\n".join(changes) if changes else "Существенных изменений в ключевых полях нет.",
            )

        messages.success(request, "Студент успешно сохранен")
        return redirect('student_detail', student_id=student.pk)


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
        if getattr(request.user, 'role', None) == 'ADMIN':
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

        if not queryset.exists():
            messages.warning(request, 'По выбранным учебным заведениям студентов не найдено, отчёт не сформирован.')
            return redirect('students')

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
        if getattr(request.user, 'role', None) != 'ADMIN':
            return JsonResponse({'error': 'Доступ запрещен'}, status=403)

        log_item = get_object_or_404(StudentLog.objects.select_related('user'), pk=log_id)

        data = {
            'action_display': log_item.get_action_display(),
            'student_name': log_item.student_name,
            'user': f"{log_item.user.last_name or ''} {log_item.user.first_name or ''}".strip() if log_item.user else "Система",
            'institution': log_item.institution_name or "Не указано",
            'date': timezone.localtime(log_item.created_at).strftime('%d.%m.%Y в %H:%M'),
            'changes': log_item.changes or "Нет подробных данных"
        }
        return JsonResponse(data)