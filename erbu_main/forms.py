from django import forms
from .models import (
    Student, Passport, DisabilityInfo, Mse, Pmpk, Parent,
    EducationEnded, EducationProcess, EducationTarget, Employment,
    EducationInstitution
)
from django.forms import inlineformset_factory


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'first_name', 'middle_name', 'last_name', 'status', 'sex',
            'email', 'phone', 'birthday', 'snils', 'inn'
        ]
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'}),
        }
        # Убрали responsible_persons из fields, так как это поле не нужно в форме


class PassportForm(forms.ModelForm):
    class Meta:
        model = Passport
        fields = [
            'series', 'number', 'issued', 'date_issued',
            'department_code', 'place_birth', 'place_resident'
        ]
        widgets = {
            'date_issued': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем все поля необязательными
        for field in self.fields.values():
            field.required = False


class DisabilityForm(forms.ModelForm):
    class Meta:
        model = DisabilityInfo
        fields = [
            'status_ovz', 'disability_group', 'nosology_type', 'year_removal'
        ]
        widgets = {
            'year_removal': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем все поля необязательными
        for field in self.fields.values():
            field.required = False


class MseForm(forms.ModelForm):
    class Meta:
        model = Mse
        fields = [
            'series', 'number', 'date_issued', 'date_next_examination'
        ]
        widgets = {
            'date_issued': forms.DateInput(attrs={'type': 'date'}),
            'date_next_examination': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем все поля необязательными
        for field in self.fields.values():
            field.required = False


class PmpkForm(forms.ModelForm):
    class Meta:
        model = Pmpk
        fields = [
            'number', 'date_issued', 'education_programm_pmpk'
        ]
        widgets = {
            'date_issued': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем все поля необязательными
        for field in self.fields.values():
            field.required = False


class EducationInstitutionForm(forms.ModelForm):
    """Форма для учебного заведения"""

    class Meta:
        model = EducationInstitution
        fields = ['name']


# Форма для родителя (без FK к студенту)
class ParentForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = [
            'first_name', 'middle_name', 'last_name', 'phone', 'email'
        ]


# Форма для оконченного образования
class EducationEndedForm(forms.ModelForm):
    class Meta:
        model = EducationEnded
        fields = [
            'education_type', 'name', 'education_document',
            'series', 'date_issued'
        ]
        widgets = {
            'date_issued': forms.DateInput(attrs={'type': 'date'}),
        }


# Форма для текущего образования
class EducationProcessForm(forms.ModelForm):
    class Meta:
        model = EducationProcess
        fields = [
            'education_institution', 'profession', 'course',
            'form', 'term', 'grad_date'
        ]
        widgets = {
            'grad_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Если пользователь - учитель, ограничиваем выбор учреждения
        if self.user and hasattr(self.user, 'role') and self.user.role == 'TEACHER':
            if hasattr(self.user, 'education_institution'):
                self.fields['education_institution'].queryset = EducationInstitution.objects.filter(
                    pk=self.user.education_institution.pk
                )
                self.fields['education_institution'].initial = self.user.education_institution
                self.fields['education_institution'].widget.attrs['readonly'] = True


# Форма для целевого образования
class EducationTargetForm(forms.ModelForm):
    class Meta:
        model = EducationTarget
        fields = [
            'agreement', 'name_organization', 'abilimpiks'
        ]


# Форма для трудоустройства
class EmploymentForm(forms.ModelForm):
    class Meta:
        model = Employment
        fields = [
            'employment_status', 'place_job', 'position',
            'hiring_date', 'reason_not_employment',
            'accounting_employment', 'resume_status'
        ]
        widgets = {
            'hiring_date': forms.DateInput(attrs={'type': 'date'}),
        }


# Formsets
ParentFormSet = inlineformset_factory(
    Student, Parent,
    form=ParentForm,
    fields=['first_name', 'middle_name', 'last_name', 'phone', 'email'],
    extra=1,
    can_delete=True
)

EducationEndedFormSet = inlineformset_factory(
    Student, EducationEnded,
    form=EducationEndedForm,
    fields=['education_type', 'name', 'education_document', 'series', 'date_issued'],
    extra=1,
    can_delete=True
)

EducationProcessFormSet = inlineformset_factory(
    Student, EducationProcess,
    form=EducationProcessForm,
    fields=['education_institution', 'profession', 'course', 'form', 'term', 'grad_date'],
    extra=1,
    can_delete=True
)

EducationTargetFormSet = inlineformset_factory(
    Student, EducationTarget,
    form=EducationTargetForm,
    fields=['agreement', 'name_organization', 'abilimpiks'],
    extra=1,
    can_delete=True
)

EmploymentFormSet = inlineformset_factory(
    Student, Employment,
    form=EmploymentForm,
    fields=['employment_status', 'place_job', 'position', 'hiring_date',
            'reason_not_employment', 'accounting_employment', 'resume_status'],
    extra=1,
    can_delete=True
)