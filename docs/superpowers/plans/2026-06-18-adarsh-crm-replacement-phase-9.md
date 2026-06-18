# Adarsh CRM Replacement Phase 9 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a conditional contact-lens work-up, one order per visit, scheduled follow-up, patient history, and existing-billing handoff without changing normal spectacle workflows.

**Architecture:** Clinical contact-lens data remains in the existing visit exam-section record. New branch-scoped contact-lens-order and follow-up-task tables own operational state, while nullable bill linkage connects orders to the existing billing engine. The active `crm/` visit workspace receives one embedded tabbed component and reuses existing save, notification, vendor, billing, and history patterns.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Alembic, Pytest, React 18, TypeScript, TanStack Query, React Hook Form patterns, Vitest, React Testing Library, Tailwind CSS.

---

## File Map

**Backend create:**

- `backend/app/models/contact_lens_order.py`: contact-lens order and follow-up task persistence.
- `backend/app/repositories/contact_lens_repository.py`: shop-scoped order and follow-up queries.
- `backend/app/schemas/contact_lens.py`: structured work-up, order, follow-up, and context contracts.
- `backend/app/services/contact_lens_service.py`: activation, validation, draft saves, order transitions, follow-up scheduling, audit events, and serialization.
- `backend/alembic/versions/0013_contact_lens_workflow.py`: additive Phase 9 schema migration.
- `backend/tests/test_contact_lens_workflow.py`: backend Phase 9 behavior and isolation tests.

**Backend modify:**

- `backend/app/models/visit.py`, `customer.py`, `shop.py`, `bill.py`, `__init__.py`: additive relationships and linkage.
- `backend/app/models/enums.py`: follow-up status/type while reusing `DispensingOrderStatus`.
- `backend/app/db/base.py`: migration metadata registration.
- `backend/app/core/exam_sections.py`: conditional Contact Lens visibility helper.
- `backend/app/services/visit_exam_section_service.py`: dynamic visibility and completed work-up validation.
- `backend/app/services/bill_service.py`, `visit_billing_service.py`: contact-lens-order context validation and summaries.
- `backend/app/repositories/bill_repository.py`: active bill lookup for a contact-lens order.
- `backend/app/schemas/bill.py`, `visit.py`, `visit_billing.py`, `customer.py`: additive API fields and history summaries.
- `backend/app/services/visit_service.py`, `customer_service.py`: activation flag and patient history.
- `backend/app/api/v1/endpoints/visits.py`: contact-lens context, activation, work-up, order, status, and follow-up endpoints.

**CRM create:**

- `crm/src/pages/visits/components/ContactLensWorkspace.tsx`: embedded Phase 9 tabbed workspace.

**CRM modify:**

- `crm/src/types/visit.ts`, `bill.ts`, `customer.ts`: Phase 9 contracts.
- `crm/src/features/visits/api.ts`: Phase 9 endpoint functions.
- `crm/src/pages/visits/examSections.ts`: contact-lens form kind and options.
- `crm/src/pages/visits/components/ExamSectionNav.tsx`: conditional activation action.
- `crm/src/pages/visits/VisitWorkspacePage.tsx`: Contact Lens component and dirty-state integration.
- `crm/src/pages/customers/CustomerRecordsPage.tsx`: contact-lens and follow-up history.
- `crm/src/pages/billing/BillingPage.tsx`: contact-lens order context and item prefill.
- `crm/src/pages/visits/VisitWorkspacePage.test.tsx`, `crm/src/pages/billing/BillingPage.test.tsx`: Phase 9 UI behavior.

---

### Task 1: Backend Contract and Conditional Visibility

**Files:**
- Test: `backend/tests/test_contact_lens_workflow.py`
- Modify: `backend/app/models/visit.py`
- Modify: `backend/app/schemas/visit.py`
- Modify: `backend/app/services/visit_service.py`
- Modify: `backend/app/services/visit_exam_section_service.py`

- [ ] **Step 1: Write failing visibility tests**

Add tests that create ordinary, contact-lens-reason, and explicitly activated visits. Assert ordinary visits return `contact_lens.is_visible is False`; reason-matched and activated visits return `True`; all remain optional.

```python
def test_contact_lens_section_is_conditional(db_session, make_user):
    actor = make_user("phase9@example.com")
    ordinary = _create_visit(db_session, actor, "Routine spectacle check")
    contact_lens = _create_visit(db_session, actor, "Contact lens fitting")

    ordinary_section = _section(VisitExamSectionService(db_session, TEST_SHOP_ONE).list_sections(ordinary.id, actor), "contact_lens")
    contact_section = _section(VisitExamSectionService(db_session, TEST_SHOP_ONE).list_sections(contact_lens.id, actor), "contact_lens")

    assert ordinary_section.is_visible is False
    assert ordinary_section.is_optional is True
    assert contact_section.is_visible is True
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `venv/bin/python -m pytest tests/test_contact_lens_workflow.py -q`

Expected: failure because visit activation and dynamic visibility do not exist.

- [ ] **Step 3: Add the compatibility-safe visit flag**

Add `contact_lens_workup_requested: bool = False` to `Visit`, `VisitCreate`, `VisitRead`, and visit serialization/creation. Make section visibility true when the normalized reason contains `contact lens`, the flag is true, or an existing Contact Lens section record exists.

```python
def _contact_lens_visible(self, visit: Visit, record: VisitExamSection | None) -> bool:
    reason = visit.reason_for_visit.lower().replace("-", " ")
    return "contact lens" in reason or visit.contact_lens_workup_requested or record is not None
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `venv/bin/python -m pytest tests/test_contact_lens_workflow.py -q`

Expected: visibility tests pass.

---

### Task 2: Contact-Lens Order, Follow-Up, and Migration

**Files:**
- Create: `backend/app/models/contact_lens_order.py`
- Create: `backend/alembic/versions/0013_contact_lens_workflow.py`
- Modify: `backend/app/models/enums.py`
- Modify: `backend/app/models/visit.py`
- Modify: `backend/app/models/customer.py`
- Modify: `backend/app/models/shop.py`
- Modify: `backend/app/models/bill.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/db/base.py`
- Test: `backend/tests/test_contact_lens_workflow.py`

- [ ] **Step 1: Write failing schema tests**

Assert model metadata contains `contact_lens_orders`, `follow_up_tasks`, `bills.contact_lens_order_id`, one-order-per-visit uniqueness, and the partial active-bill uniqueness index.

- [ ] **Step 2: Run schema tests and verify RED**

Expected: missing model/table/column failures.

- [ ] **Step 3: Implement additive models**

Create `ContactLensOrder` with shop, visit, customer, vendor, reference, `DispensingOrderStatus`, JSON work-up snapshot, JSON lens data, notes, and user/timestamp tracking. Create `FollowUpTask` with shop, customer, visit, contact-lens order, due date, `pending/completed/cancelled` status, interval, notes, and completion metadata. Add nullable `Bill.contact_lens_order_id`.

- [ ] **Step 4: Add migration 0013**

Use Alembic batch mode for adding `visits.contact_lens_workup_requested` and `bills.contact_lens_order_id`, create both tables and indexes, and create PostgreSQL/SQLite partial uniqueness for active bills:

```python
postgresql_where=sa.text("contact_lens_order_id IS NOT NULL AND NOT is_deleted"),
sqlite_where=sa.text("contact_lens_order_id IS NOT NULL AND is_deleted = 0"),
```

- [ ] **Step 5: Run schema tests and a fresh SQLite migration**

Run:

```bash
venv/bin/python -m pytest tests/test_contact_lens_workflow.py -q
DATABASE_URL=sqlite+pysqlite:////tmp/eye_phase9.sqlite3 venv/bin/alembic upgrade head
```

Expected: tests pass and Alembic reaches revision `0013_contact_lens_workflow`.

---

### Task 3: Work-Up API and Validation

**Files:**
- Create: `backend/app/schemas/contact_lens.py`
- Create: `backend/app/repositories/contact_lens_repository.py`
- Create: `backend/app/services/contact_lens_service.py`
- Modify: `backend/app/services/visit_exam_section_service.py`
- Modify: `backend/app/api/v1/endpoints/visits.py`
- Test: `backend/tests/test_contact_lens_workflow.py`

- [ ] **Step 1: Write failing work-up tests**

Cover activation, right/left persistence, incomplete drafts, completed validation, `other` indication custom text, and cross-shop access.

```python
payload = ContactLensWorkupUpdate(
    state=ExamSectionState.INCOMPLETE,
    indication={"type": "refractive", "other": None},
    assessment={"right": {"k_reading": "43.25", "hvid_mm": "11.8", "tbut_seconds": "9"}, "left": {"k_reading": "43.75", "hvid_mm": "11.7", "tbut_seconds": "8"}},
    prescription={"right": {"power": "-2.00", "base_curve_mm": "8.6", "diameter_mm": "14.2"}, "left": {"power": "-1.75", "base_curve_mm": "8.6", "diameter_mm": "14.2"}},
    lens_details={"brand": "Acuvue", "material": "Senofilcon A", "replacement_schedule": "fortnightly", "wearing_schedule": "daily wear"},
    trial_training={"trial_lens_dispensed": True, "training_status": "completed", "notes": "Independent handling"},
)
```

- [ ] **Step 2: Run focused tests and verify RED**

Expected: contact-lens schemas/service/endpoints are missing.

- [ ] **Step 3: Implement context, activation, and work-up save**

Add:

- `GET /visits/{visit_id}/contact-lens`
- `POST /visits/{visit_id}/contact-lens/activate`
- `PUT /visits/{visit_id}/contact-lens/workup`

Persist work-up data into the existing `contact_lens` exam-section payload. Preserve incomplete drafts. Validate stricter completed states. Audit activation and saves.

- [ ] **Step 4: Run focused tests and verify GREEN**

Expected: work-up tests pass with branch isolation.

---

### Task 4: Order Lifecycle and Follow-Up Scheduling

**Files:**
- Modify: `backend/app/schemas/contact_lens.py`
- Modify: `backend/app/repositories/contact_lens_repository.py`
- Modify: `backend/app/services/contact_lens_service.py`
- Modify: `backend/app/api/v1/endpoints/visits.py`
- Test: `backend/tests/test_contact_lens_workflow.py`

- [ ] **Step 1: Write failing order and follow-up tests**

Cover one order per visit, required work-up values, safe status transitions, one-week/fifteen-day/one-month/custom due dates, repeated scheduling idempotency, completion preservation, and cross-shop denial.

- [ ] **Step 2: Run tests and verify RED**

Expected: order and follow-up methods/endpoints are absent.

- [ ] **Step 3: Implement order endpoints**

Add:

- `PUT /visits/{visit_id}/contact-lens/order`
- `POST /visits/{visit_id}/contact-lens/order/status`
- `PUT /visits/{visit_id}/contact-lens/follow-up`
- `POST /visits/{visit_id}/contact-lens/follow-up/status`

Reuse spectacle-order status transitions. Snapshot the current work-up when creating the order. Prevent work-up updates from mutating a non-draft order. Audit create/update/status/follow-up actions.

- [ ] **Step 4: Run focused tests and verify GREEN**

Expected: lifecycle, follow-up, and isolation tests pass.

---

### Task 5: Existing Billing Integration

**Files:**
- Modify: `backend/app/repositories/bill_repository.py`
- Modify: `backend/app/schemas/bill.py`
- Modify: `backend/app/schemas/visit_billing.py`
- Modify: `backend/app/services/bill_service.py`
- Modify: `backend/app/services/visit_billing_service.py`
- Modify: `backend/tests/test_visit_billing_integration.py`
- Test: `backend/tests/test_contact_lens_workflow.py`

- [ ] **Step 1: Write failing billing-link tests**

Create a contact-lens order, bill it with an existing `contact_lens` item, assert official totals remain in `Bill`, reject duplicate active bills, allow replacement after soft deletion, and reject cross-customer/shop context.

- [ ] **Step 2: Run billing tests and verify RED**

Expected: `contact_lens_order_id` is not accepted or resolved.

- [ ] **Step 3: Extend existing billing context**

Add optional `contact_lens_order_id` to create/read schemas. Resolve the order through the shop-scoped repository, derive its visit, verify customer equality, and keep all calculations in `BillService`. Extend visit billing context with `contact_lens_order_id` and `contact_lens_order_bill`.

- [ ] **Step 4: Run billing tests and verify GREEN**

Run: `venv/bin/python -m pytest tests/test_contact_lens_workflow.py tests/test_visit_billing_integration.py tests/test_customer_billing_crud.py -q`

Expected: all focused billing tests pass.

---

### Task 6: Patient History

**Files:**
- Modify: `backend/app/schemas/customer.py`
- Modify: `backend/app/services/customer_service.py`
- Modify: `backend/tests/test_contact_lens_workflow.py`

- [ ] **Step 1: Write a failing history test**

Assert same-shop customer detail includes contact-lens order status/reference/visit and follow-up due date/status while cross-shop customer detail remains inaccessible.

- [ ] **Step 2: Run and verify RED**

Expected: history response lacks contact-lens and follow-up summaries.

- [ ] **Step 3: Add compact history schemas and serialization**

Return historical summaries without exposing clinical notes in the list response. Preserve existing visits, referrals, prescriptions, and bills unchanged.

- [ ] **Step 4: Run and verify GREEN**

Expected: history tests pass.

---

### Task 7: CRM Contracts, Activation, and Embedded Workspace

**Files:**
- Modify: `crm/src/types/visit.ts`
- Modify: `crm/src/features/visits/api.ts`
- Modify: `crm/src/pages/visits/examSections.ts`
- Modify: `crm/src/pages/visits/components/ExamSectionNav.tsx`
- Create: `crm/src/pages/visits/components/ContactLensWorkspace.tsx`
- Modify: `crm/src/pages/visits/VisitWorkspacePage.tsx`
- Modify: `crm/src/pages/visits/VisitWorkspacePage.test.tsx`

- [ ] **Step 1: Write failing CRM tests**

Test that ordinary visits show only the conditional activation action, activation reveals Contact Lens, internal tabs render consistent paired-eye inputs, drafts save, save failures remain visible, trial/training persists, and unsaved navigation warns.

- [ ] **Step 2: Run and verify RED**

Run: `npm test -- --run src/pages/visits/VisitWorkspacePage.test.tsx`

Expected: activation action and Contact Lens workspace are missing.

- [ ] **Step 3: Add typed APIs and conditional activation**

Add functions for context, activation, work-up save, order save/status, and follow-up save/status. Extend `ExamSectionNav` with an explicit activation callback only for hidden Contact Lens.

- [ ] **Step 4: Build the embedded workspace**

Use five stable internal tabs: Work-up, Prescription, Trial & Training, Order, and Follow-up. Match existing matte-dark, restrained pink/indigo/emerald accents, 8px-or-less control radii, section save-state feedback, and right/left eye grids. Do not add modals or another sidebar.

- [ ] **Step 5: Run and verify GREEN**

Expected: visit workspace tests pass.

---

### Task 8: CRM Billing Handoff and Patient History

**Files:**
- Modify: `crm/src/types/bill.ts`
- Modify: `crm/src/types/customer.ts`
- Modify: `crm/src/pages/billing/BillingPage.tsx`
- Modify: `crm/src/pages/billing/BillingPage.test.tsx`
- Modify: `crm/src/pages/customers/CustomerRecordsPage.tsx`
- Modify: `crm/src/pages/customers/CustomersPage.test.tsx`

- [ ] **Step 1: Write failing billing and history UI tests**

Assert Contact Lens order navigation carries `visit_id` and `contact_lens_order_id`, prefills exactly one `contact_lens` item, submits through `createBill`, and customer history renders order/follow-up status.

- [ ] **Step 2: Run and verify RED**

Expected: billing context and history cards are absent.

- [ ] **Step 3: Extend the shared billing form**

Load contact-lens context when `contact_lens_order_id` is present. Prefill a safe item name from brand/material/replacement schedule with quantity one and zero unit price. Submit the order ID with the existing bill payload and preserve the validated return path.

- [ ] **Step 4: Render patient history summaries**

Add compact unframed history sections for contact-lens orders and follow-up tasks, using existing visit navigation for `Continue Visit`.

- [ ] **Step 5: Run and verify GREEN**

Expected: billing and patient-record tests pass.

---

### Task 9: Verification and Scope Review

**Files:**
- Review all Phase 9 files.

- [ ] **Step 1: Verify migration from a clean SQLite database**

Run: `DATABASE_URL=sqlite+pysqlite:////tmp/eye_phase9_final.sqlite3 venv/bin/alembic upgrade head`

Expected: revision 0013 applies successfully.

- [ ] **Step 2: Run backend checks**

```bash
venv/bin/python -m compileall -q app
venv/bin/ruff check app tests
venv/bin/python -m pytest -q
```

Expected: compile, lint, and all backend tests pass.

- [ ] **Step 3: Run CRM checks**

```bash
npm run typecheck
npm run lint
npm test
npm run build
```

Expected: typecheck, lint, all CRM tests, and production build pass.

- [ ] **Step 4: Review scope and diff**

Run `git diff --check` and inspect Phase 9 changes for duplicated billing logic, unconditional Contact Lens UI, cross-shop lookups, accidental spectacle-order changes, generated artifacts, or unrelated edits.

- [ ] **Step 5: Stop after Phase 9**

Report implementation, reused modules, changed files, visible behavior, compatibility, test evidence, limitations, and decisions for review. Do not begin another phase.
