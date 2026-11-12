from .models import StudentLog

# Сколько последних записей журнала показывать в выпадающем списке уведомлений
ADMIN_LOGS_LIMIT = 30


def admin_notifications(request):
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated and getattr(user, 'role', None) == 'ADMIN':
        return {
            'admin_logs': StudentLog.objects.select_related('user')[:ADMIN_LOGS_LIMIT],
            'unread_count': StudentLog.objects.filter(is_read=False).count(),
        }
    return {'admin_logs': [], 'unread_count': 0}
