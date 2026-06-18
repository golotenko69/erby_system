from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
# Register your models here.

class CustomUserAdmin(UserAdmin):

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'role')

    fieldsets = UserAdmin.fieldsets + (('дополнительные поля', {'fields': ('role', 'education_institution')}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {'fields': ('role',)}),)

admin.site.register(CustomUser, CustomUserAdmin)
print('CustomUserAdmin registered successfully')
