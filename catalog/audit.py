from accounts.models import User

from .models import AuditLog


def log_action(request, action, description, via_django_admin=False):
    """
    Registra una acción del administrador en el log de auditoría.

    Se llama justo después de que la acción tuvo éxito, en la misma petición,
    así que el registro queda guardado de forma inmediata.

    - Desde las vistas de la app, el admin se identifica por la sesión (`user_id`).
    - Desde el panel de Django (/admin/), el usuario es el de Django (`request.user`),
      que no es un `accounts.User`; por eso se guarda solo su nombre de usuario.
    """
    admin = None

    if via_django_admin:
        django_user = getattr(request, 'user', None)
        if django_user is not None and django_user.is_authenticated:
            admin_email = f'{django_user.get_username()} (Django admin)'
        else:
            admin_email = 'unknown (Django admin)'
    else:
        user_id = request.session.get('user_id')
        if user_id:
            admin = User.objects.filter(id=user_id).first()
        admin_email = admin.email if admin else 'unknown'

    return AuditLog.objects.create(
        admin=admin,
        admin_email=admin_email,
        action=action,
        description=description[:300],
    )
