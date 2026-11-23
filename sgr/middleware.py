"""Require authentication for public pages; leave /admin/, /login/ and static alone."""

from django.conf import settings
from django.shortcuts import redirect


class LoginRequiredMiddleware:
    """Redirect anonymous users to LOGIN_URL except for exempt prefixes."""

    def __init__(self, get_response):
        self.get_response = get_response
        raw = getattr(
            settings,
            'LOGIN_EXEMPT_URLS',
            ['/login/', '/logout/', '/admin/', '/static/'],
        )
        self.exempt = tuple(raw)

    def __call__(self, request):
        path = request.path
        if request.user.is_authenticated:
            return self.get_response(request)
        if any(path.startswith(prefix) for prefix in self.exempt):
            return self.get_response(request)
        return redirect(f"{settings.LOGIN_URL}?next={path}")
