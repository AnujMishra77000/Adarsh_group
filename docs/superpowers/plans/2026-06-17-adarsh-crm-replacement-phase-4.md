# Adarsh CRM Replacement Phase 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the core normal-refraction examination sections end to end while preserving incomplete drafts and historical data.

**Architecture:** Continue using Phase 3 `visit_exam_sections` draft storage. Add backend validation for completed core sections and add a shop-scoped previous-exam history endpoint that reads earlier visit section records for the same patient without copying them into the current visit.

**Tech Stack:** FastAPI, SQLAlchemy, Pytest, React, Vite, TanStack Query, Vitest, React Testing Library.

---

### Task 1: Backend Core Clinical Validation And History

**Files:**
- Modify: `backend/app/repositories/visit_exam_section_repository.py`
- Modify: `backend/app/schemas/visit_exam_section.py`
- Modify: `backend/app/services/visit_exam_section_service.py`
- Modify: `backend/app/api/v1/endpoints/visits.py`
- Test: `backend/tests/test_visit_exam_sections.py`

- [x] **Step 1: Write failing backend tests**

  Add tests that incomplete drafts with invalid optical details can save, completed refraction sections reject invalid axis/optical values with clear messages, and previous visit values are returned shop-scoped.

- [x] **Step 2: Run backend test to verify RED**

  Run: `cd backend && venv/bin/pytest tests/test_visit_exam_sections.py -q`

- [x] **Step 3: Implement validation and history**

  Validate only completed core sections. Return previous visual acuity/refraction/potential vision section drafts for the same patient, excluding the current visit.

- [x] **Step 4: Run backend test to verify GREEN**

  Run: `cd backend && venv/bin/pytest tests/test_visit_exam_sections.py -q`

### Task 2: CRM Core Clinical Workspace

**Files:**
- Modify: `crm/src/types/visit.ts`
- Modify: `crm/src/features/visits/api.ts`
- Modify: `crm/src/pages/visits/examSections.ts`
- Modify: `crm/src/pages/visits/components/EyeEntryGrid.tsx`
- Modify: `crm/src/pages/visits/VisitWorkspacePage.tsx`
- Test: `crm/src/pages/visits/VisitWorkspacePage.test.tsx`

- [x] **Step 1: Write failing frontend tests**

  Add tests for Visual Acuity fields, Objective Refraction method/axis fields, previous-values panel, and visible validation failure.

- [x] **Step 2: Run frontend test to verify RED**

  Run: `cd crm && npm test -- src/pages/visits/VisitWorkspacePage.test.tsx`

- [x] **Step 3: Implement workspace details**

  Add distance/near/both-eyes/contact-lens visual acuity fields, objective method dropdown, subjective/potential vision fields, keyboard-friendly row layout, and previous-values display.

- [x] **Step 4: Run frontend test to verify GREEN**

  Run: `cd crm && npm test -- src/pages/visits/VisitWorkspacePage.test.tsx`

### Task 3: Verification

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
