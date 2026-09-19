# Identity v0.1

## Goal

Link one real human to one canonical Legacy with sufficient confidence while minimizing biometric collection.

## Identity layers

1. **Account identity** authenticates access.
2. **Human identity** links the account to the represented person.
3. **Legacy identity** establishes the canonical Legacy for that person.
4. **Persona state** represents the person during a life period.
5. **Relationship identity** changes what a permitted viewer may see and how the AI frames context.

These layers must not collapse into one database flag.

## Canonical Legacy rule

A verified subject may establish one canonical Legacy. Duplicate candidates enter review and merge workflows. Merging preserves both histories and requires proof; it never silently discards conflicting evidence.

## Temporal snapshots

- Snapshot identity includes subject, period, capture time, capture method and verification class.
- Verified and reconstructed snapshots use distinct visible labels.
- The system never backdates a reconstructed snapshot as self-recorded.
- A selected historical persona cannot use knowledge from later periods unless the user explicitly exits the historical view.

## Sensitive operations

Step-up verification is required for trustee appointment, biometric-model authorization, full export, permanent deletion, memorial activation and changes to recovery methods.

## Privacy rule

Capture media used to represent appearance or voice does not automatically become an identity-verification template. Verification templates, if used, live in a separate critical-data boundary with separate retention and deletion rules.
