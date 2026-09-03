# Informe de archivo — HU-004 Alta de inmobiliaria

## Sección D — Resultado estructurado

- **status:** passed
- **executive_summary:** El cambio HU-004 fue archivado correctamente en modo híbrido. La especificación completa de `tenant-onboarding` se sincronizó mecánicamente y la carpeta activa se movió sin alteraciones al archivo fechado.
- **next_recommended:** ready-for-next-change
- **skill_resolution:** paths-injected

## Estado y contexto

- **artifactStore:** hybrid.
- **change:** `hu004-alta-inmobiliaria`.
- **actionContext:** `mode: repo-local`; raíz autorizada: `backend`.
- **status nativo:** `dependencies.archive: ready`, `nextRecommended: archive`, `blockedReasons: []`, `tasks: 36/36`.
- **delivery:** `stacked-to-main`, PR2; no se realizaron commits, pushes, cambios de rama, resets, clean, checkout, migraciones ni modificaciones de código o pruebas.

## Artefactos leídos

- `proposal.md`
- `specs/tenant-onboarding/spec.md`
- `design.md`
- `tasks.md`
- `apply-progress.md`
- `verify-report.md`
- `openspec/config.yaml`

Las observaciones Engram leídas fueron: propuesta **3039**, spec **3040**, diseño **3041**, tareas **3042**, apply-progress **3078** y verify-report **3110**.

## Tareas y verificación final

- `tasks.md`: **36/36** tareas completadas; no quedan líneas de implementación `- [ ]`.
- Verificación estricta: `pass_with_warnings`, blockers 0, critical findings 0, requirements 8/8, scenarios 22/22.
- Evidencia fresca: **70 tests pytest pasaron**, con 3 warnings de deprecación; Pyright completo y focalizado finalizaron con código 0; Ruff focalizado pasó.
- Ruff completo no se declara limpio: conserva únicamente el `I001` preexistente en `app/main.py`, archivo sin modificar.
- `git diff --check` limpio.
- Evidencia PostgreSQL real local y temporal documentada para provisión, replay, rollback, migraciones, adopción legacy, seed, downgrade protegido y concurrencia.
- Límites honestos: `GAP-092` permanece abierto para migraciones no relacionadas del proyecto y `CP-003` permanece no ejecutado como caso académico.

## Sincronización de especificación

La especificación de `tenant-onboarding` es completa, no una delta operativa. Al no existir `openspec/specs/tenant-onboarding/spec.md`, se copió mecánicamente con `cp` y se verificó con `diff -r`.

- Requisitos ADDED: no aplica; se copió la especificación completa.
- Requisitos MODIFIED: no aplica.
- Requisitos REMOVED: no aplica.
- Requisitos RENAMED: no aplica.
- Especificación canónica creada en `openspec/specs/tenant-onboarding/spec.md`.

### Evidencia verbatim de sincronización

Comando: `diff -r openspec/changes/hu004-alta-inmobiliaria/specs/tenant-onboarding/spec.md <archivo-temporal>`

Salida: **sin salida** (diff vacío; código 0).

## Movimiento e integridad

Destino solicitado y confirmado sin colisión:

`openspec/changes/archive/2026-09-03-hu004-alta-inmobiliaria/`

La carpeta activa fue snapshotada antes del movimiento y trasladada mecánicamente con `mv` (el `git mv` no aplicó porque la carpeta no estaba rastreada). La carpeta activa ya no existe.

### Evidencia verbatim de `diff -r` post-movimiento

Comando: `diff -r "$snapshot_root/source" openspec/changes/archive/2026-09-03-hu004-alta-inmobiliaria`

Salida: **sin salida** (diff vacío; código 0).

El `archive-report.md` es un artefacto aditivo creado después del movimiento y queda excluido de esta comparación.

## Contenido archivado

- `proposal.md` ✅
- `specs/tenant-onboarding/spec.md` ✅
- `design.md` ✅
- `tasks.md` ✅ (36/36)
- `apply-progress.md` ✅
- `verify-report.md` ✅
- `archive-report.md` ✅

## Riesgos y advertencias

- Warning de Ruff completo preexistente en `app/main.py`; no pertenece al cambio.
- Tres warnings de deprecación en pytest.
- Warning de trazabilidad por diff acumulado sin commits; PR1 y PR2 permanecen sin commits por decisión del usuario.
- `GAP-092` y `CP-003` se conservan explícitamente, sin convertirlos en evidencia falsa.
- No se introdujo trabajo de UI/Flutter, HU-005/HU-006, pagos, email, identidad, memberships ni RBAC.

## Confirmaciones estructurales

- Carpeta activa ausente: sí.
- Carpeta archivada presente: sí.
- Artefactos requeridos presentes: sí.
- Spec canónica presente: sí.
- Tareas sin pendientes: sí.
- Integridad recursiva pre-movimiento/post-movimiento: diff vacío.

## Key Learnings

- La sincronización y el archivo deben realizarse con operaciones mecánicas y verificarse con `diff -r` vacío.
- La evidencia final debe distinguir el estado cerrado de HU-004 de los límites globales aún abiertos.
- Un warning preexistente de Ruff no debe presentarse como limpieza total ni como fallo del cambio archivado.
