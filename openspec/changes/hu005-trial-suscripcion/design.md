# Diseño técnico backend — Trial y suscripción mensual de tenant

- **Cambio:** `hu005-trial-suscripcion`
- **Trazabilidad:** `PB-005` / `HU-005` / `CU-005` / `CP-004`
- **Repositorio:** `sw1_pro_final_backend_2026_2`
- **Worktree gobernante:** `D:\Universidad\Proyectos\2doSemestre2026\sw1\roomforge-hu005-backend`
- **Rama:** `feature/hu005-trial-suscripcion`
- **Common directory de runtime/accounting:** el del backend; el repositorio raíz es solo referencia
- **Idioma:** español profesional y neutral
- **Estado:** diseño listo para tareas; no declara implementación ni ejecución
- **Almacén:** Hybrid (OpenSpec + Engram)
- **Modo:** Strict TDD, `RED → GREEN → TRIANGULATE → REFACTOR`
- **Límite duro de implementación:** 400 líneas modificadas como máximo
- **Forecast conservado:** 372 líneas, con reserva de 28
- **CP-004:** `not executed`

## 1. Decisión técnica y recorrido feliz

Se extenderá exclusivamente el módulo FastAPI `tenant`, conservando la separación:

```text
HTTP router → TenantService → TenantRepository → PostgreSQL
                    ├─ get_current_user / principal JWT
                    ├─ reglas de caso de uso y reloj
                    └─ HMACWebhookSignatureVerifier para eventos
```

La identidad administrativa será el principal que entrega `app/modules/identity/router.py:get_current_user`, no un `tenant_id` del cliente. El servidor formará una asociación mínima `tenant_administrator` a partir de una invitación de HU-004 efectivamente consumida. Solo esa asociación activa autoriza activación e inspección.

El flujo de suscripción será:

```text
HU-004: suscripción initial active
              │ POST /administrador/bootstrap
              ▼
       tenant_administrator activo
              │ POST /activar-prueba
              ▼
       active ──(336 h)──> trialing
                              │ webhook HMAC mensual vigente
                              ▼
                         active convertido
```

No se implementan otras transiciones, renovación, cambio de plan, billing real, notificaciones, RBAC ni memberships generales.

## 2. Hechos de baseline y decisiones cerradas

### 2.1. Hechos observados

- `app/modules/tenant/models.py` contiene `Tenant`, `Invitacion`, `Plan`, `Suscripcion` y `EventoFacturacion`.
- `Suscripcion` ya tiene `tenant_id`, `plan_id`, `estado`, `trial_fin`, `periodo_fin` y `cancelado_en`; faltan `trial_inicio` y `periodo_inicio`.
- `EventoFacturacion` ya tiene `suscripcion_id`, `tipo`, `payload_firmado`, `idempotency_key` único, `estado`, `checkout_id` y `payload_hash` nullable.
- `TenantService.activar_prueba` actualmente recibe `ActivarPruebaRequest.tenant_id`, usa `timedelta(days=14)` y persiste mediante `guardar_suscripcion`; `TenantService.suscribirse` acepta autoridad del cliente, usa 30 días y separa evento y suscripción.
- `TenantRepository` mantiene métodos separados de HU-005/HU-006 (`buscar_suscripcion`, `guardar_suscripcion`, `registrar_evento_facturacion`) y métodos transaccionales de onboarding HU-004. Los métodos nuevos de HU-005 no usarán los commits aislados.
- `tenant/router.py` expone `/activar-prueba`, `/suscribir` y `/webhook`; no existe aún `/administrador/bootstrap` ni `GET /suscripcion`.
- `get_current_user` valida Bearer/JWT y sesión mediante `AuthenticationService.me`, y devuelve `MeResponse` con `id` y `correo`.
- `HMACWebhookSignatureVerifier` está en `app/modules/tenant/signatures.py` y es la única frontera criptográfica aprobada.
- Los archivos Alembic observados son `0001` → `0004`, con `0004_hu004_onboarding.py` como head de archivos y `0003` como padre de `0004`. El head efectivo debe revalidarse antes de crear la única migración de HU-005.
- La suite enfocada existente es `tests/test_tenant_onboarding.py`; contiene `FakeClock`, helpers HMAC, fakes de repositorio, casos de raw body, replay, rollback y una prueba que todavía fija el bypass inseguro de HU-005. `tests/test_autenticacion.py` cubre `get_current_user`.

### 2.2. Decisiones que no se reabren

- El tenant siempre se deriva de una asociación activa server-owned.
- El bootstrap solo puede usar una `Invitacion` HU-004 con `estado = "consumida"`, `consumido_en IS NOT NULL` y correo normalizado coincidente con el principal.
- El trial dura exactamente `14 × 24 = 336` horas.
- La expiración es `now >= trial_fin`; el estado expirado puede permanecer `trialing`.
- La única conversión de HU-005 es `trialing → active`; no se convierte el `active` inicial de HU-004 ni un `active` ya convertido.
- El plan y su monto esperado son server-owned; el evento solo aporta datos para correlación y validación.
- El evento mensual exacto es `subscription.monthly.succeeded`.
- `/suscribir` queda como alias deprecated de la misma tubería HMAC de `/webhook`; no conserva el bypass legacy.
- El período mensual usa `America/La_Paz`, conserva la hora local y clampa el día al último día del mes siguiente.
- Evento mensual, cambio de suscripción y fechas se confirman o revierten en una sola transacción.
- El replay exacto devuelve `200`; una conversión mensual nueva devuelve `201`; la reutilización conflictiva devuelve `409`.
- Las respuestas y errores no enumeran tenants ni exponen secretos, tokens, payloads, firmas, hashes sensibles o datos de otros tenants.

## 3. Arquitectura y flujo de datos

### 3.1. Dependencias por capa

| Capa | Archivo/símbolo | Responsabilidad HU-005 |
|---|---|---|
| HTTP | `app/modules/tenant/router.py` | Resolver dependencias, leer raw body una vez, obtener headers, invocar service y traducir errores sanitizados. |
| Identidad | `app/modules/identity/router.py:get_current_user` | Validar JWT/sesión y entregar `MeResponse.id`/`correo`; no se modifica. |
| Servicio | `app/modules/tenant/service.py:TenantService` | Orquestar casos de uso, normalizar correo, aplicar guards, usar `ClockProtocol`, validar payload autenticado y proyectar respuestas. |
| Firma | `app/modules/tenant/signatures.py:HMACWebhookSignatureVerifier` | Validar formato, HMAC-SHA256, comparación constante y secreto; no se crea criptografía paralela. |
| Persistencia | `app/modules/tenant/repository.py:TenantRepository` | Consultas server-owned, locks `FOR UPDATE`, unicidad, transacción única, flush, rollback y recuperación confirmada de carreras. |
| Modelo | `app/modules/tenant/models.py` | Campos de fechas, asociación administrativa y solo el delta de resultado mensual que HU-004 no tenga. |
| Contrato | `app/modules/tenant/schemas.py` | Requests strictos y proyecciones sin datos sensibles, preservando schemas HU-004/HU-006. |

No se agregan capas, workers, outbox, proveedores externos ni un repositorio paralelo.

### 3.2. Bootstrap administrativo

1. El router aplica `Depends(get_current_user)` y no acepta un selector de tenant.
2. `TenantService` recibe el `MeResponse`, normaliza `correo` con `strip().lower()` y solicita el bootstrap por `usuario_global_id`.
3. El repository bloquea la asociación existente del usuario, si la hay. Una asociación activa reconocida se devuelve como repetición idempotente.
4. Si no existe asociación, busca invitaciones de HU-004 consumidas cuyo correo normalizado coincida, con tenant y suscripción existentes. El criterio no usa `tenant_id` del request.
5. El repository bloquea el candidato y verifica que la invitación no esté asociada. Cero candidatos o más de uno producen el error genérico `ADMIN_BOOTSTRAP_UNAVAILABLE`.
6. La inserción de `tenant_administrator` y la confirmación de la asociación ocurren en una transacción. Una carrera de unicidad se clasifica mediante lectura posterior del registro comprometido, nunca por el texto de una excepción.
7. El service proyecta una respuesta mínima: creación `201`, repetición `200`. No consume otra vez la invitación, no crea usuarios, contraseñas, roles, memberships ni notificaciones.

### 3.3. Activación del trial

1. `get_current_user` valida el principal antes de entrar al caso de uso.
2. El service llama a una operación repository que deriva el tenant desde `usuario_global_id` y su asociación activa.
3. El repository bloquea la asociación y la suscripción única del tenant. Revalida el vínculo dentro de la transacción para evitar TOCTOU.
4. La elegibilidad exige suscripción inicial `active`, `trial_inicio`, `trial_fin`, `periodo_inicio` y `periodo_fin` nulos, y ausencia de conversión mensual previa.
5. Con un `now` consciente de zona del `ClockProtocol`, escribe `trial_inicio = now`, `trial_fin = now + timedelta(hours=336)` y `estado = "trialing"`.
6. Hace un único flush/commit y el service devuelve la proyección aprobada. Una segunda solicitud ve el row iniciado bajo lock y devuelve `409` sin cambiar fechas, plan, estado ni eventos.

### 3.4. Inspección tenant-scoped

1. El router aplica el mismo `get_current_user`.
2. El service pide la suscripción a través de la asociación activa del usuario; no recibe `tenant_id`.
3. El repository resuelve el tenant y devuelve únicamente la suscripción autorizada.
4. El service serializa la proyección mínima. Asociación ausente, inactiva, tenant no disponible o suscripción no accesible comparten `404 TENANT_SUBSCRIPTION_UNAVAILABLE` cuando el JWT sí es válido.

### 3.5. Webhook mensual y preservación de HU-004

1. `/webhook` y `/suscribir` leen `await request.body()` una sola vez.
2. El router exige `Content-Type: application/json` y exactamente un header de timestamp y uno de firma.
3. El service invoca `HMACWebhookSignatureVerifier` sobre los bytes exactos antes de consultar tenant, plan o suscripción. El dispatch posterior distingue `tenant.onboarding.succeeded` de `subscription.monthly.succeeded`.
4. El JSON autenticado se valida con campos extra prohibidos. El body no se reserializa para verificar ni para calcular `SHA-256(raw_body)`.
5. El branch `tenant.onboarding.succeeded` conserva la operación HU-004 y sus respuestas; no se proyecta como conversión mensual.
6. El branch mensual delega la operación atómica al repository con `subscription_id`, `plan_id`, `monto_bob`, `idempotency_key`, raw body, hash y el instante de conversión.
7. Ambas rutas HTTP llaman al mismo handler/pipeline; `/suscribir` solo añade la marca deprecated en OpenAPI. No existe una ruta de persistencia legacy separada.

## 4. Cambios exactos por archivo y símbolos

| Archivo | Modificación prevista | Compatibilidad preservada |
|---|---|---|
| `app/modules/tenant/models.py` | Agregar `Suscripcion.trial_inicio`, `Suscripcion.periodo_inicio` y `TenantAdministrator`; agregar solo `resultado_periodo_inicio`/`resultado_periodo_fin` en `EventoFacturacion` si la verificación del head confirma que faltan. | Se conservan `trial_fin`, `periodo_fin`, `cancelado_en`, campos HU-004 y posibilidad de estados HU-006. |
| `app/modules/tenant/schemas.py` | Agregar request vacío strict para bootstrap/activación, evento mensual strict, respuesta de bootstrap, proyección tenant y respuesta de conversión. Mantener `WebhookRequest`/`WebhookResponse` de HU-004. | No cambiar el contrato de onboarding. Mantener `SuscripcionResponse` usado por HU-006 y usar una proyección separada para no ampliar respuestas con datos sensibles ni romper esa superficie. |
| `app/modules/tenant/service.py` | Extender `TenantService` con principal administrativo, bootstrap, activación derivada, inspección, cálculo de calendario y branch mensual de `procesar_webhook`. Añadir errores de dominio sanitizables. | Mantener `procesar_webhook` y `_project_onboarding` para HU-004; dejar `cambiar_plan`, cancelación y purga de HU-006 representables, sin convertirlos en alcance de HU-005. |
| `app/modules/tenant/repository.py` | Agregar operaciones de asociación, bootstrap, autorización, inspección, activación y conversión mensual. Incorporar locks, relectura post-lock, una transacción y recuperación confirmada de `IntegrityError`. | Mantener `provision_onboarding`, `consumir_activacion` y métodos existentes requeridos por HU-004/HU-006. Los nuevos casos no llaman commits aislados. |
| `app/modules/tenant/router.py` | Inyectar `get_current_user` en bootstrap, activación e inspección; agregar `GET /suscripcion`; hacer que `/webhook` y `/suscribir` compartan la entrada HMAC y mapear errores. | Preservar paths y respuestas de `/plans`, `/checkout`, `/activacion/consumir` y onboarding. Mantener paths HU-006 sin alterar su propósito. |
| `app/modules/tenant/signatures.py` | Sin implementación paralela. Solo tocar el helper si la verificación de la rama activa demuestra una adaptación mínima necesaria, conservando clase, fórmula, headers, tolerancia y errores. | HU-004 sigue usando `HMACWebhookSignatureVerifier` y sus excepciones. |
| `app/modules/identity/router.py` | Sin cambios. | JWT, sesión, `MeResponse` y errores genéricos de HU-002 permanecen intactos. |
| `alembic/versions/<revision>_hu005_trial_subscription.py` | Una sola revisión aditiva, creada únicamente después de confirmar el head efectivo y el delta HU-004. | No se duplican columnas de HU-004 ni se eliminan datos existentes. |
| `tests/test_tenant_onboarding.py` | Extender el único módulo tenant enfocado, reutilizando `FakeClock`, helpers HMAC y fixtures; reemplazar la expectativa de bypass por contrato seguro y separar regresión HU-006. | No crear una segunda colección redundante ni alterar pruebas de identidad fuera de lo necesario. |

No se modifican UI, `docs/diagramas/Diagrama1.eapx`, catálogo de planes, configuración de otros módulos ni metadata raíz. La selección final de nombres internos que no estén probados en baseline se verifica en apply antes de escribir código; no habilita alcance adicional.

## 5. Modelo de datos y migración

### 5.1. `Suscripcion`

Agregar exactamente dos columnas nullable, ambas conscientes de zona:

| Columna | SQLAlchemy/PostgreSQL | Regla |
|---|---|---|
| `trial_inicio` | `DateTime(timezone=True)`, `NULL` | Instante capturado al activar el trial. |
| `periodo_inicio` | `DateTime(timezone=True)`, `NULL` | Instante capturado al convertir mensualmente. |

`trial_fin` y `periodo_fin` se conservan y continúan siendo `DateTime(timezone=True)` según el esquema observado. Las filas initial `active` de HU-004 permanecen con los dos campos nuevos en `NULL`. No se agregan columnas `expired`, `monthly_status`, `plan_contratado` ni checks de catálogo de estados.

### 5.2. `tenant_administrator`

La tabla propuesta es exacta y dedicada a esta costura mínima:

| Campo | Tipo/constraint | Regla |
|---|---|---|
| `id` | UUID, PK, no nulo | Identificador opaco de la asociación; se genera server-side. |
| `tenant_id` | UUID, FK `tenant.id`, no nulo | Tenant derivado del servidor. |
| `usuario_global_id` | UUID, FK `usuario_global.id`, no nulo | Usuario del principal JWT. |
| `invitacion_id` | UUID, FK `invitacion.id`, no nulo | Invitación HU-004 consumida; nunca el token crudo. |
| `activo` | Boolean, no nulo, default server-side `true` | Único guard de habilitación de HU-005. |
| `creado_en` | `TIMESTAMPTZ`, no nulo, default server-side `now()` | Momento del vínculo. |
| `desactivado_en` | `TIMESTAMPTZ`, nullable | Reservado; HU-005 no desactiva asociaciones. |

Constraints con nombres estables propuestos:

- `PK tenant_administrator(id)`.
- `FK tenant_administrator.tenant_id → tenant.id`, nombre `fk_tenant_administrator_tenant`.
- `FK tenant_administrator.usuario_global_id → usuario_global.id`, nombre `fk_tenant_administrator_usuario_global`.
- `FK tenant_administrator.invitacion_id → invitacion.id`, nombre `fk_tenant_administrator_invitacion`.
- `UNIQUE (tenant_id, usuario_global_id)`, nombre `uq_tenant_administrator_tenant_usuario`.
- `UNIQUE (invitacion_id)`, nombre `uq_tenant_administrator_invitacion`.

Índices no únicos exactos para resolver autorización:

- `ix_tenant_administrator_usuario_activo` sobre `(usuario_global_id, activo)`.
- `ix_tenant_administrator_tenant_activo` sobre `(tenant_id, activo)`.

La unicidad de invitación evita que una misma activación inicial cree dos vínculos. La unicidad de tenant/usuario hace idempotente el mismo vínculo. No se agregan `rol`, `permiso`, `membership_type`, tabla de roles ni una unicidad que convierta esta tabla en RBAC general.

Una asociación solo es elegible cuando `activo = true`, el usuario coincide, el tenant existe, la invitación vinculada tiene `estado = "consumida"` y `consumido_en IS NOT NULL`. La autorización posterior usa la fila y sus FKs, no el correo ni input del cliente.

### 5.3. `EventoFacturacion`: solo delta ausente

El modelo HU-004 ya provee `suscripcion_id`, `tipo`, `payload_firmado`, `idempotency_key` único, `estado`, `checkout_id` y `payload_hash`. No se vuelven a crear esas columnas, su FK, su índice ni sus constraints.

Antes de modificar modelos o migración, apply debe leer el modelo activo y todas las revisiones efectivas. Si, y solo si, HU-004 no provee un resultado mensual persistible, se agregan exactamente:

- `resultado_periodo_inicio TIMESTAMPTZ NULL`.
- `resultado_periodo_fin TIMESTAMPTZ NULL`.

No se agrega una nueva clave de idempotencia, `subscription_id`, `payload_hash`, `checkout_id`, `tenant_id`, `resultado_estado` ni una tabla de eventos paralela. `estado = "procesado"` y el tipo mensual exacto completan el resultado; el estado de replay es conocido como `active` para este único evento.

El resultado de replay se reconstruye desde `EventoFacturacion.id`, `suscripcion_id`, tipo mensual, `payload_hash` y ambas fechas de resultado, no desde el estado actual de la suscripción ni desde el body recibido posteriormente. Un evento legacy sin `payload_hash` o sin fechas de resultado mensuales nunca se presume replay.

### 5.4. Una única migración aditiva

La revisión se crea una sola vez con un nombre nuevo y `down_revision` igual al único head efectivo confirmado en apply. Aunque los archivos leídos muestran `0004`/`0003`, no se debe fijar ese valor sin verificar la cadena real del checkout mediante la superficie Alembic disponible. Si hay múltiples heads, una revisión faltante o columnas HU-004 ausentes, se detiene apply y se coordina la dependencia; no se inventa una rama ni se duplican columnas.

El `upgrade()` debe, en orden seguro:

1. Agregar `suscripcion.trial_inicio` y `suscripcion.periodo_inicio` nullable.
2. Crear `tenant_administrator` con sus tres FKs, defaults y constraints.
3. Crear los dos índices `(usuario_global_id, activo)` y `(tenant_id, activo)`.
4. Agregar las dos columnas `resultado_periodo_*` solo si la verificación las declara ausentes.
5. No sembrar datos, no crear asociaciones retroactivas, no crear trials, no alterar planes/precios/cuotas y no cambiar el estado de filas legacy.

No se agrega ningún `CHECK` cerrado sobre `estado`; las guards pertenecen a la aplicación bajo lock para que HU-006 pueda almacenar estados futuros.

### 5.5. Downgrade seguro y forward-fix

El `downgrade()` debe inspeccionar antes de soltar cualquier pieza. Debe fallar cerrado si existe alguno de estos marcadores:

- una fila `tenant_administrator`;
- cualquier `trial_inicio` o `periodo_inicio` no nulo;
- un evento `subscription.monthly.succeeded` o el tipo legacy mensual equivalente, o cualquier resultado mensual no nulo;
- una situación de integridad que impida confirmar que no hay datos HU-005.

Incluso si los marcadores son nulos, la política operativa solo permite downgrade en una base descartable y sin datos comprometidos; en una base con datos HU-004 se conserva la migración. El orden de reversión, únicamente después de pasar el guard, es índices → constraints/FKs → tabla administrativa → columnas de resultado → columnas de suscripción. Nunca se sueltan `trial_fin`, `periodo_fin`, `checkout_id`, `payload_hash` ni datos de HU-004.

Con datos HU-005, el rollback de aplicación es un forward-fix compatible con el esquema aditivo. No se elimina historia, eventos, asociaciones ni fechas. Si la versión anterior no tolera las columnas nuevas, se deshabilita la entrada mensual y se publica una corrección hacia adelante; no se ejecuta un downgrade destructivo.

## 6. Estado, reloj y calendario

### 6.1. Guards de estado

| Operación | Precondición bajo lock | Escritura |
|---|---|---|
| Activar trial | asociación activa; estado `active`; `trial_inicio`, `trial_fin`, `periodo_inicio`, `periodo_fin` nulos; suscripción HU-004 existente | `estado = "trialing"`, `trial_inicio = now`, `trial_fin = now + 336 h` |
| Repetir activación | cualquier trial iniciado, fecha parcial o estado posterior | `409`, sin escritura |
| Convertir mensual | evento autenticado; tipo exacto; suscripción bloqueada `trialing`; fechas de trial consistentes; `now < trial_fin`; plan/monto/correlación coincidentes | `estado = "active"`, `periodo_inicio = now`, `periodo_fin = fin mensual`, evento mensual |
| Convertir en límite | `now >= trial_fin` | `409`, permanece `trialing`, sin evento mensual |
| Convertir desde `active` inicial | no existe trial elegible | `409`, sin escritura |
| Convertir un `active` convertido o estado HU-006 | transición no admitida por HU-005 | `409`, sin escritura |

No se materializa un estado `expired`; HU-006 queda responsable de remediar un trial expirado. No se implementa `past_due`, grace, `suspended`, `canceled_read_only`, `purged`, renovación o cualquier otro lifecycle.

### 6.2. Fuente de tiempo

`ClockProtocol.now()` es la única fuente del service y debe devolver un `datetime` consciente de zona. Un valor naive es error de programación y no se interpreta silenciosamente. Los instantes se normalizan a UTC para persistencia y serialización RFC 3339; las columnas son `DateTime(timezone=True)`/`TIMESTAMPTZ`.

El trial usa exactamente:

```text
trial_inicio = now
trial_fin = trial_inicio + timedelta(hours=336)
```

No se usa una aproximación de calendario ni `timedelta(days=30)`. La comparación de expiración es inclusiva: si `now == trial_fin`, el trial no puede convertirse.

### 6.3. Algoritmo mensual `America/La_Paz`

Para `periodo_inicio` consciente de zona:

1. Convertir `periodo_inicio` a `ZoneInfo("America/La_Paz")`.
2. Avanzar un mes calendario, incluyendo diciembre → enero del año siguiente.
3. Obtener el último día del mes destino con `calendar.monthrange(year, month)[1]`.
4. Usar `min(día_origen, último_día)`.
5. Construir la fecha destino con la misma hora, minuto, segundo y microsegundo local.
6. Convertir el resultado a UTC y persistirlo como `periodo_fin`.

Pseudoflujo:

```text
local = periodo_inicio.astimezone(ZoneInfo("America/La_Paz"))
(next_year, next_month) = siguiente_mes(local.year, local.month)
last_day = calendar.monthrange(next_year, next_month)[1]
local_end = datetime.combine(
    date(next_year, next_month, min(local.day, last_day)),
    local.timetz(),
)
periodo_fin = local_end.astimezone(UTC)
```

Casos obligatorios: día 31 hacia mes de 30, enero hacia febrero, febrero bisiesto y no bisiesto, diciembre hacia enero. La zona no se reemplaza por un offset fijo.

## 7. HMAC, parsing y compatibilidad de eventos

### 7.1. Contrato exacto

Se reutiliza `HMACWebhookSignatureVerifier` con:

```text
message = timestamp.encode("ascii") + b"." + raw_body
expected = HMAC-SHA256(secret, message)
valid = hmac.compare_digest(expected_hex, signature[3:])
```

Headers exactos:

```text
X-RoomForge-Webhook-Timestamp: <solo dígitos>
X-RoomForge-Webhook-Signature: v1=<64 hexadecimales minúsculos>
```

La tolerancia es `Settings.webhook_tolerance_seconds`, configurable por `BILLING_WEBHOOK_TOLERANCE_SECONDS`, con default de `300` segundos. Se rechaza solo cuando `abs(now_epoch - timestamp_epoch) > tolerance`; la igualdad se acepta. La ausencia del secreto produce `WebhookNotConfiguredError` y `503`.

El helper se invoca antes de cualquier lookup de tenant, suscripción o plan. Para conservar el replay aprobado fuera de ventana, la entrada usa el helper para autenticar formato y MAC contra el instante representado por el timestamp, y el service aplica la freshness contra el `now` actual para una clave nueva. El único read posterior al MAC y previo a la decisión de freshness es la clasificación técnica por `idempotency_key`, necesaria para distinguir replay de evento nuevo; nunca se consulta tenant/suscripción/plan antes de autenticar. Una clave nueva stale devuelve `401` antes de cualquier lookup de negocio o escritura. Un replay con firma válida puede devolver su resultado original fuera de la ventana de eventos nuevos.

Esta separación conserva la frontera criptográfica HU-004 y no agrega una segunda implementación HMAC. Si la revisión activa del helper no permite esta secuencia sin cambiar su contrato, apply debe detenerse y verificar una extensión mínima del mismo helper antes de continuar; no puede introducir una función criptográfica paralela.

### 7.2. Evento mensual

Después de autenticar los bytes, el parser acepta exactamente:

```json
{
  "event_type": "subscription.monthly.succeeded",
  "idempotency_key": "evt-monthly-0001",
  "subscription_id": "<uuid>",
  "plan_id": "<uuid>",
  "monto_bob": "449.00"
}
```

`extra="forbid"` rechaza `tenant_id`, `checkout_id` usado como autoridad, correo, cuotas, firma, payload anidado y cualquier otro campo. `subscription_id` es solo correlación; no autoriza tenant. `plan_id` y `monto_bob` se comparan contra los valores server-owned y nunca se asignan desde el evento.

JSON inválido, UUID inválido, monto no finito, campos faltantes o extra después de una firma válida producen `422` sin escritura. El `event_type` HU-004 `tenant.onboarding.succeeded` sigue su parser/servicio existente y no se mezcla con el resultado mensual. Un tipo reconocido pero incompatible con la ruta mensual se traduce a conflicto o validación según el branch, sin mutar.

### 7.3. Raw body y hash

`raw_body` se captura una sola vez y es la misma secuencia usada por el helper y `hashlib.sha256`. No se usa `json.dumps` para recalcular la firma ni el hash. El `payload_firmado` existente solo se persiste internamente si el contrato de `EventoFacturacion` lo exige; nunca se devuelve ni se registra. Un body no decodificable como UTF-8 después de una firma válida falla `422` antes de persistir.

## 8. Idempotencia, atomicidad y concurrencia

### 8.1. Registro persistente

Para un evento mensual nuevo se conserva:

- `idempotency_key` único y no nulo;
- `payload_hash = SHA-256(raw_body)`;
- `tipo = "subscription.monthly.succeeded"`;
- `suscripcion_id`;
- `estado = "procesado"`;
- `resultado_periodo_inicio` y `resultado_periodo_fin`, solo si son el delta ausente verificado;
- `payload_firmado` interno existente, sin proyección externa.

El hash es de bytes exactos: cambiar whitespace, orden JSON o cualquier campo produce otra huella. Una misma key con hash/tipo/correlación/datos incompatibles produce `409` y conserva el primer registro. Un evento HU-004 con `payload_hash NULL`, tipo distinto o resultado mensual ausente nunca se toma como replay mensual.

### 8.2. Transacción mensual

El método nuevo del repository es la única frontera de escritura mensual. Su secuencia lógica es:

```text
BEGIN
  buscar evento por idempotency_key
  si existe: confirmar tipo + hash + resultado; replay 200 o conflicto 409
  bloquear Suscripcion por subscription_id con FOR UPDATE
  volver a buscar evento por idempotency_key
  confirmar correlación, plan server-owned, monto, trialing y now < trial_fin
  calcular/recibir periodo_inicio y periodo_fin conscientes de zona
  actualizar suscripción y hacer flush
  insertar evento mensual y hacer flush
COMMIT
```

La asociación, suscripción y evento se deciden dentro de la misma transacción que gobierna la escritura. Si falla cualquier flush, FK, constraint o commit, se hace rollback completo; no queda conversión sin evento ni evento sin conversión. La actualización se flushea antes del evento para respetar la FK existente, pero solo hay un commit.

### 8.3. Carreras

- **Dos activaciones:** el lock de la suscripción y la revalidación bajo lock permiten como máximo un `trialing`; la otra solicitud devuelve `409` sin sobrescribir.
- **Dos keys para la misma suscripción:** el lock serializa. La segunda observa `active` y devuelve `409`, sin evento adicional.
- **Misma key en paralelo:** la unicidad PostgreSQL gobierna. La operación que pierde una carrera revierte su transacción, abre/usa una lectura limpia y confirma el registro comprometido por key. Solo si coinciden tipo mensual, hash y resultado devuelve replay `200`; si difieren devuelve `409`.
- **`IntegrityError` ajeno a unicidad:** no se clasifica como replay. Se traduce a fallo transaccional `500` después de rollback.
- **Bootstrap paralelo:** las constraints únicas y el lock de invitación/usuario permiten reconocer el vínculo ganador; nunca se elige silenciosamente otro candidato.

La recuperación no examina el texto de una excepción, no reutiliza una sesión en estado incierto sin rollback confirmado y no genera un segundo evento.

## 9. Contratos HTTP, proyecciones y errores

### 9.1. Bootstrap

`POST /api/v1/tenant/administrador/bootstrap`

- JWT requerido mediante `get_current_user`.
- Body ausente o `{}`; cualquier campo, incluido `tenant_id`, produce `422` por `extra="forbid"`.
- Creación: `201` con `tenant_id`, `administrador_id`, `activo: true`, `idempotente: false`.
- Repetición del mismo vínculo: `200` con los mismos identificadores e `idempotente: true`.
- Sin invitación consumida coincidente, asociación no elegible o candidatos ambiguos: `404 ADMIN_BOOTSTRAP_UNAVAILABLE` sanitizado.
- Asociación existente inactiva: `409 ADMIN_ASSOCIATION_INACTIVE` sin revelar más contexto.

No se devuelven invitación, correo completo, token, contraseña, roles ni candidatos.

### 9.2. Activación

`POST /api/v1/tenant/activar-prueba`

- JWT y asociación activa requeridos.
- Body ausente o vacío; `tenant_id` recibido no puede seleccionar nada y produce `422`.
- Éxito `200`:

```json
{
  "subscription_id": "<uuid>",
  "plan_id": "<uuid>",
  "estado": "trialing",
  "trial_inicio": "2026-09-04T15:00:00Z",
  "trial_fin": "2026-09-18T15:00:00Z",
  "periodo_inicio": null,
  "periodo_fin": null
}
```

- Asociación/suscripción no accesible: `404 TENANT_SUBSCRIPTION_UNAVAILABLE`.
- Trial iniciado, estado incompatible o fechas inconsistentes: `409 TRIAL_ALREADY_ACTIVATED` o `SUBSCRIPTION_STATE_CONFLICT`.
- Fallo transaccional: `500 SUBSCRIPTION_UPDATE_FAILED`.

### 9.3. Inspección

`GET /api/v1/tenant/suscripcion`

- JWT y asociación activa requeridos; sin query/body selector.
- Éxito `200` con exactamente: `subscription_id`, `plan_id`, `estado`, `trial_inicio`, `trial_fin`, `periodo_inicio`, `periodo_fin`.
- JWT inválido/ausente: `401` con el error genérico de HU-002.
- Asociación o suscripción no accesible: `404 TENANT_SUBSCRIPTION_UNAVAILABLE`.

No se incluyen `tenant_id`, payload, firma, secreto, monto, JWT, password, token, hashes sensibles, correo completo, datos administrativos completos ni datos de otro tenant.

### 9.4. Webhook y alias

`POST /api/v1/tenant/webhook` y `POST /api/v1/tenant/suscribir` deprecated

- `Content-Type` distinto de `application/json`: `415 UNSUPPORTED_MEDIA_TYPE`.
- Header HMAC ausente, duplicado, malformado, firma alterada, timestamp inválido o stale para una key nueva: `401 WEBHOOK_UNAUTHORIZED`.
- Secreto ausente: `503 WEBHOOK_NOT_CONFIGURED`.
- JSON/schema autenticado inválido: `422` sin escritura.
- Conversión mensual nueva: `201`:

```json
{
  "evento_id": "<uuid>",
  "subscription_id": "<uuid>",
  "estado": "active",
  "periodo_inicio": "2026-09-18T15:00:00Z",
  "periodo_fin": "2026-10-18T15:00:00Z",
  "idempotente": false
}
```

- Replay exacto autenticado, incluso fuera de la ventana de eventos nuevos: `200`, mismos IDs/fechas persistidos e `idempotente: true`.
- Key con bytes, tipo, correlación o resultado incompatibles: `409 IDEMPOTENCY_CONFLICT`.
- Suscripción initial `active`, trial expirado, active convertido, plan/monto/correlación incompatibles o estado HU-006: `409 SUBSCRIPTION_CONVERSION_CONFLICT`.
- Falla de persistencia: `500 SUBSCRIPTION_CONVERSION_FAILED`.

El handler de onboarding conserva `tenant.onboarding.succeeded`, su shape `WebhookResponse` y sus reglas. La documentación OpenAPI debe declarar ambas respuestas posibles sin forzar la respuesta mensual a la forma de onboarding.

### 9.5. No divulgación

Los errores se mapean por tipo de excepción a códigos y mensajes constantes; nunca se exponen `str(error)`, SQL, nombres de candidatos ni IDs de recursos no autorizados. Los logs, si existen, solo pueden registrar ruta, status, código estable, tipo de evento y un identificador irreversiblemente abreviado. Nunca registran raw body, `payload_firmado`, firma completa, secreto, JWT, passwords, tokens, hashes de tokens, hash completo de payload sensible, correo completo o valores de otro tenant.

## 10. Plan de pruebas y evidencia

La evidencia debe separar determinismo de infraestructura. Ningún fake se presentará como evidencia de PostgreSQL y ningún resultado se afirma en este diseño.

### 10.1. Único módulo enfocado

Se extenderá `tests/test_tenant_onboarding.py`, porque ya contiene reloj, firma, raw body, replay, rollback y regresión HU-004. No se creará una segunda suite tenant redundante ni se duplicarán helpers.

**Unit/fake/SQLite — evidencia limitada a reglas y contratos:**

- requests vacíos y `extra="forbid"`; body/query/evento con `tenant_id` nunca es autoridad;
- bootstrap desde invitación consumida, correo normalizado, repetición, ambigüedad, asociación inactiva y ausencia de leaks;
- activación con `trial_inicio`, diferencia exacta de 336 horas, segunda activación, fechas parciales y estados incompatibles;
- expiración exacta en `now == trial_fin`, conversión solo `trialing → active`, rechazo del `active` inicial y de estados HU-006;
- calendario `America/La_Paz`: día 31, meses de 30, febrero bisiesto/no bisiesto y preservación de hora/zona;
- proyección exacta y ausencia de campos sensibles;
- HMAC con bytes raw, fórmula, headers, comparación, tolerancia/borde, secreto ausente, autenticación antes del lookup de negocio y replay fuera de ventana;
- event type mensual exacto, campos extra, plan/monto server-owned, alias sin bypass, nuevo `201`, replay `200` y conflicto `409`;
- orden de servicio y rollback observado mediante fakes, identificado explícitamente como evidencia fake-only;
- regresión de `tenant.onboarding.succeeded`, `get_current_user` y paths HU-006 sin cambiar su alcance.

**SQLite/ORM:** puede apoyar mapeo, proyección y FKs simples, pero no prueba locks PostgreSQL, carreras reales, aislamiento ni semántica de migración de producción.

### 10.2. PostgreSQL y migración

Se requiere una fixture PostgreSQL real y sesiones/conexiones separadas para demostrar:

- upgrade desde el head HU-004 efectivo, columnas nullable, FKs, constraints e índices;
- preservación de tenants, planes y suscripciones initial `active`, sin trials/asociaciones/eventos sintéticos;
- activaciones y conversiones concurrentes sin duplicados;
- lock de suscripción y unicidad real de `idempotency_key`;
- carrera de la misma key con replay exacto y con payload distinto;
- rollback de fallo de actualización, inserción de evento o commit como unidad;
- replay basado en el resultado persistido y no en el estado actual;
- downgrade bloqueado con cualquier dato HU-005 y downgrade mecánico solo en una base descartable que cumpla el precondition de vacío.

La disponibilidad de PostgreSQL, la forma de levantar la fixture y la estrategia exacta de conexión no se inventan en diseño. Son verificación obligatoria de apply antes de marcar TRIANGULATE; si no existe infraestructura, se conserva un resultado pendiente/bloqueado y no se reemplaza por SQLite.

### 10.3. Calidad y evidencia operativa pendiente

Fases posteriores podrán ejecutar, desde la raíz del backend, los comandos configurados localmente:

```text
..\\.venv\\Scripts\\python.exe -m pytest tests -q
..\\.venv\\Scripts\\ruff.exe check app tests
..\\.venv\\Scripts\\pyright.exe app tests
..\\.venv\\Scripts\\python.exe -m alembic -c alembic.ini upgrade head
```

También deben registrar el resultado real de la fixture PostgreSQL y de la verificación de downgrade, sin presentar comandos previstos como evidencia. `CP-004.1`, `.2` y `.3` solo pueden dejar `not executed` por diseño; cambiar ese estado requiere evidencia ejecutada en fases posteriores.

## 11. Strict TDD, work units y presupuesto

La implementación debe respetar el orden estricto. Cada frontera se cierra antes de iniciar la siguiente; el diseño no ejecuta ni marca ninguna.

| Work unit | Fase | Contenido y frontera | Forecast |
|---|---|---|---:|
| `WU-005-TDD` | RED | Preflight de head/delta y tests fallidos de contrato, auth, estado, HMAC, concurrencia, migración y regresión. Sin código productivo HU-005. | 88 |
| `WU-005-DATA` | GREEN | Modelo, `tenant_administrator` y una migración aditiva tras confirmar head/delta. | 50 |
| `WU-005-CONTRACT` | GREEN | Requests strictos, evento mensual, proyecciones y respuestas. | 36 |
| `WU-005-RULES` | GREEN | Principal, bootstrap, guards, reloj, 336 horas y calendario. | 60 |
| `WU-005-POSTGRES` | GREEN | Repository, locks, transacción, resultado persistido y replay/carrera. | 78 |
| `WU-005-HTTP-HMAC` | GREEN | Router, auth dependency, raw body, dispatch HU-004 y alias firmado. | 27 |
| `WU-005-TRIANGULATE` | TRIANGULATE | PostgreSQL, migración, regresión y calidad; evidencia real separada de fakes. | 25 |
| `WU-005-REFACTOR` | REFACTOR | Simplificación mínima solo después de evidencia, sin cambio de contrato o guard. | 8 |
| **Total previsto** |  |  | **372** |
| **Reserva disponible** |  | No es autorización de alcance. | **28** |
| **Límite duro** |  | Si se supera, detener. | **400** |

La medición corresponde al worktree y common directory backend gobernantes. La reserva no habilita UI, refactors, nuevos eventos ni eliminación de guards. Si el diff real o el forecast de una work unit supera 400 líneas, `sdd-apply` debe detenerse antes de continuar y `ask-on-risk` debe solicitar una decisión explícita para reducir o dividir el slice. No se eleva el límite ni se recortan silenciosamente seguridad, idempotencia, atomicidad o evidencia PostgreSQL.

## 12. Resolución de las pruebas legacy inseguras

La prueba actual `test_hu005_hu006_routes_and_behavior_remain_unchanged` espera exactamente la conducta que HU-005 debe retirar: pasa `tenant_id`, cambia `plan_id` desde el cliente, usa `suscribirse` directo, persiste con dos commits y suma 30 días. Hacerla pasar mantendría el bypass y contradice R-01, R-02, R-06 y R-07.

La resolución en apply será acotada y explícita:

1. Reemplazar esa expectativa por pruebas del contrato seguro en el mismo módulo tenant: requests sin autoridad, JWT/asociación, evento HMAC mensual, estado y calendario.
2. Verificar que `/suscribir` sigue publicado como alias deprecated, pero sin headers/body mensual responde error sanitizado y no escribe; con evento válido delega exactamente al pipeline de `/webhook`.
3. Mantener pruebas separadas de HU-006 para `cambiar_plan`, cancelación y purga, usando su superficie existente y sin convertirla en una autorización de HU-005. Los estados futuros siguen siendo almacenables.
4. Retirar solo fixtures/imports/assertions que describen el bypass; no hacer refactors generales ni agregar una flag de compatibilidad insegura.
5. Conservar las pruebas HU-004 de onboarding, replay y HMAC, ajustando únicamente tipos/proyecciones si el dispatch compartido lo requiere.

El resultado esperado no es que el test legacy siga verde sin cambios; es que exprese la compatibilidad correcta: paths heredados y onboarding permanecen, mientras la antigua autoridad de cliente falla cerrado.

## 13. Rollout, rollback y observabilidad

### Rollout

1. Confirmar worktree, common directory, head Alembic efectivo, delta HU-004, helper HMAC y fixture de PostgreSQL.
2. Ejecutar RED y validar que las pruebas fallan por ausencia de la capacidad, sin escribir código productivo antes de la frontera.
3. Aplicar el único upgrade aditivo sobre fixture HU-004 y comprobar nulabilidad/preservación.
4. Implementar GREEN manteniendo la ruta onboarding y el catálogo intactos.
5. Ejecutar TRIANGULATE separando fake/unit, PostgreSQL, migración y calidad.
6. Habilitar el flujo mensual únicamente con `BILLING_WEBHOOK_SECRET` configurado y el event type exacto; mantener el alias deprecated bajo la misma autenticación.
7. Revisar status/códigos de conflicto, replay y rollback antes de una ampliación operativa.

No se agrega un proveedor de cobro, un worker, un outbox ni una notificación para este rollout.

### Rollback

- Ante un defecto mensual, detener/deshabilitar la entrada mensual según la política operativa del backend, sin borrar eventos ni deshabilitar innecesariamente inspección/bootstrap.
- Revertir aplicación solo hacia una versión compatible con columnas aditivas.
- En una base con datos HU-005, conservar esquema y usar forward-fix; nunca ejecutar el downgrade destructivo.
- Mantener el evento y su resultado para que una repetición firmada pueda recuperar `200` en vez de duplicar efectos.
- No modificar el root, el gitlink, la rama ni `docs/diagramas/Diagrama1.eapx` como mecanismo de rollback.

### Observabilidad segura

Solo se permiten códigos agregados: bootstrap no disponible, activación exitosa/conflictiva, webhook no autorizado/no configurado, conversión, replay, conflicto de idempotencia, rollback y latencia. Se pueden incluir route, status, event type y referencias irreversiblemente abreviadas; no valores sensibles.

## 14. Riesgos, alternativas rechazadas y dependencias

### Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Head real distinto de `0004` o HU-004 incompleto | Preflight obligatorio; una sola migración solo después de confirmar head/delta; detener si falta dependencia. |
| Bootstrap se convierte en membership/RBAC | Tabla dedicada, FK a invitación consumida, body vacío y ningún rol/permiso. |
| Conversión directa de `active` inicial | Guard exclusivo `trialing` con fechas consistentes y lock. |
| Alias legacy reintroduce bypass | Un único handler HMAC/parser/service; body viejo falla cerrado. |
| Replay fuera de ventana mal autenticado | MAC/formato antes de lookup; replay solo con key/hash/tipo/resultado confirmados; freshness solo se omite para replay firmado válido. |
| Carrera de key o commits parciales | Unicidad PostgreSQL, lock, relectura post-rollback y una transacción. |
| Resultado de replay cambia por HU-006 | Fechas/IDs de resultado mensual persistidos en el evento, solo si son delta ausente. |
| Período incorrecto en fin de mes | `ZoneInfo`, `monthrange`, reloj inyectado y casos de febrero/31. |
| Check de estado rompe HU-006 | No agregar check cerrado; guards en servicio/repository. |
| Exceso de 400 líneas | Forecast 372, una sola suite y reutilización HU-004; detener apply y pedir decisión si excede. |
| PostgreSQL no disponible | Reportar evidencia tipada pendiente/bloqueada; no sustituir locks/concurrencia/migración por fake. |

### Alternativas rechazadas

- **Aceptar `tenant_id`/`plan_id` del body:** rechazada porque permite suplantación y cambio de plan.
- **Usar JWT sin asociación persistente:** rechazada porque no prueba la procedencia de la invitación consumida ni aísla el tenant.
- **Conservar `suscribirse` legacy y proteger solo el webhook:** rechazada porque deja una vía de bypass.
- **Crear otro verificador HMAC o firmar JSON serializado:** rechazada porque rompe raw bytes y la frontera HU-004.
- **Sumar 30 días:** rechazada por la regla de calendario local y fin de mes.
- **Guardar evento y suscripción con commits independientes:** rechazada por estados parciales.
- **Crear una tabla de eventos mensual paralela:** rechazada porque HU-004 ya provee la auditoría e idempotencia base.
- **Agregar un `CHECK` con solo estados HU-005:** rechazada por compatibilidad con HU-006.
- **Downgrade destructivo con datos:** rechazado por pérdida de historia; se requiere forward-fix.

### Dependencias y verificaciones diferidas

Cada deferment tiene una acción obligatoria de apply:

| Punto no demostrable solo con el baseline | Verificación obligatoria en apply |
|---|---|
| Head Alembic efectivo y ausencia de ramas | Leer la cadena activa y confirmar un único head antes de crear la revisión; no crearla si falla. |
| Delta exacto de `EventoFacturacion` | Inspeccionar modelo/revisiones HU-004 y agregar solo `resultado_periodo_inicio`/`resultado_periodo_fin` si faltan. |
| Disponibilidad/configuración de PostgreSQL | Preparar la fixture real y ejecutar casos de lock, unicidad, rollback y migración; si no está disponible, bloquear TRIANGULATE. |
| Disponibilidad de `ZoneInfo("America/La_Paz")` | Resolver la zona en el entorno de tests antes de implementar; no sustituirla por offset fijo. |
| Forma exacta de la respuesta OpenAPI union | Regenerar/inspeccionar OpenAPI en apply y asegurar que HU-004 y monthly tengan shapes separadas. |
| API exacta del helper HMAC en la revisión activa | Confirmar export, errores, headers y secuencia de freshness; extender solo el mismo helper si fuera imprescindible. |
| Registro de modelos en metadata Alembic | Confirmar que el modelo nuevo es visible para la metadata importada por `alembic/env.py`, sin editar módulos ajenos salvo el mínimo necesario. |

Estas verificaciones no autorizan roles, billing, lifecycle, UI ni cambios de producto.

## 15. No-goals y trazabilidad final

Fuera de este diseño quedan React/Web, Flutter, navegación, copy, clientes generados, pagos reales, invoices, planes/precios/cuotas nuevos, enforcement de cuotas, upgrade/downgrade de plan, renovación, `past_due`, grace, suspensión, cancelación, purge, notificaciones, outbox, workers, S3/SQS, RBAC, memberships generales, invitaciones de agentes, endpoint público de historial/eventos, refactors ajenos, commits, pushes, cambios de rama, cleanup y cambios en `docs/diagramas/Diagrama1.eapx`.

| Requisito | Decisión de diseño | Evidencia posterior |
|---|---|---|
| R-01 | `get_current_user` + `tenant_administrator` desde invitación consumida | JWT, bootstrap, aislamiento y no enumeración |
| R-02 | trial único, `336` horas, fechas iniciales nulas | reloj, lock y conflicto sin mutación |
| R-03 | expiración `now >= trial_fin`; solo `trialing → active` | borde exacto y estados HU-006 representables |
| R-04 | endpoint sin selector y proyección mínima | OpenAPI/respuestas sin sensibles |
| R-05 | HMAC HU-004 sobre raw bytes | headers, fórmula, tolerancia y orden de autenticación |
| R-06 | plan server-owned y calendario `America/La_Paz` | monto/correlación y casos de fin de mes |
| R-07 | key/hash/resultado, lock, una transacción | PostgreSQL, replay, carrera y rollback |
| R-08 | `201/200/401/404/409/422/503/500` según contrato | casos HTTP y auditoría |
| R-09 | upgrade aditivo y downgrade fail-closed | migración desde HU-004 y forward-fix |
| R-10 | no divulgación y alcance cerrado | inspección de respuestas/logs y regresión |

En esta fase no se ejecutaron código, tests, migraciones, comandos Alembic, lint, typecheck, revisión, commits, pushes, cambios de rama ni operaciones de delivery. **CP-004 permanece explícitamente `not executed`.**
