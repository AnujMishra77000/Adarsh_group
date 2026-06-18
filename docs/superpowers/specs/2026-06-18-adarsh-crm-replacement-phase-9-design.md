# Adarsh CRM Replacement Phase 9 Design

## Scope

Phase 9 adds a conditional contact-lens work-up, one contact-lens order per visit, a scheduled follow-up task, patient-history summaries, and a handoff to the existing billing system. It does not alter spectacle dispensing, rebuild billing, add a second customer record, or introduce an unrelated task-management module.

## Considered UI Approaches

1. **One continuous form:** Simple, but too long for routine desktop use and inconsistent with section-based saving.
2. **Embedded section workspace:** Selected. Contact Lens remains in the existing visit sidebar and uses compact internal tabs with explicit save states.
3. **Modal wizard:** Helpful for first-time guidance, but it interrupts visit navigation and makes review or correction slower.

## Visibility and Activation

Contact Lens remains hidden and non-mandatory for ordinary spectacle visits. The backend marks it visible when any of these conditions is true:

- the visit reason clearly contains a contact-lens intent;
- `contact_lens_workup_requested` is selected for the visit;
- a contact-lens work-up record exists; or
- a contact-lens order exists.

Existing visits default to `contact_lens_workup_requested=false`. The conditional area in the current section navigation exposes a `Start Contact Lens Work-up` action. Activation sets the visit flag, creates no order or bill, and opens an incomplete draft. Starting an order also activates the section.

## Clinical Work-Up

Clinical contact-lens data remains a structured payload on the visit's existing `contact_lens` exam-section record. This preserves the established visit/section save architecture and naturally keeps each visit's historical values separate.

The payload contains:

- `indication`: cosmetic, refractive, keratoconus, sports, therapeutic, or other with custom text;
- `assessment`: right/left K readings, right/left HVID, right/left tear-film assessment, right/left TBUT, and clinical notes;
- `prescription`: separate right/left power, base curve, and diameter;
- `lens_details`: brand, material, replacement schedule, and wearing schedule;
- `trial_training`: trial dispensed, insertion/removal training status, and notes.

Draft saves permit incomplete values. Marking the section complete validates indication, custom indication when `other` is selected, non-negative measurements, and distinct right/left prescription structures. An order draft requires sufficient contact-lens prescription and lens-detail values, but optional clinical fields never block a routine spectacle visit.

## Contact-Lens Order

A new branch-scoped `contact_lens_orders` table stores one order per visit. It links to the visit and customer, optionally links to an existing vendor, and stores an order reference, the selected work-up snapshot, order-specific lens details, notes, status, creator/updater, and timestamps.

The order uses the same lifecycle vocabulary as spectacle orders:

`draft -> ready_for_vendor -> sent_to_vendor -> in_production -> ready_for_delivery -> delivered`

Cancellation follows the existing spectacle-order transition rules. Work-up edits do not silently mutate a non-draft order. Status changes and delivery are recorded through the existing audit-log service. Phase 9 does not add a contact-lens vendor PDF or WhatsApp document because the requested phase does not define one.

## Follow-Up Task

A focused `follow_up_tasks` table introduces the master instruction's follow-up concept without building a general task-management UI. Each task is branch-scoped and links to the customer, visit, and contact-lens order. It stores type, due date, status, notes, completion metadata, and user tracking.

The contact-lens workspace supports one week, fifteen days, one month, or a custom date. Saving the selection creates or updates the pending task idempotently. Completing or cancelling a task preserves it in history. A completed task is not silently reopened or overwritten.

## Billing Integration

`Bill` gains a nullable `contact_lens_order_id` foreign key and a partial unique index allowing one active bill per contact-lens order. The existing `BillService` remains authoritative for contact-lens items, discounts, GST/tax, payments, totals, balance, invoice generation, cancellation, email, and WhatsApp.

The visit billing context returns the active contact-lens order bill. `BillingPage` accepts a contact-lens order context, prefills one existing `contact_lens` bill item with safe descriptive details and zero price, and requires staff to confirm price, discount, tax, and payment. Order changes never synchronize into an existing bill.

## CRM Layout

The existing visit sidebar and page shell remain unchanged. Once activated, Contact Lens opens a single embedded workspace with internal tabs:

1. Work-up
2. Prescription
3. Trial & Training
4. Order
5. Follow-up

The patient, visit, visit status, and section status remain visible in the existing sticky header. Right and left eye values use the established paired-eye visual pattern. Each tab shows clear idle, dirty, saving, saved, and failed states. Unsaved-change protection follows the current visit workspace behavior. Billing uses `Create Bill` or `Open Bill` links to the shared billing pages and returns to the visit.

## Patient History and Isolation

Customer detail responses add compact contact-lens-order and follow-up summaries. The current Customer Records page shows these alongside visits, prescriptions, referrals, and bills. Existing historical records remain unchanged.

Every work-up, order, follow-up, and bill lookup scopes through the current shop. Cross-shop access returns not found and is covered by service tests. Legacy visits, bills, prescriptions, and spectacle orders remain compatible because all new fields and relationships are nullable or defaulted.

## Error Handling

- Draft work-up validation errors are shown without discarding entered values.
- Order creation rejects a visit/customer mismatch or missing required work-up values.
- Duplicate order and duplicate active-bill requests return clear conflict errors.
- Follow-up creation is idempotent for repeated submissions.
- Billing failures leave the work-up and order intact and allow retrying through the shared billing screen.

## Testing

Backend tests cover conditional visibility, right/left persistence, completed-section validation, one order per visit, status transitions, follow-up interval calculation, idempotency, billing linkage, patient history, and cross-shop isolation. CRM tests cover activation, internal tab navigation, independent save feedback, right/left fields, trial/training, order actions, follow-up scheduling, billing handoff, and hidden behavior for ordinary visits.

## Compatibility Decisions

- One contact-lens work-up and one contact-lens order are supported per visit.
- Existing visit reasons are used for safe contact-lens intent detection; no speculative general visit-type taxonomy is introduced.
- The manual activation flag provides an explicit path when the reason text is ambiguous.
- Spectacle orders, legacy prescriptions, invoices, and existing billing records are not modified.
