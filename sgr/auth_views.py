"""Login and logout for the public SGR site (username + password)."""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.cache import never_cache


@method_decorator(never_cache, name='dispatch')
class LoginView(View):
    template_name = 'registration/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, self.template_name)

    def post(self, request):
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, 'Usuario o contraseña incorrectos.')
            return render(
                request,
                self.template_name,
                {'username': username},
                status=400,
            )
        if not user.is_active:
            messages.error(request, 'Esta cuenta está desactivada.')
            return render(
                request,
                self.template_name,
                {'username': username},
                status=400,
            )
        login(request, user)
        messages.success(request, f'Bienvenido/a, {user.get_username()}.')
        next_url = request.GET.get('next') or request.POST.get('next') or reverse('home')
        if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            next_url = reverse('home')
        return redirect(next_url)


@method_decorator(never_cache, name='dispatch')
class LogoutView(View):
    """Cerrar sesión únicamente mediante POST protegido por CSRF."""

    def post(self, request):
        return self._logout(request)

    def _logout(self, request):
        logout(request)
        messages.info(request, 'Sesión cerrada.')
        return redirect('login')
