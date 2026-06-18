# Adarsh CRM Replacement Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the old customer quick-create path with a patient search, patient registration, visit start, and visit workspace foundation.

**Architecture:** Keep the existing `customers` table as the long-term patient record and add a separate `visits` tenant-owned table for visit-specific data. The active CRM is `crm/`; legacy prescription and billing modules remain available under their existing `/crm/...` routes.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pytest, React, Vite, TanStack Query, React Hook Form, Vitest, React Testing Library.

---

### Task 1: Backend Patient/Visit Data Foundation

**Files:**
- Modify: `backend/app/models/enums.py`
- Modify: `backend/app/models/customer.py`
- Create: `backend/app/models/visit.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/db/base.py`
- Create: `backend/alembic/versions/0008_patient_visit_foundation.py`
- Test: `backend/tests/test_patient_visit_foundation.py`

- [x] **Step 1: Write failing backend tests**

  Cover patient registration idempotency, visit idempotency, shop-scoped visit reads, customer history visits, and staff examiner assignment restrictions.

- [x] **Step 2: Run backend test to verify RED**

  Run: `cd backend && venv/bin/pytest tests/test_patient_visit_foundation.py -q`

  Expected: FAIL because `VisitStatus` / visit modules are not available.

- [x] **Step 3: Add visit model and migration**

  Add `VisitStatus`, nullable patient-level additions on `Customer`, and a new `Visit` model with `shop_id`, `shop_key`, `customer_id`, `visit_date`, `reason_for_visit`, `referred_by`, `assigned_examiner_id`, `visit_notes`, `status`, and `idempotency_key`.

- [x] **Step 4: Run backend test to verify GREEN**

  Run: `cd backend && venv/bin/pytest tests/test_patient_visit_foundation.py -q`

  Expected: PASS.

### Task 2: Backend Visit API and Customer History

**Files:**
- Modify: `backend/app/repositories/customer_repository.py`
- Create: `backend/app/repositories/visit_repository.py`
- Modify: `backend/app/schemas/customer.py`
- Create: `backend/app/schemas/visit.py`
- Modify: `backend/app/services/customer_service.py`
- Create: `backend/app/services/visit_service.py`
- Create: `backend/app/api/v1/endpoints/visits.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_patient_visit_foundation.py`

- [x] **Step 1: Add visit service and repository**

  Scope every visit query by current `shop_key`, use customer lookup to enforce branch isolation, and use `idempotency_key` to prevent duplicate draft visits from repeated submissions.

- [x] **Step 2: Extend customer detail response**

  Add visit history to `CustomerDetailRead` while preserving existing prescriptions and bills.

- [x] **Step 3: Expose visit endpoints**

  Add `POST /api/v1/visits`, `GET /api/v1/visits/{visit_id}`, and `GET /api/v1/visits/customer/{customer_id}` behind existing admin/staff authentication and shop context.

- [x] **Step 4: Run backend verification**

  Run: `cd backend && venv/bin/pytest tests/test_patient_visit_foundation.py -q`

  Expected: PASS.

### Task 3: CRM Patient Workflow

**Files:**
- Modify: `crm/src/types/customer.ts`
- Create: `crm/src/types/visit.ts`
- Create: `crm/src/features/visits/api.ts`
- Modify: `crm/src/pages/customers/CustomersPage.tsx`
- Test: `crm/src/pages/customers/CustomersPage.test.tsx`

- [x] **Step 1: Write failing frontend test**

  Verify `CustomersPage` renders "Search Patient", "New Patient", and "Start New Visit", and does not render the old quick prescription/bill controls.

- [x] **Step 2: Run frontend test to verify RED**

  Run: `cd crm && npm test -- src/pages/customers/CustomersPage.test.tsx`

  Expected: FAIL because the old "Create Customer" page is still rendered.

- [x] **Step 3: Replace primary customer form**

  Build a guided patient workflow that searches existing customers, registers new patients with only patient-level fields, starts visits with visit-level fields, and uses idempotency keys.

- [x] **Step 4: Run frontend test to verify GREEN**

  Run: `cd crm && npm test -- src/pages/customers/CustomersPage.test.tsx`

  Expected: PASS.

### Task 4: Visit Workspace and History Links

**Files:**
- Modify: `crm/src/lib/routes.ts`
- Modify: `crm/src/app/router.tsx`
- Create: `crm/src/pages/visits/VisitWorkspacePage.tsx`
- Modify: `crm/src/pages/customers/CustomerRecordsPage.tsx`
- Optional Modify: `crm/src/components/ui/Sidebar.tsx`

- [x] **Step 1: Add visit workspace route**

  Add `/crm/visits/:visitId` and fetch the visit by authenticated shop context.

- [x] **Step 2: Show patient visit history**

  Add visit history to the customer records detail view while keeping prescription and billing history visible.

- [x] **Step 3: Add continue action**

  Link draft or in-progress visits to the workspace shell.

### Task 5: Verification

**Files:**
- Read/Run only.

- [x] **Step 1: Backend focused tests**

  Run: `cd backend && venv/bin/pytest tests/test_patient_visit_foundation.py -q`

- [x] **Step 2: Backend syntax**

  Run: `cd backend && venv/bin/python -m compileall app`

- [x] **Step 3: Frontend focused tests**

  Run: `cd crm && npm test -- src/pages/customers/CustomersPage.test.tsx`

- [x] **Step 4: Frontend typecheck**

  Run: `cd crm && npm run typecheck`

- [x] **Step 5: Broader relevant checks if focused checks pass**

  Run existing customer/auth/router tests that cover the touched flow.
