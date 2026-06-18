# Adarsh CRM Replacement Phase 8 Design

## Scope

Phase 8 connects visits and spectacle dispensing orders to the existing bill, bill-item, payment, invoice, email, and WhatsApp implementation. It does not create a second pricing engine or add contact-lens clinical/order functionality.

## Verified Existing Authority

`BillService` remains authoritative for item totals, discounts, GST/tax, grand total, payment totals, balance, payment status, invoice PDF generation, and bill cancellation. The active `crm/` billing pages remain the only editable billing forms. Phase 8 adds context and navigation around that flow.

## Data Linkage

Add nullable `visit_id` and `dispensing_order_id` foreign keys to `bills`.

- A visit may have multiple bills.
- A dispensing order may have one active bill.
- A partial unique index on `dispensing_order_id` where `is_deleted = false` prevents duplicate active bills while allowing a replacement after the existing bill is cancelled through current soft-delete rules.
- The bill is the persisted owner of the links. ORM/API relationships expose the linked bill from the visit/order side without duplicating `bill_id` columns or any totals.
- Existing bills retain null context links and remain unchanged.

No `contact_lens_order_id` is added because the repository has no contact-lens-order model. The existing `contact_lens` bill-item type continues to work and a future contact-lens order can adopt the same integration boundary.

## Validation

Creating or linking a contextual bill verifies that the visit, dispensing order, bill, and customer all belong to the current shop and refer to the same patient. If both visit and order are supplied, they must match. Linking changes only the context foreign keys; it never rewrites items, totals, payments, invoice paths, or timestamps unrelated to the link.

## API

- Existing `POST /bills` accepts optional `visit_id` and `dispensing_order_id` and still delegates all calculations to `BillService`.
- `GET /visits/{visit_id}/billing` returns active linked bills and the active bill linked to the visit's dispensing order. All amounts are read directly from `Bill`.
- `POST /visits/{visit_id}/billing/link` links an existing same-shop, same-customer bill to the visit and optional dispensing order without changing financial data.

## CRM Flow

The visit Billing section becomes a compact billing integration panel, not another billing form. It shows official bill summaries, offers `Create Bill`, `Link Existing Bill`, `Open Bill`, and returns users to the visit.

The existing Billing page accepts visit/order context in query parameters, preselects the patient, and uses non-priced frame/lens/coating names from the order as editable item suggestions. Staff enter the official prices, discounts, tax, and payments in the existing form. After creation, the app opens the existing bill-detail/invoice page with a safe CRM return path.

The dispensing-order workspace exposes the same create/open billing handoff. Order edits never synchronize into an existing bill, preventing silent changes to financial records.

## Compatibility and Privacy

- Legacy and unrelated bills keep null linkage and existing behavior.
- Existing CRUD, payment, invoice, PDF download, email, WhatsApp, audit, and soft-delete behavior remains authoritative.
- All new reads and writes are shop-scoped.
- No financial totals are stored on visits or dispensing orders.

## Test Strategy

Backend tests cover contextual creation using current calculations, duplicate active-order protection, replacement after cancellation, no-mutation linking, customer/shop mismatch rejection, and legacy null links. CRM tests cover contextual handoff, order item suggestions, official bill summaries, existing-bill linking, and safe return navigation.

