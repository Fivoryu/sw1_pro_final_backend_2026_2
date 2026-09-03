# Tareas SDD — HU-004 Alta de inmobiliaria

**Cambio:** `hu004-alta-inmobiliaria`  
**Repositorio:** RoomForge Backend independiente  
**Alcance:** backend-only, HU-004/PB-004/CP-003  
**Estrategia:** `delivery_strategy: ask-on-risk`; `chain_strategy: stacked-to-main`  
**TDD:** estricto, en cada unidad RED → GREEN → TRIANGULATE → REFACTOR  
**Límite:** máximo 1000 líneas modificadas, según autorización explícita del usuario; no implementar UI, pagos/correo reales, identidad global, memberships/RBAC, trial HU-005 ni cambios/cancelación/purga HU-006.

## Review Workload Forecast

| Field | Value |
| ------- | ------- |
| Estimated changed lines | 465–580 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

El pronóstico queda dentro del máximo de 1000 únicamente con el alcance indicado. Si la estimación confirmada supera 1000 líneas modificadas, detenerse antes de aplicar y reducir alcance o solicitar una decisión explícita; no asumir una excepción. Cada PR debe mantener su propio inicio, fin, verificación y rollback. Tests y documentación contractual permanecen junto al comportamiento que validan.

## Dependencias y límites de entrega

- PR 1 se dirige a `main` y establece contratos, seams y pruebas RED; no contiene provisión funcional.
- PR 2 se dirige a `main` después de PR 1 e implementa persistencia, provisión, activación, migración, integración y regresión.
- No modificar el repositorio raíz ni copiar su `tasks.md`; solo se permite consultar sus decisiones aprobadas.
- No ejecutar implementación, tests, migraciones, lint, typecheck, commits ni pushes durante esta fase.
- `app/main.py` no requiere cambios; conservar las rutas de HU-005/HU-006.

## Unidad PR 1 — Contratos, catálogo, checkout y autenticidad

**Inicio:** código actual sin las cuatro superficies HU-004 implementadas.  
**Fin:** contratos y seams definidos, pruebas contractuales RED y límites de configuración documentados; todavía sin aprovisionamiento funcional.  
**Rollback:** retirar `catalog.py`, `signatures.py`, `ports.py`, extensiones contractuales/configuración y `tests/test_tenant_onboarding.py` asociadas a PR 1 sin tocar el comportamiento de HU-005/HU-006.

### RED

- [x] Crear `tests/test_tenant_onboarding.py` con fixtures y dobles aislados (`FakeClock`, `FakeSignatureVerifier`, `FakeTenantRepository`, `RecordingActivationNotifier`, `NullFirstAdminIdentityHook`) para probar mediante FastAPI y servicios sin declarar evidencia de ejecución; cubrir explícitamente que el test distingue fake de PostgreSQL. <!-- sdd-owner: implementation -->
- [x] Escribir primero pruebas RED para `GET /api/v1/tenant/plans`: orden exacto Básico/Profesional/Empresarial, precios Decimal serializados como `199.00`, `449.00`, `899.00` BOB, cuotas `5/50/5/10`, `15/200/20/40`, `50/1000/100/150`, y `max_agents` sin contar al administrador. <!-- sdd-owner: implementation -->
- [x] Escribir pruebas RED para catálogo incompleto (`503 PLAN_CATALOG_UNAVAILABLE` sin lista parcial ni escrituras) y plan inexistente/inactivo (`404 PLAN_NOT_AVAILABLE` sin escrituras). <!-- sdd-owner: implementation -->
- [x] Escribir pruebas RED para `POST /api/v1/tenant/checkout`: request exacto con `extra="forbid"`, normalización de correo, respuesta `201` server-owned y ausencia de tenant, suscripción, invitación, evento o activación; incluir rechazo `422` de `tenant_id`, precio, moneda, cuotas y `payload_firmado`. <!-- sdd-owner: implementation -->
- [x] Escribir pruebas RED de política `CheckoutAccessPolicy` que permitan checkout público solo con `APP_ENV=demo` y lo bloqueen fuera de demo antes de crear la intención. <!-- sdd-owner: implementation -->
- [x] Escribir pruebas RED de autenticidad para body crudo, headers únicos y formato `v1=<64 lowercase hex>`, mensaje `ASCII(timestamp) + b"." + raw_body`, HMAC-SHA256, comparación constante, secreto ausente (`503 WEBHOOK_NOT_CONFIGURED`) y firma/header/timestamp inválidos (`401 WEBHOOK_UNAUTHORIZED`). <!-- sdd-owner: implementation -->

### GREEN

- [x] Implementar `app/modules/tenant/catalog.py` con constantes server-owned y orden canónico de los tres planes, sin incluir plan admin ni datos comerciales recibidos del cliente. <!-- sdd-owner: implementation -->
- [x] Extender `app/modules/tenant/models.py` y `app/modules/tenant/schemas.py` solo para tipos y contratos de catálogo/checkout/evento necesarios en PR 1; usar `Decimal`, UUID, `extra="forbid"` y preservar esquemas de HU-005/HU-006. <!-- sdd-owner: implementation -->
- [x] Extender `app/core/config.py` con `APP_ENV`, `BILLING_WEBHOOK_SECRET` opcional sin default secreto, tolerancia de 300 segundos y TTL de activación de 7 días. <!-- sdd-owner: implementation -->
- [x] Implementar `app/modules/tenant/signatures.py` y `app/modules/tenant/ports.py` con verifier, notifier, hook de identidad, política de acceso y reloj inyectables; no persistir ni loguear secreto, firma, body, token o hash de token. <!-- sdd-owner: implementation -->
- [x] Extender `app/modules/tenant/service.py` y `app/modules/tenant/repository.py` para consulta de catálogo y creación exclusiva de `CheckoutIntent`, sin camino implícito de aprovisionamiento. <!-- sdd-owner: implementation -->
- [x] Ajustar `app/modules/tenant/router.py` para catálogo y checkout, mapeo de cuerpos sanitizados y política demo; reservar la lectura única de body crudo para el webhook y no introducir una nueva inclusión en `app/main.py`. <!-- sdd-owner: implementation -->

### TRIANGULATE

- [x] Contrastar cada prueba y respuesta de PR 1 con `specs/tenant-onboarding/spec.md` y `design.md`, verificando que los datos comerciales siempre provengan del catálogo y que el checkout nunca cree recursos de alta; registrar cualquier divergencia como tarea de corrección, no como evidencia ejecutada. <!-- sdd-owner: implementation -->
- [x] Preparar en `tests/test_tenant_onboarding.py` casos de integración de OpenAPI desde `app.main` para las superficies ya definidas, sin ejecutar gates en esta fase; comprobar ausencia de campos sensibles y conservar el alcance de PR 1. <!-- sdd-owner: implementation -->

### REFACTOR

- [x] Revisar duplicación entre schemas, errores y proyecciones de catálogo/checkout en `app/modules/tenant/`, manteniendo router → service → repository y sin cambiar rutas de HU-005/HU-006. <!-- sdd-owner: implementation -->
- [x] Revisar el diff de PR 1 contra el presupuesto y confirmar que no incluye provisión, migración, UI, pagos, identidad/RBAC ni cambios comerciales fuera del catálogo exacto. <!-- sdd-owner: implementation -->

## Unidad PR 2 — Webhook, provisión atómica, activación, migración e integración

**Dependencia:** PR 1 aplicado y revisado en `main`.  
**Inicio:** contratos/seams de PR 1 disponibles y pruebas de onboarding aún fallando para provisión.  
**Fin:** cuatro superficies completas, persistencia/migración compatible, activación consumible, regresión y gates preparados.  
**Rollback:** deshabilitar webhook y retirar únicamente la implementación HU-004 de PR 2; conservar datos creados para trazabilidad y no ejecutar downgrade destructivo sobre datos HU-004.

### RED

- [x] Completar pruebas RED para webhook autenticado: JSON inválido/esquema inválido posterior a autenticación (`422` sin escrituras), correlación inválida (`409 CHECKOUT_NOT_AVAILABLE`), datos comerciales discordantes (`409 CHECKOUT_MISMATCH`) y rechazo de `tenant_id`, nombre, correo o cuotas en el payload. <!-- sdd-owner: implementation -->
- [x] Completar pruebas RED de aprovisionamiento atómico y rollback: tenant, suscripción `active` con `trial_fin=NULL`, invitación pendiente, evento procesado y checkout `procesado`; ante fallo en cada persistencia, esperar `500 ONBOARDING_NOT_PROVISIONED` y cero efectos parciales. <!-- sdd-owner: implementation -->
- [x] Completar pruebas RED de idempotencia secuencial y concurrente con `RLock`/barrera fake y escenarios PostgreSQL preparados: mismo hash devuelve resultado original, hash distinto o evento legacy sin hash devuelve `409 IDEMPOTENCY_CONFLICT`, y checkout ya procesado con otra clave devuelve `409 CHECKOUT_ALREADY_PROVISIONED`. <!-- sdd-owner: implementation -->
- [x] Completar pruebas RED de activación: hash SHA-256 únicamente persistido, TTL de 7 días con igualdad al vencimiento expirada, notifier solo después del commit, fallo de notifier sin rollback, consumo condicional único y `410 ACTIVATION_UNAVAILABLE` para token inválido/expirado/consumido. <!-- sdd-owner: implementation -->
- [x] Completar pruebas RED de migración y seed sobre `alembic/versions/0004_hu004_onboarding.py`: `0003` como dependencia, columnas/FK/índices, seed idempotente, adopción legacy exacta, colisión/discrepancia abortada, preservación de HU-005/HU-006 y downgrade bloqueado cuando existen datos HU-004. <!-- sdd-owner: implementation -->
- [x] Completar pruebas RED de no regresión para rutas y comportamiento existente de HU-005/HU-006, sin añadir trial, cambio de plan, cancelación, cuotas operativas ni purga a HU-004. <!-- sdd-owner: implementation -->

### GREEN

- [x] Extender `app/modules/tenant/models.py` con `Plan.codigo/max_agents`, `CheckoutIntent`, `Invitacion.consumido_en`, `EventoFacturacion.checkout_id/payload_hash` y restricciones compatibles; conservar nullable legacy y representar `precio_bob` como `Decimal`. <!-- sdd-owner: implementation -->
- [x] Implementar en `app/modules/tenant/repository.py` `provision_onboarding(command)` como única escritura de alta: locks `FOR UPDATE`, constraints de idempotencia, carga server-owned, inserciones y actualización de checkout en una transacción, rollback completo y recuperación mediante sesión limpia tras colisión concurrente. <!-- sdd-owner: implementation -->
- [x] Extender `app/modules/tenant/service.py` para ordenar autenticidad → parseo → replay/idempotencia → ventana temporal para eventos nuevos → correlación → provisión; proyectar exactamente `201` nuevo, `200` replay y los errores sanitizados definidos, sin conocer SQL ni traducir genéricamente `IntegrityError`. <!-- sdd-owner: implementation -->
- [x] Ajustar `app/modules/tenant/router.py` para `POST /api/v1/tenant/webhook`, leer `Request.body()` una sola vez antes de cualquier deserialización, mapear headers y errores exactos, y retirar `/alta` como frontera autorizada de aprovisionamiento. <!-- sdd-owner: implementation -->
- [x] Implementar `POST /api/v1/tenant/activacion/consumir` en `app/modules/tenant/router.py` y su servicio/repositorio: hash del token en memoria, actualización condicional `pendiente`/`expira_en > now`, commit propio, notifier posterior al commit y hook nulo sin identidad global, membership o RBAC. <!-- sdd-owner: implementation -->
- [x] Crear `alembic/versions/0004_hu004_onboarding.py` y ajustar `alembic/env.py` para importación de metadata; hacer migración aditiva, UUIDs de seed determinísticas, adopción legacy solo ante coincidencia exacta, abortar colisiones/discrepancias y proteger el downgrade con datos HU-004. <!-- sdd-owner: implementation -->

### TRIANGULATE

- [x] Ejecutar, cuando corresponda en la fase de apply/verify y no ahora, evidencia PostgreSQL real separada de fakes para locks, constraints, rollback, upgrade desde `0001`/`0003`, seed, fixture legacy, downgrade protegido y consumo concurrente; si PostgreSQL no está disponible, conservar el gap `GAP-092` sin afirmar PASS. <!-- sdd-owner: implementation -->
- [x] Comparar respuestas HTTP, estados y cardinalidades observables de las cuatro rutas con `spec.md` y `design.md`, incluyendo replay fuera de ventana, notifier posterior al commit, ausencia de secretos/tokens en respuestas y logs, y autoridad server-owned. <!-- sdd-owner: implementation -->
- [x] Inspeccionar OpenAPI desde `app.main` y verificar exactamente catálogo, checkout, webhook y activación, cuerpos/respuestas documentados y ningún campo sensible; ejecutar además la regresión de HU-005/HU-006 con los comandos definidos en `project-context.md`. <!-- sdd-owner: implementation -->

### REFACTOR

- [x] Eliminar duplicación de errores, normalización y proyecciones sin alterar códigos HTTP ni mensajes fijos; mantener separación router → service → repository y límites de puertos. <!-- sdd-owner: implementation -->
- [x] Auditar seguridad y observabilidad en `app/modules/tenant/`: no registrar raw body, firma, secreto, token, hash de token, contraseña, correo completo ni SQL; usar solo identificadores opacos y resultados sanitizados. <!-- sdd-owner: implementation -->
- [x] Confirmar que el alta no activa trial de HU-005, no crea identidad global/membership/RBAC, no consume `max_agents` con el admin y no altera funcionalidad de HU-005/HU-006 fuera de adaptaciones indispensables. <!-- sdd-owner: implementation -->
- [x] Validar el presupuesto final de PR 2 y del cambio completo: mantenerse entre 465–580 estimadas y siempre debajo de 1000 líneas modificadas; si supera 1000, bloquear antes de apply y devolver el alcance para decisión explícita. <!-- sdd-owner: implementation -->
- [x] Dejar documentados en el informe de verificación los comandos de gates: `..\.venv\Scripts\python.exe -m pytest tests -q`, Ruff, Pyright y Alembic; no marcar CP-003 como ejecutado sin evidencia real. <!-- sdd-owner: implementation -->

## Exclusiones verificables

No crear tareas para UI/Web/Flutter, pagos reales, correo real u outbox durable, rollout productivo del checkout público, usuario global, memberships/RBAC, invitaciones de agentes, recuperación de cuentas, auditoría completa, workers, S3/SQS, catálogo inmobiliario ni refactors generales de HU-005/HU-006. No crear tareas de RDD, receipts, delivery gates, commits o pushes.

## Key Learnings

- El webhook autenticado es la única frontera de provisión; checkout y alta deben permanecer operaciones distintas.
- La igualdad de replay depende del hash de bytes crudos y las constraints/locks de PostgreSQL, no de un pre-check de aplicación.
- La activación conserva el token crudo solo en memoria hasta el commit y no resuelve identidad global.
- El presupuesto obliga a dos unidades stacked-to-main y a bloquear cualquier expansión por encima de 600 líneas.
