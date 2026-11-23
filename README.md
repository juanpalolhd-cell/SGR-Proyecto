# SGR — Tercera evaluación Back End: CRUD y seguridad

Actualización local: 8 de noviembre de 2026; despliegue en AWS: 13 de noviembre de 2026; documentación AWS actualizada el 16 de noviembre de 2026 (America/Santiago). Pauta: «Tercera evaluación de Back End — CRUD y seguridad · Caso SGR», 7 páginas. La revisión no constituye una nota ni certificación del despliegue.

## Integrantes y aportes

| Integrante | Aporte específico |
|---|---|
| Juan Ossandon | Codigo |
| Vicente Garrido | Diseño |
| Bastian Tapia | Codigo |
| Wilson Choque | Seguridad |

Hubo asistencia de IA para análisis, implementación, migraciones, documentación y pruebas. La verificación automatizada se describe en Evidencias.pdf y evidencias.md; cada integrante debe revisar el código y explicar una operación CRUD, una validación y un permiso. No se atribuyen aportes humanos no confirmados.

## Inicio local seguro

Desde la carpeta del proyecto, con el entorno virtual activado:

```console
python -m pip install -r requirements.txt
python manage.py migrate --settings=sgr.settings_pruebas
python manage.py setup_roles --settings=sgr.settings_pruebas
python manage.py demo_evaluacion --settings=sgr.settings_pruebas
python manage.py auditar_evaluacion --settings=sgr.settings_pruebas
python manage.py runserver --settings=sgr.settings_pruebas
```

En una instalación totalmente nueva, crear primero un administrador mediante `python manage.py createsuperuser --settings=sgr.settings_pruebas` (entrada privada interactiva, no documentar su contraseña). Desde el Admin protegido se configuran las cuentas normales y sus grupos para evaluación. En la BD existente no se restablecen cuentas.

También puede ejecutar `iniciar_local.bat` o `ejecutar.bat` si `venv\Scripts\python.exe` ya está instalado. Abrir http://127.0.0.1:8000/ y entrar con una cuenta existente. La gestión completa se encuentra en `/gestion/`. `sgr.settings_pruebas` fuerza SQLite local, no lee .env y no utiliza DB_HOST/DB_ENGINE del sistema. Su clave fija es exclusivamente de desarrollo/pruebas: nunca utilizar esos settings en AWS.

`demo_evaluacion` añade dos muestras ficticias por cada entidad y algunos estados inactivos. Es idempotente: no borra ni sobrescribe registros existentes. Las cuentas técnicas de muestra se crean desactivadas y con contraseña inutilizable, no son cuentas de acceso de evaluación. `seed_data` ahora es un alias NO destructivo de este comando. No ejecutar el comando antiguo desde un respaldo anterior: ese sí eliminaba datos.

## Versiones y alcance de comprobación

Local (copia aislada Linux): Python 3.13.5, Django 5.2.18 y SQLite 3.46.1; en el PC se verificaron Python 3.13.5, Django 5.2.17 y SQLite 3.49.1. La versión final pasó las 84 pruebas tanto en la copia aislada como en la carpeta original. Los módulos antiguos también exigen permiso de consulta, evitando accesos por URLs heredadas de usuarios sin grupo.

Servidor AWS (verificado el 13/11/2026): Python 3.12, Django 5.2.18, mysqlclient 2.3.0, Gunicorn 23.0.0, nginx 1.30.6 y MySQL 8.4.11 (Amazon RDS). `requirements.txt` fija Django==5.2.18 y deja rangos compatibles para mysqlclient (>=2.2,<3.0) y Gunicorn (>=23.0,<24.0), que incluyen las versiones instaladas en el servidor. mysqlclient y Gunicorn no se usan en el entorno local con SQLite.

## Modelo y pantallas: 17 entidades

Cada ruta ofrece listado, detalle, crear, editar y eliminar con confirmación, según permisos. Se conservan nombres internos antiguos para no perder claves ni relaciones.

| Entidad de pauta | Modelo Django | Ruta |
|---|---|---|
| Delegación | organizacion.Unidad | /gestion/delegaciones/ |
| Territorio | organizacion.Territorio | /gestion/territorios/ |
| Usuario funcionario | organizacion.Persona + auth.User | /gestion/funcionarios/ |
| Cargo | organizacion.Cargo | /gestion/cargos/ |
| Rol | organizacion.Rol + auth.Group | /gestion/roles/ |
| Vecino | organizacion.Vecino | /gestion/vecinos/ |
| Junta de vecinos | organizacion.JuntaVecinos | /gestion/juntas/ |
| Participación en junta | organizacion.Participacion | /gestion/participaciones/ |
| Hito | agenda.Hito | /gestion/hitos/ |
| Actividad | actividades.Actividad | /gestion/actividades/ |
| Gestión social | actividades.GestionSocial | /gestion/gestiones/ |
| Tipo de atención | organizacion.TipoAtencion | /gestion/tipos/ |
| Subtipo de atención | organizacion.SubAtencion | /gestion/subtipos/ |
| Meta (catálogo) | resultados.CatalogoMeta | /gestion/metas/ |
| Asignación de meta | resultados.Meta | /gestion/asignaciones/ |
| Evidencia | actividades.Evidencia | /gestion/evidencias/ |
| Trimestre | resultados.Periodo | /gestion/trimestres/ |

Relaciones: Territorio → Delegación; Funcionario → User/Cargo/Delegación y roles relacionales; Rol → Group; Vecino → Territorio; Junta → Delegación/Territorio; Participación → Vecino/Junta; Hito → Delegación/Territorio y responsables M2M; Asignación → Funcionario/Meta/Trimestre; Actividad → Funcionario/Asignación/Hito opcional/Solicitante/Territorio/Responsable; Gestión → Beneficiario/Tipo/Subtipo/Asignación; Evidencia → exactamente una Actividad o Gestión, autor User y verificador User opcional.

Los cargos describen la función laboral; los grupos Django son la autoridad de acceso. Los roles relacionados y su grupo se muestran, pero los formularios generales no conceden grupos/permisos. Su configuración efectiva es responsabilidad del administrador en el Admin protegido. La asociación de Rol.grupo es de solo lectura en el sitio general. No se sincronizan privilegios a partir de un texto enviado por el usuario.

## Matriz de permisos explícita

| Entidades | Acceso total | Intermedio / Gestión | Minimo / Consulta |
|---|---|---|---|
| Delegaciones, territorios, funcionarios, cargos, roles, vecinos, juntas, participaciones, tipos, subtipos | Consultar, crear, editar, eliminar | Solo consultar | Solo consultar |
| Hitos, actividades, gestiones sociales, metas, asignaciones, evidencias, trimestres | Consultar, crear, editar, eliminar | Consultar, crear, editar; nunca eliminar | Solo consultar |
| Administración de grupos, permisos y atributos privilegiados | Administrador autorizado, medio protegido | Prohibido | Prohibido |

Se reutilizan los grupos `Acceso total`, `Intermedio` y `Minimo`; el comando `setup_roles` SIN `--create-users` actualiza sus permisos, sin cambiar usuarios ni contraseñas. No invocar sus opciones históricas de creación de usuarios en una BD con cuentas existentes. Las opciones se conservan por compatibilidad, pero ahora también omiten las cuentas que ya existen sin cambiarles contraseña, atributos ni grupos. No son necesarias para instalar esta actualización.

Cuentas previstas ya utilizadas por el proyecto: `sgr_total`, `sgr_intermedio` y `sgr_minimo`, si existen en la BD que se usa. No se han creado ni restablecido esas cuentas en la BD del PC durante esta actualización. La suite crea cuentas exclusivamente en su BD de pruebas para demostrar los tres niveles, incluido un total NO superusuario. Si faltan las cuentas normales de evaluación en la BD elegida, un administrador debe configurarlas por el medio protegido. Entregar sus credenciales fuera de repositorios abiertos; este documento no contiene contraseñas ni hashes.

Todas las vistas requieren autenticación. Acceso sin sesión: redirección al login. Autenticado sin permiso: 403. Botones sujetos al mismo permiso que el servidor. Inicio de sesión por usuario/contraseña, sin correo. Logout solo POST y CSRF. Se valida el destino `next` contra el host permitido.

## Validaciones e integridad

ModelForm valida obligatoriedad, tipos, longitudes, opciones, correos, códigos y RUT únicos. Códigos vacíos de modelos que los permiten se generan al guardar; no se exige un formato especial. RUTs de muestras son ficticios y no representan personas reales; no se valida padrón externo.

Se comprueban fechas ordenadas, compromiso no anterior al ingreso de Actividad, objetivo > 0, ponderación 0–100, número de trimestre 1–4, territorio/delegación, tipo/subtipo, funcionario/asignación y coherencia de los responsables y antecedentes. Restricciones de BD refuerzan objetivo, ponderación, trimestre/fechas y origen único de Evidencia. No se impone una suma de ponderaciones ni se calcula cumplimiento en las pantallas nuevas.

La baja física solo procede con POST y confirmación. Se utiliza PROTECT para conservar antecedentes y mensajes comprensibles ante ProtectedError. Si hay dependencias se rechaza el borrado; un usuario con permiso de edición puede cambiar `estado` a inactivo/anulado. Cancelar y GET no alteran registros. Para relaciones opcionales como delegado, puede ser necesario desvincularlo justificadamente antes de eliminar un registro sin otros antecedentes. No se elimina una cuenta Django al borrar su perfil de funcionario.

Evidencia registra metadatos y una referencia ficticia de archivo: no hay subida/descarga de documentos. Su autor/verificador son relaciones, no contraseñas ni texto de autoridad.

## Continuidad y migración sin reinicio de datos

Se amplían las tablas existentes Unidad, Persona, Actividad, Evidencia, Meta y Periodo. Meta anterior se conserva como Asignación; se incorpora CatalogoMeta. Los PK originales siguen válidos. Las tablas duplicadas Delegacion, PerfilUsuario e Item se conservan como archivo histórico de solo lectura en Admin: Delegacion y PerfilUsuario se integran en Unidad/Persona sin borrar las tablas originales. Item permanece como archivo histórico, no como una entidad obligatoria adicional.

La migración `organizacion.0004_integrar_datos_historicos` no modifica contraseñas ni atributos de cuentas existentes. Crea identidades técnicas desactivadas/no autenticables para personas y autorías históricas sin cuenta conocida. Esas identidades no prueban identidad real ni son cuentas para iniciar sesión. Cuando faltan datos de la evaluación nueva, se conservan como pendientes: no se inventan territorios, vecinos ni asignaciones para actividades antiguas. Los placeholders históricos deben revisarse antes de presentar esos registros.

Las delegaciones pueden darse de alta inicialmente sin delegado para resolver el ciclo Delegación ↔ Funcionario; luego se asigna un funcionario de esa delegación. Las relaciones nuevas de los registros antiguos pueden ser nulas solo por compatibilidad histórica; los formularios de operación requieren completarlas. `auditar_evaluacion` informa conteos sin datos privados. En la copia histórica revisada quedan 5 delegaciones sin delegado y 8 actividades que requieren completar los nuevos antecedentes. Las dos muestras nuevas por entidad sí pasan validación.

La comprobación de migración comparó las columnas originales de todas las tablas de negocio y las cuentas originales, tanto en copia como en el PC instalado: 72 filas de 15 tablas conservadas, cero filas originales desaparecidas o alteradas. Se ensayó tanto BD limpia como copia de la BD existente. Las restricciones nuevas podrían rechazar datos históricos inválidos en otra BD: auditar y respaldar antes; no corregir ni borrar valores reales automáticamente.

## Pruebas y evidencias

```console
python manage.py check --settings=sgr.settings_pruebas
python manage.py makemigrations --check --dry-run --settings=sgr.settings_pruebas
python manage.py test --settings=sgr.settings_pruebas --noinput
```

84 tests aprobados en la copia aislada. Hay matriz CRUD/roles de las 17 entidades, acceso directo GET/POST, validaciones, errores sin guardado, integridad referencial, login/logout, CSRF, 404 y next seguro. Los tests usan una BD de prueba, nunca producción. Se actualizaron pruebas antiguas para logout POST y formularios completos, manteniendo regresiones de las URLs anteriores; sus escrituras utilizan el mismo CRUD validado mediante sgr.legacy.

`Evidencias.pdf` (42 páginas) documenta los resultados automatizados reales, la verificación del despliegue en AWS y 43 capturas de pantalla reales tomadas el 13/11/2026 en http://44.213.253.178/, con fecha, hora, usuario y URL; las mismas imágenes están en `capturas_evidencia/` y se describen en `evidencias.md`. No incluye capturas inventadas ni editadas y ninguna muestra contraseñas. La sección «Pendientes que NO se declaran aprobados» de ese documento enumera lo que queda por completar.

## AWS — despliegue verificado (13/11/2026)

URL: http://44.213.253.178/ . El 13/11/2026 se desplegó en AWS el mismo código de esta entrega (hashes SHA-256 de los archivos de la aplicación idénticos a los del ZIP) y se verificó su funcionamiento.

- Infraestructura: instancia EC2 `sgr-app` (Amazon Linux 2023) con IP elástica 44.213.253.178; nginx 1.30.6 como proxy inverso y Gunicorn 23.0.0 ejecutando Django 5.2.18 sobre Python 3.12; base de datos persistente Amazon RDS MySQL 8.4.11 (`sgr-mysql`) sin acceso público, con conector mysqlclient 2.3.0.
- Configuración: `sgr.settings` con variables de entorno guardadas en un archivo privado del servidor, fuera del código y del repositorio: DJANGO_SECRET_KEY, DJANGO_DEBUG=False, DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS y DB_*. `sgr.settings` se niega a arrancar sin clave cuando DEBUG está desactivado.
- Puesta en marcha: respaldo previo de la aplicación, de la configuración y de la BD (más una instantánea de RDS); migraciones aplicadas sin pendientes; `setup_roles` sin `--create-users` (no se crearon ni restablecieron cuentas); `demo_evaluacion` no destructivo; `collectstatic` para los estáticos que entrega nginx.
- Verificación: inicio y cierre de sesión (logout solo POST; GET responde 405), matriz de permisos con cuentas normales Consulta y Gestión (403 por URL directa), CRUD de las 17 entidades, persistencia en RDS (registro de prueba creado, comprobado y eliminado), borrado protegido con mensaje, formulario inválido sin guardar, CSRF y 404. Resultados y capturas en `Evidencias.pdf`.

Consideraciones:

- El sitio funciona por HTTP, sin HTTPS. No reutilizar contraseñas personales en estas cuentas de prueba; HTTPS es recomendable para un uso real.
- El entorno es AWS Academy: para que la URL responda, el laboratorio debe estar iniciado (EC2 y RDS en ejecución). Las credenciales de AWS Academy son temporales y no forman parte de la entrega.
- Las credenciales de las cuentas de prueba (Consulta y Gestión) se entregan por un medio privado; este README no contiene contraseñas ni hashes.

No copiar SQLite a RDS ni las credenciales del servidor al proyecto. No usar `sgr.settings_pruebas` ni el servidor de desarrollo como producción.

## Respaldo y restauración

Antes de cualquier cambio se creó en el Escritorio `back_end_respaldo_20261108_182541.zip`, con código y `db.sqlite3`, además de notas `RESTAURAR.txt` en la carpeta homónima. No incluye venv, .env/claves privadas ni archivos sueltos desconocidos. Para restaurar: detener Django local, conservar/renombrar la carpeta actual y recuperar juntos código y SQLite del respaldo; reutilizar o recrear el entorno. No intentar revertir esta integración de datos borrando filas; usar el respaldo completo. El respaldo es privado y no forma parte de la entrega académica.

## ZIP de entrega

`Equipo_BackEnd_Evaluacion3.zip` incluye código, migraciones, templates, estáticos, JSON ficticios, dependencias, README, `Evidencias.pdf`, `evidencias.md` y la carpeta `capturas_evidencia/` (43 capturas). Excluye venv, __pycache__, BD privada, .env, claves, contraseñas reales, respaldos y temporales. No es un respaldo de datos. Conservar por separado las credenciales privadas y demostrar las dos cuentas normales por el medio que indique la docente.
