# Adarsh CRM Replacement Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the main visit examination workspace with stable section navigation and independent draft saving.

**Architecture:** Reuse the Phase 2 `visits` foundation and add one shop-scoped `visit_exam_sections` draft table keyed by `visit_id + section_key`. The CRM workspace fetches visit context and all section drafts, renders one section at a time, and saves each section independently through `/visits/{visit_id}/exam-sections/{section_key}`.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pytest, React, Vite, TanStack Query, Vitest, React Testing Library.

---

### Task 1: Backend Section Draft Foundation

**Files:**
- Modify: `backend/app/models/enums.py`
- Create: `backend/app/models/visit_exam_section.py`
- Modify: `backend/app/models/visit.py`
- Modify: `backend/app/models/shop.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/db/base.py`
- Create: `backend/alembic/versions/0009_visit_exam_sections.py`
- Test: `backend/tests/test_visit_exam_sections.py`

- [x] **Step 1: Write failing backend tests**

  Cover section registry, saving/reopening draft data, cross-shop denial, invalid section keys, and IOP disabled/future status.

- [x] **Step 2: Run backend test to verify RED**

  Run: `cd backend && venv/bin/pytest tests/test_visit_exam_sections.py -q`

  Expected: FAIL because exam section models/services are not available.

- [x] **Step 3: Add model and migration**

  Add `VisitExamSection` with `shop_id`, `shop_key`, `visit_id`, `section_key`, `state`, `payload`, and user/timestamp mixins. Add unique constraint on `visit_id + section_key`.

- [x] **Step 4: Run backend test to verify GREEN**

  Run: `cd backend && venv/bin/pytest tests/test_visit_exam_sections.py -q`

### Task 2: Backend Section API

**Files:**
- Create: `backend/app/core/exam_sections.py`
- Create: `backend/app/repositories/visit_exam_section_repository.py`
- Create: `backend/app/schemas/visit_exam_section.py`
- Create: `backend/app/services/visit_exam_section_service.py`
- Modify: `backend/app/api/v1/endpoints/visits.py`
- Test: `backend/tests/test_visit_exam_sections.py`

- [x] **Step 1: Define registry**

  Include every Phase 3 section, mark optional/not-applicable capable sections, keep IOP as disabled future-only, and keep contact lens hidden unless relevant.

- [x] **Step 2: Add service and repository**

  Scope every section lookup through the existing visit shop context and save sections independently.

- [x] **Step 3: Add endpoints**

  Add `GET /visits/{visit_id}/exam-sections` and `PUT /visits/{visit_id}/exam-sections/{section_key}`.

### Task 3: CRM Workspace Shell

**Files:**
- Modify: `crm/src/types/visit.ts`
- Modify: `crm/src/features/visits/api.ts`
- Create: `crm/src/pages/visits/examSections.ts`
- Create: `crm/src/pages/visits/components/ExamSectionNav.tsx`
- Create: `crm/src/pages/visits/components/SectionSaveBar.tsx`
- Create: `crm/src/pages/visits/components/EyeEntryGrid.tsx`
- Create: `crm/src/pages/visits/components/ClinicalSelect.tsx`
- Modify: `crm/src/pages/visits/VisitWorkspacePage.tsx`
- Test: `crm/src/pages/visits/VisitWorkspacePage.test.tsx`

- [x] **Step 1: Write failing frontend test**

  Mock visit and exam-section APIs, then verify the workspace renders all planned sections, keeps IOP disabled, hides contact-lens content initially, and shows save actions.

- [x] **Step 2: Run frontend test to verify RED**

  Run: `cd crm && npm test -- src/pages/visits/VisitWorkspacePage.test.tsx`

- [x] **Step 3: Implement workspace**

  Add sticky visit context, left section navigation, per-section forms, reusable eye-entry grid, optional/not-applicable toggles, unsaved-change warning, and visible save states.

- [x] **Step 4: Run frontend test to verify GREEN**

  Run: `cd crm && npm test -- src/pages/visits/VisitWorkspacePage.test.tsx`

### Task 4: Verification

**Files:**
- Read/Run only.

- [x] **Step 1: Backend**

  Run: `cd backend && venv/bin/python -m compileall app`

  Run: `cd backend && venv/bin/pytest -q`

- [x] **Step 2: Frontend**

  Run: `cd crm && npm test`

  Run: `cd crm && npm run typecheck`

  Run: `cd crm && npm run build`

- [x] **Step 3: Diff review**

  Run: `git diff --check` and `git status --short`.
