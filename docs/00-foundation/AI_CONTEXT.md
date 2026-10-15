# AI Context v0.1

## Product

Memoria preserves a person's evolving digital human legacy. It is private by default, evidence-backed and portable.

## Non-negotiable rules

- One verified human, one canonical Legacy.
- Life Snapshots are immutable; corrections append.
- Every claim includes evidence level, confidence and applicable life period.
- AI inference never becomes a memory.
- Original recordings outrank AI output.
- Memory Mode uses supported evidence only.
- Reflection Mode labels extrapolation.
- A time-scoped persona cannot know later events unless the interface explicitly leaves the historical role.
- Consent must be specific to purpose, data class and audience.
- Voice, face and identity models require separate explicit consent.
- Successor Trustees inherit duties and permissions, not the person's identity.
- Posthumous Verified Self cannot be silently edited.
- Export, delete, privacy and safety controls remain available without a premium plan.
- No dependency loops, guilt messages, artificial jealousy or simulated need.

## Engineering rules

- Architecture decisions are reflected in ADRs and domain documentation before
  or together with the corresponding code.
- Every new or changed Python module, class, dataclass, enum, function, method,
  helper, and test function requires a concise one-line English docstring.

## Current scope

The backend foundation and CI are in place. Trust Kernel v1 is implemented and
merged into `main`. Stage 1.2 Identity Assurance is in progress on
`feat/identity-assurance-v1`: canonical Identity entities, the immutable
evidence revocation fact, and Evidence Policy V1 are implemented in the feature
branch and pass their checks. Stage 1.2 is not complete; its stream validator,
effective assurance resolver, application layer, persistence, migrations, and
API remain unimplemented.

Digital Legacy Mode remains the first product direction. The primary product
path is a web MVP; mobile clients follow only after the backend and web flow are
stable. The MVP excludes real-time cloned voice/video and public profiles.

## First implementation target

Build a private web application for one creator and invited family members: authentication, Legacy creation, adaptive interview, original media storage, immutable timeline snapshots, provenance, consent receipts, evidence-backed text retrieval, export and succession-plan configuration.
