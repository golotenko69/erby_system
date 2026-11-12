from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'role')

    list_filter = UserAdmin.list_filter + ('role',)
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительные поля', {'fields': ('role', 'education_institution', 'middle_name', 'phone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {'fields': ('role', 'education_institution')}),)

admin.site.register(CustomUser, CustomUserAdmin)
