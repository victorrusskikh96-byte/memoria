# ADR-007: Start as a modular monolith

Status: accepted

## Decision

Deploy one FastAPI application with domain modules and enforce boundaries in
code and tests. Extract a service only after independent scaling, isolation, or
ownership requirements are measured.

## Consequences

Transactions, migrations, local development, and audit reasoning stay simple.
Module boundaries must still be explicit; a monolith is not permission for
cross-module table access or circular dependencies.
