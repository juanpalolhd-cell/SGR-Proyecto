from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from .forms import ActividadForm, EvidenciaForm
from .models import Actividad, Evidencia


@permission_required("actividades.view_actividad", raise_exception=True)
def lista_actividades(request):
    q = (request.GET.get("q") or "").strip()
    qs = Actividad.objects.select_related("persona", "unidad")
    if q:
        qs = qs.filter(
            Q(codigo__icontains=q)
            | Q(descripcion__icontains=q)
            | Q(accion__icontains=q)
            | Q(contacto__icontains=q)
            | Q(item__icontains=q)
            | Q(estado__icontains=q)
            | Q(persona__nombre__icontains=q)
            | Q(unidad__nombre__icontains=q)
        )
    return render(
        request,
        "actividades/lista_actividades.html",
        {"actividades": qs, "q": q},
    )


@permission_required("actividades.view_actividad", raise_exception=True)
def detalle_actividad(request, actividad_id):
    actividad = get_object_or_404(
        Actividad.objects.select_related("persona", "unidad"), pk=actividad_id
    )
    evidencias = Evidencia.objects.filter(actividad=actividad)
    return render(
        request,
        "actividades/detalle_actividad.html",
        {"actividad": actividad, "evidencias": evidencias},
    )


@permission_required("actividades.view_evidencia", raise_exception=True)
def lista_evidencias(request):
    q = (request.GET.get("q") or "").strip()
    qs = Evidencia.objects.select_related("actividad")
    if q:
        qs = qs.filter(
            Q(codigo__icontains=q)
            | Q(autor__icontains=q)
            | Q(estado__icontains=q)
            | Q(observacion__icontains=q)
            | Q(actividad__codigo__icontains=q)
        )
    return render(
        request,
        "actividades/lista_evidencias.html",
        {"evidencias": qs, "q": q},
    )


@permission_required("actividades.view_evidencia", raise_exception=True)
def detalle_evidencia(request, evidencia_id):
    evidencia = get_object_or_404(
        Evidencia.objects.select_related("actividad"), pk=evidencia_id
    )
    return render(
        request,
        "actividades/detalle_evidencia.html",
        {"evidencia": evidencia, "actividad": evidencia.actividad},
    )


class ActividadCreateView(PermissionRequiredMixin, CreateView):
    model = Actividad
    form_class = ActividadForm
    template_name = "crud/formulario.html"
    permission_required = "actividades.add_actividad"
    success_url = reverse_lazy("lista_actividades")
    raise_exception = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Nueva actividad", "volver_url": reverse_lazy("lista_actividades")})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Actividad creada correctamente.")
        return super().form_valid(form)


class ActividadUpdateView(PermissionRequiredMixin, UpdateView):
    model = Actividad
    form_class = ActividadForm
    template_name = "crud/formulario.html"
    permission_required = "actividades.change_actividad"
    success_url = reverse_lazy("lista_actividades")
    raise_exception = True
    pk_url_kwarg = "actividad_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Editar actividad", "volver_url": reverse_lazy("lista_actividades")})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Actividad actualizada correctamente.")
        return super().form_valid(form)


class ActividadDeleteView(PermissionRequiredMixin, DeleteView):
    model = Actividad
    template_name = "crud/confirmar_borrar.html"
    permission_required = "actividades.delete_actividad"
    success_url = reverse_lazy("lista_actividades")
    raise_exception = True
    pk_url_kwarg = "actividad_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "titulo": "Eliminar actividad",
                "objeto_etiqueta": str(self.object),
                "volver_url": reverse_lazy("lista_actividades"),
            }
        )
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Actividad eliminada correctamente.")
        return super().form_valid(form)


class EvidenciaCreateView(PermissionRequiredMixin, CreateView):
    model = Evidencia
    form_class = EvidenciaForm
    template_name = "crud/formulario.html"
    permission_required = "actividades.add_evidencia"
    success_url = reverse_lazy("lista_evidencias")
    raise_exception = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Nueva evidencia", "volver_url": reverse_lazy("lista_evidencias")})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Evidencia creada correctamente.")
        return super().form_valid(form)


class EvidenciaUpdateView(PermissionRequiredMixin, UpdateView):
    model = Evidencia
    form_class = EvidenciaForm
    template_name = "crud/formulario.html"
    permission_required = "actividades.change_evidencia"
    success_url = reverse_lazy("lista_evidencias")
    raise_exception = True
    pk_url_kwarg = "evidencia_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Editar evidencia", "volver_url": reverse_lazy("lista_evidencias")})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Evidencia actualizada correctamente.")
        return super().form_valid(form)


class EvidenciaDeleteView(PermissionRequiredMixin, DeleteView):
    model = Evidencia
    template_name = "crud/confirmar_borrar.html"
    permission_required = "actividades.delete_evidencia"
    success_url = reverse_lazy("lista_evidencias")
    raise_exception = True
    pk_url_kwarg = "evidencia_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "titulo": "Eliminar evidencia",
                "objeto_etiqueta": str(self.object),
                "volver_url": reverse_lazy("lista_evidencias"),
            }
        )
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Evidencia eliminada correctamente.")
        return super().form_valid(form)
