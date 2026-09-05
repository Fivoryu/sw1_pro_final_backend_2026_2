# Tareas de implementación — HU-005 Trial y suscripción mensual

- **Cambio:** `hu005-trial-suscripcion`
- **Trazabilidad:** PB-005 / HU-005 / CU-005 / CP-004
- **Repositorio/worktree gobernante:** `sw1_pro_final_backend_2026_2`, `D:/Universidad/Proyectos/2doSemestre2026/sw1/roomforge-hu005-backend`
- **Rama:** `feature/hu005-trial-suscripcion`
- **Common directory y contabilidad:** exclusivamente el common directory del backend; el monorepo raíz es referencia y no se modifica.
- **Almacén:** Hybrid (OpenSpec + Engram); el archivo OpenSpec se persiste aquí. Engram no está disponible en esta ejecución.
- **Ejecución:** interactiva; el parent debe aprobar la siguiente fase.
- **Strict TDD:** obligatorio, en orden RED → GREEN → TRIANGULATE → REFACTOR.
- **Entrega:** `ask-on-risk`; estrategia de cadena `pending`.
- **Límite duro:** exactamente 400 líneas modificadas como máximo; no existe excepción implícita.
- **Estado:** implementación GREEN y TRIANGULATE completados; `T-TRI-01`, `T-TRI-02`, `T-TRI-03` y `T-TRI-04` cuentan con evidencia; `CP-004` y `CP-004.1/.2/.3` están respaldados por pruebas determinísticas, PostgreSQL disposable, migración y regresión; REFACTOR no iniciado.

## Review Workload Forecast

| Campo | Valor |
|---|---|
| Estimated changed lines | 372 (adiciones + eliminaciones) |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | PR único, con work units internos y fronteras explícitas |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |
| Reserva | 28 líneas; no autoriza alcance adicional |
| Consecuencia exacta si el total supera 400 | Detener `sdd-apply` y solicitar una decisión explícita para reducir o dividir el slice; no elevar el límite ni eliminar guards |

| Work unit | Fase | Estimación (adiciones + eliminaciones) |
|---|---|---:|
| `WU-005-TDD` | RED: preflight y tests enfocados | 88 |
| `WU-005-DATA` | GREEN: modelo y migración | 50 |
| `WU-005-CONTRACT` | GREEN: schemas y proyección | 36 |
| `WU-005-RULES` | GREEN: service, reglas y calendario | 60 |
| `WU-005-POSTGRES` | GREEN: repository, locks, transacción y replay | 78 |
| `WU-005-HTTP-HMAC` | GREEN: router, HMAC y alias | 27 |
| `WU-005-TRIANGULATE` | TRIANGULATE: PostgreSQL, migración, calidad y regresión | 25 |
| `WU-005-REFACTOR` | REFACTOR: simplificación equivalente | 8 |
| **Total** | | **372** |
| **Reserva** | | **28** |
| **Límite** | | **400** |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

## Guardas de ejecución y dependencias

1. El orden es estricto: no iniciar GREEN hasta cerrar RED; no iniciar TRIANGULATE hasta que GREEN pase; REFACTOR solo después de evidencia TRIANGULATE.
2. Antes de cada work unit runtime-bearing de `sdd-apply`/`sdd-verify`, el parent debe obtener autoridad nativa con `gentle-ai sdd-attempt acquire --cwd <backend> --change hu005-trial-suscripcion --request-id <id> --work-unit <label> --evidence-goal <goal> --max-attempts <count> --max-changed-lines <count>`. Solo `state: proceed` permite lanzar el actor; al terminar debe ejecutar `gentle-ai sdd-attempt settle ...` con un request ID distinto y evidencia acotada. No se persisten contadores inventados en este documento, Engram, prompts o estado de Pi.
3. Cada work unit tiene inicio, fin, evidencia y rollback propios. Un fallo revierte solo el work unit incompleto y bloquea el siguiente; no se hacen cleanup, commits, pushes, cambios de rama ni delivery.
4. El preflight debe revalidar el head efectivo Alembic y el delta real de HU-004. Los archivos observados son `alembic/versions/0001_crear_usuario_global.py` → `0002_crear_sesion.py` → `0003_crear_tablas_tenant.py` → `0004_hu004_onboarding.py`, con `0004` padre `0003`; esto es una observación pendiente de confirmación, no una autorización para fijar `down_revision`.
5. Solo puede existir una migración aditiva HU-005. No duplicar columnas HU-004 (`checkout_id`, `payload_hash`, `suscripcion_id`), no crear datos sintéticos y no agregar un `CHECK` cerrado sobre estados. Con datos HU-005, el rollback de esquema es forward-fix; el downgrade destructivo solo se verifica en base descartable y vacía.

## RED — contratos primero, sin código productivo

### `WU-005-RED-01` — Preflight técnico

- [x] **T-RED-01.** Confirmar en `alembic/versions/`, `alembic/env.py`, `app/modules/tenant/models.py`, `app/modules/tenant/signatures.py` y `app/modules/tenant/router.py` el head único real, el delta de `0004`, `HMACWebhookSignatureVerifier`, `SignatureValidationError`, `WebhookNotConfiguredError`, headers y tolerancia; registrar la evidencia de lectura y detenerse si hay múltiples heads o falta HU-004. <!-- sdd-owner: implementation -->
- [x] **T-RED-02.** Confirmar en `app/modules/tenant/{models,schemas,service,repository,router}.py` y `tests/test_tenant_onboarding.py` los símbolos/seams del diseño, y conservar `tests/test_tenant_onboarding.py` como único módulo enfocado; evidencia: mapa de paths y decisión sin segunda suite redundante. <!-- sdd-owner: implementation -->

### `WU-005-RED-02` — Contrato HTTP y CP-004

- [x] **T-RED-03.** En `tests/test_tenant_onboarding.py`, escribir tests RED para `POST /api/v1/tenant/administrador/bootstrap`, `POST /api/v1/tenant/activar-prueba` y `GET /api/v1/tenant/suscripcion`: body vacío/`extra="forbid"`, JWT, `201/200/401/404/409/422`, proyección mínima y errores no enumerantes; deben fallar por ausencia del contrato y no se declara ejecución. <!-- sdd-owner: implementation -->
- [x] **T-RED-04.** En el mismo módulo, escribir tests RED para `/api/v1/tenant/webhook` y `/api/v1/tenant/suscribir`, incluyendo `201` nuevo, `200` replay, `409` conflictivo, alias sin bypass y trazabilidad de `CP-004.1`, `.2` y `.3`; evidencia fake/unit, pendiente de ejecución. <!-- sdd-owner: implementation -->
- [x] **T-RED-05.** Fijar tests RED de no autoridad de `tenant_id` en body/query/header/evento y de no divulgación de payload, firma, secreto, JWT, password, token, hashes sensibles, correo completo o datos de otro tenant; separar assertions fake/unit de cualquier prueba PostgreSQL. <!-- sdd-owner: implementation -->

### `WU-005-RED-03` — Auth, bootstrap, estado y calendario

- [x] **T-RED-06.** Escribir tests RED usando `get_current_user` de `app/modules/identity/router.py`, principal `MeResponse.id/correo` y dobles locales para bootstrap desde `Invitacion` consumida: usuario inactivo, correo normalizado no coincidente, cero/múltiples candidatos, asociación inactiva, repetición y carrera; evidencia fake/unit, con no enumeración. <!-- sdd-owner: implementation -->
- [x] **T-RED-07.** Escribir tests RED con `FakeClock`/`ClockProtocol` para `active` inicial → `trialing`, `trial_inicio`, diferencia exacta de 336 horas, segunda activación, fechas parciales, estados incompatibles y `now == trial_fin`; no agregar código productivo en RED. <!-- sdd-owner: implementation -->
- [x] **T-RED-08.** Escribir tests RED del algoritmo `America/La_Paz` para día 31, meses de 30, febrero bisiesto/no bisiesto y diciembre→enero, comprobando hora local y timezone-awareness; evidencia determinística fake/unit, no sustitución por 30 días. <!-- sdd-owner: implementation -->

### `WU-005-RED-04` — HMAC, idempotencia, migración y regresión

- [x] **T-RED-09.** Reutilizar en RED los helpers HMAC existentes de `tests/test_tenant_onboarding.py` para bytes raw, `timestamp.encode("ascii") + b"." + raw_body`, headers exactos, tolerancia 300 y borde inclusivo, firma inválida/ausente/stale, secreto ausente y autenticación antes del lookup; evidencia fake/unit, no nueva criptografía. <!-- sdd-owner: implementation -->
- [x] **T-RED-10.** Escribir tests RED del evento exacto `subscription.monthly.succeeded`, `extra="forbid"`, correlación `subscription_id`, plan/monto server-owned, replay fuera de ventana, misma key con bytes distintos, evento HU-004 sin hash mensual y key nueva post-conversión; documentar `201/200/409`. <!-- sdd-owner: implementation -->
- [x] **T-RED-11.** Escribir tests RED de una transacción, rollback conjunto, `FOR UPDATE`, unicidad de `idempotency_key`, carrera de misma key y carrera de activación/conversión; marcar locks, aislamiento, unicidad y concurrencia como PostgreSQL-only, no demostrables con fake/SQLite. <!-- sdd-owner: implementation -->
- [x] **T-RED-12.** Escribir tests RED de upgrade/downgrade para el head HU-004 revalidado, nulabilidad, FKs/índices, legacy `active` intacto, ausencia de datos sintéticos y downgrade bloqueado con datos HU-005; preparar regresión de `tenant.onboarding.succeeded`, `tests/test_autenticacion.py` y estados HU-006 sin afirmar resultados. <!-- sdd-owner: implementation -->

**Frontera RED:** tests contractuales presentes y esperablemente fallidos por la capacidad faltante; preflight documentado; cero código productivo HU-005. Rollback: retirar únicamente el bloque RED, preservando tests HU-004/HU-006 existentes.

## GREEN — implementación mínima

### `WU-005-DATA` — Modelo y migración

- [x] **T-GREEN-01.** Modificar `app/modules/tenant/models.py` con `Suscripcion.trial_inicio`, `Suscripcion.periodo_inicio` como `DateTime(timezone=True)` nullable y `TenantAdministrator` con UUID, FKs, `activo`, timestamps, unicidades `uq_tenant_administrator_tenant_usuario`/`uq_tenant_administrator_invitacion` e índices acordados; agregar a `EventoFacturacion` solo `resultado_periodo_inicio/fin` si el preflight confirma que faltan. <!-- sdd-owner: implementation -->
- [x] **T-GREEN-02.** Crear una única `alembic/versions/<revision>_hu005_trial_subscription.py` con `down_revision` del head efectivo confirmado: upgrade aditivo, sin duplicar HU-004, sin siembra, sin cambios de plan/estado legacy y sin CHECK cerrado; downgrade debe fallar cerrado ante filas/asociaciones, fechas o eventos HU-005 y solo ser mecánico en base descartable vacía. <!-- sdd-owner: implementation -->

### `WU-005-CONTRACT` — Schemas y proyección

- [x] **T-GREEN-03.** Modificar `app/modules/tenant/schemas.py` con request vacío estricto para bootstrap/activación, evento mensual exacto con `extra="forbid"`, respuestas de bootstrap/conversión y proyección con únicamente `subscription_id`, `plan_id`, `estado`, `trial_inicio`, `trial_fin`, `periodo_inicio`, `periodo_fin`; conservar schemas HU-004/HU-006. <!-- sdd-owner: implementation -->

### `WU-005-RULES` — Service, principal, estado y calendario

- [x] **T-GREEN-04.** Extender `app/modules/tenant/service.py:TenantService` para recibir el principal de `get_current_user`, normalizar correo, bootstrap idempotente desde invitación consumida y autorización por asociación activa; no aceptar autoridad de cliente ni modificar `app/modules/identity/router.py`. <!-- sdd-owner: implementation -->
- [x] **T-GREEN-05.** Implementar en `TenantService` activación derivada server-owned: elegibilidad `active` inicial con fechas nulas, `trial_inicio = now`, `trial_fin = now + timedelta(hours=336)`, estado `trialing`, expiración inclusiva y rechazo sin mutación de repeticiones/estados incompatibles. <!-- sdd-owner: implementation -->
- [x] **T-GREEN-06.** Implementar el período mensual con `ClockProtocol`, `ZoneInfo("America/La_Paz")` y `calendar.monthrange`, conservando hora local, clamping al mes siguiente y UTC consciente para persistencia; no usar `timedelta(days=30)`, no implementar lifecycle HU-006. <!-- sdd-owner: implementation -->

### `WU-005-POSTGRES` — Repository, locks y atomicidad

- [x] **T-GREEN-07.** Extender `app/modules/tenant/repository.py:TenantRepository` para bootstrap, autorización, inspección y activación con asociación/tenant/suscripción server-owned, `with_for_update` y revalidación bajo lock; conservar APIs requeridas por HU-004/HU-006 y eliminar el uso HU-005 de commits aislados. <!-- sdd-owner: implementation -->
- [x] **T-GREEN-08.** Implementar en `TenantRepository` la conversión mensual en una única transacción: lookup de key, lock de suscripción, validación de tipo/hash/correlación/plan/monto/trial vigente, actualización, flush, evento con raw-body hash y resultado, y un commit; cualquier fallo revierte suscripción, fechas y evento. <!-- sdd-owner: implementation -->
- [x] **T-GREEN-09.** Recuperar `IntegrityError` únicamente mediante rollback y lectura limpia del registro comprometido, confirmando tipo mensual, hash, correlación y resultado; devolver replay original o `409`, y tratar cualquier error ajeno como fallo transaccional, nunca por texto de excepción. <!-- sdd-owner: implementation -->

### `WU-005-HTTP-HMAC` — Router, HMAC y alias

- [x] **T-GREEN-10.** Modificar `app/modules/tenant/router.py` para `Depends(get_current_user)` en bootstrap/activación/inspección, `GET /suscripcion`, body vacío, `Content-Type`, headers únicos y mapeo sanitizado; leer `await request.body()` una sola vez y autenticar antes de lookup de negocio. <!-- sdd-owner: implementation -->
- [x] **T-GREEN-11.** Unificar `/api/v1/tenant/webhook` y `/api/v1/tenant/suscribir` en la misma tubería `HMACWebhookSignatureVerifier` → parser → `TenantService`; conservar `tenant.onboarding.succeeded`, declarar alias deprecated y hacer fallar cerrado la ruta legacy sin HMAC/evento mensual. <!-- sdd-owner: implementation -->

**Frontera GREEN:** todos los RED determinísticos pasan, HU-004/HU-006 conservan su propósito, y el diff permanece ≤400 líneas; aún no se declara CP-004 ejecutado. Rollback: revertir solo work units incompletas, nunca borrar datos o artefactos HU-004.

## TRIANGULATE — evidencia real completada

- [x] **T-TRI-01.** Ejecutar en PostgreSQL con sesiones separadas activaciones/conversiones concurrentes, locks, unicidad de key, replay exacto y conflictivo, key distinta post-conversión y rollback conjunto; distinguir explícitamente esta evidencia de fake/SQLite y dejar comandos/resultados reales. Evidencia parent: `sha256:9d2b44780ac326b5f22982350474e5d9473e7ff1f3fc59e7754e3c348ac4783f`. <!-- sdd-owner: implementation -->
- [x] **T-TRI-02.** Ejecutar upgrade desde el head Alembic efectivo `0004` solo si la revalidación lo confirma y downgrade únicamente en base descartable vacía; verificar FKs/índices, legacy intacto, ningún dato sintético y bloqueo de downgrade con datos HU-005. En datos reales usar forward-fix, nunca downgrade destructivo. Evidencia disposable: `sha256:eacf82d375fa76332ccc9eae6114c6326330f5d8ad0650ef78f59eb5fb926fcd`. <!-- sdd-owner: implementation -->
- [x] **T-TRI-03.** Ejecutar, marcando cada comando como pendiente hasta correrlo, `.venv/Scripts/python.exe -m pytest tests -q`, `.venv/Scripts/ruff.exe check app tests`, `.venv/Scripts/pyright.exe app tests` y `.venv/Scripts/python.exe -m alembic -c alembic.ini upgrade head`; no afirmar resultados anticipados. <!-- sdd-owner: implementation -->
- [x] **T-TRI-04.** Verificar regresión HU-004 (`tenant.onboarding.succeeded`), HU-002 (`tests/test_autenticacion.py`), representabilidad de HU-006, alias firmado, no divulgación/logs y ausencia de UI, billing, nuevos planes, notificaciones, RBAC/memberships o cambios en `docs/diagramas/Diagrama1.eapx`; la evidencia confirma `CP-004.1/.2/.3` respaldados y el alcance fuera de esas superficies. <!-- sdd-owner: implementation -->

**Frontera TRIANGULATE:** evidencia fake, PostgreSQL, migración y calidad quedaron separadas y ejecutadas; la base disposable fue eliminada y el downgrade con datos HU-005 falló cerrado. No se sustituyó PostgreSQL por SQLite ni se declaró PASS sin evidencia. Rollback: conservar evidencia y detenerse, sin reintentos ilimitados.

## REFACTOR — únicamente simplificación equivalente

- [x] **T-REF-01.** Después de TRIANGULATE se revisó la duplicación mínima en `app/modules/tenant/{service,repository,router,schemas}.py`; no se identificó una simplificación segura que respetara contratos, guards, HMAC, calendario, queries, estados, respuestas y errores, por lo que el REFACTOR fue un no-op documentado. <!-- sdd-owner: implementation -->
- [x] **T-REF-02.** Se revisaron errores, logs y OpenAPI: la suite completa pasó, el alias `/suscribir` conserva la tubería HMAC y no se elevaron warnings a PASS ni se agregó funcionalidad. <!-- sdd-owner: implementation -->

## Matriz de trazabilidad

| Requisito | Tareas | Evidencia de cierre |
|---|---|---|
| R-01 autenticación, asociación, aislamiento | T-RED-01/06, T-GREEN-01/04/07, T-TRI-04 | JWT, invitación consumida, vínculo único, no enumeración |
| R-02 trial único y 336 horas | T-RED-03/07, T-GREEN-05/07 | `trialing`, fechas y lock sin sobrescritura |
| R-03 expiración y solo `trialing → active` | T-RED-07/10, T-GREEN-05/08, T-TRI-01 | `now >= trial_fin`, conflictos, estados HU-006 representables |
| R-04 inspección segura | T-RED-03/05/06, T-GREEN-03/04/10, T-REF-02 | proyección exacta y ausencia de sensibles |
| R-05 HMAC/raw bytes/strictness | T-RED-09/10, T-GREEN-10/11, T-TRI-04 | helper HU-004, headers, tolerancia y auth-before-lookup |
| R-06 conversión, plan y calendario | T-RED-08/10, T-GREEN-06/08/11, T-TRI-01 | event type, plan inmutable, `America/La_Paz`, clamping |
| R-07 idempotencia/atomicidad/concurrencia | T-RED-10/11, T-GREEN-08/09, T-TRI-01 | `201/200/409`, unique, locks, rollback PostgreSQL |
| R-08 statuses y auditoría | T-RED-03/04/10, T-GREEN-03/08/10/11, T-TRI-03 | respuestas y evento mensual persistido |
| R-09 migración/compatibilidad | T-RED-01/12, T-GREEN-01/02, T-TRI-02/04 | upgrade aditivo, downgrade seguro, legacy intacto |
| R-10 seguridad, privacidad y alcance | T-RED-05/06/09, T-GREEN-04/10/11, T-TRI-04, T-REF-02 | no disclosure, sin bypass, no-goals respetados |
| CP-004.1 activación | T-RED-03/07, T-GREEN-04/05/07, T-TRI-01/04 | evidencia JWT, 336 h y `trialing` |
| CP-004.2 conversión | T-RED-04/08/09/10, T-GREEN-06/08/11, T-TRI-01/04 | HMAC, transición y período mensual |
| CP-004.3 replay | T-RED-04/10/11, T-GREEN-08/09, T-TRI-01 | replay `200`, conflicto `409`, sin duplicados |

## Límites y no-goals

No implementar UI React/Flutter, navegación, clientes generados, pagos o billing real, invoices/proveedores, nuevos planes/precios/cuotas, enforcement de cuotas, cambio/renovación de plan, lifecycle HU-006 (`past_due`, grace, suspensión, cancelación, purge), RBAC/memberships generales, roles/permisos, notificaciones/outbox/workers, endpoint público de eventos, S3/SQS, refactors ajenos, cambios de identidad HU-002, commits, pushes, cambios de rama, cleanup, modificaciones del monorepo raíz o `docs/diagramas/Diagrama1.eapx`.

## Checklist final pre-apply

- [x] Confirmar que `explore.md`, `proposal.md`, `specs/tenant-subscription/spec.md`, `design.md` y este `tasks.md` fueron los artefactos vigentes antes de apply; el estado nativo no reportó blockers de planificación. <!-- sdd-owner: implementation -->
- [x] Confirmar mediante `gentle-ai sdd-attempt acquire` un token `state: proceed` para cada work unit runtime-bearing y liquidarlo con `settle` y evidencia nativa; no se usaron contadores caller-authored. <!-- sdd-owner: implementation -->
- [x] Confirmar el head Alembic efectivo `0004` y el delta HU-004 antes de fijar `down_revision = 0004`; la migración `0005` no duplica columnas HU-004. <!-- sdd-owner: implementation -->
- [x] Confirmar que la suite enfocada es `tests/test_tenant_onboarding.py`, que RED no contiene código productivo y que los resultados PostgreSQL/migración fueron ejecutados posteriormente en work units separados. <!-- sdd-owner: implementation -->
- [x] Confirmar forecast original `372/400`; el excedente posterior detuvo el work unit y solo continuó tras decisión explícita del maintainer, sin excepción silenciosa ni eliminación de guards. <!-- sdd-owner: implementation -->
- [x] Confirmar el cierre de CP-004 con evidencia PostgreSQL y migración, sin modificar `docs/diagramas/Diagrama1.eapx`, ramas, commits, pushes ni delivery; las bases temporales fueron limpiadas de forma controlada. <!-- sdd-owner: parent -->
- [x] Aprobar interactivamente el plan antes de lanzar `sdd-apply`; la implementación y la evidencia se ejecutaron por work units autorizados. <!-- sdd-owner: parent -->
