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
        # Имя URL-схемы вашей страницы авторизации
        login_url = reverse('login')

        # Если пользователь уже залогинен,middleware вообще ничего не должен блокировать
        if request.user.is_authenticated:
            return self.get_response(request)

        # Список путей-исключений, которые НЕЛЬЗЯ перенаправлять на логин
        # Добавляем сюда проверку на саму страницу логина, админку, статику и медиафайлы
        if (
            request.path == login_url
            or request.path.startswith('/admin/')
            or request.path.startswith('/static/')
            or request.path.startswith('/media/')
        ):
            return self.get_response(request)

        # Во всех остальных случаях неавторизованного пользователя отправляем на логин
        return redirect(login_url)