from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from organizacion.models import Persona, Unidad
from sgr.utils import load_json

from .forms import MetaForm, PeriodoForm
from .models import Meta, Periodo

DIAS_TRANSCURRIDOS = 15


def _parametros():
    try:
        data = load_json("resultados.json")
        return data.get("parametros", {})
    except Exception:
        return {
            "tope_ponderado": 150,
            "umbral_colectivo": 80,
            "maximo_cumplimiento": 100,
            "regla_semaforo_ambar": 60,
        }


def _calcular_meta(meta, tope, max_c):
    avance = float(meta.avance)
    objetivo = float(meta.meta)
    pct = round((avance / objetivo * 100), 1) if objetivo > 0 else 0.0
    pct_cap = min(pct, max_c)
    ponderado = round(float(meta.ponderador) * pct_cap / 100, 1)
    return {
        "pct_cumplimiento": pct,
        "pct_cap": pct_cap,
        "ponderado": ponderado,
    }


def _expected(periodo):
    dias = periodo.dias_computables
    return round((DIAS_TRANSCURRIDOS / dias * 100), 1) if dias else 0.0


def _semaforo(total, expected, umbral_ambar):
    if total >= expected:
        return "verde"
    if total >= expected * umbral_ambar / 100:
        return "ambar"
    return "rojo"


def _enriquecer_meta(meta, params):
    tope = params.get("tope_ponderado", 150)
    max_c = params.get("maximo_cumplimiento", 100)
    calc = _calcular_meta(meta, tope, max_c)
    return {
        "id": meta.id,
        "item": meta.item,
        "unidad": meta.unidad,
        "persona_id": meta.persona_id,
        "persona_nombre": meta.persona.nombre,
        "periodo_id": meta.periodo_id,
        "periodo_nombre": meta.periodo.nombre,
        "meta": meta.meta,
        "avance": meta.avance,
        "ponderador": meta.ponderador,
        "pct_cumplimiento": calc["pct_cumplimiento"],
        "ponderado": calc["ponderado"],
        "obj": meta,
    }


def _resumen_persona(persona, periodo, params):
    tope = params.get("tope_ponderado", 150)
    max_c = params.get("maximo_cumplimiento", 100)
    umbral = params.get("regla_semaforo_ambar", 60)
    metas_qs = Meta.objects.filter(persona=persona, periodo=periodo).select_related(
        "persona", "periodo"
    )
    metas = [_enriquecer_meta(m, params) for m in metas_qs]
    total = round(sum(m["ponderado"] for m in metas), 1)
    total = min(total, tope)
    expected = _expected(periodo) if periodo else 0
    return {
        "persona": persona,
        "persona_id": persona.id,
        "nombre": persona.nombre,
        "cargo": persona.cargo.nombre,
        "delegacion": persona.delegacion.nombre,
        "periodo": periodo,
        "metas": metas,
        "total_ponderado": total,
        "expected": expected,
        "semaforo": _semaforo(total, expected, umbral),
    }


@permission_required("resultados.view_meta", raise_exception=True)
def lista_metas(request):
    q = (request.GET.get("q") or "").strip()
    params = _parametros()
    qs = Meta.objects.select_related("persona", "periodo")
    if q:
        qs = qs.filter(
            Q(item__icontains=q)
            | Q(unidad__icontains=q)
            | Q(persona__nombre__icontains=q)
            | Q(periodo__nombre__icontains=q)
        )
    metas = [_enriquecer_meta(m, params) for m in qs]
    periodos = {p.id: p.nombre for p in Periodo.objects.all()}
    return render(
        request,
        "resultados/lista_metas.html",
        {"metas": metas, "periodos": periodos, "q": q},
    )


@permission_required("resultados.view_meta", raise_exception=True)
def detalle_meta(request, meta_id):
    params = _parametros()
    meta = get_object_or_404(Meta.objects.select_related("persona", "periodo"), pk=meta_id)
    tope = params.get("tope_ponderado", 150)
    max_c = params.get("maximo_cumplimiento", 100)
    calc = _calcular_meta(meta, tope, max_c)
    contexto = {
        "meta": meta,
        "persona_nombre": meta.persona.nombre,
        "periodo": meta.periodo,
        "pct_cumplimiento": calc["pct_cumplimiento"],
        "pct_cap": calc["pct_cap"],
        "ponderado": calc["ponderado"],
        "tope": tope,
    }
    return render(request, "resultados/detalle_meta.html", contexto)


@permission_required("resultados.view_meta", raise_exception=True)
def resultado_persona(request, persona_id):
    params = _parametros()
    persona = get_object_or_404(
        Persona.objects.select_related("cargo", "delegacion"), pk=persona_id
    )
    periodos = list(Periodo.objects.all())
    periodo = periodos[0] if periodos else None
    if periodo is None:
        raise Http404("No hay períodos registrados")
    resumen = _resumen_persona(persona, periodo, params)
    return render(
        request,
        "resultados/resultado_persona.html",
        {"resumen": resumen, "periodos": periodos},
    )


@permission_required("resultados.view_meta", raise_exception=True)
def tablero_unidad(request):
    params = _parametros()
    periodo = Periodo.objects.order_by("id").first()
    tablero = []
    for unidad in Unidad.objects.all():
        miembros = Persona.objects.filter(delegacion=unidad).select_related(
            "cargo", "delegacion"
        )
        filas = []
        for p in miembros:
            if periodo is None:
                continue
            r = _resumen_persona(p, periodo, params)
            filas.append(
                {
                    "persona_id": p.id,
                    "nombre": p.nombre,
                    "cargo": r["cargo"],
                    "total_ponderado": r["total_ponderado"],
                    "expected": r["expected"],
                    "semaforo": r["semaforo"],
                }
            )
        tablero.append(
            {"unidad": unidad.nombre, "ambito": unidad.ambito, "miembros": filas}
        )
    return render(
        request,
        "resultados/tablero_unidad.html",
        {"tablero": tablero, "umbral": params.get("umbral_colectivo", 80)},
    )


@permission_required("resultados.view_meta", raise_exception=True)
def informe_resumen(request):
    params = _parametros()
    periodo = Periodo.objects.order_by("id").first()
    informes = []
    for p in Persona.objects.select_related("cargo", "delegacion"):
        if periodo is None:
            break
        r = _resumen_persona(p, periodo, params)
        informes.append(
            {
                "persona_id": p.id,
                "nombre": p.nombre,
                "delegacion": r["delegacion"],
                "cargo": r["cargo"],
                "total_ponderado": r["total_ponderado"],
                "semaforo": r["semaforo"],
            }
        )
    semaforos = {
        "verde": sum(1 for i in informes if i["semaforo"] == "verde"),
        "ambar": sum(1 for i in informes if i["semaforo"] == "ambar"),
        "rojo": sum(1 for i in informes if i["semaforo"] == "rojo"),
    }
    prom = (
        round(sum(i["total_ponderado"] for i in informes) / len(informes), 1)
        if informes
        else 0
    )
    return render(
        request,
        "resultados/informe_resumen.html",
        {
            "informes": informes,
            "semaforos": semaforos,
            "promedio": prom,
            "umbral": params.get("umbral_colectivo", 80),
            "tope": params.get("tope_ponderado", 150),
        },
    )


class MetaCreateView(PermissionRequiredMixin, CreateView):
    model = Meta
    form_class = MetaForm
    template_name = "crud/formulario.html"
    permission_required = "resultados.add_meta"
    success_url = reverse_lazy("lista_metas")
    raise_exception = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Nueva meta", "volver_url": reverse_lazy("lista_metas")})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Meta creada correctamente.")
        return super().form_valid(form)


class MetaUpdateView(PermissionRequiredMixin, UpdateView):
    model = Meta
    form_class = MetaForm
    template_name = "crud/formulario.html"
    permission_required = "resultados.change_meta"
    success_url = reverse_lazy("lista_metas")
    raise_exception = True
    pk_url_kwarg = "meta_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Editar meta", "volver_url": reverse_lazy("lista_metas")})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Meta actualizada correctamente.")
        return super().form_valid(form)


class MetaDeleteView(PermissionRequiredMixin, DeleteView):
    model = Meta
    template_name = "crud/confirmar_borrar.html"
    permission_required = "resultados.delete_meta"
    success_url = reverse_lazy("lista_metas")
    raise_exception = True
    pk_url_kwarg = "meta_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "titulo": "Eliminar meta",
                "objeto_etiqueta": str(self.object),
                "volver_url": reverse_lazy("lista_metas"),
            }
        )
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Meta eliminada correctamente.")
        return super().form_valid(form)


class PeriodoCreateView(PermissionRequiredMixin, CreateView):
    model = Periodo
    form_class = PeriodoForm
    template_name = "crud/formulario.html"
    permission_required = "resultados.add_periodo"
    success_url = reverse_lazy("lista_metas")
    raise_exception = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"titulo": "Nuevo período", "volver_url": reverse_lazy("lista_metas")})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Período creado correctamente.")
        return super().form_valid(form)
