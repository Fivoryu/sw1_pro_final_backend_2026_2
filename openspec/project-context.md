# Contexto SDD — RoomForge Backend

## Identidad

- **Proyecto:** `sw1_pro_final_backend_2026_2`
- **Repositorio:** backend independiente de RoomForge
- **Raíz:** `D:/Universidad/Proyectos/2doSemestre2026/sw1/proyecto_final/backend`
- **Rama observada:** `feature/tenant-hu04-06`
- **HEAD observado:** `7429193 feat: implementacion modulo tenant HU 004, 005 y 006`
- **Estado observado:** limpio antes de crear metadatos locales de CodeGraph; CodeGraph fue inicializado en este repositorio.

## Stack y arquitectura

API monolítica modular en Python 3.11+, con FastAPI, SQLAlchemy 2.x, PostgreSQL mediante psycopg, Alembic, Argon2id, PyJWT y Pydantic. El código se organiza en `app/core`, `app/db` y módulos funcionales (`identity` y `tenant`). Las pruebas están en `tests/` y usan pytest.

## Calidad y testing

- **Strict TDD:** activo.
- **Runner esperado:** `..\\.venv\\Scripts\\python.exe -m pytest tests -q`.
- **Lint configurado:** `..\\.venv\\Scripts\\python.exe -m ruff check app tests`.
- **Typecheck configurado:** `..\\.venv\\Scripts\\pyright.exe app tests`.
- **Migraciones:** `..\\.venv\\Scripts\\python.exe -m alembic -c alembic.ini upgrade head`.
- La inicialización no ejecutó tests ni otras verificaciones runtime, por instrucción explícita.

## Convenciones y límites

- Documentación SDD en español profesional y neutral.
- Identificadores de código en inglés.
- Commits convencionales; no crear commits ni hacer push durante SDD.
- Este contexto habilita un cambio futuro **backend-only para HU-004**.
- Los artefactos aprobados del repositorio raíz son referencia externa; no se copiaron ni modificaron.
- No cambiar la rama local durante la inicialización.

## Gaps y riesgos

- **GAP-001:** Engram no estaba disponible: el servidor HTTP local `127.0.0.1:7437` no respondió. La persistencia remota queda pendiente.
- **GAP-002:** El repositorio raíz contiene un cambio con el mismo nombre lógico (`hu004-alta-inmobiliaria`); el dispatcher backend debe resolver la colisión usando el estado local de `backend/openspec/changes/` cuando se cree el cambio.
- La disponibilidad real de PostgreSQL no fue evaluada porque no se ejecutaron tests ni migraciones.
