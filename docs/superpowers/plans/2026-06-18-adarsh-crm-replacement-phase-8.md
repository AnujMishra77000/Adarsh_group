# Phase 8 Billing and Payment Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect visits and dispensing orders to the existing billing flow without duplicating calculations, payments, or invoices.

**Architecture:** Bills gain nullable visit and dispensing-order foreign keys. A focused integration service validates and links context while `BillService` remains the only financial authority. The CRM visit/order workspaces hand off to the existing billing pages and display read-only summaries sourced from bills.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, React, TypeScript, TanStack Query, React Router, Vitest.

---

### Task 1: Backend linkage contract

**Files:**
- Create: `backend/tests/test_visit_billing_integration.py`
- Modify: `backend/app/models/bill.py`
- Modify: `backend/app/schemas/bill.py`
- Create: `backend/alembic/versions/0012_visit_billing_integration.py`

- [ ] Write failing tests proving contextual bill creation preserves existing item/payment calculations, legacy bills have null links, and one active bill is allowed per dispensing order.
- [ ] Run `venv/bin/python -m pytest tests/test_visit_billing_integration.py -q` and verify failure because linkage fields are absent.
- [ ] Add nullable `visit_id` and `dispensing_order_id` foreign keys and the partial active-order uniqueness index.
- [ ] Add the fields to create/read schemas and an additive migration.
- [ ] Re-run the focused tests until the model contract passes.

### Task 2: Context validation and existing-bill linking

**Files:**
- Create: `backend/app/schemas/visit_billing.py`
- Create: `backend/app/services/visit_billing_service.py`
- Modify: `backend/app/services/bill_service.py`
- Modify: `backend/app/repositories/bill_repository.py`
- Modify: `backend/app/api/v1/endpoints/visits.py`

- [ ] Add failing tests for same-customer/shop validation, no-mutation existing-bill linking, duplicate active-order rejection, and replacement after soft deletion.
- [ ] Implement shop-scoped context validation used by bill creation and link endpoints.
- [ ] Add visit billing context and link-existing-bill endpoints.
- [ ] Ensure audit logs capture context creation/linking without financial snapshots outside the existing bill audit.
- [ ] Run the focused backend tests and existing billing tests.

### Task 3: Shared CRM billing handoff

**Files:**
- Modify: `crm/src/types/bill.ts`
- Modify: `crm/src/features/bills/api.ts`
- Modify: `crm/src/features/visits/api.ts`
- Create: `crm/src/pages/visits/components/VisitBillingWorkspace.tsx`
- Modify: `crm/src/pages/visits/VisitWorkspacePage.tsx`
- Modify: `crm/src/pages/visits/components/DispensingOrderWorkspace.tsx`
- Modify: `crm/src/pages/billing/BillingPage.tsx`
- Modify: `crm/src/pages/billing/BillingDetailPage.tsx`
- Test: `crm/src/pages/visits/VisitWorkspacePage.test.tsx`
- Create: `crm/src/pages/billing/BillingPage.test.tsx`

- [ ] Add failing tests for create/open/link actions, contextual item suggestions, payload linkage, official bill summaries, and return navigation.
- [ ] Implement typed context APIs and the compact visit billing panel.
- [ ] Pass visit/order context into the existing Billing page and keep all price, discount, GST, payment, and invoice controls there.
- [ ] Navigate created bills to the existing detail page and preserve a safe `/crm/...` return path.
- [ ] Run focused CRM tests.

### Task 4: Verification

**Files:**
- Review all Phase 8 changes only.

- [ ] Run backend compile, Ruff, full pytest, and a fresh Alembic migration through revision `0012`.
- [ ] Run CRM typecheck, ESLint, full Vitest, and production build.
- [ ] Run `git diff --check` and inspect the diff for accidental billing-engine duplication or unrelated changes.
- [ ] Report results and stop after Phase 8.
