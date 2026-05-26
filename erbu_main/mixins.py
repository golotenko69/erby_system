from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import ListView
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import logout
from users.models import CustomUser


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        # Проверяем, авторизован ли пользователь и является ли он админом
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', None) == 'ADMIN'


class TeacherRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user

        # Если не авторизован — сразу отказ
        if not user.is_authenticated:
            return False

        # Если это АДМИН — беспрепятственно пускаем
        if getattr(user, 'role', None) == 'ADMIN':
            return True

        # Если это УЧИТЕЛЬ — проверяем, что у него ЕСТЬ учебное заведение
        if getattr(user, 'role', None) == 'TEACHER':
            return user.education_institution is not None

        # Для всех остальных ролей доступ закрыт
        return False

    def handle_no_permission(self):
        user = self.request.user
        # Принудительно разлогиниваем ТОЛЬКО учителей, у которых удалили колледж
        if user.is_authenticated and getattr(user, 'role', None) == 'TEACHER' and not user.education_institution:
            logout(self.request)
            messages.error(self.request,
                           "Ваша учётная запись деактивирована, так как ваше учебное заведение было удалено.")
            return redirect('login')

        messages.error(self.request, "У вас нет прав для доступа к этой странице.")
        return redirect('login')