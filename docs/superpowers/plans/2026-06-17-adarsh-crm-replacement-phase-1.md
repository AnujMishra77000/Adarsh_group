# Adarsh CRM Replacement Phase 1 Repository Verification Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement future phase plans task-by-task. Steps in future execution plans should use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Document the current Adarsh Optical Group CRM flow and define a safe, phased replacement plan without building the new clinical workflow yet.

**Architecture:** The current system is a FastAPI backend with service/repository boundaries and an active React/Vite CRM app in `crm/`. The replacement must introduce patient visits, clinical examination sections, final prescription versioning, dispensing orders, billing integration, delivery, and follow-up while preserving current customer, prescription, bill, PDF, WhatsApp, audit, and shop-isolation behavior.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, PostgreSQL/SQLite, React, Vite, TypeScript, Tailwind, TanStack Query, React Hook Form, Zod, Vitest, pytest.

---

## Phase 1 Scope

This document is Phase 1 only. It verifies the repository and defines the implementation plan. It does not add clinical workflow models, routes, endpoints, pages, or migrations.

Allowed preparatory correction made in Phase 1:

- `docker-compose.yml` now runs the active split apps from `crm/` and `website/` instead of the legacy `frontend/`.
- `website/Dockerfile` now exposes and starts Vite on port `5174`, matching README and Compose.

## Active Frontend Verification

The active CRM application is `crm/`.

Evidence:

- `README.md` names `crm/` as the independent CRM app and `website/` as the public website.
- `.github/workflows/ci.yml` installs, typechecks, lints, builds, and tests `crm/` and `website/`.
- `crm/src/app/router.tsx` owns `/crm`, `/crm/shop-entry`, `/crm/login/*`, `/crm/dashboard`, and all CRM module routes.
- `crm/src/lib/routes.ts` defines the canonical `/crm/...` route constants.
- `frontend/` remains as a legacy combined frontend. Several files are still duplicated there, but it must not receive new replacement work.
- Before Phase 1 correction, `docker-compose.yml` still built `./frontend`; this was an obvious runtime mismatch and has been corrected to build `./crm` and `./website`.

## Current Workflow Map

### Entry, Shop Selection, Auth

1. User opens `/crm`.
2. `crm/src/app/router.tsx` renders `LaunchPage` or redirects legacy paths into `/crm/...`.
3. `ShopEntryPage` calls `POST /api/v1/public/shops/resolve` through `crm/src/features/shops/api.ts`.
4. Resolved shop metadata is validated against `crm/src/features/shops/config.ts` and stored in session storage.
5. `ShopRoute` requires a selected shop before login or protected CRM pages.
6. Admin/staff login uses `LoginPage`, `crm/src/features/auth/api.ts`, and `POST /api/v1/auth/login`.
7. `ProtectedRoute` requires an active role and access token before loading `AppShell`.
8. `AppShell` renders `Sidebar`, `Header`, and protected module pages.
9. `Header` logout calls `/auth/logout` with the active refresh token through `useAuth`, then clears local state.

Backend responsibilities:

- `backend/app/api/v1/endpoints/public_shops.py` resolves public shop identifiers.
- `backend/app/api/v1/endpoints/auth.py` exposes config, admin registration, login, refresh, logout, and `me`.
- `backend/app/services/auth_service.py` handles password checks, rate limiting, refresh rotation, logout revocation, audit logs, email normalization, and shop mismatch protection.
- `backend/app/db/session.py` extracts shop context from `X-Shop-Key`, token, or host.
- `backend/app/api/deps.py` enforces token role and shop context.

### Customer Registration

Visible screen:

- `/crm/customers` -> `crm/src/pages/customers/CustomersPage.tsx`

Frontend flow:

1. Staff enters customer identity/contact fields.
2. Optional quick-add prescription and optional quick-add bill can be submitted from the same screen.
3. The page calls:
   - `createCustomer()` -> `POST /customers`
   - optionally `createPrescription()` -> `POST /prescriptions`
   - optionally `createBill()` -> `POST /bills`
4. Query caches for customers, prescriptions, and bills are invalidated.

Backend flow:

- `POST /api/v1/customers` -> `CustomerService.create_customer()`.
- `CustomerService` generates a shop-scoped `customer_id`, writes `Customer`, logs `customer.create`, commits, and optionally sends a welcome email.
- `CustomerRepository.create()` calls `assign_shop_scope()`.

Important current data shape:

- `Customer` contains long-term identity fields plus `purpose_of_visit`.
- The replacement should stop using `purpose_of_visit` for new visits. It should remain readable for legacy records.

### Customer Search

Visible screens:

- `/crm/customers` search box redirects to `/crm/customers/records`.
- `/crm/customers/records` -> `CustomerRecordsPage`.
- Prescription and billing create pages use customer search selectors.

Frontend flow:

- `CustomerRecordsPage` calls `listCustomers({ search })` -> `GET /customers`.
- `PrescriptionsPage` and `BillingPage` call `searchCustomers()` -> `GET /customers/search`.

Backend flow:

- `GET /customers` and `GET /customers/search` both use `CustomerService.list_customers()`.
- `CustomerRepository.list()` searches `customer_id`, `name`, `contact_no`, `email`, and `whatsapp_no`.
- All searches include `shop_filter()`.

### Customer Update

Current status:

- Backend supports update through `PUT /api/v1/customers/{customer_id}`.
- `crm/src/features/customers/api.ts` exposes `updateCustomer()`.
- No visible active CRM customer-edit screen was found in `crm/src/pages/customers`.

Replacement implication:

- The patient profile editor should reuse `PUT /customers/{id}` for long-term identity fields.
- Visit reason and encounter notes must move to new visit records, not customer profile updates.

### Customer History

Visible screen:

- `/crm/customers/records` -> `CustomerRecordsPage`.

Frontend flow:

1. The records list calls `GET /customers`.
2. Selecting a customer calls `GET /customers/{id}`.
3. Detail panel shows identity fields, prescription summaries, and bill summaries.
4. Row actions link to prescription creation/records or billing creation with prefilled query params.

Backend flow:

- `CustomerService.get_customer()` loads the customer with prescriptions and bills.
- It filters out soft-deleted prescriptions and bills and returns `CustomerDetailRead`.

Replacement implication:

- Customer history is reusable but must be extended later to include visits, clinical final prescriptions, dispensing orders, referrals, follow-ups, and legacy prescriptions.

### Prescription Creation

Visible screens:

- `/crm/prescriptions` -> `PrescriptionsPage`.
- `/crm/customers` can quick-add a prescription after customer creation.

Frontend flow:

- Both paths post a simple `PrescriptionPayload` with customer id, date, right/left SPH/CYL/axis/VN, FH, ADD, PD, and notes.

Backend flow:

- `POST /prescriptions` -> `PrescriptionService.create_prescription()`.
- Customer must exist in the current shop.
- `PrescriptionRepository.create()` inherits shop scope from the customer.
- Audit action: `prescription.create`.

Replacement implication:

- This is the old editable prescription workflow. It should remain available temporarily for legacy compatibility, then be demoted to historical/read-only once the new final-prescription workflow is complete.

### Prescription Update

Visible screen:

- `/crm/prescriptions/records` -> `PrescriptionsRecordsPage`.

Frontend flow:

- Records page opens an update modal and calls `PUT /prescriptions/{id}`.

Backend flow:

- `PrescriptionService.update_prescription()` modifies the existing row, logs `prescription.update`, and commits.

Replacement implication:

- New finalized prescriptions must not silently overwrite old values. Later phases need versioning/amendment behavior. Legacy updates can remain until the new final prescription is complete.

### Prescription PDF Generation and Download

Visible screen:

- `/crm/prescriptions/records` PDF action.

Frontend flow:

1. `generatePrescriptionPdf(id)` calls `POST /prescriptions/{id}/pdf`.
2. `openPrescriptionPdf(id)` calls authenticated `GET /prescriptions/{id}/pdf/download` as a blob.

Backend flow:

- `PrescriptionService.generate_pdf()` calls `PrescriptionPdfService.generate_prescription_pdf()`.
- File path is stored as an internal media reference in `Prescription.pdf_file_path`.
- `PrescriptionService.get_pdf_file_for_download()` verifies actor/shop context and returns a local path.
- `document_file_service.resolve_media_file_reference()` confines file access to `settings.prescription_media_dir`.
- In production, `backend/app/main.py` does not mount public static media.

Replacement implication:

- Legacy prescription PDFs remain valid.
- New clinical/final prescription PDFs must use authenticated download endpoints and internal file references.
- Generated documents based on outdated finalized data need version awareness in later phases.

### Vendor Sending

Visible screen:

- `/crm/prescriptions/records` Send Vendor modal.

Frontend flow:

1. Records page lists active vendors through `GET /vendors`.
2. It calls `POST /prescriptions/{id}/send-vendor`.

Backend flow:

- `PrescriptionService.send_to_vendor()` verifies prescription, customer, vendor, and vendor active status in the current shop.
- It generates a prescription PDF, uploads media through `WhatsAppService.upload_media()`, sends a WhatsApp document, logs WhatsApp details, and logs audit action `prescription.send_vendor_whatsapp`.

Replacement implication:

- Vendor sending should be reused, but later vendor documents must contain only order-fulfillment data, not full clinical visit data.

### Bill Creation, Items, Payments

Visible screens:

- `/crm/billing` -> `BillingPage`.
- `/crm/customers` can quick-add a legacy single-product bill after customer creation.

Frontend flow:

- `BillingPage` supports multiple line items and multiple payments using `useFieldArray`.
- It calculates client-side summaries with `calculateMultiBillSummary()`.
- It posts `BillPayload` through `createBill()`.
- The quick-add customer flow still maps to the legacy single-product bill shape.

Backend flow:

- `POST /bills` -> `BillService.create_bill()`.
- `BillService` supports both:
  - old single-product payloads, mapped to one `BillItem`;
  - new `items[]` and `payments[]` payloads.
- Totals are computed server-side: subtotal, discount_total, tax_total, grand_total, paid_total, balance_amount, payment_status.
- `BillRepository.create()` inherits shop scope from the customer.
- `BillService` auto-generates an invoice PDF and optionally sends email/WhatsApp if the customer is eligible.
- Audit action: `bill.create`; PDF auto action: `bill.generate_pdf.auto`.

Replacement implication:

- Billing is reusable without rebuilding.
- Future dispensing orders should link to bills and pass bill items/payments into the existing `BillService`.

### Bill Records, Invoice PDF, Send Actions

Visible screens:

- `/crm/billing/records` -> `BillingRecordsPage`.
- `/crm/billing/view/:billId` -> `BillingDetailPage`.
- `/crm/billing/edit/:billId` -> `BillingEditPage`.

Frontend flow:

- Records list calls `GET /bills`.
- Detail page calls `GET /bills/{id}`, previews secured PDFs via `GET /bills/{id}/pdf/download`, can generate PDF, send email, and send WhatsApp.
- Edit page updates bill items, payments, tax, delivery date, notes, and customer.

Backend flow:

- `GET /bills`, `GET /bills/{id}`, `PUT /bills/{id}`, `DELETE /bills/{id}`.
- `POST /bills/{id}/generate-pdf`.
- `GET /bills/{id}/pdf/download`.
- `POST /bills/{id}/send-email`.
- `POST /bills/{id}/send-whatsapp`.
- `InvoicePdfService` renders line items and payment rows.
- `BillService` keeps authenticated download and server-side email/WhatsApp sending.

Replacement implication:

- These pages can remain as billing records.
- Later order/delivery screens should link to bill detail rather than duplicating invoice UI.

### Dashboard Metrics

Visible screen:

- `/crm/dashboard` -> `DashboardPage`.

Frontend flow:

- `getDashboardSummary()` -> `GET /analytics/dashboard`.
- Admin-only revenue chart -> `GET /analytics/revenue/timeseries`.

Backend flow:

- `AnalyticsService` counts customers, prescriptions, bills generated today, paid/partial bill revenue, scheduled campaigns, and failed WhatsApp jobs.
- Revenue uses `Bill.paid_total` when available.
- All metrics use shop-scoped queries.

Replacement implication:

- Dashboard can remain unchanged until new visit/order records exist.
- Later phases can add draft visits, active dispensing orders, pending deliveries, and follow-ups.

### CRM Sidebar and Routes

Current protected modules:

- Dashboard
- Customers
- Prescriptions
- Vendors
- Billing
- Shop Chat
- Campaigns
- Analytics (admin)
- Staff (admin)

Current route constants are in `crm/src/lib/routes.ts`.

Replacement implication:

- The sidebar should eventually make the new patient/visit workflow the primary entry point.
- Legacy prescription creation should be removed from primary navigation only after the new final-prescription workflow is tested.

### Branch/Shop Isolation

Current pattern:

- Frontend sends `X-Shop-Key` from the active shop.
- Tokens include shop context.
- `get_current_user()` rejects token/shop mismatch.
- `shop_filter()` supports `shop_id` and legacy shop-key compatibility.
- Customer, prescription, bill, vendor, campaign, WhatsApp, audit, and chat repositories scope by shop.
- Tests cover cross-shop behavior for auth, billing/customer CRUD, document downloads, chat, and shop foundation.

Replacement rule:

- Every new patient-visit, exam, final-prescription, dispensing-order, follow-up, order-status, and document lookup must scope by `shop_id`.
- Customer-linked records should also verify the linked customer belongs to the same shop.

### Audit Logging

Current audit coverage:

- Customer create/update/delete.
- Prescription create/update/delete/PDF/vendor send.
- Bill create/update/delete/PDF/email/WhatsApp.
- Auth login failures, lockouts, registration attempts, refresh, logout.
- Vendor, staff, campaign flows also use service-level audit patterns.

Replacement rule:

- New services should call `AuditService.log()` for visit creation/update, section saves, finalization, amendments, document generation/download where supported, dispensing-order actions, delivery, and follow-up completion.

### File Storage

Current storage:

- `settings.media_root_path`, default `backend/storage`.
- Invoice PDFs: `backend/storage/invoices`.
- Prescription PDFs: `backend/storage/prescriptions`.
- Chat attachments: `backend/private_storage/chat`.
- Direct static media is mounted only in non-production.
- `document_file_service` validates internal file references against allowed directories.

Replacement rule:

- New clinical/final prescription PDFs and vendor order PDFs should store internal references.
- Sensitive clinical data must not be publicly browsable by URL.
- Vendor documents must not include unnecessary patient contact data or private examination findings.

### Docker and Development Startup

Current development commands:

- Backend: `backend/run_local.sh` or `uvicorn app.main:app`.
- DB setup: `python -m app.scripts.init_dev_db`.
- CRM: `cd crm && npm run dev -- --host 127.0.0.1 --port 5173`.
- Website: `cd website && npm run dev -- --host 127.0.0.1 --port 5174`.

Phase 1 correction:

- Docker Compose now uses `crm/` for port `5173`.
- Docker Compose now includes `website/` for port `5174`.
- `website/Dockerfile` now starts Vite on `5174`.

## Old Screens Affected by Replacement

| Current screen | Current role | Replacement direction | Temporary compatibility |
| --- | --- | --- | --- |
| `/crm/customers` (`CustomersPage`) | Customer registration plus optional quick prescription/bill | Replace primary entry with Patient Search / New Patient / Start Visit | Keep until visit creation and patient registration are tested |
| `/crm/customers/records` (`CustomerRecordsPage`) | Customer search and history | Extend into patient history with visits/orders/follow-ups | Keep and extend; do not delete |
| `/crm/prescriptions` (`PrescriptionsPage`) | Old simple prescription creation | Replace with visit workspace final prescription section | Keep temporarily; later hide from sidebar |
| `/crm/prescriptions/records` (`PrescriptionsRecordsPage`) | Legacy prescription list/edit/PDF/vendor send | Become historical prescription view plus new final prescriptions | Keep legacy records readable |
| `/crm/billing` (`BillingPage`) | Standalone bill creation | Reuse as bill module; new dispensing order can open/create bills | Keep standalone billing during migration |
| `/crm/billing/records` | Bill list | Keep | Extend filters by visit/order later |
| `/crm/billing/view/:billId` | Bill detail/PDF/send | Keep | Link from dispensing orders |
| `/crm/billing/edit/:billId` | Bill update | Keep | Use existing billing permissions |
| `/crm/dashboard` | KPIs | Keep initially | Extend after new records exist |
| `/crm/vendors` | Vendor records | Keep | Reuse for lens/order vendors |

## Old-To-New Backend Responsibility Mapping

| Existing responsibility | Current backend | New responsibility | Plan |
| --- | --- | --- | --- |
| Patient identity | `Customer`, `CustomerService`, `CustomerRepository` | Patient profile | Reuse and extend carefully; keep legacy fields |
| Visit reason | `Customer.purpose_of_visit` | Per-visit reason | New visit table/service; stop writing new reasons to customer profile |
| Simple prescription | `Prescription` model/service | Legacy prescription history | Keep readable; freeze/hide editable flow later |
| Final prescription | Old `Prescription` row | Versioned final prescription from visit | Add new model/service in later phase; preserve amendments |
| Billing | `Bill`, `BillItem`, `Payment`, `BillService` | Dispensing bill/payment | Reuse directly |
| Invoice PDF | `InvoicePdfService`, bill download endpoint | Invoice document | Reuse directly |
| Vendor send | Prescription vendor send + WhatsApp service | Vendor order document/send | Reuse WhatsApp/vendor primitives; add narrow vendor-order document |
| Customer history | `CustomerDetailRead` with prescriptions/bills | Patient history timeline | Extend with visits/final prescriptions/orders/follow-ups |
| Dashboard | `AnalyticsService` | Operational KPIs | Extend later |
| Auth/session/shop | Auth service, dependencies, shop scope | Same | Reuse without replacement |
| Audit | `AuditService` | Expanded clinical/order audit | Reuse service; add actions |
| File storage | media/private storage services | Protected docs | Reuse pattern |

## Reusable Modules Without Major Changes

- Auth endpoints, token refresh/logout, rate limiter, `ProtectedRoute`, `ShopRoute`.
- Shop registry and resolver.
- `shop_filter()`, `assign_shop_scope()`, and shop-scoped repository pattern.
- `CustomerService` for identity creation/search/update, with careful extension.
- `BillService`, `BillItem`, `Payment`, invoice PDF generation, bill PDF download, email/WhatsApp send.
- `VendorService` and vendor repository.
- `WhatsAppService` and WhatsApp log repository.
- `AuditService`.
- `document_file_service`.
- `AnalyticsService` initially.
- CRM API client, auth store, shop store, error handling, toasts, loading/error patterns.
- Existing billing form components/patterns and bill calculations.

## Modules That Need Extension

- Customer schemas/model for true patient fields such as date of birth, occupation, guardian details, and profile notes, if product-approved.
- Customer detail response to include visits, final prescriptions, dispensing orders, referrals, follow-ups, and legacy prescriptions.
- Analytics service for draft visits, pending orders, delivery, follow-ups.
- PDF services for new final prescription and vendor order documents.
- Sidebar/routes to add patient/visit workspace and later demote legacy prescription creation.
- Tests to cover new visit isolation, finalization, amendments, and billing links.

## Replacement Modules To Add In Later Phases

These are not implemented in Phase 1.

- Patient visit / encounter model, repository, service, schemas, endpoints.
- Clinical examination section persistence for visual acuity, objective refraction, subjective refraction, binocular vision, cycloplegic refraction, potential vision, torch-light, slit-lamp, referral, contact-lens work-up, and disabled/future IOP.
- Final prescription version/amendment model.
- Dispensing order model for frame, lens, measurements, vendor, processing, delivery.
- Follow-up model.
- Visit workspace CRM pages/components.
- Patient history timeline UI.

## Legacy Compatibility Strategy

- Keep old `customers`, `prescriptions`, and `bills` APIs until replacement is complete and tested.
- Keep old `Prescription` rows readable and PDF-downloadable.
- Keep old prescription update only while the replacement is not complete. Once new final prescriptions launch, old prescriptions should become historical/read-only unless the owner explicitly requires legacy editing.
- Do not migrate or overwrite existing prescription rows during early phases.
- Do not delete old visible screens until the replacement screen has tests and staff can complete the equivalent workflow.
- Keep legacy route redirects in `AppRouter` while bookmarks may exist.
- Do not write new replacement code in `frontend/`.

## Duplicated Old Flow

- `CustomersPage` quick-add prescription duplicates `PrescriptionsPage`.
- `CustomersPage` quick-add bill duplicates `BillingPage`.
- Billing create and billing edit each duplicate form-building logic for items/payments.
- `frontend/` duplicates many active CRM pages and feature APIs, while route files have diverged.
- Old `Prescription` overlaps conceptually with the future final prescription, but it lacks visit linkage, finalization, and amendment rules.

## Implementation Risks

- Data loss if old prescriptions are modified in place instead of preserved as legacy history.
- Cross-shop data leakage if new visit/order queries do not use `shop_id` and linked customer checks.
- Stale documents if PDFs generated before prescription amendments remain active without versioning.
- Vendor privacy issue if full clinical records are sent for lens/order fulfillment.
- Broken deployment if future work targets `frontend/` instead of `crm/`.
- Broken local Docker flow if Compose and README diverge again.
- Billing inconsistency if future dispensing totals duplicate `BillService` calculations.
- Customer history confusion if old `purpose_of_visit` is mixed with new visit reasons.
- Migration complexity if new final prescriptions and old prescriptions are shown as the same editable object.

## Recommended Phase Order

### Phase 1 - Repository Verification and Plan

Status: this document. No clinical workflow built.

### Phase 2 - Patient Visit Data Foundation

Add backend models/schemas/repositories/services/endpoints for visits, draft status, section status metadata, and shop-scoped listing. Reuse `Customer` for patient identity. Add tests for create/list/get/update draft visits and cross-shop isolation.

### Phase 3 - CRM Patient Entry and Visit Shell

Add CRM route(s) for patient search/register/start visit/resume draft. Reuse customer search/create APIs and add visit APIs. Sidebar primary action becomes patient/visit workflow, while old create screens remain accessible.

### Phase 4 - Examination Workspace Draft Sections

Add step/tabs for visual acuity, refraction stages, binocular vision, optional cycloplegic, potential vision, torch-light, slit-lamp, referral, contact-lens work-up, and disabled IOP placeholder. Save incomplete sections as drafts with validation and section status.

### Phase 5 - Final Prescription Versioning

Add explicit review/finalize action. Finalized prescriptions become read-only. Corrections create amendments or new versions. Keep legacy prescriptions historical.

### Phase 6 - Dispensing Order and Billing Link

Add frame selection, dispensing measurements, lens order, vendor/order status, and delivery workflow. Create or link bills through existing `BillService`, `BillItem`, and `Payment`.

### Phase 7 - Documents, Vendor Order PDF, Follow-Up, Analytics

Add protected final prescription PDFs, narrow vendor order documents, follow-ups, delivery logs, dashboard metrics, and patient history timeline.

### Phase 8 - Legacy Navigation Cleanup

After tests and manual QA, remove old primary create navigation for prescriptions/customer quick-add. Keep legacy records and APIs long enough for rollback and historical access.

## Test Strategy

Backend:

- Unit/service tests for visit CRUD and section draft saves.
- Cross-shop isolation tests for every new model and endpoint.
- Final prescription finalization/amendment tests.
- PDF permission tests for new documents.
- Billing integration tests that a dispensing order creates/links a bill without duplicating calculations.
- Audit log tests for visit creation/update, finalization, amendment, order status, delivery, follow-up.
- Existing tests that must remain passing: auth, customer/billing CRUD, document downloads, single-db shop foundation, public shop resolver, chat isolation, health/config.

Frontend:

- Route tests for new patient/visit routes under `/crm`.
- Patient search/register/start visit tests.
- Protected route and shop-selection tests remain.
- Visit workspace tests for section status, draft save, optional sections, finalization confirmation.
- Billing link tests from dispensing order to existing billing pages.
- API error rendering tests.

Build/quality:

- Backend compile and selected pytest tests after each phase.
- CRM typecheck, lint, build, and relevant Vitest tests after UI phases.
- Docker Compose configuration should be smoke-checked after infrastructure changes.

## Stop Condition

Phase 1 stops here. The next phase should not begin until this plan is reviewed and the Phase 2 scope is explicitly approved.
