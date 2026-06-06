from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from erbu_main.models import EducationInstitution


class InstitutionLastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(request.user, 'role', None) == 'TEACHER':
            institution = getattr(request.user, 'education_institution', None)
            if institution:
                EducationInstitution.objects.filter(pk=institution.pk).update(last_seen=timezone.now())

        response = self.get_response(request)
        return response


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Получаем URL страницы логина (обычно '/login/' или '/accounts/login/')
        login_url = reverse('login')

        # 1. Если пользователь уже авторизован, сразу пропускаем запрос дальше
        if request.user.is_authenticated:
            return self.get_response(request)

        # 2. Если пользователь НЕ авторизован, проверяем, куда он пытается зайти.
        # Исключаем страницу логина, админку, статику и медиа из проверки, чтобы не было зацикливания.
        if (
            request.path == login_url
            or request.path.startswith('/admin/')
            or request.path.startswith('/static/')
            or request.path.startswith('/media/')
        ):
            return self.get_response(request)

        # 3. Во всех остальных случаях неавторизованного пользователя отправляем на логин
        return redirect(login_url)