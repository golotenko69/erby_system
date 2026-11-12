from datetime import timedelta

from django.contrib.auth.views import redirect_to_login
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from erbu_main.models import EducationInstitution

# Не чаще одного обновления «последний раз в сети» в минуту, чтобы не писать в БД на каждый запрос
LAST_SEEN_UPDATE_INTERVAL = timedelta(minutes=1)


class InstitutionLastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and getattr(user, 'role', None) == 'TEACHER' and user.education_institution_id:
            now = timezone.now()
            EducationInstitution.objects.filter(pk=user.education_institution_id).filter(
                Q(last_seen__isnull=True) | Q(last_seen__lt=now - LAST_SEEN_UPDATE_INTERVAL)
            ).update(last_seen=now)

        return self.get_response(request)


class LoginRequiredMiddleware:
    """Пускает неавторизованных пользователей только на страницу входа, в админку и к статике."""

    PUBLIC_PREFIXES = ('/admin/', '/static/', '/media/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            return self.get_response(request)

        login_url = reverse('login')
        if request.path == login_url or request.path.startswith(self.PUBLIC_PREFIXES):
            return self.get_response(request)

        # Сохраняем адрес, куда пользователь пытался попасть, чтобы вернуть его туда после входа
        return redirect_to_login(request.get_full_path(), login_url)

