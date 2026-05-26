from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from erbu_main.models import EducationInstitution


class InstitutionLastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Проверяем, что пользователь авторизован и у него роль TEACHER
        if request.user.is_authenticated and getattr(request.user, 'role', None) == 'TEACHER':
            institution = getattr(request.user, 'education_institution', None)
            if institution:
                # Обновляем время последней активности учреждения (без изменения auto_now полей в базе)
                EducationInstitution.objects.filter(pk=institution.pk).update(last_seen=timezone.now())

        response = self.get_response(request)
        return response

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Имя URL-схемы вашей страницы авторизации (проверьте, как она называется в urls.py)
        login_url = reverse('login')

        # Если пользователь НЕ авторизован И пытается зайти НЕ на страницу логина
        if not request.user.is_authenticated and request.path != login_url:
            # Исключаем также запросы к админке Django и статике/медиа, чтобы не сломать стили на форме логина
            if not request.path.startswith('/admin/') and not request.path.startswith('/static/'):
                return redirect(login_url)

        response = self.get_response(request)
        return response