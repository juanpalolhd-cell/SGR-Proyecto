from django.db.models import Q
from django.shortcuts import render
from django.views import View
from .catalog import ALL_SPECS as SPECS, permission

class BusquedaGlobalView(View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        grupos = []
        if q:
            for slug, (title, form, intermediate) in SPECS.items():
                if not request.user.has_perm(permission(slug, "view")): continue
                model = form._meta.model
                condition = Q()
                for field in model._meta.fields:
                    if field.get_internal_type() in ("CharField", "TextField", "EmailField"):
                        condition |= Q(**{field.name + "__icontains": q})
                rows = model.objects.filter(condition).order_by("pk")[:30]
                items = [{"etiqueta": str(obj), "extra": "", "entidad": slug, "pk": obj.pk} for obj in rows]
                if items: grupos.append({"titulo": title, "items": items})
        return render(request, "buscar.html", {"q": q, "grupos": grupos, "total": sum(len(g["items"]) for g in grupos)})
