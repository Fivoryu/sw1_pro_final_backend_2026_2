# Progreso de aplicación — HU-004 Alta de inmobiliaria

**Cambio:** `hu004-alta-inmobiliaria`\
**Repositorio:** RoomForge Backend independiente\
**Unidad:** PR 1 — contratos, catálogo, checkout y autenticidad\
**Estado:** completada y verificada; PR 2 pendiente

## Implementado

- Catálogo server-owned con los tres planes aprobados y cuotas exactas.
- Checkout demo público, separado de la provisión, con request `extra="forbid"`, normalización de correo y respuesta server-owned.
- Configuración de entorno, secreto opcional del webhook, tolerancia temporal y TTL de activación.
- Modelo y esquema de `CheckoutIntent`, precio `Decimal`, UUID y contratos de respuesta.
- Verificador HMAC-SHA256 fail-closed y seams para reloj, notifier, hook de identidad y política de acceso.
- Rutas `GET /api/v1/tenant/plans` y `POST /api/v1/tenant/checkout` sin modificar la inclusión de `app/main.py`.
- Pruebas contractuales aisladas mediante fakes, distinguiendo explícitamente fake de evidencia PostgreSQL.

## Evidencia de verificación

- `..\\.venv\\Scripts\\python.exe -m pytest tests -q`: **40 passed**, 3 warnings.
- `..\\.venv\\Scripts\\pyright.exe app tests`: **0 errores**.
- `..\\.venv\\Scripts\\python.exe -m ruff check app tests`: un único `I001` preexistente en `app/main.py`, archivo sin cambios de esta unidad.
- La candidata no cambió durante la verificación.
- El intento nativo ordinal 5 (`PR-1-final-verify`) terminó `complete: true`, con `changed_lines: 0` respecto de su candidato inicial y sin decisión pendiente.

## Alcance y pendientes

- El conteo manual del candidato seleccionado queda en el techo aprobado de 600 líneas; no ampliar esta unidad.
- No se ejecutó PostgreSQL real: conservar `GAP-092` abierto.
- `CP-003` permanece sin ejecutar.
- PR 2 — webhook, provisión atómica, activación, migración e integración — permanece pendiente.
- No se realizaron commits ni pushes.

## Continuación de aplicación — PR 2, lote de frontera y persistencia segura

**Estado:** lote aplicado; quedan tareas PR 2 pendientes para una siguiente continuación.

### Estado estructurado consumido

- `artifactStore: hybrid`; `applyState: ready`; `verify: blocked`; `nextRecommended: apply`.
- El estado previo reportaba `16/36` tareas completas; este lote marca dos tareas adicionales y deja `18/36` visibles como completas en `tasks.md`.
- `actionContext`: el resumen nativo recibido no expuso campos adicionales; el prompt del padre aportó explícitamente la raíz backend y las superficies autorizadas. No se detectó advertencia de autoridad de edición ni se tocaron raíces prohibidas.
- La autoridad de intento PR 2 ya estaba adquirida por el padre. Este agente no ejecutó `sdd-attempt acquire`, `settle` ni reset.

### Trabajo completado y checkboxes persistidos

- Se completaron las pruebas RED/GREEN del webhook para JSON/esquema autenticado inválido, correlación inexistente, discrepancias de plan/monto, campos de autoridad no permitidos, monto no finito y `Content-Type` incorrecto. La tarea RED correspondiente quedó marcada `[x]` en `tasks.md`.
- Se ajustó el router para leer el body una sola vez, exigir `application/json` y devolver un error sanitizado `415`; la superficie `/alta` continúa retirada como frontera de aprovisionamiento. La tarea GREEN del router quedó marcada `[x]`.
- Se añadió validación Pydantic de montos finitos, validación server-owned de checkout/plan/monto y diferenciación de checkout ya procesado (`CHECKOUT_ALREADY_PROVISIONED`).
- Se convirtió el camino legacy `dar_de_alta`/`provisionar_alta` en un shim explícitamente deshabilitado que no persiste efectos; no se alteraron las operaciones HU-005/HU-006.
- Se hizo determinista la proyección de replay seleccionando una única invitación mediante orden estable por identificador.
- La provisión ahora revierte también fallos inesperados durante una etapa de persistencia y los traduce a `OnboardingNotProvisionedError`.

### Evidencia TDD de este lote

| Tarea/lote | Test | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
| --- | --- | --- | --- | --- | --- | --- |
| Webhook autenticado y autoridad | `tests/test_tenant_onboarding.py` | 10 passed | 3 fallos observables antes de cambios | 19 passed | checkout desconocido, plan/monto discordantes, 5 campos prohibidos y 3 montos no finitos | imports/formato limpios |
| Rollback de etapa inesperada | `test_provisioning_rolls_back_unexpected_failure_at_persistence_stage` | 10 passed | `RuntimeError` escapaba sin rollback | 1 passed | fallo en `add_all` y aserción de rollback | sin cambio conductual adicional |
| Replay determinista | `test_replay_projection_selects_one_invitation_deterministically` | 19 passed | invitación dependía del orden de inserción | 1 passed | dos invitaciones con IDs distintos | `order_by(Invitacion.id)` |
| Camino legacy | `test_legacy_onboarding_write_path_is_disabled` | 10 passed | `dar_de_alta` intentaba consultar/persistir | 1 passed | solicitud legacy válida sin checkout escrito | shim explícito sin efectos |

### Archivos modificados en este lote

- `app/modules/tenant/schemas.py`
- `app/modules/tenant/router.py`
- `app/modules/tenant/repository.py`
- `app/modules/tenant/service.py`
- `tests/test_tenant_onboarding.py`
- `openspec/changes/hu004-alta-inmobiliaria/tasks.md`
- `openspec/changes/hu004-alta-inmobiliaria/apply-progress.md`

El worktree también conserva cambios PR 1 y el trabajo PR 2 previo en `app/modules/tenant/models.py`, `app/core/config.py`, `alembic/env.py` y `alembic/versions/0004_hu004_onboarding.py`; no fueron revertidos ni reclasificados.

### Verificación ejecutada

- Safety net inicial: `../.venv/Scripts/python.exe -m pytest tests/test_tenant_onboarding.py -q` → **10 passed**, 3 warnings.
- GREEN focalizado y regresión del archivo: `../.venv/Scripts/python.exe -m pytest tests/test_tenant_onboarding.py -q` → **19 passed**, 3 warnings.
- Suite completa: `../.venv/Scripts/python.exe -m pytest tests -q` → **53 passed**, 3 warnings.
- Pyright: `../.venv/Scripts/pyright.exe app tests` → **0 errors**.
- Ruff: `../.venv/Scripts/python.exe -m ruff check app tests` → **1 I001 preexistente en `app/main.py`**, archivo no modificado en este lote.
- No se ejecutó PostgreSQL/Alembic real; `GAP-092` permanece abierto y `CP-003` sigue `not executed`.

### Desviaciones y límites

- El código `415 UNSUPPORTED_MEDIA_TYPE` es una respuesta HTTP estándar para el requisito de `Content-Type`; el diseño no fijaba un código concreto para esa condición.
- Los métodos legacy se conservaron como shims deshabilitados para evitar una frontera de provisión alternativa sin romper referencias de HU-005/HU-006.
- La selección estable de invitación por ID resuelve la ambigüedad de replay existente sin ampliar el modelo ni la migración.
- No se iniciaron revisores, receipts, gates de delivery, commits, pushes ni cambios de rama.

### Tareas PR 2 restantes (líneas exactas sin completar)

- [ ] Completar pruebas RED de aprovisionamiento atómico y rollback: tenant, suscripción `active` con `trial_fin=NULL`, invitación pendiente, evento procesado y checkout `procesado`; ante fallo en cada persistencia, esperar `500 ONBOARDING_NOT_PROVISIONED` y cero efectos parciales. <!-- sdd-owner: implementation -->
- [ ] Completar pruebas RED de idempotencia secuencial y concurrente con `RLock`/barrera fake y escenarios PostgreSQL preparados: mismo hash devuelve resultado original, hash distinto o evento legacy sin hash devuelve `409 IDEMPOTENCY_CONFLICT`, y checkout ya procesado con otra clave devuelve `409 CHECKOUT_ALREADY_PROVISIONED`. <!-- sdd-owner: implementation -->
- [ ] Completar pruebas RED de activación: hash SHA-256 únicamente persistido, TTL de 7 días con igualdad al vencimiento expirada, notifier solo después del commit, fallo de notifier sin rollback, consumo condicional único y `410 ACTIVATION_UNAVAILABLE` para token inválido/expirado/consumido. <!-- sdd-owner: implementation -->
- [ ] Completar pruebas RED de migración y seed sobre `alembic/versions/0004_hu004_onboarding.py`: `0003` como dependencia, columnas/FK/índices, seed idempotente, adopción legacy exacta, colisión/discrepancia abortada, preservación de HU-005/HU-006 y downgrade bloqueado cuando existen datos HU-004. <!-- sdd-owner: implementation -->
- [ ] Completar pruebas RED de no regresión para rutas y comportamiento existente de HU-005/HU-006, sin añadir trial, cambio de plan, cancelación, cuotas operativas ni purga a HU-004. <!-- sdd-owner: implementation -->
- [ ] Extender `app/modules/tenant/models.py` con `Plan.codigo/max_agents`, `CheckoutIntent`, `Invitacion.consumido_en`, `EventoFacturacion.checkout_id/payload_hash` y restricciones compatibles; conservar nullable legacy y representar `precio_bob` como `Decimal`. <!-- sdd-owner: implementation -->
- [ ] Implementar en `app/modules/tenant/repository.py` `provision_onboarding(command)` como única escritura de alta: locks `FOR UPDATE`, constraints de idempotencia, carga server-owned, inserciones y actualización de checkout en una transacción, rollback completo y recuperación mediante sesión limpia tras colisión concurrente. <!-- sdd-owner: implementation -->
- [ ] Extender `app/modules/tenant/service.py` para ordenar autenticidad → parseo → replay/idempotencia → ventana temporal para eventos nuevos → correlación → provisión; proyectar exactamente `201` nuevo, `200` replay y los errores sanitizados definidos, sin conocer SQL ni traducir genéricamente `IntegrityError`. <!-- sdd-owner: implementation -->
- [ ] Implementar `POST /api/v1/tenant/activacion/consumir` en `app/modules/tenant/router.py` y su servicio/repositorio: hash del token en memoria, actualización condicional `pendiente`/`expira_en > now`, commit propio, notifier posterior al commit y hook nulo sin identidad global, membership o RBAC. <!-- sdd-owner: implementation -->
- [ ] Crear `alembic/versions/0004_hu004_onboarding.py` y ajustar `alembic/env.py` para importación de metadata; hacer migración aditiva, UUIDs de seed determinísticas, adopción legacy solo ante coincidencia exacta, abortar colisiones/discrepancias y proteger el downgrade con datos HU-004. <!-- sdd-owner: implementation -->
- [ ] Ejecutar, cuando corresponda en la fase de apply/verify y no ahora, evidencia PostgreSQL real separada de fakes para locks, constraints, rollback, upgrade desde `0001`/`0003`, seed, fixture legacy, downgrade protegido y consumo concurrente; si PostgreSQL no está disponible, conservar el gap `GAP-092` sin afirmar PASS. <!-- sdd-owner: implementation -->
- [ ] Comparar respuestas HTTP, estados y cardinalidades observables de las cuatro rutas con `spec.md` y `design.md`, incluyendo replay fuera de ventana, notifier posterior al commit, ausencia de secretos/tokens en respuestas y logs, y autoridad server-owned. <!-- sdd-owner: implementation -->
- [ ] Inspeccionar OpenAPI desde `app.main` y verificar exactamente catálogo, checkout, webhook y activación, cuerpos/respuestas documentados y ningún campo sensible; ejecutar además la regresión de HU-005/HU-006 con los comandos definidos en `project-context.md`. <!-- sdd-owner: implementation -->
- [ ] Eliminar duplicación de errores, normalización y proyecciones sin alterar códigos HTTP ni mensajes fijos; mantener separación router → service → repository y límites de puertos. <!-- sdd-owner: implementation -->
- [ ] Auditar seguridad y observabilidad en `app/modules/tenant/`: no registrar raw body, firma, secreto, token, hash de token, contraseña, correo completo ni SQL; usar solo identificadores opacos y resultados sanitizados. <!-- sdd-owner: implementation -->
- [ ] Confirmar que el alta no activa trial de HU-005, no crea identidad global/membership/RBAC, no consume `max_agents` con el admin y no altera funcionalidad de HU-005/HU-006 fuera de adaptaciones indispensables. <!-- sdd-owner: implementation -->
- [ ] Validar el presupuesto final de PR 2 y del cambio completo: mantenerse entre 465–580 estimadas y siempre debajo de 600 líneas modificadas; si supera 600, bloquear antes de apply y devolver el alcance para decisión explícita. <!-- sdd-owner: implementation -->
- [ ] Dejar documentados en el informe de verificación los comandos de gates: `..\.venv\Scripts\python.exe -m pytest tests -q`, Ruff, Pyright y Alembic; no marcar CP-003 como ejecutado sin evidencia real. <!-- sdd-owner: implementation -->

### Workload / boundary

- Delivery resuelto: `stacked-to-main`; este trabajo corresponde únicamente al lote PR 2 autorizado y no crea commits ni PRs.
- El límite nativo comunicado es 500 líneas para este intento; no se amplió el alcance para cerrar migración/concurrencia real y se mantiene el trabajo restante para otro lote cohesivo.

### Riesgos abiertos

- `GAP-092`: no hay evidencia de PostgreSQL real, locks, constraints, upgrade/downgrade ni concurrencia de consumo.
- `CP-003` permanece `not executed`.
- Notifier/outbox real y rollout productivo del checkout continúan fuera de alcance.

## Continuación de aplicación — PR 2, lote 2 de atomicidad, idempotencia, activación e inspección de migración

**Estado:** lote aplicado; PR 2 continúa incompleto y requiere otra continuación/verify posterior.

### Estado estructurado consumido y producido

- `schemaName: spec-driven`; `changeName: hu004-alta-inmobiliaria`; `artifactStore: hybrid`.
- `workspaceRoot`: repositorio backend; `actionContext.mode: repo-local`; se respetaron las superficies autorizadas por el parent y no se detectaron advertencias de raíz.
- Estado consumido: `applyState: ready`, `nextRecommended: apply`, `18/36` tareas completas, estrategia `stacked-to-main`.
- Estado producido: `applyState: ready`, `nextRecommended: apply`, `24/36` tareas de implementación completas, `12` pendientes; no corresponde declarar `all_done` ni `parent-lifecycle` todavía.
- La autoridad nativa de intento PR 2 siguió en el parent. Este agente no ejecutó `sdd-attempt acquire`, `settle`, `reset`, commits, pushes ni cambios de rama.

### Trabajo completado y checkboxes persistidos

- Se marcaron `[x]` las pruebas RED de aprovisionamiento atómico/rollback, idempotencia secuencial/concurrente, activación e inspección estática de migración.
- Se marcó `[x]` la extensión de servicio que conserva la arbitraje de persistencia para checkouts procesados concurrentemente y proyecta un replay recuperado por repositorio como idempotente.
- Se marcó `[x]` la superficie de consumo de activación, cubierta con hash en persistencia fake, expiración, consumo único, notifier posterior al commit, fallo de notifier y hook nulo.
- La prueba fake ahora conserva por separado el estado persistido y el token entregado al notifier; sus docstrings mantienen explícito que esto no es evidencia PostgreSQL.
- Se agregaron fallas controladas en etapas de tenant, suscripción, invitación, evento, actualización de checkout y commit, verificando cero recursos visibles y checkout confirmado después del rollback fake.
- Se agregaron replay exacto secuencial, conflicto de hash, evento legacy sin hash, checkout procesado con otra clave y carrera concurrente con `RLock`/`Barrier`. La segunda respuesta concurrente recupera el resultado original sin nueva notificación.
- Se añadió inspección de fuente de `0004_hu004_onboarding.py` para dependencia `0003`, columnas, FK, índices parciales, UUIDs determinísticos, seed/adopción y guardas de downgrade. No se declaró ejecución de Alembic.

### Evidencia TDD de este lote

| Tarea/lote | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Atomicidad y rollback | `tests/test_tenant_onboarding.py` | integración fake/servicio | `20 passed` | escrito; una corrida de transición detectó la carrera de checkout | `33 passed` | seis etapas de persistencia y cardinalidades exactas | seam fake transaccional acotado |
| Idempotencia concurrente | `tests/test_tenant_onboarding.py` | servicio con fake concurrente | `20 passed` | `32 passed, 1 failed`: segundo hilo obtuvo `CheckoutAlreadyProvisionedError` | `33 passed` tras corregir arbitraje en service | replay secuencial, payload distinto, legacy sin hash, otra clave y `Barrier(2)` | sin refactor conductual adicional |
| Activación | `tests/test_tenant_onboarding.py` | API/servicio fake | `20 passed` | tests escritos antes de la corrección de producción | `33 passed` | hash, TTL de 7 días, igualdad al vencimiento, notifier fallido, consumo repetido y hook | separación token entregado/persistido |
| Migración | `tests/test_tenant_onboarding.py` | inspección de fuente | `20 passed` | test estático escrito; la migración existente ya cumplía las formas inspeccionadas | evidencia estática `33 passed` | columnas/FK/índices/seeds/guardas | no aplica: sin mutación de migración |

### Archivos modificados en este lote

- `app/modules/tenant/service.py`
- `tests/test_tenant_onboarding.py`
- `openspec/changes/hu004-alta-inmobiliaria/tasks.md`
- `openspec/changes/hu004-alta-inmobiliaria/apply-progress.md`

Se conservaron sin revertir los cambios previos de PR 1 y del lote anterior en modelos, repositorio, router, configuración, metadata y migración. No se modificaron UI, Flutter, pagos/correo reales, identidad/membership/RBAC ni HU-005/HU-006.

### Verificación ejecutada

- Safety net: `..\\.venv\\Scripts\\python.exe -m pytest tests/test_tenant_onboarding.py -q` → **20 passed**, 3 warnings.
- GREEN focalizado: `..\\.venv\\Scripts\\python.exe -m pytest tests/test_tenant_onboarding.py -q` → **33 passed**, 3 warnings.
- Regresión final: `..\\.venv\\Scripts\\python.exe -m pytest tests -q` → **66 passed**, 3 warnings.
- Ruff focalizado: `..\\.venv\\Scripts\\python.exe -m ruff check app/modules/tenant/service.py tests/test_tenant_onboarding.py` → **All checks passed**.
- Pyright focalizado: `..\\.venv\\Scripts\\pyright.exe app/modules/tenant/service.py tests/test_tenant_onboarding.py` → **0 errors, 0 warnings, 0 informations**.
- Integridad de diff: `git diff --check` → sin salida/errores.
- No se ejecutó PostgreSQL ni Alembic real; `GAP-092` permanece abierto y `CP-003` continúa `not executed`.

### Desviaciones y límites

- La concurrencia se prueba únicamente con un fake sincronizado; la corrección mínima permite que el repositorio decida sobre un checkout ya procesado y evita convertir un replay concurrente en conflicto. Locks, constraints y recuperación entre sesiones PostgreSQL siguen sin evidencia.
- La migración se inspeccionó por texto/fuente, tal como permite este lote; esto no prueba upgrade, seed, downgrade ni compatibilidad en una base real.
- El notifier fallido se conserva como estado confirmado sin outbox durable, conforme al diseño; no se inventó reintento de correo.

### Tareas PR 2 restantes (líneas exactas sin completar)

- [ ] Completar pruebas RED de no regresión para rutas y comportamiento existente de HU-005/HU-006, sin añadir trial, cambio de plan, cancelación, cuotas operativas ni purga a HU-004. <!-- sdd-owner: implementation -->
- [ ] Extender `app/modules/tenant/models.py` con `Plan.codigo/max_agents`, `CheckoutIntent`, `Invitacion.consumido_en`, `EventoFacturacion.checkout_id/payload_hash` y restricciones compatibles; conservar nullable legacy y representar `precio_bob` como `Decimal`. <!-- sdd-owner: implementation -->
- [ ] Implementar en `app/modules/tenant/repository.py` `provision_onboarding(command)` como única escritura de alta: locks `FOR UPDATE`, constraints de idempotencia, carga server-owned, inserciones y actualización de checkout en una transacción, rollback completo y recuperación mediante sesión limpia tras colisión concurrente. <!-- sdd-owner: implementation -->
- [ ] Crear `alembic/versions/0004_hu004_onboarding.py` y ajustar `alembic/env.py` para importación de metadata; hacer migración aditiva, UUIDs de seed determinísticas, adopción legacy solo ante coincidencia exacta, abortar colisiones/discrepancias y proteger el downgrade con datos HU-004. <!-- sdd-owner: implementation -->
- [ ] Ejecutar, cuando corresponda en la fase de apply/verify y no ahora, evidencia PostgreSQL real separada de fakes para locks, constraints, rollback, upgrade desde `0001`/`0003`, seed, fixture legacy, downgrade protegido y consumo concurrente; si PostgreSQL no está disponible, conservar el gap `GAP-092` sin afirmar PASS. <!-- sdd-owner: implementation -->
- [ ] Comparar respuestas HTTP, estados y cardinalidades observables de las cuatro rutas con `spec.md` y `design.md`, incluyendo replay fuera de ventana, notifier posterior al commit, ausencia de secretos/tokens en respuestas y logs, y autoridad server-owned. <!-- sdd-owner: implementation -->
- [ ] Inspeccionar OpenAPI desde `app.main` y verificar exactamente catálogo, checkout, webhook y activación, cuerpos/respuestas documentados y ningún campo sensible; ejecutar además la regresión de HU-005/HU-006 con los comandos definidos en `project-context.md`. <!-- sdd-owner: implementation -->
- [ ] Eliminar duplicación de errores, normalización y proyecciones sin alterar códigos HTTP ni mensajes fijos; mantener separación router → service → repository y límites de puertos. <!-- sdd-owner: implementation -->
- [ ] Auditar seguridad y observabilidad en `app/modules/tenant/`: no registrar raw body, firma, secreto, token, hash de token, contraseña, correo completo ni SQL; usar solo identificadores opacos y resultados sanitizados. <!-- sdd-owner: implementation -->
- [ ] Confirmar que el alta no activa trial de HU-005, no crea identidad global/membership/RBAC, no consume `max_agents` con el admin y no altera funcionalidad de HU-005/HU-006 fuera de adaptaciones indispensables. <!-- sdd-owner: implementation -->
- [ ] Validar el presupuesto final de PR 2 y del cambio completo: mantenerse entre 465–580 estimadas y siempre debajo de 600 líneas modificadas; si supera 600, bloquear antes de apply y devolver el alcance para decisión explícita. <!-- sdd-owner: implementation -->
- [ ] Dejar documentados en el informe de verificación los comandos de gates: `..\\.venv\\Scripts\\python.exe -m pytest tests -q`, Ruff, Pyright y Alembic; no marcar CP-003 como ejecutado sin evidencia real. <!-- sdd-owner: implementation -->

### Workload / boundary

- Delivery: `stacked-to-main`; este lote es el segundo lote acotado de PR 2 y deja explícitamente pendientes la implementación/evidencia real del repositorio y migración.
- No se crearon commits ni PRs. El parent conserva la autoridad del límite nativo de 500 líneas y debe liquidar el intento completo; este agente no alteró ese ledger.
- Rollback boundary: retirar el seam/tests de atomicidad, idempotencia y activación y la corrección de proyección/race en `service.py`, sin revertir PR 1 ni eliminar datos de onboarding; la inspección de migración es solo de tests.

## Key Learnings

- La validación de autoridad debe ocurrir después de autenticar el body crudo y antes de generar o persistir identificadores de provisión.
- Un checkout procesado necesita un error distinto de uno inexistente para conservar la semántica de idempotencia entre claves.
- Un rollback seguro debe cubrir también excepciones de infraestructura no tipadas, no solo `SQLAlchemyError`.
- Los datos legacy requieren shims sin efectos y una selección determinista cuando el modelo no conserva una relación histórica completa.

## Continuación de aplicación — PR 2, lote 3 de contrato OpenAPI, no regresión y cierre acotado

**Estado:** implementación del lote completada; queda pendiente únicamente la evidencia PostgreSQL real de `GAP-092`. No se declara `all_done` ni CP-003 ejecutado.

### Estado estructurado consumido y producido

- Estado consumido del parent: `artifactStore: hybrid`, `applyState: ready`, `verify: blocked`, `nextRecommended: apply`, `24/36` tareas completas.
- `actionContext.mode: repo-local`; se respetaron las superficies autorizadas. No se modificaron la raíz del monorepo, `docs/diagramas/Diagrama1.eapx`, ramas, commits ni pushes.
- El parent conserva la autoridad de `sdd-attempt`; este agente no ejecutó `acquire`, `settle`, `reset`, ni alteró el ledger nativo.
- Estado producido en el artefacto local: `35/36` tareas completas; `applyState` permanece `ready`, `verify` permanece bloqueado por la evidencia PostgreSQL ausente y `GAP-092` sigue abierto.
- La lectura Engram fue intentada para los cuatro topic keys requeridos, pero el proveedor no respondió en `127.0.0.1:7437`; la persistencia híbrida de este lote se realizó en el artefacto OpenSpec local. No se afirma una escritura Engram inexistente.

### Trabajo completado y checkboxes persistidos

- Se añadió una prueba compacta de no regresión que conserva las cinco rutas HU-005/HU-006 y verifica trial de 14 días, suscripción mensual, cambio de plan, cancelación y purga; no agrega comportamiento HU-004 a esas historias.
- Se amplió la aserción OpenAPI para exigir exactamente las cuatro superficies HU-004 (`plans`, `checkout`, `webhook`, `activacion/consumir`), conservar las cinco superficies HU-005/HU-006 y rechazar campos sensibles en respuestas y campos de autoridad en requests.
- Se documentó en OpenAPI el body crudo del webhook mediante `WebhookRequest` sin convertirlo en un parámetro FastAPI que deserialice antes de autenticar; también se documentaron `201` y el replay `200`.
- Se corrigió una fuga de contrato en el replay SQL: después de consumir la activación, el replay sigue proyectando el resultado original `activacion_admin="pendiente"`, compatible con `WebhookResponse`, sin volver a notificar ni exponer el token.
- Se revisaron `models.py`, `repository.py`, `0004_hu004_onboarding.py` y `alembic/env.py` contra el diseño. Los campos Decimal/nullable legacy, la transacción única, `FOR UPDATE`, unicidad persistente, FK, índice parcial, seed determinístico/idempotente y guardas de downgrade son estructuralmente coherentes; se marcaron sus tareas de implementación como `[x]` sin refactor adicional.
- Se revisaron errores, excepciones y observabilidad del módulo: no hay logger/print que emita body crudo, firma, secreto, token/hash, password, correo completo ni SQL; las respuestas HTTP permanecen sanitizadas.
- Se confirmó mediante código y pruebas que HU-004 no activa el trial HU-005, no crea `usuario_global`/membership/RBAC, no consume `max_agents` con el administrador y conserva las operaciones de HU-005/HU-006.
- Se marcaron `[x]` las tareas de no regresión, modelos, repositorio, migración, comparación de contrato/flujo, OpenAPI/regresión, revisión de duplicación, auditoría de seguridad, límites de alcance, presupuesto del lote y documentación de gates. Se dejó sin marcar la tarea de evidencia PostgreSQL real.

### Evidencia TDD de este lote

| Tarea/lote | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAPI y contrato HTTP | `tests/test_tenant_onboarding.py` | API/contrato | `33 passed` | escrito primero; falló por esquema de lista y luego por falta de respuesta `201` documentada | `35 passed` tras documentar body y `200/201` | cuatro rutas HU-004, cinco rutas HU-005/HU-006, respuestas y campos sensibles | documentación mínima en decorator |
| No regresión HU-005/HU-006 | `tests/test_tenant_onboarding.py` | servicio + OpenAPI | `33 passed` | test de aprobación escrito antes de cambios de producción | `2 passed` focalizados | trial, mensualidad, cambio, cancelación y purga | sin cambio conductual |
| Replay posterior a activación | `tests/test_tenant_onboarding.py` | repositorio SQL/fake | `33 passed` | `1 failed`: se proyectaba `consumida` contra `WebhookResponse` | `1 passed` tras fijar la proyección original | dos invitaciones con orden determinista y primera consumida | comentario explícito del contrato |

### Archivos modificados en este lote

- `app/modules/tenant/router.py`
- `app/modules/tenant/repository.py`
- `tests/test_tenant_onboarding.py`
- `openspec/changes/hu004-alta-inmobiliaria/tasks.md`
- `openspec/changes/hu004-alta-inmobiliaria/apply-progress.md`

No se hizo churn en modelos, migración ni `alembic/env.py` porque la revisión estructural no encontró una corrección concreta pendiente.

### Verificación ejecutada

- Safety net antes de escribir pruebas: `..\\.venv\\Scripts\\python.exe -m pytest tests/test_tenant_onboarding.py -q` → **33 passed**, 3 warnings.
- RED OpenAPI: primera ejecución focalizada → **33 passed, 1 failed** por la forma array real de `GET /plans`; tras corregir la aserción, → **33 passed, 1 failed** por falta de respuesta `201` del webhook en OpenAPI.
- GREEN focalizado: `..\\.venv\\Scripts\\python.exe -m pytest tests/test_tenant_onboarding.py -q -x` → **35 passed**, 3 warnings.
- TRIANGULATE: `..\\.venv\\Scripts\\python.exe -m pytest tests/test_tenant_onboarding.py -q -k 'openapi_contract or hu005_hu006'` → **2 passed**, 3 warnings; replay consumido RED → GREEN: **1 passed**.
- Suite completa: `..\\.venv\\Scripts\\python.exe -m pytest tests -q` → **68 passed**, 3 warnings.
- Ruff focalizado: `..\\.venv\\Scripts\\python.exe -m ruff check app/modules/tenant tests/test_tenant_onboarding.py alembic/env.py alembic/versions/0004_hu004_onboarding.py` → **All checks passed**.
- Ruff completo: `..\\.venv\\Scripts\\python.exe -m ruff check app tests` → **1 error `I001` preexistente en `app/main.py`**, archivo fuera de este lote y no modificado; no se aplicó un normalizador fuera de alcance.
- Pyright completo: `..\\.venv\\Scripts\\pyright.exe app tests` → **0 errors, 0 warnings, 0 informations**.
- Integridad: `git diff --check` → sin salida/errores.
- PostgreSQL: `pg_isready` y `psql` no están disponibles; una conexión no mutante `SELECT 1` usando el `DATABASE_URL` configurado terminó en `OperationalError`. No se ejecutaron Alembic upgrade/downgrade ni integración PostgreSQL. `GAP-092` permanece abierto y no se afirma PASS.

### Presupuesto, workload y límite PR

- Boundary: `stacked-to-main`, PR 2; este lote contiene únicamente contrato OpenAPI, regresión, corrección puntual de replay y evidencia de cierre.
- El parent fijó para este intento fresco un máximo nativo de 500 líneas y un inventario esperado que excluye el trabajo previo. La nueva edición se mantuvo compacta; no se borraron tests/docs ni se hizo code-golf.
- `git diff --stat` del worktree completo muestra `1,756 insertions(+), 201 deletions(-)` porque conserva PR 1 y los lotes previos de PR 2; ese conteo acumulado no se presenta como presupuesto del intento fresco. La autoridad del límite efectivo es el ledger nativo del parent.
- Rollback boundary: retirar la documentación OpenAPI, la prueba de no regresión y la corrección de proyección de replay de este lote, sin revertir PR 1, provisión, activación ni migración, y sin eliminar datos.

### Desviaciones y riesgos

- La documentación del webhook usa `openapi_extra` para conservar la lectura/autenticación del body crudo; no se añadió un parámetro Pydantic al handler.
- El replay devuelve la proyección original pendiente aunque la activación actual pueda estar consumida, para respetar el contrato de resultado original y su esquema literal; el endpoint de activación sigue exponiendo su consumo por separado.
- La evidencia de locks, constraints, seed, upgrade/downgrade y consumo concurrente real sigue sin existir por indisponibilidad de PostgreSQL. La prueba fake continúa etiquetada como fake y no sustituye esa evidencia.

### Tareas PR 2 restantes (línea exacta sin completar)

- [ ] Ejecutar, cuando corresponda en la fase de apply/verify y no ahora, evidencia PostgreSQL real separada de fakes para locks, constraints, rollback, upgrade desde `0001`/`0003`, seed, fixture legacy, downgrade protegido y consumo concurrente; si PostgreSQL no está disponible, conservar el gap `GAP-092` sin afirmar PASS. <!-- sdd-owner: implementation -->

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAPI contract | `tests/test_tenant_onboarding.py` | API/contract | ✅ 33/33 | ✅ written; failed on undocumented `201` | ✅ 35 passed | ✅ four HU-004 paths + HU-005/HU-006 + field checks | ✅ minimal decorator docs |
| HU-005/HU-006 regression | `tests/test_tenant_onboarding.py` | service/contract | ✅ 33/33 | ✅ approval test written | ✅ 2 passed | ✅ five legacy behaviors | ➖ none needed |
| Replay projection | `tests/test_tenant_onboarding.py` | unit/integration fake | ✅ 33/33 | ✅ 1 failed on consumed state | ✅ 1 passed | ✅ deterministic invitation selection + consumed edge | ✅ explicit original-result comment |

### Key Learnings

- El body crudo puede seguir autenticándose antes del parseo y, aun así, quedar descrito en OpenAPI mediante `openapi_extra`.
- Los replays deben proyectar el resultado original persistido; no deben derivar un estado incompatible del contrato por una mutación posterior de activación.
- Una prueba corta que combine rutas registradas con operaciones existentes aporta regresión sin agregar funcionalidad de HU-005/HU-006.


## Continuación de aplicación — PR 2, corrección quirúrgica del orden FK (reintento en backend)

**Estado:** corrección aplicada y verificada con dobles locales; la evidencia PostgreSQL real permanece pendiente. No se declara `all_done`, no se marca CP-003 como ejecutado y no se marca completa la tarea PostgreSQL.

### Estado estructurado consumido y producido

- Estado consumido del contexto parent: `artifactStore: hybrid`, `applyState: ready`, `verify: blocked`, `nextRecommended: apply`, `actionContext.mode: repo-local`.
- La raíz activa fue resuelta desde el primer comando como `D:/universidad/Proyectos/2doSemestre2026/sw1/proyecto_final/backend`; se respetaron únicamente las superficies autorizadas y no se tocó el monorepo root.
- Por ownership del parent no se invocaron native SDD status, `sdd-attempt acquire`, `settle`, reset ni comandos de autoridad.
- Estado producido: `applyState: ready`, `verify: blocked` por `GAP-092`, `35/36` tareas visibles como completas; `nextRecommended` para este agente es `parent-lifecycle` porque el parent debe liquidar la corrección y ejecutar la integración PostgreSQL fresca.
- No hubo advertencias adicionales de `actionContext`; el incidente de cwd quedó corregido antes de leer o escribir artefactos.

### Defecto y corrección aplicada

- La ejecución PostgreSQL real del parent contra Alembic `0004` demostró que `session.add_all([tenant, subscription, invitation, event])` no garantiza que `evento_facturacion` se inserte después de su `suscripcion` referenciada. El fake previo no modelaba ese ordenamiento ORM.
- En `app/modules/tenant/repository.py`, `_provision_onboarding` ahora hace `add(tenant)` + `flush()`, luego `add(subscription)` + `flush()`, y finalmente añade invitación/evento y hace el flush final antes del mismo `commit()`.
- La transacción única y todos los caminos de rollback se conservaron; no se rediseñó el repositorio ni se afirmó que la base local contenga filas HU-004.
- En `tests/test_tenant_onboarding.py` se añadió `ForeignKeyOrderingSession`, un seam deliberadamente fake-only que revierte el orden de `add_all` y falla si el evento se evalúa antes de persistir la suscripción. La docstring y el test dejan explícito que no es evidencia PostgreSQL.
- El fake existente de fallo de persistencia se adaptó al método `add` real para que la prueba de rollback continúe verificando una falla en la etapa de persistencia, no una ausencia accidental de método.

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FK-safe onboarding persistence ordering | `tests/test_tenant_onboarding.py` | repository / fake-only persistence seam | prior persisted batch: `68 passed` | `1 failed, 35 deselected, 3 warnings` on event-before-subscription check | `1 passed, 35 deselected, 3 warnings` after ordered flushes | rollback + ordering focused tests: `2 passed, 34 deselected, 3 warnings`; full suite `69 passed` | Ruff focused passed; Pyright focused passed; `git diff --check` clean |

### Archivos modificados en esta continuación

- `app/modules/tenant/repository.py`
- `tests/test_tenant_onboarding.py`
- `openspec/changes/hu004-alta-inmobiliaria/apply-progress.md`

`openspec/changes/hu004-alta-inmobiliaria/tasks.md` no se modificó en esta corrección: permanece en `35/36`, con la tarea de evidencia PostgreSQL real sin marcar.

### Verificación ejecutada desde backend

- RED: `../.venv/Scripts/python.exe -m pytest tests/test_tenant_onboarding.py -q -k provisioning_persists_subscription_before_event_with_fake_seam` → **1 failed**, 35 deselected, 3 warnings.
- GREEN: el mismo comando tras la corrección → **1 passed**, 35 deselected, 3 warnings.
- Rollback y regresión de la seam: `../.venv/Scripts/python.exe -m pytest tests/test_tenant_onboarding.py -q -k 'provisioning_rolls_back_unexpected_failure_at_persistence_stage or provisioning_persists_subscription_before_event_with_fake_seam'` → **2 passed**, 34 deselected, 3 warnings.
- Suite: `../.venv/Scripts/python.exe -m pytest tests -q` → **69 passed**, 3 warnings.
- Ruff: `../.venv/Scripts/python.exe -m ruff check app/modules/tenant/repository.py tests/test_tenant_onboarding.py` → **All checks passed**.
- Pyright: `../.venv/Scripts/pyright.exe app/modules/tenant/repository.py tests/test_tenant_onboarding.py` → **0 errors, 0 warnings, 0 informations**.
- Integridad: `git diff --check` → sin salida/errores.
- PostgreSQL/Alembic: **no ejecutados por este agente**. La prueba fake no sustituye la integración real; `GAP-092` sigue abierto y el parent debe realizar una corrida fresca.

### Desviaciones y riesgos

- La prueba nueva modela únicamente el riesgo de orden de persistencia y está rotulada fake-only; no demuestra locks, constraints, rollback, seed, migración ni concurrencia PostgreSQL.
- No se actualizaron contadores ni se marcó la tarea restante para convertir evidencia fake en PostgreSQL.
- No se crearon commits, pushes, ramas, receipts, revisores ni gates de delivery. El parent conserva el token de corrección y debe liquidarlo con la evidencia de revisión exacta que corresponda.

### Tarea restante exacta

- [ ] Ejecutar, cuando corresponda en la fase de apply/verify y no ahora, evidencia PostgreSQL real separada de fakes para locks, constraints, rollback, upgrade desde `0001`/`0003`, seed, fixture legacy, downgrade protegido y consumo concurrente; si PostgreSQL no está disponible, conservar el gap `GAP-092` sin afirmar PASS. <!-- sdd-owner: implementation -->

### Workload / boundary

- `stacked-to-main`, PR 2; esta continuación es una corrección quirúrgica de orden FK, junto con su seam de regresión, sin expansión de alcance.
- Rollback boundary: retirar únicamente los flushes ordenados y `ForeignKeyOrderingSession`/su prueba, sin revertir los lotes previos de PR 1/PR 2 ni eliminar datos de onboarding.
- El cambio queda listo para que el parent ejecute la integración PostgreSQL fresca; no queda listo para declarar PR 2 completo.

### Key Learnings

- El orden de una colección entregada a `Session.add_all` no es una garantía suficiente para satisfacer FKs cuando las relaciones ORM no expresan la dependencia; un `flush` explícito de la fila referenciada cierra esa incertidumbre.
- La evidencia fake puede detectar la regresión de orden si falla de forma adversarial, pero debe permanecer etiquetada y separada de la evidencia PostgreSQL real.

## Continuación de aplicación — PR 2, corrección quirúrgica de replay concurrente

**Estado:** corrección aplicada y verificada en unidad fake; no se declara `all_done`, CP-003 ni evidencia PostgreSQL real.

### Estado estructurado consumido y producido
- `schemaName: gentle-ai.sdd-status`, `changeName: hu004-alta-inmobiliaria`, `artifactStore: hybrid`; consumido: `applyState: ready`, `verify: blocked`, `nextRecommended: apply`, `35/36` tareas.
- `actionContext.mode: repo-local`; edición limitada a backend y superficies autorizadas, sin advertencias. El parent conserva el token; este agente no ejecutó `sdd-attempt`, settlement, reset, commits, pushes ni cambios de rama. Próximo paso: `parent-lifecycle`.

### Defecto y corrección
- Ambas solicitudes pasaban el lookup inicial; la perdedora esperaba el lock de checkout y convertía el evento ya persistido en `CheckoutAlreadyProvisionedError`.
- Tras bloquear un checkout `procesado`, `_provision_onboarding` relee `EventoFacturacion` por el mismo `command.idempotency_key` con `lock=True`; si existe, devuelve `_replay(existing, command.payload_hash)`, y si no existe conserva el error.
- No cambiaron rollback, recuperación `IntegrityError`, conflictos de hash ni eventos legacy. La prueba nueva es fake/unit-only y no sustituye PostgreSQL.

### TDD Cycle Evidence
| Task | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
| --- | --- | --- | --- | --- | --- |
| Concurrent processed-checkout replay | focused prior: `5 passed` | `1 failed` on old loser error | `1 passed` | `4 passed` (matching, other key, legacy, concurrent fake) | clean; no behavior refactor |

### Archivos y checkboxes
- Modificados: `app/modules/tenant/repository.py`, `tests/test_tenant_onboarding.py`, `openspec/changes/hu004-alta-inmobiliaria/apply-progress.md`.
- `tasks.md` no cambió: la tarea de repositorio ya estaba `[x]`; la única tarea restante PostgreSQL sigue `[ ]`.

### Verificación ejecutada desde backend
- Focalizado RED/GREEN: `../.venv/Scripts/python.exe -m pytest tests/test_tenant_onboarding.py -q -k processed_checkout_rechecks_matching_event_key_for_replay` → **1 failed**, luego **1 passed**.
- TRIANGULATE: el filtro concurrente/replay/legacy → **4 passed**.
- Suite: `../.venv/Scripts/python.exe -m pytest tests -q` → **70 passed**, 3 warnings.
- Ruff: `../.venv/Scripts/python.exe -m ruff check app/modules/tenant/repository.py tests/test_tenant_onboarding.py` → **All checks passed**; Pyright: `../.venv/Scripts/pyright.exe app/modules/tenant/repository.py tests/test_tenant_onboarding.py` → **0 errors, 0 warnings, 0 informations**; `git diff --check -- app/modules/tenant/repository.py tests/test_tenant_onboarding.py openspec/changes/hu004-alta-inmobiliaria/apply-progress.md` → limpio.
- No se ejecutaron PostgreSQL/Alembic; permanecen `GAP-092`, checks de upgrade/downgrade/locks/constraints y la tarea de evidencia real.

### Tarea restante exacta
- [ ] Ejecutar, cuando corresponda en la fase de apply/verify y no ahora, evidencia PostgreSQL real separada de fakes para locks, constraints, rollback, upgrade desde `0001`/`0003`, seed, fixture legacy, downgrade protegido y consumo concurrente; si PostgreSQL no está disponible, conservar el gap `GAP-092` sin afirmar PASS. <!-- sdd-owner: implementation -->

### Workload / boundary y riesgos
- `stacked-to-main`, PR 2; corrección acotada a la carrera, un test seam y este registro. Rollback: retirar únicamente el recheck y la prueba nueva. La integración PostgreSQL fresca F-H y el settlement nativo son responsabilidad del parent.

### Key Learnings
- Bloquear el checkout no basta: tras esperar, el estado `procesado` debe reconciliarse con una segunda lectura por la misma clave antes de reportar conflicto.

## Continuación de aplicación — PR 2, segunda corrección quirúrgica de replay PostgreSQL

**Estado:** corrección aplicada y verificada localmente; la prueba PostgreSQL fresca F-H, la liquidación de la corrección y la evidencia de entrega siguen bajo responsabilidad del parent. No se declara `all_done`, `CP-003` ni evidencia PostgreSQL real.

### Estado estructurado consumido y producido

- `schemaName: gentle-ai.sdd-status`, `changeName: hu004-alta-inmobiliaria`, `artifactStore: hybrid`; `applyState: ready`, `verify: blocked`, `nextRecommended: apply`.
- Progreso persistido: `35/36` tareas de implementación completas; la única tarea restante es la evidencia PostgreSQL real. No se modificó `tasks.md` ni cambió el conteo.
- `actionContext.mode: repo-local`; `workspaceRoot` y única raíz autorizada corresponden al backend. No se editaron artefactos del monorepo raíz ni superficies fuera de las autorizadas.
- El workload sigue siendo `stacked-to-main`, PR 2, con `Decision needed before apply: No`, `Chained PRs recommended: Yes` y `400-line budget risk: High`; esta corrección es un slice quirúrgico dentro del límite nativo vigente, sin fixture nuevo ni expansión de alcance.
- El parent conserva el token de corrección y la autoridad de settlement. Este agente no ejecutó `sdd-attempt`, settlement, reset, commits, pushes, cambios de rama, revisores, receipts ni gates.

### Diagnóstico y corrección

- El precheck de `TenantService` ejecuta `buscar_checkout` sin lock antes de delegar la provisión. En la misma sesión SQLAlchemy, ese lookup puede dejar un `CheckoutIntent` cacheado con `estado='confirmado'` en el identity map.
- Aunque `_find(..., lock=True)` espere correctamente el lock de PostgreSQL, SQLAlchemy puede devolver esa instancia cacheada sin refrescar sus atributos; la rama de checkout procesado no se activa y el replay concurrente termina como `CheckoutAlreadyProvisionedError`.
- `TenantRepository._find` ahora construye el `select` y, solamente para `lock=True`, aplica `with_for_update()` junto con `execution_options(populate_existing=True)` antes de `session.scalar`. El comportamiento de las lecturas no bloqueantes permanece sin cambios.
- No se alteraron la segunda lectura por clave, `_replay`, rollback, recuperación de `IntegrityError`, conflictos de hash ni la semántica de eventos legacy. No se agregó una prueba persistente para conservar el presupuesto de la corrección; la evidencia TDD nueva usa un probe ejecutable en línea y las pruebas existentes.

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Refresh locked identity-mapped reads | `tests/test_tenant_onboarding.py` + probe Python inline | repository / fake SQLAlchemy statement seam | ✅ 2 focused tests passed | ✅ inline probe failed because locked statement lacked `populate_existing` | ✅ 2 focused tests passed and probe passed | ✅ 4 replay/idempotency tests passed; inline probe confirmed locked refresh and unchanged unlocked reads | ➖ none needed; kept the one-branch production change minimal |

The inline probe was deliberately not persisted as a new fixture: it asserted both `FOR UPDATE` and `populate_existing=True` for locked reads, then asserted no lock/refresh option for an unlocked read. It is supplemental local evidence, not PostgreSQL evidence.

### Archivos modificados en esta continuación

- `app/modules/tenant/repository.py`
- `openspec/changes/hu004-alta-inmobiliaria/apply-progress.md`

`tests/test_tenant_onboarding.py` no se modificó en esta segunda corrección; se conservaron la prueba existente de replay tras checkout procesado y los seams fake-only previos.

### Verificación ejecutada desde backend

- Safety net: `../.venv/Scripts/python.exe -m pytest tests/test_tenant_onboarding.py -q -k 'processed_checkout_rechecks_matching_event_key_for_replay or concurrent_exact_replays_create_one_set_and_one_notification'` → **2 passed**, 35 deselected, 3 warnings.
- RED: probe inline con el mismo runner → **falló** en `populate_existing` ausente para la lectura bloqueada.
- GREEN: el mismo filtro → **2 passed**, 35 deselected, 3 warnings; probe inline → **pasó**.
- TRIANGULATE: `../.venv/Scripts/python.exe -m pytest tests/test_tenant_onboarding.py -q -k 'processed_checkout_rechecks_matching_event_key_for_replay or webhook_replay_conflict_and_processed_checkout_preserve_cardinality or concurrent_exact_replays_create_one_set_and_one_notification or legacy_event_without_payload_hash_is_not_replayed'` → **4 passed**, 33 deselected, 3 warnings; probe inline de lock/unlocked → **pasó**.
- Suite completa: `../.venv/Scripts/python.exe -m pytest tests -q` → **70 passed**, 3 warnings.
- Ruff focalizado: `../.venv/Scripts/python.exe -m ruff check app/modules/tenant/repository.py tests/test_tenant_onboarding.py` → **All checks passed**.
- Pyright focalizado: `../.venv/Scripts/pyright.exe app/modules/tenant/repository.py tests/test_tenant_onboarding.py` → **0 errors, 0 warnings, 0 informations**.
- Integridad: `git diff --check -- app/modules/tenant/repository.py tests/test_tenant_onboarding.py openspec/changes/hu004-alta-inmobiliaria/apply-progress.md` → limpio.
- No se ejecutaron PostgreSQL, Alembic ni los escenarios reales F-H. Permanecen pendientes la verificación PostgreSQL de locks, constraints, rollback, upgrade/downgrade, seed, fixture legacy y concurrencia; `GAP-092` sigue abierto.

### Tareas y límites pendientes

- No hubo checkbox actualizado en esta corrección. `tasks.md` debe seguir mostrando `35/36` y esta línea exacta como única tarea sin completar:
- [ ] Ejecutar, cuando corresponda en la fase de apply/verify y no ahora, evidencia PostgreSQL real separada de fakes para locks, constraints, rollback, upgrade desde `0001`/`0003`, seed, fixture legacy, downgrade protegido y consumo concurrente; si PostgreSQL no está disponible, conservar el gap `GAP-092` sin afirmar PASS. <!-- sdd-owner: implementation -->
- El parent debe ejecutar una corrida fresca F-H contra PostgreSQL para confirmar que el lock lee `estado='procesado'` después de esperar, que el replay exacto devuelve `_replay` y que una clave distinta conserva `CHECKOUT_ALREADY_PROVISIONED`; luego debe aportar evidencia fresca y liquidar la corrección con el vínculo de remediación requerido.

### Workload / boundary y riesgos

- Boundary: `stacked-to-main`, PR 2; únicamente se corrigió el refresco de lecturas bloqueadas. No se creó un nuevo fixture y la edición de producción se mantuvo mínima para respetar el límite nativo de 100 líneas de la corrección.
- Rollback boundary: retirar la aplicación de `populate_existing=True` del branch bloqueado de `_find`, sin revertir el recheck por clave ni los lotes previos, y sin eliminar datos de onboarding.
- Riesgos abiertos: `GAP-092`, migración/upgrade/downgrade real, constraints, locks PostgreSQL y concurrencia PostgreSQL siguen sin confirmación; `CP-003` permanece `not executed`.

## Key Learnings

- `FOR UPDATE` protege la fila, pero no garantiza por sí solo que SQLAlchemy refresque una instancia existente en el identity map; las lecturas bloqueadas que arbitran estado concurrente deben usar `populate_existing=True`.
- Un precheck no bloqueante y una lectura bloqueada posterior pueden compartir una instancia stale; la corrección debe estar en la lectura de autoridad del repositorio, no en otro workaround del servicio.

## Cierre de evidencia PostgreSQL real — PR 2

**Estado:** las 36 tareas están completadas. La evidencia real se ejecutó en la base local y en bases PostgreSQL temporales desechables; no se declara CP-003 ejecutado ni se cierra el GAP-092 global de migraciones pendientes del proyecto.

### Evidencia consolidada

- Base local: PostgreSQL `16.14`, Alembic `0004`; la provisión real creó tenant activo, suscripción activa sin `trial_fin`, invitación pendiente con hash únicamente, evento procesado y checkout procesado. El replay desde otra sesión devolvió los mismos identificadores sin duplicar recursos.
- Base local: dos sesiones PostgreSQL consumieron la misma activación; exactamente una operación tuvo resultado y la otra devolvió `None`; la invitación terminó `consumida`. Un token duplicado provocó `OnboardingNotProvisionedError`, sin filas parciales y con el checkout fallido aún `confirmado`.
- Base temporal, upgrade/fixture: `0001 → 0002 → 0003` y `0003 → 0004` terminaron correctamente; tres planes legacy compatibles fueron adoptados conservando sus UUIDs, con códigos y `max_agents` canónicos. La repetición de upgrade fue idempotente.
- Base temporal, seed/downgrade: downgrade limpio a `0003`, seed determinístico desde tabla de planes vacía y nueva repetición idempotente pasaron. Con un checkout HU-004, el downgrade fue rechazado y la revisión permaneció `0004`; tras borrar únicamente ese checkout temporal, el downgrade a `0003` pasó.
- Base temporal, concurrencia final: dos webhooks idénticos en sesiones independientes produjeron exactamente un `created=true` y un replay `created=false/idempotente=true`, una sola fila de cada recurso y estados/FKs válidos. La causa fue corregida con `populate_existing=True` en lecturas bloqueadas y relectura de la misma clave después del lock.
- Todas las bases temporales fueron eliminadas; la base `roomforge` quedó sin filas HU-004 después de la limpieza exacta. No se ejecutaron operaciones amplias ni downgrade sobre la base de desarrollo.

### Evidencia de código y gates

- Suite completa: `../.venv/Scripts/python.exe -m pytest tests -q` → **70 passed**, 3 warnings.
- Ruff focalizado de superficies PR2 → **All checks passed**; el único `I001` del Ruff completo permanece preexistente en `app/main.py`, sin modificación.
- Pyright focalizado/completo → **0 errores**.
- `git diff --check` → limpio.
- El ledger nativo registró los lotes de corrección como completos: orden FK, replay concurrente y refresco de lecturas bloqueadas; no hubo commits ni pushes.

### Decisiones y pendientes honestos

- La línea de evidencia PostgreSQL de `tasks.md` se marcó `[x]` porque todos sus escenarios fueron ejecutados y documentados con separación explícita entre fakes y PostgreSQL real.
- `GAP-092` continúa abierto para las migraciones restantes del proyecto fuera de este cambio y `CP-003` continúa sin marcar como caso académico ejecutado; no se inventa evidencia de esos registros.
- El techo total de líneas de este cambio fue elevado a `1000` por autorización explícita del usuario; los lotes nativos permanecieron acotados y la corrección final no amplió el alcance funcional.
- No se modificaron UI/Flutter, pagos o correo reales, identidad global, memberships/RBAC, trial HU-005 ni cambios/purga HU-006.

### Key Learnings

- La evidencia fake detectó la regla de orden, pero PostgreSQL reveló tanto la dependencia FK como la instancia stale del identity map; ambos riesgos requieren pruebas con sesiones reales.
- `FOR UPDATE` sin `populate_existing=True` puede arbitrar una versión vieja de una entidad cacheada; la lectura bloqueada debe ser la fuente de autoridad después de una espera concurrente.
- La provisión real y el replay concurrente deben verificarse por cardinalidad, estado, FK, respuesta y limpieza; una suite fake no basta para confirmar estas propiedades.
