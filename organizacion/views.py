from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from .forms import CargoForm, PersonaForm, UnidadForm
from .models import Cargo, Persona, Unidad


@permission_required("organizacion.view_unidad", raise_exception=True)
def lista_unidades(request):
    q = (request.GET.get("q") or "").strip()
    qs = Unidad.objects.all()
    if q:
        qs = qs.filter(
            Q(nombre__icontains=q)
            | Q(ambito__icontains=q)
            | Q(responsable__icontains=q)
            | Q(estado__icontains=q)
        )
    return render(
        request,
        "organizacion/lista_unidades.html",
        {"unidades": qs, "q": q},
    )


@permission_required("organizacion.view_unidad", raise_exception=True)
def detalle_unidad(request, unidad_id):
    unidad = get_object_or_404(Unidad, pk=unidad_id)
    personas = Persona.objects.filter(delegacion=unidad).select_related("cargo")
    return render(
        request,
        "organizacion/detalle_unidad.html",
        {"unidad": unidad, "personas": personas},
    )


@permission_required("organizacion.view_persona", raise_exception=True)
def lista_personas(request):
    q = (request.GET.get("q") or "").strip()
    qs = Persona.objects.select_related("cargo", "delegacion")
    if q:
        qs = qs.filter(
            Q(nombre__icontains=q)
            | Q(estado__icontains=q)
            | Q(cargo__nombre__icontains=q)
            | Q(delegacion__nombre__icontains=q)
        )
    return render(
        request,
        "organizacion/lista_personas.html",
        {"personas": qs, "q": q},
    )


@permission_required("organizacion.view_persona", raise_exception=True)
def detalle_persona(request, persona_id):
    persona = get_object_or_404(
        Persona.objects.select_related("cargo", "delegacion"), pk=persona_id
    )
    return render(request, "organizacion/detalle_persona.html", {"persona": persona})


class UnidadCreateView(PermissionRequiredMixin, CreateView):
    model = Unidad
    form_class = UnidadForm
    template_name = "crud/formulario.html"
    permission_required = "organizacion.add_unidad"
    success_url = reverse_lazy("lista_unidades")
    raise_exception = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Nueva delegación", "volver_url": reverse_lazy("lista_unidades")})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Delegación creada correctamente.")
        return super().form_valid(form)


class UnidadUpdateView(PermissionRequiredMixin, UpdateView):
    model = Unidad
    form_class = UnidadForm
    template_name = "crud/formulario.html"
    permission_required = "organizacion.change_unidad"
    success_url = reverse_lazy("lista_unidades")
    raise_exception = True
    pk_url_kwarg = "unidad_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Editar delegación", "volver_url": reverse_lazy("lista_unidades")})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Delegación actualizada correctamente.")
        return super().form_valid(form)


class UnidadDeleteView(PermissionRequiredMixin, DeleteView):
    model = Unidad
    template_name = "crud/confirmar_borrar.html"
    permission_required = "organizacion.delete_unidad"
    success_url = reverse_lazy("lista_unidades")
    raise_exception = True
    pk_url_kwarg = "unidad_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "titulo": "Eliminar delegación",
                "objeto_etiqueta": str(self.object),
                "volver_url": reverse_lazy("lista_unidades"),
            }
        )
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Delegación eliminada correctamente.")
        return super().form_valid(form)


class PersonaCreateView(PermissionRequiredMixin, CreateView):
    model = Persona
    form_class = PersonaForm
    template_name = "crud/formulario.html"
    permission_required = "organizacion.add_persona"
    success_url = reverse_lazy("lista_personas")
    raise_exception = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Nuevo funcionario", "volver_url": reverse_lazy("lista_personas")})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Funcionario creado correctamente.")
        return super().form_valid(form)


class PersonaUpdateView(PermissionRequiredMixin, UpdateView):
    model = Persona
    form_class = PersonaForm
    template_name = "crud/formulario.html"
    permission_required = "organizacion.change_persona"
    success_url = reverse_lazy("lista_personas")
    raise_exception = True
    pk_url_kwarg = "persona_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Editar funcionario", "volver_url": reverse_lazy("lista_personas")})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Funcionario actualizado correctamente.")
        return super().form_valid(form)


class PersonaDeleteView(PermissionRequiredMixin, DeleteView):
    model = Persona
    template_name = "crud/confirmar_borrar.html"
    permission_required = "organizacion.delete_persona"
    success_url = reverse_lazy("lista_personas")
    raise_exception = True
    pk_url_kwarg = "persona_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "titulo": "Eliminar funcionario",
                "objeto_etiqueta": str(self.object),
                "volver_url": reverse_lazy("lista_personas"),
            }
        )
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Funcionario eliminado correctamente.")
        return super().form_valid(form)


class CargoCreateView(PermissionRequiredMixin, CreateView):
    model = Cargo
    form_class = CargoForm
    template_name = "crud/formulario.html"
    permission_required = "organizacion.add_cargo"
    success_url = reverse_lazy("lista_personas")
    raise_exception = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Nuevo cargo", "volver_url": reverse_lazy("lista_personas")})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Cargo creado correctamente.")
        return super().form_valid(form)
