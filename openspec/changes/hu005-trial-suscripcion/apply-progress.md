# Apply progress — `hu005-trial-suscripcion`

- **Work unit:** `WU-005-TDD` / RED only; no GREEN, TRIANGULATE or REFACTOR work was started.
- **Structured status consumed:** `applyState: ready`, `nextRecommended: apply`, `artifactStore: hybrid` with authoritative local OpenSpec files; `actionContext.mode: repo-local`, workspace and allowed edit root are the backend worktree. No status blockers or action-context warnings were reported.
- **Workload boundary:** forecast `372/400`, risk `Medium`, no chained PR recommended; this unit has an `88`-line ceiling and the parent-owned runtime authority remains responsible for settlement.

## Preflight evidence

- Alembic revisions are a single chain `0001 → 0002 → 0003 → 0004`; `0004_hu004_onboarding.py` is the unique file head and has `down_revision = "0003"`. `alembic/env.py` imports identity/tenant models into `Base.metadata`.
- HU-004 delta in `0004`: plan `codigo`/`max_agents`, `checkout_intencion`, invitation `consumido_en`, event `checkout_id`/`payload_hash`, FK/index/unique constraints and catalog adoption/seed; no HU-005 migration was created.
- HMAC seam: `HMACWebhookSignatureVerifier`; errors `SignatureValidationError` and `WebhookNotConfiguredError`; headers `X-RoomForge-Webhook-Timestamp`/`X-RoomForge-Webhook-Signature`; message `ASCII(timestamp) + b"." + raw_body`; SHA-256/constant-time comparison; default tolerance `300` seconds and inclusive boundary.
- Current seams: `TenantService` still has client-authority `activar_prueba`/legacy `suscribirse`; `TenantRepository` has separate legacy writes and no monthly conversion method; router lacks bootstrap and subscription inspection; `get_current_user` and HU-004 HMAC helpers remain unchanged.
- Focused test choice: extend only `tests/test_tenant_onboarding.py`; existing HMAC/raw-body, replay, rollback and HU-004 helpers were reused. `tests/test_autenticacion.py` was read and not modified. PostgreSQL-only locks, isolation, uniqueness, migration and concurrency remain pending.

## RED work completed

- Marked only implementation-owned `T-RED-01` through `T-RED-12` as `[x]` in `tasks.md`; parent-owned rows remain byte-for-byte unchanged.
- Added failing contract/security, monthly HMAC/idempotency, calendar, exact-336-hour and PostgreSQL/migration-boundary RED assertions. Removed only the insecure HU-005 expectation from the legacy combined test; HU-006 assertions and existing HU-004 tests remain.
- No production code, model, schema, service, repository, router, signature, Alembic migration, identity code, root repository, branch, commit, push, migration execution, lint, typecheck or delivery operation was changed or run.

## TDD Cycle Evidence

| Work unit | Test file | Layer | Safety net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| `WU-005-TDD` | `tests/test_tenant_onboarding.py` | FastAPI/unit fake plus pure-calendar contract | `37 passed` with configured test secret | `7 failed, 37 passed` | Not started by authorization | Not started | Not started |

## Verification and accounting

- **Baseline:** the requested relative venv path was absent from this worktree; the existing backend venv at `../proyecto_final/.venv/Scripts/python.exe` ran the focused baseline as `37 passed, 3 warnings`. An initial no-secret baseline exposed one pre-existing JWT configuration failure; no product code was changed to mask it.
- **RED command:** `../proyecto_final/.venv/Scripts/python.exe -m pytest tests/test_tenant_onboarding.py -q`.
- **Actual RED outcome:** `7 failed, 37 passed, 3 warnings in 2.75s`; failures are the intended absent HU-005 contract/calendar seams (`ActivarPruebaRequest` still accepts `tenant_id`, monthly routes return `422`, and the new calendar/trial methods are absent). This is not PASS.
- **Changed paths:** `tests/test_tenant_onboarding.py`; `openspec/changes/hu005-trial-suscripcion/tasks.md`; `openspec/changes/hu005-trial-suscripcion/apply-progress.md`.
- **Changed-line count:** focused test diff is `38 additions + 15 deletions = 53` changed lines; task bookkeeping changes 12 checkbox rows (`12 additions + 12 deletions`); no production-code lines changed. The progress artifact is bookkeeping and is not counted as product/test implementation budget.
- **Design deviations:** none. Calendar and trial-duration calls intentionally name RED seams for later GREEN design; the PostgreSQL/migration assertion is only a placeholder and does not claim PostgreSQL evidence.
- **Rollback boundary:** remove only the new RED assertions and restore the 12 implementation task checkboxes; preserve all HU-004/HU-006 tests and helpers. No schema/data rollback applies.
- **CP-004:** `not executed`.
- **Next recommended work unit:** parent settles this bounded RED attempt, then authorize `WU-005-DATA` / GREEN; do not run TRIANGULATE or REFACTOR from this result.

## Remaining task rows (exact unchecked lines)

- [ ] **T-GREEN-01.** Modificar `app/modules/tenant/models.py` con `Suscripcion.trial_inicio`, `Suscripcion.periodo_inicio` como `DateTime(timezone=True)` nullable y `TenantAdministrator` con UUID, FKs, `activo`, timestamps, unicidades `uq_tenant_administrator_tenant_usuario`/`uq_tenant_administrator_invitacion` e índices acordados; agregar a `EventoFacturacion` solo `resultado_periodo_inicio/fin` si el preflight confirma que faltan. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-02.** Crear una única `alembic/versions/<revision>_hu005_trial_subscription.py` con `down_revision` del head efectivo confirmado: upgrade aditivo, sin duplicar HU-004, sin siembra, sin cambios de plan/estado legacy y sin CHECK cerrado; downgrade debe fallar cerrado ante filas/asociaciones, fechas o eventos HU-005 y solo ser mecánico en base descartable vacía. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-03.** Modificar `app/modules/tenant/schemas.py` con request vacío estricto para bootstrap/activación, evento mensual exacto con `extra="forbid"`, respuestas de bootstrap/conversión y proyección con únicamente `subscription_id`, `plan_id`, `estado`, `trial_inicio`, `trial_fin`, `periodo_inicio`, `periodo_fin`; conservar schemas HU-004/HU-006. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-04.** Extender `app/modules/tenant/service.py:TenantService` para recibir el principal de `get_current_user`, normalizar correo, bootstrap idempotente desde invitación consumida y autorización por asociación activa; no aceptar autoridad de cliente ni modificar `app/modules/identity/router.py`. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-05.** Implementar en `TenantService` activación derivada server-owned: elegibilidad `active` inicial con fechas nulas, `trial_inicio = now`, `trial_fin = now + timedelta(hours=336)`, estado `trialing`, expiración inclusiva y rechazo sin mutación de repeticiones/estados incompatibles. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-06.** Implementar el período mensual con `ClockProtocol`, `ZoneInfo("America/La_Paz")` y `calendar.monthrange`, conservando hora local, clamping al mes siguiente y UTC consciente para persistencia; no usar `timedelta(days=30)`, no implementar lifecycle HU-006. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-07.** Extender `app/modules/tenant/repository.py:TenantRepository` para bootstrap, autorización, inspección y activación con asociación/tenant/suscripción server-owned, `with_for_update` y revalidación bajo lock; conservar APIs requeridas por HU-004/HU-006 y eliminar el uso HU-005 de commits aislados. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-08.** Implementar en `TenantRepository` la conversión mensual en una única transacción: lookup de key, lock de suscripción, validación de tipo/hash/correlación/plan/monto/trial vigente, actualización, flush, evento con raw-body hash y resultado, y un commit; cualquier fallo revierte suscripción, fechas y evento. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-09.** Recuperar `IntegrityError` únicamente mediante rollback y lectura limpia del registro comprometido, confirmando tipo mensual, hash, correlación y resultado; devolver replay original o `409`, y tratar cualquier error ajeno como fallo transaccional, nunca por texto de excepción. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-10.** Modificar `app/modules/tenant/router.py` para `Depends(get_current_user)` en bootstrap/activación/inspección, `GET /suscripcion`, body vacío, `Content-Type`, headers únicos y mapeo sanitizado; leer `await request.body()` una sola vez y autenticar antes de lookup de negocio. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-11.** Unificar `/api/v1/tenant/webhook` y `/api/v1/tenant/suscribir` en la misma tubería `HMACWebhookSignatureVerifier` → parser → `TenantService`; conservar `tenant.onboarding.succeeded`, declarar alias deprecated y hacer fallar cerrado la ruta legacy sin HMAC/evento mensual. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-01.** Ejecutar en PostgreSQL con sesiones separadas activaciones/conversiones concurrentes, locks, unicidad de key, replay exacto y conflictivo, key distinta post-conversión y rollback conjunto; distinguir explícitamente esta evidencia de fake/SQLite y dejar comandos/resultados reales. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-02.** Ejecutar upgrade desde el head Alembic efectivo `0004` solo si la revalidación lo confirma y downgrade únicamente en base descartable vacía; verificar FKs/índices, legacy intacto, ningún dato sintético y bloqueo de downgrade con datos HU-005. En datos reales usar forward-fix, nunca downgrade destructivo. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-03.** Ejecutar, marcando cada comando como pendiente hasta correrlo, `.venv/Scripts/python.exe -m pytest tests -q`, `.venv/Scripts/ruff.exe check app tests`, `.venv/Scripts/pyright.exe app tests` y `.venv/Scripts/python.exe -m alembic -c alembic.ini upgrade head`; no afirmar resultados anticipados. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-04.** Verificar regresión HU-004 (`tenant.onboarding.succeeded`), HU-002 (`tests/test_autenticacion.py`), representabilidad de HU-006, alias firmado, no divulgación/logs y ausencia de UI, billing, nuevos planes, notificaciones, RBAC/memberships o cambios en `docs/diagramas/Diagrama1.eapx`; registrar `CP-004.1/.2/.3` aún `not executed` hasta evidencia completa. <!-- sdd-owner: implementation -->
- [ ] **T-REF-01.** Solo después de TRIANGULATE, simplificar duplicación mínima en `app/modules/tenant/{service,repository,router,schemas}.py` sin cambiar contratos, guards, HMAC, calendario, queries, estados, respuestas ni errores; repetir únicamente checks afectados y mantener ≤400 líneas. <!-- sdd-owner: implementation -->
- [ ] **T-REF-02.** Revisar errores, logs y OpenAPI para confirmar no divulgación y que `/suscribir` sigue siendo alias deprecated de la tubería firmada; registrar warnings como warnings, no convertirlos en PASS ni agregar funcionalidad. <!-- sdd-owner: implementation -->
- [ ] Confirmar que `explore.md`, `proposal.md`, `specs/tenant-subscription/spec.md`, `design.md` y este `tasks.md` son los artefactos vigentes, y que el estado nativo recomienda `tasks` sin blockers antes de iniciar apply. <!-- sdd-owner: implementation -->
- [ ] Confirmar mediante `gentle-ai sdd-attempt acquire` que existe un token `state: proceed` para cada work unit runtime-bearing; liquidar con `settle` y evidencia, sin contadores caller-authored. <!-- sdd-owner: implementation -->
- [ ] Confirmar el head Alembic efectivo y el delta HU-004 antes de fijar `down_revision` o crear la única migración; no duplicar `0004` ni columnas HU-004. <!-- sdd-owner: implementation -->
- [ ] Confirmar que la única suite es `tests/test_tenant_onboarding.py`, que RED no contiene código productivo y que los resultados PostgreSQL/migración siguen pendientes hasta ejecución real. <!-- sdd-owner: implementation -->
- [ ] Confirmar que el forecast es 372/400 y que cualquier excedente detiene `sdd-apply` para decisión explícita de `ask-on-risk`; no crear una excepción silenciosa ni eliminar guards. <!-- sdd-owner: implementation -->
- [ ] Confirmar que CP-004 permanece `not executed` y que no se modifican root, gitlink, `docs/diagramas/Diagrama1.eapx`, ramas, commits, pushes, cleanup ni delivery durante tasks. <!-- sdd-owner: parent -->
- [ ] Aprobar interactivamente el plan antes de lanzar `sdd-apply`; esta fase no crea `apply-progress` ni implementa código. <!-- sdd-owner: parent -->

## WU-005-DATA — GREEN completado

- **Estado:** completado para `T-GREEN-01` y `T-GREEN-02`; no se inició `WU-005-CONTRACT`, `WU-005-RULES`, `WU-005-POSTGRES`, `WU-005-HTTP-HMAC`, TRIANGULATE ni REFACTOR.
- **Status consumido:** `schemaName: gentle-ai.sdd-status`, `changeName: hu005-trial-suscripcion`, `artifactStore: hybrid`, `applyState: ready`, `nextRecommended: apply`, `actionContext.mode: repo-local`, workspace/allowed edit root: `D:/Universidad/Proyectos/2doSemestre2026/sw1/roomforge-hu005-backend`; sin `blockedReasons` ni warnings de action context.
- **Workload / PR boundary:** forecast total `372/400`, riesgo `Medium`, `Chained PRs recommended: No`, `Decision needed before apply: No`; este work unit respetó el techo nativo de `50` líneas de producto y no requirió excepción ni cambio de estrategia.

### Preflight revalidado

- La inspección estática de `alembic/versions/` encontró exactamente cuatro revisiones en una cadena única: `0001 → 0002 → 0003 → 0004`; head efectivo único confirmado: `0004`, con `down_revision = "0003"`.
- `alembic/env.py` importa `app.modules.identity.models` y `app.modules.tenant.models` antes de exponer `Base.metadata`; no fue necesario modificarlo.
- El delta HU-004 confirmado en `0004` es `plan.codigo`/`max_agents`, `checkout_intencion`, `invitacion.consumido_en`, `evento_facturacion.checkout_id`/`payload_hash`, sus constraints/índice y adopción/seed de catálogo. No existía migración HU-005 ni campos `resultado_periodo_inicio`/`resultado_periodo_fin`.
- El modelo activo confirmó `Suscripcion.trial_fin`/`periodo_fin` y los campos HU-004 (`suscripcion_id`, `idempotency_key`, `checkout_id`, `payload_hash`), por lo que no se duplicaron. La importación estática confirmó visibilidad de la nueva tabla y campos en `Base.metadata`.

### Cambios de este work unit

- `app/modules/tenant/models.py`: fechas nullable timezone-aware en `Suscripcion`; `TenantAdministrator` con UUID server-side, FKs nombradas, `activo`, timestamps, unicidad de tenant/usuario e invitación e índices de autorización; resultado mensual nullable en `EventoFacturacion`.
- `alembic/versions/0005_hu005_trial_subscription.py`: única migración nueva, revisión `0005`, `down_revision = "0004"`. `upgrade()` es aditivo, no siembra datos, no cambia planes/estados legacy y no agrega CHECK de estado. `downgrade()` consulta primero asociaciones, fechas y eventos/resultados mensuales; ante datos, términos mensuales o error de inspección falla cerrado. Solo después ejecuta el descenso mecánico.
- **Contabilidad:** `33` adiciones + `1` eliminación en el modelo y `13` líneas nuevas de migración = `47` líneas de producto modificadas; tareas/progreso son bookkeeping OpenSpec y no se incluyen en ese límite. No se modificaron schemas, service, repository, router, identity, tests, configs, root files ni otros módulos.
- **Persistencia de tareas:** solo `T-GREEN-01` y `T-GREEN-02` fueron marcadas `[x]`; las filas parent-owned y todas las tareas posteriores permanecen sin cambios.

### Evidencia y límites

- **Ejecutado:** inspección estática de revisiones, parseo AST de modelo/migración e importación estática de metadata. La sintaxis fue válida y la metadata expuso `tenant_administrator`, las fechas de suscripción y los resultados mensuales.
- **No ejecutado:** pytest, lint, pyright, Alembic upgrade/downgrade, PostgreSQL, revisión, commits, pushes y delivery. La comprobación de metadata no constituye evidencia de migración ni de PostgreSQL.
- **TDD Cycle Evidence:** `WU-005-TDD` conserva `RED: 7 failed, 37 passed`; `WU-005-DATA` queda en `GREEN: implementation complete`, con `TRIANGULATE: Not started` y `REFACTOR: Not started`. `CP-004: not executed`.
- **Rollback boundary:** revertir únicamente los cambios de modelo y la revisión `0005` antes de aplicar el esquema. Si existieran datos HU-005, no ejecutar downgrade destructivo: preservar asociaciones, fechas y eventos y usar forward-fix.
- **Siguiente work unit:** `WU-005-CONTRACT`; requiere nueva autorización/contabilidad del parent. La validación PostgreSQL y de migración pertenece a `WU-005-TRIANGULATE` y sigue pendiente.

## Remaining task rows after WU-005-DATA

- [ ] **T-GREEN-03.** Modificar `app/modules/tenant/schemas.py` con request vacío estricto para bootstrap/activación, evento mensual exacto con `extra="forbid"`, respuestas de bootstrap/conversión y proyección con únicamente `subscription_id`, `plan_id`, `estado`, `trial_inicio`, `trial_fin`, `periodo_inicio`, `periodo_fin`; conservar schemas HU-004/HU-006. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-04.** Extender `app/modules/tenant/service.py:TenantService` para recibir el principal de `get_current_user`, normalizar correo, bootstrap idempotente desde invitación consumida y autorización por asociación activa; no aceptar autoridad de cliente ni modificar `app/modules/identity/router.py`. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-05.** Implementar en `TenantService` activación derivada server-owned: elegibilidad `active` inicial con fechas nulas, `trial_inicio = now`, `trial_fin = now + timedelta(hours=336)`, estado `trialing`, expiración inclusiva y rechazo sin mutación de repeticiones/estados incompatibles. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-06.** Implementar el período mensual con `ClockProtocol`, `ZoneInfo("America/La_Paz")` y `calendar.monthrange`, conservando hora local, clamping al mes siguiente y UTC consciente para persistencia; no usar `timedelta(days=30)`, no implementar lifecycle HU-006. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-07.** Extender `app/modules/tenant/repository.py:TenantRepository` para bootstrap, autorización, inspección y activación con asociación/tenant/suscripción server-owned, `with_for_update` y revalidación bajo lock; conservar APIs requeridas por HU-004/HU-006 y eliminar el uso HU-005 de commits aislados. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-08.** Implementar en `TenantRepository` la conversión mensual en una única transacción: lookup de key, lock de suscripción, validación de tipo/hash/correlación/plan/monto/trial vigente, actualización, flush, evento con raw-body hash y resultado, y un commit; cualquier fallo revierte suscripción, fechas y evento. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-09.** Recuperar `IntegrityError` únicamente mediante rollback y lectura limpia del registro comprometido, confirmando tipo mensual, hash, correlación y resultado; devolver replay original o `409`, y tratar cualquier error ajeno como fallo transaccional, nunca por texto de excepción. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-10.** Modificar `app/modules/tenant/router.py` para `Depends(get_current_user)` en bootstrap/activación/inspección, `GET /suscripcion`, body vacío, `Content-Type`, headers únicos y mapeo sanitizado; leer `await request.body()` una sola vez y autenticar antes de lookup de negocio. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-11.** Unificar `/api/v1/tenant/webhook` y `/api/v1/tenant/suscribir` en la misma tubería `HMACWebhookSignatureVerifier` → parser → `TenantService`; conservar `tenant.onboarding.succeeded`, declarar alias deprecated y hacer fallar cerrado la ruta legacy sin HMAC/evento mensual. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-01.** Ejecutar en PostgreSQL con sesiones separadas activaciones/conversiones concurrentes, locks, unicidad de key, replay exacto y conflictivo, key distinta post-conversión y rollback conjunto; distinguir explícitamente esta evidencia de fake/SQLite y dejar comandos/resultados reales. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-02.** Ejecutar upgrade desde el head Alembic efectivo `0004` solo si la revalidación lo confirma y downgrade únicamente en base descartable vacía; verificar FKs/índices, legacy intacto, ningún dato sintético y bloqueo de downgrade con datos HU-005. En datos reales usar forward-fix, nunca downgrade destructivo. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-03.** Ejecutar, marcando cada comando como pendiente hasta correrlo, `.venv/Scripts/python.exe -m pytest tests -q`, `.venv/Scripts/ruff.exe check app tests`, `.venv/Scripts/pyright.exe app tests` y `.venv/Scripts/python.exe -m alembic -c alembic.ini upgrade head`; no afirmar resultados anticipados. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-04.** Verificar regresión HU-004 (`tenant.onboarding.succeeded`), HU-002 (`tests/test_autenticacion.py`), representabilidad de HU-006, alias firmado, no divulgación/logs y ausencia de UI, billing, nuevos planes, notificaciones, RBAC/memberships o cambios en `docs/diagramas/Diagrama1.eapx`; registrar `CP-004.1/.2/.3` aún `not executed` hasta evidencia completa. <!-- sdd-owner: implementation -->
- [ ] **T-REF-01.** Solo después de TRIANGULATE, simplificar duplicación mínima en `app/modules/tenant/{service,repository,router,schemas}.py` sin cambiar contratos, guards, HMAC, calendario, queries, estados, respuestas ni errores; repetir únicamente checks afectados y mantener ≤400 líneas. <!-- sdd-owner: implementation -->
- [ ] **T-REF-02.** Revisar errores, logs y OpenAPI para confirmar no divulgación y que `/suscribir` sigue siendo alias deprecated de la tubería firmada; registrar warnings como warnings, no convertirlos en PASS ni agregar funcionalidad. <!-- sdd-owner: implementation -->
- [ ] Confirmar que `explore.md`, `proposal.md`, `specs/tenant-subscription/spec.md`, `design.md` y este `tasks.md` son los artefactos vigentes, y que el estado nativo recomienda `tasks` sin blockers antes de iniciar apply. <!-- sdd-owner: implementation -->
- [ ] Confirmar mediante `gentle-ai sdd-attempt acquire` que existe un token `state: proceed` para cada work unit runtime-bearing; liquidar con `settle` y evidencia, sin contadores caller-authored. <!-- sdd-owner: implementation -->
- [ ] Confirmar el head Alembic efectivo y el delta HU-004 antes de fijar `down_revision` o crear la migración; no duplicar `0004` ni columnas HU-004. <!-- sdd-owner: implementation -->
- [ ] Confirmar que la única suite es `tests/test_tenant_onboarding.py`, que RED no contiene código productivo y que los resultados PostgreSQL/migración siguen pendientes hasta ejecución real. <!-- sdd-owner: implementation -->
- [ ] Confirmar que el forecast es 372/400 y que cualquier excedente detiene `sdd-apply` para decisión explícita de `ask-on-risk`; no crear una excepción silenciosa ni eliminar guards. <!-- sdd-owner: implementation -->
- [ ] Confirmar que CP-004 permanece `not executed` y que no se modifican root, gitlink, `docs/diagramas/Diagrama1.eapx`, ramas, commits, pushes, cleanup ni delivery durante tasks. <!-- sdd-owner: parent -->
- [ ] Aprobar interactivamente el plan antes de lanzar `sdd-apply`; esta fase no crea `apply-progress` ni implementa código. <!-- sdd-owner: parent -->

## WU-005-CONTRACT — GREEN completado

- **Estado:** completado únicamente para `T-GREEN-03`; no se inició `WU-005-RULES`, `WU-005-POSTGRES`, `WU-005-HTTP-HMAC`, TRIANGULATE ni REFACTOR.
- **Status estructurado consumido:** `schemaName: gentle-ai.sdd-status`, `changeName: hu005-trial-suscripcion`, `artifactStore: hybrid`, `applyState: ready`, `nextRecommended: apply`, `taskProgress: 15/36 complete, 21 pending`, `dependencies.apply: ready`, sin `blockedReasons`.
- **Action context:** `mode: repo-local`; workspace y `allowedEditRoots` corresponden exclusivamente a `D:/Universidad/Proyectos/2doSemestre2026/sw1/roomforge-hu005-backend`; no se observaron warnings.
- **Workload / frontera PR:** forecast `372/400`, riesgo `Medium`, `Decision needed before apply: No`, `Chained PRs recommended: No`, estrategia `ask-on-risk`, cadena `pending`. El work unit respetó el techo nativo de `36` líneas de producto; no requirió excepción.

### Cambios y contratos

- **Producto:** `app/modules/tenant/schemas.py` añade el request vacío estricto `ActivarPruebaRequest` y su alias `BootstrapRequest`, ambos sin selector tenant; convierte `SuscribirRequest` en el evento mensual estricto con `event_type` literal `subscription.monthly.succeeded`, `idempotency_key`, `subscription_id`, `plan_id` y `monto_bob` finito, con `extra=forbid`.
- **Proyecciones seguras:** `SuscripcionProjection` contiene exactamente `subscription_id`, `plan_id`, `estado`, `trial_inicio`, `trial_fin`, `periodo_inicio` y `periodo_fin`; `BootstrapResponse` contiene únicamente `tenant_id`, `administrador_id`, `activo` e `idempotente`; `SuscripcionConversionResponse` contiene únicamente `evento_id`, `subscription_id`, `estado`, `periodo_inicio`, `periodo_fin` e `idempotente`.
- **Compatibilidad:** se preservaron byte-a-byte `WebhookRequest`/`WebhookResponse`, `ActivationRequest`/`ActivationResponse`, `SuscripcionResponse` usado por HU-006 y `CambiarPlanRequest`/`CancelarSuscripcionRequest`. No se modificaron imports de router/service ni se agregaron UI, billing, roles o memberships.
- **Contabilidad del work unit:** `app/modules/tenant/schemas.py`: `31` adiciones + `5` eliminaciones = `36` líneas de producto modificadas. `tasks.md` solo cambia el checkbox de `T-GREEN-03`; `apply-progress.md` es bookkeeping.
- **Persistencia de tareas:** solo `T-GREEN-03` se marcó `[x]` en `openspec/changes/hu005-trial-suscripcion/tasks.md`; las filas parent-owned permanecen sin cambios.

### TDD Cycle Evidence

| Work unit | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|
| `WU-005-CONTRACT` | RED previo: `7 failed, 37 passed` en el módulo enfocado; no se reescribieron esos resultados | Implementación de schemas/proyecciones completada; validación estática OK | Not started; PostgreSQL, migración y CP-004 no ejecutados | Not started |

### Evidencia y límites

- **Evidencia estática ejecutada:** importación de `app.modules.tenant.schemas` y validación de `model_json_schema()`/`model_fields`: request vacío con `additionalProperties: false`, event type exacto y `additionalProperties: false`, conjuntos exactos de campos de las tres proyecciones. Resultado: `static schema validation: ok`. Esto no es evidencia HTTP, PostgreSQL, migración ni runtime de negocio.
- **No ejecutado:** `..\\.venv\\Scripts\\python.exe -m pytest tests -q` ni ningún test enfocado; PostgreSQL; Alembic upgrade/downgrade; Ruff; Pyright; lint; typecheck; revisión; commits; pushes; delivery. No se declara PASS para ningún check no ejecutado.
- **CP-004:** `not executed`.
- **Rollback boundary:** revertir únicamente el bloque HU-005 de `app/modules/tenant/schemas.py` y desmarcar `T-GREEN-03` si este work unit debe revertirse antes de integrar los consumidores; preservar los schemas HU-004/HU-006, los cambios de `WU-005-DATA` y todos los artefactos RED. No ejecutar downgrade destructivo ni borrar datos HU-005.
- **Runtime authority:** el parent conserva y liquidará el intento nativo ya adquirido para `WU-005-CONTRACT`; este executor no adquirió, no liquidó ni persistió ningún token.
- **Siguiente work unit:** `WU-005-RULES`; requiere la liquidación/autorización del parent. `CP-004` sigue sin ejecutarse.

## Remaining task rows after WU-005-CONTRACT

- [ ] **T-GREEN-04.** Extender `app/modules/tenant/service.py:TenantService` para recibir el principal de `get_current_user`, normalizar correo, bootstrap idempotente desde invitación consumida y autorización por asociación activa; no aceptar autoridad de cliente ni modificar `app/modules/identity/router.py`. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-05.** Implementar en `TenantService` activación derivada server-owned: elegibilidad `active` inicial con fechas nulas, `trial_inicio = now`, `trial_fin = now + timedelta(hours=336)`, estado `trialing`, expiración inclusiva y rechazo sin mutación de repeticiones/estados incompatibles. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-06.** Implementar el período mensual con `ClockProtocol`, `ZoneInfo("America/La_Paz")` y `calendar.monthrange`, conservando hora local, clamping al mes siguiente y UTC consciente para persistencia; no usar `timedelta(days=30)`, no implementar lifecycle HU-006. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-07.** Extender `app/modules/tenant/repository.py:TenantRepository` para bootstrap, autorización, inspección y activación con asociación/tenant/suscripción server-owned, `with_for_update` y revalidación bajo lock; conservar APIs requeridas por HU-004/HU-006 y eliminar el uso HU-005 de commits aislados. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-08.** Implementar en `TenantRepository` la conversión mensual en una única transacción: lookup de key, lock de suscripción, validación de tipo/hash/correlación/plan/monto/trial vigente, actualización, flush, evento con raw-body hash y resultado, y un commit; cualquier fallo revierte suscripción, fechas y evento. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-09.** Recuperar `IntegrityError` únicamente mediante rollback y lectura limpia del registro comprometido, confirmando tipo mensual, hash, correlación y resultado; devolver replay original o `409`, y tratar cualquier error ajeno como fallo transaccional, nunca por texto de excepción. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-10.** Modificar `app/modules/tenant/router.py` para `Depends(get_current_user)` en bootstrap/activación/inspección, `GET /suscripcion`, body vacío, `Content-Type`, headers únicos y mapeo sanitizado; leer `await request.body()` una sola vez y autenticar antes de lookup de negocio. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-11.** Unificar `/api/v1/tenant/webhook` y `/api/v1/tenant/suscribir` en la misma tubería `HMACWebhookSignatureVerifier` → parser → `TenantService`; conservar `tenant.onboarding.succeeded`, declarar alias deprecated y hacer fallar cerrado la ruta legacy sin HMAC/evento mensual. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-01.** Ejecutar en PostgreSQL con sesiones separadas activaciones/conversiones concurrentes, locks, unicidad de key, replay exacto y conflictivo, key distinta post-conversión y rollback conjunto; distinguir explícitamente esta evidencia de fake/SQLite y dejar comandos/resultados reales. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-02.** Ejecutar upgrade desde el head Alembic efectivo `0004` solo si la revalidación lo confirma y downgrade únicamente en base descartable vacía; verificar FKs/índices, legacy intacto, ningún dato sintético y bloqueo de downgrade con datos HU-005. En datos reales usar forward-fix, nunca downgrade destructivo. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-03.** Ejecutar, marcando cada comando como pendiente hasta correrlo, `.venv/Scripts/python.exe -m pytest tests -q`, `.venv/Scripts/ruff.exe check app tests`, `.venv/Scripts/pyright.exe app tests` y `.venv/Scripts/python.exe -m alembic -c alembic.ini upgrade head`; no afirmar resultados anticipados. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-04.** Verificar regresión HU-004 (`tenant.onboarding.succeeded`), HU-002 (`tests/test_autenticacion.py`), representabilidad de HU-006, alias firmado, no divulgación/logs y ausencia de UI, billing, nuevos planes, notificaciones, RBAC/memberships o cambios en `docs/diagramas/Diagrama1.eapx`; registrar `CP-004.1/.2/.3` aún `not executed` hasta evidencia completa. <!-- sdd-owner: implementation -->
- [ ] **T-REF-01.** Solo después de TRIANGULATE, simplificar duplicación mínima en `app/modules/tenant/{service,repository,router,schemas}.py` sin cambiar contratos, guards, HMAC, calendario, queries, estados, respuestas ni errores; repetir únicamente checks afectados y mantener ≤400 líneas. <!-- sdd-owner: implementation -->
- [ ] **T-REF-02.** Revisar errores, logs y OpenAPI para confirmar no divulgación y que `/suscribir` sigue siendo alias deprecated de la tubería firmada; registrar warnings como warnings, no convertirlos en PASS ni agregar funcionalidad. <!-- sdd-owner: implementation -->
- [ ] Confirmar que `explore.md`, `proposal.md`, `specs/tenant-subscription/spec.md`, `design.md` y este `tasks.md` son los artefactos vigentes, y que el estado nativo recomienda `tasks` sin blockers antes de iniciar apply. <!-- sdd-owner: implementation -->
- [ ] Confirmar mediante `gentle-ai sdd-attempt acquire` que existe un token `state: proceed` para cada work unit runtime-bearing; liquidar con `settle` y evidencia, sin contadores caller-authored. <!-- sdd-owner: implementation -->
- [ ] Confirmar el head Alembic efectivo y el delta HU-004 antes de fijar `down_revision` o crear la única migración; no duplicar `0004` ni columnas HU-004. <!-- sdd-owner: implementation -->
- [ ] Confirmar que la única suite es `tests/test_tenant_onboarding.py`, que RED no contiene código productivo y que los resultados PostgreSQL/migración siguen pendientes hasta ejecución real. <!-- sdd-owner: implementation -->
- [ ] Confirmar que el forecast es 372/400 y que cualquier excedente detiene `sdd-apply` para decisión explícita de `ask-on-risk`; no crear una excepción silenciosa ni eliminar guards. <!-- sdd-owner: implementation -->
- [ ] Confirmar que CP-004 permanece `not executed` y que no se modifican root, gitlink, `docs/diagramas/Diagrama1.eapx`, ramas, commits, pushes, cleanup ni delivery durante tasks. <!-- sdd-owner: parent -->
- [ ] Aprobar interactivamente el plan antes de lanzar `sdd-apply`; esta fase no crea `apply-progress` ni implementa código. <!-- sdd-owner: parent -->

## WU-005-RULES — GREEN completado

- **Estado:** completado únicamente para `T-GREEN-04`, `T-GREEN-05` y `T-GREEN-06`. No se inició `WU-005-POSTGRES`, `WU-005-HTTP-HMAC`, TRIANGULATE ni REFACTOR.
- **Status estructurado consumido:** `schemaName: gentle-ai.sdd-status`, `changeName: hu005-trial-suscripcion`, `artifactStore: hybrid`, `applyState: ready`, `nextRecommended: apply`, `dependencies.apply: ready`, sin `blockedReasons`.
- **Action context:** `mode: repo-local`; workspace y `allowedEditRoots` son exclusivamente `D:/Universidad/Proyectos/2doSemestre2026/sw1/roomforge-hu005-backend`; no se observaron warnings. El runtime authority token fue provisto y permanece bajo custodia/settlement del parent; este executor no adquirió ni liquidó otro token.
- **Workload / frontera PR:** forecast `372/400`, riesgo `Medium`, `Decision needed before apply: No`, `Chained PRs recommended: No`, estrategia `ask-on-risk`, cadena `pending`. Esta unidad consumió exactamente `60` líneas de producto (`48` adiciones + `12` eliminaciones), sin excepción.

### Cambios de este work unit

- `app/modules/tenant/service.py`: `TenantService` ahora recibe el principal tipado `MeResponse`; el bootstrap normaliza el correo únicamente para matching y delega en el seam server-owned `bootstrap_administrador(principal.id, correo)`, sin aceptar `tenant_id`.
- `TenantService.activar_prueba` deriva la suscripción mediante `buscar_suscripcion_autorizada(principal.id)`, rechaza asociaciones/suscripciones no accesibles y estados o fechas incompatibles sin mutar; delega la escritura atómica a `activar_prueba_autorizada(principal.id, trial_inicio, trial_fin)` con `trial_fin` exactamente `336` horas después.
- Se agregaron `trial_duration()`, `trial_expired(now, trial_fin)` con frontera inclusiva `now >= trial_fin` y `calcular_periodo_mensual()` con `ZoneInfo("America/La_Paz")`, mes calendario siguiente, `calendar.monthrange`, clamping y timestamps conscientes de zona. El helper conserva la representación local; el seam de conversión debe persistir su resultado normalizado a UTC.
- La proyección de activación es `SuscripcionProjection`; no se tocó identidad, HU-004 ni los métodos de HU-006.

### Seams diferidos explícitamente

- `WU-005-POSTGRES` debe implementar `bootstrap_administrador`, `buscar_suscripcion_autorizada` y `activar_prueba_autorizada` con invitación HU-004 consumida, asociación activa server-owned, locks, revalidación y transacción. El service no inventó un fake ni modificó `repository.py`.
- La expiración inclusiva y el calendario UTC deben consumirse en `convertir_suscripcion_mensual`; la conversión, idempotencia, evento, locks y rollback quedan diferidos al repository.
- `WU-005-HTTP-HMAC` debe inyectar `get_current_user` en router y retirar el bypass legacy. El `suscribirse` existente, incluida su autoridad cliente y duración legacy, no fue ejecutado ni modificado en esta frontera.

### Evidencia y TDD

| Work unit | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|
| `WU-005-RULES` | RED previo: `7 failed, 37 passed` (no es PASS) | Implementación estática completa; `static compile: ok` | No iniciado | No iniciado |

- **Comando estático ejecutado:** `../proyecto_final/.venv/Scripts/python.exe -c "... compile ..."`; resultado: `static compile: ok`.
- **No ejecutado:** `..\.venv\Scripts\python.exe -m pytest tests -q`, tests enfocados, PostgreSQL, Alembic upgrade/downgrade, Ruff, Pyright, TRIANGULATE, REFACTOR, revisión, commits, pushes y delivery. No se declara PASS para estas actividades.
- **CP-004:** `not executed`.

### Contabilidad, rollback y siguiente unidad

- **Paths modificados en esta unidad:** `app/modules/tenant/service.py`, `openspec/changes/hu005-trial-suscripcion/tasks.md` y este `apply-progress.md`. El diff de producto del service es `48 + 12 = 60`; acumulado de producto informado por el parent: `196` líneas.
- **Persistencia de tareas:** solo `T-GREEN-04`, `T-GREEN-05` y `T-GREEN-06` se marcaron `[x]`; las filas parent-owned permanecen intactas y se difieren al lifecycle del parent.
- **Rollback boundary:** revertir únicamente el bloque HU-005 agregado/modificado en `service.py` y desmarcar esas tres filas antes de integrar el repository; preservar RED, DATA, CONTRACT, HU-004, HU-006 y la migración aditiva. No ejecutar downgrade destructivo ni borrar datos.
- **Siguiente work unit:** `WU-005-POSTGRES`; requiere settlement/autorización del parent. `CP-004` sigue sin ejecutarse.

### Remaining task rows (exact unchecked lines)

- [ ] **T-GREEN-07.** Extender `app/modules/tenant/repository.py:TenantRepository` para bootstrap, autorización, inspección y activación con asociación/tenant/suscripción server-owned, `with_for_update` y revalidación bajo lock; conservar APIs requeridas por HU-004/HU-006 y eliminar el uso HU-005 de commits aislados. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-08.** Implementar en `TenantRepository` la conversión mensual en una única transacción: lookup de key, lock de suscripción, validación de tipo/hash/correlación/plan/monto/trial vigente, actualización, flush, evento con raw-body hash y resultado, y un commit; cualquier fallo revierte suscripción, fechas y evento. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-09.** Recuperar `IntegrityError` únicamente mediante rollback y lectura limpia del registro comprometido, confirmando tipo mensual, hash, correlación y resultado; devolver replay original o `409`, y tratar cualquier error ajeno como fallo transaccional, nunca por texto de excepción. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-10.** Modificar `app/modules/tenant/router.py` para `Depends(get_current_user)` en bootstrap/activación/inspección, `GET /suscripcion`, body vacío, `Content-Type`, headers únicos y mapeo sanitizado; leer `await request.body()` una sola vez y autenticar antes de lookup de negocio. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-11.** Unificar `/api/v1/tenant/webhook` y `/api/v1/tenant/suscribir` en la misma tubería `HMACWebhookSignatureVerifier` → parser → `TenantService`; conservar `tenant.onboarding.succeeded`, declarar alias deprecated y hacer fallar cerrado la ruta legacy sin HMAC/evento mensual. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-01.** Ejecutar en PostgreSQL con sesiones separadas activaciones/conversiones concurrentes, locks, unicidad de key, replay exacto y conflictivo, key distinta post-conversión y rollback conjunto; distinguir explícitamente esta evidencia de fake/SQLite y dejar comandos/resultados reales. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-02.** Ejecutar upgrade desde el head Alembic efectivo `0004` solo si la revalidación lo confirma y downgrade únicamente en base descartable vacía; verificar FKs/índices, legacy intacto, ningún dato sintético y bloqueo de downgrade con datos HU-005. En datos reales usar forward-fix, nunca downgrade destructivo. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-03.** Ejecutar, marcando cada comando como pendiente hasta correrlo, `.venv/Scripts/python.exe -m pytest tests -q`, `.venv/Scripts/ruff.exe check app tests`, `.venv/Scripts/pyright.exe app tests` y `.venv/Scripts/python.exe -m alembic -c alembic.ini upgrade head`; no afirmar resultados anticipados. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-04.** Verificar regresión HU-004 (`tenant.onboarding.succeeded`), HU-002 (`tests/test_autenticacion.py`), representabilidad de HU-006, alias firmado, no divulgación/logs y ausencia de UI, billing, nuevos planes, notificaciones, RBAC/memberships o cambios en `docs/diagramas/Diagrama1.eapx`; registrar `CP-004.1/.2/.3` aún `not executed` hasta evidencia completa. <!-- sdd-owner: implementation -->
- [ ] **T-REF-01.** Solo después de TRIANGULATE, simplificar duplicación mínima en `app/modules/tenant/{service,repository,router,schemas}.py` sin cambiar contratos, guards, HMAC, calendario, queries, estados, respuestas ni errores; repetir únicamente checks afectados y mantener ≤400 líneas. <!-- sdd-owner: implementation -->
- [ ] **T-REF-02.** Revisar errores, logs y OpenAPI para confirmar no divulgación y que `/suscribir` sigue siendo alias deprecated de la tubería firmada; registrar warnings como warnings, no convertirlos en PASS ni agregar funcionalidad. <!-- sdd-owner: implementation -->
- [ ] Confirmar que `explore.md`, `proposal.md`, `specs/tenant-subscription/spec.md`, `design.md` y este `tasks.md` son los artefactos vigentes, y que el estado nativo recomienda `tasks` sin blockers antes de iniciar apply. <!-- sdd-owner: implementation -->
- [ ] Confirmar mediante `gentle-ai sdd-attempt acquire` que existe un token `state: proceed` para cada work unit runtime-bearing; liquidar con `settle` y evidencia, sin contadores caller-authored. <!-- sdd-owner: implementation -->
- [ ] Confirmar el head Alembic efectivo y el delta HU-004 antes de fijar `down_revision` o crear la migración; no duplicar `0004` ni columnas HU-004. <!-- sdd-owner: implementation -->
- [ ] Confirmar que la única suite es `tests/test_tenant_onboarding.py`, que RED no contiene código productivo y que los resultados PostgreSQL/migración siguen pendientes hasta ejecución real. <!-- sdd-owner: implementation -->
- [ ] Confirmar que el forecast es 372/400 y que cualquier excedente detiene `sdd-apply` para decisión explícita de `ask-on-risk`; no crear una excepción silenciosa ni eliminar guards. <!-- sdd-owner: implementation -->
- [ ] Confirmar que CP-004 permanece `not executed` y que no se modifican root, gitlink, `docs/diagramas/Diagrama1.eapx`, ramas, commits, pushes, cleanup ni delivery durante tasks. <!-- sdd-owner: parent -->
- [ ] Aprobar interactivamente el plan antes de lanzar `sdd-apply`; esta fase no crea `apply-progress` ni implementa código. <!-- sdd-owner: parent -->

## WU-005-POSTGRES — GREEN completado

- **Estado:** completado únicamente para `T-GREEN-07`, `T-GREEN-08` y `T-GREEN-09`; no se inició `WU-005-HTTP-HMAC`, TRIANGULATE ni REFACTOR.
- **Resultado real:** `app/modules/tenant/repository.py` cambió `77` adiciones y `1` eliminación: `78` líneas de producto, exactamente el techo de esta unidad. La eliminación solo normaliza la indentación de `buscar_suscripcion`; no se eliminaron APIs HU-004/HU-006.
- **Métodos implementados:** `_administrator` resuelve exactamente una asociación activa, usuario activo, invitación HU-004 consumida y suscripción vinculada bajo `with_for_update`; `bootstrap_administrador` normaliza correo, rechaza cero/múltiples candidatos sanitizadamente, crea una asociación única y reconoce el vínculo ganador tras `IntegrityError`; `buscar_suscripcion_autorizada` y `activar_prueba_autorizada` revalidan asociación/suscripción bajo lock y activan una sola vez con un commit; `convertir_suscripcion_mensual` bloquea evento/suscripción/plan, valida tipo, hash, correlación, monto server-owned, estado `trialing`, vigencia y fechas, actualiza suscripción, hace flush de FK, persiste evento mensual con hash/resultado y ejecuta un único commit; `_monthly_replay` confirma tipo, hash, suscripción y resultado antes del replay.
- **Errores y atomicidad:** se agregó `SubscriptionConversionConflictError`; toda escritura HU-005 hace rollback ante fallo. `IntegrityError` mensual se clasifica solo después de rollback y lectura limpia por clave, comprobando tipo/hash/correlación/resultado; no se inspecciona texto y un error sin fila comprometida se relanza.
- **Persistencia de tareas:** `tasks.md` marca únicamente `T-GREEN-07`, `T-GREEN-08` y `T-GREEN-09` como `[x]`; filas parent-owned intactas.

### TDD Cycle Evidence

| Work unit | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|
| `WU-005-POSTGRES` | Evidencia previa: `7 failed, 37 passed`; no es PASS | `python -m py_compile app/modules/tenant/repository.py` y `git diff --check` sin error; runner de tests no ejecutado | No iniciado | No iniciado |

### Archivos, evidencia y límites

- **Producto:** `app/modules/tenant/repository.py`.
- **Bookkeeping:** `openspec/changes/hu005-trial-suscripcion/tasks.md` y este `apply-progress.md`.
- **No ejecutado:** `..\.venv\Scripts\python.exe -m pytest tests -q`, PostgreSQL/concurrencia, Alembic upgrade/downgrade, Ruff, Pyright, TRIANGULATE, REFACTOR, revisión, commits, pushes y delivery. No se afirma PASS ni evidencia runtime de base de datos.
- **Diferencia de diseño:** la operación mensual recibe del service el instante y el período calendario calculados; el repository conserva y valida el resultado server-owned en la transacción. El código quedó compacto por el techo duro de `78` líneas sin retirar locks, rollback, unicidad, validación ni recuperación segura.
- **Rollback boundary:** revertir solo el diff de `repository.py` de esta unidad y desmarcar `T-GREEN-07..09`; preservar RED, DATA, CONTRACT, RULES, HU-004, HU-006 y migración aditiva. No ejecutar downgrade destructivo ni borrar datos.
- **CP-004:** `not executed`.

### Workload, status y delivery boundary

- **Status consumido:** `schemaName: gentle-ai.sdd-status`, `changeName: hu005-trial-suscripcion`, `artifactStore: hybrid`, `applyState: ready`, `nextRecommended: apply`, `dependencies.apply: ready`, `blockedReasons: []`; `actionContext.mode: repo-local`, workspace/`allowedEditRoots` limitados al backend. Runtime token `sha256:a87671f9c79a9913d979a72242d336a24ee5dcc81116d5faa5dddf768aaf0844` quedó bajo custodia del parent; este executor no adquirió ni liquidó otro.
- **Workload / PR boundary:** forecast `372/400`, riesgo `Medium`, `Decision needed before apply: No`, `Chained PRs recommended: No`, estrategia `ask-on-risk`, cadena `pending`; esta unidad consumió exactamente `78` líneas y no requiere excepción ni cadena.
- **Warnings:** no hubo warning de `actionContext`; runtime y PostgreSQL permanecen pendientes.
- **Siguiente unidad:** `WU-005-HTTP-HMAC`; no se inicia aquí router, HMAC, tests, PostgreSQL, TRIANGULATE o REFACTOR.

### Cierre nativo de WU-005-POSTGRES

- El primer actor de apply agotó el timeout de 1200000 ms después de escribir el candidato de `repository.py`; se liquidó como `interrupted`, sin afirmar PASS.
- El maintainer autorizó el reset nativo. Revisión de reset: `sha256:fc1062a33b1d5ba636b34ef5badabe93759496c6ea93c914124149cdfa600348`; nuevo candidato preservado: `sha256:85054fe49f9907064a826483a28e01c7dc57585122007dcce1ba2fefed4c371b`.
- Un validador fresco confirmó `py_compile` PASS, `git diff --check` PASS y `77` adiciones/`1` eliminación. El runtime se liquidó como `passed` con evidencia `sha256:f6a418f2c6683eb11be28f232481de2b9d2316f7d9101ec13824989bc27909fa`.
- No se ejecutaron tests, PostgreSQL, migraciones, Ruff, Pyright, TRIANGULATE, REFACTOR, revisión, commits, pushes ni delivery. `CP-004: not executed`.

### Remaining task rows after WU-005-POSTGRES

- [ ] **T-GREEN-10.** Modificar `app/modules/tenant/router.py` para `Depends(get_current_user)` en bootstrap/activación/inspección, `GET /suscripcion`, body vacío, `Content-Type`, headers únicos y mapeo sanitizado; leer `await request.body()` una sola vez y autenticar antes de lookup de negocio. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-11.** Unificar `/api/v1/tenant/webhook` y `/api/v1/tenant/suscribir` en la misma tubería `HMACWebhookSignatureVerifier` → parser → `TenantService`; conservar `tenant.onboarding.succeeded`, declarar alias deprecated y hacer fallar cerrado la ruta legacy sin HMAC/evento mensual. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-01.** Ejecutar en PostgreSQL con sesiones separadas activaciones/conversiones concurrentes, locks, unicidad de key, replay exacto y conflictivo, key distinta post-conversión y rollback conjunto; distinguir explícitamente esta evidencia de fake/SQLite y dejar comandos/resultados reales. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-02.** Ejecutar upgrade desde el head Alembic efectivo `0004` solo si la revalidación lo confirma y downgrade únicamente en base descartable vacía; verificar FKs/índices, legacy intacto, ningún dato sintético y bloqueo de downgrade con datos HU-005. En datos reales usar forward-fix, nunca downgrade destructivo. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-03.** Ejecutar, marcando cada comando como pendiente hasta correrlo, `.venv/Scripts/python.exe -m pytest tests -q`, `.venv/Scripts/ruff.exe check app tests`, `.venv/Scripts/pyright.exe app tests` y `.venv/Scripts/python.exe -m alembic -c alembic.ini upgrade head`; no afirmar resultados anticipados. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-04.** Verificar regresión HU-004 (`tenant.onboarding.succeeded`), HU-002 (`tests/test_autenticacion.py`), representabilidad de HU-006, alias firmado, no divulgación/logs y ausencia de UI, billing, nuevos planes, notificaciones, RBAC/memberships o cambios en `docs/diagramas/Diagrama1.eapx`; registrar `CP-004.1/.2/.3` aún `not executed` hasta evidencia completa. <!-- sdd-owner: implementation -->
- [ ] **T-REF-01.** Solo después de TRIANGULATE, simplificar duplicación mínima en `app/modules/tenant/{service,repository,router,schemas}.py` sin cambiar contratos, guards, HMAC, calendario, queries, estados, respuestas ni errores; repetir únicamente checks afectados y mantener ≤400 líneas. <!-- sdd-owner: implementation -->
- [ ] **T-REF-02.** Revisar errores, logs y OpenAPI para confirmar no divulgación y que `/suscribir` sigue siendo alias deprecated de la tubería firmada; registrar warnings como warnings, no convertirlos en PASS ni agregar funcionalidad. <!-- sdd-owner: implementation -->
- [ ] Confirmar que CP-004 permanece `not executed` y que no se modifican root, gitlink, `docs/diagramas/Diagrama1.eapx`, ramas, commits, pushes, cleanup ni delivery durante tasks. <!-- sdd-owner: parent -->

## WU-005-HTTP-HMAC — GREEN bloqueado

- **Estado:** `blocked` / `needs-decision`; no se modificaron líneas de producto y no se marcaron `T-GREEN-10` ni `T-GREEN-11`.
- **Status estructurado consumido:** `schemaName: gentle-ai.sdd-status`, `changeName: hu005-trial-suscripcion`, `artifactStore: hybrid`, `applyState: ready`, `nextRecommended: apply`, `actionContext.mode: repo-local`, workspace y `allowedEditRoots` limitados a `D:/Universidad/Proyectos/2doSemestre2026/sw1/roomforge-hu005-backend`; sin bloqueos autoritativos ni warnings de action context. El parent conserva el token runtime ya adquirido y este executor no adquirió ni liquidó otro.
- **Workload / PR boundary:** `Estimated changed lines: 372`, `Decision needed before apply: No`, `Chained PRs recommended: No`, `Chain strategy: pending`, `400-line budget risk: Medium`; slice asignado: `27` líneas de producto, sin excepción.

### Motivo exacto del bloqueo

La interfaz actual no permite completar T-GREEN-11 de forma segura editando únicamente `app/modules/tenant/router.py` dentro de 27 líneas: `TenantService.procesar_webhook` solo parsea y procesa `tenant.onboarding.succeeded`, no despacha `subscription.monthly.succeeded`, y no existe un método de servicio mensual que delegue a `TenantRepository.convertir_suscripcion_mensual`. Implementar la conversión directamente en el router rompería la frontera requerida `HMACWebhookSignatureVerifier → parser → TenantService → TenantRepository`, y comprimir esa lógica eliminaría guards de autenticación, parsing, frescura, no divulgación o mapeo sanitizado.

Para desbloquear se requiere autorización explícita para ampliar la superficie a `app/modules/tenant/service.py` y ajustar el presupuesto/slice, o un seam de servicio mensual previamente provisto. El router también requiere, como mínimo, registrar `get_current_user`, bootstrap `POST /api/v1/tenant/administrador/bootstrap`, activación protegida, inspección `GET /api/v1/tenant/suscripcion`, respuestas/proyección y mapeos sanitizados; esas rutas no existen hoy.

### Evidencia y límites

- **Lectura estática:** `router.py`, `service.py`, `schemas.py`, `signatures.py`, `identity/router.py`, `repository.py`, tests enfocados, spec, design, tasks y config. Se confirmó que el repository sí expone `convertir_suscripcion_mensual`, pero el service no lo expone.
- **No ejecutado:** pytest, PostgreSQL, Alembic, Ruff, Pyright, compilación, delivery y CP-004. `CP-004: not executed`.
- **Producto cambiado:** ninguno (`0` líneas añadidas/eliminadas; diff de router sin cambios).
- **Bookkeeping:** este bloqueo se agregó acumulativamente a `apply-progress.md`; no se alteraron checkboxes porque no se completó ningún task de implementación.
- **Rollback boundary:** no aplica a producto; conservar DATA, CONTRACT, RULES y POSTGRES. Si se autoriza una ampliación, el cambio debe comenzar en el seam de service y luego router, sin tocar HU-004/HU-006 ni crear una segunda firma.
- **Strict TDD:** GREEN no alcanzado para este work unit; no se ejecutó verificación. TRIANGULATE y REFACTOR permanecen diferidos.

## Remaining task rows after blocked WU-005-HTTP-HMAC

- [ ] **T-GREEN-10.** Modificar `app/modules/tenant/router.py` para `Depends(get_current_user)` en bootstrap/activación/inspección, `GET /suscripcion`, body vacío, `Content-Type`, headers únicos y mapeo sanitizado; leer `await request.body()` una sola vez y autenticar antes de lookup de negocio. <!-- sdd-owner: implementation -->
- [ ] **T-GREEN-11.** Unificar `/api/v1/tenant/webhook` y `/api/v1/tenant/suscribir` en la misma tubería `HMACWebhookSignatureVerifier` → parser → `TenantService`; conservar `tenant.onboarding.succeeded`, declarar alias deprecated y hacer fallar cerrado la ruta legacy sin HMAC/evento mensual. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-01.** Ejecutar en PostgreSQL con sesiones separadas activaciones/conversiones concurrentes, locks, unicidad de key, replay exacto y conflictivo, key distinta post-conversión y rollback conjunto; distinguir explícitamente esta evidencia de fake/SQLite y dejar comandos/resultados reales. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-02.** Ejecutar upgrade desde el head Alembic efectivo `0004` solo si la revalidación lo confirma y downgrade únicamente en base descartable vacía; verificar FKs/índices, legacy intacto, ningún dato sintético y bloqueo de downgrade con datos HU-005. En datos reales usar forward-fix, nunca downgrade destructivo. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-03.** Ejecutar, marcando cada comando como pendiente hasta correrlo, `.venv/Scripts/python.exe -m pytest tests -q`, `.venv/Scripts/ruff.exe check app tests`, `.venv/Scripts/pyright.exe app tests` y `.venv/Scripts/python.exe -m alembic -c alembic.ini upgrade head`; no afirmar resultados anticipados. <!-- sdd-owner: implementation -->

## WU-005-HTTP-HMAC — correction completed

- **Status:** `completed` for the bounded correction; overall SDD apply remains incomplete. The prior blocked candidate was remediated without starting a new runtime attempt.
- **Failed evidence remediated:** `sha256:116c5bcab06f1da374a58d034c07645e25a2b359d0fbac993fea774999cc62ae`.
- **Structured status consumed:** `schemaName: gentle-ai.sdd-status`, `changeName: hu005-trial-suscripcion`, `artifactStore: hybrid`, `applyState: ready`, `nextRecommended: apply`, `dependencies.apply: ready`, `blockedReasons: []`; `actionContext.mode: repo-local`, workspace and allowed edit root limited to `D:/Universidad/Proyectos/2doSemestre2026/sw1/roomforge-hu005-backend`, warnings none.
- **Runtime authority warning:** the parent owns the active correction token `sha256:cb6873bba19808797a6757b550e73cbf38979e969bb64a4b82e7d2a48140eab8`; this executor did not acquire or settle.
- **Workload / PR boundary:** prior accounting `386/400`; this correction changed `11` product lines (`8` in `router.py`, `3` in `service.py`), leaving `3` lines of the hard budget. No chained PR or exception was introduced.

### Corrections applied

- `app/modules/tenant/router.py`: imported `BootstrapResponse` and `SuscripcionConversionResponse`; advertised the webhook and deprecated alias with the compatible `WebhookResponse | SuscripcionConversionResponse` response model, including the `200` response.
- `app/modules/tenant/service.py`: derived bootstrap idempotency from the pre-existing server-owned authorized subscription and supplied the required `idempotente` field to `BootstrapResponse`.
- `app/modules/tenant/schemas.py`: unchanged in this correction.
- No other product, root, documentation binary, branch, commit, push, or delivery surface was touched.

### TDD Cycle Evidence

| Work unit | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|
| `WU-005-HTTP-HMAC` correction | Prior failed router/import evidence: `sha256:116c5bcab06f1da374a58d034c07645e25a2b359d0fbac993fea774999cc62ae` | `py_compile` PASS; bounded tenant router/app import PASS | Not run by explicit correction scope; no pytest/PostgreSQL/Alembic/Ruff/Pyright | Not run |

### Checks and accounting evidence

- `python -m py_compile app/modules/tenant/service.py app/modules/tenant/router.py app/modules/tenant/schemas.py` — PASS; no output.
- `python -c "from app.main import app; import app.modules.tenant.router; print('tenant router/app import: ok')"` — PASS; output `tenant router/app import: ok`.
- `git diff --numstat -- app/modules/tenant/service.py app/modules/tenant/router.py app/modules/tenant/schemas.py` — cumulative candidate versus HEAD: `46 32 app/modules/tenant/router.py`, `31 5 app/modules/tenant/schemas.py`, `82 15 app/modules/tenant/service.py`. This cumulative output is not counted as new correction work; the correction delta above is relative to the parent-provided current baseline.
- No pytest, PostgreSQL, Alembic, Ruff, Pyright, delivery gate, review actor, receipt creation/approval, commit, or push was run.

### Tasks and remaining work

- Persisted `tasks.md` now marks only implementation-owned `T-GREEN-10` and `T-GREEN-11` as `[x]`; parent-owned rows remain unchanged. Implementation progress is `23/36` complete with `13` unchecked rows remaining.
- `CP-004` remains `not executed`.
- The focused checks pass, but this is **not** a full behavioral PASS: HTTP behavior, PostgreSQL concurrency/rollback, migration behavior, and full regression remain unverified by the explicitly permitted checks. The parent must settle the correction with the failed evidence revision above and distinct fresh verification evidence.

## Cierre de TRIANGULATE y decisión del maintainer

- Se inició PostgreSQL local mediante Docker; Alembic confirmó `0004` y ejecutó `0004 -> 0005` correctamente.
- La suite completa terminó con **75 passed, 2 failed**: el contrato OpenAPI HU-004 y el webhook mensual HMAC/idempotencia (`500,500,500` frente a `201,200,409`).
- Ruff terminó con **75 violaciones** y Pyright con **5 errores**. No se repitió la suite enfocada porque el resultado completo ya aisló los fallos.
- No existía un harness disposable seguro para probar concurrencia y rollback reales en PostgreSQL; no se insertaron datos sintéticos. El downgrade no se ejecutó.
- `CP-004.1`, `CP-004.2`, `CP-004.3` y `CP-004` permanecen `not executed`. No se ejecutaron correcciones, refactor, revisión, commits, pushes ni delivery.
- Evidencia nativa de TRIANGULATE: `sha256:120f88c9f7e5721c8f590a53dfbc4472cde1d26415acd0c3cc75a96f598712e4`; el maintainer decidió detener y documentar, sin resetear el runtime bloqueado.

#### Remaining task rows (exact unchecked lines)

- [ ] **T-TRI-01.** Ejecutar en PostgreSQL con sesiones separadas activaciones/conversiones concurrentes, locks, unicidad de key, replay exacto y conflictivo, key distinta post-conversión y rollback conjunto; distinguir explícitamente esta evidencia de fake/SQLite y dejar comandos/resultados reales. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-02.** Ejecutar upgrade desde el head Alembic efectivo `0004` solo si la revalidación lo confirma y downgrade únicamente en base descartable vacía; verificar FKs/índices, legacy intacto, ningún dato sintético y bloqueo de downgrade con datos HU-005. En datos reales usar forward-fix, nunca downgrade destructivo. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-03.** Ejecutar, marcando cada comando como pendiente hasta correrlo, `.venv/Scripts/python.exe -m pytest tests -q`, `.venv/Scripts/ruff.exe check app tests`, `.venv/Scripts/pyright.exe app tests` y `.venv/Scripts/python.exe -m alembic -c alembic.ini upgrade head`; no afirmar resultados anticipados. <!-- sdd-owner: implementation -->
- [ ] **T-TRI-04.** Verificar regresión HU-004 (`tenant.onboarding.succeeded`), HU-002 (`tests/test_autenticacion.py`), representabilidad de HU-006, alias firmado, no divulgación/logs y ausencia de UI, billing, nuevos planes, notificaciones, RBAC/memberships o cambios en `docs/diagramas/Diagrama1.eapx`; registrar `CP-004.1/.2/.3` aún `not executed` hasta evidencia completa. <!-- sdd-owner: implementation -->
- [ ] **T-REF-01.** Solo después de TRIANGULATE, simplificar duplicación mínima en `app/modules/tenant/{service,repository,router,schemas}.py` sin cambiar contratos, guards, HMAC, calendario, queries, estados, respuestas ni errores; repetir únicamente checks afectados y mantener ≤400 líneas. <!-- sdd-owner: implementation -->
- [ ] **T-REF-02.** Revisar errores, logs y OpenAPI para confirmar no divulgación y que `/suscribir` sigue siendo alias deprecated de la tubería firmada; registrar warnings como warnings, no convertirlos en PASS ni agregar funcionalidad. <!-- sdd-owner: implementation -->
- [ ] Confirmar que `explore.md`, `proposal.md`, `specs/tenant-subscription/spec.md`, `design.md` y este `tasks.md` son los artefactos vigentes, y que el estado nativo recomienda `tasks` sin blockers antes de iniciar apply. <!-- sdd-owner: implementation -->
- [ ] Confirmar mediante `gentle-ai sdd-attempt acquire` que existe un token `state: proceed` para cada work unit runtime-bearing; liquidar con `settle` y evidencia, sin contadores caller-authored. <!-- sdd-owner: implementation -->
- [ ] Confirmar el head Alembic efectivo y el delta HU-004 antes de fijar `down_revision` o crear la única migración; no duplicar `0004` ni columnas HU-004. <!-- sdd-owner: implementation -->
- [ ] Confirmar que la única suite es `tests/test_tenant_onboarding.py`, que RED no contiene código productivo y que los resultados PostgreSQL/migración siguen pendientes hasta ejecución real. <!-- sdd-owner: implementation -->
- [ ] Confirmar que el forecast es 372/400 y que cualquier excedente detiene `sdd-apply` para decisión explícita de `ask-on-risk`; no crear una excepción silenciosa ni eliminar guards. <!-- sdd-owner: implementation -->
- [ ] Confirmar que CP-004 permanece `not executed` y que no se modifican root, gitlink, `docs/diagramas/Diagrama1.eapx`, ramas, commits, pushes, cleanup ni delivery durante tasks. <!-- sdd-owner: parent -->
- [ ] Aprobar interactivamente el plan antes de lanzar `sdd-apply`; esta fase no crea `apply-progress` ni implementa código. <!-- sdd-owner: parent -->

## Remediación posterior a TRIANGULATE

### Corrección de calidad

- La evidencia TRIANGULATE fallida fue `sha256:120f88c9f7e5721c8f590a53dfbc4472cde1d26415acd0c3cc75a96f598712e4`.
- La remediación preservada inicialmente expiró por timeout con `277` líneas modificadas; luego el maintainer autorizó un presupuesto de corrección separado.
- La validación fresca `sha256:630474d378db8f7642f4d251ea20fdb4d644c04f9f295e4ceae5b0565a8c184f` registró pytest `77 passed, 3 warnings`; Pyright `0`; Ruff `49 errors`; Alembic bloqueado únicamente por ausencia de `DATABASE_URL`.
- La corrección mecánica de Ruff tuvo una contabilidad nativa de `239` líneas modificadas dentro del alcance autorizado de `400` líneas. La evidencia final `sha256:2549b9067a417eac8a1f6cf1e6959b1ce4b3dcb7f70c106827a9c4123e87202f` registró pytest `77 passed, 3 warnings`; Ruff `0`; Pyright `0`; `git diff --check` PASS.
- No se realizaron cambios de código fuente durante la verificación.

### Migración y regresión

- La evidencia `sha256:8b82d1907c28898b70e7c04e4a01e8eeb2789eb2ed53f3333ac3a7d0ad501272` registró Alembic `0005 (head)`, `upgrade head` con salida `0`/sin cambios y checks de calidad en verde.
- No existe evidencia de comportamiento de CP en PostgreSQL. La base PostgreSQL persistente permaneció en `0005 (head)` desde la comprobación de migración previa; no se ejecutó downgrade.

### Intentos con base descartable

- El intento con base temporal creó, migró y eliminó una base descartable, pero se detuvo en el orden de FKs de los fixtures; evidencia `sha256:c7631958d27a93490c8a227b955829376102bb50d3f08771195b804fe9e4827a`.
- El reintento se detuvo antes de crear la base porque `DATABASE_URL` no estaba configurada; evidencia `sha256:d226f398515256a8680cf94a21b97c08be9f8e86383b7eb4db7eac9baa3904a8`.
- El intento final del parent se detuvo antes de crear la base por `SyntaxError` en un heredoc; no se creó ninguna base; evidencia `sha256:9b601baeb956c7d404b1d3b16bdac427fa8885a19f2981cfbe0cacdc52b8659a`.

### Estado actual

- `CP-004`, `CP-004.1`, `CP-004.2` y `CP-004.3` permanecen `not executed/unverified`. No se afirma evidencia de concurrencia, locks, replay, conflictos ni rollback en PostgreSQL.
- No hubo commits, pushes ni delivery. El runtime nativo está bloqueado por decisión del maintainer después del work unit final fallido de CP.

### Presupuesto y contabilidad

- El conteo nativo de la corrección es `239` líneas modificadas y se mantiene separado del acumulado de vida del runtime de `913` líneas y del pronóstico original de `400` líneas.
- No se modificó código fuente durante la verificación.

### Filas restantes

- `T-TRI-01`, `T-TRI-02` y `T-TRI-04` permanecen sin marcar; `T-TRI-03` queda marcado por la ejecución efectiva de calidad y Alembic.
- `T-REF-01` y `T-REF-02` permanecen sin marcar; no se declara REFACTOR.
- Los casos `CP-004.1`, `.2` y `.3` siguen `not executed/unverified` en el corte documental anterior.

## CP-004 — evidencia PostgreSQL y migración completadas

La sección siguiente actualiza el corte anterior y conserva la separación entre evidencia fake/SQLite y evidencia real.

### Evidencia conductual PostgreSQL

- La evidencia parent `sha256:9d2b44780ac326b5f22982350474e5d9473e7ff1f3fc59e7754e3c348ac4783f` se ejecutó contra PostgreSQL 16 en una base disposable migrada a `0005 (head)`.
- El bootstrap server-owned fue idempotente; dos sesiones concurrentes de activación produjeron un solo ganador, estado `trialing` y duración exacta de `336` horas.
- Dos sesiones concurrentes de conversión produjeron un solo evento mensual; el replay exacto devolvió el resultado original, una misma key con payload distinto produjo conflicto, una key nueva posterior a la conversión fue rechazada y un `IntegrityError` de identidad de evento revirtió estado y evento conjuntamente.
- El webhook mensual se verificó con HMAC sobre `timestamp + "." + raw_body`; el primer resultado, replay y conflicto de payload quedaron comprobados en PostgreSQL.
- El harness terminó con exit `0`, sin cambios de fuente, sin procesos huérfanos y sin datos persistentes fuera de la base temporal.

### Evidencia de migración y downgrade

- La evidencia disposable `sha256:eacf82d375fa76332ccc9eae6114c6326330f5d8ad0650ef78f59eb5fb926fcd` confirmó upgrade hasta `0005`, downgrade exitoso a `0004` en base vacía, re-upgrade exitoso a `0005` y permanencia en `0005` después de que el downgrade con datos HU-005 fallara cerrado.
- El downgrade con datos produjo el guard esperado `No se puede degradar con datos de HU-005`; la base temporal se eliminó después con `DROP DATABASE ... WITH (FORCE)`. No se ejecutó downgrade sobre la base persistente.

### Estado y tareas restantes

- `CP-004`, `CP-004.1`, `CP-004.2` y `CP-004.3` dejan de estar `not executed/unverified`: cuentan con evidencia fake/SQLite y PostgreSQL separadas, con las limitaciones documentadas.
- `T-TRI-01`, `T-TRI-02`, `T-TRI-03` y `T-TRI-04` quedan respaldados por la evidencia correspondiente; `T-REF-01` y `T-REF-02` permanecen pendientes y no se declara REFACTOR.
- La contabilidad de la corrección nativa permanece separada: `239` líneas para ese work unit, `913` líneas acumuladas de lifetime y `400` líneas del forecast original. La validación y los harnesses no modificaron código fuente.
