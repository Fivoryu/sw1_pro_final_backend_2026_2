# Propuesta local — Alta de inmobiliaria (HU-004)

- **Cambio:** `hu004-alta-inmobiliaria`
- **Historia de usuario:** HU-004 — Alta de inmobiliaria
- **Product Backlog:** PB-004
- **Caso de prueba:** CP-003
- **Prioridad:** Alta
- **Repositorio:** RoomForge Backend independiente
- **Alcance técnico:** backend-only y contrato API
- **Idioma:** español profesional y neutral
- **Estado de evidencia:** propuesta; no se ejecutaron tests, migraciones, lint ni typecheck

## 1. Intención y problema

RoomForge ya compone el módulo `tenant` bajo `/api/v1`, pero la operación actual `POST /api/v1/tenant/alta` mezcla selección de plan, datos de alta y aprovisionamiento. Además, acepta un `payload_firmado` sin una frontera verificable de autenticidad, no separa checkout de provisión, no tiene una intención de checkout persistida ni un catálogo semillado con la cuota de agentes, y no ofrece una activación consumible del primer administrador.

Esta situación dificulta que el consumidor Web distinga una intención de contratación de un alta efectiva y deja ambiguas la confianza del evento, la idempotencia ante reintentos y la recuperación ante fallos parciales. La propuesta crea un slice backend/API acotado para HU-004 y CP-003, sin anticipar funcionalidades de identidad, interfaz o facturación que pertenecen a otras historias.

## 2. Objetivos

1. Exponer el catálogo server-owned de los tres planes mensuales aprobados con monto exacto en BOB y cuotas observables.
2. Separar un checkout simulado, público únicamente en el entorno de demo, de cualquier aprovisionamiento.
3. Establecer el webhook firmado con HMAC como única frontera que puede aprovisionar una inmobiliaria.
4. Garantizar correlación, atomicidad e idempotencia del alta, incluyendo reintentos concurrentes y conflictos de payload.
5. Crear una activación mínima del primer administrador con token hasheado, expiración y consumo único, sin contraseña.
6. Dejar un contrato API consumible por el futuro panel Web y preservar funcionalmente HU-005 y HU-006.

## 3. Resultado esperado

Un consumidor podrá consultar los planes, confirmar una intención de checkout y observar su estado sin que se cree todavía un tenant. Solo un evento webhook autenticado, íntegro, correlacionado con el checkout y compatible con el catálogo podrá crear, en una unidad atómica, el tenant, su suscripción inicial activa, el registro del evento y la activación pendiente del primer administrador.

Los reintentos exactos deberán recuperar el resultado original sin duplicar recursos; una misma clave con datos diferentes deberá producir un conflicto explícito. El token crudo de activación se entregará únicamente a un adaptador controlado y no aparecerá en respuestas, persistencia ni logs.

## 4. Alcance

### 4.1. Catálogo de planes

El contrato backend expondrá únicamente los planes activos aprobados para HU-004:

| Plan | Precio mensual | `max_agents` | Almacenamiento | Inmuebles activos | Reconstrucciones/mes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Básico | 199 BOB | 5 | 50 GB | 5 | 10 |
| Profesional | 449 BOB | 15 | 200 GB | 20 | 40 |
| Empresarial | 899 BOB | 50 | 1.000 GB | 100 | 150 |

El monto se tratará como valor monetario decimal, no como `float` de autoridad. `max_agents` cuenta agentes y no incluye al administrador.

### 4.2. Checkout simulado

Se definirá una operación separada que acepte el plan activo y los datos mínimos de la inmobiliaria y del primer administrador. Devolverá una referencia correlacionable, el plan y sus datos server-owned, el precio en BOB y el estado de confirmación.

Para esta historia, el checkout será público únicamente en el simulador del entorno de demo. Registrará la intención mínima necesaria y no creará tenant, suscripción, invitación ni evento de aprovisionamiento. No aceptará datos de cuotas, precios ni `tenant_id` como autoridad del cliente.

### 4.3. Webhook y aprovisionamiento

Se implementará una operación de webhook independiente. La autenticidad e integridad se verificarán mediante HMAC-SHA256 sobre el body crudo, usando un secreto obligatorio de configuración, antes de buscar o persistir efectos de negocio. El evento deberá correlacionarse con un checkout confirmado y un plan activo; nombre, correo, precio y cuotas se tomarán de las fuentes server-owned.

El alta aceptada será atómica y comprenderá:

- tenant de la inmobiliaria;
- suscripción inicial en estado `active`;
- registro del evento facturado/procesado;
- invitación pendiente del primer administrador;
- actualización del estado de la intención de checkout.

La clave de idempotencia y una representación verificable del payload serán autoridad persistente. Los reintentos exactos, secuenciales o concurrentes, no podrán crear duplicados; una clave reutilizada con payload, checkout, plan o datos incompatibles producirá un conflicto explícito.

### 4.4. Activación mínima

La activación quedará vinculada al tenant y al correo normalizado del primer administrador. El token será aleatorio, se persistirá únicamente como hash, tendrá expiración y podrá consumirse una sola vez mediante una operación condicional. El notifier simulado/integrable podrá recibir el token crudo después del commit, pero la API no lo devolverá ni se registrará.

La suscripción inicial no activará el trial de HU-005. La activación tampoco creará una contraseña ni resolverá por adelantado la cuenta global, membership o RBAC.

### 4.5. Persistencia, configuración y contrato

El cambio podrá ampliar de forma aditiva los modelos de `tenant`, incorporar la intención de checkout, agregar la cuota de agentes, la correlación del evento, el hash del payload y el consumo de activación, y crear una migración posterior a `0003`. El seed de planes deberá ser reproducible y compatible con datos legacy, sin sobrescrituras comerciales silenciosas.

Las áreas previstas son `app/modules/tenant/` —modelos, esquemas, router, servicio, repositorio y puertos—, `app/core/config.py`, `alembic/env.py`, una migración aditiva y pruebas específicas de onboarding. `app/main.py` ya registra el router y no requiere una nueva inclusión.

## 5. Fuera de alcance y no objetivos

- Panel visual Web, navegación, copy, componentes React/TypeScript y prototipos de UI.
- Aplicación Flutter.
- Pagos reales, proveedor externo de checkout, facturación productiva y correo real.
- HU-005 — trial y suscripción mensual.
- HU-006 — cambio de plan, cancelación, cuotas operativas y purga.
- Invitaciones o aceptación de agentes.
- Creación o reutilización de `usuario_global`, memberships generales y RBAC.
- Recuperación de cuentas, auditoría completa, workers, S3/SQS y catálogo inmobiliario.
- Endpoints de consulta adicionales no necesarios para el contrato de HU-004.
- Refactor general del módulo `tenant` o correcciones funcionales de HU-005/HU-006 no imprescindibles para este slice.

## 6. Reglas de negocio e invariantes

1. Solo los tres planes aprobados y activos son contratables.
2. Los precios, moneda y cuotas son propiedad del catálogo del servidor; el administrador no consume `max_agents`.
3. El checkout simulado confirma intención, pero nunca aprovisiona recursos.
4. El webhook HMAC es la única frontera autorizada para aprovisionar.
5. La firma se valida antes de efectos de negocio; el secreto, body crudo y material sensible no se exponen.
6. Un evento debe corresponder a un checkout válido y a los datos vigentes del plan.
7. Un fallo en cualquier paso del aprovisionamiento revierte el conjunto y no deja recursos parciales.
8. La misma clave con el mismo payload es idempotente; la misma clave con datos diferentes es un conflicto.
9. El alta crea una suscripción inicial `active` y no ejecuta el trial de HU-005.
10. La activación usa token hasheado, expirable y de un solo uso; no recibe ni genera contraseña.
11. HU-004 no crea identidad global, membership ni RBAC.
12. Los cambios compartidos deben conservar el comportamiento funcional de HU-005 y HU-006.

## 7. Criterios de éxito

La entrega quedará lista para verificación cuando la evidencia futura demuestre, sin asumir resultados por adelantado:

| Criterio | Resultado observable esperado |
| --- | --- |
| CA1 / CP-003 — catálogo y checkout | Los tres planes aparecen con precio decimal en BOB y cuotas exactas; el checkout devuelve referencia y confirmación sin crear recursos de alta. |
| CA2 / CP-003 — frontera firmada | Un webhook HMAC válido y correlacionado aprovisiona el conjunto; firma ausente, inválida, payload alterado o correlación inconsistente no deja efectos. |
| CA3 / CP-003 — idempotencia | Reintentos secuenciales y concurrentes producen como máximo un tenant, una suscripción, una invitación y un evento lógico; el conflicto de payload es explícito. |
| CA4 / CP-003 — activación | El primer administrador queda pendiente con hash, expiración y consumo único; el token no se expone y un token expirado o consumido se rechaza. |
| No regresión | HU-005 y HU-006 conservan sus rutas y comportamiento funcional; no se incorpora UI ni alcance de identidad o pagos reales. |
| Migración y contrato | La migración aditiva y el contrato API quedan preparados para verificación real; cualquier limitación de PostgreSQL se registra bajo `GAP-092`. |

`CP-003` permanece `not executed` hasta que exista evidencia real de pruebas y gates. Esta propuesta no declara tests, migraciones, lint ni typecheck ejecutados.

## 8. Impacto y áreas afectadas

- **Backend/API:** cambia el contrato de alta existente hacia superficies separadas para catálogo, checkout, webhook y consumo de activación. El futuro panel Web podrá consumir el contrato, pero no se implementa aquí.
- **Datos:** se requiere una extensión aditiva del esquema, seed reproducible y compatibilidad explícita con planes y eventos legacy.
- **Operaciones:** el entorno de demo deberá configurar el secreto HMAC y controlar la exposición del checkout. La observabilidad deberá registrar códigos y resultados sin body, token, secreto, contraseña ni datos sensibles completos.
- **Producto:** la contratación simulada queda definida para demo; el rollout productivo del checkout público necesita una decisión posterior sobre autenticación y/o controles de infraestructura.
- **QA y desarrollo:** se agregará cobertura TDD estricta de contratos, seguridad, atomicidad, concurrencia, activación y migraciones, diferenciando dobles de prueba de evidencia PostgreSQL real.
- **Usuarios y soporte:** se obtiene un flujo de alta más explicable y recuperable, pero la entrega real de correo y la creación de identidad del administrador requieren fases posteriores.

## 9. Riesgos y gaps

| ID | Riesgo o gap | Tratamiento propuesto |
| --- | --- | --- |
| `GAP-004-API-001` | El contrato exacto de headers, canonicalización, timestamp y respuestas HMAC aún debe quedar verificable. | Cerrar la decisión en spec/design antes de tasks y cubrir firmas válidas, ausentes, inválidas, alteradas y fuera de ventana. |
| `GAP-004-IDEM-001` | El check-then-insert actual tiene carrera y no distingue todos los conflictos de persistencia. | Hacer que constraints, locks, hash del payload y recuperación del resultado original sean la autoridad. |
| `GAP-004-DOM-001` | No existe una decisión aprobada para vincular el primer administrador con usuario global, membership y rol. | Limitar HU-004 a tenant, correo normalizado e invitación pendiente; diferir identidad/RBAC. |
| `GAP-004-NOTIF-001` | No existe un canal real ni outbox para entregar activaciones. | Usar un puerto/adaptador simulado e integrable; dejar correo real y reintento durable fuera de alcance. |
| `GAP-004-AUTH-001` | El checkout público es válido para demo, pero su exposición productiva no está resuelta. | No desplegarlo en productivo sin decisión de producto sobre autenticación, controles de infraestructura y límites operativos. |
| `GAP-004-UI-001` | No hay una experiencia Web verificable en este repositorio backend. | Entregar solo contrato API y documentar la UI como trabajo posterior. |
| `GAP-092` | PostgreSQL, constraints, upgrade/downgrade y concurrencia real no fueron verificados durante exploración. | Ejecutar la verificación en fases posteriores si el entorno está disponible y reportar la limitación si no lo está. |
| Datos legacy | `0003` puede contener planes sin código y eventos sin hash. | Migración aditiva, adopción solo ante coincidencia exacta, aborto ante colisiones/discrepancias y sin sobrescritura silenciosa. |
| Presupuesto | El diseño de HU-004 puede crecer al tocar áreas compartidas de HU-005/HU-006. | Mantener el slice estricto y detener la implementación si el pronóstico supera 600 líneas modificadas. |

## 10. Presupuesto y entrega

El presupuesto máximo es de **600 líneas modificadas**. Incluye únicamente contratos, lógica de onboarding, configuración, modelos/migración, seed y pruebas de HU-004. No incluye UI, pagos/correo reales ni refactors de HU-005/HU-006.

La estrategia de delivery es **`ask-on-risk`**. La estrategia de cadena aprobada es **`stacked-to-main`**: si el desglose posterior confirma más de una unidad revisable, cada PR se dirige a `main` en orden. Antes de aplicar se deberá revisar el pronóstico; superar 600 líneas requiere reducir alcance o una decisión explícita, no una excepción implícita.

Durante esta fase no se implementa, no se ejecutan tests o migraciones y no se realizan commits ni pushes.

## 11. Rollback y recuperación

1. Ante un defecto de autenticidad o aprovisionamiento, deshabilitar el procesamiento del webhook para impedir nuevas altas.
2. Revertir la aplicación solo a una versión compatible con el esquema aditivo; conservar los registros creados para trazabilidad.
3. En producción, preferir un forward-fix y no ejecutar un downgrade destructivo sobre una base con tenants, suscripciones, invitaciones, intenciones o eventos HU-004.
4. En una base vacía o descartable, validar el downgrade y sus claves foráneas antes de ejecutarlo.
5. Al restaurar una versión corregida, reprocesar eventos válidos con la misma clave y depender de la idempotencia para evitar duplicados.

No se realizó ningún rollback; lo anterior es el procedimiento propuesto.

## 12. Trazabilidad, evidencia y fuentes

| Decisión o afirmación | Fuente |
| --- | --- |
| Brechas de composición, contrato actual, modelos, migración y pruebas ausentes | `backend/openspec/changes/hu004-alta-inmobiliaria/explore.md` |
| Stack, arquitectura, TDD estricto, comandos y límites locales | `backend/openspec/project-context.md` y `backend/openspec/config.yaml` |
| HU-004/PB-004/CP-003 y separación checkout/webhook | Referencias externas aprobadas del cambio raíz: `proposal.md`, `specs/tenant-onboarding/spec.md`, `design.md` y `tasks.md` |
| Planes, cuotas y exclusión del administrador | Decisiones aprobadas reflejadas en la exploración y referencias externas |
| Gaps de producto y operación | Exploración local y referencias externas aprobadas |

Las referencias del cambio raíz se consultaron únicamente como lectura. No se copiaron ni modificaron sus artefactos. La propuesta local es independiente y está limitada al repositorio backend.

## 13. Próxima fase

`next_recommended: spec` — convertir esta propuesta en requisitos y escenarios verificables para el backend, cerrando los gaps técnicos necesarios sin ampliar el alcance aprobado.
