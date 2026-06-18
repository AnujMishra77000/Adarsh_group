# Phase 11 Old CRM Flow Replacement Design

## Objective

Make the rebuilt patient-to-follow-up workflow the default visible CRM journey while preserving read access and route compatibility for legacy records. Phase 11 changes navigation, routing, operational queues, dashboard metrics, and visible legacy prescription actions. It does not replace the Phase 1-10 backend workflow or delete compatibility APIs and tables.

## Compatibility Findings

The current patient page already registers patients, creates visits, and opens the visit workspace. The visit workspace already owns examinations, versioned prescription finalization and amendments, spectacle and contact-lens orders, billing handoff, delivery, and follow-ups.

The remaining visible conflicts are:

- The primary Prescriptions navigation opens the legacy standalone creation form.
- Legacy saved prescriptions still expose update, delete, and vendor-send actions.
- The sidebar does not expose Visits, Orders, or Follow-Ups as operational modules.
- Dashboard prescription totals use the legacy prescription table and omit the rebuilt workflow states.

## Navigation

Primary operational navigation will be:

- Dashboard
- Patients
- Visits
- Prescriptions
- Orders
- Billing
- Vendors
- Follow-Ups
- Reports

Prescriptions opens the historical read-only records page. Visits, Orders, and Follow-Ups open filtered views of one shared Operations Queue page. Reports opens the existing analytics module.

Shop Chat, Campaigns, and Staff remain accessible as secondary tools. Staff remains admin-only and serves as the current settings-equivalent module. Existing role restrictions remain unchanged.

The mobile navigation must remain usable after adding modules. It will use a horizontally scrollable navigation row rather than compressing every item into narrow grid columns.

## Routes And Redirects

The following route behavior will apply:

- `/crm/customers` remains the default patient search, registration, and start-visit flow.
- `/crm/visits` opens the Operations Queue on Visits.
- `/crm/visits/:visitId` continues to open the existing visit workspace.
- `/crm/orders` opens the Operations Queue on Orders.
- `/crm/follow-ups` opens the Operations Queue on Follow-Ups.
- `/crm/prescriptions/records` remains the legacy historical prescription viewer.
- `/crm/prescriptions` redirects to `/crm/customers` because it was the old standalone creation route.
- `/crm/prescriptions/create` redirects to `/crm/customers`.
- Unprefixed legacy bookmarks continue through the existing `/crm` compatibility redirect and then reach the safe destination.
- Unknown CRM routes continue to use the existing safe root redirect.

Links that intend to view old prescriptions, including patient-history actions, must point directly to `/crm/prescriptions/records` and preserve supported customer filters. Links that intend to create a prescription must point to the patient/start-visit flow.

## Legacy Prescription Records

Legacy prescription records remain searchable and viewable. Existing PDF/document access remains available so historical clinical documents are not lost.

The visible legacy record page will no longer expose:

- inline prescription editing,
- prescription deletion,
- direct vendor-order sending.

Those actions conflict with versioned finalization and the order workflow. Backend compatibility endpoints remain intact for migration and historical compatibility; Phase 11 only removes the conflicting actions from the primary CRM interface.

## Operations Queue

One shared Operations Queue page will serve three routes to avoid duplicated page and filtering logic.

### Visits View

Show shop-scoped visits with patient, date, reason, examiner, and status. Support status filtering for draft, in-progress, completed, and cancelled visits. Opening a row navigates to the existing visit workspace.

### Orders View

Combine spectacle and contact-lens orders. Show order type, reference, patient, visit, status, expected delivery date, delayed state, and delivery timestamp. Clearly emphasize cancelled, delayed, and ready-for-delivery orders. Opening a row navigates to the owning visit workspace.

### Follow-Ups View

Show typed follow-ups with patient, visit, due date, assigned staff, status, reminder state, and completion notes. Default attention to pending and overdue follow-ups. Opening a row navigates to the owning visit workspace where completion remains auditable.

The backend will expose one shop-scoped operational queue response containing visits, orders, and follow-ups. This endpoint is read-only and reuses existing models and transition services.

## Dashboard

Dashboard workflow metrics will be calculated from the rebuilt models:

- active visits,
- draft visits,
- completed examinations,
- current finalized visit prescriptions,
- pending orders across spectacle and contact-lens workflows,
- ready-for-delivery orders,
- pending follow-ups due today or overdue,
- recorded referrals,
- bills generated today,
- revenue today using the existing confirmed-payment calculation.

Existing stable customer, campaign, WhatsApp failure, and revenue trend information may remain as secondary metrics. The legacy total-prescriptions metric will be replaced by finalized visit prescriptions.

Dashboard operational cards will link to their corresponding Patients, Visits, Prescriptions, Orders, Billing, or Follow-Ups route where useful.

## Data Flow

1. Staff enters through Patients or an operational queue.
2. Creating clinical work always begins with a visit.
3. Examination, final prescription, amendments, orders, billing, delivery, and follow-ups continue through the existing visit workspace and Phase 10 services.
4. Operations Queue reads shop-scoped summaries and links back to the visit workspace; it does not mutate order or follow-up state directly.
5. Dashboard reads aggregate values from the same rebuilt models and existing billing calculations.
6. Legacy prescription records are read-only in the visible CRM and remain backed by existing compatibility APIs.

## Error And Empty States

- Safe redirects use `replace` to prevent redirect loops in browser history.
- Operations Queue shows explicit loading, API-error, and empty states for each view.
- Shop scoping remains enforced by existing backend dependencies and query filters.
- Cancelled and delayed orders receive distinct visual treatment.
- Overdue follow-ups are derived from pending status plus due date and receive distinct visual treatment.
- Missing legacy records continue to use existing API error handling rather than falling into the new editable workflow.

## Testing

Backend tests will verify:

- shop-scoped operational queue results,
- both order types appear with correct status and delayed data,
- due follow-up and visit summaries are returned,
- dashboard metrics use visit prescriptions, visits, orders, follow-ups, referrals, and existing billing totals,
- cross-shop data is excluded.

CRM tests will verify:

- sidebar navigation contains the new operational modules without duplicate prescription creation,
- old prescription creation bookmarks redirect to Patients,
- Prescriptions opens historical records,
- legacy records are viewable without edit, delete, or vendor-send controls,
- Operations Queue route filtering and visit navigation,
- dashboard cards reflect the rebuilt workflow response,
- existing CRM tests remain green.

## Out Of Scope

- Deleting legacy backend prescription, customer, invoice, or document compatibility APIs.
- Rewriting Phase 1-10 clinical or billing services.
- Building a new messaging platform.
- Reintroducing the removed `frontend/` application.
- Starting Phase 12.
