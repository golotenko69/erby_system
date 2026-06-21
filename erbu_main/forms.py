from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from .models import (
    Student, Passport, DisabilityInfo, Mse, Pmpk, Parent,
    EducationEnded, EducationProcess, EducationTarget, Employment,
    EducationInstitution
)
from django.forms import inlineformset_factory

# ================= ВАЛИДАТОРЫ ДЛЯ ПОЛЕЙ РФ =================

# Паспорт РФ: Серия — строго 4 цифры
passport_series_validator = RegexValidator(
    regex=r'^\d{4}$',
    message="Серия паспорта должна состоять ровно из 4 цифр."
)

# Паспорт РФ: Номер — строго 6 цифр
passport_number_validator = RegexValidator(
    regex=r'^\d{6}$',
    message="Номер паспорта должен состоять ровно из 6 цифр."
)

# Код подразделения: формат 123-456
department_code_validator = RegexValidator(
    regex=r'^\d{3}-\d{3}$',
    message="Код подразделения должен быть в формате ХХХ-ХХХ (6 цифр и дефис)."
)

# ИНН: 12 цифр для физлиц
inn_validator = RegexValidator(
    regex=r'^\d{12}$',
    message="ИНН физического лица должен состоять ровно из 12 цифр."
)

# Телефон: российский формат (+7 или 8 и 10 цифр)
phone_validator = RegexValidator(
    regex=r'^(?:\+7|8)\d{10}$',
    message="Номер телефона должен быть в формате +79991234567 или 89991234567."
)

# ФИО: только буквы, дефисы и пробелы (защита от случайных цифр и символов)
name_validator = RegexValidator(
    regex=r'^[А-Яа-яЁё\s\-]+$',
    message="Поле должно содержать только буквы русского алфавита, пробелы или дефисы."
)


class StudentForm(forms.ModelForm):
    # Явно указываем required=True для текстовых полей
    first_name = forms.CharField(label="Имя", validators=[name_validator], required=True)
    middle_name = forms.CharField(label="Отчество", validators=[name_validator], required=True)
    last_name = forms.CharField(label="Фамилия", validators=[name_validator], required=True)
    phone = forms.CharField(label="Телефон", validators=[phone_validator], required=True)
    inn = forms.CharField(label="ИНН", validators=[inn_validator], required=True)
    email = forms.EmailField(label="Email", required=True)

    class Meta:
        model = Student
        fields = [
            'first_name', 'middle_name', 'last_name', 'status', 'sex',
            'email', 'phone', 'birthday', 'snils', 'inn'
        ]
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Автоматически делаем все остальные поля (status, sex, birthday, snils) обязательными
        for field_name in self.fields:
            self.fields[field_name].required = True

    def clean_snils(self):
        snils_raw = self.cleaned_data.get('snils')
        if not snils_raw:
            raise ValidationError("СНИЛС является обязательным полем.")
        snils_clean = ''.join(filter(str.isdigit, snils_raw))
        if len(snils_clean) != 11:
            raise ValidationError("СНИЛС должен содержать ровно 11 цифр.")
        return f"{snils_clean[:3]}-{snils_clean[3:6]}-{snils_clean[6:9]} {snils_clean[9:]}"

class PassportForm(forms.ModelForm):
    series = forms.CharField(label="Серия", validators=[passport_series_validator], required=True)
    number = forms.CharField(label="Номер", validators=[passport_number_validator], required=True)
    department_code = forms.CharField(label="Код подразделения", validators=[department_code_validator], required=True)

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
        # Делаем абсолютно все поля паспорта обязательными
        for field in self.fields.values():
            field.required = True

class ParentForm(forms.ModelForm):
    first_name = forms.CharField(label="Имя", validators=[name_validator], required=True)
    middle_name = forms.CharField(label="Отчество", validators=[name_validator], required=True)
    last_name = forms.CharField(label="Фамилия", validators=[name_validator], required=True)
    phone = forms.CharField(label="Телефон", validators=[phone_validator], required=True)
    email = forms.EmailField(label="Email", required=True)

    class Meta:
        model = Parent
        fields = ['first_name', 'middle_name', 'last_name', 'phone', 'email']


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
        labels = {
            'education_type': 'Уровень образования',  # Заменили название лейбла
            'name': 'Название учреждения',
            'education_document': 'Документ',
            'series': 'Серия/Номер',
            'date_issued': 'Дата выдачи',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True


class EducationProcessForm(forms.ModelForm):
    class Meta:
        model = EducationProcess
        fields = [
            'education_institution', 'profession', 'course',
            'form', 'term', 'grad_date'
        ]
        labels = {
            'education_institution': 'Название учреждения',
        }
        widgets = {
            'grad_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.required = True

        if self.user and getattr(self.user, 'role', None) == 'TEACHER':
            institution = getattr(self.user, 'education_institution', None)
            if institution:
                self.fields['education_institution'].queryset = EducationInstitution.objects.filter(pk=institution.pk)
                self.fields['education_institution'].initial = institution
                self.fields['education_institution'].widget.attrs['readonly'] = True
            else:
                self.fields['education_institution'].queryset = EducationInstitution.objects.none()
                self.fields['education_institution'].widget.attrs['disabled'] = True

# Оставляем остальные формы без изменений, так как они работают в связке
class DisabilityForm(forms.ModelForm):
    class Meta:
        model = DisabilityInfo
        fields = ['status_ovz', 'disability_group', 'nosology_type', 'year_removal']
        widgets = {'year_removal': forms.DateInput(attrs={'type': 'date'})}


class MseForm(forms.ModelForm):
    class Meta:
        model = Mse
        fields = ['series', 'number', 'date_issued', 'date_next_examination']
        widgets = {
            'date_issued': forms.DateInput(attrs={'type': 'date'}),
            'date_next_examination': forms.DateInput(attrs={'type': 'date'}),
        }


class PmpkForm(forms.ModelForm):
    class Meta:
        model = Pmpk
        fields = ['number', 'date_issued', 'education_programm_pmpk']
        widgets = {'date_issued': forms.DateInput(attrs={'type': 'date'})}


class EducationTargetForm(forms.ModelForm):
    class Meta:
        model = EducationTarget
        fields = ['agreement', 'name_organization', 'abilimpiks']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True


class EmploymentForm(forms.ModelForm):
    class Meta:
        model = Employment
        fields = [
            'employment_status', 'place_job', 'position', 'hiring_date',
            'reason_not_employment', 'accounting_employment', 'resume_status',
            'further_education_level', 'further_institution_name', 'further_grad_year'
        ]
        widgets = {
            'hiring_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Поля общего статуса всегда обязательны
        self.fields['employment_status'].required = True
        self.fields['accounting_employment'].required = True
        self.fields['resume_status'].required = True

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('employment_status')
        reason = cleaned_data.get('reason_not_employment')

        # Условная валидация в зависимости от выбора "Трудоустроен"
        if status == 'Да':
            if not cleaned_data.get('place_job'):
                self.add_error('place_job', 'При трудоустройстве это поле обязательно.')
            if not cleaned_data.get('position'):
                self.add_error('position', 'При трудоустройстве это поле обязательно.')
            if not cleaned_data.get('hiring_date'):
                self.add_error('hiring_date', 'При трудоустройстве это поле обязательно.')
        elif status == 'Нет':
            if not reason:
                self.add_error('reason_not_employment', 'Укажите причину нетрудоустройства.')

            # Если причина — продолжение обучения, требуем дополнительные окошки
            if reason == 'обучение':
                if not cleaned_data.get('further_education_level'):
                    self.add_error('further_education_level', 'Укажите уровень дальнейшего образования.')
                if not cleaned_data.get('further_institution_name'):
                    self.add_error('further_institution_name', 'Укажите наименование учреждения.')
                if not cleaned_data.get('further_grad_year'):
                    self.add_error('further_grad_year', 'Укажите год выпуска.')

        return cleaned_data

class EducationInstitutionForm(forms.ModelForm):
    teacher_last_name = forms.CharField(label='Фамилия ответственного', max_length=150, required=False,
                                        validators=[name_validator])
    teacher_first_name = forms.CharField(label='Имя ответственного', max_length=150, required=False,
                                         validators=[name_validator])
    teacher_middle_name = forms.CharField(label='Отчество ответственного', max_length=150, required=False,
                                          validators=[name_validator])
    teacher_phone = forms.CharField(label='Телефон ответственного', max_length=20, required=False,
                                    validators=[phone_validator])
    teacher_email = forms.EmailField(label='Почта ответственного', required=False)

    class Meta:
        model = EducationInstitution
        fields = ['name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['teacher_last_name'].required = True
            self.fields['teacher_first_name'].required = True
            self.fields['teacher_phone'].required = True
            self.fields['teacher_email'].required = True


ParentFormSet = inlineformset_factory(
    Student, Parent,
    form=ParentForm,
    fields=['first_name', 'middle_name', 'last_name', 'phone', 'email'],
    extra=1,
    can_delete=True
)