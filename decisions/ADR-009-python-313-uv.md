# ADR-009: Pin Python 3.13 and manage it with uv

Status: accepted

## Decision

Use Python 3.13 for the API and uv for interpreter installation, dependency
locking, virtual environments, and task execution.

## Consequences

Windows and CI use the same declared interpreter and lockfile. The project does
not depend on a system Python installation or GNU Make.
