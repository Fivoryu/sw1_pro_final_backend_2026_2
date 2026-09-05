# Especificación de alta de inmobiliaria — Backend/API

## Propósito

Definir el contrato observable del slice backend/API de HU-004, PB-004 y CP-003 para consultar planes, registrar un checkout simulado y aprovisionar una inmobiliaria únicamente mediante un webhook autenticado. La especificación es independiente del repositorio raíz y no declara evidencia de ejecución.

## Alcance y decisiones preservadas

- El checkout público está permitido únicamente como demo. Su rollout productivo permanece bloqueado hasta una decisión posterior sobre autenticación y controles operativos.
- El flujo no implementa UI, aplicación Flutter, pagos ni correo reales, usuario global, memberships/RBAC, invitaciones de agentes, ni la funcionalidad de HU-005/HU-006.
- HU-004 crea una suscripción inicial `active`, pero no activa el trial de HU-005.
- Los nombres de rutas, headers concretos y canonicalización de la firma quedan sujetos al diseño, siempre que cumplan los requisitos de confianza de esta especificación.

## Requisitos

### Requirement: Catálogo exacto de planes server-owned

El sistema MUST exponer únicamente los tres planes activos aprobados, con monto monetario decimal en BOB y cuotas propiedad del servidor. `max_agents` MUST contar únicamente agentes y MUST excluir al administrador inicial.

| Plan | Precio mensual | `max_agents` | Almacenamiento | Inmuebles activos | Reconstrucciones mensuales |
| --- | ---: | ---: | ---: | ---: | ---: |
| Básico | 199 BOB | 5 | 50 GB | 5 | 10 |
| Profesional | 449 BOB | 15 | 200 GB | 20 | 40 |
| Empresarial | 899 BOB | 50 | 1.000 GB | 100 | 150 |

#### Scenario: Consulta del catálogo aprobado

- GIVEN que el catálogo está disponible
- WHEN un consumidor consulta los planes contratables
- THEN recibe exactamente los tres planes con nombre, precio en BOB y las cuatro cuotas indicadas
- AND la respuesta HTTP es `200`
- AND no se incluyen planes de HU-005 o HU-006

#### Scenario: Plan inexistente o inactivo

- GIVEN una solicitud que referencia un plan inexistente o inactivo
- WHEN intenta iniciar o confirmar el checkout
- THEN la API responde con `404 PLAN_NOT_AVAILABLE`
- AND no crea ni modifica recursos de onboarding

#### Scenario: Catálogo incompleto

- GIVEN que falta cualquiera de los tres planes aprobados o sus datos server-owned no son utilizables
- WHEN un consumidor consulta los planes contratables o intenta iniciar un checkout
- THEN la API responde con `503 PLAN_CATALOG_UNAVAILABLE`
- AND no devuelve una lista parcial ni crea recursos de onboarding

### Requirement: Checkout simulado sin aprovisionamiento

El sistema MUST ofrecer una operación de checkout separada del aprovisionamiento. Debe aceptar un plan activo y los datos mínimos de la inmobiliaria y del primer administrador, y devolver una referencia correlacionable, el estado de confirmación y los datos vigentes del plan desde el servidor. El checkout MUST ser público solo en el entorno de demo y MUST NOT aprovisionar recursos.

El cliente MUST NOT establecer como autoridad el precio, las cuotas ni `tenant_id`; los datos comerciales de la respuesta MUST provenir del catálogo server-owned.

#### Scenario: Confirmación válida de checkout demo

- GIVEN un plan activo y datos mínimos válidos
- WHEN el consumidor confirma el checkout simulado en el entorno demo
- THEN la API responde con `201`
- AND devuelve una referencia única, estado de confirmación, precio en BOB y cuotas del catálogo
- AND persiste la intención mínima necesaria para correlación posterior
- AND no crea tenant, suscripción, invitación ni registro de aprovisionamiento

#### Scenario: Checkout fuera del entorno demo

- GIVEN que se intenta utilizar la superficie pública de checkout fuera del entorno demo
- WHEN se procesa la solicitud
- THEN la operación no queda habilitada como checkout público
- AND no aprovisiona recursos
- AND el rollout productivo permanece bloqueado

### Requirement: Webhook HMAC como única frontera de aprovisionamiento

El sistema MUST aceptar el aprovisionamiento únicamente desde una operación de webhook independiente del checkout. MUST verificar el HMAC-SHA256 sobre el body crudo y el timestamp recibido, usando un secreto de configuración obligatorio, antes de buscar, persistir o modificar efectos de negocio. El evento MUST correlacionarse con un checkout confirmado y un plan activo.

La autoridad de identidad, precio, moneda y cuotas MUST ser server-owned. La solicitud no puede autorizar un alta mediante un `tenant_id`, precio o cuota proporcionados por el cliente. Las respuestas MUST omitir secretos, firmas, body crudo, tokens y otros materiales sensibles.

#### Scenario: Webhook nuevo válido

- GIVEN un checkout confirmado, un plan activo y un body íntegro con HMAC y timestamp válidos
- WHEN la API procesa por primera vez el webhook
- THEN valida autenticidad, integridad, vigencia temporal y correlación antes del aprovisionamiento
- AND crea el conjunto atómico definido para el alta
- AND responde con `201` exponiendo solo el identificador y estado necesarios

#### Scenario: Replay exacto autenticado

- GIVEN un webhook ya procesado con la misma clave y los mismos bytes de payload
- WHEN se reenvía autenticadamente, incluso fuera de la ventana temporal
- THEN la API responde con `200` y el resultado original
- AND no duplica recursos ni vuelve a entregar el token al notifier

#### Scenario: Secreto no configurado

- GIVEN que el secreto HMAC obligatorio no está configurado
- WHEN se recibe el webhook
- THEN la API responde con `503 WEBHOOK_NOT_CONFIGURED`
- AND no persiste ni modifica efectos de negocio

#### Scenario: Headers, firma o timestamp inválidos

- GIVEN que falta o es inválido un header requerido, la firma no coincide con el body crudo o el timestamp es inválido o está fuera de ventana
- WHEN se recibe el webhook
- THEN la API responde con `401 WEBHOOK_UNAUTHORIZED`
- AND no persiste ni modifica efectos de negocio
- AND no revela el secreto ni material sensible

#### Scenario: JSON inválido después de autenticación

- GIVEN headers, firma y timestamp válidos
- WHEN el body no contiene JSON válido o no cumple el esquema del webhook
- THEN la API responde con `422`
- AND no persiste ni modifica efectos de negocio

#### Scenario: Correlación o datos comerciales inconsistentes

- GIVEN un HMAC válido asociado a un checkout inexistente, no confirmado, incompatible, o a un plan inexistente/inactivo
- WHEN se procesa el webhook
- THEN la API responde con `409 CHECKOUT_NOT_AVAILABLE` o `409 CHECKOUT_MISMATCH`, según corresponda
- AND no crea efectos parciales

### Requirement: Aprovisionamiento atómico y rollback

Para un webhook aceptado, el sistema MUST crear en una única unidad transaccional: el tenant, la suscripción inicial `active`, el registro lógico del evento, la activación pendiente del primer administrador y la actualización de estado de la intención de checkout. Si falla cualquier parte, MUST revertir el conjunto y MUST dejar cero recursos parciales observables.

#### Scenario: Alta completa

- GIVEN un webhook válido, íntegro, correlacionado y no procesado
- WHEN finaliza el aprovisionamiento
- THEN existe exactamente un tenant, una suscripción `active`, un registro lógico del evento y una activación pendiente
- AND la suscripción conserva precio y cuotas del plan server-owned
- AND la activación está vinculada al tenant y al correo normalizado del administrador inicial

#### Scenario: Fallo durante el alta

- GIVEN que falla la creación o persistencia de cualquiera de los recursos del conjunto
- WHEN termina la operación
- THEN la API responde con `500 ONBOARDING_NOT_PROVISIONED`
- AND no quedan tenant, suscripción, activación, evento ni actualización de checkout parcialmente aplicados

### Requirement: Idempotencia secuencial y concurrente

El sistema MUST persistir una identidad única del evento o clave de idempotencia junto con una representación verificable del payload y su resultado original. La misma clave con el mismo payload MUST ser idempotente en reintentos secuenciales y concurrentes. La misma clave con payload, checkout, plan o datos incompatibles MUST producir conflicto y MUST preservar el resultado original.

#### Scenario: Reintento secuencial exacto

- GIVEN un webhook que ya completó el alta
- WHEN se reenvía con la misma clave y payload
- THEN la API responde con `200` y el resultado original o uno equivalente
- AND mantiene como máximo un tenant, una suscripción, una activación y un evento lógico

#### Scenario: Reintentos concurrentes exactos

- GIVEN dos o más solicitudes simultáneas con la misma clave y payload
- WHEN se procesan
- THEN como máximo una ejecuta los efectos de alta
- AND las restantes reciben el resultado idempotente o un estado explícito de procesamiento
- AND no se generan duplicados ni efectos parciales

#### Scenario: Reutilización incompatible de clave

- GIVEN una clave ya asociada a un payload, o un evento legacy sin hash verificable
- WHEN llega otra solicitud con payload, checkout, plan o datos de alta diferentes, o se intenta reutilizar la clave legacy
- THEN la API responde con `409 IDEMPOTENCY_CONFLICT`
- AND conserva el resultado previamente asociado
- AND no modifica ni duplica el onboarding

#### Scenario: Checkout ya aprovisionado con otra clave

- GIVEN un checkout ya aprovisionado mediante una clave de idempotencia distinta
- WHEN llega un webhook válido con otra clave
- THEN la API responde con `409 CHECKOUT_ALREADY_PROVISIONED`
- AND no modifica ni duplica el onboarding

### Requirement: Activación expirable y de consumo único

El sistema MUST crear una activación pendiente para el primer administrador, vinculada al tenant y al correo normalizado. Debe persistir únicamente un hash del token, aplicar un TTL observable y consumirlo mediante una operación condicional de un solo uso. El token crudo MUST entregarse al notifier únicamente después del commit; MUST NOT llegar a persistencia, respuestas API ni logs. HU-004 MUST NOT crear contraseña, usuario global, membership, rol RBAC ni invitaciones de agentes.

#### Scenario: Emisión posterior al aprovisionamiento

- GIVEN un aprovisionamiento exitoso
- WHEN se genera la activación
- THEN existe una activación pendiente con correo normalizado, hash y fecha de expiración
- AND el adaptador controlado puede recibir el token crudo después del commit
- AND las respuestas y logs no contienen token, secreto ni contraseña

#### Scenario: Consumo válido

- GIVEN un token vigente y no consumido
- WHEN el primer administrador lo presenta para activar el acceso
- THEN la API responde con `200`
- AND marca la activación como consumida una sola vez
- AND no genera ni persiste una contraseña
- AND no crea identidad global, membership ni RBAC

#### Scenario: Token inválido, expirado o consumido

- GIVEN un token inválido, expirado o ya consumido
- WHEN se intenta utilizar
- THEN la API responde con `410 ACTIVATION_UNAVAILABLE` sin distinguir información sensible innecesaria
- AND no crea ni modifica una activación válida

### Requirement: Persistencia aditiva y migración compatible

La persistencia MUST conservar la intención de checkout, la cuota `max_agents`, la correlación del evento, la representación verificable del payload y el estado de consumo de activación necesarios para observar los requisitos anteriores. La migración MUST ser aditiva, posterior a la migración `0003` cuando corresponda, y el seed del catálogo MUST ser reproducible e idempotente.

La migración MUST ser compatible con datos legacy sin sobrescrituras comerciales silenciosas: ante colisiones o discrepancias no puede adoptar datos incorrectos. La forma exacta de tablas, índices y estrategia de compatibilidad queda para diseño, siempre que el contrato observable y las restricciones de unicidad sean preservados.

#### Scenario: Inicialización o actualización compatible

- GIVEN una base compatible, con o sin datos legacy
- WHEN se aplica la migración y el seed
- THEN el catálogo aprobado queda disponible sin duplicados ni sobrescritura silenciosa
- AND las restricciones necesarias para unicidad e idempotencia quedan persistidas
- AND no se eliminan datos funcionales existentes de HU-005/HU-006

### Requirement: No regresión de HU-005 y HU-006

El cambio MUST preservar las rutas y el comportamiento funcional existente de HU-005 y HU-006. Las extensiones compartidas no pueden alterar sus contratos salvo que una dependencia estrictamente necesaria para HU-004 lo haga explícito y verificable.

#### Scenario: Operaciones existentes preservadas

- GIVEN las operaciones funcionales de HU-005 y HU-006 disponibles antes del cambio
- WHEN se incorpora el slice de HU-004
- THEN continúan respondiendo según sus contratos existentes
- AND no se agregan a HU-004 trial, cambio de plan, cancelación, cuotas operativas ni purga

## Reglas de negocio

1. Solo Básico, Profesional y Empresarial activos son contratables.
2. Precios, moneda y cuotas son autoridad del servidor; el administrador no consume `max_agents`.
3. Checkout confirma intención; nunca aprovisiona.
4. El webhook HMAC es la única frontera autorizada para aprovisionar.
5. La firma se valida sobre el body crudo, con timestamp y secreto obligatorio, antes de cualquier efecto.
6. Un alta aceptada es atómica y falla cerrando sin recursos parciales.
7. La misma clave y payload son idempotentes; la misma clave con datos incompatibles es conflicto.
8. La suscripción inicial queda `active` sin activar el trial de HU-005.
9. El token de activación se almacena como hash, tiene TTL y solo puede consumirse una vez.
10. HU-004 no resuelve identidad global, memberships ni RBAC.

## Fuera de alcance explícito

Quedan fuera UI y navegación, copy visual, React/TypeScript, Flutter, pagos o facturación reales, correo real, rollout productivo del checkout público, usuario global, memberships/RBAC, invitaciones de agentes, recuperación de cuentas, auditoría completa, workers, S3/SQS, catálogo inmobiliario, correcciones funcionales de HU-005/HU-006 y commits o pushes.

## Trazabilidad y evidencia

- **HU-004 / PB-004 / CP-003:** catálogo, checkout, webhook, aprovisionamiento, idempotencia y activación.
- **BR-B1:** separación entre checkout simulado y frontera firmada.
- **BR-B2:** activación de un solo uso sin contraseña.
- **BR-B3:** catálogo y cuotas aprobadas.
- **GAP-004-API-001, GAP-004-AUTH-001, GAP-004-DOM-001, GAP-004-NOTIF-001 y GAP-092:** decisiones de diseño y verificación aún pendientes.

CP-003 permanece `not executed`. No se ejecutaron tests, migraciones, lint, typecheck ni rollback durante esta fase.
