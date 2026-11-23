# Evidencias técnicas SGR — Evaluación 3
Fecha original: 8 de noviembre de 2026. Actualización: 13 de noviembre de 2026, America/Santiago.

## Alcance y honestidad de la evidencia
La primera parte resume pruebas automatizadas reales ejecutadas el 8/11/2026 sobre una copia aislada con SQLite y datos ficticios. El 13/11/2026 se desplegó el mismo código en AWS (EC2 + RDS MySQL) y se verificó en funcionamiento; las capturas de pantalla de la sección final son reales, tomadas ese día con un navegador Chromium sin interfaz contra http://44.213.253.178/. No se incluyen capturas inventadas ni editadas. Ninguna captura muestra contraseñas: los campos de contraseña aparecen vacíos.

## Entorno y comandos (8/11/2026)
Box: Python 3.13.5, Django 5.2.18, SQLite 3.46.1. Intérprete PC detectado: Python 3.13.5, Django 5.2.17, SQLite 3.49.1; La copia temporal previa pasó 83 pruebas. Después de aplicar la versión final probada, la carpeta original del PC pasó las 84 pruebas en 49.926 segundos. Los permisos de consulta también se exigen en las URLs heredadas para que una cuenta sin grupo no pueda saltarse las restricciones. mysqlclient, MySQL y Gunicorn no fueron ejecutados en esta comprobación.

- python manage.py check --settings=sgr.settings_pruebas: sin incidencias.
- python manage.py makemigrations --check --dry-run --settings=sgr.settings_pruebas: sin cambios pendientes.
- python manage.py test --settings=sgr.settings_pruebas --noinput: 84 pruebas aprobadas en 8.335 segundos en el box.
- migrate + demo_evaluacion sobre BD limpia: migraciones correctas, al menos 2 muestras por cada entidad; todas pasan full_clean.
- Segunda ejecución de demo_evaluacion: conteos iguales, no duplica ni sobrescribe.
- migrate sobre copia de SQLite anterior: correcto; comparación de columnas originales confirma conservación de filas originales en 15 tablas, incluidas cuentas existentes. No se muestran contraseñas ni hashes.

Las pruebas crean usuarios exclusivamente en su BD de prueba. Los nombres que aparecen como “creado” en el log de tests no representan cuentas creadas en la BD del usuario.

## Matriz de las 17 entidades — pruebas automatizadas reales (8/11/2026)
“OK” remite a métodos test_crud_<entidad>, test_permissions_<entidad> y test_missing_<entidad> en sgr/tests_evaluacion3.py. Cada fila comprueba listado y detalle, crear con POST válido, editar manteniendo PK, invalidación sin guardar, confirmación GET sin borrado y eliminación POST de un registro desechable. Total usa un usuario normal no superusuario.

| Entidad | Crear | Consultar/listar/detalle | Editar mismo ID | Eliminar desechable | Roles GET/POST y 404 |
|---|---|---|---|---|---|
| Delegación | OK | OK | OK | OK | OK |
| Territorio | OK | OK | OK | OK | OK |
| Usuario funcionario | OK | OK | OK | OK | OK |
| Cargo | OK | OK | OK | OK | OK |
| Rol | OK | OK | OK | OK | OK |
| Vecino | OK | OK | OK | OK | OK |
| Junta de vecinos | OK | OK | OK | OK | OK |
| Participación en junta | OK | OK | OK | OK | OK |
| Hito | OK | OK | OK | OK | OK |
| Actividad | OK | OK | OK | OK | OK |
| Gestión social | OK | OK | OK | OK | OK |
| Tipo de atención | OK | OK | OK | OK | OK |
| Subtipo de atención | OK | OK | OK | OK | OK |
| Meta | OK | OK | OK | OK | OK |
| Asignación de meta | OK | OK | OK | OK | OK |
| Evidencia | OK | OK | OK | OK | OK |
| Trimestre | OK | OK | OK | OK | OK |

## Sesiones, seguridad y validaciones (8/11/2026)
- Anónimo redirigido al login en las cinco rutas de las 17 entidades, tanto GET como POST.
- Consulta: consulta las 17; GET/POST de escritura bloqueados con 403, incluso payload válido; no aparecen botones.
- Gestión: consulta las 17; creación/edición con POST válido aprobadas para hitos, actividades, gestiones, metas, asignaciones, evidencias y trimestres. Organización y catálogos protegidos con 403. No elimina ninguna entidad.
- Total: CRUD completo con cuenta normal y permisos Django, no solo por superusuario.
- Logout GET devuelve 405 y conserva sesión; POST sin CSRF devuelve 403; POST válido cierra sesión.
- Login sin CSRF bloqueado, credenciales falsas rechazadas, credenciales sintéticas correctas aceptadas; next externo/protocol-relative rechazado.
- Campos privilegiados adicionales de funcionario/Rol ignorados; no cambian grupos, is_staff ni is_superuser.
- Nueva cuenta de funcionario no adquiere privilegios ni contraseña utilizable automáticamente. Sus credenciales solo pueden establecerse por administración protegida.
- POST de cambio sin CSRF no guarda. Identificadores inexistentes: 404. Búsqueda con texto tipo inyección no ejecuta SQL arbitrario.
- Fechas inversas, objetivo 0/negativo, ponderaciones fuera de 0–100 y trimestre fuera de 1–4 rechazados.
- Territorio/delegación, tipo/subtipo, funcionario/asignación, responsable/delegación, participación territorial y antecedentes del hito verificados.
- Evidencia rechaza cero o dos orígenes. Restricciones BD impiden saltar límites numéricos y origen único mediante update directo.
- Código duplicado y correo inválido rechazados; formulario conserva el valor y la BD no cambia.
- Borrado de delegación relacionada y actividad con evidencia: mensaje amigable y conservación de antecedentes.

## Migraciones y continuidad
Se amplían modelos existentes en lugar de recrear sus tablas o PK. Nuevos modelos: Territorio, Vecino, JuntaVecinos, Participacion, Hito, GestionSocial y CatalogoMeta. Meta anterior pasa a ser asignación; Periodo conserva su nombre interno como trimestre; Unidad representa delegación. Las tablas duplicadas antiguas se conservan como archivo histórico de solo lectura.

Las cuentas originales y sus valores de contraseña/atributos permanecieron iguales al comparar la copia migrada; no se imprimen ni se entregan esos valores. Para personas/autorías históricas sin cuenta se crean identidades técnicas desactivadas y no autenticables. No se inventan relaciones de territorio o asignación desconocidas.

## Datos históricos pendientes de completar (copia local 8/11/2026, totales confirmados en AWS el 13/11/2026)
Delegación: 7 registros; 5 requieren completar/validar datos históricos.
Territorio: 2 registros; 0 requieren completar/validar datos históricos.
Usuario funcionario: 14 registros; 0 requieren completar/validar datos históricos.
Cargo: 7 registros; 0 requieren completar/validar datos históricos.
Rol: 4 registros; 0 requieren completar/validar datos históricos.
Vecino: 2 registros; 0 requieren completar/validar datos históricos.
Junta de vecinos: 2 registros; 0 requieren completar/validar datos históricos.
Participación en junta: 2 registros; 0 requieren completar/validar datos históricos.
Hito: 2 registros; 0 requieren completar/validar datos históricos.
Actividad: 10 registros; 8 requieren completar/validar datos históricos.
Gestión social: 2 registros; 0 requieren completar/validar datos históricos.
Tipo de atención: 4 registros; 0 requieren completar/validar datos históricos.
Subtipo de atención: 6 registros; 0 requieren completar/validar datos históricos.
Meta: 14 registros; 0 requieren completar/validar datos históricos.
Asignación de meta: 14 registros; 0 requieren completar/validar datos históricos.
Evidencia: 7 registros; 0 requieren completar/validar datos históricos.
Trimestre: 5 registros; 0 requieren completar/validar datos históricos.

Estos conteos se obtuvieron primero en la copia aislada después de añadir muestras; el 13/11/2026 se confirmaron los mismos totales en MySQL/RDS de AWS (ver sección de despliegue). Los registros nuevos de muestra son válidos; los antecedentes originales incompletos se preservan deliberadamente, en vez de rellenarlos con relaciones inventadas. Revisar además los textos “histórico/por completar” de direcciones, cargos y nombres antes de usarlos como demostración.

## Instalación local efectivamente realizada (8/11/2026)
La versión probada se aplicó a C:/Users/juanp/OneDrive/Escritorio/back end. Se comprobó previamente que el código y SQLite no habían cambiado desde el respaldo mediante hashes, para no sobrescribir trabajo paralelo. Se aplicaron 10 migraciones nuevas, permisos sin crear/restablecer las cuentas existentes y muestras idempotentes. check y makemigrations --check terminaron correctamente. Una comparación de solo lectura contra la BD del respaldo confirmó 72 filas originales conservadas en 15 tablas y cero diferencias en sus columnas originales, incluidas las cuentas anteriores. No se imprimieron contraseñas ni hashes. Las pruebas finales del PC pasaron 84/84 con datos de prueba aislados. No se inició un servidor web ni se accedió a AWS.

## Respaldo y entrega (8/11/2026)
Respaldo privado previo: Escritorio/back_end_respaldo_20261108_182541.zip; incluye SQLite y notas RESTAURAR.txt. La entrega académica excluye BD privada, entornos, secretos, respaldos y temporales. Restaurar juntos código y DB del respaldo si fuese necesario, nunca borrar filas manualmente para deshacer la integración.

## Despliegue y verificación en AWS (13/11/2026)
- Infraestructura: EC2 i-0d263fa1c9623341e (sgr-app, Amazon Linux 2023, t2.micro) con IP elástica 44.213.253.178; RDS MySQL 8.4.11 sgr-mysql (db.t3.micro, sin acceso público); grupo de seguridad de RDS que solo admite el puerto 3306 desde el grupo de la instancia.
- Respaldos previos: /var/backups/sgr/sgr-app-pre-20261113.tgz, /var/backups/sgr/sgr.env-pre-20261113 y /var/backups/sgr/sgr_db-pre-20261113.sql.gz (permisos restringidos), más la instantánea manual de RDS sgr-mysql-pre-20261113 (disponible).
- Código: el mismo de la entrega (sgr/catalog.py y sgr/urls.py con hashes idénticos a la carpeta del PC). Dependencias en el servidor: Python 3.12, Django 5.2.18, mysqlclient 2.3.0 y Gunicorn 23.0.0, con nginx como proxy inverso.
- Configuración por variables de entorno fuera del código: DEBUG=False, SECRET_KEY privada, ALLOWED_HOSTS y CSRF_TRUSTED_ORIGINS con la IP, base MySQL en RDS.
- Migraciones: se aplicaron las 10 migraciones nuevas sobre RDS sin errores; showmigrations no deja pendientes; manage.py check sin incidencias.
- Datos: demo_evaluacion (no destructivo) y setup_roles sin --create-users; no se restablecieron contraseñas. collectstatic copió 128 archivos.
- Conteos en MySQL tras el despliegue: Delegación 7, Territorio 2, Usuario funcionario 14, Cargo 7, Rol 4, Vecino 2, Junta de vecinos 2, Participación 2, Hito 2, Actividad 10, Gestión social 2, Tipo de atención 4, Subtipo 6, Meta (catálogo) 14, Asignación de meta 14, Evidencia 7, Trimestre 5.
- Verificación HTTP con las cuatro cuentas reales: juan_admin y sgr_total con CRUD completo en las 17 entidades; sgr_intermedio (Gestión) consulta las 17, crea/edita hitos, actividades, gestiones, metas, asignaciones, evidencias y trimestres, y recibe 403 al crear en Organización/catálogos y al eliminar; sgr_minimo (Consulta) consulta las 17 y recibe 403 en crear y eliminar. Logout por GET devuelve 405; por POST cierra la sesión. CSS estático 200. Sin errores en los registros de sgr ni de nginx.
- Persistencia: el 13/11/2026 se creó con sgr_total un Vecino temporal marcado PRUEBA-EVIDENCIA (id 3), se comprobó en el detalle y en el listado, y luego se eliminó; su detalle responde 404 y no quedó dato de prueba. Un trimestre con fechas invertidas fue rechazado sin guardarse. El intento de eliminar la delegación id 1 (protegida por 9 registros relacionados) mostró el mensaje amigable y el registro se conservó.

## Pendientes que NO se declaran aprobados
1. Completar antecedentes históricos: 5 de 7 delegaciones (por ejemplo, el delegado) y 8 de 10 actividades requieren completar o validar sus campos nuevos. No se rellenaron con datos inventados.
2. Confirmar por escrito los aportes concretos de cada integrante (Juan Ossandon, Vicente Garrido, Bastian Tapia, Wilson Choque).
3. Entregar por medio privado las credenciales de las cuentas Consulta (sgr_minimo) y Gestión (sgr_intermedio); este documento no contiene contraseñas.
4. HTTPS no está configurado; se recomienda antes de usar credenciales reales.

No se asigna nota ni porcentaje de cumplimiento.

## Capturas de pantalla (AWS, 13/11/2026)
Las capturas se incluyen en Evidencias.pdf y en la carpeta capturas_evidencia. Cada una indica fecha y hora (America/Santiago), URL y usuario.

| N° | Archivo | Descripción | Usuario | URL | Fecha y hora |
|---|---|---|---|---|---|
| 1 | 01_anonimo_redirige_login.png | Acceso anónimo a / redirige al inicio de sesión | anónimo | http://44.213.253.178/login/?next=/ | 13/11/2026 11:36:53 America/Santiago |
| 2 | 02_login_fallido.png | Inicio de sesión fallido: se muestra el error (el campo de contraseña se dejó vacío en la captura) | sgr_total (intento fallido) | http://44.213.253.178/login/ | 13/11/2026 11:36:56 America/Santiago |
| 3 | 03_inicio_sgr_total.png | Página de inicio después de iniciar sesión | sgr_total | http://44.213.253.178/ | 13/11/2026 11:36:59 America/Santiago |
| 4 | 03b_inicio_juan_admin.png | Página de inicio tras iniciar sesión como juan_admin | juan_admin | http://44.213.253.178/ | 13/11/2026 11:37:52 America/Santiago |
| 5 | 04_gestion_17_entidades.png | Módulo /gestion/ con las 17 entidades | sgr_total | http://44.213.253.178/gestion/ | 13/11/2026 11:37:00 America/Santiago |
| 6 | 04b_gestion_juan_admin.png | Módulo /gestion/ visto por juan_admin | juan_admin | http://44.213.253.178/gestion/ | 13/11/2026 11:37:53 America/Santiago |
| 7 | 05_asignaciones_crear.png | Formulario de creación de Asignación de meta | sgr_total | http://44.213.253.178/gestion/asignaciones/crear/ | 13/11/2026 11:37:15 America/Santiago |
| 8 | 05_asignaciones_detalle.png | Detalle de Asignación de meta (id 1) | sgr_total | http://44.213.253.178/gestion/asignaciones/1/ | 13/11/2026 11:37:13 America/Santiago |
| 9 | 05_asignaciones_editar.png | Formulario de edición de Asignación de meta (id 1) | sgr_total | http://44.213.253.178/gestion/asignaciones/1/editar/ | 13/11/2026 11:37:14 America/Santiago |
| 10 | 05_asignaciones_listado.png | Listado de Asignación de meta | sgr_total | http://44.213.253.178/gestion/asignaciones/ | 13/11/2026 11:37:12 America/Santiago |
| 11 | 05_gestiones_crear.png | Formulario de creación de Gestión social | sgr_total | http://44.213.253.178/gestion/gestiones/crear/ | 13/11/2026 11:37:11 America/Santiago |
| 12 | 05_gestiones_detalle.png | Detalle de Gestión social (id 1) | sgr_total | http://44.213.253.178/gestion/gestiones/1/ | 13/11/2026 11:37:09 America/Santiago |
| 13 | 05_gestiones_editar.png | Formulario de edición de Gestión social (id 1) | sgr_total | http://44.213.253.178/gestion/gestiones/1/editar/ | 13/11/2026 11:37:10 America/Santiago |
| 14 | 05_gestiones_listado.png | Listado de Gestión social | sgr_total | http://44.213.253.178/gestion/gestiones/ | 13/11/2026 11:37:08 America/Santiago |
| 15 | 05_hitos_crear.png | Formulario de creación de Hito | sgr_total | http://44.213.253.178/gestion/hitos/crear/ | 13/11/2026 11:37:07 America/Santiago |
| 16 | 05_hitos_detalle.png | Detalle de Hito (id 1) | sgr_total | http://44.213.253.178/gestion/hitos/1/ | 13/11/2026 11:37:05 America/Santiago |
| 17 | 05_hitos_editar.png | Formulario de edición de Hito (id 1) | sgr_total | http://44.213.253.178/gestion/hitos/1/editar/ | 13/11/2026 11:37:06 America/Santiago |
| 18 | 05_hitos_listado.png | Listado de Hito | sgr_total | http://44.213.253.178/gestion/hitos/ | 13/11/2026 11:37:04 America/Santiago |
| 19 | 05_trimestres_crear.png | Formulario de creación de Trimestre | sgr_total | http://44.213.253.178/gestion/trimestres/crear/ | 13/11/2026 11:37:19 America/Santiago |
| 20 | 05_trimestres_detalle.png | Detalle de Trimestre (id 1) | sgr_total | http://44.213.253.178/gestion/trimestres/1/ | 13/11/2026 11:37:17 America/Santiago |
| 21 | 05_trimestres_editar.png | Formulario de edición de Trimestre (id 1) | sgr_total | http://44.213.253.178/gestion/trimestres/1/editar/ | 13/11/2026 11:37:18 America/Santiago |
| 22 | 05_trimestres_listado.png | Listado de Trimestre | sgr_total | http://44.213.253.178/gestion/trimestres/ | 13/11/2026 11:37:16 America/Santiago |
| 23 | 05_vecinos_crear.png | Formulario de creación de Vecino | sgr_total | http://44.213.253.178/gestion/vecinos/crear/ | 13/11/2026 11:37:03 America/Santiago |
| 24 | 05_vecinos_detalle.png | Detalle de Vecino (id 1) | sgr_total | http://44.213.253.178/gestion/vecinos/1/ | 13/11/2026 11:37:02 America/Santiago |
| 25 | 05_vecinos_editar.png | Formulario de edición de Vecino (id 1) | sgr_total | http://44.213.253.178/gestion/vecinos/1/editar/ | 13/11/2026 11:37:02 America/Santiago |
| 26 | 05_vecinos_listado.png | Listado de Vecino | sgr_total | http://44.213.253.178/gestion/vecinos/ | 13/11/2026 11:37:01 America/Santiago |
| 27 | 05b1_prueba_formulario.png | Formulario de creación con el registro temporal PRUEBA-EVIDENCIA antes de guardar | sgr_total | http://44.213.253.178/gestion/vecinos/crear/ | 13/11/2026 11:38:49 America/Santiago |
| 28 | 05b2_prueba_detalle.png | Registro temporal PRUEBA-EVIDENCIA guardado en MySQL (Vecino id 3) | sgr_total | http://44.213.253.178/gestion/vecinos/3/ | 13/11/2026 11:38:50 America/Santiago |
| 29 | 05b3_prueba_en_listado.png | El listado de Vecinos muestra el registro temporal (id 3) | sgr_total | http://44.213.253.178/gestion/vecinos/ | 13/11/2026 11:38:50 America/Santiago |
| 30 | 05c1_prueba_eliminada_mensaje.png | Resultado tras confirmar la eliminación del registro temporal (id 3) | sgr_total | http://44.213.253.178/gestion/vecinos/ | 13/11/2026 11:38:51 America/Santiago |
| 31 | 05c_prueba_eliminada.png | Listado de Vecinos sin el registro temporal; su detalle ahora responde HTTP 404 | sgr_total | http://44.213.253.178/gestion/vecinos/ | 13/11/2026 11:38:51 America/Santiago |
| 32 | 06_validacion_fechas_inversas.png | Validación: trimestre con fecha de término anterior al inicio; el formulario no se guardó | sgr_total | http://44.213.253.178/gestion/trimestres/crear/ | 13/11/2026 11:37:21 America/Santiago |
| 33 | 07_confirmacion_borrar.png | Página de confirmación de eliminación de Vecino (id 1) | sgr_total | http://44.213.253.178/gestion/vecinos/1/eliminar/ | 13/11/2026 11:37:23 America/Santiago |
| 34 | 07_despues_cancelar.png | Tras pulsar Cancelar, el Vecino id 1 sigue disponible (no se eliminó) | sgr_total | http://44.213.253.178/gestion/vecinos/ | 13/11/2026 11:37:23 America/Santiago |
| 35 | 08_borrado_protegido.png | Intento de eliminar la delegación id 1 protegida por relaciones: mensaje amigable y el registro se conserva | sgr_total | http://44.213.253.178/gestion/delegaciones/1/eliminar/ | 13/11/2026 11:37:29 America/Santiago |
| 36 | 09_busqueda.png | Resultados de búsqueda (consulta «a») cubriendo entidades nuevas y existentes | sgr_total | http://44.213.253.178/buscar/?q=a | 13/11/2026 11:37:31 America/Santiago |
| 37 | 10a_intermedio_actividades_crear_visible.png | Usuario sgr_intermedio (Gestión): el listado de Actividades muestra la acción de crear | sgr_intermedio | http://44.213.253.178/gestion/actividades/ | 13/11/2026 11:37:38 America/Santiago |
| 38 | 10b_intermedio_403_eliminar.png | Usuario sgr_intermedio: 403 al abrir la URL de eliminación de una actividad (id 1) | sgr_intermedio | http://44.213.253.178/gestion/actividades/1/eliminar/ | 13/11/2026 11:37:40 America/Santiago |
| 39 | 10c_intermedio_403_crear_organizacion.png | Usuario sgr_intermedio: 403 al intentar crear un registro de Organización (delegación) | sgr_intermedio | http://44.213.253.178/gestion/delegaciones/crear/ | 13/11/2026 11:37:41 America/Santiago |
| 40 | 11a_minimo_listado_sin_botones.png | Usuario sgr_minimo (Consulta): listado de Actividades sin botones de crear, editar o eliminar | sgr_minimo | http://44.213.253.178/gestion/actividades/ | 13/11/2026 11:37:46 America/Santiago |
| 41 | 11b_minimo_403_crear.png | Usuario sgr_minimo: 403 al abrir la URL de creación de una actividad | sgr_minimo | http://44.213.253.178/gestion/actividades/crear/ | 13/11/2026 11:37:47 America/Santiago |
| 42 | 12_logout_post_login.png | Cierre de sesión por POST: el navegador termina en la página de inicio de sesión | sgr_minimo (sesión cerrada) | http://44.213.253.178/login/ | 13/11/2026 11:37:49 America/Santiago |
| 43 | 13_admin_login.png | Página de inicio de sesión del Django Admin (formulario vacío) | anónimo | http://44.213.253.178/admin/login/ | 13/11/2026 11:37:56 America/Santiago |
