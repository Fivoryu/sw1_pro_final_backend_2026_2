# Informe de archivo — HU-005 Trial y suscripción mensual

## Estado de cierre

**Archivo aprobado:** `PASS WITH WARNINGS`.

El cambio `hu005-trial-suscripcion` queda cerrado documentalmente en el backend local. El estado nativo confirmó `artifactStore: hybrid`, `apply: all_done`, `verify: all_done`, `archive: ready`, `nextRecommended: archive`, `blockedReasons: []` y **36/36 tareas completas**. No se modificaron código fuente, tests, migraciones ni superficies de entrega durante esta fase.

## Alcance y trazabilidad

- **Producto:** `PB-005`.
- **Historia de usuario:** `HU-005`.
- **Caso de uso:** `CU-005`.
- **Criterio de prueba:** `CP-004`, respaldado por `CP-004.1` activación, `CP-004.2` conversión y `CP-004.3` replay.
- **Repositorio gobernante:** `D:\Universidad\Proyectos\2doSemestre2026\sw1\roomforge-hu005-backend`.
- **Dominio sincronizado conceptualmente:** `tenant-subscription`.

El alcance implementado cubre asociación administrativa server-owned, trial único de exactamente 336 horas, inspección tenant-scoped, conversión mensual HMAC, calendario `America/La_Paz`, idempotencia, concurrencia, atomicidad, migración aditiva y downgrade fail-closed. Se preservaron los contratos relevantes de HU-002, HU-004 y la representabilidad futura de HU-006.

## Artefactos leídos

- `openspec/changes/hu005-trial-suscripcion/proposal.md`
- `openspec/changes/hu005-trial-suscripcion/specs/tenant-subscription/spec.md`
- `openspec/changes/hu005-trial-suscripcion/design.md`
- `openspec/changes/hu005-trial-suscripcion/tasks.md`
- `openspec/changes/hu005-trial-suscripcion/apply-progress.md`
- `openspec/changes/hu005-trial-suscripcion/verify-report.md`
- `openspec/config.yaml`

La especificación canónica del cambio se encuentra en `specs/tenant-subscription/spec.md`. No se modificaron ni sobrescribieron los artefactos históricos.

## Verificación y evidencia

El informe validado es un envelope `gentle-ai.verify-result/v1` con veredicto `pass_with_warnings` y revisión de evidencia `sha256:dd63622614f3549da590f37e38827d997dc5535b11f14aaa8d10db954f58b48c`.

- Requisitos: **11/11**.
- Escenarios reportados por el verificador: **0/0**.
- Pytest: **77 passed, 3 warnings**.
- Ruff: **0**.
- Pyright: **0**.
- `git diff --check`: limpio.
- Evidencia PostgreSQL: `sha256:9d2b44780ac326b5f22982350474e5d9473e7ff1f3fc59e7754e3c348ac4783f`.
- Evidencia de migración: `sha256:eacf82d375fa76332ccc9eae6114c6326330f5d8ad0650ef78f59eb5fb926fcd`.

La evidencia PostgreSQL cubrió bootstrap idempotente, activación concurrente con un ganador y trial exacto, conversión concurrente con un evento, replay exacto, payload conflictivo, rechazo de segunda clave, rollback atómico y webhook HMAC mensual. La evidencia de migración cubrió upgrade a `0005`, downgrade en base vacía a `0004`, re-upgrade y downgrade fail-closed con datos HU-005; la base disposable fue eliminada y no se degradó la base persistente.

## Advertencias y limitaciones

- Se conservan tres warnings deprecatorios de pytest.
- Pyright emitió un diagnóstico informativo sobre la ruta del entorno virtual, sin errores de typecheck.
- La contabilidad distingue el forecast original **372/400**, la corrección nativa de **239 líneas** y la contabilidad lifetime de **913 líneas**; esta diferencia queda como advertencia de claridad contable, no como blocker.
- El test con nombre histórico `red/pending` queda como sugerencia documental futura.
- La verificación final no volvió a ejecutar PostgreSQL ni Alembic; reutilizó las revisiones de evidencia asentadas arriba. Esto no reduce su trazabilidad ni las presenta como un resultado nuevo.

## No-goals confirmados

Quedaron fuera UI React/Flutter, pagos o billing real, invoices, proveedores externos, nuevos planes/precios/cuotas, cambios o renovación de plan, lifecycle completo de HU-006, RBAC o memberships generales, notificaciones, outbox, workers, endpoint público de eventos, S3/SQS, refactors ajenos, cambios en `docs/diagramas/Diagrama1.eapx`, modificaciones del monorepo raíz y cualquier operación de entrega.

## Tareas y entrega

El artefacto persistido `tasks.md` no contiene líneas de implementación sin marcar; el progreso confirmado es **36/36**. El REFACTOR fue documentado como no-op equivalente. No se realizaron commits, pushes, cambios de rama, pull requests, rollout, producción ni delivery.

**Próximo paso:** cualquier commit, push o entrega requiere autorización humana explícita.

## Hallazgos de acción y archivo

- `actionContext.mode`: `repo-local`.
- Workspace y raíz de edición autorizada: el backend gobernante indicado arriba.
- No hubo cambios fuera de `archive-report.md` en esta fase.
- No se ejecutó sincronización destructiva ni se movieron carpetas: la autorización de esta ejecución limita la superficie a este informe y preserva el historial activo sin alteraciones.
