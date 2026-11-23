"""Permission checked site CRUD, not Django Admin."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction, IntegrityError
from django.db.models import Q, ProtectedError, RestrictedError
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .catalog import SPECS, permission, menu

@login_required
def index(request):
    return render(request, "catalog/index.html", {"entidades": menu()})

class CatalogMixin(PermissionRequiredMixin):
    action = "view"
    raise_exception = True
    def get_spec(self):
        try: return SPECS[self.kwargs["entidad"]]
        except KeyError: raise Http404("Entidad inexistente")
    def get_permission_required(self):
        self.get_spec()
        return (permission(self.kwargs["entidad"], self.action),)
    def get_queryset(self):
        return self.get_spec()[1]._meta.model.objects.all().order_by("pk")
    def get_form_class(self): return self.get_spec()[1]
    def get_success_url(self): return reverse("catalog_lista", args=[self.kwargs["entidad"]])
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        slug = self.kwargs["entidad"]
        ctx.update(entidad=slug, titulo=self.get_spec()[0], volver_url=self.get_success_url(), can_add=self.request.user.has_perm(permission(slug,"add")), can_change=self.request.user.has_perm(permission(slug,"change")), can_delete=self.request.user.has_perm(permission(slug,"delete")))
        if getattr(self, "object", None) is not None:
            obj = self.object
            values = []
            for name in self.get_spec()[1]._meta.fields:
                if name == "nuevo_usuario": continue
                field = obj._meta.get_field(name)
                value = getattr(obj, name)
                if field.many_to_many: value = ", ".join(str(x) for x in value.all())
                elif isinstance(value, bool): value = "Sí" if value else "No"
                values.append((field.verbose_name, value if value is not None else "—"))
            if slug == "funcionarios":
                values += [("Último acceso", obj.usuario.last_login if obj.usuario_id else "Pendiente de vincular"), ("Grupos de acceso (solo lectura)", ", ".join(obj.usuario.groups.values_list("name", flat=True)) if obj.usuario_id else "—"), ("Roles relacionados (solo lectura)", ", ".join(obj.roles_rel.values_list("nombre", flat=True)))]
            if slug == "roles": values.append(("Grupo de permisos (solo lectura)", obj.grupo or "Asignar por administración protegida"))
            ctx["valores"] = values
            ctx["objeto_etiqueta"] = str(obj)
        return ctx

class Listado(CatalogMixin, ListView):
    template_name = "catalog/lista.html"
    context_object_name = "registros"
    paginate_by = 30
    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            condition = Q()
            for field in qs.model._meta.fields:
                if field.get_internal_type() in ("CharField", "TextField", "EmailField"):
                    condition |= Q(**{field.name + "__icontains": q})
            qs = qs.filter(condition)
        return qs
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs);ctx["q"] = self.request.GET.get("q", "");return ctx

class Detalle(CatalogMixin, DetailView):
    template_name = "catalog/detalle.html"

class GuardarMixin(CatalogMixin):
    template_name = "crud/formulario.html"
    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Registro guardado correctamente.")
        return response

class Crear(GuardarMixin, CreateView): action = "add"
class Editar(GuardarMixin, UpdateView): action = "change"

class Borrar(CatalogMixin, DeleteView):
    def get_form_class(self): return forms.Form
    action = "delete"
    template_name = "crud/confirmar_borrar.html"
    def form_valid(self, form):
        try:
            with transaction.atomic(): response = super().form_valid(form)
        except (ProtectedError, RestrictedError):
            messages.error(self.request, "No se puede eliminar: hay registros relacionados que deben conservarse. Puede editar el estado para desactivar o anular este registro.")
            return self.render_to_response(self.get_context_data(form=form), status=200)
        messages.success(self.request, "Registro eliminado correctamente.")
        return response
