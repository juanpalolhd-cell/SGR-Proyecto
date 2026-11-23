"""Evaluation 3 regression matrix; all accounts below are synthetic local-test accounts."""
from datetime import date
from itertools import count
from django.contrib.auth.models import User, Group
from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse
from sgr.catalog import SPECS
from sgr.demo_data import create_demo
from sgr import catalog_forms as forms
from organizacion.models import Unidad, Persona, Vecino
from actividades.models import Actividad, Evidencia
from resultados.models import Meta

class Evaluation3Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rows = create_demo()
        call_command('setup_roles', verbosity=0)
        cls.users = {}
        for role, group in [('total','Acceso total'),('intermedio','Intermedio'),('minimo','Minimo')]:
            user=User.objects.create_user(username='prueba_'+role,password='SoloPruebaAislada123!',is_superuser=False,is_staff=False)
            user.groups.add(Group.objects.get(name=group));cls.users[role]=user
    def setUp(self):
        self.serial=count(1)
        self.client.force_login(self.users['total'])
    def url(self, action, slug, pk=None):
        return reverse('catalog_'+action,args=[slug] + ([] if pk is None else [pk]))
    def payload(self, slug, obj=None, new=False):
        obj=obj or self.rows[1][slug]
        form=SPECS[slug][1](instance=obj)
        data={}
        for name,field in form.fields.items():
            if name=='nuevo_usuario': data[name]='';continue
            value=getattr(obj,name,None)
            if hasattr(value,'all'): value=[x.pk for x in value.all()]
            elif hasattr(value,'pk'): value=value.pk
            elif isinstance(value,date): value=value.isoformat()
            elif isinstance(value,bool): value='on' if value else ''
            elif value is None: value=''
            data[name]=value
        if new:
            n=next(self.serial)
            if 'codigo' in data: data['codigo']=f'TEST-{slug[:12]}-{n}'
            if 'nombre' in data: data['nombre']=f'Prueba {slug} {n}'
            if 'rut' in data: data['rut']=f'9500{n:04d}-0'
            if slug=='funcionarios': data['usuario']='';data['nuevo_usuario']=f'nuevo_ficticio_{n}'
            if slug=='delegaciones': data['delegado']=''
            if slug=='participaciones':
                v=self.rows[1]['vecinos']
                fresh=Vecino.objects.create(rut=f'9400{n:04d}-0',nombres='Desechable',apellidos='Ficticio',telefono='0',correo='x@example.invalid',direccion='Ficticia',territorio=v.territorio)
                data['vecino']=fresh.pk
        return data
    def test_role_setup_never_resets_existing_account(self):
        user=User.objects.create_user(username='sgr_total',password='ConservarSoloPrueba123!',is_staff=False,is_superuser=False)
        before=user.password
        call_command('setup_roles',create_users=True,password_total='DistintaSoloPrueba123!',password_intermedio='',password_minimo='',email='demo@example.invalid',verbosity=0)
        user.refresh_from_db()
        self.assertEqual(user.password,before);self.assertFalse(user.is_staff);self.assertFalse(user.is_superuser);self.assertFalse(user.groups.exists())
    def test_ungrouped_users_cannot_bypass_view_permissions(self):
        user=User.objects.create_user(username='sin_grupos_ficticio')
        self.client.force_login(user)
        for url in ('/organizacion/unidades/','/organizacion/personas/','/actividades/','/actividades/evidencias/','/agenda/','/resultados/','/resultados/tablero/','/gestion/actividades/'):
            self.assertEqual(self.client.get(url).status_code,403,url)
    def test_database_constraints(self):
        from django.db import transaction, IntegrityError
        for obj, changes in [(self.rows[1]['asignaciones'], {'meta': 0}), (self.rows[1]['asignaciones'], {'ponderador': 101}), (self.rows[1]['trimestres'], {'numero': 5}), (self.rows[1]['trimestres'], {'termino': '2025-01-01'}), (self.rows[1]['evidencias'], {'actividad': None, 'gestion_social': None})]:
            with self.subTest(changes=changes):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic(): type(obj).objects.filter(pk=obj.pk).update(**changes)
    def test_new_functionary_has_no_automatic_privileges(self):
        data=self.payload('funcionarios',new=True)
        self.assertEqual(self.client.post(self.url('crear','funcionarios'),data).status_code,302)
        user=User.objects.get(username=data['nuevo_usuario'])
        self.assertFalse(user.has_usable_password());self.assertFalse(user.is_superuser);self.assertFalse(user.is_staff);self.assertFalse(user.groups.exists())
        obj=Persona.objects.get(usuario=user)
        response=self.client.get(self.url('detalle','funcionarios',obj.pk))
        self.assertNotContains(response,user.password)
    def test_samples_idempotent_and_all_entities(self):
        before={s:sp[1]._meta.model.objects.count() for s,sp in SPECS.items()}
        create_demo()
        self.assertEqual(before,{s:sp[1]._meta.model.objects.count() for s,sp in SPECS.items()})
        self.assertEqual(len(SPECS),17)
        for row in self.rows.values():
            for obj in row.values(): obj.full_clean()
    def test_dates_and_numeric_limits(self):
        cases=[('trimestres',{'inicio':'2026-12-01','termino':'2026-01-01'}),('trimestres',{'numero':0}),('trimestres',{'numero':5}),('asignaciones',{'meta':0}),('asignaciones',{'meta':-1}),('asignaciones',{'ponderador':-1}),('asignaciones',{'ponderador':101}),('hitos',{'fecha_termino':'2025-01-01'}),('actividades',{'fecha_compromiso':'2025-01-01'}),('gestiones',{'fecha_atencion':'2025-01-01'})]
        for slug,changes in cases:
            with self.subTest(slug=slug,changes=changes):
                data=self.payload(slug);data.update(changes)
                form=SPECS[slug][1](data=data,instance=self.rows[1][slug]);self.assertFalse(form.is_valid(),form.errors)
    def test_relation_coherence(self):
        cases=[('juntas',{'territorio':self.rows[2]['territorios'].pk}),('hitos',{'territorio':self.rows[2]['territorios'].pk}),('hitos',{'responsables':[self.rows[2]['funcionarios'].pk]}),('gestiones',{'subtipo':self.rows[2]['subtipos'].pk}),('actividades',{'territorio':self.rows[2]['territorios'].pk}),('actividades',{'persona':self.rows[2]['funcionarios'].pk}),('actividades',{'asignacion':self.rows[2]['asignaciones'].pk}),('actividades',{'hito':self.rows[2]['hitos'].pk}),('actividades',{'responsable':self.rows[2]['funcionarios'].pk}),('participaciones',{'junta':self.rows[2]['juntas'].pk}),('delegaciones',{'delegado':self.rows[2]['funcionarios'].pk})]
        for slug,changes in cases:
            with self.subTest(slug=slug,changes=changes):
                data=self.payload(slug);data.update(changes)
                f=SPECS[slug][1](data=data,instance=self.rows[1][slug]);self.assertFalse(f.is_valid())
    def test_evidence_exactly_one_origin(self):
        for changes in ({'actividad':'','gestion_social':''},{'actividad':self.rows[1]['actividades'].pk,'gestion_social':self.rows[1]['gestiones'].pk}):
            data=self.payload('evidencias');data.update(changes)
            self.assertFalse(forms.EvidenciaForm(data=data,instance=self.rows[1]['evidencias']).is_valid())
    def test_protected_delete_friendly_and_preserves(self):
        obj=self.rows[1]['delegaciones']
        r=self.client.post(self.url('borrar','delegaciones',obj.pk))
        self.assertEqual(r.status_code,200);self.assertContains(r,'registros relacionados');self.assertTrue(Unidad.objects.filter(pk=obj.pk).exists())
        obj=self.rows[1]['actividades']
        r=self.client.post(self.url('borrar','actividades',obj.pk))
        self.assertEqual(r.status_code,200);self.assertTrue(Actividad.objects.filter(pk=obj.pk).exists());self.assertTrue(Evidencia.objects.filter(actividad=obj).exists())
    def test_privilege_escalation_fields_ignored(self):
        obj=self.rows[1]['funcionarios'];before=(obj.usuario.is_superuser,obj.usuario.is_staff,list(obj.usuario.groups.values_list('pk',flat=True)))
        data=self.payload('funcionarios');data.update(is_superuser='on',is_staff='on',groups=[Group.objects.get(name='Acceso total').pk],user_permissions=[1])
        r=self.client.post(self.url('editar','funcionarios',obj.pk),data);self.assertEqual(r.status_code,302)
        obj.usuario.refresh_from_db();self.assertEqual(before,(obj.usuario.is_superuser,obj.usuario.is_staff,list(obj.usuario.groups.values_list('pk',flat=True))))
        role=self.rows[1]['roles'];old=role.grupo_id;data=self.payload('roles');data['grupo']=Group.objects.get(name='Acceso total').pk
        self.assertEqual(self.client.post(self.url('editar','roles',role.pk),data).status_code,302);role.refresh_from_db();self.assertEqual(old,role.grupo_id)
    def test_credential_login_logout_and_csrf(self):
        c=Client(enforce_csrf_checks=True)
        self.assertEqual(c.get('/gestion/').status_code,302)
        self.assertEqual(c.post('/login/',{'username':'invalido','password':'invalida'}).status_code,403)
        r=c.get('/login/');token=c.cookies['csrftoken'].value
        self.assertEqual(c.post('/login/',{'username':'prueba_total','password':'invalida','csrfmiddlewaretoken':token}).status_code,400)
        self.assertEqual(c.post('/login/',{'username':'prueba_total','password':'SoloPruebaAislada123!','csrfmiddlewaretoken':token}).status_code,302)
        self.assertEqual(c.get('/logout/').status_code,405);self.assertEqual(c.get('/gestion/').status_code,200)
        self.assertEqual(c.post('/logout/').status_code,403)
        token=c.cookies['csrftoken'].value
        self.assertEqual(c.post('/logout/',{'csrfmiddlewaretoken':token}).status_code,302)
        self.assertEqual(c.get('/gestion/').status_code,302)
    def test_safe_next_and_search(self):
        for target in ('//evil.example/','https://evil.example/','javascript:alert(1)'):
            c=Client();r=c.post('/login/?next='+target,{'username':'prueba_total','password':'SoloPruebaAislada123!'})
            self.assertEqual(r['Location'],'/')
        r=self.client.get('/buscar/',{'q':'ficticia'});self.assertEqual(r.status_code,200);self.assertContains(r,'/gestion/')
        before=Actividad.objects.count();self.assertEqual(self.client.get('/buscar/',{'q':"' OR 1=1;--"}).status_code,200);self.assertEqual(before,Actividad.objects.count())
        self.assertEqual(self.client.get('/gestion/no-existe/').status_code,404)
    def test_unique_codes_email_and_preserved_errors(self):
        data=self.payload('vecinos');data['correo']='no-es-correo';obj=self.rows[1]['vecinos'];before=obj.correo
        r=self.client.post(self.url('editar','vecinos',obj.pk),data);self.assertEqual(r.status_code,200);obj.refresh_from_db();self.assertEqual(before,obj.correo);self.assertContains(r,'no-es-correo')
        data=self.payload('actividades',new=True);data['codigo']=self.rows[1]['actividades'].codigo
        self.assertFalse(forms.ActividadForm(data=data).is_valid())
    def test_post_without_csrf_does_not_write(self):
        c=Client(enforce_csrf_checks=True);c.force_login(self.users['total']);obj=self.rows[1]['actividades'];before=Actividad.objects.count()
        self.assertEqual(c.post(self.url('crear','actividades'),self.payload('actividades',new=True)).status_code,403)
        self.assertEqual(c.post(self.url('borrar','actividades',obj.pk)).status_code,403);self.assertEqual(before,Actividad.objects.count())


def crud_test(slug):
    def test(self):
        model=SPECS[slug][1]._meta.model;obj=self.rows[1][slug]
        for action,pk in [('lista',None),('detalle',obj.pk),('crear',None),('editar',obj.pk),('borrar',obj.pk)]:
            self.assertEqual(self.client.get(self.url(action,slug,pk)).status_code,200,(slug,action))
        ids=set(model.objects.values_list('pk',flat=True))
        data=self.payload(slug,new=True)
        r=self.client.post(self.url('crear',slug),data)
        self.assertEqual(r.status_code,302,(slug, getattr(r,'context',None) and r.context['form'].errors))
        new_ids=set(model.objects.values_list('pk',flat=True))-ids;self.assertEqual(len(new_ids),1);pk=new_ids.pop();obj=model.objects.get(pk=pk)
        data=self.payload(slug,obj=obj)
        r=self.client.post(self.url('editar',slug,pk),data);self.assertEqual(r.status_code,302,(slug,getattr(r,'context',None) and r.context['form'].errors));self.assertEqual(model.objects.count(),len(ids)+1)
        count_before=model.objects.count();self.assertEqual(self.client.post(self.url('editar',slug,pk),{}).status_code,200);self.assertEqual(model.objects.count(),count_before)
        self.assertEqual(self.client.get(self.url('borrar',slug,pk)).status_code,200);self.assertTrue(model.objects.filter(pk=pk).exists())
        self.assertEqual(self.client.post(self.url('borrar',slug,pk)).status_code,302);self.assertFalse(model.objects.filter(pk=pk).exists())
    return test

def permissions_test(slug):
    def test(self):
        obj=self.rows[1][slug]
        for role in ('total','intermedio','minimo'):
            self.client.force_login(self.users[role]);can_write=role=='total' or (role=='intermedio' and SPECS[slug][2])
            for action,pk in [('lista',None),('detalle',obj.pk)]: self.assertEqual(self.client.get(self.url(action,slug,pk)).status_code,200)
            for action,pk in [('crear',None),('editar',obj.pk)]:
                self.assertEqual(self.client.get(self.url(action,slug,pk)).status_code,200 if can_write else 403,(slug,role,action,'GET'))
                self.assertEqual(self.client.post(self.url(action,slug,pk),{}).status_code,200 if can_write else 403,(slug,role,action,'POST'))
            self.assertEqual(self.client.get(self.url('borrar',slug,obj.pk)).status_code,200 if role=='total' else 403)
            self.assertEqual(self.client.post(self.url('borrar',slug,999999)).status_code,404 if role=='total' else 403)
            if role == 'intermedio' and can_write:
                model=SPECS[slug][1]._meta.model
                ids=set(model.objects.values_list('pk',flat=True))
                response=self.client.post(self.url('crear',slug),self.payload(slug,new=True))
                self.assertEqual(response.status_code,302,(slug,'intermedio valid create'))
                new_ids=set(model.objects.values_list('pk',flat=True))-ids
                self.assertEqual(len(new_ids),1)
                fresh=model.objects.get(pk=new_ids.pop())
                self.assertEqual(self.client.post(self.url('editar',slug,fresh.pk),self.payload(slug,obj=fresh)).status_code,302)
                self.assertEqual(self.client.post(self.url('borrar',slug,fresh.pk)).status_code,403)
                self.assertTrue(model.objects.filter(pk=fresh.pk).exists())
            if not can_write:
                model=SPECS[slug][1]._meta.model
                before=model.objects.count()
                self.assertEqual(self.client.post(self.url('crear',slug),self.payload(slug,new=True)).status_code,403)
                self.assertEqual(before,model.objects.count())
            response=self.client.get(self.url('lista',slug))
            if not can_write: self.assertNotContains(response,self.url('crear',slug));self.assertNotContains(response,self.url('editar',slug,obj.pk))
            if role!='total': self.assertNotContains(response,self.url('borrar',slug,obj.pk))
        self.client.logout()
        for action,pk in [('lista',None),('detalle',obj.pk),('crear',None),('editar',obj.pk),('borrar',obj.pk)]:
            self.assertEqual(self.client.get(self.url(action,slug,pk)).status_code,302)
            self.assertEqual(self.client.post(self.url(action,slug,pk),{}).status_code,302)
    return test

def missing_test(slug):
    def test(self):
        for action in ('detalle','editar','borrar'):
            self.assertEqual(self.client.get(self.url(action,slug,999999)).status_code,404)
            self.assertEqual(self.client.post(self.url(action,slug,999999),{}).status_code,404 if action!='detalle' else 405)
    return test

for slug in SPECS:
    setattr(Evaluation3Tests,'test_crud_'+slug,crud_test(slug))
    setattr(Evaluation3Tests,'test_permissions_'+slug,permissions_test(slug))
    setattr(Evaluation3Tests,'test_missing_'+slug,missing_test(slug))
