"""Additive historical integration. Never deletes rows or changes existing user passwords.
Old compatibility tables stay intact. Unknown information is explicitly left pending.
"""
from django.db import migrations


def integrate(apps, schema_editor):
    db = schema_editor.connection.alias
    def model(app, name): return apps.get_model(app, name).objects.using(db)
    unidades, personas, cargos = model('organizacion','Unidad'), model('organizacion','Persona'), model('organizacion','Cargo')
    User = apps.get_model('auth','User')
    users = User.objects.using(db)
    groups = model('auth','Group')
    for name in ('Acceso total','Intermedio','Minimo'): groups.get_or_create(name=name)
    for obj in cargos.all():
        obj.codigo = obj.codigo or f'HIST-C-{obj.pk}'
        if not obj.descripcion: obj.descripcion = 'Registro histórico: descripción por completar.'
        obj.save(using=db)
    mapping = {}
    for old in model('organizacion','Delegacion').all():
        unit = unidades.filter(nombre__iexact=old.nombre).first()
        if unit is None:
            unit = unidades.create(codigo=old.codigo,nombre=old.nombre,ambito='Histórico',responsable='Por completar',estado='Activa' if old.estado else 'Inactiva',direccion='Dirección histórica por completar')
        mapping[old.pk] = unit.pk
    for obj in unidades.all():
        obj.codigo = obj.codigo or f'HIST-D-{obj.pk}'
        obj.direccion = obj.direccion or 'Dirección histórica por completar'
        obj.save(using=db)
    for rol in model('organizacion','Rol').all():
        rol.codigo = rol.codigo or f'HIST-R-{rol.pk}'
        if not rol.grupo_id:
            group_name = {'Administrador':'Acceso total','Analista':'Intermedio'}.get(rol.nombre)
            if group_name: rol.grupo_id = groups.get(name=group_name).pk
        rol.save(using=db)
    role_model = apps.get_model('organizacion','Rol')
    for person in personas.all():
        if not person.nombres: person.nombres = person.nombre
        if not person.apellidos: person.apellidos = 'Histórico'
        person.rut = person.rut or f'{99000000+person.pk}-0'
        person.correo = person.correo or f'historico-persona-{person.pk}@example.invalid'
        if not person.usuario_id:
            # Non-login technical identity, not an existing account/password reset.
            user, _ = users.get_or_create(username=f'historico_persona_{person.pk}',defaults={'password':'!','is_active':False,'is_staff':False,'is_superuser':False,'first_name':person.nombre[:150]})
            person.usuario_id = user.pk
        person.save(using=db)
        for label in person.roles or []:
            role = role_model.objects.using(db).filter(nombre=label).first()
            if role: person.roles_rel.add(role)
    for profile in model('organizacion','PerfilUsuario').all():
        person = personas.filter(usuario_id=profile.usuario_id).first()
        if person is None:
            user = users.get(pk=profile.usuario_id)
            cargo, _ = cargos.get_or_create(nombre='Cargo histórico por completar', defaults={'codigo':'HIST-C-PERFIL','descripcion':'Cargo de los perfiles anteriores; completar antes de evaluación.','estado':True,'funciones':[]})
            person = personas.create(usuario_id=user.pk,nombre=user.get_username() if hasattr(user,'get_username') else user.username,nombres=user.first_name or user.username,apellidos=user.last_name or 'Histórico',rut=f'{98000000+profile.pk}-0',correo=user.email or f'perfil-{profile.pk}@example.invalid',cargo_id=cargo.pk,delegacion_id=mapping[profile.delegacion_id],estado='Activo' if profile.estado else 'Inactivo',roles=[])
        person.roles_rel.add(profile.rol_id)
    for model_name in ('TipoAtencion',):
        for obj in model('organizacion',model_name).all():
            if not obj.descripcion:
                obj.descripcion = 'Registro histórico: descripción por completar.';obj.save(using=db)
    for period in model('resultados','Periodo').all():
        period.codigo = period.codigo or f'HIST-TRI-{period.pk}'
        period.anio = period.inicio.year
        period.numero = (period.inicio.month-1)//3+1
        period.save(using=db)
    metas = model('resultados','CatalogoMeta')
    for old in model('resultados','Meta').all():
        catalog, _ = metas.get_or_create(codigo=f'HIST-M-{old.pk}',defaults={'nombre':old.item,'descripcion':'Catálogo conservado desde asignación histórica.','tipo':'individual','unidad_medida':old.unidad,'requiere_evidencia':False,'estado':True})
        old.catalogo_id=catalog.pk
        old.fecha_asignacion=model('resultados','Periodo').get(pk=old.periodo_id).inicio
        old.save(using=db)
    # Link each historical author to a disabled technical identity; keep original author text.
    for evidence in model('actividades','Evidencia').all():
        user, _ = users.get_or_create(username=f'historico_autor_{evidence.pk}',defaults={'password':'!','is_active':False,'is_staff':False,'is_superuser':False,'first_name':evidence.autor[:150]})
        evidence.autor_usuario_id = user.pk
        evidence.save(using=db)


class Migration(migrations.Migration):
    dependencies = [('organizacion','0003_cargo_codigo_cargo_descripcion_cargo_estado_and_more'),('agenda','0003_hito_territorio'),('actividades','0004_actividad_solicitante_actividad_territorio_and_more'),('resultados','0002_catalogometa_meta_estado_meta_fecha_asignacion_and_more')]
    operations = [migrations.RunPython(integrate, migrations.RunPython.noop)]
