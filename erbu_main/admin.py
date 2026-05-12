from django.contrib import admin
from .models import Student, ResponsiblePerson, EducationProcess, EducationEnded, Passport, Pmpk, Mse, Parent, \
    DisabilityInfo, EducationTarget, Employment, EducationInstitution

# Register your models here.
admin.site.register(Student)
admin.site.register(ResponsiblePerson)
admin.site.register(EducationProcess)
admin.site.register(EducationEnded)
admin.site.register(Passport)
admin.site.register(Pmpk)
admin.site.register(Mse)
admin.site.register(Parent)
admin.site.register(DisabilityInfo)
admin.site.register(EducationTarget)
admin.site.register(Employment)
admin.site.register(EducationInstitution)