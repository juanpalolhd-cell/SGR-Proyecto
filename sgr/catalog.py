"""The 17 evaluation entities; existing model names retain stable PKs."""
from . import catalog_forms as f
SPECS = {
    "delegaciones": ("Delegación", f.DelegacionForm, False),
    "territorios": ("Territorio", f.TerritorioForm, False),
    "funcionarios": ("Usuario funcionario", f.FuncionarioForm, False),
    "cargos": ("Cargo", f.CargoForm, False),
    "roles": ("Rol", f.RolForm, False),
    "vecinos": ("Vecino", f.VecinoForm, False),
    "juntas": ("Junta de vecinos", f.JuntaForm, False),
    "participaciones": ("Participación en junta", f.ParticipacionForm, False),
    "hitos": ("Hito", f.HitoForm, True),
    "actividades": ("Actividad", f.ActividadForm, True),
    "gestiones": ("Gestión social", f.GestionForm, True),
    "tipos": ("Tipo de atención", f.TipoForm, False),
    "subtipos": ("Subtipo de atención", f.SubtipoForm, False),
    "metas": ("Meta", f.MetaForm, True),
    "asignaciones": ("Asignación de meta", f.AsignacionForm, True),
    "evidencias": ("Evidencia", f.EvidenciaForm, True),
    "trimestres": ("Trimestre", f.TrimestreForm, True),
}

# V4.3: entidades complementarias fuera de las 17 de la evaluación (mismo CRUD del sitio).
EXTRA_SPECS = {
    "empresas": ("Empresa contratista", f.EmpresaForm, False),
}
ALL_SPECS = {**SPECS, **EXTRA_SPECS}

def permission(slug, action):
    model = ALL_SPECS[slug][1]._meta.model
    return f"{model._meta.app_label}.{action}_{model._meta.model_name}"

def menu():
    return [{"slug": slug, "nombre": spec[0]} for slug, spec in SPECS.items()]

def menu_extra():
    return [{"slug": slug, "nombre": spec[0]} for slug, spec in EXTRA_SPECS.items()]
