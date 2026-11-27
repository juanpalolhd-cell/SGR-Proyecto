from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView

from organizacion.models import Persona, Vecino, participaciones_vigentes, resumen_jjvv
from sgr.reglas import mensaje_periodo_cerrado, periodos_cerrados_de

from .forms import CambioEstadoForm, SolicitudForm
from .models import ESTADOS_SOLICITUD, FLUJO, HistorialSolicitud, NO_CUENTAN, Solicitud, TERMINALES, porcentaje_estado
from .servicios import cambiar_estado


def _etapas():
    return [{"estado": e, "porcentaje": porcentaje_estado(e)} for e in FLUJO]


@permission_required("solicitudes.view_solicitud", raise_exception=True)
def lista_solicitudes(request):
    q = (request.GET.get("q") or "").strip()
    estado = request.GET.get("estado") or ""
    responsable = request.GET.get("responsable") or ""
    qs = Solicitud.objects.select_related("vecino", "responsable", "empresa", "junta")
    if q:
        qs = qs.filter(Q(codigo__icontains=q) | Q(asunto__icontains=q) | Q(descripcion__icontains=q) | Q(vecino__nombres__icontains=q) | Q(vecino__apellidos__icontains=q) | Q(vecino__rut__icontains=q) | Q(empresa__nombre__icontains=q))
    if estado in dict(ESTADOS_SOLICITUD):
        qs = qs.filter(estado=estado)
    if responsable.isdigit():
        qs = qs.filter(responsable_id=int(responsable))
    solicitudes = list(qs)
    conteo = {e: 0 for e, _ in ESTADOS_SOLICITUD}
    for s in Solicitud.objects.values_list("estado", flat=True):
        conteo[s] = conteo.get(s, 0) + 1
    return render(request, "solicitudes/lista.html", {
        "solicitudes": solicitudes, "q": q, "estado": estado, "responsable": responsable,
        "estados": ESTADOS_SOLICITUD, "conteo": [(e, conteo.get(e, 0)) for e, _ in ESTADOS_SOLICITUD],
        "responsables": Persona.objects.filter(solicitudes__isnull=False).distinct().order_by("nombre"),
        "etapas": _etapas(), "hay_filtros": any([q, estado, responsable]),
    })


@permission_required("solicitudes.view_solicitud", raise_exception=True)
def detalle_solicitud(request, solicitud_id, form_estado=None):
    s = get_object_or_404(Solicitud.objects.select_related("vecino", "responsable", "empresa", "junta", "asignacion__periodo"), pk=solicitud_id)
    cerrados = periodos_cerrados_de(s)
    puede_cambiar = request.user.has_perm("solicitudes.change_solicitud") and s.estado not in TERMINALES and not cerrados
    return render(request, "solicitudes/detalle.html", {
        "s": s, "historial": s.historial.select_related("usuario").all(),
        "jjvv_actual": resumen_jjvv(s.vecino),
        "form_estado": form_estado or (CambioEstadoForm(s) if puede_cambiar else None),
        "puede_cambiar": puede_cambiar, "bloqueo": mensaje_periodo_cerrado(cerrados) if cerrados else "",
        "etapas": _etapas(), "no_cuenta": s.estado in NO_CUENTAN,
        "puede_editar": request.user.has_perm("solicitudes.change_solicitud") and s.estado not in TERMINALES and not cerrados,
    })


@require_POST
@permission_required("solicitudes.change_solicitud", raise_exception=True)
def cambiar_estado_solicitud(request, solicitud_id):
    s = get_object_or_404(Solicitud, pk=solicitud_id)
    form = CambioEstadoForm(s, request.POST)
    if form.is_valid():
        anterior = s.estado
        try:
            cambiar_estado(s, form.cleaned_data["nuevo_estado"], request.user, form.cleaned_data.get("observacion"), form.cleaned_data.get("empresa"))
        except ValidationError as exc:
            s.refresh_from_db()
            for m in exc.messages:
                form.add_error(None, m)
            return detalle_solicitud(request, solicitud_id, form_estado=form)
        messages.success(request, f"Solicitud {s.codigo}: {anterior} → {s.estado} ({s.porcentaje} % de avance).")
        return redirect("detalle_solicitud", solicitud_id=s.pk)
    return detalle_solicitud(request, solicitud_id, form_estado=form)


@permission_required("solicitudes.view_solicitud", raise_exception=True)
def vecino_jjvv(request, vecino_id):
    vecino = get_object_or_404(Vecino, pk=vecino_id)
    r = resumen_jjvv(vecino)
    return JsonResponse({"pertenece": r["pertenece"], "con_cargo": r["con_cargo"], "junta": r["junta"].nombre if r["junta"] else "", "cargo": r["cargo"], "texto": r["texto"]})


class _SolicitudFormMixin(PermissionRequiredMixin):
    model = Solicitud
    form_class = SolicitudForm
    template_name = "solicitudes/formulario.html"
    raise_exception = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["url_jjvv"] = reverse("vecino_jjvv", args=[0]).replace("/0/", "/{id}/")
        ctx["volver_url"] = reverse("detalle_solicitud", args=[self.object.pk]) if getattr(self, "object", None) and self.object.pk else reverse("lista_solicitudes")
        return ctx

    def form_valid(self, form):
        try:
            with transaction.atomic():
                nuevo = form.instance.pk is None
                self.object = form.save()
                if nuevo:
                    HistorialSolicitud.objects.create(solicitud=self.object, usuario=self.request.user, estado_anterior="", estado_nuevo=self.object.estado, porcentaje=self.object.porcentaje, observacion="Ingreso de la solicitud. Consulta JJVV: " + (form.jjvv["texto"] if form.jjvv else "—"))
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        if form.jjvv:
            if form.jjvv["con_cargo"]:
                messages.warning(self.request, f"Atención: el vecino {form.jjvv['texto']}. La solicitud se ingresó igualmente.")
            else:
                messages.info(self.request, f"Consulta JJVV: {form.jjvv['texto']}.")
        messages.success(self.request, f"Solicitud {self.object.codigo} guardada ({self.object.estado}, {self.object.porcentaje} %).")
        return redirect("detalle_solicitud", solicitud_id=self.object.pk)


class SolicitudCreateView(_SolicitudFormMixin, CreateView):
    permission_required = "solicitudes.add_solicitud"

    def get_initial(self):
        inicial = super().get_initial()
        vecino = self.request.GET.get("vecino") or ""
        if vecino.isdigit():
            inicial["vecino"] = int(vecino)
        return inicial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = "Ingresar solicitud de vecino"
        return ctx


class SolicitudUpdateView(_SolicitudFormMixin, UpdateView):
    permission_required = "solicitudes.change_solicitud"
    pk_url_kwarg = "solicitud_id"

    def dispatch(self, request, *args, **kwargs):
        s = get_object_or_404(Solicitud, pk=kwargs["solicitud_id"])
        if request.user.is_authenticated and s.estado in TERMINALES:
            messages.error(request, f"La solicitud está {s.estado.lower()}: ya no se puede editar.")
            return redirect("detalle_solicitud", solicitud_id=s.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titulo"] = f"Editar solicitud {self.object.codigo}"
        ctx["jjvv_registrada"] = self.object.junta.nombre if self.object.junta_id else ""
        return ctx
