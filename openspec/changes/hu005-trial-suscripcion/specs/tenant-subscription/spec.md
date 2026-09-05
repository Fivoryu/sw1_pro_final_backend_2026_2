# Especificación de suscripción de tenant — HU-005

## 1. Propósito, alcance y trazabilidad

Esta especificación define el slice backend/API de `PB-005`, `HU-005`, `CU-005` y `CP-004` para activar una prueba gratuita única, inspeccionar su suscripción y convertirla mediante un evento mensual autenticado. El límite de implementación es de 400 líneas modificadas. El repositorio, las migraciones, las pruebas y la contabilidad de este cambio están restringidos al backend local `sw1_pro_final_backend_2026_2`, en el worktree indicado por la propuesta. El monorepo raíz es únicamente referencia y no forma parte de esta superficie.

`CP-004 = not executed`. Este documento no afirma ejecución de tests, migraciones, lint, typecheck, revisión, commits, pushes ni operaciones de entrega.

Se reutilizan identidad/autenticación de HU-002, aprovisionamiento y contratos HMAC de HU-004, y se preserva la representabilidad de estados futuros de HU-006. No se altera el comportamiento de HU-002 ni se duplica la frontera de HU-004.

## 2. Requisitos

### Requirement: Autenticación, autorización y aislamiento tenant

El sistema MUST reutilizar `get_current_user` para validar el principal JWT y la sesión. MUST autorizar activación e inspección solamente cuando exista una asociación activa `tenant_administrator` entre el principal y el tenant de la suscripción. El tenant MUST derivarse de esa asociación server-owned.

El sistema MUST aceptar como procedencia del administrador inicial únicamente la invitación de HU-004 efectivamente consumida. El evento firmado no concede acceso administrativo. `tenant_id` recibido en body, query, header o evento MUST NOT seleccionar el tenant ni conceder autoridad.

Los errores de autenticación, asociación, tenant y suscripción MUST ser sanitizados y no enumerar usuarios, tenants o suscripciones. HU-005 MUST NOT implementar RBAC general, catálogo de roles, permisos generales ni memberships generales.

#### Scenario R-01.1: Principal autorizado

- GIVEN un JWT válido y una asociación activa vinculada al tenant aprovisionado
- WHEN el principal solicita activar o inspeccionar
- THEN el sistema opera únicamente sobre la suscripción de ese tenant
- AND no requiere un selector de tenant del cliente

#### Scenario R-01.2: Principal no autorizado

- GIVEN un JWT ausente, inválido, inactivo, no administrador o sin asociación activa
- WHEN solicita activar o inspeccionar
- THEN la operación es rechazada con un error sanitizado
- AND no revela la existencia de otro tenant o suscripción
- AND no muta datos

### Requirement: Bootstrap administrativo mínimo e idempotente

El sistema MUST ofrecer el bootstrap backend `POST /api/v1/tenant/administrador/bootstrap`, protegido por JWT y sin autoridad tenant en el request. El body MUST ser vacío o `{}`; los campos adicionales MUST rechazarse. El servidor MUST reconocer o crear una única asociación activa trazable a la invitación inicial de HU-004 en estado consumido y cuyo correo normalizado corresponda al principal.

El bootstrap MUST ser idempotente para el mismo vínculo: la primera operación puede responder `201` y una repetición válida `200`, sin duplicar asociaciones. No puede consumir invitaciones, aceptar contraseñas o tokens crudos, crear usuarios, agentes, roles o memberships. Si no existe un vínculo server-owned elegible o existe ambigüedad, MUST fallar cerrado sin elegir por `tenant_id` ni revelar candidatos.

La composición exacta de columnas, índices y detalles internos de la asociación queda diferida a diseño/tareas; el contrato de procedencia, unicidad y aislamiento no queda diferido.

#### Scenario R-01.3: Bootstrap válido y repetido

- GIVEN un usuario inicial de HU-004, una invitación consumida y un tenant elegible sin asociación
- WHEN ejecuta el bootstrap y luego lo repite
- THEN se crea una sola asociación activa vinculada al usuario, tenant e invitación
- AND la repetición reconoce el vínculo existente sin duplicarlo

#### Scenario R-01.4: Bootstrap sin procedencia elegible

- GIVEN un principal sin invitación HU-004 consumida coincidente, o con candidatos ambiguos
- WHEN intenta ejecutar el bootstrap
- THEN la operación se rechaza sin crear asociación
- AND no se revela correo, cantidad, tenant ni criterio de selección

### Requirement: Activación única del trial

El sistema MUST proteger `POST /api/v1/tenant/activar-prueba` con JWT y asociación administrativa activa. El request MUST carecer de autoridad tenant; un `tenant_id` aportado por el cliente MUST rechazarse y nunca seleccionar la suscripción.

La activación MUST ser elegible solamente para la suscripción inicial `active` provisionada por HU-004, con `trial_inicio` y `trial_fin` ausentes y sin período mensual previo. Al aceptar, MUST persistir `trial_inicio` en el instante actual, `trial_fin` exactamente 14 × 24 horas después (`336` horas), y estado `trialing`, como una única operación atómica.

La activación MUST ser de una sola vez. Una segunda solicitud, incluso después del vencimiento, MUST responder conflicto y no modificar estado, fechas, plan, suscripción ni eventos. Los timestamps MUST conservar zona horaria. El uso concreto del reloj y la representación de columnas queda diferido a diseño/tareas.

#### Scenario R-02.1: Activación elegible

- GIVEN un administrador autorizado, una suscripción inicial `active` y un reloj que entrega `T`
- WHEN activa la prueba
- THEN el estado queda `trialing`
- AND `trial_inicio = T`
- AND `trial_fin = T + 336 horas`
- AND la respuesta contiene la proyección aprobada con períodos mensuales nulos

#### Scenario R-02.2: Segunda activación

- GIVEN una suscripción cuyo trial ya fue iniciado, haya vencido o no
- WHEN se solicita activar nuevamente
- THEN responde `409`
- AND conserva exactamente estado, fechas, plan y eventos

#### Scenario R-02.3: Estado inicial incompatible o carrera

- GIVEN una suscripción inexistente, no inicial, con fechas inconsistentes o dos activaciones concurrentes
- WHEN se procesa la activación
- THEN como máximo una operación persiste el trial
- AND las demás rechazan sin sobrescribir ni crear datos parciales

### Requirement: Máquina de estados y expiración

El sistema MUST considerar expirado un trial cuando `now >= trial_fin`. La conversión de este slice MUST aceptar solamente `trialing → active`. MUST rechazar la conversión desde el `active` inicial de HU-004, desde un `active` ya convertido y desde cualquier estado no soportado.

Un trial expirado puede permanecer persistentemente `trialing`; HU-005 MUST rechazar su conversión sin crear otro estado y MUST dejar su remediación a HU-006. HU-005 MUST NOT implementar renovación, gracia, `past_due`, `suspended`, `canceled_read_only`, `purged` ni otro lifecycle de HU-006. Las futuras cadenas de estados MUST seguir siendo representables.

#### Scenario R-03.1: Límite de expiración

- GIVEN `trial_fin = T`
- WHEN una conversión nueva se procesa con `now = T`
- THEN responde conflicto por expiración
- AND no muta la suscripción ni persiste un evento mensual

#### Scenario R-03.2: Transición permitida y transiciones no permitidas

- GIVEN una suscripción `trialing` vigente, o una suscripción `active` inicial/convertida o en un estado futuro
- WHEN llega un evento mensual nuevo
- THEN solo el primer caso puede convertir a `active`
- AND los demás se rechazan sin cambiar estado, fechas, plan ni eventos

### Requirement: Inspección protegida y proyección segura

El sistema MUST ofrecer `GET /api/v1/tenant/suscripcion`, protegido por JWT y asociación administrativa activa, sin selector de tenant. Debe devolver únicamente `subscription_id`, `plan_id`, `estado`, `trial_inicio`, `trial_fin`, `periodo_inicio` y `periodo_fin`, usando `null` cuando corresponda. El `plan_id` MUST ser el contratado y server-owned.

La respuesta MUST NOT incluir payload o body firmado, firma, secreto, monto recibido, JWT, password, token, hashes sensibles, correo completo, datos administrativos completos ni datos de otro tenant. La falta de autorización o de suscripción accesible MUST producir un resultado sanitizado no enumerante.

#### Scenario R-04.1: Inspección autorizada

- GIVEN un administrador activo con una suscripción accesible
- WHEN consulta la suscripción
- THEN recibe exactamente la proyección aprobada de su tenant
- AND no recibe campos sensibles ni datos del evento

#### Scenario R-04.2: Inspección no enumerante

- GIVEN un principal no autorizado, una asociación inactiva o una suscripción inaccesible
- WHEN consulta
- THEN recibe `401` o `404` sanitizado según corresponda
- AND no puede inferir si existe otro tenant o suscripción

### Requirement: Evento mensual firmado y frontera HMAC compartida

El sistema MUST procesar el evento mensual en `POST /api/v1/tenant/webhook` mediante `HMACWebhookSignatureVerifier` y el contrato HMAC de HU-004, sin implementar criptografía paralela. Debe exigir `Content-Type: application/json`, `X-RoomForge-Webhook-Timestamp` y `X-RoomForge-Webhook-Signature` con el formato de HU-004: timestamp decimal y firma `v1=` seguida de 64 hexadecimales minúsculos.

La firma MUST calcularse sobre `timestamp.encode("ascii") + b"." + raw_body`, con HMAC-SHA256 y comparación constante. El body MUST leerse como bytes una sola vez, sin reserialización, y esa misma representación MUST sustentar la huella SHA-256. La tolerancia MUST ser la configurada por HU-004, por defecto 300 segundos; la igualdad del límite se acepta y una diferencia mayor se rechaza.

La autenticación MUST completarse antes de consultar idempotencia, correlación, tenant, suscripción, plan o cualquier dato de negocio. Una firma ausente, inválida, malformada o timestamp inválido/stale MUST responder `401` sin lookup ni persistencia. La ausencia del secreto MUST responder `503` sin exponer configuración.

El evento mensual MUST usar exactamente `event_type = "subscription.monthly.succeeded"` y los campos aprobados `event_type`, `idempotency_key`, `subscription_id`, `plan_id` y `monto_bob`. Los campos extra, incluidos `tenant_id` y autoridades equivalentes, MUST rechazarse. La forma de parseo queda diferida a diseño/tareas, pero no la strictness ni el tipo exacto.

#### Scenario R-05.1: Evento nuevo autenticado

- GIVEN headers HMAC válidos, raw body íntegro, timestamp dentro de tolerancia y el tipo mensual exacto
- WHEN se recibe el evento
- THEN se habilita la validación de negocio
- AND ninguna consulta de negocio ocurrió antes de la autenticación

#### Scenario R-05.2: Autenticación fallida o contrato estricto

- GIVEN una firma ausente/alterada/malformada, timestamp fuera de tolerancia o body con campos extra
- WHEN se recibe el evento
- THEN responde `401` para autenticación fallida o `422` para schema autenticado inválido
- AND no muta ni persiste datos de negocio

### Requirement: Conversión server-owned, calendario y alias

Después de autenticar, el sistema MUST resolver suscripción, tenant y plan desde el servidor y validar `subscription_id`, tipo, estado `trialing`, vigencia, `plan_id` contratado y `monto_bob` contra el plan server-owned. El evento MUST NOT cambiar tenant, plan, precio, cuotas ni monto esperado.

Una conversión válida MUST cambiar `trialing` a `active`, fijar `periodo_inicio` al instante de conversión y calcular `periodo_fin` como la misma fecha local del mes siguiente en `America/La_Paz`, ajustando al último día si el día no existe. Los valores MUST ser timezone-aware y el cálculo MUST NOT equivaler a sumar 30 días.

`POST /api/v1/tenant/suscribir` MUST conservarse como alias deprecated de la misma tubería firmada de `/webhook`: raw body, headers, verificador, parser, servicio, idempotencia y mapeo HTTP. No puede conservar el bypass legacy que acepta autoridad del cliente o hace persistencias separadas. El evento `tenant.onboarding.succeeded` de HU-004 debe continuar funcionando dentro de la frontera compartida, sin proyectarse como evento mensual.

#### Scenario R-06.1: Conversión válida

- GIVEN un evento mensual autenticado y correlacionado, una suscripción `trialing` vigente y plan/monto coincidentes
- WHEN se procesa
- THEN la suscripción queda `active`
- AND conserva su `plan_id`
- AND persiste el período mensual calculado en `America/La_Paz`
- AND persiste el evento mensual asociado
- AND responde `201`

#### Scenario R-06.2: Plan, monto, correlación o alias incompatibles

- GIVEN datos incompatibles o una llamada legacy sin la frontera HMAC/contrato mensual
- WHEN se procesa
- THEN responde `409`, `422` o `401` según la validación aplicable
- AND no cambia suscripción, plan, fechas ni evento

#### Scenario R-06.3: Fin de mes

- GIVEN una conversión en día 31, o en una fecha cuyo día no existe en el mes siguiente, incluyendo febrero bisiesto y no bisiesto
- WHEN se calcula `periodo_fin`
- THEN conserva la hora local y usa el último día del mes siguiente en `America/La_Paz`
- AND no usa una duración fija de 30 días

### Requirement: Idempotencia, replay y atomicidad

El sistema MUST conservar una unicidad persistente para `idempotency_key` y la huella de los bytes exactos recibidos. Una repetición autenticada con la misma clave, tipo, datos y bytes MUST devolver `200` con los identificadores, estado, fechas y resultado original, aun fuera de la ventana temporal aplicable a eventos nuevos. No debe duplicar conversión ni evento.

La misma clave con bytes, tipo, correlación o datos diferentes MUST devolver `409` y conservar íntegramente el primer resultado. Un evento legado sin `payload_hash` o sin resultado mensual MUST NOT presumirse replay. Una clave nueva después de la conversión MUST ser conflicto de estado.

La actualización de suscripción, fechas e inserción del evento MUST ocurrir en una única transacción con serialización/lock de la suscripción. PostgreSQL MUST gobernar unicidad y carreras. Una carrera solo puede clasificarse como replay o conflicto después de leer el registro comprometido y confirmar tipo, huella y resultado; nunca por el texto de una excepción. Cualquier fallo de escritura MUST revertir todos los efectos.

#### Scenario R-07.1: Replay exacto

- GIVEN una conversión mensual confirmada
- WHEN llega el mismo evento autenticado con la misma clave y raw bytes
- THEN responde `200` con el resultado original
- AND no crea evento ni conversión adicional

#### Scenario R-07.2: Clave reutilizada o carrera

- GIVEN una clave existente con datos distintos, o solicitudes concurrentes con la misma clave
- WHEN se procesan
- THEN los datos distintos reciben `409`
- AND como máximo una conversión/evento queda persistida
- AND las solicitudes equivalentes recuperan el resultado confirmado o un conflicto idempotente

#### Scenario R-07.3: Fallo atómico

- GIVEN un fallo en cualquier escritura de conversión
- WHEN termina la operación
- THEN no queda suscripción convertida sin evento ni evento sin conversión
- AND un reintento válido conserva la semántica de idempotencia

### Requirement: Estados HTTP y persistencia observable

El sistema MUST exponer, como mínimo, `201` para bootstrap/conversión nueva, `200` para bootstrap repetido, activación, inspección y replay, `401` para autenticación inválida, `404` para recursos tenant-scoped no accesibles, `409` para conflictos de estado/idempotencia, `422` para contrato autenticado inválido, `503` para secreto no configurado y `500` para fallos transaccionales, según la operación y validación aprobadas.

El evento mensual aceptado MUST quedar persistido como auditoría asociada a la suscripción, con tipo, clave, huella y resultado suficiente para replay exacto. No se incluyen notificaciones, outbox, workers, facturación real ni proveedor de cobro.

#### Scenario R-08.1: Resultado HTTP y auditoría

- GIVEN una solicitud válida, replay, conflicto, error HMAC o fallo de persistencia
- WHEN la API responde
- THEN usa el status observable correspondiente
- AND la persistencia cumple la semántica de éxito, replay o rollback
- AND no se crea una notificación ni una entrega externa

### Requirement: Migración aditiva y compatibilidad de datos

La evolución de datos MUST ser aditiva: conservar `trial_fin`, `periodo_fin`, relaciones y eventos de HU-004, y agregar solo los campos/asociación y referencias de resultado estrictamente ausentes. El nombre exacto de columnas, índices, constraints y revisión Alembic queda diferido a diseño/tareas. El head observado en archivos es `0004` con padre `0003`, pero debe revalidarse antes de crear la migración.

Las filas legacy de HU-004 con estado inicial `active` MUST permanecer intactas, con nuevos campos nulos cuando corresponda. No se crean trials sintéticos, asociaciones retroactivas, eventos mensuales ni cambios de plan. No deben agregarse checks que impidan almacenar estados futuros de HU-006.

Un downgrade con datos HU-005 MUST fallar cerrado y no eliminar asociaciones, fechas o eventos. Un downgrade destructivo MAY ejecutarse solamente sobre una base vacía y descartable; con datos reales debe preferirse forward-fix.

#### Scenario R-09.1: Upgrade compatible

- GIVEN datos existentes de HU-004, incluidos tenants, planes y suscripciones iniciales `active`
- WHEN se aplica la migración de HU-005
- THEN los datos y planes existentes permanecen intactos
- AND no se generan trials, asociaciones ni eventos sintéticos
- AND los estados futuros siguen siendo representables

#### Scenario R-09.2: Downgrade seguro

- GIVEN una base con cualquier dato HU-005
- WHEN se solicita un downgrade destructivo
- THEN la operación se rechaza sin borrar datos comprometidos
- AND solo una base descartable sin datos HU-005 puede admitirlo

### Requirement: Seguridad, privacidad y no divulgación

El sistema MUST aislar todas las consultas tenant-scoped y autenticar HMAC antes de lookup. Respuestas, errores y logs MUST ser sanitizados y no enumerar tenants, usuarios, suscripciones, eventos o claves. MUST NOT devolver ni registrar raw bodies, payloads firmados, firmas completas, secretos, JWT, passwords, tokens, hashes de tokens, hashes sensibles de payload, correos completos ni datos de otros tenants.

Los logs MAY contener ruta, status, códigos estables, tipo de evento e identificadores irreversiblemente abreviados. HU-005 MUST excluir UI, clientes, pagos/billing reales, planes/precios/cuotas nuevos, cambios de plan, enforcement de cuotas, lifecycle HU-006, RBAC/memberships generales, notificaciones, endpoint público de eventos, refactors ajenos y cambios en `docs/diagramas/Diagrama1.eapx`.

#### Scenario R-10.1: No divulgación

- GIVEN una activación, inspección, firma fallida, replay o conflicto
- WHEN se genera la respuesta y el registro técnico
- THEN no contienen los valores sensibles prohibidos
- AND no aparece información de otro tenant

## 3. Matriz de requisitos y aceptación

| ID | Requisito cubierto | Escenarios | Evidencia futura | Estado |
|---|---|---|---|---|
| R-01 | Auth, asociación, aislamiento y bootstrap | R-01.1–R-01.4 | JWT, invitación consumida, unicidad y no enumeración | Pendiente |
| R-02 | Activación única y trial exacto | R-02.1–R-02.3 | `trialing`, fechas y 336 horas | Pendiente |
| R-03 | Expiración y máquina de estados | R-03.1–R-03.2 | `now >= trial_fin`, solo `trialing → active` | Pendiente |
| R-04 | Inspección y proyección segura | R-04.1–R-04.2 | campos permitidos y ausencia de sensibles | Pendiente |
| R-05 | HMAC, raw bytes y strictness | R-05.1–R-05.2 | headers, fórmula, tolerancia y orden auth-before-lookup | Pendiente |
| R-06 | Conversión, plan server-owned y calendario | R-06.1–R-06.3 | `subscription.monthly.succeeded`, `America/La_Paz`, clamping | Pendiente |
| R-07 | Idempotencia, concurrencia y atomicidad | R-07.1–R-07.3 | `201/200/409`, unicidad, locks y rollback PostgreSQL | Pendiente |
| R-08 | Estados HTTP y persistencia observable | R-08.1 | statuses aprobados y auditoría mensual | Pendiente |
| R-09 | Migración y compatibilidad | R-09.1–R-09.2 | upgrade HU-004 y downgrade seguro | Pendiente |
| R-10 | Seguridad y no-goals | R-10.1 | inspección de respuestas/logs y alcance | Pendiente |

| Criterio | Pasos CP-004 | Escenarios que deben cubrirlo | Estado |
|---|---|---|---|
| CP-004.1 Activación | JWT/asociación; sin autoridad de body; estado `trialing`; `trial_inicio`; 336 horas; fechas en respuesta | R-01.1, R-02.1, R-02.3 | `not executed` |
| CP-004.2 Conversión | HMAC HU-004 raw-byte; solo `trialing → active`; plan conservado; período `America/La_Paz` | R-05.1, R-06.1, R-06.3 | `not executed` |
| CP-004.3 Replay | replay exacto `200`; mismo key con datos distintos `409`; sin duplicados | R-07.1, R-07.2 | `not executed` |

La evidencia determinística con reloj, fakes o dobles de firma no sustituye la evidencia PostgreSQL requerida para locks, unicidad, concurrencia, rollback y migraciones. La fase posterior debe conservar la separación entre hechos actuales y resultados ejecutados. `CP-004` no cambia de `not executed` por la existencia de esta especificación.

## 4. Decisiones diferidas y evidencia pendiente

Quedan diferidos exclusivamente a diseño/tareas los nombres exactos de columnas adicionales si HU-004 ya provee parte del evento, la forma interna de `tenant_administrator`, índices/constraints, revisión Alembic y detalles de locks, transacción, serialización y downgrade. Estas decisiones no pueden cambiar duración, event type, plan server-owned, estados permitidos, contrato HMAC, alias seguro, no divulgación, límites de alcance ni presupuesto.

Hechos actuales: se observaron archivos Alembic `0001 → 0004`, head de archivos `0004`/padre `0003`, `get_current_user`, `HMACWebhookSignatureVerifier`, headers HU-004 y tolerancia por defecto de 300 segundos con igualdad aceptada. Pendiente: revalidar el head efectivo y el delta en la fase posterior, y ejecutar la evidencia de tests, PostgreSQL, migración, lint y typecheck. Ninguno de esos resultados se afirma aquí.
