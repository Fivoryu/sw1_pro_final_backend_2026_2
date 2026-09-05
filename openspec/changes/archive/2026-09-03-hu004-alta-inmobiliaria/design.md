# Diseño técnico — Alta de inmobiliaria (HU-004)

- **Cambio:** `hu004-alta-inmobiliaria`
- **HU/PB/CP:** HU-004 / PB-004 / CP-003
- **Repositorio:** RoomForge Backend independiente
- **Slice:** backend/API; patrón `router → service → repository`
- **Estado:** diseño listo para la fase de tareas; no declara implementación ni ejecución
- **Idioma:** español profesional y neutral
- **Presupuesto:** máximo 600 líneas modificadas
- **Delivery:** `ask-on-risk`; cadena `stacked-to-main`

## 1. Decisión ejecutiva

Se reemplaza la operación única de alta por cuatro superficies separadas: catálogo server-owned, checkout simulado, webhook firmado y consumo de activación. El checkout solo persiste una intención en demo; únicamente el webhook HMAC autenticado puede aprovisionar. La provisión crea tenant, suscripción inicial `active`, invitación pendiente y evento dentro de una transacción, junto con el estado `procesado` del checkout.

La autoridad comercial y de identidad de alta proviene de la base: el evento solo referencia `checkout_id`, `plan_id`, `monto_bob` y su clave. Nombre y correo se cargan del checkout; precio y cuotas, del plan activo. La idempotencia usa la unicidad persistente, locks PostgreSQL y `payload_hash` de los bytes recibidos. El token de activación se genera en memoria, se guarda como SHA-256, expira y se consume una sola vez. El notifier recibe el token únicamente después del commit.

No se implementan UI, pagos/correo reales, identidad global, memberships/RBAC, trial de HU-005, cambios/cancelación/purga de HU-006 ni el rollout productivo del checkout público.

## 2. Contrato HTTP cerrado

Prefijo existente: `/api/v1/tenant`. `main.py` ya registra el router y no requiere otra inclusión.

### 2.1. Catálogo

`GET /api/v1/tenant/plans` responde `200` con exactamente estos planes, en este orden:

| `codigo` | `nombre` | `precio_bob` | `max_agents` | almacenamiento | inmuebles | reconstrucciones/mes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `basico` | Básico | `199.00` BOB | 5 | 50 GB | 5 | 10 |
| `profesional` | Profesional | `449.00` BOB | 15 | 200 GB | 20 | 40 |
| `empresarial` | Empresarial | `899.00` BOB | 50 | 1.000 GB | 100 | 150 |

`max_agents` cuenta agentes y excluye al administrador inicial. La respuesta proyecta `precio_bob` como string decimal de dos posiciones y `moneda: "BOB"`; no expone `activo` como autoridad del cliente.

Si falta cualquiera de los tres planes o sus datos server-owned no son utilizables, la respuesta es `503 PLAN_CATALOG_UNAVAILABLE` con `{"code":"PLAN_CATALOG_UNAVAILABLE","detail":"El catálogo de planes no está disponible"}` y nunca una lista parcial. Una referencia de plan inexistente o inactivo durante checkout responde `404 PLAN_NOT_AVAILABLE` con `{"code":"PLAN_NOT_AVAILABLE","detail":"El plan no está disponible"}`, sin escrituras.

### 2.2. Checkout simulado

`POST /api/v1/tenant/checkout` solo se publica como operación pública del entorno `demo`; la política `CheckoutAccessPolicy` debe denegar su exposición fuera de demo antes de la creación de una intención. No se habilita el rollout productivo sin decisión posterior de producto sobre autenticación y controles operativos.

Request permitido:

```json
{
  "plan_id": "<uuid>",
  "nombre_empresa": "Inmobiliaria Ejemplo",
  "correo_admin": "admin@example.com"
}
```

La entrada usa `extra="forbid"`. No se aceptan `tenant_id`, precio, moneda, cuotas, `payload_firmado` ni otros datos comerciales como autoridad. El servicio hace `strip()` y `lower()` del correo y valida que nombre y correo queden utilizables.

Respuesta exitosa: `201`.

```json
{
  "checkout_id": "<uuid>",
  "estado": "confirmado",
  "simulado": true,
  "plan": {
    "plan_id": "<uuid>",
    "codigo": "basico",
    "nombre": "Básico",
    "precio_bob": "199.00",
    "moneda": "BOB",
    "max_agents": 5,
    "cuota_almacenamiento_gb": 50,
    "cuota_inmuebles": 5,
    "cuota_reconstrucciones_mes": 10
  }
}
```

El checkout crea solo `checkout_intencion`; no crea tenant, suscripción, invitación, evento ni activación.

### 2.3. Webhook y respuestas de error

`POST /api/v1/tenant/webhook` recibe bytes crudos y no declara un parámetro Pydantic de body que provoque una deserialización anterior a la autenticación. El request debe tener:

```text
Content-Type: application/json
X-RoomForge-Webhook-Timestamp: <epoch-seconds>
X-RoomForge-Webhook-Signature: v1=<64 lowercase hex characters>
```

Payload autenticado y con campos extra prohibidos:

```json
{
  "event_type": "tenant.onboarding.succeeded",
  "idempotency_key": "evt-demo-0001",
  "checkout_id": "<uuid>",
  "plan_id": "<uuid>",
  "monto_bob": "199.00"
}
```

No se aceptan `tenant_id`, nombre, correo ni cuotas en el webhook. Respuesta de evento nuevo: `201`.

```json
{
  "evento_id": "<uuid>",
  "tenant_id": "<uuid>",
  "suscripcion_id": "<uuid>",
  "estado_tenant": "activo",
  "estado_evento": "procesado",
  "activacion_admin": "pendiente",
  "idempotente": false
}
```

Un replay autenticado con los mismos bytes y la misma clave responde `200`, devuelve los mismos identificadores/estados, marca `idempotente: true`, no duplica recursos y no vuelve a notificar. Esta recuperación exacta sigue siendo válida aunque el timestamp esté fuera de la ventana; un evento nuevo sí debe estar dentro de ella.

| Situación | HTTP y código | Cuerpo sanitizado | Regla observable |
| --- | ---: | --- | --- |
| Secreto HMAC ausente | `503 WEBHOOK_NOT_CONFIGURED` | `{"code":"WEBHOOK_NOT_CONFIGURED","detail":"Webhook no disponible"}` | Falla cerrada antes de cualquier efecto. |
| Header ausente/múltiple/malformado, firma incorrecta o timestamp inválido/stale para evento nuevo | `401 WEBHOOK_UNAUTHORIZED` | `{"code":"WEBHOOK_UNAUTHORIZED","detail":"Evento no autorizado"}` | No busca ni modifica onboarding. |
| JSON inválido o esquema inválido después de autenticar | `422` | `detail` de validación sin body ni secretos | No persiste. |
| Checkout inexistente, no confirmado o plan no disponible en evento | `409 CHECKOUT_NOT_AVAILABLE` | `{"code":"CHECKOUT_NOT_AVAILABLE","detail":"El checkout no está disponible"}` | No crea recursos. |
| `checkout_id`, `plan_id` o `monto_bob` no coincide con la fuente server-owned | `409 CHECKOUT_MISMATCH` | `{"code":"CHECKOUT_MISMATCH","detail":"Los datos del evento no coinciden con el checkout"}` | No crea recursos parciales. |
| Misma clave con hash incompatible o evento legacy sin hash verificable | `409 IDEMPOTENCY_CONFLICT` | `{"code":"IDEMPOTENCY_CONFLICT","detail":"La clave de idempotencia ya fue utilizada con otros datos"}` | Conserva el resultado previo; nunca presume idempotencia. |
| Checkout ya procesado por otra clave | `409 CHECKOUT_ALREADY_PROVISIONED` | `{"code":"CHECKOUT_ALREADY_PROVISIONED","detail":"El checkout ya fue procesado"}` | Conserva el alta original. |
| Error de persistencia, constraint, FK o rollback | `500 ONBOARDING_NOT_PROVISIONED` | `{"code":"ONBOARDING_NOT_PROVISIONED","detail":"No se pudo completar el alta"}` | La transacción deja cero efectos parciales. |

Los cuerpos de error siguen `{ "code": "...", "detail": "..." }` con mensajes fijos y sanitizados. Los errores no incluyen valores recibidos, SQL, secretos, firmas, body ni tokens.

### 2.4. Activación

`POST /api/v1/tenant/activacion/consumir`

```json
{"token":"<token crudo recibido por el canal controlado>"}
```

Un token vigente y pendiente responde `200`:

```json
{"tenant_id":"<uuid>","estado":"consumida"}
```

Un token vacío/malformado produce `422`. Un token desconocido, expirado o ya consumido produce `410 ACTIVATION_UNAVAILABLE` con el mismo mensaje genérico para no revelar estados. Nunca se devuelve el token ni se crea contraseña, usuario global, membership o rol.

## 3. Mapa concreto de archivos

| Archivo | Cambio de diseño | Responsabilidad y límite |
| --- | --- | --- |
| `app/modules/tenant/catalog.py` | Nuevo | Constantes server-owned y orden canónico de los tres planes. |
| `app/modules/tenant/models.py` | Extender | `Plan.codigo/max_agents`, `CheckoutIntent`, `Invitacion.consumido_en`, `EventoFacturacion.checkout_id/payload_hash`; sin identidad/RBAC. |
| `app/modules/tenant/schemas.py` | Extender | Requests/responses HU-004, UUID, correo, Decimal y `extra="forbid"`; conservar esquemas HU-005/HU-006. |
| `app/modules/tenant/signatures.py` | Nuevo | HMAC-SHA256, timestamp y comparación constante; no persiste ni loguea. |
| `app/modules/tenant/ports.py` | Nuevo | `WebhookSignatureVerifier`, `ActivationNotifier`, `FirstAdminIdentityHook`, `CheckoutAccessPolicy` y seams de reloj. |
| `app/modules/tenant/service.py` | Extender | Normalización, política, parseo autenticado, correlación server-owned, comandos y proyección de respuestas. No conoce SQL ni `IntegrityError`. |
| `app/modules/tenant/repository.py` | Extender | Catálogo, checkout, transacción de provisión, `FOR UPDATE`, constraints y recuperación tras colisión concurrente. No decide HTTP. |
| `app/modules/tenant/router.py` | Ajustar | Agregar las cuatro rutas HU-004, leer body una sola vez, dependencias y mapeo de excepciones. No consulta SQL ni contiene reglas. Retirar `/alta` como frontera de aprovisionamiento. |
| `app/core/config.py` | Extender | `BILLING_WEBHOOK_SECRET: str | None`, tolerancia default 300 s, TTL default 7 días y`APP_ENV`; sin defaults secretos. |
| `alembic/env.py` | Ajustar | Importar `CheckoutIntent` para completar `Base.metadata`; mantener entidades existentes. |
| `alembic/versions/0004_hu004_onboarding.py` | Nuevo | Migración aditiva posterior a `0003`, seed seguro y downgrade protegido. |
| `tests/test_tenant_onboarding.py` | Nuevo | Contrato, servicio, fakes, rollback, concurrencia, activación, migración y regresión. |

`app/main.py` y `app/core/clock.py` se reutilizan sin cambio esperado. Las rutas de HU-005/HU-006 permanecen registradas y se toca su código solo si una adaptación mínima es indispensable, con regresión explícita.

## 4. Modelo de datos y tipos

### 4.1. Tipos y autoridad

- Todos los IDs de dominio y referencias HTTP son `UUID`; el servidor genera con `uuid4()` los IDs de checkout, tenant, suscripción, invitación y evento.
- Los UUID de seeds son constantes determinísticas por código, nunca nuevos en cada upgrade.
- `Plan.precio_bob` cambia su anotación Python de `float` a `Decimal`, conservando `NUMERIC(10,2)`.
- `precio_bob` se serializa como string `^[0-9]+\.[0-9]{2}$`; `monto_bob` se parsea y cuantiza a `Decimal("0.01")` antes de comparar.
- El administrador no consume `max_agents`; el contador no se crea ni se incrementa en HU-004.

### 4.2. Plan

Se conservan las columnas actuales y se agregan:

| Columna | Tipo/restricción | Decisión |
| --- | --- | --- |
| `codigo` | `VARCHAR(20) NULL` | Nullable para no romper filas legacy; valores HU-004: `basico`, `profesional`, `empresarial`. |
| `max_agents` | `INTEGER NULL` | Nullable para legacy; obligatorio y exacto para los tres planes contractuales. |
| `precio_bob` | `NUMERIC(10,2)` mapeado a `Decimal` | Fuente exclusiva del precio. |

El catálogo filtra `activo = true` y los tres códigos aprobados. Un plan legacy activo sin código no se expone ni se puede contratar en HU-004.

### 4.3. Checkout e invitación

`checkout_intencion` contiene:

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | UUID PK | Referencia opaca del consumidor. |
| `plan_id` | UUID FK `plan.id` | Plan activo validado al crear checkout. |
| `nombre_empresa` | `VARCHAR(120)` | Valor normalizado y validado. |
| `correo_admin` | `VARCHAR(255)` | `strip().lower()`, sin token ni password. |
| `estado` | `VARCHAR(20)` | `confirmado` o `procesado`. |
| `creado_en` | `TIMESTAMPTZ` | Reloj inyectable/UTC. |

No se persiste precio enviado por cliente: se consulta el plan. El cambio a `procesado` ocurre dentro de la transacción de onboarding.

`Invitacion.token_unico` conserva su nombre físico y su unicidad por compatibilidad con `0003`, pero su semántica es `token_hash`: SHA-256 hexadecimal del token aleatorio. Se agrega `consumido_en TIMESTAMPTZ NULL`; los estados HU-004 son `pendiente` y `consumida`. `expira_en` se fija a `now + 7 días` por configuración, con igualdad al vencimiento considerada expirada.

### 4.4. Evento

`EventoFacturacion` conserva `suscripcion_id`, `tipo`, `payload_firmado`, `idempotency_key` único y `estado`, y agrega:

- `checkout_id UUID NULL` con FK a `checkout_intencion.id`;
- `payload_hash CHAR(64) NULL`, SHA-256 de los bytes crudos.

Los eventos HU-004 guardan `checkout_id`, `payload_hash`, clave y estado `procesado`. `payload_hash` es la autoridad de igualdad; `payload_firmado` solo satisface la columna legacy con la representación UTF-8 del JSON autenticado. Ninguno de los dos se expone o loguea.

Se crea unicidad parcial de `evento_facturacion.checkout_id` cuando no es nulo y se conserva la unicidad de `idempotency_key`. Un evento legacy con `payload_hash IS NULL` nunca se adopta como replay HU-004.

## 5. Firma, autenticidad y orden de validación

La firma se calcula exactamente así, usando el secreto UTF-8:

```text
message = ASCII(timestamp) + b"." + raw_body
signature = HMAC-SHA256(BILLING_WEBHOOK_SECRET, message)
header = "v1=" + lowercase_hex(signature)
```

`Request.body()` se lee una sola vez. No se reserializa, ordena, normaliza ni vuelve a codificar JSON para verificar. El flujo es:

1. Resolver configuración; si falta `BILLING_WEBHOOK_SECRET`, responder `503 WEBHOOK_NOT_CONFIGURED` sin efectos.
2. Extraer exactamente un timestamp y una firma; validar forma decimal, prefijo `v1=` y 64 hexadecimales lowercase.
3. Calcular HMAC sobre timestamp y bytes crudos y decidir con `hmac.compare_digest`; fallar con `401 WEBHOOK_UNAUTHORIZED` si no coincide.
4. Calcular `payload_hash` y validar el JSON autenticado con `model_validate_json`, UUID, Decimal, `event_type` y campos extra prohibidos. Un error aquí es `422`, sin persistencia.
5. Buscar la clave solo después de autenticar y validar la forma. Si existe: hash igual devuelve resultado original; hash distinto o hash nulo legacy devuelve `409 IDEMPOTENCY_CONFLICT`.
6. Para una clave nueva, exigir `abs(now_epoch - timestamp) <= 300`; un timestamp futuro o atrasado fuera de ventana devuelve `401`. El límite exacto de 300 segundos es válido.
7. Validar checkout confirmado, plan activo aprobado y coincidencia de `checkout_id`, `plan_id` y `monto_bob`; mapear a los `409` definidos.
8. Delegar el comando al repositorio para la transacción atómica.
9. Tras un commit exitoso, notificar el token por el puerto controlado y devolver `201`. Una falla del notifier no deshace el alta confirmada ni entrega el token por la API; la falta de outbox/reintento durable queda fuera de alcance.

El router conoce headers y `Request`; el servicio recibe bytes, valores ya extraídos, reloj y verifier. Así se preserva `router → service → repository` y la firma se verifica antes de cualquier efecto de negocio.

## 6. Flujo transaccional e idempotencia

### 6.1. Checkout

El servicio obtiene un plan aprobado, normaliza datos y ordena al repositorio insertar una sola `CheckoutIntent`. El repositorio hace `flush` y `commit`; si falla, revierte la intención. No existe ninguna operación de provisión implícita en este camino.

### 6.2. Provisión atómica

`TenantRepository.provision_onboarding(command)` es la única operación de escritura del alta:

```text
BEGIN
  SELECT evento_facturacion BY idempotency_key FOR UPDATE
  si existe: comparar payload_hash y recuperar resultado o conflicto
  SELECT checkout_intencion BY id FOR UPDATE
  validar estado confirmado y plan asociado
  SELECT evento_facturacion BY checkout_id
  INSERT tenant
  INSERT suscripcion (estado = active, plan_id server-owned)
  INSERT invitacion (token_hash, correo del checkout, pendiente, expira_en)
  INSERT evento_facturacion (checkout_id, payload_hash, key, payload, procesado)
  UPDATE checkout_intencion SET estado = procesado
COMMIT
```

Los IDs y el token se generan en memoria antes del `flush`; nunca se genera el token en el repositorio. Nombre/correo vienen exclusivamente del checkout. Precio/cuotas vienen exclusivamente del plan. La suscripción inicial es `active`, con `trial_fin = NULL`, y no ejecuta HU-005.

Cualquier error de FK, constraint o persistencia hace rollback de la sesión y se traduce a `500 ONBOARDING_NOT_PROVISIONED`; no se convierte genéricamente toda `IntegrityError` en duplicado.

### 6.3. Carrera de reintentos

- **Misma clave, mismos bytes, secuencial:** comparar `payload_hash`, cargar `evento → suscripción → tenant` y devolver resultado original con `200`; no regenerar token ni llamar notifier.
- **Misma clave, mismos bytes, concurrente:** la unicidad de `idempotency_key` hace esperar al segundo inserto. Si el primero confirma, el segundo ejecuta `rollback()` para salir de la transacción abortada y realiza una lectura limpia; devuelve el resultado original. Si el primero revierte, el segundo puede ganar la única provisión.
- **Misma clave, bytes distintos:** después de HMAC, `payload_hash` distinto produce `409 IDEMPOTENCY_CONFLICT` y no modifica el original.
- **Checkout con otra clave:** `FOR UPDATE` sobre checkout y la unicidad parcial de `checkout_id` impiden una segunda provisión; el resultado es `409 CHECKOUT_ALREADY_PROVISIONED`.
- **Falla intermedia:** como evento y estado del checkout están en la misma transacción, no queda un evento procesado ni un recurso parcial.

La recuperación tras una colisión no reutiliza la sesión abortada: hace rollback, abre una lectura limpia y solo acepta el resultado si la fila persistida tiene hash compatible y estado procesado.

## 7. Activación y puertos

El servicio calcula `sha256(token.encode("utf-8")).hexdigest()` y retiene el token crudo solo hasta el commit. El consumo usa una actualización condicional:

```sql
UPDATE invitacion
SET estado = 'consumida', consumido_en = :now
WHERE token_unico = :token_hash
  AND estado = 'pendiente'
  AND expira_en > :now
RETURNING tenant_id, correo
```

La operación se confirma en su propia transacción. Si no retorna fila, responde `410 ACTIVATION_UNAVAILABLE`. Dos consumos concurrentes compiten sobre la misma fila y solo uno transforma `pendiente` en `consumida`. El token crudo nunca se compara con persistencia, respuesta o logs; si se verifica un hash recuperado, se usa comparación constante.

Se definen seams pequeños:

```text
ClockProtocol.now() -> aware UTC datetime
WebhookSignatureVerifier.verify(raw_body, timestamp, signature, now) -> None
ActivationNotifier.deliver(tenant_id, email, token, expires_at) -> None
FirstAdminIdentityHook.on_activation_consumed(tenant_id, email) -> None
CheckoutAccessPolicy.authorize(actor) -> None
```

`FakeClock`, `FakeSignatureVerifier`, `FakeTenantRepository`, `RecordingActivationNotifier` y `NullFirstAdminIdentityHook` se inyectan con `app.dependency_overrides`. El notifier de prueba conserva el token solo en memoria para verificar que la entrega ocurre después del commit. El hook nulo no crea `usuario_global`, membership ni RBAC.

## 8. Migración `0003 → 0004`, seed y downgrade

`0004_hu004_onboarding.py` usa `down_revision = "0003"` y es aditiva:

1. Agrega `plan.codigo` y `plan.max_agents` nullable.
2. Crea `checkout_intencion` con FK a `plan`.
3. Agrega `invitacion.consumido_en`.
4. Agrega `evento_facturacion.checkout_id` y `payload_hash`, ambos nullable.
5. Crea unicidad de código de plan y unicidad parcial de checkout no nulo.
6. Ejecuta seed reproducible de los tres códigos.

El seed usa una UUID estable y el código como clave natural. Para cada plan: si existe exactamente una fila con código, verifica nombre, precio, cuotas, `max_agents` y `activo`; si existe exactamente una fila con nombre y todos los valores aprobados, la adopta agregando código/`max_agents`; si hay colisión, duplicidad o discrepancia, aborta con error explícito; si no existe candidata, inserta. Nunca sobrescribe datos comerciales legacy silenciosamente. Filas no relacionadas se conservan y no se exponen.

El downgrade está protegido: debe detenerse si existen filas en `checkout_intencion`, si algún evento HU-004 tiene `checkout_id`/`payload_hash` no nulos o si alguna invitación tiene `consumido_en`. Solo en una base descartable sin datos HU-004 puede eliminar, en orden inverso, índices, columnas y tabla de intención; no borra tenants, suscripciones, invitaciones ni eventos. En producción se deshabilita el webhook y se prefiere forward-fix, nunca un downgrade destructivo automático.

## 9. TDD, pruebas y gates

Strict TDD queda activo. La secuencia obligatoria es **RED → GREEN → TRIANGULATE → REFACTOR**:

- **RED:** escribir primero fixtures, fakes y pruebas de contrato para catálogo, checkout, firma, errores, webhook, rollback, idempotencia, concurrencia, activación, seed legacy y downgrade.
- **GREEN:** implementar solo lo necesario en los archivos del mapa, manteniendo el patrón de capas.
- **TRIANGULATE:** comparar cada resultado con spec/diseño y agregar evidencia de PostgreSQL real para locks, constraints, rollback, seed y consumo concurrente cuando haya base disponible.
- **REFACTOR:** eliminar duplicación, revisar seguridad/logs/OpenAPI y confirmar que HU-005/HU-006 conservan rutas y comportamiento.

La concurrencia fake usa `RLock` y una barrera para modelar reintentos; no sustituye la prueba PostgreSQL real. La evidencia debe distinguir explícitamente fake de PostgreSQL. Deben cubrirse, como mínimo:

- los tres planes exactos, Decimal/string BOB y `max_agents` sin administrador;
- plan inválido/inactivo `404`, catálogo incompleto `503` y cero escrituras;
- checkout `201`, estado confirmado y ausencia de recursos de alta;
- campos de autoridad rechazados `422`;
- firma sobre bytes exactos, comparación constante, secreto ausente `503`, firma alterada/inválida `401` y límite temporal;
- JSON autenticado inválido `422` y ninguna escritura;
- webhook nuevo `201`, replay exacto fuera de ventana `200`, conflictos de correlación `409` y errores de persistencia `500`;
- misma clave con hash distinto o evento legacy sin hash `409 IDEMPOTENCY_CONFLICT`;
- reintentos concurrentes sin duplicados y checkout procesado con otra clave `409 CHECKOUT_ALREADY_PROVISIONED`;
- hash/TTL/notifier posterior a commit, consumo único y `410 ACTIVATION_UNAVAILABLE`;
- seed idempotente, adopción legacy segura, discrepancia abortada y downgrade bloqueado con datos;
- regresión de rutas y comportamiento de HU-005/HU-006.

OpenAPI se inspecciona desde `app.main`: deben aparecer exactamente las cuatro nuevas superficies, cuerpos/respuestas documentados y ningún campo sensible. Los gates futuros, no ejecutados en esta fase, son:

```text
..\.venv\Scripts\python.exe -m pytest tests -q
..\.venv\Scripts\python.exe -m ruff check app tests
..\.venv\Scripts\pyright.exe app tests
..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

La verificación de migración debe cubrir upgrade desde `0001`/`0003`, columnas, FK, índices, seeds, fixture legacy, no destrucción y downgrade controlado. `CP-003` permanece `not executed` hasta contar con evidencia real.

## 10. Plan de delivery, rollout y rollback

El pronóstico consolidado es **465–580 líneas modificadas**: riesgo alto respecto de 400 y dentro del máximo de 600 solo con disciplina de alcance. Como supera 400, se recomiendan exactamente dos unidades revisables; no se inventa una excepción.

1. **PR 1 hacia `main`:** tests RED y contratos de catálogo/checkout, catálogo, schemas, configuración, firma y seams. No contiene provisión funcional.
2. **PR 2 hacia `main`:** repositorio transaccional, servicio/router de provisión y activación, modelos/migración/seed, integración, regresión y gates.

La cadena es `stacked-to-main` y la estrategia `ask-on-risk`; si el desglose confirmado supera 600, se detiene para reducir alcance o recibir una decisión explícita. No se agregan endpoints de consulta, cuotas operativas ni refactors de HU-005/HU-006.

Rollout: configurar el secreto fuera del repositorio, validar primero el catálogo y checkout en `demo`, aceptar webhook solo con firma válida y observar códigos/conteos sin datos sensibles. Los logs estructurados se limitan a ruta, estado, código de resultado y un identificador opaco; nunca incluyen body crudo, firma, secreto, token, hash de token, contraseña, correo completo ni SQL. El checkout público queda bloqueado para productivo hasta una decisión de autenticación y controles de infraestructura. Ante defecto, deshabilitar webhook, conservar filas para trazabilidad, revertir solo a una aplicación compatible con el esquema y preferir forward-fix. Reprocesar un evento válido con su misma clave depende de la recuperación idempotente.

No se ejecutaron tests, migraciones, lint, typecheck, OpenAPI, rollback ni gates. No se hicieron commits ni pushes.

## 11. Trazabilidad, riesgos y límites

| Decisión | Fuente |
| --- | --- |
| Alcance backend-only, HU-004/PB-004/CP-003 y límites | `proposal.md`, `spec.md`, `explore.md` locales |
| Contratos HTTP y códigos cerrados | `specs/tenant-onboarding/spec.md` local y decisión aprobada del cambio raíz consultada solo como referencia |
| Arquitectura, locks, seed y activación | código local observado, `explore.md` y referencia externa aprobada de solo lectura |
| Stack, TDD, comandos y presupuesto | `openspec/config.yaml` y `project-context.md` |
| No regresión HU-005/HU-006 e identidad diferida | spec/propuesta locales y modelos/servicios/router existentes |

Riesgos pendientes: `GAP-092` (PostgreSQL y downgrade aún no verificados en ejecución), disponibilidad del notifier real/outbox, y decisión de producto para cualquier checkout fuera de demo. Ninguno autoriza ampliar el slice ni afirmar evidencia inexistente.

Fuera de alcance explícito: UI, React/TypeScript, Flutter, pagos/facturación reales, correo real, trial, cambio de plan, cancelación, purga, invitaciones de agentes, identidad global, memberships, RBAC, recuperación de cuentas, auditoría completa, workers, S3/SQS, catálogo inmobiliario, correcciones funcionales ajenas de HU-005/HU-006, commits y pushes.

## Key Learnings

- La frontera de confianza debe ser el webhook autenticado; el checkout solo representa intención.
- En concurrencia, la unicidad de la base y la recuperación en una sesión limpia son más fuertes que un pre-check de aplicación.
- El hash de bytes crudos permite distinguir replay exacto de reutilización incompatible sin exponer el payload.
- La activación puede quedar preparada sin inventar identidad global, membership ni RBAC.
