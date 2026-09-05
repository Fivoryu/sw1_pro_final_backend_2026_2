# Contexto SDD — RoomForge Backend

## Resultado

Este worktree queda inicializado para planificar posteriormente **HU-005 Trial Suscripción** (`PB-005 / HU-005 / CU-005 / CP-004`) dentro del repositorio backend independiente. La inicialización no creó propuesta, especificación, diseño ni tareas, y no modificó código de producto.

## Identidad y límites de repositorio

- **Proyecto:** `sw1_pro_final_backend_2026_2`
- **Repositorio remoto:** `https://github.com/Fivoryu/sw1_pro_final_backend_2026_2.git`
- **Worktree:** `D:/Universidad/Proyectos/2doSemestre2026/sw1/roomforge-hu005-backend`
- **Rama:** `feature/hu005-trial-suscripcion`
- **Base:** `feature/tenant-hu04-06`
- **Directorio Git común:** `D:/Universidad/Proyectos/2doSemestre2026/sw1/proyecto_final/backend/.git`

El runtime, las pruebas, las migraciones y la contabilidad nativa de HU-005 pertenecen a este worktree backend. El monorepo raíz permanece como superficie de coordinación y documentación. Sus artefactos no son visibles automáticamente aquí ni fueron copiados o mutados.

## Stack y arquitectura

API monolítica modular en Python 3.11+ con FastAPI, SQLAlchemy 2.x, PostgreSQL mediante psycopg, Alembic, Argon2id, PyJWT y Pydantic. La configuración de desarrollo declara pytest, Ruff y Pyright. El código se organiza en `app/`; las pruebas en `tests/`.

## Configuración SDD y calidad

- **Artifact store:** hybrid (OpenSpec + Engram).
- **Ejecución:** interactive.
- **Estrategia de entrega:** `ask-on-risk`; no hay estrategia de cadena definida.
- **Idioma de artefactos:** español profesional y neutral.
- **Identificadores de código:** inglés.
- **Strict TDD:** activo, con ciclo `RED → GREEN → TRIANGULATE → REFACTOR`.
- **Presupuesto máximo:** exactamente 400 líneas modificadas para la implementación de HU-005.
- **Runner de pruebas:** `..\\.venv\\Scripts\\python.exe -m pytest tests -q`.
- **Lint:** `..\\.venv\\Scripts\\ruff.exe check app tests`.
- **Typecheck:** `..\\.venv\\Scripts\\pyright.exe app tests`.
- **Migraciones:** `..\\.venv\\Scripts\\python.exe -m alembic -c alembic.ini upgrade head`.

Estos comandos se detectaron en `pyproject.toml` y la configuración existente; no se ejecutaron durante la inicialización, conforme a la instrucción de no correr pruebas, migraciones, lint ni typecheck.

## Estado de inicialización

- Se verificó que la raíz Git del worktree es distinta del monorepo y que ambos tienen directorios comunes distintos según el contexto operativo.
- Se inicializó CodeGraph localmente en `.codegraph/`; su estado es metadato generado, no código de producto.
- Engram no estaba disponible: el servidor `http://127.0.0.1:7437` no respondió. No se realizó ni se afirma una persistencia Engram exitosa (**GAP-001**).
- No se crearon directorios ni artefactos bajo `openspec/changes/`.
- No se crearon commits, pushes, migraciones ni cambios de rama.

## Próximo paso

Cuando se autorice la planificación, crear los artefactos del cambio `hu005-trial-suscripcion` únicamente dentro de este repositorio backend, respetando el presupuesto de 400 líneas y el ciclo Strict TDD.
