# Exploración backend — HU-005: trial y suscripción mensual

- **Cambio:** `hu005-trial-suscripcion`
- **Trazabilidad:** PB-005 / HU-005 / CU-005 / CP-004
- **Repositorio:** `sw1_pro_final_backend_2026_2`
- **Worktree:** `D:\universidad\Proyectos\2doSemestre2026\sw1\roomforge-hu005-backend`
- **Rama:** `feature/hu005-trial-suscripcion`
- **Common directory del backend:** `D:\universidad\Proyectos\2doSemestre2026\sw1\proyecto_final\backend/.git`
- **Almacén:** Hybrid (OpenSpec + Engram)
- **Idioma:** español profesional y neutral
- **Estado:** exploración únicamente; no se implementó código

## 1. Límite del repositorio y método

Este trabajo está deliberadamente acotado al worktree backend enlazado. El código Python, los tests y Alembic pertenecen al repositorio backend y su common directory indicado; el monorepo raíz queda como coordinación/documentación y no debe modificarse durante esta fase. Este SDD local es necesario porque el task plan raíz apunta a un common directory distinto y el runtime/accounting debe gobernar el checkout backend que realmente contiene los cambios.

Se leyeron los artefactos aprobados de HU-005 y los archivos fuente/configuración relevantes del backend. El índice CodeGraph no estuvo disponible en este worktree (`.codegraph/` no se encontró mediante lectura) y no hay MCP/CLI ejecutable disponible en esta sesión; por eso, después de esa comprobación, se aplicó una exploración directa y acotada de paths conocidos. No se ejecutaron comandos de Git, historia, tests, migraciones, lint ni typecheck.

## 2. Requisitos aprobados y seams observados

| Requisito aprobado | Seam backend actual | Estado verificado |
| --- | --- | --- |
| Asociación mínima administrador–tenant y aislamiento | `app/modules/identity/router.py:get_current_user` devuelve `MeResponse(id, correo)` tras validar Bearer/JWT y sesión. No existe modelo `TenantAdministrator` ni asociación equivalente en los modelos leídos. | **Falta seam de asociación/autorización tenant.** La dependencia JWT existe; la autorización de tenant debe agregarse sin confiar en `tenant_id` del cliente. |
| Bootstrap server-owned ligado a HU-004 | `app/modules/tenant/models.py:Invitacion` tiene `tenant_id`, `correo`, `estado` y `consumido_en`; `TenantRepository.consumir_activacion` consume la invitación y `TenantService.consumir_activacion` llama al hook `FirstAdminIdentityHook`. | **Seam parcial:** existe la invitación consumida y el hook, pero no el bootstrap ni el vínculo persistente al usuario JWT. |
| Activación única del trial | `tenant/router.py` expone `POST /api/v1/tenant/activar-prueba`; `ActivarPruebaRequest` exige `tenant_id`. `TenantService.activar_prueba` busca por tenant, rechaza solo `trial_fin != None`, fija `estado = "trialing"` y `trial_fin = ahora + timedelta(days=14)`, y usa `guardar_suscripcion`. | **Seam funcional incompleto:** existe cálculo de 14 días, pero falta `trial_inicio`, autorización JWT, guard de estado inicial, lock y transacción atómica. |
| Inspección tenant-scoped | No se observó endpoint `GET /api/v1/tenant/suscripcion` en `tenant/router.py`. `SuscripcionResponse` expone actualmente `id`, `tenant_id`, `plan_id`, estado y fechas, incluyendo campos que no corresponden a la proyección aprobada. | **Falta seam HTTP y proyección segura.** |
| Conversión mensual firmada | `tenant/router.py` expone `POST /api/v1/tenant/webhook` para HU-004 y `POST /api/v1/tenant/suscribir` para la lógica legacy de HU-005. `TenantService.suscribirse` acepta `tenant_id`, `plan_id`, `payload_firmado` e `idempotency_key`, cambia el plan, suma 30 días y hace persistencias separadas. | **Seam inseguro/incompleto:** debe converger a la frontera HMAC compartida y a la transición exclusiva `trialing → active`. |
| Idempotencia y atomicidad | `EventoFacturacion.idempotency_key` es único y `payload_hash` existe; el onboarding HU-004 usa `TenantRepository.provision_onboarding` con locks/replay. La ruta legacy usa `evento_procesado`, `registrar_evento_facturacion` y `guardar_suscripcion` por separado. | **Seam reusable de HU-004, pero falta operación transaccional mensual, hash/resultado mensual y recuperación específica de carrera.** |
| Plan server-owned y correlación | `Plan` contiene `precio_bob`, `codigo`, cuotas y `activo`; `TenantRepository.buscar_plan` existe. HU-004 valida plan/monto contra checkout en `procesar_webhook`. | **Seam parcial:** falta correlación mensual por suscripción y prohibición efectiva de cambiar `plan_id`. |
| Máquina de estados mínima | El modelo usa `Mapped[str]` y no impone catálogo; los estados de HU-006 son cadenas futuras. | **Falta guard de transición en la operación HU-005; no conviene agregar un check que bloquee estados futuros.** |
| Calendario mensual | `ClockProtocol` y `SystemClock` existen en `app/core/clock.py`; la lógica actual usa `timedelta(days=30)`. | **Falta cálculo local `America/La_Paz`, fechas de inicio y clamping de fin de mes.** |

### Archivos principales

- `app/modules/tenant/models.py`: `Tenant`, `Invitacion`, `Plan`, `Suscripcion`, `EventoFacturacion`.
- `app/modules/tenant/schemas.py`: requests actuales inseguros de HU-005 y `SuscripcionResponse`; `WebhookRequest` de HU-004 usa `extra="forbid"` y `event_type = "tenant.onboarding.succeeded"`.
- `app/modules/tenant/service.py`: `TenantService.procesar_webhook`, `activar_prueba` y `suscribirse`.
- `app/modules/tenant/repository.py`: `_find(..., lock=True)`, `_provision_onboarding`, replay HU-004, y métodos legacy separados de suscripción/evento.
- `app/modules/tenant/router.py`: dependencia de repositorio/servicio, lectura única de raw body para `/webhook`, headers y mapeo de errores; rutas HU-005 sin dependencia JWT.
- `app/modules/tenant/signatures.py`: `HMACWebhookSignatureVerifier`.
- `app/modules/identity/router.py`: `get_current_user`.
- `app/modules/identity/models.py`: `UsuarioGlobal` y `Sesion`.

## 3. Alembic y HU-004 HMAC: hechos exactos

### Cadena Alembic

La cadena leída contiene:

- `alembic/versions/0001_crear_usuario_global.py`: revisión `0001`, padre `None`.
- `alembic/versions/0002_crear_sesion.py`: revisión `0002`, padre `0001`.
- `alembic/versions/0003_crear_tablas_tenant.py`: revisión `0003`, padre `0002`.
- `alembic/versions/0004_hu004_onboarding.py`: revisión `0004`, padre `0003`.

Por tanto, el head observable en los archivos disponibles es **`0004`** y su padre es **`0003`**. La nueva revisión debe usar `0004` como `down_revision` solamente después de confirmar en la siguiente fase que no existen otras ramas/revisiones en el checkout objetivo; no se creó ninguna revisión en esta exploración.

`0004_hu004_onboarding.py` agrega a HU-004 `checkout_intencion`, `invitacion.consumido_en`, `evento_facturacion.checkout_id`, `evento_facturacion.payload_hash`, unicidad de `plan.codigo` e índice único parcial de checkout. También siembra los planes aprobados: códigos `basico`, `profesional`, `empresarial`, precios `199.00`, `449.00` y `899.00` BOB. La suscripción base de `0003` conserva `trial_fin` y `periodo_fin`, pero no tiene `trial_inicio` ni `periodo_inicio`.

### HMAC HU-004

Se encontró el helper/export exacto:

- **Path/export:** `app/modules/tenant/signatures.py:HMACWebhookSignatureVerifier`.
- **Error de firma:** `SignatureValidationError`.
- **Error de secreto ausente:** `WebhookNotConfiguredError`.
- **Headers usados por el router:** `X-RoomForge-Webhook-Timestamp` y `X-RoomForge-Webhook-Signature`.
- **Formato:** timestamp compuesto solo por dígitos; firma `v1=` seguida de 64 hexadecimales minúsculos.
- **Mensaje firmado:** `timestamp.encode("ascii") + b"." + raw_body`.
- **Algoritmo/comparación:** HMAC-SHA256 y `hmac.compare_digest`.
- **Tolerancia por defecto/configurada:** constructor por defecto `300` segundos; `Settings.webhook_tolerance_seconds` usa `BILLING_WEBHOOK_TOLERANCE_SECONDS`, también con default `300`.
- **Límite:** se rechaza cuando `abs(now_epoch - timestamp_epoch) > tolerance`; por lo tanto la igualdad del límite se acepta.
- **Raw body:** `recibir_webhook` ejecuta `await request.body()` una vez y el service valida el JSON después de verificar la firma.
- **Replay HU-004:** el service calcula SHA-256 de los bytes y busca la clave después de verificar; eventos heredados sin `payload_hash` no pueden proyectarse como replay seguro.

La verificación anterior es una frontera reutilizable; no debe crearse una segunda implementación criptográfica. La siguiente fase debe confirmar que estos hechos son los de la revisión activa antes de integrar el evento mensual.

## 4. Tests, fixtures y superficie mínima

La suite está bajo `tests/` (no `backend/tests/`). El módulo más relevante es `tests/test_tenant_onboarding.py`, que contiene:

- `FakeClock`, con `NOW = 2026-01-01 12:00 UTC`.
- `FakeSignatureVerifier` y `make_signature`, que reproducen el mensaje raw firmado.
- `FakeTenantRepository` y `OnboardingFakeRepository` para contratos y persistencia in-memory explícitamente no equivalente a PostgreSQL.
- Tests de tolerancia HMAC, autenticación antes del parseo/lookup, replay fuera de ventana, payload extra y rollback del onboarding.
- Tests SQLAlchemy con SQLite para seams de repository, incluido orden FK y proyección de replay.
- `LegacyBehaviorRepository` y `test_hu005_hu006_routes_and_behavior_remain_unchanged`, que actualmente fijan la conducta legacy de HU-005/HU-006 y deberán sustituirse o aislarse cuidadosamente para no conservar el bypass inseguro.

`tests/test_autenticacion.py` cubre `get_current_user`, JWT, sesiones, usuarios activos/inactivos, `PyJWTTokenService`, `FakeSessionRepository` y la configuración de secreto. Es la fuente de fixtures/patrones para el principal JWT, pero no existe todavía un fixture tenant-admin.

La superficie mínima recomendada es extender `tests/test_tenant_onboarding.py` o crear un único `tests/test_tenant_subscription.py` enfocado, evitando duplicar helpers HMAC y reloj. Debe separar explícitamente evidencia fake de evidencia PostgreSQL para locks, unicidad, concurrencia, rollback y migración. No se ejecutó ningún test.

## 5. Configuración y comandos previstos

`pyproject.toml` declara Python `>=3.11`, FastAPI, SQLAlchemy, Alembic, PostgreSQL `psycopg`, PyJWT, pytest y ruff. Pytest usa `pythonpath = ["."]` y `testpaths = ["tests"]`; ruff selecciona `E`, `F`, `I` con longitud 100.

`alembic.ini` usa `script_location = %(here)s/alembic`, y `alembic/env.py` importa metadata de identity y tenant y exige `DATABASE_URL` para migrar.

Comandos documentados para fases posteriores, no ejecutados aquí:

```text
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/python.exe -m ruff check app tests
.venv/Scripts/pyright.exe app tests
.venv/Scripts/python.exe -m alembic -c alembic.ini upgrade head
```

Estos comandos se consignan según la configuración real del backend; la ejecución y disponibilidad del entorno quedan pendientes de apply/verify.

## 6. Dependencias, riesgos y gaps

### Dependencias

1. **HU-004 es prerequisite técnico:** tenant, plan, suscripción inicial `active`, invitación inicial y evento de onboarding deben existir; el vínculo del admin debe partir de una invitación HU-004 efectivamente `consumida`.
2. **HU-004 HMAC:** reutilizar exactamente el helper, headers, formato raw-byte y tolerancia confirmados arriba; el evento mensual debe distinguirse de `tenant.onboarding.succeeded`.
3. **HU-002 identity:** reutilizar `get_current_user`, `MeResponse.id` y `MeResponse.correo`; no alterar el modelo global de identidad.
4. **HU-006:** conservar representables sus estados posteriores sin implementarlos ni imponer restricciones incompatibles.
5. **PostgreSQL/Alembic:** la cadena observable llega a `0004`; antes de crear una migración se debe confirmar que `0004` es el head efectivo y revisar el delta exacto de la rama backend.

### Riesgos/gaps

- `GAP-BE-005-01`: falta la asociación persistente `tenant_administrator` y el bootstrap server-owned; es el principal bloqueo para autorizar activación/inspección.
- `GAP-BE-005-02`: faltan `trial_inicio` y `periodo_inicio`; el modelo actual no permite probar todas las fechas aprobadas.
- `GAP-BE-005-03`: la ruta legacy permite `tenant_id` y `plan_id` del cliente, cambia el plan y usa commits separados.
- `GAP-BE-005-04`: falta operación mensual atómica con lock de suscripción, replay con resultado original y recuperación segura de carrera de unicidad.
- `GAP-BE-005-05`: falta endpoint de inspección y una proyección sin datos sensibles.
- `GAP-BE-005-06`: el nombre exacto de campos/event type mensual aprobado en diseño todavía debe reflejarse contra la frontera técnica existente, sin duplicar columnas HU-004.
- `GAP-BE-005-07`: no se verificó con ejecución la base PostgreSQL, la migración, la cadena Alembic mediante comando, ni los gates de calidad.
- El modelo de evento conserva `payload_firmado` como `Text`; cualquier uso mensual debe evitar exponerlo y preservar la política de raw bytes/hash sin añadir secretos.
- Las pruebas legacy actuales esperan comportamiento incompatible con los requisitos aprobados; la compatibilidad debe resolverse en apply sin reintroducir el bypass.

No se agregan requisitos de producto nuevos. Se mantienen fuera de alcance UI, pagos reales, notificaciones, catálogo nuevo, cuotas, cambios de plan, ciclo completo HU-006, RBAC/memberships generales y endpoint público de eventos.

## 7. Presupuesto y siguiente paso

El límite duro de implementación es **400 líneas modificadas**. El plan raíz aporta un forecast inicial de **372 líneas** (con reserva de 28), que debe tratarse como estimación sujeta a la evidencia real del backend, no como autorización para exceder el límite. Si el desglose backend confirmado supera 400, `ask-on-risk` exige detener apply y pedir una decisión explícita; no se eleva el límite ni se eliminan silenciosamente guards aprobados.

La siguiente fase interactiva puede ser `proposal`/continuación del flujo aprobado, pero antes de tareas/apply debe cerrar el head efectivo, la dependencia HU-004, la elección de módulo de tests y la integración concreta de asociación/admin sin ampliar alcance.

## 8. Estado de ejecución y CP-004

En esta fase:

- no se implementó código de producto;
- no se ejecutaron tests;
- no se ejecutaron migraciones ni comandos Alembic;
- no se ejecutaron lint, typecheck ni comandos de calidad;
- no se generó evidencia operativa, revisión, commit, push ni cambio de rama;
- **CP-004 permanece `not executed`**.

## Fuentes consultadas

- Artefactos aprobados raíz de `openspec/changes/hu005-trial-suscripcion/` (explore, proposal, spec, design, tasks), solo como referencia.
- `app/modules/tenant/{models,schemas,service,repository,router,signatures,ports}.py`.
- `app/modules/identity/{models,router,schemas}.py`.
- `app/core/{clock,config}.py`, `app/db/base.py`, `app/main.py`.
- `alembic.ini`, `alembic/env.py`, `alembic/versions/0001_crear_usuario_global.py`, `0002_crear_sesion.py`, `0003_crear_tablas_tenant.py`, `0004_hu004_onboarding.py`.
- `pyproject.toml`.
- `tests/test_tenant_onboarding.py`, `tests/test_autenticacion.py`.
