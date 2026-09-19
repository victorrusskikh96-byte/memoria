# Identity, Consent, Ownership and Succession System v0.1

## 1. Why these concepts form one system

Identity answers **who** is acting and who the data represents. Consent answers **what action** that person allowed. Ownership answers **who controls which object and rights**. Succession answers **how bounded control changes** after incapacity or death.

No operation is valid from one concept alone. Each sensitive operation must pass one policy decision:

`Allow = verified actor + valid authority + active consent + permitted object right + valid lifecycle state + recorded audit event`

## 2. Domain entities

| Entity | Purpose |
|---|---|
| Human Subject | Real person represented in the Legacy |
| Account | Authentication identity used to access Memoria |
| Canonical Legacy | Authoritative record attached to one verified subject |
| Evidence Object | Photo, recording, document, transcript or statement |
| Life Snapshot | Immutable state for a defined life period |
| Relationship Edge | Time-bounded relationship between people |
| Consent Receipt | Versioned authorization for a defined purpose |
| Rights Record | Ownership, license, access or stewardship claim |
| Succession Plan | Creator-authored post-incapacity and post-death instructions |
| Authority Grant | Narrow permission assigned to a contributor or trustee |
| Audit Event | Append-only record of a sensitive action |

## 3. Roles

| Role | May do | May not do |
|---|---|---|
| Creator | Create, correct, consent, revoke, export, delete, appoint trustees | Claim exclusive rights over third-party contributions without a license |
| Contributor | Add permitted memories or media | Convert contribution into Verified Self; access unrelated data |
| Viewer / Beneficiary | View permitted content | Export, train, clone or redistribute unless separately authorized |
| Guardian | Act for a minor or legally dependent subject within local law | Grant irreversible adult likeness rights beyond necessity |
| Successor Trustee | Execute the succession plan after activation | Own the identity; rewrite Verified Self; expand their own authority |
| Verification Reviewer | Validate an activation claim | Browse Legacy content beyond evidence needed for verification |
| Memoria Operator | Provide the service under least privilege | Use private content for advertising or general model training by default |

## 4. Assurance levels

| Level | Evidence | Permitted use |
|---|---|---|
| A0 | Unverified session | Explore product; no canonical Legacy publication |
| A1 | Verified account channel | Create draft, upload low-risk content |
| A2 | Strong account authentication plus identity evidence | Establish canonical Legacy, appoint trustees, manage sensitive consent |
| A3 | Step-up verification and independent evidence | Activate succession, export critical data, delete canonical Legacy, authorize biometric model creation |

Biometric verification is not a routine five-year event. A Life Chapter capture can update appearance and voice without creating or retaining a reusable verification template.

## 5. Consent model

Each receipt contains:

- grantor and represented subject;
- requesting product capability;
- exact purpose;
- data classes and selected items;
- allowed processors and recipient groups;
- output type, including text, synthetic voice, image or video;
- start, expiry and review date;
- revocation behavior and deletion obligations;
- jurisdiction and policy version;
- proof of notice and affirmative action.

Bundled consent is prohibited for identity verification, private-memory retrieval, voice cloning, likeness generation, family sharing, research and general model training.

## 6. Rights model

Memoria separates five rights:

1. **Identity authority**: only the verified subject can establish the canonical representation while capable.
2. **Content ownership**: the uploader must identify ownership or license for each contribution.
3. **Privacy interest**: people mentioned in a memory may hold rights even when they do not own the file.
4. **Processing permission**: consent authorizes a purpose; it does not transfer ownership.
5. **Stewardship authority**: a trustee may perform named duties after activation; stewardship does not transfer personality or likeness ownership.

## 7. Succession lifecycle

| State | Meaning | Allowed changes |
|---|---|---|
| Draft | Legacy setup is incomplete | Creator edits freely |
| Active | Creator controls the Legacy | Normal creation, sharing, export and revocation |
| Safeguard Hold | Incapacity or death signal received | High-risk actions paused; existing private access preserved |
| Verification Pending | Evidence and trustee authority are checked | Verification-only access; no model training or public release |
| Memorial | Trigger verified and plan activated | Verified Self locked; trustees execute bounded instructions |
| Disputed | Conflicting claims or legal challenge | Freeze nonessential mutations and disclosures |
| Archived / Exported | Service use ends but package remains usable elsewhere | Integrity verification and authorized retrieval |
| Deleted | Deletion instruction completed subject to lawful retention | Only minimal deletion audit retained where required |

## 8. Activation controls

Succession activation requires:

- a creator-authored plan that names primary and backup trustees;
- step-up verification of the claimant;
- independent evidence of incapacity or death appropriate to jurisdiction;
- a cooling period for reversible mistakes;
- notice to other designated parties;
- dual approval for high-risk actions when the creator selected it;
- an immutable activation record;
- a dispute path that freezes risky actions.

Inactivity alone cannot prove death. It may trigger a check-in and Safeguard Hold, never automatic memorialization.

## 9. Posthumous integrity

After Memorial activation:

- self-recorded snapshots and direct evidence become read-only;
- trustees may add clearly attributed family memories, annotations and corrections;
- the system never merges posthumous contributions into Verified Self;
- new AI outputs remain derivatives with model, prompt, evidence and timestamp provenance;
- voice or video generation follows the creator's explicit pre-death authorization;
- the creator's deletion, access and future-message instructions prevail unless law requires otherwise.

## 10. Operational authorization examples

| Operation | Required authority | Required consent | Additional control |
|---|---|---|---|
| Add a text memory | Creator or scoped contributor | Memory storage | Provenance record |
| Record a Life Chapter | Creator | Interview and media processing | Snapshot becomes immutable after confirmation |
| Share a story with child | Creator or authorized trustee | Named audience | Relationship-aware access |
| Train a private retrieval index | Service processor | Private AI retrieval | Derived data deletion on revocation |
| Create synthetic voice | Creator at A3 | Separate voice consent | Watermark/provenance and permitted audiences |
| Activate Memorial state | Verified trustee/reviewer | Succession plan | Evidence, cooling period, audit |
| Edit a self-recorded snapshot after death | Nobody | Not applicable | Prohibited; annotation only |
| Export full Legacy | Creator or explicitly authorized trustee | Export | Step-up authentication, encrypted package |

## 11. Core policy engine inputs

Every sensitive request should evaluate:

- actor identity and assurance level;
- actor role and authority grant;
- subject identity;
- resource ownership and data class;
- requested purpose and output modality;
- consent status and version;
- Legacy lifecycle state;
- selected life period and relationship context;
- jurisdictional restrictions;
- risk flags, dispute status and retention duties.

The decision and reason code must enter the audit log.

## 12. Failure posture

When identity, consent, ownership or succession evidence conflicts, the system fails closed for disclosure, cloning, deletion and authority transfer. It may preserve data temporarily to prevent irreversible loss while the dispute is resolved.
