# Fase 5 — Documentation Index

**Status (2026-09-18):** Fase 5 is implemented and formally closed — see
`docs/phases/phase-5-final-report.md` §41.K (`PHASE 5 — CLOSED`). This index predates
implementation and lists the pre-implementation design set only; it is kept for traceability of
the design order actually followed, not as a claim that Fase 5 is still pending. The final
report, the Definition of Done, the test matrix, and the implementation checklist/handoff
documents (added or updated during and after implementation) are not listed in §2 below — they
are the closure-time documents, read *after* this index's original set, not instead of it.

## 1. Purpose

This index defines the authoritative documentation set for Fase 5 and the recommended reading order.

## 2. Core documents

| Order | Document | Purpose |
|---:|---|---|
| 1 | `requirements.md` | Global requirements and Fase 5 functional requirements |
| 2 | `docs/phases/phase-5-documents.md` | Scope and functional boundary |
| 3 | `docs/design/care-request-domain.md` | Domain responsibilities and invariants |
| 4 | `docs/design/care-request-data-model.md` | Persistence model |
| 5 | `docs/design/care-request-workflow.md` | End-to-end workflow |
| 6 | `docs/design/care-request-permissions.md` | Authorization rules |
| 7 | `docs/design/care-request-security-and-privacy.md` | Security/privacy consolidation |
| 8 | `docs/design/care-request-service-contracts.md` | Internal service contracts |
| 9 | `docs/design/care-request-api-contracts.md` | External API contract |
| 10 | `docs/design/care-request-ux.md` | UX behavior |
| 11 | `docs/design/care-request-screens.md` | Concrete screen states |
| 12 | `docs/design/care-request-audit-and-history.md` | Audit behavior |
| 13 | `docs/phases/phase-5-testing-strategy.md` | Testing strategy and evidence |
| 14 | Related ADRs | Architectural decisions |
| 15 | `docs/phases/phase-5-design-freeze.md` | Final design certification |

## 3. Source-of-truth precedence

When documents overlap:

1. explicit approved architectural decisions and ADRs;
2. detailed Fase 5 contracts/data model/workflow;
3. requirements;
4. UX/screen documentation for presentation behavior;
5. implementation must follow the documented contracts rather than inventing new rules.

If two documents conflict, the conflict must be resolved before implementation continues.

## 4. Cross-phase references

Fase 5 reuses rather than duplicates:

- Agenda Fase 2 for slot/hold/appointment rules;
- authorization rules from ADR-004;
- integrity/transaction conventions from ADR-006;
- ClinicalDocument storage and file rules from Fase 4.

## 5. Out-of-scope references

The following remain outside Fase 5:

- waiting room/check-in;
- antivirus;
- orphan-file cleanup automation;
- independent CareRequest editing;
- new infrastructure such as Redis/Celery.

## 6. Status

This index is a navigation artifact. It does not create new requirements.
