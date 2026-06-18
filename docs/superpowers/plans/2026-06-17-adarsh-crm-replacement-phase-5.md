# Adarsh CRM Replacement Phase 5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement advanced optional clinical sections for binocular vision, cycloplegic refraction, torch-light evaluation, slit-lamp evaluation, and referral while keeping routine visits unblocked.

**Architecture:** Continue using the existing shop-scoped `visit_exam_sections` JSON draft storage. Add backend validation only for completed advanced sections, keep draft saves lenient, and expose referral summaries from saved referral exam-section payloads through the existing patient detail response. Extend the active CRM workspace (`crm/`) with structured conditional forms instead of adding new pages or tables.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Pytest, React, Vite, TanStack Query, Vitest, React Testing Library.

---

### Task 1: Backend Advanced Section Validation

**Files:**
- Modify: `backend/app/services/visit_exam_section_service.py`
- Test: `backend/tests/test_visit_exam_sections.py`

- [x] **Step 1: Write failing backend tests**

  Add tests that prove:
  - completed cycloplegic refraction validates only when `performed` is true,
  - completed torch-light evaluation rejects conflicting normal and abnormal values,
  - completed slit-lamp evaluation rejects conflicting normal and abnormal values,
  - incomplete drafts can still save conflicting or incomplete payloads.

- [x] **Step 2: Run backend test to verify RED**

  Run: `cd backend && venv/bin/pytest tests/test_visit_exam_sections.py -q`

- [x] **Step 3: Implement validation**

  Add section-specific validation inside `VisitExamSectionService`:
  - `cycloplegic_refraction`: if `performed` is true, require `drug_used`, `time_instilled`, and validate right/left refraction values using the existing refraction validator; if `performed` is false or `not_done` is true, do not require drug or result fields.
  - `torch_light_evaluation`: reject any structure where `normal` is true and abnormal findings/custom notes are also present.
  - `slit_lamp_evaluation`: reject any eye/structure where `normal` is true and abnormal findings/custom notes are also present.
  - Leave `iop_future` disabled.

- [x] **Step 4: Run backend test to verify GREEN**

  Run: `cd backend && venv/bin/pytest tests/test_visit_exam_sections.py -q`

### Task 2: Referral In Patient History

**Files:**
- Modify: `backend/app/schemas/customer.py`
- Modify: `backend/app/repositories/customer_repository.py`
- Modify: `backend/app/services/customer_service.py`
- Modify: `crm/src/types/customer.ts`
- Modify: `crm/src/pages/customers/CustomerRecordsPage.tsx`
- Test: `backend/tests/test_patient_visit_foundation.py`

- [x] **Step 1: Write failing backend test**

  Add a patient detail test proving that a saved referral exam section appears in `CustomerDetailRead.referrals` with visit id/date, specialist type, referral status, notes, and follow-up.

- [x] **Step 2: Run backend test to verify RED**

  Run: `cd backend && venv/bin/pytest tests/test_patient_visit_foundation.py -q`

- [x] **Step 3: Implement referral summaries**

  Eager-load visit exam sections in `CustomerRepository.get_detail`, add `CustomerReferralSummary`, collect saved `referral` payloads in `CustomerService.get_customer`, and render them in `CustomerRecordsPage`.

- [x] **Step 4: Run backend test to verify GREEN**

  Run: `cd backend && venv/bin/pytest tests/test_patient_visit_foundation.py -q`

### Task 3: CRM Advanced Clinical Forms

**Files:**
- Modify: `crm/src/pages/visits/examSections.ts`
- Modify: `crm/src/pages/visits/VisitWorkspacePage.tsx`
- Test: `crm/src/pages/visits/VisitWorkspacePage.test.tsx`

- [x] **Step 1: Write failing frontend tests**

  Add tests that prove:
  - binocular vision has all requested fields,
  - cycloplegic fields are hidden when not done and visible when performed,
  - torch-light evaluation exposes lids/conjunctiva/cornea/pupil normal/abnormal inputs,
  - slit-lamp evaluation exposes right/left eye structure inputs and cataract grading,
  - referral exposes specialist type, status, notes, and follow-up fields,
  - IOP remains disabled.

- [x] **Step 2: Run frontend test to verify RED**

  Run: `cd crm && npm test -- src/pages/visits/VisitWorkspacePage.test.tsx`

- [x] **Step 3: Implement advanced forms**

  Extend `SECTION_FORM_KIND` with `binocular`, `torch-light`, and `slit-lamp`. Add constants for clinical options. Implement focused render helpers in `VisitWorkspacePage` using existing `ClinicalSelect`, `TextField`, `TextAreaField`, and `EyeEntryGrid`.

- [x] **Step 4: Run frontend test to verify GREEN**

  Run: `cd crm && npm test -- src/pages/visits/VisitWorkspacePage.test.tsx`

### Task 4: Verification

**Files:**
- Read/Run only.

- [x] **Step 1: Backend verification**

  Run:
  - `cd backend && venv/bin/python -m compileall app`
  - `cd backend && venv/bin/ruff check app tests`
  - `cd backend && venv/bin/pytest -q`

- [x] **Step 2: CRM verification**

  Run:
  - `cd crm && npm run lint`
  - `cd crm && npm run typecheck`
  - `cd crm && npm test`
  - `cd crm && npm run build`

- [x] **Step 3: Diff review**

  Run:
  - `git diff --check`
  - `git status --short`
