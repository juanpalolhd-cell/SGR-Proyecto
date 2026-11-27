from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, UpdateView

from organizacion.models import Persona, Unidad
from sgr.parametros import parametros

from .forms import CompromisoForm
from .models import (
    Compromiso,
    ESTADO_REALIZADO,
    ESTADOS_COMPROMISO,
    PLAZO_ETIQUETAS,
)

FILTROS_PLAZO = [("vencido", "Vencidos"), ("proximo", "Próximos a vencer"), ("al_dia", "En plazo"), ("realizado", "Realizados")]


def _dias_aviso():
    try:
        return max(0, int(parametros().get("dias_aviso_vencimiento", 7)))
    except (TypeError, ValueError):
        return 7


def _fecha_param(valor):
    try:
        return date.fromisoformat(valor) if valor else None
    except ValueError:
        return None


def _filtrar_plazo(qs, plazo, hoy, dias):
    limite = hoy + timedelta(days=dias)
    if plazo == "vencido":
        return qs.exclude(estado=ESTADO_REALIZADO).filter(fecha_comprometida__lt=hoy)
    if plazo == "proximo":
        return qs.exclude(estado=ESTADO_REALIZADO).filter(fecha_comprometida__gte=hoy, fecha_comprometida__lte=limite)
    if plazo == "al_dia":
        return qs.exclude(estado=ESTADO_REALIZADO).filter(fecha_comprometida__gt=limite)
    if plazo == "realizado":
        return qs.filter(estado=ESTADO_REALIZADO)
    return qs


def _marcar(compromisos, hoy, dias):
    filas = []
    for c in compromisos:
        c.plazo = c.situacion_plazo(hoy, dias)
        c.plazo_etiqueta = PLAZO_ETIQUETAS[c.plazo]
        c.dias_restantes = (c.fecha_comprometida - hoy).days
        filas.append(c)
    return filas


@permission_required("agenda.view_compromiso", raise_exception=True)
def lista_compromisos(request):
    hoy, dias = timezone.localdate(), _dias_aviso()
    q = (request.GET.get("q") or "").strip()
    estado = request.GET.get("estado") or ""
    plazo = request.GET.get("plazo") or ""
    responsable = request.GET.get("responsable") or ""
    unidad = request.GET.get("unidad") or ""
    qs = Compromiso.objects.select_related("responsable", "unidad").prefetch_related("historial")
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
    if estado in dict(ESTADOS_COMPROMISO):
        qs = qs.filter(estado=estado)
    qs = _filtrar_plazo(qs, plazo, hoy, dias)
    if responsable.isdigit():
        qs = qs.filter(responsable_id=int(responsable))
    if unidad.isdigit():
        qs = qs.filter(unidad_id=int(unidad))
    compromisos = _marcar(qs, hoy, dias)
    return render(
        request,
        "agenda/lista_compromisos.html",
        {
            "compromisos": compromisos,
            "q": q,
            "estado": estado,
            "plazo": plazo,
            "responsable": responsable,
            "unidad": unidad,
            "estados": ESTADOS_COMPROMISO,
            "filtros_plazo": FILTROS_PLAZO,
            "responsables": Persona.objects.filter(compromisos__isnull=False).distinct().order_by("nombre"),
            "unidades": Unidad.objects.filter(compromisos__isnull=False).distinct().order_by("nombre"),
            "dias_aviso": dias,
            "hay_filtros": any([q, estado, plazo, responsable, unidad]),
        },
    )


@permission_required("agenda.view_compromiso", raise_exception=True)
def detalle_compromiso(request, compromiso_id):
    hoy, dias = timezone.localdate(), _dias_aviso()
    compromiso = get_object_or_404(
        Compromiso.objects.select_related("responsable", "unidad"), pk=compromiso_id
    )
    _marcar([compromiso], hoy, dias)
    historial = compromiso.historial.select_related("usuario").all()
    return render(
        request,
        "agenda/detalle_compromiso.html",
        {"compromiso": compromiso, "historial": historial, "dias_aviso": dias, "puede_ver_historial": request.user.has_perm("agenda.view_historialestado")},
    )


def _fila_vacia(nombre):
    return {"nombre": nombre, "total": 0, "por_estado": {e: 0 for e, _ in ESTADOS_COMPROMISO}, "vencidos": 0, "proximos": 0, "fuera_plazo": 0}


def _cerrar_fila(fila):
    total = fila["total"]
    realizados = fila["por_estado"]["Realizado"]
    fila["realizados"] = realizados
    fila["pendientes"] = total - realizados
    fila["por_realizado"] = round(realizados / total * 100, 1) if total else 0
    fila["por_pendiente"] = round((total - realizados) / total * 100, 1) if total else 0
    fila["estados_lista"] = [fila["por_estado"][e] for e, _ in ESTADOS_COMPROMISO]
    return fila


@permission_required("agenda.view_compromiso", raise_exception=True)
def resumen_agenda(request):
    hoy, dias = timezone.localdate(), _dias_aviso()
    desde = _fecha_param(request.GET.get("desde"))
    hasta = _fecha_param(request.GET.get("hasta"))
    qs = Compromiso.objects.select_related("responsable", "unidad").prefetch_related("historial")
    if desde:
        qs = qs.filter(fecha_comprometida__gte=desde)
    if hasta:
        qs = qs.filter(fecha_comprometida__lte=hasta)
    general = _fila_vacia("Total")
    por_responsable, por_delegacion = {}, {}
    for c in _marcar(qs, hoy, dias):
        filas = [general, por_responsable.setdefault(c.responsable_id, _fila_vacia(c.responsable.nombre)), por_delegacion.setdefault(c.unidad_id, _fila_vacia(c.unidad.nombre))]
        for fila in filas:
            fila["total"] += 1
            fila["por_estado"][c.estado] = fila["por_estado"].get(c.estado, 0) + 1
            fila["vencidos"] += c.plazo == "vencido"
            fila["proximos"] += c.plazo == "proximo"
            fila["fuera_plazo"] += c.plazo == "fuera_plazo"
    general = _cerrar_fila(general)
    resumen = {
        "totales": general["por_estado"],
        "total": general["total"],
        "realizado": general["realizados"],
        "pendiente": general["pendientes"],
        "por_realizado": general["por_realizado"],
        "por_pendiente": general["por_pendiente"],
        "vencidos": general["vencidos"],
        "proximos": general["proximos"],
        "fuera_plazo": general["fuera_plazo"],
    }
    return render(
        request,
        "agenda/resumen_agenda.html",
        {
            "resumen": resumen,
            "por_responsable": sorted((_cerrar_fila(f) for f in por_responsable.values()), key=lambda f: f["nombre"]),
            "por_delegacion": sorted((_cerrar_fila(f) for f in por_delegacion.values()), key=lambda f: f["nombre"]),
            "estados": ESTADOS_COMPROMISO,
            "desde": request.GET.get("desde", ""),
            "hasta": request.GET.get("hasta", ""),
            "dias_aviso": dias,
        },
    )


class _GuardarCompromiso:
    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        form.registrar_historial(self.request.user)
        messages.success(self.request, self.mensaje_ok)
        return response


class CompromisoCreateView(PermissionRequiredMixin, _GuardarCompromiso, CreateView):
    model = Compromiso
    form_class = CompromisoForm
    template_name = "crud/formulario.html"
    permission_required = "agenda.add_compromiso"
    success_url = reverse_lazy("lista_compromisos")
    raise_exception = True
    mensaje_ok = "Compromiso creado correctamente."

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Nuevo compromiso", "volver_url": reverse_lazy("lista_compromisos")})
        return ctx


class CompromisoUpdateView(PermissionRequiredMixin, _GuardarCompromiso, UpdateView):
    model = Compromiso
    form_class = CompromisoForm
    template_name = "crud/formulario.html"
    permission_required = "agenda.change_compromiso"
    raise_exception = True
    pk_url_kwarg = "compromiso_id"
    mensaje_ok = "Compromiso actualizado correctamente."

    def get_success_url(self):
        return reverse_lazy("detalle_compromiso", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Editar compromiso", "volver_url": reverse_lazy("lista_compromisos")})
        return ctx


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
