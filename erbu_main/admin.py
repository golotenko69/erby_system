from django.contrib import admin
from .models import Student, ResponsiblePerson

# Register your models here.
admin.site.register(Student)
admin.site.register(ResponsiblePerson)