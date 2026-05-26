from .models import StudentLog

def admin_notifications(request):
    if request.user.is_authenticated and getattr(request.user, 'role', None) == 'ADMIN':
        logs = StudentLog.objects.select_related('user').all()
        return {
            'admin_logs': logs,
            # Считаем только те, где is_read = False
            'unread_count': logs.filter(is_read=False).count()
        }
    return {'admin_logs': [], 'unread_count': 0}