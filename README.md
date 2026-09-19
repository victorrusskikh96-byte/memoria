# Memoria

Privacy-first Digital Human Legacy Platform for preserving an authentic, portable and consent-based representation of a person's memories, personality, voice, relationships and life story across time.

Status: foundation and engineering baseline v0.2, 19 September 2026.

## Current milestone

The repository contains the accepted product/trust documentation and the first executable backend baseline:

- FastAPI application factory;
- liveness and PostgreSQL readiness endpoints;
- typed trust-domain vocabulary;
- asynchronous SQLAlchemy setup;
- Alembic configuration;
- local PostgreSQL container;
- pytest, Ruff and mypy configuration;
- Windows environment audit and PowerShell developer commands.

No user-facing feature or AI generation is implemented yet. This is deliberate: the first feature slice will start only after the authorization matrix and immutable event rules are reviewed.

## Recommended host

Use Windows 11 with WSL 2 and Docker Desktop. Windows 10 reached end of support on 14 October 2025. If migration is temporarily impossible, use Windows 10 22H2 build 19045 only with Microsoft Consumer ESU and treat it as a transition environment.

## Windows quick start

Run PowerShell from the repository root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\check-environment.ps1
```

After Git, uv and Docker are available:

```powershell
Copy-Item .env.example .env
.\scripts\dev.ps1 sync
.\scripts\dev.ps1 up
.\scripts\dev.ps1 migrate
.\scripts\dev.ps1 test
.\scripts\dev.ps1 run
```

Open:

- `http://127.0.0.1:8000/health/live`
- `http://127.0.0.1:8000/health/ready`
- `http://127.0.0.1:8000/docs`

## Direct commands

PowerShell wrappers are optional. Equivalent commands:

```powershell
uv sync --all-groups
docker compose up -d postgres
uv run alembic upgrade head
uv run pytest
uv run ruff check .
uv run mypy src
uv run uvicorn memoria.main:app --reload --host 127.0.0.1 --port 8000
```

## Source of truth

- `docs/00-foundation/PROJECT_CONSTITUTION.md` defines non-negotiable principles.
- `docs/01-trust/TRUST_SYSTEM.md` connects Identity, Consent, Ownership and Succession.
- `docs/07-engineering/ARCHITECTURE_BASELINE.md` defines the initial technical shape.
- `docs/07-engineering/IMPLEMENTATION_ROADMAP.md` defines the implementation order.
- `decisions/` records decisions that future implementation must preserve.

## Important limitation

Legal sections are product requirements and risk controls, not jurisdiction-specific legal advice. Counsel must validate launch requirements in each target jurisdiction.
