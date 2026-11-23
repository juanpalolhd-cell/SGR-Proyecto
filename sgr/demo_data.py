"""Fictitious, repeatable, additive samples. Existing records are never overwritten."""
from datetime import date
from django.contrib.auth.models import User, Group
from django.db import transaction
from organizacion.models import Unidad, Cargo, Persona, Rol, Territorio, Vecino, JuntaVecinos, Participacion, TipoAtencion, SubAtencion
from agenda.models import Hito
from resultados.models import Periodo, CatalogoMeta, Meta
from actividades.models import Actividad, GestionSocial, Evidencia

@transaction.atomic
def create_demo():
    rows = {}
    for n in (1,2):
        code=f'DEMO-{n}'
        user,created=User.objects.get_or_create(username=f'muestra_sgr_{n}',defaults={'is_active':False,'first_name':f'Funcionario {n}','last_name':'Ficticio','email':f'funcionario{n}@example.invalid'})
        if created: user.set_unusable_password();user.save()
        group,_=Group.objects.get_or_create(name='Minimo' if n==1 else 'Intermedio')
        rol,_=Rol.objects.get_or_create(codigo=f'{code}-ROL',defaults={'nombre':f'Rol ficticio {n}','grupo':group,'estado':True})
        unidad,_=Unidad.objects.get_or_create(codigo=f'{code}-DEL',defaults={'nombre':f'Delegación ficticia {n}','direccion':'Calle ficticia 123','ambito':'Demostración','responsable':'Ficticio','estado':'Activa' if n==1 else 'Inactiva'})
        cargo,_=Cargo.objects.get_or_create(codigo=f'{code}-CAR',defaults={'nombre':f'Cargo ficticio {n}','descripcion':'Descripción ficticia','estado':True})
        person,_=Persona.objects.get_or_create(usuario=user,defaults={'nombre':f'Funcionario {n} Ficticio','nombres':f'Funcionario {n}','apellidos':'Ficticio','rut':f'9700000{n}-0','correo':f'funcionario{n}@example.invalid','cargo':cargo,'delegacion':unidad,'estado':'Activo'})
        person.roles_rel.add(rol)
        if not unidad.delegado_id: unidad.delegado=person;unidad.save()
        territory,_=Territorio.objects.get_or_create(codigo=f'{code}-TER',defaults={'nombre':f'Territorio ficticio {n}','descripcion':'Sector ficticio','delegacion':unidad,'estado':n==1})
        neighbor,_=Vecino.objects.get_or_create(rut=f'9600000{n}-0',defaults={'nombres':f'Vecino {n}','apellidos':'Ficticio','telefono':'000000000','correo':f'vecino{n}@example.invalid','direccion':'Dirección ficticia','territorio':territory,'estado':True})
        junta,_=JuntaVecinos.objects.get_or_create(codigo=f'{code}-JUN',defaults={'nombre':f'Junta ficticia {n}','direccion':'Dirección ficticia','delegacion':unidad,'territorio':territory,'fecha_constitucion':date(2026,1,1),'estado':True})
        participation,_=Participacion.objects.get_or_create(vecino=neighbor,junta=junta,defaults={'dirigente':False,'cargo':'Integrante','fecha_incorporacion':date(2026,1,2),'estado':True})
        hito,created=Hito.objects.get_or_create(codigo=f'{code}-HIT',defaults={'nombre':f'Hito ficticio {n}','descripcion':'Descripción ficticia','periodicidad':'unico','fecha_inicio':date(2026,1,1),'fecha_termino':date(2026,3,31),'delegacion':unidad,'territorio':territory,'estado':True})
        if created: hito.responsables.add(person)
        typ,_=TipoAtencion.objects.get_or_create(codigo=f'{code}-TIP',defaults={'nombre':f'Tipo ficticio {n}','descripcion':'Descripción ficticia','estado':True})
        subtype,_=SubAtencion.objects.get_or_create(codigo=f'{code}-SUB',defaults={'nombre':f'Subtipo ficticio {n}','descripcion':'Descripción ficticia','tipo_atencion':typ,'estado':True})
        catalog,_=CatalogoMeta.objects.get_or_create(codigo=f'{code}-MET',defaults={'nombre':f'Meta ficticia {n}','descripcion':'Descripción ficticia','tipo':'individual','unidad_medida':'Atenciones','requiere_evidencia':True,'estado':True})
        period,_=Periodo.objects.get_or_create(codigo=f'{code}-TRI',defaults={'nombre':f'Trimestre ficticio {n}','anio':2026,'numero':n,'inicio':date(2026,1 if n==1 else 4,1),'termino':date(2026,3 if n==1 else 6,30),'dias_computables':90,'estado':'Abierto'})
        assignment,_=Meta.objects.get_or_create(persona=person,catalogo=catalog,periodo=period,defaults={'item':catalog.nombre,'unidad':catalog.unidad_medida,'meta':10,'avance':0,'ponderador':50,'fecha_asignacion':period.inicio,'estado':True})
        activity,_=Actividad.objects.get_or_create(codigo=f'{code}-ACT',defaults={'fecha':date(2026,1,5),'persona':person,'asignacion':assignment,'hito':hito,'tipo':'gestion','descripcion':'Actividad ficticia','origen':'Demostración','solicitante':neighbor,'unidad':unidad,'territorio':territory,'responsable':person,'fecha_compromiso':date(2026,1,10),'apoyo':'Equipo ficticio','avance':0,'estado':'Pendiente','resultado':'','accion':'Gestión','contacto':str(neighbor),'item':catalog.nombre})
        social,_=GestionSocial.objects.get_or_create(beneficiario=neighbor,asignacion=assignment,fecha_ingreso=date(2026,1,5),defaults={'fecha_atencion':date(2026,1,6),'tipo':typ,'subtipo':subtype,'visita':False,'actuaciones':'Atención ficticia','estado':'pendiente'})
        evidence,_=Evidencia.objects.get_or_create(codigo=f'{code}-EVI',defaults={'actividad':activity if n==1 else None,'gestion_social':social if n==2 else None,'tipo':'referencia','ruta':f'ficticio/{n}.pdf','autor_usuario':user,'autor':user.username,'fecha':date(2026,1,6),'estado':'Registrada','observacion':'Sin archivo real'})
        rows[n]={'delegaciones':unidad,'territorios':territory,'funcionarios':person,'cargos':cargo,'roles':rol,'vecinos':neighbor,'juntas':junta,'participaciones':participation,'hitos':hito,'actividades':activity,'gestiones':social,'tipos':typ,'subtipos':subtype,'metas':catalog,'asignaciones':assignment,'evidencias':evidence,'trimestres':period}
    return rows
