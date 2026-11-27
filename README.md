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

## V4.1 — Tubo de trabajo, reglas del cliente y gestión de contraseñas (26/11/2026)

Todo está en el sitio público, no en Django Admin.

**Tubo de trabajo** (menú «Tubo de trabajo» → `/agenda/`; «Hitos» sigue en `/gestion/hitos/`)
- `Compromiso.estado` tiene ahora 4 estados controlados: Ingresado, Pendiente, En proceso y Realizado. Transiciones permitidas, validadas en `Compromiso.clean()`: Ingresado → Pendiente o En proceso; Pendiente ↔ En proceso; Pendiente o En proceso → Realizado; Realizado → En proceso (reapertura, con observación obligatoria). Un compromiso nuevo nace Ingresado o Pendiente.
- Migración `agenda.0005` normaliza los estados antiguos sin borrar nada. Los sinónimos («en_proceso», «realizada»…) pasan a su estado canónico y los valores desconocidos pasan a Pendiente. El valor original queda en observaciones y en el historial, y migrate lo informa por pantalla. Es reversible.
- Plazos: se marcan como vencido, próximo a vencer (umbral `dias_aviso_vencimiento` en `data/resultados.json`, por defecto 7 días), en plazo, realizado y realizado fuera de plazo. Aparecen en la lista (fila destacada), en el detalle y en el resumen, y hay filtros por estado, plazo, responsable y delegación.
- `HistorialEstado` guarda cada cambio de estado o de fecha comprometida: usuario, fecha, estado anterior y nuevo, y observación. Se muestra en el detalle. Cambiar la fecha exige indicar el motivo.
- Resumen (`/agenda/resumen/`): totales por estado, por responsable y por delegación, con % realizado y % pendiente, vencidos, próximos y fuera de plazo, y filtro por rango de fechas.
- Permisos: no cambian para Compromiso. Consulta solo ve; Gestión crea y edita; Acceso total además elimina. `HistorialEstado` es de solo lectura para los tres roles. `setup_roles` (idempotente) deja: Acceso total=85, Intermedio=38, Minimo=22 permisos.

**Reglas del cliente**
- RN-001: al guardar una asignación se bloquea si la suma de ponderaciones del funcionario en el trimestre supera 100 %. Si queda bajo 100 % solo se advierte, porque las asignaciones se registran de a una y los datos existentes tienen sumas de 50 %. La suma también se muestra en el tablero y en la ficha.
- RN-003/RN-009: el avance calculado cuenta las actividades válidas (Validada, Aprobada o Realizada) y las gestiones atendidas del período. Si el catálogo exige evidencia, solo cuentan las que tienen una evidencia Aprobada; las Rechazadas o Anuladas nunca cuentan. Se muestra junto al avance manual. El indicador usa el avance indicado en el parámetro `fuente_avance` («manual» por defecto, para no alterar los resultados históricos; «calculado» aplica la regla completa). El avance manual nunca se sobrescribe.
- RN-006: el tablero y el informe calculan el cumplimiento colectivo por delegación (promedio del total ponderado de quienes tienen metas) y lo comparan con `umbral_colectivo`.
- RN-007: la meta esperada al día usa la fecha real (`date.today()`) con el inicio y el término del período, en días corridos y con un máximo de 100 %. Ya no usa 15 días fijos. El tablero, el informe y la ficha permiten elegir el período; por defecto muestran el vigente.
- RN-010: el código es de solo lectura al editar.
- RN-012: se permiten como máximo 3 gestiones activas (no anuladas) por persona usuaria.
- RN-013: un período Cerrado bloquea crear, editar y eliminar sus asignaciones, actividades, gestiones y evidencias, así como editar o eliminar el propio período. Solo Acceso total puede reabrirlo, y la reapertura queda en el log `sgr.auditoria`.
- Teléfono (Vecino y Actividad): `RegexValidator`, por ejemplo +56 9 1234 5678.
- Evidencia y trimestre: el estado se elige de una lista (Registrada, Pendiente, Aprobada, Rechazada o Anulada; Abierto o Cerrado). Un valor antiguo distinto se conserva.
- RN-011 (felicitaciones y penalizaciones): no se implementa. La guía indica que sus valores «requieren definición oficial». Queda como trabajo futuro.

**Gestión de contraseñas**
- `/cuenta/clave/` (enlace «Cambiar contraseña» en el menú): cualquier usuario con sesión cambia su contraseña indicando la actual (`PasswordChangeView` y `PasswordChangeDoneView`).
- `/cuenta/funcionarios/<id>/clave/`, solo Acceso total (o superusuario): establece la contraseña inicial o la restablece con `SetPasswordForm`, de modo que se aplican `AUTH_PASSWORD_VALIDATORS`. Hay un enlace desde el detalle del funcionario y desde el aviso que aparece después de crear un funcionario con `nuevo_usuario`. No permite tomar cuentas staff o superusuario si quien lo hace no es superusuario, y para la propia cuenta deriva a «Cambiar contraseña». La contraseña nunca se muestra, ni se registra, ni se envía.
- El detalle del funcionario indica si la contraseña está «Establecida» o «Pendiente» (nunca muestra el hash).
- La recuperación por correo se agregó en la V4.2 (ver la sección siguiente).

## V4.2 — Contraseña temporal, cambio obligatorio y recuperación por correo (26/11/2026)

Todo está en el sitio público (no en Django Admin) y en español.

**Contraseña temporal** (`/cuenta/funcionarios/<id>/clave/`, solo Acceso total)
- Al crear un funcionario con `nuevo_usuario`, el aviso del detalle ofrece «Generar contraseña temporal»; la misma opción existe para restablecer una cuenta.
- Se genera con `secrets` (16 caracteres, con minúsculas, mayúsculas, dígitos y símbolos, sin caracteres ambiguos) y se comprueba con `AUTH_PASSWORD_VALIDATORS`. Solo se guarda el hash.
- Se muestra **una sola vez** en la página de confirmación (respuesta `no-store`). No se escribe en logs, ni en `messages`, ni en la base de datos.
- Opcionalmente se envía por correo, solo si la cuenta tiene correo y el servidor tiene SMTP configurado. Con los backends de consola o de archivo no se ofrece, porque escribirían la contraseña en la consola o en disco.
- Vence después de `SGR_CLAVE_TEMPORAL_HORAS` (72 por defecto). Después, el inicio de sesión se rechaza con el mensaje «Su contraseña temporal venció…», y una sesión abierta con ella se cierra.
- La contraseña escrita a mano por Acceso total se trata igual: obliga a cambiarla y vence en el mismo plazo.

**Cambio obligatorio al primer ingreso**
- Modelo `organizacion.EstadoClave` (uno a uno con User): `debe_cambiar_clave`, `marcado_en`, `motivo`, `vence_en` y `cambiada_en`. No guarda contraseñas. Las cuentas existentes no tienen registro y por eso no se ven afectadas: no se restableció ninguna contraseña.
- `sgr.middleware.CambioClaveObligatorioMiddleware` redirige a `/cuenta/clave/` mientras la bandera esté activa. Solo permite esa página, el cierre de sesión y `/static/`.
- Al cambiarla, `PasswordChangeView` llama a `update_session_auth_hash`: la sesión actual sigue y las demás sesiones de la cuenta quedan invalidadas. La bandera se limpia.
- `sgr.backends.ClaveTemporalBackend` (en `AUTHENTICATION_BACKENDS`) rechaza las contraseñas asignadas vencidas, también en `/admin/`.
- `setup_roles` no da permisos sobre `EstadoClave` a ningún grupo (sigue siendo idempotente: 85/38/22).

**Recuperación por correo** (`/cuenta/recuperar/`, enlace «¿Olvidó su contraseña?» en el login)
- Usa las vistas de Django `PasswordResetView`, `Done`, `Confirm` y `Complete`, con plantillas en español.
- El enlace sirve una sola vez (generador de tokens de Django) y vence según `DJANGO_PASSWORD_RESET_TIMEOUT` (3600 s por defecto).
- Siempre da la misma respuesta, exista o no el correo. Las cuentas inactivas o sin contraseña utilizable no reciben correo.
- Límite con la caché: `SGR_RECUPERACION_LIMITE` (5) solicitudes por `SGR_RECUPERACION_VENTANA` (3600 s), por IP (responde 429) y por correo (respuesta genérica, sin enviar). Detrás de nginx use `SGR_PROXY_IP_HEADER=HTTP_X_FORWARDED_FOR`. Con varios procesos de gunicorn use `SGR_CACHE=db` y `manage.py createcachetable`.
- El enlace se arma con `SGR_URL_PUBLICA` (por ejemplo `https://sgr.ejemplo.cl`) o, si falta, con el host de la petición. **En producción debe usarse HTTPS**: por HTTP el enlace y la contraseña nueva viajan sin cifrar. El kit HTTPS deja `SGR_URL_PUBLICA` en https.
- Correo: `DJANGO_EMAIL_BACKEND` y `DJANGO_EMAIL_HOST`, `_PORT`, `_USE_TLS`, `_USE_SSL`, `_HOST_USER`, `_HOST_PASSWORD` y `DJANGO_DEFAULT_FROM_EMAIL` se leen solo del entorno (`/etc/sgr/sgr.env` en el servidor; marcadores en `.env.example`). En local (`settings_pruebas`) se usa la consola; en producción sin configuración se usa `dummy` y el sitio indica que la recuperación no está disponible.
- Pruebas: 22 nuevas en `sgr/tests_v42.py`, con correo `locmem`.

## HTTPS — preparado en el kit, pendiente de activar (26/11/2026)

Estado honesto: **HTTPS está configurado en el kit de despliegue, pero todavía no está activo en AWS**. El 26/11/2026 el laboratorio estaba apagado (44.213.253.178 no responde y las credenciales de AWS Academy estaban vencidas), así que no se pudo activar. Mientras no se ejecute el kit, el sitio sigue en `http://44.213.253.178/`.

- Código (`sgr/settings.py`), todo por variables de entorno para que el desarrollo local siga por HTTP: `DJANGO_SECURE_PROXY_SSL_HEADER` (confía en `X-Forwarded-Proto` de nginx), `DJANGO_SECURE_COOKIES` (cookies de sesión y CSRF solo por HTTPS), `DJANGO_SECURE_SSL_REDIRECT` (opcional; nginx ya redirige), `DJANGO_SECURE_HSTS_SECONDS` y las opciones de subdominios y preload (desactivadas). Con `DJANGO_DEBUG=False` las dos primeras quedan activas por defecto, igual que antes.
- Kit `SGR_HTTPS_despliegue/activar_https.sh` (idempotente): respalda nginx y `sgr.env`; instala certbot (dnf o pip); usa `44-213-253-178.sslip.io` (o el nombre que se indique); pide un certificado de Let's Encrypt por webroot y, si falla, usa uno autofirmado y lo avisa; configura 443 (TLS 1.2/1.3), la redirección 80 → 443 y HSTS moderado (3600 s, solo con Let's Encrypt); deja la renovación automática con un temporizador de systemd; agrega el nombre a `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS`, cambia `SGR_URL_PUBLICA` a https y activa las opciones seguras sin mostrar valores; reinicia; hace la prueba de humo (login, redirección, admin, estáticos, cookie Secure, POST con y sin CSRF) y deja un `revertir.sh`.
- Se probó en una simulación local (nginx real, Django en modo producción): ruta con Let's Encrypt simulado, ruta de respaldo autofirmado, segunda ejecución sin cambios y reversión a HTTP.
- Pruebas: 149 aprobadas (138 + 11 de HTTPS en `sgr/tests_https.py`).
- Requiere abrir el puerto 443 en el grupo de seguridad de la instancia (instrucciones en el kit).
- `sslip.io` es un servicio DNS gratuito de terceros: si deja de funcionar, el nombre no resolverá. Para uso real conviene un dominio propio.

## Pruebas y evidencias

```console
python manage.py check --settings=sgr.settings_pruebas
python manage.py makemigrations --check --dry-run --settings=sgr.settings_pruebas
python manage.py test --settings=sgr.settings_pruebas --noinput
```

149 tests aprobados en la copia aislada (84 anteriores + 32 de V4.1 en `sgr/tests_v41.py` + 22 de V4.2 en `sgr/tests_v42.py` + 11 de HTTPS en `sgr/tests_https.py`). Hay matriz CRUD/roles de las 17 entidades, acceso directo GET/POST, validaciones, errores sin guardado, integridad referencial, login/logout, CSRF, 404 y next seguro. Los tests usan una BD de prueba, nunca producción. Se actualizaron pruebas antiguas para logout POST y formularios completos, manteniendo regresiones de las URLs anteriores; sus escrituras utilizan el mismo CRUD validado mediante sgr.legacy.

`Evidencias.pdf` (42 páginas) documenta los resultados automatizados reales, la verificación del despliegue en AWS y 43 capturas de pantalla reales tomadas el 13/11/2026 en http://44.213.253.178/, con fecha, hora, usuario y URL; las mismas imágenes están en `capturas_evidencia/` y se describen en `evidencias.md`. No incluye capturas inventadas ni editadas y ninguna muestra contraseñas. La sección «Pendientes que NO se declaran aprobados» de ese documento enumera lo que queda por completar.

## AWS — despliegue verificado (13/11/2026)

URL: http://44.213.253.178/ . El 13/11/2026 se desplegó en AWS el mismo código de esta entrega (hashes SHA-256 de los archivos de la aplicación idénticos a los del ZIP) y se verificó su funcionamiento.

- Infraestructura: instancia EC2 `sgr-app` (Amazon Linux 2023) con IP elástica 44.213.253.178; nginx 1.30.6 como proxy inverso y Gunicorn 23.0.0 ejecutando Django 5.2.18 sobre Python 3.12; base de datos persistente Amazon RDS MySQL 8.4.11 (`sgr-mysql`) sin acceso público, con conector mysqlclient 2.3.0.
- Configuración: `sgr.settings` con variables de entorno guardadas en un archivo privado del servidor, fuera del código y del repositorio: DJANGO_SECRET_KEY, DJANGO_DEBUG=False, DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS y DB_*. `sgr.settings` se niega a arrancar sin clave cuando DEBUG está desactivado.
- Puesta en marcha: respaldo previo de la aplicación, de la configuración y de la BD (más una instantánea de RDS); migraciones aplicadas sin pendientes; `setup_roles` sin `--create-users` (no se crearon ni restablecieron cuentas); `demo_evaluacion` no destructivo; `collectstatic` para los estáticos que entrega nginx.
- Verificación: inicio y cierre de sesión (logout solo POST; GET responde 405), matriz de permisos con cuentas normales Consulta y Gestión (403 por URL directa), CRUD de las 17 entidades, persistencia en RDS (registro de prueba creado, comprobado y eliminado), borrado protegido con mensaje, formulario inválido sin guardar, CSRF y 404. Resultados y capturas en `Evidencias.pdf`.

Estado de V4.1 y V4.2 en AWS: **todavía no desplegadas**. El 26/11/2026 el laboratorio estaba apagado (44.213.253.178 no responde), así que AWS sigue ejecutando la versión del 13/11. El paquete y el script de despliegue (`sgr_v42_deploy.tgz` y `deploy_v42.sh`, que incluyen la V4.1; el script respalda la app, la configuración y la BD, y luego ejecuta migrate, createcachetable, setup_roles sin crear usuarios, collectstatic, reinicio y prueba de humo) se entregan aparte, junto al ZIP. El correo real requiere completar las variables SMTP en `/etc/sgr/sgr.env`. Después de la V4.2 se activa HTTPS con `activar_https.sh` (ver sección HTTPS).

Consideraciones:

- El sitio desplegado funciona todavía por HTTP. HTTPS está preparado en el kit `SGR_HTTPS_despliegue` y queda pendiente de activar cuando el laboratorio esté encendido; después la URL será `https://44-213-253-178.sslip.io/`. Hasta entonces, no reutilizar contraseñas personales en estas cuentas de prueba.
- El entorno es AWS Academy: para que la URL responda, el laboratorio debe estar iniciado (EC2 y RDS en ejecución). Las credenciales de AWS Academy son temporales y no forman parte de la entrega.
- Las credenciales de las cuentas de prueba (Consulta y Gestión) se entregan por un medio privado; este README no contiene contraseñas ni hashes.

No copiar SQLite a RDS ni las credenciales del servidor al proyecto. No usar `sgr.settings_pruebas` ni el servidor de desarrollo como producción.

## Respaldo y restauración

Antes de cualquier cambio se creó en el Escritorio `back_end_respaldo_20261108_182541.zip`, con código y `db.sqlite3`, además de notas `RESTAURAR.txt` en la carpeta homónima. No incluye venv, .env/claves privadas ni archivos sueltos desconocidos. Para restaurar: detener Django local, conservar/renombrar la carpeta actual y recuperar juntos código y SQLite del respaldo; reutilizar o recrear el entorno. No intentar revertir esta integración de datos borrando filas; usar el respaldo completo. El respaldo es privado y no forma parte de la entrega académica.

## ZIP de entrega

`Equipo_BackEnd_Evaluacion3.zip` incluye código, migraciones, templates, estáticos, JSON ficticios, dependencias, README, `Evidencias.pdf`, `evidencias.md` y la carpeta `capturas_evidencia/` (43 capturas). Excluye venv, __pycache__, BD privada, .env, claves, contraseñas reales, respaldos y temporales. No es un respaldo de datos. Conservar por separado las credenciales privadas y demostrar las dos cuentas normales por el medio que indique la docente.
