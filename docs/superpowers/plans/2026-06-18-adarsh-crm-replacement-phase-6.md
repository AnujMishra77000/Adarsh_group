# Adarsh CRM Replacement Phase 6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add auditable, versioned final prescriptions, current-only patient PDFs, and explicit visit completion without changing legacy prescription behavior.

**Architecture:** Introduce a visit-linked prescription-version aggregate as the authority for new encounter prescriptions. Reuse visit/customer/shop scoping, examination JSON payloads, audit logging, protected file storage, and the active CRM workspace; leave the legacy prescription model and routes intact.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, React, TypeScript, TanStack Query, Vitest, React Testing Library.

---

### Task 1: Versioned prescription persistence

**Files:**
- Modify: `backend/app/models/enums.py`
- Create: `backend/app/models/visit_prescription.py`
- Modify: `backend/app/models/visit.py`
- Modify: `backend/app/models/shop.py`
- Modify: `backend/app/db/base.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/0010_visit_prescription_versions.py`
- Test: `backend/tests/test_visit_prescriptions.py`

- [x] Write a failing model/service test that expects version 1 draft storage and a unique visit/version identity.
- [x] Run `venv/bin/pytest -q tests/test_visit_prescriptions.py` from `backend` and confirm failure because the model/service does not exist.
- [x] Add `PrescriptionVersionStatus` and the `VisitPrescription` model with visit/customer/shop ownership, JSON prescription data, instructions, version metadata, finalization metadata, and internal PDF reference.
- [x] Add relationships and Alembic migration `0010` with indexes and constraints.
- [x] Re-run the focused test and confirm persistence passes.

### Task 2: Draft, review, finalization, amendments, and completion

**Files:**
- Create: `backend/app/repositories/visit_prescription_repository.py`
- Create: `backend/app/schemas/visit_prescription.py`
- Create: `backend/app/services/visit_prescription_service.py`
- Modify: `backend/app/services/visit_exam_section_service.py`
- Modify: `backend/app/services/visit_service.py`
- Modify: `backend/app/api/v1/endpoints/visits.py`
- Test: `backend/tests/test_visit_prescriptions.py`

- [x] Add failing tests for incomplete draft saves, strict finalization validation, `confirmed=true`, finalized immutability, amendment version creation, previous-version supersession, history/current flags, shop isolation, and visit completion.
- [x] Run the focused tests and verify each failure is caused by missing Phase 6 behavior.
- [x] Implement shop-scoped repository methods for visit history, active draft, current finalized version, and next version number.
- [x] Implement schemas and a service that saves drafts, assembles review warnings/summaries, finalizes transactionally, creates amendments by copying the current version, and completes visits.
- [x] Reject generic final-prescription section edits after finalization and reject exam-section edits after visit completion.
- [x] Add visit endpoints for history/current draft, draft save, review, finalize, amendment, and completion.
- [x] Re-run focused backend tests until green, then run existing visit tests for regression coverage.

### Task 3: Current-version patient PDF

**Files:**
- Create: `backend/app/services/visit_prescription_pdf_service.py`
- Modify: `backend/app/services/visit_prescription_service.py`
- Modify: `backend/app/api/v1/endpoints/visits.py`
- Test: `backend/tests/test_visit_prescriptions.py`

- [x] Add failing tests proving drafts cannot generate PDFs, current-version resolution changes after amendment, and cross-shop users cannot download documents.
- [x] Run the focused tests and verify expected failures.
- [x] Build the patient-only PDF from the current finalized snapshot with patient, branch, date, examiner, version, distance/near values, PD/fitting values, and instructions.
- [x] Add protected current PDF generate/download endpoints and audit PDF generation.
- [x] Re-run focused tests and verify current-only and isolation behavior.

### Task 4: CRM prescription API and types

**Files:**
- Modify: `crm/src/types/visit.ts`
- Modify: `crm/src/features/visits/api.ts`
- Test: `crm/src/pages/visits/VisitWorkspacePage.test.tsx`

- [x] Add failing UI tests using mocked Phase 6 APIs for version history, review data, finalize confirmation, amendment creation, and completion.
- [x] Run `npm test -- --run src/pages/visits/VisitWorkspacePage.test.tsx` from `crm` and confirm missing UI/API behavior.
- [x] Add TypeScript types for prescription data, versions, review, warnings, and confirmation payloads.
- [x] Add API functions for load/save/review/finalize/amend/PDF/complete endpoints.

### Task 5: Final prescription workspace

**Files:**
- Create: `crm/src/pages/visits/components/FinalPrescriptionWorkspace.tsx`
- Modify: `crm/src/pages/visits/VisitWorkspacePage.tsx`
- Modify: `crm/src/pages/visits/examSections.ts`
- Test: `crm/src/pages/visits/VisitWorkspacePage.test.tsx`

- [x] Implement separate distance and near right/left eye grids, PD/fitting values, and patient instructions using existing clinical controls.
- [x] Add a structured review panel with patient/visit/examiner, core summaries, referral, instructions, and warning list.
- [x] Require an explicit browser confirmation before finalization and visit completion.
- [x] Render finalized versions read-only, clearly label the current version, show historical statuses, and expose Start Amendment rather than edit controls.
- [x] Connect current PDF generation/download without exposing legacy or stale files as current.
- [x] Run the focused CRM test until all Phase 6 and existing workspace tests pass.

### Task 6: Verification and phase stop

**Files:**
- Review all Phase 6 files and `git diff` only; do not alter unrelated dirty files.

- [x] Run `venv/bin/python -m compileall app`, `venv/bin/ruff check app tests`, and `venv/bin/pytest -q` from `backend`.
- [x] Run `npm run lint`, `npm run typecheck`, `npm test`, and `npm run build` from `crm`.
- [x] Run `git diff --check` and inspect the Phase 6 diff for legacy data changes or accidental scope expansion.
- [x] Update every checklist item with its final status and stop after Phase 6.
