from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from .forms import CompromisoForm
from .models import Compromiso


@permission_required("agenda.view_compromiso", raise_exception=True)
def lista_compromisos(request):
    q = (request.GET.get("q") or "").strip()
    qs = Compromiso.objects.select_related("responsable", "unidad")
    if q:
        qs = qs.filter(
            Q(origen__icontains=q)
            | Q(solicitante__icontains=q)
            | Q(territorio__icontains=q)
            | Q(area_apoyo__icontains=q)
            | Q(estado__icontains=q)
            | Q(observaciones__icontains=q)
            | Q(responsable__nombre__icontains=q)
            | Q(unidad__nombre__icontains=q)
        )
    return render(
        request,
        "agenda/lista_compromisos.html",
        {"compromisos": qs, "q": q},
    )


@permission_required("agenda.view_compromiso", raise_exception=True)
def detalle_compromiso(request, compromiso_id):
    compromiso = get_object_or_404(
        Compromiso.objects.select_related("responsable", "unidad"), pk=compromiso_id
    )
    return render(
        request,
        "agenda/detalle_compromiso.html",
        {"compromiso": compromiso},
    )


@permission_required("agenda.view_compromiso", raise_exception=True)
def resumen_agenda(request):
    compromisos = Compromiso.objects.all()
    totales = {"Ingresado": 0, "Pendiente": 0, "En proceso": 0, "Realizado": 0}
    for c in compromisos:
        totales[c.estado] = totales.get(c.estado, 0) + 1
    total = compromisos.count()
    realizado = totales.get("Realizado", 0)
    pendiente = total - realizado
    por_realizado = round((realizado / total * 100) if total else 0, 1)
    por_pendiente = round((pendiente / total * 100) if total else 0, 1)
    resumen = {
        "totales": totales,
        "total": total,
        "realizado": realizado,
        "pendiente": pendiente,
        "por_realizado": por_realizado,
        "por_pendiente": por_pendiente,
    }
    return render(request, "agenda/resumen_agenda.html", {"resumen": resumen})


class CompromisoCreateView(PermissionRequiredMixin, CreateView):
    model = Compromiso
    form_class = CompromisoForm
    template_name = "crud/formulario.html"
    permission_required = "agenda.add_compromiso"
    success_url = reverse_lazy("lista_compromisos")
    raise_exception = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Nuevo compromiso", "volver_url": reverse_lazy("lista_compromisos")})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Compromiso creado correctamente.")
        return super().form_valid(form)


class CompromisoUpdateView(PermissionRequiredMixin, UpdateView):
    model = Compromiso
    form_class = CompromisoForm
    template_name = "crud/formulario.html"
    permission_required = "agenda.change_compromiso"
    success_url = reverse_lazy("lista_compromisos")
    raise_exception = True
    pk_url_kwarg = "compromiso_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Editar compromiso", "volver_url": reverse_lazy("lista_compromisos")})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Compromiso actualizado correctamente.")
        return super().form_valid(form)


class CompromisoDeleteView(PermissionRequiredMixin, DeleteView):
    model = Compromiso
    template_name = "crud/confirmar_borrar.html"
    permission_required = "agenda.delete_compromiso"
    success_url = reverse_lazy("lista_compromisos")
    raise_exception = True
    pk_url_kwarg = "compromiso_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "titulo": "Eliminar compromiso",
                "objeto_etiqueta": str(self.object),
                "volver_url": reverse_lazy("lista_compromisos"),
            }
        )
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Compromiso eliminado correctamente.")
        return super().form_valid(form)
