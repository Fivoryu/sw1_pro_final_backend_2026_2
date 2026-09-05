```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:a216833ec10ab2ad074ce54c8bdc8f7012e1d3cc3b0c30ad609f619d2cab2c56
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 8/8
scenarios: 22/22
test_command: ../.venv/Scripts/python.exe -m pytest tests -q
test_exit_code: 0
test_output_hash: sha256:d9fd26b9ad25de6fb2122ecb8d9533ebcd02b865506de0d2e2d11e812be67fd9
build_command: ../.venv/Scripts/pyright.exe app tests
build_exit_code: 0
build_output_hash: sha256:6d88a1b220adb7a3d62092b6e38431f0b3fe8babe9864fab90e5849766260332
```

# Informe de verificación — HU-004 Alta de inmobiliaria

## Resultado

**PASS — verificación de implementación.** No quedan blockers críticos de aceptación. Las advertencias no bloqueantes se separan explícitamente abajo.

- **Fecha/contexto:** 2026-09-03; verificación final desde `backend`, rama `feature/tenant-hu04-06`, HEAD observado `7429193`.
- **Alcance:** backend/API de HU-004, PB-004 y CP-003; se verificaron propuesta, spec, diseño, tareas y progreso de aplicación.
- **Tareas:** `36/36` completas; `0` líneas `- [ ]` de implementación.
- **CP-003:** permanece `not executed` como caso académico; no se lo presenta como evidencia.

## Estado SDD y actionContext

- `schemaName: gentle-ai.sdd-status` v2; `changeName: hu004-alta-inmobiliaria`.
- `artifactStore: hybrid`; propuesta, spec, diseño, tasks y apply-progress están `done`; el verify-report queda creado por esta fase.
- Antes de esta fase: `applyState: all_done`, `dependencies.verify: ready`, `nextRecommended: verify`, `blockedReasons: []`.
- `actionContext.mode: repo-local`.
- `workspaceRoot` y único `allowedEditRoots`: `D:/universidad/Proyectos/2doSemestre2026/sw1/proyecto_final/backend`.
- No hubo advertencias de autoridad. El token nativo de verify permanece bajo responsabilidad del parent y no fue adquirido, liquidado ni reiniciado por este agente.

## Cobertura de propuesta, spec, diseño y tareas

| Criterio | Resultado verificable | Estado |
| --- | --- | --- |
| CA1: catálogo y checkout | Tres planes exactos, precios Decimal/string BOB, cuotas server-owned, checkout demo separado y sin aprovisionamiento. Tests, inspección de código/OpenAPI y evidencia fake. | PASS |
| CA2: frontera HMAC | Body crudo, timestamp, firma `v1` HMAC-SHA256, fail-closed, correlación server-owned y errores sanitizados. Tests y provisión PostgreSQL real documentada. | PASS |
| CA3: atomicidad/idempotencia | Rollback fake por etapa; replay secuencial y concurrente; locks, constraints, cardinalidades y replay entre sesiones PostgreSQL documentados. | PASS |
| CA4: activación | Hash únicamente persistido, TTL, notifier posterior al commit, consumo condicional único y rechazo de token inválido/expirado/consumido. Tests y dos sesiones PostgreSQL documentadas. | PASS |
| Migración/contrato | `0003 → 0004`, adopción legacy, seed idempotente, downgrade protegido y OpenAPI de cuatro superficies HU-004. | PASS |
| No regresión | Rutas y comportamiento de HU-005/HU-006 conservados; sin trial, identidad global, memberships/RBAC, UI, Flutter ni pagos reales. | PASS |

## Evidencia funcional y de calidad

Comandos ejecutados una vez desde `backend`:

- `../.venv/Scripts/python.exe -m pytest tests -q` → **70 passed, 3 warnings**, exit 0.
- `../.venv/Scripts/python.exe -m ruff check app/modules/tenant tests/test_tenant_onboarding.py alembic/env.py alembic/versions/0004_hu004_onboarding.py` → **All checks passed**, exit 0.
- `../.venv/Scripts/pyright.exe app/modules/tenant tests/test_tenant_onboarding.py` → **0 errors, 0 warnings, 0 informations**, exit 0.
- `../.venv/Scripts/python.exe -m ruff check app tests` → **1 error**, exit 1: `I001` preexistente en `app/main.py`, archivo sin cambios. No se afirma un Ruff completo limpio.
- `../.venv/Scripts/pyright.exe app tests` → **0 errors, 0 warnings, 0 informations**, exit 0.
- `git diff --check` → sin salida/errores, exit 0.
- Conteo de tasks: `checked=36`, `unchecked=0`.

Se inspeccionaron los archivos de producción y prueba afectados: `alembic/env.py`, `alembic/versions/0004_hu004_onboarding.py`, `app/core/config.py`, `app/modules/tenant/{catalog,models,ports,repository,router,schemas,service,signatures}.py` y `tests/test_tenant_onboarding.py`.

## Evidencia PostgreSQL y migraciones

Se toma únicamente la evidencia fresca ya registrada en la sección final de `apply-progress`; no se ejecutaron PostgreSQL, Alembic, upgrade ni downgrade durante esta verificación.

- PostgreSQL local 16.14 en Alembic `0004`: alta real con tenant activo, suscripción `active` sin `trial_fin`, invitación pendiente con hash, evento procesado y checkout procesado; replay desde otra sesión devolvió los mismos IDs sin duplicados.
- Dos sesiones locales consumiendo la misma activación produjeron exactamente un resultado y un `None`; la invitación terminó consumida. Un token duplicado falló sin filas parciales y dejó el checkout en `confirmado`.
- Bases temporales: `0001 → 0002 → 0003` y `0003 → 0004`, adopción de tres planes legacy conservando UUIDs, seed determinístico/repetible, downgrade limpio a `0003`, downgrade protegido con checkout y downgrade posterior a limpieza exacta.
- Concurrencia final en base temporal: dos webhooks idénticos en sesiones independientes produjeron un `created=true` y un replay `created=false/idempotente=true`, una fila de cada recurso y FKs/estados válidos.
- Las bases temporales fueron eliminadas y la base `roomforge` quedó sin filas HU-004 tras limpieza exacta. No se ejecutaron operaciones amplias ni downgrade sobre la base de desarrollo.
- `GAP-092` permanece abierto únicamente para las migraciones restantes del proyecto fuera de este cambio y no invalida la evidencia específica de HU-004. No se declara rollout productivo, pagos reales, correo real ni CP-003 ejecutado.

## Seguridad, API y regresiones

- El checkout solo queda habilitado en demo; el webhook autenticado es la única frontera de provisión.
- Requests con campos de autoridad y respuestas/OpenAPI sin token, hash de token, secreto, firma, body crudo, password o SQL fueron cubiertos e inspeccionados.
- OpenAPI conserva exactamente cuatro superficies HU-004 y las cinco rutas de HU-005/HU-006. La activación no crea contraseña, identidad global, membership ni RBAC; el administrador no consume `max_agents`.
- No hay logger/print que exponga material sensible. `WebhookRequest` está importado en `router.py:19–31`; la alerta automática sobre `router.py:126` es stale/false-positive, con Ruff focalizado pasando y definición LSP reportada en `schemas.py:61`. No se cambió el router por esa alerta.

## Strict TDD y calidad de aserciones

- Strict TDD está activo en `openspec/config.yaml` y `apply-progress.md` contiene tablas `TDD Cycle Evidence`.
- Los tests reportados apuntan al archivo existente `tests/test_tenant_onboarding.py`; la suite final sigue GREEN con 70 tests.
- La auditoría no detectó tautologías, ghost loops, aserciones únicamente de tipos, smoke-only tests ni aserciones CSS. Las pruebas fake y estáticas están rotuladas como tales y quedan trianguladas con la evidencia PostgreSQL real.

## Review workload, boundary y advertencias

- Se respetó la estrategia documentada `stacked-to-main`, con boundary PR 1 → PR 2 y sin expansión a UI/Flutter ni dominios excluidos. No se crearon commits ni PRs; por ello el tamaño independiente de cada PR no puede probarse mediante historial.
- El worktree acumulado muestra `2313 insertions(+), 133 deletions(-)` por conservar PR 1 y todos los lotes de PR 2 sin commits. `apply-progress` documenta que ese conteo no representa el intento fresco y registra autorización explícita de techo total `1000`; no existe `size:exception`. Se deja como **WARNING de trazabilidad de slicing**, no como blocker de aceptación.
- Warning no bloqueante: el Ruff completo reproduce el `I001` preexistente de `app/main.py`; las superficies candidatas pasan Ruff focalizado.
- Los tres warnings de pytest son deprecaciones de Starlette/httpx y FastAPI `on_event`, sin fallos funcionales.

## Cambios y fuera de alcance

La candidata contiene únicamente cambios backend esperados en los 12 archivos inspeccionados arriba, además de metadatos locales SDD/CodeGraph. `app/main.py` no fue modificado. `git status` mantiene la rama `feature/tenant-hu04-06`, el HEAD observado y no muestra archivos UI/Flutter/Dart ni cambios fuera del backend. No se realizaron commits, pushes, cambios de rama, ni operaciones Git `reset`, `clean` o `checkout`.

## Blockers exactos

**Ninguno.** Permanecen como límites honestos `GAP-092` global y `CP-003` académico no ejecutado; no son afirmaciones de fallo de la implementación HU-004.
