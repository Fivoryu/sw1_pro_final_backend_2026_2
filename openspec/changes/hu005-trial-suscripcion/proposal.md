# Propuesta backend-local — Trial y suscripción mensual de tenant (HU-005)

- **Cambio:** `hu005-trial-suscripcion`
- **Trazabilidad:** `PB-005` / `HU-005` / `CU-005` / `CP-004`
- **Sprint / plataforma:** Sprint 1 / Web y Backend
- **Repositorio:** `sw1_pro_final_backend_2026_2`
- **Worktree:** `D:\\universidad\\Proyectos\\2doSemestre2026\\sw1\\roomforge-hu005-backend`
- **Rama:** `feature/hu005-trial-suscripcion`
- **Idioma del artefacto:** español profesional y neutral
- **Almacén:** Hybrid (OpenSpec + Engram); el archivo local quedó persistido y el mirror Engram se guardó como la observación `3170`
- **Estado:** propuesta backend-local; no declara implementación ni ejecución
- **Criterio de prueba:** `CP-004`, actualmente `not executed`
- **Presupuesto de implementación:** límite duro de `400` líneas modificadas; sin excepción implícita

## 1. Intención y valor de negocio

RoomForge necesita que el administrador de un tenant aprovisionado pueda iniciar una prueba gratuita única y completar, mediante un evento mensual firmado, la conversión de su suscripción. Este slice permite que el tenant avance desde el aprovisionamiento de HU-004 hacia la operación demostrable del SaaS, con decisiones de identidad, estado, plan, fechas, seguridad e idempotencia gobernadas por el backend.

Sin este cambio, el backend deja incompleto el recorrido de Sprint 1: la suscripción inicial y el plan existen, pero la activación de la prueba y la conversión mensual no tienen una frontera segura de autorización ni una persistencia atómica. La situación actual también permite que contratos heredados aporten `tenant_id` o `plan_id`, usa una duración de 30 días para la suscripción y separa operaciones de estado y evento.

La propuesta no redefine el producto. Es la adaptación backend-local de la propuesta, especificación, diseño y tareas aprobados en el repositorio raíz. Su objetivo es convertir esas decisiones en un plan aplicable únicamente al repositorio backend que contiene el código, las migraciones, las pruebas y la contabilidad nativa de este trabajo.

## 2. Trazabilidad

| Identificador | Relación con este cambio |
| --- | --- |
| `PB-005` | Incremento de producto para trial y suscripción mensual. |
| `HU-005` | Como administrador, activar la prueba de 14 días y suscribirse mensualmente para operar el tenant. |
| `CU-005` | Activación del trial y conversión de suscripción mediante evento firmado. |
| `CP-004` | Evidencia observable de activación, conversión y replay idempotente. Permanece `not executed`. |

La trazabilidad funcional se mantiene con RF-007, BR-A2 y BR-B3/BR-B4, además de las dependencias de identidad de HU-002, aprovisionamiento y HMAC de HU-004, y estados futuros de HU-006. Ningún identificador, revisión, resultado de prueba o evidencia se inventa en esta propuesta.

## 3. Alcance backend-only

### 3.1. Incluido

1. Autorización administrativa basada en el principal JWT de `get_current_user`.
2. Asociación mínima y server-owned `tenant_administrator` entre el usuario global, el tenant y la invitación inicial de HU-004 ya consumida.
3. Bootstrap acotado de esa asociación, sin convertirla en membresía general.
4. Activación única de un trial de exactamente `14 × 24` horas (`336` horas).
5. Consulta protegida de la proyección mínima de la suscripción.
6. Conversión mensual mediante evento firmado y autenticado con la frontera HMAC de HU-004.
7. Preservación server-owned del tenant, plan contratado y monto esperado.
8. Cálculo del período mensual por calendario local `America/La_Paz`, con clamping al último día del mes destino.
9. Idempotencia persistente, replay exacto, conflicto de reutilización de clave y recuperación segura bajo concurrencia.
10. Persistencia atómica del cambio de suscripción y del evento mensual.
11. Cambios aditivos de SQLAlchemy/Alembic y pruebas contractuales, de reglas, PostgreSQL, migración y regresión que sean necesarios para la evidencia posterior.

### 3.2. Superficie backend prevista

La composición técnica heredada del diseño aprobado contempla:

- `POST /api/v1/tenant/administrador/bootstrap`: JWT requerido y body vacío o sin campos; crea o reconoce una asociación activa trazable a la invitación consumida de HU-004.
- `POST /api/v1/tenant/activar-prueba`: JWT requerido; el tenant se deriva de la asociación activa y no del body.
- `GET /api/v1/tenant/suscripcion`: JWT requerido; devuelve únicamente la proyección autorizada.
- `POST /api/v1/tenant/webhook`: headers HMAC y body raw; procesa el evento mensual y mantiene el dispatch del evento HU-004 después de autenticar.
- `POST /api/v1/tenant/suscribir`: se conserva como alias compatible/deprecated de la misma tubería firmada; no conserva el bypass legacy ni commits separados.

Los nombres y la composición exacta de los contratos deben permanecer alineados con los artefactos aprobados de spec/design/tasks. Resolver un detalle técnico en esas fases no autoriza una nueva capacidad de producto.

## 4. Decisiones y guards que se preservan

Estas reglas están cerradas por los artefactos aprobados y no se reabren en la adaptación backend-local.

### 4.1. Autoridad y aislamiento

- El JWT es la fuente del principal; la asociación activa `tenant_administrator` es la fuente de autorización tenant.
- Ningún `tenant_id` aportado por body, query, header o evento puede seleccionar el tenant autorizado.
- El evento firmado no suplanta al administrador ni concede acceso administrativo.
- Solo una asociación activa, vinculada al usuario global autenticado y al tenant correcto, permite activar o inspeccionar.
- La asociación debe ser server-owned y trazable a la invitación de primer administrador de HU-004 en estado consumida.
- No se implementan RBAC general, catálogo de roles, permisos generales ni memberships generales.
- Los errores de identidad, asociación, tenant o suscripción deben ser sanitizados y no permitir enumeración.

### 4.2. Trial y máquina de estados

- La activación válida parte únicamente de la suscripción inicial `active` creada/provisionada por HU-004, con fechas de trial ausentes.
- La activación persiste `trial_inicio` y `trial_fin` en la misma operación que cambia el estado a `trialing`.
- `trial_fin = trial_inicio + 14 × 24 horas`, es decir, exactamente `336` horas; no se usa una duración mensual ni una aproximación de calendario.
- La activación es única. Cualquier segunda activación, incluso después del fin del trial, es conflicto y no sobrescribe fechas, estado ni eventos.
- El trial se considera expirado cuando `now >= trial_fin`.
- La única conversión nueva de este slice es `trialing → active`.
- No se convierte directamente la suscripción inicial `active` de HU-004.
- No se agregan transiciones `past_due`, grace, `suspended`, `canceled_read_only`, `purged`, renovación ni otros estados de HU-006.
- Un trial expirado puede conservar el estado persistente `trialing`; HU-005 rechaza la conversión y deja su remediación a HU-006.

### 4.3. Plan y período mensual

- El `plan_id` contratado por HU-004 es inmutable en HU-005.
- El evento no puede cambiar tenant, plan, precio, monto server-owned ni cuotas.
- El monto recibido se valida contra el plan contratado; no se acepta como autoridad.
- Se reutiliza el catálogo HU-004 existente y sus cuotas server-owned; no se siembran ni modifican planes o precios. Los valores observados son `basico` `199.00` BOB, `profesional` `449.00` BOB y `empresarial` `899.00` BOB.
- `periodo_inicio` es el instante de conversión.
- `periodo_fin` se calcula con la misma fecha calendario local del mes siguiente en `America/La_Paz`; si el día no existe, se usa el último día de ese mes.
- El cálculo no suma 30 días fijos. Debe cubrir fin de mes, febrero y años bisiestos.

### 4.4. HMAC y evento mensual

- Se reutiliza `app/modules/tenant/signatures.py:HMACWebhookSignatureVerifier`; no se crea una implementación criptográfica paralela.
- La firma se verifica sobre `ASCII(timestamp) + b"." + raw_body`, con HMAC-SHA256 y comparación constante.
- Se conservan los headers `X-RoomForge-Webhook-Timestamp` y `X-RoomForge-Webhook-Signature`, el formato HU-004 y su tolerancia configurada.
- La tolerancia observada de HU-004 es de `300` segundos por defecto; la igualdad del límite se acepta porque el rechazo ocurre cuando la diferencia es mayor que la tolerancia.
- El body se lee como bytes una sola vez y no se reserializa antes de verificarlo ni para calcular su huella.
- La autenticación ocurre antes de consultar idempotencia, tenant, suscripción, plan o cualquier otro dato de negocio.
- El evento mensual es distinto del onboarding de HU-004; el token heredado por diseño es `subscription.monthly.succeeded`.
- El body mensual usa la correlación opaca `subscription_id`, `plan_id`, `monto_bob` e `idempotency_key`, además del tipo de evento. Los campos extra, incluidos campos de autoridad, se rechazan.
- Un replay exacto previamente autenticado puede recuperar su resultado original fuera de la ventana temporal aplicable a eventos nuevos; esto no permite omitir una firma válida.

### 4.5. Idempotencia y atomicidad

- `idempotency_key` tiene unicidad persistente en PostgreSQL.
- Se conserva una huella verificable de los bytes exactos recibidos.
- La misma clave con los mismos bytes y datos produce HTTP `200` con el resultado original, sin duplicar evento ni conversión.
- La misma clave con bytes, tipo, correlación o datos distintos produce HTTP `409` y conserva íntegramente el primer resultado.
- Una clave nueva sobre una suscripción ya convertida es conflicto de estado, no una segunda conversión.
- La actualización de la suscripción, sus fechas y la inserción del evento mensual ocurren en una única transacción.
- Se bloquea la suscripción durante la decisión y la base de datos gobierna la carrera de unicidad.
- Una carrera recuperable solo se considera replay o conflicto después de leer el registro comprometido y confirmar su tipo, huella y resultado; nunca se infiere por el texto de una excepción.
- Todo fallo de escritura revierte conjuntamente estado, fechas y evento.

## 5. Resultados API y eventos observables

Estos son resultados esperados del contrato, no resultados ya ejecutados.

| Operación | Resultado esperado | Efecto observable |
| --- | --- | --- |
| Bootstrap válido | `201` | Una asociación activa única, vinculada al usuario global, tenant e invitación consumida. |
| Bootstrap repetido | `200` | Devuelve el vínculo existente sin duplicarlo. |
| Bootstrap sin vínculo server-owned o ambiguo | `404` sanitizado | No crea asociación ni revela tenants, correos o cantidades. |
| Activación válida | `200` | Proyección con `subscription_id`, `plan_id`, `trialing`, `trial_inicio`, `trial_fin` y períodos nulos. |
| Segunda activación o estado incompatible | `409` | No modifica estado, fechas ni eventos. |
| Inspección autorizada | `200` | Solo la proyección de la suscripción del tenant autorizado. |
| Inspección no autorizada o no accesible | `401`/`404` sanitizado | No permite inferir existencia de otro tenant o suscripción. |
| Evento mensual nuevo y válido | `201` | `trialing → active`, período persistido, plan conservado y `EventoFacturacion` persistido. |
| Replay exacto autenticado | `200` | Devuelve los identificadores, estado y fechas originalmente persistidos; no duplica efectos. |
| Misma clave con payload distinto | `409` | Conserva el primer evento y el primer resultado. |
| Firma ausente, inválida, alterada o timestamp inválido/stale | `401` | No se consulta ni persiste información de negocio. |
| Secreto HMAC ausente | `503` | Falla cerrado sin exponer configuración. |
| Body autenticado inválido | `422` | No persiste conversión ni evento. |
| Correlación, tipo, estado, plan o monto incompatibles | `409` | No muta suscripción, plan, fechas ni evento mensual. |
| Fallo de persistencia | `500` | Rollback conjunto; no queda conversión sin evento ni evento sin conversión. |

La proyección administrativa contiene solo `subscription_id`, `plan_id`, `estado`, `trial_inicio`, `trial_fin`, `periodo_inicio` y `periodo_fin`, con valores nulos cuando corresponda. No devuelve body firmado, payload de evento, firma, secreto, monto recibido, JWT, password, token, hashes sensibles, correo completo ni datos de otro tenant.

La persistencia del evento mensual es el registro de auditoría del evento. No se agregan notificaciones, outbox ni proveedor de entrega.

## 6. Modelo de datos y compatibilidad

Se prevén únicamente cambios aditivos necesarios para las reglas aprobadas:

- `suscripcion.trial_inicio`, manteniendo `trial_fin`.
- `suscripcion.periodo_inicio`, manteniendo `periodo_fin`.
- Tabla `tenant_administrator` con identificadores, estado, timestamps, FKs y unicidades mínimas.
- Índices para resolver asociaciones activas por usuario y tenant.
- Solo las columnas de tipo, correlación, huella o resultado mensual que HU-004 no provea ya; no se duplican `checkout_id`, `payload_hash`, `suscripcion_id` ni la frontera existente.

Las filas legacy de HU-004 con suscripción inicial `active` y fechas nuevas nulas deben permanecer intactas. No se crean trials sintéticos, asociaciones retroactivas, eventos mensuales ni cambios de plan. No se agregan checks que impidan representar estados futuros de HU-006.

## 7. Dependencias verificadas y límites de integración

### HU-004 y Alembic

La exploración backend observó la cadena de archivos Alembic `0001 → 0002 → 0003 → 0004`, con:

- head observado: `0004`, archivo `0004_hu004_onboarding.py`;
- padre observado: `0003`, archivo `0003_crear_tablas_tenant.py`;
- extensiones HU-004 observadas: `checkout_intencion`, `invitacion.consumido_en`, `evento_facturacion.checkout_id`, `evento_facturacion.payload_hash`, unicidades de catálogo y el índice de checkout.

Estos valores son evidencia de los archivos leídos en la exploración, no una afirmación de que se haya ejecutado una inspección de runtime. La fase de tareas/apply debe confirmar que `0004` sigue siendo el head efectivo antes de crear una revisión nueva y debe agregar solo el delta ausente.

La frontera HMAC observada es:

- export: `app.modules.tenant.signatures:HMACWebhookSignatureVerifier`;
- errores: `SignatureValidationError` y `WebhookNotConfiguredError`;
- headers: `X-RoomForge-Webhook-Timestamp` y `X-RoomForge-Webhook-Signature`;
- raw body y mensaje firmado: `timestamp.encode("ascii") + b"." + raw_body`;
- HMAC-SHA256 con `hmac.compare_digest`;
- tolerancia configurable mediante `BILLING_WEBHOOK_TOLERANCE_SECONDS`, default `300`.

HU-005 depende de reutilizar esos contratos, no de crear una segunda implementación.

### Identidad HU-002

Se reutiliza `app/modules/identity/router.py:get_current_user`, que entrega el principal autenticado con `MeResponse.id` y `MeResponse.correo` después de validar Bearer/JWT y sesión. HU-005 no modifica `UsuarioGlobal`, `Sesion`, la validación JWT ni la identidad global.

### PostgreSQL y Alembic

PostgreSQL es la autoridad para FKs, unicidad de `idempotency_key`, locks, transacciones y recuperación de carreras. SQLite o repositorios fake pueden apoyar reglas determinísticas, pero no sustituyen la evidencia PostgreSQL para concurrencia, rollback, constraints y migraciones. La migración debe conservar compatibilidad con datos HU-004 y con los estados que HU-006 necesitará representar.

### Frontera root/backend

El repositorio raíz y el backend son superficies Git separadas, con common directories distintos. El common directory observado del backend es `D:\\universidad\\Proyectos\\2doSemestre2026\\sw1\\proyecto_final\\backend/.git`. Este artefacto vive en el backend porque allí residen el código, los tests, Alembic y el runtime/accounting correspondiente.

Los artefactos aprobados del root son referencias de producto y planificación; no se copian, no se editan y no autorizan cambios en el monorepo. El gitlink, metadata raíz y documentación no relacionada no forman parte de la contabilidad de implementación backend.

## 8. Áreas afectadas previstas

La implementación posterior deberá mantenerse en la superficie backend estrictamente necesaria:

| Área | Alcance previsto |
| --- | --- |
| `app/modules/tenant/models.py` | Campos de fechas, asociación administrativa y delta de evento estrictamente ausente. |
| `app/modules/tenant/schemas.py` | Request vacío/bootstrap, evento mensual estricto, proyección segura y respuestas sanitizadas. |
| `app/modules/tenant/service.py` | Principal reducido, autorización, guards de estado, reloj, trial, calendario y conversión. |
| `app/modules/tenant/repository.py` | Resolución server-owned, locks, transacción única, idempotencia y recuperación segura. |
| `app/modules/tenant/router.py` | Dependencia JWT, endpoint de inspección/bootstrap, raw body, HMAC compartido y mapeo HTTP. |
| `app/modules/tenant/signatures.py` | Reutilización del helper HU-004; no se prevé una implementación paralela. |
| `alembic/versions/` | Una revisión aditiva con el `down_revision` confirmado en la fase posterior. |
| `tests/` | Un módulo enfocado o extensión de la suite tenant existente, sin duplicar helpers ni afirmar evidencia antes de ejecutarla. |

No se anticipan cambios en UI, Flutter, identidad global, catálogo de planes o módulos ajenos, salvo el registro mínimo de metadata que la integración existente requiera y que sea confirmado en apply.

## 9. No-goals explícitos

Quedan fuera de HU-005:

- UI React/Web, Flutter, navegación, copy y clientes generados.
- Pagos reales, checkout real, facturación real, invoices y proveedores externos.
- Nuevos planes, precios, cuotas, catálogo o enforcement de cuotas.
- Cambios de plan, upgrade, downgrade y renovación.
- El ciclo completo de HU-006: `past_due`, grace, suspensión, cancelación, modo solo lectura, purge y remediación de expiración.
- RBAC general, membresías generales, roles, permisos e invitaciones de agentes.
- Notificaciones por email, push o in-app, outbox, notifier y reintentos de entrega.
- Endpoint público de historial o consulta de eventos por clave.
- S3, SQS, workers, publicación y refactors no relacionados.
- Cambios en `docs/diagramas/Diagrama1.eapx` o en metadata raíz no relacionada.
- Commits, pushes, cambios de rama, cleanup o cualquier operación de entrega.

## 10. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
| --- | --- | --- |
| El bootstrap deriva en membership o RBAC | Alto | Tabla dedicada, vínculo a invitación consumida, body sin selector y sin roles/permisos. |
| Se confunde `active` inicial con conversión mensual | Alto | Activación exige trial elegible y conversión exige exclusivamente `trialing`. |
| Se rompe la frontera HMAC por el alias legacy | Alto | `/webhook` y `/suscribir` comparten raw bytes, headers, verificador y pipeline; el contrato inseguro falla cerrado. |
| Carrera de idempotencia o commits parciales | Alto | Unicidad PostgreSQL, lock de suscripción, una transacción y lectura confirmatoria del registro comprometido. |
| Replay o conflicto filtra datos | Alto | Autenticación antes del lookup, huella exacta y proyecciones/errores mínimos. |
| Período incorrecto en fin de mes | Medio/alto | Zona `America/La_Paz`, clamping por calendario, reloj inyectable y casos de febrero/leap year. |
| La migración HU-004 real difiere del modelo observado | Alto | Confirmar head y delta antes de crear revisión; detenerse si falta una dependencia, sin duplicar columnas. |
| Restricciones incompatibles con HU-006 | Alto | No imponer un catálogo cerrado de estados; mantener estados futuros representables. |
| Se supera el límite de trabajo | Alto | Forecast root de 372, reutilización de seams HU-004 y exclusión estricta de alcance. Si el total supera 400, detener apply y solicitar decisión explícita. |

## 11. Rollback y operación segura

1. Ante un defecto en la conversión mensual, deshabilitar la entrada mensual o su configuración de feature, sin borrar la historia ni deshabilitar innecesariamente la inspección protegida.
2. Revertir código solo hacia una versión compatible con el esquema aditivo. Con datos HU-005, preservar asociaciones, trials, períodos y eventos.
3. Preferir un forward-fix en bases que contengan datos HU-005. No ejecutar un downgrade destructivo sobre datos reales.
4. Permitir downgrade destructivo únicamente como verificación controlada en una base descartable y sin datos HU-005, previa comprobación de orden y constraints.
5. Mantener la posibilidad de que un retry autenticado con la misma clave recupere el resultado persistido, en vez de crear una segunda conversión.
6. Toda contabilidad, estado de runtime y decisión de entrega se gobierna en el worktree backend; no se modifica el root para simular el estado del backend.

No se ha realizado rollback, migración, cambio operativo ni operación de entrega en esta fase.

## 12. Presupuesto y contabilidad

- **Límite duro:** `400` líneas modificadas como máximo para la implementación; no se eleva ni se concede excepción automática.
- **Forecast inicial aprobado del root:** `372` líneas modificadas, con una reserva estimada de `28` líneas.
- El forecast de `372` es una estimación inicial y debe recalcularse contra la superficie backend real; no es evidencia de cambios realizados.
- Si el desglose confirmado supera `400`, `ask-on-risk` exige detener `sdd-apply` y pedir una decisión explícita para reducir o dividir el slice. No se eliminan silenciosamente guards aprobados.
- La contabilidad nativa y el runtime/accounting pertenecen al repositorio backend y a su common directory; el root no se usa como autoridad alternativa.
- La propuesta, la especificación, el diseño y las tareas son documentación y no deben contarse como implementación de producto.

## 13. Estado actual y evidencia pendiente

La exploración backend estableció estos gaps de baseline:

- falta la asociación persistente tenant–administrador y su bootstrap server-owned;
- faltan `trial_inicio` y `periodo_inicio`;
- la activación actual acepta `tenant_id`, calcula 14 días sin inicio explícito y no demuestra todos los guards;
- no existe la inspección tenant-scoped aprobada;
- la ruta legacy acepta autoridad de cliente, puede cambiar el plan, usa 30 días y separa persistencias;
- falta la operación mensual atómica con correlación, HMAC compartido, replay de resultado y recuperación segura de carreras;
- las pruebas actuales incluyen comportamiento legacy que deberá ajustarse sin reintroducir el bypass inseguro;
- no existe evidencia ejecutada de PostgreSQL, migraciones, lint, typecheck ni regresión para HU-005.

La exploración no ejecutó Git, tests, migraciones, lint, typecheck ni comandos de calidad. Este documento tampoco declara ejecución. `CP-004` permanece explícitamente `not executed`.

La evidencia pendiente deberá demostrar, como mínimo:

- activación autenticada y única con diferencia exacta de 336 horas;
- expiración en `now >= trial_fin`;
- conversión exclusiva `trialing → active` y rechazo de conversión desde el `active` inicial;
- calendario mensual `America/La_Paz` con clamping y zona consciente;
- HMAC HU-004 sobre bytes raw, tolerancia y autenticación antes del lookup;
- plan inmutable y validación de correlación/monto server-owned;
- replay exacto `200`, conflicto `409`, unicidad y concurrencia sin duplicados;
- rollback conjunto de suscripción y evento;
- upgrade desde el head HU-004 observado, preservación legacy y downgrade seguro solo en base descartable;
- ausencia de secretos, tokens, payloads, correos completos o datos de otros tenants en respuestas y logs;
- regresión del onboarding HU-004 y compatibilidad representacional con HU-006.

Los comandos posteriores pertenecen a fases de apply/verify y no se ejecutaron para crear esta propuesta:

```text
..\\.venv\\Scripts\\python.exe -m pytest tests -q
..\\.venv\\Scripts\\ruff.exe check app tests
..\\.venv\\Scripts\\pyright.exe app tests
..\\.venv\\Scripts\\python.exe -m alembic -c alembic.ini upgrade head
```

## 14. Criterios de éxito

La propuesta se considera correctamente traducida a implementación solo cuando las fases posteriores aporten evidencia verificable de que:

- `CP-004.1`, `.2` y `.3` cubren activación, conversión y replay, sin cambiar el estado a ejecutado por la existencia de este documento;
- solo el administrador JWT con asociación activa puede activar o inspeccionar;
- ningún dato de cliente puede conceder autoridad tenant ni cambiar el plan;
- el trial persiste inicio y fin exactamente separados por 336 horas;
- la expiración aplica en `now >= trial_fin`;
- solo `trialing → active` convierte y el `active` inicial no se convierte directamente;
- el período mensual respeta `America/La_Paz` y clamping de calendario;
- el HMAC reutiliza exactamente el contrato raw-byte de HU-004;
- un evento nuevo devuelve `201`, un replay exacto `200` y una reutilización conflictiva `409`;
- estado, fechas y evento se persisten o revierten como una unidad, incluso bajo concurrencia PostgreSQL;
- las filas legacy, el plan contratado y los estados futuros de HU-006 se preservan;
- no se agregan UI, billing real, nuevos planes/precios/cuotas, lifecycle HU-006, notificaciones, RBAC/memberships ni refactors ajenos;
- la implementación se mantiene en el límite duro de 400 líneas y la contabilidad corresponde al backend worktree.

## 15. Ronda de preguntas de propuesta y siguiente fase

Las decisiones de producto necesarias fueron provistas y aprobadas para este slice; por eso esta propuesta no abre una nueva decisión de negocio. La siguiente fase debe resolver únicamente detalles técnicos ya delimitados, sin ampliar alcance:

1. Confirmar mediante la superficie backend activa que `0004` continúa siendo el head Alembic y que `0003` es su padre antes de crear la revisión siguiente.
2. Confirmar las columnas de evento realmente provistas por HU-004 para no duplicar correlación, huella o resultado.
3. Confirmar la integración concreta de `tenant_administrator` con la invitación HU-004 consumida y mantener el bootstrap como costura mínima, no como membership.
4. Confirmar la suite tenant existente que se extenderá, evitando una segunda colección redundante.

Estas son aclaraciones técnicas y de evidencia, no nuevos requisitos. La fase siguiente es `spec`; esta fase termina aquí sin iniciar diseño, tareas, apply o implementación.

## Fuentes y naturaleza de la evidencia

- Exploración backend: `openspec/changes/hu005-trial-suscripcion/explore.md`.
- Propuesta, especificación, diseño y tareas aprobados del root: referencias externas no modificadas.
- Configuración local: `openspec/config.yaml` y `openspec/project-context.md`.
- Código y configuración observados por la exploración: módulos `tenant`, `identity`, `core`, Alembic y tests del backend.
- Observación Engram de exploración: `3167`; mirror Engram de esta propuesta: observación `3170`.

La separación root/backend y sus common directories es una razón de alcance y contabilidad, no una nueva decisión de producto.
