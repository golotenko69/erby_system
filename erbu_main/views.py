from django.db.models import Q
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.shortcuts import render, get_object_or_404
from django.shortcuts import render, redirect, get_object_or_404

from erbu_main.forms import StudentForm, PassportForm, DisabilityForm, MseForm, PmpkForm, ParentFormSet, \
    EducationEndedFormSet, EducationProcessFormSet, EmploymentFormSet, EducationTargetFormSet, EducationInstitutionForm
from erbu_main.mixins import TeacherRequiredMixin
from erbu_main.models import Student, EducationTarget, DisabilityInfo, EducationProcess, EducationInstitution
from users.forms import CustomUserCreationForm


# Create your views here.
def index_view(request):
    return render(request, 'erbu_main/index.html')

def about_view(request):
    return render(request, 'erbu_main/about.html')

def students_view(request):
    return render(request, 'erbu_main/students.html')

def contacts_view(request):
    return render(request, 'erbu_main/contacts.html')

class StudentsListView(ListView):
    model = Student
    template_name = 'erbu_main/students/students.html'
    context_object_name = 'students'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user

        if user.role == 'ADMIN':
            return Student.objects.all()

        if user.role == 'TEACHER':
            return Student.objects.filter(
                current_education__education_institution=user.education_institution
            ).distinct()

        return Student.objects.none()


class StudentCreateView(CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'erbu_main/students/students_form.html'
    success_url = reverse_lazy('students')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context['passport_form'] = PassportForm(self.request.POST)
            context['disability_form'] = DisabilityForm(self.request.POST)
            context['mse_form'] = MseForm(self.request.POST)
            context['pmpk_form'] = PmpkForm(self.request.POST)

            context['parent_formset'] = ParentFormSet(self.request.POST)
            context['edu_end_formset'] = EducationEndedFormSet(self.request.POST)
            context['edu_proc_formset'] = EducationProcessFormSet(
                self.request.POST,
                form_kwargs={'user': self.request.user}
            )
            context['edu_tar_formset'] = EducationTargetFormSet(self.request.POST)
            context['employment_formset'] = EmploymentFormSet(self.request.POST)
        else:
            context['passport_form'] = PassportForm()
            context['disability_form'] = DisabilityForm()
            context['mse_form'] = MseForm()
            context['pmpk_form'] = PmpkForm()

            context['parent_formset'] = ParentFormSet()
            context['edu_end_formset'] = EducationEndedFormSet()
            context['edu_proc_formset'] = EducationProcessFormSet(
                form_kwargs={'user': self.request.user}
            )
            context['edu_tar_formset'] = EducationTargetFormSet()
            context['employment_formset'] = EmploymentFormSet()

        return context

    def form_valid(self, form):
        context = self.get_context_data()

        passport_form = context['passport_form']
        disability_form = context['disability_form']
        mse_form = context['mse_form']
        pmpk_form = context['pmpk_form']

        parent_formset = context['parent_formset']
        edu_end_formset = context['edu_end_formset']
        edu_proc_formset = context['edu_proc_formset']
        edu_tar_formset = context['edu_tar_formset']
        employment_formset = context['employment_formset']

        # Проверяем валидность всех форм
        forms_valid = (
                form.is_valid() and
                passport_form.is_valid() and
                disability_form.is_valid() and
                mse_form.is_valid() and
                pmpk_form.is_valid() and
                parent_formset.is_valid() and
                edu_end_formset.is_valid() and
                edu_proc_formset.is_valid() and
                edu_tar_formset.is_valid() and
                employment_formset.is_valid()
        )

        if forms_valid:
            # Сохраняем студента
            student = form.save()

            # Сохраняем OneToOne поля
            passport = passport_form.save(commit=False)
            passport.student = student
            passport.save()

            disability = disability_form.save(commit=False)
            disability.student = student
            disability.save()

            mse = mse_form.save(commit=False)
            mse.disability = disability
            mse.save()

            pmpk = pmpk_form.save(commit=False)
            pmpk.disability = disability
            pmpk.save()

            # Сохраняем formsets
            parent_formset.instance = student
            parent_formset.save()

            edu_end_formset.instance = student
            edu_end_formset.save()

            edu_tar_formset.instance = student
            edu_tar_formset.save()

            employment_formset.instance = student
            employment_formset.save()

            # Особая логика для EducationProcess
            edu_proc_instances = edu_proc_formset.save(commit=False)
            for obj in edu_proc_instances:
                obj.student = student
                if self.request.user.role == 'TEACHER':
                    obj.education_institution = self.request.user.education_institution
                obj.save()
            edu_proc_formset.save_m2m()

            messages.success(
                self.request,
                f"Студент '{student.first_name} {student.last_name}' успешно создан!"
            )
            return redirect('student_detail', student_id=student.pk)

        return self.render_to_response(self.get_context_data(form=form))

class StudentUpdateView(UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'erby/students/student_form.html'
    success_url = reverse_lazy('students')

    def form_valid(self, form):
        messages.success(self.request, f"Студент '{form.instance.first_name} {form.instance.last_name}' успешно обновлен!")
        return super().form_valid(form)


class StudentDeleteView(DeleteView):
    model = Student
    template_name = 'erbu_main/students/student_confirm_delete.html'
    success_url = reverse_lazy('students')
    pk_url_kwarg = 'student_id'

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(self.request, f"Студент '{obj.first_name} {obj.last_name}' успешно удален!")
        return super().delete(request, *args, **kwargs)


class JournalView(TeacherRequiredMixin, ListView):
    template_name = 'erby/journal.html'

    def get(self, request, *args, **kwargs):
        education_id = kwargs.get('education_id')

        education = get_object_or_404(EducationTarget, pk=education_id)
        students = Student.objects.filter(
            EducationTarget=education
        ).order_by('last_name')

        journal_data = []
        for student in students:
            journal_data.append({
                'student': student,
            })

        context = {
            'education': education,
            'journal_data': journal_data,
        }

        return render(request, self.template_name, context)


class EducationDeleteView(DeleteView):
    model = EducationTarget
    template_name = 'erby/teachers/teacher_confirm_delete.html'
    success_url = reverse_lazy('teachers')
    pk_url_kwarg = 'education_id'

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(self.request, f"Учитель {obj.user.first_name} {obj.user.last_name} успешно удален!")
        return super().delete(request, *args, **kwargs)\





class StudentDetailView(DetailView):
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
        context['education_ended'] = student.education_history.all()
        context['education_process'] = student.current_education.select_related('education_institution').all()

        # Родители и трудоустройство
        context['parents'] = student.parents.all()
        context['employment'] = student.employment.all()

        return context

    def get_queryset(self):
        user = self.request.user

        if user.role == 'ADMIN':
            return Student.objects.all()

        return Student.objects.filter(
            Q(current_education__education_institution=user.education_institution) |
            Q(pk=self.kwargs.get('student_id'))
        ).distinct()

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'


class EducationInstitutionListView(ListView):
    """Список всех учебных заведений"""
    model = EducationInstitution
    template_name = 'erbu_main/educations/institution_list.html'
    context_object_name = 'institutions'
    paginate_by = 20

    def get_queryset(self):
        # Сортируем по названию
        return EducationInstitution.objects.all().order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем количество студентов в каждом учреждении
        for institution in context['institutions']:
            institution.student_count = EducationProcess.objects.filter(
                education_institution=institution
            ).values('student').distinct().count()
        return context


class EducationInstitutionDetailView(DetailView):
    """Детальная информация об учебном заведении"""
    model = EducationInstitution
    template_name = 'erbu_main/educations/institution_detail.html'
    context_object_name = 'institution'
    pk_url_kwarg = 'institution_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = self.object

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


class EducationInstitutionCreateView(CreateView):
    """Создание нового учебного заведения"""
    model = EducationInstitution
    form_class = EducationInstitutionForm
    template_name = 'erbu_main/educations/institution_form.html'
    success_url = reverse_lazy('institutions')

    def form_valid(self, form):
        messages.success(
            self.request,
            f"Учебное заведение '{form.instance.name}' успешно создано!"
        )
        return super().form_valid(form)


class EducationInstitutionUpdateView(UpdateView):
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


class EducationInstitutionDeleteView(DeleteView):
    """Удаление учебного заведения"""
    model = EducationInstitution
    template_name = 'erbu_main/educations/institution_confirm_delete.html'
    pk_url_kwarg = 'institution_id'
    success_url = reverse_lazy('institutions')

    def delete(self, request, *args, **kwargs):
        institution = self.get_object()
        # Проверяем, есть ли студенты в этом учреждении
        students_count = EducationProcess.objects.filter(
            education_institution=institution
        ).values('student').distinct().count()

        if students_count > 0:
            messages.error(
                request,
                f"Невозможно удалить учреждение '{institution.name}'. "
                f"В нём обучается {students_count} студентов."
            )
            return redirect('institution_detail', institution_id=institution.pk)

        messages.success(
            request,
            f"Учебное заведение '{institution.name}' успешно удалено!"
        )
        return super().delete(request, *args, **kwargs)


class StudentFullEditView(UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'erbu_main/students/students_form.html'
    pk_url_kwarg = 'student_id'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)

        # Проверка доступа для учителя
        if self.request.user.role == 'TEACHER':
            if not obj.current_education.filter(
                    education_institution=self.request.user.education_institution
            ).exists():
                raise HttpResponseForbidden("Нет доступа")

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object if self.object.pk else None

        if self.request.POST:
            context['passport_form'] = PassportForm(
                self.request.POST,
                instance=getattr(student, 'passport', None)
            )
            context['disability_form'] = DisabilityForm(
                self.request.POST,
                instance=getattr(student, 'disability_info', None)
            )

            # Для Mse и Pmpk нужно проверить существование disability
            disability = getattr(student, 'disability_info', None)
            mse_instance = disability.mse if disability and hasattr(disability, 'mse') else None
            pmpk_instance = disability.pmpk if disability and hasattr(disability, 'pmpk') else None

            context['mse_form'] = MseForm(self.request.POST, instance=mse_instance)
            context['pmpk_form'] = PmpkForm(self.request.POST, instance=pmpk_instance)

            context['parent_formset'] = ParentFormSet(self.request.POST, instance=student)
            context['edu_end_formset'] = EducationEndedFormSet(self.request.POST, instance=student)
            context['edu_proc_formset'] = EducationProcessFormSet(
                self.request.POST,
                instance=student,
                form_kwargs={'user': self.request.user}
            )
            context['edu_tar_formset'] = EducationTargetFormSet(self.request.POST, instance=student)
            context['employment_formset'] = EmploymentFormSet(self.request.POST, instance=student)
        else:
            # GET запрос - загружаем существующие данные
            disability = getattr(student, 'disability_info', None)
            mse_instance = disability.mse if disability and hasattr(disability, 'mse') else None
            pmpk_instance = disability.pmpk if disability and hasattr(disability, 'pmpk') else None

            context['passport_form'] = PassportForm(instance=getattr(student, 'passport', None))
            context['disability_form'] = DisabilityForm(instance=disability)
            context['mse_form'] = MseForm(instance=mse_instance)
            context['pmpk_form'] = PmpkForm(instance=pmpk_instance)

            context['parent_formset'] = ParentFormSet(instance=student)
            context['edu_end_formset'] = EducationEndedFormSet(instance=student)
            # В StudentCreateView и StudentFullEditView:
            context['edu_proc_formset'] = EducationProcessFormSet(
                self.request.POST if self.request.POST else None,
                instance=student if hasattr(self, 'object') and self.object.pk else None,
                form_kwargs={'user': self.request.user}
            )
            context['edu_tar_formset'] = EducationTargetFormSet(instance=student)
            context['employment_formset'] = EmploymentFormSet(instance=student)

        return context

    def form_valid(self, form):
        context = self.get_context_data()

        passport_form = context['passport_form']
        disability_form = context['disability_form']
        mse_form = context['mse_form']
        pmpk_form = context['pmpk_form']

        parent_formset = context['parent_formset']
        edu_end_formset = context['edu_end_formset']
        edu_proc_formset = context['edu_proc_formset']
        edu_tar_formset = context['edu_tar_formset']
        employment_formset = context['employment_formset']

        # Проверяем валидность всех форм
        forms_valid = (
                form.is_valid() and
                passport_form.is_valid() and
                disability_form.is_valid() and
                mse_form.is_valid() and
                pmpk_form.is_valid() and
                parent_formset.is_valid() and
                edu_end_formset.is_valid() and
                edu_proc_formset.is_valid() and
                edu_tar_formset.is_valid() and
                employment_formset.is_valid()
        )

        if forms_valid:
            # Сохраняем студента
            student = form.save()

            # Сохраняем OneToOne поля
            passport = passport_form.save(commit=False)
            passport.student = student
            passport.save()

            disability = disability_form.save(commit=False)
            disability.student = student
            disability.save()

            mse = mse_form.save(commit=False)
            mse.disability = disability
            mse.save()

            pmpk = pmpk_form.save(commit=False)
            pmpk.disability = disability
            pmpk.save()

            # Сохраняем formsets
            parent_formset.instance = student
            parent_formset.save()

            edu_end_formset.instance = student
            edu_end_formset.save()

            edu_tar_formset.instance = student
            edu_tar_formset.save()

            employment_formset.instance = student
            employment_formset.save()

            # Особая логика для EducationProcess
            edu_proc_instances = edu_proc_formset.save(commit=False)
            for obj in edu_proc_instances:
                obj.student = student
                if self.request.user.role == 'TEACHER':
                    obj.education_institution = self.request.user.education_institution
                obj.save()
            edu_proc_formset.save_m2m()

            messages.success(self.request, "Студент успешно сохранен")
            return redirect('student_detail', student_id=student.pk)

        # Если формы невалидны, показываем ошибки
        return self.render_to_response(self.get_context_data(form=form))