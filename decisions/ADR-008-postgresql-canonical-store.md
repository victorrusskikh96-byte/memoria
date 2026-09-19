# ADR-008: PostgreSQL is the canonical store

Status: accepted

## Decision

Use PostgreSQL for canonical entities, policy events, temporal snapshots, and
audit metadata. Media will use encrypted object storage; search and AI stores
are derived and rebuildable.

## Consequences

Authority-relevant state can use relational constraints and transactions.
Derived systems may not become the only copy of user data or policy state.
