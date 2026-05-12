from django.contrib.auth.mixins import AccessMixin

from users.models import CustomUser

class TeacherRequiredMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        # Обращаемся к классу Role, а не к полю role
        allowed_roles = [
            CustomUser.Role.TEACHER,
            CustomUser.Role.ADMIN,
        ]

        if request.user.role not in allowed_roles:
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

class AdminRequiredMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        allowed_roles = [
            CustomUser.Role.ADMIN,
        ]

        if request.user.role not in allowed_roles:
            return self.handle_no_permission()

        return super().handle_no_permission()