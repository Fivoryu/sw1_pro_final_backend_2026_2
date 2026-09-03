# Exploración local — Alta de inmobiliaria (HU-004)

## Resultado ejecutivo

El backend local ya registra el módulo `tenant` en la composición FastAPI y conserva rutas de HU-005/HU-006, pero HU-004 todavía está implementada como una única operación `POST /api/v1/tenant/alta` que mezcla selección de plan, payload y aprovisionamiento. No existe una frontera verificable de webhook HMAC, checkout separado, catálogo semillado ni semántica segura de idempotencia. El cambio local debe concentrarse en el slice backend/API de HU-004 y CP-003, sin implementar UI ni alterar funcionalmente HU-005/HU-006.

Esta exploración no ejecutó tests, migraciones, lint ni typecheck, conforme a la instrucción de fase.

## Fuentes consultadas

### Contexto local

- `backend/openspec/project-context.md`
- `backend/openspec/config.yaml`
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/clock.py`
- `backend/app/db/base.py`
- `backend/app/db/session.py`
- `backend/app/modules/identity/models.py`
- `backend/app/modules/tenant/models.py`
- `backend/app/modules/tenant/schemas.py`
- `backend/app/modules/tenant/service.py`
- `backend/app/modules/tenant/repository.py`
- `backend/app/modules/tenant/router.py`
- `backend/alembic/env.py`
- `backend/alembic/versions/0001_crear_usuario_global.py`
- `backend/alembic/versions/0002_crear_sesion.py`
- `backend/alembic/versions/0003_crear_tablas_tenant.py`
- búsqueda en `backend/tests/`: solo se encontró evidencia de pruebas de registro; no se encontró una suite específica de tenant/onboarding en los nombres o referencias consultados.

### Referencia externa aprobada

Se consultaron, sin modificar ni copiar como artefactos locales de referencia, los cuatro documentos del cambio raíz: `proposal.md`, `specs/tenant-onboarding/spec.md`, `design.md` y `tasks.md`. Sus decisiones sirven para delimitar esta exploración; todavía no son evidencia de implementación ni de ejecución.

## Hechos observados

### Composición y configuración

- `app/main.py` incluye `tenant_router` bajo `/api/v1`; el router usa el prefijo `/tenant`. No se necesita una nueva inclusión para exponer el módulo.
- La configuración existente contiene `DATABASE_URL`, `JWT_SECRET` y parámetros de sesión, pero no configuración de secreto HMAC, tolerancia de timestamp ni TTL de activación.
- Alembic importa las entidades actuales de identidad y tenant y usa `Base.metadata`; cualquier entidad nueva debe incorporarse a ese punto de composición.
- La cadena local de migraciones es `0001` → `0002` → `0003`. La `0003_crear_tablas_tenant.py` crea `plan`, `tenant`, `invitacion`, `suscripcion` y `evento_facturacion`, pero no carga datos semilla.
- El proyecto usa FastAPI, SQLAlchemy 2.x, PostgreSQL/psycopg, Alembic, Pydantic y pytest. El contexto local declara TDD estricto y comandos de calidad, pero ninguno fue ejecutado.

### Modelo actual

- `Plan.precio_bob` está anotado como `float` aunque la columna SQL es `Numeric(10, 2)`. No existe `codigo` ni `max_agents`.
- `Invitacion.token_unico` es único y guarda el valor que el servicio calcula como SHA-256 del token crudo; no existe `consumido_en` ni operación de consumo observable.
- `EventoFacturacion` tiene `suscripcion_id`, `tipo`, `payload_firmado`, `idempotency_key` único y `estado`; no tiene `checkout_id` ni `payload_hash`.
- No existe un modelo de intención de checkout.
- `Tenant`, `Suscripcion` e `Invitacion` no exponen relaciones ORM declaradas; las relaciones se expresan actualmente por claves foráneas y consultas directas.

### Flujo actual

- `AltaTenantRequest` exige `nombre_empresa`, `correo_admin`, `plan_id`, `payload_firmado` e `idempotency_key` en una sola solicitud.
- `TenantService.dar_de_alta` primero consulta `evento_procesado`, busca un plan por ID, crea tenant, invitación, suscripción y evento, y delega el conjunto al repositorio.
- La suscripción inicial se crea con estado `trialing`, lo que mezcla el alta con el flujo de trial de HU-005; el diseño aprobado requiere que HU-004 aprovisione una suscripción inicial `active` sin activar el trial.
- El mensaje de respuesta incluye el correo del administrador. El servicio genera el token crudo en memoria, pero no existe un puerto de notificación observable ni una operación de activación.
- `TenantRepository.provisionar_alta` agrega las cuatro entidades, hace `flush` y `commit`; cualquier `IntegrityError` se convierte genéricamente en `DuplicateEventError`. El pre-check separado y el `except` no distinguen conflicto de clave, error de FK u otra falla de persistencia.
- La ruta existente expone `POST /api/v1/tenant/alta` y mapea errores genéricamente. No existen endpoints separados para catálogo, checkout, webhook ni consumo de activación.
- Las rutas `activar-prueba`, `suscribir`, `cambiar-plan`, `cancelar` y `ejecutar-purga` permanecen en el módulo y deben conservar su comportamiento funcional.

## Brechas contra HU-004/CP-003

| Área | Evidencia actual | Brecha que debe cerrar la especificación/diseño local |
| --- | --- | --- |
| Catálogo | Tabla `plan` sin seeds, código ni cuota de agentes | Exponer únicamente Básico 199 BOB/5 agentes/50 GB/5 inmuebles/10 reconstrucciones, Profesional 449/15/200/20/40 y Empresarial 899/50/1000/100/150; monto como `Decimal`/string y admin fuera del cupo |
| Checkout | No existe intención ni endpoint separado | Checkout público solo para demo, server-owned, con referencia correlacionable y sin crear tenant, suscripción, invitación ni evento |
| Confianza | `payload_firmado` se acepta como texto en el alta; no hay verificador | Webhook independiente con HMAC-SHA256, body crudo, timestamp, comparación constante, secreto obligatorio y verificación antes de persistir |
| Correlación | El plan se busca solo por `plan_id` de la solicitud | Validar checkout, plan activo y monto contra el catálogo/checkout; no confiar en `tenant_id`, cuotas, correo o nombre enviados por el webhook |
| Atomicidad | Cuatro inserciones en una sesión, sin operación de provisión diseñada para recuperar conflictos | Una transacción que incluya tenant, suscripción, evento, invitación y estado del checkout; rollback conjunto ante cualquier falla |
| Idempotencia | Check-then-insert; unicidad de clave sin recuperación del resultado original | Reintento exacto secuencial/concurrente idempotente; misma clave con payload diferente y checkout ya procesado deben producir conflictos explícitos |
| Activación | Solo se calcula un hash; no hay consumo, expiración ni notifier | Token de un solo uso, hash persistido, TTL, consumo condicional, sin contraseña ni token en respuesta/logs |
| Identidad | Existe `usuario_global`, pero no hay membership/RBAC en tenant | Mantener HU-004 limitada a tenant + invitación pendiente + correo normalizado; diferir usuario global, membresía y rol |
| Contrato | Respuesta genérica con `mensaje`; no hay contratos públicos CP-003 | Definir esquemas y códigos observables para planes, checkout, webhook y activación, sin secretos ni payload sensible |
| Evidencia | No se encontró suite específica de tenant/onboarding; CP-003 externo figura `not executed` | Crear pruebas TDD en la fase apply y dejar CP-003 como no ejecutado hasta obtener evidencia real |

## Puntos de integración

1. **Router/composición:** extender `app/modules/tenant/router.py`; `main.py` ya registra el router. El router debe leer el body crudo del webhook una sola vez y limitarse a dependencias y mapeo HTTP.
2. **Servicio/repositorio:** conservar `router → service → repository`. El servicio debe encapsular normalización, reglas server-owned y comandos; el repositorio debe ser autoridad de transacciones, locks y constraints.
3. **Persistencia:** ampliar `models.py` y crear una migración aditiva posterior a `0003`; actualizar `alembic/env.py` para la entidad de checkout.
4. **Configuración:** añadir secreto HMAC sin default operativo, tolerancia de webhook y TTL de activación en `core/config.py`, sin exponerlos en respuestas o logs.
5. **Puertos de prueba:** introducir reloj inyectable y seams para verificador, notifier simulado, política de acceso y hook nulo de identidad. El notifier debe recibir el token únicamente después del commit.
6. **Regresión:** probar que las rutas de HU-005/HU-006 sigan registradas y no sufran cambios funcionales; no refactorizar sus reglas salvo extracción mínima imprescindible.

## Decisiones aprobadas que deben conservarse

- Planes exactos: Básico `199 BOB / 5 / 50 GB / 5 / 10`; Profesional `449 / 15 / 200 GB / 20 / 40`; Empresarial `899 / 50 / 1000 GB / 100 / 150`.
- El checkout es simulado y público únicamente para el entorno demo; no es una integración de pagos real.
- El webhook firmado con HMAC es la única frontera que puede aprovisionar.
- No se implementan UI, Flutter, HU-005, HU-006, pagos/correo reales, invitaciones de agentes, usuarios globales, memberships ni RBAC.
- El administrador no consume `max_agents`.
- La entrega se mantiene backend-only, con presupuesto máximo de 600 líneas y sin commits/pushes durante SDD.

## Riesgos y gaps para las siguientes fases

- **GAP-004-API-001:** la referencia aprobada ya propone HMAC-SHA256 y headers concretos, pero la especificación/diseño local debe convertirlo en contrato verificable sin dejar ambigüedad de canonicalización, timestamp y respuestas.
- **GAP-004-IDEM-001:** la carrera actual puede duplicar o convertir errores distintos en duplicados; requiere constraints, locks y recuperación posterior a una colisión concurrente.
- **GAP-004-DOM-001:** no inventar relación con `usuario_global`, membership o RBAC; la activación debe quedar limitada al estado de invitación.
- **GAP-004-NOTIF-001:** no hay canal de entrega real ni outbox; usar adaptador simulado/integrable y evitar devolver el token por API.
- **GAP-004-AUTH-001:** el checkout público queda resuelto para demo, pero el rollout productivo requiere una decisión posterior y controles externos.
- **GAP-092:** PostgreSQL, upgrade/downgrade y constraints no fueron verificados en ejecución real.
- **Presupuesto:** el diseño externo estima 465–580 líneas y recomienda cadena de dos PR; cualquier expansión por HU-005/HU-006 o endpoints adicionales amenaza el límite.
- **Datos legacy:** `0003` puede dejar planes sin código y eventos sin hash; la migración debe ser aditiva, reproducible y abortar ante colisiones o discrepancias, sin sobrescrituras comerciales silenciosas.

## Límites de esta exploración

- No se modificó código existente ni la referencia externa.
- Solo se debe generar este artefacto local en la fase explore; proposal/spec/design/tasks locales quedan para fases posteriores.
- No se ejecutaron tests, migraciones, lint, typecheck ni comandos runtime.
- CodeGraph no estuvo disponible en la ruta de metadatos consultada; por eso se usó lectura dirigida de archivos y búsqueda acotada como fallback, sin afirmar un índice válido.
- Engram debe considerarse pendiente hasta confirmar persistencia remota del mismo contenido.

## Siguiente fase

`next_recommended: propose` — convertir estos hechos, brechas y límites en una propuesta local independiente, leyendo este artefacto y respetando las decisiones aprobadas sin copiar la referencia raíz.
